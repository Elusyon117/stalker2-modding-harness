# Create a new mod repo with zonecraft: its own folder with the mod templates filled in, the Zone Kit plugin created,
# a git repository, and a public GitHub repo created and pushed. The mod holds only its own files; the tools and the
# knowledge stay in zonecraft.
# Usage:
#   powershell -File <zonecraft>\tools\setup\new_mod.ps1 -Name ImmersiveReloading -Short ImmReload `
#       -RepoName stalker2-immersive-reloading -Description "Sprint while reloading." [-Into <folder>] [-NoKit] [-NoGitHub] [-Private]
# -Name  = Zone Kit plugin name (PascalCase, no spaces; also the /<Name>/ content root and pak base name).
# -Short = prefix for mod-only asset names (BP_<Short>Subsystem, ...), probes and log tags.
# -Into  = the folder the mod folder is created in. Default: the machine settings' "mods_dir"; else, run from inside a
#          mod, next to that mod; else the current folder. The folder used is saved as "mods_dir".
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string]$Short,
    [Parameter(Mandatory)][string]$RepoName,
    [Parameter(Mandatory)][string]$Description,
    [string]$Into,
    [switch]$NoKit, [switch]$NoGitHub, [switch]$Private
)
. "$PSScriptRoot\..\common.ps1"
Assert-Setup (@("github_owner") + $(if ($NoKit) { @() } else { @("kit") }))

if (-not $Into) {
    if ($Cfg.mods_dir) { $Into = $Cfg.mods_dir }
    elseif ($ModCfg) { $Into = Split-Path $Repo -Parent }
    else { $Into = (Get-Location).Path }
}
$Into = (Resolve-Path $Into).Path
$dest = Join-Path $Into $RepoName
if (Test-Path $dest) { throw "$dest already exists" }

$utf8 = New-Object Text.UTF8Encoding $false
$ok = $false
New-Item -ItemType Directory -Force $dest | Out-Null
Push-Location $dest
try {
    # 1. The mod's own files, from zonecraft's templates
    $date = Get-Date -Format yyyy-MM-dd
    $subst = @{ "{{MOD}}" = $Name; "{{SHORT}}" = $Short; "{{REPO}}" = $RepoName; "{{DESCRIPTION}}" = $Description;
                "{{DATE}}" = $date; "{{OWNER}}" = $Cfg.github_owner }
    function Fill($text) { foreach ($k in $subst.Keys) { $text = $text.Replace($k, $subst[$k]) }; $text }
    $map = [ordered]@{ "CLAUDE.md" = "CLAUDE.md"; "PLAN.md" = "PLAN.md"; "BUILD.md" = "BUILD.md"; "README.md" = "README.md";
                       "LOG.md" = "zonekit\README.md"; "gitignore" = ".gitignore"; "zonecraft_path.py" = "zonekit\tools\zonecraft_path.py" }
    New-Item -ItemType Directory -Force "zonekit\$Name", "zonekit\tools\classifier\$Name", "zonekit\builds" | Out-Null
    foreach ($t in $map.Keys) {
        [IO.File]::WriteAllText("$dest\$($map[$t])", (Fill ([IO.File]::ReadAllText("$Zonecraft\templates\$t"))), $utf8)
    }
    $mod = [ordered]@{ name = $Name; short = $Short; repo = $RepoName; description = $Description;
                       release_pak_suffix = 20; dev_pak_suffix = 30; nexus_id = $null; optional_plugins = @() }
    [IO.File]::WriteAllText("$dest\mod.json", ($mod | ConvertTo-Json -Depth 4), $utf8)
    foreach ($f in "OverridePackages.txt", "NewPackages.txt") { [IO.File]::WriteAllText("$dest\zonekit\tools\classifier\$Name\$f", "", $utf8) }
    [IO.File]::WriteAllText("$dest\zonekit\builds\.gitkeep", "", $utf8)

    # 2. Zone Kit plugin
    if (-not $NoKit) {
        $plug = "$Kit\Stalker2\Mods\$Name"
        if (-not (Test-Path "$plug\$Name.uplugin")) {
            Wait-UatFree
            Write-Host "Creating the Zone Kit plugin (GSCCreatePlainMod) ..."
            & "$Kit\Engine\Build\BatchFiles\RunUAT.bat" GSCCreatePlainMod "-Project=$Uproject" "-ModName=$Name" *> "$env:TEMP\${Name}_create.log"
            if (-not (Test-Path "$plug\$Name.uplugin")) { throw "plugin not created; see $env:TEMP\${Name}_create.log" }
        }
        $u = Get-Content "$plug\$Name.uplugin" -Raw | ConvertFrom-Json
        $want = [ordered]@{ FriendlyName = $Name; Description = $Description; Category = "Game Features"; CreatedBy = $Cfg.github_owner;
                            EnabledByDefault = $true; CanContainContent = $true; ExplicitlyLoaded = $true;
                            BuiltInInitialFeatureState = "Registered"; Mod = $true }
        foreach ($k in $want.Keys) { $u | Add-Member -Force -NotePropertyName $k -NotePropertyValue $want[$k] }
        [IO.File]::WriteAllText("$plug\$Name.uplugin", ($u | ConvertTo-Json -Depth 8), $utf8)
        $env:ZONECRAFT_MOD_DIR = $dest
        & "$Tools\build\mirror_from_kit.ps1" -Mod $Name | Out-Null
        Remove-Item Env:\ZONECRAFT_MOD_DIR
    }

    # 3. Git and GitHub
    git init -q -b main
    git add -A
    git commit -q -m "Create $Name with zonecraft"
    if (-not $NoGitHub) {
        $vis = if ($Private) { "--private" } else { "--public" }
        gh repo create "$($Cfg.github_owner)/$RepoName" $vis --description $Description --source . --remote origin --push
    }

    # 4. Remember where mods live
    $settings = Read-Json $MachineSettings
    if (-not $settings) { $settings = [pscustomobject]@{} }
    $settings | Add-Member -Force -NotePropertyName mods_dir -NotePropertyValue ($Into -replace '\\', '/')
    New-Item -ItemType Directory -Force (Split-Path $MachineSettings) | Out-Null
    [IO.File]::WriteAllText($MachineSettings, ($settings | ConvertTo-Json), $utf8)

    $ok = $true
    Write-Host "Created $dest"
    if (-not $NoKit) {
        Write-Host "Tester step: restart the Zone Kit editor, then pick '$Name' in the toolbar mod selector once (creates the GameFeatureData and mounts the plugin). Then run mirror_from_kit.ps1."
    }
} finally {
    Pop-Location
    if (-not $ok -and -not (git -C $dest remote 2>$null | Select-String -Quiet '^origin$')) { Remove-Item $dest -Recurse -Force; Write-Host "Failed; removed the partial $dest" }
}
