---
name: writing-master
description: |
  AI Writing Master 主入口：完整的内容创作流程，支持从零创作和洗稿改写两种模式。
  融合深度流程（10步完整创作）与模块化设计（可独立调用）。
  触发关键词：写文章、写公众号、完整创作、从零开始。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# Writing Master — 智能写作大师主入口

## 🎯 核心理念

**流程是指南，不是教条；核心原则不可妥协。**

### 可灵活调整
- ✅ 用户明确要求跳过某步骤 → 可以（但提醒风险）
- ✅ 任务特别简单/紧急 → 可简化流程
- ✅ 上下文已包含信息 → 不重复操作

### 核心原则（不可妥协）
- ❌ **绝不编造数据**
- ❌ **绝不使用过时信息**
- ❌ **绝不省略Think Aloud**
- ❌ **绝不跳过用户确认（重要决策）**

---

## 🔄 运行约定

- **{home}** = `$WRITING_MASTER_HOME` 或 `~/.writing-master`
- **{skill_dir}** = 本 skill 目录
- **读取: <路径>** = 真实读取该文件，不是注释
- **状态管理**: 由 AI 直接创建和维护目录结构与状态文件，无需外部工具

---

## 📋 任务类型判断

收到任务后，先判断类型并 **Think Aloud**：

### A. 新写作任务（有完整需求）
→ 完整10步流程

### B. 新写作任务（无需求只有主题）
→ 先创建 brief，再走完整流程

### C. 洗稿/改写任务
→ 转 `writing-rewrite` skill

### D. 修改已有文章
→ 读取原文 → 理解需求 → 修改 → 审校

### E. 文章审校/降AI味
→ 直接进入三遍审校流程

### F. 单一模块需求（只要选题/只要配图等）
→ 路由到对应 skill

---

## 🚀 完整创作流程（10步）

```
读取: {skill_dir}/references/workflow.md
```

执行完整10步流程时，每步开始前 **Think Aloud** 说明：
- 当前步骤
- 为什么执行这一步
- 预期产出

### Step 0: 初始化任务

1. 检查环境（确认 {home} 目录存在，不存在则创建）
2. 创建任务目录：`{home}/runs/YYYYMMDD-XXX/`
3. 初始化状态文件：`status.json`

```json
{
  "task_id": "20260724-001",
  "created_at": "2026-07-24T10:00:00Z",
  "mode": "complete",
  "platform": "wechat",
  "status": "in_progress",
  "current_step": "brief",
  "steps": {
    "brief": "pending",
    "research": "pending",
    "topic": "pending",
    "style": "pending",
    "drainage": "pending",
    "draft": "pending",
    "review1": "pending",
    "review2": "pending",
    "review3": "pending",
    "title": "pending",
    "visual": "pending",
    "publish": "pending"
  }
}
```

### Step 1: 理解需求 & 保存 Brief

**操作**：
1. 与用户确认写作需求（如信息不完整）
2. 读取 `{skill_dir}/references/reader-value.md`
3. 判断文章是否以解释、判断、解决问题或指导行动为主要目的
4. 适用时完成“读者价值定义”和“价值承诺”；故事、表达、情绪、娱乐等内容跳过
5. 创建 `brief.md` 保存到任务目录

**Brief 模板**：
```markdown
# 写作 Brief

## 基本信息
- 主题：
- 目标读者：
- 预计字数：
- 截止时间：

## 核心需求
- 文章目的：
- 必须包含的内容：
- 必须排除的内容：

## 读者价值定义（适用时填写）
- 目标读者：
- 当前问题：
- 阅读后的具体变化：

## 价值承诺（适用时填写）
读完这篇文章，[目标读者] 将能够 [具体变化]，从而 [进一步价值]。

## 跳过说明（不适用时填写）
- 内容主要目的：故事 / 表达 / 情绪 / 娱乐 / 其他

## 特殊要求
- 是否需要真实测试：
- 是否需要配图：
- 其他要求：
```

**完成后**：
保存 brief 到 `{home}/runs/{task_id}/brief.md`，更新 `status.json` 中 brief 步骤状态为 "completed"

---

### Step 2: 搜索调研 & 知识库

**触发条件**：
- ✅ 涉及新概念/新方法
- ✅ 涉及2025-2026年的新技术、新工具
- ✅ 需要业界最佳实践

**操作**：
1. 使用 WebSearch 多渠道搜索
2. 保存到 `knowledge.md`

**知识库格式**：
```markdown
# 主题调研

## 元信息
- 收集时间：2026-07-24
- 下次更新：2026-08-24
- 信息来源：[列出所有链接]

## 核心内容
[整理的信息]

## 关键要点
- 要点1
- 要点2
```

**完成后**：
保存 knowledge.md 到 `{home}/runs/{task_id}/knowledge.md`，更新 `status.json` 中 research 步骤状态为 "completed"

---

### Step 3: 选题讨论 ⭐⭐⭐ 必做

**重要性**：避免方向错误的关键步骤！

**绝不要直接写文章！必须先讨论选题！**

**操作**：
1. **Think Aloud**：说明思考过程
2. 提供 **3-4个选题方向**
3. **等待用户选择**

**每个选题包含**：
```markdown
### 选题X：[标题]

**核心角度**：
[从什么角度切入]

**工作量评估**：⭐⭐⭐（1-5星）

**优势**：
- 优势1
- 优势2

**劣势**：
- 劣势1

**大纲预览**：
1. 部分1（预计500字）
2. 部分2（预计800字）
```

**完成后**：
保存选题讨论和用户选择到 `{home}/runs/{task_id}/topic.md`，更新 `status.json` 中 topic 步骤状态为 "completed"

