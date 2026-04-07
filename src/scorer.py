"""
scorer.py — 基于规则的句子打分引擎

打分维度：
  1. 长度适中加分
  2. 约束词加分
  3. 动作词加分
  4. 风险词加分
  5. 架构词加分
  6. 第一人称工程表达加分
  7. 组合命中额外加分（约束词+动作词 / 动作词+风险词）
  8. 含逗号/分句适度加分
  9. 纯英文弱化（中文语境为主）
"""

import re

# ── 词表定义 ───────────────────────────────────────────────────────────

# 约束词：表达限制、保守策略
CONSTRAINT_WORDS = [
    "不改", "不要", "不动", "不影响", "不暴露", "不扩散", "不破坏",
    "尽量", "先", "只做", "只改", "只处理", "优先", "保持", "避免",
    "不引入", "最小化", "最少", "不依赖", "不暴漏", "不涉及",
    "仅", "单一", "不超过", "不超", "保守",
]

# 动作词：工程操作动词
ACTION_WORDS = [
    "收口", "封装", "抽离", "隔离", "兼容", "迁移", "替换", "下沉",
    "兜底", "重构", "拆分", "合并", "收敛", "下放", "上移", "剥离",
    "解耦", "内聚", "收拢", "归并", "抽象", "沉淀", "统一", "规范",
    "对齐", "收紧", "放开", "切换", "灰度", "降级", "熔断", "限流",
    "回滚", "降低", "提升", "裁剪", "精简",
]

# 风险词：表达风险意识
RISK_WORDS = [
    "风险", "影响", "扩散", "调用方", "调用层", "协议", "对外接口",
    "稳定", "回滚", "边界", "副作用", "破坏", "兼容性", "耦合",
    "崩溃", "异常", "失败", "降级", "熔断", "泄漏", "污染",
    "不可控", "不确定", "敏感", "危险", "破坏性",
]

# 架构词：表达架构层面的思考
ARCH_WORDS = [
    "service", "repository", "adapter", "facade", "domain", "controller",
    "manager", "gateway", "handler", "provider", "factory", "registry",
    "接口", "协议", "层", "实现层", "调用层", "服务层", "数据层",
    "展示层", "基础设施", "领域", "聚合", "上下文", "边界",
    "模块", "组件", "抽象层", "适配器", "代理",
]

# 第一人称工程表达
FIRST_PERSON_ENGINEERING = [
    "我要", "我先", "我主要是想", "我不想", "我打算", "我需要",
    "这一版", "第一刀", "第一步", "这一步", "当前这版",
    "我的思路", "我的方案", "我倾向", "我希望",
]

# ── 正则编译 ────────────────────────────────────────────────────────────

def _build_pattern(words: list[str]) -> re.Pattern:
    escaped = [re.escape(w) for w in sorted(words, key=len, reverse=True)]
    return re.compile("|".join(escaped), re.I)

_PAT_CONSTRAINT = _build_pattern(CONSTRAINT_WORDS)
_PAT_ACTION = _build_pattern(ACTION_WORDS)
_PAT_RISK = _build_pattern(RISK_WORDS)
_PAT_ARCH = _build_pattern(ARCH_WORDS)
_PAT_FIRST_PERSON = _build_pattern(FIRST_PERSON_ENGINEERING)

# 分句标志（逗号、顿号、分号）
_PAT_CLAUSE = re.compile(r'[，,、；;]')


# ── 打分函数 ────────────────────────────────────────────────────────────

def score_sentence(sent: str) -> float:
    """
    对单条句子打分，返回浮点分数。
    分数越高，句子越像工程判断金句。
    """
    score = 0.0
    s = sent.strip()

    # 1. 长度适中加分（20-80 字为最佳区间）
    length = len(s)
    if 20 <= length <= 50:
        score += 2.0
    elif 51 <= length <= 80:
        score += 1.5
    elif 10 <= length < 20:
        score += 0.5
    elif 80 < length <= 120:
        score += 0.5
    # 120+ 字不加分（过长则信息密度低）

    # 2. 约束词
    constraint_hits = _PAT_CONSTRAINT.findall(s)
    score += min(len(constraint_hits) * 1.5, 4.5)

    # 3. 动作词
    action_hits = _PAT_ACTION.findall(s)
    score += min(len(action_hits) * 2.0, 6.0)

    # 4. 风险词
    risk_hits = _PAT_RISK.findall(s)
    score += min(len(risk_hits) * 1.5, 4.5)

    # 5. 架构词
    arch_hits = _PAT_ARCH.findall(s)
    score += min(len(arch_hits) * 1.0, 3.0)

    # 6. 第一人称工程表达
    fp_hits = _PAT_FIRST_PERSON.findall(s)
    score += min(len(fp_hits) * 2.0, 4.0)

    # 7. 组合命中额外加分
    if constraint_hits and action_hits:
        score += 3.0   # 约束词 + 动作词：最核心的工程判断句
    if action_hits and risk_hits:
        score += 2.0   # 动作词 + 风险词：风险意识句
    if constraint_hits and risk_hits:
        score += 1.5   # 约束词 + 风险词

    # 8. 含分句加分（通常说明表达更完整）
    clause_count = len(_PAT_CLAUSE.findall(s))
    if clause_count >= 1:
        score += 0.5
    if clause_count >= 2:
        score += 0.5

    # 9. 纯英文弱化（中文工程对话为主场景）
    chinese_chars = sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
    if chinese_chars == 0 and len(s) > 15:
        score *= 0.6  # 纯英文降权

    return round(score, 2)
