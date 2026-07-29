import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CiContractTests(unittest.TestCase):
    def test_ci_runs_the_release_checks(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        for token in (
            "pull_request:",
            "actions/checkout@v7",
            "actions/setup-python@v7",
            "python -m unittest discover -s tests -v",
            "python -m compileall -q src tests",
            "bash -n install.sh",
            "./bin/writing-master learn --help",
            "./bin/writing-master research --help",
            "./bin/writing-master voice --help",
            "./bin/writing-master voice list --json",
            "python -m build",
        ):
            self.assertIn(token, workflow)


if __name__ == "__main__":
    unittest.main()
