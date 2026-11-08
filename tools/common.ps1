# Shared setup for the zonecraft PowerShell tools. Dot-source it from a tool folder:  . "$PSScriptRoot\..\common.ps1"
# Gives: $Tools (this folder), $Zonecraft (the plugin root), $Repo (the mod folder: the nearest folder holding mod.json,
#        walking up from the current folder, or $env:ZONECRAFT_MOD_DIR; else the current folder), $Cfg (tools\config.json
#        < machine settings < <mod>\zonecraft.local.json), $Kit, $Game, $Mods (~mods), $ModCfg (mod.json or $null),
#        and Get-ModName [-Mod X] (explicit -Mod, else mod.json "name").
$ErrorActionPreference = "Stop"
$Tools = (Resolve-Path $PSScriptRoot).Path
$Zonecraft = (Resolve-Path "$Tools\..").Path

function Read-Json($path) { if (Test-Path $path) { Get-Content $path -Raw | ConvertFrom-Json } else { $null } }

function Find-ModRoot {
    if ($env:ZONECRAFT_MOD_DIR) { return (Resolve-Path $env:ZONECRAFT_MOD_DIR).Path }
    $d = (Get-Location).Path
    while ($d) {
        if (Test-Path (Join-Path $d "mod.json")) { return $d }
        $parent = Split-Path $d -Parent
        if ($parent -eq $d) { break }
        $d = $parent
    }
    return (Get-Location).Path
}
$Repo = Find-ModRoot

$Cfg = Read-Json "$Tools\config.json"
# Machine settings (written by setup.ps1) apply to every mod on this PC; <mod>\zonecraft.local.json overrides one mod.
# The settings file of the original harness is still read, so a PC set up before zonecraft keeps working.
$MachineSettings = "$env:LOCALAPPDATA\zonecraft\settings.json"
$LegacySettings = "$env:LOCALAPPDATA\stalker2-modding-harness\settings.json"
foreach ($local in @((Read-Json $LegacySettings), (Read-Json $MachineSettings), (Read-Json "$Repo\zonecraft.local.json"))) {
    if ($local) { foreach ($p in $local.PSObject.Properties) { $Cfg | Add-Member -Force -NotePropertyName $p.Name -NotePropertyValue $p.Value } }
}

# Tools call this for the settings they need; config.json ships empty values, setup.ps1 fills them per machine.
function Assert-Setup([string[]]$Keys = @("kit", "game")) {
    $missing = $Keys | Where-Object { -not $Cfg.$_ }
    if ($missing) { throw "Not set up on this PC yet ($($missing -join ', ') missing). Run: powershell -ExecutionPolicy Bypass -File <zonecraft>\tools\setup\setup.ps1" }
}

$Kit  = $Cfg.kit  -replace '/', '\'
$Game = ($Cfg.game -replace '/', '\') + "\Stalker2"
$Mods = "$Game\Content\Paks\~mods"
$ModCfg = Read-Json "$Repo\mod.json"
$GameExe = "Stalker2-Win64-Shipping"
$EditorCmd = "$Kit\Stalker2\Binaries\Win64\Stalker2ModEditor-Win64-Shipping-Cmd.exe"
$Uproject = "$Kit\Stalker2\Stalker2.uproject"

function Get-ModName([string]$Mod) {
    if ($Mod) { return $Mod }
    if ($ModCfg -and $ModCfg.name) { return $ModCfg.name }
    throw "No -Mod given and no mod.json in $Repo"
}

function Test-GameRunning { [bool](Get-Process -Name $GameExe -ErrorAction SilentlyContinue) }

function Wait-GameClosed {
    while (Test-GameRunning) { Write-Host "Game is running - close it to continue..."; Start-Sleep -Seconds 10 }
}

# Mount order: priority = 3 + 100 * (N + 1) for a `_N_P` suffix. Kit-named paks mount at 3.
function Get-Priority([string]$key, [int]$default) {
    if ($ModCfg -and $ModCfg.PSObject.Properties[$key]) { return [int]$ModCfg.$key }
    return $default
}

# UAT (RunUAT / AutomationTool) runs one instance per machine: a second cook or CreatePlainMod fails at once with
# "A conflicting instance of AutomationTool is already running". Another session may be cooking; wait for it.
function Wait-UatFree {
    while (Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'AutomationTool' }) {
        Write-Host "Another AutomationTool (cook) is running - waiting..."; Start-Sleep -Seconds 15
    }
}
