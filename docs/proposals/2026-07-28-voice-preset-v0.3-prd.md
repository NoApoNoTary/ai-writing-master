# AI Writing Master Voice Preset v0.3 PRD

> 状态：已实施并验收
> 日期：2026-07-28
> 来源会话：`019fa912-dea6-7052-82db-2665faee26f8`
> 执行归属：**主线升级 Session**——负责 Voice Preset Runtime、选择器、Snapshot、工作流接入、测试与最终 Pilot
> 并行依赖：模板 Session 只向实验目录交付 `voice-profile.json` 与 `READY`，不负责主线实现
> 产品术语：用户侧称“写作声音”，内部模型称 `Voice Preset` / `voice_profile`

## Executive Decision

v0.3 增加**任务级写作声音选择器**，不建设完整人格系统。

- 内容的事实、证据、核心判断、作者立场和真实经历保持原流程；Voice Preset 只控制表达层。
- 首版内置 `自然默认` 与 3 个差异明显的声音预设。
- 选择动作并入内容契约确认，不新增一次独立等待。
- 每个新任务冻结一份 `voice-profile-snapshot.json`，后续写作、审校和恢复都读取任务快照。
- Researcher 与 Editorial Strategist 不读取 Voice Preset；Writer 与 Voice Auditor 读取。
- Voice Preset 与长期 Personal Context Style Profile 分离，预设内容不写回用户长期风格。
- Nuwa 只作为首批模板的离线提炼方法，不引入 Nuwa、`chat_with_me` 或其他外部运行时。
- 首个真实 Pilot 使用 `@Khazix0918` 的 X 长文章语料生成一个实验 Profile，再对现有 canonical final 做不覆盖原稿的改写、审校和晋级判断。
- 运行时数据采用 JSON，而不是前序讨论中的 YAML 草案：当前项目无 YAML 依赖，JSON 可直接复用既有校验、hash、原子写入和测试模式。

## Problem Statement

当前 Writing Master 已经能完成调研、观点组织、写作和三层审校，但生成文本仍容易出现统一的“AI 腔”：句式、节奏、开场、转折和情绪强度缺少稳定而鲜明的差异。

现有 Personal Context Style Profile 解决的是“用户自己的长期作者风格”，它来自用户确认过的 Style Observations，并被冻结进任务 Snapshot。把博主口吻直接塞入该档案会造成三个问题：

1. 临时选择会污染用户长期风格；
2. 表达方式可能反向改变观点和事实边界；
3. 外部 Skill、抓取器或账号语料库会增加运行时依赖，却未必真正降低 AI 味。

用户需要的是：在不改变文章“脑子”的前提下，为当前任务换一套可选择、可审计、可恢复的“声音”。

## Solution

建设一个内置 Voice Preset Registry，并在新建完整文章的内容契约中加入可选 `voice_id`。

系统根据用户选择把对应 Profile 冻结为任务快照。调研、事实确认、核心角度和大纲继续按原流程执行；进入初稿时，Writer 才将任务快照作为表达约束；进入 Voice Audit 时，Auditor 使用同一快照检查可观察偏差。

### Product Principle

> 脑子保持不变，只换声音。

优先级从高到低：

1. 已确认的事实、证据边界、真实经历和安全的数据约束；
2. 已确认的 Brief、核心判断、作者立场和 Editorial Brief；
3. Channel Contract 的硬性平台要求；
4. 当前任务选择的 Voice Preset，仅作用于表达维度；
5. Personal Context Style Profile 中未与 Voice Preset 冲突的表达习惯；
6. 通用写作默认值。

任何 Voice Preset 都无权制造经历、改写事实、增强证据强度、替换作者立场或改变核心结论。

### Primary Flow

```text
模式选择
→ 内容契约中选择 voice_id
→ 冻结 voice-profile-snapshot.json
→ Researcher：事实和素材，不读取 Voice Preset
→ Editorial Strategist：角度和结构，不读取 Voice Preset
→ Writer：读取已确认内容包 + Voice Snapshot
→ Auditor：Evidence / Editorial / Voice 三层审校
→ 修订与 canonical final 验收
```

