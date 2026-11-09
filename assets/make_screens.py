"""Pictures of the two panels for the README, drawn as SVG in the desktop app's dark look: the zonecraft dashboard
(/zonecraft-panel) and the New mod form (/zonecraft-newmod), each with Clawd's animated scene in its corner. They
show example content (a mod called ImmersiveCampfires); replace them with real screenshots whenever you like.

usage: py -I make_screens.py <folder>     writes <folder>/dashboard.svg and <folder>/newmod.svg
"""
import os
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clawd_scenes  # noqa: E402
from make_logo import PALETTE, TRANSPARENT  # noqa: E402

W = 400                      # panel width
PAD = 18                     # inner padding
FONT = "Segoe UI, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
BG, CARD, BORDER = "#1f1e1d", "#262624", "#3d3c38"
TEXT, DIM, FAINT = "#ececea", "#a3a29c", "#6f6e69"
ORANGE, RUST, GREEN = "#e8772e", "#c2410c", "#4ade80"
FIELD, FIELD_BORDER = "#1f1e1d", "#4a4944"


def scene_svg(name, x, y, scale=2, step_ms=160):
    """One of Clawd's scenes as an SVG group: shared pixels once, each frame's own in a group shown in turn."""
    frames = clawd_scenes.frames(name)
    n = len(frames)
    hgt, wid = len(frames[0]), len(frames[0][0])

    def rects(rows, keep):
        out = []
        for ry, row in enumerate(rows):
            rx = 0
            while rx < wid:
                c = row[rx]
                end = rx + 1
                if c != TRANSPARENT and keep(rx, ry):
                    while end < wid and keep(end, ry) and row[end] == c:
                        end += 1
                    out.append(f'<rect x="{rx}" y="{ry}" width="{end - rx}" height="1" fill="#{PALETTE[c]:06x}"/>')
                rx = end
        return "".join(out)
    same = [[all(f[ry][rx] == frames[0][ry][rx] for f in frames) for rx in range(wid)] for ry in range(hgt)]
    body = rects(frames[0], lambda rx, ry: same[ry][rx])
    for k in range(n):
        values = ";".join("visible" if i == k else "hidden" for i in range(n))
        body += (f'<g visibility="{"visible" if k == 0 else "hidden"}"><animate attributeName="visibility" '
                 f'values="{values}" dur="{n * step_ms / 1000}s" calcMode="discrete" repeatCount="indefinite"/>'
                 + rects(frames[k], lambda rx, ry: not same[ry][rx]) + "</g>")
    return (f'<g transform="translate({x} {y}) scale({scale})" shape-rendering="crispEdges">{body}</g>',
            wid * scale, hgt * scale)


