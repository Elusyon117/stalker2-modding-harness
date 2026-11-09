r"""What the zonecraft band and Logs panel show: packaging progress, the game's and the kit's logs, crashes.

    py -I zcwatch.py poll [--mod-root DIR] [--kit DIR] [--game DIR] [--state FILE]

One call reads only what changed since the last one (offsets kept in the state file, default
%LOCALAPPDATA%\zonecraft\watch\state.json) and prints one JSON object:

    package  the latest packaging (the editor's Package Mod, cook_and_install.ps1, a Workshop upload):
             active, phase, mod, startedMs, endedMs, result ok|failed, progress [done, total], errors, log
    rc       the release candidate copy made after a successful packaging (mod.json "release".auto)
    game     {running}; editor {running}
    events   new log lines worth seeing: crash, patch (cfg patches), data (broken game data), mount, text, error
    crash    a new crash report: when, message, first stack lines, family and advice (crash_rules.json)

Packaging is found from the AutomationTool logs (%APPDATA%\Unreal Engine\AutomationTool\Logs\*\Log.txt,
<kit>\Engine\Programs\AutomationTool\Saved\Logs\Log.txt), cook_and_install's %TEMP%\<Mod>_cook.log and the
running processes. The markers are GSC's and UE's usual log lines; a kit update may change them (then edit PHASES).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "build"))
try:
    import hconf  # noqa: E402
except Exception:  # pragma: no cover
    hconf = None
import release_candidate as RC  # noqa: E402

TAIL = 256 * 1024          # bytes read from a log seen for the first time
ACTIVE_S = 25              # a packaging log written within this many seconds counts as running
MAX_EVENTS = 40

PHASES = [  # (regex, phase) checked in order on each new line; the last match wins
    (r"GSCCookMod|BuildCookRun|Parsing command line", "Starting"),
    (r"-modcooknewcontent", "Cooking new content"),
    (r"-modcookoverridecontent", "Cooking override content"),
    (r"Running UnrealPak|UnrealPak\.exe|IoStore|Creating pak", "Packing"),
    (r"\*+ STAGE COMMAND|Staging|Copying .* to staging", "Staging"),
    (r"install_paktest|Installing test pak|~mods", "Installing the test copy"),
    (r"Workshop|SteamUGC|Uploading", "Uploading"),
    (r"mod\.io|modio", "Uploading to mod.io"),
]
PROGRESS = re.compile(r"Cooked packages (\d+) Packages Remain (\d+) Total (\d+)", re.I)
EXIT = re.compile(r"(?:AutomationTool exiting with ExitCode=|ExitCode=|exit code[: ]+)(-?\d+)", re.I)
DONE_OK = re.compile(r"BUILD SUCCESSFUL|Cook and install done|Installed .*PakTest", re.I)
DONE_BAD = re.compile(r"BUILD FAILED|AutomationException|cook failed", re.I)
ERROR = re.compile(r"\bError:|\bERROR\b|: error ", re.I)
MODNAME = re.compile(r"-ModName=(\w+)|-Mod=(\w+)|-Plugin=.*?(\w+)\.uplugin", re.I)

LOG_RULES = [  # (regex, kind, level)
    (r"Fatal error|Unhandled Exception|EXCEPTION_ACCESS_VIOLATION|Assertion failed|Critical error", "crash", "bad"),
    (r"LogParserNodePatching.*\b(Error|Warning)\b", "patch", "warn"),
    (r"BrokenGameData|Broken Game Data|can't find SID|links on empty", "data", "warn"),
    (r"LogModTextToolManager.*\b(Error|Warning)\b", "text", "warn"),
    (r"LogModKitGameFeaturesManager.*\b(Error|Warning)\b", "mod", "warn"),
    (r"LogPakFile.*Mount|Mounted (IoStore|pak)|Mounting pak", "mount", "info"),
    (r"\bError:|\bFatal\b", "error", "bad"),
]
PROCS = {"game": ("stalker2-win64-shipping.exe",),
         "editor": ("stalker2modeditor-win64-shipping.exe", "stalker2modeditor.exe"),
         "cook": ("stalker2modeditor-win64-shipping-cmd.exe", "unrealpak.exe", "automationtool.exe")}


def now_ms():
    return int(time.time() * 1000)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if default is None else default


def default_state():
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "zonecraft", "watch", "state.json")


def read_new(path, offsets):
    """New lines of a log since the last read (a shrunk or replaced file is read again from its tail)."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return []
    start = offsets.get(path)
    if start is None or start > size:
        start = max(0, size - TAIL)
    if size == start:
        offsets[path] = size
        return []
    with open(path, "rb") as f:
        f.seek(start)
        data = f.read(size - start)
    offsets[path] = size
    text = data.decode("utf-8", errors="replace")
    if text and data[:3] == b"\xef\xbb\xbf":
        text = text[1:]
    if "\x00" in text[:200]:  # UTF-16 log
        text = data.decode("utf-16-le", errors="replace")
    lines = text.splitlines()
    if start > 0 and lines and start == max(0, size - TAIL):
        lines = lines[1:]  # first line was cut mid-way
    return lines


