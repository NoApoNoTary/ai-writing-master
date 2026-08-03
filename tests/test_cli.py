import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from writing_master.cli import main


class CliTests(unittest.TestCase):
    def test_subcommand_receives_rest_without_mutating_sys_argv(self):
        original = sys.argv[:]
        received = []
        module = types.SimpleNamespace(main=lambda argv: (received.append(argv), 7)[1])
        with patch("writing_master.cli.importlib.import_module", return_value=module):
            self.assertEqual(main(["quality", "article.md", "--json"]), 7)
        self.assertEqual(received, [["article.md", "--json"]])
        self.assertEqual(sys.argv, original)

    def test_unknown_command_returns_2(self):
        with redirect_stderr(StringIO()):
            self.assertEqual(main(["unknown"]), 2)

    def test_integration_registers_learn_research_voice_and_persona(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--help"]), 0)
        self.assertIn("learn", output.getvalue())
        self.assertIn("research", output.getvalue())
        self.assertIn("voice", output.getvalue())
        self.assertIn("persona", output.getvalue())
        self.assertIn("failure-cases", output.getvalue())

        for command, token in (
            ("learn", "propose"),
            ("research", "verify"),
            ("voice", "snapshot"),
            ("persona", "snapshot"),
            ("failure-cases", "propose"),
        ):
            output = StringIO()
            with redirect_stdout(output), self.assertRaises(SystemExit) as captured:
                main([command, "--help"])
            self.assertEqual(captured.exception.code, 0)
            self.assertIn(token, output.getvalue())


if __name__ == "__main__":
    unittest.main()
