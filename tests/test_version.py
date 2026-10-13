"""Unit tests for versioning and CLI version output."""

import io
import re
import unittest
from unittest.mock import patch

from src import __version__
from src.main import parse_args


class TestVersioning(unittest.TestCase):
    """Test semantic versioning compliance and CLI output."""

    def test_semantic_version_format(self):
        """Version string must strictly adhere to Semantic Versioning (SemVer 2.0.0)."""
        semver_regex = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        self.assertIsNotNone(
            re.match(semver_regex, __version__),
            f"Version '{__version__}' is not valid SemVer 2.0.0",
        )

    def test_cli_version_flag(self):
        """CLI parser must display version information when requested."""
        parser = parse_args()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                parser.parse_args(["--version"])
            self.assertEqual(cm.exception.code, 0)
            self.assertIn(__version__, mock_stdout.getvalue())
            self.assertIn("Myswoosh2Garmin", mock_stdout.getvalue())

    def test_cli_short_version_flag(self):
        """CLI parser must support -v shortcut for version."""
        parser = parse_args()
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                parser.parse_args(["-v"])
            self.assertEqual(cm.exception.code, 0)
            self.assertIn(__version__, mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
