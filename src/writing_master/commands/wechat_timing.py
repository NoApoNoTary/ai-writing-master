"""CLI for deterministic WeChat timing recommendations and report checks."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys

from writing_master.wechat_timing import (
    TimingValidationError,
    read_and_validate_wechat_draft_report,
    recommend_publish_time,
)


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="微信公众号发布时间建议与草稿报告校验")
    commands = parser.add_subparsers(dest="operation", required=True)

    recommend = commands.add_parser("recommend", help="生成确定性发布时间建议")
    recommend.add_argument("--now", help="ISO-8601 当前时间；缺省使用系统时间")
    recommend.add_argument("--timezone", default="Asia/Shanghai")
    recommend.add_argument("--content-type", default="article")
    recommend.add_argument("--timeliness", default="evergreen")
    recommend.add_argument("--length", default="medium", dest="article_length")
    recommend.add_argument("--configured-window")

    verify = commands.add_parser("verify", help="校验 wechat-draft-report.json")
    verify.add_argument("report", metavar="REPORT.json")

    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    try:
        if args.operation == "recommend":
            now = datetime.fromisoformat(args.now) if args.now else None
            _print_json(
                recommend_publish_time(
                    now=now,
                    timezone_name=args.timezone,
                    content_type=args.content_type,
                    timeliness=args.timeliness,
                    article_length=args.article_length,
                    configured_window=args.configured_window,
                )
            )
        else:
            _print_json(read_and_validate_wechat_draft_report(args.report))
    except (TimingValidationError, ValueError) as error:
        print(f"wechat-timing: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
