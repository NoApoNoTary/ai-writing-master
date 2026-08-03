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
        self.review = read("skills/writing-master/references/three-pass-review.md")
        self.context = read("skills/writing-master/references/personal-context.md")

    def test_every_contract_offers_all_three_persona_modes(self):
        phase0 = section(self.main, "### Phase 0：内容契约、能力预检与素材接收")
        for label in ("不使用", "让这个人格来写", "参考这个人格写"):
            self.assertIn(label, phase0)
            self.assertIn(label, self.contract)
        for mode in ("none", "author", "reference"):
            self.assertIn(mode, self.contract)

    def test_builtin_khazix_template_is_explicit_and_identity_safe(self):
        for token in (
            "`khazix-writer`",
            "卡兹克科技观察（实验）",
            "不注入真实作者身份、经历或第一人称事实",
            "writing-master persona list --json",
            "builtin:khazix-writer",
        ):
            self.assertIn(token, self.contract)

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

    def test_selected_persona_brief_is_source_neutral_for_downstream_roles(self):
        for document in (self.main, self.orchestration, self.editorial, self.writer, self.auditor):
            self.assertIn("选择 Persona", document)
            self.assertIn("`persona-brief.md`", document)
        self.assertIn("内置或外部 Persona", self.orchestration)
        self.assertIn("不回读来源", self.orchestration)
        self.assertIn("不得读取 `persona-skill.md`、`persona-brief.md`", self.researcher)
        self.assertIn("Persona 来源 Skill（内置或外部）", self.researcher)
        self.assertIn("所选 Persona Skill（内置或外部）", self.voice)
        self.assertIn("选择 Persona（内置或外部）", self.review)
        self.assertIn("所选 Persona（内置或外部）", self.context)

    def test_ready_persona_or_voice_change_creates_a_new_run_without_overwrite(self):
        for token in (
            "`persona_snapshot=ready`",
            "`voice_snapshot=ready`",
            "展示同样的差异",
            "创建新 Writing run",
            "新 run 的 `source_task_id` 记录当前 `task_id`",
            "当前 run 的关联字段和冻结 Snapshot 均不改写",
        ):
            self.assertIn(token, self.main)
        for token in (
            "若 `persona_snapshot=ready`",
            "新 run 的 `source_task_id` 记录原 `task_id`",
            "原 run 的关联字段、`persona-skill.md`、`persona-brief.md` 和 hash 保持不变",
            "`contract` 从 `pending` 重新确认",
        ):
            self.assertIn(token, self.contract)

    def test_voice_snapshot_controls_overlapping_surface_expression(self):
        surface = "词汇、句式、节奏、段落、开场、转折、确定性、幽默和类比"
        for document in (self.contract, self.main, self.writer):
            self.assertIn(surface, document)
            self.assertIn("显式非默认 Voice", document)
            self.assertIn("不得覆盖", document)
        self.assertIn("词汇、句式、节奏、段落形态、开场", self.voice)
        self.assertIn("显式非默认 Voice 以 Voice Snapshot 为准", self.voice)
        self.assertIn("Persona 决定身份、判断与背景", self.contract)
        self.assertIn("`natural-default` 时 Persona 的表达建议", self.contract)
        template = read("src/writing_master/persona_templates/khazix-writer/SKILL.md")
        for token in ("R01–R25", "A01–A09", "Voice Snapshot 统一决定", "不得覆盖它"):
            self.assertIn(token, template)

    def test_resume_reuses_frozen_files_and_scope_stays_small(self):
        for token in (
            "恢复任务只校验并复用任务内",
            "不回读或从任何内置、外部来源重建当前版本",
            "固定 Persona Schema",
            "自动学习",
            "Registry 导入",
            "目录扫描",
            "推荐引擎",
            "Marketplace",
        ):
            self.assertIn(token, self.contract)

    def test_persona_issues_use_existing_audit_layers(self):
        orchestration = read("skills/writing-master/references/agent-orchestration.md")
        review = read("skills/writing-master/references/three-pass-review.md")
        for document in (self.auditor, orchestration, review):
            self.assertIn("layer: evidence | editorial | voice", document)
        self.assertIn("身份、背景、模式或采用边界违规归入 `layer: editorial`", self.auditor)
        self.assertIn("表层表达冲突归入 `layer: voice`", self.auditor)


if __name__ == "__main__":
    unittest.main()
