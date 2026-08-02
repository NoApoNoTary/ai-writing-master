# 三层审校：Evidence / Editorial / Voice

三层审校把事实可靠性、编辑判断和表达声音分开处理。目标是形成可定位、可举证、可执行的问题清单，再由 Writer 统一修订；不使用主观百分比表示文章质量。

## 输入

- `brief.md`
- `channel-contract.yaml`
- `claims.yaml`
- `sources.yaml`
- `editorial-brief.md`
- `outline.md`
- `draft-v1.md`
- 用户风格档案与少量代表性正反例
- 当前任务的 `voice-profile-snapshot.json`（仅 Voice Audit；不得用全局 Registry 替代）
- 选择外部 Persona 时，当前任务的 `persona-brief.md`（Editorial、Writer、Auditor 共用同一份）
- `editorial-brief.md` 中的 `recommended_combo`

如文章包含视觉规划，同时读取 `asset-manifest.yaml` 与 `storyboard.md`。

## 通用规则

1. 每个问题必须指出位置、证据和修订边界。
2. 事实、推断、意见和用户经历使用不同身份，不相互伪装。
3. 当前作者的第一人称事件、人物、对话、时间、地点、测试结果和感官细节必须来自本次任务登记的用户素材；`author` Persona 模式可使用 `persona-brief.md` 明确标注的构造性第一人称背景，但不得冒充当前作者的现实经历。
4. 审校不通过随机增加情绪词、短句、口头禅或固定平台话术制造“人感”。
5. `writing-master quality` 只提供套话、句长、段落、副词和词汇等机械预警，不验证事实、论证、原创性或作者声音。
6. 对用户报告结论、问题和已完成修改，不展示隐藏推理过程。
7. `author` Persona 模式允许 Brief 明确采用的构造性第一人称背景；`reference` 模式保持当前作者身份。两种模式下的外部主题事实仍要求 accepted claim。
8. Auditor 按 `application_depth` 检查：`scenario` 要有具体场景、明确输入和可观察结果，合成示例必须标注；`actionable` 要有前置条件、步骤、示例输入、预期输出、失败信号、适用边界；`reproducible` 还要有实际验证环境/版本、验证方法、回滚和已知限制。没有真实测试证据时标为 `partial` 或 `blocked`，不声称 reproducible。

## 用户动作与阻断问题

审校完成后先展示可执行摘要，例如“审校发现 2 个阻断问题、3 个主要问题；等待你决定 1 个方向性问题”。只把确实需要用户判断的问题暂停给用户，其余已接受的修订由 Writer 集中完成。

| 用户动作 | 适用问题 | 结果 |
|---|---|---|
| 接受建议 | 任意问题 | Writer 按 `required_change` 修订；问题要经复核才关闭。 |
| 忽略非阻断项 | `major`、`minor` | 保留忽略原因和位置，不再要求该项修订。 |
| 修改原始要求 | 任意问题 | 更新受影响的 Brief、主张或结构，并重审受影响部分。 |
| 补充来源、降低表述或删除断言 | `blocking` 事实问题 | 作为关闭阻断问题的候选修订，再进行证据复核。 |
| 要求重写受影响部分 / 查看前后差异 | 任意问题 | 只影响指定部分，不改写已确认的无关内容。 |

`blocking` 的语义是交付闸门：它只能处于待修订、`needs_input` 或经复核关闭的状态，不能通过“忽略”关闭。存在未关闭的 `blocking` 时，任务停在“等待问题处理”或修订中；来自 Writing Master 的 `final.md` 不是“已验收 canonical final”，也不能作为 Rewrite、视觉、排版或发布来源。`needs_input` 表示等待用户，不表示问题已关闭或任务已完成。

对需要用户决定的项，在 `revision-report.yaml` 中额外记录 `user_decision: accepted | ignored_non_blocking | modified_requirement | supplied_input`；`ignored_non_blocking` 只可用于 `major` 或 `minor`。

## 问题格式

