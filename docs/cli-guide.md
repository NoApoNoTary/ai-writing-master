# CLI 工具指南

本文面向需要从 Shell 调用、编写自动化脚本或排查工程状态的用户。普通写作不以 CLI 为入口，请从[用户上手指南](quick-start.md)开始。

AI Writing Master 的 CLI 提供九项确定性辅助能力：机械文本检查、字符相似度、运行目录查询、深度模式角色交接、个人上下文管理、确认式风格学习、Research Brief 校验、任务级 Voice Snapshot 和外部 Persona Skill 冻结。它们不替代事实研究或编辑审查。

## 安装与运行

### 使用仓库启动脚本

```bash
git clone https://github.com/NoApoNoTary/ai-writing-master.git ~/ai-writing-master
cd ~/ai-writing-master
./bin/writing-master --help
```

`bin/writing-master` 会把仓库的 `src/` 加入 `PYTHONPATH`，因此无需先安装 Python 包。

完整仓库还包含两个 Skills、角色卡、参考文件与 `install.sh`；只安装 build wheel 时只得到 Python CLI 包和 `writing-master` 命令，不会安装 Skills、角色卡或用户数据目录。需要完整写作工作流时，从仓库运行 `install.sh`；只需 Runtime CLI 时可安装 wheel。

需要全局命令时，把 `bin` 加入 PATH：

```bash
export PATH="$HOME/ai-writing-master/bin:$PATH"
writing-master --version
```

### 通过安装脚本

```bash
cd ~/ai-writing-master
bash install.sh
```

若本机存在 `uv` 或 `pipx`，安装脚本会执行仓库根目录的可编辑安装；否则 Skills 仍可使用，CLI 可通过 `./bin/writing-master` 运行。

### Python 模块入口

```bash
cd ~/ai-writing-master
PYTHONPATH=./src python3 -m writing_master --help
```

## 命令概览

```bash
writing-master --help
writing-master --version
writing-master quality <file> [--verbose | --json]
writing-master similarity <file> <file> [...] [--json] [-n N]
writing-master home
writing-master handoff prepare RUN_DIR --to-role ROLE --phase PHASE --objective TEXT --decision-to-inform TEXT --input FILE --write FILE --done-criterion TEXT
writing-master handoff start RUN_DIR --agent-ref AGENT_REF
writing-master handoff recover-lost RUN_DIR --agent-ref AGENT_REF
writing-master handoff complete RUN_DIR [--result RESULT_PATH]
writing-master handoff show RUN_DIR [--json]
writing-master context init
writing-master context profile set PROFILE.json --expected-revision N [--json]
writing-master context profile show [--json]
writing-master context material add FILE --kind KIND --title TITLE --source-kind KIND --source-ref REF --visibility VISIBILITY [--tag TAG ...]
writing-master context material list [--kind KIND] [--status STATUS] [--json]
writing-master context search QUERY [--kind KIND] [--tag TAG] [--limit N] [--json]
writing-master context import-legacy SOURCE_DIR [--kind KIND]
writing-master context approve RUN_DIR ITEM_ID --allow background|paraphrase|quote
writing-master context snapshot RUN_DIR --material ITEM_ID:PURPOSE [--material ITEM_ID:PURPOSE ...]
writing-master context verify-run RUN_DIR [--json]
writing-master learn propose CANDIDATE.json --run-dir RUN_DIR [--json]
writing-master learn decide OBSERVATION_ID (--accept | --reject) [--json]
writing-master learn show [--json]
writing-master research save RUN_DIR DRAFT.json [--json]
writing-master research verify RUN_DIR [--json]
writing-master voice list [--json]
writing-master voice snapshot RUN_DIR [VOICE] [--source default|request|content-contract] [--json]
writing-master voice verify-run RUN_DIR [--json]
writing-master persona snapshot RUN_DIR SKILL.md PERSONA_BRIEF.md --mode author|reference --content-type TYPE --background default|project|none [--source-version VERSION] [--json]
writing-master persona verify-run RUN_DIR [--json]
```

## `quality`：机械文本检查

命令名 `quality` 为兼容既有工作流保留。它计算五项可观察的文本特征，并汇总为 `mechanical_score`：

| 检查项 | 权重 | 当前实现 |
|---|---:|---|
| `banned_words` | 30% | 统计内置套话表的命中数量 |
| `sentence_variance` | 20% | 计算句长标准差 |
| `paragraph_rhythm` | 20% | 检查相邻段落长度是否过于接近 |
| `adverb_density` | 15% | 统计内置常见副词密度 |
| `vocabulary_diversity` | 15% | 计算中文字符 bigram 多样性 |

