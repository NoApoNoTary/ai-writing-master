# AI Writing Master 7·28 项目推进方案

- 方案版本：v1
- 制定日期：2026-07-28
- 输入 PRD：`/home/amose/prd 7-28.md`
- 仓库基线：`codex/writing-workflow-maintenance`，审计时 HEAD `61dec8c`
- 当前结论：先完成“个人上下文与确认式学习”工程闭环，再进入热点系统和发布后增长闭环
- 配套文件：[Program 执行清单](2026-07-28-v0.2-execution-checklist.md) · [首个 Codex Goal 合同](../goals/2026-07-28-v0.2-goal-contract.md) · [Goal A 验收记录](../goals/2026-07-28-v0.2-acceptance.md)

## 1. 执行摘要

7 月 28 日 PRD 正确描述了长期方向，但当前仍属于愿景与能力地图，不宜把十个模块当成十条并行开发线。仓库已经拥有写作、审校、证据追踪、canonical final、Rewrite、Baoyu 路由和深度模式 Handoff Runtime；继续增加写作 Agent 或平台，边际价值低于补齐作者记忆。

下一阶段建议只推进一个产品里程碑：

> **Personal Content Model v0.2：作者画像、个人素材、任务快照、确认式风格学习和上下文感知选题。**

它必须形成一条可验证的因果链：

```text
用户确认的作者信息与素材
  → Runtime 生成不可变任务快照
  → 现有写作链只读取该快照
  → 用户修改稿形成风格观察候选
  → 用户接受或拒绝候选
  → 下一任务读取新的已确认风格
  → Research Agent 结合作者上下文提出选题
```

这是一项“工程闭环”目标：证明数据、状态、来源、快照和执行链真实可用。它不等于已经证明文章效果提升。产品效果需要后续真实任务实验验证。

## 2. 当前事实基线

### 2.1 已经存在，不重复建设

| 能力 | 当前事实 | 本阶段处理 |
|---|---|---|
| Quick / Standard / Deep | 主 Skill 已定义三种模式 | 保持现有模式语义 |
| 选题、调研、写作、三层审校 | 已是 `writing-master` 内部模块 | 接入个人上下文，不拆成新 Skill |
| 来源、主张和素材合同 | 已有 `sources.yaml`、`claims.yaml`、`asset-manifest.yaml` | 复用并增加个人素材身份 |
| Canonical final | 已有内容验收和只读语义 | 作为学习前的 baseline |
| 深度模式 Handoff Runtime | Manifest、Result、hash、attempt、stale、恢复均已实现 | 只增加个人快照这一种允许输入 |
| Rewrite | 已有单目标改写合同；当前 P0 支持微信、X 单帖、X Thread | 每个 run 只处理一个 `target_id` |
| 视觉、排版、发布 | 通过 Baoyu 外部能力路由 | 不自建发布系统 |
| CLI 机械工具 | `quality`、`similarity`、`handoff`、`home` | 保持兼容 |

审计时全量测试为 **51/51 通过**。Handoff Runtime PRD 记录了一次完整真实 Codex Host 链路。

### 2.2 尚未形成产品能力

| PRD 能力 | 当前缺口 |
|---|---|
| Author Profile | 缺少版本化 schema、更新入口和稳定加载机制 |
| Personal Knowledge Base | 只有目录；缺少受管导入、来源、hash 去重、标签和检索 |
| Style Learning | 没有修改前后关系、观察候选、接受/拒绝和聚合机制 |
| Research Agent 选题发现 | 现有 Researcher 服务既定 Brief；缺少 3–10 个主题、Heat、Audience、Angle 和 Evidence 合同 |
| 全模式任务状态 | 深度 Handoff 有 Runtime；quick/standard 仍主要依赖 Skill 文件合同 |
| 发布后反馈 | 没有阅读、点赞、收藏、评论的数据模型和分析闭环 |

### 2.3 开工前要消除的事实漂移

当前产品 PRD、README/Quick Start 与 Handoff Runtime PRD 对“真实 Handoff、跨会话恢复是否已验收”的表述存在漂移；`agent-orchestration.md` 与主 Skill 对视觉生产顺序也存在差异。

这不是新里程碑的主体，但属于 WP0 门槛：

1. 建立唯一能力事实表。
2. 区分“深度 Handoff 恢复已验证”与“所有模式的通用任务恢复尚未实现”。
3. 统一先验收 canonical final、再生成视觉的顺序。
4. 保留已有未跟踪文件 `docs/proposals/2026-07-24-opus5-retrospective-plan.html`，不纳入本次变更。