### User-facing Selector

首版选项暂定为：

| `voice_id` | 用户名称 | 作用 |
|---|---|---|
| `natural-default` | 自然默认 | 不附加临时声音覆盖；继续使用任务内作者风格和现有默认规则 |
| `clear-analytical` | 清晰分析 | 高信息密度、克制、结构清楚、少情绪包装 |
| `conversational-observer` | 对话观察 | 自然口语、具体观察、柔和转折、避免平台套话 |
| `sharp-commentary` | 锐利评论 | 判断先行、短句节奏、受控幽默、明确边界 |

选择器不成为独立等待点。内容契约摘要必须显示当前选择与可用选项；用户回复“确认”即接受默认值，也可用“修改：写作声音=清晰分析”完成选择。

## Goals and Success Criteria

### Goals

1. 让用户在一次内容契约确认中选择当前任务的表达声音。
2. 让 3 个非默认预设在句式、节奏、段落、开场、转折、确定性和幽默等维度上有可观察差异。
3. 保持事实、观点、作者身份和真实经历不受声音预设影响。
4. 保证任务恢复时使用创建任务时的同一份 Profile，而不是读取已变化的全局模板。
5. 保证 Voice Preset 不进入用户长期 Style Profile，也不成为默认风格学习证据。
6. 不增加外部运行时、网络调用或第三方 Python 依赖。
7. 用一份真实 Profile 和一篇真实旧稿走通“模板提炼 → 应用 → Voice Audit → 内容回归 → 晋级决策”的闭环。

### Release Success Criteria

- 新任务都能明确显示 `voice_id`；未选择时确定性使用 `natural-default`。
- 所有模式都产生可验证的 Voice Snapshot，或对旧任务明确标记 `legacy-natural`。
- Deep 模式只有 Writer 和 Auditor 的 Manifest 包含 Voice Snapshot。
- Voice Audit 的每个问题都能引用具体 Profile 规则和正文位置，不使用笼统“AI 味”评分代替证据。
- 在固定内容包的人工验收中，3 个非默认 Profile 至少在 5 个声明维度上形成可识别差异，同时不改变 accepted claims、核心判断和第一人称事实。
- Khazix Pilot 不读取日常动态，只使用 X Article 长文；模板产出与主线实施并行，主线仅在 Pilot 阶段等待 `READY` 产物。
- 现有测试全部通过，新功能不改变未选择 Voice Preset 的既有交付包语义。

## User Stories

