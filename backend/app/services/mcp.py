import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class MCPToolParamType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class MCPToolParam(BaseModel):
    name: str
    type: MCPToolParamType
    description: str = ""
    required: bool = False
    default: Optional[Any] = None


class MCPTool(BaseModel):
    name: str
    description: str
    params: List[MCPToolParam] = []


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPService:
    def __init__(self):
        self._tools: Dict[str, callable] = {}
        self._initialized = False
    
    def register_tool(self, name: str, description: str, params: List[MCPToolParam], handler: callable):
        tool = MCPTool(
            name=name,
            description=description,
            params=params,
        )
        self._tools[name] = {
            "tool": tool,
            "handler": handler,
        }
    
    def get_tools(self) -> List[MCPTool]:
        return [v["tool"] for v in self._tools.values()]
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        if request.method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={"tools": [t.model_dump() for t in self.get_tools()]}
            )
        
        elif request.method == "tools/call":
            if not request.params or "name" not in request.params:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32602, "message": "Invalid params"}
                )
            
            tool_name = request.params["name"]
            tool_args = request.params.get("arguments", {})
            
            if tool_name not in self._tools:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Tool not found: {tool_name}"}
                )
            
            try:
                handler = self._tools[tool_name]["handler"]
                result = await handler(**tool_args)
                return MCPResponse(id=request.id, result=result)
            except Exception as e:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32603, "message": str(e)}
                )
        
        elif request.method == "ping":
            return MCPResponse(id=request.id, result={"status": "ok"})
        
        else:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Method not found: {request.method}"}
            )
    
    def _register_mobile_tools(self):
        self.register_tool(
            name="device_tap",
            description="Tap on device screen at coordinates",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
                MCPToolParam(name="x", type=MCPToolParamType.NUMBER, description="X coordinate", required=True),
                MCPToolParam(name="y", type=MCPToolParamType.NUMBER, description="Y coordinate", required=True),
            ],
            handler=self._handle_device_tap,
        )
        
        self.register_tool(
            name="device_swipe",
            description="Swipe on device screen",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
                MCPToolParam(name="direction", type=MCPToolParamType.STRING, description="Swipe direction (up/down/left/right)", required=True),
            ],
            handler=self._handle_device_swipe,
        )
        
        self.register_tool(
            name="device_screenshot",
            description="Capture device screenshot",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
            ],
            handler=self._handle_device_screenshot,
        )
        
        self.register_tool(
            name="device_input_text",
            description="Input text to device",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
                MCPToolParam(name="text", type=MCPToolParamType.STRING, description="Text to input", required=True),
            ],
            handler=self._handle_device_input_text,
        )
        
        self.register_tool(
            name="device_launch_app",
            description="Launch an app on device",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
                MCPToolParam(name="package_name", type=MCPToolParamType.STRING, description="App package name", required=True),
            ],
            handler=self._handle_device_launch_app,
        )
        
        self.register_tool(
            name="device_press_key",
            description="Press device key",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
                MCPToolParam(name="key", type=MCPToolParamType.STRING, description="Key name (home/back/enter)", required=True),
            ],
            handler=self._handle_device_press_key,
        )
        
        self.register_tool(
            name="device_get_info",
            description="Get device information",
            params=[
                MCPToolParam(name="device_id", type=MCPToolParamType.STRING, description="Device ID", required=True),
            ],
            handler=self._handle_device_get_info,
        )
    
    async def _handle_device_tap(self, device_id: str, x: int, y: int) -> Dict[str, Any]:
        from app.services.device import device_control_service
        result = await device_control_service.tap(device_id, x, y)
        return {"success": result}
    
    async def _handle_device_swipe(self, device_id: str, direction: str) -> Dict[str, Any]:
        from app.services.device import device_control_service
        
        if direction == "up":
            result = await device_control_service.swipe_up(device_id)
        elif direction == "down":
            result = await device_control_service.swipe_down(device_id)
        elif direction == "left":
            result = await device_control_service.swipe_left(device_id)
        elif direction == "right":
            result = await device_control_service.swipe_right(device_id)
        else:
            return {"success": False, "error": f"Invalid direction: {direction}"}
        
        return {"success": result}
    
    async def _handle_device_screenshot(self, device_id: str) -> Dict[str, Any]:
        from app.services.screen import screenshot_service
        screenshot_base64 = screenshot_service.get_screenshot_base64(device_id)
        if screenshot_base64:
            return {"success": True, "screenshot": screenshot_base64}
        return {"success": False, "error": "Failed to capture screenshot"}
    
    async def _handle_device_input_text(self, device_id: str, text: str) -> Dict[str, Any]:
        from app.services.device import device_control_service
        result = await device_control_service.input_text(device_id, text)
        return {"success": result}
    
    async def _handle_device_launch_app(self, device_id: str, package_name: str) -> Dict[str, Any]:
        from app.services.device import device_control_service
        result = await device_control_service.start_app(device_id, package_name)
        return {"success": result}
    
    async def _handle_device_press_key(self, device_id: str, key: str) -> Dict[str, Any]:
        from app.services.device import device_control_service
        result = await device_control_service.press_key(device_id, key)
        return {"success": result}
    
    async def _handle_device_get_info(self, device_id: str) -> Dict[str, Any]:
        from app.services.device import device_control_service
        info = await device_control_service.get_device_info(device_id)
        return {"success": True, "info": info}
    
    async def initialize(self):
        if not self._initialized:
            self._register_mobile_tools()
            self._initialized = True


mcp_service = MCPService()
