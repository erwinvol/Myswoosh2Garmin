"""Unit tests for garmin_client date parsing and formatting."""

import unittest
from datetime import datetime, timezone
from src.garmin_client import parse_activity_datetime, format_local_datetime


class TestGarminClientDates(unittest.TestCase):
    """Test date parsing and local formatting."""

    def test_parse_iso_string(self):
        dt = parse_activity_datetime("2026-10-12T19:30:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 12)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_parse_numeric_milliseconds(self):
        # 1760297400000 ms = 2025-10-12 19:30:00 UTC
        dt = parse_activity_datetime("1760297400000")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_parse_datetime_instance(self):
        dt_in = datetime(2026, 10, 12, 14, 0, 0, tzinfo=timezone.utc)
        dt_out = parse_activity_datetime(dt_in)
        self.assertEqual(dt_in, dt_out)

    def test_format_local_datetime(self):
        dt_str = "2026-10-12T19:30:00Z"
        formatted = format_local_datetime(dt_str)
        self.assertTrue(len(formatted) > 5)
        # Should not throw exception and should be non-empty
        self.assertIn("2026", formatted)

    def test_format_empty_and_invalid(self):
        self.assertEqual(format_local_datetime(None), "")
        self.assertEqual(format_local_datetime(""), "")
        self.assertEqual(format_local_datetime("not-a-date"), "not-a-date")


if __name__ == "__main__":
    unittest.main()
