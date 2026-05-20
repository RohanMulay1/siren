from ..registry import register_tool


@register_tool("REVERSIBLE")
class ScaleService:
    NAME = "scale_service"
    DESCRIPTION = (
        "Change the replica count of a Docker Compose service. "
        "Use to scale up during traffic spikes or resource pressure. "
        "WARNING: scaling to 0 replicas is treated as DESTRUCTIVE by the guardrail system."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "service": {"type": "string", "description": "Service name as defined in docker-compose"},
            "replicas": {"type": "integer", "description": "Desired replica count (1-20)", "minimum": 0, "maximum": 20},
            "compose_file": {"type": "string", "description": "Path to docker-compose file", "default": "docker-compose.yml"},
        },
        "required": ["service", "replicas"],
    }

    @staticmethod
    async def execute(service: str, replicas: int, compose_file: str = "docker-compose.yml") -> str:
        import asyncio
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "compose", "-f", compose_file, "scale", f"{service}={replicas}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return f"Service '{service}' scaled to {replicas} replica(s). Output: {stdout.decode().strip()}"
            return f"[Scale error] {stderr.decode().strip()}"
        except Exception as e:
            return f"[Scale error] {type(e).__name__}: {e}"
