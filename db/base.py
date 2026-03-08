# Future
from __future__ import annotations

# Standard library
from typing import Any, ClassVar, Dict, Optional, cast

# Third-party
from pydantic import BaseModel

# Local
from db.client import supabase


class BaseDBModel(BaseModel):
    """Base Pydantic model providing shared Supabase insert logic for all DB models."""

    TABLE: ClassVar[str]
    id: Optional[Any] = None

    def _to_insert_dict(self) -> Dict[str, Any]:
        """Serialise for Supabase insert, excluding None fields."""
        return self.model_dump(mode="json", exclude_none=True)

    def post_to_db(self) -> Optional[Dict[str, Any]]:
        """Insert into Supabase and backfill DB-assigned fields (id, created_at). Returns the inserted row dict or None."""
        response: Any = (
            supabase.table(self.TABLE).insert(self._to_insert_dict()).execute()
        )

        if response.data:
            row = cast(Dict[str, Any], response.data[0])
            validated = type(self).model_validate(row)
            self.id = validated.id
            if "created_at" in type(self).model_fields:
                self.created_at = validated.created_at  # type: ignore[attr-defined, has-type]
            return row

        return None
