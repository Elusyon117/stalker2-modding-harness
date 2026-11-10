"""The README's pictures, drawn as SVG in the desktop app's dark look: one card per feature, all the same size (what
it does on the left, its panel on the right, Clawd in each panel's corner), and Clawd's scenes in one grid. The
panels show example content (a mod called ImmersiveCampfires); the Show nodes picture is drawn by
tools/blueprints/paste_view.py from a paste the node library writes.

usage: py -I make_screens.py <folder>     writes dashboard, nodes, newmod, quest, data, build, conflicts, logs and
                                          clawd .svg there
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

    def labeled(self, label, value, placeholder=False, select=False, rows=1):
        """A field with its label before it, as Input / Select draw with `label`."""
        self.out.append(f'<text x="{PAD}" y="{self.y + 16}" font-size="12" fill="{DIM}" dominant-baseline="central">'
                        f'{escape(label)}</text>')
        lx = PAD + 104
        h = 32 if rows == 1 else 20 * rows + 12
        self.out.append(f'<rect x="{lx}" y="{self.y}" width="{W - PAD - lx}" height="{h}" rx="6" fill="{FIELD}" '
                        f'stroke="{FIELD_BORDER}"/>')
        for k, line in enumerate(value.split("\n")):
            self.out.append(f'<text x="{lx + 10}" y="{self.y + 16 + k * 20}" font-size="12" '
                            f'fill="{FAINT if placeholder else TEXT}" dominant-baseline="central">{escape(line)}</text>')
        if select:
            cx, cy = W - PAD - 14, self.y + 16
            self.out.append(f'<path d="M{cx - 4} {cy - 2} l4 4 l4 -4" fill="none" stroke="{DIM}" stroke-width="1.5"/>')
        self.y += h + 6

    def buttons(self, *labels, first=False):
        """A row of buttons; with `first` the first one is the main action, in Zone orange."""
        x = PAD
        for i, label in enumerate(labels):
            main = i == 0 and first
            x += self.button(label, x, self.y, ORANGE if main else DIM, 600 if main else 400) + 6
        self.y += 34

    def chips(self, *labels):
        """Suggestion buttons (+ label), wrapping to the panel's width."""
        x = PAD
        for label in labels:
            bw = int(len(label) * 6.4) + 34
            if x + bw > W - PAD:
                x, self.y = PAD, self.y + 34
            self.out.append(f'<rect x="{x}" y="{self.y}" width="{bw}" height="28" rx="6" fill="{CARD}" '
                            f'stroke="{FIELD_BORDER}"/><text x="{x + bw / 2}" y="{self.y + 14}" font-size="12" '
                            f'fill="{DIM}" text-anchor="middle" dominant-baseline="central"><tspan fill="{ORANGE}">+ '
                            f'</tspan>{escape(label)}</text>')
            x += bw + 6
        self.y += 34

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
        art = ""
        if scene_name:                       # top right, as theme.tsx's top() places it
            _, aw, _ = scene_svg(scene_name, 0, 0)
            art = scene_svg(scene_name, W - PAD - aw, 44)[0]
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
    p.button("‹ All mods (3)", PAD, p.y + 4)
    p.y += 42
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
    p.heading("Release candidate files")
    p.hint("After every packaging the files are copied into this")
    p.hint("folder of the mod, renamed for the load order you want.")
    p.labeled("Folder", "ReleaseCandidate")
    p.labeled("Override files", "zzzz_{mod}_P")
    p.labeled("New content files", "Keep the kit's name", select=True)
    p.labeled("Copy", "Automatically after each packaging", select=True)
    p.text("ReleaseCandidate/zzzz_ImmersiveCampfires_P.pak · .utoc · .ucas", size=11, color=DIM, gap=16)
    p.text("ReleaseCandidate/ImmersiveCampfiresStalker2-Windows-NewContent.pak", size=11, color=DIM, gap=16)
    p.text("zzzz_ mounts after mods named zzz_ at the same priority.", size=11, color=DIM, gap=16)
    p.space(10)
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
    return p.svg("planning", "The New mod form: release candidate naming, the mod's name, main idea, features and details to check, a Send to "
                             "Claude button, and Clawd plotting a route on his PDA")


RED = "#f87171"


