#!/usr/bin/env python3
"""
Wires the generated sheets into the GameMaker project (run with the IDE closed):

    python3 wire_project.py <path to folder containing PixelDrift.yyp>

Creates/overwrites sprites, the tileset, two object shells (no code) and
rebuilds Room1's tile layers from the ASCII maps below. Safe to re-run: asset
ids are derived from names, so nothing is duplicated.

To change the track without the room editor, edit TRACK_MAP / GRAVEL_MAP and
run this again. (Painting in the room editor works too; a re-run overwrites it.)
"""
import json
import os
import re
import sys
import uuid

from PIL import Image

import make_art as art

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, "sheets")
NS = uuid.UUID("5b1d0c0a-7a3e-4c1e-9d55-706978656c64")
TILE = art.TILE

# --------------------------------------------------------------------------
# TRACK, 20 x 12 tiles. One character per 128px tile.
#   -  |   straights            S  start/finish (road running left-right)
#   r 7 L J tight bends, drawn like the corner they make: r=┌ 7=┐ L=└ J=┘
#   A B C D sweeping bends, always written as a 2x2 block: A=┌ B=┐ C=└ D=┘
#   #  barrier                  .  nothing (grass shows through)
# --------------------------------------------------------------------------
TRACK_MAP = """
####################
#AA------S-------BB#
#AA..............BB#
#|................|#
#|................|#
#|..........##....|#
#|...AA-----7#....|#
#|...AA.....|.....|#
#|...|......|.....|#
#|...|......|.....|#
#L---J#....#L-----J#
####################
"""

# Gravel sits on its own layer underneath the track.  o = gravel
GRAVEL_MAP = """
....................
.o................o.
....................
....................
....................
....oo..............
....oo..............
....o........o......
.............o......
.............o......
....................
....................
"""

SPAWN_COL, SPAWN_ROW = 8, 1          # car starts one tile before the line

TIGHT = {"r": art.T_BEND_SE, "7": art.T_BEND_SW, "L": art.T_BEND_NE, "J": art.T_BEND_NW}
SWEEP = {"A": art.T_SWEEP_SE, "B": art.T_SWEEP_SW, "C": art.T_SWEEP_NE, "D": art.T_SWEEP_NW}


def parse_maps():
    rows = [r for r in TRACK_MAP.strip().splitlines()]
    grav = [r for r in GRAVEL_MAP.strip().splitlines()]
    h, w = len(rows), len(rows[0])
    assert all(len(r) == w for r in rows), "TRACK_MAP rows differ in length"
    assert len(grav) == h and all(len(r) == w for r in grav), "GRAVEL_MAP size differs"
    track = [[0] * w for _ in range(h)]
    barrier = [[0] * w for _ in range(h)]
    gravel = [[art.T_GRAVEL if grav[y][x] == "o" else 0 for x in range(w)] for y in range(h)]
    grass = [[art.T_GRASS] * w for _ in range(h)]
    done = set()
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if ch == "#":
                barrier[y][x] = art.T_BARRIER
            elif ch == "-":
                track[y][x] = art.T_STRAIGHT_H
            elif ch == "|":
                track[y][x] = art.T_STRAIGHT_V
            elif ch == "S":
                track[y][x] = art.T_START_H
            elif ch in TIGHT:
                track[y][x] = TIGHT[ch]
            elif ch in SWEEP and (x, y) not in done:
                for oy in (0, 1):
                    for ox in (0, 1):
                        assert rows[y + oy][x + ox] == ch, f"'{ch}' at {x},{y} is not a 2x2 block"
                        track[y + oy][x + ox] = SWEEP[ch] + ox + oy * art.COLS
                        done.add((x + ox, y + oy))
            elif ch not in ".ABCD":
                raise ValueError(f"unknown map character '{ch}'")
    return w, h, dict(grass=grass, gravel=gravel, track=track, barrier=barrier)


# which sides of a tile the road leaves through: N E S W
def openings():
    o = {art.T_STRAIGHT_H: "EW", art.T_START_H: "EW", art.T_STRAIGHT_V: "NS", art.T_START_V: "NS",
         art.T_BEND_SE: "SE", art.T_BEND_SW: "SW", art.T_BEND_NE: "NE", art.T_BEND_NW: "NW"}
    c = art.COLS
    for first, parts in ((art.T_SWEEP_SE, {1: "E", c: "S"}), (art.T_SWEEP_SW, {0: "W", c + 1: "S"}),
                         (art.T_SWEEP_NE, {0: "N", c + 1: "E"}), (art.T_SWEEP_NW, {1: "N", c: "W"})):
        for off in (0, 1, c, c + 1):
            o[first + off] = parts.get(off, "")
    return o


