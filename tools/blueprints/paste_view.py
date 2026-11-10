"""Draw Blueprint paste text the way the Zone Kit's graph editor will show it: nodes at their pasted positions, pins
by type, wires, comment boxes, and the wires the tester draws by hand (links to nodes outside the paste).

    py -I paste_view.py <paste.txt>     writes <paste>.view.json: one picture per comment box

The zonecraft panel's "Show nodes" draws <paste>.view.json (verify_paste.py lint writes it too). Names for nodes
outside the paste (the ends of the wires drawn by hand) can come from <paste>.meta.json: {"external": {"K2Node_X_7":
"Stop Healing"}}; without one they are named after the node's class.
"""
import json
import os
import re
import sys
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------------------------------- parsing
PIN_RE = re.compile(r"^\s*CustomProperties Pin \((.*)\)\s*$")


def _field(s, key):
    m = re.search(rf'(?:^|,){re.escape(key)}=("(?:[^"\\]|\\.)*"|\w*\([^()]*(?:\([^()]*\)[^()]*)*\)|[^,]*)', s)
    if not m:
        return None
    v = m.group(1)
    return v[1:-1] if v.startswith('"') else v


def parse(text):
    nodes, boxes, cur = [], [], None
    for line in text.splitlines():
        if line.startswith("Begin Object Class="):
            m = re.match(r'Begin Object Class=(\S+) Name="([^"]+)"', line)
            cur = {"klass": m.group(1).split(".")[-1], "name": m.group(2), "props": {}, "pins": []}
            continue
        if cur is None:
            continue
        if line.startswith("End Object"):
            (boxes if cur["klass"] == "EdGraphNode_Comment" else nodes).append(cur)
            cur = None
            continue
        pm = PIN_RE.match(line)
        if pm:
            s = pm.group(1)
            links = re.findall(r"([A-Za-z0-9_]+) ([0-9A-F]{32})", _field(s, "LinkedTo") or "")
            friendly = _field(s, "PinFriendlyName")
            if friendly and friendly.startswith("NSLOCTEXT"):
                friendly = re.findall(r'"([^"]*)"', friendly)[-1]
            cur["pins"].append({
                "id": _field(s, "PinId"), "name": _field(s, "PinName"), "friendly": friendly,
                "out": _field(s, "Direction") == "EGPD_Output", "cat": _field(s, "PinType.PinCategory"),
                "sub": _field(s, "PinType.PinSubCategory") or "", "subobj": _field(s, "PinType.PinSubCategoryObject"),
                "default": _field(s, "DefaultValue"), "hidden": _field(s, "bHidden") == "True",
                "adv": _field(s, "bAdvancedView") == "True", "links": links,
                "array": _field(s, "PinType.ContainerType") == "Array",
            })
            continue
        m = re.match(r"\s+(\w+)=(.*)$", line)
        if m:
            cur["props"][m.group(1)] = m.group(2).strip().strip('"')
    return nodes, boxes


