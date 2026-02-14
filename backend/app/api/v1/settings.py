from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMConfig(BaseModel):
    provider: Optional[str] = "openai"
    model: Optional[str] = "gpt-4o"
    apiKey: Optional[str] = ""
    baseUrl: Optional[str] = ""
    agentType: Optional[str] = "glm-async"
    agentConfigParams: Optional[Dict[str, Any]] = {}
    defaultMaxSteps: Optional[int] = 100
    layeredMaxTurns: Optional[int] = 50
    visionBaseUrl: Optional[str] = ""
    visionModelName: Optional[str] = ""
    visionApiKey: Optional[str] = ""
    decisionBaseUrl: Optional[str] = ""
    decisionModelName: Optional[str] = ""
    decisionApiKey: Optional[str] = ""


CONFIG_FILE = "/Users/lisq/ai/mobileagent/mobiletest/backend/config.json"


def _load_config() -> dict:
    import json
    default = {
        "provider": "openai",
        "model": "gpt-4o",
        "apiKey": "",
        "baseUrl": "",
        "agentType": "glm-async",
        "agentConfigParams": {},
        "defaultMaxSteps": 100,
        "layeredMaxTurns": 50,
        "visionBaseUrl": "",
        "visionModelName": "",
        "visionApiKey": "",
        "decisionBaseUrl": "",
        "decisionModelName": "",
        "decisionApiKey": "",
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**default, **json.load(f)}
        except:
            pass
    return default


def _save_config(config: dict):
    import json
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


@router.get("/llm")
async def get_llm_config():
    config = _load_config()
    return config


@router.post("/llm")
async def save_llm_config(config: LLMConfig):
    config_dict = config.model_dump()
    _save_config(config_dict)
    
    return {"success": True, "message": "配置已保存，重启后生效"}


@router.post("/llm/test")
async def test_llm_connection():
    from app.agent.llm.llm import get_llm, LLMProvider, Message
    import traceback
    
    config = _load_config()
    
    vision_base_url = config.get("visionBaseUrl", "")
    vision_model_name = config.get("visionModelName", "")
    vision_api_key = config.get("visionApiKey", "")
    
    if not vision_base_url or not vision_model_name:
        return {"success": False, "message": "请先配置视觉模型 Base URL 和模型名称"}
    
    if not vision_api_key:
        return {"success": False, "message": "请先配置 API Key"}
    
    if not vision_base_url.startswith(("http://", "https://")):
        return {"success": False, "message": "Base URL 必须以 http:// 或 https:// 开头"}
    
    try:
        provider = LLMProvider.OPENAI
        if "bigmodel.cn" in vision_base_url:
            provider = LLMProvider.ZHIPU
        elif "modelscope.cn" in vision_base_url:
            provider = LLMProvider.MODELSCOPE
        elif "dashscope.aliyuncs.com" in vision_base_url:
            provider = LLMProvider.QWEN
        
        llm = get_llm(
            provider,
            vision_model_name,
            api_key=vision_api_key,
            base_url=vision_base_url
        )
        
        test_messages = [Message(role="user", content="Hello")]
        response = await llm.chat(test_messages)
        
        return {"success": True, "message": "连接成功", "response": response.content[:100]}
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"LLM Test Error: {error_detail}")
        return {"success": False, "message": f"{str(e)}", "detail": error_detail}


@router.post("/reinit")
async def reinit_agents():
    return {"success": True, "total": 0, "succeeded": [], "failed": {}}
