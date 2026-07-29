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


class DocumentationContractTests(unittest.TestCase):
    def assert_in_order(self, text: str, *tokens: str) -> None:
        position = 0
        for token in tokens:
            found = text.find(token, position)
            self.assertNotEqual(found, -1, f"Expected {token!r} after {position}")
            position = found + len(token)

    def test_readme_does_not_publish_a_roadmap(self):
        readme = read("README.md")
        self.assertNotIn("## 📈 Roadmap", readme)
        self.assertNotIn("### v2.0 (长期)", readme)

    def test_docs_distinguish_verified_deep_handoff_from_generic_resume_gap(self):
        readme = read("README.md")
        quick_start = read("docs/quick-start.md")
        summary = read("PROJECT_SUMMARY.md")
        cli_guide = read("docs/cli-guide.md")
        product_prd = read("docs/proposals/2026-07-27-product-capability-prd.md")

        self.assertIn("深度模式 Handoff Runtime 已通过运行时和真实宿主验收", readme)
        self.assertIn("`quick/standard` 仍没有通用的确定性跨会话任务恢复服务", readme)
        self.assertIn("`writing-master handoff prepare|start|recover-lost|complete|show`", readme)
        self.assertIn("Linux staging 边界", readme)
        self.assertIn("深度模式 Handoff Runtime 已验收", summary)
        self.assertIn("`writing-master handoff`", summary)
        self.assertIn("writing-master handoff prepare", cli_guide)
        self.assertIn("深度模式 Handoff Runtime 已验收", product_prd)
        self.assertIn("quick/standard 的通用任务恢复", product_prd)
        for internal in (
            "Runtime",
            "Handoff",
            "Manifest",
            "Snapshot",
            "Agent",
            "multi-agent",
            "capability preflight",
        ):
            self.assertNotIn(internal, quick_start)

    def test_docs_have_one_user_entry_and_a_separate_cli_manual(self):
        readme = read("README.md")
        quick_start = read("docs/quick-start.md")
        cli_guide = read("docs/cli-guide.md")

        self.assertIn(
            "**普通用户唯一上手入口：** [用户上手指南](docs/quick-start.md)",
            readme,
        )
        self.assertIn("[CLI 工具指南](docs/cli-guide.md)", readme)
        self.assertIn("Shell 调用或编写自动化", readme)
        self.assertIn("任务在素材提取、调研和写作前停止，不自动切换到其他模式", readme)
        self.assertIn("普通写作不以 CLI 为入口", cli_guide)
        self.assertIn("这是普通用户唯一的上手文档", quick_start)
        for heading in ("## 1. 第一次写作", "## 2. 补充素材", "## 3. 修改结果"):
            self.assertIn(heading, quick_start)
        self.assertNotIn("writing-master ", quick_start)
        self.assertNotIn("docs/goals/", quick_start)
        self.assertNotIn("docs/plans/", quick_start)
        self.assertNotIn("docs/proposals/", quick_start)

    def test_user_guide_publishes_fail_stop_messages_without_issue_automation(self):
        quick_start = read("docs/quick-start.md")

        self.assertIn("尚未进入调研或写作", quick_start)
        self.assertIn("所选的{模式显示名}当前未就绪", quick_start)
        for label in ("快速草稿", "标准写作", "深度写作"):
            self.assertIn(label, quick_start)
        self.assertIn("诊断编号：WM-CAP-001", quick_start)
        self.assertIn("未切换到其他写作模式", quick_start)
        self.assertIn("已有内容已保留", quick_start)
        self.assertIn("诊断编号：WM-RUN-001", quick_start)
        self.assertIn("提交 Issue", quick_start)
        self.assertIn("不会自动提交", quick_start)
        self.assertIn("不会替你生成 Issue 草稿", quick_start)
        self.assertIn("只有当前任务具备输入依赖校验时", quick_start)

    def test_release_docs_publish_context_learning_and_research_without_overclaiming(self):
        readme = read("README.md")
        quick_start = read("docs/quick-start.md")
        cli_guide = read("docs/cli-guide.md")
        summary = read("PROJECT_SUMMARY.md")

        self.assertIn("writing-master context init", readme)
        self.assertIn("writing-master context verify-run RUN_DIR", cli_guide)
        self.assertIn("`writing-master context`", summary)
        for command in ("writing-master learn", "writing-master research"):
            self.assertIn(command, readme)
            self.assertIn(command, cli_guide)
            self.assertIn(f"`{command}`", summary)
        for document in (readme, quick_start, cli_guide, summary):
            self.assertNotIn("自动学习作者风格", document)
            self.assertNotIn("Runtime 验证热点真实", document)
        self.assertIn("缺少实时检索时不生成 Heat 或 Brief", readme)
        self.assertIn("只影响之后创建的新 Snapshot", cli_guide)
        for command in ("writing-master context", "writing-master learn", "writing-master research"):
            self.assertNotIn(command, quick_start)

    def test_p0_critical_scenarios_preserve_ordered_happy_and_failure_paths(self):
        prd = read("docs/proposals/2026-07-27-product-capability-prd.md")
        scenario_a = section(prd, "### Scenario A：无素材标准写作")
        scenario_b = section(prd, "### Scenario B：带混合素材写作")
        scenario_d = section(prd, "### Scenario D：审校阻断")
        scenario_e = section(prd, "### Scenario E：Canonical Rewrite")

        self.assert_in_order(
            scenario_a,
            "用户请求新建文章。",
            "选择标准模式。",
            "选择 `x-post` 作为本次唯一 `target_id`。",
            "确认内容契约。",
            "选择方向。",
            "收到初稿、审校结果",
            "内容验收后的 canonical final",
            "当前渠道没有必要视觉或 HTML 时",
            "完成交付包验收",
            "交付摘要",
        )
        self.assert_in_order(
            scenario_b,
            "用户提供 URL、视频和本地图片。",
            "系统返回素材接收结果。",
            "一个素材失败时，其他素材继续处理。",
            "用户确认是否排除失败素材。",
            "最终交付包含来源与素材身份。",
        )
        self.assert_in_order(
            scenario_d,
            "审校发现事实来源不足。",
            "系统不进入已完成或发布状态。",
            "用户补充来源或降低表述强度。",
            "受影响部分重新审校后完成。",
        )
        self.assert_in_order(
            scenario_e,
            "主任务完成 canonical final。",
            "用户请求一个 X 单帖版本。",
            "Rewrite 固定 source hash",
            "用户随后请求 X Thread",
            "复用相同 source hash 与 `source-analysis.md`",
            "不修改 canonical final 或已经完成的 X 单帖。",
        )

    def test_channel_prds_keep_the_single_target_state_model(self):
        documents = [
            read("docs/proposals/2026-07-27-product-capability-prd.md"),
            read("docs/proposals/2026-07-29-channel-adaptation-p0-prd.md"),
        ]
        forbidden = (
            "Content Intent " + "Selector",
            "全" + "部生成",
            "主" + "渠道",
            "次" + "渠道",
            '"target' + 's"',
            "部分" + "成功",
            "跨目标" + "重试",
            "平台版本之间" + "的相似度",
        )

        for document in documents:
            for phrase in forbidden:
                self.assertNotIn(phrase, document)

    def test_relative_markdown_links_resolve(self):
        missing = []
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

        for markdown in ROOT.rglob("*.md"):
            if ".git" in markdown.parts:
                continue
            text = markdown.read_text(encoding="utf-8")
            for raw_target in link_pattern.findall(text):
                target = raw_target.split("#", 1)[0].strip()
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (markdown.parent / target).resolve()
                if not resolved.exists():
                    missing.append(f"{markdown.relative_to(ROOT)} -> {raw_target}")

        self.assertEqual(missing, [], "Missing local Markdown links:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
