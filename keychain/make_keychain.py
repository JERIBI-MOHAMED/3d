"""Two-color football-crest keychain generator.

python3 keychain/make_keychain.py [css|ca|all]
(needs: pip install shapely trimesh svgelements manifold3d mapbox_earcut matplotlib scipy)

Colored base (shield + outline + key-ring tab) with the crest's details raised on top in a second color.
  css  CS Sfaxien, black + white      -> stl/css_keychain_*
  ca   Club Africain, red + white     -> stl/ca_keychain_*
  brand  Brand of Sacrifice (Berserk), black + red, cut-out shape -> stl/brand_keychain_*
  est  Esperance Sportive de Tunis, black + white (from the Illustrator file) -> stl/est_keychain_*
Each writes <prefix>_<base>_base.stl, <prefix>_<top>_relief.stl, <prefix>_single_color.stl,
<prefix>_2color.3mf and images/<prefix>_preview.png.
"""
import os
import sys
import zipfile
import manifold3d
import numpy as np
import svgelements as se
import trimesh
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --- parameters (mm) ---
SHIELD_H = 50.0      # height of the crest itself
BORDER = 1.2         # base-color outline around the crest (3 lines with a 0.4 nozzle)
BASE_T = 3.2         # base thickness (16 layers at 0.2)
TAB_R = 5.0          # key-ring tab outer radius
HOLE_R = 2.25        # key-ring hole radius (4.5 mm hole)
MIN_STROKE = 0.42    # thinnest line the nozzle prints reliably
ARABIC_GROW = 0.12   # extra width per side for the thin Arabic letters
CURVE_TOL = 0.05     # curve flattening step (svg units)


def rings_of(path):
    """Flatten a path into closed rings, starting a new ring at every move and close."""
    rings, cur = [], []
    after_close = False

    def flush():
        nonlocal cur
        if len(cur) >= 3:
            rings.append(np.array(cur))
        cur = []

    for seg in path.segments():
        if isinstance(seg, se.Move):
            flush()
            cur = [(seg.end.x, seg.end.y)]
            continue
        if isinstance(seg, se.Close):
            flush()
            cur = [(seg.end.x, seg.end.y)] if seg.end is not None else []
            after_close = True
            continue
        if after_close and isinstance(seg, se.Line):
            # the Arabic dots are drawn as "z l<jump> ...": the jump is a pen-up, not an edge
            cur = [(seg.end.x, seg.end.y)]
            after_close = False
            continue
        after_close = False
        n = 1 if isinstance(seg, se.Line) else max(int(seg.length() / CURVE_TOL), 4)
        for t in np.linspace(0, 1, n + 1)[1:]:
            p = seg.point(t)
            cur.append((p.x, p.y))
    flush()
    return rings


def shape_of(path):
    # the logo uses fill-rule evenodd
    g = Polygon()
    for r in rings_of(path):
        g = g.symmetric_difference(Polygon(r).buffer(0))
    return g


def crest_transform(shield):
    """svg y points down: flip, then scale so the crest is SHIELD_H tall, centered, top edge at y=0."""
    s = SHIELD_H / (shield.bounds[3] - shield.bounds[1])
    ref = affinity.scale(shield, s, -s, origin=(0, 0)).bounds
    dx, dy = -(ref[0] + ref[2]) / 2, -ref[3]
    return lambda g: affinity.translate(affinity.scale(g, s, -s, origin=(0, 0)), dx, dy)


def clean(g):
    """Drop slivers narrower than the nozzle can print."""
    r = MIN_STROKE / 2 * 0.9
    return g.buffer(-r).buffer(r)


