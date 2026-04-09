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
    r'风险|线上风险|回归风险|'
    r'回滚|可回滚|回退|回退成本|'
    r'兜底|托底|止血|降级|熔断|限流|'
    r'边界|边界条件|信任边界|副作用|'
    r'兼容性|兼容|向下兼容|兼容老逻辑|'
    r'对外接口|调用方|调用层|协议|契约|语义|'
    r'稳定|稳定性|线上稳定|'
    r'不扩散|不影响|不破坏|不改变语义|'
    r'异常|失败|报错|超时|抖动|雪崩|'
    r'一致性|幂等|重复|乱序|并发|竞态|死锁|阻塞|'
    r'泄漏|泄露|污染|脏数据|数据错乱|'
    r'安全|数据安全|隐私|权限|鉴权|越权|'
    r'容量|瓶颈|吞吐|延迟|热点|积压|穿透|'
    r'监控|告警|可观测性|观测|'
    r'存量|遗留|历史包袱',
    re.I
)

# 开发者风格专属词（第一人称 + 口语化判断）
_DEV_STYLE_SPECIFIC = re.compile(
    r'我要|我先|我打算|我不想|我想先|我想把|我会|'
    r'我需要|我建议|我考虑|我判断|我理解|我倾向|我更倾向|'
    r'我担心|我怕|我宁可|我希望|我不希望|我看下来|我这边|我这里|'
    r'这一版|这一轮|这版|当前这版|当前这个版本|'
    r'第一刀|第一步|第二步|这一步|下一步|'
    r'我的思路|我的方案|我的判断|我的结论|我的取舍|'
    r'我觉得|我认为|感觉|其实|说白了|换句话说|本质上|'
    r'核心是|关键在于|重点是|问题是|本质问题是|'
    r'先这么做|先这样|先保守一点|先不动|先不改',
    re.I
)

# 决策句专属词（方案/策略选择）
_DECISION_SPECIFIC = re.compile(
    r'收口|封装|抽离|隔离|拆分|解耦|重构|统一|规范|迁移|替换|收敛|'
    r'收拢|归并|归一|抽象|沉淀|对齐|梳理|理顺|厘清|'
    r'兼容|适配|治理|修复|规避|包一层|兜一层|挡一层|'
    r'上提|下沉|下放|前移|后置|切换|灰度|裁剪|精简|'
    r'方案|策略|原则|取舍|权衡|折中|路线|'
    r'架构|设计|建模|语义|契约|接口|协议|'
    r'层|实现层|调用层|服务层|数据层|接入层|应用层|领域层|'
    r'模块|组件|边界|上下文|扩展点|能力|中间件|平台|'
    r'约束|规则|范式|模式',
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
