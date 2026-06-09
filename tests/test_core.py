import json
import tempfile
import unittest
from pathlib import Path

from ai_agent_context_kit.core import BuildOptions, build_context_bundle, normalize_ext, render_handoff, scan_repository


class CoreTests(unittest.TestCase):
    def test_normalize_ext_adds_dot_and_lowercases(self):
        self.assertEqual(normalize_ext("PY"), ".py")

    def test_scan_includes_text_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx"))
            self.assertEqual([file.path for file in result.included], ["app.py"])

    def test_scan_respects_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            (root / "ignored.txt").write_text("skip\n", encoding="utf-8")
            (root / "kept.txt").write_text("keep\n", encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx"))
            included = [file.path for file in result.included]
            self.assertIn("kept.txt", included)
            self.assertNotIn("ignored.txt", included)

    def test_include_ext_filters_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "b.md").write_text("# b\n", encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx", include_exts={".py"}))
            self.assertEqual([file.path for file in result.included], ["a.py"])

    def test_exclude_path_filters_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            (root / "secret.py").write_text("x = 2\n", encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx", exclude_paths=["secret.py"]))
            self.assertEqual([file.path for file in result.included], ["a.py"])

    def test_large_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "large.txt").write_text("x" * 20, encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx", max_file_bytes=5))
            self.assertFalse(result.included)
            self.assertIn("large", result.excluded[0].reason)

    def test_binary_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.bin").write_bytes(b"a\x00b")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx"))
            self.assertFalse(result.included)
            self.assertEqual(result.excluded[0].reason, "binary file")

    def test_secret_file_is_excluded_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("API_" + "KEY=abcd1234\n", encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx"))
            self.assertFalse(result.included)
            self.assertIn("potential secret", result.excluded[0].reason)

    def test_budget_truncates_later_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("aaaa\n", encoding="utf-8")
            (root / "b.txt").write_text("bbbbbbbbbbbbbbbbbbbb\n", encoding="utf-8")
            result = scan_repository(BuildOptions(root=root, output_dir=root / ".aictx", token_budget=2))
            self.assertEqual([file.path for file in result.included], ["a.txt"])
            self.assertTrue(result.truncated_by_budget)

    def test_build_writes_markdown_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# hello\n", encoding="utf-8")
            output = root / "bundle"
            build_result = build_context_bundle(BuildOptions(root=root, output_dir=output, profile="codex"))
            self.assertTrue(build_result.markdown_path.exists())
            self.assertTrue(build_result.manifest_path.exists())
            self.assertIsNotNone(build_result.handoff_path)
            self.assertTrue(build_result.handoff_path.exists())
            manifest = json.loads(build_result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["profile"], "codex")
            self.assertEqual(manifest["outputs"]["handoff"], "context-bundle.handoff.md")
            self.assertEqual(manifest["included_files"][0]["path"], "README.md")

    def test_build_can_disable_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# hello\n", encoding="utf-8")
            output = root / "bundle"
            build_result = build_context_bundle(BuildOptions(root=root, output_dir=output, write_handoff=False))
            self.assertIsNone(build_result.handoff_path)
            self.assertFalse((output / "context-bundle.handoff.md").exists())
            manifest = json.loads(build_result.manifest_path.read_text(encoding="utf-8"))
            self.assertNotIn("handoff", manifest["outputs"])

    def test_render_handoff_contains_agent_prompt_and_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# hello\n", encoding="utf-8")
            (root / "large.txt").write_text("x" * 20, encoding="utf-8")
            options = BuildOptions(root=root, output_dir=root / ".aictx", max_file_bytes=5)
            scan = scan_repository(options)
            handoff = render_handoff(scan, options, "context-bundle.md", "context-bundle.manifest.json")
            self.assertIn("AI Agent Context Handoff", handoff)
            self.assertIn("Copyable Agent Prompt", handoff)
            self.assertIn("Excluded large file", handoff)
            self.assertIn("large.txt", handoff)


if __name__ == "__main__":
    unittest.main()
