# hsr-login
崩壊：スターレイルのWebログインボーナスを取得するCLIコマンドです。

HoYoLAB の Web 版デイリーチェックインのうち、ゲーム名が「崩壊：スターレイル」のものだけを対象にします。原神やゼンレスゾーンゼロのチェックイン API は呼びません。

## インストール

ローカル環境にコマンドとしてインストールできます。

```bash
python3 -m pip install --user .
```

開発中の作業ディレクトリをそのまま使う場合は editable install が便利です。

```bash
python3 -m pip install --user -e .
```

インストール後は `hsr-login` コマンドで実行します。

```bash
hsr-login --help
```

`--user` で入れたコマンドが見つからない場合は、Python の user base の `bin` ディレクトリを `PATH` に追加してください。

```bash
python3 -m site --user-base
```

表示されたパスの末尾に `/bin` を付けた場所がコマンドのインストール先です。たとえば macOS や Linux では `~/.local/bin` になることがあります。

## 使い方

初回だけ HoYoLAB のログイン Cookie を保存します。

```bash
hsr-login login --check
```

コマンドを実行すると、自動取得用の Chrome / Chromium 系ブラウザーで「崩壊：スターレイル」のチェックインページを開きます。HoYoLAB にログインすると、CLI がブラウザー内の Cookie を検出して保存します。Chrome / Chromium / Edge / Brave / Comet / Arc などを順に探します。

Chrome が自動検出できない場合は、実行ファイルを指定できます。

```bash
hsr-login login --browser-command "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --check
```

自動取得を使わず、従来どおり開発者ツールから Request Headers の `Cookie:` 以降を貼り付ける場合は `--manual` を使います。

```bash
hsr-login login --manual --check
```

保存後は次のコマンドで本日のログインボーナスを受け取れます。

```bash
hsr-login claim
```

サブコマンドを省略した場合も `claim` として動作します。

```bash
hsr-login
```

受け取り状態だけを確認する場合は次を使います。

```bash
hsr-login status
```

保存した Cookie を削除する場合は次を使います。

```bash
hsr-login logout
```

## Cookie の保存先

既定では次の場所に保存します。

```text
~/.config/hsr-login/config.json
```

保存ファイルは可能な環境では `0600` にします。自動取得用ブラウザーのプロファイルは既定では設定ファイル横の `browser-profile` に保存します。このプロファイルにもログイン情報が含まれるため、共有やコミットはしないでください。

保存先を変える場合は `--config` または `HSR_LOGIN_CONFIG` を使ってください。

```bash
hsr-login --config ~/.config/hsr-login/main.json login
HSR_LOGIN_CONFIG=~/.config/hsr-login/main.json hsr-login claim
```

Cookie はログイン情報そのものです。共有リポジトリへコミットしたり、チャットやログへ貼り付けたりしないでください。

## 対象ページ

このスクリプトは HoYoLAB の「崩壊：スターレイル」チェックインページで使われている `hkrpg` 用の `act_id=e202303301540311` を使います。

```text
https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311
```

HoYoLAB 側の CAPTCHA / リスク判定が出た場合は、CLI では受け取りに失敗します。その場合はブラウザーで手動確認してください。
