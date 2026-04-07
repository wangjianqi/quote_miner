"""
loader.py — 从不同来源加载原始消息块

支持:
  - txt / md 文件（纯文本）
  - jsonl 文件（Codex / Claude Code 格式）
  - ~/.codex/sessions/ 自动扫描
  - ~/.claude/ 自动扫描
  - ~/.config/Cursor/User/workspaceStorage/ 自动扫描（SQLite state.vscdb）
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
    for p in sorted(claude_dir.rglob("*.jsonl")):
        blocks.extend(_load_jsonl(p))
    if not blocks:
        for p in sorted(claude_dir.rglob("*.txt")):
            blocks.extend(_load_plain(p))

    if not blocks:
        print(f"⚠️  在 {claude_dir} 下未找到可解析的日志文件", file=sys.stderr)
    return blocks


def load_from_cursor() -> list[dict]:
    """扫描 Cursor workspaceStorage 下的 state.vscdb（SQLite）并提取消息。"""
    candidates: list[Path] = []
    for base in _cursor_storage_dirs():
        if base.exists():
            candidates.extend(base.rglob("state.vscdb"))

    if not candidates:
        print(f"⚠️  未找到 Cursor state.vscdb 文件", file=sys.stderr)
        return []

    print(f"📁 扫描到 {len(candidates)} 个 Cursor state.vscdb")
    blocks: list[dict] = []
    for db_path in candidates:
        blocks.extend(_load_cursor_db(db_path))
    return blocks


def _cursor_storage_dirs() -> list[Path]:
    """返回各平台 Cursor workspaceStorage 根目录列表。"""
    home = Path.home()
    if sys.platform == "darwin":
        app_support = home / "Library" / "Application Support"
    elif sys.platform == "win32":
        app_support = Path.home() / "AppData" / "Roaming"
    else:
        app_support = home / ".config"
    return [
        app_support / "Cursor" / "User" / "workspaceStorage",
        app_support / "Cursor" / "User" / "globalStorage",
    ]


def _load_cursor_db(db_path: Path) -> list[dict]:
    """从单个 Cursor state.vscdb 数据库中解析消息块。"""
    import sqlite3

    blocks: list[dict] = []
    try:
        conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
        conn.set_trace_callback(None)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row[0] for row in cursor.fetchall()]

        for tbl in table_names:
            if tbl in ("sqlite_stat1", "sqlite_stat2", "sqlite_stat3", "sqlite_stat4"):
                continue
            blocks.extend(_extract_from_cursor_table(cursor, tbl, str(db_path)))

        conn.close()
    except sqlite3.Error as e:
        warnings.warn(f"无法读取 Cursor 数据库 {db_path}: {e}")
    return blocks


def _extract_from_cursor_table(cursor, table: str, source: str) -> list[dict]:
    """尝试从表中提取 role/content 类型的列并解析为消息块。"""
    blocks: list[dict] = []
    try:
        cursor.execute(f"SELECT * FROM {table} LIMIT 3")
        rows = cursor.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cursor.description]

        role_col = next((c for c in columns if c.lower() in ("role", "sender", "author")), None)
        content_col = next((c for c in columns if c.lower() in ("content", "text", "message", "value", "data")), None)

        if not role_col or not content_col:
            return []

        cursor.execute(f"SELECT * FROM {table}")
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            role = str(row_dict.get(role_col) or "unknown")
            raw_content = row_dict.get(content_col)
            if raw_content is None:
                continue

            if isinstance(raw_content, str):
                if raw_content.startswith("{"):
                    parsed = parse_jsonl_line(raw_content, source=source)
                    if parsed:
                        blocks.extend(parsed)
                        continue
                texts = [raw_content]
            elif isinstance(raw_content, list):
                texts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in raw_content]
            else:
                texts = [str(raw_content)]

            combined = "\n".join(t for t in texts if t.strip())
            if combined.strip():
                blocks.append({"role": _normalize_role(role), "text": combined.strip(), "source": source})
    except sqlite3.Error:
        pass
    return blocks


def _normalize_role(role: str) -> str:
    """将各种角色字符串标准化为 user/assistant/unknown。"""
    r = role.lower()
    if r in ("user", "human", "提问者"):
        return "user"
    if r in ("assistant", "ai", "cursor", "assistant:", "cursor:"):
        return "assistant"
    return "unknown"


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
