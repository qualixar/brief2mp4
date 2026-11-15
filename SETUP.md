# SETUP.md: instructions for the agent

You are Claude Code or Codex, and the user asked you to set up brief2mp4 on this machine. Follow these steps in order. Ask before installing anything system-wide, show each command before you run it, and stop on the first step you cannot finish, saying exactly what failed.

The user can start this with one message:

> Set up brief2mp4 from https://github.com/qualixar/brief2mp4 by following its SETUP.md.

## Step 1. Find out where you are

Run the probe for the shell you have and note the answers.

macOS, Linux, WSL, Git Bash:

```bash
uname -s; uname -m
for t in git node npm ffmpeg ffprobe python3 blender; do printf '%-8s ' "$t"; command -v "$t" || echo missing; done
node -v 2>/dev/null; ffmpeg -version 2>/dev/null | head -1; python3 --version 2>/dev/null
```

Windows PowerShell:

```powershell
$PSVersionTable.PSVersion; [System.Environment]::Is64BitOperatingSystem
foreach ($t in 'git','node','npm','ffmpeg','ffprobe','python','py','blender','winget') { $c = Get-Command $t -ErrorAction SilentlyContinue; "{0,-8} {1}" -f $t, $(if ($c) { $c.Source } else { 'missing' }) }
```

Decide the operating system: `Darwin` is macOS, `Linux` is Linux (WSL counts as Linux), PowerShell or `MINGW`/`MSYS` in `uname -s` is Windows.

## Step 2. Install what is missing

Required for every brief: **Node.js 22 or newer**, **ffmpeg** (with ffprobe) and **git**. On Windows also **Git for Windows**, because the skill's scripts are bash and Git Bash runs them. Optional: **Blender** (4.2 or newer, tested with 5.2) for realistic product shots, and **Python 3.12 or 3.13** for the 3D pack (its pinned numpy and scipy need 3.12+).

Ask the user once, listing only what is missing, then run the matching commands.

| Tool | macOS (Homebrew) | Windows (winget) | Ubuntu / Debian |
|---|---|---|---|
| Node.js 22+ | `brew install node` | `winget install -e --id OpenJS.NodeJS.LTS` | `curl -fsSL https://deb.nodesource.com/setup_22.x \| sudo -E bash - && sudo apt install -y nodejs` |
| ffmpeg | `brew install ffmpeg` | `winget install -e --id Gyan.FFmpeg` | `sudo apt install -y ffmpeg` |
| git / Git Bash | `xcode-select --install` | `winget install -e --id Git.Git` | `sudo apt install -y git` |
| Blender (optional) | `brew install --cask blender` | `winget install -e --id BlenderFoundation.Blender` | download from https://www.blender.org/download (the apt version is often old) |
| Python 3.12 (3D pack) | `brew install python@3.12` | `winget install -e --id Python.Python.3.12` | Ubuntu 24.04: `sudo apt install -y python3 python3-venv`; Debian 12 ships 3.11: `uv python install 3.12`, then run the 3D install with `B2M3D_PYTHON="$(uv python find 3.12)"` |

Notes:

- No Homebrew on macOS? It is at https://brew.sh. Ask before installing it.
- After a winget install on Windows, open a **new** terminal (or restart the agent session) so the PATH updates. If `ffmpeg` is still not found, it sits under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\...\bin`; add that folder to the user PATH.
- On macOS Blender is often not on the PATH: use `/Applications/Blender.app/Contents/MacOS/Blender`. On Windows it is under `C:\Program Files\Blender Foundation\Blender <version>\blender.exe`.
- Never use `sudo npm install -g`. HyperFrames runs through `npx`, so no global npm installs are needed.

## Step 3. Get the repo and install the skill

```bash
git clone https://github.com/qualixar/brief2mp4.git
cd brief2mp4
```

macOS, Linux, WSL, Git Bash:

```bash
bash install.sh                      # Claude Code and Codex
bash install.sh --with-3d            # also the 3D pack (core components)
bash install.sh --with-3d=core,cad   # 3D pack with the CadQuery modeller (about 1.3 GB more)
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -With3D core,cad
```

Install the 3D pack only when the user wants 3D products, physics, exploded views or turntables. Everything else works without it. The pack is described in `plugin/skills/brief2mp4/3d/README-3D.md`.

Install the edit pack when the user edits real footage or recordings, mixes voice-over with music, or wants thumbnails and lower thirds made by the agent: `bash install.sh --with-edit` (FilmCraft and SoundCraft; `--with-edit=film,sound,effect,photo,vector` for all five) or `install.ps1 -WithEdit film,sound`. It downloads the free ArtCraft editors' command-line tools from their GitHub releases and checks each file's SHA-256 (against the release and against a hash pinned in this repository) before unpacking; when gpg is installed it also verifies the release signature. Details: `plugin/skills/brief2mp4/edit/README-EDIT.md`.

The user may prefer the plugin route instead of the script. Then they run, inside Claude Code: `/plugin marketplace add qualixar/brief2mp4` and `/plugin install brief2mp4@brief2mp4`; in a terminal for Codex: `codex plugin marketplace add qualixar/brief2mp4` and `codex plugin add brief2mp4@brief2mp4`. Plugins do not install system tools, so Step 2 still applies.

## Step 4. Check the machine

```bash
bash plugin/skills/brief2mp4/scripts/doctor.sh
```

On Windows run the same line from Git Bash, or from PowerShell as `& "C:\Program Files\Git\bin\bash.exe" plugin/skills/brief2mp4/scripts/doctor.sh`. Every required line must say `ok`. Fix any `missing` line with the command it prints and run the doctor again.

## Step 5. Prove it works: the two-minute first render

Make an empty folder outside the repo, copy `examples/01-kinetic-type/BRIEF.md` into it, and in that folder follow the skill: spec, build, self-check, deliver. A working setup produces `final.mp4` (12.000 s, 1920x1080, 30 fps) and `check_delivery.sh` ends with `RESULT: PASS`. If the 3D pack was installed, also run `examples/04-3d-product/BRIEF.md`.

## Step 6. Tell the user

Report in five lines or fewer: the OS, what you installed, the doctor result, the path of the first `final.mp4` with its duration, and the next thing to try:

> Start a new session, then send: Use the brief2mp4 skill to make the video in this brief: (paste your brief)

A new session is needed because the apps load skills at session start.
