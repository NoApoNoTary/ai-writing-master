# AI Writing Master 软件架构评审

- 评审日期：2026-07-29
- 评审对象：`codex/writing-workflow-maintenance` 分支（评审时 HEAD：`b58155f`）
- 评审范围：`src/writing_master/`、`skills/`、`install.sh`、`pyproject.toml`、CI、文档一致性
- 评审基线：219 个单元测试在 Python 3.14 下全部通过（评审时实跑验证）

> 本文是评审记录，不是改造计划。每条结论都标注了代码位置；涉及改造的条目只描述问题与方向，不规定实现。

## 1. 架构总览

系统由三层组成，边界清晰：

| 层 | 位置 | 职责 |
|---|---|---|
| 行为层 | `skills/writing-master/`、`skills/writing-rewrite/` | 用自然语言状态机约束 Agent 行为：模式闸门、就绪闸门、阶段合同、终止协议（WM-CAP-001/WM-RUN-001） |
| 运行层 | `src/writing_master/` | 确定性文件操作：Handoff 交接、Voice 快照、个人上下文、Research Brief |
| 接口层 | `src/writing_master/cli.py`、`src/writing_master/commands/` | 手写 argv 路由的零依赖 CLI，7 个子命令 |

关键架构决策及其代价：

- **零第三方运行依赖**（`pyproject.toml` `dependencies = []`）：CLI 解析、JSON schema 校验、YAML 规避全部手写。换来的是安装面极小、供应链风险为零；代价是 `personal_context.py` 已达 2013 行，自写校验代码的维护成本会随 schema 演进持续上升。
- **文件系统即状态机**：所有跨阶段状态落盘于 `{home}/runs/{task_id}/`，不依赖对话记忆。这是"可审阅、可继续"承诺的根基。
- **行为约束放在 Skill 文档而非代码**：模式选择、降级拒绝、单 target_id 等约束靠 LLM 遵守 SKILL.md。这是该形态的正确选择，但意味着最关键的交互约束没有代码强制（见 §3.4）。

## 2. 做得好的部分（应作为模式保持）

1. **fd 锚定的防 symlink 文件访问**（`_runfs.py:22-63`）：逐路径组件 `os.open` + `O_NOFOLLOW`，配合 `/proc/self/fd` 锚定和 `fcntl.flock`（`_runfs.py:74-91`）。对运行目录这种用户可写区域，这是教科书级的加固。
2. **原子写入 + fsync**（`handoff.py:103-165`）：临时文件 → flush → fsync → `os.replace` → 目录 fsync，崩溃不会留下半截 JSON。
3. **文档-代码契约测试**（`tests/test_*_contract.py`）：文档声明的行为边界有测试看守，这是本项目文档可信度高的结构性原因。
4. **诚实边界声明**：README:72 明确"Linux staging 边界"，README:298 明确"quick/standard 通用恢复未实现"。不夸大能力。
5. **不可变快照设计**：Voice Profile 冻结为任务级 `voice-profile-snapshot.json` 并带 SHA-256，恢复时不回读可变 Registry（`voice_presets.py`），消除了"历史任务被后续配置变更污染"的整类 bug。
6. **CI 覆盖务实**：测试矩阵（3.11/3.14）+ compileall + 安装脚本语法检查 + CLI smoke + 包构建（`.github/workflows/ci.yml`），与该项目的风险面匹配。

## 3. 架构问题（按严重度排序）

### 3.1 平台边界没有运行时保护 —— 高

`_runfs.py:61` 和 `_runfs.py:69` 硬编码 `/proc/self/fd`，`_runfs.py:7` 无条件 `import fcntl`。README 声明了 Linux 边界，但代码层没有对应防线：macOS 用户调用 `handoff`/`voice` 时会得到 `/proc` 缺失的裸 `OSError`，错误信息不指向真实原因。

方向：在 `_runfs.py` 入口做 `sys.platform` 前置检查，失败时抛出带 `unsupported_platform` 错误码的 `RunFsError`；同时在 `pyproject.toml` 的 classifiers 中声明平台。成本极低，消除的是"边界声明在文档里、体验事故在用户端"的不一致。

