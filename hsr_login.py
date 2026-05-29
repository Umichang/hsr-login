#!/usr/bin/env python3
"""Claim HoYoLAB daily check-in rewards for Honkai: Star Rail."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import secrets
import shutil
import socket
import stat
import struct
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


__version__ = "0.4.0"
GAME_NAME = "崩壊：スターレイル"
ACT_ID = "e202303301540311"
DEFAULT_API_LANGUAGE = "en-us"
LEGACY_API_LANGUAGE = "ja-jp"
UI_JAPANESE = "ja"
UI_ENGLISH = "en"
GAME_NAMES = {
    UI_JAPANESE: GAME_NAME,
    UI_ENGLISH: "Honkai: Star Rail",
}
API_LANGUAGE_BY_UI = {
    UI_JAPANESE: "ja-jp",
    UI_ENGLISH: DEFAULT_API_LANGUAGE,
}
ACCEPT_LANGUAGE_BY_UI = {
    UI_JAPANESE: "ja,en-US;q=0.9,en;q=0.8",
    UI_ENGLISH: "en-US,en;q=0.9",
}
LANG = LEGACY_API_LANGUAGE
EVENT_BASE_URL = "https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html"
EVENT_URL = (
    f"{EVENT_BASE_URL}?act_id={ACT_ID}&bbs_auth_required=true"
    f"&bbs_presentation_style=fullscreen&lang={LEGACY_API_LANGUAGE}"
)
API_BASE_URL = "https://sg-public-api.hoyolab.com/event/luna/os"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
AUTH_COOKIE_NAMES = {
    "account_id",
    "account_id_v2",
    "cookie_token",
    "cookie_token_v2",
    "ltoken",
    "ltoken_v2",
    "ltuid",
    "ltuid_v2",
}
HOYOLAB_COOKIE_DOMAINS = (
    "hoyolab.com",
    "hoyoverse.com",
)
DEFAULT_BROWSER_TIMEOUT = 180
BROWSER_AUTO = "auto"
BROWSER_CHROMIUM = "chromium"
BROWSER_SAFARI = "safari"
BROWSER_CHOICES = (BROWSER_AUTO, BROWSER_CHROMIUM, BROWSER_SAFARI)


class HsrLoginError(RuntimeError):
    """A recoverable CLI error."""


@dataclass(frozen=True)
class ApiResult:
    retcode: int
    message: str
    data: dict[str, Any]


MESSAGES = {
    UI_JAPANESE: {
        "already_claimed": "{game}: 本日はすでに受け取り済みです。",
        "auto_cookie_failed": "自動取得に失敗しました: {error}",
        "auth_cookies_missing": "認証 Cookie がそろいませんでした。検出した認証系 Cookie: {names}",
        "browser_cookie_list_missing": "ブラウザーから Cookie 一覧を取得できません。",
        "browser_not_found": "ブラウザーが見つかりません: {browser}",
        "browser_opened": "ブラウザーを開きました。HoYoLAB にログインすると Cookie を自動保存します。",
        "captcha_failed": "HoYoLAB の CAPTCHA / リスク判定で自動受け取りに失敗しました。ブラウザーで手動確認してください。",
        "claim_help": "本日のログインボーナスを受け取ります。",
        "claim_failed": "受け取りに失敗しました: retcode={retcode} message={message}",
        "claimed": "{game}: ログインボーナスを受け取りました。",
        "claimed_reward": "{game}: ログインボーナスを受け取りました ({reward})。",
        "chromium_not_found": (
            "Chrome / Chromium 系ブラウザーが見つかりません。"
            "`--manual` で手動入力するか、`--browser-command` で実行ファイルを指定してください。"
        ),
        "config_help": "Cookie を保存する設定ファイルパス。既定値: %(default)s",
        "config_json_failed": "設定ファイルを JSON として読めません: {path}",
        "config_missing": "ログイン情報が未保存です。先に `hsr-login login` を実行してください。",
        "cookie_empty": "Cookie が空です。HoYoLAB の Cookie ヘッダーを貼り付けてください。",
        "cookie_prompt": "HoYoLAB の Cookie ヘッダーを貼り付けてください: ",
        "debug_port_help": "DevTools / WebDriver 用ポート。通常は自動割り当てします。",
        "devtools_command_failed": "DevTools コマンドに失敗しました: {error}",
        "devtools_connect_failed": "{service} に接続できません: {error}",
        "devtools_service": "ブラウザーの DevTools",
        "devtools_ws_failed": "DevTools WebSocket の接続に失敗しました。",
        "devtools_ws_missing": "DevTools の WebSocket URL を取得できません。",
        "error_prefix": "エラー: {error}",
        "fallback_manual": "手動入力に切り替えます。",
        "first_bind": "HoYoLAB 側で初回連携が必要です。ブラウザーで一度手動チェックインしてください。",
        "game_label": "ゲーム: {game}",
        "hoyolab_connect_failed": "HoYoLAB API に接続できません: {reason}",
        "hoyolab_http_failed": "HoYoLAB API が HTTP {code} を返しました: {body}",
        "hoyolab_json_failed": "HoYoLAB API の応答を JSON として読めません: {body}",
        "hoyolab_cookie_missing": "HoYoLAB の Cookie を検出できませんでした。",
        "interrupted": "\n中断しました。",
        "login_browser_help": "自動取得に使うブラウザー。auto は Chromium 系を優先し、macOS では Safari も候補にします。既定値: %(default)s",
        "login_browser_command_help": "自動取得に使う Chrome / Chromium 系ブラウザーの実行ファイルパスまたはコマンド名。",
        "login_check_help": "保存後にログイン状態を確認します。",
        "login_close_browser_help": "Cookie 取得後に自動取得用ブラウザーを閉じます。",
        "login_cookie_file_help": "Cookie ヘッダーを書いたテキストファイルを読み込みます。",
        "login_cookie_help": "Cookie ヘッダーを直接渡します。シェル履歴に残る点に注意してください。",
        "login_help": "HoYoLAB Cookie を保存します。",
        "login_manual_help": "ブラウザーから自動取得せず、Cookie ヘッダーを手入力します。",
        "login_no_open_help": "ブラウザーを自動で開きません。手入力時に使います。",
        "login_opening": "{game} のチェックインページを開きます:",
        "login_profile_dir_help": "自動取得用ブラウザープロファイルの保存先。既定では設定ファイル横の browser-profile を使います。",
        "login_safaridriver_help": "Safari 自動取得に使う safaridriver の実行ファイルパスまたはコマンド名。",
        "login_timeout_help": "ブラウザーから Cookie を自動取得するまで待つ秒数。既定値: %(default)s",
        "logout_deleted": "ログイン情報を削除しました: {path}",
        "logout_help": "保存済み Cookie を削除します。",
        "logout_missing": "ログイン情報はありません: {path}",
        "manual_cookie_help": """
