r"""Copy the last packaging of a mod into its Release Candidate folder, renamed for the load order you want.

    py -I release_candidate.py [--mod-root DIR] [--names]     (default: the mod folder you are in)

After every Package Mod (or cook_and_install.ps1) the kit leaves
    <kit>\Stalker2\SavedMods\Staged\<Mod>\Windows\{OverrideContent,NewContent}\...\Paks\Windows\<Mod>Stalker2-Windows-<Kind>.{pak,utoc,ucas}
This copies each set into <mod folder>\<release.folder>\ under the names mod.json "release" asks for, and writes
rc.json (when, from which staged files). --names only prints the names it would use.

mod.json:
    "release": {
      "folder": "ReleaseCandidate",          relative to the mod folder (or absolute)
      "override": "zzzz_{mod}_P",            name for the override files ({mod} = the plugin name)
      "newcontent": "{kit}",                 name for the new-content files; "{kit}" keeps the kit's own name
      "auto": true                           copy automatically after each successful packaging (the band does it)
    }
The `_P` ending (or `_<N>_P`) gives the pak its mount priority and the file name breaks ties, so a "zzzz_" prefix
mounts after mods named "zzz_..." (knowledge/pipeline.md § 5).
"""
import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try:
    import hconf  # noqa: E402
except Exception:  # pragma: no cover
    hconf = None

KINDS = ("OverrideContent", "NewContent")
EXTS = (".pak", ".utoc", ".ucas")
DEFAULTS = {"folder": "ReleaseCandidate", "override": "zzzz_{mod}_P", "newcontent": "{kit}", "auto": True}


def read_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def settings(mod):
    rel = dict(DEFAULTS)
    rel.update({k: v for k, v in (mod.get("release") or {}).items() if v not in (None, "")})
    return rel


def kit_name(mod_name, kind):
    return f"{mod_name}Stalker2-Windows-{kind}"


def target_names(mod):
    """{kind: base name without extension} for this mod's release candidate."""
    rel, name = settings(mod), mod.get("name", "")
    out = {}
    for kind, key in (("OverrideContent", "override"), ("NewContent", "newcontent")):
        pattern = rel[key]
        out[kind] = kit_name(name, kind) if pattern.strip() == "{kit}" else pattern.replace("{mod}", name).replace(
            "{kit}", kit_name(name, kind))
    return out


def staged_dir(kit, name, kind):
    return os.path.join(kit, "Stalker2", "SavedMods", "Staged", name, "Windows", kind, "Windows", "Stalker2", "Mods",
                        name, "Content", "Paks", "Windows")


def staged_files(kit, name):
    """{kind: [(ext, path, mtime)]} of what the last packaging left (missing kinds are absent)."""
    out = {}
    for kind in KINDS:
        d = staged_dir(kit, name, kind)
        files = []
        for ext in EXTS:
            p = os.path.join(d, kit_name(name, kind) + ext)
            if os.path.exists(p):
                files.append((ext, p, os.path.getmtime(p)))
        if files:
            out[kind] = files
    return out


def rc_folder(mod_root, mod):
    folder = settings(mod)["folder"]
    return folder if os.path.isabs(folder) else os.path.join(mod_root, folder)


def last_copy(mod_root, mod):
    return read_json(os.path.join(rc_folder(mod_root, mod), "rc.json"))


def needs_copy(kit, mod_root, mod):
    staged = staged_files(kit, mod.get("name", ""))
    if not staged:
        return False
    newest = max(t for files in staged.values() for _, _, t in files)
    return newest > float(last_copy(mod_root, mod).get("source_mtime", 0)) + 1


def copy(kit, mod_root, mod):
    name = mod.get("name", "")
    staged = staged_files(kit, name)
    if not staged:
        raise SystemExit(f"Nothing packaged for {name} yet (looked in {staged_dir(kit, name, 'OverrideContent')}).")
    names = target_names(mod)
    dest = rc_folder(mod_root, mod)
    os.makedirs(dest, exist_ok=True)
    # remove the previous candidate's paks (any name: the naming may have changed), keep everything else
    for f in os.listdir(dest):
        if f.lower().endswith(EXTS):
            os.remove(os.path.join(dest, f))
    written = []
    for kind, files in staged.items():
        for ext, src, _ in files:
            out = os.path.join(dest, names[kind] + ext)
            shutil.copy2(src, out)
            written.append(os.path.basename(out))
    info = {"copied": time.time(), "source_mtime": max(t for fs in staged.values() for _, _, t in fs),
            "files": written, "names": names}
    with open(os.path.join(dest, "rc.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    return dest, info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod-root", default=None)
    ap.add_argument("--kit", default=None)
    ap.add_argument("--names", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = a.mod_root or (hconf.REPO if hconf else os.getcwd())
    mod = read_json(os.path.join(root, "mod.json"))
    if not mod.get("name"):
        raise SystemExit(f"No mod.json with a name in {root}.")
    names = target_names(mod)
    if a.names:
        for kind, base in names.items():
            print(f"{kind:<16} {base}.pak / .utoc / .ucas")
        print(f"folder           {rc_folder(root, mod)}")
        return
    kit = a.kit or (hconf.KIT if hconf else "")
    if not kit:
        raise SystemExit("No kit path: set up zonecraft (tools/setup/setup.ps1) or pass --kit.")
    dest, info = copy(kit, root, mod)
    if a.json:
        print(json.dumps({"folder": dest, **info}))
    else:
        print(f"Release candidate in {dest}: " + ", ".join(info["files"]))


if __name__ == "__main__":
    main()
