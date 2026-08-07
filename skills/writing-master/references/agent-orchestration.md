# 深度写作的多 Agent 协议

本文件只在 `mode=deep` 时读取。quick 和 standard 均由当前 Agent 完成。

## 失败即停

深度任务在首次素材提取、调研、生成或角色派发前，必须已经通过 `mode-selection.md` 的所选模式就绪闸门。就绪检查失败时使用 `WM-CAP-001` 结束任务；不创建 Handoff，不进入下面的执行图，也不切换为 quick 或 standard。

运行途中，只有不改变深度模式隔离、独立研究和独立审计承诺的同模式恢复才可继续，例如 Runtime 能按既有 attempt 合同重试且输入、角色边界和验收标准保持不变。若异常已影响这些承诺，立即停止后续派发，保留已完成产物和 attempt 历史，使用 `WM-RUN-001`；不得由 Lead 或当前 Agent 补做缺失角色，也不得改走其他模式。

用户正文只说明任务停在哪个用户阶段、没有切换模式、已有内容已保留，以及诊断编号。Runtime、Handoff、Agent、failure type 和内部异常栈只进入诊断详情。只提醒用户提交 Issue，不自动创建或生成 Issue 草稿。

## 拆分原则

按长期稳定的编辑责任拆分角色，不采用“一步一个 Agent”。默认使用四类专项角色：

1. **Researcher**：事实、来源和素材证据。
2. **Editorial Strategist**：角度、读者决策、结构和 storyboard。
3. **Writer**：初稿与基于问题清单的修订。
4. **Auditor**：独立检查证据、编辑质量和声音偏差。

Lead Agent 负责模式、Brief、文件状态、用户确认、问题合并、Baoyu 闸门和最终验收。Lead 不与专项代理竞争同一份正文。

选择 Persona（内置或外部）时，Lead 还负责保存原始 `persona-skill.md`、生成一次 `persona-brief.md` 并冻结其来源 hash。Researcher 保持中立；Editorial Strategist、Writer 与 Auditor 使用同一份 Persona Brief。

任务较短时可由一个 Auditor 完成三层审计；只有文章重要且并行收益明确时，再拆成 Evidence Auditor 与 Editorial/Voice Auditor。Agent 数量服务于上下文隔离，不追求数量。

## 执行图

```text
Lead：模式 + 单一 target_id + 内容契约 + Baoyu preflight
  ↓
可选 Researcher：topic research brief（宽主题/近期选题）
  ↓ 用户确认候选方向
Researcher：claims + sources + asset manifest
  ↓
Editorial Strategist：角度 + reader decision + outline + storyboard
  ↓ 用户确认方向
Writer：draft-v1 + claim usage
  ↓
Auditor：结构化审计报告
  ↓ Lead 合并 accepted issues
Writer：draft-v2/final + revision report
  ↓
Lead：标题与 canonical final 内容验收
  ↓
当前渠道合同要求的完整产物
  ↓
Lead：交付包验收
```

## Handoff Manifest（唯一实际输入合同）

代理之间只通过运行时生成的 `manifest.json` 通信。角色卡说明职责；Manifest 才是某一次执行实际允许读取和写入的唯一合同：

```yaml
schema_version: 1
handoff_id: TASK-001-research-researcher-01
task_id: TASK-001
attempt: 1
from_role: lead
to_role: researcher
phase: research
objective: 建立事实与素材证据包
decision_to_inform: 后续角度与结构选择
allowed_inputs:
  - path: brief.md
    sha256: "..."
    required: true
forbidden_inputs: []
write_scope:
  - claims.yaml
expected_outputs:
  - claims.yaml
done_criteria:
  - 关键主张具有来源和表述边界
status: prepared
role_card: skills/writing-master/agents/researcher.md
output_root: handoffs/research-researcher/attempt-01/outputs
result_path: handoffs/research-researcher/attempt-01/result.json
```

Host 只把 **角色卡 + Manifest + Manifest 的 `allowed_inputs` 文件**交给专项 Agent，不传整个运行目录、父对话或额外上下文。专项 Agent：

