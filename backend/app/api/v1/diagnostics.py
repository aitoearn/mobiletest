from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.core.config import settings

router = APIRouter(prefix="/diagnostics", tags=["诊断接口"])


@router.get("/orchestrator")
async def get_orchestrator_status() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "planner_mode": settings.langgraph_planner_mode.value,
        "synthesize_mode": settings.langgraph_synthesize_mode.value,
        "checkpointer_backend": settings.langgraph_checkpointer_backend.value,
        "execute_live_tools": settings.langgraph_execute_live_tools,
        "show_evidence": settings.langgraph_show_evidence,
    }


@router.get("/planner-ab")
async def get_planner_ab_status() -> Dict[str, Any]:
    return {
        "enabled": settings.langgraph_planner_ab_enabled,
        "split_percentage": settings.langgraph_planner_ab_split,
        "salt": settings.langgraph_planner_ab_salt,
    }


@router.get("/config")
async def get_runtime_config() -> Dict[str, Any]:
    return {
        "debug": settings.debug,
        "api_auth_enabled": settings.api_auth_enabled,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "cors_origins": settings.cors_allow_origins,
        "session_ttl_minutes": settings.session_context_ttl_minutes,
        "session_max_threads": settings.session_context_max_threads,
    }
