# Mode Definitions — 模式定义

## 概述

AI Writing Master 提供三种写作模式，针对不同场景优化。核心区别在于**速度 vs 深度**，而不是质量高低。

## 三种模式对比

| 特性 | Quick | Standard | Deep |
|------|-------|----------|------|
| **目标** | 快速草稿 | 接近真人质量 | 深度协作 |
| **耗时** | 4-5 分钟 | 15-20 分钟 | 1 小时+ |
| **证据等级** | relaxed | balanced | strict |
| **Agent 数量** | 1 | 1 | 多个 |
| **调研深度** | 表层 | 标准 | 深度多源 |
| **审校层数** | 1 次快速 | 3 层（简化） | 3 层（完整） |
| **输出文件数** | 3-4 个 | 5-6 个 | 10+ 个 |

## Quick Mode — 快速草稿

### 适用场景
- 测试想法：快速看看这个话题能写成什么样
- 内部讨论稿：给团队看的初稿
- 时间紧急：需要立即有个可讨论的版本

### 核心特点
- **不保证质量**，只保证速度
- 最少的用户交互（能推断的都不问）
- 不生成大量 YAML 文件
- 一次性输出，不迭代打磨

### 工作流程

```
1. Phase 0: 快速准备（30 秒）
   - 理解话题和渠道
   - 不生成 capability-preflight.md
   - 直接写入 status.json

2. Phase 1: 表层调研（1 分钟）
   - 如果用户提供素材，快速提取关键点
   - 不提供素材则跳过
   - 不生成 sources.yaml

3. Phase 2-3: 跳过
   - 不生成 brief.md（或极简版）
   - 不生成 storyboard

4. Phase 4: 直接写（2 分钟）
   - 基于话题和渠道直接写
   - 不插入 claim_id
   - 写入 draft.md

5. Phase 5: 快速自查（30 秒）
   - 一次性检查逻辑和可读性
   - 生成 suggestions.md（不是 review-report.yaml）

6. Phase 6: 交付
   - 展示文章 + 可选改进建议
   - 不生成 acceptance-report.md
```

### 输出文件

```
runs/TASK_ID/
├── status.json              # 任务状态
├── draft.md                 # 文章正文
├── suggestions.md           # 可选改进建议（2-3 条）
└── references.md            # 参考来源（如果有）
```

### 用户体验

**启动**:
```
用户："快速写一篇关于 Claude 5 的文章，微信公众号"

Agent：[不询问确认，直接开始]
       正在撰写：Claude 5 发布解读
       渠道：微信公众号
       预计 4 分钟完成

       [进度] 正在搜集基本信息...
       [进度] 正在撰写...
       [进度] 快速检查...
```

**完成**:
```
文章已完成！

[显示正文]

可选改进：
- 第 3 段可以补充具体例子
- 标题可以更吸睛

要调整吗？（直接说要改哪，或"发布"）
```

### 实现要点

**✅ 做什么**:
- 能推断的默认值都用上（渠道格式、Persona、Voice Preset）
- 最少文件：只生成必要的
- 快速验证：只检查明显错误

**❌ 不做什么**:
- 不生成 capability-preflight.md
- 不生成 sources.yaml / claims.yaml
- 不生成 review-report.yaml
- 不生成 acceptance-report.md
- 不分证据层/编辑层/声音层审校
- 不逐个确认素材
- 不询问 Voice Preset
- 不问"内容契约是否满意"

## Standard Mode — 标准写作（**推荐**）

### 适用场景
- 热点速写：AI 新闻、产品发布解读
- 日常文章：微信公众号、知乎文章、技术博客
- 大部分写作需求（**80% 的场景应该用这个**）

### 核心特点
- **能稳定输出接近真人质量的文章**
- 平衡速度和质量
- 自动化为主，关键决策才询问
- 内部有证据追溯，但不暴露给用户

### 工作流程

