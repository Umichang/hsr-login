# hsr-login

[English](README.md) | [日本語](README-ja.md)

A CLI command for claiming Honkai: Star Rail web login bonus rewards.

Current version: `0.3.1`.

This command targets only the HoYoLAB web daily check-in whose game name is Honkai: Star Rail. It does not call the check-in APIs for Genshin Impact or Zenless Zone Zero.

## Quick Install

macOS / Linux:

```bash
pipx install hsr-login
```

Windows PowerShell:

```powershell
pipx install hsr-login
```

After installation, run it with the `hsr-login` command.

`pipx` installs the PyPI release of `hsr-login` into a dedicated virtual environment and exposes only the command on your normal `PATH`. If the `hsr-login` command is not found, check [PATH Setup](#path-setup).

## Usage

Save your HoYoLAB login Cookie once.

```bash
hsr-login login --check
```

`hsr-login login --check` opens the Honkai: Star Rail check-in page in a browser used for automatic capture. After you log in to HoYoLAB, the CLI detects and saves the Cookie from that browser.

After that, claim today's login bonus with:

```bash
hsr-login claim
```

If you omit the subcommand, `hsr-login` also runs `claim`.

```bash
hsr-login
```

To check only today's claim status, use:

```bash
hsr-login status
```

To delete the saved Cookie, use:

```bash
hsr-login logout
```

## Display Language

CLI output is shown in Japanese for Japanese environments and English for non-Japanese environments.

The language is not detected from the terminal locale. Instead, the command first uses the saved HoYoLAB Cookie's `mi18nLang`. `mi18nLang=ja-jp` selects Japanese; other languages select English. The HoYoLAB API `lang` parameter follows the same rule.

If login information has already been saved, the command uses `ui_language` / `lang` in the config file. Before the first login, when HoYoLAB language information is not available yet, it uses the OS display language where possible. If that is also unavailable, it falls back to English.

## Login Options

### Automatic Browser Capture

By default, login uses `--browser auto`. It looks for Chromium-family browsers such as Chrome, Chromium, Edge, Brave, Comet, and Arc. On macOS, if no Chromium-family browser is found, Safari is also considered.

To explicitly use a Chromium-family browser, pass `--browser chromium`.

```bash
hsr-login login --browser chromium --check
```

If Chrome is not detected automatically, you can specify the executable.

macOS:

```bash
hsr-login login --browser-command "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --check
```

Windows PowerShell:

```powershell
hsr-login login --browser-command "C:\Program Files\Google\Chrome\Application\chrome.exe" --check
```

To explicitly use Safari, pass `--browser safari`.

```bash
hsr-login login --browser safari --check
```

Safari automatic capture uses macOS `safaridriver`. On first use, enable "Allow Remote Automation" in Safari's Develop menu or run:

```bash
safaridriver --enable
```

Safari WebDriver uses an isolated automation window rather than your normal Safari profile, so it does not read Cookies already saved in your everyday Safari session. Log in to HoYoLAB in the Safari window that appears.

To specify the `safaridriver` location, use `--safaridriver-command`.

```bash
hsr-login login --browser safari --safaridriver-command /usr/bin/safaridriver --check
```

### Manual Entry

To skip automatic capture and paste the value after `Cookie:` from Request Headers in browser developer tools, use `--manual`.

```bash
hsr-login login --manual --check
```

## Installation Details

On PEP 668-aware environments such as Homebrew Python, global `python3 -m pip install --user ...` can fail with `externally-managed-environment`. For CLI use, `pipx` is recommended because it manages a dedicated venv automatically.

### Install From PyPI

Install the published PyPI release with:

```bash
pipx install hsr-login
```

To upgrade:

```bash
pipx upgrade hsr-login
```

If you already have your own venv, regular `pip install` also works.

```bash
python -m pip install hsr-login
```

### Install From a Local Checkout

To install an unpublished development version from this repository, you can use the local installer. It installs into a dedicated venv and exposes only the `hsr-login` command.

macOS / Linux:

```bash
./scripts/install-local.sh
```

Windows PowerShell:

```powershell
.\scripts\install-local.ps1
```

After installation, run it with the `hsr-login` command.

```console
hsr-login --help
```

To check the version:

```console
hsr-login --version
```

### PATH Setup

If the `hsr-login` command is not found, add `~/.local/bin` on macOS / Linux, or `$HOME\.local\bin` on Windows, to your `PATH`.

```bash
export PATH="$HOME/.local/bin:$PATH"
```

In PowerShell:

```powershell
$env:Path = "$HOME\.local\bin;$env:Path"
```

### Change Install Location

Use these environment variables to change the install location.

```bash
HSR_LOGIN_VENV_DIR=~/.venvs/hsr-login HSR_LOGIN_BIN_DIR=~/bin ./scripts/install-local.sh
```

PowerShell:

```powershell
$env:HSR_LOGIN_VENV_DIR = "$HOME\.venvs\hsr-login"
$env:HSR_LOGIN_BIN_DIR = "$HOME\bin"
.\scripts\install-local.ps1
```

### Use an Existing venv

If you already use a venv, you can install with regular `pip install` inside it.

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

This direct venv installation creates `.\.venv\Scripts\hsr-login.exe` as a Python console script. That is separate from the `hsr-login.cmd` shim created in `$HOME\.local\bin` by `install-local.ps1`.

### Use the Local Version With pipx

`pipx` can also install the development version from a local checkout as a CLI.

```bash
pipx install .
```

### Windows Executable Names

The Windows PowerShell installer creates `hsr-login.cmd` and `hsr-login.ps1` in `$HOME\.local\bin` by default, and internally calls the dedicated venv's `Scripts\hsr-login.exe`.

For interactive use, adding `$HOME\.local\bin` to `PATH` lets you type `hsr-login`. If you need a full executable path, such as in Task Scheduler, point it to `hsr-login.cmd`.

## PyPI Publishing

This repository exposes `hsr-login = "hsr_login:main"` through `project.scripts` in `pyproject.toml`. To build a wheel / sdist, run:

```bash
python -m pip install --upgrade build
python -m build
```

Publishing uses the GitHub Actions `Publish to PyPI` workflow. Configure Trusted Publishing on PyPI for `Umichang/hsr-login`, then publish a GitHub Release or run the workflow manually with workflow dispatch.

Before release, keep `__version__` in `hsr_login.py`, the current version at the top of the README, and the GitHub Release tag aligned.

## Cookie Storage

By default, the Cookie is saved at:

```text
~/.config/hsr-login/config.json
```

On Windows:

```text
%APPDATA%\hsr-login\config.json
```

Where possible, the saved file is set to `0600`. The automatic capture profile for Chromium-family browsers is stored in `browser-profile` next to the config file by default. This profile also contains login information, so do not share or commit it.

The config file also stores `lang` for the HoYoLAB API and `ui_language` for CLI output. Normally these are derived automatically from the HoYoLAB Cookie's `mi18nLang` captured at login.

Safari automatic capture does not use `browser-profile`. It logs in through an isolated Safari WebDriver automation session and reads Cookies from that session.

To change the storage path, use `--config` or `HSR_LOGIN_CONFIG`.

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

The Cookie is login information. Do not commit it to shared repositories or paste it into chats or logs.

## Scheduled Execution

After saving the Cookie with `hsr-login login --check`, you can run `hsr-login claim` on a schedule.

On macOS / Linux, you can use cron. First check where the `hsr-login` executable is located.

```bash
which hsr-login
```

Open your cron settings with `crontab -e`. For example, to run it every day at 5:10, add the following line. cron usually has a shorter `PATH` than your normal shell, so specify the full path to `hsr-login`.

```cron
10 5 * * * /Users/yourname/.local/bin/hsr-login claim >> /Users/yourname/.local/state/hsr-login.log 2>&1
```

If you want to specify the config file location, set `HSR_LOGIN_CONFIG` on the same line.

```cron
10 5 * * * HSR_LOGIN_CONFIG=/Users/yourname/.config/hsr-login/config.json /Users/yourname/.local/bin/hsr-login claim >> /Users/yourname/.local/state/hsr-login.log 2>&1
```

On Windows, use Task Scheduler instead of cron. In the GUI, create a daily trigger and set the action to the full path of `hsr-login.cmd` with the `claim` argument.

You can also create the task from PowerShell:

```powershell
$action = New-ScheduledTaskAction -Execute "$HOME\.local\bin\hsr-login.cmd" -Argument "claim"
$trigger = New-ScheduledTaskTrigger -Daily -At 5:10
Register-ScheduledTask -TaskName "hsr-login claim" -Action $action -Trigger $trigger
```

When using `HSR_LOGIN_CONFIG`, run through PowerShell so the environment variable is set before execution.

```powershell
$command = "`$env:HSR_LOGIN_CONFIG = '$env:APPDATA\hsr-login\config.json'; & '$HOME\.local\bin\hsr-login.cmd' claim"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -Command `"$command`""
$trigger = New-ScheduledTaskTrigger -Daily -At 5:10
Register-ScheduledTask -TaskName "hsr-login claim" -Action $action -Trigger $trigger
```

## Target Page

This script uses the `hkrpg` `act_id=e202303301540311` used by the HoYoLAB Honkai: Star Rail check-in page.

```text
https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311
```

If HoYoLAB shows CAPTCHA / risk verification, the CLI claim will fail. In that case, confirm manually in the browser.

## FAQ

Q. Why does this not support Genshin Impact or Zenless Zone Zero?

A. The author no longer actively plays either game and cannot respond quickly if something breaks. The mechanism is similar, so someone else could maintain that support, but this project will not add it proactively.
