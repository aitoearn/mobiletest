from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import os


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    QWEN = "qwen"
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
        
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        
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
        
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        
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
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
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
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
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
    else:
        raise ValueError(f"Unsupported provider: {provider}")
