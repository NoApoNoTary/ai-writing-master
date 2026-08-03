#!/usr/bin/env python3
"""机械文本检查工具 - 基于统计特征和模式检测提供可复现预警。

改编自 wewrite.commands.humanness_score，简化为 AI Writing Master 核心需求。

这个命令只检查可由代码稳定观察的文本特征。事实准确性、原创判断、
论证质量和作者风格由独立编辑审查负责，不在这里伪造为数值评分。

用法：
    writing-master quality article.md                 # 输出分数
    writing-master quality article.md --verbose       # 详细报告
    writing-master quality article.md --json          # JSON输出
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from itertools import pairwise
from pathlib import Path
from statistics import pstdev


# ============================================================
# 评分维度常量
# ============================================================

# AI套话黑名单
BANNED_WORDS = [
    "首先", "其次", "再者", "最后", "总之", "综上所述", "总而言之",
    "此外", "另外", "与此同时", "不仅如此", "更重要的是", "在此基础上",
    "作为一个", "让我们", "值得注意的是", "需要指出的是", "不可否认",
    "毋庸置疑", "众所周知", "事实上", "显而易见", "可以说", "从某种意义上说",
    "非常重要", "至关重要", "不言而喻", "具有重要意义", "发挥着重要作用",
    "意义深远", "影响深远", "引发了广泛关注", "引起了热烈讨论",
    "总的来说", "综合来看", "由此可见", "不难发现", "通过以上分析",
]

# 常见副词
COMMON_ADVERBS = [
    "非常", "十分", "极其", "特别", "相当", "尤其", "格外",
    "更加", "越来越", "逐渐", "不断", "始终", "一直",
]

MIN_CHAR_COUNT = 100
MIN_SENTENCE_COUNT = 5
MIN_PARAGRAPH_COUNT = 3

# 高置信编辑元语言与内部产物名。它们是独立候选，不参与机械分数。
PROCESS_LEAKAGE_RULES = (
    ("PROCESS-META-001", re.compile(r"(?:要不要|是否应该)(?:介绍|写|加入|提及|展开)")),
    ("PROCESS-META-002", re.compile(r"(?:别|不要)写成(?:广告|软文|宣传稿|营销文)")),
    (
        "PROCESS-META-003",
        re.compile(
            r"(?:根据用户(?:的)?要求|用户(?:的)?要求|按(?:用户|你)(?:的)?(?:要求|指示))"
            r"|用户(?:让我|希望)(?:我|我们|本文|文章)?(?:介绍|写|加入|提及|展开|删除|修改)"
        ),
    ),
    (
        "PROCESS-META-004",
        re.compile(r"(?:这部分|这一部分|这里|本文|文章)?(?:是否需要|该不该)(?:介绍|写|加入|提及|展开)"),
    ),
    (
        "PROCESS-PUBLISH-001",
        re.compile(r"(?:发布|发稿|推送)(?:时|前|后)?(?:，|,|：|:)?(?:标题|摘要|正文|封面)(?:要|需要|应|不要|保持)"),
    ),
    (
        "PROCESS-VISUAL-001",
        re.compile(r"(?:这里|此处|这一节|本段)(?:要|需要|应|不要)(?:配|放|加|生成)(?:一张|图片|配图|封面|图表|截图)"),
    ),
    (
        "PROCESS-SOURCE-001",
        re.compile(r"(?:来源|引用|资料)(?:展示)?策略(?:是|为|：|:)"),
    ),
)
INTERNAL_ARTIFACT_RULE = (
    "PROCESS-ARTIFACT-001",
    re.compile(
        r"(?:brief|editorial-brief|channel-contract|asset-manifest|review-report|"
        r"revision-report|acceptance-report|claims|sources|storyboard|draft-v[12]|"
        r"final)\.(?:md|yaml|json)|canonical\s+final|recommended_combo",
        re.IGNORECASE,
    ),
)


# ============================================================
# 辅助函数
# ============================================================

def _split_sentences(text: str) -> list[str]:
    """按中文标点分句。"""
    sentences = re.split(r'[。！？；\n]', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]


def _split_paragraphs(text: str) -> list[str]:
    """分段，排除标题。"""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs
            if p.strip() and not p.strip().startswith('#')]


# ============================================================
# 评分检查项
# ============================================================

def check_banned_words(text: str) -> dict:
    """检查AI套话。"""
    found = [w for w in BANNED_WORDS if w in text]
    score = max(0.0, 1.0 - len(found) * 0.1)
    return {
        "score": round(score, 4),
        "detail": f"发现 {len(found)} 个套话" if found else "无套话",
        "found": found[:5] if found else []
    }


def check_sentence_variance(text: str) -> dict:
    """检查句子长度变化。"""
    sentences = _split_sentences(text)
    if len(sentences) < 5:
        return {"score": 0.5, "detail": "句子数量太少"}

    stddev = pstdev(map(len, sentences))

    # 标准差越大越好（说明句子长度有变化）
    score = min(1.0, stddev / 20.0)
    return {
        "score": round(score, 4),
        "detail": f"句长标准差: {stddev:.1f}（目标 ≥15）"
    }


def check_paragraph_rhythm(text: str) -> dict:
    """检查段落节奏变化。"""
    paragraphs = _split_paragraphs(text)
    if len(paragraphs) < 3:
        return {"score": 0.5, "detail": "段落数量太少"}

    # 检查连续段落长度是否过于相似
    similar_count = sum(
        abs(len(current) - len(next_paragraph)) <= 30
        for current, next_paragraph in pairwise(paragraphs)
    )

    ratio = similar_count / (len(paragraphs) - 1)
    score = 1.0 - ratio
    return {
        "score": round(score, 4),
        "detail": f"{similar_count}/{len(paragraphs)-1} 对连续段落长度相似"
    }


def check_adverb_density(text: str) -> dict:
    """检查副词密度。"""
    char_count = len(text)
    if char_count < 50:
        return {"score": 0.5, "detail": "文本太短"}

    total_adverbs = sum(text.count(adv) for adv in COMMON_ADVERBS)
    density = total_adverbs / char_count * 100

    # 密度越低越好
    score = 1.0 if density <= 2.0 else max(0.0, 1.0 - (density - 2.0) * 0.2)
    return {
        "score": round(score, 4),
        "detail": f"副词密度: {density:.2f}/100字（目标 ≤2.0）"
    }


def check_vocabulary_diversity(text: str) -> dict:
    """检查词汇丰富度（简化版：字符bigram多样性）。"""
    cjk_chars = re.findall(r'[一-鿿]', text)
    if len(cjk_chars) < 20:
        return {"score": 0.5, "detail": "中文字符太少"}

    bigrams = [cjk_chars[i] + cjk_chars[i + 1]
               for i in range(len(cjk_chars) - 1)]
    ttr = len(set(bigrams)) / len(bigrams) if bigrams else 0

    score = min(1.0, ttr / 0.6)
    return {
        "score": round(score, 4),
        "detail": f"字符bigram多样性: {ttr:.3f}（目标 ≥0.6）"
    }


def find_process_leakage(text: str) -> list[dict]:
    """返回可定位的过程泄漏候选；标题和正文使用同一套检查。"""
    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        original = line.strip()
        if not original:
            continue
        for rule_id, pattern in PROCESS_LEAKAGE_RULES:
            match = pattern.search(original)
            if match:
                findings.append({
                    "rule_id": rule_id,
                    "severity": "blocking",
                    "line_number": line_number,
                    "original_text": _containing_sentence(original, match.start(), match.end()),
                    "kind": "prompt_process_leakage",
                })
        artifact_match = INTERNAL_ARTIFACT_RULE[1].search(original)
        if artifact_match:
            findings.append({
                "rule_id": INTERNAL_ARTIFACT_RULE[0],
                "severity": "blocking",
                "line_number": line_number,
                "original_text": _containing_sentence(original, artifact_match.start(), artifact_match.end()),
                "kind": "internal_artifact_name",
            })
    return findings


def _containing_sentence(line: str, match_start: int, match_end: int) -> str:
    """Return the sentence containing one match while retaining Markdown heading context."""
    boundaries = "。！？；!?;"
    start = max((line.rfind(mark, 0, match_start) for mark in boundaries), default=-1) + 1
    ends = [line.find(mark, match_end) for mark in boundaries]
    ends = [position for position in ends if position >= 0]
    end = min(ends) + 1 if ends else len(line)
    sentence = line[start:end].strip()
    if start == 0:
        sentence = re.sub(r"^#{1,6}\s+", "", sentence)
    return sentence


# ============================================================
# 综合评分
# ============================================================

def score_article(text: str) -> dict:
    """对文章进行机械文本检查。

    Returns:
        dict: {
            "mechanical_score": 0-100分（越高表示机械预警越少）,
            "quality_score": mechanical_score 的兼容字段,
            "dimensions": {...各维度详情},
            "char_count": 字符数,
            "findings": 独立的过程泄漏候选
        }
    """
    # 标题只从机械统计中排除；过程泄漏检查必须包含标题。
    findings = find_process_leakage(text)
    # 去除标题
    clean = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE).strip()
    sentences = _split_sentences(clean)
    paragraphs = _split_paragraphs(clean)
    cjk_char_count = len(re.findall(r'[一-鿿]', clean))
    input_stats = {
        "char_count": len(clean),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "cjk_char_count": cjk_char_count,
    }
    insufficient_reasons = []
    if len(clean) < MIN_CHAR_COUNT:
        insufficient_reasons.append(f"char_count_below_{MIN_CHAR_COUNT}")
    if len(sentences) < MIN_SENTENCE_COUNT:
        insufficient_reasons.append(f"sentence_count_below_{MIN_SENTENCE_COUNT}")
    if len(paragraphs) < MIN_PARAGRAPH_COUNT:
        insufficient_reasons.append(f"paragraph_count_below_{MIN_PARAGRAPH_COUNT}")

    # 只保留代码能够实际计算的维度。
    checks = {
        "banned_words": check_banned_words(clean),
        "sentence_variance": check_sentence_variance(clean),
        "paragraph_rhythm": check_paragraph_rhythm(clean),
        "adverb_density": check_adverb_density(clean),
        "vocabulary_diversity": check_vocabulary_diversity(clean),
    }

    # 计算机械特征加权平均分。权重不代表编辑价值或内容质量。
    weights = {
        "banned_words": 0.30,
        "sentence_variance": 0.20,
        "paragraph_rhythm": 0.20,
        "adverb_density": 0.15,
        "vocabulary_diversity": 0.15,
    }

    total_score = sum(checks[k]["score"] * weights[k] for k in weights.keys())
    mechanical_score = (
        round(total_score * 100, 2)
        if not insufficient_reasons
        else None
    )

    return {
        "score_type": "mechanical_style",
        "status": "scored" if mechanical_score is not None else "insufficient_data",
        "sufficient_data": mechanical_score is not None,
        "mechanical_score": mechanical_score,
        # 兼容 writing-rewrite 和现有调用方；新代码应读取 mechanical_score。
        "quality_score": mechanical_score,
        "dimensions": checks,
        "weights": weights,
        "char_count": len(clean),
        "input_stats": input_stats,
        "insufficient_reasons": insufficient_reasons,
        "findings": findings,
        "manual_review_required": [
            "factual_accuracy",
            "claim_support",
            "editorial_judgment",
            "voice_fidelity",
        ],
    }


def print_verbose(result: dict):
    """打印详细报告。"""
    score = result["mechanical_score"]
    print(f"\n{'=' * 60}")
    if score is None:
        print("机械文本检查: 样本不足")
    else:
        print(f"机械文本检查: {score:.1f}/100")
    print(f"{'=' * 60}\n")

    dims = result["dimensions"]
    weights = result["weights"]

    print("各维度得分:")
    for name, data in dims.items():
        weight = weights.get(name, 0)
        s = data["score"]
        bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))
        print(f"  {bar} {s:.2f} (权重{weight:.0%})  {name}")
        print(f"         {data['detail']}")
        if 'found' in data and data['found']:
            print(f"         示例: {', '.join(data['found'])}")

    print(f"\n字符数: {result['char_count']}")
    if score is None:
        print("当前输入不足以形成完整文章的机械基线")
        print("原因: " + ", ".join(result["insufficient_reasons"]))
    else:
        print(f"机械检查得分: {score:.1f}/100")
    print("编辑审查仍需覆盖: 事实、证据、论证、原创判断与作者风格")

    if result["findings"]:
        print("\n过程泄漏候选（不计入机械检查得分，需人工复核）:")
        for finding in result["findings"]:
            print(
                f"  [{finding['rule_id']}] 第 {finding['line_number']} 行: "
                f"{finding['original_text']}"
            )

    if score is None:
        print("⚠️ 请提供更完整的正文后再比较机械检查结果")
    elif score >= 60:
        print("✅ 通过机械检查门槛（≥60分）")
    else:
        print("❌ 机械检查发现较多预警（门槛: 60分）")


def main(argv=None) -> int:
    """主函数入口。"""
    parser = argparse.ArgumentParser(description="机械文本检查工具")
    parser.add_argument("input", help="Markdown 文章文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细报告")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args(argv)

    text = Path(args.input).read_text(encoding="utf-8")
    result = score_article(text)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.verbose:
        print_verbose(result)
    else:
        score = result["mechanical_score"]
        if score is None:
            print("N/A")
            print("⚠️ 样本不足，暂时没有机械检查基线")
        else:
            print(f"{score:.1f}")
            print(f"{'✅ 通过机械检查' if score >= 60 else '❌ 机械预警较多'} (阈值: 60)")
        if result["findings"]:
            print(f"⚠️ 发现 {len(result['findings'])} 条过程泄漏候选，需人工复核")

    return 0


if __name__ == "__main__":
    sys.exit(main())
