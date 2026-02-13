import os
from typing import Optional
from functools import lru_cache
from enum import Enum


class CheckpointerBackend(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MEMORY = "memory"


class PlannerMode(str, Enum):
    STUB = "stub"
    LLM = "llm"


class SynthesizeMode(str, Enum):
    STUB = "stub"
    LLM = "llm"


class Settings:
    def __init__(self):
        self.app_name = "MobileTest AI"
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        self.database_url = os.getenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./mobiletest.db"
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        self.langgraph_planner_mode = PlannerMode(
            os.getenv("LANGGRAPH_PLANNER_MODE", "stub")
        )
        self.langgraph_planner_ab_enabled = (
            os.getenv("LANGGRAPH_PLANNER_AB_ENABLED", "false").lower() == "true"
        )
        self.langgraph_planner_ab_split = int(
            os.getenv("LANGGRAPH_PLANNER_AB_SPLIT", "50")
        )
        self.langgraph_planner_ab_salt = os.getenv(
            "LANGGRAPH_PLANNER_AB_SALT", "planner-ab-v1"
        )
        
        self.langgraph_synthesize_mode = SynthesizeMode(
            os.getenv("LANGGRAPH_SYNTHESIZE_MODE", "stub")
        )
        self.langgraph_execute_live_tools = (
            os.getenv("LANGGRAPH_EXECUTE_LIVE_TOOLS", "false").lower() == "true"
        )
        self.langgraph_show_evidence = (
            os.getenv("LANGGRAPH_SHOW_EVIDENCE", "false").lower() == "true"
        )
        
        self.langgraph_checkpointer_backend = CheckpointerBackend(
            os.getenv("LANGGRAPH_CHECKPOINTER_BACKEND", "sqlite")
        )
        self.langgraph_checkpointer_allow_memory_fallback = (
            os.getenv("LANGGRAPH_CHECKPOINTER_ALLOW_MEMORY_FALLBACK", "true").lower() == "true"
        )
        
        self.api_auth_enabled = (
            os.getenv("API_AUTH_ENABLED", "false").lower() == "true"
        )
        self.rate_limit_enabled = (
            os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
        )
        
        self.cors_allow_origins = os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        self.cors_allow_credentials = (
            os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
        )
        
        self.api_public_paths = os.getenv(
            "API_PUBLIC_PATHS",
            "/health,/docs,/openapi.json,/redoc"
        ).split(",")
        
        self.session_context_ttl_minutes = int(
            os.getenv("SESSION_CONTEXT_TTL_MINUTES", "240")
        )
        self.session_context_max_threads = int(
            os.getenv("SESSION_CONTEXT_MAX_THREADS", "1000")
        )
        
        self.default_timeout = int(os.getenv("DEFAULT_TIMEOUT", "300"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
