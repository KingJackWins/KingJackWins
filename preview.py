#!/usr/bin/env python3
"""Draws preview.gif for the GitHub profile: a crowned walker at sundown,
trailed by a glowing memory orb.

The art is drawn at 128x72 and scaled 5x. Every moving layer shifts by a whole
multiple of its own period over the loop, so the GIF repeats without a seam.

    python3 preview.py [out.gif]
"""
import math
import random
import sys

from PIL import Image

W, H, SCALE = 128, 72, 5
N = 128                      # frames per loop; every period below divides it
DELAY_MS = 60
GROUND_Y = 57
SUN_X, SUN_Y, SUN_R = 32, 41, 12
WALKER_X, WALKER_Y = 60, 36
ORB_X, ORB_Y = 54, 26


def rgb(hexcode):
    h = hexcode.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t + 0.5) for i in range(3))


def rnd(v):
    return int(math.floor(v + 0.5))


def wave(t, period, phase=0.0):
    # wrap before the sin so frame N lands on bit-identical values to frame 0
    return math.sin(2 * math.pi * ((t + phase) % period) / period)


BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def dithered(ramp, t, x, y):
    """Pick between neighbouring ramp colours with a 4x4 ordered dither."""
    t = min(max(t, 0.0), 1.0) * (len(ramp) - 1)
    i = int(t)
    if i >= len(ramp) - 1:
        return ramp[-1]
    return ramp[i + 1] if (t - i) * 16 > BAYER[y % 4][x % 4] + 0.5 else ramp[i]


# ── palette ──────────────────────────────────────────────────────────────────
SKY = [rgb(c) for c in (
    "#141330", "#1c1a3f", "#282050", "#3a2762", "#523072", "#723a7d",
    "#984581", "#bd537f", "#dc6878", "#ef8870", "#f7ab6d", "#fbcd86")]
SKY_BOTTOM = 52
SUN = [rgb(c) for c in ("#fff7cc", "#ffe9a0", "#ffd47c", "#ffbb68", "#ff9f5f")]
HALO = rgb("#ffc27e")
HAZE, HAZE_EDGE = rgb("#8a4a80"), rgb("#b3607f")
FAR, FAR_EDGE, FAR_LIT = rgb("#33275a"), rgb("#3f3068"), rgb("#6a4583")
MID, MID_EDGE = rgb("#241d45"), rgb("#3a2c5e")
TREE, TREE_LIT = rgb("#19143a"), rgb("#3b2b5f")
GRASS, GRASS_TIP, GRASS_DARK = rgb("#3a2f63"), rgb("#7a5382"), rgb("#2a2350")
PATH, PATH_EDGE, PEBBLE = rgb("#3b3163"), rgb("#2b2450"), rgb("#56487e")
GROUND, SPECK = rgb("#17132c"), rgb("#262045")
FLOWER_A, FLOWER_B = rgb("#f7a06b"), rgb("#ffd98a")
SHADOW = rgb("#221b40")
FG, FG_TIP = rgb("#0b0918"), rgb("#221a3c")
STAR_DIM, STAR_MID, STAR_HI = rgb("#6d5f9c"), rgb("#bdb3e6"), rgb("#ffffff")
TRAIL = [rgb(c) for c in ("#ffffff", "#e6e0ff", "#bdb3e6", "#9589c4", "#6d5f9c", "#4d4280")]
ORB_CORE, ORB_IN, ORB_OUT, ORB_FADE = rgb("#f2ffff"), rgb("#8fe9ff"), rgb("#3fa3dd"), rgb("#2c5f9c")
FIREFLY, FIREFLY_DIM = rgb("#efffa6"), rgb("#7d8a55")
OUTLINE = rgb("#120d22")

# sprite materials: key -> (base, rim-lit by the low sun on the left)
MAT = {k: (rgb(a), rgb(b)) for k, (a, b) in {
    "Y": ("#ffd35a", "#fff1a8"), "y": ("#d99a2b", "#ffcf5a"), "J": ("#ff5a72", "#ff9aa6"),
    "H": ("#4b2d22", "#a0583a"), "h": ("#321c16", "#7a3e2a"),
    "S": ("#f3c9a2", "#ffe3c6"), "s": ("#d69c7c", "#f3c9a2"),
    "E": ("#1b1326", "#1b1326"), "C": ("#ef9a8e", "#ffb9a8"),
    "W": ("#efe9f7", "#fff1dc"), "w": ("#b9aad3", "#e9c6a6"), "A": ("#ddd3ee", "#fff1dc"),
    "P": ("#3b4a86", "#7e6aa2"), "p": ("#28315e", "#574a80"),
    "B": ("#221b35", "#6a4a62"), "b": ("#2f2745", "#4d3d5c"),
}.items()}

