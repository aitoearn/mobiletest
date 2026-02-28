"""
统一的 LLM 配置管理模块
支持多模型配置、协议适配、自动检测
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import os


class ProtocolType(Enum):
    """支持的协议类型"""
    UNIVERSAL = "universal"      # 通用协议
    AUTOGML = "autoglm"          # AutoGLM 协议
    GELAB = "gelab"              # Gelab 协议


class ModelProvider(Enum):
    """模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    ZHIPU = "zhipu"
    CUSTOM = "custom"


@dataclass
class ModelCapability:
    """模型能力配置"""
    supports_vision: bool = True
    supports_tools: bool = False
    supports_json_mode: bool = False
    max_tokens: int = 4096
    context_window: int = 8192
    recommended_temperature: float = 0.7


@dataclass
class ProtocolConfig:
    """协议配置"""
    protocol_type: ProtocolType
    # 坐标系配置
    coordinate_scale: int = 1000  # 0-1000 或 0-999
    # 图像配置
    image_size: tuple = (1080, 1920)
    image_quality: int = 90
    image_format: str = "JPEG"
    # 动作格式
    action_format: str = "json"  # json, xml, text
    # 系统提示词
    system_prompt_template: str = ""
    # 特殊配置
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    provider: ModelProvider
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    protocol: ProtocolType = ProtocolType.UNIVERSAL
    capabilities: ModelCapability = field(default_factory=ModelCapability)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.protocol, str):
            self.protocol = ProtocolType(self.protocol)
        if isinstance(self.provider, str):
            self.provider = ModelProvider(self.provider)


