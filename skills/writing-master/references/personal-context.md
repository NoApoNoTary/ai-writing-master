# Personal Context Runtime Bridge

本文件只定义 Goal A 已实现的 Runtime 边界；不定义风格学习、`learn`、Research Brief 或 quick/standard 通用恢复。

## Standard 与 Deep 的任务内上下文输入

内容契约确认后，标准写作先在既有 `{run_dir}` 中运行：

```text
writing-master context snapshot {run_dir} --material ITEM_ID:PURPOSE ...
```

- 先用 `writing-master context search` / `material list` 发现候选；只把已确认要用的 item 传给 Snapshot。
- `ask_before_use` 必须先由用户任务级批准；`private` 和 disabled item 不进入 Snapshot。
- 没有选中素材时仍创建空 Snapshot，它冻结 empty Profile/Style。
- Snapshot 已存在时，只接受同一组 `(ITEM_ID, PURPOSE)`；不同请求是冲突，不覆盖旧任务。

Standard 的 Phase 1、2、3 只能读取 `{run_dir}/personal-context-snapshot.json` 和 `{run_dir}/context-materials/`。不得扫描或直接读取 `${WRITING_MASTER_HOME}/personal-context/`、旧 `personal_materials/` 或其他全局个人目录。

Deep 模式由 Lead 在内容契约确认后创建或确认同一 Snapshot；需要个人上下文的 Writer 或 Auditor 只通过自己的 Manifest `allowed_inputs` 读取 Snapshot 和逐项列出的任务内副本。Host 不把全局个人目录或父对话全文传给专项 Agent。

## 用户摘要

只显示下列摘要，不显示 hash、全局路径或私密正文：

```text
personal_context: unavailable | empty | ready
selected_materials: N
pending_approvals: N
```

- `unavailable`：Runtime 或 Snapshot 建立失败；说明受影响的是个人上下文，不把未读取的全局内容写成已使用。
- `empty`：Snapshot 已建立但 Profile/Style 为空且未选择个人素材。
- `ready`：Snapshot 已冻结可用 Profile 或至少一条已选择素材。

## Usage 与验证

内容验收形成 `final.md` 和 `acceptance-report.md` 后，Runtime 以实际使用的 Snapshot item/purpose、section/claim 和这两个 artifact 路径写入 `context-usage.json`。不要手写或猜测 hash。

交付前执行：

```text
writing-master context verify-run {run_dir}
```

它校验 Snapshot、任务内副本、批准、usage 记录及 final/acceptance hash；它不对正文作语义性“绝无私密泄露”声明。
