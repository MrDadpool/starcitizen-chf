# 00_setup.ps1 — one-time Windows setup for the head-extraction pipeline.
#
# UNTESTED. Written on macOS without a game install. Expect to fix something.
# Run from an elevated PowerShell in the repo root.
#
#   .\scripts\00_setup.ps1

$ErrorActionPreference = 'Stop'

function Need($cmd, $wingetId, $label) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Host "[ok]   $label already installed" -ForegroundColor Green
        return
    }
    Write-Host "[..]   installing $label" -ForegroundColor Yellow
    winget install --id $wingetId --accept-source-agreements --accept-package-agreements
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget not found. Install "App Installer" from the Microsoft Store, then re-run.'
}

Need git     Git.Git                    'Git'
Need python  Python.Python.3.12         'Python 3'
Need zstd    Facebook.Zstandard         'zstd'
Need rustc   Rustlang.Rustup            'Rust toolchain'
Need blender BlenderFoundation.Blender  'Blender'

# Refresh PATH so freshly-installed tools resolve in this session.
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path','User')

# Blender's installer does not always land on PATH. Find it if it did not.
if (-not (Get-Command blender -ErrorAction SilentlyContinue)) {
    $blender = Get-ChildItem 'C:\Program Files\Blender Foundation' -Recurse `
        -Filter blender.exe -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($blender) {
        $env:Path += ";$($blender.DirectoryName)"
        Write-Host "[ok]   blender found at $($blender.FullName)" -ForegroundColor Green
        Write-Host '       (add that folder to PATH permanently if you want it in new shells)'
    } else {
        Write-Host '[!!]   blender.exe not on PATH — step 4 will need a full path' -ForegroundColor DarkYellow
    }
}

# --- Verify the pure-Python tools actually run -------------------------------
Write-Host '[..]   verifying chf.py against the bundled sample' -ForegroundColor Yellow
$repo = Join-Path $PSScriptRoot '..'
python (Join-Path $repo 'tools\chf.py') dump (Join-Path $repo 'samples\combat_veteran.chf') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'chf.py failed — check that python and zstd are on PATH' }
Write-Host '[ok]   chf.py works' -ForegroundColor Green

# --- StarBreaker -------------------------------------------------------------
$vendor = Join-Path $PSScriptRoot '..\vendor'
New-Item -ItemType Directory -Force -Path $vendor | Out-Null
$sb = Join-Path $vendor 'StarBreaker'

if (Test-Path $sb) {
    Write-Host '[..]   updating StarBreaker' -ForegroundColor Yellow
    git -C $sb pull --ff-only
} else {
    Write-Host '[..]   cloning StarBreaker' -ForegroundColor Yellow
    git clone --depth 1 https://github.com/diogotr7/StarBreaker.git $sb
}

Write-Host '[..]   building starbreaker (release, takes a few minutes)' -ForegroundColor Yellow
Push-Location $sb
cargo build --release --bin starbreaker
Pop-Location

$exe = Join-Path $sb 'target\release\starbreaker.exe'
if (-not (Test-Path $exe)) { throw "build produced no binary at $exe" }
Write-Host "[ok]   starbreaker at $exe" -ForegroundColor Green

# --- Locate Data.p4k ---------------------------------------------------------
$candidates = @(
    'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k',
    'D:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k',
    'C:\Games\StarCitizen\LIVE\Data.p4k'
)
$p4k = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $p4k) {
    Write-Host '[!!]   Data.p4k not found in the usual places.' -ForegroundColor Red
    Write-Host '       Set it manually, then re-run:' -ForegroundColor Red
    Write-Host '       [Environment]::SetEnvironmentVariable("SC_DATA_P4K","<path>","User")'
    exit 1
}

# starbreaker reads this env var for every --p4k argument.
[Environment]::SetEnvironmentVariable('SC_DATA_P4K', $p4k, 'User')
$env:SC_DATA_P4K = $p4k
Write-Host "[ok]   SC_DATA_P4K = $p4k" -ForegroundColor Green

Write-Host ''
Write-Host 'Setup done. Next: .\scripts\01_discover.ps1' -ForegroundColor Cyan