HoYoLAB にログインした状態で、ブラウザーの開発者ツールから Cookie ヘッダーを取得してください。
対象ページは「{game}」のチェックインページです。原神やゼンレスゾーンゼロのページではありません。

例:
  1. 開発者ツールの Network タブを開く
  2. ページを再読み込みする
  3. hoyolab.com / act.hoyolab.com / sg-public-api.hoyolab.com へのリクエストを選ぶ
  4. Request Headers の Cookie: 以降を貼り付ける
""",
        "no_auth_cookie_warning": (
            "警告: ltoken_v2/ltuid_v2 などの認証 Cookie が見つかりません。"
            "保存は続行しますが、チェックイン時にログインエラーになる可能性があります。"
        ),
        "none": "なし",
        "parser_description": "{game}の HoYoLAB Web版デイリーログインボーナスを受け取ります。",
        "safari_automation_hint": (
            "Safari 自動取得を使うには、Safari の開発メニューで"
            "「リモートオートメーションを許可」を有効にするか、"
            "`safaridriver --enable` を実行してください。"
        ),
        "safari_cookie_list_missing": "Safari から Cookie 一覧を取得できません。",
        "safari_json_failed": "Safari WebDriver の応答を JSON として読めません: {body}",
        "safari_not_macos": "Safari 自動取得は macOS でのみ利用できます。",
        "safari_opened": "Safari の自動化ウィンドウを開きます。HoYoLAB にログインすると Cookie を自動保存します。",
        "safari_profile_dir_unsupported": "Safari 自動取得では `--profile-dir` は使えません。Safari WebDriver の隔離セッションを使います。",
        "safari_response_invalid": "Safari WebDriver の応答形式が不正です。",
        "safari_session_id_missing": "Safari WebDriver の session ID を取得できません。",
        "safari_session_start_failed": "Safari WebDriver セッションを開始できません: {error} {hint}",
        "safaridriver_launch_failed": "safaridriver を起動できません: {error}",
        "safaridriver_not_found": "safaridriver が見つかりません: {command}",
        "safaridriver_required": "Safari 自動取得には macOS の safaridriver が必要です。`--manual` で手動入力するか、Chromium 系ブラウザーを使ってください。",
        "saved_login": "ログイン情報を保存しました: {path}",
        "status_check_help": "本日の受け取り状態を確認します。",
        "status_claim_state": "本日の受け取り: {state}",
        "status_failed": "状態確認に失敗しました: retcode={retcode} message={message}",
        "status_json_help": "HoYoLAB API の状態応答を JSON で表示します。",
        "status_today": "今日: {today}",
        "status_total": "今月のチェックイン日数: {total}",
        "timeout_seconds": "タイムアウト: {seconds} 秒",
        "unsupported_ws_url": "未対応の DevTools WebSocket URL です: {url}",
        "webdriver_command_failed": "Safari WebDriver コマンドに失敗しました: {message}",
        "webdriver_connect_failed": "Safari WebDriver に接続できません: {error}",
        "websocket_closed": "DevTools WebSocket が切断されました。",
        "websocket_read_failed": "DevTools WebSocket からの読み込みに失敗しました。",
    },
    UI_ENGLISH: {
        "already_claimed": "{game}: Today's reward has already been claimed.",
        "auto_cookie_failed": "Automatic Cookie capture failed: {error}",
        "auth_cookies_missing": "Required authentication Cookies were not complete. Detected auth Cookies: {names}",
        "browser_cookie_list_missing": "Could not read the Cookie list from the browser.",
        "browser_not_found": "Browser not found: {browser}",
        "browser_opened": "Opened the browser. Log in to HoYoLAB and the Cookie will be saved automatically.",
        "captcha_failed": "HoYoLAB blocked the automatic claim with CAPTCHA / risk verification. Please confirm manually in the browser.",
        "claim_help": "Claim today's login reward.",
        "claim_failed": "Failed to claim reward: retcode={retcode} message={message}",
        "claimed": "{game}: Login reward claimed.",
        "claimed_reward": "{game}: Login reward claimed ({reward}).",
        "chromium_not_found": (
            "Chrome / Chromium browser was not found. "
            "Use `--manual` to enter the Cookie manually, or pass the executable with `--browser-command`."
        ),
        "config_help": "Path to the config file that stores the Cookie. Default: %(default)s",
        "config_json_failed": "Could not read the config file as JSON: {path}",
        "config_missing": "Login information has not been saved yet. Run `hsr-login login` first.",
        "cookie_empty": "Cookie is empty. Paste the HoYoLAB Cookie header.",
        "cookie_prompt": "Paste the HoYoLAB Cookie header: ",
        "debug_port_help": "Port for DevTools / WebDriver. Normally assigned automatically.",
        "devtools_command_failed": "DevTools command failed: {error}",
        "devtools_connect_failed": "Could not connect to {service}: {error}",
        "devtools_service": "browser DevTools",
        "devtools_ws_failed": "Failed to connect to the DevTools WebSocket.",
        "devtools_ws_missing": "Could not get the DevTools WebSocket URL.",
        "error_prefix": "Error: {error}",
        "fallback_manual": "Falling back to manual entry.",
        "first_bind": "HoYoLAB requires first-time account binding. Please check in manually once in the browser.",
        "game_label": "Game: {game}",
        "hoyolab_connect_failed": "Could not connect to the HoYoLAB API: {reason}",
        "hoyolab_http_failed": "HoYoLAB API returned HTTP {code}: {body}",
        "hoyolab_json_failed": "Could not read the HoYoLAB API response as JSON: {body}",
        "hoyolab_cookie_missing": "Could not detect HoYoLAB Cookies.",
        "interrupted": "\nInterrupted.",
        "login_browser_help": "Browser for automatic capture. auto tries Chromium-family browsers first and also tries Safari on macOS. Default: %(default)s",
        "login_browser_command_help": "Executable path or command name for the Chrome / Chromium-family browser used for automatic capture.",
        "login_check_help": "Check the login status after saving.",
        "login_close_browser_help": "Close the automatic capture browser after the Cookie is saved.",
        "login_cookie_file_help": "Read the Cookie header from a text file.",
        "login_cookie_help": "Pass the Cookie header directly. Note that this can remain in shell history.",
        "login_help": "Save the HoYoLAB Cookie.",
        "login_manual_help": "Enter the Cookie header manually instead of automatic browser capture.",
        "login_no_open_help": "Do not open the browser automatically. Useful with manual entry.",
        "login_opening": "Opening the {game} check-in page:",
        "login_profile_dir_help": "Profile directory for the automatic capture browser. Defaults to browser-profile next to the config file.",
        "login_safaridriver_help": "Executable path or command name for safaridriver used by Safari automatic capture.",
        "login_timeout_help": "Seconds to wait for automatic Cookie capture from the browser. Default: %(default)s",
        "logout_deleted": "Deleted login information: {path}",
        "logout_help": "Delete the saved Cookie.",
        "logout_missing": "No login information found: {path}",
        "manual_cookie_help": """
