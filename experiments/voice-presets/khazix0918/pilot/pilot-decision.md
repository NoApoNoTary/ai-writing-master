# Pilot 决定：promote

## 判定

**promote**：将 `khazix0918-article-experimental` v2 和本次 Pilot 方法推进到 **candidate-registry review**。

这不是对外发布，也不把真实账号名作为用户侧产品名称。候选项仍应使用 Profile 当前的描述性标签“科技观察长文（实验）”。

## 依据

1. `READY`、Profile schema、固定 `preserve`、Profile / Blind / Manifest / Template Report hash 与 Corpus gate 均通过；详见 `validation-report.json`。
2. Pilot 基线副本和原 canonical `final.md` 均匹配固定 SHA-256 `0601c5a1fd9e78416a28032ca65b46518efac5f0debe0c82a7c1b4c0afe26b7d`。
3. Evidence Regression 通过：15 个引用标记和 5 项来源保留，未新增事实、产品主张、个人经历或证据强度。
4. Editorial Regression 通过：核心判断、论证顺序、三条风险边界、适用人群与行动建议保持不变。
5. Voice Audit 通过：变化能定位到 R01/R03/R04/R06/R08/R09/R10/R11/R12/R13/R14/R15/R16/R25；没有命中会要求牺牲内容合同的 Voice issue。
6. 机械检查为 90.79/100，高于 60 门槛且无套话命中。段落节奏项较基线低，是短段落策略与启发式评分的可解释张力，不是内容回归失败。

## 已知限制

- 这是单篇旧稿的闭环验证，不证明该 Profile 对所有主题、平台或作者材料都同样有效。
- 表格、步骤列表和代码闭环被保留，因为它们承载原稿的比较与行动信息；Profile 不能用“少列表”删掉内容结构。
- 发布级验收仍需要 PRD 所列固定内容包 benchmark：自然默认与三个非默认 Profile 的人工对比，并确认至少五个声明维度可辨识。

## 下一步

把该 Profile 纳入候选 Registry 后，执行固定 Brief 的多 Profile 人工 benchmark；若其中任何版本改变 accepted claims、作者立场或真实经历，撤回候选晋级。