# ---------------------------------------------------------------------------------------------------- naming
def human(s):
    s = re.sub(r"^(Receive|K2_|BP_)", "", s)
    s = s.replace("_", " ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return re.sub(r"\s+", " ", s).strip()


OPS = {"Add": "+", "Subtract": "−", "Multiply": "×", "Divide": "÷", "Greater": ">", "Less": "<",
       "GreaterEqual": "≥", "LessEqual": "≤", "EqualEqual": "==", "NotEqual": "!=", "BooleanAND": "AND",
       "BooleanOR": "OR", "Not": "NOT"}


def member(props, key):
    v = props.get(key, "")
    m = re.search(r'MemberName="?([^",)]+)', v)
    return m.group(1) if m else ""


def owner(props, key):
    m = re.search(r"MemberParent=\"?[^']*'[^']*?\.([A-Za-z0-9_]+)'", props.get(key, ""))
    return human(m.group(1)) if m else ""


def describe(n):
    """(kind, title, subtitle) for a node: kind picks the look."""
    k, p = n["klass"], n["props"]
    has_exec = any(x["cat"] == "exec" for x in n["pins"])
    if k == "K2Node_Event":
        name = member(p, "EventReference")
        return "event", "Event " + human(name), ""
    if k == "K2Node_CustomEvent":
        return "event", human(p.get("CustomFunctionName", "Custom Event")), "Custom Event"
    if "InputAction" in k:
        ia = re.findall(r"([A-Za-z0-9_]+)'?\"?$", p.get("InputAction", "").strip("'\""))
        return "event", (ia[0] if ia else "Input Action"), "Enhanced Input Action"
    if k == "K2Node_CallFunction":
        fn = member(p, "FunctionReference")
        base = fn.split("_")[0]
        if not has_exec and base in OPS:
            return "op", OPS[base], ""
        sub = owner(p, "FunctionReference")
        sub = f"Target is {sub}" if sub and sub not in ("Actor",) else ""
        return ("call" if has_exec else "pure"), human(fn), sub
    if k == "K2Node_VariableGet":
        return "get", human(member(p, "VariableReference")), ""
    if k == "K2Node_VariableSet":
        return "set", "SET", ""
    if k == "K2Node_IfThenElse":
        return "flow", "Branch", ""
    if k == "K2Node_ExecutionSequence":
        return "flow", "Sequence", ""
    if k == "K2Node_DynamicCast":
        t = re.findall(r"\.([A-Za-z0-9_]+)'?$", p.get("TargetType", "").strip("'\""))
        return "cast", f"Cast To {t[0] if t else '?'}", ""
    if k == "K2Node_MacroInstance":
        m = re.search(r":([A-Za-z0-9_]+)'", p.get("MacroGraphReference", ""))
        return "flow", human(m.group(1)) if m else "Macro", ""
    if k == "K2Node_AddDelegate":
        return "call", "Bind Event to " + human(member(p, "DelegateReference")), ""
    return "call", human(k.replace("K2Node_", "")), ""


HEADER = {"event": "#8c1d1d", "call": "#3c6e9e", "pure": "#4f7f3a", "flow": "#5c5c5c", "cast": "#2f7a77",
          "set": "#5c5c5c"}
PIN_COLOR = {"exec": "#ffffff", "bool": "#a01818", "real": "#8de34a", "float": "#8de34a", "double": "#8de34a",
             "int": "#2fd9b0", "int64": "#2fa88e", "byte": "#0f7a6c", "name": "#c78cff", "string": "#ff3dd5",
             "text": "#e88ab0", "object": "#1aa0f0", "class": "#6a3cff", "interface": "#f0f0a0", "struct": "#2f68d8",
             "delegate": "#ff4848", "softobject": "#8fd0ff", "softclass": "#c8b0ff"}


def pin_color(p):
    if p["cat"] == "struct" and "Vector" in (p["subobj"] or ""):
        return "#ffcb2f"
    return PIN_COLOR.get(p["cat"], "#bbbbbb")


def pin_label(n, kind, p):
    if p["cat"] == "exec":
        if p["name"] in ("execute", "then") and not p["friendly"]:
            return ""
        return p["friendly"] or human(p["name"])
    if kind in ("op", "get"):
        return ""
    if p["name"] == "self":
        return "Target"
    if p["name"] == "ReturnValue":
        return "Return Value"
    if kind == "set" and p["out"]:
        return ""
    if p["cat"] == "bool" and re.match(r"b[A-Z]", p["name"]) and not p["friendly"]:
        return human(p["name"][1:])
    return p["friendly"] or human(p["name"])


# ---------------------------------------------------------------------------------------------------- geometry
ROW, HEAD, PADX, CHAR = 24, 30, 14, 6.8
BG, GRID, GRID_BIG, BODY, BODY_EDGE = "#1d1d1d", "#262626", "#2f2f2f", "#121212", "#000000"
TEXT, DIM, ORANGE = "#e8e8e8", "#9a9a9a", "#e8772e"
FONT = "Segoe UI, Roboto, Helvetica, Arial, sans-serif"


def visible_pins(n):
    return [p for p in n["pins"] if not p["hidden"] and not p["adv"] and p["cat"] != "delegate"]


def measure(n):
    kind, title, sub = describe(n)
    pins = visible_pins(n)
    ins = [p for p in pins if not p["out"]]
    outs = [p for p in pins if p["out"]]

    def lab(p):
        t = pin_label(n, kind, p)
        d = p["default"] if (not p["out"] and not p["links"] and p["default"] not in (None, "") and p["cat"] != "object") else ""
        return len(t) * CHAR + (len(d) * CHAR + 18 if d else 0)
    if kind == "get":
        w = max(90, len(title) * 7.4 + 44)
        return {"kind": kind, "title": title, "sub": sub, "ins": [], "outs": outs, "w": w, "h": 30}
    if kind == "op":
        rows = max(len(ins), len(outs), 2)
        dw = max([lab(p) + 8 for p in ins] or [0])        # an input's typed-in value sits beside its pin
        w = 92 + dw
        return {"kind": kind, "title": title, "sub": sub, "ins": ins, "outs": outs, "w": w, "h": rows * ROW + 12,
                "mid": (24 + dw + w - 18) / 2}
    left = max([lab(p) for p in ins] or [0])
    right = max([lab(p) for p in outs] or [0])
    w = max(150, left + right + 70, len(title) * 7.6 + 46, len(sub) * 6.0 + 40)
    rows = max(len(ins), len(outs), 1)
    head = HEAD + (14 if sub else 0)
    return {"kind": kind, "title": title, "sub": sub, "ins": ins, "outs": outs, "w": w, "h": head + rows * ROW + 8,
            "head": head}


def pin_positions(n, m):
    """{pin id: (x, y, color, is_exec, is_out)} in graph units."""
    x, y = int(n["props"].get("NodePosX", 0)), int(n["props"].get("NodePosY", 0))
    out = {}
    if m["kind"] == "get":
        for p in m["outs"]:
            out[p["id"]] = (x + m["w"] - 12, y + 15, pin_color(p), False, True)
        return out
    top = y + (6 if m["kind"] == "op" else m["head"]) + ROW / 2
    for i, p in enumerate(m["ins"]):
        out[p["id"]] = (x + 12, top + i * ROW, pin_color(p), p["cat"] == "exec", False)
    for i, p in enumerate(m["outs"]):
        out[p["id"]] = (x + m["w"] - 12, top + i * ROW, pin_color(p), p["cat"] == "exec", True)
    return out


# ---------------------------------------------------------------------------------------------------- drawing
def pin_glyph(x, y, color, is_exec, linked, is_out):
    if is_exec:
        d = f"M{x - 5} {y - 6} L{x + 1} {y - 6} L{x + 6} {y} L{x + 1} {y + 6} L{x - 5} {y + 6} Z"
        return f'<path d="{d}" fill="{color if linked else "none"}" stroke="{color}" stroke-width="1.5"/>'
    return (f'<circle cx="{x}" cy="{y}" r="5" fill="{color if linked else "none"}" stroke="{color}" '
            f'stroke-width="1.6"/>')


def wire(a, b, color, is_exec, dashed=False):
    (x1, y1), (x2, y2) = a, b
    dx = max(40, abs(x2 - x1) * 0.45)
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    return (f'<path d="M{x1} {y1} C{x1 + dx} {y1} {x2 - dx} {y2} {x2} {y2}" fill="none" stroke="{color}" '
            f'stroke-width="{2.6 if is_exec else 2}" stroke-opacity="{1 if is_exec else 0.9}"{dash}/>')


def draw_node(n, m, linked_ids):
    x, y, w, h = int(n["props"].get("NodePosX", 0)), int(n["props"].get("NodePosY", 0)), m["w"], m["h"]
    k = m["kind"]
    tip = f"<title>{escape(m['title'])}{' — ' + escape(n['props'].get('NodeComment', '')) if n['props'].get('NodeComment') else ''}</title>"
    out = [f'<g>{tip}']
    if k == "get":
        c = pin_color(m["outs"][0]) if m["outs"] else "#888"
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="15" fill="{BODY}" fill-opacity="0.92" '
                   f'stroke="{c}" stroke-opacity="0.55"/>')
        out.append(f'<text x="{x + 14}" y="{y + 15}" font-size="12.5" fill="{TEXT}" dominant-baseline="central">'
                   f'{escape(m["title"])}</text>')
    elif k == "op":
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{BODY}" fill-opacity="0.92" '
                   f'stroke="{BODY_EDGE}"/>')
        out.append(f'<text x="{x + m["mid"]:.0f}" y="{y + h / 2}" font-size="24" font-weight="700" fill="{TEXT}" '
                   f'text-anchor="middle" dominant-baseline="central">{escape(m["title"])}</text>')
    else:
        hc = HEADER.get(k, "#3c6e9e")
        head = m["head"]
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{BODY}" fill-opacity="0.94" '
                   f'stroke="{BODY_EDGE}"/>')
        out.append(f'<path d="M{x} {y + 8} a8 8 0 0 1 8 -8 h{w - 16} a8 8 0 0 1 8 8 v{head - 8} h{-w} Z" fill="{hc}"/>')
        out.append(f'<rect x="{x}" y="{y + head - 1}" width="{w}" height="1" fill="#000" fill-opacity="0.5"/>')
        icon = {"event": "◆", "call": "ƒ", "pure": "ƒ", "flow": "⇉", "cast": "⇄", "set": ""}.get(k, "")
        tx = x + (26 if icon else 12)
        if icon:
            out.append(f'<text x="{x + 10}" y="{y + 15}" font-size="12" fill="#ffffff" fill-opacity="0.85" '
                       f'dominant-baseline="central">{icon}</text>')
        out.append(f'<text x="{tx}" y="{y + 15}" font-size="13" font-weight="600" fill="#ffffff" '
                   f'dominant-baseline="central">{escape(m["title"])}</text>')
        if m["sub"]:
            out.append(f'<text x="{tx}" y="{y + 31}" font-size="10.5" fill="#ffffff" fill-opacity="0.65" '
                       f'dominant-baseline="central">{escape(m["sub"])}</text>')
    pos = pin_positions(n, m)
    for p in m["ins"] + m["outs"]:
        px, py, c, is_exec, is_out = pos[p["id"]]
        out.append(pin_glyph(px, py, c, is_exec, p["id"] in linked_ids, is_out))
        lab = pin_label(n, k, p)
        if lab:
            if is_out:
                out.append(f'<text x="{px - 12}" y="{py}" font-size="12" fill="{TEXT}" text-anchor="end" '
                           f'dominant-baseline="central">{escape(lab)}</text>')
            else:
                out.append(f'<text x="{px + 12}" y="{py}" font-size="12" fill="{TEXT}" dominant-baseline="central">'
                           f'{escape(lab)}</text>')
        if not is_out and not p["links"] and p["default"] not in (None, "") and p["cat"] not in ("object", "exec"):
            dx = px + 12 + (len(lab) * CHAR + 8 if lab else 0)
            dv = p["default"]
            if p["cat"] == "bool":
                on = dv.lower() == "true"
                out.append(f'<rect x="{dx}" y="{py - 7}" width="14" height="14" rx="2" fill="{"#2d2d2d" if not on else "#d8d8d8"}" '
                           f'stroke="#666"/>' + (f'<path d="M{dx + 3} {py} l3 3 l5 -6" stroke="#111" stroke-width="2" fill="none"/>' if on else ""))
            else:
                bw = len(dv) * CHAR + 12
                out.append(f'<rect x="{dx}" y="{py - 9}" width="{bw}" height="18" rx="3" fill="#2b2b2b" stroke="#444"/>'
                           f'<text x="{dx + 6}" y="{py}" font-size="11.5" fill="{TEXT}" dominant-baseline="central">'
                           f'{escape(dv)}</text>')
    if n["props"].get("NodeComment") and k not in ("get", "op"):
        c = n["props"]["NodeComment"]
        out.append(f'<rect x="{x}" y="{y - 26}" width="{len(c) * 6.6 + 16}" height="20" rx="4" fill="#2a2a2a" '
                   f'fill-opacity="0.9"/><text x="{x + 8}" y="{y - 16}" font-size="11.5" fill="{DIM}" '
                   f'dominant-baseline="central">{escape(c)}</text>')
    out.append("</g>")
    return "".join(out)


