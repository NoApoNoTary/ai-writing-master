# 深度写作的多 Agent 协议

本文件只在 `mode=deep` 时读取。quick 和 standard 均由当前 Agent 完成。

## 拆分原则

按长期稳定的编辑责任拆分角色，不采用“一步一个 Agent”。默认使用四类专项角色：

1. **Researcher**：事实、来源和素材证据。
2. **Editorial Strategist**：角度、读者决策、结构和 storyboard。
3. **Writer**：初稿与基于问题清单的修订。
4. **Auditor**：独立检查证据、编辑质量和声音偏差。

Lead Agent 负责模式、Brief、文件状态、用户确认、问题合并、Baoyu 闸门和最终验收。Lead 不与专项代理竞争同一份正文。

任务较短时可由一个 Auditor 完成三层审计；只有文章重要且并行收益明确时，再拆成 Evidence Auditor 与 Editorial/Voice Auditor。Agent 数量服务于上下文隔离，不追求数量。

## 执行图

```text
Lead：模式 + 内容契约 + Baoyu preflight
  ↓
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
Lead：标题、视觉闸门、Baoyu production、验收与发布确认
```

## Handoff Manifest（唯一实际输入合同）

代理之间只通过运行时生成的 `manifest.json` 通信。角色卡说明职责；Manifest 才是某一次执行实际允许读取和写入的唯一合同：

```yaml
schema_version: 1
handoff_id:
task_id:
attempt:
from_role: lead
to_role: researcher
phase:
objective:
decision_to_inform:
allowed_inputs:
  - path: brief.md
    sha256: "..."
    required: true
forbidden_inputs: []
write_scope: []
expected_outputs: []
done_criteria: []
status: prepared
role_card: skills/writing-master/agents/researcher.md
output_root: handoffs/research-researcher/attempt-01/outputs
result_path: handoffs/research-researcher/attempt-01/result.json
```

Host 只把 **角色卡 + Manifest + Manifest 的 `allowed_inputs` 文件**交给专项 Agent，不传整个运行目录、父对话或额外上下文。专项 Agent：

- 只读取 `allowed_inputs`；角色卡中的“读取”是该角色通常需要的文件类型，不是绕过 Manifest 的额外权限。
- 只写入 Manifest `output_root` 内、属于 `write_scope` 的文件；把 Result 写入 Manifest `result_path`。
- 不修改 `status.json`、`state.json`、Manifest 或其他 attempt。Result 不包含隐藏推理过程。
- Lead 在宿主创建专项 Agent 后调用运行时内部 `mark_running(run_dir, agent_ref)`，并把这个精确 `agent_ref` 交给专项 Agent 写入 Result；专项 Agent 返回后由 Lead 调用 `handoff complete` 校验 Result、提升输出并更新状态。
- 会话恢复时，Host 先按精确 `agent_ref` 查询宿主 liveness：仍存在则继续等待；已丢失则调用内部 `recover_lost_running(run_dir, agent_ref)`。该 hook 只接受当前 `running` 的同一 `agent_ref`，把旧 attempt 记录为 `failed` / `host_failure`，再用同一 Manifest 合同创建下一 attempt；没有对应 CLI 操作。
- Manifest 创建后不可修改；输入 hash 变化使 prepared/running attempt 过期，重试创建新 attempt。每次 `show` 也会复核 completed attempt 的 canonical Result、暂存输出和已提升输出；历史状态保留 `completed`，但损坏会显示为 `effective_status: stale` 并阻断下游，直到最早受影响阶段重试。

`Result` 是 JSON，必须包含 `schema_version: 1`、Manifest 的 `handoff_id` 和 `attempt`、`agent_ref`、`status`、`outputs`、`blocking_issues`、`summary`、`completed_at`。完成时每项 output 使用 `{"logical_name":"final.md","path":"outputs/final.md","sha256":"..."}`（也可使用完整的 Manifest `output_root/final.md`）；失败时额外使用 `failure_type: input_error | host_failure | role_failure | output_validation | cancelled`。

通用规则：

- `allowed_inputs` 使用明确文件路径，不传整个运行目录。
- Reviewer 首轮不读取作者解释、未采用的讨论、历史表现数据和其他 Reviewer 结论。
- Writer 只读取接受后的 Brief、claims、style、editorial brief、outline 和素材选择。
- 代理只写自己的 attempt 产物；Lead/Runtime 维护 `status.json`。
- 输入变化后由 Runtime 校验 hash；只重跑受影响节点。

## 角色卡

创建代理前读取对应文件：

- `../agents/researcher.md`
- `../agents/editorial-strategist.md`
- `../agents/writer.md`
- `../agents/auditor.md`

## 并行边界

适合并行：

- Researcher 内部的事实检索与素材检索；
- 证据审计与声音审计（需要拆分 Auditor 时）；
- 已确定 canonical final 后的多个平台适配。

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

角色卡不直接调用另一个角色，也不读取宿主的全局对话。宿主没有可用的子代理接口时，深度模式在 capability preflight 阶段报告缺少能力，保留当前产物，不把单 Agent 结果伪装成深度模式结果。
