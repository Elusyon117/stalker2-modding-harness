"""Pictures of the panels for the README, drawn as SVG in the desktop app's dark look: the zonecraft dashboard
(/zonecraft-panel), the New mod form (/zonecraft-newmod), the Quest designer (/zonecraft-quest), the Conflicts panel
(/zonecraft-conflicts), the Logs panel (/zonecraft-logs) and the Build & test band above the prompt. They show example
content (a mod called ImmersiveCampfires); replace them with real screenshots whenever you like.

usage: py -I make_screens.py <folder>     writes dashboard, newmod, quest, conflicts, logs and band .svg there
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
        art = scene_svg(scene_name, W - PAD - 90, 44)[0] if scene_name else ""
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
    p.hint("Lay out the quest; Claude turns it into a Quest Blueprint")
    p.hint("plan and walks you through the Quest Tool.")
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
    return p.svg(None, "The Quest designer: a mod picked at the top, the quest's basics, start and place, characters, "
                       "ordered stages with markers, rewards, branches and rules with suggestions, and Send to Claude")


def conflicts():
    p = Panel("Mod conflicts")
    p.heading("Mod conflicts")
    p.hint("Per asset the last-mounted pak wins and nothing merges;")
    p.hint("cfg patches clash only on the same field.")
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
    return p.svg(None, "The Conflicts panel: a collection folder, the mods scanned with their mount order, and each "
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
    return p.svg(None, "The Logs panel: what is being watched, the last packaging and its release candidate, a crash "
                       "with its known family and advice, and warnings from the game and kit logs")


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


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    drawings = (("dashboard", dashboard), ("newmod", newmod), ("quest", quest), ("conflicts", conflicts),
                ("logs", logs), ("band", band))
    for name, draw in drawings:
        with open(os.path.join(out, f"{name}.svg"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(draw())
    print(", ".join(f"{n}.svg" for n, _ in drawings))
