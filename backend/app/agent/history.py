"""
历史记录管理模块
管理操作历史、循环检测、状态追踪
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from datetime import datetime
from collections import deque
import hashlib
import json
import logging

from .actions.space import Action, ActionType

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """历史记录条目"""
    step: int
    action: Action
    observation: str = ""  # 观察结果/截图描述
    screenshot_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "action": self.action.to_dict(),
            "observation": self.observation,
            "screenshot_path": self.screenshot_path,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoryEntry':
        return cls(
            step=data.get("step", 0),
            action=Action.from_dict(data.get("action", {})),
            observation=data.get("observation", ""),
            screenshot_path=data.get("screenshot_path"),
            timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now(),
            metadata=data.get("metadata", {}),
        )
    
    def get_fingerprint(self) -> str:
        """生成指纹用于循环检测"""
        # 基于动作类型和参数生成指纹
        action_data = {
            "type": self.action.action_type.value,
            "params": self.action.params,
        }
        return hashlib.md5(
            json.dumps(action_data, sort_keys=True).encode()
        ).hexdigest()[:16]


class LoopDetector:
    """循环检测器"""
    
    def __init__(
        self,
        window_size: int = 5,
        similarity_threshold: int = 3,
        max_repetitions: int = 2
    ):
        self.window_size = window_size
        self.similarity_threshold = similarity_threshold
        self.max_repetitions = max_repetitions
        self.fingerprints: deque = deque(maxlen=window_size * 2)
        self.action_counts: Dict[str, int] = {}
    
    def add_entry(self, entry: HistoryEntry) -> None:
        """添加历史条目"""
        fingerprint = entry.get_fingerprint()
        self.fingerprints.append(fingerprint)
        
        # 统计动作出现次数
        action_key = f"{entry.action.action_type.value}:{json.dumps(entry.action.params, sort_keys=True)}"
        self.action_counts[action_key] = self.action_counts.get(action_key, 0) + 1
    
    def detect_loop(self) -> Tuple[bool, Optional[str]]:
        """
        检测是否陷入循环
        
        Returns:
            (是否循环, 循环原因)
        """
        if len(self.fingerprints) < self.window_size:
            return False, None
        
        # 方法1: 滑动窗口检测重复模式
        recent = list(self.fingerprints)[-self.window_size:]
        
        # 检查最近窗口内是否有过多重复
        unique_count = len(set(recent))
        if unique_count < self.similarity_threshold:
            return True, f"检测到重复动作模式（{self.window_size - unique_count} 个重复动作）"
        
        # 方法2: 检测完全相同动作序列重复
        if len(self.fingerprints) >= self.window_size * 2:
            prev_window = list(self.fingerprints)[-self.window_size*2:-self.window_size]
            curr_window = list(self.fingerprints)[-self.window_size:]
            
            if prev_window == curr_window:
                return True, "检测到完全相同的动作序列重复"
        
        # 方法3: 检测单个动作重复过多
        for action_key, count in self.action_counts.items():
            if count > self.max_repetitions * 3:
                return True, f"动作 '{action_key}' 重复执行 {count} 次"
        
        return False, None
    
    def reset(self) -> None:
        """重置检测器"""
        self.fingerprints.clear()
        self.action_counts.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_actions": len(self.fingerprints),
            "unique_actions": len(set(self.fingerprints)),
            "action_counts": self.action_counts.copy(),
        }


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(
        self,
        max_history: int = 50,
        enable_loop_detection: bool = True,
        loop_window_size: int = 5
    ):
        self.max_history = max_history
        self.enable_loop_detection = enable_loop_detection
        self.entries: List[HistoryEntry] = []
        self.loop_detector = LoopDetector(window_size=loop_window_size) if enable_loop_detection else None
        self._step_counter = 0
    
    def add_entry(
        self,
        action: Action,
        observation: str = "",
        screenshot_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HistoryEntry:
        """添加历史记录"""
        self._step_counter += 1
        
        entry = HistoryEntry(
            step=self._step_counter,
            action=action,
            observation=observation,
            screenshot_path=screenshot_path,
            metadata=metadata or {},
        )
        
        self.entries.append(entry)
        
        # 限制历史记录数量
        if len(self.entries) > self.max_history:
            removed = self.entries.pop(0)
            logger.debug(f"历史记录超出限制，移除最早记录: step {removed.step}")
        
        # 更新循环检测器
        if self.loop_detector:
            self.loop_detector.add_entry(entry)
        
        return entry
    
    def get_recent(self, n: int = 5) -> List[HistoryEntry]:
        """获取最近 n 条记录"""
        return self.entries[-n:] if n > 0 else []
    
    def get_all(self) -> List[HistoryEntry]:
        """获取所有记录"""
        return self.entries.copy()
    
    def get_by_step(self, step: int) -> Optional[HistoryEntry]:
        """根据步骤号获取记录"""
        for entry in self.entries:
            if entry.step == step:
                return entry
        return None
    
    def get_last_action(self) -> Optional[Action]:
        """获取最后一个动作"""
        if self.entries:
            return self.entries[-1].action
        return None
    
    def get_last_n_actions(self, n: int = 5) -> List[Action]:
        """获取最近 n 个动作"""
        return [e.action for e in self.entries[-n:]]
    
    def check_loop(self) -> Tuple[bool, Optional[str]]:
        """检查是否陷入循环"""
        if self.loop_detector:
            return self.loop_detector.detect_loop()
        return False, None
    
    def get_summary(self, max_entries: int = 10) -> str:
        """获取历史摘要（用于上下文）"""
        if not self.entries:
            return "无历史记录"
        
        lines = ["历史操作记录:"]
        
        # 显示最近的操作
        recent = self.entries[-max_entries:]
        for entry in recent:
            action_desc = entry.action.get_description()
            lines.append(f"  Step {entry.step}: {action_desc}")
            if entry.observation:
                # 截断过长的观察
                obs = entry.observation[:100] + "..." if len(entry.observation) > 100 else entry.observation
                lines.append(f"    观察: {obs}")
        
        if len(self.entries) > max_entries:
            lines.append(f"  ... 还有 {len(self.entries) - max_entries} 条记录")
        
        return "\n".join(lines)
    
    def get_formatted_history(
        self,
        format_type: str = "detailed",
        max_entries: Optional[int] = None
    ) -> str:
        """
        获取格式化的历史记录
        
        Args:
            format_type: 格式类型 - "detailed", "compact", "actions_only"
            max_entries: 最大条目数
        """
        entries = self.entries
        if max_entries:
            entries = entries[-max_entries:]
        
        if format_type == "compact":
            # 紧凑格式
            parts = []
            for entry in entries:
                parts.append(f"[{entry.step}] {entry.action.action_type.value}")
            return " -> ".join(parts)
        
        elif format_type == "actions_only":
            # 仅动作
            return "\n".join([
                f"Step {e.step}: {e.action.action_type.value}"
                for e in entries
            ])
        
        else:  # detailed
            # 详细格式
            lines = []
            for entry in entries:
                lines.append(f"=== Step {entry.step} ===")
                lines.append(f"动作: {entry.action.get_description()}")
                if entry.observation:
                    lines.append(f"观察: {entry.observation}")
                lines.append("")
            return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_entries": len(self.entries),
            "current_step": self._step_counter,
        }
        
        # 动作类型统计
        action_counts: Dict[str, int] = {}
        for entry in self.entries:
            action_type = entry.action.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        stats["action_counts"] = action_counts
        
        # 循环检测统计
        if self.loop_detector:
            stats["loop_detection"] = self.loop_detector.get_stats()
        
        return stats
    
    def clear(self) -> None:
        """清空历史记录"""
        self.entries.clear()
        self._step_counter = 0
        if self.loop_detector:
            self.loop_detector.reset()
    
    def export_to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "max_history": self.max_history,
            "current_step": self._step_counter,
            "entries": [e.to_dict() for e in self.entries],
        }
    
    def import_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典导入"""
        self.max_history = data.get("max_history", self.max_history)
        self._step_counter = data.get("current_step", 0)
        self.entries = [
            HistoryEntry.from_dict(e) for e in data.get("entries", [])
        ]
        
        # 重建循环检测器状态
        if self.loop_detector:
            self.loop_detector.reset()
            for entry in self.entries:
                self.loop_detector.add_entry(entry)
    
    def save_to_file(self, filepath: str) -> None:
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.export_to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str) -> None:
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.import_from_dict(data)