def _xy(n):
    return int(n["props"].get("NodePosX", 0)), int(n["props"].get("NodePosY", 0))


def _box_rect(b):
    p = b["props"]
    return int(p.get("NodePosX", 0)), int(p.get("NodePosY", 0)), int(p.get("NodeWidth", 400)), int(p.get("NodeHeight", 200))


def _inside(n, b):
    x, y = _xy(n)
    bx, by, bw, bh = _box_rect(b)
    return bx <= x <= bx + bw and by <= y <= by + bh


def _chip(x, y, label, color, is_out, fill_opacity):
    """A rounded label at the loose end of a stub: (svg, (x, y, w, h))."""
    w = len(label) * 6.9 + 34
    left = x if is_out else x - w
    svg = (f'<rect x="{left:.0f}" y="{y - 13:.0f}" width="{w:.0f}" height="26" rx="13" fill="{color}" '
           f'fill-opacity="{fill_opacity}" stroke="{color}"/><text x="{left + w / 2:.0f}" y="{y:.0f}" font-size="12" '
           f'fill="{color}" text-anchor="middle" dominant-baseline="central">{escape(label)}</text>')
    return svg, (left, y - 13, w, 26)


def _hits(r, rects, margin=6):
    x, y, w, h = r
    return any(x < rx + rw + margin and rx < x + w + margin and y < ry + rh + margin and ry < y + h + margin
               for rx, ry, rw, rh in rects)