这五项都是启发式规则。分数高只表示机械预警较少，不表示：

- 事实准确；
- 引用充分；
- 观点原创；
- 论证严密；
- 符合特定作者声音；
- 文本来自人类而非模型。

### 基本用法

```bash
writing-master quality article.md
writing-master quality article.md --verbose
writing-master quality article.md --json
```

普通输出包含分数和机械阈值结果。当前阈值为 `60`，只用于工作流预警。

### JSON 字段

```json
{
  "score_type": "mechanical_style",
  "mechanical_score": 72.5,
  "quality_score": 72.5,
  "dimensions": {
    "banned_words": {"score": 0.8, "detail": "..."},
    "sentence_variance": {"score": 0.7, "detail": "..."},
    "paragraph_rhythm": {"score": 0.6, "detail": "..."},
    "adverb_density": {"score": 1.0, "detail": "..."},
    "vocabulary_diversity": {"score": 0.9, "detail": "..."}
  },
  "weights": {
    "banned_words": 0.3,
    "sentence_variance": 0.2,
    "paragraph_rhythm": 0.2,
    "adverb_density": 0.15,
    "vocabulary_diversity": 0.15
  },
  "char_count": 1200,
  "manual_review_required": [
    "factual_accuracy",
    "claim_support",
    "editorial_judgment",
    "voice_fidelity"
  ]
}
```

`quality_score` 与 `mechanical_score` 当前数值相同，仅为旧调用方保留。新集成应读取 `mechanical_score` 和 `score_type`。

### 套话表

当前套话表定义在 [`src/writing_master/commands/quality.py`](../src/writing_master/commands/quality.py)。它包含“综上所述”“值得注意的是”“具有重要意义”等常见模板表达。

命中并不意味着该词在所有语境中都错误；检查结果用于定位候选句，再由编辑判断是否修改。

### 短文本行为

输入少于完整文章的最低样本要求时，JSON 返回 `status: "insufficient_data"`，
`mechanical_score` 与兼容字段 `quality_score` 为 `null`，并列出 `insufficient_reasons`。
命令行输出 `N/A`，不把短标题、提纲或几句话标记为通过。

## `similarity`：字符表面相似度

### 基本用法

```bash
writing-master similarity source.md rewritten.md
writing-master similarity source.md version-a.md version-b.md
writing-master similarity source.md rewritten.md --json
writing-master similarity source.md rewritten.md -n 4
```

有意义的比较至少需要两个文件。多个文件输入时，命令返回所有文本对中的最大相似度。

### 算法

默认算法是字符 `3-gram` Jaccard：

1. 删除标点和空白，保留字母、数字及中日韩字符；
2. 为每个文本生成字符 n-gram 集合；
3. 计算 `|A ∩ B| / |A ∪ B|`；
4. 多文件场景返回最大值。

### JSON 输出

```json
{
  "max_similarity": 0.42,
  "threshold": 0.6,
  "pass": true
}
```

`0.6` 是当前工作流的固定预警线。它没有考虑语义改写、引用规范、公共事实、版权边界或跨语言翻译，因此只适合回答“字符表面重合是否偏高”。

## `home`：运行数据目录

```bash
writing-master home
```

默认返回当前用户的 `~/.writing-master`。设置环境变量后返回指定路径：

```bash
export WRITING_MASTER_HOME="$HOME/content-system"
writing-master home
```

`home` 只输出路径，不创建任务、不读取状态，也不执行写作流程。

## `context`：个人上下文

`context` 管理版本化 Author Profile、五类 Knowledge Item、任务级 approval 与不可变任务 Snapshot。所有运行时 JSON 由 Python 标准库维护；初始化、导入、Snapshot、usage 和 verify 都是显式动作。它不扫描或自动导入旧 `personal_materials/`；风格决定与 Research Brief 分别由 `learn` 和 `research` 管理。

```bash
# 初始化 Profile、Style 与 Knowledge Index 的 canonical 空状态
writing-master context init

# Profile 以 optimistic revision 更新
writing-master context profile set profile.json --expected-revision 0 --json
writing-master context profile show --json

# 导入、查询和控制素材生命周期
writing-master context material add experience.md \
  --kind experiences --title '一次可追溯经历' \
  --source-kind user_provided --source-ref 'local://experience-001' \
  --visibility ask_before_use --tag example --json
writing-master context search '可追溯' --json
writing-master context material disable ITEM_ID
writing-master context material enable ITEM_ID
```

素材 kind 是 `experiences`、`opinions`、`cases`、`references`、`previous_articles`。重复导入只在同一 `(kind, normalized_content_hash, source_kind)` 身份内幂等；相同正文以不同 kind 或 source identity 导入时保留为独立 item。

