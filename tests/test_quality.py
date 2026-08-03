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

    def test_process_leakage_findings_are_independent_and_include_title(self):
        body = "\n\n".join(["正文。" * 40] * 3)
        text = "# 要不要介绍 Qwen API？可以，但别写成广告\n\n" + body
        baseline = score_article(body)
        result = score_article(text)

        self.assertEqual(result["status"], "scored")
        self.assertEqual(result["mechanical_score"], baseline["mechanical_score"])
        self.assertEqual(result["mechanical_score"], result["quality_score"])
        self.assertGreaterEqual(len(result["findings"]), 2)
        self.assertTrue(all(f["line_number"] == 1 for f in result["findings"]))
        self.assertTrue(all(f["original_text"] == text.splitlines()[0] for f in result["findings"]))
        self.assertTrue(all(f["rule_id"].startswith("PROCESS-") for f in result["findings"]))
        self.assertTrue(all(f["severity"] == "blocking" for f in result["findings"]))

    def test_internal_artifact_name_has_a_located_finding(self):
        result = score_article("先检查 review-report.yaml。\n\n" + "\n\n".join(["正文。" * 40] * 3))

        self.assertEqual(len(result["findings"]), 1)
        finding = result["findings"][0]
        self.assertEqual(finding["rule_id"], "PROCESS-ARTIFACT-001")
        self.assertEqual(finding["line_number"], 1)
        self.assertEqual(finding["original_text"], "先检查 review-report.yaml。")

    def test_technical_api_key_reminder_is_not_editorial_meta_language(self):
        result = score_article("# API 安全\n\n不要把 API key 写进仓库。" + ("补充说明。" * 80))

        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