## 3. 产品决策

### 3.1 目标用户

首批目标用户收敛为：

> 使用本地 AI Agent、已经有历史文章或真实经历素材、持续写技术/AI 长文，愿意审阅结果但不愿维护复杂后台的个人创作者。

企业品牌团队、多人审批、内容日历和云协作不属于当前里程碑。

### 3.2 最小价值单位

本项目的价值单位不是 Agent 数量或生成次数，而是：

> 一次写作任务能明确记录自己使用了哪版作者画像、哪条个人素材和哪版风格规则，并能在用户确认后把真实修改转成下一任务可复用的上下文。

### 3.3 成功的两个层次

**工程完成**由当前 Codex Goal 闭环负责：

- 数据合同、CLI、快照、写作接入、学习状态和 Research Brief 均真实落地；
- 自动测试与隔离目录端到端 smoke 通过；
- 使用合成 fixture 证明任务 N 的已确认观察能进入任务 N+1 快照。

**产品有效**由后续真实使用实验负责：

- 至少 5 个真实写作任务；
- 对比早期与后期任务的人工修改负担；
- 观察上下文相关率、偏好候选接受率和错误个人事实；
- 数据不支持时收缩为“可追溯素材检索 + 稳定写作流程”。

工程 Goal 不用合成数据宣称产品效果提升。

### 3.4 交付必须拆成三个顺序 Goal

单个 Goal 同时承担 Store、Knowledge、快照、风格学习、Research、CI 和真实 Agent 验收，范围过大且容易让接口在长周期中漂移。因此 v0.2 作为一个 Program，按依赖顺序分成：

| Goal | 范围 | 前置条件 | 独立关闭证据 |
|---|---|---|---|
| **Goal A：Personal Context Foundation** | 事实对齐、Author Profile、Knowledge Base、隐私准入、不可变任务快照、Standard/Deep 接入 | 当前仓库基线 | 隔离 CLI smoke + 真实 Standard 合成任务 + Deep Manifest/stale 测试 |
| **Goal B：Confirmed Learning Loop** | Style Observation、accept/reject、Style Profile、任务 N→N+1 | Goal A complete | accepted/proposed/rejected 的 revision/hash 证据链 |
| **Goal C：Context-aware Research Brief** | 3–10 个主题、Heat/Audience/Angle/Evidence、四维评分与现有选题接入 | Goal A complete；Goal B 可选 | 合规 Brief validator + 真实 Research Agent 合成验收 |

每个 Goal 分别执行文档、全量测试、构建、行为 smoke 和独立审查；不把所有收尾工作集中到 Program 末尾。当前可直接启动的合同只覆盖 Goal A。

## 4. v0.2 范围

### 4.1 v0.2 Program 纳入范围

1. 版本化作者画像。
2. 五类个人素材：`experiences`、`opinions`、`cases`、`references`、`previous_articles`。
3. 受管导入、来源、内容 hash 去重、标签和确定性文本检索。
4. 每次任务的只读 `personal-context-snapshot.json` 与被选素材副本。
5. Standard 写作主链消费任务快照；Deep 角色通过 Manifest 获取同一快照。
6. 修改前后证据驱动的风格观察候选。
7. `proposed → accepted | rejected` 决策和只聚合 accepted 观察的风格档案。
8. Research Agent 的主题候选合同与现有 Phase 2 接入。
9. Runtime 级 schema、revision、ID、hash、锁、原子写入和失败语义。
10. CLI、自动测试、文档、隔离 smoke 与一次真实 Agent 合成验收。

### 4.2 明确非目标

- Web UI、数据库、向量数据库、通用 RAG 平台。
- 云同步、多用户、团队权限和审批。
- 后台进程、定时任务和自动热点爬取。
- 新的独立写作 Skill 或更多 Agent 角色。
- 把 Quick / Standard 改成多 Agent。
- 扩展新的发布平台。
- 内置微信公众号或 X 发布实现。
- 基于阅读、点赞、收藏、评论的自动优化。
- 模型微调和个人专属模型训练。
- 未经用户确认的永久风格更新。
- 向旧 `personal_materials/` 静默迁移数据。
- quick/standard 的通用 Task Runtime、任务发现、确定性恢复和版本回退；它们作为独立基础设施里程碑处理。

## 5. 架构方案

