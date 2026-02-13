import asyncio
import subprocess
import base64
from typing import Optional, Dict, Any, List, Tuple
from xml.etree import ElementTree as ET

from app.drivers.base import (
    BaseDriver, ActionResult, Element, ElementLocatorType, ActionType, Point
)


class AndroidDriver(BaseDriver):
    def __init__(self, device_id: str, capabilities: Optional[Dict[str, Any]] = None):
        super().__init__(device_id, capabilities)
        self._adb_path = "adb"
        self._ui_xml_cache = None
    
    @property
    def platform(self) -> str:
        return "android"
    
    async def _run_adb_command(self, *args, timeout: int = 30) -> str:
        cmd = [self._adb_path, "-s", self.device_id] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"ADB command failed: {stderr.decode()}")
        return stdout.decode().strip()
    
    async def connect(self) -> bool:
        try:
            result = await self._run_adb_command("get-state")
            if result == "device":
                self._connected = True
                return True
            return False
        except Exception:
            return False
    
    async def disconnect(self) -> None:
        self._connected = False
        self._ui_xml_cache = None
    
    async def get_screen_size(self) -> Tuple[int, int]:
        output = await self._run_adb_command("shell", "wm", "size")
        size_str = output.split(":")[-1].strip()
        width, height = map(int, size_str.split("x"))
        return width, height
    
    async def screenshot(self) -> bytes:
        result = await self._run_adb_command("exec-out", "screencap", "-p")
        return result.encode() if isinstance(result, str) else result
    
    async def click(self, x: int, y: int) -> ActionResult:
        try:
            await self._run_adb_command("shell", "input", "tap", str(x), str(y))
            return ActionResult(success=True, message=f"Clicked at ({x}, {y})")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def swipe(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int, 
        duration: int = 300
    ) -> ActionResult:
        try:
            await self._run_adb_command(
                "shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y), str(duration)
            )
            return ActionResult(success=True, message=f"Swiped from ({start_x},{start_y}) to ({end_x},{end_y})")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def input_text(self, text: str) -> ActionResult:
        try:
            await self._run_adb_command("shell", "input", "text", text.replace(" ", "%s"))
            return ActionResult(success=True, message=f"Input text: {text}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def press_key(self, key: str) -> ActionResult:
        key_map = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK",
            "enter": "KEYCODE_ENTER",
            "delete": "KEYCODE_DEL",
            "volume_up": "KEYCODE_VOLUME_UP",
            "volume_down": "KEYCODE_VOLUME_DOWN",
            "power": "KEYCODE_POWER",
        }
        key_code = key_map.get(key.lower(), key.upper())
        try:
            await self._run_adb_command("shell", "input", "keyevent", key_code)
            return ActionResult(success=True, message=f"Pressed key: {key}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def wait(self, seconds: float) -> ActionResult:
        await asyncio.sleep(seconds)
        return ActionResult(success=True, message=f"Waited {seconds}s")
    
    async def launch_app(self, package_name: str) -> ActionResult:
        try:
            await self._run_adb_command("shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            return ActionResult(success=True, message=f"Launched app: {package_name}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def stop_app(self, package_name: str) -> ActionResult:
        try:
            await self._run_adb_command("shell", "am", "force-stop", package_name)
            return ActionResult(success=True, message=f"Stopped app: {package_name}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def find_element(
        self, 
        locator_type: ElementLocatorType, 
        value: str,
        timeout: float = 10
    ) -> Optional[Element]:
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            elements = await self.find_elements(locator_type, value)
            if elements:
                return elements[0]
            await asyncio.sleep(0.5)
        
        return None
    
    async def find_elements(
        self, 
        locator_type: ElementLocatorType, 
        value: str
    ) -> List[Element]:
        tree = await self._get_ui_tree()
        if tree is None:
            return []
        
        elements = []
        
        for node in tree.iter():
            if self._matches_locator(node, locator_type, value):
                bounds = node.get("bounds", "")
                bounds_tuple = self._parse_bounds(bounds)
                element = Element(
                    locator_type=locator_type,
                    value=value,
                    bounds=bounds_tuple,
                    text=node.get("text", ""),
                    enabled=node.get("enabled", "true") == "true",
                    selected=node.get("selected", "false") == "true"
                )
                elements.append(element)
        
        return elements
    
    async def _get_ui_tree(self) -> Optional[ET.Element]:
        try:
            result = await self._run_adb_command("shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
            result = await self._run_adb_command("pull", "/sdcard/window_dump.xml", "-")
            if result:
                return ET.fromstring(result)
        except Exception:
            pass
        return None
    
    def _matches_locator(self, node: ET.Element, locator_type: ElementLocatorType, value: str) -> bool:
        if locator_type == ElementLocatorType.TEXT:
            return node.get("text", "").lower() == value.lower()
        elif locator_type == ElementLocatorType.ID:
            return node.get("resource-id", "").endswith(value)
        elif locator_type == ElementLocatorType.CLASS_NAME:
            return node.get("class", "").endswith(value)
        elif locator_type == ElementLocatorType.DESCRIPTION:
            return node.get("content-desc", "").lower() == value.lower()
        return False
    
    def _parse_bounds(self, bounds: str) -> Optional[Tuple[int, int, int, int]]:
        if not bounds:
            return None
        try:
            coords = bounds.replace("[", "").replace("]", ",").split(",")
            return (int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))
        except:
            return None
    
    async def get_current_activity(self) -> Optional[str]:
        try:
            result = await self._run_adb_command("shell", "dumpsys", "window", "|", "grep", "mCurrentFocus")
            if "Activity" in result:
                return result.split("Activity")[1].split("{")[0].strip()
        except:
            pass
        return None
    
    async def get_element_tree(self) -> Dict[str, Any]:
        tree = await self._get_ui_tree()
        if tree is None:
            return {}
        
        def element_to_dict(element: ET.Element) -> Dict[str, Any]:
            return {
                "class": element.get("class", ""),
                "text": element.get("text", ""),
                "resource_id": element.get("resource-id", ""),
                "content_desc": element.get("content-desc", ""),
                "bounds": element.get("bounds", ""),
                "enabled": element.get("enabled", "true") == "true",
                "children": [element_to_dict(child) for child in element]
            }
        
        return element_to_dict(tree)
