import asyncio
import base64
import json
import re
import traceback
from typing import Any, AsyncIterator, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    success: bool
    finished: bool
    action: Optional[dict]
    thinking: str
    message: str


class MobileAgent:
    def __init__(
        self,
        model_config: dict,
        device_service,
        vision_service,
        max_steps: int = 20,
        max_context_messages: int = 5,
    ):
        self.model_config = model_config
        self.device = device_service
        self.vision = vision_service
        self.max_steps = max_steps
        self.max_context_messages = max_context_messages
        
        logger.info(f"MobileAgent init with config: base_url={model_config.get('base_url')}, model={model_config.get('model')}, api_key={model_config.get('api_key', '')[:10]}...")
        
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            base_url=model_config.get("base_url", "https://open.bigmodel.cn/api/paas/v4"),
            api_key=model_config.get("api_key"),
            timeout=120,
        )
        
        self._step_count = 0
        self._is_running = False
        self._cancel_event = asyncio.Event()
        self._context: list[dict] = []
        
        from .prompts import SYSTEM_PROMPT
        self.system_prompt = SYSTEM_PROMPT
    
    async def stream(self, task: str, device_id: str) -> AsyncIterator[dict[str, Any]]:
        self._is_running = True
        self._cancel_event.clear()
        self._step_count = 0
        self._context = [{"role": "system", "content": self.system_prompt}]
        
        try:
            screenshot = await self.device.screenshot_base64(device_id)
            if not screenshot:
                yield {"type": "error", "data": {"message": "截图失败"}}
                return
            
            initial_message = self._build_user_message(
                task, 
                screenshot, 
                "等待执行任务"
            )
            self._context.append(initial_message)
            
            while self._step_count < self.max_steps and self._is_running:
                if self._cancel_event.is_set():
                    raise asyncio.CancelledError()
                
                async for event in self._execute_step(device_id):
                    yield event
                    
                    if event["type"] == "step" and event["data"].get("finished"):
                        return
            
            yield {
                "type": "done",
                "data": {
                    "message": "已达到最大步数限制",
                    "steps": self._step_count,
                    "success": False,
                }
            }
            
        except asyncio.CancelledError:
            yield {"type": "cancelled", "data": {"message": "任务已取消"}}
            raise
        except Exception as e:
            logger.error(f"Agent error: {traceback.format_exc()}")
            yield {"type": "error", "data": {"message": str(e)}}
        finally:
            self._is_running = False
    
    async def _execute_step(self, device_id: str) -> AsyncIterator[dict[str, Any]]:
        self._step_count += 1
        
        try:
            screenshot = await self.device.screenshot_base64(device_id)
            if not screenshot:
                yield {"type": "error", "data": {"message": "截图失败"}}
                yield {"type": "step", "data": {
                    "step": self._step_count,
                    "success": False,
                    "finished": True,
                    "message": "截图失败"
                }}
                return
        except Exception as e:
            yield {"type": "error", "data": {"message": f"设备错误: {e}"}}
            return
        
        screen_message = self._build_user_message("", screenshot, "当前屏幕状态")
        self._context.append(screen_message)
        
        messages = self._get_limited_context()
        
        thinking = ""
        raw_content = ""
        
        try:
            async for chunk in self._stream_llm(messages):
                if self._cancel_event.is_set():
                    raise asyncio.CancelledError()
                
                if chunk["type"] == "thinking":
                    thinking += chunk["content"]
                    yield {"type": "thinking", "data": {"chunk": chunk["content"]}}
                elif chunk["type"] == "raw":
                    raw_content += chunk["content"]
                    
        except asyncio.CancelledError:
            raise
        except Exception as e:
            yield {"type": "error", "data": {"message": f"模型错误: {e}"}}
            return
        
        logger.info(f"Raw LLM content: {raw_content[:500]}")
        logger.info(f"Thinking: {thinking[:200]}")
        
        action = self._parse_action(raw_content)
        
        if not action:
            logger.warning(f"Failed to parse action from: {raw_content}")
            yield {"type": "step", "data": {
                "step": self._step_count,
                "thinking": thinking,
                "action": None,
                "success": False,
                "finished": True,
                "message": "无法解析动作"
            }}
            return
        
        yield {"type": "action", "data": {
            "step": self._step_count,
            "action": action
        }}
        
        result = await self._execute_action(device_id, action)
        
        finished = action.get("_metadata") == "finish" or result.get("should_finish", False)
        
        self._context.append({
            "role": "assistant",
            "content": f"熟虑{thinking}全景\n<answer>{raw_content}</answer>"
        })
        
        yield {"type": "step", "data": {
            "step": self._step_count,
            "thinking": thinking,
            "action": action,
            "success": result.get("success", False),
            "finished": finished,
            "message": result.get("message", "")
        }}
    
    async def _stream_llm(self, messages: list[dict]) -> AsyncIterator[dict[str, str]]:
        logger.info(f"Calling LLM with model: {self.model_config.get('model')}, base_url: {self.model_config.get('base_url')}")
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_config.get("model", "autoglm-phone"),
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
                stream=True,
            )
        except Exception as e:
            logger.error(f"LLM API error: {traceback.format_exc()}")
            raise
        
        buffer = ""
        action_markers = ["<answer>", "finish(", "do("]
        in_action_phase = False
        
        try:
            async for chunk in stream:
                if self._cancel_event.is_set():
                    await stream.close()
                    raise asyncio.CancelledError()
                
                if len(chunk.choices) == 0:
                    continue
                
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield {"type": "raw", "content": content}
                    
                    if in_action_phase:
                        continue
                    
                    buffer += content
                    
                    marker_found = False
                    for marker in action_markers:
                        if marker in buffer:
                            thinking_part = buffer.split(marker, 1)[0]
                            thinking_part = re.sub(r'^熟虑|全景$', '', thinking_part).strip()
                            if thinking_part:
                                yield {"type": "thinking", "content": thinking_part}
                            in_action_phase = True
                            marker_found = True
                            break
                    
                    if marker_found:
                        continue
                    
                    is_potential_marker = False
                    for marker in action_markers:
                        for i in range(1, len(marker) + 1):
                            if buffer.endswith(marker[:i]):
                                is_potential_marker = True
                                break
                        if is_potential_marker:
                            break
                    
                    if not is_potential_marker and buffer:
                        yield {"type": "thinking", "content": buffer}
                        buffer = ""
                        
        finally:
            await stream.close()
    
    def _parse_action(self, content: str) -> Optional[dict]:
        content = content.strip()
        
        if "do(action=" in content:
            match = re.search(r'do\(action\s*=\s*"[^"]+".*?\)', content, re.DOTALL)
            if match:
                return self._parse_do(match.group(0))
        
        if "finish(message=" in content:
            match = re.search(r'finish\(message\s*=\s*"[^"]*"\)', content)
            if match:
                return self._parse_finish(match.group(0))
        
        if content.startswith("finish("):
            return self._parse_finish(content)
        elif content.startswith("do("):
            return self._parse_do(content)
        elif "<answer>" in content:
            answer_match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
            if answer_match:
                answer_content = answer_match.group(1).strip()
                if answer_content.startswith("finish("):
                    return self._parse_finish(answer_content)
                elif answer_content.startswith("do("):
                    return self._parse_do(answer_content)
                elif "do(action=" in answer_content:
                    match = re.search(r'do\(action\s*=\s*"[^"]+".*?\)', answer_content, re.DOTALL)
                    if match:
                        return self._parse_do(match.group(0))
                    return self._parse_do(answer_content)
        
        return None
    
    def _parse_finish(self, action_str: str) -> dict:
        message_match = re.search(r'finish\(message\s*=\s*["\']([^"\']+)["\']', action_str)
        message = message_match.group(1) if message_match else "任务完成"
        return {
            "_metadata": "finish",
            "message": message
        }
    
    def _parse_do(self, action_str: str) -> dict:
        params = self._extract_params(action_str, "do")
        action_name = params.get("action", "")
        
        result = {
            "_metadata": "do",
            "action": action_name,
        }
        
        for key, value in params.items():
            if key != "action":
                result[key] = value
        
        return result
    
    def _extract_params(self, action_str: str, function_name: str) -> dict:
        prefix = f"{function_name}("
        if not action_str.startswith(prefix):
            return {}
        
        params_str = action_str[len(prefix):-1]
        params = {}
        current_key = None
        current_value = ""
        in_quotes = False
        quote_char = None
        bracket_depth = 0
        i = 0
        
        while i < len(params_str):
            char = params_str[i]
            
            if char in ('"', "'") and (i == 0 or params_str[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            
            if not in_quotes:
                if char in ('[', '{'):
                    bracket_depth += 1
                elif char in (']', '}'):
                    bracket_depth -= 1
                
                if char == '=' and bracket_depth == 0:
                    current_key = current_value.strip()
                    current_value = ""
                    i += 1
                    continue
                
                if char == ',' and bracket_depth == 0:
                    if current_key:
                        params[current_key] = self._parse_value(current_value.strip())
                        current_key = None
                        current_value = ""
                    i += 1
                    continue
            
            current_value += char
            i += 1
        
        if current_key:
            params[current_key] = self._parse_value(current_value.strip())
        
        return params
    
    def _parse_value(self, value_str: str):
        value_str = value_str.strip()
        if not value_str:
            return ""
        
        try:
            import ast
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            return value_str
    
    async def _execute_action(self, device_id: str, action: dict) -> dict:
        if action.get("_metadata") == "finish":
            return {"success": True, "should_finish": True, "message": action.get("message", "任务完成")}
        
        action_name = action.get("action", "").lower()
        
        try:
            if action_name == "launch":
                app = action.get("app", "")
                package = self._get_package_name(app)
                success = await self.device.start_app(device_id, package)
                return {"success": success, "message": f"启动应用: {app}"}
            
            elif action_name == "tap":
                element = action.get("element", [])
                if isinstance(element, list) and len(element) >= 2:
                    x, y = element[0], element[1]
                    success = await self.device.tap(device_id, x, y)
                    return {"success": success, "message": f"点击 ({x}, {y})"}
                return {"success": False, "message": "无效的坐标"}
            
            elif action_name == "type":
                text = action.get("text", "")
                success = await self.device.input_text(device_id, text)
                return {"success": success, "message": f"输入: {text}"}
            
            elif action_name == "swipe":
                direction = action.get("direction", "down")
                if direction == "up":
                    success = await self.device.swipe_up(device_id)
                elif direction == "down":
                    success = await self.device.swipe_down(device_id)
                elif direction == "left":
                    success = await self.device.swipe_left(device_id)
                elif direction == "right":
                    success = await self.device.swipe_right(device_id)
                else:
                    success = await self.device.swipe_down(device_id)
                return {"success": success, "message": f"滑动: {direction}"}
            
            elif action_name == "back":
                success = await self.device.press_back(device_id)
                return {"success": success, "message": "返回"}
            
            elif action_name == "home":
                success = await self.device.press_home(device_id)
                return {"success": success, "message": "回到主页"}
            
            elif action_name == "wait":
                duration = action.get("duration", "1")
                if isinstance(duration, str):
                    duration = float(re.search(r'\d+', duration).group() or "1")
                await asyncio.sleep(duration)
                return {"success": True, "message": f"等待 {duration} 秒"}
            
            else:
                return {"success": False, "message": f"未知动作: {action_name}"}
                
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _get_limited_context(self) -> list[dict]:
        if len(self._context) <= self.max_context_messages + 1:
            return self._remove_old_images(self._context)
        
        system_message = self._context[0]
        recent_messages = self._context[-(self.max_context_messages):]
        
        return self._remove_old_images([system_message] + recent_messages)
    
    def _remove_old_images(self, messages: list[dict]) -> list[dict]:
        result = []
        for i, msg in enumerate(messages):
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                has_image = any(c.get("type") == "image_url" for c in msg.get("content", []))
                if has_image and i < len(messages) - 1:
                    text_parts = [c for c in msg.get("content", []) if c.get("type") == "text"]
                    if text_parts:
                        result.append({"role": msg["role"], "content": text_parts})
                    else:
                        result.append({"role": msg["role"], "content": "[历史截图已移除]"})
                else:
                    result.append(msg)
            else:
                result.append(msg)
        return result
    
    def _get_package_name(self, app_name: str) -> str:
        packages = {
            "京东": "com.jingdong.app.mall",
            "淘宝": "com.taobao.taobao",
            "微信": "com.tencent.mm",
            "支付宝": "com.eg.android.AlipayGphone",
            "抖音": "com.ss.android.ugc.aweme",
            "快手": "com.smile.gifmaker",
            "美团": "com.sankuai.meituan",
            "拼多多": "com.xunmeng.pinduoduo",
            "微博": "com.sina.weibo",
            "QQ": "com.tencent.mobileqq",
        }
        return packages.get(app_name, app_name)
    
    def _build_user_message(self, text: str, screenshot_base64: str, screen_info: str) -> dict:
        content = []
        
        if text:
            content.append({"type": "text", "text": text})
        
        content.append({"type": "text", "text": f"\n** 屏幕信息 **\n\n{screen_info}"})
        
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{screenshot_base64}"
            }
        })
        
        return {"role": "user", "content": content}
    
    async def cancel(self):
        self._cancel_event.set()
        self._is_running = False
    
    def reset(self):
        self._context = []
        self._step_count = 0
        self._is_running = False
        self._cancel_event.clear()
    
    @property
    def step_count(self) -> int:
        return self._step_count
    
    @property
    def is_running(self) -> bool:
        return self._is_running