While logged in to HoYoLAB, get the Cookie header from your browser developer tools.
Use the {game} check-in page, not the Genshin Impact or Zenless Zone Zero pages.

Example:
  1. Open the Network tab in developer tools
  2. Reload the page
  3. Select a request to hoyolab.com / act.hoyolab.com / sg-public-api.hoyolab.com
  4. Paste the value after Cookie: in Request Headers
""",
        "no_auth_cookie_warning": (
            "Warning: authentication Cookies such as ltoken_v2/ltuid_v2 were not found. "
            "The Cookie will still be saved, but check-in may fail with a login error."
        ),
        "none": "none",
        "parser_description": "Claim HoYoLAB web daily login rewards for {game}.",
        "safari_automation_hint": (
            "To use Safari automatic capture, enable Allow Remote Automation in Safari's Develop menu "
            "or run `safaridriver --enable`."
        ),
        "safari_cookie_list_missing": "Could not read the Cookie list from Safari.",
        "safari_json_failed": "Could not read the Safari WebDriver response as JSON: {body}",
        "safari_not_macos": "Safari automatic capture is only available on macOS.",
        "safari_opened": "Opening a Safari automation window. Log in to HoYoLAB and the Cookie will be saved automatically.",
        "safari_profile_dir_unsupported": "`--profile-dir` cannot be used with Safari automatic capture. Safari WebDriver uses an isolated session.",
        "safari_response_invalid": "Safari WebDriver returned an invalid response.",
        "safari_session_id_missing": "Could not get the Safari WebDriver session ID.",
        "safari_session_start_failed": "Could not start a Safari WebDriver session: {error} {hint}",
        "safaridriver_launch_failed": "Could not start safaridriver: {error}",
        "safaridriver_not_found": "safaridriver not found: {command}",
        "safaridriver_required": "Safari automatic capture requires macOS safaridriver. Use `--manual`, or use a Chromium-family browser.",
        "saved_login": "Saved login information: {path}",
        "status_check_help": "Check today's claim status.",
        "status_claim_state": "Today's claim: {state}",
        "status_failed": "Status check failed: retcode={retcode} message={message}",
        "status_json_help": "Print the HoYoLAB API status response as JSON.",
        "status_today": "Today: {today}",
        "status_total": "Monthly check-in days: {total}",
        "timeout_seconds": "Timeout: {seconds} seconds",
        "unsupported_ws_url": "Unsupported DevTools WebSocket URL: {url}",
        "webdriver_command_failed": "Safari WebDriver command failed: {message}",
        "webdriver_connect_failed": "Could not connect to Safari WebDriver: {error}",
        "websocket_closed": "DevTools WebSocket disconnected.",
        "websocket_read_failed": "Could not read from the DevTools WebSocket.",
    },
}

CLAIM_STATES = {
    UI_JAPANESE: {True: "済み", False: "未受け取り"},
    UI_ENGLISH: {True: "claimed", False: "not claimed"},
}

_CURRENT_UI_LANGUAGE: str | None = None


def language_tag(value: str | None) -> str | None:
    if not value:
        return None
    tag = value.strip().lower().replace("_", "-")
    return tag or None


def ui_language_from_tag(value: str | None) -> str | None:
    tag = language_tag(value)
    if not tag or not tag[0].isalpha():
        return None
    return UI_JAPANESE if tag.startswith("ja") else UI_ENGLISH


def normalize_ui_language(value: str | None) -> str:
    return ui_language_from_tag(value) or UI_ENGLISH


def normalize_api_language(value: str | None) -> str:
    ui_language = ui_language_from_tag(value)
    return API_LANGUAGE_BY_UI[ui_language] if ui_language else DEFAULT_API_LANGUAGE


def api_language_for_ui(ui_language: str | None) -> str:
    return API_LANGUAGE_BY_UI[normalize_ui_language(ui_language)]


def game_name(ui_language: str | None = None) -> str:
    return GAME_NAMES[normalize_ui_language(ui_language)]


def event_url(api_language: str | None = None) -> str:
    lang = normalize_api_language(api_language)
    query = urllib.parse.urlencode(
        {
            "act_id": ACT_ID,
            "bbs_auth_required": "true",
            "bbs_presentation_style": "fullscreen",
            "lang": lang,
        }
    )
    return f"{EVENT_BASE_URL}?{query}"


def cookie_values(cookie: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in cookie.split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip().lower()
        value = urllib.parse.unquote(value.strip())
        if name:
            values[name] = value
    return values


def ui_language_from_cookie(cookie: str) -> str | None:
    values = cookie_values(cookie)
    for name in ("mi18nlang", "hoyolab_lang", "hyl_lang"):
        if language := ui_language_from_tag(values.get(name)):
            return language
    return None


def ui_language_from_config(config: dict[str, Any]) -> str | None:
    for key in ("ui_language", "lang", "language"):
        value = config.get(key)
        if isinstance(value, str):
            if language := ui_language_from_tag(value):
                return language
    return None


def detect_os_ui_language() -> str | None:
    if is_macos():
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            result = None
        if result and result.stdout:
            for line in result.stdout.splitlines():
                cleaned = line.strip().strip('",;()')
                if language := ui_language_from_tag(cleaned):
                    return language
    if is_windows():
        try:
            import ctypes

            buffer = ctypes.create_unicode_buffer(85)
            size = ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
            if size:
                return ui_language_from_tag(buffer.value)
        except (AttributeError, OSError, ValueError):
            pass
    return None


def detect_ui_language(
    config_path: Path | None = None,
    cookie: str | None = None,
    fallback: str | None = None,
) -> str:
    if cookie and (language := ui_language_from_cookie(cookie)):
        return language
    if config_path and config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = {}
        if isinstance(config, dict) and (language := ui_language_from_config(config)):
            return language
    if fallback and (language := ui_language_from_tag(fallback)):
        return language
    return detect_os_ui_language() or UI_ENGLISH


def set_current_ui_language(ui_language: str | None) -> None:
    global _CURRENT_UI_LANGUAGE
    _CURRENT_UI_LANGUAGE = normalize_ui_language(ui_language)


def current_ui_language() -> str:
    return _CURRENT_UI_LANGUAGE or detect_ui_language()


def t(key: str, ui_language: str | None = None, **kwargs: object) -> str:
    language = normalize_ui_language(ui_language or current_ui_language())
    template = MESSAGES[language][key]
    if kwargs:
        return template.format(**kwargs)
    return template


def is_windows() -> bool:
    return os.name == "nt"


def is_macos() -> bool:
    return sys.platform == "darwin"


def default_config_path() -> Path:
    if value := os.environ.get("HSR_LOGIN_CONFIG"):
        return Path(value).expanduser()
    if is_windows():
        config_home = os.environ.get("APPDATA")
        if config_home:
            return Path(config_home).expanduser() / "hsr-login" / "config.json"
        return Path.home() / "AppData" / "Roaming" / "hsr-login" / "config.json"
    if value := os.environ.get("XDG_CONFIG_HOME"):
        return Path(value).expanduser() / "hsr-login" / "config.json"
    return Path.home() / ".config" / "hsr-login" / "config.json"


def normalize_cookie(raw_cookie: str) -> str:
    cookie = raw_cookie.strip()
    if cookie.lower().startswith("cookie:"):
        cookie = cookie.split(":", 1)[1].strip()

    parts: list[str] = []
    seen: set[str] = set()
    for part in cookie.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        parts.append(f"{name}={value}")

    normalized = "; ".join(parts)
    if not normalized:
        raise HsrLoginError(t("cookie_empty"))
    return normalized


def cookie_names(cookie: str) -> set[str]:
    return {part.split("=", 1)[0].strip() for part in cookie.split(";") if "=" in part}


def looks_authenticated(cookie: str) -> bool:
    names = cookie_names(cookie)
    modern = {"ltoken_v2", "ltuid_v2"} <= names
    legacy = {"ltoken", "ltuid"} <= names
    token_only = bool({"cookie_token", "cookie_token_v2"} & names) and bool(
        {"account_id", "account_id_v2"} & names
    )
    return modern or legacy or token_only


def browser_profile_path(config_path: Path) -> Path:
    return config_path.parent / "browser-profile"


def cookie_domain_matches(domain: str) -> bool:
    normalized = domain.lstrip(".").lower()
    return any(normalized == target or normalized.endswith(f".{target}") for target in HOYOLAB_COOKIE_DOMAINS)


def cookies_to_header(cookies: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for cookie in cookies:
        name = str(cookie.get("name", "")).strip()
        value = str(cookie.get("value", "")).strip()
        domain = str(cookie.get("domain", "")).strip()
        if not name or not value or name.lower() in seen or not cookie_domain_matches(domain):
            continue
        seen.add(name.lower())
        parts.append(f"{name}={value}")
    return normalize_cookie("; ".join(parts))


def windows_browser_candidates() -> list[str]:
    candidates = [
        "chrome",
        "chrome.exe",
        "msedge",
        "msedge.exe",
        "brave",
        "brave.exe",
        "comet",
        "comet.exe",
        "arc",
        "arc.exe",
    ]
    program_files = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
    ]
    relative_paths = [
        ("Google", "Chrome", "Application", "chrome.exe"),
        ("Chromium", "Application", "chrome.exe"),
        ("Microsoft", "Edge", "Application", "msedge.exe"),
        ("BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        ("Comet", "Application", "comet.exe"),
    ]
    for root in program_files:
        if not root:
            continue
        candidates.extend(str(Path(root).joinpath(*parts)) for parts in relative_paths)
    return candidates


def unix_browser_candidates() -> list[str]:
    return [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"),
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        str(Path.home() / "Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        "/Applications/Comet.app/Contents/MacOS/Comet",
        str(Path.home() / "Applications/Comet.app/Contents/MacOS/Comet"),
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        str(Path.home() / "Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
        "/Applications/Arc.app/Contents/MacOS/Arc",
        str(Path.home() / "Applications/Arc.app/Contents/MacOS/Arc"),
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "msedge",
        "brave-browser",
        "comet",
    ]


def find_browser_command(preferred: str | None = None) -> str:
    return find_chromium_browser_command(preferred)


def find_chromium_browser_command(preferred: str | None = None) -> str:
    if preferred:
        preferred = preferred.strip().strip('"')
        command = Path(preferred).expanduser()
        if command.exists():
            return str(command)
        resolved = shutil.which(preferred)
        if resolved:
            return resolved
        raise HsrLoginError(t("browser_not_found", browser=preferred))

    if value := os.environ.get("HSR_LOGIN_BROWSER"):
        return find_browser_command(value)

    candidates = windows_browser_candidates() if is_windows() else unix_browser_candidates()
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
        if resolved := shutil.which(candidate):
            return resolved
    raise HsrLoginError(t("chromium_not_found"))


def find_safaridriver_command(preferred: str | None = None) -> str:
    if preferred:
        preferred = preferred.strip().strip('"')
        command = Path(preferred).expanduser()
        if command.exists():
            return str(command)
        resolved = shutil.which(preferred)
        if resolved:
            return resolved
        raise HsrLoginError(t("safaridriver_not_found", command=preferred))

    if value := os.environ.get("HSR_LOGIN_SAFARIDRIVER"):
        return find_safaridriver_command(value)

    candidates = [
        "safaridriver",
        "/usr/bin/safaridriver",
        "/System/Cryptexes/App/usr/bin/safaridriver",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
        if resolved := shutil.which(candidate):
            return resolved
    raise HsrLoginError(t("safaridriver_required"))


def safari_automation_hint() -> str:
    return t("safari_automation_hint")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_json(url: str, timeout: float, service_name: str | None = None) -> dict[str, Any]:
    service_name = service_name or t("devtools_service")
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return payload
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(0.25)
    raise HsrLoginError(t("devtools_connect_failed", service=service_name, error=last_error))


class DevToolsWebSocket:
    def __init__(self, url: str, timeout: float = 5.0) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise HsrLoginError(t("unsupported_ws_url", url=url))

        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self._read_http_response()
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if " 101 " not in response.split("\r\n", 1)[0] or expected_accept not in response:
            self.close()
            raise HsrLoginError(t("devtools_ws_failed"))

        self._next_id = 0

    def __enter__(self) -> "DevToolsWebSocket":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        message_id = self._next_id
        payload = {"id": message_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send_text(json.dumps(payload, separators=(",", ":")))

        while True:
            message = self._read_text()
            try:
                response = json.loads(message)
            except json.JSONDecodeError:
                continue
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise HsrLoginError(t("devtools_command_failed", error=response["error"]))
            result = response.get("result")
            return result if isinstance(result, dict) else {}

    def _read_http_response(self) -> str:
        chunks: list[bytes] = []
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\r\n\r\n" in b"".join(chunks):
                break
        return b"".join(chunks).decode("iso-8859-1", errors="replace")

    def _send_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend((0x80 | 126, *struct.pack("!H", length)))
        else:
            header.extend((0x80 | 127, *struct.pack("!Q", length)))
        mask = secrets.token_bytes(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _read_text(self) -> str:
        message = bytearray()
        while True:
            opcode, payload = self._read_frame()
            if opcode == 0x8:
                raise HsrLoginError(t("websocket_closed"))
            if opcode == 0x9:
                self._send_pong(payload)
                continue
            if opcode in {0x1, 0x0}:
                message.extend(payload)
                return message.decode("utf-8")

    def _read_frame(self) -> tuple[int, bytes]:
        header = self._recv_exact(2)
        first, second = header
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _send_pong(self, payload: bytes) -> None:
        header = bytearray([0x8A])
        length = len(payload)
        if length > 125:
            return
        header.append(0x80 | length)
        mask = secrets.token_bytes(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise HsrLoginError(t("websocket_read_failed"))
            data.extend(chunk)
        return bytes(data)


def launch_chromium_cookie_browser(args: argparse.Namespace, config_path: Path) -> tuple[subprocess.Popen[bytes], int]:
    browser = find_chromium_browser_command(args.browser_command)
    port = int(args.debug_port) if args.debug_port else find_free_port()
    profile_dir = Path(args.profile_dir).expanduser() if args.profile_dir else browser_profile_path(config_path)
    api_language = api_language_for_ui(getattr(args, "ui_language", None))
    profile_dir.mkdir(parents=True, exist_ok=True)
    try:
        profile_dir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError:
        pass

    command = [
        browser,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        event_url(api_language),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process, port


def fetch_devtools_cookies(port: int) -> list[dict[str, Any]]:
    version = wait_for_json(f"http://127.0.0.1:{port}/json/version", timeout=10.0)
    websocket_url = version.get("webSocketDebuggerUrl")
    if not isinstance(websocket_url, str):
        raise HsrLoginError(t("devtools_ws_missing"))
    with DevToolsWebSocket(websocket_url) as devtools:
        result = devtools.call("Storage.getCookies")
    cookies = result.get("cookies")
    if not isinstance(cookies, list):
        raise HsrLoginError(t("browser_cookie_list_missing"))
    return [cookie for cookie in cookies if isinstance(cookie, dict)]


def get_cookie_from_chromium(args: argparse.Namespace, config_path: Path) -> str:
    process, port = launch_chromium_cookie_browser(args, config_path)
    deadline = time.monotonic() + float(args.timeout)
    ui_language = getattr(args, "ui_language", None)
    print(t("browser_opened", ui_language))
    print(t("timeout_seconds", ui_language, seconds=int(args.timeout)))
    try:
        last_cookie = ""
        while time.monotonic() < deadline:
            cookies = fetch_devtools_cookies(port)
            try:
                cookie = cookies_to_header(cookies)
            except HsrLoginError:
                cookie = ""
            if cookie:
                last_cookie = cookie
            if cookie and looks_authenticated(cookie):
                return cookie
            time.sleep(2.0)
    finally:
        if args.close_browser:
            process.terminate()
    if last_cookie:
        names = ", ".join(sorted(cookie_names(last_cookie) & AUTH_COOKIE_NAMES)) or t("none", ui_language)
        raise HsrLoginError(t("auth_cookies_missing", ui_language, names=names))
    raise HsrLoginError(t("hoyolab_cookie_missing", ui_language))


def webdriver_json_request(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = webdriver_error_message(body) or str(exc)
        raise HsrLoginError(t("webdriver_command_failed", message=message)) from exc
    except (OSError, urllib.error.URLError) as exc:
        raise HsrLoginError(t("webdriver_connect_failed", error=exc)) from exc

    try:
        result = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise HsrLoginError(t("safari_json_failed", body=body)) from exc
    if not isinstance(result, dict):
        raise HsrLoginError(t("safari_response_invalid"))
    return result


def webdriver_error_message(body: str) -> str | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or None
    if not isinstance(payload, dict):
        return None
    value = payload.get("value")
    if isinstance(value, dict):
        message = value.get("message")
        error = value.get("error")
        if message and error:
            return f"{error}: {message}"
        if message:
            return str(message)
    message = payload.get("message")
    return str(message) if message else None


def launch_safaridriver(args: argparse.Namespace) -> tuple[subprocess.Popen[bytes], int]:
    if not is_macos():
        raise HsrLoginError(t("safari_not_macos"))
    command = find_safaridriver_command(getattr(args, "safaridriver_command", None))
    port = int(args.debug_port) if args.debug_port else find_free_port()
    try:
        process = subprocess.Popen(
            [command, "-p", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise HsrLoginError(t("safaridriver_launch_failed", error=exc)) from exc
    return process, port


def create_safari_webdriver_session(port: int) -> str:
    endpoint = f"http://127.0.0.1:{port}/session"
    payload = {"capabilities": {"alwaysMatch": {"browserName": "safari"}}}
    deadline = time.monotonic() + 10.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = webdriver_json_request("POST", endpoint, payload, timeout=1.0)
            session_id = webdriver_session_id(response)
            if session_id:
                return session_id
            raise HsrLoginError(t("safari_session_id_missing"))
        except HsrLoginError as exc:
            last_error = exc
            time.sleep(0.25)
    raise HsrLoginError(
        t("safari_session_start_failed", error=last_error, hint=safari_automation_hint())
    )


def webdriver_session_id(response: dict[str, Any]) -> str | None:
    value = response.get("value")
    if isinstance(value, dict) and isinstance(value.get("sessionId"), str):
        return value["sessionId"]
    if isinstance(response.get("sessionId"), str):
        return response["sessionId"]
    return None


def safari_webdriver_base_url(port: int, session_id: str) -> str:
    return f"http://127.0.0.1:{port}/session/{urllib.parse.quote(session_id)}"


def navigate_safari_webdriver(port: int, session_id: str, api_language: str | None = None) -> None:
    webdriver_json_request(
        "POST",
        f"{safari_webdriver_base_url(port, session_id)}/url",
        {"url": event_url(api_language)},
    )


def fetch_safari_webdriver_cookies(port: int, session_id: str) -> list[dict[str, Any]]:
    response = webdriver_json_request("GET", f"{safari_webdriver_base_url(port, session_id)}/cookie", timeout=3.0)
    cookies = response.get("value")
    if not isinstance(cookies, list):
        raise HsrLoginError(t("safari_cookie_list_missing"))
    return [cookie for cookie in cookies if isinstance(cookie, dict)]


def delete_safari_webdriver_session(port: int, session_id: str) -> None:
    try:
        webdriver_json_request("DELETE", safari_webdriver_base_url(port, session_id), timeout=2.0)
    except HsrLoginError:
        pass


def get_cookie_from_safari(args: argparse.Namespace, config_path: Path) -> str:
    del config_path
    if args.profile_dir:
        raise HsrLoginError(t("safari_profile_dir_unsupported"))
    process, port = launch_safaridriver(args)
    session_id: str | None = None
    last_cookie = ""
    deadline = time.monotonic() + float(args.timeout)
    ui_language = getattr(args, "ui_language", None)
    print(t("safari_opened", ui_language))
    print(t("timeout_seconds", ui_language, seconds=int(args.timeout)))
    try:
        session_id = create_safari_webdriver_session(port)
        navigate_safari_webdriver(port, session_id, api_language_for_ui(ui_language))
        while time.monotonic() < deadline:
            cookies = fetch_safari_webdriver_cookies(port, session_id)
            try:
                cookie = cookies_to_header(cookies)
            except HsrLoginError:
                cookie = ""
            if cookie:
                last_cookie = cookie
            if cookie and looks_authenticated(cookie):
                return cookie
            time.sleep(2.0)
    finally:
        if session_id and args.close_browser:
            delete_safari_webdriver_session(port, session_id)
        process.terminate()
        try:
            process.wait(timeout=2.0)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if last_cookie:
        names = ", ".join(sorted(cookie_names(last_cookie) & AUTH_COOKIE_NAMES)) or t("none", ui_language)
        raise HsrLoginError(t("auth_cookies_missing", ui_language, names=names))
    raise HsrLoginError(t("hoyolab_cookie_missing", ui_language))


def get_cookie_from_browser(args: argparse.Namespace, config_path: Path) -> str:
    browser = getattr(args, "browser", BROWSER_AUTO)
    if browser == BROWSER_SAFARI:
        return get_cookie_from_safari(args, config_path)
    if browser == BROWSER_CHROMIUM or args.browser_command:
        return get_cookie_from_chromium(args, config_path)

    try:
        find_chromium_browser_command(None)
    except HsrLoginError:
        if is_macos():
            find_safaridriver_command(getattr(args, "safaridriver_command", None))
            return get_cookie_from_safari(args, config_path)
        raise
    return get_cookie_from_chromium(args, config_path)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HsrLoginError(t("config_missing"))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HsrLoginError(t("config_json_failed", path=path)) from exc


def save_config(path: Path, cookie: str, ui_language: str | None = None) -> None:
    ui_language = detect_ui_language(path, cookie, ui_language)
    api_language = api_language_for_ui(ui_language)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "game": game_name(ui_language),
        "act_id": ACT_ID,
        "lang": api_language,
        "ui_language": ui_language,
        "event_url": event_url(api_language),
        "cookie": cookie,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
    finally:
        try:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass


class HoyoLabClient:
    def __init__(
        self,
        cookie: str,
        timeout: float = 20.0,
        api_language: str | None = None,
        ui_language: str | None = None,
    ) -> None:
        self.cookie = cookie
        self.timeout = timeout
        self.ui_language = normalize_ui_language(
            ui_language or ui_language_from_cookie(cookie) or ui_language_from_tag(api_language)
        )
        self.api_language = normalize_api_language(api_language or api_language_for_ui(self.ui_language))

    def info(self) -> ApiResult:
        return self._request("GET", "info")

    def rewards(self) -> ApiResult:
        return self._request("GET", "home")

    def sign(self) -> ApiResult:
        return self._request("POST", "sign")

    def _request(self, method: str, action: str) -> ApiResult:
        params = urllib.parse.urlencode({"lang": self.api_language, "act_id": ACT_ID})
        url = f"{API_BASE_URL}/{action}?{params}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": ACCEPT_LANGUAGE_BY_UI[self.ui_language],
            "Cookie": self.cookie,
            "Origin": "https://act.hoyolab.com",
            "Referer": event_url(self.api_language),
            "User-Agent": DEFAULT_USER_AGENT,
            "x-rpc-app_version": "2.34.1",
            "x-rpc-client_type": "5",
            "x-rpc-language": self.api_language,
        }
        data = b"" if method == "POST" else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise HsrLoginError(t("hoyolab_http_failed", self.ui_language, code=exc.code, body=body)) from exc
        except urllib.error.URLError as exc:
            raise HsrLoginError(t("hoyolab_connect_failed", self.ui_language, reason=exc.reason)) from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HsrLoginError(t("hoyolab_json_failed", self.ui_language, body=body)) from exc

        return ApiResult(
            retcode=int(payload.get("retcode", 0)),
            message=str(payload.get("message", "")),
            data=payload.get("data") if isinstance(payload.get("data"), dict) else {},
        )


def get_cookie(args: argparse.Namespace, config_path: Path) -> str:
    if args.cookie:
        return normalize_cookie(args.cookie)
    if args.cookie_file:
        return normalize_cookie(Path(args.cookie_file).expanduser().read_text(encoding="utf-8"))
    if not args.manual and not args.no_open:
        try:
            return get_cookie_from_browser(args, config_path)
        except HsrLoginError as exc:
            ui_language = getattr(args, "ui_language", None)
            print(t("auto_cookie_failed", ui_language, error=exc), file=sys.stderr)
            print(t("fallback_manual", ui_language), file=sys.stderr)
            print_manual_cookie_help(ui_language)
    return normalize_cookie(getpass.getpass(t("cookie_prompt", getattr(args, "ui_language", None))))


def print_manual_cookie_help(ui_language: str | None = None) -> None:
    print(
        textwrap.dedent(t("manual_cookie_help", ui_language, game=game_name(ui_language))).strip()
    )


def command_login(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    ui_language = getattr(args, "ui_language", detect_ui_language(path))
    if args.manual and not args.no_open:
        print(t("login_opening", ui_language, game=game_name(ui_language)))
        url = event_url(api_language_for_ui(ui_language))
        print(url)
        webbrowser.open(url)

    if args.manual:
        print_manual_cookie_help(ui_language)

    cookie = get_cookie(args, path)
    ui_language = detect_ui_language(path, cookie, ui_language)
    args.ui_language = ui_language
    set_current_ui_language(ui_language)
    if not looks_authenticated(cookie):
        print(
            t("no_auth_cookie_warning", ui_language),
            file=sys.stderr,
        )

    save_config(path, cookie, ui_language)
    print(t("saved_login", ui_language, path=path))

    if args.check:
        return command_status(argparse.Namespace(config=str(path), json=False, ui_language=ui_language))
    return 0


def load_client(args: argparse.Namespace) -> HoyoLabClient:
    config = load_config(Path(args.config).expanduser())
    cookie = normalize_cookie(str(config.get("cookie", "")))
    ui_language = (
        ui_language_from_config(config)
        or ui_language_from_cookie(cookie)
        or getattr(args, "ui_language", None)
    )
    api_language = config.get("lang") if isinstance(config.get("lang"), str) else None
    return HoyoLabClient(cookie, api_language=api_language, ui_language=ui_language)


def command_status(args: argparse.Namespace) -> int:
    client = load_client(args)
    info = client.info()
    if args.json:
        payload = {"retcode": info.retcode, "message": info.message, "data": info.data}
        print(json.dumps(payload, ensure_ascii=False))
        return 0 if info.retcode == 0 else 1

    if info.retcode != 0:
        print(t("status_failed", client.ui_language, retcode=info.retcode, message=info.message))
        return 1

    is_sign = bool(info.data.get("is_sign"))
    total = info.data.get("total_sign_day")
    today = info.data.get("today")
    print(t("game_label", client.ui_language, game=game_name(client.ui_language)))
    print(t("status_today", client.ui_language, today=today))
    print(t("status_total", client.ui_language, total=total))
    print(t("status_claim_state", client.ui_language, state=CLAIM_STATES[client.ui_language][is_sign]))
    return 0


def today_reward(client: HoyoLabClient, total_sign_day: int | None) -> str | None:
    if total_sign_day is None:
        return None
    rewards = client.rewards()
    awards = rewards.data.get("awards")
    if not isinstance(awards, list):
        return None
    index = max(total_sign_day, 0)
    if index >= len(awards):
        return None
    award = awards[index]
    if not isinstance(award, dict):
        return None
    name = award.get("name")
    count = award.get("cnt")
    if name and count:
        return f"{name} x{count}"
    return None


def command_claim(args: argparse.Namespace) -> int:
    client = load_client(args)
    info = client.info()
    if info.retcode != 0:
        print(t("status_failed", client.ui_language, retcode=info.retcode, message=info.message))
        return 1

    if info.data.get("first_bind"):
        print(t("first_bind", client.ui_language))
        return 1

    total_sign_day = info.data.get("total_sign_day")
    if isinstance(total_sign_day, int):
        reward = today_reward(client, total_sign_day)
    else:
        reward = None

    if info.data.get("is_sign"):
        print(t("already_claimed", client.ui_language, game=game_name(client.ui_language)))
        return 0

    result = client.sign()
    if result.retcode == 0:
        if reward:
            print(t("claimed_reward", client.ui_language, game=game_name(client.ui_language), reward=reward))
        else:
            print(t("claimed", client.ui_language, game=game_name(client.ui_language)))
        return 0

    already_signed = (
        result.retcode == -5003
        or "already" in result.message.lower()
        or "already" in str(result.data).lower()
    )
    if already_signed:
        print(t("already_claimed", client.ui_language, game=game_name(client.ui_language)))
        return 0

    gt_result = result.data.get("gt_result")
    if isinstance(gt_result, dict) and gt_result.get("is_risk"):
        print(t("captcha_failed", client.ui_language))
        return 2

    print(t("claim_failed", client.ui_language, retcode=result.retcode, message=result.message))
    return 1


def command_logout(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    ui_language = getattr(args, "ui_language", detect_ui_language(path))
    if path.exists():
        path.unlink()
        print(t("logout_deleted", ui_language, path=path))
    else:
        print(t("logout_missing", ui_language, path=path))
    return 0


def config_path_from_argv(argv: list[str] | None) -> Path:
    tokens = list(argv if argv is not None else sys.argv[1:])
    for index, token in enumerate(tokens):
        if token == "--config" and index + 1 < len(tokens):
            return Path(tokens[index + 1]).expanduser()
        if token.startswith("--config="):
            return Path(token.split("=", 1)[1]).expanduser()
    return default_config_path()


def build_parser(ui_language: str | None = None, config_path: Path | None = None) -> argparse.ArgumentParser:
    ui_language = normalize_ui_language(ui_language or detect_ui_language(config_path or default_config_path()))
    parser = argparse.ArgumentParser(
        description=t("parser_description", ui_language, game=game_name(ui_language)),
    )
    parser.add_argument(
        "--config",
        default=str(default_config_path()),
        help=t("config_help", ui_language),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    login = subparsers.add_parser("login", help=t("login_help", ui_language))
    login.add_argument("--cookie", help=t("login_cookie_help", ui_language))
    login.add_argument("--cookie-file", help=t("login_cookie_file_help", ui_language))
    login.add_argument("--manual", action="store_true", help=t("login_manual_help", ui_language))
    login.add_argument("--no-open", action="store_true", help=t("login_no_open_help", ui_language))
    login.add_argument(
        "--browser",
        choices=BROWSER_CHOICES,
        default=BROWSER_AUTO,
        help=t("login_browser_help", ui_language),
    )
    login.add_argument(
        "--browser-command",
        help=t("login_browser_command_help", ui_language),
    )
    login.add_argument(
        "--safaridriver-command",
        help=t("login_safaridriver_help", ui_language),
    )
    login.add_argument(
        "--profile-dir",
        help=t("login_profile_dir_help", ui_language),
    )
    login.add_argument("--debug-port", type=int, help=t("debug_port_help", ui_language))
    login.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_BROWSER_TIMEOUT,
        help=t("login_timeout_help", ui_language),
    )
    login.add_argument("--close-browser", action="store_true", help=t("login_close_browser_help", ui_language))
    login.add_argument("--check", action="store_true", help=t("login_check_help", ui_language))
    login.set_defaults(func=command_login)

    claim = subparsers.add_parser("claim", help=t("claim_help", ui_language))
    claim.set_defaults(func=command_claim)

    status = subparsers.add_parser("status", help=t("status_check_help", ui_language))
    status.add_argument("--json", action="store_true", help=t("status_json_help", ui_language))
    status.set_defaults(func=command_status)

    logout = subparsers.add_parser("logout", help=t("logout_help", ui_language))
    logout.set_defaults(func=command_logout)

    parser.set_defaults(func=command_claim, ui_language=ui_language)
    return parser


def main(argv: list[str] | None = None) -> int:
    config_path = config_path_from_argv(argv)
    ui_language = detect_ui_language(config_path)
    set_current_ui_language(ui_language)
    parser = build_parser(ui_language, config_path)
    args = parser.parse_args(argv)
    if not hasattr(args, "ui_language"):
        args.ui_language = ui_language
    try:
        return int(args.func(args))
    except HsrLoginError as exc:
        print(t("error_prefix", getattr(args, "ui_language", ui_language), error=exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(t("interrupted", getattr(args, "ui_language", ui_language)), file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
