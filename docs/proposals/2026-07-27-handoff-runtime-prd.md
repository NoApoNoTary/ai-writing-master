# Handoff Runtime MVP PRD

- 状态：P0–P2 implemented and accepted
- 日期：2026-07-27
- 目标版本：MVP-1
- 范围：深度写作模式中的角色交接、失败恢复与跨会话续跑
- 上游产品文档：[Product Capability MVP PRD](2026-07-27-product-capability-prd.md)

## Technical Codex Execution Contract

本节供负责技术方向的 Codex 会话直接读取并执行。

### Role

你是 Handoff Runtime Technical Owner。你负责实现确定性的交接、状态、校验、失败恢复和测试，不负责重新定义用户旅程、模式或产品优先级。

### Required Read Order

1. [Product Capability MVP PRD](2026-07-27-product-capability-prd.md)。
2. 本 PRD。
3. 多 Agent 协议与四张角色卡。
4. Writing Master 主 Skill 的运行约定和恢复规则。
5. 当前 CLI 调度、命令实现和测试。

仓库已建立 CodeGraph。理解或定位代码时先使用 `codegraph explore`，修改后运行 `codegraph sync`。

### Write Scope

技术 Worktree 可以修改：

- Python CLI 与运行时模块；
- Handoff、状态、hash、路径校验和原子写入相关测试；
- 多 Agent 技术协议和角色输入输出合同；
- 本 PRD 的实施状态与技术验收记录。

### Read-only Scope

- Product Capability PRD；
- 快速、标准模式的用户旅程；
- Rewrite 平台能力；
- Baoyu 产品路由；
- 用户文档和产品定位文案。

如果技术实现需要改变用户可见行为，返回 `CONFLICTING_REQUIREMENTS`，不要直接修改产品合同。

### Forbidden Scope

- 不实现 Web UI、云服务、队列、数据库或通用 DAG；
- 不增加新的 Agent 角色和平台；
- 不修改用户已有的未跟踪提案文件；
- 不把单 Agent 模拟结果记录为真实 Handoff；
- 不为第二个尚不存在的宿主建立抽象接口。

### Execution Order

1. 实施 P0 Handoff Contract、校验和原子状态写入。
2. 通过 fake host 的高层端到端测试。
3. 接入深度模式角色链，不改变 quick/standard。
4. 实施 stale、attempt 和恢复。
5. 在一个真实宿主完成验收。
6. 运行全部测试、CLI smoke test、构建和 CodeGraph sync。
7. 只提交技术 Worktree 拥有的文件。

### Stop Conditions

- Product Capability PRD 与本 PRD 对同一行为定义冲突；
- 当前宿主缺少真实子代理调用能力；
- 实现必须改动 quick/standard 的用户行为；
- 第二宿主、并行 DAG 或数据库成为必要前提；
- 连续修复仍不能通过同一高层测试。

### Done Criteria

- Manifest、Result、状态迁移和 hash 由代码验证；
- 状态使用原子写入；
- 路径越界和过期输入被阻止；
- 重试保留 attempt 历史；
- 会话恢复只依赖运行目录；
- fake host 和真实宿主验收通过；
- quick/standard 行为不变；
- 没有新增运行时第三方依赖。

### Technical Codex Final Return

```text
status: pass | pass_with_changes | block
implemented_phase:
changed_runtime_surfaces:
tests_and_evidence:
real_host_evidence:
product_conflicts:
deferred_scope:
commit:
branch:
```

## Executive Decision

当前项目已经定义了角色卡、Context Packet、输入 hash 和 Host Adapter 概念，但这些仍是文本协议。下一阶段不应继续增加 Agent 数量、角色类型或平台功能，而应先把 **handoff 变成可验证、可恢复、可审计的运行时对象**。

本 PRD 只交付一条最短闭环：Lead 准备交接包，宿主创建专项 Agent，专项 Agent 写入约定产物，运行时校验结果并推进任务状态。它既支持深度模式的角色间交接，也支持会话中断后由新的 Lead 接管任务。

## Problem Statement

