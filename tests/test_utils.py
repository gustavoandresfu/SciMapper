import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import validate_config


class TestUtils(unittest.TestCase):
    def test_valid_config(self):
        cfg = {
            "project_metadata": {"title": "T", "short_name": "S", "temporal_window": [2020, 2024]},
            "search_strategy": {"openalex_email": "a@b.com", "queries": ["q"]},
            "nlp_tuning": {"n_clusters": 5},
        }
        self.assertEqual(validate_config(cfg), [])

    def test_invalid_config(self):
        cfg = {"project_metadata": {}, "search_strategy": {}, "nlp_tuning": {}}
        errs = validate_config(cfg)
        self.assertTrue(len(errs) > 0)


if __name__ == "__main__":
    unittest.main()