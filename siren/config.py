from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Provider: "openrouter" | "groq"
    llm_provider: str = "openrouter"
    openrouter_api_key: str = ""
    groq_api_key: str = ""

    # Model selection
    # Groq models: llama-3.3-70b-versatile (best), llama-3.1-8b-instant (fast/cheap)
    # OpenRouter models: meta-llama/llama-3.3-70b-instruct, google/gemini-2.5-pro
    model_triage: str = "llama-3.3-70b-versatile"
    model_investigate: str = "llama-3.3-70b-versatile"
    model_plan: str = "llama-3.3-70b-versatile"
    model_guard: str = "llama-3.1-8b-instant"
    model_execute: str = "llama-3.1-8b-instant"
    model_verify: str = "llama-3.3-70b-versatile"
    model_postmortem: str = "llama-3.3-70b-versatile"

    # Infrastructure
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql+asyncpg://siren:siren@localhost:5432/siren"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "incidents"

    # GitHub
    github_token: str = ""

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_channel_id: str = ""

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "siren"

    # App
    environment: str = "development"
    log_level: str = "INFO"

    # Agent tuning
    investigation_max_iterations: int = 5
    investigation_confidence_threshold: float = 0.80
    remediation_auto_approve_confidence: float = 0.85
    destructive_actions_per_hour: int = 3
    tool_output_max_chars: int = 8000
    similarity_threshold: float = 0.75
    recall_top_k: int = 5

    # Demo
    demo_redis_url: str = "redis://localhost:6380"


@lru_cache
def get_settings() -> Settings:
    return Settings()