用户选择深度写作，是为了获得研究、策划、写作和审计之间的上下文隔离，而不是让多个 Agent 在同一份对话里重复生成内容。

当前仓库存在以下缺口：

1. Context Packet 只有文档定义，没有机器可校验的实例格式。
2. `status.json` 由 Agent 按说明直接维护，没有原子更新、状态迁移校验和并发保护。
3. 输入 hash 已被要求记录，但没有命令负责生成、校验和识别过期交接。
4. Host Adapter 只有概念图，没有一个真实宿主上的完整调用闭环。
5. 子代理是否只读取允许输入、是否只写入自己的范围，目前依赖提示词自觉。
6. 失败、重试和中断恢复没有统一记录，容易覆盖旧产物或重复执行已完成阶段。
7. 当前测试主要验证文档中是否存在某些字符串，没有验证真实 handoff 行为。

因此，当前的多 Agent 能力属于设计合同，而不是稳定的产品能力。

## Solution

增加一个最小 Handoff Runtime，围绕两个机器可读产物工作：

1. **Handoff Manifest**：Lead 创建的不可变交接合同，声明角色、目标、允许输入、输入 hash、写入范围、预期输出和完成条件。
2. **Handoff Result**：专项 Agent 完成后形成的结果记录，声明实际输出、输出 hash、状态、问题和下一步建议。

执行流程：

```text
Lead 生成 Manifest
  → Runtime 校验输入与 hash
  → Lead 通过当前宿主原生工具创建专项 Agent
  → 专项 Agent 仅接收 role card + Manifest 中允许的输入
  → 专项 Agent 写入 write_scope
  → Runtime 校验 Result 与实际文件
  → 原子更新任务状态
  → 下一个角色读取新的已验证产物
```

首版只支持当前项目已有的四类角色，不建立通用工作流平台，不增加队列、数据库或第三方依赖。

## Goals

1. 让每次角色交接都具有可定位的输入、输出和责任边界。
2. 让错误输入、过期输入和越界输出在进入下一阶段前被发现。
3. 让深度模式在会话中断后能够从文件状态继续，而不是依赖旧对话记忆。
4. 让失败重试保留历史记录，不覆盖上一轮产物。
5. 用一个端到端行为测试证明 Researcher → Strategist → Writer → Auditor 链路可运行。
6. 保持 Python 标准库实现，不引入 YAML 解析器、工作流框架或数据库服务。

## Non-goals

1. 不构建通用 Agent 编排平台。
2. 不实现分布式任务队列、远程 Worker 或跨机器同步。
3. 不自动判断文章事实是否正确或内容是否优秀。
4. 不增加新的写作角色。
5. 不同时适配所有 Agent 宿主；首版只完成一个真实宿主闭环。
6. 不实现 Web UI、数据面板、成本统计或团队权限系统。
7. 不把快速草稿和标准写作改成多 Agent。

## User Stories

1. 作为用户，我希望深度模式确实由独立角色执行，而不是单个 Agent 模拟多个身份，从而获得真实的上下文隔离。
2. 作为用户，我希望中断会话后能够继续同一个写作任务，而不是重新描述全部背景。
3. 作为用户，我希望看到当前阶段、执行角色和失败原因，从而知道任务停在哪里。
4. 作为 Lead，我希望用统一合同创建 handoff，从而不必为每个角色临时拼接提示词。
5. 作为 Lead，我希望在创建子代理前校验输入文件和 hash，从而避免把过期研究结果交给 Writer。
6. 作为 Lead，我希望只有自己可以推进任务状态，从而避免多个角色同时修改 `status.json`。
7. 作为 Lead，我希望失败重试生成新的 attempt，从而保留前一次失败证据。
8. 作为 Researcher，我希望只收到 Brief、渠道合同、能力预检和用户素材，从而不被未确认角度污染。
9. 作为 Editorial Strategist，我希望只读取已验证的研究产物，从而不基于未核实事实设计结构。
10. 作为 Writer，我希望只读取已接受的编辑包，从而避免被搜索噪声和废弃方向干扰。
11. 作为 Auditor，我希望首轮看不到 Writer 的解释和父对话，从而保持独立审计。
12. 作为专项 Agent，我希望清楚知道允许写入哪些文件，从而不覆盖其他角色产物。
13. 作为维护者，我希望 handoff 使用版本化 schema，从而可以安全演进合同。
14. 作为维护者，我希望运行时只依赖标准库，从而保持安装简单。
15. 作为维护者，我希望宿主调用与 handoff 校验分离，从而更换宿主时不改写领域状态逻辑。
16. 作为维护者，我希望通过一个高层端到端测试覆盖整个交接生命周期，而不是为每个内部函数编写大量测试。
17. 作为维护者，我希望输入变化只使受影响 handoff 过期，从而避免无差别重跑整条工作流。
18. 作为维护者，我希望每次完成都记录实际输出 hash，从而能够追踪下一阶段使用了哪个版本。
19. 作为维护者，我希望损坏或缺失的 Result 阻止阶段推进，从而避免出现“状态已完成但产物不存在”。
20. 作为未来宿主适配者，我希望有清晰的输入输出协议，从而在出现第二个真实宿主时再提取公共接口。

