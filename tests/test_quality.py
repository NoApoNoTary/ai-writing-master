import unittest

from writing_master.commands.quality import score_article


class MechanicalQualityTests(unittest.TestCase):
    def test_score_contains_only_computable_dimensions(self):
        result = score_article(
            "短句。这里是一句明显更长的句子，用于形成可观察的节奏变化和更完整的输入。\n\n"
            "第二段换一种长度，继续补充可以被机械规则观察的正文内容。再补一句形成新的节奏。\n\n"
            "第三段负责让段落数量达到完整文章检查所需的最小样本。最后用一句话收束测试文本。"
        )

        self.assertEqual(result["score_type"], "mechanical_style")
        self.assertEqual(result["status"], "scored")
        self.assertTrue(result["sufficient_data"])
        self.assertEqual(result["quality_score"], result["mechanical_score"])
        self.assertNotIn("accuracy", result["dimensions"])
        self.assertAlmostEqual(sum(result["weights"].values()), 1.0)
        self.assertIn("factual_accuracy", result["manual_review_required"])
        self.assertIn("editorial_judgment", result["manual_review_required"])

    def test_short_input_is_reported_as_insufficient(self):
        result = score_article("# 标题\n\n短句。")

        self.assertEqual(result["status"], "insufficient_data")
        self.assertFalse(result["sufficient_data"])
        self.assertIsNone(result["mechanical_score"])
        self.assertIsNone(result["quality_score"])
        self.assertIn("char_count_below_100", result["insufficient_reasons"])


if __name__ == "__main__":
    unittest.main()
