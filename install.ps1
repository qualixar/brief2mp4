# Install the brief2mp4 skill for Claude Code and Codex on Windows (PowerShell 5.1 or 7).
#
#   powershell -ExecutionPolicy Bypass -File .\install.ps1                  # both apps
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Claude          # Claude Code only
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Codex           # Codex only
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -InstallTools    # also winget-install Node, ffmpeg, Git
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -With3D core,cad # also the optional 3D pack
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithEdit film,sound # also the optional edit pack
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Uninstall
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Uninstall -Uninstall3D -UninstallEdit   # also remove the optional packs
#
# Claude Code reads skills from %USERPROFILE%\.claude\skills (or $env:CLAUDE_CONFIG_DIR\skills).
# Codex reads skills from %USERPROFILE%\.codex\skills (or $env:CODEX_HOME\skills).
param(
  [switch]$Claude,
  [switch]$Codex,
  [switch]$Uninstall,
  [switch]$InstallTools,
  [switch]$Uninstall3D,
  [switch]$UninstallEdit,
  [string[]]$WithEdit = @(),
  [string[]]$With3D = @()
)
$ErrorActionPreference = 'Stop'

$Name = 'brief2mp4'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src = Join-Path $Here "plugin\skills\$Name"
$VersionFile = Join-Path $Here 'VERSION'
$Version = if (Test-Path $VersionFile) { (Get-Content $VersionFile -Raw).Trim() } else { 'dev' }
$ClaudeBase = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
$CodexBase = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$DoClaude = -not $Codex -or $Claude
$DoCodex = -not $Claude -or $Codex
$Marker = ".installed-by-$Name"

if (-not (Test-Path (Join-Path $Src 'SKILL.md'))) {
  Write-Error "install.ps1: cannot find $Src\SKILL.md (run it from the repo folder)"; exit 1
}

function Remove-Ours([string]$Dest) {
  # Only ever removes a folder this installer (or install.sh) created: it carries our marker file.
  if ((Split-Path -Leaf $Dest) -ne $Name) { return $false }
  if (-not (Test-Path (Join-Path $Dest $Marker))) { return $false }
  $item = Get-Item -LiteralPath $Dest -Force
  if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    # A junction or symlink: remove only the link, never the folder it points to.
    [System.IO.Directory]::Delete($Dest)
  } else {
    Remove-Item -LiteralPath $Dest -Recurse -Force
  }
  return $true
  return $false
}

function Install-To([string]$Base, [string]$Label) {
  $Skills = Join-Path $Base 'skills'
  $Dest = Join-Path $Skills $Name
  New-Item -ItemType Directory -Force -Path $Skills | Out-Null
  if (Test-Path $Dest) {
    if (-not (Remove-Ours $Dest)) {
      $Backup = "$Dest.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
      Move-Item $Dest $Backup
      Write-Host "  kept your existing $Name folder at $Backup"
    }
  }
  Copy-Item -Recurse $Src $Dest
  Set-Content -Path (Join-Path $Dest $Marker) -Value $Version -NoNewline
  Write-Host "  ${Label}: installed to $Dest"
}

function Uninstall-From([string]$Base, [string]$Label) {
  $Dest = Join-Path (Join-Path $Base 'skills') $Name
  if (-not (Test-Path $Dest)) { Write-Host "  ${Label}: nothing to remove"; return }
  if (Remove-Ours $Dest) { Write-Host "  ${Label}: removed $Dest" }
  else { Write-Host "  ${Label}: $Dest was not installed by this script; left it alone" }
}

function Install-Tools {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "  winget not found. Install 'App Installer' from the Microsoft Store, or install Node 22+, ffmpeg and Git for Windows by hand."
    return
  }
  $Tools = @(
    @{ Cmd = 'node';   Id = 'OpenJS.NodeJS.LTS' },
    @{ Cmd = 'ffmpeg'; Id = 'Gyan.FFmpeg' },
    @{ Cmd = 'git';    Id = 'Git.Git' }
  )
  foreach ($t in $Tools) {
    if (Get-Command $t.Cmd -ErrorAction SilentlyContinue) { Write-Host "  ok       $($t.Cmd)"; continue }
    Write-Host "  installing $($t.Cmd) ($($t.Id))"
    winget install -e --id $t.Id --accept-source-agreements --accept-package-agreements
  }
  Write-Host "  Open a NEW terminal afterwards so the PATH picks up the new tools."
}

function Find-Bash {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if ($git) {
    $gitBash = Join-Path (Split-Path -Parent (Split-Path -Parent $git.Source)) 'bin\bash.exe'
    if (Test-Path $gitBash) { return $gitBash }
  }
  foreach ($p in @("$env:ProgramFiles\Git\bin\bash.exe", "${env:ProgramFiles(x86)}\Git\bin\bash.exe", "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe")) {
    if ($p -and (Test-Path $p)) { return $p }
  }
  return $null
}

if ($Uninstall) {
  Write-Host "Removing $Name"
  if ($DoClaude) { Uninstall-From $ClaudeBase 'Claude Code' }
  if ($DoCodex) { Uninstall-From $CodexBase 'Codex' }
  if ($Uninstall3D) { & (Join-Path $Src '3d\install_3d.ps1') -Uninstall }
  else { Write-Host "  The optional 3D pack (if installed) stays in %USERPROFILE%\.brief2mp4\3d; add -Uninstall3D to remove it." }
  if ($UninstallEdit) { & (Join-Path $Src 'edit\install_edit.ps1') -Uninstall }
  else { Write-Host "  The optional edit pack (if installed) stays in %USERPROFILE%\.brief2mp4\edit; add -UninstallEdit to remove it." }
  exit 0
}

if ($InstallTools) { Write-Host 'Installing tools with winget'; Install-Tools; Write-Host '' }

Write-Host "Installing $Name $Version"
if ($DoClaude) { Install-To $ClaudeBase 'Claude Code' }
if ($DoCodex) { Install-To $CodexBase 'Codex' }

if ($With3D.Count -gt 0) {
  $Components = ($With3D -join ',')
  Write-Host ''
  Write-Host "Installing the 3D pack (components: $Components)"
  & (Join-Path $Src '3d\install_3d.ps1') -Components $Components
}

if ($WithEdit.Count -gt 0) {
  Write-Host ''
  Write-Host "Installing the edit pack (components: $($WithEdit -join ','))"
  & (Join-Path $Src 'edit\install_edit.ps1') -Components $WithEdit
}

Write-Host ''
$Bash = Find-Bash
if ($Bash) {
  & $Bash (Join-Path $Src 'scripts/doctor.sh')
} else {
  Write-Host 'Git Bash not found. The skill scripts are bash, so install Git for Windows:'
  Write-Host '  winget install -e --id Git.Git    (or run this script again with -InstallTools)'
}

Write-Host ''
Write-Host 'Done. Start a new Claude Code or Codex session, then try:'
Write-Host "  Use the $Name skill to make the video in this brief: <paste a brief from examples\>"
