#!/usr/bin/env python3
"""
quote_miner — 从 Codex / Claude Code / Cursor 对话日志中提取工程判断金句
"""

import argparse
import sys
from pathlib import Path

from src.loader import load_from_file, load_from_codex, load_from_claude, load_from_cursor
from src.sentence_splitter import split_sentences
from src.filters import filter_sentences
from src.scorer import score_sentence
from src.classifier import classify_sentence
from src.exporter import export_txt, export_md, print_terminal
from src.models import QuoteCandidate


def build_candidates(raw_text_blocks: list[dict], role_filter: str) -> list[QuoteCandidate]:
    """从原始消息块中构建候选句列表。"""
    candidates: list[QuoteCandidate] = []
    seen: set[str] = set()

    for block in raw_text_blocks:
        role = block.get("role", "unknown")
        if role_filter != "all" and role != role_filter:
            continue

        text = block.get("text", "")
        sentences = split_sentences(text)
        filtered = filter_sentences(sentences)

        for sent in filtered:
            # 去重
            key = sent.strip()
            if key in seen:
                continue
            seen.add(key)

            score = score_sentence(sent)
            if score <= 0:
                continue

            category = classify_sentence(sent)
            candidates.append(QuoteCandidate(
                text=sent.strip(),
                score=score,
                category=category,
                role=role,
                source=block.get("source", ""),
            ))

    return sorted(candidates, key=lambda c: c.score, reverse=True)


def main():
    parser = argparse.ArgumentParser(
        description="从 Codex / Claude Code / Cursor 对话日志中提取工程判断金句",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --input chat.txt
  python main.py --source codex --top 20
  python main.py --source claude --category risk_control
  python main.py --source cursor --category risk_control
  python main.py --input log.jsonl --role assistant --render-card
        """
    )

    # 输入来源
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", metavar="FILE", help="读取 txt / md / jsonl 文件")
    group.add_argument("--source", choices=["codex", "claude", "cursor"], help="自动扫描本地日志目录")

    # 过滤选项
    parser.add_argument("--role", choices=["all", "user", "assistant"], default="all",
                        help="只提取指定角色的发言（默认: all）")
    parser.add_argument("--category", choices=["decision", "risk_control", "developer_style", "general", "all"],
                        default="all", help="只输出指定类别（默认: all）")
    parser.add_argument("--top", type=int, default=15, metavar="N",
                        help="输出前 N 条句子（默认: 15）")

    # 输出选项
    parser.add_argument("--render-card", action="store_true",
                        help="生成社交分享图片卡片 output/social_card.png")
    parser.add_argument("--output-dir", default="output", metavar="DIR",
                        help="输出目录（默认: output）")

    args = parser.parse_args()

    # ── 加载原始文本块 ──────────────────────────────────────────────────
    print("📂 正在加载数据源...")
    if args.input:
        raw_blocks = load_from_file(Path(args.input))
    elif args.source == "codex":
        raw_blocks = load_from_codex()
    elif args.source == "claude":
        raw_blocks = load_from_claude()
    else:
        raw_blocks = load_from_cursor()

    if not raw_blocks:
        print("❌ 未找到任何可解析的内容，请检查输入路径或数据源。", file=sys.stderr)
        sys.exit(1)

    print(f"✅ 共加载 {len(raw_blocks)} 条消息块")

    # ── 构建候选句 ─────────────────────────────────────────────────────
    print("🔍 正在提取候选句...")
    candidates = build_candidates(raw_blocks, args.role)

    # 按 category 过滤
    if args.category != "all":
        candidates = [c for c in candidates if c.category == args.category]

    top_n = candidates[:args.top]

    if not top_n:
        print("⚠️  没有找到符合条件的高分句子。", file=sys.stderr)
        sys.exit(0)

    # ── 输出 ───────────────────────────────────────────────────────────
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print_terminal(top_n)
    export_txt(top_n, output_dir / "quotes.txt")
    export_md(top_n, output_dir / "quotes.md")

    if args.render_card:
        try:
            from src.card_renderer import render_card
            card_path = output_dir / "social_card.png"
            render_card(top_n[:5], card_path)
            print(f"🎨 社交卡片已生成: {card_path}")
        except ImportError:
            print("⚠️  生成图片卡片需要安装 Pillow：pip install Pillow", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  卡片生成失败: {e}", file=sys.stderr)

    print(f"\n✅ 完成！输出文件位于 {output_dir}/")


if __name__ == "__main__":
    main()