1. As a 写作者, I want 在创建文章时看到可用写作声音, so that 我能主动决定文章如何说话。
2. As a 写作者, I want 默认选项保持当前自然写作行为, so that 我不使用新功能时不会得到意外变化。
3. As a 写作者, I want 每个声音看到简短说明和适用场景, so that 我能根据文章目的选择而不是猜测名字。
4. As a 写作者, I want 在同一次内容契约确认里完成声音选择, so that 工作流不会多增加一次等待。
5. As a 写作者, I want 在初始请求中直接写明声音名称或 ID, so that 系统无需再次询问已经明确的信息。
6. As a 写作者, I want 文章观点和事实保持原样, so that 换声音不会变成换立场。
7. As a 写作者, I want 第一人称经历只来自我的材料, so that 声音模板不会制造虚构故事。
8. As a 写作者, I want 平台硬限制优先于声音习惯, so that 输出仍符合实际发布要求。
9. As a 写作者, I want 恢复中断任务时继续使用原来的声音, so that 同一篇文章前后不会漂移。
10. As a 写作者, I want 明确知道当前任务使用了哪个声音, so that 我能判断结果和选择之间的关系。
11. As a 写作者, I want 非法或过期的声音 ID 得到清晰提示, so that 系统不会静默换成另一种口吻。
12. As a 写作者, I want 显式选择的 Profile 加载失败时停止进入初稿, so that 系统不会假装应用了我的选择。
13. As a 写作者, I want 自然默认加载异常时仍保留原有写作能力并显示降级状态, so that 非核心故障不会毁掉任务。
14. As a 写作者, I want 预设声音不污染我的长期作者风格, so that 一次实验不会改变后续所有文章。
15. As a 写作者, I want 使用非默认声音的任务默认不参与风格学习, so that 系统不会把借用的表达误判成我的习惯。
16. As a 维护者, I want Voice Profile 是静态、可验证的数据, so that 添加模板不需要新增一套写作引擎。
17. As a 维护者, I want Profile 有稳定 ID、版本和 hash, so that 任务恢复和问题复现具有确定性。
18. As a 维护者, I want 每个 Profile 只包含表达特征, so that 身份、价值观和认知模型不会混进写作合同。
19. As a 维护者, I want 示例全部是合成示例, so that 模板不携带原博主原句和个人事实。
20. As a 维护者, I want Profile 使用描述性名称而不是创作者姓名, so that 产品提供的是表达能力而不是身份扮演。
21. As a Writer, I want 只读取当前选中的 Profile Snapshot, so that 上下文不会被全部模板占满或互相干扰。
22. As an Auditor, I want 用同一份 Snapshot 检查声音偏差, so that 审校标准与生成标准一致。
23. As a Researcher, I want 不读取 Voice Preset, so that 资料选择和事实判断不受表达偏好影响。
24. As an Editorial Strategist, I want 不读取 Voice Preset, so that 核心角度和论证结构不被人物口吻绑架。
25. As a Deep-mode Lead, I want 通过 Manifest 明确传递 Voice Snapshot, so that 角色隔离和输入 hash 仍可验证。
26. As a Rewrite 用户, I want 已验收正文继续作为 canonical source, so that 平台改写不会重新选择声音并反向修改原稿。
27. As a 旧任务用户, I want v0.3 上线后旧任务继续保持原行为, so that 缺少 Voice Snapshot 不会导致恢复失败。
28. As a 项目维护者, I want Nuwa 只用于离线制作模板, so that 生产流程没有外部 Skill 和网络依赖。
29. As a 项目维护者, I want 首个 Profile 只从目标作者的 X 长文章提炼, so that 日常短动态不会污染长文声音。
30. As a 项目维护者, I want 模板提炼与主线实现并行, so that Runtime 开发不必等待内容研究完成。
31. As a 项目维护者, I want 在模板冻结后再读取目标作者公开的官方写作 Skill, so that Nuwa 的提炼能力能被盲测而不是提前泄题。
32. As a 写作者, I want 用现有不满意的文章做真实改写实验, so that 我看到的不是抽象评分而是可对比结果。
33. As a 写作者, I want Pilot 不覆盖原 `final.md`, so that 实验失败时原 canonical final 仍可回退。
34. As a 产品决策者, I want Pilot 最终给出 promote / revise / reject 结论, so that 一个 Profile 不会因为“看起来有趣”就直接进入内置 Registry。

## Functional Requirements

### FR-1：领域边界

- `VoiceProfile` 表示当前任务的表达方式。
- `StyleProfile` 表示用户长期、经确认的作者风格。
- 两者必须保持独立的存储、快照、状态和学习语义。
- 用户界面使用“写作声音”；内部不得把该能力建模为身份扮演、人格复制或完整 Persona。

### FR-2：选择入口

- Voice 选择发生在模式选择之后、内容契约确认之内。
- `voice_id` 是内容契约字段，默认值为 `natural-default`。
- 用户可通过序号、稳定 ID 或当前显示名称选择。
- 用户已在请求中明确指定有效 Voice 时，内容契约直接展示该选择，不重复提问。
- 未知 ID、重名或不可用 Profile 必须返回可用列表并停留在内容契约确认状态。

### FR-3：首版内置范围

- 首版只提供 `natural-default` 和 3 个非默认 Profile。
- 三个 Profile 必须在至少 5 个可观察表达维度上有实质差异。
- Profile 名称使用行为描述，不使用真实创作者姓名、头像、身份或经历。
- `natural-default` 不覆盖任务内 Style Profile；不存在个人 Style 时继续使用现有通用写作规则。

### FR-4：Profile Contract

Profile 至少包含：

