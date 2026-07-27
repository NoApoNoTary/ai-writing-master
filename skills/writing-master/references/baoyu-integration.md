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
available_skills:
  baoyu-url-to-markdown: true
  baoyu-article-illustrator: true
  baoyu-cover-image: true
  baoyu-markdown-to-html: true
selected_routes: []
missing_routes: []
```

预检只确认“这次可能用到什么、当前有哪些能力、需要哪些输入”，不触发图像生成、排版或发布。

## 四级路由

### Level 1：Preflight + Material Intake（开题阶段）

在模式选择完成、建立 Brief 时执行。

1. 识别平台、内容类型、来源展示策略、视觉需求和发布意图。
2. 列出用户已经提供的 URL、YouTube、Markdown、图片、文档和历史文章。
3. 对需要提取的素材立即选择读取路由；提取结果进入研究目录，而不是直接拼进正文。
4. 对图片、GIF、视频和图表只登记来源、文件位置与用途候选。
5. 记录后续 production 可能使用的 Skill，不提前执行。

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

### Level 3：Production（正文结构稳定后）

满足 Writing Master 的视觉闸门后按需执行：

| 任务 | Baoyu Skill | 主要输入 |
|---|---|---|
| 分析文章并生成正文配图 | `baoyu-article-illustrator` | `final.md`、`storyboard.md`、视觉约束 |
| 生成文章封面 | `baoyu-cover-image` | 最终标题、摘要、平台比例、品牌约束 |
| 生成高密度信息图 | `baoyu-infographic` | 已核验的数据、结构化内容、引用要求 |
| 已有明确提示词的单图生成 | `baoyu-image-gen` | 保存后的 prompt、比例、参考图 |
| 只整理 Markdown 层级与排版 | `baoyu-format-markdown` | `final.md` |
| 转换公众号兼容 HTML | `baoyu-markdown-to-html` | 最终 Markdown、主题、外链策略 |

Production 约束：

- 只生产 storyboard 中已批准且仍缺素材的视觉位。
- 数据图和信息图只使用 `claims.yaml` 中已核验的数据。
- 保留 Baoyu 生成的 prompt 文件和输出路径，以便复现。
- 生成结果回写 `asset-manifest.yaml`，记录 `asset_id`、生成方式、身份和最终用途。
- 视觉结果变化不反向改写文章事实；出现冲突时回到证据层处理。

### Level 4：Publish（验收之后）

| 任务 | Baoyu Skill |
|---|---|
| 创建微信公众号草稿或发布 | `baoyu-post-to-wechat` |
| 创建普通 X 帖子或 X Article | `baoyu-post-to-x` |

发布顺序：

1. 完成 `final.md`、视觉资产和平台 HTML/Markdown；
2. 检查图片路径、GIF、外链、封面、摘要和移动端预览；
3. 生成 `acceptance-report.md`；
4. 用户发出清晰发布指令后调用对应 Skill；
5. 回写 draft/post ID、时间和结果到运行目录，敏感凭据留在仓库外配置。

“继续”“下一步”“看起来不错”只推进到下一份可审阅产物，不等同于公开发布指令。

## 路由决策摘要

```text
模式选择
  → 开题：能力发现 + 用户素材提取
  → 调研：事实轨 + 素材轨
  → 策划：asset manifest + storyboard
  → 写作与审校
  → 闸门通过：Baoyu 视觉/排版 production
  → 验收通过 + 明确发布指令：Baoyu publish
```

这条规则可以概括为：**早预检、早摄入、晚生成、后发布。**
