# 改写质量门槛

改写使用多类独立门槛，不把单个分数当作总质量结论。

## 0. 来源与单目标准入门槛

- `accepted_final` 必须同时具备同一任务的 `final.md`、`sources.yaml`、`claims.yaml` 与内容验收通过的 `acceptance-report.md`。
- `standalone_input` 只限用户直接提供的文件或完整正文；它是本次改写的独立 canonical source。
- Writing Master 的未验收 `draft-v1.md`、`draft-v2.md` 或未通过验收的 `final.md` 不得进入 Rewrite，也不得作为视觉、格式或发布来源。
- 准入后记录 `source_sha256`；后续检查、返工和交付都不得改写 canonical source。
- 一个 run 只记录一个 `target_id`；第二个渠道使用新的 Rewrite run。
- 复用 `source-analysis.md` 前必须同时校验其中的 source hash、支持产物 hash 与前一 run 记录的 analysis hash。

## 1. 事实、立场与声音门槛

- 关键事实和数字与源稿一致。
- 原有限定条件、反例和不确定性得到保留。
- 作者立场保持一致，表达方式可以变化。
- 没有新增来源不明的个人经历、测试结果或数据。
- Rewrite 不重新选择 Voice，也不以渠道刻板话术覆盖 source 的已验收声音。
- `accepted_final` 的 `voice_snapshot=ready` 时，source analysis 必须绑定同一任务的冻结 Voice Snapshot hash。

该门槛由编辑审查完成。

## 2. 渠道适配门槛

- 字数、结构和输出格式符合当前 `target_id` 的 YAML。
- 开头、段落节奏、互动方式适应该渠道。
- 渠道元素服务于正文，不是固定 emoji、口号和标签的堆叠。
- 内容在该渠道仍给读者明确价值或判断。
- X 单帖只有一条；X Thread 每条都按合同的 `length_validator` 独立校验；微信正文保留完整论证。

该门槛由渠道 Reviewer 完成。

## 3. 机械检查门槛

```bash
writing-master quality <rewrite_output_filename> --json
writing-master similarity source.md <rewrite_output_filename> --json
```

- `quality` 只报告套话、句长、段落、副词和词汇等机械特征。
- 输入样本不足时，`quality` 返回 `status: insufficient_data`，不参与通过/返工判定。
- `similarity` 只报告 canonical source 与当前渠道正文的字符 n-gram 重合度，默认阈值为 `0.6`。
- 两个命令都属于预警工具，编辑审查仍然拥有最终判断。
- 不执行渠道成品之间的相似度比较。

## 4. 完整交付门槛

- 渠道正文和 `<target_id>-review.json` 已完成。
- Review 内记录的 source、analysis 与 output hash 均匹配当前文件，status 记录当前 `review_sha256`。
- YAML `required_derivatives` 中的每个产物均已生成并记录路径。
- status 的 `derivatives_sha256` 覆盖每个必要派生产物并匹配当前文件。
- `wechat` 交付包含格式化 Markdown、公众号 HTML 和封面；`x-post` 与 `x-thread` 交付各自完整正文。
- Rewrite、视觉和格式只写渠道产物，不覆盖 `source.md` 或来源任务的 canonical `final.md`。
- 必要派生产物失败时，当前 Rewrite 结束为 `failed`，保留已完成文件和重试入口；原稿与之前完成的 Rewrite 保持不变。

## 定向返工

- 事实失败：回到事实、立场与声音检查。
- 渠道失败：只重写当前渠道版本。
- 与源稿相似度偏高：重构信息顺序、开头和表达框架。
- 机械预警较多：根据具体命中位置定向修订。
- 派生产物失败：只重试当前渠道对应的格式、HTML 或封面步骤。

当前 Rewrite 最多执行两轮完整重写；之后保留证据最充分、渠道适配最好的正文并记录剩余问题。只有正文、审查和必要派生产物全部完成，且所有绑定 hash 匹配时才标记 `completed`。
