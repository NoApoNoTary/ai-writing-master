# Baoyu 分阶段路由

Baoyu 提供素材提取、视觉生成、Markdown 处理、公众号 HTML 和发布能力。Writing Master 只维护调用时机、输入产物和验收条件，不复制 Baoyu 的实现。

## 能力发现

优先从当前运行时的 Skill 清单按名称发现能力，不把某个安装目录当作唯一事实。路径仅用于排障，常见位置包括：

```text
~/.agents/skills/baoyu-*
~/.claude/skills/baoyu-*
~/.codex/skills/baoyu-*
```

在 `capability-preflight.md` 中记录：

```yaml
requested_capabilities:
  - material_ingestion
  - article_illustration
  - cover
  - wechat_html
handoff_runtime: available | unavailable
visual_execution_mode: null
visual_execution_reason: null
available_skills:
  baoyu-url-to-markdown: true
  baoyu-article-illustrator: true
  baoyu-cover-image: true
  baoyu-markdown-to-html: true
selected_routes: []
missing_routes: []
```

`visual_execution_mode` 在 Phase 0（Level 1 预检）时保持 `null`；只有在用户于 Phase 6 明确回复执行方式后，才由 Writing Master 将其设为 `claude_inline` 或 `gpt_handoff`，并同步写入 `status.json`。Phase 0 阶段不默认任何执行模式，也不假设用户选择。

预检只确认“这次可能用到什么、当前有哪些能力、需要哪些输入”，不触发图像生成、排版或发布。

当用户选择深度模式时，`handoff_runtime` 只记录当前宿主对**真实 Handoff Runtime** 的实际预检结果。该检查属于更早的所选模式就绪闸门；`unavailable` 时使用 `WM-CAP-001` 结束任务，Level 1 的素材提取调用次数为 0，不模拟角色执行，也不把单 Agent 产物称为深度产物。

## 四级路由

### Level 1：Preflight + Material Intake（开题阶段）

只在模式选择完成且所选模式就绪闸门通过后，于建立 Brief 时执行。

1. 识别本次唯一的 `target_id`、内容类型、来源展示策略、视觉需求和发布意图。
2. 列出用户已经提供的 URL、YouTube、Markdown、图片、文档和历史文章。
3. 对需要提取的素材立即选择读取路由；提取结果进入研究目录，而不是直接拼进正文。
4. 对图片、GIF、视频和图表只登记来源、文件位置与用途候选。
5. 记录后续 production 可能使用的 Skill，不提前执行。
6. 按 `evidence-and-assets.md` 在 `capability-preflight.md` 中写入素材接收结果：状态、已接收/已提取/待处理/失败计数、失败重试入口和待确认事项。

素材入口：

| 输入 | 路由 | 产物 |
|---|---|---|
| 普通网页、X 帖子、网页文章 | `baoyu-url-to-markdown` | 清洗后的 Markdown + 原始 URL |
| YouTube 视频、字幕或封面 | `baoyu-youtube-transcript` | transcript、metadata、cover 记录 |
| 已有纯文本或 Markdown | 当前 Agent 读取；只需格式整理时使用 `baoyu-format-markdown` | 规范化文本 |
| 本地图片、GIF、视频、图表 | 当前 Agent 登记到 `asset-manifest.yaml` | 路径、来源、身份、用途候选 |

材料提取不等于事实确认。进入正文前仍要把相关陈述写入 `claims.yaml` 并关联来源。

### Level 2：Planning（证据和方向明确后）

在双轨调研完成、文章角度确定后执行。

输入：

- `claims.yaml`
- `sources.yaml`
- `asset-manifest.yaml`
- `editorial-brief.md`
- `outline.md`

输出：`storyboard.md`，为每个视觉位写明：

```yaml
- slot_id: visual-01
  role: cover | hero | evidence | explanation | decorative
  section: opening
  purpose: "帮助读者理解或证明什么"
  preferred_source: official | primary | third_party | editorial | decorative
  asset_id: null
  generation_route: null
  required: true
```

规划规则：

- 优先级为官方/第一方原始素材 → 一手技术资料 → 独立第三方 → 编辑解释图 → 装饰图。
- Cover 负责识别与情绪；Evidence visual 负责证明；Hero 只有承担新信息时才保留。
- 同一素材只承担一个主要视觉职责。
- `editorial` 视觉明确标识为编辑解释，不使用官方素材口吻。
- 此阶段只锁定视觉任务和路由，保持零生成成本。

### Level 3：Production（canonical final 验收后）

从 Writing Master 任务进入本层时，`source_ref` 必须是 `accepted_final`：同一任务中的 `final.md` 存在，且 `acceptance-report.md` 内容明确验收通过。未验收的 `draft-v1.md`、`draft-v2.md` 或未通过验收的 `final.md` 都不得作为视觉、格式或发布来源。

#### 执行模式识别

进入 Level 3 时先识别用户意图：

