"""Check Blueprint paste text before the tester pastes it, and check the graph after they did.

    python harness/tools/t3d/verify_paste.py lint <paste.txt>
    python harness/tools/t3d/verify_paste.py compare <paste.txt> <export.t3d> [--graph EventGraph]
    <kit python> harness/tools/t3d/verify_paste.py compare <paste.txt> --asset /MyMod/Runtime/BP_X [--graph EventGraph]

lint (no editor needed): unique node names and pin ids, every link written on both ends, links to nodes outside
the paste (the editor drops them: the tester wires those by hand, so they are listed), calls the editor drops or
prunes silently (BlueprintInternalUseOnly functions, impure static calls pasted without exec pins).

compare: the paste against the asset's T3D export (tools/editor/export_t3d.py; --asset runs that export through
ue_exec.py first, editor open). Nodes are matched by kind + member + comment, not by name (the editor renames nodes
that collide with deleted, not yet garbage-collected ones), and only nodes in each graph's Nodes(n) list count (the
export also carries deleted nodes). Reports nodes that did not arrive and nodes that arrived with fewer links than
were pasted. Exit code 0 = all there, 1 = something missing, 2 = usage / input problem.
"""
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

BEGIN = re.compile(r'^(\s*)Begin Object (?:Class=(\S+) )?Name="([^"]+)"(?: ExportPath="([^"]+)")?')
LINK = re.compile(r"LinkedTo=\(([^)]*)\)")
PIN = re.compile(r'CustomProperties Pin \(PinId=([0-9A-F]+),PinName="([^"]*)"')

# Functions the editor accepts in K2Node_CallFunction paste text but drops with their links: they are
# BlueprintInternalUseOnly and belong to their own node classes (Ease -> K2Node_EaseFunction, Array_* ->
# K2Node_CallArrayFunction). Add names here when a paste loses one.
INTERNAL_ONLY = {"Ease", "VEase", "REase", "TEase", "Array_Get", "Array_Set", "Array_Add", "Array_Length",
                 "Array_Contains", "Array_Find", "Array_Remove", "Array_Clear"}
# Static library calls known to be impure (BlueprintCallable, not BlueprintPure): pasted without exec pins they are
# pruned at compile time and read 0.
IMPURE_STATIC = {"GetScalarParameterValue", "GetVectorParameterValue", "SetScalarParameterValue",
                 "SetVectorParameterValue", "Delay", "GetAllActorsOfClass", "GetAllWidgetsOfClass",
                 "LoadAsset_Blocking", "LoadClassAsset_Blocking"}


class Block:
    def __init__(self, klass, name, path, indent, parent):
        self.klass, self.name, self.path, self.indent, self.parent = klass, name, path, indent, parent
        self.lines, self.children = [], []


def parse(text):
    """All objects of a paste or an export as Blocks (declaration and definition passes merged by ExportPath)."""
    roots, stack, by_path = [], [], {}
    for raw in text.splitlines():
        m = BEGIN.match(raw)
        if m:
            ind, klass, name, path = len(m.group(1)), m.group(2), m.group(3), m.group(4)
            parent = stack[-1] if stack else None
            key = path or ((parent.path if parent else "") + "/" + name)
            b = by_path.get(key)
            if b is None:
                b = Block(klass, name, key, ind, parent)
                by_path[key] = b
                (parent.children if parent else roots).append(b)
            elif klass and not b.klass:
                b.klass = klass
            stack.append(b)
            continue
        s = raw.strip()
        if s == "End Object":
            if stack:
                stack.pop()
            continue
        if stack and s:
            stack[-1].lines.append(s)
    return roots, list(by_path.values())


def is_node(b):
    k = b.klass or ""
    return "K2Node" in k or "AnimGraphNode" in k or "EdGraphNode_Comment" in k or "AnimStateNode" in k


def short(klass):
    return (klass or "?").rsplit(".", 1)[-1]


