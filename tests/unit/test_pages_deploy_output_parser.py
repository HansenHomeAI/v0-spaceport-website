import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.parse_pages_deploy_output import parse_pages_deploy_output


class ParsePagesDeployOutputTests(unittest.TestCase):
    def test_parses_alias_and_hash(self):
        log = """
✨ Deployment complete! Take a peek over at https://ed19c4e7.v0-spaceport-website-preview2.pages.dev
✨ Deployment alias URL: https://agent-00008778-replace-sfm-c.v0-spaceport-website-preview2.pages.dev
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrangler.log"
            path.write_text(log, encoding="utf-8")

            result = parse_pages_deploy_output(path)

        self.assertEqual(result["hash_url"], "https://ed19c4e7.v0-spaceport-website-preview2.pages.dev")
        self.assertEqual(
            result["alias_url"],
            "https://agent-00008778-replace-sfm-c.v0-spaceport-website-preview2.pages.dev",
        )
        self.assertEqual(result["preview_url"], result["alias_url"])

    def test_falls_back_to_hash_when_alias_is_missing(self):
        log = "✨ Deployment complete! Take a peek over at https://ed19c4e7.v0-spaceport-website-preview2.pages.dev\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrangler.log"
            path.write_text(log, encoding="utf-8")

            result = parse_pages_deploy_output(path)

        self.assertEqual(result["alias_url"], "")
        self.assertEqual(result["preview_url"], "https://ed19c4e7.v0-spaceport-website-preview2.pages.dev")

    def test_raises_when_hash_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrangler.log"
            path.write_text("no deployment URL here\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "deployment hash URL"):
                parse_pages_deploy_output(path)


if __name__ == "__main__":
    unittest.main()
