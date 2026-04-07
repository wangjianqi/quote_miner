"""
classifier.py — 句子类别分类器

基于规则，将候选句划分为四类：
  - decision：工程决策句
  - risk_control：风险控制句
  - developer_style：开发者风格句（第一人称 / 个人判断）
  - general：普通高分句
"""

import re
from src.scorer import (
    _PAT_CONSTRAINT, _PAT_ACTION, _PAT_RISK,
    _PAT_FIRST_PERSON, _PAT_ARCH
)

# 风险控制专属词（高权重）
_RISK_CONTROL_SPECIFIC = re.compile(
    r'风险|回滚|兜底|降级|熔断|边界|副作用|兼容性|对外接口|调用方|协议|稳定|不扩散|不影响',
    re.I
)

# 开发者风格专属词（第一人称 + 口语化判断）
_DEV_STYLE_SPECIFIC = re.compile(
    r'我要|我先|我打算|我不想|这一版|第一刀|第一步|我的思路|我倾向|我觉得|我认为|'
    r'感觉|其实|说白了|换句话说|本质上|核心是|关键在于',
    re.I
)

# 决策句专属词（方案/策略选择）
_DECISION_SPECIFIC = re.compile(
    r'收口|封装|抽离|隔离|拆分|解耦|重构|统一|规范|迁移|替换|收敛|'
    r'方案|策略|原则|架构|设计|接口|层|模块|约束|规则',
    re.I
)


def classify_sentence(sent: str) -> str:
    """
    返回句子类别字符串。
    优先级：developer_style > risk_control > decision > general
    """
    s = sent.strip()

    has_risk = bool(_RISK_CONTROL_SPECIFIC.search(s))
    has_dev_style = bool(_DEV_STYLE_SPECIFIC.search(s))
    has_action = bool(_PAT_ACTION.search(s))
    has_decision = bool(_DECISION_SPECIFIC.search(s))

    # 开发者风格句（第一人称 + 个人判断语气）
    if has_dev_style:
        return "developer_style"

    # 风险控制句（含明确风险词）
    if has_risk:
        return "risk_control"

    # 工程决策句（含动作词 + 决策词）
    if has_action or has_decision:
        return "decision"

    return "general"