```json
{
  "schema_version": 1,
  "id": "clear-analytical",
  "version": 1,
  "label": "清晰分析",
  "description": "用户可见说明",
  "best_for": ["analysis", "tutorial"],
  "scope": "expression_only",
  "voice": {
    "register": [],
    "sentence_rhythm": [],
    "paragraph_shape": [],
    "pacing": [],
    "opening": [],
    "transitions": [],
    "certainty": [],
    "humor": [],
    "analogy": [],
    "vocabulary": []
  },
  "avoid": [],
  "preserve": [
    "facts",
    "evidence_boundaries",
    "core_thesis",
    "author_position",
    "real_experiences"
  ],
  "examples": []
}
```

约束：

- `id` 在同一 registry 内唯一且发布后不复用。
- `version` 只递增；修改任何语义字段都产生新版本。
- `scope` 首版固定为 `expression_only`。
- `preserve` 必须与上述固定集合完全一致，Profile 不得删减。
- `examples` 只保存短小合成示例及其对应规则，不保存来源原文。
- Profile 必须足够紧凑；运行时只把当前选中的一个 Profile 注入任务。

### FR-5：任务快照

- 内容契约确认后、任何初稿生成前，运行时创建 `voice-profile-snapshot.json`。
- Snapshot 保存任务 ID、选择来源、Profile ID、Profile 版本、Profile hash 和完整 Profile 内容。
- 相同任务、相同 `voice_id` 的重复 Snapshot 操作必须幂等。
- Snapshot 已存在时，不得用不同 `voice_id` 静默覆盖。
- Registry 后续更新只影响新任务；已有任务始终读取自己的 Snapshot。
- Snapshot hash 不一致、结构无效或被篡改时，Phase 3 及之后必须停止。

### FR-6：读取边界

- Quick / Standard：当前 Agent 在 Phase 3 与 Voice Audit 读取任务 Voice Snapshot。
- Deep：Writer 与 Auditor 的 Manifest `allowed_inputs` 必须列出 Voice Snapshot 及 hash。
- Researcher 与 Editorial Strategist 的 Manifest 不得列出 Voice Snapshot。
- 任何角色都不得在任务执行期间回读全局 registry 替代任务 Snapshot。

### FR-7：生成边界与优先级

- Writer 只能把 Profile 用于词汇、句式、节奏、段落形态、开场、转折、确定性、幽默和类比方式。
- Profile 与 accepted claim、Brief、Editorial Brief、真实经历或 Channel Contract 冲突时，Profile 规则失效，其他合同保持不变。
- Voice Preset 不得新增人物、事件、数字、引述、测试结果、感官细节或第一人称事实。
- Profile 不得要求“模仿某人”“扮演某人”或输出身份声明。

### FR-8：Voice Audit

- Voice Audit 使用与 Writer 相同的 Voice Snapshot。
- 每个 Voice issue 必须记录正文位置、Profile 字段或规则、原句和明确修订边界。
- “像 AI”“不够像某博主”或主观百分比不能单独构成 issue。
- Voice Audit 同时检查：已声明特征是否缺失、`avoid` 是否命中、是否用随机口头禅制造人感、是否因追求声音而破坏内容合同。
- Evidence 或 Editorial 合同与 Voice 冲突时，Voice issue 不得要求牺牲事实或观点来关闭。

### FR-9：状态、摘要与恢复

- `status.json` 至少记录当前 `voice_id`、Profile 版本、Snapshot 状态和 Snapshot hash。
- 用户可见任务摘要显示 `voice: {label}` 与 `voice_snapshot: ready | legacy | unavailable`，不显示内部全局路径。
- Resume 只读取任务 Snapshot；Registry 缺失或升级不影响已冻结任务。
- v0.3 之前创建且没有 Voice Snapshot 的任务标记为 `legacy-natural`，继续原行为，不补写一个可能改变旧结果的新 Profile。

### FR-10：选择变更

- 内容契约确认前可以自由修改 Voice。
- 内容契约确认并创建 Snapshot 后，v0.3 不在原任务内切换 Voice。
- 用户需要另一种声音时创建关联新任务；多声音并行生成、比较和中途热切换留待后续版本。

### FR-11：Personal Context 与学习隔离

