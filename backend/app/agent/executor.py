import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.drivers.base import BaseDriver, ActionResult, ActionType
from app.agent.parser import ParsedAction


@dataclass
class ExecutionContext:
    device_id: str
    platform: str
    current_activity: Optional[str] = None
    variables: Dict[str, Any] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}


class ActionExecutor:
    def __init__(self, driver: BaseDriver):
        self.driver = driver

    async def execute_actions(
        self, 
        actions: List[ParsedAction],
        context: Optional[ExecutionContext] = None
    ) -> List[ActionResult]:
        if context is None:
            context = ExecutionContext(
                device_id=self.driver.device_id,
                platform=self.driver.platform
            )

        results = []
        
        for action in actions:
            result = await self._execute_single_action(action, context)
            results.append(result)
            
            if not result.success and not self._is_critical_action(action.action_type):
                break

        return results

    async def _execute_single_action(
        self, 
        action: ParsedAction, 
        context: ExecutionContext
    ) -> ActionResult:
        try:
            action_dict = self._prepare_action_dict(action, context)
            result = await self.driver.execute_action(action_dict)

            if action.action_type == ActionType.CLICK and result.success:
                context.current_activity = await self.driver.get_current_activity()

            if action.action_type == ActionType.LAUNCH_APP and result.success:
                context.current_activity = action.params.get("package_name", "")

            if action.action_type == ActionType.STOP_APP:
                context.current_activity = None

            return result

        except Exception as e:
            return ActionResult(success=False, message=str(e))

    def _prepare_action_dict(self, action: ParsedAction, context: ExecutionContext) -> Dict[str, Any]:
        action_dict = {
            "type": action.action_type.value,
            "description": action.description,
        }

        if action.action_type == ActionType.CLICK:
            target = action.target
            if target:
                if target.isdigit() or (target.replace(".", "").isdigit() and "," in target):
                    parts = target.replace(",", " ").split()
                    if len(parts) >= 2:
                        action_dict["x"] = int(parts[0])
                        action_dict["y"] = int(parts[1])
                else:
                    action_dict["locator"] = {
                        "type": "text",
                        "value": target
                    }

        elif action.action_type == ActionType.INPUT:
            if action.params and "text" in action.params:
                action_dict["text"] = action.params["text"]
            if action.target:
                action_dict["locator"] = {
                    "type": "text",
                    "value": action.target
                }

        elif action.action_type == ActionType.SWIPE:
            direction = action.params.get("direction", "down") if action.params else "down"
            screen_width, screen_height = asyncio.run(self.driver.get_screen_size())

            if direction == "up":
                action_dict.update({
                    "start_x": screen_width // 2,
                    "start_y": int(screen_height * 0.8),
                    "end_x": screen_width // 2,
                    "end_y": int(screen_height * 0.2),
                })
            elif direction == "down":
                action_dict.update({
                    "start_x": screen_width // 2,
                    "start_y": int(screen_height * 0.2),
                    "end_x": screen_width // 2,
                    "end_y": int(screen_height * 0.8),
                })
            elif direction == "left":
                action_dict.update({
                    "start_x": int(screen_width * 0.8),
                    "start_y": screen_height // 2,
                    "end_x": int(screen_width * 0.2),
                    "end_y": screen_height // 2,
                })
            elif direction == "right":
                action_dict.update({
                    "start_x": int(screen_width * 0.2),
                    "start_y": screen_height // 2,
                    "end_x": int(screen_width * 0.8),
                    "end_y": screen_height // 2,
                })

        elif action.action_type == ActionType.PRESS:
            if action.target:
                action_dict["key"] = action.target

        elif action.action_type == ActionType.WAIT:
            if action.params and "seconds" in action.params:
                action_dict["seconds"] = action.params["seconds"]

        elif action.action_type == ActionType.LAUNCH_APP:
            package_name = action.target or action.params.get("package_name", "")
            action_dict["package_name"] = package_name

        elif action.action_type == ActionType.STOP_APP:
            package_name = action.target or action.params.get("package_name", "")
            action_dict["package_name"] = package_name

        return action_dict

    def _is_critical_action(self, action_type: ActionType) -> bool:
        critical_actions = [
            ActionType.SCREENSHOT,
            ActionType.GET_ELEMENT,
            ActionType.WAIT,
        ]
        return action_type in critical_actions

    async def execute_with_vision(
        self,
        action: ParsedAction,
        screenshot: bytes,
        context: ExecutionContext
    ) -> ActionResult:
        pass
