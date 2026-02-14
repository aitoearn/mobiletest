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
            
            # 获取当前应用信息
            current_app = await self.device.get_current_app(device_id)
            screen_info = self._build_screen_info(current_app)
            
            initial_message = self._build_user_message(
                task, 
                screenshot, 
                screen_info
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
        
        # 截图前短暂等待，确保屏幕内容已稳定
        await asyncio.sleep(0.5)
        
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
        
        # 获取当前应用信息
        current_app = await self.device.get_current_app(device_id)
        print(f"[DEBUG] Current app: {current_app}")
        screen_info = self._build_screen_info(current_app)
        
        screen_message = self._build_user_message("", screenshot, screen_info)
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
        action_markers = ["finish(message=", "do(action="]
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
                            # 移除熟虑和全景标签
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
        
        print(f"[DEBUG] Parsing action, content length: {len(content)}")
        print(f"[DEBUG] Content: {content[:500]}...")
        
        # 优先检查 <answer> 标签
        if "<answer>" in content:
            answer_match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
            if answer_match:
                answer_content = answer_match.group(1).strip()
                if answer_content.startswith("finish("):
                    return self._parse_finish(answer_content)
                elif answer_content.startswith("do("):
                    return self._parse_do(answer_content)
                elif "do(action=" in answer_content:
                    return self._parse_do_from_position(answer_content, answer_content.find("do("))
        
        # 检查 finish( 模式
        finish_idx = content.find("finish(")
        if finish_idx != -1:
            print(f"[DEBUG] Found finish( at position {finish_idx}")
            return self._parse_finish_from_position(content, finish_idx)
        
        # 检查 do( 模式
        do_idx = content.find("do(")
        if do_idx != -1:
            print(f"[DEBUG] Found do( at position {do_idx}")
            return self._parse_do_from_position(content, do_idx)
        
        # 如果没有找到标准格式，尝试从文本中提取坐标和意图
        print(f"[DEBUG] No standard format found, trying to extract from text")
        return self._extract_action_from_text(content)
    
    def _parse_finish_from_position(self, content: str, start_idx: int) -> dict:
        """从指定位置解析 finish 调用"""
        # 找到 message= 后面的引号开始位置
        message_start = content.find("message=", start_idx)
        if message_start == -1:
            return {"_metadata": "finish", "message": "任务完成"}
        
        # 找到第一个引号
        quote_start = None
        quote_char = None
        for i in range(message_start + 7, min(len(content), message_start + 20)):
            if content[i] in ('"', "'"):
                quote_start = i + 1
                quote_char = content[i]
                break
        
        if quote_start is None:
            return {"_metadata": "finish", "message": "任务完成"}
        
        # 找到匹配的结束引号（处理转义和嵌套）
        message_end = None
        i = quote_start
        while i < len(content):
            char = content[i]
            # 处理转义引号
            if char == '\\' and i + 1 < len(content) and content[i + 1] == quote_char:
                i += 2
                continue
            # 找到结束引号
            if char == quote_char:
                message_end = i
                break
            i += 1
        
        if message_end is None:
            # 没找到结束引号，取到内容末尾
            message = content[quote_start:].strip()
        else:
            message = content[quote_start:message_end]
        
        # 处理转义字符
        message = message.replace('\\"', '"').replace("\\'", "'")
        
        return {
            "_metadata": "finish",
            "message": message.strip()
        }
    
    def _parse_do_from_position(self, content: str, start_idx: int) -> dict:
        """从指定位置解析 do 调用"""
        # 找到匹配的右括号
        depth = 0
        end_idx = start_idx
        in_quotes = False
        quote_char = None
        bracket_depth = 0
        
        for i in range(start_idx, len(content)):
            char = content[i]
            
            if char in ('"', "'") and (i == 0 or content[i-1] != '\\'):
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
                elif char == '(':
                    depth += 1
                elif char == ')':
                    if bracket_depth == 0:
                        depth -= 1
                        if depth == 0:
                            end_idx = i + 1
                            break
        
        action_str = content[start_idx:end_idx]
        return self._parse_do(action_str)
    
    def _parse_finish(self, action_str: str) -> dict:
        # 使用更宽松的正则来匹配多行 message
        message_match = re.search(r'finish\s*\(\s*message\s*=\s*["\'](.+?)["\']\s*\)', action_str, re.DOTALL)
        if message_match:
            message = message_match.group(1).strip()
        else:
            # 尝试提取整个 message 内容
            message_match = re.search(r'message\s*=\s*["\']([^"\']*)', action_str, re.DOTALL)
            message = message_match.group(1).strip() if message_match else "任务完成"
        
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
    
    def _extract_action_from_text(self, content: str) -> Optional[dict]:
        """当LLM没有按标准格式输出时，尝试从文本中提取动作意图和坐标"""
        print(f"[DEBUG] _extract_action_from_text called")
        
        # 提取坐标 - 匹配 (x, y) 或 [x, y] 或坐标(x, y) 等格式
        coord_patterns = [
            r'坐标\s*[（\(]\s*(\d+)\s*[，,]\s*(\d+)\s*[）\)]',  # 坐标(122, 242)
            r'[（\(]\s*(\d+)\s*[，,]\s*(\d+)\s*[）\)]',  # (122, 242)
            r'\[\s*(\d+)\s*[，,]\s*(\d+)\s*\]',  # [122, 242]
            r'位置\s*[：:]\s*[（\(]?\s*(\d+)\s*[，,]\s*(\d+)\s*[）\)]?',  # 位置: (122, 242)
        ]
        
        coords = None
        for pattern in coord_patterns:
            match = re.search(pattern, content)
            if match:
                coords = (int(match.group(1)), int(match.group(2)))
                print(f"[DEBUG] Extracted coords: {coords}")
                break
        
        # 判断动作意图
        action = None
        
        # 点击相关关键词
        click_keywords = ["点击", "点", "tap", "click", "选择", "按下", "触摸"]
        if any(kw in content.lower() for kw in click_keywords):
            action = "Tap"
        
        # 滑动相关关键词
        swipe_keywords = ["滑动", "滑", "swipe", "滚动", "上滑", "下滑", "左滑", "右滑"]
        if any(kw in content.lower() for kw in swipe_keywords):
            action = "Swipe"
            # 判断滑动方向
            if "上" in content or "up" in content.lower():
                return {"_metadata": "do", "action": "Swipe", "direction": "up"}
            elif "下" in content or "down" in content.lower():
                return {"_metadata": "do", "action": "Swipe", "direction": "down"}
            elif "左" in content or "left" in content.lower():
                return {"_metadata": "do", "action": "Swipe", "direction": "left"}
            elif "右" in content or "right" in content.lower():
                return {"_metadata": "do", "action": "Swipe", "direction": "right"}
        
        # 输入相关关键词
        input_keywords = ["输入", "打字", "type", "input", "填写"]
        if any(kw in content.lower() for kw in input_keywords):
            # 尝试提取要输入的文本
            text_match = re.search(r'[输入打字填写]\s*[：:"\']?\s*(.+?)[\"\'\n]|text\s*[=:]\s*["\'](.+?)["\']', content, re.IGNORECASE)
            if text_match:
                text = text_match.group(1) or text_match.group(2)
                return {"_metadata": "do", "action": "Type", "text": text.strip()}
        
        # 返回/后退关键词
        back_keywords = ["返回", "后退", "back", "返回上一"]
        if any(kw in content.lower() for kw in back_keywords):
            return {"_metadata": "do", "action": "Back"}
        
        # 完成关键词
        finish_keywords = ["完成", "任务完成", "成功", "finish", "done", "已经完成"]
        if any(kw in content.lower() for kw in finish_keywords):
            # 检查是否真的完成了任务
            if "完成" in content or "任务完成" in content:
                return {"_metadata": "finish", "message": "任务已完成"}
        
        # 如果找到了坐标且有点击意图
        if coords and action == "Tap":
            # 将实际坐标转换为 1000x1000 坐标系
            # 注意：这里假设屏幕分辨率大约是 1080x2400，需要根据实际情况调整
            # 但 autoglm-phone 模型返回的坐标应该已经是标准化的
            return {
                "_metadata": "do",
                "action": "Tap",
                "element": list(coords)
            }
        
        # 如果只有坐标没有明确动作，默认为点击
        if coords:
            return {
                "_metadata": "do",
                "action": "Tap",
                "element": list(coords)
            }
        
        print(f"[DEBUG] Could not extract action from text")
        return None
    
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
                # 等待应用启动和页面加载
                print(f"[DEBUG] Launched {app}, waiting for app to load...")
                await asyncio.sleep(2.0)  # 等待2秒让应用完全加载
                return {"success": success, "message": f"启动应用: {app}"}
            
            elif action_name == "tap":
                element = action.get("element", [])
                if isinstance(element, list) and len(element) >= 2:
                    # 坐标是 1000x1000 标准化坐标系，需要转换为实际屏幕坐标
                    norm_x, norm_y = element[0], element[1]
                    
                    # 获取屏幕尺寸
                    screen_size = await self.device._get_screen_size(device_id)
                    if screen_size:
                        screen_width, screen_height = screen_size
                        # 转换坐标
                        actual_x = int(norm_x * screen_width / 1000)
                        actual_y = int(norm_y * screen_height / 1000)
                        print(f"[DEBUG] Converting coords: ({norm_x}, {norm_y}) -> ({actual_x}, {actual_y}) for screen {screen_width}x{screen_height}")
                    else:
                        actual_x, actual_y = norm_x, norm_y
                        print(f"[DEBUG] Could not get screen size, using raw coords: ({actual_x}, {actual_y})")
                    
                    success = await self.device.tap(device_id, actual_x, actual_y)
                    # 点击后等待页面响应
                    await asyncio.sleep(1.0)
                    return {"success": success, "message": f"点击 ({actual_x}, {actual_y})"}
                return {"success": False, "message": "无效的坐标"}
            
            elif action_name == "type":
                text = action.get("text", "")
                success = await self.device.input_text(device_id, text)
                # 输入后短暂等待
                await asyncio.sleep(0.5)
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
        
        # 参考 AutoGLM-GUI: 先放图片，再放文字
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{screenshot_base64}"
            }
        })
        
        if text:
            content.append({"type": "text", "text": text})
        
        content.append({"type": "text", "text": f"\n** Screen Info **\n\n{screen_info}"})
        
        return {"role": "user", "content": content}
    
    def _build_screen_info(self, current_app: Optional[str]) -> str:
        """构建屏幕信息 JSON 字符串"""
        import json
        info = {"current_app": current_app or "unknown"}
        return json.dumps(info, ensure_ascii=False)
    
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
