# 渠道适配 P0：单渠道、双入口

**日期：2026-07-29**

## 1. 目标

AI Writing Master 保留两个明确入口：

| `entry` | 输入 | 结果 |
|---|---|---|
| `writing` | 从零创作请求 | 完整调研、写作、审校、验收及一个渠道成品 |
| `rewrite` | 已有 canonical final 或用户完整正文 | 固定 source hash 后生成一个经过渠道审查的成品 |

入口枚举与 Skill 的映射固定为：`writing` → `writing-master`，`rewrite` → `writing-rewrite`。

P0 支持三个 `target_id`：

- `wechat`
- `x-post`
- `x-thread`

每个任务只处理一个 `target_id`。用户需要第二个渠道时，创建新的 Rewrite，并复用同一 canonical source、`source_sha256` 和已验证的 `source-analysis.md`。

## 2. 用户流程

### 2.1 从零创作

```text
识别为从零创作
  → 选择写作模式
  → 选择一个 target_id
  → 调研、写作和渠道审校
  → 验收该渠道的 canonical final
  → 生成渠道必要产物
  → 完整交付
```

`final.md` 从初稿开始就按当前渠道合同写作，不先生成通用长文再压缩。内容验收通过后，`final.md` 成为该任务的只读 canonical final；`sources.yaml`、`claims.yaml` 和本次验收引用的编辑产物共同构成可供后续 Rewrite 读取的只读 canonical package。

### 2.2 改写已有内容

```text
识别为已有正文
  → 选择一个 target_id
  → 固定 source.md 与 source_sha256
  → 生成或复用 source-analysis.md
  → 渠道适配与独立审查
  → 生成渠道必要产物
  → 完整交付
```

用户说“再生成一个 X Thread”时，新建 Rewrite run。新 run 校验并复用前一个包的 `source.md`、`source_sha256` 和 `source-analysis.md`，同时按 analysis 中记录的 hash 复核原 canonical package 的支持产物；不重新做 Article Research，也不读取前一个渠道正文作为输入。

## 3. 最小接口

```yaml
entry: writing | rewrite
target_id: wechat | x-post | x-thread
source_ref: accepted_final | standalone_input
source_sha256: ...
```

- `writing` 在内容验收后把 `source_ref` 记录为 `accepted_final`，并写入 `final.md` 的 SHA-256。
- `rewrite` 在开始改写前固定全部四个字段。
- `target_id` 是标量。

## 4. 渠道合同

合同继续位于 `skills/writing-rewrite/platforms/`：

- `wechat.yaml`
- `x-post.yaml`
- `x-thread.yaml`

Writing Master 在 Phase 0 把所选合同的共享字段复制为任务内 `channel-contract.yaml`，并写入主写作的 `output_filename: final.md`。平台 YAML 的 `rewrite_output_filename` 只供 Writing Rewrite 使用。两个入口共享同一套渠道约束、Voice 保持规则、编辑审查和定向返工方法。

不新增 Python Router、Adapter 基类或第二套渠道目录。

## 5. 交付合同

### 5.1 Writing

- `final.md`
- `sources.yaml`
- `claims.yaml`
- `asset-manifest.yaml`
- `review-report.yaml`
- `revision-report.yaml`
- `acceptance-report.md`
- 当前渠道 YAML 要求的必要产物

### 5.2 Rewrite

- `source.md` 与 `source_sha256`
- `rewrite-status.json`
- `source-analysis.md` 与分析 hash
- 当前渠道正文
- `<target_id>-review.json`
- 当前渠道 YAML 要求的必要产物

### 5.3 渠道必要产物

| `target_id` | 完整交付 |
|---|---|
| `wechat` | 渠道正文、`formatted.md`、`wechat.html`、`cover.png` |
| `x-post` | 一条通过事实、渠道审查及实际 composer 预览的帖子 |
| `x-thread` | 每条均通过事实、渠道审查及实际 composer 预览的完整 Thread |

微信排版、HTML 和封面继续组合现有 Baoyu Skills。发布是交付后的独立用户动作。

## 6. 状态与失败

`rewrite-status.json` 保持单目标结构：

```json
{
  "entry": "rewrite",
  "target_id": "x-thread",
  "source_ref": "accepted_final",
  "source_sha256": "...",
  "source_analysis_sha256": "...",
  "output_sha256": "...",
  "review_sha256": "...",
  "derivatives_sha256": {},
  "status": "in_progress | completed | failed",
  "attempt": 1
}
```

`completed` 必须绑定当前 source、analysis、渠道正文、Review 和必要派生产物的 hash。当前 Rewrite 失败时保留 source、分析、正文草稿和审查记录，结束当前 run。它不修改来源 canonical final，也不改变之前完成的 Rewrite。

X 的 280 weighted length 不由仓库内字符估算冒充。`x-post` 和 `x-thread` 必须在 Review 中记录实际 composer 预览或用户提供的同文预览证据；能力或证据缺失时保存草稿并以 `failed` 结束。

## 7. P0 边界

P0 不包含：

- X Article；
- 自动发布；
- 渠道数据反馈或表现学习；
- 新的运行时路由层。

## 8. 验收场景

1. 从零创作进入 `writing-master`，已有完整正文进入 `writing-rewrite`。
2. 单次任务只有一个标量 `target_id`。
3. 第二次 Rewrite 在 source hash 一致时复用 `source-analysis.md`。
4. Rewrite 不修改来源 canonical final，也不重新选择 Voice。
5. `wechat` 满足自己的 YAML 合同；`x-post`、`x-thread` 还必须具有有效的 composer 预览证据。
6. 当前渠道失败不影响原稿或之前完成的 Rewrite。
7. 既有核心合同测试和完整测试集通过。
