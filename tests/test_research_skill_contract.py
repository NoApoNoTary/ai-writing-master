from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ResearchSkillContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.researcher = (ROOT / "skills/writing-master/agents/researcher.md").read_text(encoding="utf-8")
        self.reference = (ROOT / "skills/writing-master/references/research-brief.md").read_text(encoding="utf-8")
        self.cli = (ROOT / "src/writing_master/cli.py").read_text(encoding="utf-8")

    def test_topic_research_and_article_research_have_separate_outputs(self):
        self.assertIn("`topic_research`", self.researcher)
        self.assertIn("`research-brief-draft.json`", self.researcher)
        self.assertIn("`research`", self.researcher)
        for artifact in ("sources.yaml", "claims.yaml", "asset-manifest.yaml", "research-summary.md"):
            self.assertIn(artifact, self.researcher)
        self.assertIn("不自动进入 `claims.yaml`", self.researcher)

    def test_research_brief_evidence_is_not_an_accepted_article_claim(self):
        self.assertIn("not an accepted article claim", self.reference)
        self.assertIn("文章主张必须在本模式中独立验证和分级", self.researcher)

    def test_topic_research_consumes_only_manifest_selected_task_inputs(self):
        self.assertIn("Manifest `allowed_inputs`", self.researcher)
        self.assertIn("`personal-context-snapshot.json`", self.researcher)
        self.assertIn("`context-materials/ITEM_ID.md`", self.researcher)
        self.assertNotIn("personal-context/author-profile.json", self.researcher)

    def test_missing_live_retrieval_is_blocked_without_a_brief(self):
        self.assertIn('"code": "realtime_research_unavailable"', self.researcher)
        self.assertIn('"missing_capability": "web_search"', self.researcher)
        self.assertIn("创建 Handoff 前", self.researcher)
        self.assertIn("不是 Handoff Result", self.researcher)
        self.assertIn("不写入 Manifest `result_path`", self.researcher)
        self.assertIn("不创建 Handoff", self.researcher)
        self.assertIn("不生成 draft", self.researcher)
        self.assertIn("不创建或覆盖 `research-brief.json`", self.researcher)
        for field in ('"status": "blocked"', '"code": "realtime_research_unavailable"', '"missing_capability": "web_search"'):
            self.assertIn(field, self.reference)
        self.assertIn("not a Handoff Result", self.reference)
        self.assertIn("No Handoff, `research-brief-draft.json`, or `research-brief.json` is created", self.reference)

    def test_researcher_offers_candidates_but_does_not_select_a_final_angle(self):
        self.assertIn("多个候选", self.researcher)
        self.assertIn("不选择最终方向", self.researcher)
        self.assertIn("不选择最终角度", self.reference)

    def test_integration_registers_the_top_level_research_route(self):
        self.assertIn('"research": ("writing_master.commands.research"', self.cli)


if __name__ == "__main__":
    unittest.main()
