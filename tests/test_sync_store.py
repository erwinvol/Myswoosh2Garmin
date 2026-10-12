"""Unit tests for SyncStore SQLite persistence."""

import tempfile
import unittest
from pathlib import Path

from src.sync_store import SyncStore


class TestSyncStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sync.db"
        self.store = SyncStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_check_synced(self):
        self.assertFalse(self.store.is_synced("act_123"))

        self.store.record_activity(
            mywhoosh_id="act_123",
            file_id="file_abc",
            name="Morning Ride",
            activity_date="2026-10-12T08:00:00Z",
            status="UPLOADED",
            notes="Edge 1040",
        )

        self.assertTrue(self.store.is_synced("act_123"))
        self.assertEqual(self.store.count(), 1)

    def test_conflict_update(self):
        self.store.record_activity(
            mywhoosh_id="act_456",
            file_id="file_def",
            name="Intervals",
            activity_date="2026-10-12T09:00:00Z",
            status="SKIPPED_DUPLICATE",
            notes="Initial duplicate",
        )

        # Update status
        self.store.record_activity(
            mywhoosh_id="act_456",
            file_id="file_def",
            name="Intervals",
            activity_date="2026-10-12T09:00:00Z",
            status="UPLOADED",
            notes="Forced upload",
        )

        recent = self.store.get_recent_synced(limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["garmin_status"], "UPLOADED")


if __name__ == "__main__":
    unittest.main()