### 5.1 核心原则

继续贯彻 PRD 的分工：

| Agent / Prompt | Runtime |
|---|---|
| 归纳作者信息 | 校验 schema 和 revision |
| 判断素材类别、摘要与标签 | 复制文件、生成 ID、计算 hash、去重 |
| 判断哪些素材与任务相关 | 确定性检索、过滤、生成不可变快照 |
| 从 diff 提炼风格候选 | 校验候选、记录决策、重建已确认风格档案 |
| 调研热点、角度和证据 | 校验 Research Brief、时间和来源字段 |
| 写作和编辑 | 保存任务产物与使用记录 |

### 5.2 深模块

新增一个深模块，而不是四个平行浅模块：

```text
writing_master.personal_context
```

它对调用方暴露少量稳定操作，隐藏目录组织、锁、原子写入、revision、hash 和迁移细节。建议实现接口：

```text
initialize()
get_profile() / update_profile(expected_revision)
add_material() / list_materials() / search_materials()
create_snapshot(run_dir, selected_material_ids)
record_observation() / decide_observation() / get_style_profile()
```

Research Brief 作为相邻的确定性合同模块，只负责验证和持久化，不负责替 Agent 做热点判断。

### 5.3 CLI 接口

Goal A 保持一个聚合入口，并把隐私和生命周期操作做成可执行合同：

```text
writing-master context init
writing-master context profile set PROFILE.json [--expected-revision N]
writing-master context profile show [--json]
writing-master context material add FILE --kind KIND --title TITLE --source-kind KIND --source-ref REF --visibility VISIBILITY [--tag TAG ...]
writing-master context material list [--kind KIND] [--status STATUS] [--json]
writing-master context material disable ITEM_ID
writing-master context material enable ITEM_ID
writing-master context material set-visibility ITEM_ID VISIBILITY [--expected-revision N]
writing-master context search QUERY [--kind KIND] [--tag TAG] [--limit N] [--json]
writing-master context import-legacy SOURCE_DIR [--kind KIND]
writing-master context approve RUN_DIR ITEM_ID --allow background|paraphrase|quote
writing-master context snapshot RUN_DIR --material ITEM_ID:PURPOSE [--material ITEM_ID:PURPOSE ...]
writing-master context verify-run RUN_DIR
```

Goal B 在 Goal A 接口稳定后增加：

```text
writing-master learn propose CANDIDATE.json
writing-master learn decide OBSERVATION_ID --accept | --reject
writing-master learn show [--json]
```

Goal C 的 validator 必须有可自动测试的入口；具体是否增加 `research` 顶层命令，在 Goal A 的实际模块接口完成后由 Sol 决定，当前不预设一个只有单操作的浅命令。

### 5.4 数据目录

运行时 canonical 格式采用 JSON，正文材料保留 Markdown/纯文本。这样可以保持 Python 标准库实现，不引入 YAML 运行依赖。PRD 中的 YAML 仅作为可读示例；如未来需要，可生成单向只读投影。

```text
${WRITING_MASTER_HOME}/
├── personal-context/
│   ├── author-profile.json
│   ├── style-profile.json
│   ├── knowledge-index.json
│   ├── knowledge/
│   │   ├── experiences/ITEM_ID/{metadata.json,content.md}
│   │   ├── opinions/ITEM_ID/{metadata.json,content.md}
│   │   ├── cases/ITEM_ID/{metadata.json,content.md}
│   │   ├── references/ITEM_ID/{metadata.json,content.md}
│   │   └── previous_articles/ITEM_ID/{metadata.json,content.md}
│   └── style-observations/OBSERVATION_ID.json
└── runs/TASK_ID/
    ├── personal-context-snapshot.json
    ├── context-materials/ITEM_ID.md
    ├── context-usage.json
    └── research-brief.json
```

现有 `personal_materials/` 只作为显式、幂等导入来源；安装或初始化不得自动扫描和迁移。

## 6. 核心数据合同

### 6.1 Author Profile

最低字段：

```json
{
  "schema_version": 1,
  "profile_id": "author-default",
  "revision": 1,
  "updated_at": "RFC3339",
  "identity": {"display_name": "ROLE_A"},
  "expertise": ["AI Agent"],
  "content_directions": ["软件开发"],
  "values": ["证据优先"],
  "expression": {"tone": ["analytical", "concise"]},
  "avoid": ["空泛总结"],
  "provenance": {"kind": "user_confirmed"}
}
```

