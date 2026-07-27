import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class WritingSkillContractTests(unittest.TestCase):
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

        self.assertRegex(
            rewrite,
            r"(?s)(?:源稿分类|source_type|source_kind).{0,160}accepted_writing_master_final.{0,160}standalone_user_input",
        )
        self.assertRegex(
            rewrite,
            r"(?s)accepted_writing_master_final.{0,700}(?:final\.md)",
        )
        self.assertRegex(
            rewrite,
            r"(?s)accepted_writing_master_final.{0,700}(?:acceptance-report\.md|验收报告)",
        )
        self.assertRegex(
            rewrite,
            r"(?s)standalone_user_input.{0,600}(?:用户(?:提供|粘贴)|文件)",
        )


if __name__ == "__main__":
    unittest.main()