def crest_css():
    """CS Sfaxien: white shield, black field with the stripes, white CSS and Arabic name on top."""
    paths = [e for e in se.SVG.parse(os.path.join(HERE, "cs_sfaxien_logo.svg")).elements() if isinstance(e, se.Path)]
    shapes = [shape_of(p) for p in paths]
    tf = crest_transform(shapes[0])
    shield, black, text = tf(shapes[0]), tf(shapes[1]), tf(unary_union(shapes[2:]))
    # the Arabic name sits in the top band, CSS letters below it
    band_bottom = -SHIELD_H * 0.17
    parts = list(getattr(text, "geoms", [text]))
    arabic = unary_union([p for p in parts if p.centroid.y > band_bottom])
    css = unary_union([p for p in parts if p.centroid.y <= band_bottom])
    arabic = arabic.buffer(ARABIC_GROW, join_style="round")
    white = unary_union([clean(shield.difference(black)), clean(css), arabic])
    return shield, white


def crest_ca():
    """Club Africain: paint the shapes in document order, tracking the red area."""
    svg = se.SVG.parse(os.path.join(HERE, "club_africain_logo.svg"))
    clip = shape_of(se.Path(svg.get_element_by_id("SVGID_1_")))  # clip of the red stripes
    red, shield = Polygon(), None
    for e in svg.elements():
        if not isinstance(e, se.Shape):
            continue
        if e.fill is None or e.fill.value is None:
            # stroke-only outline of the striped area
            g = clip.exterior.buffer(e.stroke_width / 2)
            is_red = True
        else:
            g = shape_of(se.Path(e))
            is_red = str(e.fill).lower() != "#ffffff"
        if e.id == "path4":  # outer white border: its outside ring is the crest silhouette
            shield = Polygon(max(getattr(g, "geoms", [g]), key=lambda p: p.area).exterior)
        if isinstance(e, se.Rect):
            g = g.intersection(clip)
        red = red.union(g) if is_red else red.difference(g)
    tf = crest_transform(shield)
    shield = tf(shield)
    return shield, shield.difference(tf(red))


def _isect(p, d, q, e):
    """Intersection of the lines p + t*d and q + s*e."""
    return p + np.linalg.solve(np.array([d, -e]).T, q - p)[0] * d


def thick_polyline(pts, widths, tips=(0, 0)):
    """Centerline polyline -> polygon with one width per segment, mitred joins and pointed ends."""
    pts = [np.array(p, float) for p in pts]
    dirs = [(b - a) / np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])]
    nors = [np.array([-d[1], d[0]]) for d in dirs]
    sides = []
    for sgn in (1, -1):
        line = [pts[0] + sgn * nors[0] * widths[0] / 2]
        for i in range(1, len(pts) - 1):
            line.append(_isect(pts[i] + sgn * nors[i - 1] * widths[i - 1] / 2, dirs[i - 1],
                               pts[i] + sgn * nors[i] * widths[i] / 2, dirs[i]))
        line.append(pts[-1] + sgn * nors[-1] * widths[-1] / 2)
        sides.append(line)
    ring = list(sides[0])
    if tips[1]:
        ring.append(pts[-1] + dirs[-1] * tips[1])
    ring += sides[1][::-1]
    if tips[0]:
        ring.append(pts[0] - dirs[0] * tips[0])
    return Polygon(ring).buffer(0)


def roughen(g, seed=7, amp=0.09, corr=0.45, bite_every=2.5, bite_depth=(0.12, 0.35), bite_w=(0.3, 0.7)):
    """Hand-carved edge: smooth random wobble plus small chips, pushed inward (mm)."""
    rng = np.random.default_rng(seed)
    step = 0.05

    def ring_xy(line):
        n = max(int(line.length / step), 16)
        pts = np.array([line.interpolate(t).coords[0] for t in np.linspace(0, line.length, n, endpoint=False)])
        nxt, prv = np.roll(pts, -1, 0), np.roll(pts, 1, 0)
        tang = nxt - prv
        out = np.c_[tang[:, 1], -tang[:, 0]]  # right-hand normal = out of the material (orient(g, 1))
        out /= np.linalg.norm(out, axis=1)[:, None]
        noise = rng.normal(size=n)
        k = np.exp(-0.5 * (np.arange(-3 * int(corr / step), 3 * int(corr / step) + 1) * step / corr) ** 2)
        noise = np.convolve(np.r_[noise[-len(k):], noise, noise[:len(k)]], k / k.sum(), "same")[len(k):-len(k)]
        d = noise / noise.std() * amp - amp
        s_pos = np.arange(n) * step
        for _ in range(int(line.length / bite_every)):
            c, w, dep = rng.uniform(0, line.length), rng.uniform(*bite_w), rng.uniform(*bite_depth)
            dist = np.abs((s_pos - c + line.length / 2) % line.length - line.length / 2)
            d -= dep * np.clip(1 - dist / (w / 2), 0, None)
        return pts + out * d[:, None]

    polys = []
    for p in getattr(g, "geoms", [g]):
        p = orient(p, 1)
        polys.append(Polygon(ring_xy(p.exterior), [ring_xy(i) for i in p.interiors]).buffer(0))
    return unary_union(polys)