def render(text, box=None, external_names=None):
    """SVG of the paste: all of it (box None), one comment box (its index) or the nodes in no box ("other").
    external_names: {node name: readable name} for links that leave the paste (the tester wires those by hand).
    Returns (svg, info); info["hand"] lists the wires to draw by hand, as sentences."""
    external_names = external_names or {}
    nodes, boxes = parse(text)
    by_name = {n["name"]: n for n in nodes}
    meas = {n["name"]: measure(n) for n in nodes}
    pos = {}
    for n in nodes:
        pos.update(pin_positions(n, meas[n["name"]]))

    if box is None:
        shown_boxes, shown = boxes, nodes
    elif box == "other":
        shown_boxes, shown = [], [n for n in nodes if not any(_inside(n, b) for b in boxes)]
    else:
        shown_boxes, shown = [boxes[box]], [n for n in nodes if _inside(n, boxes[box])]
    names = {n["name"] for n in shown}
    if not shown and not shown_boxes:
        return "", {"nodes": 0, "hand": [], "minx": 0, "miny": 0, "w": 0, "h": 0}

    rects = [(*_xy(n), meas[n["name"]]["w"], meas[n["name"]]["h"]) for n in shown]
    xs = [r[0] for r in rects] + [_box_rect(b)[0] for b in shown_boxes]
    ys = [r[1] - 30 for r in rects] + [_box_rect(b)[1] for b in shown_boxes]
    x2 = [r[0] + r[2] for r in rects] + [_box_rect(b)[0] + _box_rect(b)[2] for b in shown_boxes]
    y2 = [r[1] + r[3] for r in rects] + [_box_rect(b)[1] + _box_rect(b)[3] for b in shown_boxes]
    pad = 40
    minx, miny, maxx, maxy = min(xs) - pad, min(ys) - pad, max(x2) + pad, max(y2) + pad

    def box_title(name):
        n = by_name.get(name)
        for b in boxes:
            if n is not None and _inside(n, b):
                return b["props"].get("NodeComment", "") or "another box"
        return "outside the boxes"

    def node_phrase(n, p):
        kind, title, _ = describe(n)
        c = n["props"].get("NodeComment", "")
        pin = pin_label(n, kind, p) or human(p["name"])
        return f"{title}{f' ({c})' if c else ''} › {pin}"

    linked, wires, stubs, hand = set(), [], [], []
    for n in shown:
        for p in visible_pins(n):
            for other, opid in p["links"]:
                linked.add(p["id"])
                if other in names:
                    if p["out"] and opid in pos:
                        a, b = pos[p["id"]], pos[opid]
                        wires.append(wire((a[0] + 6, a[1]), (b[0] - 6, b[1]), a[2], a[3]))
                elif other in by_name:            # to a node of the paste in another comment box
                    stubs.append((n, p, "→ " + box_title(other) if p["out"] else box_title(other) + " →", "#9a9a9a"))
                else:                             # to a node already in the graph: the tester wires it by hand
                    label = external_names.get(other) or human(re.sub(r"_\d+$", "", other.replace("K2Node_", "")))
                    stubs.append((n, p, label, ORANGE))
                    hand.append(f"{node_phrase(n, p)} → {label}" if p["out"] else f"{label} → {node_phrase(n, p)}")

    ext_svg, taken = [], list(rects)
    for n, p, label, color in stubs:
        x, y, _, is_exec, is_out = pos[p["id"]]
        ex = x + 70 if is_out else x - 70
        for dy in (0, 36, -36, 72, -72, 108, -108, 144):
            chip_svg, r = _chip(ex, y + dy, label, color, is_out, 0.16 if color == ORANGE else 0.08)
            if not _hits(r, taken):
                break
        taken.append(r)
        ends = ((x + 6, y), (ex, y + dy)) if is_out else ((ex, y + dy), (x - 6, y))
        ext_svg.append(wire(*ends, color, True, dashed=True) + chip_svg)
        minx, maxx = min(minx, r[0] - 20), max(maxx, r[0] + r[2] + 20)
        miny, maxy = min(miny, r[1] - 20), max(maxy, r[1] + r[3] + 20)

    W, H = maxx - minx, maxy - miny
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="{minx:.0f} {miny:.0f} {W:.0f} {H:.0f}" font-family="{FONT}" role="img">',
           f'<defs><pattern id="g" width="16" height="16" patternUnits="userSpaceOnUse" x="0" y="0">'
           f'<path d="M16 0 H0 V16" fill="none" stroke="{GRID}" stroke-width="1"/></pattern>'
           f'<pattern id="G" width="128" height="128" patternUnits="userSpaceOnUse" x="0" y="0">'
           f'<rect width="128" height="128" fill="url(#g)"/><path d="M128 0 H0 V128" fill="none" stroke="{GRID_BIG}" '
           f'stroke-width="1.5"/></pattern></defs>',
           f'<rect x="{minx:.0f}" y="{miny:.0f}" width="{W:.0f}" height="{H:.0f}" fill="{BG}"/>',
           f'<rect x="{minx:.0f}" y="{miny:.0f}" width="{W:.0f}" height="{H:.0f}" fill="url(#G)"/>']
    for b in shown_boxes:
        bx, by, bw, bh = _box_rect(b)
        out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="4" fill="#ffffff" fill-opacity="0.06" '
                   f'stroke="#ffffff" stroke-opacity="0.18"/>')
        out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="34" rx="4" fill="#ffffff" fill-opacity="0.1"/>')
        out.append(f'<text x="{bx + 12}" y="{by + 17}" font-size="17" fill="#f0f0f0" dominant-baseline="central">'
                   f'{escape(b["props"].get("NodeComment", ""))}</text>')
    out += wires + ext_svg
    for n in shown:
        out.append(draw_node(n, meas[n["name"]], linked))
    out.append("</svg>")
    return "".join(out), {"nodes": len(shown), "hand": hand, "minx": round(minx), "miny": round(miny),
                          "w": round(W), "h": round(H)}


