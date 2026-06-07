import json
import tempfile
import unittest
from pathlib import Path

from ai_agent_context_kit.cli import main


class CliTests(unittest.TestCase):
    def test_cli_builds_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
            exit_code = main([str(root), "--output-dir", "ctx", "--name", "demo", "--include-ext", "py"])
            self.assertEqual(exit_code, 0)
            self.assertTrue((root / "ctx" / "demo.md").exists())
            manifest = json.loads((root / "ctx" / "demo.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["included_files"][0]["path"], "app.py")

    def test_cli_fail_on_secret_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("TOK" + "EN=abcd1234\n", encoding="utf-8")
            exit_code = main([str(root), "--output-dir", "ctx", "--fail-on-secret"])
            self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
