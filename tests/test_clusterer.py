import unittest
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clusterer import AutoClusterer


class TestClusterer(unittest.TestCase):
    def test_run_small(self):
        config = {
            "project_metadata": {"output_dir": "./output_test_tmp"},
            "nlp_tuning": {"n_clusters": 2, "stop_words": "english"},
        }
        df = pd.DataFrame({
            "title": ["machine learning in health", "deep learning diagnosis", "nlp clinical notes", "medical imaging ai"],
            "abstract": ["a study", "another study", "clinical nlp", "imaging ai"],
            "publication_year": [2022, 2023, 2023, 2024],
        })
        emb = np.random.RandomState(0).randn(4, 8)
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        cl = AutoClusterer(config)
        out_df, topics = cl.run(df, emb)
        self.assertEqual(len(out_df), 4)
        self.assertIn("topic_id", out_df.columns)
        self.assertIn("coord_x", out_df.columns)
        self.assertTrue(len(topics) >= 1)


if __name__ == "__main__":
    unittest.main()