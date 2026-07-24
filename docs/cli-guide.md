# CLI 工具使用指南

AI Writing Master 提供独立的命令行工具，可以在不依赖 AI 的情况下进行质量检测和相似度分析。

## 📦 安装

### 方式1: 直接使用（无需 pip）

```bash
# 克隆项目
git clone https://github.com/NoApoNoTary/ai-writing-master.git ~/ai-writing-master

# 添加到 PATH（添加到 ~/.bashrc 或 ~/.zshrc）
export PATH="$HOME/ai-writing-master/bin:$PATH"

# 验证安装
writing-master --version
```

### 方式2: 使用 Python 模块

```bash
cd ~/ai-writing-master
PYTHONPATH=./src python3 -m writing_master --help
```

## 🚀 命令概览

```bash
writing-master --help              # 查看所有命令
writing-master --version           # 查看版本
writing-master home                # 输出状态目录路径
writing-master quality <文件>      # 质量评分
writing-master similarity <文件...> # 相似度检测
```

---

## 📊 quality - 质量评分

对 Markdown 文章进行多维度质量检测。

### 基本用法

```bash
# 简单评分
writing-master quality article.md
# 输出: 72.5
#       ✅ 通过 (阈值: 60)

# 详细报告
writing-master quality article.md --verbose

# JSON 输出（供程序解析）
writing-master quality article.md --json
```

### 评分维度

CLI 工具使用统计方法检测以下维度：

| 维度 | 权重 | 检测内容 | 目标 |
|------|------|----------|------|
| **准确性** | 25% | 提醒人工核对事实 | 默认0.9 |
| **套话检测** | 20% | 14类AI套话黑名单 | 无套话 |
| **句子变化** | 15% | 句长标准差 | ≥15 |
| **段落节奏** | 10% | 段落长度多样性 | 变化丰富 |
| **副词密度** | 15% | 过度修饰检测 | ≤2.0/100字 |
| **词汇丰富度** | 15% | 字符bigram多样性 | ≥0.6 |

**质量门槛**：≥60分

### AI套话黑名单

CLI 工具检测以下套话模式：

```
首先、其次、再者、最后、总之、综上所述、总而言之
此外、另外、与此同时、不仅如此、更重要的是
作为一个、让我们、值得注意的是、需要指出的是
不可否认、毋庸置疑、众所周知、事实上、显而易见
非常重要、至关重要、不言而喻、具有重要意义
意义深远、影响深远、引发了广泛关注
总的来说、综合来看、由此可见、不难发现、通过以上分析
```

### 详细报告示例

```bash
writing-master quality article.md --verbose
```

输出：

```
============================================================
写作质量评分: 85.8/100
============================================================

各维度得分:
  █████████░ 0.90 (权重25%)  accuracy
         需人工核对事实
  █████████░ 0.90 (权重20%)  banned_words
         发现 1 个套话
         示例: 最后
  ███████░░░ 0.73 (权重15%)  sentence_variance
         句长标准差: 14.6（目标 ≥15）
  ████░░░░░░ 0.44 (权重10%)  paragraph_rhythm
         18/32 对连续段落长度相似
  ██████████ 1.00 (权重15%)  adverb_density
         副词密度: 0.07/100字（目标 ≤2.0）
  ██████████ 1.00 (权重15%)  vocabulary_diversity
         字符bigram多样性: 0.827（目标 ≥0.6）

字符数: 1471
综合得分: 85.8/100
✅ 通过质量门槛（≥60分）
```

### JSON 输出示例

```bash
writing-master quality article.md --json
```

输出：

```json
{
  "quality_score": 85.75,
  "dimensions": {
    "accuracy": {
      "score": 0.9,
      "detail": "需人工核对事实"
    },
    "banned_words": {
      "score": 0.9,
      "detail": "发现 1 个套话",
      "found": ["最后"]
    },
    "sentence_variance": {
      "score": 0.7333,
      "detail": "句长标准差: 14.6（目标 ≥15）"
    },
    "paragraph_rhythm": {
      "score": 0.4375,
      "detail": "18/32 对连续段落长度相似"
    },
    "adverb_density": {
      "score": 1.0,
      "detail": "副词密度: 0.07/100字（目标 ≤2.0）"
    },
    "vocabulary_diversity": {
      "score": 1.0,
      "detail": "字符bigram多样性: 0.827（目标 ≥0.6）"
    }
  },
  "weights": {
    "accuracy": 0.25,
    "banned_words": 0.2,
    "sentence_variance": 0.15,
    "paragraph_rhythm": 0.1,
    "adverb_density": 0.15,
    "vocabulary_diversity": 0.15
  },
  "char_count": 1471
}
```

---

## 🔄 similarity - 相似度检测

检测两个或多个文本之间的相似度，用于防洗稿检查。

### 基本用法

