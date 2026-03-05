# Standard library
import binascii
from datetime import datetime, timedelta, timezone
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import math
import os
import smtplib
import ssl
from string import Template
import traceback as tb
from typing import Any, Dict, List, Optional

# Third-party
from croniter import croniter
import qrcode
import qrcode.constants

# Local
from db.mails import Mail
from db.orders import Order
from db.runs import Run
from log import log
from settings import settings

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "emails")
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

_SLIPPAGE_THRESHOLD = 0.03  # 3% fill price vs expected price
_FEE_RATIO_THRESHOLD = 0.005  # 0.5% fee as share of fill value
_FX_DRIFT_THRESHOLD = 0.02  # 2% fill FX rate vs submission FX rate


def _czech_account_to_iban(account: str) -> str:
    """Convert a Czech account number (e.g. '19-123456789/0800') to IBAN (e.g. 'CZ...')."""
    number_part, bank_code = account.split("/")
    if "-" in number_part:
        prefix, base = number_part.split("-")
    else:
        prefix, base = "0", number_part
    bban = f"{bank_code:0>4}{int(prefix):06d}{int(base):010d}"
    # IBAN check digits: rearrange as BBAN + "CZ00", replace letters, mod-97
    numeric = int(bban + "123500")  # C=12, Z=35, 00
    check = 98 - (numeric % 97)
    return f"CZ{check:02d}{bban}"


