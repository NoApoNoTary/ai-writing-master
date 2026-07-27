# 改写质量门槛

改写使用多类独立门槛，不把单个分数当作总质量结论。

## 0. 来源准入门槛

- `accepted_writing_master_final` 必须同时具备同一任务的 `final.md` 与内容验收通过的 `acceptance-report.md`。
- `standalone_user_input` 只限用户直接提供的文件或完整正文；它是本次改写的独立 canonical source。
- Writing Master 的未验收 `draft-v1.md`、`draft-v2.md` 或未通过验收的 `final.md` 不得进入 Rewrite，也不得作为视觉、格式或发布来源。
- 准入后记录 source hash；后续检查、返工和交付都不得改写 canonical source。

## 1. 事实与立场门槛

- 关键事实和数字与源稿一致。
- 原有限定条件、反例和不确定性得到保留。
- 作者立场保持一致，表达方式可以变化。
- 没有新增来源不明的个人经历、测试结果或数据。

该门槛由编辑审查完成。

## 2. 平台适配门槛

- 字数、结构和输出格式符合对应平台 YAML。
- 开头、段落节奏、互动方式适应该平台。
- 平台元素服务于正文，不是固定 emoji、口号和标签的堆叠。
- 内容在该平台仍给读者明确价值或判断。

该门槛由平台 Reviewer 完成。

## 3. 机械检查门槛

```bash
writing-master quality <platform>.md --json
writing-master similarity source.md <platform>.md --json
```

- `quality` 只报告套话、句长、段落、副词和词汇等机械特征。
- 输入样本不足时，`quality` 返回 `status: insufficient_data`，不参与通过/返工判定。
- `similarity` 报告字符 n-gram 重合度，默认阈值为 `0.6`。
- 两个命令都属于预警工具，编辑审查仍然拥有最终判断。

## 4. Canonical 完整性门槛

- Rewrite、视觉、格式和发布只读取 canonical source 或已经通过审查的平台版本。
- 它们只写入平台正文、视觉资产、格式化文件、HTML 或发布记录；不覆盖 `source.md` 或来源任务的 canonical `final.md`。
- 任一平台失败只返工该平台，canonical source 和其他平台版本保持不变。

## 定向返工

- 事实失败：回到事实与立场检查。
- 平台失败：只重写该平台版本。
- 相似度偏高：重构信息顺序、开头和表达框架。
- 机械预警较多：根据具体命中位置定向修订。

每个平台最多执行两轮完整重写；之后保留证据最充分、平台适配最好的版本，并记录剩余问题。