def views(text, external_names=None):
    """One picture per comment box that holds nodes, plus the nodes in no box; the whole paste when it has no box."""
    nodes, boxes = parse(text)
    picks = [(i, b["props"].get("NodeComment", "") or f"Box {i + 1}") for i, b in enumerate(boxes)
             if any(_inside(n, b) for n in nodes)]
    if not boxes:
        picks = [(None, "Graph")]
    elif any(not any(_inside(n, b) for b in boxes) for n in nodes):
        picks.append(("other", "Not in a box"))
    out = []
    for key, title in picks:
        svg, info = render(text, key, external_names)
        out.append({"title": title, **info, "svg": svg})
    return out


def write_view(paste_path):
    """<paste>.view.json beside the paste: what the panel's "Show nodes" draws. Returns its summary dict."""
    base = paste_path[:-4] if paste_path.lower().endswith(".txt") else paste_path
    with open(paste_path, encoding="utf-8-sig") as f:
        text = f.read()
    names = {}
    if os.path.exists(base + ".meta.json"):
        try:
            with open(base + ".meta.json", encoding="utf-8-sig") as f:
                names = json.load(f).get("external", {}) or {}
        except (OSError, ValueError, AttributeError):
            names = {}
    vs = views(text, names)
    hand = []
    for v in vs:
        hand += [h for h in v["hand"] if h not in hand]
    with open(base + ".view.json", "w", encoding="utf-8") as f:
        json.dump({"version": 1, "views": vs, "hand": hand}, f)
    return {"views": len(vs), "nodes": sum(v["nodes"] for v in vs), "hand": len(hand)}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    print(json.dumps(write_view(sys.argv[1])))