def processes():
    """Lower-case image names of running processes (Windows; empty elsewhere)."""
    if os.name != "nt":
        return set()
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.split('","')[0].strip('"').lower() for line in out.splitlines() if line.startswith('"')}


def running(procs, kind):
    return any(p in procs for p in PROCS[kind])


def package_logs(kit, mod_name):
    cands = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands += glob.glob(os.path.join(appdata, "Unreal Engine", "AutomationTool", "Logs", "*", "Log.txt"))
    if kit:
        cands.append(os.path.join(kit, "Engine", "Programs", "AutomationTool", "Saved", "Logs", "Log.txt"))
    temp = os.environ.get("TEMP")
    if temp and mod_name:
        cands.append(os.path.join(temp, f"{mod_name}_cook.log"))
    return [p for p in cands if os.path.exists(p)]


def update_package(pkg, lines, log, mtime_ms, cook_running, t):
    """Advance the packaging state with new lines of its log."""
    fresh = t - mtime_ms < ACTIVE_S * 1000
    if lines and (not pkg.get("active")) and (fresh or cook_running):
        starts = any(re.search(PHASES[0][0], l, re.I) for l in lines) or pkg.get("log") != log or pkg.get("endedMs")
        if starts:
            pkg.clear()
            pkg.update({"active": True, "phase": "Starting", "startedMs": t, "log": log, "errors": [], "lines": 0})
    if not pkg.get("active"):
        return pkg
    for line in lines:
        pkg["lines"] = pkg.get("lines", 0) + 1
        for rx, phase in PHASES:
            if re.search(rx, line, re.I):
                pkg["phase"] = phase
        m = MODNAME.search(line)
        if m and not pkg.get("mod"):
            pkg["mod"] = next(g for g in m.groups() if g)
        m = PROGRESS.search(line)
        if m:
            done, remain, total = (int(x) for x in m.groups())
            pkg["progress"] = [done, total or done + remain]
        if ERROR.search(line) and not re.search(r"\b0 error", line, re.I):
            pkg["errors"] = (pkg.get("errors", []) + [line.strip()[:300]])[-6:]
        if line.strip():
            pkg["last"] = line.strip()[:200]
        m = EXIT.search(line)
        if m or DONE_OK.search(line) or DONE_BAD.search(line):
            code = int(m.group(1)) if m else (0 if DONE_OK.search(line) else 1)
            pkg.update({"active": False, "endedMs": t, "result": "ok" if code == 0 else "failed", "exitCode": code})
            break
    if pkg.get("active") and not fresh and not cook_running and t - pkg.get("startedMs", t) > ACTIVE_S * 1000:
        # the log stopped and nothing is cooking: it ended without a marker we know
        pkg.update({"active": False, "endedMs": t, "result": "failed" if pkg.get("errors") else "ok",
                    "note": "ended without an exit line; result guessed from the errors seen"})
    return pkg


def classify_line(line):
    for rx, kind, level in LOG_RULES:
        if re.search(rx, line, re.I):
            return kind, level
    return None


def log_events(lines, source, mod_name, seen):
    out = []
    for line in lines:
        c = classify_line(line)
        if not c:
            continue
        kind, level = c
        text = line.strip()[:400]
        if kind == "mount" and not (mod_name and mod_name.lower() in text.lower()) and "~mods" not in text.lower():
            continue
        key = re.sub(r"\[[^\]]*\]|\d+", "", text)[:200]  # same message, other timestamp or numbers
        if key in seen:
            continue
        seen.append(key)
        out.append({"kind": kind, "level": level, "source": source, "text": text})
    del seen[:-200]
    return out


def crash_rules():
    return read_json(os.path.join(HERE, "crash_rules.json")).get("rules", [])


def classify_crash(text, rules=None):
    for r in rules if rules is not None else crash_rules():
        if re.search(r["match"], text, re.I):
            return r["family"], r["advice"]
    return "Unknown", "Not a known crash family. Read the log's last lines and the call stack (diagnostics.md)."


def xml_tag(text, tag):
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S)
    if not m:
        return ""
    return re.sub(r"&lt;|&gt;|&amp;|&quot;|&apos;", lambda x: {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&quot;": '"',
                                                            "&apos;": "'"}[x.group(0)], m.group(1)).strip()


