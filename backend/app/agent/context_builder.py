"""
上下文构建器模块
构建 LLM 的完整上下文，包括系统提示、历史记录、当前状态等
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
import json

from .config import ProtocolType, ModelConfig, get_config_manager
from .protocol_adapter import get_adapter, AdaptedMessage
from .history import HistoryManager, HistoryEntry
from .actions.space import ActionSpace


@dataclass
class ContextConfig:
    """上下文配置"""
    # 历史记录配置
    max_history_entries: int = 10
    include_screenshots: bool = True
    include_action_results: bool = True
    
    # 提示词配置
    system_prompt_template: str = ""
    task_prompt_template: str = ""
    
    # 格式配置
    action_format: str = "json"  # json, xml, text
    coordinate_scale: int = 1000
    
    # 额外上下文
    extra_context: Dict[str, Any] = field(default_factory=dict)


class ContextBuilder:
    """上下文构建器"""
    
    # 默认系统提示词模板
    DEFAULT_SYSTEM_PROMPT = """你是一个移动端自动化测试助手，可以通过控制 Android/iOS 设备来完成各种任务。

你的职责：
1. 分析当前屏幕状态
2. 决定下一步操作
3. 执行操作并观察结果
4. 重复直到任务完成

注意事项：
- 坐标使用 0-{scale} 的相对坐标系
- 每次只执行一个动作
- 如果操作失败，尝试替代方案
- 任务完成后必须调用 finish 动作

{action_space}
"""
    
    # 默认任务提示词模板
    DEFAULT_TASK_PROMPT = """当前任务: {task}

{context}

请根据当前屏幕和历史操作，决定下一步动作。
"""
    
    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        protocol: ProtocolType = ProtocolType.UNIVERSAL
    ):
        self.config = config or ContextConfig()
        self.protocol = protocol
        self.adapter = get_adapter(protocol)
    
    def build_system_prompt(self, custom_prompt: Optional[str] = None) -> str:
        """构建系统提示词"""
        if custom_prompt:
            prompt = custom_prompt
        elif self.config.system_prompt_template:
            prompt = self.config.system_prompt_template
        else:
            prompt = self.DEFAULT_SYSTEM_PROMPT
        
        # 替换变量
        action_space_prompt = ActionSpace.get_action_prompt()
        prompt = prompt.format(
            scale=self.config.coordinate_scale,
            action_space=action_space_prompt,
            **self.config.extra_context
        )
        
        # 使用协议适配器适配提示词
        return self.adapter.adapt_system_prompt(prompt)
    
    def build_task_prompt(
        self,
        task: str,
        history_manager: Optional[HistoryManager] = None,
        current_observation: Optional[str] = None,
        custom_context: Optional[str] = None
    ) -> str:
        """构建任务提示词"""
        context_parts = []
        
        # 添加历史记录
        if history_manager:
            history_summary = history_manager.get_summary(self.config.max_history_entries)
            context_parts.append(history_summary)
        
        # 添加当前观察
        if current_observation:
            context_parts.append(f"当前屏幕:\n{current_observation}")
        
        # 添加自定义上下文
        if custom_context:
            context_parts.append(custom_context)
        
        context = "\n\n".join(context_parts)
        
        # 使用模板
        if self.config.task_prompt_template:
            prompt = self.config.task_prompt_template.format(
                task=task,
                context=context,
                **self.config.extra_context
            )
        else:
            prompt = self.DEFAULT_TASK_PROMPT.format(
                task=task,
                context=context
            )
        
        return prompt
    
    def build_messages(
        self,
        task: str,
        history_manager: Optional[HistoryManager] = None,
        current_screenshot: Optional[str] = None,
        current_observation: Optional[str] = None,
        custom_system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        构建完整的消息列表
        
        Returns:
            OpenAI 格式的消息列表
        """
        messages = []
        
        # 1. 系统提示词
        system_prompt = self.build_system_prompt(custom_system_prompt)
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 2. 历史记录（转换为消息格式）
        if history_manager:
            history_messages = self._build_history_messages(history_manager)
            messages.extend(history_messages)
        
        # 3. 当前状态
        task_prompt = self.build_task_prompt(
            task=task,
            history_manager=None,  # 已经单独处理
            current_observation=current_observation
        )
        
        # 如果有截图，使用多模态格式
        if current_screenshot and self.config.include_screenshots:
            content = [
                {"type": "text", "text": task_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{current_screenshot}"
                    }
                }
            ]
            messages.append({
                "role": "user",
                "content": content
            })
        else:
            messages.append({
                "role": "user",
                "content": task_prompt
            })
        
        return messages
    
    def _build_history_messages(
        self,
        history_manager: HistoryManager
    ) -> List[Dict[str, Any]]:
        """将历史记录转换为消息格式"""
        messages = []
        entries = history_manager.get_recent(self.config.max_history_entries)
        
        for entry in entries:
            # 动作作为 assistant 消息
            action_desc = entry.action.get_description()
            action_msg = {
                "role": "assistant",
                "content": f"执行: {action_desc}"
            }
            messages.append(action_msg)
            
            # 观察结果作为 user 消息
            if self.config.include_action_results and entry.observation:
                obs_msg = {
                    "role": "user",
                    "content": f"结果: {entry.observation}"
                }
                messages.append(obs_msg)
        
        return messages
    
    def build_compact_context(
        self,
        task: str,
        history_manager: HistoryManager,
        current_observation: Optional[str] = None
    ) -> str:
        """
        构建紧凑的上下文（用于非多模态模型）
        
        将历史记录和当前状态压缩为文本描述
        """
        parts = []
        
        # 任务
        parts.append(f"任务: {task}")
        
        # 历史记录（紧凑格式）
        if history_manager:
            history_text = history_manager.get_formatted_history(
                format_type="compact",
                max_entries=self.config.max_history_entries
            )
            parts.append(f"历史: {history_text}")
        
        # 当前观察
        if current_observation:
            parts.append(f"当前: {current_observation}")
        
        return "\n".join(parts)
    
    def adapt_messages_for_model(
        self,
        messages: List[Dict[str, Any]],
        model_config: ModelConfig
    ) -> List[Dict[str, Any]]:
        """
        根据模型配置调整消息格式
        
        不同模型可能有不同的消息格式要求
        """
        adapted_messages = []
        
        for msg in messages:
            adapted_msg = msg.copy()
            
            # 处理多模态内容
            if isinstance(msg.get("content"), list):
                # 检查模型是否支持视觉
                if not model_config.capabilities.supports_vision:
                    # 提取文本部分
                    text_parts = []
                    for item in msg["content"]:
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    adapted_msg["content"] = "\n".join(text_parts)
            
            adapted_messages.append(adapted_msg)
        
        return adapted_messages
    
    def with_protocol(self, protocol: ProtocolType) -> 'ContextBuilder':
        """创建使用不同协议的新构建器"""
        return ContextBuilder(
            config=self.config,
            protocol=protocol
        )
    
    def with_config(self, config: ContextConfig) -> 'ContextBuilder':
        """创建使用不同配置的新构建器"""
        return ContextBuilder(
            config=config,
            protocol=self.protocol
        )