def crest_brand():
    """Brand of Sacrifice, rebuilt as strokes measured from the hand-drawn reference (2x pixel coords)."""
    P = dict(TL=(236, 108), UL=(85, 270), LR=(544, 668), BOT=(306, 913), LL=(81, 652), UR=(535, 284), TR=(384, 118))
    WS, WX, WU, WL = 40, 38, 44, 62  # stem, X, upper arms, lower V
    loop = thick_polyline([P["TL"], P["UL"], P["LR"], P["BOT"], P["LL"], P["UR"], P["TR"]],
                          [WU, WX, WL, WL, WX, WU], tips=(22, 22))
    stem = thick_polyline([(315, 95), (307, 900)], [WS], tips=(57, 0))
    sym = unary_union([loop, stem])
    tf = crest_transform(sym)
    sym = tf(sym)
    return sym, roughen(sym)


def thicken(g, r):
    """Widen the thin lines of g (narrower than 2r) to about 2r.

    The thin parts are what an opening removes. Each one only grows by what it is missing (its mean width is
    estimated from area and perimeter), so lines already close to 2r stay as they are. Small leftovers at
    corners are skipped, so corners stay sharp instead of growing blobs.
    """
    thin = g.difference(g.buffer(-0.95 * r).buffer(0.95 * r))
    grown = []
    for p in getattr(thin, "geoms", [thin]):
        if p.is_empty or p.area < 2 * r * r:
            continue
        x0, y0, x1, y1 = p.bounds
        if max(x1 - x0, y1 - y0) < 3 * r:
            continue
        mean_w = 2 * p.area / p.length
        grow = r - mean_w / 2
        if grow > 0.01:
            grown.append(p.buffer(grow))
    return unary_union([g] + grown)


