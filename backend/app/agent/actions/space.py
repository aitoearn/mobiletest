"""
动作空间定义
定义所有支持的动作类型及其参数规范
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
import json


class ActionType(Enum):
    """动作类型枚举"""
    # 基础交互
    CLICK = "click"
    LONG_CLICK = "long_click"
    DOUBLE_CLICK = "double_click"
    
    # 滑动操作
    SWIPE = "swipe"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    SCROLL_LEFT = "scroll_left"
    SCROLL_RIGHT = "scroll_right"
    
    # 输入操作
    TYPE = "type"
    CLEAR = "clear"
    
    # 系统导航
    BACK = "back"
    HOME = "home"
    RECENT = "recent"
    
    # 等待
    WAIT = "wait"
    
    # 任务控制
    FINISH = "finish"
    FAIL = "fail"
    
    # 高级操作
    LAUNCH_APP = "launch_app"
    PRESS_KEY = "press_key"
    SCREENSHOT = "screenshot"
    
    # 思考/规划
    THINK = "think"
    PLAN = "plan"


@dataclass
class ActionParameter:
    """动作参数定义"""
    name: str
    param_type: type
    required: bool = True
    default: Any = None
    description: str = ""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """验证参数值"""
        if value is None:
            if self.required:
                return False, f"参数 '{self.name}' 是必需的"
            return True, None
        
        # 类型检查
        if not isinstance(value, self.param_type):
            try:
                value = self.param_type(value)
            except (ValueError, TypeError):
                return False, f"参数 '{self.name}' 类型错误，期望 {self.param_type.__name__}"
        
        # 范围检查
        if self.min_value is not None and value < self.min_value:
            return False, f"参数 '{self.name}' 不能小于 {self.min_value}"
        
        if self.max_value is not None and value > self.max_value:
            return False, f"参数 '{self.name}' 不能大于 {self.max_value}"
        
        return True, None


@dataclass
class ActionDefinition:
    """动作定义"""
    action_type: ActionType
    description: str
    parameters: List[ActionParameter] = field(default_factory=list)
    returns_result: bool = False
    requires_screenshot: bool = False
    
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证动作参数"""
        errors = []
        
        # 检查必需参数
        param_names = {p.name for p in self.parameters}
        for param in self.parameters:
            if param.required and param.name not in params:
                errors.append(f"缺少必需参数: {param.name}")
        
        # 验证每个参数
        for name, value in params.items():
            if name not in param_names:
                errors.append(f"未知参数: {name}")
                continue
            
            param_def = next(p for p in self.parameters if p.name == name)
            valid, error = param_def.validate(value)
            if not valid:
                errors.append(error)
        
        return len(errors) == 0, errors


