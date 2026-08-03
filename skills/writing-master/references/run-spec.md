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

首次发布同时写不可变的 `spec-v1.md`、当前投影 `spec.md` 和 `spec-metadata.json`。同一版本、同一内容重复保存是幂等操作；同一版本出现不同内容时报冲突，不覆盖既有文件。

明确创建下一合同版本时，先保留新的不可变 `spec-vN.md`，再同步当前 `spec.md`，并在 metadata 中记录 `current_version`、`current_sha256` 和各历史版本 hash。版本必须连续；旧版本保持可校验、可审阅。多文件发布若在中途停止，以相同版本和内容重试可完成剩余写入，不重建或覆盖既有历史。

恢复时通过 anchored run directory 读取 metadata、当前文件和全部已登记历史，校验它们的 SHA-256；调用方还可提供 `expected_sha256` 绑定预期合同。任何当前文件、历史或 metadata 篡改都停止恢复。外部偏好或后续默认值不覆盖任务内合同；合同失效与重新确认由上层流程处理。
