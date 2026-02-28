"""
动作执行器
将 Action 转换为设备操作
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import logging

from .space import Action, ActionType, ActionSpace

logger = logging.getLogger(__name__)


class ActionResult:
    """动作执行结果"""
    
    def __init__(
        self,
        success: bool,
        message: str = "",
        data: Dict[str, Any] = None,
        screenshot: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.message = message
        self.data = data or {}
        self.screenshot = screenshot
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }
    
    @classmethod
    def success_result(cls, message: str = "", data: Dict[str, Any] = None, screenshot: Optional[str] = None):
        return cls(True, message, data, screenshot)
    
    @classmethod
    def failure_result(cls, error: str, message: str = ""):
        return cls(False, message, error=error)


class ActionExecutor(ABC):
    """动作执行器基类"""
    
    def __init__(self):
        self._handlers: Dict[ActionType, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认动作处理器"""
        self._handlers = {
            ActionType.CLICK: self._handle_click,
            ActionType.LONG_CLICK: self._handle_long_click,
            ActionType.DOUBLE_CLICK: self._handle_double_click,
            ActionType.SWIPE: self._handle_swipe,
            ActionType.SCROLL_UP: self._handle_scroll_up,
            ActionType.SCROLL_DOWN: self._handle_scroll_down,
            ActionType.SCROLL_LEFT: self._handle_scroll_left,
            ActionType.SCROLL_RIGHT: self._handle_scroll_right,
            ActionType.TYPE: self._handle_type,
            ActionType.CLEAR: self._handle_clear,
            ActionType.BACK: self._handle_back,
            ActionType.HOME: self._handle_home,
            ActionType.RECENT: self._handle_recent,
            ActionType.WAIT: self._handle_wait,
            ActionType.FINISH: self._handle_finish,
            ActionType.FAIL: self._handle_fail,
            ActionType.LAUNCH_APP: self._handle_launch_app,
            ActionType.PRESS_KEY: self._handle_press_key,
            ActionType.SCREENSHOT: self._handle_screenshot,
            ActionType.THINK: self._handle_think,
            ActionType.PLAN: self._handle_plan,
        }
    
    def execute(self, action: Action) -> ActionResult:
        """执行动作"""
        # 首先验证动作
        valid, errors = ActionSpace.validate_action(action)
        if not valid:
            return ActionResult.failure_result(
                error=f"动作验证失败: {'; '.join(errors)}"
            )
        
        # 获取处理器
        handler = self._handlers.get(action.action_type)
        if not handler:
            return ActionResult.failure_result(
                error=f"未找到动作处理器: {action.action_type.value}"
            )
        
        # 执行动作
        try:
            logger.info(f"执行动作: {action.action_type.value}, 参数: {action.params}")
            result = handler(action.params)
            
            # 如果返回的是 ActionResult，直接使用
            if isinstance(result, ActionResult):
                return result
            
            # 否则包装为成功结果
            return ActionResult.success_result(
                message=f"动作 {action.action_type.value} 执行成功",
                data={"result": result}
            )
        except Exception as e:
            logger.error(f"动作执行失败: {e}", exc_info=True)
            return ActionResult.failure_result(
                error=str(e),
                message=f"动作 {action.action_type.value} 执行失败"
            )
    
    def register_handler(self, action_type: ActionType, handler: Callable):
        """注册自定义处理器"""
        self._handlers[action_type] = handler
    
    # ========== 抽象方法 - 子类必须实现 ==========
    
    @abstractmethod
    def _handle_click(self, params: Dict[str, Any]) -> ActionResult:
        """处理点击"""
        pass
    
    @abstractmethod
    def _handle_long_click(self, params: Dict[str, Any]) -> ActionResult:
        """处理长按"""
        pass
    
    @abstractmethod
    def _handle_double_click(self, params: Dict[str, Any]) -> ActionResult:
        """处理双击"""
        pass
    
    @abstractmethod
    def _handle_swipe(self, params: Dict[str, Any]) -> ActionResult:
        """处理滑动"""
        pass
    
    @abstractmethod
    def _handle_scroll_up(self, params: Dict[str, Any]) -> ActionResult:
        """处理向上滚动"""
        pass
    
    @abstractmethod
    def _handle_scroll_down(self, params: Dict[str, Any]) -> ActionResult:
        """处理向下滚动"""
        pass
    
    @abstractmethod
    def _handle_scroll_left(self, params: Dict[str, Any]) -> ActionResult:
        """处理向左滚动"""
        pass
    
    @abstractmethod
    def _handle_scroll_right(self, params: Dict[str, Any]) -> ActionResult:
        """处理向右滚动"""
        pass
    
    @abstractmethod
    def _handle_type(self, params: Dict[str, Any]) -> ActionResult:
        """处理输入文字"""
        pass
    
    @abstractmethod
    def _handle_clear(self, params: Dict[str, Any]) -> ActionResult:
        """处理清空输入"""
        pass
    
    @abstractmethod
    def _handle_back(self, params: Dict[str, Any]) -> ActionResult:
        """处理返回"""
        pass
    
    @abstractmethod
    def _handle_home(self, params: Dict[str, Any]) -> ActionResult:
        """处理主页"""
        pass
    
    @abstractmethod
    def _handle_recent(self, params: Dict[str, Any]) -> ActionResult:
        """处理最近任务"""
        pass
    
    @abstractmethod
    def _handle_wait(self, params: Dict[str, Any]) -> ActionResult:
        """处理等待"""
        pass
    
    @abstractmethod
    def _handle_finish(self, params: Dict[str, Any]) -> ActionResult:
        """处理完成"""
        pass
    
    @abstractmethod
    def _handle_fail(self, params: Dict[str, Any]) -> ActionResult:
        """处理失败"""
        pass
    
    @abstractmethod
    def _handle_launch_app(self, params: Dict[str, Any]) -> ActionResult:
        """处理启动应用"""
        pass
    
    @abstractmethod
    def _handle_press_key(self, params: Dict[str, Any]) -> ActionResult:
        """处理按键"""
        pass
    
    @abstractmethod
    def _handle_screenshot(self, params: Dict[str, Any]) -> ActionResult:
        """处理截图"""
        pass
    
    @abstractmethod
    def _handle_think(self, params: Dict[str, Any]) -> ActionResult:
        """处理思考"""
        pass
    
    @abstractmethod
    def _handle_plan(self, params: Dict[str, Any]) -> ActionResult:
        """处理计划"""
        pass


