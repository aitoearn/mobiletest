from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import os


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    QWEN = "qwen"
    ZHIPU = "zhipu"
    MODELSCOPE = "modelscope"
    LOCAL = "local"


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


@dataclass
class Message:
    role: str
    content: str


class BaseLLM(ABC):
    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: List[Message], **kwargs):
        pass


class OpenAILLM(BaseLLM):
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs
        )
        
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    async def stream_chat(self, messages: List[Message], **kwargs):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicLLM(BaseLLM):
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic package not installed")
        
        client = AsyncAnthropic(api_key=self.api_key)
        
        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                filtered_messages.append({"role": msg.role, "content": msg.content})
        
        response = await client.messages.create(
            model=self.model,
            system=system_message,
            messages=filtered_messages,
            **kwargs
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason="stop",
        )
    
    async def stream_chat(self, messages: List[Message], **kwargs):
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic package not installed")
        
        client = AsyncAnthropic(api_key=self.api_key)
        
        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                filtered_messages.append({"role": msg.role, "content": msg.content})
        
        async with client.messages.stream(
            model=self.model,
            system=system_message,
            messages=filtered_messages,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text


class QwenLLM(BaseLLM):
    def __init__(self, model: str = "qwen-max", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs
        )
        
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    async def stream_chat(self, messages: List[Message], **kwargs):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class ZhipuLLM(BaseLLM):
    def __init__(self, model: str = "glm-4-plus", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.base_url = base_url or "https://open.bigmodel.cn/api/paas/v4"
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs
        )
        
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    async def stream_chat(self, messages: List[Message], **kwargs):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class ModelScopeLLM(BaseLLM):
    def __init__(self, model: str = "Qwen/Qwen2.5-72B-Instruct", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        self.api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
        self.base_url = base_url or "https://api-inference.modelscope.cn/v1"
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs
        )
        
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    async def stream_chat(self, messages: List[Message], **kwargs):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package not installed")
        
        import httpx
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=httpx.AsyncClient(proxy=None)
        )
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def get_llm(provider: LLMProvider, model: Optional[str] = None, **kwargs) -> BaseLLM:
    if provider == LLMProvider.OPENAI:
        return OpenAILLM(model=model or "gpt-4o", **kwargs)
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicLLM(model=model or "claude-sonnet-4-20250514", **kwargs)
    elif provider == LLMProvider.QWEN:
        return QwenLLM(model=model or "qwen-max", **kwargs)
    elif provider == LLMProvider.ZHIPU:
        return ZhipuLLM(model=model or "glm-4-plus", **kwargs)
    elif provider == LLMProvider.MODELSCOPE:
        return ModelScopeLLM(model=model or "Qwen/Qwen2.5-72B-Instruct", **kwargs)
    else:
        return OpenAILLM(model=model or "gpt-4o", **kwargs)


import json
import re
from app.core.config import settings


class LLMClient:
    def __init__(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None):
        if provider is None:
            provider_str = os.getenv("LLM_PROVIDER", "openai").lower()
            provider = LLMProvider(provider_str)
        
        provider = provider or settings.llm_provider
        model = model or settings.llm_model
        
        self.llm = get_llm(
            provider,
            model,
            api_key=settings.llm_api_key or None,
            base_url=settings.llm_base_url or None
        )
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_devices",
                    "description": "获取所有连接的移动设备列表",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "device_control",
                    "description": "控制移动设备执行操作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string", "description": "设备ID"},
                            "action": {"type": "string", "description": "操作类型: click/swipe/input/screenshot/launch_app/get_screen_info"},
                            "params": {"type": "object", "description": "操作参数"}
                        },
                        "required": ["action"]
                    }
                }
            }
        ]
    
    async def chat_stream(self, messages: list[dict]):
        msg_objects = [Message(role=m["role"], content=m["content"]) for m in messages]
        
        async for content in self.llm.stream_chat(msg_objects, tools=self.tools):
            yield content
    
    def extract_tools(self, response: str) -> tuple[str, list[dict]]:
        content = ""
        tools = []
        
        tool_pattern = r'\{[\s\S]*?"function"[\s\S]*?\}'
        json_blocks = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
        
        for block in json_blocks:
            try:
                data = json.loads(block)
                if "function" in data or data.get("type") == "function":
                    tools.append(data.get("function", data))
                    response = response.replace(block, "")
                elif "name" in data and "arguments" in data:
                    tools.append({"name": data["name"], "arguments": data["arguments"]})
                    response = response.replace(block, "")
            except:
                pass
        
        content = response.strip()
        return content, tools
