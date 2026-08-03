import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallContractTests(unittest.TestCase):
    def test_voice_registry_is_declared_as_package_data(self):
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('[tool.setuptools.package-data]', project)
        self.assertIn('voice_profiles/*.json', project)
        self.assertTrue((ROOT / "src/writing_master/voice_profiles/registry.json").is_file())

    def test_persona_templates_are_declared_as_package_data(self):
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('persona_templates/*/SKILL.md', project)
        self.assertTrue((ROOT / "src/writing_master/persona_templates/khazix-writer/SKILL.md").is_file())

    def test_cli_installs_from_repository_root(self):
        script = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertNotIn('$PROJECT_DIR/cli', script)
        self.assertIn('uv tool install --editable "$PROJECT_DIR"', script)
        self.assertIn('pipx install --editable "$PROJECT_DIR"', script)

    def test_installer_does_not_claim_missing_templates(self):
        script = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertNotIn('templates/config.example.yaml', script)
        self.assertNotIn('templates/style.example.yaml', script)

    def test_installer_advertises_only_the_two_single_channel_entries(self):
        script = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn("writing-master    - 单渠道完整创作主入口", script)
        self.assertIn("writing-rewrite   - 单渠道内容改写", script)
        self.assertIn("把这篇文章改写成 X Thread", script)
        self.assertNotIn("改写成小红书", script)

    def test_installer_preserves_existing_skill_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            existing = home / ".codex/skills/writing-master"
            existing.mkdir(parents=True)
            sentinel = existing / "KEEP.txt"
            sentinel.write_text("user-owned", encoding="utf-8")
            legacy = home / ".writing-master/personal_materials/experiences/legacy.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("legacy remains explicit", encoding="utf-8")

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = "/usr/bin:/bin"
            result = subprocess.run(
                ["bash", str(ROOT / "install.sh")],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "user-owned")
            self.assertIn("保留现有文件", result.stdout)
            personal_context = home / ".writing-master" / "personal-context"
            self.assertTrue(personal_context.is_dir())
            self.assertFalse((personal_context / "author-profile.json").exists())
            self.assertFalse((personal_context / "knowledge-index.json").exists())
            self.assertEqual(legacy.read_text(encoding="utf-8"), "legacy remains explicit")


if __name__ == "__main__":
    unittest.main()
