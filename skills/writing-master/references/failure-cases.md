# Failure Cases

失败案例库默认位于 `${WRITING_MASTER_HOME:-~/.writing-master}/failure-cases.jsonl`。仅使用标准库和 JSON Lines；每条记录最少包含：`id`、`status`、`tags`、`source_run`、`source_session`、`symptom`、`root_cause`、`guardrail`、`audit_check`。

## 生命周期

- `proposed`：已登记，尚未进入新任务。
- `active`：可被新任务选择。
- `superseded`：保留追溯，不再选择。

使用 `writing-master failure-cases propose` 登记 proposed 案例，`status CASE_ID active|superseded` 更新状态，`list` 查看案例，`snapshot RUN_DIR --tag TAG --limit N` 生成任务快照。更新以锁和 fsync 后原子替换持久化，避免中断时丢失已有库。

## 任务注入

按当前任务标签从 active 案例中默认选择 3–5 条（上限由 `--limit` 控制），写 `{run_dir}/failure-case-snapshot.md`。没有匹配时也写空 snapshot 并继续。Writer 与 Auditor 只读取 snapshot 中选中条目的 `guardrail` 与 `audit_check`，不读取完整库、来源会话或历史讨论。

## 合成案例 fixture

`FC-20260803-001`：内部广告判断成为文章小标题。其 guardrail 是把广告/内部判断留在执行约束，不作为读者可见标题；audit check 是逐个检查标题是否服务读者问题，且不包含内部决策语言。
