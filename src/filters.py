"""
filters.py — 过滤噪音句子

过滤规则：
  - 太短（< 10 字符）或太长（> 200 字符）
  - 纯代码行
  - diff / patch 行
  - 正则字面量 / 源码字符串列表项
  - 调试输出行（含 score/category 前缀）
  - 文件路径
  - 命令行命令
  - URL
  - JSON 行
  - 日志行（含时间戳）
  - Stack trace
  - 无意义礼貌短句
  - 纯数字 / 纯标点
"""

import re

# ── 编译正则（模块级缓存）─────────────────────────────────────────────

# URL
_RE_URL = re.compile(r'https?://\S+|www\.\S+', re.I)

# ANSI 颜色/控制码
_RE_ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

# 文件路径（绝对路径 / 相对路径）
_RE_PATH = re.compile(r'(?:^|[\s])(?:/[\w.\-/]+|\.{1,2}/[\w.\-/]+|[A-Za-z]:\\[\w.\-\\]+)')

# 命令行命令（以 $ / # / > 开头，或 cd/ls/git/pip/npm/curl/wget 开头）
_RE_COMMAND = re.compile(
    r'^[\$#>]\s|^(?:cd|ls|ll|pwd|git|pip|pip3|npm|yarn|python|python3|node|'
    r'curl|wget|make|cargo|go|java|mvn|gradle|docker|kubectl|helm|'
    r'cat|grep|sed|awk|find|rm|cp|mv|mkdir|touch|echo|export|source|'
    r'which|chmod|chown|ps|kill|top|df|du)\s',
    re.I
)

# JSON 行（以 { 或 [ 开头，以 } 或 ] 结尾）
_RE_JSON = re.compile(r'^\s*[\[{].*[\]}]\s*$', re.S)

# 日志行（含时间戳或日志级别）
_RE_LOG = re.compile(
    r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'  # ISO 时间戳
    r'|\b(?:DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE|CRITICAL)\b'
    r'|\[\d{2}:\d{2}:\d{2}\]'
    r'|^\s*at\s+[\w.<>]+\(.*:\d+\)',              # Stack trace
)

# 纯代码特征（以编程符号为主）
_RE_CODE_LINE = re.compile(
    r'^(?:import |from |#include |using |require\(|def |class |function |'
    r'const |let |var |public |private |protected |static |return |if\s*\(|'
    r'for\s*\(|while\s*\(|try\s*\{|catch\s*\(|throw |async |await )'
    r'|^[\w.]+\(.*\)\s*[{;]?\s*$'  # 函数调用行
    r'|[{}]\s*$'                    # 只有大括号的行
)

# diff / patch 行
_RE_DIFF_LINE = re.compile(
    r'^(?:\+\+\+|---|@@ )'
    r'|^[+-]\s{0,4}(?:r?[\'"]|\d+\s+[\'"])'
    r'|^\d+\s+[+-]\s+'
)
_RE_MARKDOWN_BULLET = re.compile(r'^\s*[-*+]\s+')

# Python/JS 风格源码字符串或正则字面量
_RE_LITERAL_LINE = re.compile(
    r'^\s*(?:\d+\s+)?(?:[+-]\s*)?(?:[rubf]+)?[\'"].*[\'"]\s*,?\s*$',
    re.I
)
_RE_ESCAPED_LITERAL_LINE = re.compile(
    r'^\s*(?:\d+\s+)?(?:[+-]\s*)?\\[\'"].*',
    re.I
)
_RE_UNBALANCED_QUOTE_LINE = re.compile(
    r'^\s*(?:\d+\s+)?(?:[+-]\s*)?[\'"].*$'
)
_RE_CODE_STRING_PREFIX = re.compile(
    r'^\s*(?:[rubf]+)?[\'"]|^\s*r[\'"]',
    re.I
)
_RE_RAW_LITERAL_PREFIX = re.compile(r'^\s*[+-]?\s*r[\'"]', re.I)
_RE_REGEX_LITERAL = re.compile(
    r'^\s*(?:\d+\s+)?(?:[+-]\s*)?r[\'"].*(?:\||\\).*[\'"]\s*,?\s*$',
    re.I
)

# 带 score/category 的调试输出行
_RE_DEBUG_SCORE = re.compile(
    r'^\s*\d+\.\s+\d+(?:\.\d+)?\s+'
    r'(?:decision|risk_control|developer_style|general)\b',
    re.I
)
_RE_RESULT_META = re.compile(
    r'^\s*\[(?:风险控制|开发者风格|工程决策|普通高分)\]\s+score='
    r'|^\s*工程判断金句(?:\s*/\s*Engineering Quotes)?\s*$',
    re.I
)
_RE_BOOL_PREFIX = re.compile(r'^\s*(?:True|False)\s+', re.I)
_RE_ENUM_PREFIX = re.compile(r'^\s*\d+\.\s+')

