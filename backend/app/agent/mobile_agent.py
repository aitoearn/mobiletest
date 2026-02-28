import asyncio
import base64
import json
import re
import traceback
from typing import Any, AsyncIterator, Optional, Dict, List
from dataclasses import dataclass, field
import logging

from openai import AsyncOpenAI
import httpx

# 导入新架构模块
from .config import ProtocolType, ModelConfig, ModelProvider, get_config_manager
from .protocol_adapter import get_adapter, parse_action as adapt_parse_action
from .actions import Action, ActionType, ActionSpace, create_parser
from .history import HistoryManager, HistoryEntry
from .context_builder import ContextBuilder, ContextConfig
from .planner import create_planner, TaskPlan, PlanExecutor

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """步骤执行结果"""
    success: bool
    finished: bool
    action: Optional[dict]
    thinking: str
    message: str
    step: int = 0
    screenshot: Optional[str] = None


@dataclass
class AgentConfig:
    """Agent 配置"""
    model_config: Dict[str, Any] = field(default_factory=dict)
    protocol: ProtocolType = ProtocolType.UNIVERSAL
    max_steps: int = 20
    max_context_messages: int = 10
    enable_history: bool = True
    enable_planning: bool = True
    enable_loop_detection: bool = True
    system_prompt: Optional[str] = None


