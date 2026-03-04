# Standard library
import smtplib
import ssl
import traceback
from email.message import EmailMessage
from typing import Dict, List, Optional

# Local
from db.orders import Order
from db.runs import Run
from log import log
from settings import settings


class Mailer:
    """Sends plain-text alert emails for investment lifecycle events."""

    my_mail: str = settings.my_mail
    mail_recipient: str = settings.mail_recipient
    mail_host: str = settings.mail_host
    mail_port: int = settings.mail_port
    mail_password: str = settings.mail_password

    def __init__(self) -> None:
        pass

    def _send(self, subject: str, body: str) -> None:
        """Send a plain-text email via SMTP_SSL. Logs and re-raises on failure."""
        msg = EmailMessage()
        msg["From"] = self.my_mail
        msg["To"] = self.mail_recipient
        msg["Subject"] = subject
        msg.set_content(body)

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

        lines = [
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
            lines.append(f"{ticker:<12} {czk:>10.2f} {mult:>12.2f} {exchange:>10}")

        self._send("[auto-invest] Investment complete", "\n".join(lines))

    def send_error_alert(self, error: Exception, run: Optional[Run] = None) -> None:
        """Send error alert email when an investment run fails."""
        lines = [
            "An error occurred during the investment run.",
            "",
        ]
        if run:
            lines += [
                f"Run ID:  {run.id}",
                f"Started: {run.started_at.strftime('%Y-%m-%d %H:%M UTC')}",
                "",
            ]
        lines += [
            f"Error: {repr(error)}",
            "",
            "Traceback:",
            traceback.format_exc(),
        ]

        self._send("[auto-invest] ERROR", "\n".join(lines))

    def send_monthly_summary(self, runs: List[Run], orders: List[Order]) -> None:
        """Send monthly summary email with investment totals for the previous month."""
        if not runs:
            return

        month_label = runs[0].started_at.strftime("%B %Y")
        total_czk = sum(r.planned_total_czk or 0.0 for r in runs)
        num_runs = len(runs)

        ticker_totals: Dict[str, float] = {}
        for o in orders:
            ticker_totals[o.t212_ticker] = ticker_totals.get(o.t212_ticker, 0.0) + o.total_czk

        lines = [
            f"Monthly summary for {month_label}",
            "",
            f"Investment runs: {num_runs}",
            f"Total CZK deployed: {total_czk:.2f}",
            "",
            f"{'Ticker':<12} {'Total CZK':>12}",
            f"{'-' * 26}",
        ]
        for ticker, czk in sorted(ticker_totals.items(), key=lambda x: -x[1]):
            lines.append(f"{ticker:<12} {czk:>12.2f}")

        self._send(f"[auto-invest] Monthly summary – {month_label}", "\n".join(lines))


if __name__ == "__main__":
    from datetime import datetime, timezone
    from uuid import uuid4

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

    # --- 1. Investment confirmation ---
    mailer.send_investment_confirmation(
        run=dummy_run,
        orders=dummy_orders,
        cash_distribution=dummy_distribution,
        multipliers=dummy_multipliers,
    )
    print("1. send_investment_confirmation sent — check inbox")

    # --- 2. Error alert (no run) ---
    try:
        raise ValueError("Something went badly wrong (no run context)")
    except Exception as e:
        mailer.send_error_alert(e)
    print("2. send_error_alert (no run) sent — check inbox")

    # --- 3. Error alert (with run) ---
    try:
        raise RuntimeError("DB insert failed unexpectedly")
    except Exception as e:
        mailer.send_error_alert(e, run=dummy_run)
    print("3. send_error_alert (with run) sent — check inbox")

    # --- 4. Monthly summary ---
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
    mailer.send_monthly_summary(
        runs=[dummy_run, dummy_run2],
        orders=dummy_orders * 2,
    )
    print("4. send_monthly_summary sent — check inbox")
