"""Two-color sign: white plaque with raised black Arabic calligraphy (like the AL-WARSHA DESIGNS print).

python3 sign/make_sign.py [font] [--line]      font: ruqaa (Aref Ruqaa Bold) or amiri (Amiri Bold, Naskh)
-> stl/sign_mornaguia_<font>.3mf (white plaque filament 1, black text filament 2), STLs and a preview.
--line: the whole phrase on one line; the plaque height follows the text (files end in _line).

Arabic is shaped with HarfBuzz (joined letter forms, ligatures, right-to-left), then the glyph outlines are
turned into shapes. Layout: the title large on top, a rule, the second line below.
"""
import os
import sys
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "keychain"))
import make_keychain as kc  # noqa: E402  (thicken, extrude, write_3mf)

FONTS = {"ruqaa": "ArefRuqaa-Bold.ttf", "amiri": "Amiri-Bold.ttf"}
TITLE = "إبداعات"
SUBTITLE = "مودعي سجن المرناقية"

W, H = 160.0, 85.0        # plaque (mm)
T_PLATE = 5.0             # plaque thickness
T_TEXT = 1.0              # raised text (5 layers at 0.2)
MARGIN = 10.0
TITLE_H = 30.0            # max height of the title line (ink)
SUB_H = 15.0              # max height of the second line (ink)
RULE = 1.2                # thickness of the dividing rule


