"""
协议适配器模块
支持 AutoGLM/Gelab/Universal 三种协议的自动适配
处理坐标转换、动作格式化、提示词适配等
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
import json
import re

from .config import ProtocolType, ProtocolConfig, get_config_manager


@dataclass
class AdaptedAction:
    """适配后的动作"""
    action_type: str
    params: Dict[str, Any]
    raw_output: str
    confidence: float = 1.0
    reasoning: str = ""


@dataclass
class AdaptedMessage:
    """适配后的消息"""
    role: str
    content: Union[str, List[Dict]]
    protocol: ProtocolType
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProtocolAdapter(ABC):
    """协议适配器基类"""
    
    def __init__(self, config: ProtocolConfig):
        self.config = config
    
    @abstractmethod
    def adapt_coordinates(self, x: float, y: float, from_scale: int = 1000) -> Tuple[int, int]:
        """坐标转换"""
        pass
    
    @abstractmethod
    def format_action(self, action_type: str, params: Dict[str, Any]) -> str:
        """格式化动作为协议特定格式"""
        pass
    
    @abstractmethod
    def parse_action(self, raw_output: str) -> Optional[AdaptedAction]:
        """解析模型输出为统一动作格式"""
        pass
    
    @abstractmethod
    def adapt_system_prompt(self, base_prompt: str) -> str:
        """适配系统提示词"""
        pass
    
    @abstractmethod
    def adapt_message(self, message: Dict[str, Any]) -> AdaptedMessage:
        """适配消息格式"""
        pass
    
    def scale_coordinates(self, x: float, y: float, from_scale: int, to_scale: int) -> Tuple[int, int]:
        """通用坐标缩放方法"""
        if from_scale == to_scale:
            return int(x), int(y)
        
        # 先归一化到 0-1，再缩放到目标范围
        x_norm = x / from_scale
        y_norm = y / from_scale
        
        x_scaled = int(x_norm * to_scale)
        y_scaled = int(y_norm * to_scale)
        
        # 确保在有效范围内
        x_scaled = max(0, min(x_scaled, to_scale))
        y_scaled = max(0, min(y_scaled, to_scale))
        
        return x_scaled, y_scaled


class UniversalAdapter(ProtocolAdapter):
    """通用协议适配器"""
    
    def adapt_coordinates(self, x: float, y: float, from_scale: int = 1000) -> Tuple[int, int]:
        """通用协议使用 0-1000 坐标系"""
        return self.scale_coordinates(x, y, from_scale, self.config.coordinate_scale)
    
    def format_action(self, action_type: str, params: Dict[str, Any]) -> str:
        """格式化为 JSON 格式"""
        action = {
            "action": action_type,
            "params": params
        }
        return json.dumps(action, ensure_ascii=False)
    
    def parse_action(self, raw_output: str) -> Optional[AdaptedAction]:
        """解析 JSON 格式的动作"""
        try:
            # 尝试直接解析 JSON
            data = json.loads(raw_output)
            if isinstance(data, dict):
                action_type = data.get("action", "")
                params = data.get("params", {})
                return AdaptedAction(
                    action_type=action_type,
                    params=params,
                    raw_output=raw_output,
                    reasoning=data.get("reasoning", "")
                )
        except json.JSONDecodeError:
            pass
        
        # 尝试从文本中提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', raw_output)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return AdaptedAction(
                    action_type=data.get("action", ""),
                    params=data.get("params", {}),
                    raw_output=raw_output,
                    reasoning=data.get("reasoning", "")
                )
            except json.JSONDecodeError:
                pass
        
        return None
    
    def adapt_system_prompt(self, base_prompt: str) -> str:
        """通用协议使用标准提示词"""
        action_format = """
请按照以下 JSON 格式返回动作：
{
    "action": "动作类型",
    "params": {
        // 动作参数
    },
    "reasoning": "思考过程（可选）"
}