def quest():
    p = Panel("Quest designer")
    p.heading("Quest designer")
    for line in ("Lay out the quest; Claude", "turns it into a Quest", "Blueprint plan and walks",
                 "you through the Quest Tool."):
        p.hint(line)
    p.space()
    p.heading("Mod")
    p.hint("The quest belongs to this mod: its files, PLAN.md and texts.")
    p.labeled("Mod", "ImmersiveCampfires (this folder)", select=True)
    p.out.append(f'<text x="{PAD}" y="{p.y + 14}" font-size="12" fill="{DIM}" dominant-baseline="central">Saved:</text>')
    p.button("IC_ASeatByTheFire", PAD + 46, p.y, TEXT)
    p.y += 34
    p.space(8)
    p.heading("Quest")
    p.labeled("Title", "A Seat by the Fire")
    p.labeled("SID", "IC_ASeatByTheFire", placeholder=True)
    p.labeled("Kind", "Side quest", select=True)
    p.labeled("Summary", "An old stalker at the camp wants someone\nto sit and hear his last story.", rows=2)
    p.labeled("Journal", "What the PDA journal says", placeholder=True)
    p.space(8)
    p.heading("Start and place")
    p.labeled("Starts when", "Talk to a quest giver", select=True)
    p.labeled("Detail", "Old Hryts, after dark", )
    p.labeled("Region", "Zalissya", select=True)
    p.labeled("Place", "The campfire behind the church")
    p.space(8)
    p.heading("Characters")
    p.hint("Set the pickers, then type the name and press Enter.")
    for line in ("Old Hryts (Quest giver, Loners, Stay)", "Bandits ×3 (Enemy, Bandits, Patrol)"):
        p.out.append(f'<text x="{PAD}" y="{p.y + 15}" font-size="12" dominant-baseline="central"><tspan fill="{ORANGE}">'
                     f'•</tspan><tspan fill="{TEXT}" dx="8">{escape(line)}</tspan></text>')
        p.button("Remove", W - PAD - 72, p.y, w=72)
        p.y += 32
    p.labeled("Role", "Quest giver", select=True)
    p.labeled("Faction", "Loners", select=True)
    p.labeled("Behavior", "Stay (idle)", select=True)
    p.labeled("How many", "1")
    p.labeled("Vanilla SID", "Empty for a new character", placeholder=True)
    p.labeled("Name", "Add a character and press Enter", placeholder=True)
    p.space(8)
    p.heading("Stages")
    p.hint("Each objective in order (a Set Journal stage each).")
    for i, (k, t, m) in enumerate((("Talk to", "Hear Hryts out", "Quest Marker"),
                                    ("Collect", "Bring firewood", "Zone marker"),
                                    ("Defend", "Hold the camp till dawn", "optional"))):
        p.out.append(f'<text x="{PAD}" y="{p.y + 15}" font-size="12" fill="{TEXT}" dominant-baseline="central">'
                     f'{i + 1}. <tspan fill="{ORANGE}">[{escape(k)}]</tspan> {escape(t)} '
                     f'<tspan fill="{DIM}">({escape(m)})</tspan></text>')
        p.button("↑", W - PAD - 56, p.y, w=26)
        p.button("↓", W - PAD - 26, p.y, w=26)
        p.y += 32
    p.labeled("Kind", "Go to", select=True)
    p.labeled("Marker", "Marker (fixed point)", select=True)
    p.labeled("Stage is", "Required", select=True)
    p.labeled("Objective", "Find the courier in the tunnels", placeholder=True)
    p.space(8)
    p.heading("Rewards")
    p.hint("What the player gets on success.")
    p.item("-", "Hryts' old harmonica")
    p.field("3000 coupons and a Saiga", placeholder=True)
    p.chips("Money (coupons)", "Reputation with a faction", "A stash marker")
    p.space(4)
    p.heading("Choices and branches")
    p.hint("Where the player decides, and what each way leads to.")
    p.field("Return the PDA or sell it to the bandits", placeholder=True)
    p.chips("Spare or kill the target", "Peaceful route through dialog")
    p.space(4)
    p.heading("Rules and failure")
    p.item("-", "Fails if the quest giver dies")
    p.chips("Protect quest NPCs", "Works in existing saves")
    p.space(4)
    p.hint("Dialogs, items, world changes, audio, outcome, languages")
    p.hint("and notes follow the same way.")
    p.space(8)
    p.hint("Ready to send.")
    p.buttons("Send to Claude", "Save", "New quest", first=True)
    p.y -= 6
    return p.svg("stories", "The Quest designer: a mod picked at the top, the quest's basics, start and place, characters, "
                       "ordered stages with markers, rewards, branches and rules with suggestions, and Send to Claude")


