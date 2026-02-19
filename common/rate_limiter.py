import redis
from django.conf import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
)

WINDOW_SECONDS = 60
MAX_CALLS_PER_WINDOW = 90  # set below Monday's actual limit as a safety margin


def check_rate_limit(account_id):
    key = f"rate_limit:{account_id}"

    current_count = redis_client.incr(key)

    if current_count == 1:
        redis_client.expire(key, WINDOW_SECONDS)

    if current_count > MAX_CALLS_PER_WINDOW:
        ttl = redis_client.ttl(key)
        return {"allowed": False, "retry_after_seconds": ttl}

    return {"allowed": True}