```bash
# legacy 导入仍是显式操作；每个文件独立报告 imported/skipped/failed
writing-master context import-legacy personal_materials

# ask_before_use 需要当前任务 approval，之后才能进入 Snapshot
writing-master context approve RUN_DIR ITEM_ID --allow background
writing-master context snapshot RUN_DIR --material ITEM_ID:background

# final.md 与 acceptance-report.md 存在后，由 Runtime 记录 usage 并核验整条链路
writing-master context verify-run RUN_DIR --json
```

`publishable` 可直接进入新 Snapshot；`ask_before_use` 需要对应任务、item 和用途的 approval；`private` 永远不会进入写作 Snapshot。Snapshot 写入后保持不可变，任务只读取 Snapshot 和任务内 `context-materials/` 副本；`verify-run` 检查明确记录的 hash、approval、usage 及 final/acceptance 文件，不宣称对正文作语义性隐私审计。

## `learn`：确认式风格学习

`learn` 保存可追溯的 Style Observation Candidate，并要求用户显式接受或拒绝。Runtime 不从一次编辑自动修改 Style，也不对规则语义作判断。

```bash
writing-master learn propose style-candidate.json --run-dir RUN_DIR --json
writing-master learn decide OBSERVATION_ID --accept --json
writing-master learn decide OBSERVATION_ID --reject --json
writing-master learn show --json
```

Candidate 记录：

- 来源任务；
- baseline/edited 文件路径与 SHA-256；
- before/after 片段或 diff 引用；
- `expression | sentence | structure | stance | platform` 规则维度；
- global/platform/content type/topic 适用范围；
- proposal model 与 prompt。

`propose` 只创建 `proposed` observation。终态为 `accepted` 或 `rejected`；重复相同决定幂等，相反决定返回 revision conflict。Style Profile 只由 accepted observations 确定性重建，每条规则保留 observation ID/revision/hash 引用。全局 Style 更新只影响之后创建的新 Snapshot，既有任务不变化。`--run-dir RUN_DIR` 必须绑定来源任务并执行 Voice 隔离校验；非默认 Voice 任务的表达变化不进入 Style Observation。

完整 Candidate schema 见 [`Goal B Contract`](goals/2026-07-28-v0.2b-goal-contract.md)。

## `voice`：任务级写作声音

```bash
writing-master voice list --json
writing-master voice snapshot RUN_DIR
writing-master voice snapshot RUN_DIR clear-analytical --source content-contract --json
writing-master voice snapshot RUN_DIR 清晰分析 --json
writing-master voice verify-run RUN_DIR --json
```

`list` 返回稳定 ID、版本、显示名称、说明和适用场景。`snapshot` 接受序号、ID 或显示名称；省略时使用 `natural-default`。同一任务、同一 Voice 重试幂等，不同 Voice 返回 `snapshot_conflict` 且保留原文件。

任务 Snapshot 保存任务 ID、选择来源、Profile ID/版本、Profile hash、完整 Profile 与 Snapshot hash，并同步更新 `status.json` 的 `voice_id`、`voice_profile_version`、`voice_snapshot` 和 `voice_snapshot_sha256`。新任务在调用 `snapshot` 前由工作流写入 `voice_snapshot: pending`；缺少全部 Voice 字段的旧任务会标记为 `legacy-natural`，不回填新 Profile。`verify-run` 只读任务文件校验完整性，不依赖当前 Registry。显式非默认 Voice 加载失败会阻止进入初稿；自然默认 Registry 异常会标记 `unavailable` 并保留既有自然写作行为。

当前内置五项：`natural-default`、`clear-analytical`、`conversational-observer`、`sharp-commentary`、`magazine-dialogue-editor`。Profile 只约束表达维度，不得改变事实、证据边界、核心判断、作者立场或真实经历。

## `persona`：任务级外部作者人格

```bash
writing-master persona snapshot RUN_DIR /path/to/PERSONA/SKILL.md persona-brief-draft.md \
  --mode author --content-type analysis --background project --json
writing-master persona verify-run RUN_DIR --json
```

`snapshot` 原样保存外部 `SKILL.md` 为任务内 `persona-skill.md`，并在自由格式 Brief 前追加最小来源注释后保存为 `persona-brief.md`。来源版本优先读取原 Skill frontmatter 的 `version`，且 `--source-version` 不得覆盖它；Skill 没有版本时可显式提供外部版本，再缺失时使用完整内容 SHA-256。无论版本来自哪里，状态始终另存原始 Skill hash、Brief hash 和使用模式，不建立固定 Persona Schema。