```
1. Phase 0: 准备（1-2 分钟）
   - 确认话题、渠道、作者风格
   - 生成 content-contract.yaml（内部）
   - 默认 evidence_level: balanced

2. Phase 1-2: 调研（3-5 分钟）
   - 自动搜集素材（如果启用 auto_research）
   - 提取核心数据（价格、日期、性能指标）
   - 生成 sources.yaml（只包含核心数据来源）
   - 生成 brief.md

3. Phase 3: 大纲（2 分钟）
   - 规划文章结构
   - 确定关键论点
   - 不生成 storyboard（或极简版）

4. Phase 4: 撰写（5-8 分钟）
   - 基于 brief 和素材撰写
   - 只对核心数据插入 claim_id（内部）
   - 写入 draft.md

5. Phase 5: 三层审校（3-5 分钟）
   - 证据层：只检查核心数据准确性
   - 编辑层：逻辑、可读性、节奏
   - 声音层：表达自然度、AI 味
   - 生成 review-notes.md（不是打分报告）

6. Phase 6: 定稿
   - 展示文章 + 编辑建议
   - 用户选择应用或跳过
   - 生成 final.md
```

### 输出文件

```
runs/TASK_ID/
├── status.json              # 任务状态
├── content-contract.yaml    # 内容契约（内部）
├── brief.md                 # 调研简报
├── sources.yaml             # 核心数据来源（内部）
├── draft.md                 # 初稿
├── review-notes.md          # 编辑建议
└── final.md                 # 定稿
```

**不生成**:
- ❌ capability-preflight.md（改为内联到 content-contract）
- ❌ claims.yaml（claim_id 只在内存中维护）
- ❌ review-report.yaml（改为 review-notes.md）
- ❌ acceptance-report.md（改为简单确认）

### 用户体验

**启动**:
```
用户："写一篇关于 Claude 5 的文章"

Agent：准备撰写：Claude 5 发布解读
       
       确认几个细节：
       1. 发布渠道：微信公众号 / 知乎 / X Thread？
       2. 作者风格：用你常用的"卡兹克科技观察"？
       
       （输入数字或直接说，如"公众号，用卡兹克风格"）
```

**写作中**:
```
[进度] 正在搜集最新信息...
       ✓ 找到官方发布博客
       ✓ 找到社区早期反馈
       
[进度] 正在撰写...
       ✓ 开场：反问式引入
       ✓ 主体：三个关键变化
       ✓ 结尾：实用建议
       
[进度] 正在审校...
       ✓ 核心数据已验证
       ✓ 逻辑检查通过
```

**完成**:
```
文章已完成！

[显示正文]

已验证核心数据：
- 发布时间：2026 年 8 月（官方博客）
- 上下文窗口：200K（技术文档）
- 定价：$3/百万 tokens（定价页面）

编辑建议：
1. 第 5 段"然而"用得太频繁，可以换"不过"
2. 标题可选："Claude 5 来了" vs "Claude 5：新标杆"
3. 结尾可以加行动号召或保持克制

操作：
- "应用全部" — 应用所有建议
- "只改标题" — 指定应用哪些
- "跳过" — 直接定稿
- 或直接说要改的地方
```

### 实现要点

**✅ 做什么**:
- 自动搜集素材（如果话题需要最新信息）
- 核心数据验证（价格、日期、性能指标）
- 给出编辑建议（不是打分）
- 内部维护 claim_id（不暴露给用户）

**❌ 不做什么**:
- 不每个环节都问用户确认
- 不展示 sources.yaml 给用户
- 不说"claim_001 已验证"
- 不生成"验收报告"
- 不把所有陈述都标 claim_id

**平衡点**:
- 速度：15-20 分钟（不是 4 分钟也不是 1 小时）
- 质量：接近真人（不是完美也不是草稿）
- 交互：关键决策才问（不是全自动也不是每步确认）

## Deep Mode — 深度写作

### 适用场景
- 重要长文：年度总结、深度分析
- 严肃报道：调查性文章、技术白皮书
- 高风险内容：会被广泛引用的权威内容

