# 证据与素材契约

事实调研和素材调研并行进行，最终通过稳定 ID 关联正文、来源和视觉资产。

## 素材接收结果

开题阶段把用户可见的“素材接收结果”写入 `capability-preflight.md`，不另建运行时状态。它只说明输入是否已经接收或提取，不把提取结果误写成已确认事实。

```yaml
material_receipt:
  status: receiving | ready_to_continue | needs_confirmation | partial_failure
  counts:
    received: 3
    extracted: 2
    pending: 1
    failed: 0
    confirmation_required: 1
  items:
    - material_id: material-001
      kind: url | youtube | markdown | image | gif | video | chart | document | historical_article
      location: "URL 或本地路径"
      status: received | extracting | extracted | pending | failed
      extracted_to: "研究目录中的文件路径或 null"
      failure:
        reason: null
        action: null
        impact: null
        retry: null
      confirmation:
        status: not_required | required | confirmed | excluded
        question: null
  next_action: "继续添加素材 | 结束摄入并继续 | 确认/排除指定素材 | 重试 material-001"
```

- `received` 是已登记输入总数；`extracted`、`pending`、`failed` 是该总数的当前处理结果，不要求相加等于总数。
- 每个失败项都写明失败动作、对后续的影响、已保留产物和可执行的重试入口；失败项不阻塞无关素材。
- 只在公开引用、来源身份或素材用途存在实际歧义时设置 `confirmation.status=required`。用户可确认、排除、重试，或结束素材摄入继续主流程。
- 向用户展示时使用简洁计数，例如：

```text
已接收：3 项
已提取：2 项
等待处理：1 项
失败：0 项
需要你确认：素材 A 是否允许作为公开引用
```

`material_id` 仅标识这次输入；进入正文的事实仍要经过 `sources.yaml` 和 `claims.yaml` 的确认流程。

## `sources.yaml`

```yaml
sources:
  - source_id: src-001
    material_id: material-001
    title: "来源标题"
    url: "https://example.com/..."
    publisher: "发布者"
    published_at: "2026-07-27"
    accessed_at: "2026-07-27"
    source_type: official | primary | independent | secondary | user_provided
    notes: "适用范围与限制"
```

## `claims.yaml`

```yaml
claims:
  - claim_id: claim-001
    statement: "准备进入正文的最小可核验陈述"
    source_ids: [src-001]
    evidence_level: confirmed | supported | inference | user_experience
    boundary: "适用条件、样本或时间范围"
    allowed_wording: "正文可使用的强度"
    status: accepted | pending | excluded
```

规则：

- 一个 claim 表达一个最小陈述。
- 推断明确标记 `inference`，并列出支持它的来源。
- 用户经验记录其来源文件或本次对话位置，不扩写成普遍事实。
- `pending` 和 `excluded` 主张不进入正文事实句。

## `asset-manifest.yaml`

```yaml
assets:
  - asset_id: asset-001
    material_id: material-001
    kind: image | gif | video | chart | screenshot | document
    source_class: official | primary | third_party | editorial | decorative | user_provided
    source_id: src-001
    original_location: "URL 或本地路径"
    local_path: null
    proves_claims: [claim-001]
    intended_role: evidence
    rights_note: "来源和使用说明"
    status: candidate | selected | produced | rejected
```

素材优先级：

1. 官方或第一方原始素材；
2. 一手技术资料与原始数据；
3. 独立第三方验证素材；
4. 编辑解释图；
5. 装饰图。

生成图只承担解释或氛围职责。涉及产品实际表现、benchmark、案例结果和界面行为时，优先使用可溯源原始素材。

## `storyboard.md`

每个视觉位记录：

```markdown
## visual-01
- 位置：开头 / 某小节之后
- 角色：Cover / Hero / Evidence / Explanation / Decorative
- 任务：读者看完这张图要理解或相信什么
- 关联主张：claim-001
- 首选素材：asset-001
- 备选路由：baoyu-infographic
- 必需性：required / optional
- 验收：来源准确、移动端可读、与其他视觉职责不重复
```

## 进入视觉生产的检查

- 每个 Evidence visual 至少关联一个 accepted claim。
- 每个 selected 原始素材都有来源和身份。
- 每个 editorial visual 都有明确解释任务。
- Cover、Hero 和案例证明图不复用同一素材承担多个主要职责。
- 找到真实素材后，删除对应的占位生成计划。
- 文章结构变化时，先更新 storyboard，再执行 Baoyu。
