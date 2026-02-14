import asyncio
import subprocess
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

ADB_KEYBOARD_PACKAGE = "com.android.adbkeyboard"


@dataclass
class TouchEvent:
    x: int
    y: int
    action: str = "tap"


@dataclass
class SwipeEvent:
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration: int = 300


class DeviceControlService:
    def __init__(self):
        self._device_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def connect_device(self, device_id: str, platform: str = "android") -> bool:
        try:
            if platform == "android":
                result = await self._run_adb_command(device_id, "get-state")
                if result == "device":
                    self._device_sessions[device_id] = {
                        "platform": platform,
                        "connected": True,
                        "screen_on": True,
                    }
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect device {device_id}: {e}")
            return False
    
    async def disconnect_device(self, device_id: str) -> bool:
        if device_id in self._device_sessions:
            del self._device_sessions[device_id]
            return True
        return False
    
    async def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = await self._run_adb_command(device_id, "shell", "getprop", "ro.product.model")
            model = result.strip()
            
            result = await self._run_adb_command(device_id, "shell", "getprop", "ro.build.version.release")
            android_version = result.strip()
            
            result = await self._run_adb_command(device_id, "shell", "wm", "size")
            size = result.strip().split(":")[-1].strip() if ":" in result else "unknown"
            
            return {
                "device_id": device_id,
                "model": model,
                "android_version": android_version,
                "screen_size": size,
                "connected": device_id in self._device_sessions,
            }
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            return None
    
    async def tap(self, device_id: str, x: int, y: int) -> bool:
        try:
            await self._run_adb_command(device_id, "shell", "input", "tap", str(x), str(y))
            return True
        except Exception as e:
            logger.error(f"Failed to tap: {e}")
            return False
    
    async def touch_down(self, device_id: str, x: int, y: int) -> bool:
        """Send touch down event at specified coordinates."""
        try:
            await self._run_adb_command(
                device_id, "shell", "input", "motionevent", "DOWN", str(x), str(y)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send touch down: {e}")
            return False
    
    async def touch_move(self, device_id: str, x: int, y: int) -> bool:
        """Send touch move event at specified coordinates."""
        try:
            await self._run_adb_command(
                device_id, "shell", "input", "motionevent", "MOVE", str(x), str(y)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send touch move: {e}")
            return False
    
    async def touch_up(self, device_id: str, x: int, y: int) -> bool:
        """Send touch up event at specified coordinates."""
        try:
            await self._run_adb_command(
                device_id, "shell", "input", "motionevent", "UP", str(x), str(y)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send touch up: {e}")
            return False
    
    async def swipe(self, device_id: str, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 300) -> bool:
        try:
            await self._run_adb_command(
                device_id, "shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y), str(duration)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to swipe: {e}")
            return False
    
    async def swipe_up(self, device_id: str) -> bool:
        screen_size = await self._get_screen_size(device_id)
        if not screen_size:
            return False
        
        width, height = screen_size
        center_x = width // 2
        start_y = int(height * 0.8)
        end_y = int(height * 0.2)
        
        return await self.swipe(device_id, center_x, start_y, center_x, end_y)
    
    async def swipe_down(self, device_id: str) -> bool:
        screen_size = await self._get_screen_size(device_id)
        if not screen_size:
            return False
        
        width, height = screen_size
        center_x = width // 2
        start_y = int(height * 0.2)
        end_y = int(height * 0.8)
        
        return await self.swipe(device_id, center_x, start_y, center_x, end_y)
    
    async def swipe_left(self, device_id: str) -> bool:
        screen_size = await self._get_screen_size(device_id)
        if not screen_size:
            return False
        
        width, height = screen_size
        center_y = height // 2
        start_x = int(width * 0.8)
        end_x = int(width * 0.2)
        
        return await self.swipe(device_id, start_x, center_y, end_x, center_y)
    
    async def swipe_right(self, device_id: str) -> bool:
        screen_size = await self._get_screen_size(device_id)
        if not screen_size:
            return False
        
        width, height = screen_size
        center_y = height // 2
        start_x = int(width * 0.2)
        end_x = int(width * 0.8)
        
        return await self.swipe(device_id, start_x, center_y, end_x, center_y)
    
    async def input_text(self, device_id: str, text: str) -> bool:
        try:
            import base64
            
            await self._ensure_adb_keyboard(device_id)
            
            encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            
            await self._run_adb_command(
                device_id, "shell", "am", "broadcast", 
                "-a", "ADB_INPUT_B64", "--es", "msg", encoded_text
            )
            return True
        except Exception as e:
            logger.error(f"Failed to input text: {e}")
            return False
    
    async def _ensure_adb_keyboard(self, device_id: str) -> bool:
        try:
            result = await self._run_adb_command(
                device_id, "shell", "pm", "list", "packages", ADB_KEYBOARD_PACKAGE
            )
            
            if ADB_KEYBOARD_PACKAGE not in result:
                apk_path = os.path.join(
                    os.path.dirname(__file__), 
                    "../../resources/apks/ADBKeyboard.apk"
                )
                abs_apk_path = os.path.abspath(apk_path)
                
                if not os.path.exists(abs_apk_path):
                    logger.error(f"ADB Keyboard APK not found at {abs_apk_path}")
                    return False
                
                await self._run_adb_command(device_id, "install", "-r", abs_apk_path)
                logger.info("ADB Keyboard installed successfully")
            
            result = await self._run_adb_command(
                device_id, "shell", "settings", "get", "secure", "default_input_method"
            )
            current_ime = result.strip() if result else ""
            
            if "com.android.adbkeyboard/.AdbIME" not in current_ime:
                await self._run_adb_command(
                    device_id, "shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"
                )
                logger.info("Switched to ADB Keyboard for text input")
            
            return True
        except Exception as e:
            logger.warning(f"Could not set ADB keyboard: {e}")
            return False
    
    async def press_key(self, device_id: str, key: str) -> bool:
        key_map = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK",
            "enter": "KEYCODE_ENTER",
            "delete": "KEYCODE_DEL",
            "volume_up": "KEYCODE_VOLUME_UP",
            "volume_down": "KEYCODE_VOLUME_DOWN",
            "power": "KEYCODE_POWER",
            "menu": "KEYCODE_MENU",
        }
        
        keycode = key_map.get(key.lower(), key.upper())
        
        try:
            await self._run_adb_command(device_id, "shell", "input", "keyevent", keycode)
            return True
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return False
    
    async def press_enter(self, device_id: str) -> bool:
        return await self.press_key(device_id, "enter")
    
    async def press_back(self, device_id: str) -> bool:
        return await self.press_key(device_id, "back")
    
    async def press_home(self, device_id: str) -> bool:
        return await self.press_key(device_id, "home")
    
    async def wake_screen(self, device_id: str) -> bool:
        try:
            await self._run_adb_command(device_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
            return True
        except Exception as e:
            logger.error(f"Failed to wake screen: {e}")
            return False
    
    async def turn_screen_off(self, device_id: str) -> bool:
        try:
            await self._run_adb_command(device_id, "shell", "input", "keyevent", "KEYCODE_SLEEP")
            return True
        except Exception as e:
            logger.error(f"Failed to turn off screen: {e}")
            return False
    
    async def start_app(self, device_id: str, package_name: str) -> bool:
        try:
            await self._run_adb_command(device_id, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1")
            return True
        except Exception as e:
            logger.error(f"Failed to start app: {e}")
            return False
    
    async def stop_app(self, device_id: str, package_name: str) -> bool:
        try:
            await self._run_adb_command(device_id, "shell", "am", "force-stop", package_name)
            return True
        except Exception as e:
            logger.error(f"Failed to stop app: {e}")
            return False
    
    async def get_current_app(self, device_id: str) -> Optional[str]:
        try:
            result = await self._run_adb_command(
                device_id, "shell", "dumpsys", "window", "|", "grep", "-E", "mCurrentFocus"
            )
            if "mCurrentFocus" in result:
                parts = result.split()
                for i, part in enumerate(parts):
                    if "mCurrentFocus" in part and i + 1 < len(parts):
                        return parts[i + 1].rstrip("}")
            return None
        except Exception as e:
            logger.error(f"Failed to get current app: {e}")
            return None
    
    async def _get_screen_size(self, device_id: str) -> Optional[tuple]:
        try:
            result = await self._run_adb_command(device_id, "shell", "wm", "size")
            if "Physical size:" in result:
                size_str = result.split(":")[-1].strip()
                width, height = map(int, size_str.split("x"))
                return (width, height)
            return None
        except Exception:
            return None
    
    async def screenshot(self, device_id: str) -> Optional[bytes]:
        """Take a screenshot and return as PNG bytes."""
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            
            remote_path = "/sdcard/screenshot.png"
            await self._run_adb_command(device_id, "shell", "screencap", "-p", remote_path)
            await self._run_adb_command(device_id, "pull", remote_path, tmp_path)
            await self._run_adb_command(device_id, "shell", "rm", remote_path)
            
            with open(tmp_path, "rb") as f:
                data = f.read()
            
            os.unlink(tmp_path)
            return data
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    async def screenshot_base64(self, device_id: str) -> Optional[str]:
        """Take a screenshot and return as base64 string."""
        import base64
        
        data = await self.screenshot(device_id)
        if data:
            return base64.b64encode(data).decode("utf-8")
        return None
    
    async def _run_adb_command(self, device_id: str, *args) -> str:
        cmd = ["adb", "-s", device_id] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"ADB command failed: {stderr.decode()}")
        
        return stdout.decode()


device_control_service = DeviceControlService()
