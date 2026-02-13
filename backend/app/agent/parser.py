import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.drivers.base import ActionType, ElementLocatorType


@dataclass
class ParsedAction:
    action_type: ActionType
    target: Optional[str] = None
    params: Dict[str, Any] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.action_type.value}
        if self.target:
            result["target"] = self.target
        if self.params:
            result.update(self.params)
        if self.description:
            result["description"] = self.description
        return result


class NaturalLanguageParser:
    ACTION_PATTERNS = {
        "click": [
            r"(?:点击|点一下|tap|click)\s*(?:在|于)?\s*(.+?)(?:\s+按钮|\s+元素)?$",
            r"(?:点击|点一下)\s+(?:那个|这个)?\s*(.+?)(?:\s+上|\s+键)?$",
        ],
        "input": [
            r"(?:输入|打字|填写|type|input)\s+(.+?)\s*(?:到|在|into)\s*(.+?)$",
            r"(?:输入|填写)\s*(.+?)$",
        ],
        "swipe": [
            r"(?:向上|向下滑动|滑动|swipe)\s*(?:一下|一点)?\s*(?:屏幕)?\s*(?:一点)?$",
            r"(?:向左|向右)滑动\s*(?:一下)?$",
            r"从\s*(.+?)\s*滑动到\s*(.+?)$",
        ],
        "press": [
            r"(?:按|按下|press)\s*(返回|home|电源|音量)\s*(?:键|按钮)?$",
        ],
        "wait": [
            r"(?:等待|等)\s*(\d+)\s*(?:秒|秒钟)?$",
        ],
        "launch_app": [
            r"(?:打开|启动|launch)\s*(.+?)(?:\s+应用|\s+APP)?$",
        ],
        "stop_app": [
            r"(?:关闭|停止|stop)\s*(.+?)(?:\s+应用|\s+APP)?$",
        ],
        "screenshot": [
            r"(?:截屏|截图|screenshot|capture)$",
        ],
    }

    def __init__(self, llm=None):
        self.llm = llm

    def parse(self, natural_language: str) -> List[ParsedAction]:
        natural_language = natural_language.strip()
        actions = []

        for action_type, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, natural_language, re.IGNORECASE)
                if match:
                    action = self._create_action(action_type, match.groups())
                    if action:
                        actions.append(action)
                    break

        if not actions and self.llm:
            actions = self._parse_with_llm(natural_language)

        return actions

    def _create_action(self, action_type: str, groups: tuple) -> Optional[ParsedAction]:
        if action_type == "click":
            return ParsedAction(
                action_type=ActionType.CLICK,
                target=groups[0] if groups else None,
                description=f"Click on {groups[0] if groups else 'element'}"
            )

        elif action_type == "input":
            text = groups[0] if groups else ""
            target = groups[1] if len(groups) > 1 else None
            return ParsedAction(
                action_type=ActionType.INPUT,
                target=target,
                params={"text": text},
                description=f"Input '{text}'"
            )

        elif action_type == "swipe":
            direction = "down"
            if groups and any(word in str(groups[0]) for word in ["上", "up"]):
                direction = "up"
            elif groups and any(word in str(groups[0]) for word in ["下", "down"]):
                direction = "down"
            elif groups and any(word in str(groups[0]) for word in ["左", "left"]):
                direction = "left"
            elif groups and any(word in str(groups[0]) for word in ["右", "right"]):
                direction = "right"

            return ParsedAction(
                action_type=ActionType.SWIPE,
                params={"direction": direction},
                description=f"Swipe {direction}"
            )

        elif action_type == "press":
            key = groups[0] if groups else "back"
            return ParsedAction(
                action_type=ActionType.PRESS,
                target=key,
                description=f"Press {key}"
            )

        elif action_type == "wait":
            seconds = float(groups[0]) if groups else 1.0
            return ParsedAction(
                action_type=ActionType.WAIT,
                params={"seconds": seconds},
                description=f"Wait {seconds} seconds"
            )

        elif action_type == "launch_app":
            app_name = groups[0] if groups else ""
            return ParsedAction(
                action_type=ActionType.LAUNCH_APP,
                target=app_name,
                params={"package_name": app_name},
                description=f"Launch {app_name}"
            )

        elif action_type == "stop_app":
            app_name = groups[0] if groups else ""
            return ParsedAction(
                action_type=ActionType.STOP_APP,
                target=app_name,
                params={"package_name": app_name},
                description=f"Stop {app_name}"
            )

        elif action_type == "screenshot":
            return ParsedAction(
                action_type=ActionType.SCREENSHOT,
                description="Take screenshot"
            )

        return None

    async def _parse_with_llm(self, natural_language: str) -> List[ParsedAction]:
        if not self.llm:
            return []

        prompt = f"""请将以下自然语言指令解析为移动UI自动化动作。
可用动作类型: click, input, swipe, press, wait, launch_app, stop_app, screenshot

动作参数格式:
- click: {{"x": int, "y": int}} 或 {{"locator": {{"type": "text|id|xpath", "value": str}}}}
- input: {{"text": str, "locator": {{...}}}}
- swipe: {{"direction": "up|down|left|right"}}
- press: {{"key": "home|back|enter"}}
- wait: {{"seconds": float}}
- launch_app: {{"package_name": str}}
- stop_app: {{"package_name": str}}

请以JSON数组格式返回动作列表。

用户指令: {natural_language}"""

        from app.agent.llm.llm import Message
        messages = [Message(role="user", content=prompt)]

        try:
            response = await self.llm.chat(messages)
            import json
            actions_data = json.loads(response.content)

            actions = []
            for action_data in actions_data:
                action_type = ActionType(action_data.get("type", ""))
                params = action_data.get("params", {})
                actions.append(ParsedAction(
                    action_type=action_type,
                    target=action_data.get("target"),
                    params=params,
                    description=action_data.get("description", "")
                ))

            return actions
        except Exception:
            return []

    def parse_test_case(self, content: str) -> List[Dict[str, Any]]:
        steps = []
        lines = content.split("\n")

        current_action = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.")):
                line = re.sub(r"^\d+\.\s*", "", line)

            actions = self.parse(line)
            for action in actions:
                steps.append(action.to_dict())

        return steps
