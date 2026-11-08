"""Find zonecraft and put its tool folders on sys.path, so this mod's generators can `import bp_nodes`.

    import zonecraft_path  # noqa: F401  (first import in every zonekit/tools/gen_*.py)
    from bp_graph import Graph
    from bp_nodes import Nodes

Looks in this order: $ZONECRAFT_ROOT (a zonecraft checkout), then the newest zonecraft installed as a Claude Code
plugin (~/.claude/plugins/cache/<marketplace>/zonecraft/<version>).
"""
import glob
import os
import sys


def _version_key(path):
    parts = []
    for p in os.path.basename(path).split("."):
        parts.append(int(p) if p.isdigit() else -1)
    return parts


def find():
    root = os.environ.get("ZONECRAFT_ROOT")
    if root and os.path.isdir(os.path.join(root, "tools")):
        return os.path.abspath(root)
    found = glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "plugins", "cache", "*", "zonecraft", "*"))
    found = [f for f in found if os.path.isdir(os.path.join(f, "tools"))]
    if not found:
        raise SystemExit("zonecraft not found: install the plugin (/plugin install zonecraft --marketplace "
                         "Elusyon117/zonecraft) or set ZONECRAFT_ROOT to a zonecraft checkout.")
    return max(found, key=_version_key)


ROOT = find()
for sub in ("blueprints", ""):
    path = os.path.join(ROOT, "tools", sub)
    if path not in sys.path:
        sys.path.insert(0, path)
