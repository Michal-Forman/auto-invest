# Future
from __future__ import annotations

# Standard library
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast
from uuid import UUID

# Third-party
from pydantic import BaseModel

# Local
from db.client import supabase
from log import log

TABLE = "mails"

MailType = str  # "investment_confirmation" | "error_alert" | "monthly_summary"


class Mail(BaseModel):
    """Record of a sent email stored in the mails table."""

    id: Optional[UUID] = None
    type: MailType
    subject: str
    sent_at: Optional[datetime] = None
    period: Optional[str] = None

    @staticmethod
    def summary_sent_for_period(period: str) -> bool:
        """Return True if a monthly_summary mail was already sent for the given period (e.g. '2026-02')."""
        try:
            res = (
                supabase.table(TABLE)
                .select("id")
                .eq("type", "monthly_summary")
                .eq("period", period)
                .limit(1)
                .execute()
            )
            return len(res.data) > 0
        except Exception as e:
            log.error(f"Failed to check mails table for period {period}: {repr(e)}")
            return False

    @staticmethod
    def balance_alert_sent_today() -> bool:
        """Return True if a balance_alert email was already sent today (UTC)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            res = (
                supabase.table(TABLE)
                .select("id")
                .eq("type", "balance_alert")
                .eq("period", today)
                .limit(1)
                .execute()
            )
            return len(res.data) > 0
        except Exception as e:
            log.error(f"Failed to check mails table for balance_alert: {repr(e)}")
            return False

    def post_to_db(self) -> Optional[Dict[str, Any]]:
        """Insert this mail record into Supabase. Returns inserted row or None on error."""
        data: Dict[str, Any] = self.model_dump(mode="json", exclude_none=True)
        try:
            res = supabase.table(TABLE).insert(data).execute()
            row: Dict[str, Any] = cast(Dict[str, Any], res.data[0])
            log.info(f"Mail persisted to DB: type={self.type} subject={self.subject!r}")
            return row
        except Exception as e:
            log.error(f"Failed to persist mail to DB: {repr(e)}")
            return None
