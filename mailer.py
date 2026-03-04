# Standard library
import os
import smtplib
import ssl
import traceback as tb
from datetime import datetime, timezone
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template
from typing import Dict, List, Optional

# Local
from db.mails import Mail
from db.orders import Order
from db.runs import Run
from log import log
from settings import settings

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "emails")
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


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

    def _send(self, subject: str, plain: str, html: str, mail_type: str, period: Optional[str] = None) -> None:
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
            f"Total CZK: {total_czk:.2f}",
            "",
            f"{'Ticker':<12} {'CZK':>10} {'Multiplier':>12} {'Exchange':>10}",
            f"{'-' * 46}",
        ]
        for ticker, czk in sorted(cash_distribution.items(), key=lambda x: -x[1]):
            mult = multipliers.get(ticker, 1.0)
            exchange = exchange_map.get(ticker, "")
            plain_lines.append(f"{ticker:<12} {czk:>10.2f} {mult:>12.2f} {exchange:>10}")

        # HTML rows
        row_html = []
        for i, (ticker, czk) in enumerate(sorted(cash_distribution.items(), key=lambda x: -x[1])):
            mult = multipliers.get(ticker, 1.0)
            exchange = exchange_map.get(ticker, "—")
            bg = "#f8faff" if i % 2 == 0 else "#ffffff"
            mult_color = "#16a34a" if mult > 1.0 else "#1e293b"
            row_html.append(
                f'<tr style="background-color:{bg};">'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;font-weight:600;">{ticker}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{czk:,.2f}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:{mult_color};text-align:right;font-weight:600;">{mult:.2f}×</td>'
                f'<td style="padding:10px 14px;font-size:12px;color:#6b7280;text-align:right;">{exchange}</td>'
                f"</tr>"
            )

        run_id_short = str(run.id)[:8] + "…" if run.id else "—"
        html = self._load_template("investment_confirmation.html").substitute(
            run_id_short=run_id_short,
            timestamp=run.started_at.strftime("%Y-%m-%d %H:%M UTC"),
            date_label=run.started_at.strftime("%B %-d, %Y"),
            total_czk=f"{total_czk:,.2f}",
            order_rows="\n".join(row_html),
        )

        self._send("✅ [auto-invest] Investment complete", "\n".join(plain_lines), html, mail_type="investment_confirmation")

    def send_error_alert(self, error: Exception, run: Optional[Run] = None) -> None:
        """Send error alert email when an investment run fails."""
        traceback_str = tb.format_exc()
        banner_message = "An error occurred during the investment run." if run else "An unexpected error occurred."

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

        self._send("⚠️ [auto-invest] ERROR", "\n".join(plain_lines), html, mail_type="error_alert")

    def send_monthly_summary(self, runs: List[Run], orders: List[Order], failed_runs: Optional[List[Run]] = None) -> None:
        """Send monthly summary email with investment totals and any issues for the previous month."""
        all_runs = runs + (failed_runs or [])
        if not all_runs:
            return

        anchor_run = min(all_runs, key=lambda r: r.started_at)
        month_label = anchor_run.started_at.strftime("%B %Y")
        num_runs = len(runs)

        successful_orders = [o for o in orders if o.status not in ("FAILED", "CANCELLED", "UNKNOWN")]
        ticker_totals: Dict[str, float] = {}
        for o in successful_orders:
            ticker_totals[o.t212_ticker] = ticker_totals.get(o.t212_ticker, 0.0) + o.total_czk
        total_czk = sum(ticker_totals.values())

        # Collect issues
        error_orders = [o for o in orders if o.status in ("FAILED", "CANCELLED", "UNKNOWN", "PARTIALLY_FILLED")]
        _failed_runs = failed_runs or []

        # Plain text
        plain_lines = [
            f"Monthly summary for {month_label}",
            "",
            f"Investment runs: {num_runs}",
            f"Total CZK deployed: {total_czk:.2f}",
            "",
            f"{'Ticker':<12} {'Total CZK':>12}",
            f"{'-' * 26}",
        ]
        for ticker, czk in sorted(ticker_totals.items(), key=lambda x: -x[1]):
            plain_lines.append(f"{ticker:<12} {czk:>12.2f}")

        plain_lines += ["", "--- Issues ---"]
        if not _failed_runs and not error_orders:
            plain_lines.append("No issues found.")
        else:
            for r in _failed_runs:
                plain_lines.append(f"FAILED run {str(r.id)[:8]}… on {r.started_at.strftime('%Y-%m-%d')}: {r.error or 'no details'}")
            for o in error_orders:
                plain_lines.append(f"Order {o.t212_ticker} [{o.status}]: {o.error or 'no details'}")

        # HTML ticker rows
        row_html = []
        for i, (ticker, czk) in enumerate(sorted(ticker_totals.items(), key=lambda x: -x[1])):
            bg = "#f8faff" if i % 2 == 0 else "#ffffff"
            share = (czk / total_czk * 100) if total_czk else 0.0
            row_html.append(
                f'<tr style="background-color:{bg};">'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;font-weight:600;">{ticker}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#1e293b;text-align:right;">{czk:,.2f}</td>'
                f'<td style="padding:10px 14px;font-size:13px;color:#6b7280;text-align:right;">{share:.1f}%</td>'
                f"</tr>"
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
            total_czk=f"{total_czk:,.2f}",
            ticker_rows="\n".join(row_html),
            errors_section=errors_section,
        )

        period = anchor_run.started_at.strftime("%Y-%m")
        self._send(f"[auto-invest] Monthly summary – {month_label}", "\n".join(plain_lines), html, mail_type="monthly_summary", period=period)


if __name__ == "__main__":
    from uuid import uuid4

    # ── Pick which emails to send ──────────────────────────────────────────
    SEND = {
        "investment_confirmation": False,
        "error_no_run": False,
        "error_with_run": False,
        "monthly_summary_clean": False,
        "monthly_summary_with_issues": False,
        "monthly_summary_real": True,   # fetch real dev DB data for the month below
    }
    REAL_YEAR, REAL_MONTH = 2026, 3   # ← change to the month you want to test
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

    def _make_order(ticker: str, total_czk: float, exchange: str, multiplier: float) -> Order:
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
    dummy_distribution: Dict[str, float] = {o.t212_ticker: o.total_czk for o in dummy_orders}
    dummy_multipliers: Dict[str, float] = {o.t212_ticker: o.multiplier for o in dummy_orders}

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
        real_failed_runs: List[Run] = Run.get_failed_runs_for_period(REAL_YEAR, REAL_MONTH)
        if not real_runs and not real_failed_runs:
            print(f"6. No runs found for {REAL_YEAR}-{REAL_MONTH:02d} — nothing to send")
        else:
            real_run_ids: List[str] = [str(r.id) for r in real_runs]
            real_orders: List[Order] = Order.get_orders_for_runs(real_run_ids)
            mailer.send_monthly_summary(real_runs, real_orders, real_failed_runs)
            print(f"6. send_monthly_summary (real {REAL_YEAR}-{REAL_MONTH:02d}) sent — check inbox")
