"""Clawd's scenes: the zonecraft crab in its gas mask doing what stalkers do in the Zone. Each scene is a few
animation steps of a small pixel grid on a transparent background, drawn with make_logo.py's palette and crab.

usage: py -I clawd_scenes.py <out.ts>          the panels' data (hooks/clawd.ts)
       py -I clawd_scenes.py <folder>          one looping GIF per scene (assets/clawd/<name>.gif)
       py -I clawd_scenes.py <out.png> sheet   every scene's steps on one sheet, light and dark, for checking
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_logo as m  # noqa: E402
from make_logo import (ANOM, BG, CRAB, DOG, DOG_SHADE, EMBER, FLAME, FLAME_HI, FLOOR, HOOD_GREEN, HOOD_TAN,  # noqa: E402
                       LENS, LENS_DIM, LOG, LOG_SHADE, MASK, MASK2, PACK, PACK_SHADE, PALETTE, PUFF, SAUSAGE, SUB, TITLE,
                       TRANSPARENT, WARN, campfire, crab, px, rect)

STEPS = 4


def canvas(w, h):
    return [[TRANSPARENT] * w for _ in range(h)]


def grass(f, floor, xs):
    """Tufts of dry grass on the ground line."""
    for x in xs:
        px(f, x, floor - 1, PACK)
        px(f, x + 1, floor - 2, PACK)
        px(f, x + 2, floor - 1, PACK_SHADE)


def bubble(f, x, y, w, h, inside, tail_x):
    """A speech bubble, light with a grey rim (it shows on light and dark panels), its tail at tail_x."""
    rect(f, x + 1, y, w - 2, h, SUB)
    rect(f, x, y + 1, w, h - 2, SUB)
    rect(f, x + 1, y + 1, w - 2, h - 2, TITLE)
    px(f, tail_x, y + h, SUB)
    px(f, tail_x, y + h + 1, SUB)
    for dx, dy, c in inside:
        px(f, x + dx, y + dy, c)


def note(f, x, y, c=TITLE):
    """A music note: a round head, a stem and a flag."""
    rect(f, x, y + 3, 2, 1, c)
    rect(f, x + 1, y, 1, 3, c)
    px(f, x + 2, y, c)


def rifle(f, x, y, kick=0):
    """A scoped rifle pointing right, stock at x."""
    x -= kick
    rect(f, x, y, 3, 2, LOG)                             # stock
    rect(f, x + 3, y, 11, 1, MASK2)                      # receiver
    rect(f, x + 7, y + 1, 1, 2, MASK2)                   # magazine
    rect(f, x + 14, y, 4, 1, PUFF)                       # barrel
    rect(f, x + 6, y - 1, 4, 1, MASK2)                   # scope
    px(f, x + 9, y - 1, ANOM)                            # its lens


def dog(f, x0, floor, step):
    """A blind dog running left: no eyes, ribs showing, its legs in stride."""
    y0 = floor - 8
    rect(f, x0, y0 + 1, 4, 3, DOG)                       # head
    px(f, x0 + 2, y0, DOG_SHADE)                         # ear
    px(f, x0 - 1, y0 + 2, MASK)                          # nose
    px(f, x0, y0 + 3, DOG_SHADE)                         # mouth
    rect(f, x0 + 3, y0 + 2, 8, 3, DOG)                   # body
    rect(f, x0 + 4, y0 + 4, 6, 1, DOG_SHADE)             # belly
    for rx in (5, 7, 9):
        px(f, x0 + rx, y0 + 3, DOG_SHADE)                # ribs
    px(f, x0 + 11, y0 + 2, DOG_SHADE)                    # tail
    px(f, x0 + 12, y0 + 1, DOG_SHADE)
    reach = 1 if step % 2 else -1
    for k, lx in enumerate((3, 5, 8, 10)):
        s = reach if k % 2 == 0 else -reach
        rect(f, x0 + lx, y0 + 5, 1, 2, DOG_SHADE if k % 2 else DOG)
        px(f, x0 + lx + s, y0 + 7, DOG_SHADE if k % 2 else DOG)


def artifact(f, x, y, step):
    """An artifact lying in the grass: a glowing stone with a flicker of light around it."""
    rect(f, x, y, 3, 2, LENS)
    px(f, x + 1, y, TITLE)
    for k, (dx, dy) in enumerate(((-2, 0), (4, -1), (1, -3), (-1, -2), (4, 2))):
        if (k + step) % 3 == 0:
            px(f, x + dx, y + dy, FLAME_HI)


def coins(f, x, y, n=3):
    for k in range(n):
        rect(f, x, y - k, 3, 1, WARN if k % 2 == 0 else FLAME_HI)


# ---- the scenes -------------------------------------------------------------------------------------------------
def guitar(step):
    """Clawd sitting on the ground playing the guitar, notes drifting up."""
    w, h, floor = 46, 20, 19
    f = canvas(w, h)
    cy = floor - 16
    crab(f, at=(2, cy), arm_r=3 + (step % 2))
    rect(f, 12, cy + 10, 9, 5, LOG)                      # guitar body across the lap
    rect(f, 13, cy + 9, 6, 1, LOG)
    rect(f, 13, cy + 15, 7, 1, LOG_SHADE)
    rect(f, 15, cy + 11, 2, 2, MASK)                     # sound hole
    for k in range(10):                                  # neck up to the left hand
        px(f, 20 + k, cy + 10 - k // 2, LOG_SHADE)
    rect(f, 30, cy + 3, 2, 2, MASK2)                     # headstock
    if step % 2:                                         # the strings ring
        rect(f, 12, cy + 12, 9, 1, WARN)
    for k, (nx, base) in enumerate(((34, 10), (39, 6), (43, 9))):
        rise = (step + k * 2) % 6
        if rise < 5:
            note(f, nx - (k == 2) * 3, cy + base - rise, (FLAME, WARN, FLAME_HI)[k])
    return f


def stories(step):
    """Clawd and two other stalkers at a campfire at night, swapping stories."""
    w, h, floor = 96, 24, 23
    f = canvas(w, h)
    cy = floor - 16
    crab(f, at=(1, cy), hood=HOOD_GREEN)                 # a Freedom stalker,
    crab(f, at=(29, cy))                                 # Clawd,
    campfire(f, 58, floor, step)
    crab(f, at=(70, cy), hood=HOOD_TAN, arm_l=3 - (step < 2))   # and a loner telling one
    if step < 2:                                         # the loner tells one...
        bubble(f, 74, 0, 11, 5, [(3, 2, MASK), (5, 2, MASK), (7, 2, MASK)], 78)
    else:                                                # ...the other two can't believe it
        bubble(f, 37, 0, 7, 6, [(3, 1, EMBER), (3, 2, EMBER), (3, 4, EMBER)], 41)
        bubble(f, 9, 1, 7, 5, [(2, 2, MASK), (4, 2, MASK)], 13)
    return f


def bolt(step):
    """Clawd throwing a bolt to find an anomaly; the bolt arcs over and the anomaly flares where it lands."""
    w, h, floor = 58, 22, 21
    f = canvas(w, h)
    cy = floor - 18
    crab(f, at=(0, cy), sitting=False, arm_r=1 if step == 0 else 3)
    t = step / (STEPS - 1)
    bx = 27 + t * 20
    by = cy + 2 - math.sin(t * math.pi) * 6 + t * 12
    rect(f, int(bx), int(by), 2, 1, MASK2)
    ax, ay = 49, floor - 5
    r = 3 + (1 if step == STEPS - 1 else 0) + (step % 2) * 0.5
    for k in range(20):                                  # the anomaly's shimmer, turning
        a = 2 * math.pi * k / 20 + step * 0.4
        if k % 5 != 0:
            px(f, ax + r * math.cos(a), ay + 0.7 * r * math.sin(a), ANOM)
    px(f, ax, ay, TITLE if step == STEPS - 1 else ANOM)
    for k in range(3):                                   # a leaf caught in it
        a = step * 1.2 + k * 2.1
        px(f, ax + (r + 2) * math.cos(a), ay + 0.7 * (r + 2) * math.sin(a), PACK)
    grass(f, floor, (30, 40))
    return f


def detector(step):
    """Clawd sweeping a detector over the grass; it beeps faster as an artifact glows ahead."""
    w, h, floor = 50, 22, 21
    f = canvas(w, h)
    cy = floor - 18
    crab(f, at=(0, cy), sitting=False)
    for k in range(6):                                   # the detector's rod down to the ground
        px(f, 26 + k, cy + 9 + k, MASK2)
    rect(f, 26, cy + 6, 4, 3, MASK2)                     # the box, its light blinking
    px(f, 27, cy + 7, FLAME_HI if step % 2 == 0 else EMBER)
    rect(f, 31, cy + 15, 4, 1, MASK2)                    # the sensor head
    if step % 2 == 0:                                    # beep
        for dx, dy in ((31, cy + 4), (33, cy + 5), (32, cy + 3)):
            px(f, dx, dy, FLAME_HI)
    artifact(f, 42, floor - 3, step)
    grass(f, floor, (37, 46))
    return f


def hunt(step):
    """Clawd sighting a rifle on a blind dog coming at a run; a muzzle flash, then it keeps coming."""
    w, h, floor = 72, 22, 21
    f = canvas(w, h)
    cy = floor - 18
    crab(f, at=(0, cy), sitting=False)
    kick = 1 if step == 2 else 0
    rifle(f, 22, cy + 7, kick)
    if step == 1:                                        # the shot
        rect(f, 40, cy + 6, 2, 3, FLAME_HI)
        px(f, 42, cy + 7, FLAME)
        px(f, 40, cy + 5, FLAME)
    if step == 2:
        px(f, 41, cy + 5, PUFF)
        px(f, 43, cy + 4, PUFF)
    dog(f, 58 - step * 2, floor, step)
    grass(f, floor, (30, 47, 66))
    return f


def stash(step):
    """Clawd opening a stash crate: a medkit, ammo and an artifact come out one by one."""
    w, h, floor = 48, 21, 20
    f = canvas(w, h)
    cy = floor - 16
    crab(f, at=(0, cy), arm_r=2)
    x0 = 31
    rect(f, x0, floor - 6, 13, 6, LOG)                   # the crate
    rect(f, x0, floor - 6, 13, 1, LOG_SHADE)
    rect(f, x0 + 6, floor - 5, 1, 5, LOG_SHADE)
    rect(f, x0 - 1, floor - 9, 2, 3, LOG_SHADE)          # its lid, propped open
    rect(f, x0 + 1, floor - 10, 11, 1, LOG_SHADE)
    items = [                                            # medkit, ammo, artifact
        lambda y: (rect(f, x0 + 2, y, 4, 3, EMBER), rect(f, x0 + 3, y + 1, 2, 1, TITLE)),
        lambda y: (rect(f, x0 + 7, y, 4, 2, PACK), px(f, x0 + 8, y, WARN), px(f, x0 + 10, y, WARN)),
        lambda y: (rect(f, x0 + 5, y, 3, 2, LENS), px(f, x0 + 6, y, TITLE)),
    ]
    for k, draw in enumerate(items):
        if step > k:
            draw(floor - 13 - (2 if step == k + 1 else 0) + k)
    if step == STEPS - 1:
        for dx, dy in ((x0 + 4, floor - 16), (x0 + 9, floor - 15), (x0 + 1, floor - 14)):
            px(f, dx, dy, FLAME_HI)
    return f


def trading(step):
    """Clawd trading an artifact with the trader across his counter: the artifact goes over, the coins come back."""
    w, h, floor = 70, 22, 21
    f = canvas(w, h)
    cy = floor - 18
    crab(f, at=(0, cy), sitting=False, arm_r=2)
    crab(f, at=(42, cy + 1), sitting=False, hood=MASK2, arm_l=2)
    rect(f, 26, floor - 7, 32, 7, LOG)                   # the counter
    rect(f, 26, floor - 7, 32, 1, LOG_SHADE)
    for x in (30, 40, 50):
        rect(f, x, floor - 5, 1, 5, LOG_SHADE)
    top = floor - 9
    ax = (28, 36, 44, 44)[step]                          # the artifact slides over
    rect(f, ax, top, 3, 2, LENS)
    px(f, ax + 1, top, TITLE)
    if step >= 2:                                        # the coins slide back
        coins(f, (50, 50, 42, 31)[step], top + 1)
    if step == 3:
        bubble(f, 50, 0, 7, 5, [(2, 2, WARN), (3, 2, WARN), (4, 2, WARN)], 53)
    return f


def exploring(step):
    """Clawd walking through the Zone with his pack, past a dead tree and a signpost going by."""
    w, h, floor = 56, 23, 22
    f = canvas(w, h)
    cy = floor - 18
    shift = step * 2                                     # the ground goes by, looping every 8 px
    for base in (4, 12, 20, 28, 36, 44, 52, 60):
        x = base - shift
        if 0 <= x < w:
            px(f, x, floor - 1, PACK)
            px(f, x + 1, floor - 1, PACK_SHADE)
    for base in (40, 48):                                # a dead tree going by, the same loop length
        x = base - shift
        if base == 40 and -6 < x < w:
            rect(f, x, floor - 12, 1, 12, LOG_SHADE)
            px(f, x - 1, floor - 9, LOG_SHADE)
            px(f, x - 2, floor - 10, LOG_SHADE)
            px(f, x + 1, floor - 7, LOG_SHADE)
            px(f, x + 2, floor - 8, LOG_SHADE)
    rect(f, 3, cy - 2, 8, 3, LOG)                        # the bedroll on his pack, over a shoulder
    rect(f, 3, cy - 2, 8, 1, LOG_SHADE)
    crab(f, at=(4, cy - (step % 2)), sitting=False, walk=step)
    rect(f, 9, cy + 4 - (step % 2), 2, 6, PACK_SHADE)    # pack straps
    rect(f, 25, cy + 4 - (step % 2), 2, 6, PACK_SHADE)
    return f


def sleeping(step):
    """Clawd asleep in his bedroll against his pack, goggles dark, Zs drifting up."""
    w, h, floor = 44, 21, 20
    f = canvas(w, h)
    cy = floor - 16
    rect(f, 0, cy + 2, 8, 12, PACK)                      # the pack behind him
    rect(f, 0, cy + 2, 8, 2, LOG)
    crab(f, at=(2, cy), lens=LENS_DIM)
    rect(f, 3, cy + 10, 26, 6, PACK)                     # the bedroll pulled up
    rect(f, 3, cy + 10, 26, 1, PACK_SHADE)
    rect(f, 3, cy + 15, 26, 1, PACK_SHADE)
    for k in range(3):
        rise = (step + k * 2) % 6
        if rise < 5:
            zx, zy = 31 + k * 4, cy + 6 - rise - k
            rect(f, zx, zy, 3, 1, SUB)
            px(f, zx + 1, zy + 1, SUB)
            rect(f, zx, zy + 2, 3, 1, SUB)
    return f


def repair(step):
    """Clawd sitting with a rifle across his knees, tightening it with a wrench; sparks on each turn."""
    w, h, floor = 48, 20, 19
    f = canvas(w, h)
    cy = floor - 16
    crab(f, at=(0, cy), arm_r=2 + (step % 2))
    rifle(f, 6, cy + 13)
    wy = cy + 5 + (step % 2) * 2                         # the wrench in the right hand
    rect(f, 26, wy, 6, 1, MASK2)
    rect(f, 31, wy - 1, 2, 3, MASK2)
    px(f, 32, wy, BG)
    if step % 2:
        for dx, dy in ((34, wy - 2), (35, wy + 1), (33, wy - 3)):
            px(f, dx, dy, FLAME_HI)
    rect(f, 36, floor - 3, 8, 3, EMBER)                  # the red toolbox
    rect(f, 36, floor - 3, 8, 1, SAUSAGE)
    rect(f, 38, floor - 4, 4, 1, MASK2)
    return f


def campfire_scene(step):
    """Clawd by his campfire, roasting a sausage (the zonecraft panel)."""
    return m.badge(step)


def planning(step):
    """Clawd with his PDA out plotting a route, his pack ready (the New mod form)."""
    return m.planning(step)


# name -> (what it shows, how to draw one step)
SCENES = {
    "campfire": campfire_scene,
    "planning": planning,
    "guitar": guitar,
    "stories": stories,
    "bolt": bolt,
    "detector": detector,
    "hunt": hunt,
    "stash": stash,
    "trading": trading,
    "exploring": exploring,
    "sleeping": sleeping,
    "repair": repair,
}


def frames(name):
    return [SCENES[name](step) for step in range(STEPS)]


def write_ts(path):
    """Every scene as TypeScript data: the palette and, per scene, each step's rows, one character per pixel
    (base-32 palette index, '.' transparent)."""
    digits = "0123456789abcdefghijklmnopqrstuv"
    lines = ["// Generated by assets/clawd_scenes.py (py -I assets/clawd_scenes.py hooks/clawd.ts); do not edit by hand.",
             "// Clawd, the zonecraft crab, doing what stalkers do in the Zone: one scene per activity.",
             "export type Scene = { readonly w: number; readonly h: number; readonly frames: readonly (readonly string[])[] }",
             "export const PALETTE: readonly string[] = [",
             "  " + ", ".join(f"'#{c:06x}'" for c in PALETTE) + ",",
             "]"]
    for name, draw in SCENES.items():
        doc = (draw.__doc__ or name).strip().rstrip(".")
        fr = frames(name)
        lines += [f"/** {doc}. */", f"export const {name.upper()}: Scene = {{",
                  f"  w: {len(fr[0][0])},", f"  h: {len(fr[0])},", "  frames: ["]
        for step in fr:
            lines.append("    [")
            lines += ["      '" + "".join("." if c == TRANSPARENT else digits[c] for c in row) + "'," for row in step]
            lines.append("    ],")
        lines += ["  ],", "}"]
    lines.append("export const SCENES = { " + ", ".join(f"{n}: {n.upper()}" for n in SCENES) + " } as const")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def write_gifs(folder, scale=4, delay=18):
    """One looping GIF per scene, on a transparent background."""
    os.makedirs(folder, exist_ok=True)
    keep = m.W, m.H, m.SCALE
    for name in SCENES:
        fr = frames(name)
        m.W, m.H, m.SCALE = len(fr[0][0]), len(fr[0]), scale
        m.write_gif(os.path.join(folder, f"{name}.gif"), [(f_, delay) for f_ in fr])
    m.W, m.H, m.SCALE = keep


def write_sheet(path, scale=4):
    """Every scene's steps side by side, each row on a light and a dark strip: for checking the drawings."""
    import struct
    import zlib
    rows = []
    for name in SCENES:
        fr = frames(name)
        for bg in (0xffffff, 0x262624):
            band = [[bg] * 2 for _ in range(len(fr[0]) + 2)]
            for step in fr:
                for y in range(len(fr[0]) + 2):
                    line = step[y - 1] if 0 < y <= len(step) else [TRANSPARENT] * len(step[0])
                    band[y] += [bg if c == TRANSPARENT else PALETTE[c] for c in line] + [bg] * 3
            rows += band
    width = max(len(r) for r in rows)
    raw = bytearray()
    for r in rows:
        r = r + [0x808080] * (width - len(r))
        line = bytearray([0])
        for c in r:
            line += bytes([(c >> 16) & 255, (c >> 8) & 255, c & 255]) * scale
        raw += bytes(line) * scale

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width * scale, len(rows) * scale, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


if __name__ == "__main__":
    out = sys.argv[1]
    if out.endswith(".ts"):
        write_ts(out)
    elif out.endswith(".png"):
        write_sheet(out)
    else:
        write_gifs(out)
    print(f"{len(SCENES)} scenes")