- Voice Snapshot 不写入 `personal-context-snapshot.json`。
- Voice Profile 不创建 Style Observation，也不参与 Style Profile 重建。
- 使用非默认 Voice 的任务默认不得作为确认式风格学习的 baseline 或 evidence。
- “把这个声音的一部分变成我的长期风格”属于未来的显式采纳流程，不在 v0.3 内隐式完成。

### FR-12：Rewrite 边界

- Writing Rewrite 继续只读取已验收 canonical final 或 standalone input。
- v0.3 不为 Rewrite 增加独立 Voice Selector。
- 来自 Writing Master 的正文在平台 Rewrite 中保持其已验收声音；平台合同只做必要的平台适配，不反向修改 canonical final。

### FR-13：失败语义

- 用户显式选择非默认 Voice，而 Profile 不存在、无效或无法创建 Snapshot：阻止进入 Phase 3，并显示可执行错误。
- 默认 `natural-default` 的 Profile 运行异常：记录 `voice_snapshot: unavailable`，继续既有自然写作行为，不声称已应用 Profile。
- Snapshot 校验失败：阻止生成、审校和发布，不自动改用当前 Registry。
- Voice Audit 失败不影响 Evidence Audit 的已完成事实，但在声音问题关闭前不得把结果标记为完全通过。

### FR-14：模板生产

- Nuwa 仅用于离线分析一手文本中的可观察表达特征。
- 提炼过程必须删除身份、世界观、价值判断、人物经历、近期动态和角色扮演指令。
- 最终模板由项目维护者人工复核并转换为项目自己的 Profile Contract。
- 生产运行时不调用 Nuwa、`chat_with_me`、抓取器或远程模型来生成 Profile。

### FR-15：首个真实 Pilot

- 目标账号为 X 上的 `@Khazix0918`，仅使用该账号发布的 X Article 长文章正文。
- Corpus 必须排除普通 `status` 动态、回复、转发、引用帖、评论区、个人简介和文章推广短帖。
- 模板会话使用 Nuwa 的文章采集、表达 DNA、Voice Check 与 Fidelity 思路，但跳过心智模型、决策启发式、价值观、时间线、身份卡和角色扮演。
- Blind Profile 冻结前不得读取目标作者公开的 `khazix-writer` Skill；冻结后才把该 Skill 作为本人自述的 post-hoc benchmark，比较 Nuwa 提炼的命中与遗漏。
- 目标作者来源信息只保留在实验 provenance 中；若 Profile 晋级产品 Registry，用户可见名称必须改为表达特征名称。
- 模板产出目录固定为 `experiments/voice-presets/khazix0918/`；主线以其中的 `READY` 和 `voice-profile.json` 为 Pilot readiness gate。
- 主线 Runtime、Snapshot 与工作流合同可以在模板未完成时继续实施；只有进入真实改写 Pilot 时才检查 readiness gate。
- Gate 缺失时，Pilot 状态为 `template_pending` 并停止该阶段；不得临时改用目标作者官方 Skill、自然默认或未验收草稿冒充 Nuwa Profile。
- Pilot 输入固定为 `/home/amose/.writing-master/runs/20260728-001/final.md`，基线 SHA-256 为 `0601c5a1fd9e78416a28032ca65b46518efac5f0debe0c82a7c1b4c0afe26b7d`。
- Pilot 必须复制输入后再改写，绝不覆盖原 `final.md`。
- 改写只改变表达层，保留事实、引用标记、来源、核心判断、论证顺序、风险边界和第一人称事实；允许调整段落长度、转场、局部标题和列表表现。
- Pilot 完成后输出 baseline、rewritten、Voice Audit、内容回归对比和 `promote | revise | reject` 结论。

## Implementation Decisions