def conflicts():
    p = Panel("Mod conflicts")
    p.heading("Mod conflicts")
    for line in ("Per asset the last-mounted pak", "wins and nothing merges; cfg", "patches clash only on the same field."):
        p.hint(line)
    p.labeled("Collection folder", "D:/ST2ZKMods/Collections/Hardcore")
    p.labeled("Show", "Every conflict", select=True)
    p.buttons("Scan again", first=True)
    p.space(4)
    p.heading("Mods scanned (14)")
    p.hint("3 min ago · yours, installed, collection")
    p.out.append(f'<text x="{PAD}" y="{p.y + 13}" font-size="12"><tspan fill="{ORANGE}">ImmersiveCampfires (yours) · 103'
                 f'</tspan><tspan fill="{DIM}" dx="10">BetterHud · 203</tspan></text>')
    p.y += 19
    p.text("GrittyCamps · 103   WeaponOverhaul · 103   and 10 more", size=12, color=DIM, gap=26)
    p.heading("Conflicts (4)")
    p.hint("1 risky · 1 check · 2 one wins")

    def conflict(mark, color, kind, what, winner, losers, note, yours=False):
        p.out.append(f'<text x="{PAD}" y="{p.y + 13}" font-size="13"><tspan fill="{color}">{mark}</tspan>'
                     f'<tspan fill="{DIM}" dx="8">{kind}</tspan><tspan fill="{TEXT}" font-weight="600" dx="8">'
                     f'{escape(what)}</tspan>'
                     + (f'<tspan fill="{ORANGE}" font-size="12" dx="8">yours</tspan>' if yours else "") + '</text>')
        p.y += 20
        p.out.append(f'<text x="{PAD + 16}" y="{p.y + 14}" font-size="12" dominant-baseline="central">'
                     f'<tspan fill="{GREEN}">wins: {escape(winner)}</tspan><tspan fill="{DIM}" dx="8">over '
                     f'{escape(losers)}</tspan></text>')
        p.button("Ask Claude", W - PAD - 86, p.y, w=86)
        p.y += 32
        p.text(note, x=PAD + 16, size=12, color=DIM, gap=26)
    conflict("✗", RED, "asset", "…/Player/AnimBP_Player", "GrittyCamps", "ImmersiveCampfires",
             "Heavily shared asset: merge, or make one optional.", True)
    conflict("!", RUST, "asset", "…/UI/W_GameHUD", "BetterHud", "GrittyCamps",
             "Same mount order: the file name decides.")
    conflict("!", ORANGE, "cfg", "corevariables.cfg › CampfireHealRate", "ImmersiveCampfires", "GrittyCamps",
             "Both patch this field; yours loads later and wins.", True)
    conflict("!", ORANGE, "cfg", "weapon…prototypes.cfg › GunAK74_ST › Recoil", "WeaponOverhaul", "Hardcore",
             "Both patch this field; WeaponOverhaul loads later.")
    p.buttons("Ask Claude about all of them", first=True)
    p.hint("37 more files are shipped identically by several mods.")
    return p.svg("hunt", "The Conflicts panel: a collection folder, the mods scanned with their mount order, and each "
                       "conflict with its winner, the mods it beats and an Ask Claude button")


def logs():
    p = Panel("zonecraft logs")
    p.heading("Watching")
    p.hint("Last look just now")
    p.hint("Game not running · Zone Kit open")
    p.space()
    p.heading("Last packaging")
    p.text("ImmersiveCampfires packaged 4 min ago (5:42)")
    p.text("Release candidate: ReleaseCandidate (6 files)", size=12, color=DIM, gap=18)
    p.space()
    p.heading("Crashes")
    p.out.append(f'<text x="{PAD}" y="{p.y + 15}" font-size="13" dominant-baseline="central"><tspan fill="{RED}">✗'
                 f'</tspan><tspan fill="{TEXT}" font-weight="600" dx="8">UE4SS (a probe or script mod)</tspan>'
                 f'<tspan fill="{DIM}" dx="8">1 h ago</tspan></text>')
    p.button("Ask Claude", W - PAD - 86, p.y, ORANGE, 600, w=86)
    p.y += 34
    p.text("The crash is inside UE4SS. Turn dev probes off in", size=12, gap=16)
    p.text("ue4ss/Mods/mods.txt and retest.", size=12, gap=18)
    p.text("Access violation reading address 0x18", size=12, color=DIM, gap=16)
    p.text("  UE4SS.dll!RC::Unreal::UObject::GetClassPrivate()", size=11, color=FAINT, gap=20)
    p.space(6)
    p.heading("From the logs")
    p.hint("Cfg patch warnings, broken game data, texts, mod mounts.")
    for mark, color, src, line in (("!", RUST, "game patch", "CampfireHeal also modified by GrittyCamps"),
                                   ("✗", RED, "game data", "Unknown SID IC_Harmonica"),
                                   ("!", RUST, "kit text", "Missing text key IC_Quest_Hryts_01"),
                                   ("!", RUST, "game mount", "zzz_GrittyCamps_P mounted (103)")):
        p.out.append(f'<text x="{PAD}" y="{p.y + 13}" font-size="12"><tspan fill="{color}">{mark}</tspan>'
                     f'<tspan fill="{DIM}" dx="8">{src}</tspan><tspan fill="{TEXT}" dx="8">{escape(line)}</tspan></text>')
        p.y += 21
    p.space(6)
    p.buttons("Ask Claude about these", "Clear", "Refresh", first=True)
    p.y -= 6
    return p.svg("repair", "The Logs panel: what is being watched, the last packaging and its release candidate, a crash "
                       "with its known family and advice, and warnings from the game and kit logs")


