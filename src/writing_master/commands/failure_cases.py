"""CLI for the small failure-case library."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from writing_master.failure_cases import FailureCaseError, list_cases, propose_case, update_case_status, write_snapshot
from writing_master.personal_context import ContextError

class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise FailureCaseError("invalid_input", message)

def _json(value):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    json_requested = "--json" in argv
    parser = _Parser(description="管理失败案例库")
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("propose", help="登记 proposed 案例")
    p.add_argument("case_json", help="JSON object or path to JSON file")
    p.add_argument("--path")
    p.add_argument("--json", action="store_true")
    u = sub.add_parser("status", help="更新案例状态")
    u.add_argument("case_id"); u.add_argument("status", choices=("proposed", "active", "superseded")); u.add_argument("--path"); u.add_argument("--json", action="store_true")
    l = sub.add_parser("list", help="列出案例")
    l.add_argument("--status", choices=("proposed", "active", "superseded")); l.add_argument("--path"); l.add_argument("--json", action="store_true")
    s = sub.add_parser("snapshot", help="生成 run 内案例快照")
    s.add_argument("run_dir"); s.add_argument("--tag", action="append", default=[]); s.add_argument("--limit", type=int, default=5); s.add_argument("--path"); s.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.operation == "propose":
            try:
                raw = Path(args.case_json).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                raw = args.case_json
            case = propose_case(json.loads(raw), args.path)
        elif args.operation == "status":
            case = update_case_status(args.case_id, args.status, args.path)
        elif args.operation == "list":
            case = {"cases": list_cases(args.path, status=args.status)}
        else:
            case = write_snapshot(args.run_dir, tags=args.tag, limit=args.limit, path=args.path)
    except (ContextError, json.JSONDecodeError, TypeError, ValueError) as error:
        if json_requested:
            _json({"error": {"code": getattr(error, "code", "invalid_input"), "message": str(error)}})
        else:
            print(f"failure-cases: {error}", file=sys.stderr)
        return 1
    if args.json:
        _json(case)
    elif args.operation == "snapshot":
        print(case["path"])
    elif args.operation == "list":
        for item in case["cases"]:
            print(f"{item['id']} [{item['status']}] {' '.join(item['tags'])}")
    else:
        print(case["id"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
