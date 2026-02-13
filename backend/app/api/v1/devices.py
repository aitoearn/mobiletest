from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.scanner import device_scanner

router = APIRouter(prefix="/devices", tags=["设备管理"])


class DeviceResponse(BaseModel):
    device_id: str
    status: str
    model: Optional[str] = None
    brand: Optional[str] = None
    android_version: Optional[str] = None
    screen_size: Optional[str] = None
    screen_density: Optional[str] = None
    battery_level: Optional[int] = None
    connected: bool = False


class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]


@router.get("/scan", response_model=DeviceListResponse)
async def scan_devices():
    devices = await device_scanner.scan_devices()
    
    result = []
    for device in devices:
        device_info = await device_scanner.get_device_info(device.device_id)
        result.append(DeviceResponse(
            device_id=device.device_id,
            status=device.status,
            model=device_info.get("model") or device.model,
            brand=device_info.get("brand"),
            android_version=device_info.get("android_version"),
            screen_size=device_info.get("screen_size"),
            screen_density=device_info.get("screen_density"),
            battery_level=device_info.get("battery_level"),
            connected=device_info.get("connected", False),
        ))
    
    return DeviceListResponse(devices=result)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    device_info = await device_scanner.get_device_info(device_id)
    
    if not device_info.get("connected"):
        raise HTTPException(status_code=404, detail="设备未连接")
    
    return DeviceResponse(
        device_id=device_id,
        status="device",
        model=device_info.get("model"),
        brand=device_info.get("brand"),
        android_version=device_info.get("android_version"),
        screen_size=device_info.get("screen_size"),
        screen_density=device_info.get("screen_density"),
        battery_level=device_info.get("battery_level"),
        connected=True,
    )


@router.post("/{device_id}/connect")
async def connect_device(device_id: str):
    from app.services.device import device_control_service
    
    success = await device_control_service.connect_device(device_id)
    if not success:
        raise HTTPException(status_code=400, detail="设备连接失败")
    
    return {"status": "connected", "device_id": device_id}


@router.post("/{device_id}/disconnect")
async def disconnect_device(device_id: str):
    from app.services.device import device_control_service
    
    success = await device_control_service.disconnect_device(device_id)
    return {"status": "disconnected", "device_id": device_id}


@router.post("/{device_id}/tap")
async def tap_device(device_id: str, x: int, y: int):
    from app.services.device import device_control_service
    
    success = await device_control_service.tap(device_id, x, y)
    if not success:
        raise HTTPException(status_code=400, detail="点击操作失败")
    
    return {"status": "success", "action": "tap", "x": x, "y": y}


@router.post("/{device_id}/swipe")
async def swipe_device(
    device_id: str,
    direction: str = "up",
    start_x: Optional[int] = None,
    start_y: Optional[int] = None,
    end_x: Optional[int] = None,
    end_y: Optional[int] = None,
    duration: int = 300,
):
    from app.services.device import device_control_service
    
    if direction in ["up", "down", "left", "right"]:
        if direction == "up":
            success = await device_control_service.swipe_up(device_id)
        elif direction == "down":
            success = await device_control_service.swipe_down(device_id)
        elif direction == "left":
            success = await device_control_service.swipe_left(device_id)
        else:
            success = await device_control_service.swipe_right(device_id)
    elif all([start_x, start_y, end_x, end_y]):
        success = await device_control_service.swipe(
            device_id, start_x, start_y, end_x, end_y, duration
        )
    else:
        raise HTTPException(status_code=400, detail="无效的滑动参数")
    
    if not success:
        raise HTTPException(status_code=400, detail="滑动操作失败")
    
    return {"status": "success", "action": "swipe", "direction": direction}


@router.post("/{device_id}/input")
async def input_text(device_id: str, text: str):
    from app.services.device import device_control_service
    
    success = await device_control_service.input_text(device_id, text)
    if not success:
        raise HTTPException(status_code=400, detail="输入操作失败")
    
    return {"status": "success", "action": "input", "text": text}


@router.post("/{device_id}/key")
async def press_key(device_id: str, key: str):
    from app.services.device import device_control_service
    
    success = await device_control_service.press_key(device_id, key)
    if not success:
        raise HTTPException(status_code=400, detail="按键操作失败")
    
    return {"status": "success", "action": "press_key", "key": key}


@router.get("/{device_id}/screenshot")
async def get_screenshot(device_id: str):
    from app.services.screen import screenshot_service
    
    screenshot_base64 = screenshot_service.get_screenshot_base64(device_id)
    if not screenshot_base64:
        raise HTTPException(status_code=400, detail="截图失败")
    
    return {"status": "success", "screenshot": screenshot_base64}


class TouchDownRequest(BaseModel):
    device_id: str
    x: int
    y: int


class TouchMoveRequest(BaseModel):
    device_id: str
    x: int
    y: int


class TouchUpRequest(BaseModel):
    device_id: str
    x: int
    y: int


@router.post("/touch_down")
async def touch_down(request: TouchDownRequest):
    from app.services.device import device_control_service
    
    success = await device_control_service.touch_down(request.device_id, request.x, request.y)
    if not success:
        raise HTTPException(status_code=400, detail="触摸按下失败")
    
    return {"status": "success", "action": "touch_down", "x": request.x, "y": request.y}


@router.post("/touch_move")
async def touch_move(request: TouchMoveRequest):
    from app.services.device import device_control_service
    
    success = await device_control_service.touch_move(request.device_id, request.x, request.y)
    if not success:
        raise HTTPException(status_code=400, detail="触摸移动失败")
    
    return {"status": "success", "action": "touch_move", "x": request.x, "y": request.y}


@router.post("/touch_up")
async def touch_up(request: TouchUpRequest):
    from app.services.device import device_control_service
    
    success = await device_control_service.touch_up(request.device_id, request.x, request.y)
    if not success:
        raise HTTPException(status_code=400, detail="触摸抬起失败")
    
    return {"status": "success", "action": "touch_up", "x": request.x, "y": request.y}
