# AI Writing Master 快速开始

## 1. 安装

要求：

- Python 3.11 或更高版本；
- 本机至少存在一个受支持 Agent 的配置目录：Claude Code、Cursor、OpenClaw 或 Codex。

```bash
git clone https://github.com/NoApoNoTary/ai-writing-master.git ~/ai-writing-master
cd ~/ai-writing-master
bash install.sh
```

安装脚本会链接 `writing-master` 和 `writing-rewrite`，并创建默认数据目录 `~/.writing-master/`（含空的 `personal-context/` 根目录）。它不会初始化画像、读取或导入旧 `personal_materials/`。如果本机存在 `uv` 或 `pipx`，脚本还会从仓库根目录安装 CLI。

验证仓库内 CLI：

```bash
cd ~/ai-writing-master
./bin/writing-master --version
./bin/writing-master --help
```

如果已由 `uv` 或 `pipx` 安装，也可以直接运行：

```bash
writing-master --version
```

## 2. 第一次新建文章

向 Agent 输入：

```text
写一篇关于本地 AI Agent 工作流的公众号文章。
```

如果请求中没有模式，`writing-master` 会先停在模式选择闸门：

固定问题和选项见 [`mode-selection.md`](../skills/writing-master/references/mode-selection.md)。

直接回复 `1`、`2` 或 `3`。模式确定之前不会创建任务目录、开始调研或执行 Baoyu。

### 快速草稿

```text
用快速草稿模式写一篇 1200 字文章，主题是本地模型的实际使用成本。
```

特点：

- 当前 Agent 单独执行；
- 只核验正文会使用的关键事实；
- 形成简版大纲和完整草稿；
- 做一次合并审校。

### 标准写作

```text
用标准写作模式，写一篇面向独立开发者的公众号文章：如何选择本地 Agent 工具。
```

特点：

- 当前 Agent 单独执行；
- 完成事实与素材双轨调研；
- 先确认角度，再写作；
- 依次完成证据层、编辑层和声音层审校；
- 输出标题和验收报告。

#### 可选：先配置个人上下文

Profile 和素材需要显式管理；安装或首次写作不会自动把历史文件作为个人事实使用。

```bash
writing-master context init
writing-master context profile set profile.json --expected-revision 0
writing-master context material add experience.md \
  --kind experiences --title '一次可追溯经历' \
  --source-kind user_provided --source-ref 'local://experience-001' \
  --visibility ask_before_use --tag example

# 查看确认式风格学习状态
writing-master learn show --json
```

标准或深度任务在内容契约确认后才创建任务内 Snapshot。`ask_before_use` 素材需要 `context approve RUN_DIR ITEM_ID --allow background|paraphrase|quote`；`private` 素材不会进入 Snapshot。可用 `context search`、`context snapshot` 和 `context verify-run` 查看或核验 Runtime 结果。

用户明确要求从一次编辑中学习时，先准备包含 baseline/edited hash、具体证据、规则与范围的 Candidate，再显式决定：

```bash
writing-master learn propose style-candidate.json --json
writing-master learn decide OBSERVATION_ID --accept --json
```