def new_crash(saved, since_ms, game):
    """The newest crash report (game Saved/Crashes, or a UE4SS dump) newer than since_ms."""
    best = None
    for d in glob.glob(os.path.join(saved, "Crashes", "*")):
        if os.path.isdir(d):
            t = int(os.path.getmtime(d) * 1000)
            if t > since_ms and (best is None or t > best[0]):
                best = (t, d)
    dumps = glob.glob(os.path.join(game, "Stalker2", "Binaries", "Win64", "ue4ss", "crash_*.dmp")) if game else []
    for p in dumps:
        t = int(os.path.getmtime(p) * 1000)
        if t > since_ms and (best is None or t > best[0]):
            best = (t, p)
    if not best:
        return None
    t, path = best
    message, stack = "", []
    if os.path.isdir(path):
        for name in ("CrashContext.runtime-xml",):
            p = os.path.join(path, name)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    x = f.read()
                message = xml_tag(x, "ErrorMessage")
                stack = [s.strip() for s in xml_tag(x, "CallStack").splitlines() if s.strip()][:10]
        if not message:
            logs = glob.glob(os.path.join(path, "*.log"))
            if logs:
                with open(logs[0], encoding="utf-8", errors="replace") as f:
                    tail = f.read()[-20000:].splitlines()
                hits = [l for l in tail if classify_line(l) and classify_line(l)[0] == "crash"]
                message = hits[-1].strip() if hits else (tail[-1] if tail else "")
    else:
        message = "UE4SS wrote a crash dump: " + os.path.basename(path)
        stack = ["ue4ss"]
    family, advice = classify_crash(message + "\n" + "\n".join(stack))
    return {"atMs": t, "path": path, "message": message[:600], "stack": stack, "family": family, "advice": advice}


def poll(mod_root, kit, game, state_path, t=None):
    t = t or now_ms()
    st = read_json(state_path, {"offsets": {}, "package": {}, "seen": [], "crashMs": 0})
    st.setdefault("offsets", {})
    st.setdefault("package", {})
    st.setdefault("seen", [])
    if not st.get("crashMs"):
        st["crashMs"] = t  # do not report crashes from before the first poll
    mod = read_json(os.path.join(mod_root, "mod.json")) if mod_root else {}
    mod_name = mod.get("name", "")
    procs = processes()
    out = {"atMs": t, "game": {"running": running(procs, "game")}, "editor": {"running": running(procs, "editor")},
           "events": [], "crash": None, "rc": None}

    # packaging: follow the most recently written packaging log
    logs = package_logs(kit, mod_name)
    if logs:
        log = max(logs, key=os.path.getmtime)
        lines = read_new(log, st["offsets"])
        for other in logs:  # keep the others' offsets current so an old run is not replayed later
            if other != log:
                read_new(other, st["offsets"])
        update_package(st["package"], lines, log, int(os.path.getmtime(log) * 1000), running(procs, "cook"), t)
    out["package"] = {k: v for k, v in st["package"].items() if k != "lines"}

    # release candidate after a successful packaging of this mod
    pkg = st["package"]
    if mod_name and kit and pkg.get("result") == "ok" and (not pkg.get("mod") or pkg["mod"] == mod_name):
        rel = RC.settings(mod)
        try:
            if "release" in mod and rel.get("auto") and RC.needs_copy(kit, mod_root, mod):
                dest, info = RC.copy(kit, mod_root, mod)
                out["rc"] = {"folder": dest, **info, "isNew": True}
            elif "release" in mod:
                last = RC.last_copy(mod_root, mod)
                pending = RC.needs_copy(kit, mod_root, mod)
                out["rc"] = {"folder": RC.rc_folder(mod_root, mod), **last, "isNew": False, "pending": pending}
        except OSError as err:
            out["rc"] = {"error": str(err)}

    # logs: the game's and the kit's (same Saved folder), only new lines
    local = os.environ.get("LOCALAPPDATA") or ""
    saved = os.path.join(local, "Stalker2", "Saved")
    for path in glob.glob(os.path.join(saved, "Logs", "*.log")):
        name = os.path.basename(path)
        if "backup" in name.lower():
            continue
        source = "kit" if "editor" in name.lower() else "game"
        out["events"] += log_events(read_new(path, st["offsets"]), source, mod_name, st["seen"])
    out["events"] = out["events"][-MAX_EVENTS:]

    crash = new_crash(saved, st["crashMs"], game)
    if crash:
        st["crashMs"] = crash["atMs"]
        out["crash"] = crash

    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(st, f)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["poll"])
    ap.add_argument("--mod-root", default=None)
    ap.add_argument("--kit", default=None)
    ap.add_argument("--game", default=None)
    ap.add_argument("--state", default=default_state())
    a = ap.parse_args(argv)
    kit = a.kit if a.kit is not None else (hconf.KIT if hconf else "")
    game = a.game if a.game is not None else ((hconf.CFG.get("game") or "") if hconf else "")
    root = a.mod_root
    if root is None and hconf and os.path.exists(os.path.join(hconf.REPO, "mod.json")):
        root = hconf.REPO
    print(json.dumps(poll(root or "", kit, game, a.state)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None
    main()
