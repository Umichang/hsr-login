import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
    def test_default_config_path_uses_appdata_on_windows(self):
        with mock.patch("hsr_login.is_windows", return_value=True), mock.patch.dict(
            os.environ,
            {"APPDATA": r"C:\Users\kai\AppData\Roaming"},
            clear=True,
        ):
            path = hsr_login.default_config_path()

        self.assertEqual(str(path), r"C:\Users\kai\AppData\Roaming/hsr-login/config.json")

    def test_save_config_keeps_hsr_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            hsr_login.save_config(path, "ltuid_v2=123; ltoken_v2=abc")
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["game"], hsr_login.GAME_NAME)
        self.assertEqual(payload["act_id"], hsr_login.ACT_ID)
        self.assertIn("/hkrpg/", payload["event_url"])


class BrowserTests(unittest.TestCase):
    def test_windows_browser_candidates_include_common_commands(self):
        candidates = hsr_login.windows_browser_candidates()

        self.assertIn("chrome.exe", candidates)
        self.assertIn("msedge.exe", candidates)

    def test_preferred_browser_strips_powershell_quotes(self):
        with mock.patch("hsr_login.shutil.which", return_value=r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
            path = hsr_login.find_browser_command('"chrome.exe"')

        self.assertEqual(path, r"C:\Program Files\Google\Chrome\Application\chrome.exe")

    def test_safaridriver_command_strips_powershell_quotes(self):
        with mock.patch("hsr_login.shutil.which", return_value="/usr/bin/safaridriver"):
            path = hsr_login.find_safaridriver_command('"safaridriver"')

        self.assertEqual(path, "/usr/bin/safaridriver")

    def test_webdriver_session_id_accepts_w3c_response(self):
        self.assertEqual(
            hsr_login.webdriver_session_id({"value": {"sessionId": "abc", "capabilities": {}}}),
            "abc",
        )

    def test_webdriver_error_message_reads_value_message(self):
        body = json.dumps({"value": {"error": "session not created", "message": "Allow Remote Automation"}})

        self.assertEqual(
            hsr_login.webdriver_error_message(body),
            "session not created: Allow Remote Automation",
        )


class ParserTests(unittest.TestCase):
    def test_version_is_current(self):
        self.assertEqual(hsr_login.__version__, "0.3.0")

    def test_parser_accepts_installed_command_style(self):
        args = hsr_login.build_parser().parse_args(["login", "--check"])

        self.assertEqual(args.command, "login")
        self.assertTrue(args.check)

    def test_parser_accepts_safari_browser(self):
        args = hsr_login.build_parser().parse_args(["login", "--browser", "safari", "--check"])

        self.assertEqual(args.browser, "safari")
        self.assertTrue(args.check)


if __name__ == "__main__":
    unittest.main()
