# Third-party
from cachetools import TTLCache

# 15-minute TTL cache for slow Yahoo Finance / T212 live-data endpoints
instruments_cache: TTLCache = TTLCache(maxsize=4, ttl=900)
