import asyncio
import subprocess
from typing import Optional, Dict, Any, List, Tuple

from app.drivers.base import (
    BaseDriver, ActionResult, Element, ElementLocatorType, ActionType
)


class IOSDriver(BaseDriver):
    def __init__(self, device_id: str, capabilities: Optional[Dict[str, Any]] = None):
        super().__init__(device_id, capabilities)
        self._bundle_id = capabilities.get("bundleId", "") if capabilities else ""
    
    @property
    def platform(self) -> str:
        return "ios"
    
    async def _run_xcrun_command(self, *args, timeout: int = 30) -> str:
        cmd = ["xcrun", "simctl", "spawn", self.device_id] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"xcrun command failed: {stderr.decode()}")
        return stdout.decode().strip()
    
    async def connect(self) -> bool:
        try:
            result = await self._run_xcrun_command("id")
            self._connected = bool(result)
            return self._connected
        except Exception:
            return False
    
    async def disconnect(self) -> None:
        self._connected = False
    
    async def get_screen_size(self) -> Tuple[int, int]:
        cmd = ["xcrun", "simctl", "getdevicestate", self.device_id, "current-pixel-width"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        width = int(stdout.decode().strip())
        
        cmd = ["xcrun", "simctl", "getdevicestate", self.device_id, "current-pixel-height"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        height = int(stdout.decode().strip())
        
        return width, height
    
    async def screenshot(self) -> bytes:
        cmd = ["xcrun", "simctl", "io", self.device_id, "screenshot", "-"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout
    
    async def click(self, x: int, y: int) -> ActionResult:
        try:
            cmd = ["xcrun", "simctl", "io", self.device_id, "touch", f"{x}", f"{y}"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
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
            cmd = [
                "xcrun", "simctl", "io", self.device_id, "gesture",
                "pinch", "open",
                f"{start_x}", f"{start_y}",
                f"{end_x}", f"{end_y}",
                str(duration)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return ActionResult(success=True, message=f"Swiped from ({start_x},{start_y}) to ({end_x},{end_y})")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def input_text(self, text: str) -> ActionResult:
        try:
            cmd = ["xcrun", "simctl", "ui", self.device_id, "type", text]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return ActionResult(success=True, message=f"Input text: {text}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def press_key(self, key: str) -> ActionResult:
        key_map = {
            "home": "home",
            "back": "escape",
            "enter": "return",
            "delete": "delete",
            "volume_up": "volumeup",
            "volume_down": "volumedown",
            "power": "lock",
        }
        key_name = key_map.get(key.lower(), key.lower())
        try:
            cmd = ["xcrun", "simctl", "ui", self.device_id, "press", key_name]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return ActionResult(success=True, message=f"Pressed key: {key}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def wait(self, seconds: float) -> ActionResult:
        await asyncio.sleep(seconds)
        return ActionResult(success=True, message=f"Waited {seconds}s")
    
    async def launch_app(self, bundle_id: str) -> ActionResult:
        try:
            cmd = ["xcrun", "simctl", "launch", self.device_id, bundle_id]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return ActionResult(success=True, message=f"Launched app: {bundle_id}")
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def stop_app(self, bundle_id: str) -> ActionResult:
        try:
            cmd = ["xcrun", "simctl", "terminate", self.device_id, bundle_id]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return ActionResult(success=True, message=f"Stopped app: {bundle_id}")
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
        try:
            accessibility_tree = await self._get_accessibility_tree()
            if not accessibility_tree:
                return []
            
            elements = []
            for node in accessibility_tree:
                if self._matches_locator(node, locator_type, value):
                    element = Element(
                        locator_type=locator_type,
                        value=value,
                        text=node.get("label", ""),
                        enabled=node.get("enabled", True),
                        selected=node.get("selected", False)
                    )
                    elements.append(element)
            
            return elements
        except Exception:
            return []
    
    async def _get_accessibility_tree(self) -> List[Dict[str, Any]]:
        try:
            cmd = ["xcrun", "simctl", "ui", self.device_id, "inspect"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            import json
            return json.loads(stdout.decode()) if stdout else []
        except Exception:
            return []
    
    def _matches_locator(self, node: Dict[str, Any], locator_type: ElementLocatorType, value: str) -> bool:
        if locator_type == ElementLocatorType.TEXT:
            return node.get("label", "").lower() == value.lower()
        elif locator_type == ElementLocatorType.ID:
            return node.get("identifier", "").endswith(value)
        elif locator_type == ElementLocatorType.ACCESSIBILITY_ID:
            return node.get("identifier", "").lower() == value.lower()
        elif locator_type == ElementLocatorType.CLASS_NAME:
            return node.get("type", "").lower() == value.lower()
        return False
    
    async def get_current_activity(self) -> Optional[str]:
        try:
            cmd = ["xcrun", "simctl", "ui", self.device_id, "current-app"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            result = stdout.decode().strip()
            if result:
                parts = result.split()
                return parts[0] if parts else None
        except Exception:
            pass
        return None
    
    async def get_element_tree(self) -> Dict[str, Any]:
        tree = await self._get_accessibility_tree()
        if not tree:
            return {}
        
        def element_to_dict(element: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "type": element.get("type", ""),
                "label": element.get("label", ""),
                "identifier": element.get("identifier", ""),
                "enabled": element.get("enabled", True),
                "children": [element_to_dict(child) for child in element.get("children", [])]
            }
        
        if tree:
            return element_to_dict(tree[0])
        return {}