def member(b):
    for l in b.lines:
        for pat in (r'FunctionReference=\(.*?MemberName="([^"]+)"', r'VariableReference=\(.*?MemberName="([^"]+)"',
                    r'EventReference=\(.*?MemberName="([^"]+)"', r'DelegateReference=\(.*?MemberName="([^"]+)"',
                    r'^CustomFunctionName="([^"]+)"', r"StandardMacros:(\w+)'", r"^InputAction=.*\.(\w+)'",
                    r"^TargetType=.*[./](\w+)'"):
            m = re.search(pat, l)
            if m:
                return m.group(1)
    return ""


def comment(b):
    for l in b.lines:
        m = re.match(r'NodeComment="(.*)"$', l)
        if m:
            return m.group(1)
    return ""


def sig(b):
    return (short(b.klass), member(b), comment(b))


def pins(b):
    """[(pin_id, pin_name, [(node_name, pin_id), ...], line)]"""
    out = []
    for l in b.lines:
        m = PIN.search(l)
        if not m:
            continue
        lk = LINK.search(l)
        links = [tuple(x.strip().split(" ")) for x in lk.group(1).split(",") if x.strip()] if lk else []
        out.append((m.group(1), m.group(2), links, l))
    return out


def nodes_of_paste(text):
    roots, _ = parse(text)
    return [b for b in roots if is_node(b)]


# ---- lint ------------------------------------------------------------------------------------------------------
def lint(text):
    nodes = nodes_of_paste(text)
    errors, notes = [], []
    names = Counter(b.name for b in nodes)
    errors += [f"node name used {c}x: {n}" for n, c in names.items() if c > 1]
    pin_of = {}
    for b in nodes:
        for pid, pname, _, _ in pins(b):
            if pid in pin_of:
                errors.append(f"pin id reused: {pid} ({b.name}.{pname} and {pin_of[pid][0]}.{pin_of[pid][1]})")
            pin_of[pid] = (b.name, pname)
    by_name = {b.name: b for b in nodes}
    for b in nodes:
        for pid, pname, links, _ in pins(b):
            for ln in links:
                if len(ln) != 2:
                    errors.append(f"bad LinkedTo entry on {b.name}.{pname}: {' '.join(ln)}")
                    continue
                other, opid = ln
                if other not in by_name:
                    notes.append(f"external link {b.name}.{pname} -> {other} (dropped on paste: wire it by hand)")
                    continue
                if opid not in pin_of or pin_of[opid][0] != other:
                    errors.append(f"{b.name}.{pname} links to a pin id {other} does not have: {opid}")
                    continue
                back = [l2 for p2, _, l2, _ in pins(by_name[other]) if p2 == opid]
                if not back or (b.name, pid) not in [tuple(x) for x in back[0]]:
                    errors.append(f"one-sided link {b.name}.{pname} -> {other}.{pin_of[opid][1]} (write both ends)")
        kind, mem, _ = sig(b)
        if kind == "K2Node_CallFunction":
            if mem in INTERNAL_ONLY:
                errors.append(f"{b.name}: {mem} is BlueprintInternalUseOnly; the editor drops it with its links")
            has_exec = any(l.find('PinType.PinCategory="exec"') >= 0 for _, _, _, l in pins(b))
            if mem in IMPURE_STATIC and not has_exec:
                errors.append(f"{b.name}: {mem} is impure; without exec pins it is pruned at compile and reads 0")
    for b in nodes:
        if short(b.klass) != "EdGraphNode_Comment" and not any(PIN.search(l) for l in b.lines):
            notes.append(f"{b.name} ({short(b.klass)}) has no pins")
    return nodes, errors, notes