- 只读取 `allowed_inputs`；角色卡中的“读取”是该角色通常需要的文件类型，不是绕过 Manifest 的额外权限。
- 只写入 Manifest `output_root` 内、属于 `write_scope` 的文件；把 Result 写入 Manifest `result_path`。
- 不修改 `status.json`、`state.json`、Manifest 或其他 attempt。Result 不包含隐藏推理过程。
- Lead 为每个 attempt 生成本次运行内唯一、不可解释且不复用的 `agent_ref`；执行 `writing-master handoff start RUN_DIR --agent-ref AGENT_REF` 成功后，才创建专项 Agent。宿主调用 identity 如何映射到这个 `agent_ref` 由具体 adapter 定义：例如 Codex 使用 `task_name == agent_ref`，Claude Code foreground 不使用 `Agent.name`。专项 Agent 把这个精确 `agent_ref` 写入 Result；宿主调用明确终止后由 Lead 调用 `handoff complete` 校验 Result、提升输出并更新状态。
- 是否支持宿主恢复、如何判定 liveness 以及何时调用 `recover-lost`，由具体 Host adapter 定义；不得从通用 Handoff 状态或角色名猜测 liveness。
- Manifest 创建后不可修改；输入 hash 变化使 prepared/running attempt 过期，重试创建新 attempt。每次 `show` 也会复核 completed attempt 的 canonical Result、暂存输出和已提升输出；历史状态保留 `completed`，但损坏会显示为 `effective_status: stale` 并阻断下游，直到最早受影响阶段重试。

`Result` 是 JSON，必须包含 `schema_version: 1`、Manifest 的 `handoff_id` 和 `attempt`、`agent_ref`、`status`、`outputs`、`blocking_issues`、`summary`、`completed_at`。完成时每项 output 使用 `{"logical_name":"final.md","path":"outputs/final.md","sha256":"..."}`（也可使用完整的 Manifest `output_root/final.md`）；失败时额外使用 `failure_type: input_error | host_failure | role_failure | output_validation | cancelled`。

通用规则：

- `allowed_inputs` 使用明确文件路径，不传整个运行目录。
- Reviewer 首轮不读取作者解释、未采用的讨论、历史表现数据和其他 Reviewer 结论。
- Writer 只读取接受后的 Brief、claims、style、editorial brief、outline、素材选择，以及 Manifest 列出的 Voice Snapshot。
- 代理只写自己的 attempt 产物；Lead/Runtime 维护 `status.json`。
- 输入变化后由 Runtime 校验 hash；只重跑受影响节点。

### Codex host adapter

Codex 对每个 attempt 固定执行以下顺序；`start` 必须在 `spawn_agent` 前完成，避免 Agent 已创建而 `agent_ref` 尚未持久化的中断窗口：

```text
writing-master handoff prepare RUN_DIR ...
→ 生成唯一 task_name，并令 agent_ref = task_name
→ writing-master handoff start RUN_DIR --agent-ref AGENT_REF
→ spawn_agent(fork_turns="none", task_name=AGENT_REF)
→ Agent 只写 Manifest output_root 和 Result
→ writing-master handoff complete RUN_DIR
```

Lead 将角色卡、Manifest 和 Manifest 列出的输入内容写进 `spawn_agent.message`；`fork_turns` 固定为 `"none"`，不把父对话隐式传给专项 Agent。`task_name` 在当前 Codex 线程树内唯一，重试使用新的名称；旧 `agent_ref` 只用于 `recover-lost` 校验。会话恢复时，Host 先按精确 `agent_ref` 查询宿主 liveness：仍存在则继续等待；已丢失则执行 `writing-master handoff recover-lost RUN_DIR --agent-ref AGENT_REF`。该宿主命令只接受当前 `running` 的同一 `agent_ref`，把旧 attempt 记录为 `failed` / `host_failure`，再用同一 Manifest 合同创建下一 attempt。上述调用是 Codex 编排协议，不属于 Handoff 或 Voice Runtime。

### Claude Code foreground host adapter

Claude Code 使用普通前台 subagent `Agent` 调用，不使用 experimental agent team teammate。每个 attempt 由 Lead 在调用前生成一个当前运行内唯一、不可解释且不复用的 `AGENT_REF`；它只进入 Handoff 状态与 Agent prompt/Result，不作为 `Agent.name`。`run_in_background=false` 是等待普通 subagent 完成并返回单一最终报告的同步边界；`name` 只用于地址标识，不能作为完成信号。适配器固定执行以下顺序：

```text
writing-master handoff prepare RUN_DIR ...
→ 生成唯一 opaque AGENT_REF，并把它写入 Handoff 状态与 Agent prompt
→ writing-master handoff start RUN_DIR --agent-ref AGENT_REF
→ Agent(run_in_background=false, prompt=包含 AGENT_REF、角色卡、Manifest 与 allowed_inputs)
→ Agent 只写 Manifest output_root 和 Result，且 Result.agent_ref == AGENT_REF
→ 前台调用产生明确终止结果后，调用 writing-master handoff complete RUN_DIR
→ Runtime 以 Result 与暂存输出为事实源，将 attempt 原子推进到 completed 或 failed
```