1. **复用现有工作流，不新增写作引擎。** Voice 是 Phase 3 和 Voice Audit 的附加输入，不改变 Phase 1、Phase 2、canonical final 或发布链路。
2. **只增加一个新的运行时边界：Voice Registry → Task Snapshot。** 其余角色通过现有任务产物与 Manifest 读取。
3. **使用 JSON 和 Python 标准库。** 不添加 YAML 解析器或新依赖；复用项目已有的 canonical JSON、SHA-256、原子写入、稳定错误码和路径安全模式。
4. **提供最小 CLI 合同。** `voice list` 返回可用 Profile；`voice snapshot` 创建或确认任务快照；`voice verify-run` 校验状态与 hash。首版不提供在线编辑器、导入器或生成器。
5. **一个 Registry、一个任务 Snapshot。** 首版 Profile 数量很少，不建设数据库、插件系统、市场或远程配置。
6. **自然默认也是确定性选择。** 新任务始终有明确 `voice_id`；默认值不是缺失值。
7. **Profile 版本不可变。** 已发布版本只读；修改语义时增加版本，旧任务依靠 Snapshot 继续复现。
8. **Deep 模式沿用 Manifest 隔离。** 只扩展 Writer/Auditor 的允许输入，不绕过现有 Handoff Runtime。
9. **Voice issue 沿用现有 `review-report.yaml`。** 不新增第二套审校报告，只在 `layer: voice` 中引用 Profile 规则。
10. **不做自动风格量化评分。** 机械语言工具可提供预警，但不能代替 Profile 对照和人工内容验收。
11. **Profile 使用描述性品牌。** 首批声音可由多个优秀样本启发，但不以真实博主姓名对外呈现，也不保留来源原句。
12. **首版冻结后不切换。** 这是为保持任务产物和审校输入确定性的刻意收缩；需要 A/B 时再建立关联任务能力。
13. **模板生产与主线解耦。** 独立会话按实验任务书生成 Khazix Profile；主线先实现通用合同，到 Pilot 节点只检查 `READY`，没有则停在该节点。
14. **盲提炼后再对照官方 Skill。** `khazix-writer` 是高价值的一手 benchmark，但提前读取会让 Nuwa 测试失真；只允许在 Blind Profile 写入后用于验证和修正。

## Testing Decisions

### What Makes a Good Test

- 测试外部合同：用户选择、任务产物、状态、hash、角色输入和失败语义。
- 不测试 LLM 的隐藏推理，也不把某一篇具体文案当成永久金句快照。
- 对生成质量采用固定内容包 + 可观察 Profile 规则的人工验收；对运行时确定性采用自动测试。

### Automated Tests

1. Registry 校验：唯一 ID、唯一默认项、版本、固定 `scope`、固定 `preserve`、必填字段和非法数据。
2. CLI 合同：`list`、`snapshot`、`verify-run` 的成功、JSON 输出和稳定错误码。
3. Snapshot 幂等：同任务同 Voice 重试不改变内容；不同 Voice 返回冲突且不覆盖原文件。
4. Snapshot 完整性：Registry 更新、删除或顺序变化后，旧任务仍可验证并恢复。
5. 篡改检测：Snapshot、状态 hash 或任务 ID 不一致时验证失败。
6. 路径安全：任务目录替换、符号链接和越界路径不能把 Snapshot 写到任务外。
7. Workflow Contract：Voice 选择位于内容契约中，不增加新的用户等待点。
8. Phase Contract：Researcher / Editorial Strategist 不读取 Voice；Writer / Auditor 读取。
9. Deep Handoff：Manifest 对 Voice Snapshot 的 allowed input 与 hash 可验证，过期输入使 Handoff stale。
10. Audit Contract：Voice issue 必须包含位置、证据、Profile 规则和 required change。
11. Learning Isolation：非默认 Voice 任务不能直接产生长期 Style Observation。
12. Backward Compatibility：无 Voice Snapshot 的旧任务继续 `legacy-natural` 行为。
13. Rewrite Contract：Rewrite 仍从 canonical final 或 standalone input 开始，不出现独立 Voice 选择路径。
14. Regression：现有 Personal Context、Research Brief、Handoff、Skill Contract 和 CLI 测试全部通过。

优先复用现有最高层测试缝：工作流文档合同测试、任务 Snapshot/CLI 测试、Handoff Manifest 测试；不为每个 Markdown 片段建立重复低层测试。

### Khazix End-to-End Pilot

