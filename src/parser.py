"""
parser.py — 将原始行/文本解析为统一的消息块格式

消息块结构:
  {
    "role": "user" | "assistant" | "unknown",
    "text": "消息正文",
    "source": "来源文件路径"
  }

兼容多种 jsonl schema:
  - Codex: {"type": "message", "role": "...", "content": [...]}
  - Claude Code: {"type": "...", "message": {"role": "...", "content": [...]}}
  - 简单格式: {"role": "...", "content": "..."}
  - 通用 chat: {"messages": [...]}
"""

import json
import warnings
from typing import Optional


def parse_jsonl_line(line: str, source: str = "") -> list[dict]:
    """
    解析单行 jsonl，返回消息块列表（一行可能包含多条消息）。
    无法解析时返回空列表并输出 warning。
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        # 不是 JSON，当纯文本行处理
        text = line.strip()
        if text:
            return [{"role": "unknown", "text": text, "source": source}]
        return []

    if not isinstance(obj, dict):
        return []

    blocks: list[dict] = []

    # ── Schema 1: Codex 格式 ──────────────────────────────────────────
    # {"type": "message", "role": "user", "content": [...]}
    if obj.get("type") == "message" and "role" in obj:
        text = _extract_content(obj.get("content", ""))
        if text:
            blocks.append({"role": obj["role"], "text": text, "source": source})
        return blocks

    # ── Schema 2: Claude Code 格式 ───────────────────────────────────
    # {"type": "...", "message": {"role": "...", "content": [...]}}
    if "message" in obj and isinstance(obj["message"], dict):
        msg = obj["message"]
        role = msg.get("role", "unknown")
        text = _extract_content(msg.get("content", ""))
        if text:
            blocks.append({"role": role, "text": text, "source": source})
        return blocks

    # ── Schema 3: 简单键值格式 ────────────────────────────────────────
    # {"role": "...", "content": "..."}
    if "role" in obj and "content" in obj:
        text = _extract_content(obj["content"])
        if text:
            blocks.append({"role": obj["role"], "text": text, "source": source})
        return blocks

    # ── Schema 4: messages 数组 ───────────────────────────────────────
    # {"messages": [{"role": "...", "content": "..."}, ...]}
    if "messages" in obj and isinstance(obj["messages"], list):
        for msg in obj["messages"]:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role", "unknown")
            text = _extract_content(msg.get("content", ""))
            if text:
                blocks.append({"role": role, "text": text, "source": source})
        return blocks

    # ── Schema 5: 兜底——提取所有字符串值 ─────────────────────────────
    text_parts = _extract_all_strings(obj)
    if text_parts:
        blocks.append({"role": "unknown", "text": "\n".join(text_parts), "source": source})

    return blocks


def parse_plain_text(text: str, source: str = "") -> list[dict]:
    """
    解析纯文本文件。
    尝试按角色分段（识别 'user:' / 'assistant:' 前缀），否则整体作为 unknown。
    """
    blocks: list[dict] = []
    lines = text.splitlines()

    current_role = "unknown"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        # 识别角色前缀行
        if lower.startswith(("user:", "human:", "用户:")):
            if current_lines:
                blocks.append(_make_block(current_role, current_lines, source))
            current_role = "user"
            current_lines = [stripped.split(":", 1)[-1].strip()]
        elif lower.startswith(("assistant:", "claude:", "ai:", "助手:")):
            if current_lines:
                blocks.append(_make_block(current_role, current_lines, source))
            current_role = "assistant"
            current_lines = [stripped.split(":", 1)[-1].strip()]
        else:
            current_lines.append(stripped)

    if current_lines:
        blocks.append(_make_block(current_role, current_lines, source))

    return blocks


# ── 内部辅助函数 ────────────────────────────────────────────────────────

def _extract_content(content) -> str:
    """从各种 content 格式中提取纯文本。"""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # {"type": "text", "text": "..."}
                if item.get("type") == "text" and "text" in item:
                    parts.append(item["text"])
                elif "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(_extract_content(item["content"]))
        return "\n".join(p for p in parts if p.strip())

    if isinstance(content, dict):
        return _extract_content(content.get("text", ""))

    return ""


def _extract_all_strings(obj: dict, depth: int = 0) -> list[str]:
    """递归提取 dict 中所有字符串值（深度限制为 3）。"""
    if depth > 3:
        return []
    results: list[str] = []
    for v in obj.values():
        if isinstance(v, str) and len(v) > 10:
            results.append(v)
        elif isinstance(v, dict):
            results.extend(_extract_all_strings(v, depth + 1))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and len(item) > 10:
                    results.append(item)
                elif isinstance(item, dict):
                    results.extend(_extract_all_strings(item, depth + 1))
    return results


def _make_block(role: str, lines: list[str], source: str) -> dict:
    text = "\n".join(l for l in lines if l)
    return {"role": role, "text": text, "source": source}
