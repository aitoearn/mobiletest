"""
系统提示词管理模块

支持不同协议/模型的系统提示词：
- universal: 通用协议，兼容大多数 VLM 模型
- autoglm: AutoGLM 协议 (do/finish 格式)
- gelab: Gelab 协议

引擎配置的用户提示词将作为补充追加到基础提示词后。
"""

from .system import (
    UNIVERSAL_PROMPT,
    AUTOGML_PROMPT,
    GELAB_PROMPT,
    get_system_prompt,
    combine_prompts,
    get_combined_prompt,
)

__all__ = [
    'UNIVERSAL_PROMPT',
    'AUTOGML_PROMPT', 
    'GELAB_PROMPT',
    'get_system_prompt',
    'combine_prompts',
    'get_combined_prompt',
]