进入 Level 3 前，`visual_execution_mode` 必须已由用户在 Phase 6 明确回复，且已写入 `status.json`（值为 `claude_inline` 或 `gpt_handoff`，`visual_execution_selected: true`）。未收到明确回复时不得进入 Level 3 视觉生产。

| 用户表述（Phase 6 回复） | 执行模式 | 行为 |
|---|---|---|
| 回复 1、"Claude 做" 或等效表述 | `claude_inline` | 当前 Agent 调用 Baoyu Skills 完成视觉和发布 |
| "交给 GPT"、"GPT 完成"、"Codex 执行"、"外部配合 Codex" | `gpt_handoff` | 生成交付文档，停在当前会话 |

#### claude_inline 模式

| 任务 | Baoyu Skill | 主要输入 | 输出 |
|---|---|---|---|
| 分析文章并生成正文配图 | `baoyu-article-illustrator` | `final.md`（只读）、`storyboard.md`、视觉约束 | 视觉资产与 manifest 记录 |
| 生成文章封面 | `baoyu-cover-image` | 最终标题、摘要、平台比例、品牌约束 | 封面资产 |
| 生成高密度信息图 | `baoyu-infographic` | 已核验的数据、结构化内容、引用要求 | 信息图资产 |
| 已有明确提示词的单图生成 | `baoyu-image-gen` | 保存后的 prompt、比例、参考图 | 单图资产 |
| 只整理 Markdown 层级与排版 | `baoyu-format-markdown` | `final.md`（只读） | `formatted.md` |
| 转换公众号兼容 HTML | `baoyu-markdown-to-html` | 已验收 Markdown（只读）、主题、外链策略 | `wechat.html` |

图像类视觉生产约束：

- 只生产 storyboard 中已批准且仍缺素材的视觉位。
- 数据图和信息图只使用 `claims.yaml` 中已核验的数据。
- 保留 Baoyu 生成的 prompt 文件和输出路径，以便复现。
- 生成结果回写 `asset-manifest.yaml`，记录 `asset_id`、生成方式、身份和最终用途。
- 视觉结果变化不反向改写文章事实；出现冲突时回到证据层处理。
- 视觉、格式和发布都把 canonical `final.md` 当作不可变输入；写入派生产物、资产清单或发布记录，绝不覆盖或修改它。

Markdown 格式化和 HTML 转换不属于图像类视觉生产：它们在 canonical final 通过内容验收后，读取 `channel-contract.yaml` 的主题和外链策略即可执行；不要求 storyboard、`asset-manifest.yaml` 或图像生成意图。

当 `target_id=wechat` 时，`channel-contract.yaml.required_derivatives` 中的 `formatted.md`、`wechat.html` 与 `cover.png` 属于渠道完整交付；Lead 组合现有 Baoyu 能力完成它们。`x-post` 与 `x-thread` 不因此增加图像或 HTML 产物。

#### gpt_handoff 模式

用户明确要求"交给 GPT"或"Codex 执行"时，生成两份交付文档后停止：

**1. `visual-handoff-for-gpt.md`** — 配图设计规格

从 `storyboard.md` 转写，每个视觉位包含：

```markdown
## 图 {N}：{slot_id}

**视觉角色**：{role}  
**对应文章阶段**：{section}  
**设计意图**：{purpose}  
**内容描述**：{从 final.md 提取该位置的上下文，描述应该呈现什么内容}  
**素材来源要求**：{preferred_source}  
**尺寸要求**：{从 channel-contract 提取}  
**输出路径**：attachments/{slot_id}.png  
**是否必需**：{required}

---
```

**严格限制**：`visual-handoff-for-gpt.md` 只包含上述字段。禁止添加：
- "生成命令参考"或任何 bash 命令示例
- API key、token 或任何凭据（即使是"示例"）
- "Prompt 文件"字段或 prompts/ 路径引用
- "状态"字段或 Visual QA Checklist
- 任何未在模板中定义的额外节

**2. `wechat-publish-spec.md`** — 发布参数清单

从 `final.md`、`channel-contract.yaml` 和 `acceptance-report.md` 提取：

