# Personal Context Runtime Bridge

本文件定义 Personal Context Runtime 与确认式风格学习边界；Research Brief 见 `research-brief.md`。它不定义 quick/standard 通用恢复。

## Standard 与 Deep 的任务内上下文输入

内容契约确认后，标准写作先在既有 `{run_dir}` 中运行：

```text
writing-master context snapshot {run_dir} --material ITEM_ID:PURPOSE ...
```

- 先用 `writing-master context search` / `material list` 发现候选；只把已确认要用的 item 传给 Snapshot。
- `ask_before_use` 必须先由用户任务级批准；`private` 和 disabled item 不进入 Snapshot。
- 没有选中素材时仍创建 Snapshot，它冻结当前 Profile/Style；尚未配置时使用 canonical empty 状态。
- Snapshot 已存在时，只接受同一组 `(ITEM_ID, PURPOSE)`；不同请求是冲突，不覆盖旧任务。

Standard 的 Phase 1、2、3 只能读取 `{run_dir}/personal-context-snapshot.json` 和 `{run_dir}/context-materials/`。不得扫描或直接读取 `${WRITING_MASTER_HOME}/personal-context/`、旧 `personal_materials/` 或其他全局个人目录。

Deep 模式由 Lead 在内容契约确认后创建或确认同一 Snapshot；需要个人上下文的 Writer 或 Auditor 只通过自己的 Manifest `allowed_inputs` 读取 Snapshot 和逐项列出的任务内副本。Host 不把全局个人目录或父对话全文传给专项 Agent。

## Voice Preset 独立边界

`voice-profile-snapshot.json` 与 `personal-context-snapshot.json` 是两个独立任务文件：Voice Profile 不写入 Personal Context Snapshot，Personal Context 也不成为 Voice Profile 的来源。Voice 的选择、版本、hash、Phase 3/Voice Audit 读取和失败语义见 `voice-presets.md`。

外部 Persona 的 `persona-skill.md` 与 `persona-brief.md` 同样不写入 Personal Context Snapshot，不自动生成 Style Observation，也不回写 Author Profile。项目补充背景只属于当前任务。

- Phase 1 Research 与 Phase 2 Editorial 不读取 Voice Snapshot；它不影响个人材料选择、事实、角度或结构。
- Quick / Standard 仅在 Phase 3 与 Voice Audit 读取任务 Voice Snapshot。
- Deep 仅 Writer 与 Auditor Manifest 可列 Voice Snapshot 及 hash；Researcher 与 Editorial Strategist Manifest 不得列它。

## 用户摘要

只显示下列摘要，不显示 hash、全局路径或私密正文：

```text
personal_context: unavailable | empty | ready
selected_materials: N
pending_approvals: N
```

- `unavailable`：Runtime 或 Snapshot 建立失败；说明受影响的是个人上下文，不把未读取的全局内容写成已使用。
- `empty`：Snapshot 已建立但 Profile/Style 为空且未选择个人素材。
- `ready`：Snapshot 已冻结可用 Profile、accepted Style 或至少一条已选择素材。

## 确认式风格学习

风格学习不是自动动作。只有用户明确要求从一次可追溯编辑中学习时，Agent 才生成 candidate：

```text
writing-master learn propose CANDIDATE.json --run-dir RUN_DIR --json
writing-master learn decide OBSERVATION_ID --accept --json
writing-master learn decide OBSERVATION_ID --reject --json
writing-master learn show --json
```

- Candidate 必须记录 baseline/edited 文件 hash、具体 before/after 片段或 diff 引用、规则维度、适用范围、来源任务和 proposal 信息。
- `propose` 只创建 `proposed` observation；Runtime 不替用户作语义决定。
- 用户明确接受或拒绝后才运行 `decide`；同一决定幂等，相反终态决定返回冲突。
- Style Profile 只从 accepted observations 确定性重建；proposed/rejected 不进入规则。
- 当前任务 Snapshot 写入后保持不变；accepted Style 只影响后续新任务 Snapshot。
- 非默认 Voice 任务不作为确认式风格学习的 baseline 或 evidence；其 Profile 驱动表达不生成 Style Observation，也不进入 Style Profile 重建。把借用的声音变成长期风格属于后续显式采纳能力，不在 v0.3 隐式执行。

## Usage 与验证

内容验收形成 `final.md` 和 `acceptance-report.md` 后，Runtime 以实际使用的 Snapshot item/purpose、section/claim 和这两个 artifact 路径写入 `context-usage.json`。不要手写或猜测 hash。

交付前执行：

```text
writing-master context verify-run {run_dir}
```

它校验 Snapshot、任务内副本、批准、usage 记录及 final/acceptance hash；它不对正文作语义性“绝无私密泄露”声明。
