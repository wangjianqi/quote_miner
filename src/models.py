"""
数据模型定义
"""

from dataclasses import dataclass, field


@dataclass
class QuoteCandidate:
    """一条候选工程金句。"""
    text: str               # 原始句子文本
    score: float            # 综合评分（越高越优先）
    category: str           # 分类：decision / risk_control / developer_style / general
    role: str               # 发言角色：user / assistant / unknown
    source: str = ""        # 来源文件路径

    def __repr__(self) -> str:
        return f"[{self.score:.1f}][{self.category}] {self.text[:60]}"