只有 accepted observation 会进入后续任务的新 Snapshot，当前任务不会被反向改写。完整参数见 [CLI 工具指南](cli-guide.md#learn确认式风格学习)。

宽主题、只做选题或近期热点请求可先形成 Research Brief。Agent 生成 3–10 个候选 draft 后，Runtime 负责绑定和校验：

```bash
writing-master research save RUN_DIR research-brief-draft.json --json
writing-master research verify RUN_DIR --json
```

缺少实时检索能力时不生成 Heat 或 Brief。用户选择 candidate 后再进入文章事实研究；Research Brief Evidence 不自动成为正文 claim。详见 [CLI 工具指南](cli-guide.md#research上下文感知选题-brief)。

### 深度写作

```text
用深度写作模式，基于我提供的资料写一篇重要长文。研究、策划、写作和审计要隔离上下文。
```

特点：

- Lead 维护状态和用户确认；
- Researcher 负责来源、主张与素材；
- Editorial Strategist 负责角度和结构；
- Writer 只读取已接受的内容包；
- Auditor 独立审查后，由 Writer 统一修订。

这些是深度模式的角色协议。深度模式 Handoff Runtime 已验收：对已建立的 deep/multi-agent 运行目录，它校验 Manifest、Result、hash、stale 与 attempt，并已有真实宿主链路证据。每次任务仍要由 capability preflight 确认当前宿主能够实际创建子代理；快速和标准模式不会隐式创建子代理。

### P0 任务状态与内容契约

模式确定后，Agent 先用用户可读的任务摘要说明当前位置：

```text
任务：TASK_ID（已建立任务目录时显示）
模式：标准写作
阶段：等待内容契约确认
已完成：素材接收结果
下一步：回复“确认”，或说明要修改的字段
```

内容契约会合并请求中已经明确的主题、读者、平台、目的、篇幅、时效、证据等级，以及视觉、排版和发布意图；只追问尚未确定的阻断字段。回复“确认”继续，直接指出字段即可修改，回复“取消”停止本次任务。未收到明确发布指令时，流程只形成可审阅产物。

## 3. 把素材带入写作

可以在首个请求中同时提供：

- 网页或 X 帖子 URL；
- YouTube 链接；
- 本地 Markdown、PDF、图片、GIF、视频或图表路径；
- 历史文章和个人经历记录。

示例：

```text
用标准写作模式写一篇公众号文章。
参考资料：
- https://example.com/article
- https://youtube.com/watch?v=VIDEO_ID
- ./materials/test-result.md
- ./materials/screenshot-01.png
先整理事实和素材清单，再给我选题方向。
```

模式选择后，工作流会进行能力与素材预检：

1. 发现当前运行时已经安装的 Baoyu Skills；
2. 用 `baoyu-url-to-markdown` 或 `baoyu-youtube-transcript` 提取可读材料；
3. 把本地视觉素材登记到 `asset-manifest.yaml`；
4. 将准备进入正文的陈述写入 `claims.yaml` 并关联 `sources.yaml`；
5. 在结构确定后生成 `storyboard.md`。

素材接收后先报告结果，而不是直接把内容写进正文：

```text
已接收：3 项
已提取：2 项
等待处理：1 项
失败：0 项
需要你确认：素材 A 是否允许作为公开引用
```

素材被接收或提取不表示其中的事实已经接受。进入正文的陈述仍需关联 `claim_id` 和来源；真实素材与编辑生成素材也会在清单中分开记录。

此时还不会生成图片。标题与正文完成内容验收、形成 canonical final 后，图像类视觉才按 storyboard 调用配图、封面或信息图；Markdown 格式化和 HTML 则读取已验收正文与 `channel-contract.yaml`，不依赖 storyboard。

公开发布需要单独、清晰的发布指令；“继续”“下一步”或“看起来可以”只推进到下一份可审阅产物。

## 4. 改写已有文章

```text
把 ./article.md 改写成小红书版本。
保留原文事实和立场，但重构信息顺序、开头和表达方式。
```

此请求由 `writing-rewrite` 处理，不询问三种新写作模式。若未指定目标平台，Agent 会先让你选择平台。

当前仓库内置的小红书和抖音平台合同分别位于 `platforms/xiaohongshu.yaml` 与 `platforms/douyin.yaml`。其他平台需要先提供对应输出合同。

改写在 P0 始终由当前 Agent 完成；每个目标平台都从同一个只读源稿独立生成。深度或多 Agent 改写不属于当前 P0。来自 Writing Master 的输入必须是同一任务中内容验收通过的 `final.md`；用户直接提供的完整正文则作为独立的 `standalone_user_input`，不被描述为已验收的 Writing Master final。

相似度命令可以提供表面重合预警：

```bash
writing-master similarity article.md xiaohongshu.md --json
```

它不替代人工的原创性、版权和事实审查。

## 5. 只做一个模块

以下请求不启动完整写作链：

```text
只给我三个选题方向，不写正文。
```

```text
只审校这篇文章，分别列出证据问题、结构问题和声音偏差。
```

```text
只根据 final.md 和 storyboard.md 生成公众号配图。
```

选题、审校和标题属于 `writing-master` 内部模块；配图、封面、排版和发布路由到当前环境里实际存在的 Baoyu Skill。

## 6. 查阅已有任务产物

```text
请读取 TASK_ID（或任务目录）中的产物，告诉我当前阶段、已完成文件和下一步。
```

如果已存在 `${WRITING_MASTER_HOME:-~/.writing-master}/runs/TASK_ID/`，可让 Agent 读取其中的 `status.json`、Brief、素材、草稿和审校产物，先给出当前状态摘要，再决定是否继续。

直接提供任务目录或 `task_id`，避免把“上次”解释为错误对象。对于已建立的 deep/multi-agent 运行目录，可使用：

```bash
writing-master handoff show RUN_DIR --json
```

它只复核深度角色交接，不发现“最近任务”，也不推进快速或标准写作；`quick/standard` 尚未提供通用的确定性跨会话续跑。

## 7. 交付包

标准写作先完成标题与正文的内容验收，使 `final.md` 成为 canonical final；只有随后按需生成视觉资产、HTML 或平台草稿。最后的交付包验收列出本次文件位置和仍缺的请求项：

- `final.md`；
- `sources.yaml`、`claims.yaml` 与 `asset-manifest.yaml`；
- `review-report.yaml` 与 `revision-report.yaml`；
- `acceptance-report.md`；
- 用户明确要求的视觉资产、HTML 或平台草稿。

未请求发布时，任务停在交付包验收或平台草稿，不产生公开发布动作。

## 8. CLI 辅助检查

### 机械文本检查

```bash
writing-master quality final.md --verbose
```

它检查五项可由代码重复计算的文本特征：

- 套话命中；
- 句长变化；
- 段落长度变化；
- 常见副词密度；
- 字符 bigram 多样性。

机械得分只表示这些预警的多少。事实、证据、论证和声音仍由审校流程处理。

### 表面相似度

```bash
writing-master similarity source.md rewritten.md
```

默认使用字符 3-gram Jaccard，相似度阈值为 `0.6`。这个阈值是工作流信号，不是原创性结论。

更多参数见 [CLI 工具指南](cli-guide.md)。

## 9. 数据目录

```bash
writing-master home
```

默认输出：

```text
~/.writing-master
```

可通过环境变量修改：

```bash
export WRITING_MASTER_HOME="$HOME/content-system"
writing-master home
```

安装脚本创建：

```text
runs/
personal_materials/articles/
personal_materials/experiences/
personal_materials/topics/
exemplars/
themes/
output/
```

## 10. 常见问题

### 没有出现模式选择

- 洗稿、只审校、只做标题等单模块请求本来就不触发；
- 当前请求已经明确写了模式时不会重复询问；
- 新建完整文章且未指定模式时，应先出现固定的三选一问题。

### Baoyu 没有被调用

先检查对应 Skill 是否已经安装到当前 Agent 的可发现目录。预检只记录能力和素材入口；标题与正文完成内容验收、形成 canonical final 后，图像类视觉按 storyboard 执行，Markdown/HTML 按渠道合同执行。

### `writing-master` 命令不存在

直接使用仓库启动脚本：

```bash
cd ~/ai-writing-master
./bin/writing-master --help
```

或把 `~/ai-writing-master/bin` 加入 PATH。

### 机械得分高，但文章仍然不好

这是预期情况。机械检查不理解事实、论证、读者价值或个人风格，最终判断应以研究和独立审校为准。

## 相关文档

- [项目 README](../README.md)
- [CLI 工具指南](cli-guide.md)
- [模式选择规则](../skills/writing-master/references/mode-selection.md)
- [深度写作多 Agent 协议（角色合同）](../skills/writing-master/references/agent-orchestration.md)
- [证据与素材契约](../skills/writing-master/references/evidence-and-assets.md)
- [Baoyu 分阶段路由](../skills/writing-master/references/baoyu-integration.md)