class LLMConfigManager:
    """LLM 配置管理器"""
    
    # 模型名称到协议的自动映射规则
    PROTOCOL_DETECTION_RULES = [
        ("autoglm", ProtocolType.AUTOGML),
        ("glm", ProtocolType.AUTOGML),
        ("gelab", ProtocolType.GELAB),
    ]
    
    # 默认协议配置
    DEFAULT_PROTOCOL_CONFIGS = {
        ProtocolType.UNIVERSAL: ProtocolConfig(
            protocol_type=ProtocolType.UNIVERSAL,
            coordinate_scale=1000,
            image_size=(1080, 1920),
            image_quality=90,
            image_format="JPEG",
            action_format="json",
        ),
        ProtocolType.AUTOGML: ProtocolConfig(
            protocol_type=ProtocolType.AUTOGML,
            coordinate_scale=999,
            image_size=(1080, 1920),
            image_quality=85,
            image_format="JPEG",
            action_format="json",
        ),
        ProtocolType.GELAB: ProtocolConfig(
            protocol_type=ProtocolType.GELAB,
            coordinate_scale=1000,
            image_size=(720, 1280),
            image_quality=80,
            image_format="JPEG",
            action_format="xml",
        ),
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.models: Dict[str, ModelConfig] = {}
        self.protocol_configs: Dict[ProtocolType, ProtocolConfig] = {}
        self._load_default_protocol_configs()
        
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)
    
    def _load_default_protocol_configs(self):
        """加载默认协议配置"""
        self.protocol_configs = self.DEFAULT_PROTOCOL_CONFIGS.copy()
    
    def detect_protocol(self, model_name: str) -> ProtocolType:
        """根据模型名称自动检测协议类型"""
        model_lower = model_name.lower()
        for pattern, protocol in self.PROTOCOL_DETECTION_RULES:
            if pattern in model_lower:
                return protocol
        return ProtocolType.UNIVERSAL
    
    def register_model(self, config: ModelConfig) -> None:
        """注册模型配置"""
        # 自动检测协议（如果未指定）
        if config.protocol == ProtocolType.UNIVERSAL:
            detected = self.detect_protocol(config.model_id)
            if detected != ProtocolType.UNIVERSAL:
                config.protocol = detected
        
        self.models[config.name] = config
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self.models.get(name)
    
    def get_protocol_config(self, protocol: ProtocolType) -> ProtocolConfig:
        """获取协议配置"""
        return self.protocol_configs.get(protocol, self.protocol_configs[ProtocolType.UNIVERSAL])
    
    def list_models(self) -> List[str]:
        """列出所有已注册模型"""
        return list(self.models.keys())
    
    def load_from_file(self, path: str) -> None:
        """从 JSON 文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载模型配置
        for model_data in data.get('models', []):
            config = ModelConfig(**model_data)
            self.register_model(config)
        
        # 加载协议配置（可选）
        for proto_name, proto_data in data.get('protocols', {}).items():
            protocol = ProtocolType(proto_name)
            self.protocol_configs[protocol] = ProtocolConfig(
                protocol_type=protocol,
                **proto_data
            )
    
    def save_to_file(self, path: str) -> None:
        """保存配置到 JSON 文件"""
        data = {
            'models': [
                {
                    'name': m.name,
                    'provider': m.provider.value,
                    'model_id': m.model_id,
                    'api_key': m.api_key,
                    'base_url': m.base_url,
                    'protocol': m.protocol.value,
                    'capabilities': {
                        'supports_vision': m.capabilities.supports_vision,
                        'supports_tools': m.capabilities.supports_tools,
                        'supports_json_mode': m.capabilities.supports_json_mode,
                        'max_tokens': m.capabilities.max_tokens,
                        'context_window': m.capabilities.context_window,
                        'recommended_temperature': m.capabilities.recommended_temperature,
                    },
                    'custom_headers': m.custom_headers,
                    'extra_params': m.extra_params,
                }
                for m in self.models.values()
            ],
            'protocols': {
                p.value: {
                    'coordinate_scale': c.coordinate_scale,
                    'image_size': c.image_size,
                    'image_quality': c.image_quality,
                    'image_format': c.image_format,
                    'action_format': c.action_format,
                    'extra_params': c.extra_params,
                }
                for p, c in self.protocol_configs.items()
            }
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_default_configs(self) -> Dict[str, ModelConfig]:
        """创建默认模型配置"""
        configs = {
            "gpt-4o": ModelConfig(
                name="gpt-4o",
                provider=ModelProvider.OPENAI,
                model_id="gpt-4o",
                protocol=ProtocolType.UNIVERSAL,
                capabilities=ModelCapability(
                    supports_vision=True,
                    supports_tools=True,
                    supports_json_mode=True,
                    max_tokens=4096,
                    context_window=128000,
                ),
            ),
            "claude-3-5-sonnet": ModelConfig(
                name="claude-3-5-sonnet",
                provider=ModelProvider.ANTHROPIC,
                model_id="claude-3-5-sonnet-20241022",
                protocol=ProtocolType.UNIVERSAL,
                capabilities=ModelCapability(
                    supports_vision=True,
                    supports_tools=True,
                    supports_json_mode=False,
                    max_tokens=4096,
                    context_window=200000,
                ),
            ),
            "gemini-2.0-flash": ModelConfig(
                name="gemini-2.0-flash",
                provider=ModelProvider.GEMINI,
                model_id="gemini-2.0-flash-exp",
                protocol=ProtocolType.UNIVERSAL,
                capabilities=ModelCapability(
                    supports_vision=True,
                    supports_tools=False,
                    supports_json_mode=False,
                    max_tokens=4096,
                    context_window=1000000,
                ),
            ),
            "autoglm-phone": ModelConfig(
                name="autoglm-phone",
                provider=ModelProvider.ZHIPU,
                model_id="autoglm-phone",
                protocol=ProtocolType.AUTOGML,
                capabilities=ModelCapability(
                    supports_vision=True,
                    supports_tools=False,
                    supports_json_mode=False,
                    max_tokens=2048,
                    context_window=8192,
                ),
            ),
        }
        
        for config in configs.values():
            self.register_model(config)
        
        return configs


# 全局配置管理器实例
_config_manager: Optional[LLMConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> LLMConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = LLMConfigManager(config_path)
    return _config_manager


def reset_config_manager():
    """重置配置管理器（主要用于测试）"""
    global _config_manager
    _config_manager = None
