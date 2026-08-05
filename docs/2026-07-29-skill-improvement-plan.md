# AI Writing Master：Skill 视角改进计划

- 日期：2026-07-29
- 定位：对前两份文档的视角修正与收敛
  - `docs/2026-07-29-architecture-review.md`（工程评审，结论在 Skill 视角下基本仍成立）
  - `docs/2026-07-29-product-prd.md`（产品 PRD，部分优先级被本文修正）
- 前提：本项目是一个 **Skill 项目**，不是宏大产品。目标是"把当前项目搞好"，不为假想的未来形态过度建设。

## 1. 视角转换：Skill 项目的成功标准

产品视角问"用户增长、留存、差异化"；Skill 视角问四个更朴素的问题：

1. **被安装**：能不能进技能市场、被 README 搜到、多宿主可装？
2. **被路由对**：Agent 在正确的时机触发它，而不是误触发或不触发？
3. **不翻车**：Agent 遵守约束跑完全程，不自由发挥带崩流程？
4. **不腐烂**：宿主升级、模型换代、文件改名之后，它还能工作吗？

本仓库的差异化恰恰在第 3、4 条：绝大多数 Skill 是纯 prompt，而本仓库有 219 个测试、契约测试和 CI。**"防腐烂"是这个项目在 Skill 生态里的核心资产，应当继续做厚。**

## 2. 双用户模型：人 + Agent

Skill 的第一读者是 Agent（它是运行时），第二读者才是人。两条直接推论：

- **`SKILL.md` frontmatter 的 `description` 就是落地页**。Agent 靠它路由，用户靠它决定安装。当前 `skills/writing-master/SKILL.md:3-4` 的 description 偏"说明书体"，信息全但触发词密度可以更高——"写文章、写公众号、从零创作、改写、Thread"这类词就是 Skill 世界的 SEO。值得像打磨 README 标题一样打磨。
- **SKILL.md 本体的每一条约束都在与 Agent 的注意力竞争**。项目已做了 progressive disclosure（细节下沉 `references/`），方向正确。下一步 audit：统计主文件 token 量，把"只在特定分支使用的约束"继续下沉。主文件越短，遵守率越高。

## 3. 对既有文档的优先级修正

| 条目 | 产品 PRD 中的位置 | Skill 视角修正 | 理由 |
|---|---|---|---|
| quick/standard 恢复 | 唯一 P0（架构缺口） | **降级**：不做通用恢复服务，只加一个轻量 `writing-master status {task_id}` 展示"上次停在 X 阶段、产物在 Y" | Skill 世界会话天然短命；文件化状态已领先同类，轻量展示即兑现大部分价值 |
| WM-CAP-001 失败出口 | P0-2 | **升级为最高优先**：纯 SKILL.md 文案改动，成本近零 | 对话是 Skill 的全部产品表面，死胡同文案是体验最差的 10 秒钟 |
| 模式默认值学习 | P1-2（机制 + 阈值决策） | **变形为一句话**：在 mode-selection canonical prompt 中加"用户历史 N 次选择同一模式时可提示默认值" | Skill 哲学是把判断留给 Agent，不急于代码化 |
| 渠道扩展（知乎/Newsletter） | P2-1 | **搁置**，等真实使用反馈驱动 | Skill 项目不为假想用户扩面 |
| 本地统计 `stats` | P2-2 | **搁置** | 没有规模就没有值得统计的东西 |
| 风格学习主动提示 | P1-3 | **搁置** | 同上，等 dogfood 验证 |

架构评审中的以下结论在 Skill 视角下**维持不变**：`_runfs.py` 平台运行时检查、版本/CHANGELOG 收敛、`install.sh` 健壮性（`set -u`、ponytail 注释、卸载路径）。这些都是小时级的低风险修复。

## 4. Skill 语境下的"下一版"（小而完整）

全部轻量改动，不动架构：

1. **WM-CAP-001 出口文案**：把"停止 + 提交 Issue"改为用户可选的岔路（改用可用模式并明示损失 / 保留任务 / 取消）。改的是 `skills/writing-master/SKILL.md` 与 `references/mode-selection.md` 的文案，不是代码。
2. **`writing-master status {task_id}` 小命令**：只读运行目录，展示阶段与产物位置。不实现恢复语义，只消除"关掉对话后两眼一抹黑"。
3. **SKILL.md 引用完整性契约测试**：看守主文件与 `references/` 中引用的每个文件路径、CLI 命令、诊断码真实存在。纯 prompt Skill 最常见的腐烂方式就是引用了改名后的文件而无人发现——项目已有契约测试设施，这是其自然延伸。
4. **一次真实 dogfood 记录**：用它写一篇真文章，记录每次 Agent 误解指令、每次想插嘴的瞬间。这是 Skill 项目唯一有效的用户研究，比 PRD 里的可用性测试假设可靠。
5. **frontmatter description 打磨**：按触发词覆盖密度重写两个 SKILL.md 的 description。
6. **对齐社区 Skill 规范**：跟踪 Claude Skills / Codex / Cursor 的 SKILL.md 约定收敛（frontmatter 字段、`allowed-tools`、目录结构），保持兼容 = 保留被各市场收录的资格。这比任何增长功能更接近 Skill 项目的增长。

## 5. 保持克制：否定句是这个项目的护城河

产品思维推着加功能；Skill 思维应该推着**删模糊性**。本仓库最珍贵的特质是那些"不做"的声明——"不虚构独立 Skill""不隐式代选""不切换模式""不自动创建 Issue"。纯 prompt Skill 最常见的死法就是 Agent 自由发挥把流程带崩，这些否定句正是防线。继续维护好它们，比加新能力更符合"把当前项目搞好"。

产品 PRD 中的渠道扩展、增长资产、指标体系不是错了，而是**早了**——等 dogfood 和真实安装反馈回来时，它们自然会知道该不该启动。
