# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-24

### Added

#### CLI 工具 🎉
- **quality** 命令：5维度写作质量评分
  - 准确性检测（提醒人工核对）
  - AI套话检测（14类黑名单）
  - 句子长度变化检测
  - 段落节奏检测
  - 副词密度检测
  - 词汇丰富度检测（字符bigram多样性）
  - 支持 `--verbose` 详细报告和 `--json` JSON输出
- **similarity** 命令：字符3-gram Jaccard相似度检测
  - 支持多文件两两比较
  - 阈值≤0.6，用于防洗稿检查
  - 支持 `--json` JSON输出
- **home** 命令：输出状态目录路径
- **便捷启动脚本** `bin/writing-master`：无需 pip 安装即可使用

#### 文档
- `docs/cli-guide.md`：完整的 CLI 工具使用指南
  - 安装说明（2种方式）
  - 命令详解（quality、similarity、home）
  - 评分维度说明
  - AI套话黑名单列表
  - 实战示例（4个场景）
  - 故障排除

#### 核心 Skills
- `writing-master`：完整的10步创作流程
  - Think Aloud 透明思考
  - 创意排水理论应用
  - 三遍审校机制
  - 状态管理（支持断点续写）
- `writing-rewrite`：内容级真改写
  - 多平台适配（小红书/抖音）
  - 质量双门槛（评分≥60，相似度≤0.6）
  - 优先使用 CLI 工具，回退到 AI 评估

#### 参考文档
- `skills/writing-master/references/creative-drainage.md`：创意排水详解
- `skills/writing-master/references/three-pass-review.md`：三遍审校详解
- `skills/writing-rewrite/platforms/xiaohongshu.yaml`：小红书平台定义
- `skills/writing-rewrite/platforms/douyin.yaml`：抖音平台定义

#### 其他
- `pyproject.toml`：Python 包配置
- `install.sh`：一键安装脚本
- `LICENSE`：MIT 许可证 + 致谢原项目
- `README.md`：完整项目说明（350+行）

### Changed

- **writing-rewrite/SKILL.md**：更新质量检查逻辑
  - 优先使用 CLI 工具（如果可用）
  - CLI 不可用时回退到 AI 评估
  - 添加 CLI 输出示例
- **README.md**：添加 CLI 工具说明
  - 安装方式新增"方式3: 安装 CLI 工具"
  - 技术栈部分添加 CLI 能力说明
  - 项目结构添加 `bin/` 和 `src/` 目录

### Fixed

- **writing-master/SKILL.md**：移除不存在的 CLI 命令引用
  - Line 83: `writing-master diagnose --json` → 改为直接检查环境
  - Lines 243-358: 移除所有 `writing-master run step` 命令，改为文件操作说明
- **writing-rewrite/SKILL.md**：移除不存在的 CLI 命令引用
  - 移除了错误的 `writing-master quality-score` 和 `writing-master similarity` 命令
  - 改为正确的 `writing-master quality` 和 `writing-master similarity`

### Technical Details

#### Python 包结构
```
src/writing_master/
├── __init__.py          # 版本信息
├── __main__.py          # 模块入口
├── cli.py               # 主调度器
└── commands/
    ├── __init__.py
    ├── quality.py       # 质量评分实现
    └── similarity.py    # 相似度检测实现
```

#### 算法说明
- **质量评分**：加权平均（准确性25% + 套话20% + 句子变化15% + 段落节奏10% + 副词密度15% + 词汇丰富度15%）
- **相似度检测**：字符3-gram Jaccard相似度，去除markdown标记和标点

#### 依赖
- Python ≥3.11
- 仅依赖标准库（无需 pip 安装外部包）
- 可选依赖：`pyyaml>=6.0`（用于未来的配置文件支持）

---

## [0.9.0] - 2026-07-23

### Added
- 初始项目结构
- 融合 auto-claude-writing-agent 和 wewrite 两个项目
- 基础 skills 框架

---

## 致谢

本项目融合了以下开源项目的优秀设计：

- [auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub) by MapleShaw
  - 10步完整写作流程
  - 创意排水理论
  - 三遍审校机制

- [wewrite](https://github.com/imraywang/wewrite) by imraywang
  - 模块化架构设计
  - CLI 工具实现参考
  - 洗稿/改写功能

特别感谢两位作者的开源贡献！