模板会话与主线并行运行，详细合同见 `experiments/voice-presets/khazix0918/TEMPLATE_TASK.md`。

主线进入 Pilot 时执行以下闭环：

1. 检查 `READY` 与 `voice-profile.json`；缺失则记录 `template_pending` 并停在这里。
2. 校验 Profile schema、固定 `preserve`、Profile hash 与模板报告。
3. 复制基线 `final.md` 到实验输出，不修改 Writing Master 原任务。
4. 对基线运行机械语言预警并记录可观察问题；该结果只作信号，不作 Voice 真值。
5. 只读取基线正文与实验 Voice Profile，生成 `pilot-rewrite.md`，不做新调研、不新增事实或个人经历。
6. 运行 Evidence Regression：逐项检查引文、日期、产品名、限制条件、来源列表和核心判断是否保留。
7. 运行 Editorial Regression：检查论证顺序、适用人群、风险边界和行动建议是否发生语义漂移。
8. 运行 Voice Audit：按 Profile 字段定位命中、缺失、过度模仿和 `avoid` 命中。
9. 生成逐段对比与总结，明确哪些变化改善了自然度，哪些变化牺牲了清晰度或可信度。
10. 给出 `promote | revise | reject`：只有内容回归通过且 Voice 改善可解释时才允许晋级候选 Registry。

Pilot 产物至少包括：基线副本、`pilot-rewrite.md`、`review-report.yaml`、`comparison.md` 和 `pilot-decision.md`。

### Manual Release Benchmark

使用同一份固定 Brief、accepted claims、Editorial Brief 和用户材料，分别生成自然默认与 3 个非默认版本：

- 对比事实、核心判断、作者立场和第一人称事实，必须保持一致；
- 按每个 Profile 声明的维度逐项检查命中与 `avoid`；
- 确认任一版本都没有通过虚构经历、随机口头禅或平台套话制造差异；
- 确认 Auditor 能把主要声音偏差定位到具体规则，而不是给出笼统评分；
- 结果作为首批 Profile 是否可发布的验收记录，不把单次模型输出写成自动化 golden text。

## Acceptance Scenarios

### Scenario A：自然默认的新任务

1. 用户选择任意写作模式，未指定 Voice。
2. 内容契约显示“自然默认”，用户一次确认。
3. 系统冻结 `natural-default` Snapshot。
4. 文章按现有 Style Profile 和默认规则生成，交付包结构不变。

**通过条件：** 没有新增等待点，没有临时声音覆盖，没有长期 Style 变更。

### Scenario B：Standard 选择清晰分析

1. 用户在内容契约中选择“清晰分析”。
2. 系统冻结对应版本和 hash。
3. Phase 1、2 不读取 Snapshot；Phase 3 与 Voice Audit 读取。
4. 审校报告能引用 Profile 的句式、节奏或 `avoid` 规则。

**通过条件：** accepted claims、核心判断和个人经历保持不变，表达特征符合 Profile。

### Scenario C：Deep 模式输入隔离

1. Lead 创建任务 Voice Snapshot。
2. Researcher 与 Editorial Strategist Manifest 不含该文件。
3. Writer 与 Auditor Manifest 含该文件及 hash。

**通过条件：** Handoff 可验证；篡改 Snapshot 后相关 Handoff 变为 stale。

### Scenario D：任务恢复时 Registry 已升级

1. 任务使用 Profile v1 创建 Snapshot 后中断。
2. 全局 Registry 更新为 v2。
3. 用户恢复原任务。

**通过条件：** 原任务继续使用 Snapshot 中的 v1；新任务才使用 v2。

### Scenario E：显式选择无效

1. 用户指定不存在的 `voice_id`。
2. 系统返回稳定错误与当前可用列表。

**通过条件：** 任务停在内容契约确认；不静默使用默认项，不产生初稿。

### Scenario F：声音规则与事实冲突

1. Profile 偏好强确定性表达，但证据只支持条件性结论。
2. Writer 保留证据边界。
3. Auditor 不要求为“更像该声音”而升级结论强度。

**通过条件：** Evidence Contract 胜出，Voice issue 只能在不损害事实的范围内修订。

