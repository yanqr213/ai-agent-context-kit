import unittest

from ai_agent_context_kit.ignore import build_matcher, parse_ignore_line


class IgnoreTests(unittest.TestCase):
    def test_parse_comment_returns_none(self):
        self.assertIsNone(parse_ignore_line("# comment"))

    def test_default_ignores_node_modules(self):
        matcher = build_matcher("")
        self.assertTrue(matcher.is_ignored("node_modules/pkg/index.js"))

    def test_gitignore_directory_pattern_ignores_children(self):
        matcher = build_matcher("tmp/\n")
        self.assertTrue(matcher.is_ignored("tmp/cache.txt"))

    def test_negated_pattern_reincludes_file(self):
        matcher = build_matcher("*.md\n!README.md\n")
        self.assertFalse(matcher.is_ignored("README.md"))
        self.assertTrue(matcher.is_ignored("notes.md"))

    def test_anchored_pattern_matches_root_only(self):
        matcher = build_matcher("/build.log\n")
        self.assertTrue(matcher.is_ignored("build.log"))
        self.assertFalse(matcher.is_ignored("nested/build.log"))


if __name__ == "__main__":
    unittest.main()
