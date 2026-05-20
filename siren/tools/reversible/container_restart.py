from ..registry import register_tool


@register_tool("REVERSIBLE")
class RestartDockerContainer:
    NAME = "restart_docker_container"
    DESCRIPTION = (
        "Restart a Docker container gracefully. Reversible — container can be stopped again. "
        "Use when a service is unresponsive, stuck in an error loop, or needs a fresh start."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "container_name": {"type": "string", "description": "Container name or ID"},
            "timeout": {"type": "integer", "description": "Graceful stop timeout in seconds", "default": 10},
        },
        "required": ["container_name"],
    }

    @staticmethod
    async def execute(container_name: str, timeout: int = 10) -> str:
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(container_name)
            container.restart(timeout=timeout)
            container.reload()
            return (
                f"Container '{container_name}' restarted successfully. "
                f"New status: {container.status}."
            )
        except Exception as e:
            return f"[Docker restart error] {type(e).__name__}: {e}"
