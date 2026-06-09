import unittest

from ai_agent_context_kit.safety import detect_secret_findings, is_binary_bytes, shannon_entropy


class SafetyTests(unittest.TestCase):
    def test_binary_bytes_detects_null_byte(self):
        self.assertTrue(is_binary_bytes(b"hello\x00world"))

    def test_plain_text_is_not_binary(self):
        self.assertFalse(is_binary_bytes(b"hello\nworld\n"))

    def test_secret_pattern_detects_key_assignment(self):
        findings = detect_secret_findings("API_" + "KEY=abcd1234\n")
        self.assertTrue(findings)

    def test_detects_fine_grained_github_token_shape(self):
        fake_pat = "github_" + "pat_" + ("A" * 44)
        findings = detect_secret_findings(fake_pat)
        self.assertTrue(findings)

    def test_entropy_is_higher_for_varied_value(self):
        self.assertGreater(shannon_entropy("aB3xY9qP0zLmN7rS"), shannon_entropy("aaaaaaaaaaaaaaaa"))


if __name__ == "__main__":
    unittest.main()