def _make_spd_qr(account: str, vs: str, amount: float) -> bytes:
    """Return PNG bytes of a Czech SPD QR code for the given account, variable symbol, and amount."""
    iban = _czech_account_to_iban(account)
    # Build canonical SPAYD (keys sorted alphabetically) for CRC32, then append checksum
    parts = sorted(
        [f"ACC:{iban}", f"AM:{amount:.2f}", "CC:CZK", f"X-VS:{vs}"],
        key=lambda p: p.split(":")[0],
    )
    canonical = "SPD*1.0*" + "*".join(parts)
    crc = binascii.crc32(canonical.encode("utf-8")) & 0xFFFFFFFF
    spd = f"{canonical}*CRC32:{crc:08X}"
    img = qrcode.make(spd, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")  # type: ignore[call-arg]
    return buf.getvalue()


def _runs_in_next_30_days(cron_expr: str) -> int:
    """Count how many times a cron schedule fires in the next 30 calendar days (max once per day)."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=30)
    cron = croniter(cron_expr, now)
    seen_dates: set = set()
    while True:
        nxt = cron.get_next(datetime)
        if nxt > end:
            break
        seen_dates.add(nxt.date())
    print(f"seen dates: {len(seen_dates)}")
    return len(seen_dates)


class Mailer:
    """Sends alert emails for investment lifecycle events."""

    my_mail: str = settings.my_mail
    mail_recipient: str = settings.mail_recipient
    mail_host: str = settings.mail_host
    mail_port: int = settings.mail_port
    mail_password: str = settings.mail_password

    def __init__(self) -> None:
        pass

    @staticmethod
    def _load_template(name: str) -> Template:
        """Load an HTML email template by filename from the templates/emails directory."""
        path = os.path.join(_TEMPLATE_DIR, name)
        with open(path, "r", encoding="utf-8") as f:
            return Template(f.read())

    def _send(
        self,
        subject: str,
        plain: str,
        html: str,
        mail_type: str,
        period: Optional[str] = None,
        extra_images: Optional[Dict[str, bytes]] = None,
    ) -> None:
        """Send a multipart email (plain-text + HTML + inline logo) via SMTP_SSL, then persist to DB. Logs and re-raises on failure."""
        # multipart/related wraps HTML + inline image together
        msg = MIMEMultipart("related")
        msg["From"] = self.my_mail
        msg["To"] = self.mail_recipient
        msg["Subject"] = subject

        # multipart/alternative carries plain-text fallback + HTML
        alt = MIMEMultipart("alternative")
        msg.attach(alt)
        alt.attach(MIMEText(plain, "plain"))
        alt.attach(MIMEText(html, "html"))

        # Inline logo attached with Content-ID so templates can reference cid:logo
        logo_path = os.path.join(_ASSETS_DIR, "logo_white.png")
        with open(logo_path, "rb") as f:
            logo = MIMEImage(f.read(), "png")
        logo.add_header("Content-ID", "<logo>")
        logo.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(logo)

        # Optional extra inline images (e.g. QR codes) keyed by Content-ID
        for cid, data in (extra_images or {}).items():
            img = MIMEImage(data, "png")
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
            msg.attach(img)

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(
                self.mail_host, self.mail_port, context=context, timeout=20
            ) as server:
                server.login(self.my_mail, self.mail_password)
                server.send_message(msg)
                log.info(f"Email sent: {subject}")
        except Exception as e:
            log.error(f"SMTP error: {repr(e)}")
            raise

        Mail(type=mail_type, subject=subject, period=period).post_to_db()

    def send_investment_confirmation(
        self,
        run: Run,
        orders: List[Order],
        cash_distribution: Dict[str, float],
        multipliers: Dict[str, float],
    ) -> None:
        """Send confirmation email after a successful investment run."""
        total_czk = sum(cash_distribution.values())
        exchange_map: Dict[str, str] = {o.t212_ticker: o.exchange for o in orders}

        # Plain text
        plain_lines = [
            "Investment run complete.",
            "",
            f"Run ID:    {run.id}",
            f"Timestamp: {run.started_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Total CZK: {round(total_czk)}",
            "",
            f"{'Ticker':<12} {'CZK':>10} {'Multiplier':>12} {'Exchange':>10}",
            f"{'-' * 46}",
        ]
        for ticker, czk in sorted(cash_distribution.items(), key=lambda x: -x[1]):
            mult = multipliers.get(ticker, 1.0)
            exchange = exchange_map.get(ticker, "")
            plain_lines.append(
                f"{ticker:<12} {czk:>10.2f} {mult:>12.2f} {exchange:>10}"
            )

        # HTML rows
        row_html = []
        for i, (ticker, czk) in enumerate(
            sorted(cash_distribution.items(), key=lambda x: -x[1])
        ):
            mult = multipliers.get(ticker, 1.0)
            exchange = exchange_map.get(ticker, "—")
            bg = "#f8faff" if i % 2 == 0 else "#ffffff"
            mult_color = "#16a34a" if mult > 1.0 else "#1e293b"
            czk_str = f"{czk:_.2f}".replace("_", "\u00a0")
            row_html.append(
                f'<tr style="background-color:{bg};">'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;font-weight:600;">{ticker}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{czk_str}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:{mult_color};text-align:right;font-weight:600;">{mult:.2f}×</td>'
                f'<td style="padding:10px 14px;font-size:12px;color:#6b7280;text-align:right;">{exchange}</td>'
                f"</tr>"
            )

        run_id_short = str(run.id)[:8] + "…" if run.id else "—"
        html = self._load_template("investment_confirmation.html").substitute(
            run_id_short=run_id_short,
            timestamp=run.started_at.strftime("%Y-%m-%d %H:%M UTC"),
            date_label=run.started_at.strftime("%B %-d, %Y"),
            total_czk=f"{round(total_czk):_}".replace("_", "\u00a0"),
            order_rows="\n".join(row_html),
        )

        self._send(
            "✅ [auto-invest] Investment complete",
            "\n".join(plain_lines),
            html,
            mail_type="investment_confirmation",
        )

    def send_error_alert(self, error: Exception, run: Optional[Run] = None) -> None:
        """Send error alert email when an investment run fails."""
        traceback_str = tb.format_exc()
        banner_message = (
            "An error occurred during the investment run."
            if run
            else "An unexpected error occurred."
        )

        # Plain text
        plain_lines = [banner_message, ""]
        if run:
            plain_lines += [
                f"Run ID:  {run.id}",
                f"Started: {run.started_at.strftime('%Y-%m-%d %H:%M UTC')}",
                "",
            ]
        plain_lines += [f"Error: {repr(error)}", "", "Traceback:", traceback_str]

        # HTML run context block
        if run:
            run_context_block = (
                "<tr><td style='padding:16px 40px 0;'>"
                "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
                "<td width='50%' style='padding-right:8px;'>"
                "<div style='background-color:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:14px 16px;'>"
                "<p style='margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Run ID</p>"
                f"<p style='margin:6px 0 0;font-size:12px;color:#1e3a8a;font-weight:700;word-break:break-all;'>{str(run.id)[:8]}…</p>"
                "</div></td>"
                "<td width='50%'>"
                "<div style='background-color:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:14px 16px;'>"
                "<p style='margin:0;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Started</p>"
                f"<p style='margin:6px 0 0;font-size:12px;color:#1e3a8a;font-weight:700;'>{run.started_at.strftime('%Y-%m-%d %H:%M UTC')}</p>"
                "</div></td>"
                "</tr></table></td></tr>"
            )
        else:
            run_context_block = ""

        alert_dt = run.started_at if run else datetime.now(timezone.utc)
        html = self._load_template("error_alert.html").substitute(
            banner_message=banner_message,
            date_label=alert_dt.strftime("%B %-d, %Y"),
            run_context_block=run_context_block,
            error_repr=repr(error),
            traceback=traceback_str,
        )

        self._send(
            "🔴 [auto-invest] ERROR",
            "\n".join(plain_lines),
            html,
            mail_type="error_alert",
        )

    @staticmethod
    def _compute_warnings(orders: List[Order]) -> List[Dict[str, str]]:
        """Scan filled orders for anomalies: price slippage, high fees, and FX rate drift.

        Groups identical ticker+type warnings and reports count + average deviation.
        fx_rate is stored as foreign/CZK; fill_fx_rate is stored as CZK/foreign,
        so the comparable baseline is 1/fx_rate.
        """
        raw: List[Dict[str, str]] = []
        for o in orders:
            if o.status != "FILLED":
                continue

            # Order was filled for different price than ordered
            if o.fill_price and o.price and o.price > 0:
                slippage = abs(o.fill_price - o.price) / o.price
                if slippage > _SLIPPAGE_THRESHOLD:
                    direction = "above" if o.fill_price > o.price else "below"
                    raw.append(
                        {
                            "ticker": o.t212_ticker,
                            "type": "Price slippage",
                            "detail": f"{slippage * 100:.1f}% {direction}",
                            "pct": f"{slippage * 100:.1f}",
                        }
                    )

            # Fees were too high
            if o.fee_czk and o.filled_total_czk and o.filled_total_czk > 0:
                fee_ratio = o.fee_czk / o.filled_total_czk
                if fee_ratio > _FEE_RATIO_THRESHOLD:
                    raw.append(
                        {
                            "ticker": o.t212_ticker,
                            "type": "High fee",
                            "detail": f"{fee_ratio * 100:.2f}% of fill",
                            "pct": f"{fee_ratio * 100:.2f}",
                        }
                    )
            # Currency rate changed severly between order creation and order fullfillment
            if o.currency != "CZK" and o.fill_fx_rate and o.fx_rate and o.fx_rate > 0:
                fx_drift = abs(o.fill_fx_rate - o.fx_rate) / o.fx_rate
                if fx_drift > _FX_DRIFT_THRESHOLD:
                    direction = "better" if o.fill_fx_rate > o.fx_rate else "worse"
                    raw.append(
                        {
                            "ticker": o.t212_ticker,
                            "type": "FX shift",
                            "detail": f"{fx_drift * 100:.1f}% {direction}",
                            "pct": f"{fx_drift * 100:.1f}",
                        }
                    )

        # Group by ticker+type, accumulate pct values for averaging
        groups: Dict[str, Dict[str, Any]] = {}
        for w in raw:
            key = f"{w['ticker']}|{w['type']}"
            if key not in groups:
                groups[key] = {"ticker": w["ticker"], "type": w["type"], "pcts": [], "details": []}
            groups[key]["pcts"].append(float(w["pct"]))
            groups[key]["details"].append(w["detail"])

        warnings: List[Dict[str, str]] = []
        for g in groups.values():
            count = len(g["pcts"])
            avg = sum(g["pcts"]) / count
            occurrences = f"{count}×" if count > 1 else ""
            # Extract direction from last detail (they should all agree)
            direction_word = g["details"][-1].split()[-1]  # "above"/"below"/"better"/"worse"
            warnings.append(
                {
                    "ticker": g["ticker"],
                    "type": g["type"],
                    "detail": f"{occurrences} avg {avg:.1f}% {direction_word}".strip(),
                }
            )

        return warnings

    def send_monthly_summary(
        self,
        runs: List[Run],
        orders: List[Order],
        failed_runs: Optional[List[Run]] = None,
    ) -> None:
        """Send monthly summary email with investment totals and any issues for the previous month."""
        all_runs = runs + (failed_runs or [])
        if not all_runs:
            return

        anchor_run = min(all_runs, key=lambda r: r.started_at)
        month_label = anchor_run.started_at.strftime("%B %Y")
        num_runs = len(runs)

        successful_orders = [
            o for o in orders if o.status not in ("FAILED", "CANCELLED", "UNKNOWN")
        ]
        ticker_totals: Dict[str, float] = {}
        for o in successful_orders:
            ticker_totals[o.t212_ticker] = (
                ticker_totals.get(o.t212_ticker, 0.0) + o.total_czk
            )
        total_czk = sum(ticker_totals.values())

        # Collect issues
        error_orders = [
            o
            for o in orders
            if o.status in ("FAILED", "CANCELLED", "UNKNOWN", "PARTIALLY_FILLED")
        ]
        _failed_runs = failed_runs or []

        # Collect warnings
        warnings = self._compute_warnings(successful_orders)

        # Plain text
        plain_lines = [
            f"Monthly summary for {month_label}",
            "",
            f"Investment runs: {num_runs}",
            f"Total CZK deployed: {round(total_czk)}",
            "",
            f"{'Ticker':<12} {'Total CZK':>12}",
            f"{'-' * 26}",
        ]
        for ticker, czk in sorted(ticker_totals.items(), key=lambda x: -x[1]):
            plain_lines.append(f"{ticker:<12} {czk:>12.2f}")

        plain_lines += ["", "--- Warnings ---"]
        if not warnings:
            plain_lines.append("No warnings.")
        else:
            for w in warnings:
                plain_lines.append(f"{w['ticker']} [{w['type']}]: {w['detail']}")

        plain_lines += ["", "--- Issues ---"]
        if not _failed_runs and not error_orders:
            plain_lines.append("No issues found.")
        else:
            for r in _failed_runs:
                plain_lines.append(
                    f"FAILED run {str(r.id)[:8]}… on {r.started_at.strftime('%Y-%m-%d')}: {r.error or 'no details'}"
                )
            for o in error_orders:
                plain_lines.append(
                    f"Order {o.t212_ticker} [{o.status}]: {o.error or 'no details'}"
                )

        # HTML ticker rows
        row_html = []
        for i, (ticker, czk) in enumerate(
            sorted(ticker_totals.items(), key=lambda x: -x[1])
        ):
            bg = "#f8faff" if i % 2 == 0 else "#ffffff"
            share = (czk / total_czk * 100) if total_czk else 0.0
            czk_str = f"{czk:_.2f}".replace("_", "\u00a0")
            row_html.append(
                f'<tr style="background-color:{bg};">'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;font-weight:600;">{ticker}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{czk_str}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#6b7280;text-align:right;">{share:.1f}%</td>'
                f"</tr>"
            )

        # HTML warnings section
        if not warnings:
            warnings_section = (
                "<tr><td style='padding:0 40px 28px;'>"
                "<div style='background-color:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:16px 20px;display:flex;align-items:center;gap:10px;'>"
                "<span style='font-size:18px;'>&#9728;</span>"
                "<div>"
                "<p style='margin:0;font-size:13px;font-weight:700;color:#92400e;'>No warnings</p>"
                "<p style='margin:4px 0 0;font-size:12px;color:#78350f;'>Prices, fees, and FX rates all looked normal this month.</p>"
                "</div>"
                "</div>"
                "</td></tr>"
            )
        else:
            warn_rows = []
            for w in warnings:
                warn_rows.append(
                    f'<tr style="background-color:#fffbeb;">'
                    f'<td style="padding:10px 14px;font-size:12px;color:#b45309;font-weight:700;">{w["type"]}</td>'
                    f'<td style="padding:10px 14px;font-size:12px;color:#1e293b;">{w["ticker"]}</td>'
                    f'<td style="padding:10px 14px;font-size:12px;color:#6b7280;word-break:break-word;">{w["detail"]}</td>'
                    f"</tr>"
                )
            warnings_section = (
                "<tr><td style='padding:0 40px 28px;'>"
                "<h2 style='margin:0 0 14px;font-size:14px;color:#92400e;text-transform:uppercase;letter-spacing:1px;font-weight:700;'>Warnings</h2>"
                "<table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;'>"
                "<thead><tr style='background-color:#fde68a;'>"
                "<th style='padding:10px 14px;text-align:left;font-size:12px;color:#78350f;font-weight:600;'>Type</th>"
                "<th style='padding:10px 14px;text-align:left;font-size:12px;color:#78350f;font-weight:600;'>Ticker</th>"
                "<th style='padding:10px 14px;text-align:left;font-size:12px;color:#78350f;font-weight:600;'>Detail</th>"
                "</tr></thead>"
                "<tbody>" + "\n".join(warn_rows) + "</tbody>"
                "</table>"
                "</td></tr>"
            )

        # HTML issues section
        if not _failed_runs and not error_orders:
            errors_section = (
                "<tr><td style='padding:0 40px 28px;'>"
                "<div style='background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:16px 20px;display:flex;align-items:center;gap:10px;'>"
                "<span style='font-size:18px;'>&#10003;</span>"
                "<div>"
                "<p style='margin:0;font-size:13px;font-weight:700;color:#15803d;'>No issues found</p>"
                "<p style='margin:4px 0 0;font-size:12px;color:#4ade80;color:#166534;'>All runs and orders completed successfully this month.</p>"
                "</div>"
                "</div>"
                "</td></tr>"
            )
        else:
            issue_rows = []
            for r in _failed_runs:
                date_str = r.started_at.strftime("%b %-d")
                run_id_short = str(r.id)[:8] + "…"
                detail = r.error or "expired without all orders filling"
                issue_rows.append(
                    f'<tr style="background-color:#fff7f7;">'
                    f'<td style="padding:10px 14px;font-size:12px;color:#991b1b;font-weight:700;">FAILED RUN</td>'
                    f'<td style="padding:10px 14px;font-size:12px;color:#1e293b;">{run_id_short} &middot; {date_str}</td>'
                    f'<td style="padding:10px 14px;font-size:12px;color:#6b7280;word-break:break-word;">{detail}</td>'
                    f"</tr>"
                )
            for o in error_orders:
                detail = o.error or "—"
                issue_rows.append(
                    f'<tr style="background-color:#fffbeb;">'
                    f'<td style="padding:10px 14px;font-size:12px;color:#b45309;font-weight:700;">{o.status}</td>'
                    f'<td style="padding:10px 14px;font-size:12px;color:#1e293b;">{o.t212_ticker}</td>'
                    f'<td style="padding:10px 14px;font-size:12px;color:#6b7280;word-break:break-word;">{detail}</td>'
                    f"</tr>"
                )
            errors_section = (
                "<tr><td style='padding:0 40px 28px;'>"
                "<h2 style='margin:0 0 14px;font-size:14px;color:#991b1b;text-transform:uppercase;letter-spacing:1px;font-weight:700;'>Issues</h2>"
                "<table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;'>"
                "<thead><tr style='background-color:#fca5a5;'>"
                "<th style='padding:10px 14px;text-align:left;font-size:12px;color:#7f1d1d;font-weight:600;'>Type</th>"
                "<th style='padding:10px 14px;text-align:left;font-size:12px;color:#7f1d1d;font-weight:600;'>Item</th>"
                "<th style='padding:10px 14px;text-align:left;font-size:12px;color:#7f1d1d;font-weight:600;'>Details</th>"
                "</tr></thead>"
                "<tbody>" + "\n".join(issue_rows) + "</tbody>"
                "</table>"
                "</td></tr>"
            )

        html = self._load_template("monthly_summary.html").substitute(
            month_label=month_label,
            num_runs=num_runs,
            total_czk=f"{round(total_czk):_}".replace("_", "\u00a0"),
            ticker_rows="\n".join(row_html),
            warnings_section=warnings_section,
            errors_section=errors_section,
        )

        period = anchor_run.started_at.strftime("%Y-%m")
        self._send(
            f"[auto-invest] Monthly summary – {month_label}",
            "\n".join(plain_lines),
            html,
            mail_type="monthly_summary",
            period=period,
        )

    def send_balance_alert(self, alerts: List[Dict[str, Any]]) -> None:
        """Send low-balance warning email.

        Each alert dict: {exchange, balance, spend_per_run, runs_out_on, days_until_broke}
        """
        now = datetime.now(timezone.utc)
        date_label = now.strftime("%B %-d, %Y")
        today_str = now.strftime("%Y-%m-%d")

        # Plain text
        plain_lines = [
            "Low balance alert.",
            "",
            f"{'Exchange':<12} {'Balance (CZK)':>14} {'Spend/Run':>12} {'Runs Out On':>22} {'Days':>6}",
            f"{'-' * 68}",
        ]
        for a in alerts:
            plain_lines.append(
                f"{a['exchange']:<12} {a['balance']:>14.2f} {a['spend_per_run']:>12.2f}"
                f" {a['runs_out_on'].strftime('%Y-%m-%d %H:%M UTC'):>22} {a['days_until_broke']:>6}"
            )

        # HTML rows
        row_html = []
        for i, a in enumerate(alerts):
            bg = "#f8faff" if i % 2 == 0 else "#ffffff"
            bal_str = f"{a['balance']:_.2f}".replace("_", "\u00a0")
            spend_str = f"{a['spend_per_run']:_.2f}".replace("_", "\u00a0")
            runs_out_str = a["runs_out_on"].strftime("%Y-%m-%d %H:%M UTC")
            days = a["days_until_broke"]
            days_color = "#dc2626" if days <= 2 else "#b45309"
            row_html.append(
                f'<tr style="background-color:{bg};">'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;font-weight:600;">{a["exchange"]}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{bal_str}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{spend_str}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{runs_out_str}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:{days_color};text-align:right;font-weight:700;">{days}d</td>'
                f"</tr>"
            )

        # Build QR codes and topup section
        deposit_config: Dict[str, Dict[str, Optional[str]]] = {
            "T212": {
                "account": settings.t212_deposit_account,
                "vs": settings.t212_deposit_vs,
            },
            "COINMATE": {
                "account": settings.coinmate_deposit_account,
                "vs": settings.coinmate_deposit_vs,
            },
        }
        runs_30 = _runs_in_next_30_days(settings.portfolio.invest_interval)
        extra_images: Dict[str, bytes] = {}
        topup_cards: List[str] = []

        for a in alerts:
            exchange: str = a["exchange"]
            cfg = deposit_config.get(exchange, {})
            account = cfg.get("account")
            vs = cfg.get("vs")
            if not account or not vs:
                continue
            spend_per_run: float = a["spend_per_run"]
            suggested = math.ceil(runs_30 * spend_per_run / 100) * 100
            cid = f"qr_{exchange}"
            extra_images[cid] = _make_spd_qr(account, vs, float(suggested))
            suggested_str = f"{suggested:_.0f}".replace("_", "\u00a0")
            topup_cards.append(
                f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;background-color:#f8faff;border:1px solid #bfdbfe;border-radius:6px;">'
                f'<tr>'
                f'<td width="130" style="padding:16px 20px 16px 16px;vertical-align:middle;">'
                f'<img src="cid:{cid}" alt="QR {exchange}" width="110" height="110" style="display:block;" />'
                f'</td>'
                f'<td style="padding:16px 16px 16px 0;vertical-align:middle;">'
                f'<p style="margin:0;font-size:13px;font-weight:700;color:#1e3a8a;">{exchange}</p>'
                f'<p style="margin:6px 0 2px;font-size:12px;color:#374151;"><strong>Account:</strong> {account}</p>'
                f'<p style="margin:2px 0;font-size:12px;color:#374151;"><strong>Variable symbol:</strong> {vs}</p>'
                f'<p style="margin:6px 0 0;font-size:12px;color:#374151;"><strong>Suggested top-up:</strong> {suggested_str} CZK <span style="color:#6b7280;">(next 30 days)</span></p>'
                f'</td>'
                f'</tr>'
                f'</table>'
            )

        if topup_cards:
            topup_section = (
                "<tr><td style='padding:0 40px 28px;'>"
                "<h2 style='margin:0 0 14px;font-size:14px;color:#1e3a8a;text-transform:uppercase;letter-spacing:1px;font-weight:700;'>Top Up</h2>"
                + "\n".join(topup_cards)
                + "</td></tr>"
            )
        else:
            topup_section = ""

        html = self._load_template("balance_alert.html").substitute(
            date_label=date_label,
            alert_rows="\n".join(row_html),
            topup_section=topup_section,
        )

        self._send(
            "\u26a0\ufe0f [auto-invest] Low balance alert",
            "\n".join(plain_lines),
            html,
            mail_type="balance_alert",
            period=today_str,
            extra_images=extra_images or None,
        )


if __name__ == "__main__":
    from uuid import uuid4

    # ── Pick which emails to send ──────────────────────────────────────────
    SEND = {
        "investment_confirmation": False,
        "error_no_run": False,
        "error_with_run": False,
        "monthly_summary_clean": False,
        "monthly_summary_with_issues": False,
        "monthly_summary_real": False,  # fetch real dev DB data for the month below
        "balance_alert": True,
    }
    REAL_YEAR, REAL_MONTH = 2026, 3  # ← change to the month you want to test
    # ──────────────────────────────────────────────────────────────────────

    mailer = Mailer()
    run_id = uuid4()
    now = datetime.now(timezone.utc)

    dummy_run = Run(
        id=run_id,
        started_at=now,
        finished_at=now,
        status="FINISHED",
        invest_amount=5000.0,
        invest_interval="monthly",
        t212_default_weight=90,
        btc_default_weight=10.0,
        planned_total_czk=5000.0,
        total_orders=3,
        successful_orders=3,
        failed_orders=0,
        test=True,
    )

    def _make_order(
        ticker: str, total_czk: float, exchange: str, multiplier: float
    ) -> Order:
        """Build a minimal dummy Order for manual testing."""
        return Order(
            run_id=run_id,
            exchange=exchange,  # type: ignore[arg-type]
            instrument_type="CRYPTO" if ticker == "BTC" else "ETF",
            t212_ticker=ticker,
            yahoo_symbol=ticker,
            name=ticker,
            currency="CZK",
            side="BUY",
            order_type="MARKET",
            fx_rate=1.0,
            price=total_czk,
            quantity=1.0,
            total=total_czk,
            total_czk=total_czk,
            extended_hours=False,
            multiplier=multiplier,
            submitted_at=now,
            status="FILLED",
        )

    dummy_orders = [
        _make_order("VWCE", 3000.0, "T212", 1.0),
        _make_order("CSPX", 1500.0, "T212", 1.2),
        _make_order("BTC", 500.0, "COINMATE", 1.5),
    ]
    dummy_distribution: Dict[str, float] = {
        o.t212_ticker: o.total_czk for o in dummy_orders
    }
    dummy_multipliers: Dict[str, float] = {
        o.t212_ticker: o.multiplier for o in dummy_orders
    }

    dummy_run2 = Run(
        id=uuid4(),
        started_at=now,
        finished_at=now,
        status="FILLED",
        invest_amount=5000.0,
        invest_interval="monthly",
        t212_default_weight=90,
        btc_default_weight=10.0,
        planned_total_czk=5000.0,
        test=True,
    )

    if SEND["investment_confirmation"]:
        mailer.send_investment_confirmation(
            run=dummy_run,
            orders=dummy_orders,
            cash_distribution=dummy_distribution,
            multipliers=dummy_multipliers,
        )
        print("1. send_investment_confirmation sent — check inbox")

    if SEND["error_no_run"]:
        try:
            raise ValueError("Something went badly wrong (no run context)")
        except Exception as e:
            mailer.send_error_alert(e)
        print("2. send_error_alert (no run) sent — check inbox")

    if SEND["error_with_run"]:
        try:
            raise RuntimeError("DB insert failed unexpectedly")
        except Exception as e:
            mailer.send_error_alert(e, run=dummy_run)
        print("3. send_error_alert (with run) sent — check inbox")

    dummy_failed_run = Run(
        id=uuid4(),
        started_at=now,
        finished_at=now,
        status="FAILED",
        invest_amount=5000.0,
        invest_interval="monthly",
        t212_default_weight=90,
        btc_default_weight=10.0,
        error="Order placement timed out after 14 days",
        test=True,
    )
    dummy_failed_order = _make_order("IWDA", 800.0, "T212", 1.0)
    dummy_failed_order.status = "FAILED"  # type: ignore[assignment]
    dummy_failed_order.error = "Insufficient funds"

    if SEND["monthly_summary_clean"]:
        mailer.send_monthly_summary(
            runs=[dummy_run, dummy_run2],
            orders=dummy_orders * 2,
        )
        print("4. send_monthly_summary (clean) sent — check inbox")

    if SEND["monthly_summary_with_issues"]:
        mailer.send_monthly_summary(
            runs=[dummy_run, dummy_run2],
            orders=dummy_orders * 2 + [dummy_failed_order],
            failed_runs=[dummy_failed_run],
        )
        print("5. send_monthly_summary (with issues) sent — check inbox")

    if SEND["monthly_summary_real"]:
        real_runs: List[Run] = Run.get_runs_for_period(REAL_YEAR, REAL_MONTH)
        real_failed_runs: List[Run] = Run.get_failed_runs_for_period(
            REAL_YEAR, REAL_MONTH
        )
        if not real_runs and not real_failed_runs:
            print(
                f"6. No runs found for {REAL_YEAR}-{REAL_MONTH:02d} — nothing to send"
            )
        else:
            real_run_ids: List[str] = [str(r.id) for r in real_runs]
            real_orders: List[Order] = Order.get_orders_for_runs(real_run_ids)
            mailer.send_monthly_summary(real_runs, real_orders, real_failed_runs)
            print(
                f"6. send_monthly_summary (real {REAL_YEAR}-{REAL_MONTH:02d}) sent — check inbox"
            )

    if SEND["balance_alert"]:
        from datetime import timezone as _tz

        _invest = settings.portfolio.invest_amount
        _t212_weight = settings.portfolio.t212_weight
        _btc_weight = settings.portfolio.btc_weight
        _t212_spend = _invest * _t212_weight / (_t212_weight + _btc_weight)
        _btc_spend = _invest * _btc_weight / (_t212_weight + _btc_weight)
        dummy_alerts: List[Dict[str, Any]] = [
            {
                "exchange": "T212",
                "balance": round(_t212_spend * 2, 2),
                "spend_per_run": _t212_spend,
                "runs_out_on": datetime(2026, 3, 7, 9, 0, 0, tzinfo=_tz.utc),
                "days_until_broke": 2,
            },
            {
                "exchange": "COINMATE",
                "balance": round(_btc_spend * 9, 2),
                "spend_per_run": _btc_spend,
                "runs_out_on": datetime(2026, 3, 10, 9, 0, 0, tzinfo=_tz.utc),
                "days_until_broke": 5,
            },
        ]
        mailer.send_balance_alert(dummy_alerts)
        print("7. send_balance_alert sent — check inbox")
