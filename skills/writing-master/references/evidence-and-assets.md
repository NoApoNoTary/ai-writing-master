# 证据与素材契约

事实调研和素材调研并行进行，最终通过稳定 ID 关联正文、来源和视觉资产。

## `sources.yaml`

```yaml
sources:
  - source_id: src-001
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
