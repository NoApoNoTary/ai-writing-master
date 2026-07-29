---
name: writing-master
description: |
  AI Writing Master 的端到端从零创作入口。新建完整内容时先让用户明确选择快速草稿、标准写作或深度写作，并为本次任务选择一个 target_id；快速与标准模式由当前 Agent 单独完成，只有具备真实 Handoff Runtime 的深度模式启用多 Agent。流程覆盖内容契约、个人上下文、上下文感知选题、事实与素材双轨调研、写作、渠道审校、确认式风格学习和 Baoyu 视觉/排版路由。适用于“写文章、写公众号、从零创作、写 X 单帖或 Thread”等请求；已有正文改写转 writing-rewrite。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - Task
---

# Writing Master

## 目标

把完整写作变成一条可审阅、可继续、可验收的编辑流程，而不是一次性生成正文。

核心约束：

- 新建完整文章必须先完成模式选择，Agent 不根据题目难度自行决定模式。
- 每个任务只选择一个 `target_id`：`wechat`、`x-post` 或 `x-thread`；需要第二个渠道时，在当前 canonical final 完成后新建一次 Rewrite。
- 快速草稿和标准写作始终使用当前 Agent；只有深度模式启用多 Agent，且当前宿主必须具备真实 Handoff Runtime。
- 事实、引用、个人经历和测试结果都要可追溯；未知项保留为待确认项。
- Baoyu 在开题阶段进入能力与素材预检，视觉生产放在证据、角度和文章结构明确之后。
- 重要方向由用户确认；公开发布只响应清晰的发布指令。
- 对用户展示结论、选项、状态和产物，不输出隐藏推理过程。
- 所选模式未就绪时，在素材提取、调研、生成或其他高 Token 操作前结束任务；运行途中若所选模式的质量承诺已受影响，保留已有产物并停止，不切换到其他模式。

## 入口路由

先识别请求属于哪一类：

| 请求 | 行为 |
|---|---|
| 从零创作完整内容 | 执行“模式选择闸门”，再在内容契约中确定一个 `target_id` |
| 用户已在当前请求中明确说快速、标准或深度 | 直接采用该模式，不重复提问 |
| 继续指定任务 | 检查任务恢复能力；已验证可用时读取指定 `task_id`，否则展示 Product–Technical Gap 和已知产物 |
| 已有正文、洗稿、改写或渠道重写 | 转 `writing-rewrite` |
| 一次要求多个渠道 | 只确认本次一个 `target_id`；其余目标在完成后分别进入新的 Rewrite |
| 只做选题 | 在当前 Skill 内按需执行 `references/research-brief.md`，不虚构独立 Skill |
| 只做审校、标题或素材规划 | 在当前 Skill 内执行对应模块，不虚构独立 Skill |
| 只做配图、封面、信息图、HTML 或发布 | 只读取已验收的 canonical final，读取 `references/baoyu-integration.md` 后路由到实际存在的 Baoyu Skill |

### 模式选择闸门

新建完整文章且用户尚未选择模式时，只询问下面这一题，然后等待回复：

读取 `references/mode-selection.md` 中的 Canonical prompt，原样展示后等待用户回复。
在用户回复前，不创建运行目录、不开始调研，也不执行 Baoyu。

### 所选模式就绪闸门

用户选择模式后，立即读取 `references/mode-selection.md` 的“所选模式就绪闸门”并执行轻量检查。该检查必须早于运行目录中的内容工作，以及任何素材提取、实时检索、正文生成、视觉生成、角色派发或其他高 Token 操作。

模式确定后只创建最小运行目录，并先写入 `capability-preflight.md` 的 `selected_mode`、`mode_readiness`、`diagnostic_id` 与版本。此时不创建 Brief、素材副本或其他写作产物；就绪后 Phase 0 在同一文件追加能力与素材结果，未就绪时保留该诊断记录后结束。

- `mode_readiness=ready`：保持现有入口、状态摘要和 Phase 0–6 流程不变。
- `mode_readiness=unavailable`：使用 `WM-CAP-001` 用户正文，立即结束当前任务。调研和生成调用次数为 0，不切换到 quick、standard 或其他模式，不询问用户是否改用其他模式。

