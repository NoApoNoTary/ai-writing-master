---
name: writing-master
description: |
  AI Writing Master 的端到端内容创作入口。新建完整文章时先让用户明确选择快速草稿、标准写作或深度写作；快速与标准模式由当前 Agent 单独完成，只有具备真实 Handoff Runtime 的深度模式启用多 Agent。流程覆盖内容契约、素材接收回执、事实与素材双轨调研、选题与 storyboard、写作、审校、验收产物、Baoyu 视觉/排版路由和发布验收。适用于“写文章、写公众号、从零创作、深度写稿”等请求；洗稿改写转 writing-rewrite。
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
- 快速草稿和标准写作始终使用当前 Agent；只有深度模式启用多 Agent，且当前宿主必须具备真实 Handoff Runtime。
- 事实、引用、个人经历和测试结果都要可追溯；未知项保留为待确认项。
- Baoyu 在开题阶段进入能力与素材预检，视觉生产放在证据、角度和文章结构明确之后。
- 重要方向由用户确认；公开发布只响应清晰的发布指令。
- 对用户展示结论、选项、状态和产物，不输出隐藏推理过程。
- 运行时没有确认支持时，不把跨会话恢复、版本回退或深度多 Agent 执行描述为已完成能力；明确展示缺失能力、影响和当前可继续的动作。

## 入口路由

先识别请求属于哪一类：

| 请求 | 行为 |
|---|---|
| 新建完整文章 | 执行“模式选择闸门” |
| 用户已在当前请求中明确说快速、标准或深度 | 直接采用该模式，不重复提问 |
| 继续指定任务 | 检查任务恢复能力；已验证可用时读取指定 `task_id`，否则展示 Product–Technical Gap 和已知产物 |
| 洗稿、改写、平台重写 | 转 `writing-rewrite` |
| 只做选题、审校、标题或素材规划 | 在当前 Skill 内执行对应模块，不虚构独立 Skill |
| 只做配图、封面、信息图、HTML 或发布 | 只读取已验收的 canonical final，读取 `references/baoyu-integration.md` 后路由到实际存在的 Baoyu Skill |

### 模式选择闸门

新建完整文章且用户尚未选择模式时，只询问下面这一题，然后等待回复：

读取 `references/mode-selection.md` 中的 Canonical prompt，原样展示后等待用户回复。
在用户回复前，不创建运行目录、不开始调研，也不执行 Baoyu。

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
  "mode": "quick | standard | deep",
  "execution": "single_agent | multi_agent",
  "platform": "wechat | x | other",
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

快速、标准模式设置 `execution=single_agent`；深度模式仅在当前宿主证实可执行真实 Handoff 时设置 `execution=multi_agent` 并读取 `references/agent-orchestration.md`。缺少该能力时，说明深度模式受影响，保持等待用户选择或结束任务，不模拟多 Agent 结果。

## 用户可见任务合同

每次阶段变更、等待用户或失败时，都用用户语言给出同一份简洁摘要：

