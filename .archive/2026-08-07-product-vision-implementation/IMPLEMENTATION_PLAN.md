# 实现计划：从证据审查系统到速写助手

## 目标

根据 PRODUCT_VISION.md，将 AI Writing Master 从"证据审查系统"转型为"AI 热点速写助手"。

## 短期实现（1-3 个月）- 本次完成

### 1. 标准模式优化 ✓ (文档已完成)

**目标**: 让 `balanced` 证据等级成为默认

**已完成**:
- ✅ PRODUCT_VISION.md 明确了 `balanced` 作为标准模式的定位
- ✅ DESIGN_PRINCIPLES.md 详细说明了三个证据等级的行为差异
- ✅ AGENT.md 给 AI 明确指示避免过度强调证据

**待实现**:
- [ ] 在 Skill 的 phase-0 中添加 `evidence_level` 参数（默认 balanced）
- [ ] 修改审校流程：balanced 模式只检查核心数据，不要求所有陈述都有 claim_id
- [ ] 快速模式不生成 sources.yaml/claims.yaml

### 2. 交互简化 ✓ (设计已完成)

**目标**: 减少确认点，只在关键决策时才停下来

**已完成**:
- ✅ DESIGN_PRINCIPLES.md 明确了"不要每个环节都问用户"
- ✅ 去掉了 Personal Context 的 `ask_before_use`（改为导入时标记）

**待实现**:
- [ ] 简化内容契约确认：合并相关字段，只问阻断性问题
- [ ] Voice Preset 默认"自然默认"，不单独询问
- [ ] 素材接收不要逐个确认，批量展示即可

### 3. 快速模式真正快起来 (需实现)

**目标**: 4-5 分钟出稿，不生成大量 YAML

**待实现**:
- [ ] 快速模式跳过 capability-preflight.md
- [ ] 快速模式只生成：brief.md + draft.md + references.md（简单列表）
- [ ] 不生成：sources.yaml, claims.yaml, review-report.yaml, acceptance-report.md
- [ ] 一次性审校（不分证据层/编辑层/声音层）

### 4. 自动调研（部分设计，需实现）

**目标**: 用户说主题，系统自动去找最新信息

**已有基础**:
- 已有 baoyu-url-to-markdown 集成
- 已有 Context-aware Research Brief 机制

**待实现**:
- [ ] Phase 1 增加 `auto_research: enabled` 模式
- [ ] 自动调用 web_search 或 aihot skill
- [ ] 找到素材后直接进入写作，不等用户确认"素材已接收"

## 实现优先级

### P0 - 本次必须完成
1. ✅ 文档体系（PRODUCT_VISION, DESIGN_PRINCIPLES, AGENT.md）
2. ✅ 清理内部文档，防止用户困惑
3. [ ] 在 Skill 中添加 `evidence_level` 配置支持
4. [ ] 快速模式简化（不生成大量 YAML）

### P1 - 下一个迭代
5. [ ] 自动调研实现
6. [ ] 内容契约简化
7. [ ] 标准模式审校优化（balanced 行为）

### P2 - 后续优化
8. [ ] Personal Context 的 `ask_before_use` 迁移逻辑
9. [ ] Voice Preset 默认行为调整

## 本次实现范围

由于这是文档和架构调整的第一步，本次主要完成：

### ✅ 已完成
1. 产品定位文档（PRODUCT_VISION.md）
2. 技术实现原则（DESIGN_PRINCIPLES.md）
3. AI Agent 指南（AGENT.md）
4. 清理 27 个内部开发文档
5. 修复文档链接和测试

### 🎯 本次新增实现

#### A. Skill 层面支持 evidence_level

在 `skills/writing-master/references/` 中添加 evidence-level 配置文件，明确三种模式的行为差异。

#### B. 快速模式简化

修改 Skill 的快速模式定义，明确不生成哪些文件。

#### C. 创建迁移指南

为已有运行目录提供迁移说明，避免破坏现有任务。

## 不在本次范围

以下内容需要更大的架构调整，留待后续迭代：

- ❌ 自动调研实现（需要集成 web_search 或外部 API）
- ❌ Personal Context 的 visibility 迁移逻辑（需要数据迁移工具）
- ❌ 审校流程重构（需要重写 phase-5）
- ❌ Voice Preset 默认行为（需要修改 content-contract 确认流程）

## 验收标准

### 文档层面 ✅
- [x] PRODUCT_VISION.md 明确产品定位
- [x] DESIGN_PRINCIPLES.md 提供实现规则
- [x] AGENT.md 给 AI 明确边界
- [x] 所有测试通过

### 实现层面 (本次)
- [ ] evidence-levels.md 定义三种证据等级
- [ ] mode-definitions.md 更新快速模式定义
- [ ] MIGRATION_GUIDE.md 提供迁移说明

### 用户体验层面 (验证)
- [ ] 新启动 Skill 时，Agent 不再过度强调证据追溯
- [ ] 快速模式生成的文件数量明显减少
- [ ] 标准模式的输出读起来像"文章"而不是"报告"

## 归档与清理

### 归档位置
本次实现过程产生的临时文件将归档到：
- `.archive/2026-08-07-product-vision-implementation/`

### 归档内容
- 本实现计划（IMPLEMENTATION_PLAN.md）
- 实现过程中的笔记和决策记录
- 临时测试文件

### 清理标准
- 所有临时文件移到 .archive/
- 仓库根目录不留实现过程文件
- 只保留最终的产品文档和代码改动

## 下一步

1. 创建 evidence-levels.md
2. 更新 mode-definitions.md
3. 创建 MIGRATION_GUIDE.md
4. 验证 Agent 行为
5. 归档本计划文档
6. 创建 PR 并审计
7. 合并到主分支
