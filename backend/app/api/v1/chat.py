import asyncio
import json
import threading
from typing import Any, AsyncGenerator, Optional
from datetime import datetime
from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.contracts import ChatRequestV1, ChatResponseV1
from app.agent.llm.llm import LLMClient
from app.services.scanner import device_scanner

router = APIRouter(prefix="/chat", tags=["对话接口"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatAPIRequest(BaseModel):
    messages: list[ChatMessage]
    device_id: Optional[str] = None
    session_id: Optional[str] = None


class SessionContext(BaseModel):
    session_id: str
    device_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    messages: list[dict] = field(default_factory=list)


_sessions: dict[str, SessionContext] = {}
_sessions_lock = threading.Lock()

_active_tasks: dict[str, asyncio.Task] = {}
_active_tasks_lock = threading.Lock()


PLANNER_INSTRUCTIONS = """## 核心目标
你是一个负责操控手机的高级智能中枢。你的任务是将用户的意图转化为可执行的原子操作。

## 极其重要的限制
你的下级是一个执行者，只能：
1. 执行点击、滑动、输入等UI操作
2. 截图获取屏幕信息

## 交互策略

### 1. 如果你需要"操作手机"
下达明确的UI动作指令。
- ✅ "点击'设置'图标"
- ✅ "向下滑动屏幕"
- ✅ "打开微信"

### 2. 如果你需要"获取信息"
必须通过询问执行者获取屏幕信息。

## 工具集
1. `list_devices()` - 获取设备列表
2. `device_control(device_id, action, params)` - 控制设备执行操作

## 工作流
1. **Observe**: 调用工具获取当前状态
2. **Think**: 分析用户目标，规划下一步操作
3. **Act**: 发送操作指令

## 输出格式
直接输出文字回复用户，不需要调用工具的JSON格式。
"""


def _get_or_create_session(session_id: str, device_id: Optional[str] = None) -> SessionContext:
    with _sessions_lock:
        if session_id not in _sessions:
            _sessions[session_id] = SessionContext(
                session_id=session_id,
                device_id=device_id,
            )
        return _sessions[session_id]


def _clear_session(session_id: str) -> bool:
    with _sessions_lock:
        if session_id in _sessions:
            del _sessions[session_id]
            return True
        return False


async def _list_devices() -> str:
    devices = await device_scanner.scan_devices()
    result = []
    for device in devices:
        device_info = await device_scanner.get_device_info(device.device_id)
        result.append({
            "id": device.device_id,
            "model": device_info.get("model") or device.model,
            "status": device.status,
            "serial": device.device_id,
        })
    return json.dumps(result, ensure_ascii=False)


async def _device_control(device_id: str, action: str, params: dict = None) -> str:
    from app.services.device import device_control_service
    
    params = params or {}
    
    try:
        if action == "click":
            x = params.get("x")
            y = params.get("y")
            if x and y:
                success = await device_control_service.tap(device_id, x, y)
                return json.dumps({"success": success, "message": f"点击 ({x}, {y})"})
            return json.dumps({"success": False, "message": "缺少坐标参数"})
        
        elif action == "swipe":
            direction = params.get("direction", "down")
            if direction == "up":
                success = await device_control_service.swipe_up(device_id)
            elif direction == "down":
                success = await device_control_service.swipe_down(device_id)
            elif direction == "left":
                success = await device_control_service.swipe_left(device_id)
            elif direction == "right":
                success = await device_control_service.swipe_right(device_id)
            else:
                success = await device_control_service.swipe_down(device_id)
            return json.dumps({"success": success, "message": f"滑动 {direction}"})
        
        elif action == "input":
            text = params.get("text", "")
            success = await device_control_service.input_text(device_id, text)
            return json.dumps({"success": success, "message": f"输入: {text}"})
        
        elif action == "screenshot":
            return json.dumps({"success": True, "message": "截图功能需要通过 scrcpy 获取"})
        
        elif action == "launch_app":
            package = params.get("package")
            if package:
                success = await device_control_service.start_app(device_id, package)
                return json.dumps({"success": success, "message": f"启动应用: {package}"})
            return json.dumps({"success": False, "message": "缺少包名"})
        
        elif action == "get_screen_info":
            info = await device_control_service.get_device_info(device_id)
            return json.dumps({"success": True, "message": "获取成功", "data": info})
        
        elif action == "get_current_app":
            app = await device_control_service.get_current_app(device_id)
            return json.dumps({"success": True, "message": f"当前应用: {app}"})
        
        else:
            return json.dumps({"success": False, "message": f"未知动作: {action}"})
    
    except Exception as e:
        return json.dumps({"success": False, "message": str(e)})


async def _process_with_llm(
    messages: list[dict],
    device_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    llm_client = LLMClient()
    
    system_message = {
        "role": "system",
        "content": PLANNER_INSTRUCTIONS
    }
    
    all_messages = [system_message] + messages
    
    try:
        async for response in llm_client.chat_stream(all_messages):
            if response:
                yield f"data: {json.dumps({'type': 'message', 'content': response})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("", response_model=ChatResponseV1)
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
    session.messages.append(user_message)
    
    full_response = ""
    async for chunk in _process_with_llm(session.messages, request.device_id, session_id):
        pass
    
    assistant_message = {
        "role": "assistant",
        "content": full_response,
        "timestamp": datetime.now().isoformat(),
    }
    session.messages.append(assistant_message)
    
    return ChatResponseV1(
        thread_id=session_id,
        message=full_response,
        status="success",
    )


@router.post("/stream")
async def chat_stream(request: ChatAPIRequest):
    last_message = request.messages[-1] if request.messages else None
    if not last_message:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    session_id = request.session_id or request.device_id or "default"
    session = _get_or_create_session(session_id, request.device_id)
    
    user_message = {
        "role": "user",
        "content": last_message.content,
    }
    session.messages.append(user_message)
    
    async def event_generator():
        try:
            llm_client = LLMClient()
            
            system_message = {
                "role": "system", 
                "content": PLANNER_INSTRUCTIONS
            }
            
            all_messages = [system_message] + session.messages
            
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            tool_calls = []
            full_response = ""
            
            async for response in llm_client.chat_stream(all_messages):
                if response:
                    full_response += response
                    yield f"data: {json.dumps({'type': 'message', 'content': response})}\n\n"
            
            print(f"[DEBUG] Full LLM response: {full_response[:500]}")
            
            content, tools = llm_client.extract_tools(full_response)
            print(f"[DEBUG] Extracted tools: {tools}")
            
            if tools:
                for tool in tools:
                    tool_calls.append(tool)
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': tool.get('name'), 'tool_args': tool.get('arguments', {})})}\n\n"
            
            for tool in tool_calls:
                tool_name = tool.get("name")
                tool_args = tool.get("arguments", {})
                
                result = ""
                if tool_name == "list_devices":
                    result = await _list_devices()
                elif tool_name == "device_control":
                    device_id = tool_args.get("device_id") or tool_args.get("params", {}).get("device_id") or request.device_id
                    action = tool_args.get("action", "")
                    params = tool_args.get("params", {})
                    print(f"[DEBUG] device_control: device_id={device_id}, action={action}, params={params}")
                    result = await _device_control(device_id, action, params)
                
                yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': tool_name, 'result': result})}\n\n"
            
            assistant_message = {
                "role": "assistant",
                "content": full_response or "任务完成",
                "timestamp": datetime.now().isoformat(),
            }
            session.messages.append(assistant_message)
            
            yield f"data: {json.dumps({'type': 'done', 'content': '任务完成'})}\n\n"
            
        except Exception as e:
            import traceback
            print(f"[ERROR] chat_stream error: {traceback.format_exc()}")
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


class AbortRequest(BaseModel):
    session_id: str


@router.post("/abort")
async def abort_session(request: AbortRequest):
    with _active_tasks_lock:
        if request.session_id in _active_tasks:
            task = _active_tasks[request.session_id]
            task.cancel()
            del _active_tasks[request.session_id]
            return {"success": True, "message": f"Session {request.session_id} aborted"}
    return {"success": False, "message": "No active session"}


class ResetRequest(BaseModel):
    session_id: str


@router.post("/reset")
async def reset_session(request: ResetRequest):
    cleared = _clear_session(request.session_id)
    return {
        "success": True,
        "message": f"Session {request.session_id} {'cleared' if cleared else 'not found'}"
    }


@router.post("/supervisor", response_model=ChatResponseV1)
async def chat_supervisor(request: ChatRequestV1):
    response = await graph_runner.run(request)
    return response


@router.post("/supervisor/stream")
async def chat_supervisor_stream(request: ChatRequestV1):
    async def event_generator():
        async for chunk in graph_runner.run_stream(request):
            yield chunk
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


from app.orchestrator.runner import graph_runner
