# Future
from __future__ import annotations

# Standard library
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, cast
from uuid import UUID

# Third-party
from pydantic import BaseModel

# Local
from core.db.client import supabase
from core.log import log

TABLE = "mails"

MailType = str  # "investment_confirmation" | "error_alert" | "monthly_summary"


class Mail(BaseModel):
    """Record of a sent email stored in the mails table."""

    id: Optional[UUID] = None
    user_id: Optional[str] = None
    type: MailType
    subject: str
    sent_at: Optional[datetime] = None
    period: Optional[str] = None

    @staticmethod
    def summary_sent_for_period(period: str, user_id: Optional[str] = None) -> bool:
        """Return True if a monthly_summary mail was already sent for the given period (e.g. '2026-02')."""
        try:
            query = (
                supabase.table(TABLE)
                .select("id")
                .eq("type", "monthly_summary")
                .eq("period", period)
                .limit(1)
            )
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.execute()
            return len(res.data) > 0
        except Exception as e:
            log.error(f"Failed to check mails table for period {period}: {repr(e)}")
            return False

    @staticmethod
    def build_alert_period(sent_at: datetime, short_exchanges: List[str]) -> str:
        """Encode a funding alert's date and short exchanges into the period column.

        Stored as e.g. "2026-08-13|COINMATE,T212" so the next check can tell whether
        the set of underfunded exchanges changed without needing a new column.
        """
        exchanges = ",".join(sorted(short_exchanges))
        return f"{sent_at.strftime('%Y-%m-%d')}|{exchanges}"

    @staticmethod
    def parse_alert_period(period: Optional[str]) -> Set[str]:
        """Return the short exchanges encoded in a funding alert's period column."""
        if not period or "|" not in period:
            return set()
        _, _, exchanges = period.partition("|")
        return {e for e in exchanges.split(",") if e}

    @staticmethod
    def last_balance_alert(user_id: Optional[str] = None) -> Optional["Mail"]:
        """Return the most recently sent balance_alert mail, or None if there is none."""
        try:
            query = (
                supabase.table(TABLE)
                .select("*")
                .eq("type", "balance_alert")
                .order("sent_at", desc=True)
                .limit(1)
            )
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.execute()
            if not res.data:
                return None
            row: Dict[str, Any] = cast(Dict[str, Any], res.data[0])
            return Mail(**row)
        except Exception as e:
            log.error(f"Failed to check mails table for balance_alert: {repr(e)}")
            return None

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
