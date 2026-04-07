# quote_miner

> 从 Codex / Claude Code 对话日志中自动提取「工程判断金句」

不做词云，不做摘要——只从原始对话中筛选出**本身就像工程师做判断时说的话**的句子，保留原话风格，直接可用于社交平台分享。

---

## 示例输出

```
 1. 第一刀只做收口，不改协议和对外接口。
    ⚙️ 工程决策  score=14.5  role=assistant

 2. 尽量把风险压在实现层，不要扩散到调用方。
    🛡️ 风险控制  score=13.0  role=assistant

 3. 这一版不动外部行为，先把内部边界收住。
    💬 开发者风格  score=11.5  role=assistant

 4. 先兼容旧逻辑，后面再慢慢清理。
    ⚙️ 工程决策  score=9.0  role=assistant
```

---

## 安装

```bash
# 克隆项目
git clone https://github.com/wangjianqi/quote_miner.git
cd quote_miner

# 无需额外安装（核心功能使用 Python 标准库）
# 可选：生成图片卡片需要 Pillow
pip install Pillow
```

**依赖要求：Python 3.11+，无需数据库，无需网络。**

---

## 使用方式

### 基本用法

```bash
# 从 txt/md/jsonl 文件提取
python main.py --input sample_data/sample_chat.txt

# 从 jsonl 文件提取
python main.py --input sample_data/sample_chat.jsonl

# 自动扫描 Codex 日志（~/.codex/sessions/）
python main.py --source codex

# 自动扫描 Claude Code 日志（~/.claude/）
python main.py --source claude
```

### 过滤选项

```bash
# 只看 assistant 的发言
python main.py --input chat.txt --role assistant

# 只看风险控制类句子
python main.py --input chat.txt --category risk_control

# 输出前 20 条
python main.py --input chat.txt --top 20
```

### 输出选项

```bash
# 生成社交卡片图片（需要 Pillow）
python main.py --input chat.txt --render-card

# 自定义输出目录
python main.py --input chat.txt --output-dir my_output
```

---

## 支持的数据源

| 来源 | 说明 |
|------|------|
| `--input file.txt` | 纯文本对话文件 |
| `--input file.md` | Markdown 格式对话文件 |
| `--input file.jsonl` | JSONL 格式日志（Codex / Claude Code 原始格式） |
| `--source codex` | 自动扫描 `~/.codex/sessions/` 下所有 jsonl |
| `--source claude` | 自动扫描 `~/.claude/` 下所有 jsonl 和 txt |
| `--source cursor` | 自动扫描 `~/.config/Cursor/User/workspaceStorage/` 下所有 SQLite state.vscdb |

---

## 完整命令参考

```
usage: main.py [-h] (--input FILE | --source {codex,claude,cursor})
               [--role {all,user,assistant}]
               [--category {decision,risk_control,developer_style,general,all}]
               [--top N] [--render-card] [--output-dir DIR]

选项:
  --input FILE          读取 txt / md / jsonl 文件
  --source {codex,claude,cursor}
                        自动扫描本地日志目录
  --role {all,user,assistant}
                        只提取指定角色的发言（默认: all）
  --category {decision,risk_control,developer_style,general,all}
                        只输出指定类别（默认: all）
  --top N               输出前 N 条句子（默认: 15）
  --render-card         生成社交分享图片卡片
  --output-dir DIR      输出目录（默认: output）
```

---

## 输出文件

运行后自动在 `output/` 目录生成：

| 文件 | 说明 |
|------|------|
| `quotes.txt` | 纯文本格式，含分类和评分 |
| `quotes.md` | Markdown 格式，按类别分组 |
| `social_card.png` | 社交分享卡片（`--render-card` 时生成） |

---

## 句子分类说明

| 类别 | emoji | 说明 | 典型词汇 |
|------|-------|------|----------|
| `decision` | ⚙️ | 工程决策句 | 收口、封装、抽离、解耦、重构 |
| `risk_control` | 🛡️ | 风险控制句 | 风险、回滚、兜底、边界、兼容性 |
| `developer_style` | 💬 | 开发者风格句 | 我要、这一版、第一刀、说白了 |
| `general` | 📌 | 普通高分句 | 其他高分但分类不明确的句子 |

---

## 项目结构

```
quote_miner/
├── main.py                  # CLI 入口，参数解析和流程编排
├── requirements.txt
├── README.md
├── src/
│   ├── models.py            # QuoteCandidate dataclass
│   ├── loader.py            # 数据加载（文件 / codex / claude）
│   ├── parser.py            # JSONL / 纯文本解析
│   ├── sentence_splitter.py # 文本切句
│   ├── filters.py           # 噪音过滤
│   ├── scorer.py            # 规则打分
│   ├── classifier.py        # 类别分类
│   ├── exporter.py          # 终端 / txt / md 输出
│   └── card_renderer.py     # 图片卡片生成（Pillow）
├── sample_data/
│   ├── sample_chat.txt      # 示例纯文本对话
│   └── sample_chat.jsonl    # 示例 JSONL 日志
└── output/                  # 运行后自动生成
    ├── quotes.txt
    ├── quotes.md
    └── social_card.png
```

---

## 后续规划

- [x] 支持 Cursor 数据源（SQLite state.vscdb）
- [ ] 支持更多 JSONL schema（Continue 等）
- [ ] 句子去重增强（语义级别）
- [ ] 支持批量导出为 CSV
- [ ] 支持 --min-score 阈值过滤
- [ ] 多语言支持（英文工程日志）
- [ ] 可配置词表（自定义加分词）
- [ ] 支持从剪贴板读取输入

---

## License

MIT