```markdown
## 微信公众号发布规格

### 元数据
- **标题**：{final.md 最终标题}
- **摘要**：{channel-contract 或自动生成}
- **作者**：{channel-contract.author 或 EXTEND.md default_author}
- **封面图片**：attachments/cover.png
- **原文链接**：{channel-contract.content_source_url 如有}

### 正文文件
- **Markdown 源**：final.md（只读，不可修改）
- **HTML 输出**：wechat.html（待生成）

### 视觉资产
{从 storyboard.md 列出所有视觉位及其输出路径}

### 发布配置
- **主题**：{EXTEND.md default_theme 或 default}
- **主题色**：{EXTEND.md default_color 如有}
- **外链处理**：转换为底部引用（默认）
- **评论设置**：
  - need_open_comment: {EXTEND.md 或默认 1}
  - only_fans_can_comment: {EXTEND.md 或默认 0}

### 执行步骤（供 GPT/Codex 参考）

1. 根据 `visual-handoff-for-gpt.md` 使用 `baoyu-image-gen` 或 `codex imagegen` 生成所有图片
2. 使用 `baoyu-markdown-to-html` 转换 final.md → wechat.html（传入主题、主题色）
3. 使用 `baoyu-post-to-wechat` 发布：
   ```bash
   bun {baoyu-post-to-wechat}/scripts/wechat-api.ts wechat.html \
     --theme {theme} \
     --color {color if set} \
     --title "{title}" \
     --summary "{summary}" \
     --author "{author}" \
     --cover attachments/cover.png \
     --source-url "{source_url if set}"
   ```

### 时区与发布窗口
- **账号时区**：{EXTEND.md timezone 或 Asia/Shanghai}
- **推荐发布时间**：待 draft/add 成功后由脚本自动生成

---

**注意**：
- final.md 已通过内容验收，任何阶段都不可修改
- 图片生成失败不影响 HTML 转换和草稿创建
- 草稿创建成功后必须记录 `recommended_publish_time` 到 wechat-draft-report.json
```

生成两份文档后，向用户输出：

```
✓ 已生成 GPT/Codex 交付文档

文档位置：
• {run_dir}/visual-handoff-for-gpt.md — 配图设计规格（{N} 个视觉位）
• {run_dir}/wechat-publish-spec.md — 微信发布参数清单

输入文件（只读）：
• {run_dir}/final.md — 已验收正文
• {run_dir}/storyboard.md — 视觉规划
• {run_dir}/channel-contract.yaml — 渠道约定

后续步骤：
1. 将上述文档交给 GPT 或 Codex
2. GPT/Codex 按照 wechat-publish-spec.md 执行图片生成、HTML 转换和草稿发布
3. 确认微信草稿创建成功并获取推荐发布时间

Writing Master 当前任务已完成交付准备，等待外部执行。
```

不在当前会话执行 `baoyu-image-gen`、`baoyu-markdown-to-html` 或 `baoyu-post-to-wechat`。

### Level 4：Publish（验收之后）

| 任务 | Baoyu Skill |
|---|---|
| 创建微信公众号草稿或发布 | `baoyu-post-to-wechat` |
| 创建普通 X 帖子 | `baoyu-post-to-x` |

发布顺序：

1. 确认来源为 `accepted_final`，再完成视觉资产和平台 HTML/Markdown；
2. 检查图片路径、GIF、外链、封面、摘要和移动端预览；
3. 在已有 `acceptance-report.md` 中追加视觉/排版验收结果，不重新打开内容验收或修改 canonical `final.md`；
4. 用户发出清晰发布指令后调用对应 Skill；
5. 回写 draft/post ID、时间和结果到运行目录，敏感凭据留在仓库外配置。

微信公众号草稿创建或更新成功后，必须先运行确定性的发布时间推荐函数（固定 `now`、账号/任务时区、内容类型、时效性和篇幅作为输入），再写入 `wechat-draft-report.json` 并把同一对象展示给用户。`recommended_publish_time` 必须完整包含：

```json
{
  "window": "YYYY-MM-DD HH:MM–HH:MM",
  "timezone": "Asia/Shanghai / UTC+08:00",
  "reason": "一句简短理由（可核验）",
  "basis_type": "account_history | configured_window | generic_heuristic",
  "basis_detail": "使用了哪些数据；或为什么使用通用估计",
  "confidence": "high | medium | low",
  "backup_window": "YYYY-MM-DD HH:MM–HH:MM"
}
```

Writing Master 收尾必须校验该对象；字段缺失或格式错误时任务不得标记为完整完成。账号历史数据属于后续增强；当前没有可用历史数据时固定使用 `basis_type=generic_heuristic`，在 `basis_detail` 中明确标注回退原因。`publish_intent=draft_only` 或 `prepare` 仍生成建议，但用户未明确请求正式发布或群发时只停在草稿状态，不调用正式发布接口。

用户可见完成报告同步展示账号时区、具体窗口、一句简短理由和数据依据。账号历史接入后优先使用该账号后台历史数据；历史数据不可用时回退到通用经验估计；在当前 P0 中不拉取历史数据。未明确发布指令时不自动执行正式发布。

“继续”“下一步”“看起来不错”只推进到下一份可审阅产物，不等同于公开发布指令。

## 路由决策摘要

```text
模式选择
  → 开题：能力发现 + 用户素材提取
  → 调研：事实轨 + 素材轨
  → 策划：asset manifest + storyboard
  → 写作与审校
  → 内容验收：canonical final
  → 当前渠道必要视觉：Baoyu 视觉 production
  → canonical final + channel contract：Baoyu 排版 / HTML
  → 渠道完整交付
  → 后续明确发布指令：独立 Baoyu publish 动作
```

这条规则可以概括为：**早预检、早摄入、晚生成、后发布。**
