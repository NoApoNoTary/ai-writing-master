# 写作模式选择

## Canonical prompt

这是完整写作入口唯一的模式选择文案。其他文档只引用本文件，不复制这段文本。

```text
请选择本次写作模式：
1. 快速草稿：单 Agent，最少调研与一次审校，适合先拿到可讨论版本。
2. 标准写作（推荐）：单 Agent，完整调研、素材规划、写作与三层审校。
3. 深度写作：多 Agent 分工，独立研究、策划、写作和审计，适合重要长文。
注：深度执行仅在本次 capability preflight 检出真实 Handoff Runtime 后可用。
```

## 入口规则

新建完整文章时，模式选择是第一道闸门。用户未在当前请求中明确模式时，发送下面的固定问题并等待回复：

发送上面的 Canonical prompt，不要在其他文件重新编写选项文案。

规则：

- 不根据题目、字数、平台、时限或用户身份代选。
- 用户已说“快速写”“标准模式”“深度写稿”“多 Agent 写”等明确表述时，视为已选择。
- “继续上次”时要求用户指定 `task_id` 或运行目录；只有运行时已验证恢复能力后才读取 `status.json.mode`，否则展示所需输入与 Product–Technical Gap。
- 单一模块请求和 `writing-rewrite` 路由按用户当前指令执行；升级为端到端新文章时再触发模式选择。
- 用户只回复序号时：`1=quick`、`2=standard`、`3=deep`。

## 所选模式就绪闸门

模式确定后，先执行一次轻量就绪检查，再进入内容契约、素材提取或任何高 Token 步骤。检查必须早于网页/视频提取、实时检索、正文生成、视觉生成和角色派发。

在 `capability-preflight.md` 中记录：

```yaml
selected_mode: quick | standard | deep
mode_readiness: ready | unavailable
diagnostic_id: null | WM-CAP-001
handoff_runtime: available | unavailable  # 仅 deep 使用
```

- `quick` / `standard`：确认当前会话能按所选模式完成核心写作流程并保存任务产物。
- `deep`：只有当前宿主的真实 Handoff Runtime 能执行本次角色交接时才记录 `ready`。角色卡、协议文档、命令名称或配置片段都不是可用性的证据。
- `ready`：继续既有 Phase 0 和后续流程。
- `unavailable`：立即结束当前任务；素材提取、调研、正文生成、视觉生成和角色派发的调用次数必须为 0。不切换到 quick、standard 或其他模式，也不创建模拟结果。

`unavailable` 时向用户显示：

```text
所选的深度写作模式当前未就绪，任务已停止，尚未进入调研或写作。

如需反馈，请提交 Issue，并附上：
诊断编号：WM-CAP-001
版本：VERSION
```

发送时用当前安装版本替换 `VERSION`；无法确定时写 `unknown`。普通错误正文只包含用户结果、诊断编号和版本。Handoff Runtime、宿主能力、异常类型和内部异常栈只写入诊断详情。只提醒用户提交 Issue，不自动创建 Issue，也不生成 Issue 草稿。

## 模式合同

### 1. 快速草稿（quick）

- 执行：当前 Agent。
- 目标：尽快形成有依据、可讨论的完整版本。
- 产物：与标准模式相同的核心文件：简版 `brief.md`、关键 `sources.yaml`/`claims.yaml`、`asset-manifest.yaml`、简版大纲、`draft-v1.md`、一次合并 `review-report.yaml`、`revision-report.yaml`、`final.md` 和 `acceptance-report.md`。
- 调研：仅覆盖正文实际使用的关键事实；近期或易变化信息仍实时核验。
- 用户确认：内容契约；主题存在明显分叉时确认角度；其余环节连续推进。
- Baoyu：照常做早期 capability/material preflight；内容验收通过后，只有明确需要且图像类视觉闸门通过才生产视觉资产。

### 2. 标准写作（standard）

- 执行：当前 Agent，不创建子代理。
- 目标：完成可发布的常规文章。
- 产物：完整 Brief、`sources.yaml`、`claims.yaml`、`asset-manifest.yaml`、选题、大纲、storyboard、初稿、三层审校、标题、验收报告。
- 调研：事实与素材双轨进行。
- 用户确认：内容契约、核心角度、发布动作。标题随最终稿交付，除非用户主动要求选择或修改。
- Baoyu：早期预检和素材摄入；内容验收通过后按需生产。图像类视觉另需结构稳定和 storyboard。

### 3. 深度写作（deep）

- 执行：仅当就绪闸门记录 `mode_readiness=ready` 且 `handoff_runtime=available` 时，Lead Agent 才调度 fresh-context 专项代理；否则使用 `WM-CAP-001` 结束当前任务。
- 目标：通过角色隔离提高重要长文的研究、判断与审校质量。
- 产物：实际执行成功时，与标准模式相同，额外保留各代理的结构化报告和输入 hash。
- 调研：Researcher 独立维护事实和素材清单。
- 策划：Editorial Strategist 基于已核验证据形成角度、读者决策和 storyboard。
- 写作：Writer 只读取接受后的内容包。
- 审校：Auditor 首轮不读取 Writer 的解释和父对话全文。
- Baoyu：由 Lead 统一执行预检和闸门；子代理只产出计划与 manifest。

完整协议见 `agent-orchestration.md`。

## 模式保持与变更

- 模式写入 `status.json` 后贯穿该任务。
- 用户可明确要求从 quick 升为 standard/deep，或从 deep 收缩为 standard。
- 变更时记录 `mode_history`、变更时间、原因和从哪个阶段继续。
- 从单 Agent 升到 deep 时，子代理只接收已有文件产物，不复制完整父对话。
