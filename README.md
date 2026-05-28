# hsr-login
崩壊：スターレイルのWebログインボーナスを取得するCLIコマンドです。

現在のバージョンは `0.3.1` です。

HoYoLAB の Web 版デイリーチェックインのうち、ゲーム名が「崩壊：スターレイル」のものだけを対象にします。原神やゼンレスゾーンゼロのチェックイン API は呼びません。

## クイックインストール

macOS / Linux:

```bash
pipx install hsr-login
```

Windows PowerShell:

```powershell
pipx install hsr-login
```

インストール後は `hsr-login` コマンドで実行します。

`pipx` を使うと、専用の仮想環境に PyPI 版の `hsr-login` を入れ、コマンドだけを普段の `PATH` から呼び出せます。`hsr-login` コマンドが見つからない場合は、[PATH の設定](#path-の設定)を確認してください。

## 使い方

初回だけ HoYoLAB のログイン Cookie を保存します。

```bash
hsr-login login --check
```

`hsr-login login --check` では、自動取得用のブラウザーで「崩壊：スターレイル」のチェックインページを開きます。HoYoLAB にログインすると、CLI がブラウザー内の Cookie を検出して保存します。

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

## ログインのオプション

### ブラウザー自動取得

既定では `--browser auto` として動作します。Chrome / Chromium / Edge / Brave / Comet / Arc などの Chromium 系ブラウザーを順に探し、macOS では Chromium 系ブラウザーが見つからない場合に Safari も候補にします。

Chromium 系ブラウザーを明示する場合は `--browser chromium` を指定します。

```bash
hsr-login login --browser chromium --check
```

Chrome が自動検出できない場合は、実行ファイルを指定できます。

macOS:

```bash
hsr-login login --browser-command "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --check
```

Windows PowerShell:

```powershell
hsr-login login --browser-command "C:\Program Files\Google\Chrome\Application\chrome.exe" --check
```

Safari を明示して使う場合は `--browser safari` を指定します。

```bash
hsr-login login --browser safari --check
```

Safari 自動取得は macOS の `safaridriver` を使います。初回は Safari の開発メニューで「リモートオートメーションを許可」を有効にするか、次を実行してください。

```bash
safaridriver --enable
```

Safari WebDriver は通常の Safari プロファイルではなく隔離された自動化ウィンドウを使うため、普段使いの Safari に保存済みの Cookie は読み取りません。表示された Safari ウィンドウで HoYoLAB にログインしてください。

`safaridriver` の場所を明示する場合は `--safaridriver-command` を使います。

```bash
hsr-login login --browser safari --safaridriver-command /usr/bin/safaridriver --check
```

### 手動入力

自動取得を使わず、従来どおり開発者ツールから Request Headers の `Cookie:` 以降を貼り付ける場合は `--manual` を使います。

```bash
hsr-login login --manual --check
```

## インストール詳細

Homebrew 版 Python など PEP 668 に対応した環境では、グローバルな `python3 -m pip install --user ...` が `externally-managed-environment` で失敗することがあります。CLI として使う場合は、専用 venv を自動で管理する `pipx` を推奨します。

### PyPI からインストールする

PyPI に公開済みのリリースは、次のコマンドでインストールできます。

```bash
pipx install hsr-login
```

更新する場合は次を使います。

```bash
pipx upgrade hsr-login
```

すでに自分で作った venv の中に入れる場合は、通常の `pip install` も使えます。

```bash
python -m pip install hsr-login
```

### ローカルリポジトリからインストールする

未公開の開発版をこのリポジトリから入れる場合は、専用 venv に `pip install` して `hsr-login` コマンドだけを呼べるようにするローカルインストーラを使えます。

macOS / Linux:

```bash
./scripts/install-local.sh
```

Windows PowerShell:

```powershell
.\scripts\install-local.ps1
```

インストール後は `hsr-login` コマンドで実行します。

```console
hsr-login --help
```

バージョンを確認する場合は次を使います。

```console
hsr-login --version
```

### PATH の設定

`hsr-login` コマンドが見つからない場合は、macOS / Linux では `~/.local/bin`、Windows では `$HOME\.local\bin` を `PATH` に追加してください。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

PowerShell では次のように追加できます。

```powershell
$env:Path = "$HOME\.local\bin;$env:Path"
```

### インストール先を変える

インストール先を変えたい場合は、次の環境変数を使えます。

```bash
HSR_LOGIN_VENV_DIR=~/.venvs/hsr-login HSR_LOGIN_BIN_DIR=~/bin ./scripts/install-local.sh
```

PowerShell:

```powershell
$env:HSR_LOGIN_VENV_DIR = "$HOME\.venvs\hsr-login"
$env:HSR_LOGIN_BIN_DIR = "$HOME\bin"
.\scripts\install-local.ps1
```

### 既存の venv を使う

すでに venv を使っている場合は、その venv の中で通常の `pip install` も使えます。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/hsr-login --help
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\hsr-login.exe --help
```

この venv 直下のインストールでは、Python の console script として `.\.venv\Scripts\hsr-login.exe` が作成されます。上の `install-local.ps1` が `$HOME\.local\bin` に作成する `hsr-login.cmd` とは別です。

### pipx でローカル版を使う

`pipx` でも、ローカルリポジトリから開発版を CLI としてインストールできます。

```bash
pipx install .
```

### Windows の実行ファイル名

Windows PowerShell 版のインストーラは、既定では `$HOME\.local\bin` に `hsr-login.cmd` と `hsr-login.ps1` を作成し、内部から専用 venv の `Scripts\hsr-login.exe` を呼びます。

対話的に実行する場合は、`$HOME\.local\bin` を `PATH` に追加しておけば `hsr-login` と入力できます。タスク スケジューラなどで実行ファイルのフルパスを指定する場合は、`hsr-login.cmd` を指定してください。

## PyPI 公開手順

このリポジトリは `pyproject.toml` の `project.scripts` で `hsr-login = "hsr_login:main"` を公開します。wheel / sdist を作る場合は次を実行します。

```bash
python -m pip install --upgrade build
python -m build
```

公開は GitHub Actions の `Publish to PyPI` ワークフローを使います。PyPI 側で `Umichang/hsr-login` に対する Trusted Publishing を設定してから、GitHub Release を publish するか、手動で workflow dispatch を実行してください。

リリース前には、`hsr_login.py` の `__version__`、README 冒頭の現在バージョン、GitHub Release のタグを同じバージョンにそろえてください。

## Cookie の保存先

既定では次の場所に保存します。

```text
~/.config/hsr-login/config.json
```

Windows では次の場所です。

```text
%APPDATA%\hsr-login\config.json
```

保存ファイルは可能な環境では `0600` にします。Chromium 系ブラウザーの自動取得用プロファイルは、既定では設定ファイル横の `browser-profile` に保存します。このプロファイルにもログイン情報が含まれるため、共有やコミットはしないでください。

Safari 自動取得では `browser-profile` は使いません。Safari WebDriver の隔離された自動化セッションでログインし、そのセッションから Cookie を取得します。

保存先を変える場合は `--config` または `HSR_LOGIN_CONFIG` を使ってください。

```bash
hsr-login --config ~/.config/hsr-login/main.json login
HSR_LOGIN_CONFIG=~/.config/hsr-login/main.json hsr-login claim
```

PowerShell:

```powershell
hsr-login --config "$env:APPDATA\hsr-login\main.json" login
$env:HSR_LOGIN_CONFIG = "$env:APPDATA\hsr-login\main.json"
hsr-login claim
```

Cookie はログイン情報そのものです。共有リポジトリへコミットしたり、チャットやログへ貼り付けたりしないでください。

## 定時実行

`hsr-login login --check` で Cookie を保存したあとは、`hsr-login claim` を定時実行できます。

macOS / Linux では cron を使えます。まず `hsr-login` の実行ファイルの場所を確認します。

```bash
which hsr-login
```

`crontab -e` で cron の設定を開き、たとえば毎日 5:10 に実行する場合は次のように追加します。cron は通常のシェルより `PATH` が短いため、`hsr-login` はフルパスで指定してください。

```cron
10 5 * * * /Users/yourname/.local/bin/hsr-login claim >> /Users/yourname/.local/state/hsr-login.log 2>&1
```

設定ファイルの場所を明示したい場合は、`HSR_LOGIN_CONFIG` を同じ行で指定できます。

```cron
10 5 * * * HSR_LOGIN_CONFIG=/Users/yourname/.config/hsr-login/config.json /Users/yourname/.local/bin/hsr-login claim >> /Users/yourname/.local/state/hsr-login.log 2>&1
```

Windows では cron の代わりに「タスク スケジューラ」を使えます。操作画面から登録する場合は、毎日実行するトリガーを作り、操作として `hsr-login.cmd` のフルパスと `claim` 引数を指定してください。

PowerShell から登録する場合は、次のようにタスクを作成できます。

```powershell
$action = New-ScheduledTaskAction -Execute "$HOME\.local\bin\hsr-login.cmd" -Argument "claim"
$trigger = New-ScheduledTaskTrigger -Daily -At 5:10
Register-ScheduledTask -TaskName "hsr-login claim" -Action $action -Trigger $trigger
```

`HSR_LOGIN_CONFIG` を使う場合は、PowerShell 経由で環境変数を指定してから実行します。

```powershell
$command = "`$env:HSR_LOGIN_CONFIG = '$env:APPDATA\hsr-login\config.json'; & '$HOME\.local\bin\hsr-login.cmd' claim"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -Command `"$command`""
$trigger = New-ScheduledTaskTrigger -Daily -At 5:10
Register-ScheduledTask -TaskName "hsr-login claim" -Action $action -Trigger $trigger
```

## 対象ページ

このスクリプトは HoYoLAB の「崩壊：スターレイル」チェックインページで使われている `hkrpg` 用の `act_id=e202303301540311` を使います。

```text
https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311
```

HoYoLAB 側の CAPTCHA / リスク判定が出た場合は、CLI では受け取りに失敗します。その場合はブラウザーで手動確認してください。

## FAQ

Q. なぜ原神やゼンレスゾーンゼロには対応していないの？

A. どちらも作者が引退状態で、不具合が出た際に即座に対応できないからです。仕組みとしては同じなので、どなたか面倒を見てくださる方がいればワンチャンはあります。自分からはやりません。
