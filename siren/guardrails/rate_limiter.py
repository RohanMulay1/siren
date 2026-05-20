import redis.asyncio as aioredis


class DestructiveActionRateLimiter:
    """
    Redis sliding window counter. Prevents runaway destructive actions.
    Default: max 3 destructive actions per hour globally.
    """

    KEY = "siren:destructive_actions:count"

    def __init__(self, redis_client: aioredis.Redis, max_actions: int = 3, window_seconds: int = 3600):
        self.redis = redis_client
        self.max_actions = max_actions
        self.window = window_seconds

    async def check_and_consume(self) -> tuple[bool, int]:
        """Returns (allowed, current_count)."""
        count = await self.redis.incr(self.KEY)
        if count == 1:
            await self.redis.expire(self.KEY, self.window)
        allowed = count <= self.max_actions
        return allowed, count

    async def current_count(self) -> int:
        val = await self.redis.get(self.KEY)
        return int(val) if val else 0
