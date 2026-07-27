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


if __name__ == "__main__":
    unittest.main()
