# AI Writing Master

面向 AI Agent 的文件化写作工作流：先由用户选择执行模式，再在同一份内容契约中确定任务级写作声音，完成事实与素材调研、写作、审校和交付。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab.svg)](pyproject.toml)

## 项目定位

这个仓库目前提供两个可安装的 Skill：

| Skill | 用途 |
|---|---|
| `writing-master` | 从零创作一个渠道成品；包含三种模式、证据与素材双轨、审校和 Baoyu 路由 |
| `writing-rewrite` | 对已有正文进行单渠道重构；P0 内置微信、X 单帖和 X Thread 合同 |

它不是十几个独立 Skill 的集合。选题、调研、结构、标题、审校和素材规划目前都是 `writing-master` 内部模块，不应路由到并不存在的 `writing-topic`、`writing-review` 等名称。

## 三种写作模式

新建完整文章时，如果用户尚未明确模式，`writing-master` 必须先询问：

固定问题和选项以 [`mode-selection.md`](skills/writing-master/references/mode-selection.md) 为唯一来源。

| 模式 | 执行方式 | 适合场景 |
|---|---|---|
| 快速草稿 | 当前 Agent | 先获得一个有依据、可继续讨论的版本 |
| 标准写作 | 当前 Agent | 常规长文和可发布文章；默认推荐 |
| 深度写作 | 宿主具备真实子代理能力时由 Lead + 专项角色执行 | 重要长文，需要隔离研究、写作和审计上下文 |

**多 Agent 不是默认入口。** 对新建完整文章，只有用户选择深度写作时才进入角色协议；实际创建子代理还取决于宿主能力。用户已经在当前请求中说出“快速”“标准”“深度”或“多 Agent 写作”等明确模式时，直接采用，不重复询问，也不根据题目难度隐式代选。

已有正文改写和只做标题、审校、选题等单一模块请求不触发这道完整文章模式闸门。`writing-rewrite` 在 P0 始终由当前 Agent 单独执行；每次只生成一个 `target_id`。需要第二个渠道时创建新的 Rewrite，并复用相同 source hash、canonical package 支持产物与 `source-analysis.md`。深度或多 Agent 改写不属于当前 P0。

## 工作流

标准写作的主链路如下：

```text
模式选择
  → 单一 target_id + 内容契约（含写作声音）+ 能力/素材预检
  → 事实轨 + 素材轨调研
  → 角度、读者决策、大纲和 storyboard
  → 初稿
  → 证据层、编辑层、声音层审校
  → 渠道审校与内容验收（形成该渠道 canonical final）
  → 当前渠道必要产物
  → 交付包验收
  → 后续明确发布指令才进入独立发布动作
```

深度写作的角色协议沿用同一条链路；宿主具备真实子代理能力时，才把高干扰环节拆给 fresh-context 角色：

- `Researcher`：来源、主张和真实素材；
- `Editorial Strategist`：角度、读者决策、结构和 storyboard；
- `Writer`：只读取已经接受的内容包；
- `Auditor`：独立检查证据、编辑质量和声音偏差；
- `Lead`：维护状态、用户确认、问题合并、Baoyu 闸门和最终验收。

代理之间通过运行目录中的文件产物通信，不把父对话全文复制给所有角色。深度模式 Handoff Runtime 已通过运行时和真实宿主验收：它对已建立的 `mode=deep`、`execution=multi_agent` 运行目录校验 Manifest、Result、hash、stale 与 attempt 历史，并可从该目录复核当前 handoff。它不是通用任务管理器；`quick/standard` 仍没有通用的确定性跨会话任务恢复服务。

## P0：任务摘要、确认与交付

标准写作的用户主链是：**任务状态 → 素材接收 → 单一渠道内容契约确认 → 调研、写作与审校 → 内容验收 → 渠道必要产物 → 交付包验收**。每个等待用户决定的节点，Agent 应展示用户可读摘要，而不是内部 schema：

```text
任务：TASK_ID（已建立任务目录时显示）
模式：标准写作
渠道：wechat
写作声音：自然默认
voice_snapshot：ready
阶段：等待内容契约确认
已完成：素材接收结果
下一步：回复“确认”，或说明要修改的字段
```

