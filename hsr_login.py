#!/usr/bin/env python3
"""Claim HoYoLAB daily check-in rewards for Honkai: Star Rail."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


class HsrLoginError(RuntimeError):
    """A recoverable CLI error."""


@dataclass(frozen=True)
class ApiResult:
    retcode: int
    message: str
    data: dict[str, Any]


def default_config_path() -> Path:
    if value := os.environ.get("HSR_LOGIN_CONFIG"):
        return Path(value).expanduser()
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


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HsrLoginError(
            f"ログイン情報が未保存です。先に `python {Path(__file__).name} login` を実行してください。"
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


def get_cookie(args: argparse.Namespace) -> str:
    if args.cookie:
        return normalize_cookie(args.cookie)
    if args.cookie_file:
        return normalize_cookie(Path(args.cookie_file).expanduser().read_text(encoding="utf-8"))
    return normalize_cookie(getpass.getpass("HoYoLAB の Cookie ヘッダーを貼り付けてください: "))


def command_login(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    if not args.no_open:
        print(f"{GAME_NAME} のチェックインページを開きます:")
        print(EVENT_URL)
        webbrowser.open(EVENT_URL)

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

    cookie = get_cookie(args)
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

    subparsers = parser.add_subparsers(dest="command")

    login = subparsers.add_parser("login", help="HoYoLAB Cookie を保存します。")
    login.add_argument("--cookie", help="Cookie ヘッダーを直接渡します。シェル履歴に残る点に注意してください。")
    login.add_argument("--cookie-file", help="Cookie ヘッダーを書いたテキストファイルを読み込みます。")
    login.add_argument("--no-open", action="store_true", help="ブラウザーを自動で開きません。")
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
