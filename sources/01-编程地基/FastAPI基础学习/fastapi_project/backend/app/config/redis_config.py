import redis

from app.config.app_config import settings

_redis_pool = redis.ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password or None,
    db=settings.redis_db,
    decode_responses=settings.redis_decode_responses,
)


def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=_redis_pool)
