r"""Game data index: look up any .cfg prototype of the game (and the current mod) without grepping.

    py -I gamedata.py build [--kit DIR]          index the kit's GameLite/GameData + DLCGameData (+ texts); ~minutes
    py -I gamedata.py status                     when it was built, counts, whether the kit changed since
    py -I gamedata.py find <SID|Name> [--raw] [--depth N] [--field RE]
                                                 where it is, inheritance chain, resolved fields, DLC copies, the
                                                 mod's patches to it, in-game name, where a patch for it goes
    py -I gamedata.py search <text> [--in FILE_RE] [--limit N]
                                                 SIDs / struct names / in-game names containing the text
    py -I gamedata.py kids <SID|Name>            prototypes that inherit from it (they keep their own overrides)
    py -I gamedata.py patch <SID|Name> --set Path=Value [--set ...] [--remove Path]
                                                 a ready {bpatch} patch and the file it belongs in, checked against
                                                 the resolved struct (unknown paths are flagged)

The index lives per machine in %LOCALAPPDATA%\zonecraft\gamedata\index.sqlite (never in a repo). The current mod's
own cfgs (kit plugin folder, else the repo mirror zonekit/<Mod>/) are read live on every query, so they never go
stale. Rebuild after a Zone Kit update (status says so). Fields are resolved by following refkey/refurl; that merge
is an approximation of the game's, good for reading values, not a substitute for testing.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfg_parse as C  # noqa: E402

try:
    import hconf  # noqa: E402
except Exception:  # pragma: no cover
    hconf = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIRS = ("GameLite/GameData", "GameLite/DLCGameData")
MOD_DATA_DIRS = ("GameLite/GameData", "GameLite/DLCGameData", "GameLite/ModGameData")
TEXT_DB = "TextToolBackup/TextDatabase.json"
CFG_FILE = re.compile(r"\.cfg($|_patch_)", re.I)


def default_db():
    base = os.environ.get("ZONECRAFT_GAMEDATA_DB")
    if base:
        return base
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "zonecraft", "gamedata",
                        "index.sqlite")


def kit_exe(kit):
    return os.path.join(kit, "Stalker2", "Binaries", "Win64", "Stalker2ModEditor-Win64-Shipping.exe")


# ---------------------------------------------------------------------------------------------------- file roles
def classify(rel, known):
    """Return (base, is_patch_file). base = the vanilla cfg this file belongs to or patches (rel to Content).
    known = {lowercased rel: rel} of the game's own cfg files.

    X.cfg_patch_Y                     -> X.cfg (a patch)
    a vanilla *Prototypes.cfg         -> itself (also when it sits inside another prototype's folder)
    D/P/.../F.cfg, D/P.cfg is vanilla -> D/P.cfg (deepest such folder; vanilla: a part of it, in a mod: a patch)
    D/XPrototypes/.../F.cfg           -> D/XPrototypes.cfg even when that file does not exist (SpawnActorPrototypes)
    anything else                     -> itself
    """
    rel = rel.replace("\\", "/")
    m = re.match(r"(.*\.cfg)_patch_.*$", rel, re.I)
    if m and (m.group(1).lower() in known or not known):
        return known.get(m.group(1).lower(), m.group(1)), True
    stem = os.path.splitext(os.path.basename(rel))[0]
    if rel.lower() in known and stem.endswith("Prototypes"):
        return rel, False
    parts = rel.split("/")
    for i in range(len(parts) - 1, 2, -1):
        cand = "/".join(parts[:i]) + ".cfg"
        if cand.lower() in known:
            return known[cand.lower()], False
    for i in range(len(parts) - 1, 2, -1):
        if parts[i - 1].endswith("Prototypes"):
            return "/".join(parts[:i]) + ".cfg", False
    return rel, bool(m)


def walk_cfgs(content_root, dirs):
    for d in dirs:
        top = os.path.join(content_root, d)
        for dirpath, _dirs, files in os.walk(top):
            for f in files:
                if CFG_FILE.search(f):
                    full = os.path.join(dirpath, f)
                    yield os.path.relpath(full, content_root).replace("\\", "/"), full


def scan_file(full):
    try:
        lines = C.read_text(full).splitlines()
    except OSError:
        return []
    return list(C.scan_top(lines))


def entries_for(content_root, dirs, src, game_files):
    files = list(walk_cfgs(content_root, dirs))
    known = game_files if src == "mod" else {rel.lower(): rel for rel, _ in files
                                             if not re.search(r"_patch_", rel, re.I)}
    out = []
    for rel, full in files:
        base, patchfile = classify(rel, known)
        in_mod_override = src == "mod" and not rel.startswith("GameLite/ModGameData")
        for e in scan_file(full):
            out.append({
                "name": e["name"], "sid": e["sid"], "file": rel, "line": e["line"], "end": e["end"],
                "refurl": e["attrs"].get("refurl") if isinstance(e["attrs"].get("refurl"), str) else None,
                "refkey": e["attrs"].get("refkey") if isinstance(e["attrs"].get("refkey"), str) else None,
                "bpatch": 1 if "bpatch" in e["attrs"] else 0, "removenode": 1 if e["removenode"] else 0,
                "src": src if src != "game" else ("dlc" if rel.startswith("GameLite/DLCGameData") else "game"),
                "base": base, "is_patch": 1 if (patchfile or in_mod_override or "bpatch" in e["attrs"]
                                                or e["removenode"]) else 0,
            })
    return out


# ---------------------------------------------------------------------------------------------------------- texts
EN_KEYS = ("en", "EN", "En", "english", "English", "eng", "Text", "text", "Value", "value")
SID_KEYS = ("SID", "Sid", "sid", "Key", "key", "ID", "Id", "id", "StringSID", "TextSID")


def load_texts(path):
    """Best effort over an unknown JSON layout: collect (key, English text) pairs."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return [], "not found or not JSON"
    out = {}

    def english(v):
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for k in EN_KEYS:
                if isinstance(v.get(k), str):
                    return v[k]
        return None

    def walk(o, depth=0):
        if depth > 12:
            return
        if isinstance(o, dict):
            sid = next((o[k] for k in SID_KEYS if isinstance(o.get(k), str)), None)
            if sid:
                for k in EN_KEYS + ("Localization", "Localizations", "Texts", "Translations"):
                    t = english(o.get(k)) if k in o else None
                    if t and t != sid:
                        out.setdefault(sid, t)
                        break
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)

    walk(data)
    if not out and isinstance(data, dict):  # flat {key: text} or {lang: {key: text}}
        flat = data.get("en") or data.get("English") or data
        if isinstance(flat, dict):
            out = {k: v for k, v in flat.items() if isinstance(v, str)}
    note = f"{len(out)} texts" if out else ("format not recognised; top-level: " +
                                            ", ".join(list(data)[:8]) if isinstance(data, dict) else type(data).__name__)
    return list(out.items()), note


