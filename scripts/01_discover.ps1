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
$patterns = @{
    'protos_face'   = '*protos_human*face*'
    'heads'         = '*head*.skin'
    'heads_cgf'     = '*head*.cgf'
    'faces'         = '*face*.skin'
    'dna'           = '*dna*'
    'characters'    = 'Data/Objects/Characters/Human/*'
    'male_heads'    = '*male*head*'
}

foreach ($name in $patterns.Keys) {
    $glob = $patterns[$name]
    $file = Join-Path $out "$name.txt"
    Write-Host "[..]   listing $glob" -ForegroundColor Yellow
    & $sb p4k list --filter $glob 2>&1 | Out-File -Encoding utf8 $file
    $n = (Get-Content $file | Measure-Object -Line).Lines
    Write-Host "[ok]   $name -> $n lines ($file)" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Discovery written to out\discovery\.' -ForegroundColor Cyan
Write-Host 'Send those .txt files back and I will pick the exact head asset paths.' -ForegroundColor Cyan
