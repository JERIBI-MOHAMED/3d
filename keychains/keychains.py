"""Keychain generator: names (Latin + Arabic), Tunisian flag, khomsa, club jerseys, wedding heart.

Every design is a stack of flat layers, one colour per height band, so it prints in
colour on ANY single-nozzle printer: add a filament change (M600 / "pause at height")
at each layer start listed in parts.json. Multi-colour printers can load the
per-colour STLs as one multi-part object instead.

    pip install shapely manifold3d trimesh uharfbuzz fonttools numpy
    python keychains.py            # writes ../stl/keychain_*.stl and parts.json

Sizes are in mm. Change NAMES / JERSEYS / HEART_INITIALS below for custom orders.
"""
import json
import math
import os
import sys

import numpy as np
import manifold3d as m3d
import trimesh
import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Cairo-ExtraBold.ttf")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "stl")

BASE_H = 3.0      # base plate thickness
LAYER_H = 0.8     # each raised colour layer
TEXT_H = 1.4      # raised name text
HOLE_R = 2.3      # key-ring hole (fits 25 mm split rings)
TAB_R = 5.0

# Colours used for the renders (and suggested filament colours)
C = {
    "white": "#F4F2EC", "black": "#1E1E22", "red": "#C8102E", "yellow": "#F6C312",
    "blue": "#1C4FA1", "turquoise": "#1FA3A8", "gold": "#D4A62A", "pink": "#D9487A",
    "navy": "#13294B", "green": "#1E8C4E", "orange": "#F07D1A",
}

NAMES = [  # (id, text, base colour, text colour)
    ("name_yasmine", "Yasmine", "pink", "white"),
    ("name_yasmine_ar", "ياسمين", "turquoise", "white"),
    ("name_ahmed", "Ahmed", "navy", "yellow"),
    ("name_ahmed_ar", "أحمد", "black", "gold"),
]
JERSEYS = [  # (id, number, shirt, stripes/number pad, number colour)
    ("jersey_red_yellow", "10", "red", "yellow", "red"),
    ("jersey_red_white", "7", "red", "white", "red"),
    ("jersey_white_red", "9", "white", "red", "white"),
]
HEART_INITIALS = ("Y", "A")


# ---------------------------------------------------------------- text -> polygons
class _FlatPen(BasePen):
    def __init__(self, glyphset, steps=10):
        super().__init__(glyphset)
        self.contours, self.cur, self.steps = [], [], steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        for t in np.linspace(0, 1, self.steps + 1)[1:]:
            u = 1 - t
            self.cur.append(tuple(u**3 * np.array(p0) + 3 * u * u * t * np.array(p1)
                                  + 3 * u * t * t * np.array(p2) + t**3 * np.array(p3)))

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        for t in np.linspace(0, 1, self.steps + 1)[1:]:
            u = 1 - t
            self.cur.append(tuple(u * u * np.array(p0) + 2 * u * t * np.array(p1) + t * t * np.array(p2)))

    def _closePath(self):
        if len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


_font = TTFont(FONT)
_glyphset = _font.getGlyphSet()
_order = _font.getGlyphOrder()
_hbfont = hb.Font(hb.Face(hb.Blob.from_file_path(FONT)))
_upem = _font["head"].unitsPerEm


