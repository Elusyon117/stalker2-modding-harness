"""Animated zonecraft logo: a pixel crab in a gas mask stands in a hazy Zone at dusk (ruined plant, a warning sign,
a pulsing anomaly). It breathes through its filter, its goggles glint, the anomaly flares and the crab hops.
Pure Python (no Pillow): draws frames on a small pixel grid, scales them up and writes a looping GIF.

usage: py -I make_logo.py <out.gif> [frame,frame,...]   (frame list: write those frames as stills for preview)
"""
import math
import sys

W, H = 152, 48          # canvas in base pixels
SCALE = 5               # each base pixel is 5x5 in the GIF (760 x 240)

PALETTE = [
    0x1f1e1d,  # 0 background
    0xd97757,  # 1 crab
    0xa9533a,  # 2 crab shade
    0x2b2a27,  # 3 mask dark
    0x5b5850,  # 4 mask mid
    0xd4dc6a,  # 5 lens glow
    0x7d8a36,  # 6 lens dim
    0x2f2d27,  # 7 ruins silhouette
    0xfaf9f5,  # 8 title
    0xa1a1aa,  # 9 subtitle
    0x3a3830,  # 10 floor
    0x6e5f3e,  # 11 dull sun
    0xeab308,  # 12 warning yellow
    0x8f8b82,  # 13 breath puff
    0x7dd3fc,  # 14 anomaly
    0x000000,  # 15 transparent (rounded corners)
]
TRANSPARENT = 15
(BG, CRAB, SHADE, MASK, MASK2, LENS, LENS_DIM, RUIN, TITLE, SUB, FLOOR, SUN, WARN, PUFF, ANOM) = range(15)

FLOOR_Y = 42
CX, CY = 6, 24                  # crab origin
ANOM_C = (63, 35)

GLYPHS = {
    'z': ["     ", "     ", "XXXXX", "   X ", "  X  ", " X   ", "XXXXX"],
    'o': ["     ", "     ", " XXX ", "X   X", "X   X", "X   X", " XXX "],
    'n': ["     ", "     ", "X XX ", "XX  X", "X   X", "X   X", "X   X"],
    'e': ["     ", "     ", " XXX ", "X   X", "XXXXX", "X    ", " XXX "],
    'c': ["     ", "     ", " XXX ", "X    ", "X    ", "X    ", " XXX "],
    'r': ["     ", "     ", "X XX ", "XX  X", "X    ", "X    ", "X    "],
    'a': ["     ", "     ", " XXX ", "    X", " XXXX", "X   X", " XXXX"],
    'f': ["  XX ", " X   ", " X   ", "XXXX ", " X   ", " X   ", " X   "],
    't': [" X   ", " X   ", "XXXX ", " X   ", " X   ", " X  X", "  XX "],
}
SMALL = {
    'b': ["X  ", "XX ", "X X", "X X", "XX "],
    'y': ["   ", "X X", "X X", " XX", "  X", "XX "],
    'E': ["XXX", "X  ", "XX ", "X  ", "XXX"],
    'l': ["X  ", "X  ", "X  ", "X  ", "XX "],
    'u': ["   ", "X X", "X X", "X X", " XX"],
    's': ["   ", " XX", "X  ", "  X", "XX "],
    'o': ["   ", " X ", "X X", "X X", " X "],
    'n': ["   ", "XX ", "X X", "X X", "X X"],
    ' ': ["   "] * 5,
}


def blank():
    return [[BG] * W for _ in range(H)]


