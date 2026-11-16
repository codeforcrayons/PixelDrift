#!/usr/bin/env python3
"""
PixelDrift art generator.

Draws every sheet pixel by pixel from a few rules, so the art can be restyled
by editing numbers and re-running:

    python3 make_art.py            (writes into ./sheets next to this file)

Outputs
    sheets/car_hatch.png   576x64   9 frames of 64x64, frame 4 = wheels centred
    sheets/car_coupe.png   576x64
    sheets/car_wedge.png   576x64
    sheets/tiles.png       1024x512 8x4 grid of 128x128 tiles (see TILE INDEX)

Cars face RIGHT (GameMaker angle 0). Frame 0 = full left lock, 8 = full right.
"""
import math
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sheets")

# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def noise(x, y, seed=0):
    """Deterministic 0..1 value per pixel (so re-running gives the same art)."""
    n = (x * 374761393 + y * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def shade(rgb, amount):
    return tuple(max(0, min(255, int(c + amount))) for c in rgb)


def profile(points, x):
    """Half-width of a shape at position x, from a list of (x, halfwidth)."""
    if x < points[0][0] or x > points[-1][0]:
        return -1.0
    for (x0, w0), (x1, w1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            return w0 + (w1 - w0) * t
    return -1.0


# --------------------------------------------------------------------------
# CARS
# --------------------------------------------------------------------------
FRAME = 64
FRAMES = 9
MAX_WHEEL_DEG = 40          # visual lock at frames 0 and 8
WHEEL_LEN, WHEEL_WID = 12, 6
TYRE = (24, 24, 28)
TREAD = (46, 46, 54)
GLASS = (28, 38, 58)
GLASS_HI = (96, 130, 170)
HEADLIGHT = (255, 240, 170)
TAILLIGHT = (225, 40, 45)

# All coordinates are car-local pixels: x forward (+ is the nose), y sideways,
# (0, 0) is the centre of the 64x64 frame.
CARS = {
    "hatch": dict(      # short wheelbase, boxy, AWD
        body=[(-20, 9), (-19, 11), (14, 11), (18, 10), (20, 7)],
        glass=[(-15, 9), (8, 9)],
        roof=[(-12, 8), (3, 8)],
        front_axle=12, rear_axle=-12, front_track=12, rear_track=12,
        paint=(45, 105, 215), light=(96, 152, 245), dark=(22, 54, 130),
    ),
    "coupe": dict(      # long bonnet, cabin set back, front engine RWD
        body=[(-24, 8), (-22, 11), (-8, 12), (10, 11), (20, 10), (24, 6)],
        glass=[(-17, 8), (-12, 9), (4, 9)],
        roof=[(-11, 8), (-2, 8)],
        front_axle=16, rear_axle=-14, front_track=12, rear_track=13,
        paint=(205, 45, 50), light=(242, 100, 92), dark=(120, 18, 28),
    ),
    "wedge": dict(      # long wheelbase, cab forward, wide tail, mid engine RWD
        body=[(-26, 11), (-24, 13), (-10, 13), (2, 11), (16, 9), (23, 7), (26, 4)],
        glass=[(-3, 9), (6, 8), (14, 6)],
        roof=[(0, 7), (7, 7)],
        front_axle=17, rear_axle=-17, front_track=10, rear_track=14,
        paint=(240, 168, 34), light=(255, 214, 96), dark=(150, 92, 12),
    ),
}


def car_detail(name, x, y, c):
    """Per-car decoration. Returns a colour or None. y is |sideways|."""
    if name == "hatch":
        if -12 <= x <= 20 and y < 2:
            return (238, 238, 232)                      # centre stripe
        if x >= 18 and 4 <= y <= 9:
            return HEADLIGHT
        if x <= -19 and 5 <= y <= 10:
            return TAILLIGHT
        if -19 <= x < -17:
            return c["dark"]                            # roof spoiler lip
    if name == "coupe":
        if 4 <= x <= 23 and 2 <= y < 4:
            return (30, 30, 34)                         # twin bonnet stripes
        if -24 <= x <= -17 and 2 <= y < 4:
            return (30, 30, 34)
        if x >= 21 and 5 <= y <= 8:
            return HEADLIGHT
        if x <= -23 and 3 <= y <= 9:
            return TAILLIGHT
    if name == "wedge":
        if x <= -24:
            return (30, 30, 34)                         # rear wing
        if -21 <= x <= -6 and y < 7 and int(x) % 3 == 0:
            return (30, 30, 34)                         # engine louvres
        if -8 <= x <= -4 and y >= 11:
            return (30, 30, 34)                         # side intakes
        if 19 <= x <= 22 and 3 <= y <= 5:
            return HEADLIGHT
        if -24 < x <= -22 and 6 <= y <= 11:
            return TAILLIGHT
    return None


def car_pixel(name, c, x, y, steer_deg):
    """Colour of one pixel of a car, or None for transparent."""
    ay = abs(y)
    body_w = profile(c["body"], x)
    in_body = ay <= body_w

    if in_body:
        # 1px dark outline wherever the next pixel outward leaves the body
        edge = (ay + 1 > body_w or profile(c["body"], x - 1) < ay
                or profile(c["body"], x + 1) < ay)
        if edge:
            return c["dark"]
        d = car_detail(name, x, ay, c)
        roof_w = profile(c["roof"], x)
        glass_w = profile(c["glass"], x)
        if ay <= roof_w:
            return d if (d and name == "hatch") else c["light"]
        if ay <= glass_w:
            # one bright pixel row along the glass to read as reflection
            return GLASS_HI if abs(ay - (glass_w - 2)) < 0.5 else GLASS
        return d if d else c["paint"]

    # wheels: test the pixel in each wheel's own rotated frame
    for axle, track, deg in ((c["front_axle"], c["front_track"], steer_deg),
                             (c["rear_axle"], c["rear_track"], 0.0)):
        a = math.radians(deg)
        for side in (-1, 1):
            dx, dy = x - axle, y - side * track
            u = dx * math.cos(a) + dy * math.sin(a)       # along the tyre
            v = -dx * math.sin(a) + dy * math.cos(a)      # across the tyre
            if abs(u) <= WHEEL_LEN / 2 and abs(v) <= WHEEL_WID / 2:
                return TREAD if abs(v) < 1.0 else TYRE
    return None


def draw_car_frame(name, steer_deg):
    c = CARS[name]
    img = Image.new("RGBA", (FRAME, FRAME), (0, 0, 0, 0))
    px = img.load()
    for py in range(FRAME):
        for px_ in range(FRAME):
            x, y = px_ + 0.5 - FRAME / 2, py + 0.5 - FRAME / 2
            col = car_pixel(name, c, x, y, steer_deg)
            if col is None:
                # soft drop shadow: the body shape shifted 2px down-right
                if abs(y - 2) <= profile(c["body"], x - 2):
                    px[px_, py] = (0, 0, 0, 70)
            else:
                px[px_, py] = col + (255,)
    return img


def make_car_strip(name):
    strip = Image.new("RGBA", (FRAME * FRAMES, FRAME), (0, 0, 0, 0))
    for i in range(FRAMES):
        steer = (i - 4) / 4.0                 # -1 .. +1, same number the game uses
        strip.paste(draw_car_frame(name, steer * MAX_WHEEL_DEG), (i * FRAME, 0))
    return strip


# --------------------------------------------------------------------------
# TILES
# --------------------------------------------------------------------------
TILE = 128
COLS, ROWS = 8, 4
ROAD_HALF = 52              # half the asphalt width
KERB = 6                    # kerb strip outside the asphalt on bends

# TILE INDEX (index = row * 8 + column). Index 0 must stay empty: GameMaker
# treats tile 0 as "no tile".
T_EMPTY, T_STRAIGHT_H, T_STRAIGHT_V, T_START_H, T_START_V = 0, 1, 2, 3, 4
T_GRASS, T_GRAVEL, T_BARRIER = 5, 6, 7
T_BEND_SE, T_BEND_SW, T_BEND_NE, T_BEND_NW = 8, 9, 10, 11   # named by openings
# Sweeping bends are 2x2 blocks; value = index of the block's top-left tile.
# The other three tiles are +1, +8 and +9.
T_SWEEP_SE, T_SWEEP_SW, T_SWEEP_NE, T_SWEEP_NW = 16, 18, 20, 22

ASPHALT = (58, 60, 68)
LINE = (226, 226, 220)
KERB_RED = (205, 52, 48)
GRASS = (72, 138, 62)
GRAVEL = (196, 178, 138)


def road(d, s, gx, gy, kerb):
    """Road cross-section. d = distance from the centre line, s = distance
    travelled along it. The same rule draws straights and bends."""
    ad = abs(d)
    if ad <= ROAD_HALF:
        if ROAD_HALF - 7 <= ad <= ROAD_HALF - 4:
            return LINE                                   # solid edge line
        if ad <= 1.5 and (s % 32) < 16:
            return shade(LINE, -30)                       # dashed centre line
        n = noise(gx, gy, 1)
        return shade(ASPHALT, (n - 0.5) * 10 if n > 0.2 else -14)
    if kerb and ad <= ROAD_HALF + KERB:
        return KERB_RED if int(s // 12) % 2 == 0 else LINE
    return None


def straight(x, y, gx, gy, vertical, start):
    d, s = (x - 64, y) if vertical else (y - 64, x)
    col = road(d, s, gx, gy, kerb=False)
    if start and col is not None and abs(d) < ROAD_HALF - 7 and abs(s - 64) < 8:
        return (236, 236, 236) if (int(s // 8) + int((d + 64) // 8)) % 2 else (22, 22, 26)
    return col


def bend(x, y, gx, gy, cx, cy, radius):
    """Quarter circle about (cx, cy). x, y are local to the tile or 2x2 block."""
    dx, dy = x - cx, y - cy
    r = math.hypot(dx, dy)
    s = radius * math.atan2(abs(dy), abs(dx))
    return road(r - radius, s, gx, gy, kerb=True)


def grass(gx, gy):
    n = noise(gx, gy, 2)
    if n > 0.94:
        return shade(GRASS, 26)
    if n < 0.10:
        return shade(GRASS, -22)
    return shade(GRASS, (noise(gx // 4, gy // 4, 3) - 0.5) * 12)


def gravel(gx, gy):
    n = noise(gx, gy, 4)
    if n > 0.80:
        return shade(GRAVEL, 24)
    if n < 0.25:
        return shade(GRAVEL, -38)
    return shade(GRAVEL, (noise(gx // 2, gy // 2, 5) - 0.5) * 16)


def barrier(x, y, gx, gy):
    edge = min(x, y, TILE - 1 - x, TILE - 1 - y)
    if edge < 4:
        return (40, 40, 46)
    if edge < 20:
        return KERB_RED if int((x + y) // 16) % 2 == 0 else LINE
    if edge < 23:
        return (40, 40, 46)
    return shade((150, 152, 158), (noise(gx, gy, 6) - 0.5) * 18)


CORNER = {"SE": (1, 1), "SW": (0, 1), "NE": (1, 0), "NW": (0, 0)}  # arc centre


def tile_pixel(index, x, y, gx, gy):
    """x, y = pixel centre inside the tile (0..128). gx, gy = sheet pixel."""
    if index in (T_STRAIGHT_H, T_START_H):
        return straight(x, y, gx, gy, False, index == T_START_H)
    if index in (T_STRAIGHT_V, T_START_V):
        return straight(x, y, gx, gy, True, index == T_START_V)
    if index == T_GRASS:
        return grass(gx, gy)
    if index == T_GRAVEL:
        return gravel(gx, gy)
    if index == T_BARRIER:
        return barrier(x, y, gx, gy)
    for name, first in (("SE", T_BEND_SE), ("SW", T_BEND_SW),
                        ("NE", T_BEND_NE), ("NW", T_BEND_NW)):
        if index == first:
            cx, cy = CORNER[name]
            return bend(x, y, gx, gy, cx * TILE, cy * TILE, TILE / 2)
    for name, first in (("SE", T_SWEEP_SE), ("SW", T_SWEEP_SW),
                        ("NE", T_SWEEP_NE), ("NW", T_SWEEP_NW)):
        for k, (ox, oy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
            if index == first + ox + oy * COLS:
                cx, cy = CORNER[name]
                return bend(x + ox * TILE, y + oy * TILE, gx, gy,
                            cx * 2 * TILE, cy * 2 * TILE, 1.5 * TILE)
    return None


def make_tiles():
    img = Image.new("RGBA", (COLS * TILE, ROWS * TILE), (0, 0, 0, 0))
    px = img.load()
    for gy in range(ROWS * TILE):
        for gx in range(COLS * TILE):
            index = (gy // TILE) * COLS + gx // TILE
            col = tile_pixel(index, gx % TILE + 0.5, gy % TILE + 0.5, gx, gy)
            if col is not None:
                px[gx, gy] = col + (255,)
    return img


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name in CARS:
        make_car_strip(name).save(os.path.join(OUT, f"car_{name}.png"))
    make_tiles().save(os.path.join(OUT, "tiles.png"))
    print("wrote", sorted(os.listdir(OUT)))