素材接收先报告已接收、已提取、等待处理、失败和待确认项；接收或提取不表示其中事实已经接受。进入正文的陈述仍关联来源和 `claim_id`，真实素材与后续生成的编辑视觉也保持不同身份。

内容契约合并请求中已明确的信息，只追问阻断字段，并确认主题、读者、一个 `target_id`、目的、篇幅、时效、证据等级、写作声音及视觉、排版和发布意图。写作声音默认是“自然默认”，可按序号、稳定 ID 或显示名称修改，不增加独立等待点。用户可以确认、指出修改字段或取消。

先完成内容验收，使 `final.md` 成为所选渠道的 canonical final；仅在其后生成渠道 YAML 要求的必要产物。交付包验收再列出文件位置和缺失项：核心包为 `final.md`、`sources.yaml`、`claims.yaml`、`asset-manifest.yaml`、`review-report.yaml`、`revision-report.yaml`、`acceptance-report.md`，外加当前渠道必要产物。微信完整交付包含格式化 Markdown、HTML 和封面；X 单帖与 X Thread 交付各自经过逐项渠道审查的正文。

任务状态摘要是写作流程的用户交互合同，不是 CLI 任务管理器。当前 CLI 提供机械检查、目录定位，以及已建立深度运行目录的确定性交接操作：`writing-master handoff prepare|complete|show`；这不扩大为 `quick/standard` 的通用续跑功能。

## 素材与 Baoyu 路由

Baoyu Skills 是独立安装的能力，本仓库不复制它们的实现。`writing-master` 负责在正确阶段发现和调用它们。

### 早预检、早摄入

模式确定后立即进行 capability/material preflight：

| 用户提供的素材 | 可用路由（已安装时） | 写作侧产物 |
|---|---|---|
| 网页、文章、X 帖子 | `baoyu-url-to-markdown` | 清洗后的 Markdown 和原始 URL |
| YouTube 视频、字幕或封面 | `baoyu-youtube-transcript` | transcript、metadata 和素材记录 |
| 纯文本或 Markdown | 当前 Agent；需要格式整理时用 `baoyu-format-markdown` | 规范化文本 |
| 本地图片、GIF、视频或图表 | 当前 Agent 登记 | `asset-manifest.yaml` |

预检阶段只识别能力、提取已有材料并记录来源，不生成图片、不排版、不发布。素材进入正文前仍需转换成可追溯的 `claim_id` 和来源记录。

### 晚生成、后发布

内容验收完成并形成 canonical final 后，图像类视觉才按 `storyboard.md` 路由：

- `baoyu-article-illustrator`：正文配图；
- `baoyu-cover-image`：封面；
- `baoyu-infographic`：基于已核验数据的信息图；
- `baoyu-image-gen`：明确提示词的单图；
- `baoyu-format-markdown`：Markdown 整理；
- `baoyu-markdown-to-html`：公众号 HTML；
- `baoyu-post-to-wechat` / `baoyu-post-to-x`：用户明确要求发布后执行。

`baoyu-format-markdown` 和 `baoyu-markdown-to-html` 只读取已验收正文与 `channel-contract.yaml`；它们不依赖图像类 storyboard。

详细规则见 [`baoyu-integration.md`](skills/writing-master/references/baoyu-integration.md)。

单渠道双入口的产品合同见[渠道适配 P0 PRD](docs/proposals/2026-07-29-channel-adaptation-p0-prd.md)。

## 安装

### 一键安装 Skills，并尝试安装 CLI

```bash
git clone https://github.com/NoApoNoTary/ai-writing-master.git ~/ai-writing-master
cd ~/ai-writing-master
bash install.sh
```

安装脚本会：

1. 检测本机已有的 Claude Code、Cursor、OpenClaw 或 Codex 配置目录；
2. 将仓库中的两个 Skill 链接到检测到的 Agent；
3. 创建 `${WRITING_MASTER_HOME:-~/.writing-master}` 的运行、素材与 `personal-context/` 基础目录；不会初始化画像或扫描、导入旧素材；
4. 在存在 `uv` 或 `pipx` 时，从仓库根目录安装 CLI。

### 直接使用 CLI

即使没有 `uv` 或 `pipx`，仓库内启动脚本也可直接运行：

