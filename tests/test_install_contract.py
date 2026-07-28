import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallContractTests(unittest.TestCase):
    def test_cli_installs_from_repository_root(self):
        script = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertNotIn('$PROJECT_DIR/cli', script)
        self.assertIn('uv tool install --editable "$PROJECT_DIR"', script)
        self.assertIn('pipx install --editable "$PROJECT_DIR"', script)

    def test_installer_does_not_claim_missing_templates(self):
        script = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertNotIn('templates/config.example.yaml', script)
        self.assertNotIn('templates/style.example.yaml', script)

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
