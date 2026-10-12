"""Unit tests for Config loader."""

import os
import unittest
from unittest.mock import patch

from src.config import Config


class TestConfig(unittest.TestCase):
    def test_missing_credentials_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                Config.from_env()

    def test_valid_config(self):
        env_vars = {
            "MYWHOOSH_EMAIL": "test@example.com",
            "MYWHOOSH_PASSWORD": "secretpassword",
            "GARMIN_USERNAME": "garmin_user",
            "GARMIN_PASSWORD": "garmin_pass",
            "SYNC_INTERVAL_MINUTES": "30",
            "SPOOF_GARMIN_DEVICE": "true",
            "DEVICE_PRODUCT_ID": "4024",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            cfg = Config.from_env()
            self.assertEqual(cfg.mywhoosh_email, "test@example.com")
            self.assertEqual(cfg.mywhoosh_password, "secretpassword")
            self.assertEqual(cfg.sync_interval_minutes, 30)
            self.assertTrue(cfg.spoof_garmin_device)
            self.assertEqual(cfg.device_product_id, 4024)


if __name__ == "__main__":
    unittest.main()
