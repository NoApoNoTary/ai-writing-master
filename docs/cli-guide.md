# CLI 工具指南

AI Writing Master 的 CLI 提供三项确定性辅助能力：机械文本检查、字符相似度和运行目录查询。它们不替代事实研究或编辑审查。

## 安装与运行

### 使用仓库启动脚本

```bash
git clone https://github.com/NoApoNoTary/ai-writing-master.git ~/ai-writing-master
cd ~/ai-writing-master
./bin/writing-master --help
```

`bin/writing-master` 会把仓库的 `src/` 加入 `PYTHONPATH`，因此无需先安装 Python 包。

需要全局命令时，把 `bin` 加入 PATH：

```bash
export PATH="$HOME/ai-writing-master/bin:$PATH"
writing-master --version
```

### 通过安装脚本

```bash
cd ~/ai-writing-master
bash install.sh
```

若本机存在 `uv` 或 `pipx`，安装脚本会执行仓库根目录的可编辑安装；否则 Skills 仍可使用，CLI 可通过 `./bin/writing-master` 运行。

### Python 模块入口

```bash
cd ~/ai-writing-master
PYTHONPATH=./src python3 -m writing_master --help
```

## 命令概览

```bash
writing-master --help
writing-master --version
writing-master quality <file> [--verbose | --json]
writing-master similarity <file> <file> [...] [--json] [-n N]
writing-master home
```

## `quality`：机械文本检查

命令名 `quality` 为兼容既有工作流保留。它计算五项可观察的文本特征，并汇总为 `mechanical_score`：

| 检查项 | 权重 | 当前实现 |
|---|---:|---|
| `banned_words` | 30% | 统计内置套话表的命中数量 |
| `sentence_variance` | 20% | 计算句长标准差 |
| `paragraph_rhythm` | 20% | 检查相邻段落长度是否过于接近 |
| `adverb_density` | 15% | 统计内置常见副词密度 |
| `vocabulary_diversity` | 15% | 计算中文字符 bigram 多样性 |

这五项都是启发式规则。分数高只表示机械预警较少，不表示：

- 事实准确；
- 引用充分；
- 观点原创；
- 论证严密；
- 符合特定作者声音；
- 文本来自人类而非模型。

### 基本用法

```bash
writing-master quality article.md
writing-master quality article.md --verbose
writing-master quality article.md --json
```

普通输出包含分数和机械阈值结果。当前阈值为 `60`，只用于工作流预警。

### JSON 字段

```json
{
  "score_type": "mechanical_style",
  "mechanical_score": 72.5,
  "quality_score": 72.5,
  "dimensions": {
    "banned_words": {"score": 0.8, "detail": "..."},
    "sentence_variance": {"score": 0.7, "detail": "..."},
    "paragraph_rhythm": {"score": 0.6, "detail": "..."},
    "adverb_density": {"score": 1.0, "detail": "..."},
    "vocabulary_diversity": {"score": 0.9, "detail": "..."}
  },
  "weights": {
    "banned_words": 0.3,
    "sentence_variance": 0.2,
    "paragraph_rhythm": 0.2,
    "adverb_density": 0.15,
    "vocabulary_diversity": 0.15
  },
  "char_count": 1200,
  "manual_review_required": [
    "factual_accuracy",
    "claim_support",
    "editorial_judgment",
    "voice_fidelity"
  ]
}
```

`quality_score` 与 `mechanical_score` 当前数值相同，仅为旧调用方保留。新集成应读取 `mechanical_score` 和 `score_type`。

### 套话表

当前套话表定义在 [`src/writing_master/commands/quality.py`](../src/writing_master/commands/quality.py)。它包含“综上所述”“值得注意的是”“具有重要意义”等常见模板表达。

命中并不意味着该词在所有语境中都错误；检查结果用于定位候选句，再由编辑判断是否修改。

### 短文本行为

输入少于完整文章的最低样本要求时，JSON 返回 `status: "insufficient_data"`，
`mechanical_score` 与兼容字段 `quality_score` 为 `null`，并列出 `insufficient_reasons`。
命令行输出 `N/A`，不把短标题、提纲或几句话标记为通过。

## `similarity`：字符表面相似度

### 基本用法

```bash
writing-master similarity source.md rewritten.md
writing-master similarity source.md version-a.md version-b.md
writing-master similarity source.md rewritten.md --json
writing-master similarity source.md rewritten.md -n 4
```

有意义的比较至少需要两个文件。多个文件输入时，命令返回所有文本对中的最大相似度。

### 算法

默认算法是字符 `3-gram` Jaccard：

1. 删除标点和空白，保留字母、数字及中日韩字符；
2. 为每个文本生成字符 n-gram 集合；
3. 计算 `|A ∩ B| / |A ∪ B|`；
4. 多文件场景返回最大值。

### JSON 输出

```json
{
  "max_similarity": 0.42,
  "threshold": 0.6,
  "pass": true
}
```

`0.6` 是当前工作流的固定预警线。它没有考虑语义改写、引用规范、公共事实、版权边界或跨语言翻译，因此只适合回答“字符表面重合是否偏高”。

## `home`：运行数据目录

```bash
writing-master home
```

默认返回当前用户的 `~/.writing-master`。设置环境变量后返回指定路径：

```bash
export WRITING_MASTER_HOME="$HOME/content-system"
writing-master home
```

`home` 只输出路径，不创建任务、不读取状态，也不执行写作流程。

## 在自动化中使用

### 机械检查

```bash
result=$(writing-master quality final.md --json)
score=$(printf '%s' "$result" | jq -r '.mechanical_score')
printf 'mechanical score: %s\n' "$score"
```

脚本门禁后仍应保留独立编辑审查：

```text
机械检查
  → 证据审查
  → 编辑判断
  → 声音审查
  → 验收
```

### 改写重合预警

```bash
writing-master similarity source.md rewritten.md --json \
  | jq '{max_similarity, threshold, pass}'
```

不要根据 `pass` 字段自动声明原创或直接发布。

## 故障排查

### `command not found: writing-master`

```bash
cd ~/ai-writing-master
./bin/writing-master --help
```

确认可运行后再把目录加入 PATH：

```bash
echo 'export PATH="$HOME/ai-writing-master/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### `No module named writing_master`

从仓库根目录调用启动脚本，或显式设置：

```bash
cd ~/ai-writing-master
PYTHONPATH=./src python3 -m writing_master --help
```

### 文件读取错误

命令按 UTF-8 读取输入。先检查路径、文件权限和编码：

```bash
file article.md
test -r article.md && echo readable
```

### 分数与编辑判断不一致

优先相信针对事实、证据、论证和作者声音的具体审校证据。机械分数只用于发现规则能够观察到的问题。

## 相关文件

- [README](../README.md)
- [快速开始](quick-start.md)
- [`quality.py`](../src/writing_master/commands/quality.py)
- [`similarity.py`](../src/writing_master/commands/similarity.py)
