import unittest

from ai_agent_context_kit.budget import estimate_tokens


class BudgetTests(unittest.TestCase):
    def test_empty_text_has_zero_tokens(self):
        self.assertEqual(estimate_tokens(""), 0)

    def test_ascii_text_uses_four_char_heuristic(self):
        self.assertEqual(estimate_tokens("abcdefgh"), 2)

    def test_cjk_text_counts_wide_chars_more_directly(self):
        self.assertEqual(estimate_tokens("你好世界"), 4)


if __name__ == "__main__":
    unittest.main()