class MockActionExecutor(ActionExecutor):
    """模拟动作执行器（用于测试）"""
    
    def __init__(self):
        super().__init__()
        self.executed_actions: list = []
    
    def execute(self, action: Action) -> ActionResult:
        """记录并执行动作"""
        self.executed_actions.append(action)
        return super().execute(action)
    
    def _handle_click(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"点击 ({params.get('x')}, {params.get('y')})")
    
    def _handle_long_click(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(
            f"长按 ({params.get('x')}, {params.get('y')}) {params.get('duration', 1000)}ms"
        )
    
    def _handle_double_click(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"双击 ({params.get('x')}, {params.get('y')})")
    
    def _handle_swipe(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(
            f"滑动 ({params.get('x1')}, {params.get('y1')}) -> ({params.get('x2')}, {params.get('y2')})"
        )
    
    def _handle_scroll_up(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"向上滚动 {params.get('distance', 500)}")
    
    def _handle_scroll_down(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"向下滚动 {params.get('distance', 500)}")
    
    def _handle_scroll_left(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"向左滚动 {params.get('distance', 500)}")
    
    def _handle_scroll_right(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"向右滚动 {params.get('distance', 500)}")
    
    def _handle_type(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"输入: {params.get('text', '')}")
    
    def _handle_clear(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result("清空输入")
    
    def _handle_back(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result("返回")
    
    def _handle_home(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result("回到主页")
    
    def _handle_recent(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result("显示最近任务")
    
    def _handle_wait(self, params: Dict[str, Any]) -> ActionResult:
        import time
        duration = params.get('duration', 1000)
        time.sleep(duration / 1000)
        return ActionResult.success_result(f"等待 {duration}ms")
    
    def _handle_finish(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(
            f"任务完成: {params.get('message', '')}",
            data={"status": params.get('status', 'success')}
        )
    
    def _handle_fail(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.failure_result(params.get('reason', '未知原因'))
    
    def _handle_launch_app(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"启动应用: {params.get('package_name', '')}")
    
    def _handle_press_key(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"按键: {params.get('keycode', '')}")
    
    def _handle_screenshot(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result("截图", data={"screenshot": "mock_screenshot_data"})
    
    def _handle_think(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"思考: {params.get('thought', '')}")
    
    def _handle_plan(self, params: Dict[str, Any]) -> ActionResult:
        return ActionResult.success_result(f"计划: {params.get('steps', [])}")


# 便捷函数
def execute_action(action: Action, executor: Optional[ActionExecutor] = None) -> ActionResult:
    """执行动作的便捷函数"""
    if executor is None:
        executor = MockActionExecutor()
    return executor.execute(action)
