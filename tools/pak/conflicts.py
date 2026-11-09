r"""Which mods conflict: the installed ones in ~mods, your own (their release candidates or test paks), and any folder
of paks you are putting together as a collection.

    py -I conflicts.py scan [--mods DIR] [--yours MODROOT ...] [--collection DIR ...] [--only-yours] [--json]
    py -I conflicts.py scan --listing FILE.json ...      (test: containers' file lists from a JSON file, no kit needed)

How it decides (knowledge/compatibility.md, config-files.md):
- **Assets**: per package the last-mounted pak wins outright, nothing merges. Two mods shipping the same package
  conflict; the winner is the higher mount order (`_P` 103, `_<N>_P` 3 + 100 * (N + 1), kit names 3), then the file
  name (later in name order mounts later). Same sha1 in both = the same file, harmless.
- **Whole cfg files** (a `.cfg` that is not a patch, under GameLite/GameData): the last one replaces the whole file.
- **Cfg patches** (`X.cfg_patch_<Mod>`, any `.cfg` in a `<X>Prototypes/` folder): mods patching the same file
  coexist unless they touch the same field. The patches are extracted and compared field by field: a struct without
  {bpatch} replaces its whole node, so it overlaps every field under it. The later-loaded mod wins that field.
New content (ModGameData, /<Mod>/ packages) never conflicts.

Containers are listed with the kit's `UnrealPak.exe <file> -List`; the lists are cached by size and date in
%LOCALAPPDATA%\zonecraft\conflicts\lists.json, so a second scan is quick. Prints one JSON object with --json:
    {atMs, sources, mods: [{name, files, order, isYours, source}], conflicts: [{kind, what, mods: [{name, file,
     order}] (winner first), verdict same|wins|tie|risky, note, isYours}], errors}
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from hconf import CFG, KIT, MODS_DIR  # noqa: E402
import cfg_parse  # noqa: E402

CONTAINERS = (".pak", ".utoc")
GAMEDATA = "gamelite/gamedata/"
# Assets many mods override; a conflict on one of these is worth a closer look even when one side wins.
HOT = ("animbp_player", "bp_stalker2character", "imc_exploration", "da_inputelementsmodels", "w_gamehud",
       "corevariables.cfg")


def priority(fname):
    m = re.search(r"_(\d+)_P\.(pak|utoc|ucas)$", fname, re.I)
    if m:
        return 3 + 100 * (int(m.group(1)) + 1)
    return 103 if re.search(r"_P\.(pak|utoc|ucas)$", fname, re.I) else 3


def stem(fname):
    return re.sub(r"\.(pak|utoc|ucas|sig)$", "", fname, flags=re.I)


def mod_name_of(stem_):
    """A readable mod name from a container stem: zzzz_MyMod_P, MyModStalker2-Windows-OverrideContent_P -> MyMod."""
    s = re.sub(r"(_\d+)?_P$", "", stem_, flags=re.I)
    s = re.sub(r"Stalker2-Windows-(OverrideContent|NewContent)$", "", s, flags=re.I)
    s = re.sub(r"_?(OverrideContent|NewContent)$", "", s, flags=re.I)
    s = re.sub(r"^z+_", "", s, flags=re.I)
    return s.strip("_- ") or stem_


# ---------------------------------------------------------------- listing containers

LIST_LINE = re.compile(r'"(?P<path>[^"]+)"(?:.*?size:\s*(?P<size>\d+))?(?:.*?sha1:\s*(?P<sha>[0-9A-Fa-f]+))?')


def parse_listing(text):
    """UnrealPak -List output -> {path: sha1 or ''} (paths relative to the mount point, forward slashes)."""
    out = {}
    for line in text.splitlines():
        m = LIST_LINE.search(line)
        if not m:
            continue
        p = m.group("path").replace("\\", "/").lstrip("/")
        if "." not in os.path.basename(p):
            continue
        out[p] = (m.group("sha") or "").upper()
    return out


def unrealpak():
    exe = os.path.join(KIT, "Engine", "Binaries", "Win64", "UnrealPak.exe") if KIT else ""
    return exe if exe and os.path.exists(exe) else ""


class Lister:
    def __init__(self, listing_file=None):
        self.fixed = None
        if listing_file:
            with open(listing_file, encoding="utf-8") as f:
                self.fixed = json.load(f)
        local = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        self.cache_path = os.path.join(local, "zonecraft", "conflicts", "lists.json")
        self.cache = {}
        if not self.fixed and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    self.cache = json.load(f)
            except (OSError, ValueError):
                self.cache = {}
        self.dirty = False

    def files(self, path):
        """{inner path: sha1} for one container."""
        if self.fixed is not None:
            return self.fixed.get(os.path.basename(path), {})
        st = os.stat(path)
        key = f"{os.path.abspath(path).lower()}|{st.st_size}|{int(st.st_mtime)}"
        if key in self.cache:
            return self.cache[key]
        exe = unrealpak()
        if not exe:
            raise RuntimeError("the Zone Kit is not set up (UnrealPak.exe lists the paks); run tools/setup/setup.ps1")
        r = subprocess.run([exe, path, "-List"], capture_output=True, text=True, errors="replace", timeout=600)
        files = parse_listing(r.stdout)
        if r.returncode != 0 and not files:
            raise RuntimeError(f"UnrealPak could not list {os.path.basename(path)}: {(r.stderr or r.stdout)[-200:]}")
        self.cache[key] = files
        self.dirty = True
        self.save()  # kept as it goes: a scan cut short does not list this pak again
        return files

    def extract(self, container, inner, out_dir):
        """One file out of a container; returns its local path or None."""
        if self.fixed is not None:
            text = self.fixed.get("__text__", {}).get(f"{os.path.basename(container)}:{inner}")
            if text is None:
                return None
            p = os.path.join(out_dir, re.sub(r"[^A-Za-z0-9_.-]", "_", inner))
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            return p
        exe = unrealpak()
        if not exe:
            return None
        sub = os.path.join(out_dir, re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(container)))
        os.makedirs(sub, exist_ok=True)
        subprocess.run([exe, container, "-Extract", sub, f"-Filter=*{os.path.basename(inner)}"],
                       capture_output=True, text=True, errors="replace", timeout=600)
        for dp, _, fs in os.walk(sub):
            for f in fs:
                full = os.path.join(dp, f)
                if full.replace("\\", "/").lower().endswith(inner.lower().split("/")[-1]):
                    return full
        return None

    def save(self):
        if self.dirty:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
            self.dirty = False


# ---------------------------------------------------------------- what a file is

def package_key(inner):
    """The package an inner path belongs to (lowercase, no extension), or None for non-package files."""
    p = inner.lower()
    if not p.endswith((".uasset", ".umap", ".uexp", ".ubulk", ".uptnl")):
        return None
    return re.sub(r"\.(uasset|umap|uexp|ubulk|uptnl)$", "", p)


def gamedata_rel(inner):
    p = inner.replace("\\", "/")
    i = p.lower().find(GAMEDATA)
    return p[i + len(GAMEDATA):] if i >= 0 else None


def cfg_target(inner):
    """For a GameData cfg: ('patch', target cfg) or ('file', the cfg itself); None for anything else."""
    rel = gamedata_rel(inner)
    if rel is None:
        return None
    parts = rel.split("/")
    name = parts[-1]
    m = re.match(r"(.+\.cfg)_patch_.+$", name, re.I)
    if m:
        target = m.group(1)
        # ObjPrototypes/ObjPrototypes.cfg_patch_X.cfg: the folder is named after the cfg, the cfg sits beside it
        if len(parts) >= 2 and parts[-2].lower() == target[:-4].lower():
            return "patch", "/".join(parts[:-2] + [target]).lower()
        return "patch", "/".join(parts[:-1] + [target]).lower()
    if not name.lower().endswith(".cfg"):
        return None
    if len(parts) >= 2 and parts[-2].lower().endswith("prototypes") and name.lower() != parts[-2].lower() + ".cfg":
        return "patch", "/".join(parts[:-2] + [parts[-2] + ".cfg"]).lower()
    return "file", rel.lower()


def patch_paths(text):
    """Field paths a cfg patch touches. A struct without {bpatch} replaces its node: its own path stands for all."""
    root = cfg_parse.parse(text)
    out = set()

    def walk(node, path):
        for key, val in node.items:
            p = path + (key,)
            if isinstance(val, cfg_parse.Node):
                if val.bpatch:
                    walk(val, p)
                else:
                    out.add(p)
            else:
                out.add(p)  # a field set, or removenode
    walk(root, ())
    return out


def overlap(a, b):
    """Paths of `a` and `b` that touch the same field (one is a prefix of the other)."""
    hits = set()
    for x in a:
        for y in b:
            n = min(len(x), len(y))
            if x[:n] == y[:n]:
                hits.add(x if len(x) >= len(y) else y)
    return hits


# ---------------------------------------------------------------- gathering mods

def gather(sources):
    """sources: [(source label, folder or file list, isYours)] -> mods {name: {containers, order, isYours, source}}."""
    mods = {}
    for label, folder, yours in sources:
        files = []
        if isinstance(folder, list):
            files = folder
        elif os.path.isdir(folder):
            for dp, _, fs in os.walk(folder):
                files += [os.path.join(dp, f) for f in fs if f.lower().endswith(CONTAINERS)]
        for path in files:
            st = stem(os.path.basename(path))
            name = mod_name_of(st)
            if isinstance(folder, str) and os.path.isdir(folder):
                rel = os.path.relpath(os.path.dirname(path), folder)
                if rel not in (".", "") and not yours:
                    name = rel.replace("\\", "/").split("/")[0]  # a mod in its own subfolder of ~mods
            m = mods.setdefault((name.lower(), label), {"name": name, "containers": [], "order": 0, "isYours": yours,
                                                        "source": label})
            m["containers"].append(path)
            m["order"] = max(m["order"], priority(os.path.basename(path)))
    # the same mod installed and yours: keep yours (it is what you are working on)
    by_name = {}
    for (low, _), m in mods.items():
        if low in by_name and by_name[low]["isYours"]:
            continue
        by_name[low] = m
    return list(by_name.values())


def mount_key(entry):
    """Sort key: later mounts (winners) sort last."""
    return (entry["order"], os.path.basename(entry["file"]).lower())


def scan(mods, lister, only_yours=False):
    errors = []
    assets = {}   # package -> [entry]
    files = {}    # whole cfg -> [entry]
    patches = {}  # target cfg -> [entry + inner]
    counts = {}
    for m in mods:
        n = 0
        for c in m["containers"]:
            try:
                listed = lister.files(c)
            except Exception as err:  # noqa: BLE001 (one unreadable pak must not stop the scan)
                errors.append(str(err))
                continue
            for inner, sha in listed.items():
                n += 1
                entry = {"mod": m, "file": c, "inner": inner, "sha": sha, "order": priority(os.path.basename(c))}
                ct = cfg_target(inner)
                if ct and ct[0] == "patch":
                    patches.setdefault(ct[1], []).append(entry)
                    continue
                if ct and ct[0] == "file":
                    files.setdefault(ct[1], []).append(entry)
                    continue
                key = package_key(inner)
                if key and inner.lower().endswith((".uasset", ".umap")):
                    assets.setdefault(key, []).append(entry)
        counts[id(m)] = n

    conflicts = []

    def mods_of(entries):
        es = sorted(entries, key=mount_key, reverse=True)
        return [{"name": e["mod"]["name"], "file": os.path.basename(e["file"]), "order": e["order"]} for e in es], es

    def emit(kind, what, entries, verdict, note):
        listed, es = mods_of(entries)
        yours = any(e["mod"]["isYours"] for e in es)
        if only_yours and not yours:
            return
        conflicts.append({"kind": kind, "what": what, "mods": listed, "verdict": verdict, "note": note, "isYours": yours})

    def distinct(entries):
        seen = {}
        for e in entries:
            seen.setdefault(e["mod"]["name"].lower(), e)
        return list(seen.values())

    for key, entries in assets.items():
        es = distinct(entries)
        if len(es) < 2:
            continue
        shas = {e["sha"] for e in es}
        top = sorted(es, key=mount_key, reverse=True)
        if len(shas) == 1 and "" not in shas:
            emit("asset", key, es, "same", "Identical file in each: harmless.")
            continue
        tie = top[0]["order"] == top[1]["order"]
        hot = any(h in key for h in HOT)
        verdict = "risky" if hot else ("tie" if tie else "wins")
        note = (f"{top[0]['mod']['name']} wins; the others' changes to it are lost."
                + (" Same mount order: the file name decides." if tie else "")
                + (" A heavily shared asset: merge the changes or make one mod optional." if hot else ""))
        emit("asset", key, es, verdict, note)

    for key, entries in files.items():
        es = distinct(entries)
        if len(es) < 2:
            continue
        top = sorted(es, key=mount_key, reverse=True)
        emit("cfg-file", key, es, "risky",
             f"Whole-file replacements: {top[0]['mod']['name']}'s copy wins and the others' are ignored. "
             "Ask the authors for patch files (config-files.md).")
    # a whole-file replacement also wipes every patch's base... patches still apply on top, so no conflict there.

    with tempfile.TemporaryDirectory(prefix="zc_conflicts_") as tmp:
        for target, entries in patches.items():
            es = distinct(entries)
            if len(es) < 2:
                continue
            paths = []
            for e in es:
                local = lister.extract(e["file"], e["inner"], tmp)
                if not local:
                    paths.append(None)
                    continue
                try:
                    paths.append(patch_paths(cfg_parse.read_text(local)))
                except Exception as err:  # noqa: BLE001
                    errors.append(f"{e['inner']}: {err}")
                    paths.append(None)
            if any(p is None for p in paths):
                emit("cfg", target, es, "tie",
                     "Several mods patch this file; their patches could not all be read, so fields may overlap.")
                continue
            for i in range(len(es)):
                for j in range(i + 1, len(es)):
                    for hit in sorted(overlap(paths[i], paths[j]))[:20]:
                        pair = [es[i], es[j]]
                        top = sorted(pair, key=mount_key, reverse=True)
                        emit("cfg", f"{target} › {' › '.join(hit)}", pair, "wins",
                             f"Both patch this field; {top[0]['mod']['name']} loads later and wins it.")

    order = {"risky": 0, "tie": 1, "wins": 2, "same": 3}
    conflicts.sort(key=lambda c: (not c["isYours"], order[c["verdict"]], c["what"]))
    out_mods = [{"name": m["name"], "files": counts.get(id(m), 0), "order": m["order"], "isYours": m["isYours"],
                 "source": m["source"]} for m in mods]
    return {"mods": sorted(out_mods, key=lambda m: (not m["isYours"], m["name"].lower())), "conflicts": conflicts,
            "errors": errors}


def your_containers(root):
    """A mod folder's packaged files: its release candidate copy, else the kit's last staged output."""
    try:
        with open(os.path.join(root, "mod.json"), encoding="utf-8-sig") as f:
            mod = json.load(f)
    except (OSError, ValueError):
        mod = {}
    rel = (mod.get("release") or {}).get("folder") or "ReleaseCandidate"
    rc = rel if os.path.isabs(rel) else os.path.join(root, rel)
    found = []
    if os.path.isdir(rc):
        found = [os.path.join(rc, f) for f in os.listdir(rc) if f.lower().endswith(CONTAINERS)]
    name = mod.get("name") or os.path.basename(os.path.normpath(root))
    if not found and KIT:
        staged = os.path.join(KIT, "Stalker2", "SavedMods", "Staged", name)
        for dp, _, fs in os.walk(staged):
            found += [os.path.join(dp, f) for f in fs if f.lower().endswith(CONTAINERS)]
    return name, found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["scan"])
    ap.add_argument("--mods", help="the game's ~mods folder (default: from the machine settings)")
    ap.add_argument("--no-installed", action="store_true", help="leave the installed mods out")
    ap.add_argument("--yours", action="append", default=[], help="a mod folder of yours (repeatable)")
    ap.add_argument("--collection", action="append", default=[], help="a folder of paks to check together (repeatable)")
    ap.add_argument("--only-yours", action="store_true", help="only conflicts a mod of yours is part of")
    ap.add_argument("--listing", help="test: a JSON file {container file name: {inner path: sha1}}")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    sources = []
    yours_names = set()
    for root in a.yours:
        name, cs = your_containers(root)
        if cs:
            sources.append((f"yours: {name}", cs, True))
            yours_names.add(name.lower())
    for c in a.collection:
        sources.append((f"collection: {c}", c, False))
    mods_dir = a.mods or (MODS_DIR if CFG.get("game") else "")
    if not a.no_installed and mods_dir:
        sources.append(("installed", mods_dir, False))
    if a.listing and not sources:
        sources.append(("test", list(json.load(open(a.listing, encoding="utf-8")).keys() - {"__text__"}), False))

    lister = Lister(a.listing)
    mods = gather(sources)
    for m in mods:
        if m["name"].lower() in yours_names:
            m["isYours"] = True
    report = scan(mods, lister, a.only_yours)
    lister.save()
    report["atMs"] = int(time.time() * 1000)
    report["sources"] = [s[0] for s in sources]
    if not sources:
        report["errors"].append("Nothing to scan: the game is not set up and no mod or collection was given.")
    if a.json:
        print(json.dumps(report))
        return 0
    for c in report["conflicts"]:
        print(f"[{c['verdict']:5}] {c['kind']:8} {c['what']}")
        for i, m in enumerate(c["mods"]):
            print(f"         {'wins ' if i == 0 else '     '}{m['name']} ({m['file']}, order {m['order']})")
        print(f"         {c['note']}")
    print(f"{len(report['mods'])} mods, {len(report['conflicts'])} conflicts")
    for e in report["errors"]:
        print("error:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
