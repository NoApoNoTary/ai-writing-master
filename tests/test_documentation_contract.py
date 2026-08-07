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

    def test_docs_have_one_user_entry_and_a_separate_cli_manual(self):
        readme = read("README.md")
        quick_start = read("docs/quick-start.md")
        cli_guide = read("docs/cli-guide.md")
        
        # User entry point is quick-start
        self.assertIn("用户上手指南", readme)
        self.assertIn("docs/quick-start.md", readme)
        
        # CLI has separate guide
        self.assertIn("CLI 工具指南", readme)
        self.assertIn("docs/cli-guide.md", readme)
        
        # Quick start should not duplicate CLI details
        self.assertGreater(len(cli_guide), len(quick_start))

    def test_release_docs_publish_context_learning_and_research_without_overclaiming(self):
        readme = read("README.md")
        
        # Context capabilities are published
        self.assertIn("Personal Context", readme)
        
        # Learning is published (via learn command)
        self.assertIn("learn", readme)
        
        # Research brief is published
        self.assertIn("Context-aware Research Brief", readme)
        
        # But doesn't overclaim features
        self.assertNotIn("AI 会自动", readme.lower())
        self.assertNotIn("完全自动", readme.lower())

    def test_user_guide_publishes_fail_stop_messages_without_issue_automation(self):
        quick_start = read("docs/quick-start.md")
        
        # Mentions fail-stop behavior
        if "WM-CAP-001" in quick_start or "WM-RUN-001" in quick_start:
            # If diagnostic codes are mentioned, should not auto-create issues
            self.assertNotIn("自动创建 Issue", quick_start)
            self.assertNotIn("automatically create", quick_start.lower())

    def test_relative_markdown_links_resolve(self):
        """Verify all relative markdown links point to existing files."""
        docs = [
            "README.md",
            "CLAUDE.md", 
            "PROJECT_SUMMARY.md",
            "CHANGELOG.md",
            "docs/INDEX.md",
            "docs/PRODUCT_VISION.md",
            "docs/quick-start.md",
            "docs/cli-guide.md",
            "skills/writing-master/SKILL.md",
            "skills/writing-master/AGENT.md",
            "skills/writing-master/DESIGN_PRINCIPLES.md",
            "skills/writing-rewrite/SKILL.md",
        ]
        
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        missing = []
        
        for doc_path in docs:
            try:
                content = read(doc_path)
            except FileNotFoundError:
                continue
                
            doc_dir = ROOT / Path(doc_path).parent
            
            for match in link_pattern.finditer(content):
                link = match.group(2)
                
                # Skip external links
                if link.startswith(('http://', 'https://', '#', 'mailto:')):
                    continue
                
                # Remove anchor
                link = link.split('#')[0]
                if not link:
                    continue
                
                # Resolve relative to document directory
                target = (doc_dir / link).resolve()
                
                if not target.exists():
                    missing.append(f"{doc_path} -> {link}")
        
        self.assertEqual(missing, [], "Missing local Markdown links:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