def check_track(track):
    """Every road end must meet a road end on the neighbouring tile."""
    o = openings()
    step = {"N": (0, -1, "S"), "S": (0, 1, "N"), "E": (1, 0, "W"), "W": (-1, 0, "E")}
    problems = []
    for y, row in enumerate(track):
        for x, t in enumerate(row):
            for side in o.get(t, ""):
                dx, dy, back = step[side]
                nx, ny = x + dx, y + dy
                ok = 0 <= ny < len(track) and 0 <= nx < len(row) and back in o.get(track[ny][nx], "")
                if not ok:
                    problems.append(f"tile {x},{y} opens {side} into nothing")
    return problems


# --------------------------------------------------------------------------
# GameMaker's .yy flavour of JSON (trailing commas)
# --------------------------------------------------------------------------
def gm_load(path):
    text = open(path, encoding="utf-8").read()
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", text))


def gm_dump(v, ind=0):
    sp = "  " * ind
    if isinstance(v, dict):
        if not v:
            return "{}"
        return "{\n" + "".join(f"{sp}  {json.dumps(k)}:{gm_dump(x, ind + 1)},\n" for k, x in v.items()) + sp + "}"
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(isinstance(x, int) and not isinstance(x, bool) for x in v):
            return "[" + ",".join(str(x) for x in v) + ",]"
        return "[\n" + "".join(f"{sp}  {gm_dump(x, ind + 1)},\n" for x in v) + sp + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, float):
        return repr(v)
    return json.dumps(v)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def gid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def ref(kind, name):
    return {"name": name, "path": f"{kind}/{name}/{name}.yy"}


# --------------------------------------------------------------------------
# resources
# --------------------------------------------------------------------------
def write_sprite(root, proj, name, frames, origin_centre):
    w, h = frames[0].size
    folder = os.path.join(root, "sprites", name)
    layer = gid(name, "layer")
    ids = [gid(name, "frame", str(i)) for i in range(len(frames))]
    box = None
    for im in frames:
        b = im.getbbox() or (0, 0, w, h)
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    for fid, im in zip(ids, frames):
        os.makedirs(os.path.join(folder, "layers", fid), exist_ok=True)
        im.save(os.path.join(folder, f"{fid}.png"))
        im.save(os.path.join(folder, "layers", fid, f"{layer}.png"))
    path = f"sprites/{name}/{name}.yy"
    keys = [{
        "$Keyframe<SpriteFrameKeyframe>": "",
        "Channels": {"0": {"$SpriteFrameKeyframe": "", "Id": {"name": fid, "path": path},
                           "resourceType": "SpriteFrameKeyframe", "resourceVersion": "2.0"}},
        "Disabled": False, "id": gid(name, "key", str(i)), "IsCreationKey": False,
        "Key": float(i), "Length": 1.0,
        "resourceType": "Keyframe<SpriteFrameKeyframe>", "resourceVersion": "2.0", "Stretch": False,
    } for i, fid in enumerate(ids)]
    yy = {
        "$GMSprite": "v2", "%Name": name,
        "bboxMode": 0, "bbox_bottom": box[3] - 1, "bbox_left": box[0], "bbox_right": box[2] - 1, "bbox_top": box[1],
        "collisionKind": 1, "collisionTolerance": 0, "DynamicTexturePage": False,
        "edgeFiltering": False, "For3D": False,
        "frames": [{"$GMSpriteFrame": "v1", "%Name": fid, "name": fid,
                    "resourceType": "GMSpriteFrame", "resourceVersion": "2.0"} for fid in ids],
        "gridX": 0, "gridY": 0, "height": h, "HTile": False,
        "layers": [{"$GMImageLayer": "", "%Name": layer, "blendMode": 0, "displayName": "default",
                    "isLocked": False, "name": layer, "opacity": 100.0,
                    "resourceType": "GMImageLayer", "resourceVersion": "2.0", "visible": True}],
        "name": name, "nineSlice": None,
        "origin": 4 if origin_centre else 0,
        "parent": {"name": proj, "path": f"{proj}.yyp"},
        "preMultiplyAlpha": False, "resourceType": "GMSprite", "resourceVersion": "2.0",
        "sequence": {
            "$GMSequence": "v1", "%Name": name, "autoRecord": True,
            "backdropHeight": 768, "backdropImageOpacity": 0.5, "backdropImagePath": "",
            "backdropWidth": 1366, "backdropXOffset": 0.0, "backdropYOffset": 0.0,
            "events": {"$KeyframeStore<MessageEventKeyframe>": "", "Keyframes": [],
                       "resourceType": "KeyframeStore<MessageEventKeyframe>", "resourceVersion": "2.0"},
            "eventStubScript": None, "eventToFunction": {},
            "length": float(len(frames)), "lockOrigin": False,
            "moments": {"$KeyframeStore<MomentsEventKeyframe>": "", "Keyframes": [],
                        "resourceType": "KeyframeStore<MomentsEventKeyframe>", "resourceVersion": "2.0"},
            "name": name, "playback": 1,
            "playbackSpeed": 0.0,            # 0 fps: frames are a lookup table, never an animation
            "playbackSpeedType": 0,
            "resourceType": "GMSequence", "resourceVersion": "2.0",
            "seqHeight": float(h), "seqWidth": float(w),
            "showBackdrop": True, "showBackdropImage": False, "timeUnits": 1,
            "tracks": [{
                "$GMSpriteFramesTrack": "", "builtinName": 0, "events": [],
                "inheritsTrackColour": True, "interpolation": 1, "isCreationTrack": False,
                "keyframes": {"$KeyframeStore<SpriteFrameKeyframe>": "", "Keyframes": keys,
                              "resourceType": "KeyframeStore<SpriteFrameKeyframe>", "resourceVersion": "2.0"},
                "modifiers": [], "name": "frames",
                "resourceType": "GMSpriteFramesTrack", "resourceVersion": "2.0",
                "spriteId": None, "trackColour": 0, "tracks": [], "traits": 0,
            }],
            "visibleRange": None, "volume": 1.0,
            "xorigin": w // 2 if origin_centre else 0, "yorigin": h // 2 if origin_centre else 0,
        },
        "swatchColours": None, "swfPrecision": 0.5,
        "textureGroupId": {"name": "Default", "path": "texturegroups/Default"},
        "type": 0, "VTile": False, "width": w,
    }
    write_text(os.path.join(root, path), gm_dump(yy))
    return ref("sprites", name)


