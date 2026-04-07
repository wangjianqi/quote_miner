"""
sentence_splitter.py — 将段落文本切分成候选句子

中文文本常见分隔符：。！？；…
英文文本分隔符：. ! ?
也支持换行符分句（对话日志中常见）。
"""

import re

# 句子结束标点（中英文）
_SENTENCE_END = re.compile(
    r'(?<=[。！？!?；;…\n])'
    r'|(?<=\.\s)'
    r'|(?<=\n\n)'
)

# 用于二次切分的换行模式
_NEWLINE_SPLIT = re.compile(r'\n+')


def split_sentences(text: str) -> list[str]:
    """
    将原始文本切分为候选句子列表。
    保留句子的原始措辞。
    """
    if not text or not text.strip():
        return []

    # 先按换行拆（对话日志多为换行分段）
    paragraphs = _NEWLINE_SPLIT.split(text)
    sentences: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 再按标点拆
        subs = _split_by_punctuation(para)
        sentences.extend(subs)

    return sentences


def _split_by_punctuation(text: str) -> list[str]:
    """按中英文标点切分单段落文本为句子。"""
    # 切分标点：中文句末 + 英文句末
    pattern = re.compile(r'(?<=[。！？!?；;…])\s*|(?<=\.\s)\s*')
    parts = pattern.split(text)

    results: list[str] = []
    for part in parts:
        part = part.strip()
        if part:
            results.append(part)

    # 如果未切出任何内容，返回原文
    if not results:
        return [text.strip()] if text.strip() else []

    return results
