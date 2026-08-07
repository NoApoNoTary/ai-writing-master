# Migration Guide — 迁移指南

## 概述

本文档说明如何将现有的运行目录和工作流迁移到新的产品定位（从"证据审查系统"到"速写助手"）。

## 变更摘要

### 产品定位变化

**之前**:
- 强调证据追溯和审查
- 每个环节都需要用户确认
- 生成大量内部状态文件（YAML、报告）
- 用合规语言（验收、审计、预检）

**现在**:
- 强调速写和表达自然
- 自动化为主，关键决策才询问
- 精简输出文件（内部机制不暴露）
- 用创作语言（准备、撰写、打磨、定稿）

### 核心原则不变

✅ **保留的机制**:
- 证据追溯（作为内部质量保障）
- 来源登记（sources.yaml）
- 三层审校（证据层、编辑层、声音层）
- Personal Context 和 Persona 系统

❌ **改变的是表现形式**:
- 不把 `claim_id` 暴露给用户
- 不生成用户看不懂的 `.yaml` 报告
- 不用"验收"、"审计"等合规词汇
- 不在每个环节停下来问用户

## 新增概念

### 1. Evidence Level（证据等级）

新增三个等级来控制证据追溯的强度：

| 等级 | 模式 | 行为 |
|------|------|------|
| `relaxed` | Quick | 不生成 sources.yaml/claims.yaml |
| `balanced` | Standard | 只验证核心数据，不要求所有陈述都有来源 |
| `strict` | Deep | 完整证据链，每个事实都有 claim_id |

**默认**: Standard Mode 使用 `balanced`。

### 2. 精简的文件结构

**Quick Mode**:
```
runs/TASK_ID/
├── status.json
├── draft.md
├── suggestions.md
└── references.md
```

**Standard Mode**:
```
runs/TASK_ID/
├── status.json
├── content-contract.yaml
├── brief.md
├── sources.yaml          # 只包含核心数据来源
├── draft.md
├── review-notes.md       # 替代 review-report.yaml
└── final.md
```

**Deep Mode**:
```
runs/TASK_ID/
├── status.json
├── capability-preflight.md
├── content-contract.yaml
├── brief.md
├── storyboard.yaml
├── sources.yaml          # 完整来源档案
├── claims.yaml
├── draft.md
├── review-report.yaml
├── revision-report.yaml
├── acceptance-report.md
└── final.md
```

### 3. 新的用户体验语言

| 旧词汇 | 新词汇 |
|--------|--------|
| capability-preflight | preparation（准备） |
| acceptance-report | final-check（定稿确认） |
| Auditor | Editor（编辑） |
| claim_id | ref（内部引用） |
| 验收通过 | 文章已完成 |
| 审计 | 审校/检查 |

## 迁移场景

### 场景 1: 现有运行目录

**问题**: 已有的 `~/.writing-master/runs/` 目录包含旧格式的任务。

**解决方案**: 自动推断 + 向后兼容

1. **读取旧任务时**:
   ```python
   status = read_status_json(task_id)
   
   # 如果没有 evidence_level 字段，根据 mode 推断
   if 'evidence_level' not in status:
       status['evidence_level'] = infer_evidence_level(status['mode'])
       status['inferred'] = True
       write_status_json(task_id, status)
   ```

2. **推断规则**:
   ```python
   def infer_evidence_level(mode):
       if mode == 'quick':
           return 'relaxed'
       elif mode == 'deep':
           return 'strict'
       else:  # standard or unknown
           return 'balanced'
   ```

3. **兼容性**:
   - 旧任务即使没有 `evidence_level` 也能继续运行
   - 首次读取时自动补充字段
   - 所有等级都支持读取 sources.yaml/claims.yaml（如果存在）

### 场景 2: 恢复旧任务

**问题**: 用户想恢复一个之前暂停的任务。

**解决方案**: 读取时自动迁移

```python
def resume_task(task_id):
    status = read_status_json(task_id)
    
    # 补充缺失的字段
    if 'evidence_level' not in status:
        status['evidence_level'] = infer_evidence_level(status.get('mode', 'standard'))
        status['inferred'] = True
    
    # 检查文件结构
    run_dir = get_run_dir(task_id)
    existing_files = list_files(run_dir)
    
    # 根据现有文件推断原始模式（如果 status.json 中没有）
    if 'mode' not in status:
        if 'capability-preflight.md' in existing_files:
            status['mode'] = 'deep'
        elif 'sources.yaml' in existing_files:
            status['mode'] = 'standard'
        else:
            status['mode'] = 'quick'
    
    # 保存更新后的状态
    write_status_json(task_id, status)
    
    # 继续任务
    continue_from_phase(task_id, status['phase'])
```

