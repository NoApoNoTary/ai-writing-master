# 写作模式选择

## Canonical prompt

这是完整写作入口唯一的模式选择文案。其他文档只引用本文件，不复制这段文本。

```text
请选择本次写作模式：
1. 快速草稿：单 Agent，最少调研与一次审校，适合先拿到可讨论版本。
2. 标准写作（推荐）：单 Agent，完整调研、素材规划、写作与三层审校。
3. 深度写作：多 Agent 分工，独立研究、策划、写作和审计，适合重要长文。
注：深度执行仅在本次 capability preflight 检出真实 Handoff Runtime 后可用。
```

## 入口规则

新建完整文章时，模式选择是第一道闸门。用户未在当前请求中明确模式时，发送下面的固定问题并等待回复：

发送上面的 Canonical prompt，不要在其他文件重新编写选项文案。

规则：

- 不根据题目、字数、平台、时限或用户身份代选。
- 用户已说“快速写”“标准模式”“深度写稿”“多 Agent 写”等明确表述时，视为已选择。
- “继续上次”读取 `status.json.mode`，不重复询问。
- 单一模块请求和 `writing-rewrite` 路由按用户当前指令执行；升级为端到端新文章时再触发模式选择。
- 用户只回复序号时：`1=quick`、`2=standard`、`3=deep`。

## 深度执行可用性闸门

选择 `deep` 只表示用户选择了工作深度，不表示当前宿主已经完成多 Agent 执行。开题阶段必须把实际能力预检结果写入 `capability-preflight.md`：

```yaml
handoff_runtime: available | unavailable
```

只有当前宿主的**真实 Handoff Runtime** 可执行本次角色交接时才记录 `available`。角色卡、协议文档、命令名称或配置片段都不是可用性的证据。

- `available`：才可进入深度模式的 Lead/角色交接流程。
- `unavailable`：向用户显示“深度执行当前不可用”；不创建模拟角色、不把单 Agent 结果标成深度结果。等待用户选择 quick、standard 或取消。

本闸门只报告本次运行时的事实，不对 Handoff Runtime 是否已实现作泛化声明。

## 模式合同

### 1. 快速草稿（quick）

- 执行：当前 Agent。
- 目标：尽快形成有依据、可讨论的完整版本。
- 产物：简版 Brief、关键来源/主张、简版大纲、`draft-v1.md`、一次合并审校、`final.md`。
- 调研：仅覆盖正文实际使用的关键事实；近期或易变化信息仍实时核验。
- 用户确认：主题存在明显分叉时确认角度；其余环节连续推进。
- Baoyu：照常做早期 capability/material preflight；只有明确需要且视觉闸门通过后才生产。

### 2. 标准写作（standard）

- 执行：当前 Agent，不创建子代理。
- 目标：完成可发布的常规文章。
- 产物：完整 Brief、`sources.yaml`、`claims.yaml`、`asset-manifest.yaml`、选题、大纲、storyboard、初稿、三层审校、标题、验收报告。
- 调研：事实与素材双轨进行。
- 用户确认：核心角度、最终标题、发布动作。
- Baoyu：早期预检和素材摄入；文章结构稳定后按需生产。

### 3. 深度写作（deep）

- 执行：仅当 capability preflight 的 `handoff_runtime=available` 时，Lead Agent 才调度 fresh-context 专项代理；否则深度执行状态为 `unavailable`。
- 目标：通过角色隔离提高重要长文的研究、判断与审校质量。
- 产物：实际执行成功时，与标准模式相同，额外保留各代理的结构化报告和输入 hash。
- 调研：Researcher 独立维护事实和素材清单。
- 策划：Editorial Strategist 基于已核验证据形成角度、读者决策和 storyboard。
- 写作：Writer 只读取接受后的内容包。
- 审校：Auditor 首轮不读取 Writer 的解释和父对话全文。
- Baoyu：由 Lead 统一执行预检和闸门；子代理只产出计划与 manifest。

完整协议见 `agent-orchestration.md`。

## 模式保持与变更

- 模式写入 `status.json` 后贯穿该任务。
- 用户可明确要求从 quick 升为 standard/deep，或从 deep 收缩为 standard。
- 变更时记录 `mode_history`、变更时间、原因和从哪个阶段继续。
- 从单 Agent 升到 deep 时，子代理只接收已有文件产物，不复制完整父对话。
