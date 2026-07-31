import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from writing_master.commands.wechat_timing import main
from writing_master.wechat_timing import (
    TimingValidationError,
    recommend_publish_time,
    validate_wechat_draft_report,
)


class WechatTimingTests(unittest.TestCase):
    def test_fixed_now_is_deterministic_and_uses_generic_fallback(self):
        now = datetime.fromisoformat("2026-07-31T19:00:00+08:00")
        first = recommend_publish_time(now=now)
        second = recommend_publish_time(now="2026-07-31T19:00:00+08:00", timezone="Asia/Shanghai")
        self.assertEqual(first, second)
        self.assertEqual(first["window"], "2026-07-31 20:30–21:00")
        self.assertEqual(first["basis_type"], "generic_heuristic")
        self.assertIn("未提供可用账号历史数据", first["basis_detail"])

    def test_expired_window_rolls_to_next_local_day(self):
        now = datetime.fromisoformat("2026-07-31T22:00:00+08:00")
        result = recommend_publish_time(now=now)
        self.assertTrue(result["window"].startswith("2026-08-01 "))
        self.assertTrue(result["backup_window"].startswith("2026-08-02 "))

    def test_configured_window_is_explicit(self):
        result = recommend_publish_time(
            now=datetime.fromisoformat("2026-07-31T10:00:00+08:00"),
            configured_window="09:00–09:30",
        )
        self.assertEqual(result["basis_type"], "configured_window")
        self.assertEqual(result["window"], "2026-08-01 09:00–09:30")

    def test_report_requires_all_fields(self):
        with self.assertRaises(TimingValidationError):
            validate_wechat_draft_report({"draft_media_id": "MEDIA"})

    def test_cli_recommend_and_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wechat-draft-report.json"
            report = {
                "recommended_publish_time": recommend_publish_time(
                    now=datetime.fromisoformat("2026-07-31T19:00:00+08:00")
                )
            }
            path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(main(["verify", str(path)]), 0)
        self.assertEqual(
            main(
                [
                    "recommend",
                    "--now",
                    "2026-07-31T19:00:00+08:00",
                    "--timezone",
                    "Asia/Shanghai",
                ]
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
