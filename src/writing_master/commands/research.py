"""Direct CLI for saving and verifying task-local Research Briefs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from writing_master.personal_context import ContextError
from writing_master.research_brief import reject_excessive_json_nesting, save_research_brief, verify_research_brief


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ContextError("invalid_input", message)


def _print_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _read_draft(path: str) -> dict:
    draft_path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(draft_path, flags)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", f"missing research draft: {path}") from error
    except (OSError, ValueError) as error:
        raise ContextError("path_escape", f"unsafe research draft: {path}") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ContextError("path_escape", f"research draft must be a regular file: {path}")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = None
            text = handle.read()
        reject_excessive_json_nesting(text)
        value = json.loads(
            text,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except ContextError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise ContextError("invalid_json", f"invalid research draft JSON: {path}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not isinstance(value, dict):
        raise ContextError("invalid_json", "research draft JSON object required")
    return value


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    json_requested = "--json" in argv
    parser = _Parser(description="保存或校验 Context-aware Research Brief")
    commands = parser.add_subparsers(dest="operation", required=True)

    save = commands.add_parser("save", help="校验 draft 并保存 canonical Research Brief")
    save.add_argument("run_dir", metavar="RUN_DIR")
    save.add_argument("draft", metavar="DRAFT.json")
    save.add_argument("--json", action="store_true", help="JSON 格式输出")

    verify = commands.add_parser("verify", help="校验 canonical Research Brief 和当前输入")
    verify.add_argument("run_dir", metavar="RUN_DIR")
    verify.add_argument("--json", action="store_true", help="JSON 格式输出")

    try:
        args = parser.parse_args(argv)
        if args.operation == "save":
            result = save_research_brief(args.run_dir, _read_draft(args.draft))
        else:
            result = verify_research_brief(args.run_dir)
    except ContextError as error:
        if json_requested:
            _print_json({"error": {"code": error.code, "message": str(error)}})
        else:
            print(f"research: {error}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(result)
    elif args.operation == "save":
        print("research-brief.json")
    else:
        print(f"verified {result['task_id']}: {result['candidate_count']} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