```yaml
issues:
  - issue_id: EVID-001
    severity: blocking | major | minor
    layer: evidence | editorial | voice
    location: "章节、段落、原句或 claim_id"
    problem: "可观察的问题"
    evidence: "来源、原句、任务合同或风格对照"
    required_change: "必须怎样修，哪些内容保持不动"
verdict: pass | revise | needs_input
application_check:
  depth: none | scenario | actionable | reproducible
  required_blocks: []
  status: pass | partial | blocked
```

`application_check.status` 只有 `pass` 可进入内容验收通过。`partial` 需要修订或显式降低深度后重审；`blocked` 作为阻断问题处理。

严重程度：

- `blocking`：虚构经历、关键事实无来源、来源与结论相反、核心任务答非所问等阻止交付的问题。
- `major`：明显削弱结论、结构、读者价值或作者声音的问题。
- `minor`：局部措辞、节奏、标点和排版问题。

## 第一层：Evidence Audit

### 目标

确认正文中的具体事实和个人材料都可追溯，表述强度与证据强度一致。

### 检查项

#### 1. Claim 对齐

- 每个数字、日期、版本、引述、研究结论、案例结果和时效性事实都关联 accepted claim。
- `pending`、`excluded` 或 `unsupported` 内容未写成确定事实。
- `claim-usage.yaml` 与正文实际使用一致。

#### 2. 来源质量

- 原始报告、官方文档和第一方资料优先于转述。
- 搜索摘要只作为发现线索，正文引用回到原页面。
- 来源日期、访问日期、发布方和适用范围记录完整。
- 单一来源的营销说法没有被写成普遍结论。

#### 3. 表述边界

- 样本、地区、版本、时间窗口和使用场景保留在正文。
- 相关关系没有升级为因果关系。
- 推断使用“这意味着”“更可能”等明确身份，并列出支持来源。
- 意见使用编辑判断身份，不伪装成行业共识。

#### 4. 个人材料

- 每个第一人称事实都能指向 `user_provided` material。
- 原素材没有提供的数字、动作、对话和情绪未被补写。
- 单次个人经验没有扩张为普遍规律。

### 处理原则

- 有可靠来源：补齐 claim 和引用。
- 证据只支持较弱结论：缩小正文表述。
- 仍待核实：删除具体断言或保留为明确问题。
- 用户明确要求个人故事但素材不足：标记 `needs_input`，不生成替代故事。

## 第二层：Editorial Audit

### 目标

确认文章围绕一个清晰判断展开，每一节都帮助目标读者理解、选择或行动。

### 检查项

#### 1. 任务对齐

- 正文回答 `brief.md` 中的核心问题。
- 核心判断与 `editorial-brief.md` 一致。
- 文章承诺没有超出证据和篇幅可交付范围。

#### 2. 论证链

- 开头尽快建立问题、判断或有效场景。
- 每个主要章节承担明确作用：定义、证明、解释、比较、反驳或行动。
- 结论来自前文证据，没有突然增加新主张。
- 反方、限制条件和失败场景会真实影响结论，而非礼貌性附加。

#### 3. 读者决策

- 读者能明确知道“这对我意味着什么”。
- 教程包含前置条件、关键步骤、失败信号和验证方式。
- 对比或评测给出适用人群与选择条件，不只罗列功能。
- 分析或观点文明确区分事实描述和编辑判断。

#### 4. 信息密度

- 删除重复解释、空泛过渡和只为凑结构存在的段落。
- 同一证据没有被多个章节重复包装。
- 小标题描述真实内容，不使用空洞概念词代替判断。
- 可替换主题名仍成立的句子优先删除或具体化。

### 通过标准

- 核心问题得到直接回答。
- 主要章节均服务同一编辑判断。
- 至少处理一个真实反方或边界。
- 删除任一主要段落都会损失必要信息，而非只损失篇幅。

## 第三层：Voice Audit

### 目标

让表达与用户的可观察写作习惯和目标平台一致，同时保持准确、自然和完整。

Voice Preset 已选择时，Auditor 使用 Writer 的同一份任务 `voice-profile-snapshot.json`；它只影响表达检查，不得覆盖事实、证据边界、核心判断、作者立场或真实经历。Snapshot 结构、任务 ID 或 hash 失败时，停止 Voice Audit 和后续验收/发布，不读取当前 Registry 代替。

