import json
import tempfile
import unittest
from pathlib import Path

import hsr_login


class CookieTests(unittest.TestCase):
    def test_normalize_cookie_strips_header_and_duplicates(self):
        self.assertEqual(
            hsr_login.normalize_cookie("Cookie: ltuid_v2=123; ltoken_v2=abc; ltuid_v2=456; broken"),
            "ltuid_v2=123; ltoken_v2=abc",
        )

    def test_normalize_cookie_rejects_empty_value(self):
        with self.assertRaises(hsr_login.HsrLoginError):
            hsr_login.normalize_cookie("Cookie: ; broken")

    def test_auth_cookie_detection_accepts_v2_pair(self):
        self.assertTrue(hsr_login.looks_authenticated("ltuid_v2=123; ltoken_v2=abc"))

    def test_cookies_to_header_keeps_hoyolab_cookies(self):
        self.assertEqual(
            hsr_login.cookies_to_header(
                [
                    {"name": "ltuid_v2", "value": "123", "domain": ".hoyolab.com"},
                    {"name": "ltoken_v2", "value": "abc", "domain": "act.hoyolab.com"},
                    {"name": "session", "value": "skip", "domain": "example.com"},
                ]
            ),
            "ltuid_v2=123; ltoken_v2=abc",
        )

    def test_cookie_domain_matches_subdomains(self):
        self.assertTrue(hsr_login.cookie_domain_matches(".act.hoyolab.com"))
        self.assertFalse(hsr_login.cookie_domain_matches("example.com"))


class ConfigTests(unittest.TestCase):
    def test_save_config_keeps_hsr_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            hsr_login.save_config(path, "ltuid_v2=123; ltoken_v2=abc")
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["game"], hsr_login.GAME_NAME)
        self.assertEqual(payload["act_id"], hsr_login.ACT_ID)
        self.assertIn("/hkrpg/", payload["event_url"])


if __name__ == "__main__":
    unittest.main()