@dataclass
class Action:
    """动作实例"""
    action_type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 1.0
    timestamp: Optional[float] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action": self.action_type.value,
            "params": self.params,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """从字典创建"""
        action_type = ActionType(data.get("action", "click"))
        return cls(
            action_type=action_type,
            params=data.get("params", {}),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 1.0),
            timestamp=data.get("timestamp"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Action':
        """从 JSON 字符串创建"""
        return cls.from_dict(json.loads(json_str))
    
    def get_description(self) -> str:
        """获取动作描述"""
        action_def = ActionSpace.get_definition(self.action_type)
        if not action_def:
            return f"未知动作: {self.action_type.value}"
        
        desc = action_def.description
        params_str = ", ".join([f"{k}={v}" for k, v in self.params.items()])
        return f"{desc} ({params_str})"


class ActionSpace:
    """动作空间 - 管理所有可用动作"""
    
    _definitions: Dict[ActionType, ActionDefinition] = {}
    
    @classmethod
    def initialize(cls):
        """初始化标准动作空间"""
        cls._definitions = {
            # 点击操作
            ActionType.CLICK: ActionDefinition(
                action_type=ActionType.CLICK,
                description="点击屏幕指定位置",
                parameters=[
                    ActionParameter("x", int, True, description="X坐标(0-1000)"),
                    ActionParameter("y", int, True, description="Y坐标(0-1000)"),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.LONG_CLICK: ActionDefinition(
                action_type=ActionType.LONG_CLICK,
                description="长按屏幕指定位置",
                parameters=[
                    ActionParameter("x", int, True, description="X坐标(0-1000)"),
                    ActionParameter("y", int, True, description="Y坐标(0-1000)"),
                    ActionParameter("duration", int, False, 1000, "长按持续时间(毫秒)", 100, 5000),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.DOUBLE_CLICK: ActionDefinition(
                action_type=ActionType.DOUBLE_CLICK,
                description="双击屏幕指定位置",
                parameters=[
                    ActionParameter("x", int, True, description="X坐标(0-1000)"),
                    ActionParameter("y", int, True, description="Y坐标(0-1000)"),
                ],
                requires_screenshot=True,
            ),
            
            # 滑动操作
            ActionType.SWIPE: ActionDefinition(
                action_type=ActionType.SWIPE,
                description="从一点滑动到另一点",
                parameters=[
                    ActionParameter("x1", int, True, description="起点X坐标(0-1000)"),
                    ActionParameter("y1", int, True, description="起点Y坐标(0-1000)"),
                    ActionParameter("x2", int, True, description="终点X坐标(0-1000)"),
                    ActionParameter("y2", int, True, description="终点Y坐标(0-1000)"),
                    ActionParameter("duration", int, False, 300, "滑动持续时间(毫秒)", 50, 5000),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.SCROLL_UP: ActionDefinition(
                action_type=ActionType.SCROLL_UP,
                description="向上滚动",
                parameters=[
                    ActionParameter("distance", int, False, 500, "滚动距离", 100, 2000),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.SCROLL_DOWN: ActionDefinition(
                action_type=ActionType.SCROLL_DOWN,
                description="向下滚动",
                parameters=[
                    ActionParameter("distance", int, False, 500, "滚动距离", 100, 2000),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.SCROLL_LEFT: ActionDefinition(
                action_type=ActionType.SCROLL_LEFT,
                description="向左滚动",
                parameters=[
                    ActionParameter("distance", int, False, 500, "滚动距离", 100, 2000),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.SCROLL_RIGHT: ActionDefinition(
                action_type=ActionType.SCROLL_RIGHT,
                description="向右滚动",
                parameters=[
                    ActionParameter("distance", int, False, 500, "滚动距离", 100, 2000),
                ],
                requires_screenshot=True,
            ),
            
            # 输入操作
            ActionType.TYPE: ActionDefinition(
                action_type=ActionType.TYPE,
                description="输入文字",
                parameters=[
                    ActionParameter("text", str, True, description="要输入的文字"),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.CLEAR: ActionDefinition(
                action_type=ActionType.CLEAR,
                description="清空输入框",
                parameters=[
                    ActionParameter("x", int, False, description="输入框X坐标"),
                    ActionParameter("y", int, False, description="输入框Y坐标"),
                ],
                requires_screenshot=True,
            ),
            
            # 系统导航
            ActionType.BACK: ActionDefinition(
                action_type=ActionType.BACK,
                description="返回上一页",
                parameters=[],
                requires_screenshot=True,
            ),
            
            ActionType.HOME: ActionDefinition(
                action_type=ActionType.HOME,
                description="返回主页",
                parameters=[],
                requires_screenshot=True,
            ),
            
            ActionType.RECENT: ActionDefinition(
                action_type=ActionType.RECENT,
                description="显示最近任务",
                parameters=[],
                requires_screenshot=True,
            ),
            
            # 等待
            ActionType.WAIT: ActionDefinition(
                action_type=ActionType.WAIT,
                description="等待一段时间",
                parameters=[
                    ActionParameter("duration", int, False, 1000, "等待时间(毫秒)", 0, 60000),
                ],
            ),
            
            # 任务控制
            ActionType.FINISH: ActionDefinition(
                action_type=ActionType.FINISH,
                description="任务完成",
                parameters=[
                    ActionParameter("status", str, False, "success", "完成状态: success/failed"),
                    ActionParameter("message", str, False, "", "结果信息"),
                ],
                returns_result=True,
            ),
            
            ActionType.FAIL: ActionDefinition(
                action_type=ActionType.FAIL,
                description="任务失败",
                parameters=[
                    ActionParameter("reason", str, True, description="失败原因"),
                ],
                returns_result=True,
            ),
            
            # 高级操作
            ActionType.LAUNCH_APP: ActionDefinition(
                action_type=ActionType.LAUNCH_APP,
                description="启动应用",
                parameters=[
                    ActionParameter("package_name", str, True, description="应用包名"),
                    ActionParameter("activity", str, False, "", "启动Activity"),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.PRESS_KEY: ActionDefinition(
                action_type=ActionType.PRESS_KEY,
                description="按下物理按键",
                parameters=[
                    ActionParameter("keycode", int, True, description="按键代码"),
                ],
                requires_screenshot=True,
            ),
            
            ActionType.SCREENSHOT: ActionDefinition(
                action_type=ActionType.SCREENSHOT,
                description="截图",
                parameters=[],
                returns_result=True,
            ),
            
            # 思考/规划
            ActionType.THINK: ActionDefinition(
                action_type=ActionType.THINK,
                description="思考步骤",
                parameters=[
                    ActionParameter("thought", str, True, description="思考内容"),
                ],
            ),
            
            ActionType.PLAN: ActionDefinition(
                action_type=ActionType.PLAN,
                description="制定计划",
                parameters=[
                    ActionParameter("steps", list, True, description="计划步骤列表"),
                ],
            ),
        }
    
    @classmethod
    def get_definition(cls, action_type: ActionType) -> Optional[ActionDefinition]:
        """获取动作定义"""
        return cls._definitions.get(action_type)
    
    @classmethod
    def get_all_definitions(cls) -> Dict[ActionType, ActionDefinition]:
        """获取所有动作定义"""
        return cls._definitions.copy()
    
    @classmethod
    def get_action_types(cls) -> List[ActionType]:
        """获取所有动作类型"""
        return list(cls._definitions.keys())
    
    @classmethod
    def validate_action(cls, action: Action) -> tuple[bool, List[str]]:
        """验证动作"""
        definition = cls.get_definition(action.action_type)
        if not definition:
            return False, [f"未知的动作类型: {action.action_type.value}"]
        
        return definition.validate_params(action.params)
    
    @classmethod
    def get_action_prompt(cls) -> str:
        """生成动作说明提示词"""
        lines = ["可用动作列表:"]
        
        for action_type, definition in cls._definitions.items():
            params_str = ""
            if definition.parameters:
                params = []
                for p in definition.parameters:
                    if p.required:
                        params.append(f"{p.name}: {p.param_type.__name__}")
                    else:
                        params.append(f"{p.name}?: {p.param_type.__name__} = {p.default}")
                params_str = f"({', '.join(params)})"
            
            lines.append(f"  - {action_type.value}{params_str}: {definition.description}")
        
        return "\n".join(lines)
    
    @classmethod
    def register_custom_action(cls, definition: ActionDefinition):
        """注册自定义动作"""
        cls._definitions[definition.action_type] = definition


# 初始化动作空间
ActionSpace.initialize()
