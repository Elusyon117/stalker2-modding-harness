r"""Parser for GSC's game data DSL (the .cfg files under GameLite/GameData).

    Name : struct.begin {refurl=../X.cfg; refkey=[0]; bpatch}
       Key = Value
       [0] = Value
       Child : struct.begin {bpatch}
          ...
       struct.end
       [2] : removenode
    struct.end

parse(text)        -> Node (a root holding the file's top-level structs)
scan_top(lines)    -> one light pass that yields the top-level structs only (for the index)
apply_patch(b, p)  -> b with patch p applied, following GSC's rules: a struct without {bpatch} replaces the node,
                      {bpatch} merges child by child, `X : removenode` deletes X.
inherit(child, parent) -> child's fields over its refkey parent's (an approximation of the game's own merge: nested
                      structs merge key by key unless the child struct has {bskipref}).
dump(node)         -> cfg text again (indent 3 spaces, as GSC's examples).
"""
import re

BEGIN = re.compile(r"^\s*(?P<key>[^:=/{}]+?)\s*:\s*struct\.begin\b\s*(?:\{(?P<attrs>[^}]*)\})?", re.I)
END = re.compile(r"^\s*struct\.end\b", re.I)
REMOVE = re.compile(r"^\s*(?P<key>[^:=/{}]+?)\s*:\s*removenode\b", re.I)
FIELD = re.compile(r"^\s*(?P<key>[^=]+?)\s*=\s*(?P<val>.*?)\s*$")
COMMENT = re.compile(r"(^|\s)//.*$")
REMOVED = object()  # value of a `X : removenode` item


class Node:
    __slots__ = ("name", "attrs", "items", "line", "end")

    def __init__(self, name="", attrs=None, line=0):
        self.name, self.attrs, self.items, self.line, self.end = name, dict(attrs or {}), [], line, line

    # items is an ordered list of [key, value]; value is a str, a Node or REMOVED
    def get(self, key, default=None):
        for k, v in self.items:
            if k == key:
                return v
        return default

    def set(self, key, value):
        for it in self.items:
            if it[0] == key:
                it[1] = value
                return
        self.items.append([key, value])

    def delete(self, key):
        self.items = [it for it in self.items if it[0] != key]

    def copy(self):
        n = Node(self.name, self.attrs, self.line)
        n.end = self.end
        n.items = [[k, v.copy() if isinstance(v, Node) else v] for k, v in self.items]
        return n

    @property
    def bpatch(self):
        return "bpatch" in self.attrs


def parse_attrs(s):
    out = {}
    for part in (s or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
        else:
            out[part.lower()] = True
    return out


def strip_comment(line):
    return COMMENT.sub("", line).rstrip("\r\n")


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")


def parse(text, first_line=1):
    root = Node("<file>", line=first_line)
    stack = [root]
    for i, raw in enumerate(text.splitlines(), first_line):
        line = strip_comment(raw)
        if not line.strip():
            continue
        m = BEGIN.match(line)
        if m:
            n = Node(m.group("key").strip(), parse_attrs(m.group("attrs")), i)
            stack[-1].items.append([n.name, n])
            stack.append(n)
            continue
        if END.match(line):
            if len(stack) > 1:
                stack.pop().end = i
            continue
        m = REMOVE.match(line)
        if m:
            stack[-1].items.append([m.group("key").strip(), REMOVED])
            continue
        m = FIELD.match(line)
        if m:
            stack[-1].items.append([m.group("key").strip(), m.group("val")])
    root.end = first_line + len(text.splitlines())
    return root


def scan_top(lines):
    """Yield dicts for each top-level struct or removenode: name, attrs, line, end, sid (1-based lines)."""
    depth, cur = 0, None
    for i, raw in enumerate(lines, 1):
        line = strip_comment(raw)
        if not line.strip():
            continue
        m = BEGIN.match(line)
        if m:
            if depth == 0:
                cur = {"name": m.group("key").strip(), "attrs": parse_attrs(m.group("attrs")),
                       "line": i, "end": i, "sid": None, "removenode": False}
            depth += 1
            continue
        if END.match(line):
            if depth > 0:
                depth -= 1
                if depth == 0 and cur:
                    cur["end"] = i
                    yield cur
                    cur = None
            continue
        if depth == 0:
            m = REMOVE.match(line)
            if m:
                yield {"name": m.group("key").strip(), "attrs": {}, "line": i, "end": i, "sid": None,
                       "removenode": True}
            continue
        if depth == 1 and cur is not None and cur["sid"] is None:
            m = FIELD.match(line)
            if m and m.group("key").strip() == "SID":
                cur["sid"] = m.group("val")
    if cur:  # unterminated struct at end of file
        cur["end"] = len(lines)
        yield cur


def apply_patch(base, patch):
    """Return base with patch applied (base may be None: the patch adds the node)."""
    if patch is REMOVED:
        return REMOVED
    if not isinstance(patch, Node):
        return patch
    if base is None or not isinstance(base, Node) or not patch.bpatch:
        out = patch.copy()
        out.attrs.pop("bpatch", None)
        return out
    out = base.copy()
    for k, v in patch.items:
        if v is REMOVED:
            out.delete(k)
            continue
        out.set(k, apply_patch(out.get(k), v))
    return out


def inherit(child, parent):
    if parent is None or "bskipref" in child.attrs:
        return child.copy()
    out = parent.copy()
    out.name, out.attrs, out.line, out.end = child.name, dict(child.attrs), child.line, child.end
    for k, v in child.items:
        if v is REMOVED:
            out.delete(k)
        elif isinstance(v, Node) and isinstance(out.get(k), Node):
            out.set(k, inherit(v, out.get(k)))
        else:
            out.set(k, v.copy() if isinstance(v, Node) else v)
    return out


def dump(node, indent=0, max_depth=99):
    pad = "   " * indent
    attrs = "; ".join(k if v is True else f"{k}={v}" for k, v in node.attrs.items())
    lines = [f"{pad}{node.name} : struct.begin" + (f" {{{attrs}}}" if attrs else "")]
    for k, v in node.items:
        if v is REMOVED:
            lines.append(f"{pad}   {k} : removenode")
        elif isinstance(v, Node):
            if indent + 1 >= max_depth:
                lines.append(f"{pad}   {k} : struct.begin ... ({len(v.items)} items) struct.end")
            else:
                lines.extend(dump(v, indent + 1, max_depth).splitlines())
        else:
            lines.append(f"{pad}   {k} = {v}")
    lines.append(f"{pad}struct.end")
    return "\n".join(lines)


def build_patch(name, sets=(), removes=()):
    """Patch text for one top-level struct. sets: 'A.B.[0].C=value'; removes: 'A.[2]'."""
    root = Node(name, {"bpatch": True})

    def walk(path):
        n = root
        for part in path:
            child = n.get(part)
            if not isinstance(child, Node):
                child = Node(part, {"bpatch": True})
                n.set(part, child)
            n = child
        return n

    for s in sets:
        path, value = s.split("=", 1)
        parts = split_path(path)
        walk(parts[:-1]).set(parts[-1], value.strip())
    for r in removes:
        parts = split_path(r)
        walk(parts[:-1]).set(parts[-1], REMOVED)
    return dump(root)


def split_path(path):
    """'A.B.[0].C' or 'A.B[0].C' -> ['A', 'B', '[0]', 'C']"""
    path = re.sub(r"(?<=[^.])\[", ".[", path.strip())
    return [p.strip() for p in path.split(".") if p.strip()]


def lookup(node, parts):
    for p in parts:
        if not isinstance(node, Node):
            return None
        node = node.get(p)
    return node
