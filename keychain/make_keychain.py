"""Two-color football-crest keychain generator.

python3 keychain/make_keychain.py [css|ca|all]
(needs: pip install shapely trimesh svgelements manifold3d mapbox_earcut matplotlib scipy)

Colored base (shield + outline + key-ring tab) with the white parts of the crest raised on top.
  css  CS Sfaxien, black + white      -> stl/css_keychain_*
  ca   Club Africain, red + white     -> stl/ca_keychain_*
Each writes <prefix>_<base>_base.stl, <prefix>_white_relief.stl, <prefix>_single_color.stl,
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
from shapely.geometry import Point, Polygon
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


LOGOS = {
    "css": dict(name="CS Sfaxien", crest=crest_css, base="black", relief_t=0.8,
                colors=("#0d0d0d", "#f2f2f2")),
    # 1.0 mm (5 layers) of white so the red base does not tint it pink
    "ca": dict(name="Club Africain", crest=crest_ca, base="red", relief_t=1.0,
               colors=("#d40514", "#f4f4f4")),
}


def build_2d(crest):
    shield, white = crest()
    outline = shield.buffer(BORDER, join_style="round")
    top = outline.bounds[3]
    tab = Point(0, top + TAB_R - 1.5).buffer(TAB_R, 128)
    hole = Point(0, top + TAB_R - 1.5).buffer(HOLE_R, 128)
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
    base2d, white2d = build_2d(logo["crest"])
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
    white.export(f"{pre}_white_relief.stl")
    single.export(f"{pre}_single_color.stl")
    write_3mf(f"{pre}_2color.3mf", f"{logo['name']} keychain", [(base_name, base), ("white_relief", white)])
    preview(base2d, white2d, os.path.join(ROOT, "images", f"{key}_keychain_preview.png"), logo, BASE_T + relief_t)
    for n, m in [("base", base), ("white", white), ("single", single)]:
        print(key, n, "watertight", m.is_watertight, "extents", np.round(m.extents, 2), "volume", round(m.volume, 1))


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for key in LOGOS if which == "all" else [which]:
        make(key)


if __name__ == "__main__":
    main()
