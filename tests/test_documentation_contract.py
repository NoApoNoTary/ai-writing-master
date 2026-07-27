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

    def test_readme_marks_cross_session_resume_and_handoff_as_runtime_gaps(self):
        readme = read("README.md")

        self.assertRegex(
            readme,
            r"(?s)(?:跨会话(?:恢复|继续|续跑).{0,180}(?:尚未|未|技术依赖|技术运行时|Product.?Technical Gap)|(?:尚未|未|技术依赖|技术运行时|Product.?Technical Gap).{0,180}跨会话(?:恢复|继续|续跑))",
        )
        self.assertRegex(
            readme,
            r"(?s)(?:Handoff.{0,180}(?:尚未|未|技术依赖|技术运行时|不是|不等于).{0,180}(?:运行时|真实执行|宿主验收)|(?:运行时|真实执行|宿主验收).{0,180}(?:尚未|未|技术依赖|技术运行时|不是|不等于).{0,180}Handoff)",
        )

    def test_quick_start_does_not_advertise_cross_session_resume(self):
        quick_start = read("docs/quick-start.md")

        self.assertRegex(
            quick_start,
            r"(?s)(?:跨会话(?:恢复|继续|续跑).{0,180}(?:尚未|未|技术依赖|技术运行时|Product.?Technical Gap)|(?:尚未|未|技术依赖|技术运行时|Product.?Technical Gap).{0,180}跨会话(?:恢复|继续|续跑))",
        )
        self.assertNotRegex(
            quick_start,
            r"(?s)从\s*`?\$\{WRITING_MASTER_HOME.*?/runs/.*?(?:读取|恢复).*?(?:最近|未完成)",
        )

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
            "确认内容契约。",
            "选择方向。",
            "收到初稿、审校结果",
            "内容验收后的 canonical final",
            "未请求视觉、HTML 和发布时",
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
            "用户请求小红书和抖音版本。",
            "两个版本独立生成。",
            "任一平台版本失败不修改 canonical final 和其他平台版本。",
        )

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
