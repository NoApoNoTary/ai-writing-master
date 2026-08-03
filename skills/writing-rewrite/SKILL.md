---
name: writing-rewrite
description: |
  将一份已有 canonical source 改写为一个经过渠道审查的完整成品。每次 Rewrite 只接受一个 target_id；需要第二个渠道时新建一次 Rewrite，并复用相同的 source hash 与 source-analysis。编辑审查负责事实、立场、声音和渠道价值，CLI 只提供机械文本与源稿相似度预警。触发词：改写、渠道适配、公众号版、X 单帖、X Thread、再生成一个渠道版本。
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

保留源稿的事实、证据边界、作者立场、真实案例和已验收声音，同时只为本次选择的一个渠道重新决定：

- 内容顺序；
- 开头与收束；
- 信息密度；
- 句式与段落；
- 互动方式；
- 渠道要求的格式、图片或封面。

改写不是逐句替换，也不通过固定 emoji、口号或平台刻板话术制造“渠道感”。

## 运行约定

- `{home}` = `$WRITING_MASTER_HOME`，未设置时使用 `~/.writing-master`
- `{skill_dir}` = 当前 `writing-rewrite` Skill 目录
- `source_ref` 只能是 `accepted_final` 或 `standalone_input`；整个 Rewrite 内 `source.md` 保持只读
- P0 的 `target_id` 只能是 `wechat`、`x-post` 或 `x-thread`
- 一个 run 只接受一个 `target_id`，不创建目标列表或批处理状态
- P0 默认并始终使用当前 Agent；深度或多 Agent 改写尚未定义真实渠道角色与 Handoff 合同，收到该请求时说明受影响能力并等待用户确认标准改写或取消
- Rewrite 不新增、展示或解析 Voice Selector；来自 Writing Master 的 canonical source 保持其已验收声音，只按渠道合同做必要适配，绝不回写来源 `final.md`
- 用户需要第二个渠道时新建一次 Rewrite；复用相同 `source_sha256` 和已验证的 `source-analysis.md`，不重复调研，也不把前一个渠道正文作为输入

## Phase 0：输入、单目标与任务目录

先确定来源，不根据“当前任务存在”自动挑选源稿：

1. `accepted_final`：使用同一 Writing Master 任务的已验收 canonical package。必须读取 `final.md`、`acceptance-report.md`、`sources.yaml` 与 `claims.yaml`；存在时同时读取同一任务的 `editorial-brief.md`、`outline.md` 和 `research-summary.md`。任务状态为 `voice_snapshot=ready` 时，还要读取并校验同一任务的 `voice-profile-snapshot.json`。`acceptance-report.md` 必须确认内容验收通过。未验收的 `draft-v1.md`、`draft-v2.md` 或 `final.md` 不得进入 Rewrite，也不得作为视觉、格式或发布来源。
2. `standalone_input`：用户直接提供的文件或当前对话中的完整正文。它可作为本次 Rewrite 的独立 canonical source，不要求 Writing Master 的验收报告。

将获准输入复制为本次 run 的 `source.md`，计算 SHA-256；之后 `source.md` 只读。`standalone_input` 不应被描述成已验收的 Writing Master final。

确认本次唯一的 `target_id`：

- `platforms/wechat.yaml`
- `platforms/x-post.yaml`
- `platforms/x-thread.yaml`

用户一次给出多个目标时，只让用户确定本次的一个 `target_id`；其余目标通过后续 Rewrite 完成。目标确定前不创建渠道正文。

创建新的 Rewrite run，并保存：

```text
source.md
rewrite-status.json
```

`rewrite-status.json` 使用单目标结构：

```json
{
  "entry": "rewrite",
  "target_id": "wechat | x-post | x-thread",
  "source_ref": "accepted_final | standalone_input",
  "source_sha256": "...",
  "source_analysis_sha256": null,
  "output_sha256": null,
  "review_sha256": null,
  "derivatives_sha256": {},
  "status": "in_progress | completed | failed",
  "attempt": 1
}
```

`target_id` 是标量；状态只描述当前 Rewrite，不维护目标集合、逐目标状态或跨任务重试。

## Phase 1：加载单一渠道合同

真实读取：

