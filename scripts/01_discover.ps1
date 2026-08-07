# 01_discover.ps1 — find the head mesh assets inside Data.p4k.
#
# UNTESTED. We do not yet know the real asset paths, so this casts a wide net
# and dumps every hit to out/discovery/. Read the results, pick the right
# pattern, then feed it to 02_export_heads.ps1.
#
#   .\scripts\01_discover.ps1

$ErrorActionPreference = 'Stop'

$sb = Join-Path $PSScriptRoot '..\vendor\StarBreaker\target\release\starbreaker.exe'
if (-not (Test-Path $sb)) { throw "starbreaker not built — run 00_setup.ps1 first" }
if (-not $env:SC_DATA_P4K) { throw 'SC_DATA_P4K not set — run 00_setup.ps1 first' }

$out = Join-Path $PSScriptRoot '..\out\discovery'
New-Item -ItemType Directory -Force -Path $out | Out-Null

# Known-good starting points, from the CHF name hash table:
#   protos_human_male_face_t1_pu / protos_human_female_face_t1_pu
# NOTE on glob syntax: a single '*' matches within ONE directory only. To match
# across directories the pattern must start with '**/'. Every pattern here was
# originally written with a bare '*' and silently matched nothing.
$patterns = @{
    'riglogic'      = 'Data/Objects/Characters/RigLogic/**'
    'protos_face'   = '**/*protos_human*'
    'heads'         = '**/*head*.skin'
    'heads_cgf'     = '**/*head*.cgf'
    'faces'         = '**/*face*.skin'
    'dna'           = '**/*dna*'
    'characters'    = 'Data/Objects/Characters/Human/heads/**'
    'male_heads'    = '**/*male*head*'
}

foreach ($name in $patterns.Keys) {
    $glob = $patterns[$name]
    $file = Join-Path $out "$name.txt"
    Write-Host "[..]   listing $glob" -ForegroundColor Yellow
    # A filter that matches nothing is expected while we are still guessing
    # patterns, and starbreaker reports it on stderr. Do not let that abort the
    # sweep: capture stderr inside the child process, never via PowerShell's
    # 2>&1, which turns native stderr into a terminating NativeCommandError.
    $stderr = "$file.err"
    Start-Process -FilePath $sb `
        -ArgumentList @('p4k', 'list', '--filter', $glob) `
        -NoNewWindow -Wait `
        -RedirectStandardOutput $file -RedirectStandardError $stderr | Out-Null

    $n = if (Test-Path $file) { (Get-Content $file | Measure-Object -Line).Lines } else { 0 }
    if ($n -gt 0) {
        Write-Host "[ok]   $name -> $n lines ($file)" -ForegroundColor Green
        Remove-Item $stderr -ErrorAction SilentlyContinue
    } else {
        $msg = (Get-Content $stderr -ErrorAction SilentlyContinue) -join ' '
        Write-Host "[--]   $name -> no matches. $msg" -ForegroundColor DarkGray
    }
}

Write-Host ''
Write-Host 'Discovery written to out\discovery\.' -ForegroundColor Cyan
Write-Host 'Send those .txt files back and I will pick the exact head asset paths.' -ForegroundColor Cyan