只允许把技术原因写入诊断详情；普通错误正文不得出现 Runtime、Handoff、Agent、multi-agent 或内部异常栈。只提醒用户提交 Issue，不调用 Issue 工具，也不生成 Issue 草稿。

## 运行约定与技术边界

- `{home}` = `$WRITING_MASTER_HOME`，未设置时使用 `~/.writing-master`
- `{skill_dir}` = 当前 `writing-master` Skill 目录
- 运行目录 = `{home}/runs/{task_id}/`
- 所有跨阶段信息写入运行目录；不要依赖对话记忆作为唯一状态。
- `task_id` 分配、跨会话任务发现、原子状态写入、输入变化检测和版本回退属于 Handoff Runtime 的技术边界。当前会话只基于已确认存在的运行目录和产物汇报状态。
- `status.json` 是内部工作记录。用户只看到下方的任务摘要，不展示内部 schema、hash 或代理实现细节。

初始化 `status.json`：

```json
{
  "task_id": "YYYYMMDD-001",
  "entry": "writing",
  "mode": "quick | standard | deep",
  "execution": "single_agent | multi_agent",
  "target_id": "wechat | x-post | x-thread",
  "voice_id": "natural-default",
  "voice_profile_version": 1,
  "voice_snapshot": "pending | ready | legacy | unavailable",
  "voice_snapshot_sha256": "...",
  "status": "in_progress",
  "current_phase": "contract",
  "phases": {
    "contract": "pending",
    "research": "pending",
    "strategy": "pending",
    "draft": "pending",
    "review": "pending",
    "packaging": "pending",
    "visual": "pending",
    "acceptance": "pending"
  }
}
```

快速、标准模式设置 `execution=single_agent`；深度模式仅在就绪闸门通过后设置 `execution=multi_agent` 并读取 `references/agent-orchestration.md`。缺少该能力时使用 `WM-CAP-001` 结束任务，不创建写作产物、不切换模式，也不模拟多 Agent 结果。

## 用户可见任务合同

每次阶段变更、等待用户或失败时，都用用户语言给出同一份简洁摘要：

```text
任务：{task_id 或“当前对话任务”}
模式：{quick | standard | deep}
渠道：{wechat | x-post | x-thread}
阶段：{用户状态}
状态：{进行中 | 等待用户 | 失败 | 已取消 | 已完成}
已完成：{产物或阶段}
当前动作：{正在处理什么}
等待你：{没有则写“无”}
下一步：{继续方式}
最近失败：{没有则写“无”}
personal_context: {unavailable | empty | ready}
selected_materials: {N}
pending_approvals: {N}
voice: {label}
voice_snapshot: {ready | legacy | unavailable}
```

| 用户状态 | 含义 | 允许动作 |
|---|---|---|
| 等待模式 | 尚未选择快速、标准或深度 | 选择、取消 |
| 接收素材 | 正在登记和提取输入 | 继续添加、结束摄入、取消 |
| 等待契约确认 | Brief 已整理 | 确认、修改、取消 |
| 调研中 | 正在处理证据和素材 | 查看进度、补充素材、取消 |
| 等待方向确认 | 候选方向已形成 | 选择、修改、取消 |
| 写作中 | 正在生成或修订正文 | 查看阶段、取消 |
| 等待问题处理 | 存在需要用户决定的问题 | 接受、忽略非阻断项、修改要求、要求重写受影响部分 |
| 打包中 | 正在形成最终产物集 | 查看进度 |
| 已完成 | 核心产物有效 | Rewrite、视觉、发布、请求以此为新任务起点 |
| 失败 | 当前动作未完成 | 查看原因、重试、取消 |
| 已取消 | 任务停止但保留已完成产物 | 查看、请求以此为新任务起点、归档 |

版本语义：`draft-v1.md` 是不可覆盖的初稿快照；`draft-v2.md` 是依据审校结果生成的修订稿；只有内容验收通过的 `final.md` 才是 canonical final。用户可以查看修订前后差异或基于任一保留版本发起新修订；确定性版本回退依赖运行时的不可变历史，属于 Product–Technical Gap。