def tline(p, parts, size=12, gap=20, x=PAD):
    """One line of coloured parts: [(text, color, weight)]."""
    spans = "".join(f'<tspan fill="{c}" font-weight="{w}"{" dx=\"6\"" if i else ""}>{escape(t)}</tspan>'
                    for i, (t, c, w) in enumerate(parts))
    p.out.append(f'<text x="{x}" y="{p.y + 14}" font-size="{size}" dominant-baseline="central">{spans}</text>')
    p.y += gap


def dataentry():
    p = Panel("Game data")
    bw = p.button("‹ Back to results", PAD, p.y)
    p.button("★", PAD + bw + 6, p.y, ORANGE, w=34)       # kept short: Clawd trades at the top right
    p.y += 36
    p.text("AK74 Kalashnikov", size=16, weight=600, gap=22)
    tline(p, [("GunAK74_ST", DIM, 400), ("· WeaponGeneralSetupPrototypes.cfg:1842", FAINT, 400)], size=12)
    tline(p, [("Inherits", DIM, 400), ("GunBase_AR", TEXT, 400), ("‹", FAINT, 400), ("GunBase", TEXT, 400)])
    tline(p, [("!", RUST, 400), ("4 weapons inherit from this; DLC copy in DLCGameData/Deluxe", DIM, 400)])
    p.space(12)
    p.heading("Values")
    p.hint("Dim = inherited · orange = your mod changes it · press a")
    p.hint("value to change it.")

    def val(path, value, kind="own", edit=None, indent=0):
        x = PAD + indent
        col = {"own": TEXT, "inh": FAINT, "mine": ORANGE}[kind]
        p.out.append(f'<text x="{x}" y="{p.y + 15}" font-size="12" fill="{DIM if kind != "inh" else FAINT}" '
                     f'dominant-baseline="central">{escape(path)}</text>')
        vx = PAD + 200
        if edit is None:
            p.out.append(f'<text x="{vx}" y="{p.y + 15}" font-size="12" fill="{col}" dominant-baseline="central">'
                         f'{escape(value)}</text>')
        else:
            p.out.append(f'<rect x="{vx - 6}" y="{p.y}" width="{W - PAD - vx + 6}" height="28" rx="5" fill="{FIELD}" '
                         f'stroke="{ORANGE}"/><text x="{vx + 4}" y="{p.y + 14}" font-size="12" fill="{TEXT}" '
                         f'dominant-baseline="central"><tspan fill="{FAINT}" text-decoration="line-through">{value}'
                         f'</tspan>  {escape(edit)}</text>')
        p.y += 30 if edit is not None else 23

    val("BaseDamage", "10", edit="14")
    val("Cost", "4800")
    val("Weight", "3.6", "inh")
    val("MagazineSize", "30", "inh")
    val("RateOfFire", "650", "mine")
    val("▾ Recoil", "2 entries", "inh")
    val("Up", "1.2", indent=14)
    val("Side", "0.4", "inh", indent=14)
    val("› WeaponReloadTimePerAttachment", "3 entries", "inh")
    p.space(12)
    p.heading("Pending changes (1)")
    p.button("Remove", W - PAD - 72, p.y, w=72)
    tline(p, [("BaseDamage", TEXT, 400), ("10 → 14", ORANGE, 600)], gap=34)
    box_y = p.y
    lines = ["GunAK74_ST : struct.begin {bpatch}", "   BaseDamage = 14", "struct.end"]
    p.out.append(f'<rect x="{PAD}" y="{box_y}" width="{W - 2 * PAD}" height="{18 * len(lines) + 30}" rx="6" '
                 f'fill="{FIELD}" stroke="{FIELD_BORDER}"/>')
    for i, l in enumerate(lines):
        p.out.append(f'<text x="{PAD + 10}" y="{box_y + 18 + i * 18}" font-size="11.5" fill="{TEXT}" '
                     f'font-family="Consolas, monospace" xml:space="preserve">{escape(l)}</text>')
    p.out.append(f'<text x="{PAD + 10}" y="{box_y + 18 + len(lines) * 18 + 4}" font-size="11" fill="{DIM}">'
                 f'→ …/WeaponGeneralSetupPrototypes/ImmersiveCampfires.cfg (added)</text>')
    p.y += 18 * len(lines) + 38
    p.buttons("Add to my mod", "Send to Claude", "Copy patch", first=True)
    tline(p, [("✓", GREEN, 400), ("Checked: every field exists on GunAK74_ST", DIM, 400)])
    p.y -= 4
    return p.svg("trading", "The Game data browser, an entry: name, file, inheritance, values with one being edited, "
                       "the pending patch and Add to my mod")


