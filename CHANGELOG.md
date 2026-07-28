# Changelog

本文件记录仓库已经落地的显著变化。格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，版本遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Added

- 为新建完整文章增加用户显式模式选择：快速草稿、标准写作和深度写作。
- 增加深度写作的 Researcher、Editorial Strategist、Writer、Auditor 角色卡和文件化 Context Packet 协议。
- 增加 `sources.yaml`、`claims.yaml`、`asset-manifest.yaml` 与 `storyboard.md` 的证据/素材契约。
- 增加 Baoyu 的 capability/material preflight，以及 Planning、Production、Publish 分阶段路由。
- 补齐 `writing-rewrite` 的小红书/抖音平台 YAML，以及多平台改写和质量门槛参考文件。
- 增加 Personal Context Runtime：版本化 Profile、五类素材、隐私准入、不可变任务 Snapshot、usage 与 hash 验证。
- 增加 `writing-master learn`：可追溯 Style Observation、显式接受/拒绝和 accepted-only Style Profile。
- 增加 `writing-master research`：3–10 个上下文感知候选、实时 Evidence、四维评分及任务 Brief/Snapshot 绑定。
- 增加最小 GitHub Actions，执行全量单元测试、compileall、CLI smoke、安装脚本语法检查和包构建。

### Changed

- 主写作流程仅在用户选择深度写作时启用多 Agent；快速和标准模式保持单 Agent。
- `writing-master quality` 改为五维机械文本检查；新增 `mechanical_score` 与 `score_type`，保留 `quality_score` 兼容字段。
- `quality` 对短标题、提纲和过短输入返回 `insufficient_data`，避免中性占位值被误读为通过。
- 安装脚本从仓库根目录安装 Python 包，并停止引用不存在的 `cli/` 与模板目录。
- 安装脚本保留用户已有的同名 Skill 文件或第三方链接，只复用本仓库已经建立的链接。
- 删除未使用的 PyYAML 运行依赖和不存在的 package-data 配置，CLI 保持零第三方运行依赖。
- `LICENSE` 保持纯 MIT 文本；来源项目致谢集中维护在 README 与项目现状文档。
- 重写 README、项目现状、快速开始和 CLI 指南，删除 Roadmap、固定模型推荐和未落地能力宣传。
- Baoyu 调用原则调整为“早预检、早摄入、晚生成、明确指令后发布”。
- 对齐运行时事实：深度模式 Handoff Runtime 已通过真实宿主验收；`quick/standard` 仍没有通用任务恢复，并在 CLI 指南列出 `handoff prepare|complete|show`。
- 主写作流程按需在文章事实研究前执行 Topic Research，并只在用户明确决定后把 accepted 风格规则用于后续任务 Snapshot。

### Fixed

- 删除 README 中不存在的 `writing-topic`、`writing-review`、`writing-visual` 等独立 Skill 声明。
- 删除不存在的示例、模板、配置和文档路径。
- 修复文档中的失效内部链接和错误 GitHub 反馈地址。
- 删除“AI 味百分比”、默认准确性分和整体质量保证等无法由 CLI 验证的表述。
- 使用 run-local 锁和 no-clobber 发布保护跨 Context Home 的 approval 与不可变 Snapshot 竞争。
- Handoff prepare 从入口逐段锚定 run 目录并 descriptor-relative 创建 attempt，拒绝 symlink 与 ancestor retarget 写出任务目录。

## [1.0.0] - 2026-07-24

### Added

- `writing-master`：从 Brief、调研、创意排水、初稿到分层审校的完整写作入口。
- `writing-rewrite`：已有文章的内容级重构与平台改写入口。
- `writing-master quality`：套话、句长、段落节奏、副词和字符多样性的启发式检查。
- `writing-master similarity`：字符 n-gram Jaccard 相似度。
- `writing-master home`：用户运行目录查询。
- `bin/writing-master`：直接从仓库运行 CLI 的启动脚本。
- `install.sh`：创建用户目录并链接 Skills。
- Creative Drainage 与三遍审校参考文档。
- README、快速开始和 CLI 指南。

### Notes

- 初始文档把部分参考项目能力写成了当前仓库能力；这些声明已在 `Unreleased` 的仓库审计中修正。
- 1.0.0 的 CLI `quality_score` 是机械启发式汇总值，不代表事实准确性或整体编辑质量。

## [0.9.0] - 2026-07-23

### Added

- 初始仓库结构。
- 引入 `auto-claude-writing-agent` 与 `wewrite` 的方法参考。
- 建立 `writing-master` 和 `writing-rewrite` 两个 Skill 入口。

## 来源与致谢

- [auto-claude-writing-agent](https://github.com/MapleShaw/auto-claude-writing-agent-pub) by MapleShaw
- [wewrite](https://github.com/imraywang/wewrite) by imraywang