- `references/single-target-rewrite.md`
- `references/quality-gates.md`
- 本次 `target_id` 对应的一个 `platforms/<target_id>.yaml`

平台 YAML 是长度、输出类型、图片、HTML、封面、标签、必要派生产物和 `rewrite_brief` 的真实来源。不要同时加载其他目标合同，也不要使用未写入 YAML 的固定模板。

`x-post` 与 `x-thread` 的 `manual_x_composer_preview` 是显式外部验收能力：开始正文前先确认当前宿主能取得实际 composer 预览，或用户会提供同一正文的预览证据。两者都没有时仍可保存草稿，但本次 Rewrite 必须以 `failed` 结束，不得声称通过 280 weighted length 校验。

## Phase 2：生成或复用 source analysis

首次处理该 source hash 时生成 `source-analysis.md`：

```yaml
source_sha256: "..."
supporting_artifacts:
  - path: "claims.yaml"
    sha256: "..."
core_thesis: "核心判断"
facts:
  - statement: "不可变事实"
    source_or_location: "源稿位置或来源"
boundaries:
  - "限制条件或不确定性"
author_position:
  - "作者明确立场"
voice_basis:
  - "来自冻结 Voice Snapshot 或源稿的词汇、句式、节奏和确定性边界"
personal_materials:
  - "真实经历及其源稿位置"
optional_details:
  - "不影响核心判断的源稿旁支"
```

`accepted_final` 的分析从 `final.md` 与同一只读 canonical package 的 accepted claims、来源边界、编辑判断和冻结 Voice Snapshot 中抽取，因此短渠道 final 不会丢掉已经完成的研究依据或任务级声音；`standalone_input` 只分析用户正文。分析阶段不生成目标渠道文案，也不重新做 Article Research。`source-analysis.md` 不写 `target_id`、渠道结构或渠道输出决定；首次保存后立即计算 SHA-256，并写入 `rewrite-status.json.source_analysis_sha256`。

再次基于同一 canonical source 发起 Rewrite 时，优先复制前一 Rewrite 包中的 `source-analysis.md`。复用必须同时满足：分析内记录的 `source_sha256` 与本次 `source.md` 完全一致；`supporting_artifacts` 中每个文件的当前 hash 一致；分析文件当前 SHA-256 与前一 run 的 `rewrite-status.json.source_analysis_sha256` 一致。校验通过后把同一分析 hash 写入新 run，并保持分析文件只读。任一 hash 不一致时为当前 source 重新分析，不继承旧渠道正文或旧分析结论。

## Phase 3：单渠道改写

只执行本次 `target_id`：

1. 读取只读 `source.md`、`source-analysis.md` 和一个渠道 YAML；
2. 选择该渠道最需要保留的一个主判断；
3. 重新建立结构，不沿用源稿段落顺序；
4. 保留事实、边界和作者立场；
5. 第一人称只使用源稿或用户提供的真实素材；
6. 保留源稿已验收的写作声音，不重新选择 Voice；
7. 按 YAML 生成正文、标签及必要的格式或视觉需求；
8. 保存为 YAML 中的 `rewrite_output_filename`。

本次 Rewrite 不读取任何其他渠道正文，也不把已完成版本作为当前版本的输入。

## Phase 4：渠道编辑审查

先执行语义层面的编辑审查，再运行 CLI。

### 事实、立场与声音

- 关键事实与源稿一致；
- 限制条件得到保留；
- 没有新增来源不明的经历、数据或测试；
- 作者立场没有因渠道化而反转；
- 渠道适配没有覆盖 source 中已经验收的 Voice。

### 渠道价值

- 开头、结构和节奏符合当前渠道 YAML；
- 删减后仍保留一个完整判断；
- 互动元素服务于正文；
- 成品不是缩写版源稿或刻板模板；
- YAML 声明的必要派生产物都有明确生成路径。

保存 `<target_id>-review.json`：