def band():
    """The Build & test band above the prompt: a packaging running, then the finished build with its next steps."""
    bw, bh = 640, 356
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw}" height="{bh}" viewBox="0 0 {bw} {bh}" '
           f'font-family="{FONT}" role="img"><title>The Build and test band above the prompt: a packaging in '
           f'progress with its stage and time, then the finished build with Install test copy and What to test'
           f'</title><rect width="{bw}" height="{bh}" rx="12" fill="{BG}"/>'
           f'<rect x="0.5" y="0.5" width="{bw - 1}" height="{bh - 1}" rx="12" fill="none" stroke="{BORDER}"/>']

    def label(y, s):
        out.append(f'<text x="{PAD}" y="{y}" font-size="11" fill="{FAINT}" letter-spacing="0.8">{escape(s)}</text>')

    def prompt(y):
        out.append(f'<rect x="{PAD}" y="{y}" width="{bw - 2 * PAD}" height="38" rx="10" fill="{CARD}" '
                   f'stroke="{FIELD_BORDER}"/><text x="{PAD + 14}" y="{y + 19}" font-size="13" fill="{FAINT}" '
                   f'dominant-baseline="central">Reply to Claude…</text>')

    def btn(x, y, s, main=False):
        w = int(len(s) * 6.6) + 24
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="6" fill="{CARD}" stroke="{FIELD_BORDER}"/>'
                   f'<text x="{x + w / 2}" y="{y + 13}" font-size="12" fill="{ORANGE if main else DIM}" '
                   f'font-weight="{600 if main else 400}" text-anchor="middle" dominant-baseline="central">'
                   f'{escape(s)}</text>')
        return x + w + 6

    label(28, "WHILE PACKAGING")
    out.append(f'<text x="{PAD}" y="54" font-size="13"><tspan fill="{ORANGE}">●</tspan><tspan fill="{TEXT}" '
               f'font-weight="600" dx="8">Packaging ImmersiveCampfires</tspan><tspan fill="{TEXT}" dx="8">Cooking'
               f'</tspan><tspan fill="{DIM}" dx="8">3:12 · 64% · close the game before installing</tspan></text>')
    out.append(f'<text x="{PAD}" y="74" font-size="12" fill="{DIM}">LogCook: Display: Cooked packages 1840 '
               f'Packages Remain 1032 Total 2872</text>')
    prompt(88)

    label(166, "AFTER A GOOD BUILD")
    out.append(f'<text x="{PAD}" y="192" font-size="13"><tspan fill="{GREEN}">✓</tspan><tspan fill="{TEXT}" '
               f'font-weight="600" dx="8">Packaged ImmersiveCampfires in 5:42</tspan><tspan fill="{DIM}" dx="8">'
               f'just now</tspan></text>')
    out.append(f'<text x="{PAD}" y="219" font-size="12" fill="{DIM}">Release candidate: 6 files just now</text>')
    x = btn(PAD + 214, 202, "Install test copy")
    x = btn(x, 202, "Hide tests")
    btn(x, 202, "Hide")
    out.append(f'<text x="{PAD + 16}" y="250" font-size="12" fill="{DIM}">Try each in game, then press what '
               f'happened:</text>')
    out.append(f'<text x="{PAD + 16}" y="276" font-size="13"><tspan fill="{ORANGE}">○</tspan><tspan fill="{TEXT}" '
               f'dx="8">Time passes faster while sitting</tspan></text>')
    x = btn(PAD + 270, 260, "Worked")
    btn(x, 260, "Didn't")
    prompt(bh - 38 - PAD + 4)
    out.append("</svg>")
    return "".join(out)


