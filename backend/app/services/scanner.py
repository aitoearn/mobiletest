import asyncio
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AdbDevice:
    device_id: str
    status: str
    model: Optional[str] = None
    product: Optional[str] = None
    device: Optional[str] = None
    transport_id: Optional[str] = None


class DeviceScanner:
    async def scan_devices(self) -> List[AdbDevice]:
        devices = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "adb", "devices", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"ADB command failed: {stderr.decode()}")
                return devices
            
            output = stdout.decode()
            lines = output.strip().split("\n")
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    
                    device_info = {
                        "device_id": device_id,
                        "status": status,
                    }
                    
                    for part in parts[2:]:
                        if ":" in part:
                            key, value = part.split(":", 1)
                            if key == "model":
                                device_info["model"] = value
                            elif key == "product":
                                device_info["product"] = value
                            elif key == "device":
                                device_info["device"] = value
                            elif key == "transport_id":
                                device_info["transport_id"] = value
                    
                    devices.append(AdbDevice(
                        device_id=device_id,
                        status=status,
                        model=device_info.get("model"),
                        product=device_info.get("product"),
                        device=device_info.get("device"),
                        transport_id=device_info.get("transport_id"),
                    ))
            
        except FileNotFoundError:
            logger.error("ADB not found. Please install Android Debug Bridge.")
        except Exception as e:
            logger.error(f"Failed to scan devices: {e}")
        
        return devices
    
    async def get_device_info(self, device_id: str) -> Dict[str, Any]:
        info = {
            "device_id": device_id,
            "connected": False,
        }
        
        try:
            model = await self._run_adb_shell(device_id, "getprop", "ro.product.model")
            info["model"] = model.strip()
            
            brand = await self._run_adb_shell(device_id, "getprop", "ro.product.brand")
            info["brand"] = brand.strip()
            
            android_version = await self._run_adb_shell(device_id, "getprop", "ro.build.version.release")
            info["android_version"] = android_version.strip()
            
            sdk_version = await self._run_adb_shell(device_id, "getprop", "ro.build.version.sdk")
            info["sdk_version"] = sdk_version.strip()
            
            screen_size = await self._run_adb_shell(device_id, "wm", "size")
            if "Physical size:" in screen_size:
                info["screen_size"] = screen_size.split(":")[-1].strip()
            
            screen_density = await self._run_adb_shell(device_id, "wm", "density")
            if "Physical density:" in screen_density:
                info["screen_density"] = screen_density.split(":")[-1].strip()
            
            battery = await self._run_adb_shell(device_id, "dumpsys", "battery")
            if "level:" in battery:
                match = re.search(r"level:\s*(\d+)", battery)
                if match:
                    info["battery_level"] = int(match.group(1))
            
            info["connected"] = True
            
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
        
        return info
    
    async def _run_adb_shell(self, device_id: str, *args) -> str:
        cmd = ["adb", "-s", device_id, "shell"] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()


device_scanner = DeviceScanner()
