# Voice Preset 合同

Voice Preset 是任务级“写作声音”，只控制表达层；它不是身份模仿、人格、作者立场或长期 Style Profile。用户侧称“写作声音”，内部字段为 `voice_id` 与 `voice_profile`。

所选 Persona Skill（内置或外部）与 Voice Preset 是两条独立输入：Persona 决定任务采用的身份、背景、观察和判断方式，Voice 继续只控制表层表达。两者可组合，互不转换、互不写入对方 Snapshot；详见 `persona-skills.md`。

## 内容契约中的选择

Voice 选择属于内容契约，不增加独立等待点。新任务默认：

```yaml
voice_id: natural-default
voice_label: 自然默认
voice_selection_source: default | request | content_contract
```

内容契约摘要必须展示当前选择和以下可用项；用户回复“确认”即接受 `natural-default`，也可回复“修改：写作声音=清晰分析”、稳定 ID 或当前列表序号。用户请求已给出有效选择时直接展示，不重复询问。

| 序号 | `voice_id` | 名称 | 适用场景 |
|---|---|---|---|
| 1 | `natural-default` | 自然默认 | 保持任务内 Style Profile 与既有自然规则，不附加临时覆盖。 |
| 2 | `clear-analytical` | 清晰分析 | 分析、教程；信息密度高、克制、结构清楚。 |
| 3 | `conversational-observer` | 对话观察 | 观察与解释；自然口语、具体观察、柔和转折。 |
| 4 | `sharp-commentary` | 锐利评论 | 评论与观点；判断先行、短句节奏、受控幽默。 |
| 5 | `magazine-dialogue-editor` | 杂志对谈 | 杂志特稿；克制的讲述与追问双声部，不伪装真实采访。 |

未知或不可用的 `voice_id`：展示可用列表并留在“等待契约确认”，不得静默替换为默认项或进入初稿。Registry 在发布前拒绝重复 ID 或显示名称。

## Profile 与 Snapshot

Registry Profile 使用 JSON；每个已发布版本固定包含：

```json
{
  "schema_version": 1,
  "id": "clear-analytical",
  "version": 1,
  "label": "清晰分析",
  "description": "高信息密度、克制、结构清楚。",
  "best_for": ["analysis", "tutorial"],
  "scope": "expression_only",
  "voice": {
    "register": [],
    "sentence_rhythm": [],
    "paragraph_shape": [],
    "pacing": [],
    "opening": [],
    "transitions": [],
    "certainty": [],
    "humor": [],
    "analogy": [],
    "vocabulary": []
  },
  "avoid": [],
  "preserve": [
    "facts",
    "evidence_boundaries",
    "core_thesis",
    "author_position",
    "real_experiences"
  ],
  "examples": []
}
```

`scope` 固定为 `expression_only`；`preserve` 必须是上述完整集合。Profile 只含可观察表达规则和短小合成示例，禁止含真实创作者姓名、原句、身份、经历、价值判断或角色扮演指令。

内容契约确认后、任何初稿前，创建或确认 `{run_dir}/voice-profile-snapshot.json`。Snapshot 至少含任务 ID、选择来源、Profile ID、版本、完整 Profile 与 Profile hash。相同任务、相同 `voice_id` 的重试幂等；`voice_snapshot=ready` 后改用其他 `voice_id` 不覆盖既有 Snapshot，应新建 Writing run，新 run 的 `source_task_id` 指向原 `task_id`、`contract` 从 `pending` 重新确认。后续 Registry 更新、删除或排序变化不影响已冻结任务。

新 run 的顺序固定为：保留原 run 的关联字段与 Voice Snapshot → 创建新 `task_id` 并写入 `source_task_id`、`source_change_kind: voice` 与变更摘要 hash → 将新 run 的 `contract` 设为 `pending` → 用户确认后再写入新 Voice Snapshot。不得先改写原 run。

## 阶段读取边界

