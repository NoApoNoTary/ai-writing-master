# 单目标渠道改写

P0 的执行合同是“一次 Rewrite、一个 target_id”。渠道具体约束读取
`{skill_dir}/platforms/<target_id>.yaml`。

## 核心合同

1. 保留事实、来源边界、作者立场、真实案例和 source 已验收的声音。
2. 为当前渠道重新决定信息顺序、开头、节奏、段落形态和互动方式。
3. 一个 run 只生成一个渠道成品；另一个渠道使用新的 Rewrite run。
4. 任何新增第一人称经历必须来自用户素材，渠道适配不创造个人经验。
5. 渠道正文、视觉和格式都是派生产物，不修改 canonical source。
6. 同一 source hash 的后续 Rewrite 复用已验证的 `source-analysis.md`，不重复调研。

## 输入分类

| `source_ref` | 准入条件 | canonical source |
|---|---|---|
| `accepted_final` | 同一 Writing Master 任务的 `final.md`、`sources.yaml`、`claims.yaml` 存在，且 `acceptance-report.md` 内容验收通过 | 该任务只读 canonical package 的渠道正文与支持产物 |
| `standalone_input` | 用户直接提供文件或完整正文 | 该用户输入的只读副本 |

来自 Writing Master 的未验收 `draft-v1.md`、`draft-v2.md` 或未通过验收的 `final.md` 不可进入 Rewrite，也不可作为视觉、格式或发布来源。`standalone_input` 是独立任务的合法输入，但不能冒充已验收的 Writing Master final。

## 单次执行顺序

1. 固定 `source.md` 并记录 `source_sha256`。
2. 选择一个 `target_id`，只读取对应渠道 YAML。
3. 从 canonical package 生成 `source-analysis.md`；若已有分析的 source、支持产物与 analysis hash 完全一致，则直接复用。
4. 为当前渠道重新建立结构，不沿用源稿段落顺序。
5. 生成正文后执行渠道编辑审查与机械检查。
6. 只重做当前渠道未通过的部分，最多两轮。
7. 完成 YAML 声明的必要派生产物后交付本次 Rewrite。

## 产物

- `source.md`：当前 Rewrite 的只读 canonical source 副本。
- `rewrite-status.json`：单一 `target_id` 的状态，不含目标数组。
- `source-analysis.md`：按 source hash 与 analysis hash 双重校验后复用的事实、判断、案例和渠道中立 Voice 基线。
- `<rewrite_output_filename>`：当前渠道正文。
- `<target_id>-review.json`：绑定 source、analysis 与 output hash 的编辑结论、机械预警和源稿相似度结果。
- YAML `required_derivatives`：当前渠道完整交付所需的格式、HTML 或封面。

用户随后要求另一个渠道时，新 run 复制相同 `source.md` 与通过双 hash 校验的 `source-analysis.md`。新 run 只读取自己的渠道合同；前一次渠道正文不参与生成。当前 run 失败不修改 canonical source，也不改变之前已经完成的 Rewrite。