class MobileAgentV2:
    """
    MobileAgent V2 - 重构版本
    集成新架构：协议适配、历史管理、上下文构建、任务规划
    """
    
    def __init__(
        self,
        model_config: dict,
        device_service,
        vision_service,
        max_steps: int = 20,
        max_context_messages: int = 10,
    ):
        # 从 model_config 中提取系统提示词和协议
        system_prompt = model_config.get("system_prompt")
        protocol_str = model_config.get("protocol", "universal")
        
        try:
            protocol = ProtocolType(protocol_str)
        except ValueError:
            protocol = ProtocolType.UNIVERSAL
        
        self.config = AgentConfig(
            model_config=model_config,
            protocol=protocol,
            max_steps=max_steps,
            max_context_messages=max_context_messages,
            system_prompt=system_prompt,
        )
        self.device = device_service
        self.vision = vision_service
        
        # 初始化协议适配
        self._init_protocol_adapter()
        
        # 初始化 LLM 客户端
        self._init_llm_client()
        
        # 初始化新架构组件
        self._init_components()
        
        # 状态管理
        self._step_count = 0
        self._is_running = False
        self._cancel_event = asyncio.Event()
        self._context: List[Dict] = []
        self._current_task: Optional[str] = None
        
        logger.info(f"MobileAgentV2 initialized with protocol: {self.config.protocol.value}")
    
    def _init_protocol_adapter(self):
        """初始化协议适配器"""
        model_id = self.config.model_config.get("model", "")
        
        # 如果配置中已指定协议，优先使用；否则自动检测
        if self.config.protocol == ProtocolType.UNIVERSAL:
            config_manager = get_config_manager()
            detected_protocol = config_manager.detect_protocol(model_id)
            self.config.protocol = detected_protocol
            logger.info(f"Protocol auto-detected: {detected_protocol.value}")
        else:
            logger.info(f"Protocol from config: {self.config.protocol.value}")
        
        # 获取适配器
        self.adapter = get_adapter(self.config.protocol)
        logger.info(f"Protocol adapter initialized: {self.config.protocol.value}")
    
    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        base_url = self.config.model_config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        api_key = self.config.model_config.get("api_key")
        
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=120,
            http_client=httpx.AsyncClient(proxy=None),
        )
        
        logger.info(f"LLM client initialized: base_url={base_url}")
    
    def _init_components(self):
        """初始化新架构组件"""
        # 历史管理器
        if self.config.enable_history:
            self.history_manager = HistoryManager(
                max_history=50,
                enable_loop_detection=self.config.enable_loop_detection,
            )
        else:
            self.history_manager = None
        
        # 上下文构建器
        context_config = ContextConfig(
            max_history_entries=self.config.max_context_messages,
                system_prompt_template=self.config.system_prompt,
            coordinate_scale=self.adapter.config.coordinate_scale if hasattr(self, 'adapter') else 1000,
        )
        self.context_builder = ContextBuilder(
            config=context_config,
            protocol=self.config.protocol
        )
        
        print(f"_init_components Context builder initialized: {context_config}")
        # 动作解析器
        self.action_parser = create_parser("autoglm")
        
        # 任务规划器
        if self.config.enable_planning:
            self.plan_executor = PlanExecutor()
        else:
            self.plan_executor = None
    
    async def stream(self, task: str, device_id: str) -> AsyncIterator[dict[str, Any]]:
        """
        执行任务流
        
        使用新架构组件：
        - 历史管理器记录操作历史
        - 上下文构建器构建 LLM 消息
        - 动作解析器解析模型输出
        - 任务规划器管理复杂任务
        """
        self._is_running = True
        self._cancel_event.clear()
        self._step_count = 0
        self._current_task = task
        
        # 重置历史记录
        if self.history_manager:
            self.history_manager.clear()
        
        # 创建任务计划（如果启用）
        if self.plan_executor and self.config.enable_planning:
            plan = self.plan_executor.create_plan(task)
            logger.info(f"Task plan created: {len(plan.steps)} steps")
            yield {"type": "plan", "data": plan.to_dict()}
        
        try:
            # 初始截图
            screenshot = await self.device.screenshot_base64(device_id)
            if not screenshot:
                yield {"type": "error", "data": {"message": "截图失败"}}
                return
            
            # 主循环
            while self._step_count < self.config.max_steps and self._is_running:
                if self._cancel_event.is_set():
                    raise asyncio.CancelledError()
                
                # 检查循环检测
                if self.history_manager:
                    is_loop, loop_reason = self.history_manager.check_loop()
                    if is_loop:
                        logger.warning(f"Loop detected: {loop_reason}")
                        yield {"type": "warning", "data": {"message": f"检测到循环: {loop_reason}"}}
                        # 可以在这里添加循环处理逻辑
                
                async for event in self._execute_step_v2(device_id, task, screenshot):
                    yield event
                    
                    if event["type"] == "step" and event["data"].get("finished"):
                        return
                
                # 更新截图用于下一步
                screenshot = await self.device.screenshot_base64(device_id)
            
            # 达到最大步数
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
        
        # 构建用户消息：包含任务提醒，让 LLM 知道当前执行状态
        step_prompt = f"当前是第 {self._step_count} 步，请根据当前截图继续执行任务。"
        if self._step_count > 1:
            step_prompt += " 注意：请检查上一步操作是否生效，如果已完成部分任务，请继续下一步，不要重复已完成的操作。"
        
        screen_message = self._build_user_message(step_prompt, screenshot, screen_info)
        self._context.append(screen_message)
        
        messages = self._get_limited_context()
        
        # 调试：打印完整上下文
        print(f"[DEBUG] ===== Step {self._step_count} Context ({len(messages)} messages) =====")
        for i, msg in enumerate(messages):
            content_preview = ""
            if isinstance(msg.get("content"), str):
                content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            elif isinstance(msg.get("content"), list):
                content_parts = []
                for c in msg.get("content", []):
                    if c.get("type") == "text":
                        text = c.get("text", "")[:80]
                        content_parts.append(f"text: {text}...")
                    elif c.get("type") == "image_url":
                        content_parts.append("image")
                content_preview = " | ".join(content_parts)
            print(f"[DEBUG] Msg {i} [{msg.get('role')}]: {content_preview}")
        print(f"[DEBUG] ===== End Context =====")
        
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
            logger.warning(f"Failed to parse action1 from: {raw_content}")
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
        
        # 执行动作后再次截图，获取执行后的屏幕状态
        try:
            final_screenshot = await self.device.screenshot_base64(device_id)
        except Exception:
            final_screenshot = screenshot  # 如果失败，使用之前的截图
        
        # 更新上下文：将上一条用户消息中的图片移除，只保留文本，减少token消耗
        if len(self._context) >= 2 and self._context[-1].get("role") == "user":
            last_user_msg = self._context[-1]
            if isinstance(last_user_msg.get("content"), list):
                # 只保留文本部分
                text_only_content = [
                    c for c in last_user_msg.get("content", []) 
                    if c.get("type") == "text"
                ]
                if text_only_content:
                    self._context[-1] = {
                        "role": "user",
                        "content": text_only_content
                    }
        
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
            "message": result.get("message", ""),
            "screenshot": screenshot  # 添加截图
        }}
    
    async def _execute_step_v2(
        self,
        device_id: str,
        task: str,
        screenshot: str
    ) -> AsyncIterator[dict[str, Any]]:
        """
        执行单步 - V2 版本（使用新架构组件）
        """
        self._step_count += 1
        
        # 截图前短暂等待
        await asyncio.sleep(0.5)
        
        try:
            # 获取当前应用信息
            current_app = await self.device.get_current_app(device_id)
            screen_info = self._build_screen_info(current_app)
            
            # 使用上下文构建器构建消息
            step_prompt = f"当前是第 {self._step_count} 步，请根据当前截图继续执行任务。"
            if self._step_count > 1:
                step_prompt += " 注意：请检查上一步操作是否生效，不要重复已完成的操作。"
            
            messages = self.context_builder.build_messages(
                task=task,
                history_manager=self.history_manager,
                current_screenshot=screenshot,
                current_observation=screen_info,
            )
            
            # 添加步骤提示
            messages.append({
                "role": "user",
                "content": step_prompt
            })
            
            logger.debug(f"Step {self._step_count}: Sending {len(messages)} messages to LLM")
            
            # 调用 LLM
            thinking = ""
            raw_content = ""
            
            async for chunk in self._stream_llm(messages):
                if self._cancel_event.is_set():
                    raise asyncio.CancelledError()
                
                if chunk["type"] == "thinking":
                    thinking += chunk["content"]
                    yield {"type": "thinking", "data": {"chunk": chunk["content"]}}
                elif chunk["type"] == "raw":
                    raw_content += chunk["content"]
            
            print(f"Raw LLM content: {raw_content[:500]}")
          
            
            # 使用动作解析器解析动作
            action_obj = self.action_parser.parse(raw_content)
            
            if not action_obj:
                logger.warning(f"Failed to parse action2 from: {raw_content}")
                yield {"type": "step", "data": {
                    "step": self._step_count,
                    "thinking": thinking,
                    "action": None,
                    "success": False,
                    "finished": True,
                    "message": "无法解析动作"
                }}
                return
            
            # 转换为旧格式以保持兼容性
            action_dict = self._action_to_dict(action_obj)
            
            yield {"type": "action", "data": {
                "step": self._step_count,
                "action": action_dict
            }}
            
            # 执行动作
            result = await self._execute_action(device_id, action_dict)
            
            # 记录到历史
            if self.history_manager:
                self.history_manager.add_entry(
                    action=action_obj,
                    observation=result.get("message", ""),
                    metadata={"success": result.get("success", False)}
                )
            
            # 检查是否完成
            finished = action_obj.action_type == ActionType.FINISH or result.get("should_finish", False)
            
            # 更新计划执行器
            if self.plan_executor:
                self.plan_executor.report_step_result(
                    success=result.get("success", False),
                    observation=result.get("message", "")
                )
            
            yield {"type": "step", "data": {
                "step": self._step_count,
                "thinking": thinking,
                "action": action_dict,
                "success": result.get("success", False),
                "finished": finished,
                "message": result.get("message", ""),
                "screenshot": screenshot
            }}
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Step execution error: {e}", exc_info=True)
            yield {"type": "error", "data": {"message": f"步骤执行错误: {e}"}}
            yield {"type": "step", "data": {
                "step": self._step_count,
                "success": False,
                "finished": True,
                "message": str(e)
            }}
    
    def _action_to_dict(self, action: Action) -> dict:
        """将 Action 对象转换为字典（保持向后兼容）"""
        action_type_map = {
            ActionType.CLICK: "Tap",
            ActionType.LONG_CLICK: "LongPress",
            ActionType.SWIPE: "Swipe",
            ActionType.TYPE: "Type",
            ActionType.BACK: "Back",
            ActionType.HOME: "Home",
            ActionType.RECENT: "Recent",
            ActionType.WAIT: "Wait",
            ActionType.FINISH: "Finish",
            ActionType.LAUNCH_APP: "Launch",
        }
        
        action_name = action_type_map.get(action.action_type, action.action_type.value)
        
        result = {
            "_metadata": "do",
            "action": action_name,
        }
        
        # 添加参数
        for key, value in action.params.items():
            result[key] = value
        
        # 特殊处理某些动作的参数映射
        if action.action_type == ActionType.CLICK and "x" in action.params and "y" in action.params:
            result["element"] = [action.params["x"], action.params["y"]]
        
        if action.action_type == ActionType.FINISH:
            result["_metadata"] = "finish"
            result["message"] = action.params.get("message", "任务完成")
        
        return result
    
    async def _stream_llm(self, messages: list[dict]) -> AsyncIterator[dict[str, str]]:
        logger.info(f"Calling LLM with model: {self.config.model_config.get('model')}, base_url: {self.config.model_config.get('base_url')}")
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model_config.get("model", "autoglm-phone"),
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
        
        print(f"[DEBUG] _parse_action Parsing action, content length: {len(content)}")
        print(f"[DEBUG] _parse_action Content: {content[:900]}...")
        
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
        """限制上下文消息数量，保留最近的消息和初始任务描述，并清理历史图片"""
        # 先清理所有历史消息中的图片（只保留最后一条用户消息的图片）
        cleaned_context = self._remove_old_images_from_context()
        
        if len(cleaned_context) <= self.config.max_context_messages + 1:
            return cleaned_context
        
        system_message = cleaned_context[0]
        # 保留初始任务描述（第一条用户消息），防止任务丢失
        initial_task_message = cleaned_context[1] if len(cleaned_context) > 1 and cleaned_context[1].get("role") == "user" else None
        
        # 计算需要保留的最近消息数量
        # 如果有初始任务消息，则需要为它留出空间
        slots_for_recent = self.config.max_context_messages - 1 if initial_task_message else self.config.max_context_messages
        recent_messages = cleaned_context[-(slots_for_recent):]
        
        # 构建最终上下文：system + 初始任务 + 最近消息
        if initial_task_message:
            return [system_message, initial_task_message] + recent_messages
        else:
            return [system_message] + recent_messages
    
    def _remove_old_images_from_context(self) -> list[dict]:
        """清理上下文中的历史图片，只保留最后一条用户消息的图片"""
        result = []
        # 找到最后一条包含图片的用户消息索引
        last_image_idx = -1
        for i in range(len(self._context) - 1, -1, -1):
            msg = self._context[i]
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                if any(c.get("type") == "image_url" for c in msg.get("content", [])):
                    last_image_idx = i
                    break
        
        for i, msg in enumerate(self._context):
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                has_image = any(c.get("type") == "image_url" for c in msg.get("content", []))
                # 如果不是最后一条带图片的消息，则移除图片
                if has_image and i != last_image_idx:
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
    
    # ========== 新架构扩展方法 ==========
    
    def get_history_summary(self) -> str:
        """获取历史记录摘要"""
        if self.history_manager:
            return self.history_manager.get_summary()
        return "历史记录未启用"
    
    def get_plan_progress(self) -> Dict[str, Any]:
        """获取任务计划进度"""
        if self.plan_executor:
            return self.plan_executor.get_progress()
        return {"total": 0, "completed": 0, "failed": 0, "pending": 0, "percentage": 0}
    
    def export_session(self) -> Dict[str, Any]:
        """导出会话数据"""
        return {
            "task": self._current_task,
            "steps": self._step_count,
            "history": self.history_manager.export_to_dict() if self.history_manager else None,
            "plan": self.plan_executor.current_plan.to_dict() if self.plan_executor and self.plan_executor.current_plan else None,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        stats = {
            "steps": self._step_count,
            "protocol": self.config.protocol.value,
        }
        
        if self.history_manager:
            stats["history"] = self.history_manager.get_statistics()
        
        if self.plan_executor:
            stats["plan"] = self.get_plan_progress()
        
        return stats


# ========== 向后兼容别名 ==========

class MobileAgent(MobileAgentV2):
    """
    MobileAgent - 向后兼容的别名
    
    此类继承自 MobileAgentV2，提供完全相同的 API。
    新代码建议直接使用 MobileAgentV2。
    """
    pass


# 便捷函数
def create_agent(
    model_config: dict,
    device_service,
    vision_service,
    **kwargs
) -> MobileAgentV2:
    """创建 Agent 的便捷函数"""
    return MobileAgentV2(
        model_config=model_config,
        device_service=device_service,
        vision_service=vision_service,
        **kwargs
    )