# 无意义短句（白名单排除）
_NOISE_PHRASES = frozenset([
    "好的", "可以", "明白了", "收到", "好", "嗯", "哦", "了解", "明白",
    "好的好的", "没问题", "ok", "okay", "sure", "yes", "no", "got it",
    "understood", "alright", "great", "thanks", "thank you", "谢谢",
    "对", "是的", "不是", "是", "不", "行", "好吧", "那好",
])

_NOISE_SUBSTRINGS = (
    "我还做了定向验证",
    "像你贴出来的这些脏行",
    "输出文件位于",
    "已导出:",
)

# 纯数字 / 纯标点 / 纯符号
_RE_NON_TEXT = re.compile(r'^[\d\s\W]+$')

# 最小/最大长度
MIN_LEN = 10
MAX_LEN = 200


def filter_sentences(sentences: list[str]) -> list[str]:
    """对句子列表做清洗和噪音过滤，返回通过过滤的句子。"""
    results: list[str] = []
    for sent in sentences:
        normalized = normalize_sentence(sent)
        if normalized and _is_valid(normalized):
            results.append(normalized)
    return results


def normalize_sentence(sent: str) -> str:
    """归一化候选句，去除 ANSI、调试前缀和常见转义噪音。"""
    s = sent.strip()
    if not s:
        return ""

    s = _RE_ANSI.sub("", s).strip()
    for _ in range(3):
        s = _RE_ENUM_PREFIX.sub("", s).strip()
        s = _RE_BOOL_PREFIX.sub("", s).strip()

    # 常见终端/调试输出前缀，例如 "12. 24.0 developer_style ..."
    s = re.sub(
        r'^\s*\d+(?:\.\d+)?\s+(?:decision|risk_control|developer_style|general)\s+',
        "",
        s,
        flags=re.I,
    ).strip()

    s = s.replace(r"\n", " ").replace(r"\t", " ").strip()

    # 去掉外层转义和引号噪音
    s = s.replace(r"\'", "'").replace(r"\"", '"').replace(r"\\", "\\").strip()
    for _ in range(3):
        s = s.lstrip("`'\" ,，").rstrip("`'\" ,，").strip()

    s = re.sub(r"\s+", " ", s).strip()

    return s


def _is_valid(sent: str) -> bool:
    """判断一条句子是否有价值（True = 保留）。"""
    s = sent.strip()

    # 长度检查
    if len(s) < MIN_LEN or len(s) > MAX_LEN:
        return False

    # 无意义短句
    if s.lower().rstrip("。！？!?.…~～") in _NOISE_PHRASES:
        return False
    if any(token in s for token in _NOISE_SUBSTRINGS):
        return False

    # 纯数字/符号
    if _RE_NON_TEXT.match(s):
        return False

    # markdown 列表项
    if _RE_MARKDOWN_BULLET.match(s):
        return False

    # 反引号不配平，通常是代码示例或残句
    if s.count("`") % 2 == 1:
        return False

    # URL
    if _RE_URL.search(s) and len(s) < 80:
        # 短 URL 行过滤，长文中嵌入的 URL 不影响
        return False

    # JSON 行
    if _RE_JSON.match(s):
        return False

    # 命令行
    if _RE_COMMAND.match(s):
        return False

    # 日志行 / stack trace
    if _RE_LOG.search(s):
        return False

    # 纯代码行
    if _RE_CODE_LINE.match(s):
        return False

    # diff / patch 行
    if _RE_DIFF_LINE.match(s):
        return False

    # 调试输出行（例如 "12. 24.0 developer_style ..."）
    if _RE_DEBUG_SCORE.match(s):
        return False
    if _RE_RESULT_META.match(s):
        return False

    # 代码字符串字面量 / 正则字面量
    if _RE_REGEX_LITERAL.match(s):
        return False
    if _RE_RAW_LITERAL_PREFIX.match(s):
        return False
    if _RE_ESCAPED_LITERAL_LINE.match(s):
        return False
    if _RE_CODE_STRING_PREFIX.match(s):
        if "|" in s or "\\n" in s or "\\t" in s:
            return False
    if _RE_UNBALANCED_QUOTE_LINE.match(s):
        single_quotes = s.count("'")
        double_quotes = s.count('"')
        if single_quotes % 2 == 1 or double_quotes % 2 == 1:
            return False
    if _RE_LITERAL_LINE.match(s):
        inner = s.strip()
        quote_count = inner.count('"') + inner.count("'")
        comma_count = inner.count(",")
        pipe_count = inner.count("|")
        backslash_count = inner.count("\\")
        if comma_count >= 1 or pipe_count >= 1 or backslash_count >= 1 or quote_count >= 4:
            return False

    # 文件路径（路径占句子 50% 以上）
    path_matches = _RE_PATH.findall(s)
    if path_matches and sum(len(m) for m in path_matches) / len(s) > 0.5:
        return False

    return True
