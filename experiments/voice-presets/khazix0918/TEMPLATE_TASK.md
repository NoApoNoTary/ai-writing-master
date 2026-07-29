# Khazix0918 Article-only Voice Profile — Template Task

> 执行归属：**模板 Session**——只负责 Khazix Voice Profile 的提炼、验证与交付
> 不负责：Voice Preset Runtime、选择器、Snapshot、工作流接入或旧稿 Pilot
> 目标：使用 Nuwa 的表达 DNA 方法，从 `@Khazix0918` 的 X 长文章中生成一个可供 Voice Preset Pilot 使用的实验 Profile
> 输出目录：本文件所在目录
> 主线等待条件：`READY` 与 `voice-profile.json` 同时存在

## 1. 任务结论

这不是完整人物 Persona，也不是把 Nuwa 生成的整套人物 Skill 接入 AI Writing Master。

只提炼**长文表达层**：句式、段落、节奏、开场、转场、确定性、幽默、类比、词汇、格式习惯、禁用表达和收束方式。输出必须符合 Voice Preset PRD 的 `expression_only` Profile Contract。

## 2. 固定输入与版本

### Project Contract

- 必读：`docs/proposals/2026-07-28-voice-preset-v0.3-prd.md` 的 FR-4、FR-15、Testing Decisions。
- 本任务只负责模板产物，不修改 PRD、Runtime 或 Pilot 旧稿。

### Nuwa

- Repository：`https://github.com/alchaincyf/nuwa-skill`
- 本任务基线 commit：`27642f5bfed2dc1bbf8ee59a2c1ee602a626bbd7`
- 必读：`SKILL.md`、`references/extraction-framework.md`、`references/fidelity-scorecard.md`
- 不使用完整 `skill-template.md` 输出人物 Skill；只参考它来确认哪些 Persona 字段需要剔除。

### 目标作者

- X Profile：`https://x.com/Khazix0918`
- 只接受：`https://x.com/Khazix0918/article/...`
- 明确排除：`/status/`、回复、转发、引用帖、评论区、个人简介、日常短动态、文章推广短帖。

### Post-hoc Benchmark

- Repository：`https://github.com/KKKKhazix/khazix-skills`
- 本任务基线 commit：`1668c2c929caa2e9f510ade061b5d11f55a1a6b8`
- Benchmark 目录：`khazix-writer/`
- **在 `voice-profile-blind.json` 写入并计算 hash 之前不得读取此目录。**

这是作者本人公开的写作 Skill，适合作为盲测后的高质量基准；提前读取会污染 Nuwa 提炼实验。

## 3. Nuwa 裁剪规则

执行 Nuwa 的下列部分：

1. 一手长文章采集与来源登记；
2. 调研 Review 检查点；
3. `Phase 2.3 表达 DNA 分析`；
4. `extraction-framework.md` 的句式指纹、风格标签、禁忌词和口癖；
5. `Phase 4.3 Voice Check`；
6. Fidelity Scorecard 中与风格辨识度、来源透明度有关的部分。

跳过：

- 六维人物全量调研与六 Agent swarm；
- 心智模型、决策启发式、价值观、反模式立场；
- 身份卡、人物时间线、最新动态、智识谱系；
- “某人会怎么看”的推断；
- 角色扮演规则和以作者身份自称；
- 日常社交媒体碎片表达。

本任务是单维度快速实验，不需要执行 Nuwa 的完整标准档。

## 4. Corpus 合同

### Seed Articles

以下链接是发现入口，不代表可以跳过正文校验：

#### Training

1. `https://x.com/Khazix0918/article/2033750706910597627`
2. `https://x.com/Khazix0918/article/2039904593396879494`
3. `https://x.com/Khazix0918/article/2068927263035506977`
4. `https://x.com/Khazix0918/article/2059857381841158252`
5. `https://x.com/Khazix0918/article/2029399057941315761`
6. `https://x.com/Khazix0918/article/2012387342657450349`
7. `https://x.com/Khazix0918/article/2013812311388229792`
8. `https://x.com/Khazix0918/article/2069672408781594723`

#### Holdout — Blind Profile 冻结前不得用于规则提炼

1. `https://x.com/Khazix0918/article/2079067830755147898`
2. `https://x.com/Khazix0918/article/2031579241062740206`
3. `https://x.com/Khazix0918/article/2064546404559999014`
4. `https://x.com/Khazix0918/article/2041835036413149323`

### Inclusion Rules