规则：所有更新使用乐观 revision；旧 revision 更新失败并返回可执行错误；画像只保存用户明确提供或确认的信息。

### 6.2 Knowledge Item

每条素材至少记录：

- 稳定 `item_id`、`schema_version`、`kind`、`status`。
- `title`、`summary`、`tags`。
- `source_kind`、`source_ref`、`source_hash`。
- 受管 `content.md` 的 SHA-256。
- `visibility: private | publishable | ask_before_use`。
- `created_at`、`updated_at`。

规则：去重键为 `(kind, normalized_content_hash, source_kind)`。同一身份内的重复导入幂等；同一文本以不同 kind 或 source identity 导入时保留独立 item。`disabled` 项不得进入新快照。

隐私准入：

- `publishable` 可直接被任务选择。
- `ask_before_use` 默认不能进入快照，只有任务目录中存在针对该 item 的显式 approval，并记录 `background | paraphrase | quote` 范围后才可进入。
- `private` 永远不进入写作快照；用户需要先显式修改可见性，或创建脱敏后的派生 item。
- `context-usage.json` 和最终验收必须验证实际用途没有越过 approval 范围。

### 6.3 Personal Context Snapshot

快照至少固定：

- `task_id` 和创建时间。
- 作者画像 revision 与 hash。
- 风格档案 revision 与 hash。
- 被选 Knowledge Item 的 ID、metadata hash、content hash 和使用目的。
- 任务目录中材料副本的相对路径。

空状态使用 canonical 对象：未配置 Profile/Style 时分别记录 `status: empty`、`revision: 0` 和空内容 hash，不用缺失文件或 `null` 表达。任务开始后只读取快照，不直接读取会变化的全局档案；全局更新只影响后续任务。

### 6.4 Style Observation 与 Style Profile

观察记录至少包含：

- baseline 与 edited 文件 hash。
- 具体前后证据片段或 diff 引用。
- 规则维度：表达、句式、结构、观点倾向或平台偏好。
- 适用范围：全局、平台、内容类型或主题。
- 状态：`proposed | accepted | rejected`。
- 用户决定时间和来源 task。

规则：`proposed` 和 `rejected` 均不得改变风格档案；Style Profile 只能由 accepted observations 重建；每条规则必须能追溯 observation ID。

### 6.5 Research Brief

输出 3–10 个候选，每个候选至少包含：

```text
Topic
Heat: score + basis + as_of
Audience
Angle
Evidence[]
Scores: heat, user_value, differentiation, author_fit
Rationale
```

规则：四项评分范围统一为 `0..10` 并有理由；`as_of` 使用 RFC3339 且不得在未来；Evidence 使用稳定 `evidence_id`，并记录可解析来源、日期与内容 hash。Heat 不得用无时间和证据的主观数字冒充实时热度；`author_fit` 必须引用快照中的 `profile revision + hash` 或 Knowledge Item ID。Runtime 只证明结构和引用完整，不证明语义热度真实。

## 7. 推进阶段与退出条件

项目不按功能数量或日历宣告完成，按以下退出条件推进。

### Goal A / WP0：事实基线与合同对齐

- 统一 Handoff 和恢复能力的文档事实。
- 修正 canonical final 与视觉生产顺序。
- 记录测试、构建、CLI 和工作区基线。

退出条件：仓库只有一份不矛盾的能力事实说明；全量测试仍通过。

### Goal A / WP1：Personal Context Store

- 实现初始化、路径边界、锁、原子 JSON、schema 和 revision。
- 实现 Author Profile。

退出条件：并发/陈旧 revision、损坏 JSON、目录越界和初始化幂等均有测试。

### Goal A / WP2：Knowledge Base

- 实现五类素材、受管复制、hash 去重、标签和文本检索。
- 实现旧目录显式导入，不做静默迁移。

退出条件：重复导入稳定；过滤和排序确定；来源和个人经历身份不丢失。

### Goal A / WP3：任务快照与写作接入

- 生成不可变上下文快照和材料副本。
- Standard 主链只消费快照。
- Deep Host 调用只根据角色卡、Manifest 和 `allowed_inputs` 构造上下文；Manifest 不列出全局个人目录。本阶段不宣称 OS 级文件访问隔离。
- 记录正文实际使用的素材 ID。

退出条件：修改全局画像或素材后，已创建任务不变化；新任务读取新 revision；一个使用合成素材的真实 Standard Agent run 产出 snapshot、context usage、final 和 acceptance evidence。

