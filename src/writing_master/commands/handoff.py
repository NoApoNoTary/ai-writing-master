"""CLI surface for deterministic deep-mode handoffs."""
from __future__ import annotations

import argparse
import json
import sys

from writing_master import handoff


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="深度模式的可验证角色交接")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    prepare = subparsers.add_parser("prepare", help="创建不可变 Manifest")
    prepare.add_argument("run_dir")
    prepare.add_argument("--to-role", required=True, choices=sorted(handoff.ROLES - {"lead"}))
    prepare.add_argument("--phase", required=True)
    prepare.add_argument("--objective", required=True)
    prepare.add_argument("--decision-to-inform", required=True)
    prepare.add_argument("--input", action="append", required=True, dest="inputs")
    prepare.add_argument("--write", action="append", required=True, dest="write_scope")
    prepare.add_argument("--done-criterion", action="append", required=True, dest="done_criteria")
    prepare.add_argument("--forbidden-input", action="append", default=[])
    prepare.add_argument("--from-role", default="lead", choices=sorted(handoff.ROLES))
    start = subparsers.add_parser("start", help="在派发 Agent 前持久化 agent_ref")
    start.add_argument("run_dir")
    start.add_argument("--agent-ref", required=True)
    recover = subparsers.add_parser("recover-lost", help="为宿主已确认丢失的 Agent 创建重试")
    recover.add_argument("run_dir")
    recover.add_argument("--agent-ref", required=True)
    complete = subparsers.add_parser("complete", help="校验 Result 并推进状态")
    complete.add_argument("run_dir")
    complete.add_argument("--result")
    show = subparsers.add_parser("show", help="显示当前交接和输入新鲜度")
    show.add_argument("run_dir")
    show.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "prepare":
            result = handoff.prepare(
                args.run_dir, to_role=args.to_role, phase=args.phase, objective=args.objective,
                decision_to_inform=args.decision_to_inform, inputs=args.inputs, write_scope=args.write_scope,
                done_criteria=args.done_criteria, from_role=args.from_role,
                forbidden_inputs=args.forbidden_input,
            )
            print(result["attempt_dir"] / "manifest.json")
        elif args.operation == "start":
            result = handoff.mark_running(args.run_dir, args.agent_ref)
            if result["status"] != "running":
                raise handoff.HandoffError(result.get("reason") or "handoff did not enter running state")
            print(result["status"])
        elif args.operation == "recover-lost":
            result = handoff.recover_lost_running(args.run_dir, args.agent_ref)
            print(result["prepared"]["attempt_dir"] / "manifest.json")
        elif args.operation == "complete":
            result = handoff.complete(args.run_dir, args.result)
            print(result["state"]["status"])
        else:
            result = handoff.show(args.run_dir)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else (
                f"{result['handoff']['handoff_id']}: {result['effective_status']}"
            ))
    except handoff.HandoffError as error:
        print(f"handoff: {error}", file=sys.stderr)
        return 1
    return 0
