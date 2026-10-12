"""Unit tests for FitEnhancer and normalized power calculations."""

import tempfile
import unittest
from pathlib import Path

from src.fit_enhancer import FitEnhancer, _calc_np


class TestFitEnhancer(unittest.TestCase):
    def test_calc_np(self):
        # Empty power list returns 0
        self.assertEqual(_calc_np([]), 0.0)

        # Constant power NP equals average power
        powers = [200.0] * 100
        self.assertAlmostEqual(_calc_np(powers), 200.0, places=1)

        # Variable power NP is higher than arithmetic average
        var_powers = [100.0, 300.0] * 50  # average 200W
        np_val = _calc_np(var_powers)
        self.assertGreater(np_val, 200.0)

    def test_disabled_enhancement_returns_original_path(self):
        enhancer = FitEnhancer(spoof_device=False)
        with tempfile.NamedTemporaryFile(suffix=".fit") as tmp:
            result = enhancer.enhance(tmp.name)
            self.assertEqual(result, tmp.name)

    def test_cleanup_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        self.assertTrue(Path(tmp_path).exists())
        FitEnhancer.cleanup_file(tmp_path)
        self.assertFalse(Path(tmp_path).exists())


if __name__ == "__main__":
    unittest.main()