## 用户等待与继续方式

只在模式、内容契约、重大方向、阻断问题、明确请求的风格候选决定和发布需要用户决定时中断。每个等待点都给出明确问题和继续方式：

| 等待点 | 必须展示的问题 | 继续方式 |
|---|---|---|
| 内容契约 | `请确认内容契约：{摘要}` | 回复“确认”，或用“修改：字段=值”更新，或回复“取消” |
| 方向 | `请选择方向：1/2/3，或说明你要修改的取舍。` | 选择、修改或取消 |
| 审校问题 | `审校发现 {blocking} 个阻断、{major} 个主要问题。需要你决定：{方向性问题}` | 接受建议、忽略非阻断项、修改原始要求、补充证据，或要求重写受影响部分 |
| 风格候选 | `是否接受这条可追溯风格规则：{规则、范围、证据摘要}？` | 接受、拒绝或暂不决定 |
| 发布 | `最终产物已验收。是否发布到 {平台}？` | 只有“发布到 {平台}”这类明确指令才产生外部副作用 |

“继续”“下一步”只推进到下一份可审阅产物，不等同于发布指令。阻断问题不得通过“忽略”进入已完成或发布状态。

用户修改内容契约时，任务摘要必须列出受影响阶段（调研、方向、草稿、审校或打包）和下一步。运行时具备输入 hash 与依赖关系时，只重跑这些阶段；缺少该能力时，说明局部重跑仍属 Product–Technical Gap，不把它描述为已执行。

## 核心工作流

### Phase 0：内容契约、能力预检与素材接收

仅在所选模式就绪闸门通过后进入本阶段；模式未就绪的失败分支不得执行下面任何一步。

1. 收集主题、目标读者、时效、字数、内容目的、已有素材和视觉/排版/发布意图，并确认本次唯一的 `target_id`。未指定时只让用户在 `wechat`、`x-post`、`x-thread` 中选择一个；一次给出多个目标时不创建批量任务。
2. 读取 `references/reader-value.md`；仅对解释、判断、解决问题和行动指导类内容定义读者价值。
3. 读取 `{skill_dir}/../writing-rewrite/platforms/<target_id>.yaml`，将共享渠道字段复制为任务内 `channel-contract.yaml`，并将主写作入口的 `output_filename` 规范为 `final.md`；YAML 中的 `rewrite_output_filename` 只供 Rewrite 使用。再读取 `references/baoyu-integration.md`，按渠道合同和 Skill 名称检查本次任务需要的能力。
4. 对用户已经给出的网页、YouTube、文件、图片或历史文章建立素材入口；需要提取时立即路由到对应读取能力。
5. 按 `references/evidence-and-assets.md` 将每项素材与素材接收结果写入 `capability-preflight.md`，并先向用户返回：已接收、已提取、等待处理、失败、需要确认及其影响。失败项不阻塞无关素材。
6. 只完成 capability/material preflight，不生成图片、不排版、不发布。
7. 读取 `references/voice-presets.md`，将 `voice_id` 并入内容契约：默认 `natural-default`，展示当前选择与可用写作声音。用户已指定有效名称、ID 或序号时直接展示该选择；这不是独立等待点。
8. 合并已知信息，只追问阻断字段；展示一次内容契约摘要并等待确认后才进入调研。用户回复“确认”同时确认当前 `voice_id`；可用“修改：写作声音=清晰分析”更新选择。
9. 内容契约确认后、任何初稿前创建或确认 `voice-profile-snapshot.json`。显式非默认 Voice 不可用、无效或创建失败时停留在“等待契约确认”，展示可用项并阻止进入 Phase 3；`natural-default` 运行异常记录 `voice_snapshot: unavailable`，继续既有自然写作而不声称已应用 Voice。
10. **标准或深度写作**在内容契约确认后、Phase 1 前读取 `references/personal-context.md`：在既有 `{run_dir}` 创建或确认 `personal-context-snapshot.json`。只把用户明确选择且已满足 visibility/approval 的素材写入 Snapshot；失败时摘要写 `personal_context: unavailable`，不扫描全局个人目录，也不把未读取资料写成已使用。深度写作只由 Lead 创建/确认 Snapshot，并通过后续 Manifest 将任务内文件交给 Writer 或 Auditor。Voice Snapshot 与 Personal Context Snapshot 独立，互不写入。