# ---- compare ---------------------------------------------------------------------------------------------------
def live_nodes(export_text, graph=None):
    """Nodes listed in each graph's Nodes(n) array (falls back to every node block when an export has none)."""
    _, blocks = parse(export_text)
    out, any_list = [], False
    for g in blocks:
        listed = []
        for l in g.lines:
            m = re.match(r"Nodes\(\d+\)=(.*)$", l)
            if m:
                ref = m.group(1).strip().strip('"').rstrip("'")
                listed.append(re.split(r"[.:'/]", ref)[-1])
        if not listed:
            continue
        any_list = True
        if graph and g.name != graph:
            continue
        kids = {c.name: c for c in g.children}
        out += [kids[n] for n in listed if n in kids and is_node(kids[n])]
    if not any_list:
        out = [b for b in blocks if is_node(b) and (not graph or (b.parent and b.parent.name == graph))]
        print("note: no Nodes(n) lists in the export; counting every node block (deleted nodes may be included)")
    return out


def internal_link_count(b, names):
    return sum(1 for _, _, links, _ in pins(b) for ln in links if ln and ln[0] in names)


def compare(paste_text, export_text, graph=None):
    pasted = nodes_of_paste(paste_text)
    pnames = set(b.name for b in pasted)
    live = live_nodes(export_text, graph)
    want, have = defaultdict(list), defaultdict(list)
    for b in pasted:
        want[sig(b)].append(internal_link_count(b, pnames))
    for b in live:
        have[sig(b)].append(sum(len(links) for _, _, links, _ in pins(b)))
    missing, thin = [], []
    for s, counts in want.items():
        got = sorted(have.get(s, []), reverse=True)
        if len(got) < len(counts):
            missing.append((s, len(counts) - len(got)))
        exp = sorted(counts, reverse=True)
        for e, g_ in zip(exp, got):
            if g_ < e:
                thin.append((s, e, g_))
    return pasted, live, missing, thin


def fmt(s):
    kind, mem, com = s
    return f"{kind}" + (f" {mem}" if mem else "") + (f'  "{com}"' if com else "")


def export_asset(asset):
    here = os.path.dirname(os.path.abspath(__file__))
    tools = os.path.dirname(here)
    sys.path.insert(0, tools)
    from hconf import SCRATCH  # noqa: E402
    dst = os.path.join(SCRATCH, asset.rsplit("/", 1)[-1].split(".")[0] + ".t3d")
    if os.path.exists(dst):
        os.remove(dst)   # a failed run leaves the old file in place (blueprints.md)
    r = subprocess.run([sys.executable, os.path.join(tools, "ue_exec.py"),
                        os.path.join(tools, "editor", "export_t3d.py"), "--arg", f"ASSET={asset}"])
    if r.returncode != 0 or not os.path.exists(dst):
        raise SystemExit(f"export failed for {asset} (editor open? remote execution on?)")
    return dst


def main(argv):
    if len(argv) < 2 or argv[0] not in ("lint", "compare"):
        print(__doc__)
        return 2
    graph = None
    if "--graph" in argv:
        i = argv.index("--graph"); graph = argv[i + 1]; del argv[i:i + 2]
    asset = None
    if "--asset" in argv:
        i = argv.index("--asset"); asset = argv[i + 1]; del argv[i:i + 2]
    paste = open(argv[1], encoding="utf-8-sig").read()
    if argv[0] == "lint":
        nodes, errors, notes = lint(paste)
        print(f"{len(nodes)} nodes, {len(errors)} problems")
        for e in errors:
            print("  ERROR", e)
        for n in notes:
            print("  note ", n)
        return 1 if errors else 0
    export_path = export_asset(asset) if asset else (argv[2] if len(argv) > 2 else None)
    if not export_path:
        print("compare needs <export.t3d> or --asset")
        return 2
    pasted, live, missing, thin = compare(paste, open(export_path, encoding="utf-8", errors="replace").read(), graph)
    print(f"pasted {len(pasted)} nodes; graph{' ' + graph if graph else 's'} now hold {len(live)} nodes")
    for s, k in missing:
        print(f"  MISSING x{k}: {fmt(s)}")
    for s, e, g_ in thin:
        print(f"  FEWER LINKS ({g_} of {e}): {fmt(s)}")
    if not missing and not thin:
        print("  every pasted node arrived with its links")
    return 1 if (missing or thin) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