def px(f, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < W and 0 <= y < H:
        f[y][x] = c


def rect(f, x, y, w, h, c):
    for yy in range(max(0, y), min(H, y + h)):
        for xx in range(max(0, x), min(W, x + w)):
            f[yy][xx] = c


def text(f, words, x0, y0, color, font=GLYPHS, advance=6):
    for n, ch in enumerate(words):
        for gy, line in enumerate(font[ch]):
            for gx, p in enumerate(line):
                if p == 'X':
                    f[y0 + gy][x0 + n * advance + gx] = color


# ---- the Zone ------------------------------------------------------------------------------------------------
def backdrop(f, anomaly_r, flare):
    for y in range(H):                                  # dull sun low on the horizon
        for x in range(W):
            if (x - 44) ** 2 + (y - 13) ** 2 <= 20:
                f[y][x] = SUN
    # a nuclear plant in the style of the one in the Zone: long turbine hall, reactor block and the tall striped
    # ventilation stack inside its lattice tower
    rect(f, 46, 34, 26, 8, RUIN)                         # turbine hall
    for wx in range(48, 70, 3):
        rect(f, wx, 36, 1, 2, BG)
    rect(f, 52, 25, 12, 9, RUIN)                         # reactor block
    rect(f, 49, 29, 3, 5, RUIN)
    rect(f, 64, 29, 5, 5, RUIN)
    for k in range(16):                                  # lattice tower: two legs narrowing upwards...
        y = 25 - k
        px(f, 53 + k * 3 / 15, y, FLOOR)
        px(f, 63 - k * 3 / 15, y, FLOOR)
    for y in (11, 15, 19, 23):                           # ...with cross braces
        rect(f, 54, y, 9, 1, FLOOR)
    for k in range(4):                                   # diagonal bracing between them
        for s in range(4):
            px(f, 55 + s * 2 - (k % 2) * 0, 12 + k * 4 - (s % 2), FLOOR)
    rect(f, 57, 6, 3, 19, MASK2)                         # the stack, red bands at the top
    for y in (6, 10, 14):
        rect(f, 57, y, 3, 2, SHADE)
    rect(f, 56, 6, 5, 1, MASK2)
    rect(f, 4, FLOOR_Y, 68, 1, FLOOR)
    # warning sign on a post: yellow triangle with a dark "!"
    rect(f, 44, 35, 1, 7, MASK2)
    for row in range(6):
        rect(f, 44 - row, 29 + row, 1 + 2 * row, 1, WARN)
    rect(f, 44, 31, 1, 2, BG)
    px(f, 44, 34, BG)
    # anomaly: a pulsing ring of light just above the ground, sparks when it flares
    ax, ay = ANOM_C
    for k in range(28):
        a = 2 * math.pi * k / 28
        px(f, ax + anomaly_r * math.cos(a), ay + 0.75 * anomaly_r * math.sin(a), ANOM)
    px(f, ax, ay, ANOM)
    if flare:
        for k in range(8):
            a = 2 * math.pi * k / 8 + 0.3
            px(f, ax + (anomaly_r + 3) * math.cos(a), ay + 0.75 * (anomaly_r + 3) * math.sin(a), TITLE)


# ---- the crab in a gas mask ---------------------------------------------------------------------------------
def crab(f, dy=0, lens=LENS, glint=None):
    def cell(cx, cy, cw, ch, c=CRAB):
        rect(f, CX + cx * 2, CY + dy + cy * 2, cw * 2, ch * 2, c)
    cell(3, 0, 8, 7)                                     # head + body
    cell(1, 3, 2, 2)                                     # arms
    cell(11, 3, 2, 2)
    for lx in (3, 5, 8, 10):                             # legs
        cell(lx, 7, 1, 2)
    ox, oy = CX, CY + dy
    rect(f, ox + 6, oy + 4, 16, 1, MASK)                 # head strap
    rect(f, ox + 7, oy + 1, 14, 8, MASK)                 # rubber face plate
    for x, y in ((7, 1), (20, 1), (7, 8), (20, 8)):
        px(f, ox + x, oy + y, CRAB)
    for gx in (7, 15):                                   # goggles: metal rim, glowing lens
        rect(f, ox + gx, oy + 1, 6, 6, MASK2)
        rect(f, ox + gx + 1, oy + 2, 4, 4, lens)
        rect(f, ox + gx + 1, oy + 5, 4, 1, LENS_DIM if lens == LENS else lens)
        px(f, ox + gx + 1, oy + 2, TITLE if lens == LENS else lens)   # highlight
    if glint is not None:                                # a glint sweeping across the lenses
        for gx in (7, 15):
            px(f, ox + gx + 2 + glint, oy + 2 + glint, TITLE)
    rect(f, ox + 10, oy + 7, 8, 3, MASK)                 # respirator snout
    rect(f, ox + 11, oy + 10, 6, 5, MASK2)               # filter can
    rect(f, ox + 11, oy + 11, 6, 1, MASK)
    rect(f, ox + 11, oy + 13, 6, 1, MASK)
    rect(f, ox + 12, oy + 15, 4, 1, MASK)


def corners(f, r=4):
    for y in range(H):
        for x in range(W):
            cx = r if x < r else (W - 1 - r if x >= W - r else x)
            cy = r if y < r else (H - 1 - r if y >= H - r else y)
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                f[y][x] = TRANSPARENT


def scene(t, dy=0, lens=LENS, glint=None, puffs=(), anomaly_r=3.0, flare=False):
    f = blank()
    backdrop(f, anomaly_r, flare)
    crab(f, dy, lens, glint)
    for x, y, c in puffs:
        px(f, x, y + dy, c)
    text(f, "zonecraft", 84, 17, TITLE)
    text(f, "by Elusyon", 85, 27, SUB, SMALL, 4)
    corners(f)
    return f


def breath(step):
    """Puff particles out of both sides of the filter can, step 0..7."""
    if step is None or step > 7:
        return []
    c = PUFF if step < 5 else FLOOR
    out = []
    base_y = CY + 12
    for side in (-1, 1):
        cx = CX + 14 + side * (5 + step * 1.3)
        cy = base_y - step * 1.1
        out.append((cx, cy, c))
        if step > 1:
            out.append((cx + side, cy - 1, c))
        if 2 < step < 6:
            out.append((cx - side, cy - 2, c))
    return out


def frames():
    out = []   # (frame, delay in 1/100 s)
    n = 0
    for cycle in range(3):                               # three calm breaths
        for k in range(12):
            r = 3.0 + 0.8 * math.sin((n + k) * 0.6)
            dy = 1 if (k // 3) % 2 else 0
            glint = (k - 6) if (cycle == 1 and 6 <= k <= 8) else None
            out.append((scene(n, dy=dy, glint=glint, puffs=breath(k - 3 if k >= 3 else None), anomaly_r=r), 9))
        n += 12
    for k, r in enumerate((4.5, 6.0, 7.5, 8.5)):         # the anomaly flares...
        out.append((scene(n, lens=LENS if k % 2 else LENS_DIM, anomaly_r=r, flare=k >= 1), 6))
    for dy in (-2, -4, -4, -2, 0):                        # ...and the crab hops
        out.append((scene(n, dy=dy, anomaly_r=5.0, flare=dy == -4), 6))
    for k in range(6):                                    # settles, breathing hard
        out.append((scene(n, dy=k % 2, puffs=breath(k + 1), anomaly_r=3.0 + 0.5 * (k % 2)), 8))
    out.append((scene(n, anomaly_r=3.0), 60))
    return out


# ---- GIF writer ---------------------------------------------------------------------------------------------
def lzw(indices, min_size):
    clear, eoi = 1 << min_size, (1 << min_size) + 1
    size = min_size + 1
    nxt = eoi + 1
    table = {}
    bits = 0
    nbits = 0
    out = bytearray()

    def emit(code):
        nonlocal bits, nbits
        bits |= code << nbits
        nbits += size
        while nbits >= 8:
            out.append(bits & 0xFF)
            bits >>= 8
            nbits -= 8

    emit(clear)
    prefix = indices[0]
    for k in indices[1:]:
        key = (prefix, k)
        code = table.get(key)
        if code is not None:
            prefix = code
            continue
        emit(prefix)
        if nxt < 4096:
            table[key] = nxt
            nxt += 1
            if nxt > (1 << size) and size < 12:
                size += 1
        else:
            emit(clear)
            table = {}
            size = min_size + 1
            nxt = eoi + 1
        prefix = k
    emit(prefix)
    emit(eoi)
    if nbits:
        out.append(bits & 0xFF)
    return bytes(out)


def scaled(f):
    data = bytearray()
    for row in f:
        line = bytearray()
        for c in row:
            line.extend([c] * SCALE)
        for _ in range(SCALE):
            data.extend(line)
    return data


def write_gif(path, seq):
    w, h = W * SCALE, H * SCALE
    g = bytearray(b"GIF89a")
    g += w.to_bytes(2, "little") + h.to_bytes(2, "little")
    g += bytes([0xB3, 0, 0])                       # global table, 16 colors
    for c in PALETTE:
        g += bytes([(c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF])
    g += b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00"   # loop forever
    for f, delay in seq:
        g += b"\x21\xF9\x04" + bytes([0x05]) + delay.to_bytes(2, "little") + bytes([TRANSPARENT, 0])
        g += b"\x2C" + (0).to_bytes(2, "little") * 2 + w.to_bytes(2, "little") + h.to_bytes(2, "little") + b"\x00"
        g += bytes([4])
        data = lzw(scaled(f), 4)
        for i in range(0, len(data), 255):
            chunk = data[i:i + 255]
            g += bytes([len(chunk)]) + chunk
        g += b"\x00"
    g += b"\x3B"
    with open(path, "wb") as fh:
        fh.write(g)


def write_icon(path, size=64, scale=8):
    """Square PNG (size*scale px): the masked crab in front of the plant's stack, for the plugin listing."""
    import struct
    import zlib
    global W, H, CX, CY
    W, H = size, size
    CX, CY = 18, 30
    f = blank()
    rect(f, 39, 6, 5, 36, MASK2)                              # stack, red bands
    for y in (6, 12, 18):
        rect(f, 39, y, 5, 3, SHADE)
    for k in range(30):                                       # lattice legs
        px(f, 35 + k * 3 / 29, 41 - k, FLOOR)
        px(f, 47 - k * 3 / 29, 41 - k, FLOOR)
    for y in (14, 22, 30, 38):
        rect(f, 36, y, 11, 1, FLOOR)
    rect(f, 30, 42, 26, 10, RUIN)                             # reactor block
    rect(f, 4, 50, 56, 1, FLOOR)
    crab(f)
    raw = bytearray()
    for row in f:
        line = bytearray([0])
        for c in row:
            rgb = PALETTE[BG if c == TRANSPARENT else c]
            line += bytes([(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255]) * scale
        raw += bytes(line) * scale
    n = size * scale

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


if __name__ == "__main__":
    if sys.argv[1].endswith(".png"):
        write_icon(sys.argv[1])
        sys.exit(0)
    seq = frames()
    if len(sys.argv) > 2:
        for k in sys.argv[2].split(','):
            write_gif(sys.argv[1].replace('.gif', f'-frame{k}.gif'), [seq[int(k)]])
        sys.exit(0)
    write_gif(sys.argv[1], seq)
    print(f"{len(seq)} frames, {sum(d for _, d in seq) / 100:.1f}s loop")