```text
任务：{task_id 或“当前对话任务”}
模式：{quick | standard | deep}
阶段：{用户状态}
状态：{进行中 | 等待用户 | 失败 | 已取消 | 已完成}
已完成：{产物或阶段}
当前动作：{正在处理什么}
等待你：{没有则写“无”}
下一步：{继续方式}
最近失败：{没有则写“无”}
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

只在模式、内容契约、重大方向、标题、阻断问题和发布需要用户决定时中断。每个等待点都给出明确问题和继续方式：

| 等待点 | 必须展示的问题 | 继续方式 |
|---|---|---|
| 内容契约 | `请确认内容契约：{摘要}` | 回复“确认”，或用“修改：字段=值”更新，或回复“取消” |
| 方向 | `请选择方向：1/2/3，或说明你要修改的取舍。` | 选择、修改或取消 |
| 标题 | `请选择标题：自然版 / 判断版 / 传播版，或给出你的修改。` | 选择、修改或继续使用用户已给标题 |
| 审校问题 | `审校发现 {blocking} 个阻断、{major} 个主要问题。需要你决定：{方向性问题}` | 接受建议、忽略非阻断项、修改原始要求、补充证据，或要求重写受影响部分 |
| 发布 | `最终产物已验收。是否发布到 {平台}？` | 只有“发布到 {平台}”这类明确指令才产生外部副作用 |

“继续”“下一步”只推进到下一份可审阅产物，不等同于发布指令。阻断问题不得通过“忽略”进入已完成或发布状态。

## 核心工作流

### Phase 0：内容契约、能力预检与素材接收

1. 收集主题、目标读者、平台、时效、字数、文章目的、已有素材、是否需要视觉/排版/发布。
2. 读取 `references/reader-value.md`；仅对解释、判断、解决问题和行动指导类内容定义读者价值。
3. 读取 `references/baoyu-integration.md`，按 Skill 名称检查本次任务需要的能力。
4. 对用户已经给出的网页、YouTube、文件、图片或历史文章建立素材入口；需要提取时立即路由到对应读取能力。
5. 按 `references/evidence-and-assets.md` 将每项素材与素材接收结果写入 `capability-preflight.md`，并先向用户返回：已接收、已提取、等待处理、失败、需要确认及其影响。失败项不阻塞无关素材。
6. 只完成 capability/material preflight，不生成图片、不排版、不发布。
7. 合并已知信息，只追问阻断字段；展示一次内容契约摘要并等待确认后才进入调研。

产物：

- `brief.md`
- `channel-contract.yaml`
- `capability-preflight.md`
- `status.json`

`capability-preflight.md` 同时记录外部能力、`handoff_runtime: available | unavailable` 和素材接收结果。每项素材至少记录输入名称、类型、状态、提取产物、失败影响、是否需要用户确认和下一步；素材接收状态使用 `received | extracting | extracted | pending | failed`。

`channel-contract.yaml` 至少记录：

```yaml
content_type: release | analysis | review | opinion | tutorial | story
platform: wechat | x | other
evidence_level: light | standard | strict
source_display: inline | footnote | endnotes | none
asset_policy: source_first | mixed | text_only
ai_editorial_visuals: allowed | ask | excluded
publish_intent: draft_only | prepare | publish_after_confirmation
```

### Phase 1：事实与素材双轨调研

读取 `references/evidence-and-assets.md`。

**事实轨**：为正文中的关键主张记录来源、日期、证据等级和表述边界。

**素材轨**：同步寻找官方 GIF、视频、截图、图表、论文插图和用户素材；先登记真实素材，再判断是否需要编辑解释图。

产物：

- `sources.yaml`
- `claims.yaml`
- `asset-manifest.yaml`
- `research-summary.md`

快速模式只维护实际会进入正文的关键主张；标准和深度模式维护完整证据链。涉及近期变化、产品能力、数据、政策或版本时，执行实时检索。素材提取成功不等于事实确认；失败或待确认的素材继续保留在 `capability-preflight.md`，并在任务摘要中说明影响。

### Phase 2：角度、读者决策与 Storyboard

1. 按 `references/mode-selection.md` 中当前模式的用户确认规则，给出一个建议角度或多个候选角度及其取舍。
2. 明确一句“读者看完后应形成的判断或行动”。
3. 需要时读取 `references/creative-drainage.md`，排除可替换主题名仍成立的套话角度。
4. 形成文章结构，并为每个视觉位定义职责：Cover、Hero（可省略）、Evidence、Explanation 或 Decorative。
5. 需要确认时等待用户确认核心方向；用户已经明确角度，或 quick 模式没有明显分叉时，只做简短复述并继续。

产物：

- `editorial-brief.md`
- `outline.md`
- `storyboard.md`

### Phase 3：初稿

正文只使用已经接受的 Brief、主张、来源、素材、风格档案和大纲。

写作要求：

- 每一部分服务于核心编辑判断。
- 官方表述、独立证据、编辑推断和个人经验身份分明。
- 个人经历仅来自用户提供的记录。
- 具体数据关联 `claim_id`；边界条件进入正文，而不是藏在研究笔记里。
- 风格匹配依赖历史文本的可观察特征，不靠随机添加情绪词或口语套句。

产物：`draft-v1.md` 和 `claim-usage.yaml`。完成后保留 `draft-v1.md` 原样，后续修订另写版本文件。

### Phase 4：三层审校与修订

读取 `references/three-pass-review.md` 时只采用其中事实、结构、模板句和节奏检查项；本文件中的“展示产物而非隐藏推理”和“以证据报告代替主观百分比”规则优先。

三层职责：

1. **证据层**：事实、日期、版本、因果、引用身份和主张边界。
2. **编辑层**：观点、结构、段落作用、反例、读者决策和冗余。
3. **声音层**：用户风格偏差、模板句、虚假口语、节奏和平台适配。

快速模式合并为一次审校；标准模式由当前 Agent 依次完成三层；深度模式只在真实 Handoff Runtime 可用时由 fresh-context 审计代理执行，再由 Writer 根据结构化问题清单修订。

审校结果必须按严重程度汇总给用户：阻断问题需要补充来源、缩小表述、修改要求或重新生成受影响部分；主要和次要问题可以接受、带理由忽略或请求重写。先集中询问真正需要用户决定的方向性问题，再统一修订，避免每条小问题打断写作。

产物：`review-report.yaml`、`draft-v2.md`、`revision-report.yaml`、`final.md`。`revision-report.yaml` 逐项对应已接受的问题和处理结果。阻断问题未关闭前，任务不得进入已完成、视觉生产或发布状态。

### Phase 5：标题与 canonical final 验收

先完成标题与摘要，再确认 canonical final。

标题至少提供自然版、判断版和传播版；每个标题都要与正文证据强度一致。用户选择后写入 `final.md`。

在视觉、排版、Rewrite 或发布前，先在 `acceptance-report.md` 中完成内容验收：

- 标题与正文结论一致；
- 关键主张均有来源或明确标为观点；
- 所有 blocking 审校问题已经关闭；
- `final.md`、来源、主张、素材和审校产物彼此对应。

验收通过后，`final.md` 成为只读 canonical final。后续 Rewrite、视觉、排版和发布只读取该文件及其关联产物，绝不反向改写 canonical final。

### Phase 6：交付包、视觉、排版与发布

任务只在核心交付包有效时标记完成。标准交付包至少包含：

- `final.md`
- `sources.yaml`
- `claims.yaml`
- `asset-manifest.yaml`
- `review-report.yaml`
- `revision-report.yaml`
- `acceptance-report.md`

`acceptance-report.md` 必须列出交付包清单、缺失项、canonical final 的内容验收结果、可选视觉/HTML/平台草稿的状态，以及最终验收结论。用户收到简洁交付摘要和全部文件位置。

视觉闸门同时满足以下条件后，才执行 Baoyu production：

- `final.md` 已是已验收的 canonical final；
- `claims.yaml` 已明确关键主张；
- `asset-manifest.yaml` 已区分原始素材与编辑生成素材；
- `storyboard.md` 已定义每张图的职责；
- 用户本次请求包含视觉生产，或用户在方案阶段确认执行。

然后按 `references/baoyu-integration.md` 路由配图、封面、信息图、Markdown 格式化或公众号 HTML。未请求视觉、HTML 或平台草稿时，它们不构成交付包缺失项。

准备发布和实际发布是两个状态。先保存草稿和最终验收报告；只有用户明确发出发布指令时，才路由 `baoyu-post-to-wechat` 或 `baoyu-post-to-x`。平台失败只记录在对应平台产物中，不修改 canonical final 或其他平台版本。

完成后，用户可以独立请求 Rewrite、视觉、排版、发布、保存为个人素材或以此任务创建新任务起点；这些动作都创建关联产物，不改变 canonical final。

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

阶段失败时，任务摘要必须说明失败动作、影响范围、已保留产物和可执行下一步。重试、回退和取消只作用于受影响阶段；没有运行时的 attempt 历史时，不承诺不可变回退。

## 可用参考文件

- `references/mode-selection.md`：入口问法与三种模式边界
- `references/agent-orchestration.md`：仅供深度模式使用的多 Agent 协议
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
