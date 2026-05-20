# Import all tool modules to trigger @register_tool decorators
from .read import logs, metrics, git_blame, db_query, docker_inspect  # noqa: F401
from .reversible import container_restart, scale_service  # noqa: F401
from .destructive import flush_cache, drain_lb_node  # noqa: F401
from .registry import TOOL_REGISTRY, get_anthropic_tool_schemas  # noqa: F401
