# Standard library
from functools import lru_cache

# Local
from core.coinmate import Coinmate
from core.settings import settings
from core.trading212 import Trading212


@lru_cache(maxsize=1)
def get_t212() -> Trading212:
    """Return a cached Trading212 client instance."""
    return Trading212(settings.t212_id_key, settings.t212_private_key, env=settings.env)


@lru_cache(maxsize=1)
def get_coinmate() -> Coinmate:
    """Return a cached Coinmate client instance."""
    return Coinmate(
        settings.coinmate_client_id,
        settings.coinmate_public_key,
        settings.coinmate_private_key,
    )
