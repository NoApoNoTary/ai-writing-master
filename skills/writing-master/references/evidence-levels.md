# Evidence Levels — 证据等级定义

## 概述

证据追溯机制是质量保障的基础设施，但不应该渗透到用户可见的输出。不同场景需要不同的证据强度，这里定义三个等级。

## 三个等级

| 等级 | 适用场景 | 证据要求 | 用户体验 |
|------|---------|---------|---------|
| **relaxed** | 快速草稿、内部讨论稿 | 只防止明显造假，不要求来源 | 最快，4-5 分钟出稿 |
| **balanced** | 热点速写、常规文章（**默认**） | 核心数据需验证，观点可主观 | 15-20 分钟，接近真人质量 |
| **strict** | 深度报道、技术白皮书 | 每个主张都需要来源和 claim_id | 1 小时+，最严格 |

**默认选择**: `balanced` — 这是标准模式的默认设置。

## 详细行为定义

### relaxed（宽松）

**使用场景**:
- 快速草稿模式
- 内部讨论稿
- 测试想法

**证据要求**:
- ❌ 不生成 sources.yaml
- ❌ 不生成 claims.yaml
- ❌ 不要求每个陈述都有来源
- ✅ 只在明显错误时标记（如"Claude 5 支持 1000 万 tokens"）

**审校行为**:
- 一次性快速审校（不分证据层/编辑层/声音层）
- 只检查：逻辑连贯性、可读性、明显事实错误
- 不检查：来源可达性、claim_id 完整性、证据时效性

**输出文件**:
```
runs/TASK_ID/
├── status.json
├── brief.md
├── draft.md
└── suggestions.md          # 可选改进建议，不是 review-report.yaml
```

**用户看到的**:
```
文章已完成！

[显示文章正文]

可选改进建议：
- 第 3 段可以补充一个具体例子
- 结尾可以更有力

要调整吗？（直接说要改的地方，或"跳过"）
```

### balanced（平衡）— **默认**

**使用场景**:
- 标准模式（热点速写、常规文章）
- 微信公众号、知乎文章、X Thread
- 大部分日常写作

**证据要求**:
- ✅ 核心数据需要验证（价格、日期、版本号、性能指标）
- ✅ 引用他人观点时需要来源
- ❌ 作者自己的观点和分析不需要 claim_id
- ❌ 常识性陈述不需要来源
- ✅ 生成 sources.yaml，但不是每句话都关联

**审校行为**:
- 证据层：只检查**核心数据**是否准确（不要求所有陈述都有来源）
- 编辑层：逻辑、可读性、节奏
- 声音层：表达自然度、AI 味检测

**什么是"核心数据"**:
- ✅ 需要验证：价格（"Claude 5 每百万 tokens $3"）、日期（"2026 年 8 月发布"）、版本号、性能指标、统计数字
- ❌ 不需要验证：作者观点（"我认为这个设计很合理"）、常识（"AI 模型需要大量算力"）、经历（"我之前遇到过类似问题"）

**输出文件**:
```
runs/TASK_ID/
├── status.json
├── brief.md
├── sources.yaml            # 只包含核心数据来源，不是所有陈述
├── draft.md
├── review-notes.md         # 编辑建议，不是打分报告
└── final.md
```

**用户看到的**:
```
文章已完成！

[显示文章正文]

已验证核心数据：
- Claude 5 定价：$3/百万 tokens（来源：官方定价页面）
- 上下文窗口：200K（来源：技术文档）

编辑建议：
- 第 5 段"然而"用得太频繁，可以换成"不过"
- 标题可以更吸引眼球："Claude 5 来了" vs "Claude 5：AI 助手的新标杆"

应用这些建议吗？（"全部应用" / "只改标题" / "跳过"）
```

### strict（严格）

**使用场景**:
- 深度模式
- 严肃报道、调查性文章
- 技术白皮书、研究报告
- 需要完整证据链的内容

**证据要求**:
- ✅ 每个事实性陈述都需要 claim_id
- ✅ 所有来源必须可追溯、时效性验证
- ✅ 引用必须标注页码或段落
- ✅ 生成完整的 sources.yaml 和 claims.yaml

**审校行为**:
- 证据层：逐个验证 claim_id、来源可达性、内容一致性、时效性
- 编辑层：逻辑严密性、论证完整性
- 声音层：专业性、客观性

**输出文件**:
```
runs/TASK_ID/
├── status.json
├── brief.md
├── sources.yaml            # 完整来源档案
├── claims.yaml             # 每个主张都有 claim_id
├── draft.md
├── review-report.yaml      # 三层审校报告
├── revision-report.yaml
├── acceptance-report.md
└── final.md
```

