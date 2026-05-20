from ..registry import register_tool


@register_tool("READ")
class QueryPostgresReadonly:
    NAME = "query_postgres_readonly"
    DESCRIPTION = (
        "Execute a SELECT query against the application database. "
        "Enforced read-only — any non-SELECT query will be rejected. "
        "Useful for: pg_stat_activity (active connections), pg_stat_statements (slow queries), "
        "table sizes, lock waits."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "SELECT statement only"},
            "database_url": {"type": "string", "description": "Optional override connection string"},
        },
        "required": ["query"],
    }

    @staticmethod
    async def execute(query: str, database_url: str | None = None) -> str:
        # Safety: reject anything that isn't a SELECT
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
            return "[SIREN GUARDRAIL] Only SELECT queries are allowed in read-only tool."

        try:
            import asyncpg
            from siren.config import get_settings
            settings = get_settings()

            url = (database_url or settings.database_url).replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(url)
            try:
                rows = await conn.fetch(query)
                if not rows:
                    return "Query returned 0 rows."

                # Format as simple table
                headers = list(rows[0].keys())
                lines = [" | ".join(headers)]
                lines.append("-" * len(lines[0]))
                for row in rows[:50]:  # cap at 50 rows
                    lines.append(" | ".join(str(v) for v in row.values()))

                if len(rows) > 50:
                    lines.append(f"... ({len(rows) - 50} more rows truncated)")

                return "\n".join(lines)
            finally:
                await conn.close()
        except Exception as e:
            return f"[Database error] {type(e).__name__}: {e}"
