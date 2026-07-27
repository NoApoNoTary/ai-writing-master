# AI Writing Master

面向 AI Agent 的文件化写作工作流：先由用户选择执行模式，再完成内容契约、事实与素材调研、写作、审校和交付。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab.svg)](pyproject.toml)

## 项目定位

这个仓库目前提供两个可安装的 Skill：

| Skill | 用途 |
|---|---|
| `writing-master` | 从零创作完整文章；包含三种模式、证据与素材双轨、审校和 Baoyu 路由 |
| `writing-rewrite` | 对已有文章进行内容重构；内置小红书和抖音平台合同 |

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

洗稿、平台改写和只做标题、审校、选题等单一模块请求不触发这道完整文章模式闸门。`writing-rewrite` 在 P0 始终由当前 Agent 单独执行；每个平台从同一个只读源稿独立生成。深度或多 Agent 改写不属于当前 P0。

## 工作流

标准写作的主链路如下：

```text
模式选择
  → 内容契约 + 能力/素材预检
  → 事实轨 + 素材轨调研
  → 角度、读者决策、大纲和 storyboard
  → 初稿
  → 证据层、编辑层、声音层审校
  → 标题与内容验收（形成 canonical final）
  → 按需视觉、HTML 或平台草稿
  → 交付包验收
  → 明确发布指令后发布
```

深度写作的角色协议沿用同一条链路；宿主具备真实子代理能力时，才把高干扰环节拆给 fresh-context 角色：

- `Researcher`：来源、主张和真实素材；
- `Editorial Strategist`：角度、读者决策、结构和 storyboard；
- `Writer`：只读取已经接受的内容包；
- `Auditor`：独立检查证据、编辑质量和声音偏差；
- `Lead`：维护状态、用户确认、问题合并、Baoyu 闸门和最终验收。

代理之间通过运行目录中的文件产物通信，不把父对话全文复制给所有角色。角色协议不等于已完成的运行时能力：在技术运行时和真实宿主验收完成前，不把单 Agent 的角色模拟、跨会话续跑或文件存在本身描述为真实 Handoff。

## P0：任务摘要、确认与交付

标准写作的用户主链是：**任务状态 → 素材接收 → 内容契约确认 → 调研、写作与审校 → 内容验收 → 按需视觉/HTML/平台草稿 → 交付包验收**。每个等待用户决定的节点，Agent 应展示用户可读摘要，而不是内部 schema：

```text
任务：TASK_ID（已建立任务目录时显示）
模式：标准写作
阶段：等待内容契约确认
已完成：素材接收结果
下一步：回复“确认”，或说明要修改的字段
```

素材接收先报告已接收、已提取、等待处理、失败和待确认项；接收或提取不表示其中事实已经接受。进入正文的陈述仍关联来源和 `claim_id`，真实素材与后续生成的编辑视觉也保持不同身份。

内容契约合并请求中已明确的信息，只追问阻断字段，并确认主题、读者、平台、目的、篇幅、时效、证据等级及视觉、排版和发布意图。用户可以确认、指出修改字段或取消；未请求发布时只准备可审阅产物。

先完成内容验收，使 `final.md` 成为 canonical final；仅在其后生成本次要求的视觉资产、HTML 或平台草稿。交付包验收再列出文件位置和缺失项：核心包为 `final.md`、`sources.yaml`、`claims.yaml`、`asset-manifest.yaml`、`review-report.yaml`、`revision-report.yaml`、`acceptance-report.md`，外加本次明确要求的派生产物。

任务状态摘要是写作流程的用户交互合同，不是 CLI 任务管理器。当前 CLI 提供机械检查和目录定位；确定性的跨会话续跑及真实深度模式 Handoff 仍以技术运行时和真实宿主验收为准。

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
3. 创建 `${WRITING_MASTER_HOME:-~/.writing-master}` 的运行与素材目录；
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

### 改写已有文章

```text
把 article.md 内容级改写成小红书版本，保留事实和立场，重构叙事顺序。
```

此请求进入 `writing-rewrite`，不启动深度写作代理链。

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
```

`quality` 这个命令名为兼容现有调用保留。它只检查套话、句长变化、段落节奏、副词密度和字符 bigram 多样性，并输出机械预警分数。它不验证事实、证据、原创性、论证质量或作者风格，也不产生“AI 味百分比”。

`similarity` 使用字符 n-gram Jaccard 相似度。默认阈值 `0.6` 是工作流预警线，不等于抄袭、版权或原创性结论。

完整说明见 [CLI 工具指南](docs/cli-guide.md)。

## 运行目录

默认用户数据目录为 `~/.writing-master/`，也可通过 `WRITING_MASTER_HOME` 修改。安装脚本只创建真实存在的基础目录：

```text
~/.writing-master/
├── runs/
├── personal_materials/
│   ├── articles/
│   ├── experiences/
│   └── topics/
├── exemplars/
├── themes/
└── output/
```

写作任务的文件化合同使用 `runs/{task_id}/` 保存 `status.json`、Brief、来源、主张、素材清单、草稿和审校报告。具体文件随所选模式和任务需求变化；当前 CLI 不把这套文件合同承诺为确定性的跨会话续跑服务。

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
│       ├── platforms/              # 小红书、抖音输出合同
│       └── references/             # 多平台改写与质量门槛
├── src/writing_master/             # CLI 实现
├── bin/writing-master              # 无需安装的 CLI 启动脚本
├── docs/
│   ├── quick-start.md
│   └── cli-guide.md
├── install.sh
└── pyproject.toml
```

## 当前能力边界

- 已交付：两个 Skill、三种新写作模式、深度模式角色协议、证据/素材契约、Baoyu 分阶段路由、小红书/抖音改写合同、机械文本检查和相似度命令。
- Baoyu Skills 需要独立安装；仓库只负责能力发现和路由。
- 仓库当前没有 Web UI、数据面板、内置发布实现、十个独立写作模块、示例工程或模板目录。
- `writing-rewrite` 当前内置的平台合同只有小红书和抖音；其他平台需要先补对应合同再宣称支持。
- CLI 是确定性辅助工具；文章事实和编辑质量仍由研究与审校流程处理。
- 深度模式已有角色协议；真实子代理 Handoff 和跨会话续跑仍取决于技术运行时及真实宿主验收。

项目现状和迁移核对见 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)。

## 来源与致谢

本项目参考并重组了以下项目的方法：

- [auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub)：长文流程、创意排水和分层审校思路；
- [wewrite](https://github.com/imraywang/wewrite)：模块化 Skill、改写工作流和 CLI 工程思路。

当前仓库是独立实现，实际能力以本仓库中的文件和测试结果为准。

## License 与反馈

[MIT License](LICENSE)

- [GitHub Issues](https://github.com/NoApoNoTary/ai-writing-master/issues)
