# Third-party
from cachetools import TTLCache

# 15-minute TTL cache for slow Yahoo Finance / T212 live-data endpoints (per-user keyed)
instruments_cache: TTLCache = TTLCache(maxsize=50, ttl=900)

# 5-minute TTL cache for the health endpoint (per-user keyed)
health_cache: TTLCache = TTLCache(maxsize=50, ttl=300)