## Handoff Contract

首版使用 JSON 作为运行时合同格式，原因是 Python 标准库可以直接解析和验证。现有 Markdown/YAML 内容产物保持不变。

Manifest 的决策性字段如下：

```json
{
  "schema_version": 1,
  "handoff_id": "TASK-001-research-01",
  "task_id": "TASK-001",
  "attempt": 1,
  "from_role": "lead",
  "to_role": "researcher",
  "phase": "research",
  "objective": "建立事实与素材证据包",
  "decision_to_inform": "后续角度与结构选择",
  "allowed_inputs": [
    {"path": "brief.md", "sha256": "...", "required": true}
  ],
  "forbidden_inputs": ["parent_conversation", "discarded_directions"],
  "write_scope": ["sources.yaml", "claims.yaml", "asset-manifest.yaml", "research-summary.md"],
  "expected_outputs": ["sources.yaml", "claims.yaml", "asset-manifest.yaml", "research-summary.md"],
  "done_criteria": ["关键主张具有来源、日期和表述边界"],
  "status": "prepared"
}
```

Result 至少记录：

- `handoff_id`
- `attempt`
- `agent_ref`
- `status: completed | failed`
- 实际输出路径与 SHA-256
- 阻断问题
- 简短结果摘要
- 完成时间

Result 不保存隐藏推理过程，不复制父对话全文。

## State Model

Handoff 使用有限状态：

```text
prepared → running → completed
                   ↘ failed
prepared/running → stale
```

规则：

1. Manifest 创建后保持不可变；重试生成新的 attempt。
2. 输入缺失、hash 不一致或 Manifest schema 无效时，不进入 `running`。
3. `completed` 必须同时满足 Result 合法、预期输出存在、输出位于 write scope、输出 hash 可重算。
4. 输入在执行前后发生变化时，当前 handoff 标记为 `stale`，结果不进入下一阶段。
5. 只有 Lead 或 Runtime 可以修改任务级状态；专项 Agent 只写自己的产物和 Result。
6. 状态写入使用临时文件加原子替换，避免中断留下半个 JSON。
7. 已完成 attempt 不被覆盖，后续 attempt 使用独立记录。

## Implementation Decisions

### 1. 单一领域边界

Handoff Runtime 只负责：合同生成、schema 校验、文件 hash、状态迁移、结果校验和历史记录。它不负责文章质量判断，也不负责决定写作流程的业务顺序。

### 2. 宿主调用保持薄层

首版不建立只有一个实现的抽象接口。当前宿主适配只负责把 role card、Manifest 和允许输入转换为一次原生子代理调用，并返回 `agent_ref` 与最终状态。出现第二个真实宿主后，再提取公共 adapter 接口。

### 3. 最少命令面

只提供三个操作：

- `handoff prepare`：生成 Manifest、计算输入 hash 并校验边界。
- `handoff complete`：校验 Result 和实际输出后推进状态。
- `handoff show`：显示当前 handoff、attempt、输入状态和阻断原因。

宿主原生的“创建子代理”动作仍由 Lead 执行；CLI 不伪装成能够直接控制所有 Agent 平台。

