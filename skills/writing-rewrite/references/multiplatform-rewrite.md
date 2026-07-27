# 多平台内容级改写

本文件改编自 wewrite 的多平台改写规则。平台的具体输出约束读取
`{skill_dir}/platforms/<platform>.yaml`。

## 核心合同

1. 保留事实、来源边界、作者立场和真实案例。
2. 重新决定信息顺序、开头、节奏、段落形态和互动方式。
3. 每个平台从同一个 canonical source 独立生成，避免后一个版本继承前一个平台的语言习惯。
4. 任何新增第一人称经历必须来自用户素材，平台适配不创造个人经验。
5. 所有平台版本、视觉、格式和发布记录都是派生产物，不修改 canonical source。

## 输入分类

| `source_class` | 准入条件 | canonical source |
|---|---|---|
| `accepted_writing_master_final` | 同一 Writing Master 任务的 `final.md` 存在，且 `acceptance-report.md` 内容验收通过 | 该 `final.md` 的只读副本 |
| `standalone_user_input` | 用户直接提供文件或完整正文 | 该用户输入的只读副本 |

来自 Writing Master 的未验收 `draft-v1.md`、`draft-v2.md` 或未通过验收的 `final.md` 不可进入 Rewrite，也不可作为视觉、格式或发布来源。`standalone_user_input` 是独立任务的合法输入，但不能冒充已验收的 Writing Master final。

## 每个平台的执行顺序

1. 读取平台 YAML，确认字数、输出类型、图片和标签要求。
2. 从源稿提取不可变事实、核心判断、案例与限制条件。
3. 为目标平台重新建立结构，不沿用源稿段落顺序。
4. 生成版本后执行编辑审查与机械检查。
5. 与源稿及其他平台版本运行相似度检查。
6. 只重做未通过的目标平台版本，最多两轮。

## 产物

- `source-analysis.md`：源稿的事实、判断、案例和语气。
- `<platform>.md`：目标平台正文。
- `<platform>-review.json`：编辑结论、机械预警和相似度结果。

平台版本保存到当前 run 目录，源稿保持只读。

平台文字通过审查后，视觉、格式和发布只读取相应通过版本并写入资产、格式化文件或发布记录；任何平台失败都不修改 canonical source 或其他平台版本。
