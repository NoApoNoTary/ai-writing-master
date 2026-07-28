"""CLI surface for confirmed Style Observation learning."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from writing_master.personal_context import ContextError, ContextStore


def _print_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ContextError("invalid_input", message)


def _read_candidate(path: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ContextError("invalid_input", f"cannot read candidate input: {path}") from error
    except json.JSONDecodeError as error:
        raise ContextError("invalid_json", f"invalid candidate JSON: {path}") from error
    if not isinstance(value, dict):
        raise ContextError("invalid_json", f"candidate JSON object required: {path}")
    return value


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    json_requested = "--json" in argv
    parser = _Parser(description="管理确认式 Style Observation 学习")
    commands = parser.add_subparsers(dest="operation", required=True)

    propose = commands.add_parser("propose", help="提交一条风格候选")
    propose.add_argument("candidate", metavar="CANDIDATE.json")
    propose.add_argument("--json", action="store_true", help="JSON 格式输出")

    decide = commands.add_parser("decide", help="确认或拒绝一条候选")
    decide.add_argument("observation_id", metavar="OBSERVATION_ID")
    decision = decide.add_mutually_exclusive_group(required=True)
    decision.add_argument("--accept", dest="decision", action="store_const", const="accepted")
    decision.add_argument("--reject", dest="decision", action="store_const", const="rejected")
    decide.add_argument("--json", action="store_true", help="JSON 格式输出")

    show = commands.add_parser("show", help="显示 Style 和全部 observations")
    show.add_argument("--json", action="store_true", help="JSON 格式输出")

    try:
        args = parser.parse_args(argv)
        store = ContextStore()
        if args.operation == "propose":
            result = store.propose_style_observation(_read_candidate(args.candidate))
        elif args.operation == "decide":
            result = store.decide_style_observation(args.observation_id, decision=args.decision)
        else:
            result = {
                "style": store.read_style(),
                "observations": store.list_style_observations(),
            }
    except ContextError as error:
        if json_requested:
            _print_json({"error": {"code": error.code, "message": str(error)}})
        else:
            print(f"learn: {error}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(result)
    elif args.operation == "propose":
        print(result["observation_id"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