`start` 成功前禁止调用 `Agent`。前台调用产生明确终止结果（正常返回、显式失败或已确认取消）后，Lead 必须且只能调用一次 `complete`；`complete` 是终止化与校验屏障，不是“成功专用”命令。适配器不得先以最终报告文本或自行重复校验来决定是否调用它：合法的 `Result.status == completed` 且输出校验通过时，Runtime 推进到 `completed`；合法的 `Result.status == failed` 时，Runtime 推进到 `failed`；缺少或格式错误的 Result、`agent_ref` 不匹配、输出缺失或 hash 校验失败时，`complete` 原子地将当前 attempt 标记为 `failed`（`output_validation`），并返回错误。`Agent` 抛错、被明确中止、返回被截断或未完成的报告时仍调用 `complete`，由 Runtime 根据磁盘上的 Result 进行最终判定；若没有可用 Result，则按上述校验失败处理。之后立即 fail-stop：不由 Lead 补做角色，不降级到其他模式；保留当前 attempt 和诊断，按 `WM-RUN-001` 停止。

前台调用尚未返回，或 Host 尚未明确确认调用已终止时，不得把“等待中”判为丢失，不得按超时、`unknown`、瞬时宿主错误或角色名猜测 liveness，也不得调用 `recover-lost`。普通前台 `Agent` 调用不会向 Handoff 提供可恢复的 teammate identity；如果 Host 在返回前丢失，当前适配器不能证明原调用不存在，因此必须保留 running attempt 并按 `WM-RUN-001` 停止，交由人工按宿主实际状态处理，不得自动重放或创建第二个 Agent。

`recover-lost` 仍只适用于具有宿主可查询 invocation identity 的编排适配器（例如 Codex 的 `agent_ref` 协议），不适用于本节的普通 Claude Code foreground 调用。Claude Code 重试必须在 `complete` 或明确的 Host 丢失处置已将旧 attempt 终止后，生成新的 opaque `AGENT_REF`，重新执行 `start → Agent`；不得复用旧 ref，也不得恢复 `prepared`、`completed`、`failed` 或 `stale` attempt。

### Personal context

内容契约确认后，Lead 创建或确认任务内 `personal-context-snapshot.json`。当 Deep 的 Researcher、Writer 或 Auditor 需要个人上下文时，其 Manifest 必须逐项列出该 Snapshot 与所选 `context-materials/ITEM_ID.md` 副本；不得列出 `${WRITING_MASTER_HOME}/personal-context/`、其他全局个人目录或父对话全文。篡改 Snapshot 会使引用它的 handoff stale。

这是 Host 输入构造、Manifest/hash 和 stale 的可证明合同，不是 OS 级文件访问隔离声明。

### Voice Preset

Voice 选择在内容契约中完成；Lead 在确认后创建或确认任务内 `voice-profile-snapshot.json`，不把全局 Registry 交给任何专项 Agent。Phase 1 与 Phase 2 保持 Voice-free：Researcher 和 Editorial Strategist 的 Manifest `allowed_inputs` **不得**列出 `voice-profile-snapshot.json`、其 hash、Registry Profile 或其等价内容。

Deep 模式只有 Writer 与 Auditor 可通过 Manifest 接收 Voice Snapshot；每次列入都必须带任务文件的精确 hash：

```yaml
allowed_inputs:
  - path: voice-profile-snapshot.json
    sha256: "..."
    required: true
```

Writer 只在 Phase 3 使用该 Snapshot 调整表达；Auditor 用同一 Snapshot 进行 Voice Audit。Snapshot 输入 hash 变化或校验失败会使相关 handoff stale，并阻断生成、审校、验收和发布；不得改读当前 Registry 或回退为另一 Voice。`natural-default` 的 Snapshot 不可用时由 Lead 记录 `voice_snapshot: unavailable` 并走既有自然写作；显式非默认 Voice 的创建失败保持在内容契约确认，不能派发 Writer。

### Selected Persona Skill

内置或外部 Persona 的选择和任务 Brief 见 `persona-skills.md`。Lead 只解析用户明确提供的内置 ID、名称或路径，把原始 `SKILL.md` 原样保存为任务内 `persona-skill.md`，再创建自由格式 `persona-brief.md`；不把 Persona 转成 Voice Profile。

Researcher 的 Manifest `allowed_inputs` **不得**列出 `persona-skill.md`、`persona-brief.md` 或其等价内容。Editorial Strategist、Writer 与 Auditor 在 Persona 启用时都列出同一份 Persona Brief 及精确 hash：