# ----------------------------------------------------------------------------------------------------------- build
SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE entry(name TEXT, sid TEXT, file TEXT, line INT, "end" INT, refurl TEXT, refkey TEXT, bpatch INT,
                   removenode INT, src TEXT, base TEXT, is_patch INT);
CREATE TABLE text(key TEXT PRIMARY KEY, en TEXT);
CREATE INDEX entry_name ON entry(name COLLATE NOCASE);
CREATE INDEX entry_sid ON entry(sid COLLATE NOCASE);
CREATE INDEX entry_refkey ON entry(refkey COLLATE NOCASE);
CREATE INDEX entry_base ON entry(base);
"""
COLS = ("name", "sid", "file", "line", "end", "refurl", "refkey", "bpatch", "removenode", "src", "base", "is_patch")


def build(kit, db_path):
    content = os.path.join(kit, "Stalker2", "Content")
    if not os.path.isdir(os.path.join(content, "GameLite", "GameData")):
        raise SystemExit(f"No GameLite/GameData under {content}: is the kit path right? (--kit)")
    t0 = time.time()
    entries = entries_for(content, DATA_DIRS, "game", {})
    texts, note = load_texts(os.path.join(content, TEXT_DB))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    tmp = db_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA)
    con.executemany(f"INSERT INTO entry VALUES ({','.join('?' * len(COLS))})",
                    [tuple(e[c] for c in COLS) for e in entries])
    con.executemany("INSERT OR IGNORE INTO text VALUES (?, ?)", texts)
    exe = kit_exe(kit)
    meta = {"kit": kit, "built": str(int(time.time())), "kit_exe_mtime": str(int(os.path.getmtime(exe)))
            if os.path.exists(exe) else "", "entries": str(len(entries)), "files": str(len({e["file"] for e in entries})),
            "texts_note": note}
    con.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
    con.commit()
    con.close()
    os.replace(tmp, db_path)
    print(f"Indexed {meta['entries']} prototypes in {meta['files']} files, texts: {note} "
          f"({time.time() - t0:.0f} s) -> {db_path}")


# ----------------------------------------------------------------------------------------------------------- query
class Index:
    def __init__(self, db_path, kit=None, mod=None, mod_content=None):
        if not os.path.exists(db_path):
            raise SystemExit("No game data index on this PC yet: run `gamedata.py build` (needs the Zone Kit).")
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.meta = dict(self.con.execute("SELECT key, value FROM meta").fetchall())
        self.kit = kit or self.meta.get("kit", "")
        self.game_content = os.path.join(self.kit, "Stalker2", "Content")
        self.mod, self.mod_content = mod, mod_content
        self.mod_entries = []
        if mod_content and os.path.isdir(mod_content):
            game_files = {r["file"].lower(): r["file"] for r in self.con.execute(
                "SELECT DISTINCT file FROM entry WHERE file NOT LIKE '%\\_patch\\_%' ESCAPE '\\'")}
            self.mod_entries = entries_for(mod_content, MOD_DATA_DIRS, "mod", game_files)
        self._lines = {}

    # rows are dicts: one shape for game rows and mod rows
    def _rows(self, where, args):
        rows = [dict(r) for r in self.con.execute(f"SELECT * FROM entry WHERE {where}", args)]
        return rows

    def _mod(self, pred):
        return [e for e in self.mod_entries if pred(e)]

    def lookup(self, key):
        k = key.lower()
        rows = self._rows("sid = ? COLLATE NOCASE OR name = ? COLLATE NOCASE", (key, key))
        rows += self._mod(lambda e: (e["sid"] or "").lower() == k or e["name"].lower() == k)
        return rows

    def stale(self):
        exe = kit_exe(self.kit)
        if os.path.exists(exe) and self.meta.get("kit_exe_mtime"):
            return int(os.path.getmtime(exe)) > int(self.meta["kit_exe_mtime"])
        return False

    def path_of(self, row):
        root = self.mod_content if row["src"] == "mod" else self.game_content
        return os.path.join(root, row["file"]).replace("/", os.sep)

    def node(self, row):
        p = self.path_of(row)
        if p not in self._lines:
            self._lines[p] = C.read_text(p).splitlines()
        text = "\n".join(self._lines[p][row["line"] - 1:row["end"]])
        root = C.parse(text, row["line"])
        if root.items and root.items[0][1] is C.REMOVED:
            return C.REMOVED
        return root.items[0][1] if root.items else None

    def parent_row(self, row):
        key = row.get("refkey")
        if not key:
            return None
        if row.get("refurl"):
            target = os.path.normpath(os.path.join(os.path.dirname(row["file"]), row["refurl"])).replace("\\", "/")
            mine = [e for e in self.mod_entries if e["name"] == key and not e["is_patch"]
                    and target.lower() in (e["file"].lower(), e["base"].lower())]
            if mine:
                return mine[0]
            cands = self._rows("name = ? AND (file = ? COLLATE NOCASE OR base = ? COLLATE NOCASE) AND is_patch = 0",
                               (key, target, target))
            if cands:
                return cands[0]
            base = classify(target, {})[0]
            cands = self._rows("name = ? AND base = ? COLLATE NOCASE AND is_patch = 0", (key, base))
            if cands:
                return cands[0]
        same = [e for e in (self.mod_entries if row["src"] == "mod" else [])
                if e["file"] == row["file"] and e["name"] == key and e is not row]
        if same:
            return same[0]
        cands = self._rows("name = ? AND file = ? AND is_patch = 0 AND line <> ?", (key, row["file"], row["line"]))
        if not cands:
            cands = self._rows("name = ? AND base = ? AND is_patch = 0", (key, row["base"]))
        if not cands:
            cands = self._rows("name = ? AND is_patch = 0", (key,))
            if len(cands) > 1:
                cands = [c for c in cands if c["src"] == row["src"]] or cands
        return cands[0] if cands else None

    def resolve(self, row, depth=0):
        """(resolved node, chain of rows from row up to the root parent)."""
        own = self.node(row)
        if own is C.REMOVED or own is None or depth > 25:
            return own, [row]
        parent = self.parent_row(row)
        if parent is None or (parent["file"], parent["line"]) == (row["file"], row["line"]):
            return own.copy(), [row]
        pnode, chain = self.resolve(parent, depth + 1)
        return C.inherit(own, pnode if isinstance(pnode, C.Node) else None), [row] + chain

    def patches_to(self, row):
        """Patch entries (the mod's, and vanilla bpatch ones) aimed at the same struct."""
        return [e for e in self.mod_entries if e["name"] == row["name"] and e["is_patch"]
                and e["base"].lower() == row["base"].lower()]

    def text(self, key):
        r = self.con.execute("SELECT en FROM text WHERE key = ? COLLATE NOCASE", (key,)).fetchone()
        return r[0] if r else None

    def name_of(self, sid, node):
        keys = []
        if isinstance(node, C.Node):
            for k, v in node.items:
                if isinstance(v, str) and re.search(r"(TextKey|LocalizationSID|NameSID|TitleSID|NameKey)$", k):
                    keys.append(v)
        keys += [sid, f"sid_character_{sid}", f"sid_items_{sid}_name", f"sid_items_{sid}"]
        for k in keys:
            t = self.text(k)
            if t:
                return t, k
        r = self.con.execute("SELECT key, en FROM text WHERE key LIKE ? ESCAPE '\\' COLLATE NOCASE LIMIT 1",
                             ("%\\_" + sid.replace("_", "\\_"),)).fetchone()
        return (r[1], r[0]) if r else (None, None)


# ------------------------------------------------------------------------------------------------- patch location
def is_prototype_file(base):
    return os.path.splitext(os.path.basename(base))[0].endswith("Prototypes")


def suggest_patch(row, mod):
    """Where a patch for this struct goes (relative to the mod's Content folder), per GSC's two rules."""
    mod = mod or "<Mod>"
    base = row["base"]
    if row["file"] != base:  # a part file inside a prototype folder: sibling file with the mod's suffix
        d, f = os.path.split(row["file"])
        return f"{d}/{os.path.splitext(f)[0]}_{mod}.cfg"
    if is_prototype_file(base):
        return f"{os.path.splitext(base)[0]}/{mod}.cfg"
    return f"{base}_patch_{mod}"


# ------------------------------------------------------------------------------------------------------------ cli
def pick(rows, key):
    if not rows:
        raise SystemExit(f"'{key}' is not in the index (try `gamedata.py search {key}`).")
    defs = [r for r in rows if not r["is_patch"]]
    game = [r for r in defs if r["src"] == "game"]
    return (game or defs or rows)[0]


def where(ix, r):
    return f"{ix.path_of(r)}:{r['line']}"


def cmd_find(ix, a):
    rows = ix.lookup(a.key)
    row = pick(rows, a.key)
    node, chain = ix.resolve(row)
    print(f"{row['name']}" + (f"  (SID {row['sid']})" if row["sid"] and row["sid"] != row["name"] else ""))
    print(f"  defined   {where(ix, row)}  [{row['src']}]")
    if len(chain) > 1:
        print("  inherits  " + " <- ".join(f"{c['name']} ({os.path.basename(c['file'])})" for c in chain[1:]))
    elif row["refkey"]:
        print(f"  inherits  {row['refkey']} (not found in the index)")
    for r in rows:
        if r is row or (r["file"], r["line"]) == (row["file"], row["line"]):
            continue
        tag = "patch" if r["is_patch"] else "also defined"
        print(f"  {tag:<9} {where(ix, r)}  [{r['src']}]" + ("  removenode" if r["removenode"] else ""))
    name, key = ix.name_of(row["sid"] or row["name"], node)
    if name:
        print(f"  in game   \"{name}\"  (text {key})")
    kids = ix.con.execute("SELECT COUNT(*) FROM entry WHERE refkey = ? COLLATE NOCASE AND is_patch = 0",
                          (row["name"],)).fetchone()[0]
    if kids:
        print(f"  children  {kids} prototypes inherit from it (`gamedata.py kids {row['name']}`); a patch here does "
              "not change fields they override")
    print(f"  patch in  Mods/{ix.mod or '<Mod>'}/Content/{suggest_patch(row, ix.mod)}")
    if row["src"] == "game" and "/DLCGameData/" not in row["file"]:
        dlc = [r for r in rows if r["src"] == "dlc"]
        if dlc:
            print("  note      DLC copies exist: patch those files too")
    if node is C.REMOVED:
        print("  (this entry is a removenode)")
        return
    shown = ix.node(row) if a.raw else node
    for p in ix.patches_to(row) if not a.raw else []:
        pn = ix.node(p)
        shown = C.apply_patch(shown, pn) if pn is not None else shown
    if a.field:
        rx = re.compile(a.field, re.I)
        sub = C.Node(shown.name, shown.attrs)
        sub.items = [it for it in shown.items if rx.search(it[0])]
        shown = sub
    label = "own fields" if a.raw else ("resolved fields" + (" with the mod's patches" if ix.patches_to(row) else ""))
    print(f"--- {label} ---")
    print(C.dump(shown, max_depth=a.depth))


def cmd_search(ix, a):
    like = f"%{a.text}%"
    rx = re.compile(a.within, re.I) if a.within else None
    rows = ix._rows("(sid LIKE ? OR name LIKE ?) AND is_patch = 0 LIMIT ?", (like, like, a.limit * 4))
    rows += ix._mod(lambda e: a.text.lower() in (e["sid"] or e["name"]).lower())
    seen, n = set(), 0
    for r in rows:
        if rx and not rx.search(r["file"]):
            continue
        k = (r["name"], r["file"])
        if k in seen:
            continue
        seen.add(k)
        print(f"{(r['sid'] or r['name']):<40} {r['file']}:{r['line']}  [{r['src']}]")
        n += 1
        if n >= a.limit:
            break
    texts = ix.con.execute("SELECT key, en FROM text WHERE en LIKE ? OR key LIKE ? LIMIT ?",
                           (like, like, a.limit)).fetchall()
    if texts:
        print("--- texts ---")
        for k, t in texts:
            print(f"{k:<40} {t[:90]}")
    if not n and not texts:
        print("No matches.")


def cmd_kids(ix, a):
    row = pick(ix.lookup(a.key), a.key)
    rows = ix._rows("refkey = ? COLLATE NOCASE AND is_patch = 0", (row["name"],))
    rows += ix._mod(lambda e: (e["refkey"] or "").lower() == row["name"].lower() and not e["is_patch"])
    for r in rows:
        print(f"{(r['sid'] or r['name']):<40} {r['file']}:{r['line']}  [{r['src']}]")
    print(f"{len(rows)} prototypes inherit from {row['name']}.")


def cmd_patch(ix, a):
    row = pick(ix.lookup(a.key), a.key)
    node, _ = ix.resolve(row)
    warn = []
    for s in a.set or []:
        if "=" not in s:
            raise SystemExit(f"--set needs Path=Value: {s}")
        path = C.split_path(s.split("=", 1)[0])
        if C.lookup(node, path) is None:
            warn.append(f"{'.'.join(path)} is not in the resolved struct: a typo, or a new field/element")
    for r in a.remove or []:
        if C.lookup(node, C.split_path(r)) is None:
            warn.append(f"{r} does not exist: nothing to remove")
    print(f"# file: Mods/{ix.mod or '<Mod>'}/Content/{suggest_patch(row, ix.mod)}")
    print(C.build_patch(row["name"], a.set or [], a.remove or []))
    for w in warn:
        print(f"# WARNING: {w}")


def cmd_status(ix, a):
    m = ix.meta
    built = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(m.get("built", "0"))))
    print(f"kit {m.get('kit')}\nbuilt {built}: {m.get('entries')} prototypes, {m.get('files')} files, texts: "
          f"{m.get('texts_note')}")
    print(f"mod {ix.mod or '(none)'}: {len(ix.mod_entries)} entries read live from {ix.mod_content or '-'}")
    print("STALE: the Zone Kit was updated after the index was built; run `gamedata.py build`." if ix.stale()
          else "up to date with the kit")


