import redis
from app.config import settings

def get_redis():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