### 场景 3: Personal Context 的 visibility

**问题**: 旧的 Personal Context 使用 `ask_before_use`，新设计不再需要这个。

**解决方案**: 渐进迁移

1. **读取时兼容**:
   ```python
   def load_personal_context(file_path):
       ctx = read_yaml(file_path)
       
       # 兼容旧的 visibility 值
       if ctx.get('visibility') == 'ask_before_use':
           # 默认视为 available（用户已提供即允许使用）
           ctx['visibility'] = 'available'
           ctx['migrated_from'] = 'ask_before_use'
       
       return ctx
   ```

2. **新建时使用新规则**:
   ```yaml
   visibility: private | available | publishable
   # 不再有 ask_before_use
   ```

3. **不强制迁移旧文件**:
   - 旧文件继续有效
   - 读取时自动转换
   - 用户不需要手动更新

### 场景 4: Skill 的 SKILL.md 指令

**问题**: Skill 的旧指令可能过度强调证据追溯。

**解决方案**: 优先读取新文档

1. **文档优先级**:
   ```
   1. skills/writing-master/AGENT.md        ← AI 明确指引
   2. skills/writing-master/DESIGN_PRINCIPLES.md  ← 实现规则
   3. docs/PRODUCT_VISION.md                ← 产品定位
   4. skills/writing-master/SKILL.md        ← 原有 Skill 定义
   ```

2. **在 AGENT.md 中明确**:
   - 证据追溯是基础设施，不是产品特性
   - 不把 `claim_id` 暴露给用户
   - 用创作语言，不用合规语言

3. **Skill 的 Phase 指令兼容**:
   - 保留所有 Phase 的原有逻辑
   - 但根据 `evidence_level` 调整行为
   - `balanced` 模式下不强制生成所有 YAML

## 实现步骤

### 步骤 1: 更新 status.json 结构

**新增字段**:
```json
{
  "task_id": "writing-20260807-001",
  "mode": "standard",
  "evidence_level": "balanced",    // 新增
  "phase": "phase-4-writing",
  "created_at": "2026-08-07T10:00:00Z",
  "updated_at": "2026-08-07T10:15:00Z"
}
```

**向后兼容**:
- 旧 `status.json` 没有 `evidence_level` 时自动推断
- 推断后写回文件，下次读取时就有了

### 步骤 2: Phase 0 支持 evidence_level

**在内容契约中记录**:
```yaml
# content-contract.yaml
mode: standard
evidence_level: balanced
target_id: wechat
topic: "Claude 5 发布解读"
persona: khazix-writer
voice_preset: natural-default
```

**设置逻辑**:
```python
def determine_evidence_level(mode, user_request):
    # 用户明确指定时优先
    if 'relaxed' in user_request or 'strict' in user_request:
        return extract_evidence_level(user_request)
    
    # 否则根据模式默认
    defaults = {
        'quick': 'relaxed',
        'standard': 'balanced',
        'deep': 'strict'
    }
    return defaults.get(mode, 'balanced')
```

### 步骤 3: Phase 1-2 根据 evidence_level 调整

**relaxed**:
```python
if evidence_level == 'relaxed':
    # 不生成 sources.yaml
    # 只提取关键信息到 brief.md
    skip_source_registration()
```

**balanced**:
```python
if evidence_level == 'balanced':
    # 只登记核心数据来源
    register_core_data_sources(prices, dates, metrics)
    # 观点和经历不需要登记
```

**strict**:
```python
if evidence_level == 'strict':
    # 完整来源登记
    register_all_sources()
    generate_claims_yaml()
```

### 步骤 4: Phase 4 插入 claim_id 的条件

**不是所有模式都插入**:
```python
def should_insert_claim_id(statement, evidence_level):
    if evidence_level == 'relaxed':
        return False  # 快速模式不插入
    
    if evidence_level == 'balanced':
        # 只对核心数据插入
        return is_core_data(statement)  # 价格、日期、性能指标
    
    if evidence_level == 'strict':
        # 所有事实性陈述都插入
        return is_factual_claim(statement)
```

### 步骤 5: Phase 5 审校简化

**balanced 模式的证据层**:
```python
def evidence_layer_review(draft, evidence_level):
    if evidence_level == 'relaxed':
        return quick_fact_check(draft)  # 只检查明显错误
    
    if evidence_level == 'balanced':
        # 只检查核心数据
        return verify_core_data(draft)  # 不要求所有陈述都有来源
    
    if evidence_level == 'strict':
        return full_verification(draft)  # 逐个验证 claim_id
```

**输出格式**:
```python
if evidence_level in ['relaxed', 'balanced']:
    generate_review_notes_md()  # 用户友好的 Markdown
else:
    generate_review_report_yaml()  # 完整的结构化报告
```

