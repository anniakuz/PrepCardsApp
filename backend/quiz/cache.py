import time

from django.core.cache import cache

STATS_TTL = 60


def _stamp_key(user_id):
    return f"stats-stamp:{user_id}"


def stats_key(user_id, params):
    stamp = cache.get(_stamp_key(user_id), 0)
    suffix = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"stats:{user_id}:{stamp}:{suffix}"


def bump_stats(user_id):
    """Invalida las estadísticas en caché del usuario."""
    cache.set(_stamp_key(user_id), time.time_ns(), None)
