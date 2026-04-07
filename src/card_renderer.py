"""
card_renderer.py — 生成社交分享图片卡片（需要 Pillow）

设计语言：深色背景 + 等宽字体 + 分类色标签
尺寸：1080 × 1350（竖版适合小红书/朋友圈）
"""

from pathlib import Path
from src.models import QuoteCandidate

# 类别颜色（RGB）
_CATEGORY_COLOR_RGB = {
    "decision":        (64, 196, 255),    # 蓝青
    "risk_control":    (255, 100, 100),   # 红
    "developer_style": (255, 200, 64),    # 黄
    "general":         (180, 180, 180),   # 灰
}

_CATEGORY_LABEL_ZH = {
    "decision":        "工程决策",
    "risk_control":    "风险控制",
    "developer_style": "开发者风格",
    "general":         "普通高分",
}

# 背景色
BG_COLOR = (14, 17, 23)        # GitHub dark
CARD_COLOR = (22, 27, 34)      # 卡片背景
BORDER_COLOR = (48, 54, 61)    # 分隔线
TEXT_COLOR = (230, 237, 243)   # 主文字
MUTED_COLOR = (110, 118, 129)  # 次级文字


def render_card(candidates: list[QuoteCandidate], output_path: Path) -> None:
    """生成社交卡片图片。"""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1350
    PADDING = 72
    CARD_RADIUS = 16

    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── 字体 ────────────────────────────────────────────────────────────
    font_title = _load_font(size=40, bold=True)
    font_quote = _load_font(size=34)
    font_meta = _load_font(size=26)
    font_watermark = _load_font(size=22)

    # ── 标题 ─────────────────────────────────────────────────────────────
    title = "Engineering Quotes"
    draw.text((PADDING, 60), title, font=font_title, fill=TEXT_COLOR)
    subtitle = "工程判断金句 · quote_miner"
    draw.text((PADDING, 108), subtitle, font=font_meta, fill=MUTED_COLOR)

    # 分隔线
    draw.line([(PADDING, 158), (W - PADDING, 158)], fill=BORDER_COLOR, width=1)

    # ── 句子卡片 ─────────────────────────────────────────────────────────
    y = 180
    card_h = (H - y - 60 - PADDING) // max(len(candidates), 1)
    card_h = min(card_h, 220)  # 单卡最高 220px

    for c in candidates[:5]:
        cat_color = _CATEGORY_COLOR_RGB.get(c.category, (180, 180, 180))
        cat_label = _CATEGORY_LABEL_ZH.get(c.category, c.category)

        # 卡片背景
        card_rect = [PADDING, y, W - PADDING, y + card_h - 12]
        _draw_rounded_rect(draw, card_rect, CARD_COLOR, CARD_RADIUS)

        # 左侧色条
        draw.rectangle([PADDING, y, PADDING + 4, y + card_h - 12], fill=cat_color)

        # 类别标签
        draw.text((PADDING + 20, y + 14), cat_label, font=font_meta, fill=cat_color)

        # 句子文本（自动换行）
        quote_lines = _wrap_text(c.text, font_quote, W - PADDING * 2 - 40)
        text_y = y + 46
        for line in quote_lines[:3]:  # 最多 3 行
            draw.text((PADDING + 20, text_y), line, font=font_quote, fill=TEXT_COLOR)
            text_y += 42

        # 分数
        score_text = f"score {c.score:.1f}"
        draw.text((W - PADDING - 120, y + 14), score_text,
                  font=font_meta, fill=MUTED_COLOR)

        y += card_h

    # ── 水印 ─────────────────────────────────────────────────────────────
    wm = "github.com/yourname/quote_miner"
    wm_w = _text_width(draw, wm, font_watermark)
    draw.text((W - PADDING - wm_w, H - 44), wm,
              font=font_watermark, fill=MUTED_COLOR)

    img.save(str(output_path), "PNG", quality=95)


# ── 辅助函数 ────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False):
    """加载字体，找不到系统字体时降级为默认字体。"""
    from PIL import ImageFont
    import os

    candidates = [
        # macOS
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode MS.ttf",
        # Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # 降级：PIL 内置字体
    return ImageFont.load_default()


def _draw_rounded_rect(draw, rect, color, radius):
    """绘制圆角矩形。"""
    from PIL import ImageDraw
    x1, y1, x2, y2 = rect
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=color)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=color)
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=color)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=color)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=color)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=color)


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """将文本按最大宽度自动换行（字符级）。"""
    from PIL import Image, ImageDraw
    # 用临时 draw 对象测量
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    lines: list[str] = []
    current = ""
    for char in text:
        test = current + char
        w = _text_width(tmp, test, font)
        if w > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _text_width(draw, text: str, font) -> int:
    """获取文本渲染宽度，兼容新旧 Pillow API。"""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    except AttributeError:
        w, _ = draw.textsize(text, font=font)
        return w