### 步骤 6: Phase 6 验收简化

**Quick Mode**:
```python
if mode == 'quick':
    # 不生成 acceptance-report.md
    return deliver_draft_directly()
```

**Standard Mode**:
```python
if mode == 'standard':
    # 简化验收：只确认核心数据和文章质量
    return simple_acceptance_check()
```

**Deep Mode**:
```python
if mode == 'deep':
    # 完整验收报告
    return generate_acceptance_report()
```

## 测试迁移

### 测试用例 1: 恢复旧任务

```bash
# 创建一个旧格式的任务
mkdir -p ~/.writing-master/runs/test-old-task
echo '{"task_id": "test-old-task", "mode": "standard", "phase": "phase-4-writing"}' > \
  ~/.writing-master/runs/test-old-task/status.json

# 恢复任务（应该自动补充 evidence_level）
./bin/writing-master resume test-old-task

# 验证 status.json 已更新
cat ~/.writing-master/runs/test-old-task/status.json
# 应该包含: "evidence_level": "balanced"
```

### 测试用例 2: Quick Mode 不生成 YAML

```bash
# 启动快速模式
./bin/writing-master quick "写一篇关于 AI 的文章"

# 检查生成的文件
ls ~/.writing-master/runs/$(latest_task_id)/

# 应该只有:
# - status.json
# - draft.md
# - suggestions.md
# - references.md (如果有素材)

# 不应该有:
# - sources.yaml
# - claims.yaml
# - review-report.yaml
```

### 测试用例 3: Standard Mode 只验证核心数据

```bash
# 启动标准模式
./bin/writing-master write "Claude 5 发布解读，微信公众号"

# 检查 sources.yaml
cat ~/.writing-master/runs/$(latest_task_id)/sources.yaml

# 应该只包含核心数据来源:
# - 价格、日期、性能指标的来源
# 不应该包含:
# - 作者观点的"来源"
# - 常识性陈述的"来源"
```

## 回滚策略

如果新行为导致问题，可以临时回滚：

### 临时使用 strict 模式

```bash
# 对单个任务强制使用严格模式
./bin/writing-master write "..." --evidence-level strict

# 或在环境变量中设置默认
export WRITING_MASTER_EVIDENCE_LEVEL=strict
./bin/writing-master write "..."
```

### 检查是否是迁移导致的问题

```bash
# 查看任务的 evidence_level 是推断的还是明确指定的
cat ~/.writing-master/runs/TASK_ID/status.json | jq '.inferred'

# 如果是 true，说明是自动推断的
# 如果是 false 或不存在，说明是用户明确指定的
```

## 常见问题

### Q1: 旧任务能否继续运行？

**A**: 可以。旧任务首次读取时会自动补充 `evidence_level` 字段，然后按新规则继续。

### Q2: 我想要旧的严格模式怎么办？

**A**: 使用 Deep Mode 或明确指定 `--evidence-level strict`。

### Q3: Personal Context 的 `ask_before_use` 怎么办？

**A**: 读取时自动转换为 `available`，不需要手动迁移。

### Q4: 现有的 Skill 指令会冲突吗？

**A**: 不会。AGENT.md 和 DESIGN_PRINCIPLES.md 优先级更高，会覆盖旧指令中的过度证据要求。

### Q5: 如何验证迁移成功？

**A**: 观察新启动的 Standard Mode 任务：
- 输出文件数量应该是 5-6 个（不是 10+）
- 用户看到的是"文章 + 编辑建议"（不是"验收报告"）
- Agent 不会说"claim_001 已验证"（会说"Claude 5 定价已验证"）

## 总结

### 核心变更

1. ✅ **新增 evidence_level 参数**（relaxed / balanced / strict）
2. ✅ **精简输出文件**（根据模式和证据等级）
3. ✅ **改进用户体验语言**（创作语言替代合规语言）
4. ✅ **向后兼容**（旧任务自动迁移）

### 不需要手动迁移的内容

- ❌ 现有运行目录（自动推断 evidence_level）
- ❌ Personal Context 文件（读取时自动转换）
- ❌ Skill 指令（新文档优先级更高）

### 验收标准

- [ ] 旧任务能正常恢复和继续
- [ ] Quick Mode 只生成 3-4 个文件
- [ ] Standard Mode 不过度强调证据
- [ ] Deep Mode 保持完整证据链
- [ ] 用户体验使用创作语言（不是合规语言）

### 下一步

1. 测试迁移逻辑（见"测试迁移"章节）
2. 更新 Skill 的 Phase 指令（根据 evidence_level 调整）
3. 验证用户体验（启动几个测试任务）
4. 监控是否有兼容性问题
5. 收集用户反馈并迭代