def sample_paste():
    """The seat-heal paste the Show nodes picture draws: two comment boxes written by the node library, with two
    links to nodes already in the graph (the wires the tester draws by hand)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "blueprints"))
    from bp_graph import Graph
    from bp_nodes import Nodes
    g = Graph()
    n = Nodes(g, self_class="/ImmersiveCampfires/Runtime/BP_SeatedMode.BP_SeatedMode_C")
    g.box("EdGraphNode_Comment_900", -80, -140, 900, 520, "Tick: heal while seated")
    tick = n.event_tick()
    pc = n.cast_player(exec_from=[tick["then"]], label="tick")
    br = n.branch(n.self_get("Seated", "bool"), "only while seated")
    n.chain(pc, br)
    dt = n.math("Subtract_DoubleDouble", n.game_time(), n.self_get("LastHeal", "real", "double"))
    br2 = n.branch(n.math("Greater_DoubleDouble", dt, None, b_const="2.0"), "every 2 s")
    n.chain(br, br2)
    n.chain(br2, n.self_set("LastHeal", "real", value=n.game_time(), sub="double", comment="remember when"))
    g.box("EdGraphNode_Comment_901", -80, 500, 900, 400, "Input: stand up")
    ia = n.input_action("/ImmersiveCampfires/Input/IA_StandUp.IA_StandUp", x=20, y=600, comment="stand up")
    n.chain(ia, n.self_set("Seated", "bool", default="false", x=300, y=600, comment="not seated"))
    g.layout_tree()
    text = "\n".join(g.text())
    text = link_out(text, lambda c: "IfThenElse" in c, "else", "K2Node_CallFunction_77", "0" * 31 + "1")
    return link_out(text, lambda c: "VariableSet" in c and 'MemberName="Seated"' in c, "then", "K2Node_CallFunction_78",
                    "0" * 31 + "2")


def link_out(text, pick, pin, target, pid):
    """Points one pin of the first node block `pick` accepts at a node that is not in the paste."""
    out, block, done = [], "", False
    lines = text.splitlines()
    for k, line in enumerate(lines):
        if line.startswith("Begin Object"):
            end = next(j for j in range(k, len(lines)) if lines[j].startswith("End Object"))
            block = "\n".join(lines[k:end + 1])
        if not done and pick(block) and f'PinName="{pin}"' in line and "LinkedTo" not in line:
            line = line.replace("PersistentGuid=", f"LinkedTo=({target} {pid},),PersistentGuid=", 1)
            done = True
        out.append(line)
    return "\n".join(out)


def nodes_pane():
    """The Nodes pane (Show nodes, then Own pane): a comment box of a paste as the graph editor will show it."""
    text = sample_paste()                    # puts tools/blueprints on the path
    import paste_view
    vs = paste_view.views(text, {"K2Node_CallFunction_77": "Stop Healing", "K2Node_CallFunction_78": "Play Stand Up"})
    hand = []
    for v in vs:
        hand += [h for h in v["hand"] if h not in hand]
    v = vs[0]
    nodes, _ = paste_view.parse(text)
    seated = next(n for n in nodes if n["props"].get("NodeComment") == "only while seated")
    ww, wh = 620, 300                        # a window around the first Branch and its hand-wired stub
    wx = max(0, min(v["w"] - ww, int(seated["props"]["NodePosX"]) - v["minx"] - 60))
    wy = max(0, min(v["h"] - wh, int(seated["props"]["NodePosY"]) - v["miny"] - 70))
    p = Panel("seat_heal nodes")
    p.heading("Seat_heal · nodes")
    p.hint("As the Zone Kit graph")
    p.hint("will show it.")
    p.space(10)
    x = PAD
    for i, q in enumerate(vs):
        x += p.button(f"{q['title']}  {q['nodes']}", x, p.y, ORANGE if i == 0 else DIM, 600 if i == 0 else 400) + 6
    p.y += 38
    tline(p, [("!", ORANGE, 400), (f"wire by hand after pasting ({len(hand)}):", DIM, 400)], gap=19)
    for h in hand:
        tline(p, [(h, TEXT, 400)], x=PAD + 16, gap=19)
    p.space(8)
    pw = W - 2 * PAD
    ph = round(pw * wh / ww)
    pic = v["svg"].replace("<svg ", f'<svg x="{PAD}" y="{p.y}" ', 1)
    pic = pic.replace(f'width="{v["w"]}" height="{v["h"]}"', f'width="{pw}" height="{ph}"', 1)
    pic = pic.replace(f'viewBox="{v["minx"]} {v["miny"]} {v["w"]} {v["h"]}"',
                      f'viewBox="{v["minx"] + wx} {v["miny"] + wy} {ww} {wh}"', 1)
    p.out.append(pic + f'<rect x="{PAD - 0.5}" y="{p.y - 0.5}" width="{pw + 1}" height="{ph + 1}" rx="6" '
                       f'fill="none" stroke="{FIELD_BORDER}"/>')
    p.y += ph + 10
    p.buttons("+ Closer", "− Whole box", "◀", "▶")
    p.hint("Dashed orange: wire by hand. Dashed grey: goes on")
    p.hint("in another box.")
    p.y -= 4
    return p.svg("repair", "The Nodes pane: a Blueprint paste's comment box drawn as the Zone Kit graph editor will "
                           "show it, the wires to draw by hand after pasting, zoom and move buttons, and Clawd fixing "
                           "his gear")


# ---------------------------------------------------------------------------------------------------- README cards
CW, CH = 880, 500              # every feature card is this size, so the README reads as one even column
CARD_BG = "#141312"


def _size(svg):
    import re
    m = re.match(r'<svg[^>]*?width="([\d.]+)" height="([\d.]+)"', svg)
    return float(m.group(1)), float(m.group(2))


def _wrap(s, chars):
    lines, cur = [], ""
    for w in s.split():
        if cur and len(cur) + len(w) + 1 > chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + ([cur] if cur else [])


def _frame(body, alt):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}" '
            f'font-family="{FONT}" role="img"><title>{escape(alt)}</title><defs>'
            f'<linearGradient id="zc-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1d1c1a"/>'
            f'<stop offset="1" stop-color="{CARD_BG}"/></linearGradient>'
            f'<radialGradient id="zc-glow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{ORANGE}" '
            f'stop-opacity="0.16"/><stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="zc-fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CARD_BG}" '
            f'stop-opacity="0"/><stop offset="1" stop-color="{CARD_BG}"/></linearGradient>'
            f'<filter id="zc-shadow" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="8" '
            f'stdDeviation="10" flood-color="#000" flood-opacity="0.55"/></filter>'
            f'<clipPath id="zc-clip"><rect width="{CW}" height="{CH}" rx="16"/></clipPath></defs>'
            f'<g clip-path="url(#zc-clip)"><rect width="{CW}" height="{CH}" fill="url(#zc-bg)"/>{body}</g>'
            f'<rect x="0.5" y="0.5" width="{CW - 1}" height="{CH - 1}" rx="16" fill="none" stroke="{BORDER}"/></svg>')


def _chip(x, y, s):
    w = len(s) * 7.2 + 22
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="26" rx="13" fill="{ORANGE}" fill-opacity="0.12" '
            f'stroke="{ORANGE}" stroke-opacity="0.5"/><text x="{x + w / 2:.0f}" y="{y + 13}" font-size="12.5" '
            f'fill="{ORANGE}" font-family="Consolas, Menlo, monospace" text-anchor="middle" '
            f'dominant-baseline="central">{escape(s)}</text>')


def card(title, command, tagline, bullets, panel, alt):
    """A feature card: what it is on the left, the panel on the right, cut off with a fade when it is taller than
    the card."""
    out = [_chip(48, 48, command),
           f'<text x="48" y="118" font-size="30" font-weight="700" fill="{TEXT}">{escape(title)}</text>']
    y = 152
    for line in _wrap(tagline, 44):
        out.append(f'<text x="48" y="{y}" font-size="15" fill="{DIM}">{escape(line)}</text>')
        y += 22
    y += 20
    for b in bullets:
        for k, line in enumerate(_wrap(b, 44)):
            if k == 0:
                out.append(f'<text x="48" y="{y}" font-size="14" fill="{ORANGE}" font-weight="700">›</text>')
            out.append(f'<text x="66" y="{y}" font-size="13.5" fill="{TEXT}">{escape(line)}</text>')
            y += 20
        y += 10
    left, top, area_w = 436, 34, CW - 436 - 30
    out.append(f'<ellipse cx="{left + area_w / 2}" cy="{CH / 2}" rx="{area_w * 0.75}" ry="{CH * 0.6}" '
               f'fill="url(#zc-glow)"/>')
    pw, ph = _size(panel)
    s = min(1.0, area_w / pw)
    out.append(f'<g transform="translate({left + (area_w - pw * s) / 2:.1f} {top}) scale({s:.3f})" '
               f'filter="url(#zc-shadow)">{panel}</g>')
    if top + ph * s > CH - 20:
        out.append(f'<rect x="{left - 30}" y="{CH - 90}" width="{area_w + 60}" height="90" fill="url(#zc-fade)"/>')
    return _frame("".join(out), alt)


def wide_card(title, command, tagline, panel, alt):
    """A card for a wide picture (the band above the prompt): the words on top, the picture under them."""
    out = [_chip(48, 40, command),
           f'<text x="48" y="106" font-size="30" font-weight="700" fill="{TEXT}">{escape(title)}</text>']
    for k, line in enumerate(_wrap(tagline, 96)):
        out.append(f'<text x="48" y="{138 + 22 * k}" font-size="15" fill="{DIM}">{escape(line)}</text>')
    pw, ph = _size(panel)
    s = min(1.0, (CH - 210) / ph, (CW - 96) / pw)
    out.append(f'<ellipse cx="{CW / 2}" cy="{CH - 120}" rx="{CW * 0.5}" ry="{CH * 0.45}" fill="url(#zc-glow)"/>')
    out.append(f'<g transform="translate({(CW - pw * s) / 2:.1f} {CH - 30 - ph * s:.1f}) scale({s:.3f})" '
               f'filter="url(#zc-shadow)">{panel}</g>')
    return _frame("".join(out), alt)


SCENE_LABELS = (("campfire", "By the campfire"), ("guitar", "Playing the guitar"), ("planning", "Plotting a route"),
                ("exploring", "Exploring the Zone"), ("bolt", "Throwing bolts"), ("detector", "Hunting artifacts"),
                ("hunt", "Hunting mutants"), ("stash", "Looting a stash"), ("trading", "Trading"),
                ("stories", "Stories at the fire"), ("repair", "Fixing his gear"), ("sleeping", "Sleeping it off"))


def clawd_grid():
    """Every scene of Clawd in one even grid: four across, each at the same pixel scale, standing on one line."""
    cols, cell_w, cell_h, top = 4, CW / 4, 130, 26
    rows = (len(SCENE_LABELS) + cols - 1) // cols
    h = top + rows * cell_h
    out = []
    for i, (name, label) in enumerate(SCENE_LABELS):
        cx, cy = (i % cols) * cell_w, top + (i // cols) * cell_h
        _, aw, ah = scene_svg(name, 0, 0)
        out.append(scene_svg(name, round(cx + (cell_w - aw) / 2), round(cy + 66 - ah))[0])
        out.append(f'<text x="{cx + cell_w / 2:.0f}" y="{cy + 94}" font-size="13" fill="{DIM}" '
                   f'text-anchor="middle">{escape(label)}</text>')
    alt = "Clawd, zonecraft's crab in a gas mask, in twelve scenes: " + ", ".join(l.lower() for _, l in SCENE_LABELS)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{h}" viewBox="0 0 {CW} {h}" '
            f'font-family="{FONT}" role="img"><title>{escape(alt)}</title>'
            f'<rect width="{CW}" height="{h}" rx="16" fill="{CARD_BG}"/>'
            f'<rect x="0.5" y="0.5" width="{CW - 1}" height="{h - 1}" rx="16" fill="none" stroke="{BORDER}"/>'
            + "".join(out) + "</svg>")


def cards():
    """The README's pictures: one card per feature, all the same size, plus Clawd's scenes."""
    return {
        "dashboard": card(
            "Dashboard", "/zonecraft-panel", "Every mod you work on, and where each one stands.",
            ["All mods: packaging, build, test copy, features and conflicts for each mod",
             "Each mod's page: the last cook, the test copy in your game, checkpoints",
             "The plan, ticked off as each feature works in game"],
            dashboard(),
            "The zonecraft dashboard: a mod's page with its build, test copy, plan and Blueprint pastes, and Clawd "
            "at his campfire"),
        "nodes": card(
            "Show nodes", "/zonecraft-panel", "See a Blueprint paste before you paste it.",
            ["Each comment box drawn the way the Zone Kit graph editor will show it",
             "The wires to draw by hand after pasting, listed and drawn as dashed stubs",
             "Copy with one button, then check that every node arrived"],
            nodes_pane(),
            "Show nodes: a Blueprint paste's comment box drawn as the Zone Kit graph editor will show it, with "
            "the wires to draw by hand"),
        "newmod": card(
            "New mod", "/zonecraft-newmod", "Write down the mod you want; Claude takes it from there.",
            ["Name, main idea, the features you want and the details to check",
             "How its packaged files are named for the load order",
             "Send to Claude: a plan and a GitHub page for the mod"],
            newmod(),
            "The New mod form: release candidate naming, the mod's name, main idea, features and details to check, "
            "and Send to Claude"),
        "quest": card(
            "Quest designer", "/zonecraft-quest", "Lay out a quest before you open the Quest Tool.",
            ["Characters, stages with markers, dialogs, items and rewards",
             "Branches, failure rules and world changes, with suggestions",
             "Saved in the mod; Claude turns it into a Quest Blueprint plan"],
            quest(),
            "The Quest designer: the quest's basics, start and place, characters, ordered stages with markers, "
            "rewards, branches and rules, and Send to Claude"),
        "data": card(
            "Game data", "/zonecraft-data", "Look up any weapon, item, NPC, quest or effect, and change it.",
            ["Search the game's own data, with your mod's changes marked",
             "Every value shown as its own, inherited or changed by your mod",
             "Change a value and add the patch to your mod in one press"],
            dataentry(),
            "The Game data browser: the AK74 entry with its values, one being changed, and the patch to add to "
            "the mod"),
        "build": wide_card(
            "Build & test", "above the prompt", "While you press Package Mod in the Zone Kit, the band above the "
            "prompt follows it: stage, time and errors, then Install test copy and what to try in game.",
            band(),
            "The Build and test band above the prompt: a packaging in progress with its stage and time, then the "
            "finished build with Install test copy and the features to try"),
        "conflicts": card(
            "Conflicts", "/zonecraft-conflicts", "Which mods fight over the same files, and which one wins.",
            ["Your mods, the installed mods and a collection folder",
             "Shared assets with the winner, whole cfg files, patches on one field",
             "Ask Claude about any conflict"],
            conflicts(),
            "The Conflicts panel: the mods scanned with their mount order, and each conflict with its winner and "
            "an Ask Claude button"),
        "logs": card(
            "Logs", "/zonecraft-logs", "What the game and the Zone Kit said, without opening a log.",
            ["Packaging as it happens, and its release candidate",
             "Crashes with what they mean and what to try",
             "Cfg patch warnings, broken game data and mod mounts"],
            logs(),
            "The Logs panel: the last packaging, a crash with its known family and advice, and warnings from the "
            "game and kit logs"),
        "clawd": clawd_grid(),
    }


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    drawn = cards()
    for name, svg in drawn.items():
        with open(os.path.join(out, f"{name}.svg"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
    print(", ".join(f"{n}.svg" for n in drawn))