def _bezier(p0, p1, p2, p3, n=12):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def parse_ai3(fn):
    """Adobe Illustrator 3 (text PostScript) -> painted items in drawing order.

    Each item: dict(kind="fill"|"stroke", cmyk, width (pt), rings=[N x 2 arrays]). Fill + stroke paths ("b")
    give a fill item and, when the outline color differs, a stroke item marked outline=True (the border of
    a filled shape, e.g. an eye). Compound paths (*u .. *U) are one fill (even-odd).
    """
    items, fill, stroke, width = [], (0, 0, 0, 1), (0, 0, 0, 1), 1.0
    sub, cur, compound, started = [], [], None, False

    def end_sub():
        nonlocal cur
        if len(cur) >= 2:
            sub.append(np.array(cur))
        cur = []

    for line in open(fn, encoding="latin-1"):
        t = line.split()
        if not t:
            continue
        if t[0] == "%%EndSetup":
            started = True
            continue
        if not started or t[0].startswith("%"):
            continue
        op = t[-1]
        try:
            v = [float(x) for x in t[:-1]]
        except ValueError:
            continue
        if op == "k" and len(v) == 4:
            fill = tuple(v)
        elif op == "K" and len(v) == 4:
            stroke = tuple(v)
        elif op == "w" and len(v) == 1:
            width = v[0]
        elif op == "m":
            end_sub()
            cur = [tuple(v)]
        elif op in ("l", "L"):
            cur.append(tuple(v))
        elif op in ("c", "C", "v", "V", "y", "Y"):
            p0 = np.array(cur[-1])
            if op in "cC":
                c1, c2, p3 = np.array(v[0:2]), np.array(v[2:4]), np.array(v[4:6])
            elif op in "vV":
                c1, c2, p3 = p0, np.array(v[0:2]), np.array(v[2:4])
            else:
                c1, c2, p3 = np.array(v[0:2]), np.array(v[2:4]), np.array(v[2:4])
            cur += [tuple(p) for p in _bezier(p0, c1, c2, p3)]
        elif op in ("f", "F", "b", "B", "s", "S", "n", "N"):
            end_sub()
            new = []
            if op in "fFbB":
                new.append(dict(kind="fill", cmyk=fill, width=0, rings=list(sub)))
            if op in "sS" or (op in "bB" and stroke != fill):
                new.append(dict(kind="stroke", cmyk=stroke, width=width, rings=list(sub), outline=op in "bB"))
            (compound if compound is not None else items).extend(new)
            sub = []
        elif op == "*u":
            compound = []
        elif op == "*U":
            fills = [c for c in compound if c["kind"] == "fill"]
            if fills:
                items.append(dict(kind="fill", cmyk=fills[0]["cmyk"], width=0,
                                  rings=[r for c in fills for r in c["rings"]]))
            items += [c for c in compound if c["kind"] == "stroke"]
            compound = None
    return items


def cmyk_is_light(c):
    r, g, b = ((1 - x) * (1 - c[3]) for x in c[:3])
    return 0.299 * r + 0.587 * g + 0.114 * b > 0.5


def arc_text(text, font, r_base, cap_h, a0, a1, tracking):
    """Text along the bottom of a circle (centered at 0,0), read left to right, letter tops toward the center.

    Spread between angles a0..a1 (degrees, a0 < a1, e.g. 195..345); letters are squeezed horizontally to fit.
    """
    from fontTools.ttLib import TTFont
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    tt = TTFont(font)
    upm, cmap, hmtx = tt["head"].unitsPerEm, tt.getBestCmap(), tt["hmtx"]
    h = TextPath((0, 0), "H", size=1, prop=FontProperties(fname=font)).get_extents()
    em = cap_h / h.height
    prop = FontProperties(fname=font)
    glyphs, adv = [], []
    for ch in text:
        g = Polygon()
        if ch != " ":
            for ring in TextPath((0, 0), ch, size=em, prop=prop).to_polygons():
                if len(ring) >= 3:
                    g = g.symmetric_difference(Polygon(ring).buffer(0))
        glyphs.append(g)
        adv.append(hmtx[cmap[ord(ch)]][0] / upm * em)
    arc = np.radians(a1 - a0) * (r_base - cap_h / 2)
    sx = (arc - tracking * (len(text) - 1)) / sum(adv)
    out, pos = [], 0.0
    for g, a in zip(glyphs, adv):
        w = a * sx
        theta = np.radians(a0) + (pos + w / 2) / (r_base - cap_h / 2)
        pos += w + tracking
        if g.is_empty:
            continue
        g = affinity.scale(g, sx, 1, origin=(0, 0))
        g = affinity.translate(g, -w / 2, 0)                     # centered on the baseline point
        g = affinity.rotate(g, np.degrees(theta) + 90, origin=(0, 0))
        out.append(affinity.translate(g, r_base * np.cos(theta), r_base * np.sin(theta)))
    return unary_union(out), sx


