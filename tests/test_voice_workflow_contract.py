from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    boundary = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    match = boundary.search(text, start + len(heading))
    return text[start : match.start() if match else len(text)]


class VoiceWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = read("skills/writing-master/SKILL.md")
        self.voice = read("skills/writing-master/references/voice-presets.md")
        self.orchestration = read("skills/writing-master/references/agent-orchestration.md")
        self.review = read("skills/writing-master/references/three-pass-review.md")
        self.context = read("skills/writing-master/references/personal-context.md")
        self.researcher = read("skills/writing-master/agents/researcher.md")
        self.editorial = read("skills/writing-master/agents/editorial-strategist.md")
        self.writer = read("skills/writing-master/agents/writer.md")
        self.auditor = read("skills/writing-master/agents/auditor.md")
        self.rewrite = read("skills/writing-rewrite/SKILL.md")

    def test_selector_defaults_to_natural_default_inside_the_contract(self):
        phase0 = section(self.main, "### Phase 0：内容契约、能力预检与素材接收")

        self.assertIn("`voice_id` 并入内容契约", phase0)
        self.assertIn("默认 `natural-default`", phase0)
        self.assertIn("这不是独立等待点", phase0)
        for voice_id, label in (
            ("natural-default", "自然默认"),
            ("clear-analytical", "清晰分析"),
            ("conversational-observer", "对话观察"),
            ("sharp-commentary", "锐利评论"),
            ("magazine-dialogue-editor", "杂志对谈"),
        ):
            self.assertIn(voice_id, self.voice)
            self.assertIn(label, self.voice)

    def test_voice_profile_contract_is_expression_only_and_preserves_content(self):
        for token in (
            '"schema_version": 1',
            '"scope": "expression_only"',
            '"facts"',
            '"evidence_boundaries"',
            '"core_thesis"',
            '"author_position"',
            '"real_experiences"',
            '"sentence_rhythm"',
            '"paragraph_shape"',
            '"transitions"',
            '"certainty"',
            '"humor"',
        ):
            self.assertIn(token, self.voice)

    def test_phase_one_and_two_are_voice_free_but_phase_three_and_audit_read_snapshot(self):
        phase1 = section(self.main, "### Phase 1：事实与素材双轨调研")
        phase2 = section(self.main, "### Phase 2：角度、读者决策与 Storyboard")
        phase3 = section(self.main, "### Phase 3：初稿")
        phase4 = section(self.main, "### Phase 4：三层审校与修订")

        self.assertIn("不得读取 `voice-profile-snapshot.json`", phase1)
        self.assertIn("不得读取 `voice-profile-snapshot.json`", phase2)
        self.assertIn("只读取任务 `voice-profile-snapshot.json`", phase3)
        self.assertIn("同一任务 `voice-profile-snapshot.json`", phase4)

    def test_deep_manifest_exposes_voice_only_to_writer_and_auditor(self):
        self.assertIn("只有 Writer 与 Auditor", self.orchestration)
        self.assertIn("`voice-profile-snapshot.json`", self.orchestration)
        self.assertIn("sha256", self.orchestration)
        self.assertIn("Researcher 和 Editorial Strategist", self.orchestration)
        self.assertIn("不得**列出", self.orchestration)

        for card in (self.writer, self.auditor):
            self.assertIn("`voice-profile-snapshot.json`", card)
            self.assertIn("`sha256`", card)
        for card in (self.researcher, self.editorial):
            self.assertIn("不得读取 `voice-profile-snapshot.json`", card)

    def test_voice_audit_issues_are_located_and_rule_backed(self):
        voice_audit = section(self.review, "## 第三层：Voice Audit")

        for token in (
            "`location`",
            "`profile_rule`",
            "`excerpt`",
            "`required_change`",
            "voice.<field>",
            "不要求加强结论",
        ):
            self.assertIn(token, voice_audit)
        self.assertIn("不以“像 AI”、像某人或百分比代替证据", self.auditor)

    def test_status_recovery_failure_and_learning_are_voice_safe(self):
        for token in (
            "voice: {label}",
            "voice_snapshot: {ready | legacy | unavailable}",
            "`legacy-natural`",
            "`voice_snapshot: unavailable`",
            "显式非默认 Voice",
            "Snapshot 校验失败不降级",
        ):
            self.assertIn(token, self.main + self.voice)
        self.assertIn("非默认 Voice 任务不作为确认式风格学习的 baseline 或 evidence", self.context)
        self.assertIn("不生成 Style Observation", self.context)
        self.assertIn("writing-master learn propose CANDIDATE.json --run-dir RUN_DIR", self.main)

    def test_rewrite_has_no_voice_selector(self):
        self.assertIn("Rewrite 不新增、展示或解析 Voice Selector", self.rewrite)
        self.assertIn("保留源稿已验收的写作声音，不重新选择 Voice", self.rewrite)


if __name__ == "__main__":
    unittest.main()
