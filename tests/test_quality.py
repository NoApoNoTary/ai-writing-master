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
        self.assertTrue(all(f["original_text"] == "要不要介绍 Qwen API？" or f["original_text"] == "可以，但别写成广告" for f in result["findings"]))
        self.assertTrue(all(f["rule_id"].startswith("PROCESS-") for f in result["findings"]))
        self.assertTrue(all(f["severity"] == "blocking" for f in result["findings"]))

    def test_internal_artifact_name_has_a_located_finding(self):
        samples = (
            "先检查 review-report.yaml。",
            "先检查 asset-manifest.yaml。",
            "打开 revision-report.yaml 查看修订记录。",
        )

        for sample in samples:
            with self.subTest(sample=sample):
                result = score_article(sample + "\n\n" + "\n\n".join(["正文。" * 40] * 3))
                self.assertEqual(len(result["findings"]), 1)
                finding = result["findings"][0]
                self.assertEqual(finding["rule_id"], "PROCESS-ARTIFACT-001")
                self.assertEqual(finding["line_number"], 1)
                self.assertEqual(finding["original_text"], sample)

    def test_technical_api_key_reminder_is_not_editorial_meta_language(self):
        result = score_article("# API 安全\n\n不要把 API key 写进仓库。" + ("补充说明。" * 80))

        self.assertEqual(result["findings"], [])

    def test_spec_categories_have_narrow_high_confidence_findings(self):
        samples = (
            "根据用户的要求，我们先介绍 Qwen API。",
            "按你的要求，本文不介绍安装过程。",
            "发布时标题要短一些。",
            "这里需要配一张图。",
            "来源策略：优先官方文档。",
            "是否应该介绍 Qwen API？",
            "是否要介绍 Qwen API？",
            "应不应该写 Qwen API？",
            "需不需要提及 Qwen API？",
            "这部分是否需要写 Qwen API？",
        )

        for sample in samples:
            with self.subTest(sample=sample):
                result = score_article(sample + "\n\n" + "正文。" * 80)
                self.assertTrue(result["findings"])
                self.assertEqual(result["findings"][0]["original_text"], sample)

    def test_finding_preserves_only_the_matching_sentence_on_a_multi_sentence_line(self):
        line = "这句属于正常正文。根据用户要求，这里需要补充 API。后一句也属于正常正文。"
        result = score_article(line + "\n\n" + "正文。" * 80)

        self.assertEqual(result["findings"][0]["line_number"], 1)
        self.assertEqual(result["findings"][0]["original_text"], "根据用户要求，这里需要补充 API。")

    def test_normal_product_user_intent_is_not_process_leakage(self):
        samples = (
            "用户希望导出 PDF。",
            "用户要求系统支持双因素认证。",
            "数据来源策略是优先使用官方统计。",
            "数据来源策略是优先官方文档。",
            "brief.yaml 是服务配置文件。",
            "根据用户要求，我们修改了登录流程。",
            "按用户要求，我们补充了批量导出功能。",
        )

        for sample in samples:
            with self.subTest(sample=sample):
                result = score_article(sample + "\n\n" + "正文。" * 80)
                self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