### Goal B / WP4：确认式风格学习

- 验证并保存风格观察候选。
- 支持接受、拒绝和可追溯聚合。
- 将已确认风格写入后续任务快照。

退出条件：合成任务 N 的 accepted 观察进入任务 N+1；proposed/rejected 不进入。

### Goal C / WP5：Research Agent 与选题接入

- 定义并验证 Research Brief。
- 让现有选题阶段结合个人快照生成候选。
- 保持 Research 判断与 Runtime 验证分离。

退出条件：3–10 个候选均满足五个核心字段、四维评分、时间和证据要求。

### 每个 Goal 的闭环

Goal A、B、C 各自在自己的范围结束时更新用户文档，在隔离 `WRITING_MASTER_HOME` 中运行行为 smoke，执行全量测试、compileall、构建、链接检查、CodeGraph 同步和独立审查。证据日志与 checkbox 更新属于 evidence-only 变更，不触发代码重测；一旦证据更新同时改变了合同语义，则必须重新运行受影响验证。

## 8. 指标与验证计划

### 8.1 工程指标

- 100% 快照记录 profile/style revision 与内容 hash。
- 100% 进入正文的个人经历可追溯到 Knowledge Item。
- 0 次 proposed/rejected 风格规则进入新快照。
- 0 次 disabled 素材进入新快照。
- schema、hash 或 revision 校验失败后，任务不静默推进。

### 8.2 产品实验指标

真实使用阶段再采集：

- 每千字 accepted final 的人工修改字符数。
- 有效修改轮次。
- 检索上下文相关率。
- 风格候选接受率。
- 错误或虚构第一人称经历次数。

初始判断门槛只用于实验，不写成既成效果：上下文相关率目标 70%，偏好候选接受率目标 50%，前后任务中位修改负担目标下降 20%。取得真实基线后再校准。

## 9. 风险、反对意见与反转条件

### 最强反对意见

用户可能只想快速获得好文章，并不愿维护画像或确认风格候选；模型升级带来的提升也可能高于个人记忆系统。

### 主要风险

| 风险 | 控制 |
|---|---|
| 单次修改污染永久风格 | 强制 proposed/accepted/rejected |
| 个人事实被错误推断 | 只保存用户明确提供或确认的信息 |
| 全局修改污染运行中任务 | 不可变任务快照 |
| 过早引入向量库 | 首版确定性文本检索，数据证明不足再升级 |
| 四套子系统形成浅接口 | 收敛到一个 `personal_context` 深模块 |
| Skill 文案先于代码宣称能力 | 代码、测试、真实 smoke 后再更新“已交付”状态 |
| 旧数据格式漂移 | 显式导入、schema version，不静默迁移 |

### 反转条件

在至少 10 个真实任务后，若上下文相关率持续低于 50%，或人工修改负担没有方向性改善，停止扩建自动学习，将产品收缩为：

> 可追溯的个人素材检索 + 稳定写作工作流。

## 10. 后续路线

只有 v0.2 工程闭环和真实使用实验均通过后，再按证据触发：

1. 用户持续卡在选题，推进 v0.3 Topic Intelligence。
2. 已有稳定发布样本，推进描述性内容反馈分析。
3. 素材规模导致确定性检索退化，再评估向量检索。
4. 某平台需求重复出现，再补对应平台合同。
5. 发布数据形成可靠来源后，再研究自动优化，不直接让弱信号改写作者画像。

## 11. 当前决策状态

| 决策 | 状态 |
|---|---|
| 下一里程碑聚焦个人内容模型 | 已决定 |
| 单用户、本地文件、零运行依赖 | 已决定 |
| JSON 为 Runtime canonical contract | 已决定 |
| 不新增独立写作 Skill | 已决定 |
| 风格更新需要用户确认 | 已决定 |
| 旧目录只显式导入 | 已决定 |
| v0.3/v0.4 不进入当前 Goal | 已决定 |
| Web UI、向量库和云同步 | 延后 |
| 产品效果是否成立 | 等真实使用实验 |

下一步由 [Program 执行清单](2026-07-28-v0.2-execution-checklist.md) 和 [Goal A 合同](../goals/2026-07-28-v0.2-goal-contract.md)驱动，不再从原 PRD 的十个模块平铺开工。Goal A 关闭后，由 Sol 基于真实接口和验收证据激活 Goal B；Goal C 同理。
