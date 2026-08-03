# P0 Handoff：合同失效与输出边界审计

- 日期：2026-08-03
- Worktree：`/home/amose/media/awm-p0-contract-boundary`
- Branch：`codex/p0-contract-boundary`
- Base / PR target：`codex/writing-workflow-maintenance`
- 执行模型：Terra

## 目标

修复 `20260803-001` 暴露的发布级问题：已确认内容合同在实质变更后仍继续执行，以及编辑/生产约束泄漏为标题或正文。保持现有 Evidence 审计强度，不用更多免责声明替代验证。

## 必须完成

1. **确认失效**
   - 内容合同确认后，主题、受众、渠道、篇幅、结构、正文必含内容、应用深度、Evidence、Persona、Voice 或视觉范围出现实质变化时，合同回到 pending。
   - 向用户展示变更前后差异、保持不变项和受影响阶段；再次确认前停在合同阶段。
   - 微小措辞修正不触发完整重确认。
2. **过程泄漏审计**
   - Editorial Audit 增加 prompt/process leakage。
   - 每个 H1/H2/H3 判断其服务读者问题还是作者/编辑决策；后者至少为 major。
   - “是否应该写某内容、广告判断、发布/生图/来源策略、用户要求、内部产物名”等只影响取舍，除文章主题本身讨论编辑流程外，不进入读者正文。
3. **机械候选预警**
   - `quality.py` 保留现有机械分数和兼容字段。
   - 新增独立 findings，至少覆盖高置信编辑元语言与内部产物名，包含行号、原句、规则 ID；标题必须参与该检查。
   - findings 不混入机械总分。
4. **验收闸门**
   - canonical final 验收明确要求未解决的 blocking issue 为 0。
   - 高置信过程泄漏在人工复核前保持 blocking。
5. **回归测试**
   - 本次坏例：“要不要介绍 Qwen API？可以，但别写成广告”必须命中。
   - 正常技术提醒如“不要把 API key 写进仓库”不得误报为编辑元语言。
   - 覆盖 findings 的行号、标题检查和原机械分数兼容性。

## 文件责任

主要负责：

- `skills/writing-master/SKILL.md`：等待点/合同失效、Phase 4/5 验收。
- `skills/writing-master/references/three-pass-review.md`：过程泄漏与标题审计。
- `skills/writing-master/agents/auditor.md`：Auditor 输出责任。
- `src/writing_master/commands/quality.py`。
- `tests/test_quality.py`、相关最小合同测试。

共享文件约束：P1 也可能编辑 `SKILL.md` 与 `tests/test_skill_contracts.py`，只改本任务对应小节，不重排整文件，不覆盖其他 worktree 的后续变更。

## 非目标

- 不实现失败案例持久化、`spec.md` 或来源展示规则；这些属于 P1。
- 不引入依赖。
- 不把机械分数包装成语义质量分。
- 不重构无关 CLI 或 Handoff Runtime。

## 验收

```bash
PYTHONPATH=src python -m unittest tests.test_quality tests.test_skill_contracts -v
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/awm-p0-pyc python -m compileall -q src tests
bash -n install.sh
./bin/writing-master --help
```

提交使用简短 Conventional Commit；完成后推送分支并创建目标为 `codex/writing-workflow-maintenance` 的 PR。PR 描述列出受影响 worktree、行为变化和精确验证命令。
