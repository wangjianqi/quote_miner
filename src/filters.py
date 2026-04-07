"""
filters.py — 过滤噪音句子

过滤规则：
  - 太短（< 10 字符）或太长（> 200 字符）
  - 纯代码行
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

# 无意义短句（白名单排除）
_NOISE_PHRASES = frozenset([
    "好的", "可以", "明白了", "收到", "好", "嗯", "哦", "了解", "明白",
    "好的好的", "没问题", "ok", "okay", "sure", "yes", "no", "got it",
    "understood", "alright", "great", "thanks", "thank you", "谢谢",
    "对", "是的", "不是", "是", "不", "行", "好吧", "那好",
])

# 纯数字 / 纯标点 / 纯符号
_RE_NON_TEXT = re.compile(r'^[\d\s\W]+$')

# 最小/最大长度
MIN_LEN = 10
MAX_LEN = 200


def filter_sentences(sentences: list[str]) -> list[str]:
    """对句子列表做噪音过滤，返回通过过滤的句子。"""
    return [s for s in sentences if _is_valid(s)]


def _is_valid(sent: str) -> bool:
    """判断一条句子是否有价值（True = 保留）。"""
    s = sent.strip()

    # 长度检查
    if len(s) < MIN_LEN or len(s) > MAX_LEN:
        return False

    # 无意义短句
    if s.lower().rstrip("。！？!?.…~～") in _NOISE_PHRASES:
        return False

    # 纯数字/符号
    if _RE_NON_TEXT.match(s):
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

    # 文件路径（路径占句子 50% 以上）
    path_matches = _RE_PATH.findall(s)
    if path_matches and sum(len(m) for m in path_matches) / len(s) > 0.5:
        return False

    return True
