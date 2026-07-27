---
name: writing-rewrite
description: |
  将一份 canonical source 按目标平台重新组织为独立版本。默认由当前 Agent 执行；每个平台都从源稿重新生成，不串行继承其他平台版本。编辑审查负责事实、立场和平台价值，CLI 只提供机械文本与相似度预警。触发词：改写、小红书版、抖音版、一稿多发、平台适配。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Writing Rewrite

## 目标

保留源稿的事实、证据边界、作者立场和真实案例，同时为目标平台重新决定：

- 内容顺序；
- 开头与收束；
- 信息密度；
- 句式与段落；
- 互动方式；
- 图片或画面需求。

改写不是逐句替换，也不通过固定 emoji、口号或平台刻板话术制造“平台感”。

## 运行约定

- `{home}` = `$WRITING_MASTER_HOME`，未设置时使用 `~/.writing-master`
- `{skill_dir}` = 当前 `writing-rewrite` Skill 目录
- 源稿是 canonical source，整个任务内保持只读
- 默认使用当前 Agent；用户明确要求深度改写或多 Agent 时，才按目标平台创建 fresh-context 代理
- 多个平台版本彼此隔离，每个版本都从 canonical source 开始

## Phase 0：输入与任务目录

按优先级取得源稿：

1. 用户指定的文件；
2. 用户在当前对话粘贴的正文；
3. Writing Master 当前任务的 `final.md`。

确认目标平台。支持的平台来自实际存在的 YAML：

- `platforms/xiaohongshu.yaml`
- `platforms/douyin.yaml`

创建或复用当前 run 目录，并保存：

```text
source.md
rewrite-status.json
```

`rewrite-status.json` 至少记录源稿 hash、目标平台、各版本状态和重试次数。

## Phase 1：加载合同

真实读取：

- `references/multiplatform-rewrite.md`
- `references/quality-gates.md`
- 每个目标平台对应的 `platforms/<platform>.yaml`

平台 YAML 是长度、输出类型、图片需求、标签数量和 `rewrite_brief` 的真实来源。不要使用未写入 YAML 的固定模板。

## Phase 2：分析 canonical source

生成 `source-analysis.md`：

```yaml
core_thesis: "核心判断"
facts:
  - statement: "不可变事实"
    source_or_location: "源稿位置或来源"
boundaries:
  - "限制条件或不确定性"
author_position:
  - "作者明确立场"
personal_materials:
  - "真实经历及其源稿位置"
optional_details:
  - "平台版本可删减的旁支"
```

分析阶段只抽取，不生成目标平台文案。

## Phase 3：独立平台改写

对每个平台分别执行：

1. 读取 canonical `source.md`、`source-analysis.md` 和该平台 YAML；
2. 选择该平台最需要保留的一个主判断；
3. 重新建立结构，不沿用源稿段落顺序；
4. 保留事实、边界和作者立场；
5. 第一人称只使用源稿或用户提供的真实素材；
6. 按 YAML 生成正文、标签、画面提示或补图需求；
7. 保存为 YAML 中的 `output_filename`。

用户明确要求多 Agent 时，每个平台代理的输入只包含：

```text
source.md
source-analysis.md
platforms/<platform>.yaml
references/multiplatform-rewrite.md
```

平台代理不读取其他平台版本。

## Phase 4：编辑审查

先执行人工语义层面的编辑审查，再运行 CLI。

### 事实与立场

- 关键事实与源稿一致；
- 限制条件得到保留；
- 没有新增来源不明的经历、数据或测试；
- 作者立场没有因平台化而反转。

### 平台价值

- 开头、结构和节奏符合平台 YAML；
- 删减后仍保留一个完整判断；
- 互动元素服务于正文；
- 平台版本不是缩写版源稿或刻板模板。

保存 `<platform>-review.json`：

```json
{
  "editorial_decision": "pass | revise",
  "fact_issues": [],
  "platform_issues": [],
  "voice_issues": [],
  "required_changes": []
}
```

## Phase 5：机械预警

CLI 可用时执行：

```bash
writing-master quality <platform>.md --json
writing-master similarity source.md <platform>.md --json
```

多个目标平台时，再检查平台版本之间的相似度：

```bash
writing-master similarity source.md xiaohongshu.md douyin.md --json
```

解释规则：

- `mechanical_score` 只表示机械语言预警多少；
- `similarity.max_similarity` 只表示字符 n-gram 重合程度；
- 两者都不替代编辑审查；
- 机械检查结果附加到 `<platform>-review.json`。

## Phase 6：定向返工

根据失败类型只重做相应部分：

- 事实问题：恢复或修正源稿中的事实与限定；
- 平台问题：重新组织该平台版本；
- 相似度偏高：改变信息顺序、开头、结构和表达框架；
- 机械预警：针对具体套话、句长或段落命中修订。

每个平台最多两轮完整重写。每轮更新 review 文件并保留版本差异。

## Phase 7：素材与 Baoyu 路由

平台 YAML 中 `needs_images=true` 时，先输出 `visual-needs.md`，列出每张图的职责、位置与是否已有素材。

- 小红书图片卡片：用户要求制作后路由 `baoyu-xhs-images`；
- 普通正文配图：路由 `baoyu-article-illustrator`；
- 封面：路由 `baoyu-cover-image`。

文字版本通过编辑审查后再执行视觉生产。视觉产物不覆盖平台正文源文件。

## Phase 8：交付

汇报：

- canonical source 路径与 hash；
- 每个平台输出路径和字数；
- 编辑审查结论；
- 机械检查与相似度预警；
- 已知剩余问题；
- 素材或视觉下一步。

## 参考文件

- `references/multiplatform-rewrite.md`
- `references/quality-gates.md`
- `platforms/xiaohongshu.yaml`
- `platforms/douyin.yaml`