- 页面作者必须是 `@Khazix0918`。
- 必须取得完整 Article 正文；搜索摘要、推广动态或截断页面不算可用来源。
- Holdout 可以预先下载、校验并封存，但 Blind Extraction 阶段不得分析其正文或用它修正规则。
- Training 至少 8 篇完整长文，Holdout 至少 3 篇完整长文。
- Corpus 应覆盖多种长文原型，避免全部是同一种产品发布或工具教程。
- 每篇登记标题、URL、发布日期、正文字符数、清洗后 SHA-256、用途 `training | holdout` 和提取方法。
- 正文只用于本地分析；项目产物不复制整篇来源文本，只保留必要的短证据、统计和 hash。

### Stop Condition

如果无法取得至少 8 篇 Training 和 3 篇 Holdout 的完整正文：

1. 写出 `template-report.md`，状态为 `CORPUS_INSUFFICIENT`；
2. 列出可用、失败和截断链接；
3. 不生成 `READY`；
4. 不用普通 X 动态补数量。

## 5. Blind Extraction

只读取 Training Corpus，至少完成以下统计或观察：

- 平均句长及长短句分布；
- 疑问句比例；
- 第一人称使用率；
- 确定性与保留语气比例；
- 转折词和口语打断频率；
- 段落长度中位数、单句成段比例；
- 标题、列表、加粗、代码块和引用的使用方式；
- 开头模式、信息推进方式和结尾回扣方式；
- 类比、案例、幽默和读者直呼的使用边界；
- 高频表达、稀有表达、禁用套话和标点偏好。

每条 Profile 规则必须满足至少一种证据：

1. 在多个 Training Article 中复现；
2. 有可量化统计支持；
3. 有多个短证据片段支持。

单篇偶然现象不得写成稳定规则。口癖只能低剂量记录，不能变成模仿秀。

## 6. Profile Output

先生成并冻结：

- `voice-profile-blind.json`

Profile 必须符合主 PRD 的 JSON Contract，额外要求：

- `id`: `khazix0918-article-experimental`
- `label`: `科技观察长文（实验）`
- `scope`: `expression_only`
- `preserve` 必须严格等于：`facts`、`evidence_boundaries`、`core_thesis`、`author_position`、`real_experiences`
- 不包含作者身份、经历、价值观或“亲自做过”的虚构要求。
- “第一人称真实经历”只能作为已有材料的表达方式，Profile 无权要求补写经历。
- `examples` 使用合成示例，不复制原文句子。

写入 Blind Profile 后立即记录 SHA-256；从这一步开始视为冻结，不再静默修改。

## 7. Holdout Validation

Blind Profile 冻结后才读取 Holdout Corpus：

1. 检查 Profile 能否解释 Holdout 的句式、段落、开场、节奏和收束；
2. 记录规则的 true positive、false positive 和明显遗漏；
3. 不因为单篇 Holdout 例外就重写整个 Profile；
4. 使用一个与 Corpus 无关的中性 AI 主题生成 300–500 字 Voice Check；
5. 检查结果不是通用 AI 文、不是原句拼接、没有虚构个人经历。

## 8. Official Skill Benchmark

完成 Blind + Holdout 后，才读取 pinned `khazix-writer`：

- 对照它公开声明的节奏、结构、词汇、禁区和自检规则；
- 标记 Nuwa Blind Profile 的命中、漏项、误判和过拟合；
- 不把官方 Skill 中缺乏 Article Corpus 支持的规则直接复制进 Profile；
- 只有同时得到 Article Corpus 和官方 Skill 支持的修正，才进入最终 `voice-profile.json`；
- `voice-profile-blind.json` 保持不变，用于评估 Nuwa 的真实提炼质量。

## 9. Required Outputs

完成时必须存在：

1. `corpus-manifest.json`：Training/Holdout 清单、hash、字数和提取状态；
2. `voice-profile-blind.json`：读取官方 Skill 前冻结的 Nuwa 结果；
3. `voice-profile.json`：可供主线 Pilot 使用的最终 Profile；
4. `template-report.md`：提炼证据、Holdout 结果、官方 Skill 对照、已知局限；
5. `READY`：最后创建，至少记录最终 Profile SHA-256、Nuwa commit、benchmark commit 和完成时间。

不得修改：

- 主 PRD；
- Writing Master Runtime；
- `/home/amose/.writing-master/runs/20260728-001/final.md`；
- 项目内其他 Voice Profile。

## 10. Done Criteria

- Training ≥ 8，Holdout ≥ 3，全部为完整 X Article 正文；
- 普通 X 动态数量为 0；
- Blind Profile 在读取官方 Skill 前已冻结并记录 hash；
- Profile schema、固定 `preserve` 和 JSON 解析通过；
- Holdout 验证完成；
- 官方 Skill benchmark 完成；
- `template-report.md` 明确写出局限和不确定规则；
- 最终才创建 `READY`。