def crest_est():
    """Esperance Sportive de Tunis from the Illustrator file, in two colors.

    Light colors (yellow, gold, skin, white) -> white; black, grey and red -> black. The mascot's hairline
    outlines become 0.42 mm black lines. The bottom text is too condensed to print at this size, so it is
    re-lettered along the full bottom arc.
    """
    items = parse_ai3(os.path.join(HERE, "esperance_tunis_logo.ai"))
    outer = Polygon(items[0]["rings"][0])          # first shape: the outer yellow rim
    c = outer.centroid
    radius = (outer.bounds[2] - outer.bounds[0]) / 2
    s = SHIELD_H / 2 / radius                       # pt -> mm
    tf = lambda g: affinity.scale(affinity.translate(g, -c.x, -c.y), s, s, origin=(0, 0))
    white = Polygon()
    def filled(rings):
        g = Polygon()
        for r in rings:
            if len(r) >= 3:
                g = g.symmetric_difference(Polygon(r).buffer(0))
        return g

    for it in items:
        if it["kind"] == "fill":
            g = filled(it["rings"])
        else:
            w = it["width"] if cmyk_is_light(it["cmyk"]) else max(it["width"], MIN_STROKE / s)
            if it.get("outline"):
                # border of a filled shape: draw it outward only, so small shapes (eyes, teeth) keep their size
                f = filled(it["rings"])
                g = f.buffer(w).difference(f)
            else:
                g = unary_union([LineString(r).buffer(w / 2) for r in it["rings"]])
        g = tf(g)
        if cmyk_is_light(it["cmyk"]):
            p = g.centroid
            ang = np.degrees(np.arctan2(p.y, p.x)) % 360
            if 0.79 < np.hypot(p.x, p.y) / (SHIELD_H / 2) < 0.965 and 190 < ang < 350:
                continue                                 # original bottom text, re-lettered below
            white = white.union(g)
        else:
            white = white.difference(g)
    disk = Point(0, 0).buffer(SHIELD_H / 2, 256)
    black = thicken(disk.difference(white), MIN_STROKE / 2)  # gaps and lines the nozzle must keep open
    white = thicken(disk.difference(black), 0.17).intersection(disk)  # thin rims (Arachne prints 0.34)
    text, _ = arc_text("ESPERANCE SPORTIVE DE TUNIS", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                       r_base=0.947 * SHIELD_H / 2, cap_h=3.1, a0=196, a1=344, tracking=0.32)
    white = unary_union([white, text])
    top = lambda g: affinity.translate(g, 0, -SHIELD_H / 2)          # top edge at y=0
    return top(disk), top(white)


LOGOS = {
    "css": dict(name="CS Sfaxien", crest=crest_css, base="black", top="white", relief_t=0.8,
                colors=("#0d0d0d", "#f2f2f2")),
    # 1.0 mm (5 layers) of white so the red base does not tint it pink
    "ca": dict(name="Club Africain", crest=crest_ca, base="red", top="white", relief_t=1.0,
               colors=("#d40514", "#f4f4f4")),
    # cut-out keychain: the base follows the symbol; the ring tab overlaps the stem tip for strength
    "brand": dict(name="Brand of Sacrifice", crest=crest_brand, base="black", top="red", relief_t=1.0,
                  colors=("#0d0d0d", "#c8101a"), border=1.5, tab_overlap=3.5),
    # 1.0 mm of white so the black base does not grey it
    "est": dict(name="Esperance Sportive de Tunis", crest=crest_est, base="black", top="white", relief_t=1.0,
                colors=("#0d0d0d", "#f2f2f2")),
}


def build_2d(logo):
    shield, white = logo["crest"]()
    outline = shield.buffer(logo.get("border", BORDER), join_style="round")
    top = outline.bounds[3]
    tab_y = top + TAB_R - logo.get("tab_overlap", 1.5)
    tab = Point(0, tab_y).buffer(TAB_R, 128)
    hole = Point(0, tab_y).buffer(HOLE_R, 128)
    base = unary_union([outline, tab]).difference(hole)
    white = white.intersection(shield)
    white = white.buffer(0.02).buffer(-0.02)  # fuse point contacts so the mesh stays manifold
    white = unary_union([p for p in getattr(white, "geoms", [white]) if p.area > 0.02])  # drop specks
    return base, white


