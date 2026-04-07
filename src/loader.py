"""
loader.py — 从不同来源加载原始消息块

支持:
  - txt / md 文件（纯文本）
  - jsonl 文件（Codex / Claude Code 格式）
  - ~/.codex/sessions/ 自动扫描
  - ~/.claude/ 自动扫描
"""

import json
import sys
import warnings
from pathlib import Path

from src.parser import parse_jsonl_line, parse_plain_text


def load_from_file(path: Path) -> list[dict]:
    """根据文件扩展名选择合适的解析方式。"""
    if not path.exists():
        print(f"❌ 文件不存在: {path}", file=sys.stderr)
        return []

    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _load_jsonl(path)
    elif suffix in (".txt", ".md", ""):
        return _load_plain(path)
    else:
        # 未知类型：先尝试 jsonl，失败则当纯文本处理
        blocks = _load_jsonl(path)
        if not blocks:
            blocks = _load_plain(path)
        return blocks


def load_from_codex() -> list[dict]:
    """扫描 ~/.codex/sessions/ 下的所有 jsonl 文件。"""
    sessions_dir = Path.home() / ".codex" / "sessions"
    return _scan_jsonl_dir(sessions_dir, label="Codex")


def load_from_claude() -> list[dict]:
    """扫描 ~/.claude/ 下可能的日志文件（jsonl / txt）。"""
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        print(f"⚠️  未找到 Claude 日志目录: {claude_dir}", file=sys.stderr)
        return []

    blocks: list[dict] = []
    # 递归查找 jsonl 文件
    for p in sorted(claude_dir.rglob("*.jsonl")):
        blocks.extend(_load_jsonl(p))
    # 兜底：txt 文件
    if not blocks:
        for p in sorted(claude_dir.rglob("*.txt")):
            blocks.extend(_load_plain(p))

    if not blocks:
        print(f"⚠️  在 {claude_dir} 下未找到可解析的日志文件", file=sys.stderr)
    return blocks


# ── 内部辅助函数 ────────────────────────────────────────────────────────

def _scan_jsonl_dir(directory: Path, label: str = "") -> list[dict]:
    """递归扫描目录下所有 jsonl 文件并合并解析结果。"""
    if not directory.exists():
        print(f"⚠️  未找到 {label} 日志目录: {directory}", file=sys.stderr)
        return []

    blocks: list[dict] = []
    files = sorted(directory.rglob("*.jsonl"))
    if not files:
        print(f"⚠️  {label} 目录下未找到 jsonl 文件: {directory}", file=sys.stderr)
        return []

    print(f"📁 扫描到 {len(files)} 个 jsonl 文件（{label}）")
    for p in files:
        blocks.extend(_load_jsonl(p))
    return blocks


def _load_jsonl(path: Path) -> list[dict]:
    """解析单个 jsonl 文件，每行独立解析，遇错跳过并 warning。"""
    blocks: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                result = parse_jsonl_line(line, source=str(path))
                if result:
                    blocks.extend(result)
                # 解析失败的行已在 parse_jsonl_line 内 warning
    except OSError as e:
        warnings.warn(f"无法读取文件 {path}: {e}")
    return blocks


def _load_plain(path: Path) -> list[dict]:
    """将纯文本文件整体作为一个未知角色的消息块返回。"""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return parse_plain_text(text, source=str(path))
    except OSError as e:
        warnings.warn(f"无法读取文件 {path}: {e}")
        return []
