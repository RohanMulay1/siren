from ..registry import register_tool


@register_tool("DESTRUCTIVE")
class FlushRedisCache:
    NAME = "flush_redis_cache"
    DESCRIPTION = (
        "Execute FLUSHDB on a specific Redis database index. "
        "DESTRUCTIVE: all cached data in that DB is permanently lost. "
        "Requires human approval via Slack before execution."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "redis_url": {"type": "string", "description": "Redis connection URL, e.g. redis://localhost:6379"},
            "db_index": {"type": "integer", "description": "Redis database index (0-15)", "minimum": 0, "maximum": 15},
        },
        "required": ["redis_url", "db_index"],
    }

    @staticmethod
    async def execute(redis_url: str = "redis://localhost:6379", db_index: int = 0, db: int | None = None, **kwargs) -> str:
        if db is not None:
            db_index = db
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(redis_url, db=db_index)
            key_count = await client.dbsize()
            await client.flushdb(asynchronous=False)
            await client.aclose()
            return (
                f"Redis FLUSHDB executed on {redis_url} db={db_index}. "
                f"Cleared {key_count} keys."
            )
        except Exception as e:
            return f"[Redis flush error] {type(e).__name__}: {e}"
