#!/usr/bin/env python3
"""写作质量评分工具 - 基于统计特征和模式检测的质量评估。

改编自 wewrite.commands.humanness_score，简化为 AI Writing Master 核心需求。

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
from pathlib import Path


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

    lengths = [len(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    stddev = variance ** 0.5

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
    similar_count = 0
    for i in range(len(paragraphs) - 1):
        if abs(len(paragraphs[i]) - len(paragraphs[i + 1])) <= 30:
            similar_count += 1

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


# ============================================================
# 综合评分
# ============================================================

def score_article(text: str) -> dict:
    """对文章进行综合评分。

    Returns:
        dict: {
            "quality_score": 0-100分（越高越好）,
            "dimensions": {...各维度详情},
            "char_count": 字符数
        }
    """
    # 去除标题
    clean = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE).strip()

    # 五个维度检查
    checks = {
        "accuracy": {"score": 0.9, "detail": "需人工核对事实"},  # 默认给90分，提醒人工核对
        "banned_words": check_banned_words(clean),
        "sentence_variance": check_sentence_variance(clean),
        "paragraph_rhythm": check_paragraph_rhythm(clean),
        "adverb_density": check_adverb_density(clean),
        "vocabulary_diversity": check_vocabulary_diversity(clean),
    }

    # 计算加权平均分
    # accuracy(准确性): 25%, banned_words(观点性): 20%,
    # sentence_variance(可读性): 15%, paragraph_rhythm(可读性): 10%,
    # adverb_density(实用性): 15%, vocabulary_diversity(实用性): 15%
    weights = {
        "accuracy": 0.25,
        "banned_words": 0.20,
        "sentence_variance": 0.15,
        "paragraph_rhythm": 0.10,
        "adverb_density": 0.15,
        "vocabulary_diversity": 0.15,
    }

    total_score = sum(checks[k]["score"] * weights[k] for k in weights.keys())
    quality_score = round(total_score * 100, 2)

    return {
        "quality_score": quality_score,
        "dimensions": checks,
        "weights": weights,
        "char_count": len(clean),
    }


def print_verbose(result: dict):
    """打印详细报告。"""
    score = result["quality_score"]
    print(f"\n{'=' * 60}")
    print(f"写作质量评分: {score:.1f}/100")
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
    print(f"综合得分: {score:.1f}/100")

    if score >= 60:
        print("✅ 通过质量门槛（≥60分）")
    else:
        print("❌ 未达到质量门槛（需≥60分）")


def main(argv=None) -> int:
    """主函数入口。"""
    parser = argparse.ArgumentParser(description="写作质量评分工具")
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
        score = result["quality_score"]
        print(f"{score:.1f}")
        print(f"{'✅ 通过' if score >= 60 else '❌ 不通过'} (阈值: 60)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
