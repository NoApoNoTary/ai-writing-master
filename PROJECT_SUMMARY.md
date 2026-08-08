# AI Writing Master：项目现状与迁移核对

**核对日期：2026-07-29**

**仓库：** `NoApoNoTary/ai-writing-master`

这份文件记录当前仓库实际拥有的能力，不承担 Roadmap 或完成度宣传功能。若文档与代码冲突，以仓库中的 Skill、CLI 源码和验证结果为准。

## 当前交付物

### Skills

| 路径 | 当前职责 |
|---|---|
| `skills/writing-master/` | 从零创作一个渠道成品；模式选择、证据与素材、写作、审校、Baoyu 路由和验收 |
| `skills/writing-rewrite/` | 对已有正文进行单渠道重构；带微信、X 单帖、X Thread YAML 合同及质量门槛参考 |

仓库里没有 `writing-topic`、`writing-research`、`writing-review`、`writing-visual`、`writing-publish` 等独立 Skill。相关能力属于 `writing-master` 内部模块，或由已安装的 Baoyu Skills 提供。

### 写作模式

| 模式 | Agent 结构 | 主要差异 |
|---|---|---|
| 快速草稿 | 当前 Agent | 简版内容契约、关键事实、一次合并审校 |
| 标准写作 | 当前 Agent | 完整事实/素材双轨、三层审校和验收 |
| 深度写作 | Lead + 专项子代理 | 已验收的 Handoff Runtime 处理已建立 deep/multi-agent 运行目录；本次仍需宿主实际具备子代理能力 |

新建完整内容必须由用户选择模式和一个 `target_id`，并在内容契约中明确是否使用内置模板或外部 Persona Skill。主写作流程的多 Agent 只属于深度写作，不作为默认路由；改写流程保持单 Agent，且每个 Rewrite 只处理一个渠道。

### CLI

| 命令 | 实际能力 |
|---|---|
| `writing-master quality` | 五项机械文本特征检查；保留 `quality_score` 兼容字段 |
| `writing-master similarity` | 字符 n-gram Jaccard 表面相似度 |
| `writing-master home` | 输出运行数据目录 |
| `writing-master handoff` | 已建立 deep/multi-agent 运行目录的 `prepare`、`start`、`recover-lost`、`complete`、`show` 交接操作 |
| `writing-master context` | 显式管理 Profile、五类素材、privacy approval、不可变 Snapshot 与 usage/run 验证 |
| `writing-master learn` | 提交、接受或拒绝可追溯 Style Observation，并显示 accepted-only Style Profile |
| `writing-master research` | 将 Agent 选题 draft 绑定到任务 Brief/Snapshot，并保存或验证 canonical Research Brief |
| `writing-master failure-cases` | 管理 `proposed/active/superseded` 失败案例，并生成任务内 `failure-case-snapshot.md` |
| `writing-master persona` | 列出内置人格模板（当前为 `khazix-writer` / 卡兹克科技观察（实验））、原样冻结内置/外部 Persona Skill 与自由格式任务 Brief，并从任务内 hash 校验恢复版本 |
| `writing-master wechat-timing` | 生成或校验公众号 `wechat-draft-report.json` 的发布时间建议 |

机械检查不负责事实核验、证据强度、原创性、论证质量或作者声音判断。

### Baoyu 集成

Baoyu 不随本仓库分发。当前集成层负责：

1. 模式选择后发现当前运行时已有的 Baoyu 能力；
2. 提取 URL、YouTube、Markdown 和本地素材；
3. 维护 `asset-manifest.yaml` 与 `storyboard.md`；
4. 标题与正文内容验收形成所选渠道 canonical final 后，生成渠道 YAML 要求的视觉或 HTML；
5. 渠道交付完成后，只有用户另行明确发布才调用发布 Skill。

## 来源项目的迁移情况

### 来自 auto-claude-writing-agent 的方法

已吸收并重新实现：

- 长文从 Brief、调研到审校的阶段化思路；
- Creative Drainage；
- 内容、风格和细节检查思路，现已重组为证据层、编辑层和声音层。

没有照搬：

- 固定模型名称和版本；
- 对用户展示隐藏推理过程；
- 用虚构的“AI 味百分比”表示审校效果；
- 把固定十步当作所有任务的唯一入口。

### 来自 wewrite 的方法

已吸收并重新实现：