**用户看到的**:
```
文章已完成并通过三层审校。

[显示文章正文]

证据审查结果：
- 共 47 个事实性陈述
- 已验证：45 个
- 需要补充来源：2 个（已标记）

编辑层：✓ 通过
声音层：✓ 通过

查看详细审校报告？（"是" / "跳过"）
```

## 如何选择

### 决策树

```
用户请求
  ↓
是快速草稿吗？ → 是 → relaxed
  ↓ 否
是深度报道/白皮书吗？ → 是 → strict
  ↓ 否
默认 → balanced
```

### 用户没有明确指定时

- **快速模式** → `relaxed`
- **标准模式** → `balanced`（默认）
- **深度模式** → `strict`

### 用户明确指定时

用户可以覆盖默认选择：

```
"写一篇关于 Claude 5 的文章，relaxed 证据等级"
"用 strict 模式写这篇技术分析"
```

但要警告不匹配的组合：

```
用户："快速模式，strict 证据"
Agent："快速模式通常用 relaxed 证据等级（4-5 分钟），
       strict 需要 1 小时+。确定要用 strict 吗？"
```

## 配置方式

### 在 status.json 中记录

```json
{
  "task_id": "writing-20260807-001",
  "mode": "standard",
  "evidence_level": "balanced",
  "phase": "phase-5-review"
}
```

### 在内容契约中确认

Phase 0 capability-preflight 时：

```yaml
# content-contract.yaml
mode: standard
evidence_level: balanced   # 默认，用户未指定时
target_id: wechat
topic: "Claude 5 发布解读"
```

如果用户明确要求其他等级：

```
用户："写一篇关于 Claude 5 的严肃技术分析"
Agent：检测到"严肃技术分析"，建议 evidence_level: strict
```

## 迁移现有任务

**已有的运行目录如何处理？**

1. **没有 evidence_level 字段的旧任务**:
   - 根据 `mode` 推断：
     - `mode: quick` → `relaxed`
     - `mode: standard` → `balanced`
     - `mode: deep` → `strict`

2. **恢复旧任务时**:
   - 读取 `status.json` 的 `evidence_level`
   - 如果缺失，按上述规则推断并记录

3. **不破坏现有流程**:
   - 所有等级都支持原有的 sources.yaml/claims.yaml
   - `relaxed` 只是"不要求生成"，不是"禁止生成"
   - 如果已有 sources.yaml，继续使用

## 实现检查清单

### Phase 0 - Capability Preflight
- [ ] 根据 mode 设置默认 evidence_level
- [ ] 用户明确指定时覆盖默认值
- [ ] 不匹配组合时给出警告
- [ ] 写入 status.json 和 content-contract.yaml

### Phase 1 - Research
- [ ] `relaxed`: 不生成 sources.yaml（除非素材本身有明确来源）
- [ ] `balanced`: 只登记核心数据来源
- [ ] `strict`: 完整来源档案

### Phase 4 - Writing
- [ ] `relaxed`: 不插入 claim_id
- [ ] `balanced`: 只对核心数据插入 claim_id
- [ ] `strict`: 每个事实性陈述都有 claim_id

### Phase 5 - Review
- [ ] `relaxed`: 一次性快速审校 → suggestions.md
- [ ] `balanced`: 三层审校，但证据层只检查核心数据 → review-notes.md
- [ ] `strict`: 完整三层审校 → review-report.yaml

### Phase 6 - Acceptance
- [ ] `relaxed`: 直接交付，不生成 acceptance-report.md
- [ ] `balanced`: 简化验收 → 只确认核心数据和文章质量
- [ ] `strict`: 完整验收报告

## 反模式

### ❌ 错误做法

**1. 把 evidence_level 暴露给用户**

```
错误："请选择证据等级：relaxed / balanced / strict"
正确：根据 mode 自动选择，用户不需要知道这个概念
```

**2. 所有模式都生成一样的文件**

```
错误：relaxed 也生成 sources.yaml、claims.yaml、review-report.yaml
正确：relaxed 只生成必要文件，不要为了"一致性"生成空文件
```

**3. 用户可见输出提到 claim_id**

```
错误："claim_001 的来源已验证"
正确："Claude 5 定价已验证（来源：官方定价页面）"
```

**4. 把 evidence_level 当成"质量等级"**

```
错误：relaxed = 低质量，strict = 高质量
正确：relaxed = 快速且足够好，strict = 慢但最严格
       不同场景需要不同强度，不是质量高低
```

## 总结

- **evidence_level 是内部参数**，用户通常不需要知道
- **默认是 balanced**，适合 80% 的写作场景
- **证据追溯是质量机制**，不应该变成用户可见的产品特性
- **不同等级生成不同文件**，而不是都生成然后标记"未使用"