产物：

- `brief.md`
- `channel-contract.yaml`
- `capability-preflight.md`
- `status.json`

`capability-preflight.md` 先记录 `selected_mode`、`mode_readiness` 和诊断编号，再记录外部能力、deep 所需的 `handoff_runtime: available | unavailable` 和素材接收结果。每项素材至少记录输入名称、类型、状态、提取产物、失败影响、是否需要用户确认和下一步；素材接收状态使用 `received | extracting | extracted | pending | failed`。

`channel-contract.yaml` 只记录本次目标，并保留所选平台 YAML 的长度、输出类型、视觉和必要派生产物字段；至少补充：

```yaml
entry: writing
target_id: wechat | x-post | x-thread
output_filename: final.md
content_type: release | analysis | review | opinion | tutorial | story
evidence_level: light | standard | strict
source_display: inline | footnote | endnotes | none
asset_policy: source_first | mixed | text_only
ai_editorial_visuals: allowed | ask | excluded
publish_intent: draft_only | prepare | publish_after_confirmation
```

### Phase 1：事实与素材双轨调研

读取 `references/evidence-and-assets.md`。

本阶段不得读取 `voice-profile-snapshot.json` 或全局 Voice Registry；Voice 不影响来源、事实、素材和 accepted claim 的判断。

当用户明确只要选题、内容契约仍是宽主题，或要求近期热点/值得关注的话题时，先读取 `references/research-brief.md` 并执行 Topic Research：

- Host 先检查实时检索能力；缺失时记录 `realtime_research_unavailable`，不生成 Heat、draft 或 canonical Brief。
- quick/standard 由当前 Agent 基于任务 `brief.md`、Snapshot、任务内材料副本和实时来源生成 `research-brief-draft.json`。
- deep 由 Lead 创建 `topic_research -> researcher` Handoff，只传 Manifest 明确列出的任务内输入；Handoff 完成后使用已提升的 draft。
- 运行 `writing-master research save {run_dir} {draft}` 和 `writing-master research verify {run_dir}`，再向用户展示 3–10 个候选及取舍并等待方向选择。
- 用户或 Lead 选定 candidate 后，才进入下面的 Article Research；Research Brief Evidence 不自动成为 `claims.yaml` 中的 accepted claim。

**事实轨**：为正文中的关键主张记录来源、日期、证据等级和表述边界。

**素材轨**：同步寻找官方 GIF、视频、截图、图表、论文插图和用户素材；先登记真实素材，再判断是否需要编辑解释图。

产物：

- `sources.yaml`
- `claims.yaml`
- `asset-manifest.yaml`
- `research-summary.md`

快速模式只维护实际会进入正文的关键主张；标准和深度模式维护完整证据链。涉及近期变化、产品能力、数据、政策或版本时，执行实时检索。素材提取成功不等于事实确认；失败或待确认的素材继续保留在 `capability-preflight.md`，并在任务摘要中说明影响。

标准写作如有个人上下文，只读取任务 Snapshot（`personal-context-snapshot.json`）和 `context-materials/`；不得在调研阶段回读全局个人素材目录。

### Phase 2：角度、读者决策与 Storyboard

本阶段不得读取 `voice-profile-snapshot.json` 或全局 Voice Registry；角度、核心判断、论证结构和 storyboard 保持声音无关。

1. 若存在已验证的 `research-brief.json`，只从用户或 Lead 选定的 candidate 继续；否则按 `references/mode-selection.md` 中当前模式的用户确认规则，给出一个建议角度或多个候选角度及其取舍。
2. 明确一句“读者看完后应形成的判断或行动”。
3. 需要时读取 `references/creative-drainage.md`，排除可替换主题名仍成立的套话角度。
4. 形成文章结构，并为每个视觉位定义职责：Cover、Hero（可省略）、Evidence、Explanation 或 Decorative。
5. 需要确认时等待用户确认核心方向；用户已经明确角度，或 quick 模式没有明显分叉时，只做简短复述并继续。

