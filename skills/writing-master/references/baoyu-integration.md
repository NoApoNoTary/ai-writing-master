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
available_skills:
  baoyu-url-to-markdown: true
  baoyu-article-illustrator: true
  baoyu-cover-image: true
  baoyu-markdown-to-html: true
selected_routes: []
missing_routes: []
```

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