---

### Step 4: 风格学习 & 个人素材库 ⭐⭐⭐

**目标**：确保文章风格像用户本人

**操作**：
1. 读取 `{home}/personal_materials/` 中的历史文章
2. 使用 Grep 搜索相关素材
3. **Think Aloud**：提取到的风格特征

**提取内容**：
- ✅ 开头方式
- ✅ 结构偏好
- ✅ 语言特征（句式、节奏、常用词汇）
- ✅ 真实案例和个人经历

**完成后**：
保存风格学习结果到 `{home}/runs/{task_id}/style.md`，更新 `status.json` 中 style 步骤状态为 "completed"

---

### Step 5: 创意排水 ⭐（推荐）

```
读取: {skill_dir}/references/creative-drainage.md
```

**操作流程**：
1. 快速草稿（5-10分钟）→ 不加批判地写
2. 识别"废水" → 标记套话、陈词滥调
3. 挖掘"清水" → 寻找独特角度
4. 如果 `brief.md` 中存在价值承诺，对照它优先保留能帮助读者获得承诺变化的内容；不存在时不强行套用
5. 进入正式写作

**完成后**：
保存创意排水过程和"清水"创意到 `{home}/runs/{task_id}/drainage.md`，更新 `status.json` 中 drainage 步骤状态为 "completed"

---

### Step 6: 创作初稿

**写作原则**：
- ✅ 基于真实数据写作
- ✅ 基于"清水"创意
- ✅ 保持风格一致
- ✅ 加入真实案例
- ✅ 自然融入个人经验
- ✅ 如果 `brief.md` 中存在价值承诺，正文持续服务于它；不存在时按文章自身目的自然展开

**保存**：`draft-v1.md`

**完成后**：
保存初稿到 `{home}/runs/{task_id}/draft-v1.md`，更新 `status.json` 中 draft 步骤状态为 "completed"

---

### Step 7-9: 三遍审校 ⭐⭐⭐

```
读取: {skill_dir}/references/three-pass-review.md
```

**第一遍：内容审校** → `draft-v2.md`
- 事实准确性
- 逻辑清晰度
- 结构合理性
- 段落迷你论点检查
- 如果存在价值承诺，检查读者是否获得了承诺中的具体变化

**第二遍：风格审校（降AI味）** → `draft-v3.md`
- 删除套话
- 拆解AI句式
- 替换书面词汇
- 加入真实细节

**第三遍：细节打磨** → `final.md`
- 句子长度与节奏
- 段落长度
- 标点、排版

**完成后**：
保存三遍审校结果：
- `{home}/runs/{task_id}/draft-v2.md`（第一遍：内容审校）
- `{home}/runs/{task_id}/draft-v3.md`（第二遍：风格审校）
- `{home}/runs/{task_id}/final.md`（第三遍：细节打磨）
更新 `status.json` 中 review1、review2、review3 步骤状态为 "completed"

---

### Step 10: 标题拟定 ⭐⭐⭐

```
读取: {skill_dir}/references/title-guide.md
```

**提供3-5个方案**：
1. 自然版（符合作者风格）
2. 爆款版（注入吸引要素）
3. 组合版（平衡吸引力与质感）

**等待用户选择**

**完成后**：
保存标题方案和用户选择到 `{home}/runs/{task_id}/title.md`，将最终标题添加到 `final.md` 顶部，更新 `status.json` 中 title 步骤状态为 "completed"，整体状态更新为 "completed"

---

## 🎨 可选后续动作

### A. 配图
读取 `{skill_dir}/references/baoyu-integration.md`，在用户明确要求配图时路由到 `baoyu-article-illustrator`；封面路由到 `baoyu-cover-image`；信息图路由到 `baoyu-infographic`。

### B. 排版与发布
读取 `{skill_dir}/references/baoyu-integration.md`。公众号 HTML 路由到 `baoyu-markdown-to-html`，公众号发布路由到 `baoyu-post-to-wechat`，X 发布路由到 `baoyu-post-to-x`。

---

## 🔧 模块路由

当用户只要某个功能时，路由到对应 skill：

| 用户需求 | 路由到 |
|---------|--------|
| 只要选题 | `writing-topic` |
| 洗稿/改写 | `writing-rewrite` |
| 只审校 | `writing-review` |
| 只配图 | `baoyu-article-illustrator` |
| 只生成封面 | `baoyu-cover-image` |
| 只生成信息图 | `baoyu-infographic` |
| 发布公众号 | `baoyu-post-to-wechat` |
| 发布 X | `baoyu-post-to-x` |
| 学习修改 | `writing-learn` |
| 数据复盘 | `writing-stats` |

---

## 💾 状态管理

每步完成后更新 `status.json`，支持断点续写。

用户说"继续上次"时：
1. 读取 `{home}/runs/` 下最近的未完成任务
2. 查看 `status.json` 确定当前步骤
3. 从该步骤继续执行

---

## 🚨 错误处理

步骤失败时：
1. 在 `status.json` 中标记该步骤状态为 "failed"
2. 记录错误原因
3. 保留当前任务，下次恢复后重做失败步骤

---

## 📖 参考文档

本 skill 自带详细参考文档：

- `workflow.md` - 完整流程说明
- `creative-drainage.md` - 创意排水详解
- `three-pass-review.md` - 三遍审校详解
- `reader-value.md` - 读者价值定义与价值承诺
- `baoyu-integration.md` - 可选素材、排版与发布路由
- `title-guide.md` - 标题拟定指南
- `principles.md` - 核心原则
- `checkpoint.md` - 状态管理

---

**开始创作前，记得 Think Aloud！**