```bash
cd ~/ai-writing-master
./bin/writing-master --version
./bin/writing-master --help
```

也可以把 `bin` 加入 PATH：

```bash
export PATH="$HOME/ai-writing-master/bin:$PATH"
```

## 快速使用

### 新建文章

```text
写一篇关于本地 AI Agent 工作流的公众号文章。
```

此时先选择快速、标准或深度模式。若希望直接跳过询问，在请求中明确模式：

```text
用深度写作模式，基于下面三个链接和两个本地截图写一篇公众号长文。
```

每个主写作任务只选择 `wechat`、`x-post`、`x-thread` 中的一个目标，正文从初稿开始就按该渠道合同创作。

### 改写已有文章

```text
把 article.md 改写成 X Thread，保留事实和立场，重构叙事顺序。
```

此请求进入 `writing-rewrite`，不启动深度写作代理链。之后说“再生成一个 X 单帖”会创建新的 Rewrite，并复用同一 source hash 与分析结果。

### 只执行一个环节

```text
只帮我审校这篇文章，重点检查证据和空话。
```

单模块任务由当前 Agent 在 `writing-master` 内执行，不伪装成不存在的独立 Skill。

更多示例见[快速开始指南](docs/quick-start.md)。

## CLI：机械检查，不是编辑裁判

```bash
# 机械文本检查
writing-master quality article.md --verbose

# 字符 n-gram 表面相似度
writing-master similarity source.md rewritten.md --json

# 显示运行数据目录
writing-master home

# 检查已建立的深度模式 handoff
writing-master handoff show RUN_DIR --json

# 显式管理个人上下文
writing-master context init
writing-master context profile show --json
writing-master context material list --json

# 确认或拒绝可追溯的风格候选
writing-master learn show --json

# 保存并校验任务内选题 Research Brief
writing-master research verify RUN_DIR --json

# 列出声音并冻结任务 Snapshot
writing-master voice list --json
writing-master voice snapshot RUN_DIR clear-analytical --source content-contract --json
writing-master voice verify-run RUN_DIR --json
```

`quality` 这个命令名为兼容现有调用保留。它只检查套话、句长变化、段落节奏、副词密度和字符 bigram 多样性，并输出机械预警分数。它不验证事实、证据、原创性、论证质量或作者风格，也不产生“AI 味百分比”。

`similarity` 使用字符 n-gram Jaccard 相似度。默认阈值 `0.6` 是工作流预警线，不等于抄袭、版权或原创性结论。

完整说明见 [CLI 工具指南](docs/cli-guide.md)。

## Voice Preset：任务级写作声音

Voice Preset 只控制词汇、句式、节奏、段落、开场、转折、确定性、幽默和类比，不改变事实、证据边界、核心判断、作者立场或真实经历。首版内置“自然默认”“清晰分析”“对话观察”“锐利评论”四项；内容契约确认后写入不可变的 `voice-profile-snapshot.json`，后续恢复只读任务快照，不回读已变化的 Registry。

Quick / Standard 只在初稿和 Voice Audit 读取该 Snapshot。Deep 模式仅 Writer 与 Auditor 的 Manifest 可列出它；Researcher 与 Editorial Strategist 不读取。非默认 Voice 任务默认不作为长期 Style Observation 的 baseline/evidence，平台 Rewrite 继续从已验收 canonical final 开始，不重新选择 Voice。

## Personal Context：显式、可追溯的个人上下文

Personal Context Runtime 提供版本化 Author Profile、五类 Knowledge Item、隐私准入、任务 Snapshot、usage 验证和确认式 Style Observation。它不会从 `personal_materials/` 自动扫描或迁移，也不会根据一次编辑自动改变作者风格。

```bash
# 只初始化 canonical Profile/Style/Knowledge 空状态
writing-master context init

# Profile 更新使用乐观 revision；素材按来源身份和 visibility 受管导入
writing-master context profile set profile.json --expected-revision 0
writing-master context material add experience.md \
  --kind experiences --title '一次可追溯经历' \
  --source-kind user_provided --source-ref 'local://experience-001' \
  --visibility ask_before_use --tag example

# Candidate 只进入 proposed；接受或拒绝都需要显式决定
writing-master learn propose style-candidate.json --run-dir RUN_DIR --json
writing-master learn decide OBSERVATION_ID --accept --json
```