标准写作只把 Snapshot 中冻结的身份、风格和已选素材作为个人上下文；不得用全局 Profile/Knowledge 覆盖任务内版本。

产物：

- `editorial-brief.md`
- `outline.md`
- `storyboard.md`

### Phase 3：初稿

正文只使用已经接受的 Brief、主张、来源、素材、风格档案和大纲。标准写作的个人上下文只能来自任务 Snapshot 和任务内材料副本。

初稿同时读取任务内唯一的 `channel-contract.yaml`：`wechat` 生成完整长文结构，`x-post` 只生成一条可独立成立的帖子，`x-thread` 按逐条推进的 Thread 结构生成。Writer 不为同一任务生成第二个渠道版本。

读取 `references/voice-presets.md`。Quick / Standard 在本阶段只读取任务 `voice-profile-snapshot.json`，不回读全局 Registry；Deep 仅由 Writer Manifest 列出该 Snapshot 与 hash 后读取。Snapshot 结构、任务 ID 或 hash 校验失败时停止生成，不自动改用当前 Registry 或默认 Voice。

写作要求：

- 每一部分服务于核心编辑判断。
- 官方表述、独立证据、编辑推断和个人经验身份分明。
- 个人经历仅来自用户提供的记录。
- 具体数据关联 `claim_id`；边界条件进入正文，而不是藏在研究笔记里。
- 风格匹配依赖历史文本的可观察特征，不靠随机添加情绪词或口语套句。
- Voice 只调整词汇、句式、节奏、段落、开场、转折、确定性、幽默和类比；事实、证据边界、核心判断、作者立场和真实经历优先。

产物：`draft-v1.md` 和 `claim-usage.yaml`。完成后保留 `draft-v1.md` 原样，后续修订另写版本文件。

### Phase 4：三层审校与修订

读取 `references/three-pass-review.md` 时只采用其中事实、结构、模板句和节奏检查项；本文件中的“展示产物而非隐藏推理”和“以证据报告代替主观百分比”规则优先。

读取 `references/voice-presets.md`。Voice Audit 与 Writer 使用同一任务 `voice-profile-snapshot.json`；每个 Voice issue 都要精确定位正文、引用 Profile 字段/规则、保留原句证据并给出不改变事实或核心判断的修订边界。Snapshot 校验失败时停止审校、验收和发布。

三层职责：

1. **证据层**：事实、日期、版本、因果、引用身份和主张边界。
2. **编辑层**：观点、结构、段落作用、反例、读者决策和冗余。
3. **声音层**：用户风格偏差、模板句、虚假口语、节奏和平台适配。

快速模式合并为一次审校；标准模式由当前 Agent 依次完成三层；深度模式只在真实 Handoff Runtime 可用时由 fresh-context 审计代理执行，再由 Writer 根据结构化问题清单修订。

审校结果必须按严重程度汇总给用户：阻断问题需要补充来源、缩小表述、修改要求或重新生成受影响部分；主要和次要问题可以接受、带理由忽略或请求重写。先集中询问真正需要用户决定的方向性问题，再统一修订，避免每条小问题打断写作。

产物：`review-report.yaml`、`draft-v2.md`、`revision-report.yaml`、`final.md`。`revision-report.yaml` 逐项对应已接受的问题和处理结果。阻断问题未关闭前，任务不得进入已完成、视觉生产或发布状态。

### Phase 5：标题与 canonical final 验收

先完成标题与摘要，再确认 canonical final。

`wechat` 标题至少提供自然版、判断版和传播版；每个标题都要与正文证据强度一致。默认采用与正文最一致的推荐标题写入 `final.md`，同时在交付摘要保留其他候选；用户主动要求选择或修改时再等待该决定。`x-post` 不添加文章标题，只审查首句；`x-thread` 不添加文章标题，只审查第一条的独立价值与整条 Thread 的顺序。

在视觉、排版、Rewrite 或发布前，先在 `acceptance-report.md` 中完成内容验收：

- 标题与正文结论一致；
- 关键主张均有来源或明确标为观点；
- 所有 blocking 审校问题已经关闭；
- `final.md`、来源、主张、素材和审校产物彼此对应。
- `final.md` 已满足当前 `target_id` 的正文、结构和长度合同。