### Scenario G：使用非默认 Voice 后请求学习

1. 用户完成一篇 `sharp-commentary` 任务。
2. 用户请求从本次编辑中学习长期风格。

**通过条件：** v0.3 不把 Profile 驱动的表达特征生成 Style Observation；提示该能力属于未来显式采纳流程。

### Scenario H：旧任务恢复

1. v0.3 上线前的任务没有 Voice Snapshot。
2. 用户恢复并继续现有流程。

**通过条件：** 状态显示 `legacy-natural`，正文与交付链路不被新 Profile 反向改变。

### Scenario I：Rewrite 平台适配

1. 已验收的 canonical final 使用某个 Voice Preset。
2. 用户发起小红书或抖音 Rewrite。

**通过条件：** Rewrite 以 canonical final 为源，只做平台合同要求的适配；不重新选择 Voice，不修改 canonical final。

### Scenario J：Khazix Article-only 闭环 Pilot

1. 独立模板会话只从 `@Khazix0918` 的 X Article 长文生成 Blind Profile。
2. Blind Profile 冻结后，再与作者公开的 `khazix-writer` Skill 做 post-hoc 对照。
3. 主线发现 `READY` 后，用该 Profile 改写固定旧稿副本。
4. Evidence、Editorial 与 Voice 三类检查全部完成。

**通过条件：** 原 `final.md` 未被修改；日常动态未进入 Corpus；改写没有新增事实或经历；最终留下可复查对比和明确晋级结论。

## Out of Scope

- 完整 Persona：身份、价值观、心智模型、立场、决策启发式和角色扮演。
- 以真实博主姓名对外提供“某某同款”或身份模仿。
- 抓取博主账号、批量导入语料、自动更新人物动态。
- 在生产运行时调用 Nuwa、`chat_with_me` 或其他外部 Skill。
- 用户自定义 Profile、Profile 编辑器、Profile 生成器、导入导出和市场。
- Web UI、头像卡片、推荐算法、使用分析和个性化排序。
- 同一任务多 Voice 并行生成、A/B 对比和中途热切换。
- 将非默认 Voice 自动吸收到 Personal Context Style Profile。
- 为 Writing Rewrite 增加独立 Voice Selector。
- 视觉设计人格、配图风格或语音合成声音。
- 对“AI 味”建立不可解释的单一分数或承诺彻底消除。
- 把 Khazix 实验 Profile 直接以真实账号名作为正式内置产品选项。

## Further Notes

### Why Nuwa, Not `chat_with_me`

前序调研结论保持不变：Nuwa 更适合作为**首批内置声音模板的离线提炼方法**；`chat_with_me` 更接近未来的账号采集与 Persona 生成产品，但不是 v0.3 所需的运行时能力。

项目借用的是提炼框架，不是外部 Skill。最终 Registry、Profile Contract、合成示例、测试和发布判断全部归属 AI Writing Master。

Nuwa 在本 Pilot 中不是完整执行：只取其一手来源优先、表达 DNA 量化、Voice Check 和 Fidelity 验证；完整 Persona 所需的认知、立场和角色层明确剔除。

目标作者已公开自己的 `khazix-writer` Skill。它对实验非常有价值，但角色是**盲测后的本人基准**，不是 Nuwa 提炼阶段的输入；否则无法判断 Nuwa 从文章本身提炼出了什么。

### Deliberate Simplifications

- 只做 4 个内置选项，先验证选择、快照、生成和审校闭环。
- 只加载一个 Profile，不建设组合、继承或权重系统。
- 内容契约确认后冻结，不在同一任务里解决多版本比较。
- 使用 JSON 保持零新增依赖；前序 YAML 仅作为字段草图，不作为运行时决定。

### Recommended Implementation Order

1. Voice Registry、Profile 校验、Snapshot 与最小 CLI。
2. 内容契约、任务摘要、Phase 3、Voice Audit 和 Deep Manifest 合同。
3. `自然默认` + 3 个内置 Profile。
4. 自动测试、Khazix 真实旧稿 Pilot、固定内容包 benchmark、文档与安装验证。
