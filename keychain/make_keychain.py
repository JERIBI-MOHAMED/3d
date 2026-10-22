"""Two-color football-crest keychain generator.

python3 keychain/make_keychain.py [css|ca|all]
(needs: pip install shapely trimesh svgelements manifold3d mapbox_earcut matplotlib scipy)

Colored base (shield + outline + key-ring tab) with the crest's details raised on top in a second color.
  css  CS Sfaxien, black + white      -> stl/css_keychain_*
  ca   Club Africain, red + white     -> stl/ca_keychain_*
  brand  Brand of Sacrifice (Berserk), black + red, cut-out shape -> stl/brand_keychain_*
  est  Esperance Sportive de Tunis, black + white (from the Illustrator file) -> stl/est_keychain_*
  est_flat  the same crest with a flat top: white inlaid flush in the black (needs a multi-color unit, e.g. CFS)
  moon  moon with sigil, black + white (from a black/white image) -> stl/moon_keychain_*
  sleep  Sleep Token sigil + crescent moon, black + white, 3.6 mm (rebuilt from a mockup photo) -> stl/sleep_keychain_*
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
from shapely.geometry import LineString, Point, Polygon, box
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


def stl_mascot(fn, region):
    """Raised line-art from the print-ready EST STL (inches): union of the top faces of the bodies inside
    region (x0, y0, x1, y1 in mm)."""
    m = trimesh.load(fn)
    m.apply_scale(25.4)
    x0, y0, x1, y1 = region
    tris = []
    for b in m.split(only_watertight=False):
        (bx0, by0, _), (bx1, by1, _) = b.bounds
        if bx0 >= x0 and by0 >= y0 and bx1 <= x1 and by1 <= y1:
            tris += [Polygon(t) for t in b.triangles[b.face_normals[:, 2] > 0.99][:, :, :2]]
    return unary_union([t for t in tris if t.area > 1e-9]).buffer(1e-4).buffer(-1e-4)


def crest_est():
    """Esperance Sportive de Tunis from the Illustrator file, in two colors.

    Light colors (yellow, gold, skin, white) -> white; black, grey and red -> black. The bottom text is too
    condensed to print at this size, so it is re-lettered along the full bottom arc.
    The mascot is replaced by the one from the print-ready STL (esperance_tunis_mascot_source.stl), whose
    line-art is drawn for a nozzle, and used at its own size. That STL raises the lines on a dark background; here the mascot sits on
    white, so its lines become black and the space between them white (light face, dark hair and pupils).
    """
    items = parse_ai3(os.path.join(HERE, "esperance_tunis_logo.ai"))
    outer = Polygon(items[0]["rings"][0])          # first shape: the outer yellow rim
    c = outer.centroid
    radius = (outer.bounds[2] - outer.bounds[0]) / 2
    s = SHIELD_H / 2 / radius                       # pt -> mm
    tf = lambda g: affinity.scale(affinity.translate(g, -c.x, -c.y), s, s, origin=(0, 0))

    def filled(rings):
        g = Polygon()
        for r in rings:
            if len(r) >= 3:
                g = g.symmetric_difference(Polygon(r).buffer(0))
        return g

    white, old_mascot = Polygon(), []
    for i, it in enumerate(items):
        pts = np.concatenate(it["rings"])
        # items 13+ are the original mascot, except the "1919" digits and their outlines (below the mascot)
        if i >= 13 and not (pts[:, 1].min() > 607 and pts[:, 1].max() < 620):
            old_mascot.append(pts)
            continue
        if it["kind"] == "fill":
            g = filled(it["rings"])
        else:
            g = unary_union([LineString(r).buffer(it["width"] / 2) for r in it["rings"]])
        g = tf(g)
        if cmyk_is_light(it["cmyk"]):
            p = g.centroid
            ang = np.degrees(np.arctan2(p.y, p.x)) % 360
            if 0.79 < np.hypot(p.x, p.y) / (SHIELD_H / 2) < 0.965 and 190 < ang < 350:
                continue                                 # original bottom text, re-lettered below
            white = white.union(g)
        else:
            white = white.difference(g)

    # STL mascot at its own (printable) size: feet where the original mascot's feet were, centered on it.
    # It is a little taller than the original, so the middle stripe gets a 0.6 mm white gap around the hat.
    old = (np.concatenate(old_mascot) - [c.x, c.y]) * s
    ox0, oy0, ox1 = old[:, 0].min(), old[:, 1].min(), old[:, 0].max()
    lines = stl_mascot(os.path.join(HERE, "esperance_tunis_mascot_source.stl"), (-6.5, -5.2, 6.0, 16.2))
    lx0, ly0, lx1, ly1 = lines.bounds
    lines = affinity.translate(lines, (ox0 + ox1) / 2 - (lx0 + lx1) / 2, oy0 - ly0)
    silhouette = unary_union([Polygon(p.exterior) for p in getattr(lines, "geoms", [lines])])
    mid = (silhouette.bounds[1] + silhouette.bounds[3]) / 2
    halo = silhouette.buffer(0.6).intersection(box(-SHIELD_H, mid, SHIELD_H, SHIELD_H))
    white = white.union(silhouette).union(halo).difference(lines)

    disk = Point(0, 0).buffer(SHIELD_H / 2, 256)
    black = thicken(disk.difference(white), MIN_STROKE / 2)  # gaps and lines the nozzle must keep open
    white = thicken(disk.difference(black), 0.17).intersection(disk)  # thin rims (Arachne prints 0.34)
    text, _ = arc_text("ESPERANCE SPORTIVE DE TUNIS", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                       r_base=0.947 * SHIELD_H / 2, cap_h=3.1, a0=196, a1=344, tracking=0.32)
    white = unary_union([white, text])
    top = lambda g: affinity.translate(g, 0, -SHIELD_H / 2)          # top edge at y=0
    return top(disk), top(white)


def mask_to_shapes(mask, px_mm, sigma=1.0):
    """Raster mask -> smooth shapely geometry in mm (subpixel contours, even-odd nesting); y up."""
    import cv2
    from skimage import measure
    m = cv2.GaussianBlur(np.pad(mask.astype(float), 2), (0, 0), sigma)
    rings = [Polygon(np.c_[c[:, 1] - 2, -(c[:, 0] - 2)] * px_mm).buffer(0)
             for c in measure.find_contours(m, 0.5) if len(c) > 8]
    g = Polygon()
    for p in sorted(rings, key=lambda p: -p.area):
        g = g.symmetric_difference(p)
    return g.simplify(0.01)


def crest_moon():
    """Moon with the sigil, from a black-and-white image.

    The sigil is drawn inverted where it crosses the dark maria (white strokes on black), so it is kept as part of
    the image. The moon texture is cleaned to what a 0.4 mm nozzle prints: specks under 0.45 x 0.45 mm and lines
    under 0.37 mm (both colors) are dropped; the sigil's 0.7-0.8 mm strokes are untouched.
    """
    import cv2
    from PIL import Image
    from scipy import ndimage as ndi
    g = np.array(Image.open(os.path.join(HERE, "moon_logo.webp")).convert("L"))
    ys, xs = np.nonzero(g < 128)
    (cx, cy), radius = cv2.minEnclosingCircle(np.c_[xs, ys].astype(np.float32))  # the moon's black outer edge
    px_mm = SHIELD_H / (2 * radius)
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    disk = np.hypot(xx - cx, yy - cy) < radius

    def drop_small(m, min_area):
        lab, n = ndi.label(m)
        if n == 0:
            return m
        return np.r_[False, ndi.sum(m, lab, range(1, n + 1)) >= min_area][lab]

    min_area = (0.45 / px_mm) ** 2
    r = int(round(MIN_STROKE * 0.88 / 2 / px_mm))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    white = (g >= 128) & disk
    for _ in range(2):
        white = drop_small(white, min_area)
        white = ~drop_small(~white & disk, min_area) & disk
        white = cv2.morphologyEx(white.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
        white = cv2.morphologyEx(white.astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool) & disk
    shapes = affinity.translate(mask_to_shapes(white, px_mm), -cx * px_mm, cy * px_mm)
    circle = Point(0, 0).buffer(SHIELD_H / 2, 256)
    top = lambda geom: affinity.translate(geom, 0, -SHIELD_H / 2)     # top edge at y=0
    return top(circle), top(shapes.intersection(circle))


def crest_sleep():
    """Sleep Token sigil over a crescent moon, rebuilt from the mockup photo sleep_token_reference.jpg.

    Measured on the photo (pixels of the front view): outer circle center (258, 300.1) R 173.1; left crescent =
    outer circle minus a circle shifted up (thickness 21.64 + 2.16 cos - 11.08 sin, fitted, rms 0.8 px), kept
    on the left up to the leftmost spike; terminator of the textured moon = circle (189.9, 336.7) R 193.3.
    The sigil is traced from its left half and mirrored about its own axis (x = 255.75), so it is exactly
    symmetric; the right roof is extended to the moon's edge like the left one. The moon texture is traced,
    cleaned to printable spots and kept 0.6 mm away from the sigil (black halo), as in the mockup.
    """
    import cv2
    from PIL import Image
    from scipy import ndimage as ndi
    D_MM = 35.5                                    # outer white circle, gives ~54 mm total height like the mockup
    cx, cy, R0 = 258.0, 300.1, 173.1
    s = D_MM / (2 * R0)                            # mm per photo pixel
    x0, y0, F = 60, 110, 4                         # crop of the front view, upsampling for smooth outlines
    g = np.array(Image.open(os.path.join(HERE, "sleep_token_reference.jpg")).convert("L")).astype(np.float32)
    up = cv2.resize(g[y0:570, x0:460], None, fx=F, fy=F, interpolation=cv2.INTER_CUBIC)
    W = up > 150
    pmm = lambda x, y: ((x - cx) * s, -(y - cy) * s)          # photo pixel -> mm (origin at circle center, y up)
    to_mm = lambda geom: affinity.translate(geom, (x0 - cx) * s, -(y0 - cy) * s)  # mask_to_shapes frame -> mm

    D0 = Point(0, 0).buffer(R0 * s, 256)
    D1 = Point(*pmm(cx - 2.16, cy - 11.08)).buffer((R0 - 21.64) * s, 256)
    Dt = Point(*pmm(189.9, 336.7)).buffer(193.3 * s, 256)
    axis = pmm(255.75, 0)[0]
    big = 3 * SHIELD_H
    left_of = lambda x: box(-big, -big, x, big)
    # crescent only on the left, ending at the leftmost spike (x 163 px) in the lower half
    crescent = D0.difference(D1).intersection(left_of(axis))
    crescent = crescent.difference(box(pmm(163, 0)[0], -big, big, pmm(0, 350)[1]))
    texture_region = D0.difference(Dt)

    # sigil: left half of the trace, mirrored
    trace = to_mm(mask_to_shapes(W, s / F))
    below_top = box(-big, -big, big, pmm(0, 200)[1])               # the sigil starts at y 210 px (central spike)
    left = trace.intersection(left_of(axis)).intersection(below_top).difference(crescent).difference(texture_region)
    # left roof, extended to the moon's edge (centroid and direction measured on the photo)
    c0, d = np.array(pmm(152.8, 281.9)), np.array([-0.684, -0.730])
    roof_ext = LineString([c0, c0 + d * R0 * s]).buffer(11.1 * s / 2, cap_style="flat").intersection(D0)
    left = unary_union([left, roof_ext])
    sigil = unary_union([left, affinity.scale(left, -1, 1, origin=(axis, 0))]).buffer(0.01).buffer(-0.01)

    # moon texture: traced inside the region, specks below the nozzle removed, 0.6 mm halo around the sigil
    yy, xx = np.mgrid[:W.shape[0], :W.shape[1]]
    px, py = x0 + xx / F, y0 + yy / F
    region = (np.hypot(px - cx, py - cy) < R0) & (np.hypot(px - 189.9, py - 336.7) > 193.3)
    tex = W & region
    min_area = (0.45 / (s / F)) ** 2
    r = int(round(0.185 / (s / F)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

    def drop_small(m):
        lab, n = ndi.label(m)
        return m if n == 0 else np.r_[False, ndi.sum(m, lab, range(1, n + 1)) >= min_area][lab]

    for _ in range(2):
        tex = drop_small(tex)
        tex = ~drop_small(~tex & region) & region
        tex = cv2.morphologyEx(tex.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
        tex = cv2.morphologyEx(tex.astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool) & region
    texture = to_mm(mask_to_shapes(tex, s / F)).intersection(D0).difference(sigil.buffer(0.6))

    white = unary_union([sigil, crescent, texture])
    shield = unary_union([D0, sigil]).buffer(1.2).buffer(-1.2)      # disc + rounded lobe around the spikes
    black = thicken(shield.difference(white), MIN_STROKE / 2)
    white = thicken(shield.difference(black), 0.17).intersection(shield)
    top = shield.bounds[3]
    return affinity.translate(shield, 0, -top), affinity.translate(white, 0, -top)


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
    # flat top: the black body is full height and the white is inlaid 1.0 mm deep, flush with it
    "est_flat": dict(name="Esperance Sportive de Tunis (flat)", crest=crest_est, base="black", top="white",
                     relief_t=1.0, colors=("#0d0d0d", "#f2f2f2"), flat=True),
    "moon": dict(name="Moon", crest=crest_moon, base="black", top="white", relief_t=1.0,
                 colors=("#0d0d0d", "#f2f2f2")),
    # like the mockup: ~54 mm tall, 3.6 mm thick (2.6 mm base + 1.0 mm white)
    "sleep": dict(name="Sleep Token", crest=crest_sleep, base="black", top="white", relief_t=1.0, base_t=2.6,
                  colors=("#0d0d0d", "#f2f2f2"), border=1.5),
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


# Filament slot of each color in Creality Print after syncing the CFS (1A white, 1B black, 1C -, 1D red)
FILAMENT = {"white": 1, "black": 2, "red": 4}
BED_CENTER = (110, 107.5)  # K2 SE bed 220 x 215 mm


def write_3mf(path, title, parts):
    """One object made of named parts, each already assigned to its filament.

    parts: [(name, mesh, filament)]. Metadata/model_settings.config holds the per-part "extruder"; OrcaSlicer
    and Creality Print read it from any 3MF, so the parts open in their colors.
    """
    res, comps, cfg = [], [], []
    for i, (name, m, filament) in enumerate(parts, start=1):
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        res.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{v}</vertices>'
                   f'<triangles>{t}</triangles></mesh></object>')
        comps.append(f'<component objectid="{i}"/>')
        cfg.append(f'  <part id="{i}" subtype="normal_part">\n'
                   f'   <metadata key="name" value="{name}"/>\n'
                   f'   <metadata key="extruder" value="{filament}"/>\n'
                   f'  </part>\n')
    oid = len(parts) + 1
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><resources>' + "".join(res) +
             f'<object id="{oid}" name="{title.replace(" ", "_")}" type="model"><components>{"".join(comps)}</components></object>'
             f'</resources><build><item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {BED_CENTER[0]} {BED_CENTER[1]} 0"/>'
             '</build></model>')
    settings = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
                f' <object id="{oid}">\n'
                f'  <metadata key="name" value="{title}"/>\n'
                f'  <metadata key="extruder" value="{parts[0][2]}"/>\n' + "".join(cfg) +
                ' </object>\n</config>\n')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in [("[Content_Types].xml", ct), ("_rels/.rels", rels), ("3D/3dmodel.model", model),
                           ("Metadata/model_settings.config", settings)]:
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)


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
    base_t = logo.get("base_t", BASE_T)
    base = extrude(base2d, base_t, 0)
    white = extrude(white2d, relief_t, base_t)
    flat = logo.get("flat", False)
    if flat:
        # black fills the top layer everywhere the white is not: one flat face, two colors in the same layers
        base = trimesh.boolean.union([base, extrude(base2d.difference(white2d), relief_t, base_t)], engine="manifold")
    single = trimesh.boolean.union([base, white], engine="manifold")
    assert base.is_volume and white.is_volume and single.is_volume
    out = os.path.join(ROOT, "stl")
    os.makedirs(out, exist_ok=True)
    pre = os.path.join(out, f"{key}_keychain")
    base_name = f"{logo['base']}_body" if flat else f"{logo['base']}_base"
    base.export(f"{pre}_{base_name}.stl")
    top_name = f"{logo['top']}_inlay" if flat else f"{logo['top']}_relief"
    white.export(f"{pre}_{top_name}.stl")
    if not flat:  # a flat keychain in one color would just be a plain disc
        single.export(f"{pre}_single_color.stl")
    write_3mf(f"{pre}_2color.3mf", f"{logo['name']} keychain",
              [(base_name, base, FILAMENT[logo["base"]]), (top_name, white, FILAMENT[logo["top"]])])
    preview(base2d, white2d, os.path.join(ROOT, "images", f"{key}_keychain_preview.png"), logo, base_t + relief_t)
    for n, m in [("base", base), ("white", white), ("single", single)]:
        print(key, n, "watertight", m.is_watertight, "extents", np.round(m.extents, 2), "volume", round(m.volume, 1))


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for key in LOGOS if which == "all" else [which]:
        make(key)


if __name__ == "__main__":
    main()