def extrude(g, h, z0):
    rings = []
    g = g.simplify(0.01)  # 10 micron: invisible, keeps the files small
    for p in getattr(g, "geoms", [g]):
        rings.append(np.array(p.exterior.coords[:-1]))
        rings += [np.array(i.coords[:-1]) for i in p.interiors]
    cs = manifold3d.CrossSection(rings, manifold3d.FillRule.EvenOdd)
    out = cs.extrude(h).translate((0, 0, z0)).to_mesh()
    return trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts)


def write_3mf(path, title, parts):
    """One object made of named parts (slicers load it as a multi-part object; set a filament per part)."""
    res, comps = [], []
    for i, (name, m) in enumerate(parts, start=1):
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        res.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{v}</vertices>'
                   f'<triangles>{t}</triangles></mesh></object>')
        comps.append(f'<component objectid="{i}"/>')
    oid = len(parts) + 1
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><resources>' + "".join(res) +
             f'<object id="{oid}" name="{title.replace(" ", "_")}" type="model"><components>{"".join(comps)}</components></object>'
             f'</resources><build><item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 128 128 0"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def preview(base, white, path, logo, thickness):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bg = "#20242a"
    base_c, top_c = logo["colors"]

    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    from shapely.geometry.polygon import orient

    def draw(ax, g, color):
        # one compound path per polygon (holes wound the other way) so islands inside holes stay visible
        for p in getattr(g, "geoms", [g]):
            p = orient(p, 1)
            rings = [np.asarray(p.exterior.coords)] + [np.asarray(i.coords) for i in p.interiors]
            codes = np.concatenate([[MPath.MOVETO] + [MPath.LINETO] * (len(r) - 2) + [MPath.CLOSEPOLY] for r in rings])
            ax.add_patch(PathPatch(MPath(np.concatenate(rings), codes), color=color, lw=0))

    fig, ax = plt.subplots(figsize=(6, 7.5), facecolor=bg)
    ax.set_facecolor(bg)
    draw(ax, base, base_c)
    draw(ax, white, top_c)
    for p in getattr(base, "geoms", [base]):
        ax.plot(*p.exterior.xy, color="#555", lw=0.6)
        for i in p.interiors:
            ax.plot(*i.xy, color="#555", lw=0.6)
    x0, y0, x1, y1 = base.bounds
    ax.set_title(f"{logo['name']} keychain  {x1 - x0:.1f} x {y1 - y0:.1f} x {thickness:.1f} mm", color="w", fontsize=11)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    plt.savefig(path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())


def make(key):
    logo = LOGOS[key]
    base2d, white2d = build_2d(logo)
    relief_t = logo["relief_t"]
    base = extrude(base2d, BASE_T, 0)
    white = extrude(white2d, relief_t, BASE_T)
    single = trimesh.boolean.union([base, white], engine="manifold")
    assert base.is_volume and white.is_volume and single.is_volume
    out = os.path.join(ROOT, "stl")
    os.makedirs(out, exist_ok=True)
    pre = os.path.join(out, f"{key}_keychain")
    base_name = f"{logo['base']}_base"
    base.export(f"{pre}_{base_name}.stl")
    top_name = f"{logo['top']}_relief"
    white.export(f"{pre}_{top_name}.stl")
    single.export(f"{pre}_single_color.stl")
    write_3mf(f"{pre}_2color.3mf", f"{logo['name']} keychain", [(base_name, base), (top_name, white)])
    preview(base2d, white2d, os.path.join(ROOT, "images", f"{key}_keychain_preview.png"), logo, BASE_T + relief_t)
    for n, m in [("base", base), ("white", white), ("single", single)]:
        print(key, n, "watertight", m.is_watertight, "extents", np.round(m.extents, 2), "volume", round(m.volume, 1))


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for key in LOGOS if which == "all" else [which]:
        make(key)


if __name__ == "__main__":
    main()