### 核心特点
- 多 Agent 协作（需要 Handoff Runtime）
- 完整证据链追溯
- 三层审校（完整版）
- 最严格的质量标准

### 工作流程

```
1. Phase 0: 深度准备（5 分钟）
   - Editorial Strategist 分析话题
   - 生成详细的内容契约
   - 生成 capability-preflight.md
   - 设置 evidence_level: strict

2. Phase 1-2: 深度调研（15-20 分钟）
   - Researcher 多源调研
   - 交叉验证关键信息
   - 生成完整 sources.yaml 和 claims.yaml

3. Phase 3: 详细规划（10 分钟）
   - 生成详细 brief.md
   - 生成 storyboard
   - 规划论证路径

4. Phase 4: 协作撰写（20-30 分钟）
   - Writer 撰写主体
   - Editorial Strategist 插入关键转折
   - 每个事实性陈述都有 claim_id

5. Phase 5: 严格审校（15-20 分钟）
   - 证据层：逐个验证 claim_id
   - 编辑层：论证完整性
   - 声音层：专业性和客观性
   - Auditor 独立审查
   - 生成完整 review-report.yaml

6. Phase 6: 正式验收（5 分钟）
   - 生成 acceptance-report.md
   - 多维度质量确认
   - 交付包完整性检查
```

### 输出文件

```
runs/TASK_ID/
├── status.json
├── capability-preflight.md
├── content-contract.yaml
├── brief.md
├── storyboard.yaml
├── sources.yaml             # 完整来源档案
├── claims.yaml              # 每个主张都有 claim_id
├── draft.md
├── review-report.yaml       # 三层完整审校
├── revision-report.yaml
├── acceptance-report.md     # 正式验收
└── final.md
```

### 用户体验

**启动**:
```
用户："深度模式写一篇技术白皮书"

Agent：启动深度写作模式

       Editorial Strategist 正在分析话题...
       ✓ 识别出 5 个核心论点
       ✓ 规划 3 个论证路径
       
       预计耗时：1 小时 15 分钟
       
       内容契约：
       - 目标：技术白皮书
       - 深度：完整论证 + 证据链
       - 审校：三层严格审查
       
       确认开始？
```

**完成**:
```
深度写作已完成！

文章统计：
- 字数：8,500
- 论证链：3 条
- 引用来源：23 个
- 事实性陈述：47 个（全部已验证）

三层审校结果：
✓ 证据层：47/47 陈述已验证
✓ 编辑层：论证完整，逻辑严密
✓ 声音层：专业性强，客观中立

[显示正文]

查看详细审校报告？（"是" / "直接定稿"）
```

### 实现要点

**✅ 做什么**:
- 完整证据链（每个事实都有来源）
- 多 Agent 协作（Strategist、Researcher、Writer、Auditor）
- 详细的内部文档（对后续迭代有价值）
- 严格的质量门槛

**❌ 不做什么**:
- 不追求速度（质量优先）
- 不省略任何质量检查步骤
- 但仍然不要把 claim_id 暴露给用户

## 如何选择模式

### 决策树

```
用户请求
  ↓
明确说"快速" / "草稿" / "先看看"？
  ↓ 是
  Quick Mode
  
  ↓ 否
明确说"深度" / "严肃" / "白皮书" / "重要"？
  ↓ 是
  Deep Mode
  
  ↓ 否
  Standard Mode（默认）
```

### 关键词映射

**Quick Mode 触发词**:
- "快速"、"草稿"、"先看看"
- "测试一下"、"讨论稿"
- "给个初稿"

**Standard Mode**:
- 默认选择（没有明确指定模式时）
- "写一篇"、"帮我写"
- "公众号文章"、"热点解读"

**Deep Mode 触发词**:
- "深度"、"严肃"、"重要"
- "白皮书"、"技术报告"
- "调查性"、"权威"

### 不匹配时提醒

