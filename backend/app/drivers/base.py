from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class ActionType(str, Enum):
    CLICK = "click"
    SWIPE = "swipe"
    INPUT = "input"
    PRESS = "press"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    LAUNCH_APP = "launch_app"
    STOP_APP = "stop_app"
    GET_ELEMENT = "get_element"
    ASSERT = "assert"


class ElementLocatorType(str, Enum):
    ID = "id"
    TEXT = "text"
    XPath = "xpath"
    ACCESSIBILITY_ID = "accessibility_id"
    CLASS_NAME = "class_name"
    DESCRIPTION = "description"


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Element:
    locator_type: ElementLocatorType
    value: str
    bounds: Optional[Tuple[int, int, int, int]] = None
    text: Optional[str] = None
    enabled: bool = True
    selected: bool = False


@dataclass
class ActionResult:
    success: bool
    message: str = ""
    screenshot: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class BaseDriver(ABC):
    def __init__(self, device_id: str, capabilities: Optional[Dict[str, Any]] = None):
        self.device_id = device_id
        self.capabilities = capabilities or {}
        self._connected = False
    
    @property
    @abstractmethod
    def platform(self) -> str:
        pass
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def get_screen_size(self) -> Tuple[int, int]:
        pass
    
    @abstractmethod
    async def screenshot(self) -> bytes:
        pass
    
    @abstractmethod
    async def click(self, x: int, y: int) -> ActionResult:
        pass
    
    @abstractmethod
    async def swipe(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int, 
        duration: int = 300
    ) -> ActionResult:
        pass
    
    @abstractmethod
    async def input_text(self, text: str) -> ActionResult:
        pass
    
    @abstractmethod
    async def press_key(self, key: str) -> ActionResult:
        pass
    
    @abstractmethod
    async def wait(self, seconds: float) -> ActionResult:
        pass
    
    @abstractmethod
    async def launch_app(self, package_name: str) -> ActionResult:
        pass
    
    @abstractmethod
    async def stop_app(self, package_name: str) -> ActionResult:
        pass
    
    @abstractmethod
    async def find_element(
        self, 
        locator_type: ElementLocatorType, 
        value: str,
        timeout: float = 10
    ) -> Optional[Element]:
        pass
    
    @abstractmethod
    async def find_elements(
        self, 
        locator_type: ElementLocatorType, 
        value: str
    ) -> List[Element]:
        pass
    
    @abstractmethod
    async def get_current_activity(self) -> Optional[str]:
        pass
    
    @abstractmethod
    async def get_element_tree(self) -> Dict[str, Any]:
        pass
    
    async def execute_action(self, action: Dict[str, Any]) -> ActionResult:
        action_type = action.get("type")
        
        try:
            if action_type == ActionType.CLICK:
                x, y = action.get("x", 0), action.get("y", 0)
                return await self.click(x, y)
            
            elif action_type == ActionType.SWIPE:
                return await self.swipe(
                    action.get("start_x", 0),
                    action.get("start_y", 0),
                    action.get("end_x", 0),
                    action.get("end_y", 0),
                    action.get("duration", 300)
                )
            
            elif action_type == ActionType.INPUT:
                return await self.input_text(action.get("text", ""))
            
            elif action_type == ActionType.PRESS:
                return await self.press_key(action.get("key", ""))
            
            elif action_type == ActionType.WAIT:
                return await self.wait(action.get("seconds", 1.0))
            
            elif action_type == ActionType.SCREENSHOT:
                await self.screenshot()
                return ActionResult(success=True, message="Screenshot captured")
            
            elif action_type == ActionType.LAUNCH_APP:
                return await self.launch_app(action.get("package_name", ""))
            
            elif action_type == ActionType.STOP_APP:
                return await self.stop_app(action.get("package_name", ""))
            
            elif action_type == ActionType.GET_ELEMENT:
                locator = action.get("locator")
                if locator:
                    element = await self.find_element(
                        locator.get("type"),
                        locator.get("value"),
                        action.get("timeout", 10)
                    )
                    if element:
                        return ActionResult(
                            success=True,
                            data={"element": {
                                "locator_type": element.locator_type,
                                "value": element.value,
                                "text": element.text,
                                "bounds": element.bounds
                            }}
                        )
                return ActionResult(success=False, message="Element not found")
            
            else:
                return ActionResult(success=False, message=f"Unknown action: {action_type}")
        
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