class Panel:
    """A tiny top-to-bottom layout: each call draws one line and moves the cursor down."""

    def __init__(self, title):
        self.title = title
        self.out = []
        self.y = 50

    def text(self, s, x=PAD, size=13, color=TEXT, weight=400, gap=19, spacing=0):
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        self.out.append(f'<text x="{x}" y="{self.y + size}" font-size="{size}" fill="{color}" '
                        f'font-weight="{weight}"{ls}>{escape(s)}</text>')
        self.y += gap

    def heading(self, s):
        self.text(s.upper(), size=11, color=ORANGE, weight=600, gap=18, spacing=0.8)

    def hint(self, s):
        self.text(s, size=12, color=DIM, gap=18)

    def space(self, h=14):
        self.y += h

    def button(self, label, x, y, color=DIM, weight=400, w=None):
        w = w or int(len(label) * 6.6) + 24
        self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="6" fill="{CARD}" stroke="{FIELD_BORDER}"/>'
                        f'<text x="{x + w / 2}" y="{y + 14}" font-size="12" fill="{color}" font-weight="{weight}" '
                        f'text-anchor="middle" dominant-baseline="central">{escape(label)}</text>')
        return w

    def field(self, s, placeholder=False, rows=1, select=False):
        h = 32 if rows == 1 else 20 * rows + 12
        self.out.append(f'<rect x="{PAD}" y="{self.y}" width="{W - 2 * PAD}" height="{h}" rx="6" fill="{FIELD}" '
                        f'stroke="{FIELD_BORDER}"/>')
        for k, line in enumerate(s.split("\n")):
            self.out.append(f'<text x="{PAD + 11}" y="{self.y + 16 + k * 20}" font-size="13" '
                            f'fill="{FAINT if placeholder else TEXT}" dominant-baseline="central">{escape(line)}</text>')
        if select:
            cx, cy = W - PAD - 16, self.y + 16
            self.out.append(f'<path d="M{cx - 4} {cy - 2} l4 4 l4 -4" fill="none" stroke="{DIM}" stroke-width="1.5"/>')
        self.y += h + 6

    def row(self, mark, mark_color, label, value, indent=0, value_color=TEXT):
        x = PAD + indent
        self.out.append(f'<text x="{x}" y="{self.y + 13}" font-size="13" fill="{mark_color}">{escape(mark)}</text>')
        if label:
            self.out.append(f'<text x="{x + 16}" y="{self.y + 13}" font-size="13" fill="{DIM}">{escape(label)}</text>')
            self.out.append(f'<text x="{x + 106}" y="{self.y + 13}" font-size="13" fill="{value_color}">'
                            f'{escape(value)}</text>')
        else:
            self.out.append(f'<text x="{x + 16}" y="{self.y + 13}" font-size="13" fill="{value_color}">'
                            f'{escape(value)}</text>')
        self.y += 21

    def item(self, num, s):
        self.out.append(f'<text x="{PAD}" y="{self.y + 16}" font-size="13" fill="{DIM}" dominant-baseline="central">'
                        f'{escape(num)}</text><text x="{PAD + 18}" y="{self.y + 16}" font-size="13" fill="{TEXT}" '
                        f'dominant-baseline="central">{escape(s)}</text>')
        self.button("Remove", W - PAD - 72, self.y + 2, w=72)
        self.y += 34

    def svg(self, scene_name, alt):
        art, aw, _ = scene_svg(scene_name, W - PAD - 90, 44)
        h = self.y + PAD
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
                f'font-family="{FONT}" role="img"><title>{escape(alt)}</title>'
                f'<rect width="{W}" height="{h}" rx="12" fill="{BG}"/>'
                f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="12" fill="none" stroke="{BORDER}"/>'
                f'<text x="{PAD}" y="27" font-size="13" font-weight="600" fill="{TEXT}">{escape(self.title)}</text>'
                f'<path d="M{W - PAD - 9} 18 l8 8 M{W - PAD - 1} 18 l-8 8" stroke="{FAINT}" stroke-width="1.4"/>'
                + "".join(self.out) + art + "</svg>")


def dashboard():
    p = Panel("zonecraft")
    p.heading("Mod")
    p.out.append(f'<text x="{PAD}" y="{p.y + 19}" font-size="12" fill="{DIM}" dominant-baseline="central">Tracking</text>')
    keep = PAD
    globals()["PAD"] = PAD + 58                          # the picker sits after its label
    p.out.append(f'<rect x="{PAD}" y="{p.y + 4}" width="{W - PAD - 118}" height="30" rx="6" fill="{FIELD}" '
                 f'stroke="{FIELD_BORDER}"/><text x="{PAD + 10}" y="{p.y + 19}" font-size="12" fill="{TEXT}" '
                 f'dominant-baseline="central">ImmersiveCampfires (this folder)</text>'
                 f'<path d="M{W - 128} {p.y + 17} l4 4 l4 -4" fill="none" stroke="{DIM}" stroke-width="1.5"/>')
    globals()["PAD"] = keep
    p.y += 44
    p.text("ImmersiveCampfires", size=15, weight=600, gap=21)
    p.out[-1] = p.out[-1].replace("</text>", f'<tspan fill="{DIM}" font-weight="400" font-size="13"> · IC</tspan></text>')
    p.text("Sit down at any campfire: the camera lowers, time", gap=18)
    p.text("passes faster and you heal slowly.", gap=19)
    p.hint("2026-11-09: seated pose and camera confirmed in game.")
    p.space(4)
    p.row("✓", GREEN, "Zone Kit", "set up")
    p.row("✓", GREEN, "Last cook", "12 min ago")
    p.row("!", RUST, "Test copy", "installed 2 h ago (older than the last cook)")
    p.row("·", FAINT, "Checkpoints", "3 (last: build3)")
    p.space()
    p.heading("Plan")
    p.row("·", FAINT, "Features", "2 of 4 done")
    p.row("✓", GREEN, "", "Sit with a key near a fire", 16, DIM)
    p.row("✓", GREEN, "", "Camera lowers while seated", 16, DIM)
    p.row("○", ORANGE, "", "Time passes faster while sitting", 16)
    p.row("○", ORANGE, "", "Slow healing by the fire", 16)
    p.row("·", FAINT, "To check", "1 open")
    p.row("-", FAINT, "", "Works alongside other popular mods", 16, DIM)
    p.space()
    p.heading("Blueprint pastes")
    w = p.button("Copy", PAD, p.y, ORANGE, 600)
    p.out.append(f'<text x="{PAD + w + 10}" y="{p.y + 14}" font-size="13" font-weight="600" fill="{TEXT}" '
                 f'dominant-baseline="central">seated_legs <tspan font-weight="400" fill="{DIM}" font-size="12">'
                 f'7 nodes · just now</tspan></text>')
    p.y += 34
    p.row("✓", GREEN, "", "check: 7 nodes, 6 links, no problems", 16, DIM)
    p.hint("Copy, click into the Blueprint graph in the Zone Kit, press")
    p.hint("Ctrl+V, then Compile and Save.")
    p.space(10)
    p.button("Refresh", PAD, p.y)
    p.y += 28
    return p.svg("campfire", "The zonecraft dashboard: the tracked mod, its build and test copy, the plan's features, "
                             "Blueprint pastes with a Copy button, and Clawd at his campfire")


