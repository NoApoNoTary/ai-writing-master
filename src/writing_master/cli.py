"""写作大师 CLI 调度器 - 子命令路由。

改编自 wewrite.cli，适配 AI Writing Master 项目结构。
"""
import importlib
import sys
from pathlib import Path

from . import __version__

# 子命令映射：命令名 → (模块路径, 描述)
_COMMANDS = {
    "quality": ("writing_master.commands.quality", "写作质量评分（5维度检测）"),
    "similarity": ("writing_master.commands.similarity", "文本相似度检测（防洗稿）"),
    "home": (None, "输出状态目录路径"),
}


def _get_home() -> Path:
    """获取状态目录路径。"""
    import os
    env_home = os.getenv("WRITING_MASTER_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".writing-master"


def _usage() -> str:
    """生成帮助信息。"""
    home = _get_home()
    lines = [
        f"writing-master {__version__} — AI Writing Master CLI",
        f"状态目录: {home}",
        "",
        "用法: writing-master <命令> [参数…]",
        "",
        "命令:",
    ]
    for name, (_, desc) in _COMMANDS.items():
        lines.append(f"  {name:<16}{desc}")
    lines += [
        "",
        "使用 'writing-master <命令> --help' 查看命令详细参数。",
    ]
    return "\n".join(lines)


def main() -> None:
    """CLI 主入口。"""
    argv = sys.argv[1:]

    # 处理全局选项
    if not argv or argv[0] in {"-h", "--help"}:
        print(_usage())
        return
    if argv[0] in {"-V", "--version"}:
        print(__version__)
        return

    cmd, rest = argv[0], argv[1:]

    # 内置命令: home
    if cmd == "home":
        print(_get_home())
        return

    # 动态加载子命令
    if cmd in _COMMANDS:
        module_name, _ = _COMMANDS[cmd]
        if module_name is None:
            print(f"命令 '{cmd}' 未实现。", file=sys.stderr)
            sys.exit(1)

        try:
            module = importlib.import_module(module_name)
            sys.argv = [f"writing-master {cmd}", *rest]
            module.main()
        except ImportError as e:
            print(f"无法加载命令模块: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # 未知命令
    print(f"未知命令: {cmd}\n", file=sys.stderr)
    print(_usage(), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
