import os
from ..config import get_settings


def setup_langsmith() -> bool:
    settings = get_settings()
    if not settings.langsmith_api_key:
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    return True