def newmod():
    p = Panel("New mod")
    p.heading("New mod brief")
    p.hint("Write down what you know. Claude asks about the")
    p.hint("rest and keeps this plan in the mod's PLAN.md.")
    p.space()
    p.heading("Name")
    p.hint("What players will see on Nexus.")
    p.field("Immersive Campfires")
    p.space(8)
    p.heading("Main idea")
    p.hint("One or two sentences: what changes for the player.")
    p.field("Sit down at any campfire: the camera lowers, time\npasses faster and you heal slowly.", rows=2)
    p.space(8)
    p.heading("Features")
    p.hint("One at a time. They become the checklist in the panel.")
    p.item("1.", "Sit with a key near a fire")
    p.item("2.", "Camera lowers while seated")
    p.field("Add a feature and press Enter", placeholder=True)
    p.space(8)
    p.heading("Details to check")
    p.hint("Questions to settle and cases to test.")
    p.item("-", "Keyboard and gamepad")
    p.field("Add a detail and press Enter", placeholder=True)
    x = PAD
    for label in ("Rebound keys", "Survives save, load and death"):
        bw = int(len(label) * 6.6) + 36
        p.out.append(f'<rect x="{x}" y="{p.y}" width="{bw}" height="28" rx="6" fill="{CARD}" stroke="{FIELD_BORDER}"/>'
                     f'<text x="{x + bw / 2}" y="{p.y + 14}" font-size="12" fill="{DIM}" text-anchor="middle" '
                     f'dominant-baseline="central"><tspan fill="{ORANGE}">+ </tspan>{escape(label)}</text>')
        x += bw + 6
    p.y += 34
    label = "Works alongside other popular mods"
    bw = int(len(label) * 6.6) + 36
    p.out.append(f'<rect x="{PAD}" y="{p.y}" width="{bw}" height="28" rx="6" fill="{CARD}" stroke="{FIELD_BORDER}"/>'
                 f'<text x="{PAD + bw / 2}" y="{p.y + 14}" font-size="12" fill="{DIM}" text-anchor="middle" '
                 f'dominant-baseline="central"><tspan fill="{ORANGE}">+ </tspan>{escape(label)}</text>')
    p.y += 34
    p.space(10)
    p.hint("Ready to send.")
    w = p.button("Send to Claude", PAD, p.y, ORANGE, 600)
    p.button("Start over", PAD + w + 8, p.y)
    p.y += 28
    return p.svg("planning", "The New mod form: the mod's name, main idea, features and details to check, a Send to "
                             "Claude button, and Clawd plotting a route on his PDA")


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name, draw in (("dashboard", dashboard), ("newmod", newmod)):
        with open(os.path.join(out, f"{name}.svg"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(draw())
    print("dashboard.svg, newmod.svg")
