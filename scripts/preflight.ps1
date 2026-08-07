# preflight.ps1 — report what is already installed. Installs NOTHING.
#
#   .\scripts\preflight.ps1
#
# Dot-source it to reuse the detectors:
#   . .\scripts\preflight.ps1 -Quiet
#   $tools = Get-ToolStatus

param([switch]$Quiet)

$ErrorActionPreference = 'Stop'

# On Win11 "python.exe" and "python3.exe" exist as Microsoft Store stubs that
# are not Python — they just open the Store. Reject anything under WindowsApps.
function Test-StoreStub($path) {
    return $path -like '*\AppData\Local\Microsoft\WindowsApps\*'
}

function Find-Exe {
    <#
      Resolve a real executable. Tries PATH first (skipping Store stubs), then
      any extra directories given, then a recursive search of well-known roots.
    #>
    param(
        [string]$Name,
        [string[]]$ExtraPaths = @(),
        [string[]]$SearchRoots = @()
    )

    foreach ($cmd in @(Get-Command $Name -All -ErrorAction SilentlyContinue)) {
        if ($cmd.Source -and -not (Test-StoreStub $cmd.Source)) { return $cmd.Source }
    }
    foreach ($p in $ExtraPaths) {
        if ($p -and (Test-Path $p)) { return (Resolve-Path $p).Path }
    }
    foreach ($root in $SearchRoots) {
        if (-not (Test-Path $root)) { continue }
        $hit = Get-ChildItem $root -Recurse -Filter "$Name.exe" -ErrorAction SilentlyContinue |
               Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

function Get-Version($exe, $arg) {
    if (-not $exe) { return $null }
    try {
        $out = & $exe $arg 2>&1 | Select-Object -First 1
        return ($out | Out-String).Trim()
    } catch { return 'present (version check failed)' }
}

function Get-ToolStatus {
    $pf  = $env:ProgramFiles
    $lad = $env:LOCALAPPDATA

    $python = Find-Exe -Name python -SearchRoots @(
        "$lad\Programs\Python", "$pf\Python311", "$pf\Python312", "$pf\Python313"
    )
    # The `py` launcher is the reliable Windows entry point when it exists.
    if (-not $python) {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if ($py) { $python = $py.Source }
    }

    $blender = Find-Exe -Name blender -SearchRoots @(
        "$pf\Blender Foundation", "${env:ProgramFiles(x86)}\Steam\steamapps\common\Blender"
    )

    $cargo = Find-Exe -Name cargo -ExtraPaths @("$env:USERPROFILE\.cargo\bin\cargo.exe")

    return @(
        [pscustomobject]@{
            Name = 'Python 3'; Exe = $python; WingetId = 'Python.Python.3.12'
            Version = (Get-Version $python '--version'); Required = 'core'
        }
        [pscustomobject]@{
            Name = 'zstd'; Exe = (Find-Exe -Name zstd); WingetId = 'Meta.Zstandard'
            Version = (Get-Version (Find-Exe -Name zstd) '--version'); Required = 'core'
        }
        [pscustomobject]@{
            Name = 'Git'; Exe = (Find-Exe -Name git); WingetId = 'Git.Git'
            Version = (Get-Version (Find-Exe -Name git) '--version'); Required = 'extract'
        }
        [pscustomobject]@{
            Name = 'Rust (cargo)'; Exe = $cargo; WingetId = 'Rustlang.Rustup'
            Version = (Get-Version $cargo '--version'); Required = 'extract'
        }
        [pscustomobject]@{
            Name = 'Blender'; Exe = $blender; WingetId = 'BlenderFoundation.Blender'
            Version = (Get-Version $blender '--version'); Required = 'render'
        }
    )
}

function Find-DataP4k {
    <#
      Look for Data.p4k across every fixed drive rather than guessing C:.
      Checks the standard RSI layout first, then falls back to a shallow scan.
    #>
    if ($env:SC_DATA_P4K -and (Test-Path $env:SC_DATA_P4K)) { return $env:SC_DATA_P4K }

    $drives = Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' |
              Select-Object -ExpandProperty DeviceID

    $suffixes = @(
        'Roberts Space Industries\StarCitizen\LIVE\Data.p4k',
        'Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k',
        'Games\Roberts Space Industries\StarCitizen\LIVE\Data.p4k',
        'Games\StarCitizen\LIVE\Data.p4k',
        'StarCitizen\LIVE\Data.p4k'
    )

    foreach ($d in $drives) {
        foreach ($s in $suffixes) {
            $candidate = Join-Path "$d\" $s
            if (Test-Path $candidate) { return $candidate }
        }
    }

    # Nothing standard — scan a few levels deep for any LIVE\Data.p4k.
    foreach ($d in $drives) {
        $hit = Get-ChildItem "$d\" -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                Get-ChildItem $_.FullName -Depth 3 -Filter 'Data.p4k' `
                    -File -ErrorAction SilentlyContinue
            } | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

function Show-Preflight {
    $tools = Get-ToolStatus

    Write-Host ''
    Write-Host 'Preflight — nothing is being installed' -ForegroundColor Cyan
    Write-Host ('-' * 64)

    foreach ($t in $tools) {
        if ($t.Exe) {
            Write-Host ('[have] {0,-14} {1}' -f $t.Name, $t.Version) -ForegroundColor Green
            Write-Host ('       {0}' -f $t.Exe) -ForegroundColor DarkGray
        } else {
            Write-Host ('[MISS] {0,-14} needed for: {1}' -f $t.Name, $t.Required) -ForegroundColor Yellow
        }
    }

    Write-Host ('-' * 64)
    $p4k = Find-DataP4k
    if ($p4k) {
        $gb = [math]::Round((Get-Item $p4k).Length / 1GB, 1)
        Write-Host ('[have] Data.p4k       {0} GB' -f $gb) -ForegroundColor Green
        Write-Host ('       {0}' -f $p4k) -ForegroundColor DarkGray
    } else {
        Write-Host '[MISS] Data.p4k       not found on any fixed drive' -ForegroundColor Yellow
        Write-Host '       set it manually: $env:SC_DATA_P4K = "F:\...\LIVE\Data.p4k"'
    }

    Write-Host ''
    $missing = @($tools | Where-Object { -not $_.Exe })
    if ($missing.Count -eq 0) {
        Write-Host 'Everything present. Nothing to install.' -ForegroundColor Green
    } else {
        Write-Host ('Missing {0}: {1}' -f $missing.Count, ($missing.Name -join ', ')) -ForegroundColor Yellow
        Write-Host 'Run .\scripts\00_setup.ps1 to install only those.' -ForegroundColor Cyan
    }
    Write-Host ''

    return $tools
}

if (-not $Quiet -and $MyInvocation.InvocationName -ne '.') {
    Show-Preflight | Out-Null
}
