# 外部作者人格 Skill 合同

外部作者人格是用户提供的、可保存和复用的原始 `SKILL.md`。Nuwa 产物直接使用该载体；Writing Master 不把它转换为 Voice JSON，也不建立第二套固定 Persona Schema。

## 内容契约中的选择

每次新任务都在同一份内容契约中询问：

```text
本次是否使用外部作者人格？
1. 不使用
2. 让这个人格来写
3. 参考这个人格写
```

- `none` / 不使用：保持现有流程，不创建 Persona 产物。
- `author` / 让这个人格来写：可采用人格的背景、判断、表达和第一人称叙事。
- `reference` / 参考这个人格写：只借用观察方式、判断习惯和写作方式；正文仍以当前作者身份表达。

选择 `author` 或 `reference` 后，读取用户明确提供的 Skill 名称或路径。名称必须能由当前宿主精确解析为一个 `SKILL.md`；路径可以指向该文件或只包含一个 `SKILL.md` 的目录。不要扫描用户目录、猜测最近使用项、导入 Registry、调用推荐引擎或联网寻找同名人格。

同一内容契约还选择本次背景：

1. 使用人格 Skill 的默认背景；
2. 使用人格默认背景，并追加用户提供的项目背景；
3. 本次不生成背景。

项目背景只进入当前任务，不写回外部 Persona Skill。

## 任务内产物

确认选择后，把原始 `SKILL.md` 的字节原样保存为 `{run_dir}/persona-skill.md`，不重排 frontmatter、不格式化、不删改正文。然后生成自由格式 `{run_dir}/persona-brief.md`，至少清楚记录：

- `mode`: `author | reference`；
- 原始 Skill 的用户输入、解析后的来源路径、可见版本和 SHA-256；
- 当前文章 `content_type` 与由此形成的角色侧重；
- 本次实际采用的人格背景、观察方式、判断习惯和写作方式；
- 项目补充背景或“本次不生成背景”；
- 可用边界：哪些内容可以借用，哪些仍属于当前作者、任务 Brief 或事实调研；
- 与当前 Voice Preset 的分工。

`persona-brief.md` 不采用固定字段集合或 Persona Schema。它是本次任务的可审阅角色说明，不是新的人格模板。

## 按文章类型调整角色侧重

从 Persona Skill 中选择与本次 `content_type` 有用的部分，而不是整份指令无差别叠加：

| `content_type` | 本次角色侧重 |
|---|---|
| `analysis` | 问题框架、因果判断、证据边界和反例意识 |
| `review` | 评价标准、取舍、使用视角和限制条件 |
| `opinion` | 立场、判断习惯、反方处理和语言力度 |
| `tutorial` | 解释顺序、实践判断、失败信号和验证方式 |
| `story` | 叙事视角、注意力分配、节奏和背景使用 |
| `release` | 信息优先级、受众判断、克制程度和行动指向 |

表格是选择提示，不是 Persona Schema。Skill 中与当前任务无关或与内容契约冲突的部分在 Brief 中标为本次未采用。

## Persona 与 Voice Preset

两者可以组合，职责保持分离：

- Persona：作者身份、背景、观察方式、判断习惯、立场形成方式和写作方法；
- Voice Preset：词汇、句式、节奏、段落、开场、转折、确定性、幽默和类比等表层表达。

冲突优先级：事实与证据边界 → 已确认 Brief 与当前作者要求 → Persona Brief → Channel Contract → Voice Snapshot → 其他风格规则。Voice 不得覆盖 Persona 的身份边界；Persona 也不取代 Voice Registry 或写入 `voice-profile-snapshot.json`。

## 角色读取边界

- Researcher 不读取 `persona-skill.md` 或 `persona-brief.md`；它接收的 `brief.md` 只含 Persona-neutral 的主题、读者、渠道、内容目的和证据要求，不含 Persona 原文、背景、拟采用部分或角色侧重。
- Editorial Strategist、Writer 与 Auditor 读取同一份任务内 `persona-brief.md` 及其精确 SHA-256。
- Writer 在 `author` 模式可使用 Brief 明确采用的构造性第一人称背景；在 `reference` 模式不得把 Persona 的身份、经历、关系或第一人称事件移给当前作者。
- 外部主题事实、数据、引述、真实人物事件和测试结果在两种模式下都进入正常调研，不因写在 Persona Skill 中就成为 accepted claim。
- 角色不回读外部 Persona Skill，也不把原始 `persona-skill.md` 当作角色输入；需要核对原文时由 Lead 读取任务内保存副本，且仍受运行目录边界限制。

## 恢复与完整性

`status.json` 记录 `persona_mode`、`persona_snapshot: none | pending | ready | unavailable`、来源路径、可见版本、原始 Skill SHA-256 和 Persona Brief SHA-256。恢复任务只校验并复用任务内 `persona-skill.md` 与 `persona-brief.md`，不采用外部 Skill 的当前版本；即使外部路径内容已更新，也继续使用原任务版本。不同 Persona、模式、背景选项或项目背景属于内容契约变化，不覆盖既有 Brief。

`content_type` 随内容契约和 Persona Snapshot 在当前 run 内冻结。选题后的推荐组合只调整应用深度；另一文章类型可作为备选建议，采用时新建 Writing run，因此不会改写已冻结的 `persona-brief.md`。

旧任务缺少 Persona 字段时按 `none` 处理。Persona 文件缺失或 hash 不一致时停止依赖 Persona 的策划、写作和审校，不从外部路径重建一个看似相同的版本。

首版不包含固定 Persona Schema、自动学习、Registry 导入、目录扫描、推荐引擎或 Marketplace。
