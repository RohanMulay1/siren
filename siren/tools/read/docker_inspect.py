import json
from ..registry import register_tool


@register_tool("READ")
class InspectDockerContainer:
    NAME = "inspect_docker_container"
    DESCRIPTION = (
        "Inspect a Docker container: get its status, CPU/memory usage, "
        "restart count, and last exit code. Use to determine if a service "
        "is crash-looping, OOM-killed, or in an unhealthy state."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "container_name": {"type": "string", "description": "Container name or ID"},
        },
        "required": ["container_name"],
    }

    @staticmethod
    async def execute(container_name: str) -> str:
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(container_name)
            stats = container.stats(stream=False)

            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"].get("system_cpu_usage", 0)
            num_cpus = stats["cpu_stats"].get("online_cpus", 1)
            cpu_pct = (cpu_delta / system_delta * num_cpus * 100) if system_delta > 0 else 0

            mem_usage = stats["memory_stats"]["usage"]
            mem_limit = stats["memory_stats"]["limit"]
            mem_pct = mem_usage / mem_limit * 100 if mem_limit > 0 else 0

            attrs = container.attrs
            state = attrs["State"]

            return (
                f"Container: {container_name}\n"
                f"Status: {container.status}\n"
                f"Running: {state.get('Running')}\n"
                f"Restart count: {attrs.get('RestartCount', 0)}\n"
                f"Exit code: {state.get('ExitCode', 'N/A')}\n"
                f"OOM killed: {state.get('OOMKilled', False)}\n"
                f"CPU usage: {cpu_pct:.1f}%\n"
                f"Memory usage: {mem_usage / 1024 / 1024:.1f} MB / {mem_limit / 1024 / 1024:.1f} MB ({mem_pct:.1f}%)\n"
                f"Started at: {state.get('StartedAt', 'N/A')}\n"
                f"Finished at: {state.get('FinishedAt', 'N/A')}"
            )
        except Exception as e:
            return f"[Docker error] {type(e).__name__}: {e}"