### 4. 运行目录仍是事实来源

不引入数据库。每个任务继续使用独立运行目录，任务状态只引用当前 handoff 和最近完成 handoff。所有恢复信息必须能够从目录中的 JSON 和内容产物重建。

### 5. 文件边界验证

- 所有相对路径必须解析到当前运行目录内部。
- 禁止 `..`、绝对路径和符号链接越界。
- 输入文件在执行前计算 SHA-256。
- 输出文件必须属于 Manifest 的 write scope。
- Result 声明的 hash 必须与磁盘内容一致。

### 6. 角色合同复用

现有 Researcher、Editorial Strategist、Writer、Auditor 角色卡继续作为职责来源。Manifest 引用角色卡，不在每次 handoff 中复制整套角色定义。

### 7. 失败与重试

- 失败必须记录类型：输入错误、宿主失败、角色执行失败、输出校验失败或人工取消。
- 重试默认复用相同目标和输出合同，但重新计算输入 hash。
- 已存在的失败产物保留在 attempt 历史中；新 attempt 写入独立暂存区，通过校验后再成为正式阶段产物。

### 8. 恢复策略

“继续上次”先读取任务状态，再验证当前 handoff：

- `prepared`：重新校验后等待宿主调用。
- `running` 且宿主任务仍存在：继续等待。
- `running` 且宿主任务已丢失：记录失败并创建新 attempt。
- `completed`：校验输出后进入下一阶段。
- `stale`：回到产生变化的最近上游节点。

## Testing Decisions

### 最高测试缝

核心自动化测试只走一个高层入口：在临时运行目录中完成 `prepare → fake host completion → complete → resume`。Fake host 只模拟专项 Agent 写出约定文件，不模拟模型内容质量。

这个测试应验证：

1. Manifest 只包含允许输入。
2. 输入 hash 正确。
3. Result 合法时状态推进。
4. 输出越界或缺失时状态保持不变。
5. 输入修改后旧 handoff 变为 stale。
6. 失败重试不覆盖上一 attempt。
7. 新进程可以仅凭运行目录恢复状态。

### 补充边界测试

只为数据损坏风险保留少量测试：

- 路径越界。
- 非法状态迁移。
- 损坏 JSON。
- hash 不一致。
- 原子写入中断后保留上一有效状态。

继续使用现有 `unittest`，不增加测试框架和 fixture 库。

### 真实宿主验收

自动化测试之外，首版必须在一个真实宿主执行一次完整深度链：

```text
Researcher → Editorial Strategist → Writer → Auditor → Writer revision
```

验收记录必须包含每次 handoff 的 Manifest、agent_ref、Result、状态变化和最终产物。没有这条证据，不宣称“深度多 Agent 已实现”。

## Acceptance Criteria

1. 每次深度模式角色切换都产生可验证 Manifest 和 Result。
2. 缺失输入、过期输入、越界输出和缺失输出均阻止状态推进。
3. 专项 Agent 不直接修改任务级状态。
4. 会话重启后能够从运行目录恢复当前 handoff。
5. 重试保留历史 attempt，不覆盖已完成或失败证据。
6. 自动化端到端测试和真实宿主验收均通过。
7. 快速、标准模式行为保持不变。
8. 不增加运行时第三方依赖。

## Success Metrics

MVP 阶段只追踪可验证指标：

- 100% 深度模式 handoff 具有 Manifest 和 Result。
- 100% 完成状态具有可重算的输出 hash。
- 0 次校验失败后仍推进阶段。
- 中断恢复测试通过率 100%。
- 一个真实长文任务能够完整跑通所有角色交接。

不使用“文章质量提升百分比”作为本阶段指标，因为目前没有可靠基线和盲评数据。

## Delivery Plan

### P0：Handoff Contract

- 固化 Manifest、Result 和状态迁移规则。
- 实现 JSON 读取、schema 校验、SHA-256、路径边界与原子写入。
- 增加 `prepare`、`complete`、`show` 三个操作。
- 完成 fake host 高层测试。

### P1：深度模式接入