def shape_text(text, font_path, size=1000.0):
    """HarfBuzz-shaped text -> shapely geometry (font units scaled to `size` per em), baseline at y=0."""
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"liga": True, "calt": True})
    tt = TTFont(font_path)
    gs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    upm = tt["head"].unitsPerEm
    k = size / upm
    x = 0.0
    shapes = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = DecomposingRecordingPen(gs)          # composite glyphs (letter + dots) -> plain outlines
        gs[order[info.codepoint]].draw(pen)
        rings, cur = [], []
        for op, args in pen.value:
            if op == "moveTo":
                cur = [args[0]]
            elif op == "lineTo":
                cur.append(args[0])
            elif op in ("qCurveTo", "curveTo"):
                p0 = np.array(cur[-1], float)
                pts = [np.array(a, float) for a in args]
                if op == "curveTo":
                    c1, c2, p3 = pts
                    for t in np.linspace(0, 1, 9)[1:]:
                        cur.append(tuple((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p3))
                else:
                    # TrueType quadratic spline with implied on-curve points between off-curve ones
                    offs, end = pts[:-1], pts[-1]
                    seq = []
                    for i, c in enumerate(offs):
                        nxt = offs[i + 1] if i + 1 < len(offs) else None
                        on = (c + nxt) / 2 if nxt is not None else end
                        seq.append((c, on))
                    for c, on in seq:
                        for t in np.linspace(0, 1, 7)[1:]:
                            cur.append(tuple((1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t ** 2 * on))
                        p0 = on
            elif op in ("closePath", "endPath"):
                if len(cur) >= 3:
                    rings.append(cur)
                cur = []
        g = Polygon()
        for r in rings:
            p = Polygon(r).buffer(0)
            g = g.symmetric_difference(p)
        if not g.is_empty:
            shapes.append(affinity.translate(g, x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    return affinity.scale(unary_union(shapes), k, k, origin=(0, 0))


def fit(g, w, h):
    x0, y0, x1, y1 = g.bounds
    s = min(w / (x1 - x0), h / (y1 - y0))
    g = affinity.scale(g, s, s, origin=(0, 0))
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, -(y0 + y1) / 2)


def design_line(font_key):
    """The whole phrase on one line, plaque fitted around it with even margins."""
    global H
    font = os.path.join(HERE, "fonts", FONTS[font_key])
    text = fit(shape_text(TITLE + " " + SUBTITLE, font), W - 2 * MARGIN, 60.0)
    H = round((text.bounds[3] - text.bounds[1]) + 2 * MARGIN)
    text = kc.thicken(text, kc.MIN_STROKE / 2)
    plate = box(-W / 2, -H / 2, W / 2, H / 2)
    gaps = kc.thicken(plate.difference(text), 0.2)
    return plate, plate.difference(gaps).buffer(0.01).buffer(-0.01)


def design(font_key):
    font = os.path.join(HERE, "fonts", FONTS[font_key])
    inner_w = W - 2 * MARGIN
    title = fit(shape_text(TITLE, font), inner_w * 0.75, TITLE_H)
    sub = fit(shape_text(SUBTITLE, font), inner_w, SUB_H)
    gap = 5.0
    total = (title.bounds[3] - title.bounds[1]) + gap + RULE + gap + (sub.bounds[3] - sub.bounds[1])
    top = total / 2
    th = title.bounds[3] - title.bounds[1]
    title = affinity.translate(title, 0, top - th / 2)
    rule_y = top - th - gap - RULE / 2
    rule = box(-inner_w / 2, rule_y - RULE / 2, inner_w / 2, rule_y + RULE / 2)
    sh = sub.bounds[3] - sub.bounds[1]
    sub = affinity.translate(sub, 0, rule_y - RULE / 2 - gap - sh / 2)
    text = unary_union([title, rule, sub])
    text = kc.thicken(text, kc.MIN_STROKE / 2)                     # strokes and dots >= 0.42 mm
    plate = box(-W / 2, -H / 2, W / 2, H / 2)
    gaps = kc.thicken(plate.difference(text), 0.2)                 # counters / gaps >= 0.4 mm
    text = plate.difference(gaps).buffer(0.01).buffer(-0.01)
    return plate, text


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    line = "--line" in sys.argv
    keys = [a for a in sys.argv[1:] if not a.startswith("--")] or ["ruqaa", "amiri"]
    suffix = "_line" if line else ""
    fig, axs = plt.subplots(len(keys), 1, figsize=(8, (2.6 if line else 4.6) * len(keys)))
    axs = np.atleast_1d(axs)
    for ax, key in zip(axs, keys):
        plate, text = design_line(key) if line else design(key)
        base = kc.extrude(plate, T_PLATE, 0)
        top = kc.extrude(text, T_TEXT, T_PLATE)
        single = trimesh.boolean.union([base, top], engine="manifold")
        assert base.is_volume and top.is_volume and single.is_volume
        pre = os.path.join(ROOT, "stl", f"sign_mornaguia_{key}{suffix}")
        base.export(pre + "_white_plate.stl")
        top.export(pre + "_black_text.stl")
        single.export(pre + "_single_color.stl")
        kc.write_3mf(pre + ".3mf", f"Mornaguia sign ({key})", [("white_plate", base, 1), ("black_text", top, 2)])
        print(key, "plate", np.round(base.extents, 1).tolist(), "text", np.round(top.extents, 1).tolist())
        ax.set_facecolor("#20242a")
        kc_draw(ax, plate, "#f4f4f2")
        kc_draw(ax, text, "#111")
        ax.set_xlim(-W / 2 - 5, W / 2 + 5); ax.set_ylim(-H / 2 - 5, H / 2 + 5)
        ax.set_aspect("equal"); ax.axis("off"); ax.set_title(f"{key}: {W:.0f} x {H:.0f} mm", color="k")
    plt.tight_layout()
    plt.savefig(os.path.join(ROOT, "images", f"sign_mornaguia{suffix}_preview.png"), dpi=110, bbox_inches="tight")


def kc_draw(ax, g, color):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    from shapely.geometry.polygon import orient
    for p in getattr(g, "geoms", [g]):
        if p.is_empty or p.geom_type != "Polygon":
            continue
        p = orient(p, 1)
        rings = [np.asarray(p.exterior.coords)] + [np.asarray(i.coords) for i in p.interiors]
        codes = np.concatenate([[MPath.MOVETO] + [MPath.LINETO] * (len(r) - 2) + [MPath.CLOSEPOLY] for r in rings])
        ax.add_patch(PathPatch(MPath(np.concatenate(rings), codes), color=color, lw=0))


if __name__ == "__main__":
    main()