验收通过后，`final.md` 成为本次所选渠道的只读 canonical final；本次验收引用的 `sources.yaml`、`claims.yaml`、`editorial-brief.md`、`outline.md` 与 `research-summary.md` 同时冻结为 canonical package 的只读支持产物。此时向 `channel-contract.yaml` 写入 `source_ref: accepted_final` 和 `source_sha256`；后续 Rewrite 可从该 package 建立渠道中立分析，但视觉、排版、Rewrite 和发布都绝不反向改写 canonical package。

### Phase 6：交付包、视觉、排版与发布

任务只在核心交付包有效时标记完成。所有模式的核心交付包至少包含：

- `final.md`
- `sources.yaml`
- `claims.yaml`
- `asset-manifest.yaml`
- `review-report.yaml`
- `revision-report.yaml`
- `acceptance-report.md`

`acceptance-report.md` 必须列出交付包清单、缺失项、canonical final 的内容验收结果、当前渠道必要产物的状态，以及最终验收结论。用户收到简洁交付摘要和全部文件位置。

主写作的完整交付还必须满足当前 `channel-contract.yaml`：

- `wechat`：`final.md` 作为渠道正文，并组合现有 Baoyu 能力生成 `formatted.md`、`wechat.html` 与 `cover.png`；
- `x-post`：`final.md` 是一条完成渠道审查的 X 单帖；
- `x-thread`：`final.md` 是逐条完成长度和渠道审查的 X Thread。

只在核心交付包和当前渠道必要产物都有效时标记完成。当前渠道失败只影响本任务，不修改其输入材料或之前完成的 Rewrite；第二个渠道始终作为新的 Rewrite 处理。

标准写作实际使用 Snapshot 素材时，在 `final.md` 与 `acceptance-report.md` 已存在后，用 Personal Context Runtime 写入 `context-usage.json`，记录精确 `item_id`、purpose、section/claim 和两个 artifact。交付前运行 `writing-master context verify-run {run_dir}`；校验失败时保留既有产物并报告失败，不把任务标为已完成。

图像类视觉闸门同时满足以下条件后，才执行 Baoyu production：

- `final.md` 已是已验收的 canonical final；
- `claims.yaml` 已明确关键主张；
- `asset-manifest.yaml` 已区分原始素材与编辑生成素材；
- `storyboard.md` 已定义每张图的职责；
- 用户本次请求包含视觉生产、用户在方案阶段确认执行，或当前渠道合同把对应视觉列为必要派生产物。

闸门通过后，按 `references/baoyu-integration.md` 路由配图、封面、信息图或单图生成。Markdown 格式化和公众号 HTML 只要求已验收的 canonical final 与适用的 `channel-contract.yaml`，不要求 storyboard、`asset-manifest.yaml` 或图像类视觉意图。`wechat` 合同声明的格式化、HTML 和封面属于本次渠道必要产物；其他未请求视觉不构成交付包缺失项。

准备发布和实际发布是两个状态。渠道适配 P0 在完整成品处结束，不自动发布；只有用户之后明确发出发布指令时，才把它作为独立动作路由 `baoyu-post-to-wechat` 或 `baoyu-post-to-x`。发布失败不修改 canonical final。

完成后，用户可以独立请求 Rewrite、视觉、排版、发布、保存为个人素材或以此任务创建新任务起点；这些动作都创建关联产物，不改变 canonical final。

用户明确要求从本次编辑中学习时，读取 `references/personal-context.md`：只从具有 baseline/edited hash 和具体证据的修改生成 Style Observation candidate，运行 `writing-master learn propose CANDIDATE.json --run-dir RUN_DIR`，展示规则、范围和证据后等待用户接受或拒绝。非默认 Voice 任务的 Profile 驱动表达不作为 Style Observation 的 baseline 或 evidence；Runtime 不自动决定；只有 accepted observation 会进入后续任务的新 Snapshot，当前任务 Snapshot 与 canonical final 均保持不变。

## 模式差异