def text_shape(text, height):
    """Shaped (Arabic joins correctly) text as a shapely geometry, cap height ~= height, centred."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(_hbfont, buf, {"kern": True, "liga": True})
    polys, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = _FlatPen(_glyphset)
        _glyphset[_order[info.codepoint]].draw(pen)
        g = Polygon()
        for c in pen.contours:  # even-odd fill handles counters (holes in o, a, ...)
            g = g.symmetric_difference(Polygon(c).buffer(0))
        if not g.is_empty:
            polys.append(affinity.translate(g, x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    shape = unary_union(polys)
    cap = _font["OS/2"].sCapHeight or 0.7 * _upem
    shape = affinity.scale(shape, height / cap, height / cap, origin=(0, 0))
    minx, miny, maxx, maxy = shape.bounds
    return affinity.translate(shape, -(minx + maxx) / 2, -(miny + maxy) / 2)


# ---------------------------------------------------------------- helpers
def fill_holes(g):
    geoms = g.geoms if isinstance(g, MultiPolygon) else [g]
    return unary_union([Polygon(p.exterior) for p in geoms])


def closing(g, r):
    return g.buffer(r, join_style="round").buffer(-r, join_style="round")


def star(cx, cy, r_out, r_in, rot_deg=90, n=5):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot_deg) + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return Polygon(pts)


def capsule(p0, p1, w):
    from shapely.geometry import LineString
    return LineString([p0, p1]).buffer(w / 2, cap_style="round")


def with_tab(outline, tab_xy):
    tx, ty = tab_xy
    tab = Point(tx, ty).buffer(TAB_R, resolution=48)
    joined = closing(unary_union([outline, tab]), 2.0)
    return joined, Point(tx, ty).buffer(HOLE_R, resolution=48)


class Design:
    def __init__(self, did, label):
        self.id, self.label, self.layers, self.hole = did, label, [], None

    def add(self, colour, geom, z0, z1):
        self.layers.append({"colour": colour, "geom": geom, "z0": z0, "z1": z1})
        return self

    def export(self, outdir):
        files = []
        for i, L in enumerate(self.layers):
            g = L["geom"].difference(self.hole) if self.hole is not None else L["geom"]
            mesh = extrude(g, L["z0"], L["z1"])
            fname = f"keychain_{self.id}_{i}_{L['colour']}.stl"
            mesh.export(os.path.join(outdir, fname))
            files.append({"file": fname, "colour": L["colour"], "hex": C[L["colour"]],
                          "z0": L["z0"], "z1": L["z1"]})
        minx, miny, maxx, maxy = self.layers[0]["geom"].bounds
        hx, hy = (self.hole.centroid.x, self.hole.centroid.y) if self.hole is not None else (None, None)
        changes = sorted({L["z0"] for L in self.layers if L["z0"] > 0})
        return {"id": self.id, "label": self.label, "parts": files,
                "size_mm": [round(maxx - minx, 1), round(maxy - miny, 1), max(L["z1"] for L in self.layers)],
                "bounds": [minx, miny, maxx, maxy], "hole": [hx, hy],
                "colour_change_at_mm": changes}


def extrude(g, z0, z1):
    geoms = g.geoms if isinstance(g, MultiPolygon) else [g]
    contours = []
    for p in geoms:
        if p.is_empty or p.area < 0.05:
            continue
        p = p.simplify(0.01)
        contours.append(np.array(p.exterior.coords[:-1]))
        contours += [np.array(r.coords[:-1]) for r in p.interiors]
    cs = m3d.CrossSection(contours, m3d.FillRule.EvenOdd)
    solid = cs.extrude(z1 - z0).translate((0, 0, z0))
    mesh = solid.to_mesh()
    return trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=True)


# ---------------------------------------------------------------- designs
def name_keychain(did, text, base_c, text_c):
    arabic = any("؀" <= ch <= "ۿ" for ch in text)
    t = text_shape(text, 10.5 if arabic else 11.0)
    outline = fill_holes(closing(t.buffer(3.2, join_style="round"), 3.0))
    minx, miny, maxx, maxy = outline.bounds
    # Ring at the start of the word: left for Latin, right for Arabic (read right to left)
    tab = (maxx + 2.2, (miny + maxy) / 2) if arabic else (minx - 2.2, (miny + maxy) / 2)
    outline, hole = with_tab(outline, tab)
    d = Design(did, text)
    d.add(base_c, outline, 0, BASE_H).add(text_c, t, BASE_H, BASE_H + TEXT_H)
    d.hole = hole
    return d


def flag_keychain():
    w, h = 48.0, 32.0
    plate = box(-w / 2, -h / 2, w / 2, h / 2).buffer(-3).buffer(3)
    R = h / 4  # white disc radius (diameter = half the flag height)
    disc = Point(0, 0).buffer(R, resolution=96)
    crescent = Point(0, 0).buffer(0.75 * R, resolution=96).difference(
        Point(0.1875 * R, 0).buffer(0.6 * R, resolution=96))
    st = star(0.22 * R, 0, 0.36 * R, 0.145 * R, rot_deg=180)
    outline, hole = with_tab(plate, (-w / 2 - 2.0, h / 2 - 7))
    d = Design("flag_tunisia", "Drapeau Tunisie")
    d.add("red", outline, 0, BASE_H)
    d.add("white", disc, BASE_H, BASE_H + LAYER_H)
    d.add("red", unary_union([crescent, st]), BASE_H + LAYER_H, BASE_H + 2 * LAYER_H)
    d.hole = hole
    return d


def khomsa_keychain():
    parts = [
        affinity.scale(Point(0, -6).buffer(1, resolution=64), 13.5, 14.5),   # palm
        capsule((0, -2), (0, 20), 8.2),        # middle finger
        capsule((-8.4, -3), (-8.4, 16.5), 7.8),  # index
        capsule((8.4, -3), (8.4, 16.5), 7.8),    # ring finger
    ]
    for s in (-1, 1):  # symmetric thumbs curling outwards, typical of the khomsa
        parts.append(capsule((s * 10.5, -12), (s * 17.5, -2.5), 7.0))
        parts.append(capsule((s * 17.5, -2.5), (s * 19.5, 3.5), 6.0))
    hand = closing(unary_union(parts), 1.6)
    hand = hand.buffer(-0.6).buffer(0.6)
    outline, hole = with_tab(hand, (0, 25.5))
    rim = hand.buffer(-1.6).difference(hand.buffer(-2.8))
    # Eye (nazar) in the palm
    eye = Point(0, -5.5).buffer(1, resolution=96)
    eye = affinity.scale(eye, 8.5, 5.0).intersection(
        Point(0, -5.5 - 6.0).buffer(10.5).intersection(Point(0, -5.5 + 6.0).buffer(10.5)))
    iris = Point(0, -5.5).buffer(3.3, resolution=64)
    pupil = Point(0, -5.5).buffer(1.4, resolution=48)
    drops = unary_union([Point(x, y).buffer(1.2, resolution=32)
                         for x, y in [(-7.5, 7), (0, 10), (7.5, 7), (0, 3.2)]])
    d = Design("khomsa", "Khomsa")
    d.add("blue", outline, 0, BASE_H)
    d.add("white", unary_union([rim, eye, drops]), BASE_H, BASE_H + LAYER_H)
    d.add("turquoise", iris.difference(pupil), BASE_H + LAYER_H, BASE_H + 2 * LAYER_H)
    d.add("black", pupil, BASE_H + LAYER_H, BASE_H + 2 * LAYER_H)
    d.hole = hole
    return d


def jersey_keychain(did, number, shirt_c, pad_c, num_c):
    half = [(0, 37.5), (6.5, 40), (13, 38.5), (22, 32), (18, 23.5), (13.5, 26.5), (13.5, 0)]
    pts = half + [(-x, y) for x, y in reversed(half)][:-1]
    shirt = Polygon(pts).buffer(-1.2, join_style="round").buffer(1.2, join_style="round")
    collar_cut = Point(0, 41.5).buffer(5.2, resolution=64)
    shirt = shirt.difference(collar_cut)
    outline, hole = with_tab(shirt, (0, 41.8))
    inner = shirt.buffer(-1.5)
    stripes = unary_union([box(x - 2.1, -5, x + 2.1, 45) for x in np.arange(-15, 16, 7.5)]).intersection(inner)
    num = text_shape(number, 13.5)
    num = affinity.translate(num, 0, 16)
    pad = num.buffer(1.3, join_style="round")
    collar = Point(0, 41.5).buffer(6.6, resolution=64).difference(collar_cut).intersection(shirt)
    d = Design(did, f"Maillot {number}")
    d.add(shirt_c, outline, 0, BASE_H)
    d.add(pad_c, unary_union([stripes.difference(pad.buffer(0.8)), pad, collar]), BASE_H, BASE_H + LAYER_H)
    d.add(num_c, num, BASE_H + LAYER_H, BASE_H + 2 * LAYER_H)
    d.hole = hole
    return d


def heart_keychain(a, b):
    t = np.linspace(0, 2 * math.pi, 240)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    heart = Polygon(np.c_[x, y] * 1.45).buffer(0)
    outline, hole = with_tab(heart, (0, 17.5))
    txt = text_shape(f"{a}&{b}", 11.5)
    txt = affinity.translate(txt, 0, 1.0)
    d = Design("heart_initials", f"{a} & {b}")
    d.add("red", outline, 0, BASE_H)
    d.add("white", txt, BASE_H, BASE_H + TEXT_H)
    d.hole = hole
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    designs = [name_keychain(*n) for n in NAMES]
    designs += [flag_keychain(), khomsa_keychain()]
    designs += [jersey_keychain(*j) for j in JERSEYS]
    designs.append(heart_keychain(*HEART_INITIALS))
    meta = [d.export(OUT) for d in designs]
    with open(os.path.join(HERE, "parts.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    for m in meta:
        print(f"{m['id']:22s} {m['size_mm']}  colour change at {m['colour_change_at_mm']} mm")


if __name__ == "__main__":
    main()