```json
{
  "target_id": "wechat | x-post | x-thread",
  "source_sha256": "...",
  "source_analysis_sha256": "...",
  "output_sha256": "...",
  "length_validation": {
    "validator": "manual_x_composer_preview | not_applicable",
    "status": "pass | unavailable | not_applicable",
    "evidence": ["预览时间、截图路径或用户确认；Thread 每条各一项，不适用时为空"]
  },
  "editorial_decision": "pass | revise",
  "fact_issues": [],
  "channel_issues": [],
  "voice_issues": [],
  "required_changes": []
}
```

生成审查文件前先计算当前渠道正文的 `output_sha256`。Review 中的 source、analysis 与 output hash 必须指向本次当前文件。正文发生变化时，原审查结论失效，必须重新审查并更新 `output_sha256`；此阶段 `review_sha256` 保持为 null，直到机械结果附加完成。

X 渠道的 `length_validation.status` 只有在实际 composer 预览或用户提供的同文预览证据确认通过后才能写为 `pass`。字符数估算、编辑器字数或模型自行判断都不能替代该证据；正文变化会使原长度证据失效。微信使用 `not_applicable`。

## Phase 5：机械预警

CLI 可用时只比较 canonical source 与当前渠道正文：

```bash
writing-master quality <rewrite_output_filename> --json
writing-master similarity source.md <rewrite_output_filename> --json
```

解释规则：

- `mechanical_score` 只表示机械语言预警多少；
- `similarity.max_similarity` 只表示源稿与当前成品的字符 n-gram 重合程度；
- 两者都不替代编辑审查；
- 机械检查结果附加到 `<target_id>-review.json`；
- 不比较两个渠道成品之间的相似度。

编辑结论为 `pass` 且机械结果附加完成后，计算最终 Review 文件的 SHA-256，写入 `rewrite-status.json.review_sha256`。任何后续正文、机械结果或 Review 变化都将 `review_sha256` 重置为 null，并重新执行受影响的审查步骤。

## Phase 6：定向返工

根据失败类型只重做当前渠道的相应部分：

- 事实问题：恢复或修正源稿中的事实与限定；
- 渠道问题：重新组织当前渠道版本；
- 与源稿相似度偏高：改变信息顺序、开头、结构和表达框架；
- 机械预警：针对具体套话、句长或段落命中修订；
- 派生产物失败：保留已审查正文，重试当前渠道所需的格式、HTML 或封面步骤。

当前 Rewrite 最多两轮完整重写。每轮更新 review 文件并保留版本差异；失败只结束当前 Rewrite，不改动 canonical source 或之前完成的渠道版本。

## Phase 7：必要派生产物

正文通过渠道审查后，读取 YAML 的 `required_derivatives`：

- `wechat`：组合 `baoyu-format-markdown`、`baoyu-markdown-to-html` 与 `baoyu-cover-image`，生成 `formatted.md`、`wechat.html` 和 `cover.png`；
- `x-post`：在 `manual_x_composer_preview` 证据通过后交付 `x-post.md`；
- `x-thread`：每条都取得 `manual_x_composer_preview` 证据后交付 `x-thread.md`。

每个必要派生产物完成后计算 SHA-256，写入 `rewrite-status.json.derivatives_sha256`。必要能力或派生产物失败时，当前 Rewrite 标记为 `failed`，并记录已保留正文、失败步骤和重试入口；不汇总其他任务的成功或失败。视觉和格式只写派生产物，不覆盖渠道正文、`source.md` 或来源任务的 canonical `final.md`。

本阶段不自动发布。发布是用户之后单独触发的动作，不属于 Rewrite 完成条件。

## Phase 8：完整交付

只汇报本次渠道：

- `target_id`；
- canonical source 路径与 `source_sha256`；
- `source-analysis.md` 路径、是否复用及其 hash；
- 渠道正文路径和字数；
- 渠道审查结论；
- 机械检查与源稿相似度预警；
- YAML 要求的派生产物；
- 已知剩余问题。

只有渠道正文、渠道审查和必要派生产物都完成，X 渠道长度证据为 `pass`，且 status 中的 source、analysis、output、review 与 derivative hash 全部匹配当前文件时，`rewrite-status.json.status` 才写为 `completed`。

## 参考文件

- `references/single-target-rewrite.md`
- `references/quality-gates.md`
- `platforms/wechat.yaml`
- `platforms/x-post.yaml`
- `platforms/x-thread.yaml`