- Phase 1 Research 与 Phase 2 Editorial 不读取 Voice Snapshot、不回读全局 Registry；事实选择、核心判断和论证结构保持声音无关。
- Quick / Standard 只在 Phase 3 Writer 与 Voice Audit 读取任务 `voice-profile-snapshot.json`。
- Deep 仅 Writer 与 Auditor 的 Manifest `allowed_inputs` 可列 `voice-profile-snapshot.json`，并带该文件的 `sha256`；Researcher 与 Editorial Strategist 的 Manifest 不得列该文件或其 hash。
- 任何阶段只使用任务 Snapshot，绝不以全局 Registry 替代它。Snapshot 校验失败时，Phase 3、审校、验收和发布停止。

## Writer 与 Voice Audit

Writer 只把 Voice 用于词汇、句式、节奏、段落形态、开场、转折、确定性、幽默和类比。当存在 Persona 与这些表达维度重叠时，`natural-default` 可采用 Persona 建议，显式非默认 Voice 以 Voice Snapshot 为准。优先级从高到低：事实与证据边界、已确认 Brief/核心判断/真实经历、Channel Contract、Voice Snapshot、不冲突的 Personal Context Style、通用默认规则。Voice 不得新增人物、事件、数字、引述、测试结果、感官细节或第一人称事实。

Voice Audit 使用 Writer 的同一份 Snapshot。每条 `layer: voice` issue 必须包含正文精确位置、命中的 Profile 字段或规则、原句/可观察证据和不改变事实或核心判断的 `required_change`；“像 AI”“不像某人”或百分比不是证据。

```yaml
- issue_id: VOICE-001
  severity: major
  layer: voice
  location: "第 2 节，第 3 段，第 2 句"
  problem: "开场未建立 Profile 要求的具体观察。"
  evidence:
    profile_rule: "voice.opening[0]: 从具体对象或场景进入"
    excerpt: "这几年，工具变化非常快。"
  required_change: "改为当前材料中已有的具体对象开场；保留 claim-003 的条件边界，不新增经历。"
```

Audit 同时检查声明特征缺失、`avoid` 命中、随机口头禅、伪细节，以及追求声音是否破坏证据或编辑合同。Evidence/Editorial 合同冲突时，Voice 不得要求牺牲事实、边界或观点。

## 摘要、恢复与失败语义

用户摘要追加：

```text
voice: {label}
voice_snapshot: ready | legacy | unavailable
```

- `ready`：任务 Snapshot 已冻结且校验通过。
- `legacy`：v0.3 前的任务缺少 Snapshot，内部语义为 `legacy-natural`；继续既有行为，不补写新 Profile。
- `unavailable`：默认 `natural-default` 的 Profile 或 Snapshot 运行异常；记录状态并继续既有自然写作，不声称已应用 Voice。

显式选择非默认 Voice 时，Profile 不存在、无效或 Snapshot 创建失败会阻止进入 Phase 3，摘要保留可执行失败原因和可用 Voice 列表。Snapshot 结构、任务 ID 或 hash 校验失败时，不自动切换到当前 Registry，也不降级为默认；停止生成、审校、验收和发布。Voice Audit 的未关闭问题不抹去已完成的 Evidence Audit，但结果不得标记为完全通过。

`status.json` 至少记录 `voice_id`、Profile 版本、Snapshot 状态和 Snapshot hash；用户摘要不展示 Registry 路径或内部 hash。

## Personal Context 与学习隔离

Voice Snapshot 不写入 `personal-context-snapshot.json`；Voice Profile 不创建 Style Observation，也不参与 Style Profile 重建。使用非默认 Voice 的任务不是确认式风格学习的 baseline 或 evidence；用户请求学习时只说明该任务的 Voice 驱动表达不进入 v0.3 的长期 Style 学习。

## Rewrite

Writing Rewrite 只从已验收 canonical `final.md` 或用户 standalone input 读取，保持源稿已验收的声音，仅做目标平台必要适配。Rewrite 不展示、解析或新增 Voice Selector，也不修改来源任务的 canonical final。