`publishable` 素材可进入任务 Snapshot；`ask_before_use` 需要该任务的显式 approval；`private` 不进入写作 Snapshot。Style Profile 只聚合 accepted observations；proposed/rejected 不进入规则。标准或深度写作在内容契约确认后只使用任务内 Snapshot 和被选素材副本；全局更新只影响后续新任务。完整命令见 [CLI 工具指南](docs/cli-guide.md#context个人上下文)。

## Context-aware Research Brief

宽主题、只做选题或近期热点请求可先生成 3–10 个有实时 Evidence 的候选，并将 Agent draft 绑定到任务 `brief.md` 与冻结 Snapshot：

```bash
writing-master research save RUN_DIR research-brief-draft.json --json
writing-master research verify RUN_DIR --json
```

Runtime 校验字段、时间、分数、Evidence hash 和 `author_fit` 引用，不替 Agent 判断热度是否真实。缺少实时检索时不生成 Heat 或 Brief；用户选择 candidate 后，文章事实研究仍需独立形成 `sources.yaml` 与 `claims.yaml`。

## 运行目录

默认用户数据目录为 `~/.writing-master/`，也可通过 `WRITING_MASTER_HOME` 修改。安装脚本只创建真实存在的基础目录：

```text
~/.writing-master/
├── runs/
├── personal-context/              # installer 只创建根；context init 写入 canonical 空状态
├── personal_materials/
│   ├── articles/
│   ├── experiences/
│   └── topics/
├── exemplars/
├── themes/
└── output/
```

写作任务的文件化合同使用 `runs/{task_id}/` 保存 `status.json`、Brief、来源、主张、素材清单、草稿和审校报告。对已有 deep/multi-agent 运行目录，Handoff Runtime 可复核和恢复交接状态；它不会发现“最近任务”，也不把这套文件合同扩展成 `quick/standard` 的通用跨会话续跑服务。

## 仓库结构

```text
ai-writing-master/
├── skills/
│   ├── writing-master/
│   │   ├── SKILL.md
│   │   ├── agents/                 # 深度模式角色卡
│   │   └── references/             # 模式、证据、审校与 Baoyu 契约
│   └── writing-rewrite/
│       ├── SKILL.md
│       ├── platforms/              # 微信、X 单帖、X Thread 输出合同
│       └── references/             # 单目标改写与质量门槛
├── src/writing_master/             # CLI 实现
├── bin/writing-master              # 无需安装的 CLI 启动脚本
├── docs/
│   ├── quick-start.md
│   └── cli-guide.md
├── install.sh
└── pyproject.toml
```

## 当前能力边界

- 已交付：两个 Skill、三种新写作模式、深度模式角色协议、证据/素材契约、Baoyu 分阶段路由、微信/X 单帖/X Thread 单目标合同、机械文本检查和相似度命令，以及显式的个人上下文 Profile/Knowledge/Snapshot Runtime。
- Baoyu Skills 需要独立安装；仓库只负责能力发现和路由。
- 仓库当前没有 Web UI、数据面板、内置发布实现、十个独立写作模块、示例工程或模板目录。
- 渠道适配 P0 只接受 `wechat`、`x-post`、`x-thread`；X Article、自动发布和渠道数据反馈不属于本阶段。
- CLI 是确定性辅助工具；文章事实和编辑质量仍由研究与审校流程处理。
- 深度模式 Handoff Runtime 已验收，覆盖已建立 deep/multi-agent 运行目录的交接、hash、stale、attempt 与真实宿主链路；`quick/standard` 的通用任务恢复仍未实现。

项目现状和迁移核对见 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)。

## 来源与致谢

本项目参考并重组了以下项目的方法：

- [auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub)：长文流程、创意排水和分层审校思路；
- [wewrite](https://github.com/imraywang/wewrite)：模块化 Skill、改写工作流和 CLI 工程思路。

当前仓库是独立实现，实际能力以本仓库中的文件和测试结果为准。

## License 与反馈

[MIT License](LICENSE)

- [GitHub Issues](https://github.com/NoApoNoTary/ai-writing-master/issues)