- Lead 在每次角色切换前创建 Manifest。
- 四类角色只读取允许输入并写入各自范围。
- 任务状态引用当前 handoff。
- 删除现有依赖 Agent 手工维护 hash 和完成状态的重复说明。

### P2：恢复与真实宿主验收

- 支持 stale 检测、attempt 历史和中断恢复。
- 在当前宿主跑通完整深度写作链。
- 将验收记录保存在运行目录。

### P3：出现真实需求后再做

- 第二个宿主适配。
- 并行 handoff。
- 成本与时延统计。
- 可视化任务图。

P3 不属于当前 MVP。

## Risks and Mitigations

1. **风险：把文件协议继续包装成“真实编排”。** 规避方式：真实宿主闭环作为发布门槛。
2. **风险：状态与文件内容不一致。** 规避方式：原子状态更新和完成前输出校验。
3. **风险：Agent 越权读取父对话。** 规避方式：Host Adapter 只构造允许输入，不传全局对话。
4. **风险：过早抽象多宿主。** 规避方式：只实现一个具体宿主，第二个出现后再抽象。
5. **风险：重试覆盖有效产物。** 规避方式：attempt 暂存与通过校验后的提升机制。
6. **风险：合同过重降低写作效率。** 规避方式：只在深度模式启用；快速和标准模式保持当前路径。

## Out of Scope

- 通用 DAG 调度器。
- 消息队列和后台 Worker。
- 云端状态服务。
- Agent 市场或插件系统。
- 自动发布审批系统。
- 全平台统一 Host Adapter SDK。
- 内容效果预测与发布后数据闭环。

## Further Notes

Handoff Runtime 是当前项目从“可安装的流程说明”升级为“可重复执行的写作系统”的最短路径。完成 P0–P2 后，项目才适合把深度模式称为 MVP 能力；在此之前，深度模式应描述为实验性协议。

该方向优先级高于增加更多平台合同、更多审校角色和可视化界面，因为它直接验证项目最核心的多 Agent 差异化是否真实成立。

## Implementation Record — 2026-07-27

### Completed

- P0: `writing_master.handoff` implements schema v1 Manifest/Result validation, SHA-256, run-directory path and symlink boundaries, immutable Manifest hashes, `fcntl` locking, and fsync + replace JSON state writes.
- P0: `writing-master handoff prepare|complete|show` is registered without changing quick/standard execution paths.
- P1: the deep-mode protocol and all four role cards now require Manifest-only inputs, attempt `output_root` writes, Result output, and Lead-owned state transitions.
- P2 runtime behavior: stale input detection, retained attempt history, failed-result categories, restart-from-run-directory inspection, and an automated fake-host Researcher → Strategist → Writer → Auditor → Writer revision chain are covered by `tests/test_handoff.py`.

### Verification

- `python -m unittest discover -s tests -v` passes with 44 tests, including the fake-host five-role chain, malformed Result handling, staged-output boundaries, stale propagation, failed-stage retry enforcement, and interrupted-prepare recovery.
- CLI smoke: `handoff prepare` followed by `handoff show --json` creates and inspects an attempt from a deep/multi-agent `status.json`.
- `uv build`, `compileall`, `git diff --check`, and `codegraph sync` pass.

### Real-host acceptance status

Run directory: `$WRITING_MASTER_HOME/runs/handoff-runtime-acceptance-20260727-final-v3/`.

- Codex completed the full fresh-context chain: Researcher → Editorial Strategist → Writer → Auditor → Writer revision.
- Every handoff retained its Manifest, exact host `agent_ref`, Result, completed state, staged outputs, promoted outputs, and SHA-256 records.
- The Auditor returned `revise`; Lead accepted two evidence issues, and the revision report closes both before producing `final.md`.
- `real-host-acceptance.json` records each Manifest, Result, state transition, host thread/reference, output hash, and the final hash. `acceptance-report.md` provides the readable summary.
- Final `effective_status` is `completed`, with zero stale handoffs. `final.md` SHA-256 is `9f4f8a63e3cb12448639ec6fa7ae7b2f23f478530998470348e63ca76c7447a2`.
