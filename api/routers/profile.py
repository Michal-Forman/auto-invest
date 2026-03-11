# Standard library
import dataclasses
from typing import Any, Dict

# Third-party
from fastapi import APIRouter, Depends

# Local
from api.dependencies import (
    get_current_user_id,
    get_user_record,
    invalidate_user_record,
)
from api.schemas import ProfileResponse, ProfileUpdate
from core.db.client import supabase
from core.db.users import UserRecord

router = APIRouter()


@router.get("/profile", response_model=ProfileResponse)
def get_profile(user_id: str = Depends(get_current_user_id)) -> ProfileResponse:
    """Return the current user's profile and configuration."""
    record = get_user_record(user_id)
    d: Dict[str, Any] = {
        k: v for k, v in dataclasses.asdict(record).items() if k not in ("id", "email")
    }
    return ProfileResponse(**d)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate, user_id: str = Depends(get_current_user_id)
) -> ProfileResponse:
    """Update per-user profile configuration fields."""
    updates: Dict[str, Any] = {
        k: v for k, v in body.model_dump().items() if v is not None
    }
    if updates:
        supabase.table("users").update(updates).eq("id", user_id).execute()
    invalidate_user_record(user_id)
    record: UserRecord = UserRecord.from_db(user_id)
    d: Dict[str, Any] = {
        k: v for k, v in dataclasses.asdict(record).items() if k not in ("id", "email")
    }
    return ProfileResponse(**d)
