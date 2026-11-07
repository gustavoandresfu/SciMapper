import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.collector import reconstruct_abstract, normalize_title, clean_text


class TestCollectorHelpers(unittest.TestCase):
    def test_reconstruct_abstract(self):
        inv = {"hello": [0], "world": [1]}
        self.assertEqual(reconstruct_abstract(inv), "hello world")

    def test_reconstruct_empty(self):
        self.assertEqual(reconstruct_abstract({}), "")
        self.assertEqual(reconstruct_abstract(None), "")

    def test_normalize_title(self):
        self.assertEqual(normalize_title("Hello, World! 123"), "helloworld123")
        self.assertTrue(len(normalize_title("a" * 200)) <= 80)

    def test_clean_text(self):
        self.assertEqual(clean_text("  a   b \n c "), "a b c")


if __name__ == "__main__":
    unittest.main()