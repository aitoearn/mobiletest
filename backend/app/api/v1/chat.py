import json
import os
import asyncio
from datetime import datetime
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.device import DeviceControlService as DeviceService
from app.services.vision import VisionService
from app.agent.mobile_agent import MobileAgent
from app.agent.config import ProtocolType, get_config_manager
from app.agent.prompts import get_combined_prompt
from app.models import Engine
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatAPIRequest(BaseModel):
    messages: list[Message]
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    engine_id: Optional[str] = None  # 新增：引擎ID


class ChatResponseV1(BaseModel):
    thread_id: str
    message: str
    status: str


_sessions: dict = {}


def _get_or_create_session(session_id: str, device_id: Optional[str] = None):
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": [],
            "device_id": device_id,
            "agent": None,
        }
    return _sessions[session_id]


def _load_config() -> dict:
    config_file = "/Users/lisq/ai/mobileagent/mobiletest/backend/config.json"
    logger.info(f"Loading config from: {config_file}, exists: {os.path.exists(config_file)}")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                logger.info(f"Config loaded: baseUrl={config.get('baseUrl')}, model={config.get('model')}, apiKey={config.get('apiKey', '')[:10]}...")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    return {}


def _get_model_config(engine: Optional[Engine] = None):
    """获取模型配置，优先使用引擎配置"""
    # 加载系统设置
    config = _load_config()
    provider_api_keys = config.get("providerApiKeys", {})
    
    # 检测协议类型
    config_manager = get_config_manager()
    
    if engine:
        # 使用引擎配置，API Key 从系统设置中获取
        provider = engine.provider or ""
        api_key = provider_api_keys.get(provider, "") if provider else config.get("apiKey", "")
        
        # 检测协议类型
        detected_protocol = config_manager.detect_protocol(engine.model or "")
        protocol_value = detected_protocol.value
        
        print(f"[ChatAPI] Engine config: provider={provider}, model={engine.model}, base_url={engine.base_url}")
        print(f"[ChatAPI] API Key found: {bool(api_key)}")
        print(f"[ChatAPI] Detected protocol: {protocol_value}")
        
        # 组合系统提示词：基础提示词 + 引擎补充提示词
        combined_prompt = get_combined_prompt(protocol_value, engine.prompt)
        
        return {
            "base_url": engine.base_url or "https://open.bigmodel.cn/api/paas/v4",
            "api_key": api_key,
            "model": engine.model or "autoglm-phone",
            "protocol": protocol_value,
            "system_prompt": combined_prompt,  # 组合后的完整提示词
            "user_prompt": engine.prompt,  # 保留原始用户提示词用于日志
        }
    
    # 使用默认配置
    return {
        "base_url": config.get("baseUrl") or "https://open.bigmodel.cn/api/paas/v4",
        "api_key": config.get("apiKey") or "",
        "model": config.get("model") or "autoglm-phone",
        "protocol": "universal",
        "system_prompt": get_combined_prompt("universal", None),
        "user_prompt": None,
    }


@router.post("/stream")
async def chat_stream(request: ChatAPIRequest, db: Session = Depends(get_db)):
    print(f"[ChatAPI] ====== Received stream request ======")
    print(f"[ChatAPI] device_id={request.device_id}, session_id={request.session_id}, engine_id={request.engine_id}")
    
    last_message = request.messages[-1] if request.messages else None
    if not last_message:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    session_id = request.session_id or request.device_id or "default"
    session = _get_or_create_session(session_id, request.device_id)
    
    user_message = {
        "role": "user",
        "content": last_message.content,
    }
    session["messages"].append(user_message)
    
    device_id = request.device_id or session.get("device_id")
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID is required")
    
    # 加载引擎配置
    engine = None
    if request.engine_id:
        engine = await db.get(Engine, request.engine_id)
        if engine:
            print(f"[ChatAPI] Using engine: {engine.name} (model: {engine.model})")
        else:
            print(f"[ChatAPI] Engine {request.engine_id} not found, using default config")
    
    print(f"[ChatAPI] Creating MobileAgent for device {device_id}")
    
    async def event_generator():
        try:
            device_service = DeviceService()
            vision_service = VisionService()
            
            model_config = _get_model_config(engine)
            print(f"[ChatAPI] Model config: base_url={model_config['base_url']}, model={model_config['model']}")
            
            agent = MobileAgent(
                model_config=model_config,
                device_service=device_service,
                vision_service=vision_service,
            )
            
            print(f"[ChatAPI] Starting agent.stream for task: {last_message.content}")
            
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            async for event in agent.stream(last_message.content, device_id):
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                # print(f"[ChatAPI] Event: {event_type}")
                
                if event_type == "thinking":
                    # print(f"[ChatAPI] Thinking: {event_data.get('chunk', '')}")
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event_data.get('chunk', '')})}\n\n"
                
                elif event_type == "action":
                    action = event_data.get("action", {})
                    print(f"[ChatAPI] Action: {action}")
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': action.get('action'), 'tool_args': action})}\n\n"
                
                elif event_type == "step":
                    step_data = event_data
                    print(f"[ChatAPI] Step data: {step_data}")
                    print(f"[ChatAPI] Step: {step_data.get('step')}, action: {step_data.get('action')}")
                    yield f"data: {json.dumps({'type': 'step', 'step': step_data.get('step'), 'thinking': step_data.get('thinking'), 'action': step_data.get('action'), 'success': step_data.get('success'), 'finished': step_data.get('finished'), 'message': step_data.get('message'), 'screenshot': step_data.get('screenshot')})}\n\n"
                    
                    if step_data.get("finished"):
                        yield f"data: {json.dumps({'type': 'done', 'content': step_data.get('message', '任务完成')})}\n\n"
                        return
                
                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': event_data.get('message')})}\n\n"
                
                elif event_type == "cancelled":
                    yield f"data: {json.dumps({'type': 'done', 'content': '任务已取消'})}\n\n"
                    return
            
            yield f"data: {json.dumps({'type': 'done', 'content': '任务完成'})}\n\n"
            
        except Exception as e:
            print(f"[ChatAPI] Stream error: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat", response_model=ChatResponseV1)
async def chat(request: ChatAPIRequest):
    last_message = request.messages[-1] if request.messages else None
    if not last_message:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    session_id = request.session_id or request.device_id or "default"
    session = _get_or_create_session(session_id, request.device_id)
    
    user_message = {
        "role": "user",
        "content": last_message.content,
        "timestamp": datetime.now().isoformat(),
    }
    session["messages"].append(user_message)
    
    full_response = ""
    async for chunk in chat_stream(request):
        pass
    
    assistant_message = {
        "role": "assistant",
        "content": full_response,
        "timestamp": datetime.now().isoformat(),
    }
    session["messages"].append(assistant_message)
    
    return ChatResponseV1(
        thread_id=session_id,
        message=full_response,
        status="success",
    )


@router.post("/cancel")
async def cancel_task(request: ChatAPIRequest):
    session_id = request.session_id or request.device_id or "default"
    session = _sessions.get(session_id)
    
    if session and session.get("agent"):
        agent = session["agent"]
        if hasattr(agent, 'cancel'):
            await agent.cancel()
    
    return {"success": True, "message": "Task cancelled"}