```
用户："快速写一篇 10000 字的深度技术分析"

Agent：检测到不匹配：
       - "快速" → Quick Mode（4-5 分钟）
       - "10000 字深度分析" → Deep Mode（1 小时+）
       
       建议：
       1. Quick Mode 先写个 2000 字草稿（5 分钟）
       2. Deep Mode 写完整版（1 小时+）
       
       选哪个？
```

## 模式对比总结

### 速度 vs 深度

```
Quick     ━━━━━━━━━━ 4-5 分钟   草稿质量
Standard  ━━━━━━━━━━━━━━━━━━ 15-20 分钟  真人质量  ← 推荐
Deep      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1 小时+   最高质量
```

### 文件数量

```
Quick:    3-4 个文件    （status, draft, suggestions, references）
Standard: 5-6 个文件    （+ brief, sources, review-notes）
Deep:     10+ 个文件    （+ capability-preflight, claims, storyboard, reports）
```

### 用户交互

```
Quick:    最少（能推断的都不问）
Standard: 平衡（关键决策才问）
Deep:     适中（重要环节需确认）
```

### 证据追溯

```
Quick:    relaxed  （防止明显错误）
Standard: balanced （核心数据验证）
Deep:     strict   （完整证据链）
```

## 迁移指南

### 从旧版本迁移

如果现有任务没有明确的模式定义：

1. **根据文件推断模式**:
   - 有 capability-preflight.md + claims.yaml → Deep
   - 有 sources.yaml 但无 claims.yaml → Standard
   - 只有 draft.md → Quick

2. **根据 handoff_runtime 推断**:
   - `handoff_runtime: available` → Deep
   - `handoff_runtime: unavailable` → Standard 或 Quick

3. **更新 status.json**:
   ```json
   {
     "mode": "standard",  // 推断出的模式
     "evidence_level": "balanced",  // 根据模式设置
     "inferred": true  // 标记这是推断的，不是用户指定的
   }
   ```

## 反模式

### ❌ 错误做法

**1. 所有模式都走相同流程**
```
错误：Quick Mode 也生成 capability-preflight.md 和 claims.yaml
正确：每个模式有不同的文件生成策略
```

**2. 用文件数量衡量质量**
```
错误："Deep Mode 生成 10+ 文件所以更好"
正确："Deep Mode 适合需要完整证据链的场景，不是所有场景"
```

**3. 让用户在三个模式间纠结**
```
错误："请选择 Quick / Standard / Deep"
正确：根据用户请求自动选择，必要时确认
```

**4. Standard Mode 不够好**
```
错误：把 Standard 当成"妥协版"
正确：Standard 应该是 80% 场景的最佳选择
       - 15-20 分钟出稿
       - 接近真人质量
       - 不需要用户等 1 小时
```

## 实现检查清单

### Quick Mode
- [ ] 不生成 capability-preflight.md
- [ ] 不生成 sources.yaml / claims.yaml
- [ ] 一次性审校 → suggestions.md
- [ ] 不询问 Voice Preset（用默认）
- [ ] 总耗时 < 5 分钟

### Standard Mode
- [ ] 默认 evidence_level: balanced
- [ ] 生成 sources.yaml（只包含核心数据）
- [ ] 三层审校（证据层只检查核心数据）
- [ ] 输出 review-notes.md（不是 review-report.yaml）
- [ ] 总耗时 15-20 分钟

### Deep Mode
- [ ] 默认 evidence_level: strict
- [ ] 生成完整 sources.yaml 和 claims.yaml
- [ ] 三层完整审校 → review-report.yaml
- [ ] 生成 acceptance-report.md
- [ ] 多 Agent 协作（需要 Handoff Runtime）

## 总结

- **Quick**: 快速草稿，4-5 分钟，3-4 个文件
- **Standard**: 真人质量，15-20 分钟，5-6 个文件（**推荐默认**）
- **Deep**: 最高质量，1 小时+，10+ 个文件

**核心原则**:
- 模式选择应该自动化（根据用户请求推断）
- 不同模式生成不同文件（不是都生成然后标记"未使用"）
- Standard Mode 是产品核心，不是妥协方案
- 速度和质量的平衡点在 Standard Mode
