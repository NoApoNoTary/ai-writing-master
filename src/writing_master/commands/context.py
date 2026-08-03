"""CLI surface for Personal Context initialization and profile updates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from writing_master.personal_context import (
    ContextError,
    ContextStore,
    MATERIAL_KINDS,
    SOURCE_KINDS,
    VISIBILITIES,
)


def _print_json(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ContextError("invalid_input", message)


def _read_profile_input(path: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ContextError("invalid_input", f"cannot read profile input: {path}") from error
    except json.JSONDecodeError as error:
        raise ContextError("invalid_json", f"invalid profile JSON: {path}") from error
    if not isinstance(value, dict):
        raise ContextError("invalid_json", f"profile JSON object required: {path}")
    return value


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    json_requested = "--json" in argv
    parser = _Parser(description="管理 Personal Context")
    commands = parser.add_subparsers(dest="operation", required=True)

    init = commands.add_parser("init", help="初始化 Personal Context")
    init.add_argument("--json", action="store_true", help="JSON 格式输出")

    profile = commands.add_parser("profile", help="管理作者 Profile")
    profile_commands = profile.add_subparsers(dest="profile_operation", required=True)
    profile_show = profile_commands.add_parser("show", help="显示作者 Profile")
    profile_show.add_argument("--json", action="store_true", help="JSON 格式输出")
    profile_set = profile_commands.add_parser("set", help="更新作者 Profile")
    profile_set.add_argument("profile", metavar="PROFILE.json", help="Profile 内容 JSON 文件")
    profile_set.add_argument("--expected-revision", type=int, required=True)
    profile_set.add_argument("--json", action="store_true", help="JSON 格式输出")

    material = commands.add_parser("material", help="管理个人素材")
    material_commands = material.add_subparsers(dest="material_operation", required=True)
    material_add = material_commands.add_parser("add", help="受管导入一条素材")
    material_add.add_argument("source", metavar="FILE")
    material_add.add_argument("--kind", required=True, choices=MATERIAL_KINDS)
    material_add.add_argument("--title", required=True)
    material_add.add_argument("--source-kind", required=True, choices=SOURCE_KINDS)
    material_add.add_argument("--source-ref", required=True)
    material_add.add_argument("--visibility", required=True, choices=VISIBILITIES)
    material_add.add_argument("--tag", action="append", default=[])
    material_add.add_argument("--summary", default="")
    material_add.add_argument("--json", action="store_true", help="JSON 格式输出")
    material_list = material_commands.add_parser("list", help="列出素材 metadata")
    material_list.add_argument("--kind", choices=MATERIAL_KINDS)
    material_list.add_argument("--status", choices=("active", "disabled"))
    material_list.add_argument("--json", action="store_true", help="JSON 格式输出")
    material_disable = material_commands.add_parser("disable", help="停用一条素材")
    material_disable.add_argument("item_id")
    material_disable.add_argument("--json", action="store_true", help="JSON 格式输出")
    material_enable = material_commands.add_parser("enable", help="启用一条素材")
    material_enable.add_argument("item_id")
    material_enable.add_argument("--json", action="store_true", help="JSON 格式输出")
    material_visibility = material_commands.add_parser("set-visibility", help="更新素材可见性")
    material_visibility.add_argument("item_id")
    material_visibility.add_argument("visibility", choices=VISIBILITIES)
    material_visibility.add_argument("--expected-revision", type=int, required=True)
    material_visibility.add_argument("--json", action="store_true", help="JSON 格式输出")

    search = commands.add_parser("search", help="检索 active 个人素材")
    search.add_argument("query")
    search.add_argument("--kind", choices=MATERIAL_KINDS)
    search.add_argument("--tag")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--json", action="store_true", help="JSON 格式输出")

    legacy = commands.add_parser("import-legacy", help="显式导入旧素材目录")
    legacy.add_argument("source_dir", metavar="SOURCE_DIR")
    legacy.add_argument("--kind", choices=MATERIAL_KINDS)
    legacy.add_argument("--json", action="store_true", help="JSON 格式输出")

    approve = commands.add_parser("approve", help="记录任务级素材用途批准")
    approve.add_argument("run_dir", metavar="RUN_DIR")
    approve.add_argument("item_id")
    approve.add_argument("--allow", required=True, choices=("background", "paraphrase", "quote"))
    approve.add_argument("--json", action="store_true", help="JSON 格式输出")

    snapshot = commands.add_parser("snapshot", help="创建不可变个人上下文 Snapshot")
    snapshot.add_argument("run_dir", metavar="RUN_DIR")
    snapshot.add_argument("--material", action="append", default=[])
    snapshot.add_argument("--json", action="store_true", help="JSON 格式输出")

    verify = commands.add_parser("verify-run", help="校验任务 Snapshot、usage 与交付引用")
    verify.add_argument("run_dir", metavar="RUN_DIR")
    verify.add_argument("--json", action="store_true", help="JSON 格式输出")

    try:
        args = parser.parse_args(argv)
        store = ContextStore()
        if args.operation == "init":
            result = store.initialize()
        elif args.operation == "profile":
            if args.profile_operation == "show":
                result = store.read_profile()
            else:
                result = store.update_profile(
                    _read_profile_input(args.profile), expected_revision=args.expected_revision
                )
        elif args.operation == "material":
            if args.material_operation == "add":
                result = store.add_material(
                    args.source,
                    kind=args.kind,
                    title=args.title,
                    source_kind=args.source_kind,
                    source_ref=args.source_ref,
                    visibility=args.visibility,
                    tags=args.tag,
                    summary=args.summary,
                )
            elif args.material_operation == "list":
                result = store.list_materials(kind=args.kind, status=args.status)
            elif args.material_operation == "disable":
                result = store.set_material_status(args.item_id, "disabled")
            elif args.material_operation == "enable":
                result = store.set_material_status(args.item_id, "active")
            else:
                result = store.set_material_visibility(
                    args.item_id,
                    args.visibility,
                    expected_revision=args.expected_revision,
                )
        elif args.operation == "search":
            result = store.search_materials(
                args.query,
                kind=args.kind,
                tag=args.tag,
                limit=args.limit,
            )
        elif args.operation == "import-legacy":
            result = store.import_legacy(args.source_dir, kind=args.kind)
        elif args.operation == "snapshot":
            materials = []
            for raw in args.material:
                if raw.count(":") != 1:
                    raise ContextError("invalid_input", "Snapshot material must use ITEM_ID:PURPOSE")
                item_id, purpose = raw.split(":", 1)
                materials.append((item_id, purpose))
            result = store.create_snapshot(args.run_dir, materials=materials)
        elif args.operation == "verify-run":
            result = store.verify_run(args.run_dir)
        else:
            result = store.approve(args.run_dir, args.item_id, allowed_use=args.allow)
    except ContextError as error:
        if json_requested:
            _print_json({"error": {"code": error.code, "message": str(error)}})
        else:
            print(f"context: {error}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(result)
    elif args.operation == "init":
        print("initialized")
    elif args.operation == "profile" and args.profile_operation == "set":
        print(f"updated profile revision {result['revision']}")
    elif args.operation == "material" and args.material_operation == "add":
        print(result["item_id"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
