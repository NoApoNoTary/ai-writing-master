# Run Spec

`{run_dir}/spec.md` 是内容契约确认后的用户可读冻结合同；它是一页式归档产物，不替代 `brief.md`、`channel-contract.yaml` 或运行时状态。

## 必含区块

- 读者目标
- 交付物
- 正文必含
- 读者可见内容
- 内部执行约束
- Persona / Voice
- 验收条件
- 采用的失败案例规则
- 待确认项

## 投影与边界

确认合同后先写 `spec.md`，再从其中投影 Researcher 所需的 `brief.md`。`brief.md` 只保留主题、读者、渠道、内容目的和证据要求，保持 Persona-neutral；内部广告判断、视觉 provider、发布意图及执行细节不进入读者内容或研究投影。

## 冻结、hash 与恢复

`spec.md` 写入后冻结，并记录其 SHA-256 供恢复时校验。恢复只复用任务内已冻结版本；外部偏好或后续默认值不覆盖它。用户修改合同字段时生成新的 run 或新的 `spec_version` 与新 hash，保留旧版本供审阅；合同失效与重新确认由上层流程处理。
