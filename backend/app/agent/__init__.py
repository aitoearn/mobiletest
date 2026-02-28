from .mobile_agent import MobileAgent
from .prompts import get_combined_prompt

# 向后兼容：提供默认的 SYSTEM_PROMPT
SYSTEM_PROMPT = get_combined_prompt("autoglm", None)

__all__ = ["MobileAgent", "SYSTEM_PROMPT"]
