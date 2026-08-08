# Changelog

本文件记录仓库已经落地的显著变化。格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，版本遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Removed

- 移除 `writing-master voice` 命令、内置 Voice Registry 与 `voice_presets` 模块：写作声音不再是独立可选项，自然表达由 Persona 与 Style Observation 决定。
- 移除 `writing-master learn propose` 的 `--run-dir` 参数：不再需要 Voice 隔离校验。

### Added

- 增加 evidence_level 三级证据等级系统：relaxed（快速草稿）、balanced（标准写作，默认）、strict（深度写作）。
- 标准和深度模式增加 Auto Research 自动调研功能：遇到 AI 热点主题时自动搜索最新信息，无需用户手动提供素材。
- Quick Mode 文件生成策略优化：只生成 4-5 个必要文件（status.json、draft.md、suggestions.md、references.md），不生成内部 YAML 报告。
- Standard Mode 审校优化：只验证核心数据（价格、日期、版本号、性能指标），作者观点和常识性陈述不需要 claim_id。

### Changed

- **产品定位转型**：从"证据审查系统"转向"为读者提供价值的写作系统"；价值包括信息、决策、情绪、社交、时间等多维度，AI 可灵活识别读者需要的价值类型。
- **质量标准重新定义**：从"真人级写作"（像真人）转向"读者愿意读下去、读完有收获、愿意转发、下次还来"；"真人级"是质量基线（不写 AI 味废话），不是目的本身。
- 用户体验语言优化：使用"准备、撰写、打磨、定稿"等创作语言，避免"验收、审计、预检、合同"等合规部门语言。
- 内容契约简化：不逐个确认素材接收，批量展示"已接收 N 项素材"；Voice Preset 默认 natural-default，不单独询问。
- 证据追溯机制定位调整：作为内部质量保障基础设施，不暴露给用户；claim_id、source_sha256、diagnostic_id 等实现细节不再出现在用户可见输出中。
- 审校输出格式优化：给出可选的编辑建议（纯文本），不生成带数值评分的 YAML 报告。

### Added

- 为新建完整文章增加用户显式模式选择：快速草稿、标准写作和深度写作。
- 增加深度写作的 Researcher、Editorial Strategist、Writer、Auditor 角色卡和文件化 Context Packet 协议。
- 增加 `sources.yaml`、`claims.yaml`、`asset-manifest.yaml` 与 `storyboard.md` 的证据/素材契约。
- 增加 Baoyu 的 capability/material preflight，以及 Planning、Production、Publish 分阶段路由。
- 增加渠道适配 P0：`writing-master` 从零创作与 `writing-rewrite` 已有正文改写双入口，每次任务只接受一个 `target_id`。
- 增加微信、X 单帖、X Thread 渠道 YAML，以及 source hash / source-analysis 复用和完整交付合同。
- 增加 Personal Context Runtime：版本化 Profile、五类素材、隐私准入、不可变任务 Snapshot、usage 与 hash 验证。
- 增加 `writing-master learn`：可追溯 Style Observation、显式接受/拒绝和 accepted-only Style Profile。
- 增加 `writing-master research`：3–10 个上下文感知候选、实时 Evidence、四维评分及任务 Brief/Snapshot 绑定。
- 增加 `writing-master voice`：四个内置表达 Profile、任务级不可变 Snapshot、状态/hash 校验及 legacy/default 降级语义。
- 增加 `writing-master persona`：原样冻结外部 Persona `SKILL.md`、保存自由格式任务 Brief，并让 Editorial Strategist、Writer、Auditor 共享同一份 hash 输入；Researcher 保持中立。
- 增加内置 `khazix-writer` 人格模板与 `writing-master persona list`；模板复用现有 Persona Snapshot、hash 和恢复边界。
- 在内容契约、Phase 3、Voice Audit 与 Deep Handoff 中接入任务 Voice Snapshot；仅 Writer/Auditor 读取。
- 将内置 Voice Registry JSON 作为实际 package data 打入 wheel，保持零第三方运行依赖。
- 增加最小 GitHub Actions，执行全量单元测试、compileall、CLI smoke、安装脚本语法检查和包构建。

### Changed

- 将 `docs/quick-start.md` 收敛为普通用户唯一上手入口，CLI 与工程资料按受众分层导航。
- 所选模式未就绪时在素材提取、调研和生成前停止；运行途中影响模式承诺时保留产物并停止，统一使用 `WM-CAP-001` / `WM-RUN-001`，不切换模式或自动创建 Issue。
- 主写作流程仅在用户选择深度写作时启用多 Agent；快速和标准模式保持单 Agent。
- `writing-master quality` 改为五维机械文本检查；新增 `mechanical_score` 与 `score_type`，保留 `quality_score` 兼容字段。
- `quality` 对短标题、提纲和过短输入返回 `insufficient_data`，避免中性占位值被误读为通过。
- 安装脚本从仓库根目录安装 Python 包，并停止引用不存在的 `cli/` 与模板目录。
- 安装脚本保留用户已有的同名 Skill 文件或第三方链接，只复用本仓库已经建立的链接。
- 删除未使用的 PyYAML 运行依赖和不存在的 package-data 配置，CLI 保持零第三方运行依赖。
- `LICENSE` 保持纯 MIT 文本；来源项目致谢集中维护在 README 与项目现状文档。
- 重写 README、项目现状、快速开始和 CLI 指南，删除 Roadmap、固定模型推荐和未落地能力宣传。
- Baoyu 调用原则调整为“早预检、早摄入、晚生成、明确指令后发布”。
- 对齐运行时事实：深度模式 Handoff Runtime 已通过真实宿主验收；`quick/standard` 仍没有通用任务恢复，并在 CLI 指南列出 `handoff prepare|start|recover-lost|complete|show`。
- 主写作流程按需在文章事实研究前执行 Topic Research，并只在用户明确决定后把 accepted 风格规则用于后续任务 Snapshot。
- Rewrite 状态收缩为单目标结构；第二个渠道使用新 Rewrite，不引入批处理 Router 或目标数组。
- 渠道适配任务在完整成品处结束；自动发布、X Article 和渠道数据反馈留在后续阶段。

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
