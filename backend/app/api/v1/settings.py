from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMConfig(BaseModel):
    provider: str
    model: str
    apiKey: str
    baseUrl: str


def _load_env_file():
    env_file = "/Users/lisq/ai/mobileagent/mobiletest/backend/.env"
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value
    return env_vars


def _save_env_file(env_vars: dict):
    env_file = "/Users/lisq/ai/mobileagent/mobiletest/backend/.env"
    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")


@router.get("/llm")
async def get_llm_config():
    env_vars = _load_env_file()
    return {
        "provider": env_vars.get("LLM_PROVIDER", "openai"),
        "model": env_vars.get("LLM_MODEL", "gpt-4o"),
        "apiKey": env_vars.get("LLM_API_KEY", ""),
        "baseUrl": env_vars.get("LLM_BASE_URL", ""),
    }


@router.post("/llm")
async def save_llm_config(config: LLMConfig):
    env_vars = _load_env_file()
    
    env_vars["LLM_PROVIDER"] = config.provider
    env_vars["LLM_MODEL"] = config.model
    if config.apiKey:
        env_vars["LLM_API_KEY"] = config.apiKey
    if config.baseUrl:
        env_vars["LLM_BASE_URL"] = config.baseUrl
    
    _save_env_file(env_vars)
    return {"success": True}


@router.post("/llm/test")
async def test_llm_connection():
    from app.agent.llm.llm import get_llm, LLMProvider, Message
    from app.core.config import settings
    
    try:
        env_vars = _load_env_file()
        provider = env_vars.get("LLM_PROVIDER", "openai")
        model = env_vars.get("LLM_MODEL", "gpt-4o")
        api_key = env_vars.get("LLM_API_KEY", "")
        base_url = env_vars.get("LLM_BASE_URL", "")
        
        llm = get_llm(
            LLMProvider(provider),
            model,
            api_key=api_key or None,
            base_url=base_url or None
        )
        
        test_messages = [Message(role="user", content="Hello")]
        response = await llm.chat(test_messages)
        
        return {"success": True, "message": "连接成功", "response": response.content[:100]}
    except Exception as e:
        return {"success": False, "message": str(e)}