class MultiTurnContextBuilder(ContextBuilder):
    """多轮对话上下文构建器"""
    
    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        protocol: ProtocolType = ProtocolType.UNIVERSAL,
        max_turns: int = 20
    ):
        super().__init__(config, protocol)
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []
    
    def add_turn(
        self,
        user_input: str,
        assistant_response: str,
        screenshot: Optional[str] = None
    ) -> None:
        """添加一轮对话"""
        turn = {
            "user": user_input,
            "assistant": assistant_response,
            "screenshot": screenshot,
        }
        self.turns.append(turn)
        
        # 限制轮数
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)
    
    def build_messages(
        self,
        task: str,
        history_manager: Optional[HistoryManager] = None,
        current_screenshot: Optional[str] = None,
        current_observation: Optional[str] = None,
        custom_system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """构建包含多轮对话的消息列表"""
        messages = super().build_messages(
            task=task,
            history_manager=history_manager,
            current_screenshot=current_screenshot,
            current_observation=current_observation,
            custom_system_prompt=custom_system_prompt
        )
        
        # 添加历史对话轮次
        for turn in self.turns:
            # 用户输入
            if turn.get("screenshot") and self.config.include_screenshots:
                user_content = [
                    {"type": "text", "text": turn["user"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{turn['screenshot']}"
                        }
                    }
                ]
            else:
                user_content = turn["user"]
            
            messages.append({"role": "user", "content": user_content})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        
        return messages
    
    def clear_turns(self) -> None:
        """清空对话历史"""
        self.turns.clear()


# 便捷函数
def create_context_builder(
    protocol: ProtocolType = ProtocolType.UNIVERSAL,
    **kwargs
) -> ContextBuilder:
    """创建上下文构建器的便捷函数"""
    config = ContextConfig(**kwargs)
    return ContextBuilder(config=config, protocol=protocol)


def build_simple_context(
    task: str,
    history_manager: Optional[HistoryManager] = None,
    screenshot: Optional[str] = None
) -> List[Dict[str, Any]]:
    """快速构建简单上下文的便捷函数"""
    builder = create_context_builder()
    return builder.build_messages(
        task=task,
        history_manager=history_manager,
        current_screenshot=screenshot
    )