class ContextWindowManager:
    """上下文窗口管理器 - 管理历史记录的窗口大小"""
    
    def __init__(
        self,
        max_context_entries: int = 10,
        max_context_tokens: int = 4000,
        summary_interval: int = 5
    ):
        self.max_context_entries = max_context_entries
        self.max_context_tokens = max_context_tokens
        self.summary_interval = summary_interval
        self.summaries: Dict[int, str] = {}  # step -> summary
    
    def build_context(
        self,
        history_manager: HistoryManager,
        include_current: bool = True
    ) -> List[Dict[str, Any]]:
        """
        构建上下文消息列表
        
        Returns:
            格式化的消息列表，可直接用于 LLM
        """
        messages = []
        entries = history_manager.get_all()
        
        if not entries:
            return messages
        
        # 如果历史记录较少，全部包含
        if len(entries) <= self.max_context_entries:
            for entry in entries:
                messages.append(self._entry_to_message(entry))
        else:
            # 需要压缩历史记录
            # 1. 保留最早的摘要
            early_summary = self._summarize_entries(entries[:-self.max_context_entries])
            if early_summary:
                messages.append({
                    "role": "system",
                    "content": f"早期操作摘要:\n{early_summary}"
                })
            
            # 2. 包含最近的详细记录
            for entry in entries[-self.max_context_entries:]:
                messages.append(self._entry_to_message(entry))
        
        return messages
    
    def _entry_to_message(self, entry: HistoryEntry) -> Dict[str, Any]:
        """将历史条目转换为消息格式"""
        content = f"动作: {entry.action.get_description()}"
        if entry.observation:
            content += f"\n观察: {entry.observation}"
        
        return {
            "role": "assistant" if entry.action.action_type in [ActionType.THINK, ActionType.PLAN] else "user",
            "content": content,
            "metadata": {
                "step": entry.step,
                "action_type": entry.action.action_type.value,
            }
        }
    
    def _summarize_entries(self, entries: List[HistoryEntry]) -> str:
        """摘要一组历史条目"""
        if not entries:
            return ""
        
        # 简单的统计摘要
        action_counts: Dict[str, int] = {}
        for entry in entries:
            action_type = entry.action.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        parts = [f"共执行 {len(entries)} 步操作:"]
        for action_type, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            parts.append(f"  - {action_type}: {count}次")
        
        return "\n".join(parts)
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数（粗略估计）"""
        # 中文字符约1.5 tokens，英文单词约1 token
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return int(chinese_chars * 1.5 + english_words + len(text) * 0.1)


# 便捷函数
def create_history_manager(**kwargs) -> HistoryManager:
    """创建历史管理器的便捷函数"""
    return HistoryManager(**kwargs)


def create_loop_detector(**kwargs) -> LoopDetector:
    """创建循环检测器的便捷函数"""
    return LoopDetector(**kwargs)
