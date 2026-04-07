# 工程判断金句

> 从 Codex / Claude Code 对话日志中自动提取的工程决策句和风险控制句。

## 🛡️ 风险控制

> 优先保持调用链不断，不要因为重构影响现有功能的稳定性。
>
> `score=18.5` `assistant`

> 不要让这次重构成为一个无法回滚的操作。
>
> `score=14.0` `assistant`

> 先把 service 层加进来，不要动 repository 层的逻辑，也不要改 controller 的调用方式，只是在中间加一个转发层。
>
> `score=13.0` `assistant`

> 任何一步出问题都要能快速回滚，不能让风险扩散到生产环境。
>
> `score=11.0` `assistant`

> 另外做好回滚方案，万一有问题能快速切回去。
>
> `score=8.0` `assistant`
