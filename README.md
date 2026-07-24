# AI Writing Master - 智能写作大师

**融合深度流程与模块化设计的多平台写作系统**

实用型内容从两个问题开始：读者当前处于什么问题，读完文章后能获得什么具体变化。故事、表达、情绪和娱乐内容不强行套用。

选题 · 写作 · 洗稿 · 审校 · 配图 · 排版 · 发布 · 越用越像你

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Model: Opus 4.8 / Fable 5](https://img.shields.io/badge/Model-Opus%204.8%20%2F%20Fable%205-orange)](https://www.anthropic.com)
[![Skills](https://img.shields.io/badge/skills-2%20入口%20%2B%2010%20模块-8b5cf6)](#模块列表)

---

## 🎯 项目定位

这是一个为 Claude Code / Cursor 等 AI Agent 设计的**企业级写作系统**，融合：

1. **[auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub)** 的深度写作流程
   - 10步完整流程（从需求到发布）
   - 创意排水理论（排空废水，找到清水）
   - 三遍审校机制（内容→风格→细节）
   - Think Aloud 透明思考

2. **[wewrite](https://github.com/imraywang/wewrite)** 的模块化架构
   - 独立可组合的 skill 模块
   - 洗稿（rewrite）功能
   - 多平台改写（小红书/抖音）
   - CLI 工具支持

## ✨ 核心特性

### 🎭 两种工作模式

#### 模式1: 从零创作（完整流程）
```
"写一篇公众号文章"
  → 理解需求 → 搜索调研 → 选题讨论 → 风格学习
  → 创意排水 → 初稿创作 → 三遍审校 → 标题拟定
  → 配图准备 → 发布交付
```

#### 模式2: 洗稿改写（快速模式）
```
"把这篇文章改写成小红书版本"
  → 内容级真改 → 平台适配 → 质量检测 → 相似度门槛
```

### 🚀 主要优势

- ✅ **模块化设计** - 只要选题？只要洗稿？随意组合
- ✅ **状态管理** - 支持断点续写，跨会话不丢失进度
- ✅ **质量保证** - 三遍审校 + 编辑判断，AI味<30%
- ✅ **真实可信** - 绝不编造数据，所有信息可溯源
- ✅ **条件价值导向** - 实用型内容使用读者价值定义与价值承诺，其他内容按自身目的自然写作
- ✅ **风格学习** - 个人素材库，越用越像你
- ✅ **多平台** - 公众号/小红书/抖音/知乎，一稿多发
- ✅ **CLI支持** - 独立工具，不依赖AI也能用

---

## 📦 模块列表

### 核心入口

| Skill | 触发词 | 功能 |
|-------|--------|------|
| `writing-master` | "写一篇文章" | 完整创作流程入口 |
| `writing-rewrite` | "洗稿"、"改写" | 洗稿/改写入口 |

### 功能模块

| Skill | 功能 | 来源 |
|-------|------|------|
| `writing-topic` | 选题生成（热点+评分+去重） | wewrite |
| `writing-research` | 搜索调研+知识库管理 | auto-claude |
| `writing-style` | 风格学习+个人素材库 | auto-claude |
| `writing-drainage` | 创意排水（排废水找清水） | auto-claude |
| `writing-draft` | 初稿创作+框架生成 | 整合 |
| `writing-review` | 三遍审校+编辑判断 | 整合 |
| `writing-title` | 标题拟定（爆款+自然） | auto-claude |
| `writing-visual` | 配图生成+Prompt | wewrite |
| `writing-publish` | 排版+发布+18主题 | wewrite |
| `writing-multiplatform` | 多平台改写 | wewrite |
| `writing-learn` | 学习修改+范文库 | wewrite |
| `writing-stats` | 数据复盘+效果分析 | wewrite |

> 当前素材、排版与发布能力使用独立安装的 Baoyu Skills：`baoyu-article-illustrator`、`baoyu-cover-image`、`baoyu-infographic`、`baoyu-markdown-to-html`、`baoyu-post-to-wechat` 和 `baoyu-post-to-x`。普通写作任务不会自动触发这些能力。

---

## 🚀 快速开始

### 安装

```bash
# 方式1: 一键安装（推荐）
git clone https://github.com/NoApoNoTary/ai-writing-master.git ~/ai-writing-master
cd ~/ai-writing-master && bash install.sh

# 方式2: 手动安装 Skills
cd ~/.claude/skills/
ln -s ~/ai-writing-master/skills/* .

# 方式3: 安装 CLI 工具（可选）
cd ~/ai-writing-master
export PATH="$PWD/bin:$PATH"  # 添加到 ~/.bashrc 或 ~/.zshrc

# 验证安装
writing-master --version
writing-master --help
```

### 使用

#### 完整创作流程
```
你: 写一篇关于AI编程工具的公众号文章

AI:
【Think Aloud】
任务类型: 新写作任务（无brief）
平台: 微信公众号
模式: 完整流程（10步）
预计耗时: 2-3小时

Step 1: 理解需求...
[自动执行完整流程]
```

#### 洗稿模式
```
你: 把这篇文章洗稿成小红书版本
    [粘贴原文]

AI:
【洗稿模式】
源文章: 3200字公众号文章
目标平台: 小红书
改写策略: 内容级真改

→ 改写后: 1200字，6个emoji，3个标签
→ 质量评分: 72/100
→ 相似度: 0.42（通过）
```

---

## 📖 详细文档

- [快速开始指南](docs/quick-start.md)
- [完整流程说明](docs/workflow-guide.md)
- [洗稿使用手册](docs/rewrite-guide.md)
- [配置说明](docs/configuration.md)
- [API参考](docs/api-reference.md)
- [常见问题](docs/faq.md)

---

## 🎨 核心理念

### 1. 流程是指南，不是教条

### 2. 真实性 > 完美性

### 3. AI是搭档，不是替代品

### 4. 越用越像你

---

## 🛠️ 技术栈

- **AI模型**: Claude Opus 4.8 / Fable 5
- **开发工具**: Claude Code / Cursor
- **文件格式**: Markdown
- **CLI工具**: Python 3.11+ (可选，不依赖 pip)
- **状态管理**: YAML + JSON

### CLI 工具能力

不依赖 AI，独立可用：

```bash
# 质量评分（5维度检测）
writing-master quality article.md --verbose

# 相似度检测（防洗稿）
writing-master similarity source.md rewritten.md

# 状态目录
writing-master home
```

**质量评分维度**：
- 准确性（25%）：事实核对提醒
- 套话检测（20%）：14类AI套话黑名单
- 句子变化（15%）：句长标准差检查
- 段落节奏（10%）：段落长度多样性
- 副词密度（15%）：过度修饰检测
- 词汇丰富度（15%）：字符bigram多样性

**相似度算法**：字符3-gram Jaccard相似度，阈值≤0.6

---

## 📊 项目结构

```
ai-writing-master/
├── README.md                         # 项目说明
├── install.sh                        # 一键安装脚本
├── LICENSE                           # MIT 协议
├── pyproject.toml                    # Python 包配置
│
├── bin/                              # CLI 启动脚本
│   └── writing-master                # 命令行入口
│
├── src/                              # Python CLI 实现
│   └── writing_master/
│       ├── cli.py                    # 主调度器
│       └── commands/                 # 子命令
│           ├── quality.py            # 质量评分
│           └── similarity.py         # 相似度检测
│
├── skills/                           # Skills 目录（复制即用）
│   ├── writing-master/               # 主入口：完整创作流程
│   │   ├── SKILL.md                 # Skill 定义
│   │   └── references/              # 参考文档
│   │       ├── workflow.md          # 10步流程
│   │       ├── principles.md        # 核心原则
│   │       └── checkpoint.md        # 状态管理
│   │
│   ├── writing-rewrite/              # 洗稿入口
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── rewrite-guide.md     # 洗稿指南
│   │       └── quality-gates.md     # 质量门槛
│   │
│   ├── writing-topic/                # 选题生成
│   ├── writing-research/             # 搜索调研
│   ├── writing-style/                # 风格学习
│   ├── writing-drainage/             # 创意排水
│   ├── writing-draft/                # 初稿创作
│   ├── writing-review/               # 三遍审校
│   ├── writing-title/                # 标题拟定
│   ├── writing-visual/               # 配图生成
│   ├── writing-publish/              # 排版发布
│   └── writing-learn/                # 学习优化
│
├── cli/                              # CLI 工具（可选）
│   ├── pyproject.toml
│   └── src/writing_master/
│       ├── cli.py
│       ├── commands/
│       └── toolkit/
│
├── docs/                             # 文档
│   ├── quick-start.md
│   ├── workflow-guide.md
│   ├── rewrite-guide.md
│   └── ...
│
├── examples/                         # 示例
│   ├── complete-workflow/            # 完整流程示例
│   │   ├── brief.md
│   │   ├── draft-v1.md
│   │   ├── draft-v2.md
│   │   ├── draft-v3.md
│   │   └── final.md
│   └── rewrite-workflow/             # 洗稿示例
│       ├── source.md
│       ├── xiaohongshu.md
│       └── douyin.md
│
└── templates/                        # 模板文件
    ├── brief-template.md
    ├── cooperation-template.md
    └── review-checklist.md
```

## 🔧 用户状态目录

所有个人数据存储在 `~/.writing-master/`（仓库外）：

```
~/.writing-master/
├── config.yaml                       # 配置文件
├── style.yaml                        # 风格设置
├── history.yaml                      # 历史记录
├── playbook.md                       # 学习规则
│
├── runs/                             # 任务目录（支持断点续写）
│   ├── 20260724-001/
│   │   ├── status.json              # 任务状态
│   │   ├── brief.md                 # 需求文档
│   │   ├── knowledge.md             # 调研资料
│   │   ├── draft-v1.md              # 初稿
│   │   ├── draft-v2.md              # 审校v2
│   │   ├── draft-v3.md              # 审校v3
│   │   ├── final.md                 # 最终稿
│   │   ├── sources.yaml             # 信息来源
│   │   └── review-report.json       # 审校报告
│   └── 20260724-002/
│
├── personal_materials/               # 个人素材库
│   ├── articles/                    # 历史文章
│   ├── experiences/                 # 个人经历
│   └── topics/                      # 主题素材
│
├── exemplars/                        # 范文库
├── themes/                           # 自定义主题
└── output/                           # 输出文件
```

---

## 💡 使用场景

### 场景1: 从零开始写公众号文章

```
你: 写一篇关于 Claude Code 使用技巧的公众号文章

[AI 自动执行]
✅ Step 1: 创建 brief
✅ Step 2: 搜索调研（保存到知识库）
✅ Step 3: 提供3个选题方案
  
  选题1: 《Claude Code 让我效率翻倍的5个技巧》
  选题2: 《从 Cursor 迁移到 Claude Code：值得吗？》
  选题3: 《Claude Code 深度测评：优势与坑》

你选哪个？

你: 选1

✅ Step 4: 搜索个人素材库
✅ Step 5: 创意排水（5分钟快速草稿）
✅ Step 6: 创作初稿（保存为 draft-v1.md）
✅ Step 7: 第一遍审校（内容，保存为 draft-v2.md）
✅ Step 8: 第二遍审校（风格，保存为 draft-v3.md）
✅ Step 9: 第三遍审校（细节，保存为 final.md）
✅ Step 10: 标题拟定

标题方案：
1. 《Claude Code 让我效率翻倍的5个技巧》（自然版）
2. 《1周节省20小时！我用Claude Code发现的5个神技巧》（爆款版）
3. 《Claude Code：这5个功能，Cursor用户都羡慕哭了》（对比版）

你选哪个？
```

### 场景2: 洗稿/改写

```
你: 把这篇文章改写成小红书版本
    [粘贴3000字公众号文章]

[AI 执行]
✅ 分析源文章结构
✅ 提取核心观点
✅ 适配小红书平台特性
✅ 内容级真改（非简单缩写）
✅ 质量检测（评分72/100）
✅ 相似度检测（0.42，通过）

改写完成！

📄 小红书版本（1200字）
📸 建议配图6张
🏷️ 标签: #AI工具 #效率提升 #程序员必备
😊 Emoji密度: 适中

保存位置: ~/.writing-master/runs/20260724-002/xiaohongshu.md
```

### 场景3: 只要某个环节

```
你: 给我10个选题
→ 激活 writing-topic

你: 帮我审校这篇文章
→ 激活 writing-review

你: 配个封面
→ 激活 writing-visual

你: 学习我的修改
→ 激活 writing-learn
```

---

## 🎯 核心功能详解

### 1. 创意排水（Creative Drainage）

**理论来源**: Julian Shapiro 的"创意水龙头"理论

**核心思想**:
- 创意像管道中的水，最初流出的是"废水"（陈词滥调）
- 必须先排空废水，"清水"（独特创意）才会来

**操作流程**:
```
1. 快速草稿（5-10分钟）- 不加批判地写下第一反应
2. 识别"废水" - 标记套话、老生常谈
3. 挖掘"清水" - 寻找独特角度和个人经历
4. 正式写作 - 基于"清水"创作
```

### 2. 三遍审校机制

**第一遍：内容审校**
- ✅ 事实准确性
- ✅ 逻辑清晰度
- ✅ 结构合理性
- ✅ 段落迷你论点检查

**第二遍：风格审校（降AI味）**
- ❌ 删除套话："在当今时代"、"综上所述"
- ❌ 拆解AI句式："不仅...还..."、"既...又..."
- ✅ 替换书面词汇
- ✅ 加入真实细节
- ✅ 加入个人态度

**第三遍：细节打磨**
- 句子长度与节奏（15-25字为主，但要有变化）
- 段落长度（手机屏3-5行）
- 标点、排版、节奏

**效果**: AI味从60%降到<30%

### 3. 洗稿质量门槛

**双重质量门**:
1. **质量评分** ≥ 60/100
   - 准确性（25分）
   - 观点性（20分）
   - 实用性（20分）
   - 可读性（20分）
   - 平台适配（15分）

2. **相似度门槛** ≤ 0.6
   - 与源文章相似度
   - 与其他平台版本相似度
   - 确保真正改写，而非简单洗稿

**不通过 → 重写，最多2次**

---

## 🔒 核心原则（不可妥协）

### 1. 绝不编造数据 ❌

**反面案例**:
```
"根据最新研究，85%的用户表示..."  ← 这个数据是编的
```

**正确做法**:
```
"从评论区的反馈看，大部分人都在担心..."
或
"具体比例我没有数据，但评论区确实很多人在讨论"
```

### 2. 绝不使用过时信息 ❌

- 涉及技术、政策、数据必须搜索最新资料
- 标注时效性："截至2026年7月"

### 3. 绝不省略 Think Aloud ❌

每个关键决策都说明思考过程

### 4. 绝不跳过用户确认（重要决策）❌

涉及选题、风格、重大修改时必须征询意见

---

## 🆚 对比：本项目 vs 原项目

| 特性 | auto-claude | wewrite | ai-writing-master |
|------|-------------|---------|-------------------|
| 完整创作流程 | ✅ (10步) | ✅ (6步) | ✅ (整合10步) |
| 洗稿功能 | ❌ | ✅ | ✅ |
| 模块化设计 | ❌ | ✅ | ✅ |
| 状态管理 | ❌ | ✅ | ✅ |
| 创意排水 | ✅ | ❌ | ✅ |
| 三遍审校 | ✅ | ✅（简化） | ✅（完整） |
| CLI工具 | ❌ | ✅ | ✅ |
| 多平台 | 部分 | ✅ | ✅ |
| Think Aloud | ✅ | 部分 | ✅ |
| 推荐模型 | Sonnet 4.5 (过时) | 不限 | Opus 4.8 / Fable 5 |

---

## 📈 Roadmap

### v1.0 (当前)
- [x] 融合两个项目的核心功能
- [x] 模块化 skill 设计
- [x] 完整创作流程
- [x] 洗稿功能
- [x] 状态管理

### v1.1 (1-2周)
- [x] CLI 工具开发（quality + similarity）
- [ ] 完整示例文档
- [ ] 视频教程
- [ ] 单元测试

### v1.2 (1个月)
- [ ] 知乎平台支持
- [ ] 数据分析面板
- [ ] 自动化脚本
- [ ] 性能优化

### v2.0 (长期)
- [ ] Web UI 界面
- [ ] 团队协作
- [ ] 插件生态
- [ ] 多语言支持

---

## 🔗 推荐配合工具

### cheat-on-content - 内容效果预测系统

如果你想知道**哪些内容会爆**、想**数据驱动地提升选题能力**，强烈推荐配合使用：

**核心价值**：
- 📊 打分 → 🎯 盲预测 → 🚀 发布 → 📈 T+3天复盘 → 🧬 进化判断力
- 把每次"我感觉这条会爆"变成可校准的实验
- 一个月后你会有**只属于你的爆款公式**

**与 ai-writing-master 的配合**：
```
ai-writing-master          cheat-on-content
      ↓                           ↓
  选题 → 写作 → 审校           打分 → 预测
      ↓                           ↓
    final.md ────────────→   发布 → 复盘
                                  ↓
                              进化 rubric
                                  ↓
                          下次选题更准确 ←──┐
                                            │
                          影响下一轮 ────────┘
```

**完美互补**：
- ✅ ai-writing-master 负责**生产高质量内容**
- ✅ cheat-on-content 负责**选择正确方向**和**复盘学习**
- ✅ 一个让内容写得好，一个让你知道什么该写

**快速开始**：
```bash
# 1. 安装 cheat-on-content
git clone https://github.com/XBuilderLAB/cheat-on-content.git ~/cheat-on-content
cd ~/cheat-on-content && bash install.sh

# 2. 在内容项目目录初始化
初始化 cheat-on-content

# 3. 对 writing-master 生成的文章进行预测
启动预测 ~/.writing-master/runs/20260724-001/final.md

# 4. 发布3天后复盘
复盘 videos/2026-07-24_001/
```

**项目地址**：https://github.com/XBuilderLAB/cheat-on-content

---

## 🤝 贡献指南

欢迎各种形式的贡献！

### 贡献方式
- 🐛 提交 Bug 报告
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码 PR

### 开发规范
- 遵循 Markdown 格式规范
- 每个 skill 必须包含 SKILL.md 和 references/
- 保持向后兼容
- 添加测试用例

---

## 📄 License

MIT License

你可以自由使用、修改、商用。唯一要求：保留原作者版权声明。

---

## 🙏 致谢

感谢以下项目提供灵感和基础：

- [auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub) by MapleShaw
- [wewrite](https://github.com/imraywang/wewrite) by imraywang
- [Claude](https://www.anthropic.com/claude) by Anthropic

---

## 📞 联系方式

- GitHub Issues: [提交问题](https://github.com/YOUR_USERNAME/ai-writing-master/issues)
- Discussions: [参与讨论](https://github.com/YOUR_USERNAME/ai-writing-master/discussions)

---

<div align="center">

**用 AI 赋能创作，而不是替代创作**

Made with ❤️ by AI Writing Master Team

[快速开始](#快速开始) · [查看文档](docs/) · [提交反馈](https://github.com/YOUR_USERNAME/ai-writing-master/issues)

</div>
