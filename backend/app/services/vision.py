import base64
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ElementInfo:
    description: str
    x: int
    y: int
    width: int = 0
    height: int = 0


class VisionService:
    def __init__(self):
        self.config = self._load_config()
        self.api_key = self.config.get("visionApiKey") or os.getenv("ZHIPU_API_KEY")
        self.base_url = self.config.get("visionBaseUrl") or "https://open.bigmodel.cn/api/paas/v4"
        self.model = self.config.get("visionModelName") or "autoglm-phone"
    
    def _load_config(self) -> dict:
        config_file = "/Users/lisq/ai/mobileagent/mobiletest/backend/config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    async def analyze_screen(
        self, 
        screenshot_base64: str, 
        instruction: str,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        messages = [
            {
                "role": "system",
                "content": """你是一个手机屏幕分析助手。你的任务是分析屏幕截图，找到用户指定的元素，并返回其坐标。

输出格式要求：
1. 如果找到元素，返回 JSON 格式：
   {"found": true, "x": 坐标x, "y": 坐标y, "description": "元素描述"}

2. 如果找不到元素，返回：
   {"found": false, "reason": "原因", "suggestion": "建议"}

坐标说明：
- 返回的坐标应该是元素的中心点
- 坐标原点在屏幕左上角
- x 向右增加，y 向下增加"""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"请在截图中找到：{instruction}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ]
            }
        ]
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content
            logger.info(f"[VisionService] LLM response: {content}")
            
            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            return {
                "found": False,
                "reason": "无法解析模型响应",
                "raw_response": content
            }
            
        except Exception as e:
            logger.error(f"[VisionService] Error analyzing screen: {e}")
            return {
                "found": False,
                "reason": str(e)
            }
    
    async def find_element(
        self,
        screenshot_base64: str,
        element_description: str,
        device_id: Optional[str] = None
    ) -> Optional[ElementInfo]:
        result = await self.analyze_screen(
            screenshot_base64,
            f"找到「{element_description}」的位置",
            device_id
        )
        
        if result.get("found"):
            return ElementInfo(
                description=result.get("description", element_description),
                x=result.get("x", 0),
                y=result.get("y", 0),
                width=result.get("width", 0),
                height=result.get("height", 0),
            )
        
        return None
    
    async def get_screen_description(self, screenshot_base64: str) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请描述这个手机屏幕的内容，包括：1. 当前是什么应用/页面 2. 屏幕上有哪些可点击的元素 3. 搜索框的位置（如果有）"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ]
            }
        ]
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"[VisionService] Error getting screen description: {e}")
            return f"获取屏幕描述失败: {str(e)}"


vision_service = VisionService()