# ── static backdrop: sky, sun, haze ridge, far mountains ─────────────────────
HAZE_PTS = ((0, 48), (14, 45), (30, 49), (44, 47), (60, 48), (78, 45), (96, 47), (112, 44), (128, 47))
FAR_PTS = ((0, 45), (8, 40), (15, 36), (22, 42), (28, 48), (38, 51), (48, 49), (56, 44), (64, 39),
           (72, 34), (80, 40), (90, 45), (100, 38), (109, 42), (118, 46), (128, 43))


def interp(points, x):
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


rng = random.Random(11)
HAZE_TOP = [rnd(interp(HAZE_PTS, x) + 0.8 * wave(x, 23)) for x in range(W)]
FAR_TOP = [rnd(interp(FAR_PTS, x)) + rng.choice((0, 0, 0, 0, 1)) for x in range(W)]


def faces_sun(tops, x):
    nb = min(max(x - 1 if x > SUN_X else x + 1, 0), W - 1)
    return tops[nb] > tops[x]


def build_backdrop():
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            sky = dithered(SKY, y / SKY_BOTTOM, x, y)
            d2 = (x - SUN_X) ** 2 + (y - SUN_Y) ** 2
            rim = math.sqrt(d2) - SUN_R
            if d2 <= SUN_R * SUN_R + SUN_R:
                c = dithered(SUN, (y - SUN_Y + SUN_R) / (2 * SUN_R), x, y)
            elif rim <= 2:
                c = mix(sky, HALO, 0.42)
            elif rim <= 4:
                c = mix(sky, HALO, 0.22)
            elif rim <= 7:
                c = mix(sky, HALO, 0.10)
            else:
                c = sky
            px[x, y] = c
    for x in range(W):
        for y in range(HAZE_TOP[x], H):
            px[x, y] = HAZE_EDGE if y == HAZE_TOP[x] else HAZE
        lit = faces_sun(FAR_TOP, x)
        for y in range(FAR_TOP[x], H):
            if lit and y <= FAR_TOP[x] + 1:
                px[x, y] = FAR_LIT
            else:
                px[x, y] = FAR_EDGE if y == FAR_TOP[x] else FAR
    return img


# ── sky life: stars, one shooting star ───────────────────────────────────────
srng = random.Random(3)
STARS = []
while len(STARS) < 34:
    sx, sy = srng.randrange(W), srng.randrange(1, 30)
    if math.hypot(sx - SUN_X, sy - SUN_Y) < SUN_R + 9 or math.hypot(sx - ORB_X, sy - ORB_Y) < 9:
        continue
    if any(abs(sx - x) <= 2 and abs(sy - y) <= 2 for x, y, *_ in STARS):
        continue
    period = srng.choice((16, 32, 64))
    STARS.append((sx, sy, srng.random(), period, srng.randrange(period)))


