"""Deterministic WeChat draft timing recommendations and report validation."""
from __future__ import annotations

from datetime import datetime, time, timedelta
import json
from pathlib import Path
import re
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "Asia/Shanghai"
REQUIRED_RECOMMENDATION_FIELDS = {
    "window",
    "timezone",
    "reason",
    "basis_type",
    "basis_detail",
    "confidence",
    "backup_window",
}
_WINDOW_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}–\d{2}:\d{2}$"
)
_BASIS_TYPES = {"account_history", "configured_window", "generic_heuristic"}
_CONFIDENCE = {"high", "medium", "low"}


class TimingValidationError(ValueError):
    """Raised when a draft report lacks a complete timing recommendation."""


def _zone(timezone_name: str | None) -> tuple[str, ZoneInfo]:
    name = (timezone_name or DEFAULT_TIMEZONE).strip()
    try:
        return name, ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise TimingValidationError(f"unknown timezone: {name}") from error


def _format_timezone(name: str, zone: ZoneInfo, at: datetime) -> str:
    offset = at.astimezone(zone).utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    suffix = f"UTC{sign}{hours:02d}:{minutes:02d}"
    return f"{name} / {suffix}"


def _as_local(now: datetime | str | None, zone: ZoneInfo) -> datetime:
    value = datetime.fromisoformat(now) if isinstance(now, str) else (now or datetime.now(zone))
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def _parse_clock(value: str) -> tuple[time, time]:
    match = re.fullmatch(r"(\d{2}):(\d{2})\s*[–-]\s*(\d{2}):(\d{2})", value.strip())
    if not match:
        raise TimingValidationError("configured_window must be HH:MM–HH:MM")
    sh, sm, eh, em = (int(item) for item in match.groups())
    try:
        return time(sh, sm), time(eh, em)
    except ValueError as error:
        raise TimingValidationError("configured_window contains an invalid clock time") from error


def _window(day: datetime, start: time, end: time) -> str:
    return f"{day:%Y-%m-%d} {start:%H:%M}–{end:%H:%M}"


def recommend_publish_time(
    *,
    now: datetime | str | None = None,
    timezone_name: str | None = None,
    timezone: str | None = None,
    content_type: str = "article",
    timeliness: str = "evergreen",
    article_length: str | int = "medium",
    configured_window: str | None = None,
) -> dict[str, str]:
    """Return a reproducible recommendation without fetching account history.

    ``now`` is injectable so callers and tests do not depend on wall-clock time.
    Historical analytics are intentionally outside this P0 helper; callers can
    provide a configured window when an account has one.
    """
    name, zone = _zone(timezone_name or timezone)
    local_now = _as_local(now, zone)
    if configured_window:
        start, end = _parse_clock(configured_window)
        basis_type = "configured_window"
        basis_detail = f"使用任务或账号配置窗口 {configured_window}；本次未读取账号历史表现。"
        confidence = "medium"
    elif timeliness.lower() in {"breaking", "hot", "urgent", "news"} or content_type.lower() in {
        "news",
        "hot_topic",
    }:
        start, end = time(20, 30), time(21, 0)
        basis_type = "generic_heuristic"
        basis_detail = "未提供可用账号历史数据，按热点时效和晚间阅读习惯使用通用经验估计。"
        confidence = "low"
    elif str(article_length).lower() in {"short", "brief", "short-form"}:
        start, end = time(12, 0), time(12, 30)
        basis_type = "generic_heuristic"
        basis_detail = "未提供可用账号历史数据，按短内容和午间阅读习惯使用通用经验估计。"
        confidence = "low"
    else:
        start, end = time(20, 30), time(21, 0)
        basis_type = "generic_heuristic"
        basis_detail = "未提供可用账号历史数据，按文章时效、读者习惯和篇幅使用通用经验估计。"
        confidence = "low"

    day = local_now.date()
    candidate = datetime.combine(day, start, tzinfo=zone)
    if candidate <= local_now:
        day += timedelta(days=1)
    recommended = datetime.combine(day, start, tzinfo=zone)

    if start.hour >= 18:
        backup_day = day + timedelta(days=1)
        backup_start, backup_end = time(9, 0), time(9, 30)
    else:
        backup_day = day
        backup_start, backup_end = time(20, 30), time(21, 0)

    if basis_type == "configured_window":
        reason = f"配置窗口与{content_type}内容的既定发布节奏一致，适合在读者活跃时段发布。"
    elif timeliness.lower() in {"breaking", "hot", "urgent", "news"} or content_type.lower() in {
        "news",
        "hot_topic",
    }:
        reason = "热点时效较强，优先安排在晚间完整阅读时段；当前没有账号历史数据。"
    elif str(article_length).lower() in {"short", "brief", "short-form"}:
        reason = "内容较短，午间窗口可快速完成阅读；当前没有账号历史数据。"
    else:
        reason = "文章适合晚间完整阅读；当前没有账号历史数据，因此使用通用经验估计。"

    recommendation = {
        "window": _window(datetime.combine(day, time.min, tzinfo=zone), start, end),
        "timezone": _format_timezone(name, zone, recommended),
        "reason": reason,
        "basis_type": basis_type,
        "basis_detail": basis_detail,
        "confidence": confidence,
        "backup_window": _window(datetime.combine(backup_day, time.min, tzinfo=zone), backup_start, backup_end),
    }
    validate_recommended_publish_time(recommendation)
    return recommendation


def validate_recommended_publish_time(value: object) -> dict[str, str]:
    """Validate and return the required timing object."""
    if not isinstance(value, Mapping):
        raise TimingValidationError("recommended_publish_time must be an object")
    missing = REQUIRED_RECOMMENDATION_FIELDS - set(value)
    if missing:
        raise TimingValidationError(f"recommended_publish_time missing: {', '.join(sorted(missing))}")
    result = {field: value[field] for field in REQUIRED_RECOMMENDATION_FIELDS}
    for field in ("window", "timezone", "reason", "basis_type", "basis_detail", "confidence", "backup_window"):
        if not isinstance(result[field], str) or not result[field].strip():
            raise TimingValidationError(f"recommended_publish_time.{field} must be a non-empty string")
    if not _WINDOW_RE.fullmatch(result["window"]):
        raise TimingValidationError("recommended_publish_time.window has invalid format")
    if not _WINDOW_RE.fullmatch(result["backup_window"]):
        raise TimingValidationError("recommended_publish_time.backup_window has invalid format")
    if " / UTC" not in result["timezone"]:
        raise TimingValidationError("recommended_publish_time.timezone must include UTC offset")
    if result["basis_type"] not in _BASIS_TYPES:
        raise TimingValidationError("recommended_publish_time.basis_type is invalid")
    if result["confidence"] not in _CONFIDENCE:
        raise TimingValidationError("recommended_publish_time.confidence is invalid")
    return result


def validate_wechat_draft_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Reject a completion report that has no complete timing recommendation."""
    if not isinstance(report, Mapping):
        raise TimingValidationError("wechat draft report must be an object")
    recommendation = validate_recommended_publish_time(report.get("recommended_publish_time"))
    return {**dict(report), "recommended_publish_time": recommendation}


def read_and_validate_wechat_draft_report(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TimingValidationError(f"invalid draft report: {report_path}") from error
    return validate_wechat_draft_report(report)


def write_wechat_draft_report(path: str | Path, report: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_wechat_draft_report(report)
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return validated


# Stable aliases for callers that use the shorter completion vocabulary.
recommend_timing = recommend_publish_time
validate_draft_completion = validate_wechat_draft_report
