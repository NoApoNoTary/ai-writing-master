"""CLI for freezing and verifying task-local Persona Skills."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from writing_master.persona import (
    BACKGROUND_MODES,
    CONTENT_TYPES,
    MODES,
    PersonaError,
    PersonaStore,
)
from writing_master.persona_templates import list_templates


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PersonaError("invalid_input", message)


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    json_requested = "--json" in argv
    parser = _Parser(description="管理任务级人格模板与 Persona Skill")
    commands = parser.add_subparsers(dest="operation", required=True)

    catalog = commands.add_parser("list", help="列出内置人格模板")
    catalog.add_argument("--json", action="store_true")

    snapshot = commands.add_parser("snapshot", help="冻结 Persona Skill 与任务 Brief")
    snapshot.add_argument("run_dir", metavar="RUN_DIR")
    snapshot.add_argument("source", metavar="TEMPLATE_OR_SKILL")
    snapshot.add_argument("brief", metavar="PERSONA_BRIEF.md")
    snapshot.add_argument("--mode", required=True, choices=sorted(MODES))
    snapshot.add_argument("--content-type", required=True, choices=sorted(CONTENT_TYPES))
    snapshot.add_argument("--background", required=True, choices=sorted(BACKGROUND_MODES))
    snapshot.add_argument("--source-version")
    snapshot.add_argument("--json", action="store_true")

    verify = commands.add_parser("verify-run", help="校验任务 Persona Snapshot")
    verify.add_argument("run_dir", metavar="RUN_DIR")
    verify.add_argument("--json", action="store_true")

    try:
        args = parser.parse_args(argv)
        store = PersonaStore()
        if args.operation == "list":
            result = list_templates()
        elif args.operation == "snapshot":
            result = store.create_snapshot(
                args.run_dir,
                args.source,
                Path(args.brief),
                mode=args.mode,
                content_type=args.content_type,
                background_mode=args.background,
                source_version=args.source_version,
            )
        else:
            result = store.verify_run(args.run_dir)
    except PersonaError as error:
        if json_requested:
            _print_json({"error": {"code": error.code, "message": str(error)}})
        else:
            print(f"persona: {error}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(result)
    elif args.operation == "list":
        for template in result["templates"]:
            print(f"{template['id']}\t{template['label']}\t{template['description']}")
    elif args.operation == "snapshot":
        print("persona-brief.md")
    else:
        print(f"verified {result['task_id']}: {result['persona_mode']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
