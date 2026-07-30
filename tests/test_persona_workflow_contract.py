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


class PersonaWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = read("skills/writing-master/SKILL.md")
        self.contract = read("skills/writing-master/references/persona-skills.md")
        self.orchestration = read("skills/writing-master/references/agent-orchestration.md")
        self.researcher = read("skills/writing-master/agents/researcher.md")
        self.editorial = read("skills/writing-master/agents/editorial-strategist.md")
        self.writer = read("skills/writing-master/agents/writer.md")
        self.auditor = read("skills/writing-master/agents/auditor.md")
        self.voice = read("skills/writing-master/references/voice-presets.md")

    def test_every_contract_offers_all_three_persona_modes(self):
        phase0 = section(self.main, "### Phase 0：内容契约、能力预检与素材接收")
        for label in ("不使用", "让这个人格来写", "参考这个人格写"):
            self.assertIn(label, phase0)
            self.assertIn(label, self.contract)
        for mode in ("none", "author", "reference"):
            self.assertIn(mode, self.contract)

    def test_skill_is_saved_verbatim_and_brief_is_free_form(self):
        for token in (
            "原始 `SKILL.md` 的字节原样保存",
            "`persona-skill.md`",
            "自由格式 `{run_dir}/persona-brief.md`",
            "来源路径",
            "SHA-256",
            "不采用固定字段集合或 Persona Schema",
        ):
            self.assertIn(token, self.contract)

    def test_background_and_content_type_paths_are_explicit(self):
        for token in (
            "使用人格 Skill 的默认背景",
            "追加用户提供的项目背景",
            "本次不生成背景",
            "项目背景只进入当前任务",
            "analysis",
            "review",
            "opinion",
            "tutorial",
            "story",
            "release",
        ):
            self.assertIn(token, self.contract)

    def test_author_and_reference_identity_boundaries_differ(self):
        self.assertIn("可采用人格的背景、判断、表达和第一人称叙事", self.contract)
        self.assertIn("正文仍以当前作者身份表达", self.contract)
        self.assertIn("构造性第一人称背景", self.writer)
        self.assertIn("正文仍保持当前作者身份", self.writer)

    def test_researcher_is_neutral_and_other_roles_share_one_brief(self):
        for token in ("`persona-skill.md`", "`persona-brief.md`", "事实资料中立"):
            self.assertIn(token, self.researcher)
        for card in (self.editorial, self.writer, self.auditor):
            self.assertIn("`persona-brief.md`", card)
            self.assertIn("`sha256`", card)
        self.assertIn("Editorial Strategist、Writer 与 Auditor", self.orchestration)
        self.assertIn("同一份 Persona Brief", self.orchestration)

    def test_persona_and_voice_stay_composable_and_separate(self):
        combined = self.contract + self.voice + self.main
        for token in (
            "两者可以组合",
            "Persona 负责身份",
            "Voice 只负责表层表达",
            "互不转换",
            "voice-profile-snapshot.json",
        ):
            self.assertIn(token, combined)

    def test_resume_reuses_frozen_files_and_scope_stays_small(self):
        for token in (
            "恢复任务只校验并复用任务内",
            "不采用外部 Skill 的当前版本",
            "固定 Persona Schema",
            "自动学习",
            "Registry 导入",
            "目录扫描",
            "推荐引擎",
            "Marketplace",
        ):
            self.assertIn(token, self.contract)


if __name__ == "__main__":
    unittest.main()
