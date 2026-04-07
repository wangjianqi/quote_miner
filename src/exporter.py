"""
exporter.py — 输出模块

支持：
  - 终端彩色打印
  - output/quotes.txt
  - output/quotes.md
"""

from pathlib import Path
from src.models import QuoteCandidate

# 类别颜色（ANSI）
_CATEGORY_COLOR = {
    "decision":       "\033[36m",   # cyan
    "risk_control":   "\033[31m",   # red
    "developer_style": "\033[33m",  # yellow
    "general":        "\033[37m",   # white
}
_RESET = "\033[0m"
_BOLD = "\033[1m"

# 类别标签（中文）
_CATEGORY_LABEL = {
    "decision":        "工程决策",
    "risk_control":    "风险控制",
    "developer_style": "开发者风格",
    "general":         "普通高分",
}

# 类别 emoji
_CATEGORY_EMOJI = {
    "decision":        "⚙️ ",
    "risk_control":    "🛡️ ",
    "developer_style": "💬 ",
    "general":         "📌 ",
}


def print_terminal(candidates: list[QuoteCandidate]) -> None:
    """终端彩色打印 Top N 句子。"""
    print(f"\n{'━' * 60}")
    print(f"{_BOLD}  🔍 工程判断金句 Top {len(candidates)}{_RESET}")
    print(f"{'━' * 60}\n")

    for i, c in enumerate(candidates, 1):
        color = _CATEGORY_COLOR.get(c.category, "")
        label = _CATEGORY_LABEL.get(c.category, c.category)
        emoji = _CATEGORY_EMOJI.get(c.category, "")

        print(f"{_BOLD}{i:>2}.{_RESET} {c.text}")
        print(f"    {color}{emoji}{label}{_RESET}  "
              f"score={c.score:.1f}  role={c.role}")
        print()

    print(f"{'━' * 60}\n")


def export_txt(candidates: list[QuoteCandidate], path: Path) -> None:
    """导出为纯文本格式。"""
    lines: list[str] = []
    lines.append("工程判断金句 / Engineering Quotes")
    lines.append("=" * 50)
    lines.append("")

    for i, c in enumerate(candidates, 1):
        label = _CATEGORY_LABEL.get(c.category, c.category)
        lines.append(f"{i}. {c.text}")
        lines.append(f"   [{label}] score={c.score:.1f} role={c.role}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📄 已导出: {path}")


def export_md(candidates: list[QuoteCandidate], path: Path) -> None:
    """导出为 Markdown 格式，按类别分组。"""
    # 按类别分组
    groups: dict[str, list[QuoteCandidate]] = {}
    for c in candidates:
        groups.setdefault(c.category, []).append(c)

    category_order = ["decision", "risk_control", "developer_style", "general"]
    lines: list[str] = []
    lines.append("# 工程判断金句")
    lines.append("")
    lines.append("> 从 Codex / Claude Code 对话日志中自动提取的工程决策句和风险控制句。")
    lines.append("")

    for cat in category_order:
        if cat not in groups:
            continue
        label = _CATEGORY_LABEL.get(cat, cat)
        emoji = _CATEGORY_EMOJI.get(cat, "")
        lines.append(f"## {emoji}{label}")
        lines.append("")

        for c in groups[cat]:
            lines.append(f"> {c.text}")
            lines.append(f">")
            lines.append(f"> `score={c.score:.1f}` `{c.role}`")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📝 已导出: {path}")
