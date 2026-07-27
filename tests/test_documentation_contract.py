import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class DocumentationContractTests(unittest.TestCase):
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