- Skill 入口与模块化组织思路；
- 内容级改写入口；
- 渠道输出 YAML 的组织方式；
- 机械文本检查与相似度工具的工程思路。

当前仓库并未完整迁移原项目的全部模块、模板、其他平台定义、主题、发布实现或数据系统。README 只列出实际存在的文件，不再把参考项目的能力写成本仓库已交付能力。

### 本仓库新增的架构

- 用户显式选择快速、标准或深度模式；
- 多 Agent 仅在深度模式启用；
- `claims.yaml`、`sources.yaml`、`asset-manifest.yaml` 和 `storyboard.md` 的文件契约；
- Researcher、Editorial Strategist、Writer、Auditor 角色卡；
- Baoyu 的 Preflight → Planning → Production → Publish 分阶段路由；
- 机械脚本与独立编辑审查分离。
- `personal_context` 深模块：revisioned Author Profile、五类 Knowledge Item、visibility/approval、任务内 Snapshot、usage、确认式 Style Observation 与 accepted-only Style Profile。
- `research_brief` 深模块：3–10 个上下文感知候选、实时 Evidence、四维评分、任务输入绑定和 write-once 验证。
- Persona 模板与外部 Skill：内置 `khazix-writer` / 卡兹克科技观察（实验）模板，外部 `SKILL.md` 任务内保存、自由格式 `persona-brief.md`、按文章类型生成角色侧重，以及 Editorial/Writer/Auditor 共用 Brief、Researcher 中立的角色边界。
- `failure_cases` 深模块：`proposed/active/superseded` 案例库与任务内 `failure-case-snapshot.md`，只向 Writer/Auditor 注入选中 guardrail。
- `wechat_timing` 深模块：生成与校验公众号草稿发布时间建议，不调用发布或群发接口。
- `channel_adaptation` P0：`writing` / `rewrite` 双入口、单一 `target_id`、source-analysis 复用及微信/X 完整交付合同。

Personal Context Foundation、确认式风格学习和 Context-aware Research Brief 已交付；`quick/standard` 的通用确定性跨会话 Task Runtime 仍未交付。

## 2026-07-27 仓库审计修正

本轮修正处理了以下问题：

- 删除 README 和项目总结中的 Roadmap；
- 删除不存在的十个独立模块、目录、模板和示例声明；
- 移除失效的内部文档链接；
- 移除固定模型推荐、企业级、效果百分比和预计耗时等无证据宣传；
- 把 CLI `quality` 明确为机械文本预警，而非事实或整体质量评分；
- 修正 Baoyu 的路由时机：早预检、早摄入、晚生成、明确指令后发布；
- 修正安装文档，使其与仓库根目录的实际 Python 包结构一致；
- 把多 Agent 从默认路线收缩为用户显式选择的深度模式。
- 对齐事实：深度模式 Handoff Runtime 已验收；`quick/standard` 的通用任务恢复仍未实现。

## 当前目录边界

当前仓库有：

```text
skills/writing-master/
skills/writing-rewrite/
skills/writing-rewrite/platforms/wechat.yaml
skills/writing-rewrite/platforms/x-post.yaml
skills/writing-rewrite/platforms/x-thread.yaml
skills/writing-rewrite/references/single-target-rewrite.md
skills/writing-rewrite/references/quality-gates.md
src/writing_master/
src/writing_master/persona_templates/khazix-writer/SKILL.md
bin/writing-master
docs/quick-start.md
docs/cli-guide.md
docs/proposals/2026-07-29-channel-adaptation-p0-prd.md
install.sh
pyproject.toml
```

当前仓库没有：

```text
skills/writing-topic/
skills/writing-review/
skills/writing-visual/
skills/writing-publish/
examples/
templates/
cli/
Web UI 或数据面板
```

## 维护原则

1. README 只写已经存在并经过路径检查的能力。
2. 新功能在代码或 Skill 文件落地后再更新文档。
3. Roadmap、预计日期和固定模型推荐不进入仓库门面。
4. 外部 Skill 写成依赖与路由，不写成本仓库内置功能。
5. 机械指标、编辑判断和发布动作使用不同的验收语义。

## 来源与致谢

- [auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub) by MapleShaw
- [wewrite](https://github.com/imraywang/wewrite) by imraywang

两者提供了重要参考；当前仓库的文件结构、模式设计和 Agent 协议由本项目独立维护。
