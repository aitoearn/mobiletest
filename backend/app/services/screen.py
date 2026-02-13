import asyncio
import base64
import subprocess
import os
from typing import Optional, AsyncGenerator
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScreenStreamFrame:
    data: bytes
    width: int
    height: int
    timestamp: float


class ScreenStreamService:
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._frame_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._running = False
    
    async def start_stream(self, device_id: str, bitrate: int = 4000000) -> bool:
        if self._running:
            await self.stop_stream()
        
        try:
            cmd = [
                "scrcpy",
                "-s", device_id,
                "--window-title", f"Device {device_id}",
                "--stay-awake",
                "--turn-screen-off",
                "--bit-rate", str(bitrate),
                "--max-fps", "60",
                "-",
            ]
            
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            self._running = True
            asyncio.create_task(self._read_frames())
            
            logger.info(f"Screen stream started for device {device_id}")
            return True
            
        except FileNotFoundError:
            logger.error("scrcpy not found. Please install scrcpy first.")
            return False
        except Exception as e:
            logger.error(f"Failed to start screen stream: {e}")
            return False
    
    async def stop_stream(self):
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        logger.info("Screen stream stopped")
    
    async def _read_frames(self):
        while self._running and self._process:
            try:
                header = self._process.stdout.read(4)
                if not header or len(header) < 4:
                    break
                
                cmd = header[0]
                if cmd == 0x04:
                    pts_bytes = self._process.stdout.read(8)
                    pts = int.from_bytes(pts_bytes, "little")
                elif cmd == 0x06:
                    pts_bytes = self._process.stdout.read(8)
                    pts = int.from_bytes(pts_bytes, "little")
                
                size_bytes = self._process.stdout.read(4)
                size = int.from_bytes(size_bytes, "little")
                
                if size > 0:
                    frame_data = self._process.stdout.read(size)
                    if frame_data:
                        await self._frame_queue.put({
                            "data": frame_data,
                            "timestamp": asyncio.get_event_loop().time()
                        })
                
            except Exception as e:
                logger.error(f"Error reading frame: {e}")
                break
    
    async def get_frame(self, timeout: float = 1.0) -> Optional[ScreenStreamFrame]:
        try:
            frame = await asyncio.wait_for(self._frame_queue.get(), timeout=timeout)
            return ScreenStreamFrame(
                data=frame["data"],
                width=0,
                height=0,
                timestamp=frame["timestamp"]
            )
        except asyncio.TimeoutError:
            return None
    
    async def stream_frames(self, device_id: str) -> AsyncGenerator[bytes, None]:
        if not self._running:
            await self.start_stream(device_id)
        
        while self._running:
            frame = await self.get_frame(timeout=2.0)
            if frame:
                yield frame.data
    
    def is_running(self) -> bool:
        return self._running


class ScreenshotService:
    def __init__(self):
        self._temp_dir = "/tmp/mobiletest"
        os.makedirs(self._temp_dir, exist_ok=True)
    
    async def capture_screenshot(self, device_id: str) -> Optional[bytes]:
        import mss
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                screenshot = sct.grab(monitor)
                
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                return img_byte_arr.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    async def save_screenshot(self, device_id: str, path: str) -> bool:
        try:
            screenshot_data = await self.capture_screenshot(device_id)
            if screenshot_data:
                with open(path, "wb") as f:
                    f.write(screenshot_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return False
    
    def get_screenshot_base64(self, device_id: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "screencap", "-p"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return base64.b64encode(result.stdout).decode()
            return None
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}")
            return None


screen_stream_service = ScreenStreamService()
screenshot_service = ScreenshotService()