支持的动作类型：
- click: 点击，参数 { "x": 坐标x, "y": 坐标y }
- long_click: 长按，参数 { "x": 坐标x, "y": 坐标y, "duration": 持续时间(毫秒) }
- swipe: 滑动，参数 { "x1": 起点x, "y1": 起点y, "x2": 终点x, "y2": 终点y, "duration": 持续时间 }
- type: 输入文字，参数 { "text": "要输入的文字" }
- back: 返回，无参数
- home: 回到主页，无参数
- recent: 显示最近任务，无参数
- wait: 等待，参数 { "duration": 等待时间(毫秒) }
- finish: 任务完成，参数 { "status": "success/failed", "message": "结果信息" }
"""
        return base_prompt + "\n" + action_format
    
    def adapt_message(self, message: Dict[str, Any]) -> AdaptedMessage:
        """通用协议保持消息原样"""
        return AdaptedMessage(
            role=message.get("role", "user"),
            content=message.get("content", ""),
            protocol=ProtocolType.UNIVERSAL
        )


class AutoGLMAdapter(ProtocolAdapter):
    """AutoGLM 协议适配器"""
    
    def adapt_coordinates(self, x: float, y: float, from_scale: int = 1000) -> Tuple[int, int]:
        """AutoGLM 使用 0-999 坐标系"""
        return self.scale_coordinates(x, y, from_scale, self.config.coordinate_scale)
    
    def format_action(self, action_type: str, params: Dict[str, Any]) -> str:
        """格式化为 AutoGLM 格式"""
        # AutoGLM 使用特定的动作格式
        if action_type == "click":
            x, y = params.get("x", 0), params.get("y", 0)
            return f"click(x={x}, y={y})"
        elif action_type == "long_click":
            x, y = params.get("x", 0), params.get("y", 0)
            duration = params.get("duration", 1000)
            return f"long_click(x={x}, y={y}, duration={duration})"
        elif action_type == "swipe":
            x1, y1 = params.get("x1", 0), params.get("y1", 0)
            x2, y2 = params.get("x2", 0), params.get("y2", 0)
            return f"swipe(x1={x1}, y1={y1}, x2={x2}, y2={y2})"
        elif action_type == "type":
            text = params.get("text", "")
            return f'type(text="{text}")'
        elif action_type == "back":
            return "back()"
        elif action_type == "home":
            return "home()"
        elif action_type == "recent":
            return "recent()"
        elif action_type == "wait":
            duration = params.get("duration", 1000)
            return f"wait(duration={duration})"
        elif action_type == "finish":
            status = params.get("status", "success")
            return f"finish(status={status})"
        else:
            return json.dumps({"action": action_type, "params": params})
    
    def parse_action(self, raw_output: str) -> Optional[AdaptedAction]:
        """解析 AutoGLM 格式的动作"""
        # 匹配 AutoGLM 格式: action_name(param1=value1, param2=value2)
        pattern = r'(\w+)\(([^)]*)\)'
        match = re.match(pattern, raw_output.strip())
        
        if match:
            action_type = match.group(1)
            params_str = match.group(2)
            
            # 解析参数
            params = {}
            if params_str:
                # 匹配 key=value 或 key="value"
                param_pattern = r'(\w+)=(?:"([^"]*)"|([^,\s]*))'
                for param_match in re.finditer(param_pattern, params_str):
                    key = param_match.group(1)
                    value = param_match.group(2) if param_match.group(2) else param_match.group(3)
                    # 尝试转换为数字
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass
                    params[key] = value
            
            return AdaptedAction(
                action_type=action_type,
                params=params,
                raw_output=raw_output
            )
        
        # 尝试解析 JSON 格式作为备选
        try:
            data = json.loads(raw_output)
            if isinstance(data, dict):
                return AdaptedAction(
                    action_type=data.get("action", ""),
                    params=data.get("params", {}),
                    raw_output=raw_output,
                    reasoning=data.get("reasoning", "")
                )
        except json.JSONDecodeError:
            pass
        
        return None
    
    def adapt_system_prompt(self, base_prompt: str) -> str:
        """AutoGLM 特定提示词"""
        action_format = """
请按照以下格式返回动作（使用 0-999 坐标系）：
动作格式: action_name(param1=value1, param2=value2)