### 检查项

#### 1. 风格证据

- 语气、句长、段落、开头、转折和结尾偏好来自风格档案或用户示例。
- 单篇范文只提供局部参考，不自动升级为全局硬规则。
- 第三方范文只校准结构和节奏，不提供观点、句子或个人经历。
- Voice issue 必须引用具体 `voice.<field>` 规则或 `avoid` 条目，并定位到章节、段落和原句；“像 AI”“不像某人”或主观百分比不是 issue 证据。

#### 2. 模板化表达

- 删除没有信息作用的宏大背景、总结套话和机械过渡。
- 检查过度整齐的排比、连续同构句和固定三段式。
- 避免把所有正式表达都改成短句；术语、逻辑关系和必要限定应保留。
- 避免套用与正文无关的固定平台口号；互动方式应来自用户风格和当前内容目的。

#### 3. 伪口语与伪细节

- 口语化不等于加入“我愣住了”“真的不骗你”等固定情绪句。
- 没有用户素材时，不添加亲历式开头或朋友、同事、客户故事。
- 具体性来自可核实对象、条件、步骤和证据，不来自补造时间地点。

#### 4. 节奏与可读性

- 长短句服务信息关系，不追求固定字数区间。
- 段落长度适合目标平台，但复杂论证可以保留必要展开。
- 代词指向、连接关系、标点和 Markdown 层级清楚。
- 大声朗读或逐段阅读时，没有明显拗口、断裂或意义重复。

#### Voice issue 的精确格式

```yaml
- issue_id: VOICE-001
  severity: major
  layer: voice
  location: "第 3 节，第 2 段，第 1 句"
  problem: "转折未体现当前 Profile 的克制条件化规则。"
  evidence:
    profile_rule: "voice.transitions[1]: 用条件与证据说明转折"
    excerpt: "所以，这个结论显然成立。"
  required_change: "保留 claim-004 的范围，改为与现有证据一致的条件性转折；不新增事实或经历。"
```

每条 Voice issue 的 `location`、`profile_rule`、`excerpt` 和 `required_change` 都必填。`required_change` 只能在表达层修订；Evidence 或 Editorial 合同冲突时，Voice 问题不要求加强结论、删除必要边界或改变作者判断。

### 机械预警

需要时运行：

```bash
writing-master quality draft-v1.md --json
```

逐项查看命中位置，再判断是否修改。机械分数较低不自动判定文章失败，分数较高也不代表文章已经通过编辑审查。

## 修订流程

### 标准模式

当前 Agent 按 Evidence → Editorial → Voice 顺序检查，先生成完整问题清单，再统一修改，避免后一层破坏前一层已经确认的事实和结构。

### 深度模式

1. Auditor 在独立上下文中生成 `review-report.yaml`，首轮不读取 Writer 的解释。
2. Lead 去重、解决冲突并生成 `accepted-issues.yaml`。
3. Writer 只依据接受的问题统一生成 `draft-v2.md` 与 `final.md`。
4. Auditor 只复核 blocking 与 major 问题是否关闭。

## 修订报告

```yaml
revision_report:
  - issue_id: EVID-001
    action: fixed | rejected | needs_input
    changed_location: "章节或段落"
    note: "修改结果或保留理由"
remaining_issues: []
final_verdict: pass | needs_input
```

## 完成条件

- 所有 blocking 问题已经经复核关闭；任何 `needs_input` 都保持任务等待，不进入完成状态。
- major 问题均有处理记录。
- 关键事实可追溯到 accepted claim 和来源。
- 个人经历均来自用户素材，没有扩写式细节。
- 核心判断、反方、边界和读者决策清晰。
- 表达符合风格与 Voice Snapshot 证据，没有固定口语模板和伪细节；每个 Voice issue 可定位、可复核。
- `review-report.yaml`、`accepted-issues.yaml`（深度模式）和 `revision-report.yaml` 已保存。