### 3.2 版本与 CHANGELOG 脱节 —— 高

`pyproject.toml:7` 与 `__init__.py` 均为 `1.0.0`，但 `CHANGELOG.md` 的 `[Unreleased]` 节已积累 Voice、Learn、Research、渠道适配 P0、Handoff Runtime 验收等远超 1.0.0 的内容，且其中 Rewrite 状态结构收缩为单目标属于 breaking change。

方向：发版时将 Unreleased 收敛为 `2.0.0`（或拆分 1.1.0 + 2.0.0）；并在契约测试体系中增加"包版本 == CHANGELOG 最新版本节"检查——项目已有 `test_documentation_contract.py` 类的设施，这是其自然延伸。

### 3.3 quick/standard 缺跨会话恢复 —— 高（架构缺口）

Handoff Runtime 只覆盖已建立的 `mode=deep, execution=multi_agent` 运行目录（`handoff.py` 的状态机 `TRANSITIONS` 与角色协议均围绕 deep 设计）。但架构上，恢复所需的全部基础设施已经存在：运行目录锚定（`run_directory`）、锁（`run_lock`）、原子写、`status.json` 阶段合同。缺口不是技术能力，而是 quick/standard 的**恢复语义未被定义**：哪些阶段可重入、输入变化如何失效、产物如何续接。

方向：见配套 PRD 的 P0-1。架构上建议把"恢复"抽象为与执行模式正交的运行目录服务，而不是把 handoff 的角色协议下放给单 Agent 模式。

### 3.4 关键行为约束无代码强制 —— 中

"只选一个 target_id""未验收 final 不得进入 Rewrite""深度未就绪不降级"等核心约束全部依赖 Agent 遵守 SKILL.md。LLM 大概率遵守，但没有确定性兜底。例如 `writing-rewrite` 的"一次一个 target_id"（`skills/writing-rewrite/SKILL.md:36`）在 CLI 层无任何对应校验。

方向：不必全部代码化（会丧失 Skill 形态的优势），但对**不可逆或跨任务污染的约束**（Rewrite 输入必须是 accepted_final、source.md 只读）值得在 CLI 层加校验入口，让 Agent 调用时得到硬错误而非靠自觉。

### 3.5 安装脚本健壮性 —— 低

- `install.sh:5` 仅 `set -e`，缺 `set -u -o pipefail`；`DETECTED_AGENTS` 等变量在未检测到 agent 时未初始化，目前靠 `[ -n "$X" ]` 守卫兜底。
- `install.sh:72` 注释含内部代号 `ponytail`，建议改中性描述。
- 无卸载路径：安装创建 4 处 agent 目录符号链接 + `~/.writing-master/`，用户无法干净移除。

### 3.6 包元数据不完整 —— 低

`pyproject.toml` 无 classifiers（License、Platform、Python 版本）。若发布 PyPI 必须补；即使不发布，`Operating System :: POSIX :: Linux` 也能与 §3.1 的边界呼应。

### 3.7 源码归属注释 —— 低

`cli.py:3`、`commands/similarity.py:4`、`commands/quality.py:4` 声明"改编自 wewrite"。署名意识正确；建议增加 NOTICE 文件集中记录，与 LICENSE 分离，避免散落在文件头的归属信息日后难以维护。

## 4. 已验证无问题的疑点

评审中核实并排除的问题：

- `pyproject.toml` 的 package-data `voice_profiles/*.json` 指向 `src/writing_master/voice_profiles/registry.json`，文件存在，非配置悬空。
- CI 矩阵仅 ubuntu 与 Linux-only 边界一致，是合理剪裁而非遗漏（若 §3.1 未来解除，再将 macOS 加入 matrix）。
- `bin/writing-master` 与 entry point 双入口指向同一 `main`，行为一致。

## 5. 结论

架构的主干（文件化状态机、不可变快照、零依赖、契约测试）是健康且可演进的。当前最需修复的不是任何代码结构，而是三处**承诺与实现的不一致**：平台边界没有代码防线、版本号落后于能力、README 的"可继续"在默认模式下不成立。前两者是小时级工作，第三者是下一个版本的核心架构议题。

配套文档：`docs/2026-07-29-product-prd.md`。
