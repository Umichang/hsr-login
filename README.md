# hsr-login
崩壊：スターレイルのWebログインボーナスを取得するCLIコマンドです。

HoYoLAB の Web 版デイリーチェックインのうち、ゲーム名が「崩壊：スターレイル」のものだけを対象にします。原神やゼンレスゾーンゼロのチェックイン API は呼びません。

## 使い方

初回だけ HoYoLAB のログイン Cookie を保存します。

```bash
python hsr_login.py login --check
```

コマンドを実行すると「崩壊：スターレイル」のチェックインページを開きます。HoYoLAB にログインした状態で、ブラウザーの開発者ツールから Request Headers の `Cookie:` 以降を貼り付けてください。

保存後は次のコマンドで本日のログインボーナスを受け取れます。

```bash
python hsr_login.py claim
```

サブコマンドを省略した場合も `claim` として動作します。

```bash
python hsr_login.py
```

受け取り状態だけを確認する場合は次を使います。

```bash
python hsr_login.py status
```

保存した Cookie を削除する場合は次を使います。

```bash
python hsr_login.py logout
```

## Cookie の保存先

既定では次の場所に保存します。

```text
~/.config/hsr-login/config.json
```

保存ファイルは可能な環境では `0600` にします。保存先を変える場合は `--config` または `HSR_LOGIN_CONFIG` を使ってください。

```bash
python hsr_login.py --config ~/.config/hsr-login/main.json login
HSR_LOGIN_CONFIG=~/.config/hsr-login/main.json python hsr_login.py claim
```

Cookie はログイン情報そのものです。共有リポジトリへコミットしたり、チャットやログへ貼り付けたりしないでください。

## 対象ページ

このスクリプトは HoYoLAB の「崩壊：スターレイル」チェックインページで使われている `hkrpg` 用の `act_id=e202303301540311` を使います。

```text
https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311
```

HoYoLAB 側の CAPTCHA / リスク判定が出た場合は、CLI では受け取りに失敗します。その場合はブラウザーで手動確認してください。