```bash
# 比较两个文件
writing-master similarity source.md rewritten.md
# 输出: 最大相似度: 0.4200
#       ✅ 通过 (阈值: 0.6)

# 比较多个文件（计算两两最大相似度）
writing-master similarity source.md v1.md v2.md v3.md

# JSON 输出
writing-master similarity source.md rewritten.md --json
```

### 算法说明

使用**字符 3-gram Jaccard 相似度**：

1. 提取每个文本的字符3-gram集合
2. 计算 Jaccard 相似度：`|A ∩ B| / |A ∪ B|`
3. 返回所有文本对之间的最大相似度

**相似度阈值**：≤0.6

### 判断标准

| 相似度范围 | 判断 | 建议 |
|-----------|------|------|
| > 0.6 | ❌ 不通过 | 过于相似，需要更激进的重构 |
| 0.4-0.6 | ⚠️ 边缘 | 检查是否有明显洗稿痕迹 |
| < 0.4 | ✅ 通过 | 内容级真改写 |

### JSON 输出示例

```bash
writing-master similarity source.md rewritten.md --json
```

输出：

```json
{
  "max_similarity": 0.42,
  "threshold": 0.6,
  "pass": true
}
```

### 高级选项

```bash
# 自定义 n-gram 长度（默认 3）
writing-master similarity a.md b.md -n 4
```

---

## 🏠 home - 状态目录

输出状态目录路径，用于脚本集成。

```bash
writing-master home
# 输出: /home/user/.writing-master
```

### 环境变量

可以通过环境变量自定义状态目录：

```bash
export WRITING_MASTER_HOME=/custom/path
writing-master home
# 输出: /custom/path
```

---

## 🔧 在 Skill 中使用

在 `writing-rewrite` skill 中，AI 会自动检测 CLI 工具是否可用：

```bash
# AI 自动执行以下逻辑
if command -v writing-master &> /dev/null; then
    # CLI 可用，使用 CLI 工具
    writing-master quality xiaohongshu.md --json
    writing-master similarity source.md xiaohongshu.md --json
else
    # CLI 不可用，使用 AI 评估
    # [AI 自行评估质量和相似度]
fi
```

**优势**：

- ✅ **一致性**：CLI 工具使用固定算法，结果可复现
- ✅ **速度**：无需 LLM 推理，秒级完成
- ✅ **独立性**：不依赖 API 额度，可离线使用
- ✅ **可集成**：JSON 输出方便集成到自动化流程

---

## 📝 实战示例

### 场景1：写作后质量检查

```bash
# 写完文章后立即检查
writing-master quality my-article.md --verbose

# 如果分数低于60，查看详细问题
# 根据提示修改文章
# 再次检查直到通过
```

### 场景2：洗稿质量验证

```bash
# 洗稿前：记录原文路径
source="original-article.md"

# 洗稿后：检查质量和相似度
writing-master quality rewritten.md
writing-master similarity $source rewritten.md

# 如果相似度 > 0.6，需要更激进的重构
```

### 场景3：批量检查多篇文章

```bash
#!/bin/bash
for file in articles/*.md; do
    echo "检查: $file"
    score=$(writing-master quality "$file" --json | jq -r '.quality_score')
    if (( $(echo "$score >= 60" | bc -l) )); then
        echo "  ✅ $score/100"
    else
        echo "  ❌ $score/100 (需要修改)"
    fi
done
```

### 场景4：多平台改写相似度矩阵

```bash
# 检查所有平台版本的相似度
writing-master similarity \
    source.md \
    wechat.md \
    xiaohongshu.md \
    douyin.md \
    zhihu.md

# 输出最大相似度，确保所有版本都是独立改写
```

---

## 🐛 故障排除

### 问题1: `command not found: writing-master`

**原因**：CLI 工具未加入 PATH

**解决**：

```bash
# 临时添加
export PATH="$HOME/ai-writing-master/bin:$PATH"

# 永久添加（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export PATH="$HOME/ai-writing-master/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 问题2: `No module named writing_master`

**原因**：Python 无法找到模块

**解决**：

```bash
# 使用绝对路径
cd ~/ai-writing-master
./bin/writing-master --help

# 或设置 PYTHONPATH
export PYTHONPATH="$HOME/ai-writing-master/src:$PYTHONPATH"
```

### 问题3: 评分结果不符合预期

**说明**：CLI 工具使用统计方法，与人工判断可能有差异

**建议**：

- CLI 评分是**参考指标**，不是绝对标准
- 最终质量判断应结合人工审校
- 可以调整写作策略提高各维度得分

---

## 📚 相关文档

- [完整流程说明](workflow-guide.md)
- [洗稿使用手册](rewrite-guide.md)
- [质量评分算法](quality-scoring.md)
- [相似度算法](similarity-algorithm.md)

---

**CLI 工具版本**：1.0.0  
**Python 要求**：≥3.11  
**依赖**：无（标准库即可运行）
