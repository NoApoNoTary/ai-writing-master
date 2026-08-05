import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return a Markdown heading and everything before its peer/parent."""
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    boundary = re.compile(rf"^#{{1,{level}}}\s", re.MULTILINE)
    match = boundary.search(text, start + len(heading))
    return text[start : match.start() if match else len(text)]


class WritingSkillContractTests(unittest.TestCase):
    def assert_in_order(self, text: str, *tokens: str) -> None:
        position = 0
        for token in tokens:
            found = text.find(token, position)
            self.assertNotEqual(found, -1, f"Expected {token!r} after {position}")
            position = found + len(token)

    def test_content_routing_contract(self):
        main = read("skills/writing-master/SKILL.md")
        routing = read("skills/writing-master/references/content-routing.md")
        editorial = read("skills/writing-master/agents/editorial-strategist.md")
        writer = read("skills/writing-master/agents/writer.md")
        auditor = read("skills/writing-master/agents/auditor.md")
        review = read("skills/writing-master/references/three-pass-review.md")
        persona = read("skills/writing-master/references/persona-skills.md")
        orchestration = read("skills/writing-master/references/agent-orchestration.md")
        waiting = section(main, "## 用户等待与继续方式")
        phase2 = section(main, "### Phase 2：角度、读者决策与 Storyboard")
        self.assertIn("references/content-routing.md", main)
        for depth in ("none", "scenario", "actionable", "reproducible"):
            self.assertIn(depth, routing)
        self.assert_in_order(main, "Phase 0", "Article Research 完成后由 Phase 2", "recommended_combo")
        self.assertIn("已选 candidate 或已明确主题", phase2)
        for field in ("label", "content_type", "application_depth", "reason", "required_blocks"):
            self.assertIn(field, routing)
        self.assertIn("修改：组合类型=实测评测+场景应用", main)
        self.assertIn("不创建独立的组合类型等待点", phase2)
        self.assertNotIn("| 组合类型 |", waiting)
        self.assertIn("用户已明确路线时仍展示建议但保留用户选择", phase2)
        self.assertIn("`content_type` 随内容契约和 Persona Snapshot 在当前 run 内冻结", persona)
        self.assertIn("采用它时新建 Writing run", routing)
        self.assertIn("保持已确认的 `content_type`", phase2)
        self.assertIn("合成示例需要明确标注", routing)
        self.assertIn("Content Routing", orchestration)
        self.assertIn("精确 SHA-256", orchestration)
        self.assertNotIn("references/content-routing.md", writer)
        for doc in (editorial, writer, auditor, review):
            self.assertIn("recommended_combo", doc)
        self.assertIn("application_check", auditor)
        self.assertIn("application_check", review)
        self.assertIn("只有 `pass` 状态可使内容验收通过", routing)

    def test_p1_spec_failure_cases_and_endnotes_contract(self):
        main = read("skills/writing-master/SKILL.md")
        spec = read("skills/writing-master/references/run-spec.md")
        failures = read("skills/writing-master/references/failure-cases.md")
        writer = read("skills/writing-master/agents/writer.md")
        auditor = read("skills/writing-master/agents/auditor.md")

        for token in ("`spec.md`", "failure-case-snapshot.md", "references/run-spec.md", "references/failure-cases.md"):
            self.assertIn(token, main)
        for token in ("读者目标", "内部执行约束", "冻结", "SHA-256", "brief.md"):
            self.assertIn(token, spec)
        for token in ("proposed", "active", "superseded", "FC-20260803-001", "原子替换"):
            self.assertIn(token, failures)
        for card in (writer, auditor):
            self.assertIn("failure-case-snapshot.md", card)
            self.assertIn("source_display=endnotes", card)
            self.assertIn("官方来源", card)
            self.assertIn("独立来源", card)

    def test_complete_writing_requires_explicit_mode_selection(self):
        main = read("skills/writing-master/SKILL.md")

        self.assertIn("references/mode-selection.md", main)
        self.assertIn("Canonical prompt", read("skills/writing-master/references/mode-selection.md"))
        self.assertLess(main.index("### 模式选择闸门"), main.index("### Phase 0"))

    def test_mode_prompt_stays_in_sync_across_user_facing_docs(self):
        prompt_lines = [
            "请选择本次写作模式：",
            "1. 快速草稿：单 Agent，最少调研与一次审校，适合先拿到可讨论版本。",
            "2. 标准写作（推荐）：单 Agent，完整调研、素材规划、写作与三层审校。",
            "3. 深度写作：多 Agent 分工，独立研究、策划、写作和审计，适合重要长文。",
        ]
        canonical = read("skills/writing-master/references/mode-selection.md")
        for line in prompt_lines:
            self.assertIn(line, canonical, f"Canonical prompt 缺少统一模式文案: {line}")

        self.assertIn("mode-selection.md", read("README.md"))
        quick_start = read("docs/quick-start.md")
        for label in ("快速草稿", "标准写作", "深度写作"):
            self.assertIn(label, quick_start)
        self.assertNotIn("mode-selection.md", quick_start)

    def test_selected_mode_readiness_stops_before_expensive_work(self):
        main = read("skills/writing-master/SKILL.md")
        mode = section(
            read("skills/writing-master/references/mode-selection.md"),
            "## 所选模式就绪闸门",
        )
        gate = section(main, "### 所选模式就绪闸门")

        self.assertLess(main.index("### 模式选择闸门"), main.index("### 所选模式就绪闸门"))
        self.assertLess(main.index("### 所选模式就绪闸门"), main.index("### Phase 0"))
        for operation in ("素材提取", "实时检索", "正文生成", "视觉生成", "角色派发"):
            self.assertIn(operation, gate)
            self.assertIn(operation, mode)
        self.assertIn("调研和生成调用次数为 0", gate)
        self.assertIn("调用次数必须为 0", mode)
        self.assertIn("mode_readiness=ready", gate)
        self.assertIn("Phase 0–6 流程不变", gate)
        for forbidden in ("等待用户选择 quick", "改用标准", "切换到 standard"):
            self.assertNotIn(forbidden, gate + mode)

    def test_mode_failures_use_stable_user_messages_without_internal_terms(self):
        main = read("skills/writing-master/SKILL.md")
        unavailable = section(main, "### 用户正文：所选模式未就绪")
        interrupted = section(main, "### 用户正文：运行途中停止")

        self.assertIn("诊断编号：WM-CAP-001", unavailable)
        self.assertIn("所选的{模式显示名}当前未就绪", unavailable)
        self.assertIn("快速草稿", diagnostics := section(main, "### 诊断详情"))
        self.assertIn("标准写作", diagnostics)
        self.assertIn("深度写作", diagnostics)
        self.assertIn("版本：VERSION", unavailable)
        self.assertIn("诊断编号：WM-RUN-001", interrupted)
        self.assertIn("已有内容已保留", interrupted)
        for body in (unavailable, interrupted):
            self.assertIn("提交 Issue", body)
            for internal in ("Runtime", "Handoff", "Agent", "multi-agent", "异常栈"):
                self.assertNotIn(internal, body)

        self.assertIn("内部异常栈", diagnostics)
        self.assertIn("不自动创建 Issue", diagnostics)
        self.assertIn("不生成 Issue 草稿", diagnostics)

    def test_mid_run_mode_failure_preserves_outputs_without_fallback(self):
        main = section(read("skills/writing-master/SKILL.md"), "## 恢复与失败的用户表现")
        orchestration = section(
            read("skills/writing-master/references/agent-orchestration.md"),
            "## 失败即停",
        )

        for contract in (main, orchestration):
            self.assertIn("保留", contract)
            self.assertIn("不切换", contract)
            self.assertIn("WM-RUN-001", contract)
        self.assertIn("不由当前 Agent 补做深度角色工作", main)
        self.assertIn("不得由 Lead 或当前 Agent 补做缺失角色", orchestration)
        self.assertIn("不改变最终交付标准", main)

    def test_readiness_diagnostic_is_written_before_phase_zero_content(self):
        main = section(read("skills/writing-master/SKILL.md"), "### 所选模式就绪闸门")
        mode = section(
            read("skills/writing-master/references/mode-selection.md"),
            "## 所选模式就绪闸门",
        )

        for contract in (main, mode):
            self.assertIn("最小运行目录", contract)
            self.assertIn("capability-preflight.md", contract)
            self.assertIn("不创建 Brief、素材副本或其他写作产物", contract)

    def test_mode_selection_requires_an_explicit_resume_target(self):
        entry_rules = section(
            read("skills/writing-master/references/mode-selection.md"),
            "## 入口规则",
        )

        self.assert_in_order(
            entry_rules,
            "“继续上次”时要求用户指定 `task_id` 或运行目录",
            "只有运行时已验证恢复能力后才读取 `status.json.mode`",
            "Product–Technical Gap",
        )
        self.assertNotIn("“继续上次”读取 `status.json.mode`", entry_rules)

    def test_quick_mode_produces_the_shared_core_artifacts(self):
        quick = section(
            read("skills/writing-master/references/mode-selection.md"),
            "### 1. 快速草稿（quick）",
        )

        self.assertIn("与标准模式相同的核心文件", quick)
        for artifact in (
            "brief.md",
            "sources.yaml",
            "claims.yaml",
            "asset-manifest.yaml",
            "draft-v1.md",
            "review-report.yaml",
            "revision-report.yaml",
            "final.md",
            "acceptance-report.md",
        ):
            self.assertIn(artifact, quick)
        self.assertIn("内容契约", quick)

    def test_multi_agent_is_deep_mode_only(self):
        main = read("skills/writing-master/SKILL.md")
        orchestration = read("skills/writing-master/references/agent-orchestration.md")

        self.assertIn("快速草稿和标准写作始终使用当前 Agent", main)
        self.assertIn("只有深度模式启用多 Agent", main)
        self.assertIn("本文件只在 `mode=deep` 时读取", orchestration)

    def test_codex_handoff_persists_agent_ref_before_spawn(self):
        orchestration = read("skills/writing-master/references/agent-orchestration.md")

        self.assert_in_order(
            orchestration,
            "writing-master handoff prepare RUN_DIR",
            "agent_ref = task_name",
            "writing-master handoff start RUN_DIR --agent-ref AGENT_REF",
            'spawn_agent(fork_turns="none", task_name=AGENT_REF)',
            "Agent 只写 Manifest output_root 和 Result",
            "writing-master handoff complete RUN_DIR",
        )
        self.assertIn("writing-master handoff recover-lost RUN_DIR --agent-ref AGENT_REF", orchestration)
        self.assertIn("Host 先按精确 `agent_ref` 查询宿主 liveness", orchestration)

    def test_claude_code_handoff_terminalizes_every_foreground_outcome(self):
        orchestration = section(
            read("skills/writing-master/references/agent-orchestration.md"),
            "### Claude Code foreground host adapter",
        )

        self.assert_in_order(
            orchestration,
            "普通前台 subagent `Agent` 调用",
            "生成唯一 opaque AGENT_REF",
            "writing-master handoff start RUN_DIR --agent-ref AGENT_REF",
            "Agent(run_in_background=false, prompt=包含 AGENT_REF",
            "Result.agent_ref == AGENT_REF",
            "前台调用产生明确终止结果后，调用 writing-master handoff complete RUN_DIR",
            "Runtime 以 Result 与暂存输出为事实源，将 attempt 原子推进到 completed 或 failed",
        )
        agent_lines = [line for line in orchestration.splitlines() if "Agent(" in line]
        self.assertTrue(agent_lines)
        self.assertTrue(all("name=" not in line for line in agent_lines))
        self.assertIn("不作为 `Agent.name`", orchestration)
        self.assertIn("不使用 experimental agent team teammate", orchestration)
        self.assertIn("start` 成功前禁止调用 `Agent`", orchestration)
        self.assertIn("必须且只能调用一次 `complete`", orchestration)
        self.assertIn("`complete` 是终止化与校验屏障，不是“成功专用”命令", orchestration)
        self.assertIn("合法的 `Result.status == completed`", orchestration)
        self.assertIn("合法的 `Result.status == failed`", orchestration)
        self.assertIn("`complete` 原子地将当前 attempt 标记为 `failed`", orchestration)
        self.assertIn("Agent` 抛错、被明确中止、返回被截断或未完成的报告时仍调用 `complete`", orchestration)
        self.assertIn("缺少或格式错误的 Result", orchestration)
        self.assertIn("立即 fail-stop", orchestration)
        self.assertNotIn("不调用 `complete`", orchestration)
        self.assertIn("不得把“等待中”判为丢失", orchestration)
        self.assertIn("不得调用 `recover-lost`", orchestration)
        self.assertIn("不会向 Handoff 提供可恢复的 teammate identity", orchestration)
        self.assertIn("不适用于本节的普通 Claude Code foreground 调用", orchestration)
        self.assertIn("`recover-lost` 仍只适用于具有宿主可查询 invocation identity 的编排适配器", orchestration)
        self.assertIn("`complete` 或明确的 Host 丢失处置已将旧 attempt 终止后", orchestration)
        self.assertIn("不得复用旧 ref", orchestration)

    def test_baoyu_is_early_preflight_and_late_production(self):
        routing = read("skills/writing-master/references/baoyu-integration.md")

        self.assertIn("Level 1：Preflight + Material Intake", routing)
        self.assertIn("baoyu-url-to-markdown", routing)
        self.assertIn("baoyu-youtube-transcript", routing)
        self.assertIn("Level 3：Production", routing)
        self.assertIn("早预检、早摄入、晚生成、后发布", routing)

    def test_wechat_draft_completion_recommends_timing_without_auto_publish(self):
        publish = section(
            read("skills/writing-master/references/baoyu-integration.md"),
            "### Level 4：Publish（验收之后）",
        )

        for token in (
            "微信公众号草稿创建或更新成功后",
            "YYYY-MM-DD HH:MM–HH:MM",
            "Asia/Shanghai / UTC+08:00",
            "一句简短理由",
            "数据依据",
            "账号时区",
            "优先使用该账号后台历史数据",
            "历史数据不可用时",
            "通用经验估计",
            "明确标注",
            "停在草稿状态",
            "不自动执行正式发布",
        ):
            self.assertIn(token, publish)

    def test_wechat_timing_completion_is_structured_and_blocking(self):
        routing = read("skills/writing-master/references/baoyu-integration.md")
        main = read("skills/writing-master/SKILL.md")
        for token in ("basis_type", "basis_detail", "confidence", "backup_window", "wechat-draft-report.json"):
            self.assertIn(token, routing)
            self.assertIn(token, main)
        self.assertIn("字段缺失或格式错误时任务不得标记为完整完成", routing)
        self.assertIn("publish_intent=draft_only", routing)

    def test_cover_generation_has_fail_fast_acceptance_gate(self):
        cover = read("skills/writing-master/SKILL.md")
        for token in (
            "planned",
            "prompt_ready",
            "generated_raw",
            "visual_qa_passed",
            "accepted",
            "blocked_waiting_user",
            "输出 SHA-256",
            "HTML、SVG、Canvas、浏览器截图、Pillow/ImageMagick",
        ):
            self.assertIn(token, cover)

    def test_main_skill_has_user_visible_status_and_waiting_contract(self):
        main = read("skills/writing-master/SKILL.md")

        for field in (r"(?:当前)?任务", r"(?:当前)?模式", r"(?:当前)?阶段", r"已完成", r"下一步"):
            self.assertRegex(main, field)
        for state in (r"等待模式", r"等待(?:内容)?契约确认", r"等待方向确认", r"等待问题处理"):
            self.assertRegex(main, state)
        self.assertRegex(main, r"(?:当前动作|正在执行)")

    def test_main_skill_returns_a_material_receipt(self):
        main = read("skills/writing-master/SKILL.md")

        self.assertIn("素材接收结果", main)
        for field in ("已接收", "已提取", "等待处理", "失败"):
            self.assertIn(field, main)
        self.assertRegex(main, r"(?s)素材接收结果.{0,600}(?:需要你确认|待确认)")
        self.assertRegex(main, r"(?s)失败.{0,160}(?:不阻塞|继续处理).{0,160}(?:其他|其余|无关)")

    def test_main_skill_defines_delivery_package_and_blocking_issue_behavior(self):
        main = read("skills/writing-master/SKILL.md")

        self.assertIn("交付包", main)
        package_start = main.index("交付包")
        package = main[package_start:package_start + 1800]
        for artifact in (
            "final.md",
            "sources.yaml",
            "claims.yaml",
            "asset-manifest.yaml",
            "acceptance-report.md",
        ):
            self.assertIn(artifact, package)
        self.assertRegex(package, r"(?:review-report\.yaml|revision-report\.yaml)")
        self.assertRegex(main, r"(?:忽略.{0,30}非阻断|非阻断.{0,30}忽略)")
        self.assertRegex(
            main,
            r"(?s)阻断问题.{0,140}(?:未关闭|未解决|未处理|关闭后|解决后|处理后).{0,220}(?:完成|发布)",
        )

    def test_title_defaults_without_an_extra_waiting_gate(self):
        main = read("skills/writing-master/SKILL.md")
        waiting = section(main, "## 用户等待与继续方式")
        title = section(main, "### Phase 5：标题与 canonical final 验收")
        standard = section(
            read("skills/writing-master/references/mode-selection.md"),
            "### 2. 标准写作（standard）",
        )

        self.assertNotIn("| 标题 |", waiting)
        self.assertIn(
            "只在模式、内容契约、重大方向、阻断问题、明确请求的风格候选决定和发布",
            waiting,
        )
        self.assert_in_order(
            title,
            "标题至少提供自然版、判断版和传播版",
            "默认采用与正文最一致的推荐标题写入 `final.md`",
            "用户主动要求选择或修改时再等待该决定",
        )
        self.assertIn("用户确认：内容契约、核心角度、发布动作", standard)
        self.assertIn("标题随最终稿交付", standard)

    def test_acceptance_precedes_visual_and_format_routes(self):
        main = read("skills/writing-master/SKILL.md")
        acceptance = section(main, "### Phase 5：标题与 canonical final 验收")
        downstream = section(main, "### Phase 6：交付包、视觉、排版与发布")
        routing = read("skills/writing-master/references/baoyu-integration.md")
        production = section(routing, "### Level 3：Production（canonical final 验收后）")
        route_summary = section(routing, "## 路由决策摘要")

        self.assertLess(
            main.index("### Phase 5：标题与 canonical final 验收"),
            main.index("### Phase 6：交付包、视觉、排版与发布"),
        )
        self.assert_in_order(
            acceptance,
            "在视觉、排版、Rewrite 或发布前",
            "`acceptance-report.md` 中完成内容验收",
            "验收通过后，`final.md` 成为本次所选渠道的只读 canonical final",
        )
        self.assert_in_order(
            downstream,
            "图像类视觉闸门",
            "`final.md` 已是已验收的 canonical final",
            "Markdown 格式化和公众号 HTML",
            "不要求 storyboard、`asset-manifest.yaml` 或图像类视觉意图",
        )
        self.assert_in_order(
            production,
            "### Level 3：Production（canonical final 验收后）",
            "`accepted_final`",
            "`acceptance-report.md` 内容明确验收通过",
            "图像类视觉生产约束",
        )
        self.assertIn("Markdown 格式化和 HTML 转换不属于图像类视觉生产", production)
        self.assert_in_order(
            route_summary,
            "内容验收：canonical final",
            "当前渠道必要视觉：Baoyu 视觉 production",
            "canonical final + channel contract：Baoyu 排版 / HTML",
            "渠道完整交付",
        )

    def test_deep_protocol_orders_content_acceptance_before_optional_delivery(self):
        orchestration = read("skills/writing-master/references/agent-orchestration.md")

        self.assert_in_order(
            orchestration,
            "Lead：标题与 canonical final 内容验收",
            "当前渠道合同要求的完整产物",
            "Lead：交付包验收",
        )

    def test_deep_personal_context_is_manifest_only_not_os_isolation(self):
        main = read("skills/writing-master/SKILL.md")
        bridge = read("skills/writing-master/references/personal-context.md")
        orchestration = read("skills/writing-master/references/agent-orchestration.md")

        self.assertIn("标准或深度写作", main)
        self.assertIn("Deep 模式由 Lead", bridge)
        for token in (
            "personal-context-snapshot.json",
            "context-materials/ITEM_ID.md",
            "不得列出 `${WRITING_MASTER_HOME}/personal-context/`",
            "父对话全文",
            "Host 输入构造",
            "不是 OS 级文件访问隔离声明",
        ):
            self.assertIn(token, orchestration)

    def test_deep_mode_role_cards_exist(self):
        cards = [
            "researcher.md",
            "editorial-strategist.md",
            "writer.md",
            "auditor.md",
        ]
        for card in cards:
            self.assertTrue((ROOT / "skills/writing-master/agents" / card).is_file())

    def test_standard_personal_context_uses_only_task_snapshot_and_records_usage(self):
        main = read("skills/writing-master/SKILL.md")
        bridge = read("skills/writing-master/references/personal-context.md")
        phase0 = section(main, "### Phase 0：内容契约、能力预检与素材接收")
        phase1 = section(main, "### Phase 1：事实与素材双轨调研")
        phase2 = section(main, "### Phase 2：角度、读者决策与 Storyboard")
        phase3 = section(main, "### Phase 3：初稿")
        phase6 = section(main, "### Phase 6：交付包、视觉、排版与发布")

        self.assertIn("references/personal-context.md", main)
        self.assert_in_order(
            phase0,
            "内容契约确认后、Phase 1 前",
            "personal-context-snapshot.json",
            "personal_context: unavailable",
        )
        for phase in (phase1, phase2, phase3):
            self.assertIn("Snapshot", phase)
        self.assertIn("不得在调研阶段回读全局个人素材目录", phase1)
        self.assertIn("不得用全局 Profile/Knowledge 覆盖任务内版本", phase2)
        self.assertIn("任务 Snapshot 和任务内材料副本", phase3)
        self.assert_in_order(
            phase6,
            "final.md` 与 `acceptance-report.md` 已存在后",
            "context-usage.json",
            "context verify-run {run_dir}",
        )
        self.assertIn("personal_context: {unavailable | empty | ready}", main)
        self.assertIn("selected_materials: {N}", main)
        self.assertIn("pending_approvals: {N}", main)
        self.assertIn("不得扫描或直接读取 `${WRITING_MASTER_HOME}/personal-context/`", bridge)
        self.assertIn("不对正文作语义性“绝无私密泄露”声明", bridge)

    def test_confirmed_style_learning_only_affects_future_snapshots(self):
        main = read("skills/writing-master/SKILL.md")
        bridge = read("skills/writing-master/references/personal-context.md")

        for token in (
            "writing-master learn propose",
            "writing-master learn decide",
            "Style Profile 只从 accepted observations",
            "当前任务 Snapshot 写入后保持不变",
        ):
            self.assertIn(token, bridge)
        self.assertIn("只有 accepted observation 会进入后续任务的新 Snapshot", main)
        self.assertIn("Runtime 不自动决定", main)

    def test_topic_research_precedes_article_research_and_uses_runtime_validation(self):
        main = read("skills/writing-master/SKILL.md")
        orchestration = read("skills/writing-master/references/agent-orchestration.md")
        phase1 = section(main, "### Phase 1：事实与素材双轨调研")

        self.assertIn("references/research-brief.md", main)
        self.assert_in_order(
            phase1,
            "Topic Research",
            "research-brief-draft.json",
            "writing-master research save",
            "Article Research",
        )
        for token in (
            "phase=topic_research",
            "to_role=researcher",
            "research-brief-draft.json",
            "writing-master research save/verify",
            "Research Brief Evidence 不自动进入文章 claims",
        ):
            self.assertIn(token, orchestration)

    def test_rewrite_reads_real_platform_contracts(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")

        self.assertIn("references/single-target-rewrite.md", rewrite)
        self.assertIn("references/quality-gates.md", rewrite)
        self.assertIn("platforms/wechat.yaml", rewrite)
        self.assertIn("platforms/x-post.yaml", rewrite)
        self.assertIn("platforms/x-thread.yaml", rewrite)
        self.assertIn("机械语言预警", rewrite)
        self.assertNotIn("姐妹们", rewrite)
        self.assertNotIn("别划走", rewrite)

    def test_rewrite_distinguishes_accepted_final_from_standalone_input(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")
        runtime = section(rewrite, "## 运行约定")
        inputs = section(rewrite, "## Phase 0：输入、单目标与任务目录")
        gates = section(
            read("skills/writing-rewrite/references/quality-gates.md"),
            "## 0. 来源与单目标准入门槛",
        )

        self.assertIn(
            "`source_ref` 只能是 `accepted_final` 或 `standalone_input`",
            runtime,
        )
        self.assert_in_order(
            inputs,
            "`accepted_final`",
            "已验收 canonical package",
            "`final.md`",
            "`acceptance-report.md` 必须确认内容验收通过",
            "`standalone_input`",
            "用户直接提供的文件或当前对话中的完整正文",
            "`source.md` 只读",
        )
        self.assertIn("未验收的 `draft-v1.md`、`draft-v2.md` 或 `final.md` 不得进入 Rewrite", inputs)
        self.assertIn("`sources.yaml` 与 `claims.yaml`", inputs)
        self.assertIn("不要求 Writing Master 的验收报告", inputs)
        self.assertIn("`standalone_input` 只限用户直接提供的文件或完整正文", gates)
        self.assertIn("不得改写 canonical source", gates)

    def test_rewrite_p0_has_no_fresh_context_or_multi_agent_path(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")
        runtime = section(rewrite, "## 运行约定")
        channel_rewrite = section(rewrite, "## Phase 3：单渠道改写")

        self.assertIn("P0 默认并始终使用当前 Agent", runtime)
        self.assertIn("深度或多 Agent 改写尚未定义真实渠道角色与 Handoff 合同", runtime)
        self.assertIn("等待用户确认标准改写或取消", runtime)
        self.assertNotIn("fresh-context", rewrite)
        self.assertIn("本次 Rewrite 不读取任何其他渠道正文", channel_rewrite)
        self.assertIn("不把已完成版本作为当前版本的输入", channel_rewrite)

    def test_channel_p0_is_single_target_with_two_entries(self):
        main = read("skills/writing-master/SKILL.md")
        rewrite = read("skills/writing-rewrite/SKILL.md")
        prd = read("docs/proposals/2026-07-29-channel-adaptation-p0-prd.md")

        self.assertIn('\"entry\": \"writing\"', main)
        self.assertIn("每个任务只选择一个 `target_id`", main)
        self.assertIn("一次要求多个渠道", main)
        self.assertIn("只确认本次一个 `target_id`", main)
        self.assertIn("一个 run 只接受一个 `target_id`", rewrite)
        self.assertIn("`target_id` 是标量", rewrite)
        self.assertIn("第二个渠道时新建一次 Rewrite", rewrite)
        self.assertIn("output_filename: final.md", main)
        self.assertIn("`rewrite_output_filename` 只供 Rewrite 使用", main)
        self.assertIn("entry: writing | rewrite", prd)
        self.assertIn("`writing` → `writing-master`", prd)
        self.assertIn("`rewrite` → `writing-rewrite`", prd)
        self.assertNotRegex(prd, r"Intent\s+Selector")
        self.assertNotRegex(prd, r"全.{0,2}生成")

    def test_second_rewrite_reuses_source_analysis_by_hash(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")
        analysis = section(rewrite, "## Phase 2：生成或复用 source analysis")
        delivery = section(rewrite, "## Phase 8：完整交付")

        self.assert_in_order(
            analysis,
            "`source_sha256` 与本次 `source.md` 完全一致",
            "`rewrite-status.json.source_analysis_sha256` 一致",
            "同一分析 hash 写入新 run",
            "分析文件只读",
            "任一 hash 不一致时为当前 source 重新分析",
        )
        self.assertIn("是否复用及其 hash", delivery)
        self.assertIn("voice_basis:", analysis)
        self.assertIn("supporting_artifacts:", analysis)
        self.assertIn("冻结 Voice Snapshot", analysis)
        self.assertIn("短渠道 final 不会丢掉已经完成的研究依据", analysis)
        self.assertIn("不写 `target_id`、渠道结构或渠道输出决定", analysis)

    def test_wechat_x_post_and_x_thread_contracts_are_complete(self):
        expected = {
            "wechat.yaml": ("wechat", "wechat.html", "cover.png"),
            "x-post.yaml": ("x-post", "max_chars: 280", "single_post", "length_validator: manual_x_composer_preview"),
            "x-thread.yaml": ("x-thread", "max_chars_per_post: 280", "thread", "length_validator: manual_x_composer_preview"),
        }

        for filename, tokens in expected.items():
            contract = read(f"skills/writing-rewrite/platforms/{filename}")
            self.assertIn(f"target_id: {tokens[0]}", contract)
            for token in tokens[1:]:
                self.assertIn(token, contract)
            for field in (
                "output_kind:",
                "rewrite_output_filename:",
                "min_chars:",
                "max_chars:",
                "needs_images:",
                "required_derivatives:",
                "rewrite_brief:",
            ):
                self.assertIn(field, contract)
            top_level_keys = [
                line.split(":", 1)[0]
                for line in contract.splitlines()
                if line and not line[0].isspace() and ":" in line
            ]
            self.assertEqual(len(top_level_keys), len(set(top_level_keys)))
            self.assertNotIn("output_filename", top_level_keys)

        platform_dir = ROOT / "skills/writing-rewrite/platforms"
        self.assertEqual(
            {path.name for path in platform_dir.glob("*.yaml")},
            set(expected),
        )

    def test_rewrite_status_and_review_bind_one_target_to_source_hashes(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")
        status = section(rewrite, "## Phase 0：输入、单目标与任务目录")
        review = section(rewrite, "## Phase 4：渠道编辑审查")

        for token in (
            '\"target_id\": \"wechat | x-post | x-thread\"',
            '\"source_ref\": \"accepted_final | standalone_input\"',
            '\"source_sha256\": \"...\"',
            '\"source_analysis_sha256\": null',
            '\"output_sha256\": null',
            '\"review_sha256\": null',
            '\"derivatives_sha256\": {}',
        ):
            self.assertIn(token, status)
        self.assertNotRegex(status, r'\"target' + r's\"')
        for token in (
            '\"target_id\": \"wechat | x-post | x-thread\"',
            '\"source_sha256\": \"...\"',
            '\"source_analysis_sha256\": \"...\"',
            '\"output_sha256\": \"...\"',
            '\"validator\": \"manual_x_composer_preview | not_applicable\"',
            '\"status\": \"pass | unavailable | not_applicable\"',
        ):
            self.assertIn(token, review)

        self.assertIn("实际 composer 预览或用户提供的同文预览证据", rewrite)
        self.assertIn("字符数估算、编辑器字数或模型自行判断都不能替代", rewrite)
        self.assertIn("Thread 每条各一项", review)

        mechanical = section(rewrite, "## Phase 5：机械预警")
        self.assertIn("不比较两个渠道成品之间的相似度", mechanical)
        self.assertNotIn("x-post.md x-thread.md", mechanical)

        delivery = section(rewrite, "## Phase 8：完整交付")
        self.assertIn("source、analysis、output、review 与 derivative hash 全部匹配", delivery)
        self.assertIn("X 渠道长度证据为 `pass`", delivery)

        main_acceptance = section(
            read("skills/writing-master/SKILL.md"),
            "### Phase 5：标题与 canonical final 验收",
        )
        self.assertIn("冻结为 canonical package 的只读支持产物", main_acceptance)

    def test_channel_p0_adds_no_router_adapter_or_third_entry(self):
        skill_dirs = {
            path.name for path in (ROOT / "skills").iterdir() if path.is_dir()
        }
        self.assertEqual(skill_dirs, {"writing-master", "writing-rewrite"})

        runtime = ROOT / "src/writing_master"
        python_files = {
            path.relative_to(runtime).as_posix()
            for path in runtime.rglob("*.py")
        }
        self.assertFalse(any("channel" in path or "adapter" in path for path in python_files))
        self.assertFalse((runtime / "channels").exists())

    def test_voice_selection_is_part_of_the_content_contract_not_a_waiting_gate(self):
        main = read("skills/writing-master/SKILL.md")
        phase0 = section(main, "### Phase 0：内容契约、能力预检与素材接收")
        waiting = section(main, "## 用户等待与继续方式")
        voice = read("skills/writing-master/references/voice-presets.md")

        self.assertIn("`voice_id` 并入内容契约", phase0)
        self.assertIn("默认 `natural-default`", phase0)
        self.assertIn("这不是独立等待点", phase0)
        self.assertIn("Voice 选择属于内容契约，不增加独立等待点", voice)
        self.assertNotIn("| 写作声音 |", waiting)

    def test_rewrite_keeps_the_accepted_voice_without_a_selector(self):
        rewrite = read("skills/writing-rewrite/SKILL.md")

        self.assertIn("Rewrite 不新增、展示或解析 Voice Selector", rewrite)
        self.assertIn("保留源稿已验收的写作声音，不重新选择 Voice", rewrite)

    def test_confirmed_contract_reverts_to_pending_after_material_change(self):
        main = read("skills/writing-master/SKILL.md")

        for field in (
            "主题、受众、渠道、篇幅、结构、正文必含内容、应用深度、Evidence 要求或视觉范围，以及尚未 `ready` 的 Persona/Voice 选择",
            "变更前后差异",
            "保持不变项",
            "受影响阶段",
            "`current_phase` 退回 `contract`、`phases.contract` 退回 `pending`",
            "`persona_snapshot=ready`",
            "`voice_snapshot=ready`",
            "创建新 Writing run",
            "新 run 的 `source_task_id` 记录当前 `task_id`",
            "当前 run 的关联字段和冻结 Snapshot 均不改写",
            "停在“等待契约确认”",
            "未再次确认前不得继续调研、写作、审校、验收或交付",
            "微小措辞",
        ):
            self.assertIn(field, main)

    def test_process_leakage_is_a_blocking_editorial_boundary(self):
        main = read("skills/writing-master/SKILL.md")
        review = read("skills/writing-master/references/three-pass-review.md")
        auditor = read("skills/writing-master/agents/auditor.md")

        for document in (main, review, auditor):
            self.assertIn("prompt/process leakage", document.lower())
            self.assertIn("标题", document)
            self.assertIn("H1/H2/H3", document)
            self.assertIn("高置信", document)
            self.assertIn("blocking", document)
        self.assertIn("未解决的 blocking issue 必须为 0", main)
        for document in (review, auditor):
            self.assertIn("rule_id:", document)
            self.assertIn("line_number:", document)
            self.assertIn("excerpt:", document)


if __name__ == "__main__":
    unittest.main()
