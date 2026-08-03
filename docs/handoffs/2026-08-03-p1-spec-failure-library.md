# P1 Handoff：轻量 Spec、失败案例库与来源展示

- 日期：2026-08-03
- Worktree：`/home/amose/media/awm-p1-spec-failure-library`
- Branch：`codex/p1-spec-failure-library`
- Base / PR target：`codex/writing-workflow-maintenance`
- 执行模型：Terra

## 目标

把用户确认内容保存成一页式 `spec.md`，建立低上下文成本的失败案例库，并让 `source_display: endnotes` 真正影响正文归因方式。保留现有 `brief.md` 作为 Researcher 的中立投影，避免重型 PRD。

## 必须完成

1. **Run Spec**
   - 内容合同确认时生成 `{run_dir}/spec.md`，作为用户可读、可归档的冻结合同。
   - 至少区分：读者目标、交付物、正文必含、读者可见内容、内部执行约束、Persona/Voice、验收条件、采用的失败案例规则、待确认项。
   - `brief.md` 从 Spec 投影研究需要的信息；内部广告判断、视觉 provider、发布意图等不得混入读者内容。
   - 明确 Spec 的冻结、hash/恢复语义以及合同变更后的新版本行为；P0 负责确认失效闸门，本分支只定义产物和输入边界。
2. **失败案例库**
   - 默认位置：`${WRITING_MASTER_HOME:-~/.writing-master}/failure-cases.jsonl`。
   - 使用标准库；记录最少包含 `id/status/tags/source_run/source_session/symptom/root_cause/guardrail/audit_check`。
   - 状态为 `proposed | active | superseded`；只有 active 进入新任务。
   - 提供最小 CLI/API：登记 proposed、更新状态、列出案例、按标签选择最多 N 条并生成 run 内 `failure-case-snapshot.md`。
   - 读取时只注入选中的 guardrail/audit check，不把完整历史会话交给 Writer/Auditor。
   - 文件更新需避免数据丢失；沿用仓库已有原子写入模式或等价 stdlib 实现。
3. **本次首个案例**
   - 提供合成 fixture，表达 `FC-20260803-001` 的问题：内部广告判断成为文章小标题。
   - 测试不得依赖用户真实 session 文件或真实 home 状态。
4. **来源展示**
   - `source_display=endnotes` 时，正文只在来源身份会改变结论处首次标明“官方/独立来源”；相邻段落避免重复身份标签，其余归尾注。
   - Writer 与 Auditor 都有明确检查规则。
   - 不改变 Evidence 边界或来源可追溯性。
5. **上下文预算**
   - 每次默认选择 3–5 条相关 active case；没有匹配时生成空 snapshot 并继续。
   - 不引入向量库、数据库或新依赖。

## 文件责任

主要负责：

- 新增 `skills/writing-master/references/run-spec.md`。
- 新增 `skills/writing-master/references/failure-cases.md`。
- `skills/writing-master/SKILL.md`：Spec、失败案例 snapshot、产物与可用参考入口；只改 P1 对应小节。
- `skills/writing-master/agents/writer.md`、必要的来源展示审计合同。
- 新增失败案例 runtime/command 与聚焦测试。
- `src/writing_master/cli.py` 仅注册新命令。

共享文件约束：P0 也可能编辑 `SKILL.md`、Auditor 合同和 `tests/test_skill_contracts.py`，只做窄范围 diff，不重排文件；发现重叠时保留双方语义并通知主代理。

## 非目标

- 不实现 P0 的过程泄漏机械规则、标题分类或合同重新确认闸门。
- 不建立完整 PRD 系统、全文语义检索或 embeddings。
- 不扫描/复制 Codex session 历史。
- 不改写既有 run 或用户真实失败案例库。

## 验收

```bash
PYTHONPATH=src python -m unittest tests.test_failure_cases tests.test_skill_contracts -v
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/awm-p1-pyc python -m compileall -q src tests
bash -n install.sh
./bin/writing-master --help
```

提交使用简短 Conventional Commit；完成后推送分支并创建目标为 `codex/writing-workflow-maintenance` 的 PR。PR 描述列出受影响 worktree、行为变化和精确验证命令。
