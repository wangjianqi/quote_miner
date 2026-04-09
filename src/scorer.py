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
  9. 中英双语支持
"""

import re

# ── 词表定义 ───────────────────────────────────────────────────────────

# 约束词：表达限制、保守策略
CONSTRAINT_WORDS = [
    "不改", "不要", "不动", "不影响", "不暴露", "不扩散", "不破坏",
    "不改接口", "不改协议", "不改调用方", "不改行为", "不改语义",
    "尽量", "先", "优先", "保持", "避免", "保守", "稳一点", "稳妥",
    "只做", "只改", "只处理", "只收口", "只兜底", "只在", "只针对",
    "先不动", "先不改", "先收口", "先兜底", "先兼容", "先保证",
    "不引入", "不依赖", "不涉及", "不穿透", "不下沉", "不上提",
    "不新增", "不新增概念", "不新增接口", "不新增依赖", "不新增字段",
    "不改变", "不改变现状", "不改变语义", "不改变链路",
    "不直接", "不直接改", "不直接暴露", "不直接依赖",
    "不耦合", "不绑定", "不侵入", "低侵入", "非侵入",
    "最小化", "最少", "最小变更", "最小修改", "最小影响", "最小范围",
    "控制范围", "收敛范围", "限制范围", "限定", "约束住",
    "仅", "仅在", "单一", "单向", "局部", "局部处理", "局部收敛",
    "不超过", "不超", "不跨", "不跨层", "不跨模块", "不出边界",
    "兼容存量", "向下兼容", "兼容老逻辑", "保持兼容",
    "以不变应万变", "按现有", "沿用", "复用现有", "基于现状",
    "必要时", "兜住", "卡住", "守住", "先保住",
    "不暴漏",
    "avoid", "keep", "preserve", "minimize", "minimal",
    "as is", "for now", "first", "prefer", "prefer to",
    "do not change", "don't change", "do not touch", "don't touch",
    "do not expose", "do not leak", "do not break",
    "without changing", "without breaking", "without introducing",
    "only", "only change", "only handle", "only in", "just",
    "non-invasive", "low-invasive", "minimal change", "minimal impact",
    "keep compatibility", "backward compatible", "preserve behavior",
    "preserve semantics", "stay compatible", "limit the scope",
    "within the boundary", "reuse existing", "based on existing",
]

# 动作词：工程操作动词
ACTION_WORDS = [
    "收口", "封装", "抽离", "隔离", "兼容", "迁移", "替换", "下沉",
    "上提", "上移", "下放", "前移", "后置", "前置",
    "兜底", "托底", "拦住", "拦截", "短路", "旁路",
    "重构", "拆分", "合并", "收敛", "收拢", "归并", "归一", "统一",
    "剥离", "解耦", "内聚", "抽象", "沉淀", "规范", "标准化",
    "对齐", "校准", "梳理", "理顺", "厘清", "收紧", "放开",
    "切换", "灰度", "降级", "熔断", "限流", "回滚", "回退",
    "降低", "提升", "优化", "裁剪", "精简", "瘦身",
    "补齐", "补全", "兜住", "覆盖", "兼容住", "适配", "适配掉",
    "治理", "修正", "修补", "修复", "消化", "吞掉", "规避",
    "拆出来", "提出来", "包一层", "兜一层", "挡一层", "抽一层",
    "落盘", "透传", "透出", "回传", "转发", "编排",
    "归口", "归档", "归类", "聚合", "编织", "拼装",
    "缓存", "预热", "削峰", "填谷", "分流", "路由", "降噪",
    "观测", "监控", "埋点", "校验", "校验掉", "判空", "判重",
    "清理", "清退", "收回", "关闭", "封禁", "止血",
    "wrap", "encapsulate", "extract", "isolate", "migrate", "replace",
    "sink", "lift", "move", "split", "merge", "converge",
    "refactor", "decouple", "abstract", "align", "normalize",
    "switch", "toggle", "degrade", "fallback", "rollback",
    "optimize", "trim", "simplify", "adapt", "patch", "fix",
    "guard", "intercept", "short-circuit", "reroute", "fan out",
    "route", "cache", "warm up", "throttle", "rate limit",
    "monitor", "observe", "instrument", "validate", "dedupe",
    "cleanup", "sunset", "deprecate", "stabilize",
]

# 风险词：表达风险意识
RISK_WORDS = [
    "风险", "影响", "扩散", "调用方", "调用层", "协议", "对外接口",
    "稳定", "稳定性", "回滚", "可回滚", "边界", "副作用", "破坏",
    "兼容性", "兼容", "耦合", "链路", "主链路", "旁路",
    "崩溃", "异常", "失败", "报错", "超时", "抖动", "雪崩",
    "降级", "熔断", "泄漏", "污染", "脏数据", "数据错乱",
    "不可控", "不确定", "敏感", "危险", "破坏性", "脆弱",
    "线上", "线上风险", "线上问题", "线上行为", "线上稳定",
    "事故", "故障", "止血", "回退", "回退成本", "恢复",
    "一致性", "幂等", "重复", "乱序", "并发", "竞态",
    "死锁", "阻塞", "积压", "穿透", "打满", "热点",
    "泄洪", "削峰", "容量", "水位", "瓶颈", "吞吐", "延迟",
    "观测", "可观测性", "监控", "告警", "漏报", "误报",
    "权限", "鉴权", "越权", "安全", "数据安全", "隐私",
    "暴露", "泄露", "入侵", "攻击面", "信任边界",
    "回归", "回归风险", "历史包袱", "存量", "老逻辑", "遗留",
    "破窗", "踩坑", "坑", "成本", "维护成本", "心智负担",
    "risk", "blast radius", "rollback", "fallback", "boundary",
    "side effect", "breaking change", "compatibility", "stable", "stability",
    "failure", "error", "timeout", "latency", "jitter", "outage",
    "exception", "crash", "leak", "data leak", "pollution",
    "inconsistent", "consistency", "idempotent", "duplicate", "reorder",
    "concurrency", "race condition", "deadlock", "blocking",
    "throughput", "capacity", "bottleneck", "hotspot", "backlog",
    "security", "privacy", "permission", "auth", "authorization",
    "monitoring", "alert", "observability", "legacy", "regression",
    "maintenance cost", "cognitive load",
]

# 架构词：表达架构层面的思考
ARCH_WORDS = [
    "service", "repository", "adapter", "facade", "domain", "controller",
    "manager", "gateway", "handler", "provider", "factory", "registry",
    "middleware", "client", "server", "model", "entity", "aggregate",
    "application", "infra", "infrastructure", "port", "usecase",
    "use case", "boundary", "context", "contract", "semantic", "semantics",
    "module", "component", "layer", "domain model", "data model",
    "object model", "application layer", "domain layer", "data layer",
    "service layer", "adapter layer", "gateway layer", "extension point",
    "pipeline", "orchestration", "runtime", "platform", "kernel",
    "接口", "协议", "层", "实现层", "调用层", "服务层", "数据层",
    "展示层", "接入层", "网关层", "领域层", "应用层", "模型层",
    "基础设施", "领域", "聚合", "上下文", "边界", "边界条件",
    "模块", "组件", "抽象层", "适配器", "代理", "门面", "仓储",
    "上下游", "链路", "主链路", "调用链", "路径", "拓扑",
    "契约", "语义", "模型", "数据模型", "领域模型", "对象模型",
    "扩展点", "插槽", "能力", "编排", "编排层", "路由",
    "内核", "壳层", "核心链路", "公共层", "公共能力", "基础能力",
    "中间件", "平台", "平台层", "容器", "运行时", "上下文隔离",
    "横切", "切面", "依赖倒置", "抽象", "实现", "实例",
]

# 第一人称工程表达
FIRST_PERSON_ENGINEERING = [
    "我要", "我先", "我主要是想", "我不想", "我打算", "我需要",
    "我倾向", "我希望", "我建议", "我考虑", "我判断", "我理解",
    "我担心", "我怕", "我宁可", "我更想", "我更倾向", "我会",
    "我这边", "我这里", "我看下来", "我现在的想法", "我的思路",
    "我的方案", "我的判断", "我的结论", "我的取舍",
    "我先收口", "我先兜底", "我先兼容", "我先不动", "我先保守一点",
    "我不想动", "我不想改", "我不想把", "我不希望",
    "我想先", "我想把", "我想收敛", "我想控制", "我想避免",
    "这一版", "这一轮", "这版", "当前这版", "当前这个版本",
    "第一刀", "第一步", "第二步", "这一步", "下一步",
    "我这里第一刀", "我这里先", "这次先", "这轮先",
    "i want to", "i want", "i plan to", "i need to", "i would",
    "i'd rather", "i would rather", "i prefer to", "i'm leaning toward",
    "i think", "i believe", "i feel", "i guess", "i worry",
    "my plan", "my approach", "my thinking", "my take", "my conclusion",
    "first step", "second step", "for this round", "for now",
]

# ── 正则编译 ────────────────────────────────────────────────────────────

def _build_pattern(words: list[str]) -> re.Pattern:
    patterns = []
    for word in sorted(set(words), key=len, reverse=True):
        if re.fullmatch(r"[A-Za-z0-9_./+-]+(?: [A-Za-z0-9_./+-]+)*", word):
            parts = [re.escape(part) for part in word.split()]
            patterns.append(
                rf"(?<![A-Za-z0-9_]){r'\s+'.join(parts)}(?![A-Za-z0-9_])"
            )
        else:
            patterns.append(re.escape(word))
    return re.compile("|".join(patterns), re.I)

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

    return round(score, 2)
