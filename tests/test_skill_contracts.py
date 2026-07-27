import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return a Markdown heading and everything before its peer/parent."""
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    boundary = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    match = boundary.search(text, start + len(heading))
    return text[start : match.start() if match else len(text)]


class WritingSkillContractTests(unittest.TestCase):
    def assert_in_order(self, text: str, *tokens: str) -> None:
        position = 0
        for token in tokens:
            found = text.find(token, position)
            self.assertNotEqual(found, -1, f"Expected {token!r} after {position}")
            position = found + len(token)

    def test_complete_writing_requires_explicit_mode_selection(self):
        main = read("skills/writing-master/SKILL.md")

        self.assertIn("references/mode-selection.md", main)
        self.assertIn("Canonical prompt", read("skills/writing-master/references/mode-selection.md"))
        self.assertLess(main.index("### 模式选择闸门"), main.index("### Phase 0"))

    def test_mode_prompt_stays_in_sync_across_user_facing_docs(self):
        prompt_lines = [
            "请选择本次写作模式：",
            "1. 快速草稿：单 Agent，最少调研与一次审校，适合先拿到可讨论版本。",
            "2. 标准写作（推荐）：单 Agent，完整调研、素材规划、写作与三层审校。",
            "3. 深度写作：多 Agent 分工，独立研究、策划、写作和审计，适合重要长文。",
        ]
        canonical = read("skills/writing-master/references/mode-selection.md")
        for line in prompt_lines:
            self.assertIn(line, canonical, f"Canonical prompt 缺少统一模式文案: {line}")

        for relative in ("README.md", "docs/quick-start.md"):
            content = read(relative)
            self.assertIn("mode-selection.md", content)

    def test_mode_selection_requires_an_explicit_resume_target(self):
        entry_rules = section(
            read("skills/writing-master/references/mode-selection.md"),
            "## 入口规则",
        )

        self.assert_in_order(
            entry_rules,
            "“继续上次”时要求用户指定 `task_id` 或运行目录",
            "只有运行时已验证恢复能力后才读取 `status.json.mode`",
            "Product–Technical Gap",
        )
        self.assertNotIn("“继续上次”读取 `status.json.mode`", entry_rules)

    def test_quick_mode_produces_the_shared_core_artifacts(self):
        quick = section(
            read("skills/writing-master/references/mode-selection.md"),
            "### 1. 快速草稿（quick）",
        )

        self.assertIn("与标准模式相同的核心文件", quick)
        for artifact in (
            "brief.md",
            "sources.yaml",
            "claims.yaml",
            "asset-manifest.yaml",
            "draft-v1.md",
            "review-report.yaml",
            "revision-report.yaml",
            "final.md",
            "acceptance-report.md",
        ):
            self.assertIn(artifact, quick)
        self.assertIn("内容契约", quick)

    def test_multi_agent_is_deep_mode_only(self):
        main = read("skills/writing-master/SKILL.md")
        orchestration = read("skills/writing-master/references/agent-orchestration.md")

        self.assertIn("快速草稿和标准写作始终使用当前 Agent", main)
        self.assertIn("只有深度模式启用多 Agent", main)
        self.assertIn("本文件只在 `mode=deep` 时读取", orchestration)

    def test_baoyu_is_early_preflight_and_late_production(self):
        routing = read("skills/writing-master/references/baoyu-integration.md")

        self.assertIn("Level 1：Preflight + Material Intake", routing)
        self.assertIn("baoyu-url-to-markdown", routing)
        self.assertIn("baoyu-youtube-transcript", routing)
        self.assertIn("Level 3：Production", routing)
        self.assertIn("早预检、早摄入、晚生成、后发布", routing)

    def test_main_skill_has_user_visible_status_and_waiting_contract(self):
        main = read("skills/writing-master/SKILL.md")

        for field in (r"(?:当前)?任务", r"(?:当前)?模式", r"(?:当前)?阶段", r"已完成", r"下一步"):
            self.assertRegex(main, field)
        for state in (r"等待模式", r"等待(?:内容)?契约确认", r"等待方向确认", r"等待问题处理"):
            self.assertRegex(main, state)
        self.assertRegex(main, r"(?:当前动作|正在执行)")

    def test_main_skill_returns_a_material_receipt(self):
        main = read("skills/writing-master/SKILL.md")

        self.assertIn("素材接收结果", main)
        for field in ("已接收", "已提取", "等待处理", "失败"):
            self.assertIn(field, main)
        self.assertRegex(main, r"(?s)素材接收结果.{0,600}(?:需要你确认|待确认)")
        self.assertRegex(main, r"(?s)失败.{0,160}(?:不阻塞|继续处理).{0,160}(?:其他|其余|无关)")

    def test_main_skill_defines_delivery_package_and_blocking_issue_behavior(self):
        main = read("skills/writing-master/SKILL.md")

        self.assertIn("交付包", main)
        package_start = main.index("交付包")
        package = main[package_start:package_start + 1800]
        for artifact in (
            "final.md",
            "sources.yaml",
            "claims.yaml",
            "asset-manifest.yaml",
            "acceptance-report.md",
        ):
            self.assertIn(artifact, package)
        self.assertRegex(package, r"(?:review-report\.yaml|revision-report\.yaml)")
        self.assertRegex(main, r"(?:忽略.{0,30}非阻断|非阻断.{0,30}忽略)")
        self.assertRegex(
            main,
            r"(?s)阻断问题.{0,140}(?:未关闭|未解决|未处理|关闭后|解决后|处理后).{0,220}(?:完成|发布)",
        )

    def test_title_defaults_without_an_extra_waiting_gate(self):
        main = read("skills/writing-master/SKILL.md")
        waiting = section(main, "## 用户等待与继续方式")
        title = section(main, "### Phase 5：标题与 canonical final 验收")
        standard = section(
            read("skills/writing-master/references/mode-selection.md"),
            "### 2. 标准写作（standard）",
        )

        self.assertNotIn("| 标题 |", waiting)
        self.assertIn("只在模式、内容契约、重大方向、阻断问题和发布", waiting)
        self.assert_in_order(
            title,
            "标题至少提供自然版、判断版和传播版",
            "默认采用与正文最一致的推荐标题写入 `final.md`",
            "用户主动要求选择或修改时再等待该决定",
        )
        self.assertIn("用户确认：内容契约、核心角度、发布动作", standard)
        self.assertIn("标题随最终稿交付", standard)

    def test_acceptance_precedes_visual_and_format_routes(self):
        main = read("skills/writing-master/SKILL.md")
        acceptance = section(main, "### Phase 5：标题与 canonical final 验收")
        downstream = section(main, "### Phase 6：交付包、视觉、排版与发布")
        routing = read("skills/writing-master/references/baoyu-integration.md")
        production = section(routing, "### Level 3：Production（canonical final 验收后）")
        route_summary = section(routing, "## 路由决策摘要")

        self.assertLess(
            main.index("### Phase 5：标题与 canonical final 验收"),
            main.index("### Phase 6：交付包、视觉、排版与发布"),
        )
        self.assert_in_order(
            acceptance,
            "在视觉、排版、Rewrite 或发布前",
            "`acceptance-report.md` 中完成内容验收",
            "验收通过后，`final.md` 成为只读 canonical final",
        )
        self.assert_in_order(
            downstream,
            "图像类视觉闸门",
            "`final.md` 已是已验收的 canonical final",
            "Markdown 格式化和公众号 HTML",
            "不要求 storyboard、`asset-manifest.yaml` 或图像类视觉意图",
        )
        self.assert_in_order(
            production,
            "### Level 3：Production（canonical final 验收后）",
            "`accepted_writing_master_final`",
            "`acceptance-report.md` 内容明确验收通过",
            "图像类视觉生产约束",
        )
        self.assertIn("Markdown 格式化和 HTML 转换不属于图像类视觉生产", production)
        self.assert_in_order(
            route_summary,
            "内容验收：canonical final",
            "图像类视觉闸门通过：Baoyu 视觉 production",
            "canonical final + channel contract：Baoyu 排版 / HTML",
        )

    def test_deep_mode_role_cards_exist(self):
        cards = [
            "researcher.md",
            "editorial-strategist.md",
            "writer.md",
            "auditor.md",
        ]
        for card in cards:
            self.assertTrue((ROOT / "skills/writing-master/agents" / card).is_file())

    def test_rewrite_reads_real_platform_contracts(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")

        self.assertIn("references/multiplatform-rewrite.md", rewrite)
        self.assertIn("references/quality-gates.md", rewrite)
        self.assertIn("platforms/xiaohongshu.yaml", rewrite)
        self.assertIn("platforms/douyin.yaml", rewrite)
        self.assertIn("机械语言预警", rewrite)
        self.assertNotIn("姐妹们", rewrite)
        self.assertNotIn("别划走", rewrite)

    def test_rewrite_distinguishes_accepted_final_from_standalone_input(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")
        runtime = section(rewrite, "## 运行约定")
        inputs = section(rewrite, "## Phase 0：输入与任务目录")
        gates = section(
            read("skills/writing-rewrite/references/quality-gates.md"),
            "## 0. 来源准入门槛",
        )

        self.assertIn(
            "源稿分类只能是 `accepted_writing_master_final` 或 `standalone_user_input`",
            runtime,
        )
        self.assert_in_order(
            inputs,
            "`accepted_writing_master_final`",
            "已验收的 `final.md`",
            "`acceptance-report.md` 确认内容验收通过",
            "`standalone_user_input`",
            "用户直接提供的文件或当前对话中的完整正文",
            "`source.md` 只读",
        )
        self.assertIn("未验收的 `draft-v1.md`、`draft-v2.md` 或 `final.md` 不得进入 Rewrite", inputs)
        self.assertIn("不要求 Writing Master 的验收报告", inputs)
        self.assertIn("`standalone_user_input` 只限用户直接提供的文件或完整正文", gates)
        self.assertIn("不得改写 canonical source", gates)

    def test_rewrite_p0_has_no_fresh_context_or_multi_agent_path(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")
        runtime = section(rewrite, "## 运行约定")
        platform_rewrite = section(rewrite, "## Phase 3：独立平台改写")

        self.assertIn("P0 默认并始终使用当前 Agent", runtime)
        self.assertIn("深度或多 Agent 改写尚未定义真实平台角色与 Handoff 合同", runtime)
        self.assertIn("等待用户确认标准改写或取消", runtime)
        self.assertNotIn("fresh-context", rewrite)
        self.assertIn("当前 Agent 对每个平台都只读取", platform_rewrite)
        self.assertIn("不把一个平台版本作为另一个平台的输入", platform_rewrite)


if __name__ == "__main__":
    unittest.main()