def mod_paths(kit):
    name = (hconf.MOD.get("name") if hconf else "") or ""
    if not name:
        return None, None
    in_kit = os.path.join(kit, "Stalker2", "Mods", name, "Content")
    if os.path.isdir(in_kit):
        return name, in_kit
    mirror = os.path.join(hconf.REPO, "zonekit", name, "Content")
    return name, mirror if os.path.isdir(mirror) else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", default=None)
    ap.add_argument("--db", default=default_db())
    ap.add_argument("--mod", default=None, help="mod name (default: mod.json)")
    ap.add_argument("--mod-content", default=None, help="the mod's Content folder (default: kit plugin, else mirror)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("status")
    p = sub.add_parser("find")
    p.add_argument("key")
    p.add_argument("--raw", action="store_true", help="only the struct's own lines, no inheritance or patches")
    p.add_argument("--depth", type=int, default=4, help="nested struct levels to print")
    p.add_argument("--field", default=None, help="only top-level fields matching this regex")
    p = sub.add_parser("search")
    p.add_argument("text")
    p.add_argument("--in", dest="within", default=None, help="only files matching this regex")
    p.add_argument("--limit", type=int, default=30)
    p = sub.add_parser("kids")
    p.add_argument("key")
    p = sub.add_parser("patch")
    p.add_argument("key")
    p.add_argument("--set", action="append")
    p.add_argument("--remove", action="append")
    a = ap.parse_args(argv)

    kit = a.kit or (hconf.KIT if hconf else "")
    if a.cmd == "build":
        if not kit:
            raise SystemExit("No kit path: set up zonecraft (tools/setup/setup.ps1) or pass --kit.")
        return build(kit, a.db)
    name, content = mod_paths(kit) if kit else (None, None)
    ix = Index(a.db, kit or None, a.mod or name, a.mod_content or content)
    if ix.stale() and a.cmd != "status":
        print("# NOTE: the Zone Kit changed since this index was built; rebuild with `gamedata.py build`.")
    {"find": cmd_find, "search": cmd_search, "kids": cmd_kids, "patch": cmd_patch, "status": cmd_status}[a.cmd](ix, a)


if __name__ == "__main__":
    main()