```yaml
allowed_inputs:
  - path: persona-brief.md
    sha256: "..."
    required: true
```

上述三个角色不回读来源路径，也不把原始 `persona-skill.md` 作为角色输入；它只作为 Lead 的冻结副本和恢复校验依据。恢复时继续使用冻结文件，不回读或从任何内置、外部来源重建当前版本。

Persona/Voice 已 ready 后的变更由 Lead 创建关联 Writing run，不覆盖原 run。新 run 的 `status.json` 必须写入：

```yaml
source_task_id: 原 run 的 task_id
source_change_kind: persona | voice
source_change_sha256: 变更摘要 hash
```

原 run 的 Persona/Voice Snapshot、hash 和关联字段保持不变；新 run 从 `contract: pending` 开始，用户确认后才创建新的 Snapshot。

### Topic Research

用户明确只要选题、内容契约仍是宽主题，或要求近期热点时，Host 先检查实时检索能力。能力可用后，Lead 才创建 `phase=topic_research`、`to_role=researcher` 的 Handoff：

- `allowed_inputs` 只列出 Persona-neutral 的 `brief.md`、`personal-context-snapshot.json`、所选任务内材料副本和 `references/research-brief.md`；该 Brief 不含 Persona 原文、背景、拟采用部分或角色侧重。
- 唯一 expected output 是 `research-brief-draft.json`；Researcher 提出 3–10 个候选但不选择最终方向。
- Runtime 提升 draft 后，Lead 运行 `writing-master research save/verify`，再让用户选择 candidate。
- 缺少实时检索时在 Handoff 创建前记录 capability response；不创建 Handoff、draft 或 canonical Brief。
- 选定 candidate 后才创建普通 `phase=research` Handoff；Research Brief Evidence 不自动进入文章 claims。

### Content Routing

进入 Phase 2 时，quick/standard 由当前 Agent 读取 `references/content-routing.md`。Deep 模式的 Editorial Strategist Manifest 将该文件作为带精确 SHA-256 的 `allowed_inputs`；Article Research 已形成 accepted evidence 后，Editorial Strategist 才生成 `recommended_combo` 并写入 `editorial-brief.md` 与 `outline.md`。推荐沿用当前 run 已冻结的 `content_type`，另一文章类型只进入新 run 建议。Writer 和 Auditor 只消费任务内已保存的组合及其 `required_blocks`，不额外读取路由参考文件。

## 角色卡

创建代理前读取对应文件：

- `../agents/researcher.md`
- `../agents/editorial-strategist.md`
- `../agents/writer.md`
- `../agents/auditor.md`

## 并行边界

适合并行：

- Researcher 内部的事实检索与素材检索；
- 证据审计与声音审计（需要拆分 Auditor 时）。

渠道适配不在同一任务内并行：当前任务只处理一个 `target_id`；另一个渠道由后续 Rewrite 独立执行。

保持串行：

- 证据 → 角度；
- 角度确认 → 写作；
- 初稿 → 独立审计；
- 审计问题合并 → 统一修订；
- 结构稳定 → Baoyu production。

## 审计问题格式

```yaml
- issue_id: EVID-001
  severity: blocking | major | minor
  layer: evidence | editorial | voice
  location: "section/paragraph/claim_id"
  problem: "可观察的问题"
  evidence: "来源、原句或对照规则"
  required_change: "修订边界"
```

Lead 负责去重和处理冲突，形成 `accepted-issues.yaml`。Writer 根据该文件统一修订，避免多个 Reviewer 分别重写全文。

## Baoyu 边界

- Lead 在开题阶段执行 capability/material preflight。
- Researcher 负责把已有真实素材登记到 `asset-manifest.yaml`。
- Editorial Strategist 决定视觉位的编辑职责。
- Writer 引用素材身份，不发起图像生成。
- Auditor 检查来源、身份和重复使用。
- Lead 在视觉闸门通过后调用 Baoyu Skills。

## Host adapter

角色卡保持平台中立。只有 Lead 的 host adapter 负责把角色卡转换成当前 Agent 宿主的子代理调用：

```text
role card + Manifest + allowed input files
        ↓
host adapter（Task / 原生协作接口）
        ↓
Result 写入 Manifest result_path
```

角色卡不直接调用另一个角色，也不读取宿主的全局对话。宿主没有可用的子代理接口时，深度模式在所选模式就绪闸门使用 `WM-CAP-001` 结束任务；不开始素材提取、调研或生成，不把单 Agent 结果伪装成深度模式结果。