同一任务、同一来源输入与 Brief 重试幂等；外部文件之后变化不会覆盖任务副本。不同人格、`author/reference` 模式、文章类型、背景选项或 Brief 返回 `snapshot_conflict`。`verify-run` 只校验任务内两份文件和 `status.json`，不回读外部路径、不扫描 Skill 目录。

## `research`：上下文感知选题 Brief

`research` 不执行网络调研。Researcher 或当前 Agent 先基于实时来源生成 `research-brief-draft.json`，Runtime 再把它绑定到既有任务的 `brief.md` 与 `personal-context-snapshot.json`：

```bash
writing-master research save RUN_DIR research-brief-draft.json --json
writing-master research verify RUN_DIR --json
```

有效 draft 包含 3–10 个候选，每个候选具备 Topic、Heat、Audience、Angle、Evidence、`heat/user_value/differentiation/author_fit` 四维评分及 Rationale。Runtime 校验：

- 分数范围和 Heat 一致性；
- 非未来 RFC3339 时间；
- Evidence URL、内容 hash 和稳定 ID；
- `author_fit` 只引用冻结 Snapshot 的 Profile revision/hash 或已选 Material ID；
- canonical Brief 与原始 `brief.md`、Snapshot 的输入 hash。

相同保存幂等；同一任务的不同第二次保存返回 duplicate。`verify` 会发现 Brief、Snapshot 或 canonical 文件变化。Research Brief Evidence 只支持候选排序，不自动成为文章 `claims.yaml` 中的 accepted claim。缺少实时检索能力时，Host 在生成 draft 前报告 `realtime_research_unavailable`。

Draft schema 与 Agent 边界见 [`Research Brief reference`](../skills/writing-master/references/research-brief.md)。

## `handoff`：深度模式角色交接

`handoff` 只处理已建立且 `status.json` 为 `mode=deep`、`execution=multi_agent` 的运行目录。它创建不可变 Manifest、校验专项 Agent Result 并显示输入新鲜度；路径、hash、stale 和 attempt 历史由 Runtime 复核。

```bash
writing-master handoff prepare RUN_DIR \
  --to-role researcher \
  --phase research \
  --objective '建立证据包' \
  --decision-to-inform '后续角度选择' \
  --input brief.md \
  --write claims.yaml \
  --done-criterion '关键主张可追溯'

writing-master handoff start RUN_DIR --agent-ref AGENT_REF
# 仅当宿主确认该 Agent 已丢失时：
writing-master handoff recover-lost RUN_DIR --agent-ref AGENT_REF
writing-master handoff complete RUN_DIR
writing-master handoff show RUN_DIR --json
```

`prepare` 输出 Manifest 路径；`start` 在创建 Agent 前持久化 `agent_ref`；`recover-lost` 只处理宿主已确认丢失的同一 Agent；`complete` 在 Result 和已暂存输出都通过校验后推进状态；`show` 显示当前 handoff、输入新鲜度和阻断原因。它不是“继续最近任务”命令，也不为 quick/standard 提供通用恢复。当前运行目录锚定与锁定属于 Linux staging 边界。

## 在自动化中使用

### 机械检查

```bash
result=$(writing-master quality final.md --json)
score=$(printf '%s' "$result" | jq -r '.mechanical_score')
printf 'mechanical score: %s\n' "$score"
```

脚本门禁后仍应保留独立编辑审查：

```text
机械检查
  → 证据审查
  → 编辑判断
  → 声音审查
  → 验收
```

### 改写重合预警

```bash
writing-master similarity source.md rewritten.md --json \
  | jq '{max_similarity, threshold, pass}'
```

不要根据 `pass` 字段自动声明原创或直接发布。

## 故障排查

### `command not found: writing-master`

```bash
cd ~/ai-writing-master
./bin/writing-master --help
```

确认可运行后再把目录加入 PATH：

```bash
echo 'export PATH="$HOME/ai-writing-master/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### `No module named writing_master`

从仓库根目录调用启动脚本，或显式设置：

```bash
cd ~/ai-writing-master
PYTHONPATH=./src python3 -m writing_master --help
```

### 文件读取错误

命令按 UTF-8 读取输入。先检查路径、文件权限和编码：

```bash
file article.md
test -r article.md && echo readable
```

### 分数与编辑判断不一致

优先相信针对事实、证据、论证和作者声音的具体审校证据。机械分数只用于发现规则能够观察到的问题。

## 相关文件

- [README](../README.md)
- [用户上手指南](quick-start.md)
- [`quality.py`](../src/writing_master/commands/quality.py)
- [`similarity.py`](../src/writing_master/commands/similarity.py)