def write_tileset(root, proj, name, sprite_name, sheet):
    count = art.COLS * art.ROWS
    out_cols = 1
    while out_cols * out_cols < count:
        out_cols += 1
    # the IDE's working copy: every tile padded with a 2px copy of its own edge
    b = 2
    cell = TILE + 2 * b
    out = Image.new("RGBA", (out_cols * cell, -(-count // out_cols) * cell), (0, 0, 0, 0))
    for i in range(count):
        t = sheet.crop(((i % art.COLS) * TILE, (i // art.COLS) * TILE,
                        (i % art.COLS + 1) * TILE, (i // art.COLS + 1) * TILE))
        ox, oy = (i % out_cols) * cell, (i // out_cols) * cell
        padded = Image.new("RGBA", (cell, cell))
        padded.paste(t, (b, b))
        for k in range(b):                       # left and right edges
            padded.paste(t.crop((0, 0, 1, TILE)), (k, b))
            padded.paste(t.crop((TILE - 1, 0, TILE, TILE)), (cell - 1 - k, b))
        full = padded.copy()
        for k in range(b):                       # then top and bottom, corners included
            full.paste(padded.crop((0, b, cell, b + 1)), (0, k))
            full.paste(padded.crop((0, b + TILE - 1, cell, b + TILE)), (0, cell - 1 - k))
        out.paste(full, (ox, oy))
    folder = os.path.join(root, "tilesets", name)
    os.makedirs(folder, exist_ok=True)
    out.save(os.path.join(folder, "output_tileset.png"))
    yy = {
        "$GMTileSet": "v1", "%Name": name, "autoTileSets": [],
        "macroPageTiles": {"SerialiseHeight": 0, "SerialiseWidth": 0, "TileSerialiseData": []},
        "name": name, "out_columns": out_cols, "out_tilehborder": b, "out_tilevborder": b,
        "parent": {"name": proj, "path": f"{proj}.yyp"},
        "resourceType": "GMTileSet", "resourceVersion": "2.0",
        "spriteId": ref("sprites", sprite_name), "spriteNoExport": False,
        "textureGroupId": {"name": "Default", "path": "texturegroups/Default"},
        "tileAnimationFrames": [], "tileAnimationSpeed": 15.0,
        "tileHeight": TILE, "tilehsep": 0, "tilevsep": 0, "tileWidth": TILE,
        "tilexoff": 0, "tileyoff": 0, "tile_count": count,
    }
    write_text(os.path.join(folder, f"{name}.yy"), gm_dump(yy))
    return ref("tilesets", name)


def write_object(root, proj, name, sprite, visible, physics):
    folder = os.path.join(root, "objects", name)
    keep = []
    old = os.path.join(folder, f"{name}.yy")
    if os.path.exists(old):                      # never throw away events typed in the IDE
        keep = gm_load(old).get("eventList", [])
    yy = {
        "$GMObject": "", "%Name": name, "eventList": keep, "managed": True, "name": name,
        "overriddenProperties": [], "parent": {"name": proj, "path": f"{proj}.yyp"},
        "parentObjectId": None, "persistent": False,
        "physicsAngularDamping": physics["angular_damping"],
        "physicsDensity": physics["density"],
        "physicsFriction": physics["friction"],
        "physicsGroup": 0, "physicsKinematic": False,
        "physicsLinearDamping": physics["linear_damping"],
        "physicsObject": True,
        "physicsRestitution": physics["restitution"],
        "physicsSensor": False,
        "physicsShape": 1,                       # 1 = box
        "physicsShapePoints": [{"x": float(x), "y": float(y)} for x, y in physics["box"]],
        "physicsStartAwake": True, "properties": [],
        "resourceType": "GMObject", "resourceVersion": "2.0", "solid": False,
        "spriteId": sprite, "spriteMaskId": None, "visible": visible,
    }
    write_text(old, gm_dump(yy))
    return ref("objects", name)


def rle(values):
    """GameMaker tile data: a negative count repeats the next value, a positive
    count is followed by that many literal values."""
    out, i = [], 0
    while i < len(values):
        j = i
        while j < len(values) and values[j] == values[i]:
            j += 1
        if j - i >= 2:
            out += [-(j - i), values[i]]
            i = j
        else:
            lit = []
            while i < len(values) and not (i + 1 < len(values) and values[i + 1] == values[i]):
                lit.append(values[i])
                i += 1
            out += [len(lit)] + lit
    return out


def tile_layer(name, depth, grid, tileset, w, h):
    flat = [t for row in grid for t in row]
    return {
        "$GMRTileLayer": "", "%Name": name, "depth": depth, "effectEnabled": True, "effectType": None,
        "gridX": 32, "gridY": 32, "hierarchyFrozen": False, "inheritLayerDepth": False,
        "inheritLayerSettings": False, "inheritSubLayers": True, "inheritVisibility": True,
        "layers": [], "name": name, "properties": [],
        "resourceType": "GMRTileLayer", "resourceVersion": "2.0",
        "tiles": {"SerialiseHeight": h, "SerialiseWidth": w, "TileCompressedData": rle(flat), "TileDataFormat": 1},
        "tilesetId": tileset, "userdefinedDepth": False, "visible": True, "x": 0, "y": 0,
    }


def update_room(root, room_name, tileset, car, w, h, grids):
    path = os.path.join(root, "rooms", room_name, f"{room_name}.yy")
    room = gm_load(path)
    rel = f"rooms/{room_name}/{room_name}.yy"
    old = {l["name"]: l for l in room["layers"]}
    inst_layer, bg = old["Instances"], old["Background"]

    if not any(i["objectId"]["name"] == car["name"] for i in inst_layer["instances"]):
        iname = "inst_" + gid(room_name, "car")[:8].upper()
        inst_layer["instances"].append({
            "$GMRInstance": "v4", "%Name": iname, "colour": 4294967295, "frozen": False,
            "hasCreationCode": False, "ignore": False,
            "imageIndex": 4,                     # frame 4 = wheels centred
            "imageSpeed": 1.0, "inheritCode": False, "inheritedItemId": None,
            "inheritItemSettings": False, "isDnd": False, "name": iname, "objectId": car,
            "properties": [], "resourceType": "GMRInstance", "resourceVersion": "2.0",
            "rotation": 0.0, "scaleX": 1.0, "scaleY": 1.0,
            "x": float(SPAWN_COL * TILE + TILE // 2), "y": float(SPAWN_ROW * TILE + TILE // 2),
        })
        room["instanceCreationOrder"].append({"name": iname, "path": rel})

    inst_layer["depth"], bg["depth"] = 0, 500
    room["layers"] = [
        inst_layer,
        tile_layer("Tiles_Barrier", 100, grids["barrier"], tileset, w, h),
        tile_layer("Tiles_Track", 200, grids["track"], tileset, w, h),
        tile_layer("Tiles_Gravel", 300, grids["gravel"], tileset, w, h),
        tile_layer("Tiles_Grass", 400, grids["grass"], tileset, w, h),
        bg,
    ]
    room["roomSettings"]["Width"], room["roomSettings"]["Height"] = w * TILE, h * TILE
    room["physicsSettings"].update(PhysicsWorld=True, PhysicsWorldGravityX=0.0, PhysicsWorldGravityY=0.0)
    room["viewSettings"]["enableViews"] = True
    # view 0: 1280x720 window that keeps the car centred (borders = half the view)
    room["views"][0].update(visible=True, wview=1280, hview=720, wport=1280, hport=720,
                            hborder=640, vborder=360, hspeed=-1, vspeed=-1, objectId=car)
    write_text(path, gm_dump(room))


def update_project(root, proj, refs):
    path = os.path.join(root, f"{proj}.yyp")
    yyp = gm_load(path)
    have = {r["id"]["path"] for r in yyp["resources"]}
    for r in refs:
        if r["path"] not in have:
            yyp["resources"].append({"id": r})
    yyp["resources"].sort(key=lambda r: r["id"]["name"].lower())
    write_text(path, gm_dump(yyp))


def backup(root, rel):
    dst = os.path.join(HERE, "backup", rel.replace("/", "__"))
    if not os.path.exists(dst):
        write_text(dst, open(os.path.join(root, rel), encoding="utf-8").read())


def main(root):
    proj = [f for f in os.listdir(root) if f.endswith(".yyp")][0][:-4]
    w, h, grids = parse_maps()
    problems = check_track(grids["track"])
    if problems:
        sys.exit("track does not connect:\n  " + "\n  ".join(problems))

    backup(root, f"{proj}.yyp")
    backup(root, "rooms/Room1/Room1.yy")

    refs = []
    for car in art.CARS:
        strip = Image.open(os.path.join(SHEETS, f"car_{car}.png")).convert("RGBA")
        frames = [strip.crop((i * art.FRAME, 0, (i + 1) * art.FRAME, art.FRAME)) for i in range(art.FRAMES)]
        refs.append(write_sprite(root, proj, f"spr_car_{car}", frames, origin_centre=True))
    sheet = Image.open(os.path.join(SHEETS, "tiles.png")).convert("RGBA")
    refs.append(write_sprite(root, proj, "spr_tiles", [sheet], origin_centre=False))
    bx, by = (art.T_BARRIER % art.COLS) * TILE, (art.T_BARRIER // art.COLS) * TILE
    spr_barrier = write_sprite(root, proj, "spr_barrier", [sheet.crop((bx, by, bx + TILE, by + TILE))], False)
    refs.append(spr_barrier)
    tileset = write_tileset(root, proj, "ts_track", "spr_tiles", sheet)
    refs.append(tileset)

    # Object shells: physics switched on, no events. Values are starting points
    # that the car code overrides.
    car = write_object(root, proj, "obj_car", ref("sprites", "spr_car_hatch"), True, dict(
        density=0.5, restitution=0.1, friction=0.2, linear_damping=0.5, angular_damping=2.0,
        box=[(8, 20), (56, 20), (56, 44), (8, 44)]))            # 48x24 body inside the 64x64 frame
    refs.append(car)
    refs.append(write_object(root, proj, "obj_barrier", spr_barrier, False, dict(
        density=0.0, restitution=0.4, friction=0.2, linear_damping=0.0, angular_damping=0.0,   # density 0 = static
        box=[(0, 0), (TILE, 0), (TILE, TILE), (0, TILE)])))

    update_room(root, "Room1", tileset, car, w, h, grids)
    update_project(root, proj, refs)
    print(f"wired {len(refs)} resources into {proj}; room is {w}x{h} tiles ({w * TILE}x{h * TILE}px)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE))
