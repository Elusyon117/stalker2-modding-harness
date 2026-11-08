r"""Shared config for the zonecraft Python tools that run OUTSIDE the editor (kit Python or any Python 3).

    from hconf import CFG, REPO, MOD, KIT, GAME, MODS_DIR, TOOLS, ZONECRAFT

TOOLS = this folder, ZONECRAFT = the plugin root. REPO = the mod folder: the nearest folder holding mod.json, walking up
from the current folder (or $ZONECRAFT_MOD_DIR), else the current folder. CFG = tools/config.json < machine settings
(%LOCALAPPDATA%\zonecraft\settings.json, after the original harness's settings file) < <mod>/zonecraft.local.json;
MOD = mod.json (or {}). Editor-side scripts do not import this: ue_exec.py / run_headless.ps1 prepend a prelude with
the same values.
"""
import json
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))
ZONECRAFT = os.path.dirname(TOOLS)


def _find_mod_root():
    if os.environ.get("ZONECRAFT_MOD_DIR"):
        return os.path.abspath(os.environ["ZONECRAFT_MOD_DIR"])
    d = os.getcwd()
    while True:
        if os.path.exists(os.path.join(d, "mod.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.getcwd()
        d = parent


REPO = _find_mod_root()


def _read(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


_LOCAL = os.environ.get("LOCALAPPDATA", "")
CFG = _read(os.path.join(TOOLS, "config.json"))
CFG.update(_read(os.path.join(_LOCAL, "stalker2-modding-harness", "settings.json")))
CFG.update(_read(os.path.join(_LOCAL, "zonecraft", "settings.json")))
CFG.update(_read(os.path.join(REPO, "zonecraft.local.json")))
MOD = _read(os.path.join(REPO, "mod.json"))
KIT = CFG.get("kit", "")
GAME = os.path.join(CFG.get("game", ""), "Stalker2")
MODS_DIR = os.path.join(GAME, "Content", "Paks", "~mods")
SCRATCH = os.environ.get("ZONECRAFT_SCRATCH") or os.environ.get("HARNESS_SCRATCH") or os.path.join(os.environ.get("TEMP", "/tmp"), "zonecraft")


def prelude(mod_name=None, args=None):
    """Python source defining the values editor scripts rely on (MOD, MOD_ROOT, UPLUGIN, KIT, SCRATCH, REPO)
    plus ARGS, a dict of the caller's --arg KEY=VALUE pairs (scripts read e.g. ARGS["SRC"])."""
    name = mod_name or MOD.get("name", "")
    vals = {
        "MOD": name,
        "MOD_ROOT": "/" + name if name else "",
        "SHORT": MOD.get("short", name),
        "UPLUGIN": f"{KIT}/Stalker2/Mods/{name}/{name}.uplugin".replace("\\", "/"),
        "KIT": KIT.replace("\\", "/"),
        "REPO": REPO.replace("\\", "/"),
        "SCRATCH": SCRATCH.replace("\\", "/"),
        "ARGS": dict(args or {}),
    }
    return "".join(f"{k} = {v!r}\n" for k, v in vals.items()) + "# ---- end zonecraft prelude ----\n"


def require(*keys):
    """Exit with a clear message when this PC has not been set up (config.json ships empty per-user values)."""
    missing = [k for k in keys if not CFG.get(k)]
    if missing:
        raise SystemExit(f"Not set up on this PC yet ({', '.join(missing)} missing). "
                         "Ask Claude to set up zonecraft (tools/setup/setup.ps1).")
