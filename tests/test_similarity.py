from contextlib import redirect_stderr
from io import StringIO
import unittest

from writing_master.commands.similarity import main, max_pairwise


class SimilarityTests(unittest.TestCase):
    def test_max_pairwise_returns_largest_pair(self):
        texts = ["abcdef", "abcxyz", "uvwxyz"]

        self.assertGreater(
            max_pairwise(texts),
            max_pairwise([texts[0], texts[2]]),
        )
        self.assertEqual(max_pairwise([texts[0]]), 0.0)

    def test_cli_rejects_incomplete_parameters(self):
        for argv in (["only-one.md"], ["a.md", "b.md", "-n", "0"]):
            with self.subTest(argv=argv), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(argv)
                self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
