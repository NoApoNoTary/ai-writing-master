import sys
import types
import unittest
from contextlib import redirect_stderr
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


if __name__ == "__main__":
    unittest.main()