| 能力 | 快速草稿 | 标准写作 | 深度写作 |
|---|---|---|---|
| 执行主体 | 当前 Agent | 当前 Agent | Lead + 专项子代理（需要真实 Runtime） |
| 调研 | 关键事实 | 完整双轨 | 独立研究与资产核验 |
| 方向 | 1 个建议方向 | 2–3 个候选 | 独立策划后给出候选 |
| 审校 | 合并一次 | 当前 Agent 三层审校 | 独立 Auditor + Writer 修订 |
| 交付 | 同一核心产物集，可使用简版内容 | 同一核心产物集 | 同一核心产物集，加角色报告和输入 hash |
| Baoyu | 同一套早预检、晚生产规则 | 同左 | 同左，由 Lead 控制闸门 |

详细差异见 `references/mode-selection.md`。深度模式的角色、上下文包和执行图见 `references/agent-orchestration.md`。

## 恢复与失败的用户表现

用户指定“继续 `{task_id}`”时，只有当前运行时已验证任务状态存储和恢复能力，才执行以下步骤：

1. 读取指定运行目录和 `status.json`；
2. 展示恢复的任务、模式、阶段、已完成产物、待确认项和输入变化；
3. 校验可用产物后从正确阶段继续，不重跑无关阶段。

当前运行时未提供上述能力时，明确显示：恢复依赖确定性任务状态存储、运行目录发现、输入 hash 与原子状态更新；这些是 Product–Technical Gap。保留已知产物路径，要求用户指定可用运行目录或继续当前对话任务，不猜测“最近任务”。

普通子步骤异常只有在能自动恢复、保持所选模式且不改变最终交付标准时，才沿用既有重试或局部处理。若异常已经影响所选模式承诺，立即停止当前任务：不派发后续工作、不由当前 Agent 补做深度角色工作、不切换到其他写作模式；保留所有已完成产物和失败前的版本。

### 用户正文：所选模式未就绪

```text
所选的{模式显示名}当前未就绪，任务已停止，尚未进入调研或写作。

如需反馈，请提交 Issue，并附上：
诊断编号：WM-CAP-001
版本：VERSION
```

### 用户正文：运行途中停止

```text
任务在{用户可理解的阶段}阶段停止，未切换到其他写作模式。
已有内容已保留。如需反馈，请提交 Issue 并附诊断编号：WM-RUN-001。
```

### 诊断详情

普通错误正文只描述用户结果。发送时把 `{模式显示名}` 替换为“快速草稿”“标准写作”或“深度写作”，不得固定写成某一种模式。所选模式、内部阶段、Runtime/Handoff/Agent 状态、异常类型和内部异常栈放入单独的诊断详情；默认不展开。发送 `WM-CAP-001` 时用当前安装版本替换 `VERSION`，无法确定时写 `unknown`。两类失败都只提醒用户提交 Issue，不自动创建 Issue，不调用 Issue 工具，也不生成 Issue 草稿。

Voice 恢复只读取任务 Snapshot：旧任务缺少该文件时摘要显示 `voice: 自然默认`、`voice_snapshot: legacy`，内部按 `legacy-natural` 保持原行为；已冻结任务不受 Registry 缺失或升级影响。Snapshot 校验失败不降级，停止后续生成、审校、验收和发布。

## 可用参考文件

- `references/mode-selection.md`：入口问法与三种模式边界
- `references/agent-orchestration.md`：仅供深度模式使用的多 Agent 协议
- `references/personal-context.md`：任务 Snapshot、素材准入、usage 与确认式风格学习
- `references/voice-presets.md`：内容契约 Voice 选择、任务 Snapshot、读取边界、审校与失败语义
- `references/research-brief.md`：上下文感知 Topic Research 的 draft、Evidence、评分与作者匹配合同
- `references/evidence-and-assets.md`：来源、主张、素材与 storyboard 契约
- `references/baoyu-integration.md`：Baoyu 预检、规划、生产和发布路由
- `references/reader-value.md`：读者价值定义
- `references/creative-drainage.md`：创意排水方法
- `references/three-pass-review.md`：三层审校检查项来源

深度模式角色卡：

- `agents/researcher.md`
- `agents/editorial-strategist.md`
- `agents/writer.md`
- `agents/auditor.md`
