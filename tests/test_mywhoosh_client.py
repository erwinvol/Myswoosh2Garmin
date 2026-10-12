"""Unit tests for MyWhooshClient response parsing."""

import unittest
from unittest.mock import MagicMock, patch

from src.mywhoosh_client import MyWhooshClient


class TestMyWhooshClient(unittest.TestCase):
    def setUp(self):
        self.client = MyWhooshClient(email="user@test.com", password="pass")
        self.client.access_token = "mock_token"
        self.client.whoosh_id = "whoosh_123"

    def test_extract_activity_items_formats(self):
        # Format 1: Direct list
        data_list = [{"id": 1, "name": "Ride 1"}]
        self.assertEqual(len(self.client._extract_activity_items(data_list)), 1)

        # Format 2: Dict with results
        data_dict = {"data": {"results": [{"id": 2, "name": "Ride 2"}]}}
        self.assertEqual(len(self.client._extract_activity_items(data_dict)), 1)

        # Format 3: Dict with activities
        data_act = {"activities": [{"id": 3, "name": "Ride 3"}]}
        self.assertEqual(len(self.client._extract_activity_items(data_act)), 1)

    def test_normalize_activity(self):
        raw_item = {
            "id": 99,
            "activityFileId": "file_xyz",
            "name": "AlUla Time Trial",
            "startTime": "2026-10-10T14:00:00Z",
            "totalDistanceMeters": 25000,
            "movingTime": 2400,
        }
        normalized = self.client._normalize_activity(raw_item)
        self.assertEqual(normalized["id"], "99")
        self.assertEqual(normalized["activity_file_id"], "file_xyz")
        self.assertEqual(normalized["name"], "AlUla Time Trial")
        self.assertEqual(normalized["date"], "2026-10-10T14:00:00Z")
        self.assertEqual(normalized["distance_m"], 25000)
        self.assertEqual(normalized["duration_s"], 2400)


if __name__ == "__main__":
    unittest.main()
