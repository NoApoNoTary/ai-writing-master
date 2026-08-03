# 内容路由：组合类型与应用深度

`content_type` 复用既有类型：`release | analysis | review | opinion | tutorial | story`。
`application_depth`：`none | scenario | actionable | reproducible`。

- `none`：不承诺场景或操作复现。
- `scenario`：具体使用场景、明确输入和可观察结果；合成示例需要明确标注。
- `actionable`：前置条件、步骤、示例输入、预期输出、失败信号、适用边界。
- `reproducible`：以上全部，加实际验证环境/版本、验证方法、回滚和已知限制；没有真实测试证据不得声称此级别。

Phase 0 根据初始主题确认 `content_type` 并形成暂定应用深度，写入 `channel-contract.yaml`。内容契约确认后，`content_type` 在当前 run 内冻结：

```yaml
content_type: analysis
application_depth: scenario
application_depth_source: user | ai
```

Phase 2 在选题已确定且 Article Research 已形成 accepted evidence 后重新推荐一个 `recommended_combo`。有 Topic Research 时使用选定 `candidate`；用户已给出明确主题时使用该主题和已确认角度。推荐同时考虑目标读者、素材与可验证性：

```yaml
recommended_combo:
  label: "深度分析 + 场景应用"
  content_type: analysis
  application_depth: actionable
  reason: "..."
  required_blocks: [prerequisites, steps, example_input, expected_output, failure_signals, applicability_boundary]
```

低确定性时可附一个 `alternative`，但不新增等待点。推荐组合随现有“核心方向/选题确认”一起展示；用户可用“修改：组合类型=实测评测+场景应用”覆盖。用户已明确指定路线时保留用户选择并同时展示 AI 建议。

当前 run 的 `recommended_combo.content_type` 必须与已确认的 `channel-contract.yaml` 一致；AI 可以把另一文章类型放进 `alternative`，采用它时新建 Writing run。Phase 3 前只将最终 `application_depth` 与 `application_depth_source` 对齐到渠道合同。若推荐深度超出现有证据、素材或测试能力，先补充受影响的调研/验证，或采用证据能够支持的较低深度。

`application_depth_source` 只记录 `user` 或 `ai`。每个组合的 `required_blocks` 是 Writer 的交付清单，也是 Auditor 的验收清单。

`acceptance-report.md` 增加：

```yaml
application_check:
  depth: actionable
  required_blocks: [prerequisites, steps]
  status: pass | partial | blocked
```

只有 `pass` 状态可使内容验收通过。`partial` 表示当前正文尚未满足所选深度，需要修订或显式降低深度后重新验收；`blocked` 表示缺少证据、素材或输入，相关问题解决后再验收。