支持的动作：
- click(x=500, y=500) - 点击指定坐标
- long_click(x=500, y=500, duration=1000) - 长按
- swipe(x1=500, y1=800, x2=500, y2=200) - 滑动
- type(text="要输入的文字") - 输入文字
- back() - 返回
- home() - 回到主页
- recent() - 显示最近任务
- wait(duration=1000) - 等待
- finish(status=success) - 任务完成
"""
        return base_prompt + "\n" + action_format
    
    def adapt_message(self, message: Dict[str, Any]) -> AdaptedMessage:
        """AutoGLM 消息适配"""
        return AdaptedMessage(
            role=message.get("role", "user"),
            content=message.get("content", ""),
            protocol=ProtocolType.AUTOGML
        )


class GelabAdapter(ProtocolAdapter):
    """Gelab 协议适配器"""
    
    def adapt_coordinates(self, x: float, y: float, from_scale: int = 1000) -> Tuple[int, int]:
        """Gelab 使用 0-1000 坐标系"""
        return self.scale_coordinates(x, y, from_scale, self.config.coordinate_scale)
    
    def format_action(self, action_type: str, params: Dict[str, Any]) -> str:
        """格式化为 Gelab XML 格式"""
        xml_parts = [f'<action type="{action_type}">']
        
        for key, value in params.items():
            if isinstance(value, (int, float)):
                xml_parts.append(f'  <{key}>{value}</{key}>')
            else:
                xml_parts.append(f'  <{key}>{str(value)}</{key}>')
        
        xml_parts.append('</action>')
        return '\n'.join(xml_parts)
    
    def parse_action(self, raw_output: str) -> Optional[AdaptedAction]:
        """解析 Gelab XML 格式的动作"""
        # 匹配 XML 格式
        pattern = r'<action\s+type="(\w+)"[^>]*>(.*?)</action>'
        match = re.search(pattern, raw_output, re.DOTALL)
        
        if match:
            action_type = match.group(1)
            content = match.group(2)
            
            # 解析 XML 参数
            params = {}
            param_pattern = r'<(\w+)>([^<]*)</\1>'
            for param_match in re.finditer(param_pattern, content):
                key = param_match.group(1)
                value = param_match.group(2)
                # 尝试转换为数字
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
                params[key] = value
            
            return AdaptedAction(
                action_type=action_type,
                params=params,
                raw_output=raw_output
            )
        
        # 尝试解析 JSON 作为备选
        try:
            data = json.loads(raw_output)
            if isinstance(data, dict):
                return AdaptedAction(
                    action_type=data.get("action", ""),
                    params=data.get("params", {}),
                    raw_output=raw_output
                )
        except json.JSONDecodeError:
            pass
        
        return None
    
    def adapt_system_prompt(self, base_prompt: str) -> str:
        """Gelab 特定提示词"""
        action_format = """
请按照以下 XML 格式返回动作（使用 0-1000 坐标系）：
<action type="动作类型">
  <param1>value1</param1>
  <param2>value2</param2>
</action>

支持的动作类型：
- click: <action type="click"><x>500</x><y>500</y></action>
- long_click: <action type="long_click"><x>500</x><y>500</y><duration>1000</duration></action>
- swipe: <action type="swipe"><x1>500</x1><y1>800</y1><x2>500</x2><y2>200</y2></action>
- type: <action type="type"><text>要输入的文字</text></action>
- back: <action type="back"></action>
- home: <action type="home"></action>
- finish: <action type="finish"><status>success</status></action>
"""
        return base_prompt + "\n" + action_format
    
    def adapt_message(self, message: Dict[str, Any]) -> AdaptedMessage:
        """Gelab 消息适配"""
        return AdaptedMessage(
            role=message.get("role", "user"),
            content=message.get("content", ""),
            protocol=ProtocolType.GELAB
        )


class AdapterFactory:
    """适配器工厂"""
    
    _adapters: Dict[ProtocolType, type] = {
        ProtocolType.UNIVERSAL: UniversalAdapter,
        ProtocolType.AUTOGML: AutoGLMAdapter,
        ProtocolType.GELAB: GelabAdapter,
    }
    
    @classmethod
    def get_adapter(cls, protocol: ProtocolType, config: Optional[ProtocolConfig] = None) -> ProtocolAdapter:
        """获取适配器实例"""
        if config is None:
            config = get_config_manager().get_protocol_config(protocol)
        
        adapter_class = cls._adapters.get(protocol, UniversalAdapter)
        return adapter_class(config)
    
    @classmethod
    def register_adapter(cls, protocol: ProtocolType, adapter_class: type):
        """注册自定义适配器"""
        cls._adapters[protocol] = adapter_class
    
    @classmethod
    def detect_and_get_adapter(cls, model_name: str) -> ProtocolAdapter:
        """根据模型名称自动检测并获取适配器"""
        protocol = get_config_manager().detect_protocol(model_name)
        return cls.get_adapter(protocol)


# 便捷函数
def get_adapter(protocol: Union[ProtocolType, str]) -> ProtocolAdapter:
    """获取适配器的便捷函数"""
    if isinstance(protocol, str):
        protocol = ProtocolType(protocol)
    return AdapterFactory.get_adapter(protocol)


def adapt_coordinates(x: float, y: float, protocol: ProtocolType, from_scale: int = 1000) -> Tuple[int, int]:
    """坐标适配便捷函数"""
    adapter = get_adapter(protocol)
    return adapter.adapt_coordinates(x, y, from_scale)


def parse_action(raw_output: str, protocol: ProtocolType) -> Optional[AdaptedAction]:
    """动作解析便捷函数"""
    adapter = get_adapter(protocol)
    return adapter.parse_action(raw_output)
