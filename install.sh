#!/bin/bash

# AI Writing Master 一键安装脚本
# 适用于 Claude Code / Cursor / OpenClaw / Codex

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="AI Writing Master"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${WRITING_MASTER_HOME:-$HOME/.writing-master}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  ${PROJECT_NAME} 安装程序${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检测环境
echo -e "${YELLOW}[1/4] 检测环境...${NC}"

# 检测 AI Agent
DETECTED_AGENTS=()

if [ -d "$HOME/.claude" ]; then
    DETECTED_AGENTS+=("Claude Code")
    CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
fi

if [ -d "$HOME/.cursor" ]; then
    DETECTED_AGENTS+=("Cursor")
    CURSOR_SKILLS_DIR="$HOME/.cursor/skills"
fi

if [ -d "$HOME/.openclaw" ]; then
    DETECTED_AGENTS+=("OpenClaw")
    OPENCLAW_SKILLS_DIR="$HOME/.openclaw/skills"
fi

if [ -d "$HOME/.codex" ]; then
    DETECTED_AGENTS+=("Codex")
    CODEX_SKILLS_DIR="$HOME/.codex/skills"
fi

if [ ${#DETECTED_AGENTS[@]} -eq 0 ]; then
    echo -e "${RED}✗ 未检测到支持的 AI Agent${NC}"
    echo -e "${YELLOW}请先安装 Claude Code、Cursor、OpenClaw 或 Codex${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 检测到: ${DETECTED_AGENTS[*]}${NC}"

# 创建用户状态目录
echo ""
echo -e "${YELLOW}[2/4] 创建用户状态目录...${NC}"

if [ -d "$HOME_DIR" ]; then
    echo -e "${YELLOW}  目录已存在: $HOME_DIR${NC}"
else
    mkdir -p "$HOME_DIR"
    echo -e "${GREEN}✓ 创建目录: $HOME_DIR${NC}"
fi

# 创建子目录
mkdir -p "$HOME_DIR/runs"
mkdir -p "$HOME_DIR/personal_materials/articles"
mkdir -p "$HOME_DIR/personal_materials/experiences"
mkdir -p "$HOME_DIR/personal_materials/topics"
mkdir -p "$HOME_DIR/exemplars"
mkdir -p "$HOME_DIR/themes"
mkdir -p "$HOME_DIR/output"

echo -e "${GREEN}✓ 目录结构创建完成${NC}"

# 链接 skills
echo ""
echo -e "${YELLOW}[3/4] 链接 Skills...${NC}"

link_skills() {
    local skills_dir=$1
    local agent_name=$2

    if [ -z "$skills_dir" ] || [ ! -d "$(dirname "$skills_dir")" ]; then
        return
    fi

    mkdir -p "$skills_dir"

    for skill in "$PROJECT_DIR/skills"/*; do
        if [ -d "$skill" ]; then
            skill_name=$(basename "$skill")
            target="$skills_dir/$skill_name"

            if [ -L "$target" ]; then
                existing_target=$(readlink "$target")
                if [ "$existing_target" = "$skill" ]; then
                    echo -e "${GREEN}  ✓ $agent_name: $skill_name（已链接）${NC}"
                    continue
                fi
                echo -e "${YELLOW}  ⚠ $agent_name: $skill_name 已指向其他位置，保留现有链接${NC}"
                continue
            fi

            if [ -e "$target" ]; then
                echo -e "${YELLOW}  ⚠ $agent_name: $skill_name 已存在，保留现有文件${NC}"
                continue
            fi

            ln -s "$skill" "$target"
            echo -e "${GREEN}  ✓ $agent_name: $skill_name${NC}"
        fi
    done
}

# 为所有检测到的 Agent 链接 skills
if [ -n "$CLAUDE_SKILLS_DIR" ]; then
    link_skills "$CLAUDE_SKILLS_DIR" "Claude Code"
fi

if [ -n "$CURSOR_SKILLS_DIR" ]; then
    link_skills "$CURSOR_SKILLS_DIR" "Cursor"
fi

if [ -n "$OPENCLAW_SKILLS_DIR" ]; then
    link_skills "$OPENCLAW_SKILLS_DIR" "OpenClaw"
fi

if [ -n "$CODEX_SKILLS_DIR" ]; then
    link_skills "$CODEX_SKILLS_DIR" "Codex"
fi

# 安装 CLI（可选）
echo ""
echo -e "${YELLOW}[4/4] 安装 CLI 工具（可选）...${NC}"

if command -v uv >/dev/null 2>&1; then
    echo -e "${BLUE}检测到 uv，使用 uv 安装 CLI...${NC}"
    if uv tool install --editable "$PROJECT_DIR"; then
        echo -e "${GREEN}✓ CLI 安装完成（uv）${NC}"
    else
        echo -e "${YELLOW}  CLI 安装未完成；Skills 链接保持可用${NC}"
    fi
elif command -v pipx >/dev/null 2>&1; then
    echo -e "${BLUE}检测到 pipx，使用 pipx 安装 CLI...${NC}"
    if pipx install --editable "$PROJECT_DIR"; then
        echo -e "${GREEN}✓ CLI 安装完成（pipx）${NC}"
    else
        echo -e "${YELLOW}  CLI 安装未完成；Skills 链接保持可用${NC}"
    fi
else
    echo -e "${YELLOW}  未检测到 uv 或 pipx，跳过 CLI 安装${NC}"
    echo -e "${YELLOW}  Skills 可以独立使用，不需要 CLI${NC}"
fi

# 完成
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ 安装完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📦 已安装的 Skills:${NC}"
echo -e "  • writing-master    - 完整创作流程主入口"
echo -e "  • writing-rewrite   - 平台内容改写"
echo ""
echo -e "${BLUE}📁 用户数据目录:${NC}"
echo -e "  $HOME_DIR"
echo ""
echo -e "${BLUE}🚀 开始使用:${NC}"
echo -e "  1. 打开 Claude Code / Cursor"
echo -e "  2. 对话输入: ${GREEN}写一篇公众号文章${NC}"
echo -e "  3. 或输入: ${GREEN}把这篇文章改写成小红书版本${NC}"
echo ""
echo -e "${BLUE}📖 查看文档:${NC}"
echo -e "  cat $PROJECT_DIR/README.md"
echo ""
