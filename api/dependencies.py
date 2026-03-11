# Standard library
import os

# Third-party
from cachetools import TTLCache
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient

# Local
from core.coinmate import Coinmate
from core.db.users import UserRecord
from core.settings import UserSettings, settings
from core.trading212 import Trading212

_user_record_cache: TTLCache = TTLCache(maxsize=50, ttl=300)
_jwks_client = PyJWKClient(
    f"{os.environ['SUPABASE_URL']}/auth/v1/.well-known/jwks.json"
)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
) -> str:
    """Validate Supabase JWT Bearer token and return the user's UUID."""
    signing_key = _jwks_client.get_signing_key_from_jwt(credentials.credentials)
    payload = jwt.decode(
        credentials.credentials,
        signing_key.key,
        algorithms=["ES256", "RS256", "HS256"],
        audience="authenticated",
    )
    return str(payload["sub"])


def get_user_record(user_id: str) -> UserRecord:
    """Return cached UserRecord for the given user_id (TTL 5 min)."""
    if user_id in _user_record_cache:
        return _user_record_cache[user_id]  # type: ignore[return-value]
    user: UserRecord = UserRecord.from_db(user_id)
    _user_record_cache[user_id] = user
    return user


def get_t212_for_user(user_id: str) -> Trading212:
    """Create a Trading212 client for the given user."""
    user = get_user_record(user_id)
    us = UserSettings.from_user(user)
    return Trading212(us.t212_id_key, us.t212_private_key, env=settings.env)


def get_coinmate_for_user(user_id: str) -> Coinmate:
    """Create a Coinmate client for the given user."""
    user = get_user_record(user_id)
    us = UserSettings.from_user(user)
    client_id: int = us.coinmate_client_id or 0
    return Coinmate(
        client_id,
        us.coinmate_public_key,
        us.coinmate_private_key,
    )


def get_user_settings_for_user(user_id: str) -> UserSettings:
    """Return UserSettings for the given user_id."""
    return UserSettings.from_user(get_user_record(user_id))


def invalidate_user_record(user_id: str) -> None:
    """Remove a user record from the TTL cache, forcing a fresh fetch."""
    _user_record_cache.pop(user_id, None)
