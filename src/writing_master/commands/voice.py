"""CLI surface for Voice Preset listing and task snapshots."""
from __future__ import annotations

import argparse
import json
import sys

from writing_master.voice_presets import VoiceError, VoicePresetStore


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise VoiceError("invalid_input", message)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    json_requested = "--json" in argv
    parser = _Parser(description="管理任务级写作声音")
    commands = parser.add_subparsers(dest="operation", required=True)

    listing = commands.add_parser("list", help="列出可用 Voice Preset")
    listing.add_argument("--json", action="store_true")

    snapshot = commands.add_parser("snapshot", help="创建或确认任务 Voice Snapshot")
    snapshot.add_argument("run_dir", metavar="RUN_DIR")
    snapshot.add_argument("voice", nargs="?", help="序号、稳定 ID 或显示名称")
    snapshot.add_argument(
        "--source",
        choices=("default", "request", "content-contract"),
        help="选择来源；省略时按是否显式给出 Voice 推断",
    )
    snapshot.add_argument("--json", action="store_true")

    verify = commands.add_parser("verify-run", help="校验任务 Voice Snapshot 与状态")
    verify.add_argument("run_dir", metavar="RUN_DIR")
    verify.add_argument("--json", action="store_true")

    try:
        args = parser.parse_args(argv)
        store = VoicePresetStore()
        if args.operation == "list":
            result = store.list_profiles()
        elif args.operation == "snapshot":
            source = args.source.replace("-", "_") if args.source else None
            result = store.create_snapshot(args.run_dir, args.voice, selection_source=source)
        else:
            result = store.verify_run(args.run_dir)
    except VoiceError as error:
        payload = {"error": {"code": error.code, "message": str(error)}}
        if error.available is not None:
            payload["error"]["available"] = error.available
        if json_requested:
            _print_json(payload)
        else:
            print(f"voice: {error}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(result)
    elif args.operation == "list":
        for profile in result["profiles"]:
            suffix = "（默认）" if profile["default"] else ""
            print(f"{profile['number']}. {profile['label']} [{profile['id']}] v{profile['version']}{suffix}")
            print(f"   {profile['description']}")
    elif args.operation == "snapshot" and result.get("voice_snapshot") == "unavailable":
        print("natural-default (voice snapshot unavailable)")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
