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


__version__ = "0.3.1"
GAME_NAME = "崩壊：スターレイル"
ACT_ID = "e202303301540311"
LANG = "ja-jp"
EVENT_URL = (
    "https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html"
    f"?act_id={ACT_ID}&bbs_auth_required=true&bbs_presentation_style=fullscreen&lang={LANG}"
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
        raise HsrLoginError("Cookie が空です。HoYoLAB の Cookie ヘッダーを貼り付けてください。")
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
        raise HsrLoginError(f"ブラウザーが見つかりません: {preferred}")

    if value := os.environ.get("HSR_LOGIN_BROWSER"):
        return find_browser_command(value)

    candidates = windows_browser_candidates() if is_windows() else unix_browser_candidates()
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
        if resolved := shutil.which(candidate):
            return resolved
    raise HsrLoginError(
        "Chrome / Chromium 系ブラウザーが見つかりません。"
        "`--manual` で手動入力するか、`--browser-command` で実行ファイルを指定してください。"
    )


def find_safaridriver_command(preferred: str | None = None) -> str:
    if preferred:
        preferred = preferred.strip().strip('"')
        command = Path(preferred).expanduser()
        if command.exists():
            return str(command)
        resolved = shutil.which(preferred)
        if resolved:
            return resolved
        raise HsrLoginError(f"safaridriver が見つかりません: {preferred}")

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
    raise HsrLoginError(
        "Safari 自動取得には macOS の safaridriver が必要です。"
        "`--manual` で手動入力するか、Chromium 系ブラウザーを使ってください。"
    )


def safari_automation_hint() -> str:
    return (
        "Safari 自動取得を使うには、Safari の開発メニューで"
        "「リモートオートメーションを許可」を有効にするか、"
        "`safaridriver --enable` を実行してください。"
    )


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_json(url: str, timeout: float, service_name: str = "ブラウザーの DevTools") -> dict[str, Any]:
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
    raise HsrLoginError(f"{service_name} に接続できません: {last_error}")


class DevToolsWebSocket:
    def __init__(self, url: str, timeout: float = 5.0) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise HsrLoginError(f"未対応の DevTools WebSocket URL です: {url}")

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
            raise HsrLoginError("DevTools WebSocket の接続に失敗しました。")

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
                raise HsrLoginError(f"DevTools コマンドに失敗しました: {response['error']}")
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
                raise HsrLoginError("DevTools WebSocket が切断されました。")
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
                raise HsrLoginError("DevTools WebSocket からの読み込みに失敗しました。")
            data.extend(chunk)
        return bytes(data)


def launch_chromium_cookie_browser(args: argparse.Namespace, config_path: Path) -> tuple[subprocess.Popen[bytes], int]:
    browser = find_chromium_browser_command(args.browser_command)
    port = int(args.debug_port) if args.debug_port else find_free_port()
    profile_dir = Path(args.profile_dir).expanduser() if args.profile_dir else browser_profile_path(config_path)
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
        EVENT_URL,
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process, port


def fetch_devtools_cookies(port: int) -> list[dict[str, Any]]:
    version = wait_for_json(f"http://127.0.0.1:{port}/json/version", timeout=10.0)
    websocket_url = version.get("webSocketDebuggerUrl")
    if not isinstance(websocket_url, str):
        raise HsrLoginError("DevTools の WebSocket URL を取得できません。")
    with DevToolsWebSocket(websocket_url) as devtools:
        result = devtools.call("Storage.getCookies")
    cookies = result.get("cookies")
    if not isinstance(cookies, list):
        raise HsrLoginError("ブラウザーから Cookie 一覧を取得できません。")
    return [cookie for cookie in cookies if isinstance(cookie, dict)]


def get_cookie_from_chromium(args: argparse.Namespace, config_path: Path) -> str:
    process, port = launch_chromium_cookie_browser(args, config_path)
    deadline = time.monotonic() + float(args.timeout)
    print("ブラウザーを開きました。HoYoLAB にログインすると Cookie を自動保存します。")
    print(f"タイムアウト: {int(args.timeout)} 秒")
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
        names = ", ".join(sorted(cookie_names(last_cookie) & AUTH_COOKIE_NAMES)) or "なし"
        raise HsrLoginError(f"認証 Cookie がそろいませんでした。検出した認証系 Cookie: {names}")
    raise HsrLoginError("HoYoLAB の Cookie を検出できませんでした。")


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
        raise HsrLoginError(f"Safari WebDriver コマンドに失敗しました: {message}") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise HsrLoginError(f"Safari WebDriver に接続できません: {exc}") from exc

    try:
        result = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise HsrLoginError(f"Safari WebDriver の応答を JSON として読めません: {body}") from exc
    if not isinstance(result, dict):
        raise HsrLoginError("Safari WebDriver の応答形式が不正です。")
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
        raise HsrLoginError("Safari 自動取得は macOS でのみ利用できます。")
    command = find_safaridriver_command(getattr(args, "safaridriver_command", None))
    port = int(args.debug_port) if args.debug_port else find_free_port()
    try:
        process = subprocess.Popen(
            [command, "-p", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise HsrLoginError(f"safaridriver を起動できません: {exc}") from exc
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
            raise HsrLoginError("Safari WebDriver の session ID を取得できません。")
        except HsrLoginError as exc:
            last_error = exc
            time.sleep(0.25)
    raise HsrLoginError(f"Safari WebDriver セッションを開始できません: {last_error} {safari_automation_hint()}")


def webdriver_session_id(response: dict[str, Any]) -> str | None:
    value = response.get("value")
    if isinstance(value, dict) and isinstance(value.get("sessionId"), str):
        return value["sessionId"]
    if isinstance(response.get("sessionId"), str):
        return response["sessionId"]
    return None


def safari_webdriver_base_url(port: int, session_id: str) -> str:
    return f"http://127.0.0.1:{port}/session/{urllib.parse.quote(session_id)}"


def navigate_safari_webdriver(port: int, session_id: str) -> None:
    webdriver_json_request("POST", f"{safari_webdriver_base_url(port, session_id)}/url", {"url": EVENT_URL})


def fetch_safari_webdriver_cookies(port: int, session_id: str) -> list[dict[str, Any]]:
    response = webdriver_json_request("GET", f"{safari_webdriver_base_url(port, session_id)}/cookie", timeout=3.0)
    cookies = response.get("value")
    if not isinstance(cookies, list):
        raise HsrLoginError("Safari から Cookie 一覧を取得できません。")
    return [cookie for cookie in cookies if isinstance(cookie, dict)]


def delete_safari_webdriver_session(port: int, session_id: str) -> None:
    try:
        webdriver_json_request("DELETE", safari_webdriver_base_url(port, session_id), timeout=2.0)
    except HsrLoginError:
        pass


def get_cookie_from_safari(args: argparse.Namespace, config_path: Path) -> str:
    del config_path
    if args.profile_dir:
        raise HsrLoginError("Safari 自動取得では `--profile-dir` は使えません。Safari WebDriver の隔離セッションを使います。")
    process, port = launch_safaridriver(args)
    session_id: str | None = None
    last_cookie = ""
    deadline = time.monotonic() + float(args.timeout)
    print("Safari の自動化ウィンドウを開きます。HoYoLAB にログインすると Cookie を自動保存します。")
    print(f"タイムアウト: {int(args.timeout)} 秒")
    try:
        session_id = create_safari_webdriver_session(port)
        navigate_safari_webdriver(port, session_id)
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
        names = ", ".join(sorted(cookie_names(last_cookie) & AUTH_COOKIE_NAMES)) or "なし"
        raise HsrLoginError(f"認証 Cookie がそろいませんでした。検出した認証系 Cookie: {names}")
    raise HsrLoginError("HoYoLAB の Cookie を検出できませんでした。")


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
        raise HsrLoginError(
            "ログイン情報が未保存です。先に `hsr-login login` を実行してください。"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HsrLoginError(f"設定ファイルを JSON として読めません: {path}") from exc


def save_config(path: Path, cookie: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "game": GAME_NAME,
        "act_id": ACT_ID,
        "lang": LANG,
        "event_url": EVENT_URL,
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
    def __init__(self, cookie: str, timeout: float = 20.0) -> None:
        self.cookie = cookie
        self.timeout = timeout

    def info(self) -> ApiResult:
        return self._request("GET", "info")

    def rewards(self) -> ApiResult:
        return self._request("GET", "home")

    def sign(self) -> ApiResult:
        return self._request("POST", "sign")

    def _request(self, method: str, action: str) -> ApiResult:
        params = urllib.parse.urlencode({"lang": LANG, "act_id": ACT_ID})
        url = f"{API_BASE_URL}/{action}?{params}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Cookie": self.cookie,
            "Origin": "https://act.hoyolab.com",
            "Referer": EVENT_URL,
            "User-Agent": DEFAULT_USER_AGENT,
            "x-rpc-app_version": "2.34.1",
            "x-rpc-client_type": "5",
            "x-rpc-language": LANG,
        }
        data = b"" if method == "POST" else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise HsrLoginError(f"HoYoLAB API が HTTP {exc.code} を返しました: {body}") from exc
        except urllib.error.URLError as exc:
            raise HsrLoginError(f"HoYoLAB API に接続できません: {exc.reason}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HsrLoginError(f"HoYoLAB API の応答を JSON として読めません: {body}") from exc

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
            print(f"自動取得に失敗しました: {exc}", file=sys.stderr)
            print("手動入力に切り替えます。", file=sys.stderr)
            print_manual_cookie_help()
    return normalize_cookie(getpass.getpass("HoYoLAB の Cookie ヘッダーを貼り付けてください: "))


def print_manual_cookie_help() -> None:
    print(
        textwrap.dedent(
            f"""
            HoYoLAB にログインした状態で、ブラウザーの開発者ツールから Cookie ヘッダーを取得してください。
            対象ページは「{GAME_NAME}」のチェックインページです。原神やゼンレスゾーンゼロのページではありません。

            例:
              1. 開発者ツールの Network タブを開く
              2. ページを再読み込みする
              3. hoyolab.com / act.hoyolab.com / sg-public-api.hoyolab.com へのリクエストを選ぶ
              4. Request Headers の Cookie: 以降を貼り付ける
            """
        ).strip()
    )


def command_login(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    if args.manual and not args.no_open:
        print(f"{GAME_NAME} のチェックインページを開きます:")
        print(EVENT_URL)
        webbrowser.open(EVENT_URL)

    if args.manual:
        print_manual_cookie_help()

    cookie = get_cookie(args, path)
    if not looks_authenticated(cookie):
        print(
            "警告: ltoken_v2/ltuid_v2 などの認証 Cookie が見つかりません。"
            "保存は続行しますが、チェックイン時にログインエラーになる可能性があります。",
            file=sys.stderr,
        )

    save_config(path, cookie)
    print(f"ログイン情報を保存しました: {path}")

    if args.check:
        return command_status(argparse.Namespace(config=str(path), json=False))
    return 0


def load_client(args: argparse.Namespace) -> HoyoLabClient:
    config = load_config(Path(args.config).expanduser())
    cookie = normalize_cookie(str(config.get("cookie", "")))
    return HoyoLabClient(cookie)


def command_status(args: argparse.Namespace) -> int:
    client = load_client(args)
    info = client.info()
    if args.json:
        payload = {"retcode": info.retcode, "message": info.message, "data": info.data}
        print(json.dumps(payload, ensure_ascii=False))
        return 0 if info.retcode == 0 else 1

    if info.retcode != 0:
        print(f"状態確認に失敗しました: retcode={info.retcode} message={info.message}")
        return 1

    is_sign = bool(info.data.get("is_sign"))
    total = info.data.get("total_sign_day")
    today = info.data.get("today")
    print(f"ゲーム: {GAME_NAME}")
    print(f"今日: {today}")
    print(f"今月のチェックイン日数: {total}")
    print(f"本日の受け取り: {'済み' if is_sign else '未受け取り'}")
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
        print(f"状態確認に失敗しました: retcode={info.retcode} message={info.message}")
        return 1

    if info.data.get("first_bind"):
        print("HoYoLAB 側で初回連携が必要です。ブラウザーで一度手動チェックインしてください。")
        return 1

    total_sign_day = info.data.get("total_sign_day")
    if isinstance(total_sign_day, int):
        reward = today_reward(client, total_sign_day)
    else:
        reward = None

    if info.data.get("is_sign"):
        print(f"{GAME_NAME}: 本日はすでに受け取り済みです。")
        return 0

    result = client.sign()
    if result.retcode == 0:
        if reward:
            print(f"{GAME_NAME}: ログインボーナスを受け取りました ({reward})。")
        else:
            print(f"{GAME_NAME}: ログインボーナスを受け取りました。")
        return 0

    already_signed = (
        result.retcode == -5003
        or "already" in result.message.lower()
        or "already" in str(result.data).lower()
    )
    if already_signed:
        print(f"{GAME_NAME}: 本日はすでに受け取り済みです。")
        return 0

    gt_result = result.data.get("gt_result")
    if isinstance(gt_result, dict) and gt_result.get("is_risk"):
        print("HoYoLAB の CAPTCHA / リスク判定で自動受け取りに失敗しました。ブラウザーで手動確認してください。")
        return 2

    print(f"受け取りに失敗しました: retcode={result.retcode} message={result.message}")
    return 1


def command_logout(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    if path.exists():
        path.unlink()
        print(f"ログイン情報を削除しました: {path}")
    else:
        print(f"ログイン情報はありません: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{GAME_NAME}の HoYoLAB Web版デイリーログインボーナスを受け取ります。",
    )
    parser.add_argument(
        "--config",
        default=str(default_config_path()),
        help="Cookie を保存する設定ファイルパス。既定値: %(default)s",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    login = subparsers.add_parser("login", help="HoYoLAB Cookie を保存します。")
    login.add_argument("--cookie", help="Cookie ヘッダーを直接渡します。シェル履歴に残る点に注意してください。")
    login.add_argument("--cookie-file", help="Cookie ヘッダーを書いたテキストファイルを読み込みます。")
    login.add_argument("--manual", action="store_true", help="ブラウザーから自動取得せず、Cookie ヘッダーを手入力します。")
    login.add_argument("--no-open", action="store_true", help="ブラウザーを自動で開きません。手入力時に使います。")
    login.add_argument(
        "--browser",
        choices=BROWSER_CHOICES,
        default=BROWSER_AUTO,
        help="自動取得に使うブラウザー。auto は Chromium 系を優先し、macOS では Safari も候補にします。既定値: %(default)s",
    )
    login.add_argument(
        "--browser-command",
        help="自動取得に使う Chrome / Chromium 系ブラウザーの実行ファイルパスまたはコマンド名。",
    )
    login.add_argument(
        "--safaridriver-command",
        help="Safari 自動取得に使う safaridriver の実行ファイルパスまたはコマンド名。",
    )
    login.add_argument(
        "--profile-dir",
        help="自動取得用ブラウザープロファイルの保存先。既定では設定ファイル横の browser-profile を使います。",
    )
    login.add_argument("--debug-port", type=int, help="DevTools / WebDriver 用ポート。通常は自動割り当てします。")
    login.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_BROWSER_TIMEOUT,
        help="ブラウザーから Cookie を自動取得するまで待つ秒数。既定値: %(default)s",
    )
    login.add_argument("--close-browser", action="store_true", help="Cookie 取得後に自動取得用ブラウザーを閉じます。")
    login.add_argument("--check", action="store_true", help="保存後にログイン状態を確認します。")
    login.set_defaults(func=command_login)

    claim = subparsers.add_parser("claim", help="本日のログインボーナスを受け取ります。")
    claim.set_defaults(func=command_claim)

    status = subparsers.add_parser("status", help="本日の受け取り状態を確認します。")
    status.add_argument("--json", action="store_true", help="HoYoLAB API の状態応答を JSON で表示します。")
    status.set_defaults(func=command_status)

    logout = subparsers.add_parser("logout", help="保存済み Cookie を削除します。")
    logout.set_defaults(func=command_logout)

    parser.set_defaults(func=command_claim)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except HsrLoginError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n中断しました。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
