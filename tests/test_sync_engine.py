"""Unit tests for SyncEngine orchestration."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from src.config import Config
from src.sync_engine import SyncEngine
from src.sync_store import SyncStore


class TestSyncEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_engine.db"
        self.store = SyncStore(self.db_path)

        self.config = Config(
            mywhoosh_email="test@test.com",
            mywhoosh_password="pass",
            garmin_username=None,
            garmin_password=None,
            garmin_token_dir=Path(self.temp_dir.name),
            data_dir=Path(self.temp_dir.name),
            check_duplicates=False,
            spoof_garmin_device=False,
        )

        self.mock_whoosh = MagicMock()
        self.mock_garmin = MagicMock()
        self.mock_enhancer = MagicMock()

        self.engine = SyncEngine(
            config=self.config,
            mywhoosh=self.mock_whoosh,
            garmin=self.mock_garmin,
            enhancer=self.mock_enhancer,
            store=self.store,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sync_latest_processes_only_single_newest_activity(self):
        # 3 activities returned from MyWhoosh
        self.mock_whoosh.get_activities.return_value = [
            {"id": "act_old", "name": "Old Ride", "date": "2026-01-01T10:00:00Z", "activity_file_id": "f1"},
            {"id": "act_newest", "name": "Latest Ride", "date": "2026-10-12T10:00:00Z", "activity_file_id": "f2"},
            {"id": "act_mid", "name": "Mid Ride", "date": "2026-06-01T10:00:00Z", "activity_file_id": "f3"},
        ]
        self.mock_whoosh.download_activity_fit.return_value = "/tmp/fake.fit"
        self.mock_enhancer.enhance.return_value = "/tmp/fake_enh.fit"
        self.mock_garmin.upload_activity.return_value = {"status": "uploaded"}

        stats = self.engine.run_sync(sync_latest=True)

        # Must have uploaded exactly 1 activity
        self.assertEqual(stats["uploaded"], 1)
        self.assertEqual(stats["total_found"], 1)

        # The uploaded activity must be the newest one
        self.assertTrue(self.store.is_synced("act_newest"))
        self.assertFalse(self.store.is_synced("act_mid"))
        self.assertFalse(self.store.is_synced("act_old"))


if __name__ == "__main__":
    unittest.main()