def put(px, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[x, y] = c


def draw_sky_life(px, f):
    for x, y, kind, period, phase in STARS:
        if kind < 0.55:
            put(px, x, y, STAR_MID if y < 14 else STAR_DIM)
            continue
        v = (wave(f, period, phase) + 1) / 2
        if v > 0.85:
            put(px, x, y, STAR_HI)
            if kind > 0.88:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    put(px, x + dx, y + dy, STAR_DIM)
        elif v > 0.5:
            put(px, x, y, STAR_MID)
        elif v > 0.2:
            put(px, x, y, STAR_DIM)
    t = f - 76
    if 0 <= t < 9:
        hx, hy = 118 - 5 * t, 2 + rnd(1.6 * t)
        fade = 2 if t >= 7 else 0
        for k, c in enumerate(TRAIL[fade:]):
            put(px, hx + 2 * k, hy - rnd(0.64 * k), c)


# ── mid hills + pines (1px every 2 frames, period 64) ────────────────────────
def mid_top(wx):
    return rnd(51 - 3 * wave(wx, 64) - 1.5 * wave(wx, 32, 6) - 0.7 * wave(wx, 64 / 5, 2))


TREES = ((4, 7), (9, 5), (25, 9), (30, 6), (44, 7), (51, 10), (56, 6))


def draw_pine(px, cx, base, h):
    for i in range(h):
        y = base - h + i
        hw = min(i // 2, 3)
        for x in range(cx - hw, cx + hw + 1):
            lit_edge = (x == cx - hw) if cx > SUN_X else (x == cx + hw)
            put(px, x, y, TREE_LIT if lit_edge and i > 1 else TREE)
    put(px, cx, base, TREE)


def draw_mid(px, f):
    off = (f // 2) % 64
    for x in range(W):
        top = mid_top((x + off) % 64)
        for y in range(top, GROUND_Y):
            px[x, y] = MID_EDGE if y == top else MID
    for wx, h in TREES:
        for rep in (0, 1, 2):
            cx = wx - off + rep * 64
            if -4 <= cx < W + 4:
                draw_pine(px, cx, mid_top(wx) + 1, h)


# ── fireflies (ride the ground layer) ────────────────────────────────────────
FIREFLIES = ((20, 49, 0), (47, 53, 11), (95, 46, 23), (116, 52, 5))


def draw_fireflies(px, f):
    for wx, by, ph in FIREFLIES:
        blink = (f + ph) % 32
        if blink >= 22:
            continue
        x = (wx - f + rnd(2 * wave(f, 64, ph))) % W
        y = by + rnd(2 * wave(f, 32, ph))
        put(px, x, y, FIREFLY if blink < 18 else FIREFLY_DIM)


# ── ground: grass edge, path, meadow (1px per frame, period 128) ─────────────
grng = random.Random(5)
TUFTS = sorted((grng.randrange(W), grng.choice("sstf")) for _ in range(18))
PEBBLES = [(grng.randrange(W), grng.randrange(GROUND_Y + 2, GROUND_Y + 6)) for _ in range(12)]
SPECKS = [(grng.randrange(W), grng.randrange(GROUND_Y + 7, H)) for _ in range(34)]
TUFT_SHAPES = {
    "s": ((0, -1), (1, -2), (2, -1)),
    "t": ((0, -1), (0, -2), (1, -3), (2, -1), (2, -2)),
    "f": ((0, -1), (0, -2), (1, -3), (2, -1), (2, -2)),
}


def draw_ground(px, f):
    off = f % W
    for x in range(W):
        for y in range(GROUND_Y, H):
            if y == GROUND_Y:
                c = GRASS
            elif y == GROUND_Y + 1 or y == GROUND_Y + 6:
                c = PATH_EDGE
            elif y <= GROUND_Y + 5:
                c = PATH
            else:
                c = GROUND
            px[x, y] = c
    for group, color in ((PEBBLES, PEBBLE), (SPECKS, SPECK)):
        for wx, y in group:
            put(px, (wx - off) % W, y, color)
    for wx, kind in TUFTS:
        shape = TUFT_SHAPES[kind]
        top = min(dy for _, dy in shape)
        for bx in ((wx - off) % W, (wx - off) % W - W):
            for dx, dy in shape:
                put(px, bx + dx, GROUND_Y + dy, GRASS_TIP if dy == top else GRASS)
            if kind == "f":
                put(px, bx + 1, GROUND_Y - 4, FLOWER_A if wx % 2 else FLOWER_B)


def draw_foreground(px, f):
    off = (2 * f) % W
    for base in (6, 41, 83, 110):
        for i, h in enumerate((4, 7, 5, 8, 3)):
            x0 = (base + 2 * i - off) % W
            for k in range(h):
                y = H - 1 - k
                x = x0 - (1 if k >= h * 2 // 3 else 0)
                put(px, x, y, FG_TIP if k == h - 1 else FG)


# ── the walker ───────────────────────────────────────────────────────────────
HEAD = (
    "......Y..Y..Y...",
    "......YY.Y.YY...",
    "......yYYJYYy...",
    ".....HHHHHHHH...",
    "....HHHHHHHHHH..",
    "....HHHHHHHHHHH.",
    "....HHHHSSSSESS.",
    "....hHHsSSSSESSS",
    "....hHHSSSSCSSS.",
    ".....hHSSSSSSSs.",
    "......hsSSSSSs..",
)
TORSO = (
    "......wWWWWW....",
    ".....wWWWWWWW...",
    ".....wWWWWWWW...",
    ".....wWWWWWWW...",
    ".....wWWWWWWW...",
    ".....wWWWWWWW...",
    ".....wwwwwwww...",
)


def leg_pose(k):
    """Planted feet ride the ground at 1px/frame; swinging feet lift and return."""
    if k < 8:
        return 3 - k, 0
    j = k - 8
    return -4 + j, (0, 1, 2, 3, 3, 2, 1, 0)[j]


def stroke(sprite, a, b, key, thick=2):
    (x0, y0), (x1, y1) = a, b
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        x = rnd(x0 + (x1 - x0) * i / steps)
        y = rnd(y0 + (y1 - y0) * i / steps)
        for t in range(thick):
            sprite[(x + t, y)] = key


def blit_rows(sprite, rows, top):
    for r, row in enumerate(rows):
        for c, key in enumerate(row):
            if key != ".":
                sprite[(c, top + r)] = key


def draw_leg(sprite, hip_x, hip_y, dx, lift, leg, shoe):
    ax, ay = hip_x + dx, 23 - lift
    if lift:
        knee = (hip_x + dx // 2 + 1, (hip_y + ay) // 2)
        stroke(sprite, (hip_x, hip_y), knee, leg)
        stroke(sprite, knee, (ax, ay), leg)
    else:
        stroke(sprite, (hip_x, hip_y), (ax, ay), leg)
    for x in range(ax - 1, ax + 3):
        sprite[(x, ay + 1)] = shoe
        sprite[(x, ay + 2)] = shoe


def draw_arm(sprite, sx, sy, adx, edge, fill, hand):
    for r in range(5):
        x = sx + rnd(adx * r / 4)
        sprite[(x, sy + r)] = edge
        sprite[(x + 1, sy + r)] = fill
    hx = sx + adx
    sprite[(hx, sy + 5)] = hand
    sprite[(hx + 1, sy + 5)] = hand


def walker(f):
    k = f % 16
    near_dx, near_lift = leg_pose(k)
    far_dx, far_lift = leg_pose((k + 8) % 16)
    bob = 1 if k % 8 in (7, 0) else 0
    arm = max(-2, min(2, rnd(-near_dx * 0.6)))
    sprite = {}
    draw_arm(sprite, 7, 12 + bob, -arm, "w", "w", "s")
    draw_leg(sprite, 6, 18 + bob, far_dx, far_lift, "p", "b")
    blit_rows(sprite, TORSO, 11 + bob)
    blit_rows(sprite, HEAD, bob)
    draw_leg(sprite, 9, 18 + bob, near_dx, near_lift, "P", "B")
    draw_arm(sprite, 10, 12 + bob, arm, "w", "A", "S")

    shaded = {}
    for (x, y), key in sprite.items():
        base, lit = MAT[key]
        shaded[(x, y)] = lit if (x - 1, y) not in sprite else base
    for (x, y) in sprite:
        for n in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if n not in sprite:
                shaded[n] = OUTLINE
    return shaded


def draw_walker(px, f):
    for x in range(WALKER_X + 1, WALKER_X + 14):
        put(px, x, WALKER_Y + 26, SHADOW)
    for (x, y), c in walker(f).items():
        put(px, WALKER_X + x, WALKER_Y + y, c)


# ── the memory orb and its trail ─────────────────────────────────────────────
def orb_pos(f):
    return ORB_X + rnd(2 * wave(f, 64)), ORB_Y + rnd(2 * wave(f, 32))


def draw_orb(px, f):
    for s in range(0, N, 8):
        age = (f - s) % N
        if age >= 16:
            continue
        ox, oy = orb_pos(s)
        x, y = ox - 3 - age, oy - age // 4 + (s // 8) % 3 - 1   # left behind, rising
        if age < 3:
            put(px, x, y, STAR_HI)
            if age < 2:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    put(px, x + dx, y + dy, ORB_IN)
        else:
            put(px, x, y, ORB_IN if age < 7 else ORB_OUT if age < 12 else ORB_FADE)
    ox, oy = orb_pos(f)
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            d = math.hypot(dx, dy)
            x, y = ox + dx, oy + dy
            if d <= 1.0:
                put(px, x, y, ORB_CORE)
            elif d <= 2.3:
                put(px, x, y, ORB_IN)
            elif d <= 3.6 and (x + y) % 2 == 0:
                put(px, x, y, ORB_OUT)
            elif 3.6 < d <= 5.3 and 0 <= x < W and 0 <= y < H and BAYER[y % 4][x % 4] < 3:
                put(px, x, y, ORB_OUT)


# ── render ───────────────────────────────────────────────────────────────────
def render_frame(backdrop, f):
    img = backdrop.copy()
    px = img.load()
    draw_sky_life(px, f)
    draw_mid(px, f)
    draw_fireflies(px, f)
    draw_ground(px, f)
    draw_walker(px, f)
    draw_orb(px, f)
    draw_foreground(px, f)
    return img


def render():
    backdrop = build_backdrop()
    frames = [render_frame(backdrop, f) for f in range(N)]
    # the loop is seamless only if the frame after the last one IS the first
    if render_frame(backdrop, N).tobytes() != frames[0].tobytes():
        sys.exit("seam: frame N does not match frame 0")
    return [fr.resize((W * SCALE, H * SCALE), Image.NEAREST) for fr in frames]


def save_gif(frames, path):
    colors = sorted({c for fr in frames for _, c in fr.getcolors(1 << 20)})
    if len(colors) > 256:
        sys.exit(f"palette overflow: {len(colors)} colours")
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in colors for v in c] + [0] * (768 - 3 * len(colors)))
    indexed = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:],
                    duration=DELAY_MS, loop=0, disposal=1, optimize=False)
    return len(colors)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "preview.gif"
    n = save_gif(render(), out)
    print(f"{out}: {N} frames, {n} colours")
