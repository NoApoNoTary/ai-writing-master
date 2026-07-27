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

安装脚本会链接 `writing-master` 和 `writing-rewrite`，并创建默认数据目录 `~/.writing-master/`。如果本机存在 `uv` 或 `pipx`，脚本还会从仓库根目录安装 CLI。

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

新建文章时只有深度模式使用多 Agent。快速和标准模式不会隐式创建子代理。

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

此时还不会生成图片。正文结构稳定、storyboard 明确且本次任务需要视觉交付后，才调用配图、封面、信息图或 HTML Skill。

公开发布需要单独、清晰的发布指令；“继续”“下一步”或“看起来可以”只推进到下一份可审阅产物。

## 4. 改写已有文章

```text
把 ./article.md 改写成小红书版本。
保留原文事实和立场，但重构信息顺序、开头和表达方式。
```

此请求由 `writing-rewrite` 处理，不询问三种新写作模式。若未指定目标平台，Agent 会先让你选择平台。

当前仓库内置的小红书和抖音平台合同分别位于 `platforms/xiaohongshu.yaml` 与 `platforms/douyin.yaml`。其他平台需要先提供对应输出合同。

改写默认由当前 Agent 完成。只有在请求中明确提出“深度改写”或“多 Agent 改写”时，才为不同目标平台创建隔离代理。

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

## 6. 继续上次任务

```text
继续上次的文章。
```

工作流会从 `${WRITING_MASTER_HOME:-~/.writing-master}/runs/` 中读取最近的未完成任务，并从 `status.json` 恢复模式和当前阶段。

如果有多个未完成任务，最好直接提供任务目录或 `task_id`，避免恢复错误对象。

## 7. CLI 辅助检查

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

## 8. 数据目录

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

## 9. 常见问题

### 没有出现模式选择

- 洗稿、只审校、只做标题等单模块请求本来就不触发；
- 当前请求已经明确写了模式时不会重复询问；
- 新建完整文章且未指定模式时，应先出现固定的三选一问题。

### Baoyu 没有被调用

先检查对应 Skill 是否已经安装到当前 Agent 的可发现目录。预检只记录能力和素材入口；生图与排版要等证据、结构和 storyboard 稳定后执行。

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
- [深度写作多 Agent 协议](../skills/writing-master/references/agent-orchestration.md)
- [证据与素材契约](../skills/writing-master/references/evidence-and-assets.md)
- [Baoyu 分阶段路由](../skills/writing-master/references/baoyu-integration.md)
