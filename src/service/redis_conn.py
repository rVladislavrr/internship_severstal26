import asyncio
import redis.asyncio as redis
import logging

from src.config import settings

logger = logging.getLogger('Редис конект')


class RedisClient:

    def __init__(self):

        self.redis = None

    async def connect(self):
        if self.redis is None:
            for attempt in range(3):
                try:
                    self.redis = await redis.from_url(settings.REDIS_URL, decode_responses=True, encoding='utf-8')
                    await self.redis.ping()
                    return
                except:
                    self.redis = None
                    await asyncio.sleep(1)
            raise RuntimeError("Redis connection failed")

    async def get_redis(self):
        try:
            await self.redis.ping()
        except:
            self.redis = None

        if self.redis is None:
            logger.critical('Редис недоступен во время запроса')
            raise RuntimeError('Redis connection failed')
        return self.redis

    async def close(self):
        if self.redis:
            await self.redis.close()


redis_client = RedisClient()
