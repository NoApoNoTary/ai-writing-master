# Baoyu 可选素材路由

Baoyu 是独立安装的素材、排版与发布能力。AI Writing Master 不复制其源码，只在用户明确需要相关后续动作时调用。

默认全局位置：

```text
~/.claude/skills/baoyu-*
```

## 路由表

| 用户需求 | Baoyu Skill |
|---|---|
| 为文章规划并生成配图 | `baoyu-article-illustrator` |
| 生成文章封面 | `baoyu-cover-image` |
| 生成信息图 | `baoyu-infographic` |
| 生成单张图片 | `baoyu-image-gen` |
| Markdown 转公众号 HTML | `baoyu-markdown-to-html` |
| 发布微信公众号 | `baoyu-post-to-wechat` |
| 发布普通 X 帖子或 X Article | `baoyu-post-to-x` |

## 调用规则

1. 普通写作任务不自动触发 Baoyu。
2. 用户在当前请求中提出配图、封面、信息图、排版或发布时，路由到对应 Skill。
3. 文章完成后可以列出可选动作，但不自动生成或发布。
4. Baoyu Skill 不存在时，保留 `final.md`，提示安装对应 Skill 后继续。

## 生图能力说明

- `baoyu-article-illustrator` 负责分析文章、识别配图位置、选择 Type × Style × Palette，并保存可复现的提示词文件。
- `baoyu-cover-image` 负责封面的类型、色板、渲染、文字、情绪和比例。
- `baoyu-image-gen` 是实际生图后端适配器，支持 OpenAI、Google、Azure OpenAI、OpenRouter、DashScope、Z.AI、MiniMax、Replicate、Jimeng、Seedream 和 Agnes 等提供方。
- 首次生图需要通过 `EXTEND.md` 选择 provider、model、quality 和配置保存位置，并提供对应 API Key。
