"""Black cut-out wall art (no backlight), printed in tiles on a small bed.

python3 wallart/make_wallart.py        (same dependencies as keychain/make_keychain.py)
python3 wallart/make_wallart.py --from-3mf sign.3mf --part "SOA Redwood OG" --out DIR
    takes the logo from a part of a 3MF you have (sliced at mid-height; mirrored back when the part sits at
    the bottom of the model, i.e. a sign printed face down) and writes the tiles and previews into DIR.
python3 wallart/make_wallart.py --image logo.jpg --name wallart_soa_redwood
    traces a light logo on a dark background (smooth sub-pixel outlines, svg/raster_to_svg.py) and names the
    files NAME_rRcC.stl, NAME_preview.png, NAME_tiles.png.

Sons of Anarchy panel, 50 cm wide x 100 cm tall: a black frame with the logo cut out. The logo's light parts
(the two text banners and the reaper) are the plastic; its black background is open, so the wall shows
through, and the letters are cut out of the banners. Every piece is bridged to the frame so the panel is one
part, then it is cut into tiles that fit the Creality K2 SE bed (220 x 215 mm), joined by dovetails on the
frame and glued.

Outputs: stl/wallart_soa_rRcC.stl (one tile per plate) and images/wallart_soa_preview.png / _tiles.png.
"""
import os
import sys
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "keychain"))
import make_keychain as kc  # noqa: E402  (mask_to_shapes, thicken, extrude)

# --- parameters (mm) ---
W, H = 500.0, 1000.0      # panel: 50 cm wide x up to 100 cm tall
TOP_GAP = 15.0            # space between the top of the logo and the top frame bar (None: full height H)
BOTTOM_GAP = 15.0         # space between the bottom of the logo and the bottom frame bar (None: full height H)
Y0, Y1 = -H / 2, H / 2    # panel bottom / top, set by design()
FRAME = 25.0              # frame border width
LOGO_W = 440.0            # logo width inside the frame
T_FRAME = 5.0             # frame thickness
T_ART = 4.0               # logo thickness (sits flush with the frame back, 1 mm lower at the front)
MIN_PLASTIC = 3.0         # thinnest plastic line (sturdy at this size)
MIN_HOLE = 2.0            # thinnest opening
MIN_ISLAND = 50.0         # plastic pieces smaller than this (mm2) are dropped instead of bridged
BRIDGE = 4.0              # bridge width
COLS, ROWS = 3, 5         # tiles; ROWS is recomputed by design(): rows <= MAX_ROW tall. Column cuts cross the least logo
MAX_ROW = 205.0           # tallest row (+ the 10 mm dovetail = 215 mm, the K2 SE bed depth)
DOVE = 10.0               # dovetail size on the frame joints
CLEAR = 0.15              # dovetail clearance per side


SOURCE = None             # (3mf path, part name) to take the logo from, set by --from-3mf / --part
IMAGE = None              # light-on-dark logo image to trace instead, set by --image
NAME = "wallart_soa"      # output file prefix, set by --name
OUT = None                # output directory (default: stl/ and images/ of the repository)


def logo_from_3mf(path, part):
    """The named part of a Bambu/Orca 3MF -> 2D outline (slice at mid-height), mirrored back if face-down."""
    import re
    import zipfile
    import trimesh
    z = zipfile.ZipFile(path)
    cfg = z.read("Metadata/model_settings.config").decode()
    ids = re.findall(r'<part id="(\d+)"[^>]*>\s*<metadata key="name" value="([^"]+)"', cfg)
    pid = next(i for i, n in ids if n == part)
    main = z.read("3D/3dmodel.model").decode()
    comps = dict(re.findall(r'<component [^>]*objectid="(\d+)"[^>]*transform="([^"]+)"', main))
    meshes = {}
    for name in z.namelist():
        if name.startswith("3D/Objects/") and name.endswith(".model"):
            src = z.read(name).decode()
            for oid, body in re.findall(r'<object id="(\d+)"[^>]*>(.*?)</object>', src, re.S):
                v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body), float)
                fc = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body), int)
                if oid in comps:
                    M = np.array(comps[oid].split(), float).reshape(4, 3)
                    v = v @ M[:3] + M[3]
                meshes[oid] = trimesh.Trimesh(v, fc, process=False)
    m = meshes[pid]
    zmid = m.bounds[:, 2].mean()
    planar, _ = m.section(plane_origin=[0, 0, zmid], plane_normal=[0, 0, 1]).to_2D(to_2D=np.eye(4), check=False)
    g = unary_union(planar.polygons_full)
    zmin_all = min(mm.bounds[0, 2] for mm in meshes.values())
    if m.bounds[0, 2] - zmin_all < 0.5:                      # at the bottom: the sign prints face down
        g = affinity.scale(g, -1, 1, origin=(0, 0))
    return g


def logo_shapes():
    """Light parts of the logo -> shapely geometry in mm, centered at (0, 0), LOGO_W wide."""
    if SOURCE:
        art = logo_from_3mf(*SOURCE)
        x0, y0, x1, y1 = art.bounds
        k = LOGO_W / (x1 - x0)
        art = affinity.scale(art, k, k, origin=((x0 + x1) / 2, (y0 + y1) / 2))
        x0, y0, x1, y1 = art.bounds
        return affinity.translate(art, -(x0 + x1) / 2, -(y0 + y1) / 2)
    if IMAGE:
        sys.path.insert(0, os.path.join(ROOT, "svg"))
        import raster_to_svg
        rings, _ = raster_to_svg.trace(IMAGE, threshold=128, invert=True)
        art = Polygon()
        for p in sorted((Polygon(np.c_[r[:, 0], -r[:, 1]]).buffer(0) for r in rings), key=lambda p: -p.area):
            art = art.symmetric_difference(p)                  # even-odd nesting; image y points down
        x0, y0, x1, y1 = art.bounds
        k = LOGO_W / (x1 - x0)
        art = affinity.scale(art, k, k, origin=((x0 + x1) / 2, (y0 + y1) / 2))
        x0, y0, x1, y1 = art.bounds
        return affinity.translate(art, -(x0 + x1) / 2, -(y0 + y1) / 2)
    from PIL import Image
    g = np.array(Image.open(os.path.join(HERE, "soa_reference.jpg")).convert("L")).astype(np.float32)
    light = g > 110
    ys, xs = np.nonzero(light)
    px_mm = LOGO_W / (xs.max() - xs.min() + 1)
    art = kc.mask_to_shapes(light, px_mm, sigma=1.0)
    x0, y0, x1, y1 = art.bounds
    return affinity.translate(art, -(x0 + x1) / 2, -(y0 + y1) / 2)


def parts(g):
    return [p for p in getattr(g, "geoms", [g]) if not p.is_empty]


def clean(art):
    art = kc.thicken(art, MIN_PLASTIC / 2)                       # plastic lines >= 3 mm
    fr = art.envelope.buffer(5)
    art = fr.difference(kc.thicken(fr.difference(art), MIN_HOLE / 2)).intersection(art.envelope.buffer(1))
    art = unary_union([p for p in parts(art) if p.area >= MIN_ISLAND])
    # fill holes too small to see
    art = unary_union([Polygon(p.exterior, [i for i in p.interiors if Polygon(i).area >= 4.0]) for p in parts(art)])
    return art


def bridge(a, b):
    pa, pb = nearest_points(a, b)
    return LineString([pa, pb]).buffer(BRIDGE / 2, cap_style="flat").union(pa.buffer(BRIDGE / 2)).union(pb.buffer(BRIDGE / 2))


def connect(frame, art):
    """Bridge every logo piece to the frame (directly or through pieces already connected).

    Big pieces (the banners, the reaper) get a second bridge from their other half, so they don't pivot."""
    main = frame
    pieces = sorted(parts(art), key=lambda p: -p.area)
    big = pieces[0].area * 0.15
    bridges = []
    remaining = pieces[:]
    while remaining:
        # connect the piece closest to what is already connected
        i = min(range(len(remaining)), key=lambda j: remaining[j].distance(main))
        p = remaining.pop(i)
        b1 = bridge(p, main)
        bridges.append(b1)
        if p.area >= big:
            # second bridge from the half of the piece away from the first bridge
            c = p.centroid
            bx = b1.centroid
            d = np.array([bx.x - c.x, bx.y - c.y])
            d = d / (np.linalg.norm(d) + 1e-9)
            far = p.intersection(Polygon([(c.x + d[1] * 2e3 - d[0] * 2e3, c.y - d[0] * 2e3 - d[1] * 2e3),
                                          (c.x - d[1] * 2e3 - d[0] * 2e3, c.y + d[0] * 2e3 - d[1] * 2e3),
                                          (c.x - d[1] * 2e3, c.y + d[0] * 2e3),
                                          (c.x + d[1] * 2e3, c.y - d[0] * 2e3)]))
            if not far.is_empty:
                bridges.append(bridge(far, main.difference(p.buffer(1))))
        main = unary_union([main, p, *bridges[-2:]])
    return unary_union(bridges)


def design():
    global Y0, Y1, ROWS
    art = clean(logo_shapes())
    if TOP_GAP is not None:
        Y1 = min(H / 2, art.bounds[3] + TOP_GAP + FRAME)     # top frame bar right above the logo
    if BOTTOM_GAP is not None:
        Y0 = max(-H / 2, art.bounds[1] - BOTTOM_GAP - FRAME)  # bottom frame bar right below it
    ROWS = int(np.ceil((Y1 - Y0) / MAX_ROW))
    outer = box(-W / 2, Y0, W / 2, Y1)
    frame = outer.difference(box(-W / 2 + FRAME, Y0 + FRAME, W / 2 - FRAME, Y1 - FRAME))
    bars = connect(frame, art)
    return frame, art, bars


def dovetail(c, d, normal):
    """Dovetail tab centered at c on a cut, pointing along `normal` (unit vector) into the next tile."""
    n = np.array(normal, float)
    t = np.array([-n[1], n[0]])
    c = np.array(c, float)
    neck, head = 4.0, 7.0
    pts = [c - t * neck, c - t * head + n * d, c + t * head + n * d, c + t * neck]
    return Polygon(pts).union(Polygon([c - t * neck - n * 1.0, c - t * neck, c + t * neck, c + t * neck - n * 1.0]))


def column_cuts(logo, max_w=200.0):
    """The two vertical cuts (3 columns, each <= max_w wide) that cross the least logo."""
    def crossed(x):
        return logo.intersection(LineString([(x, Y0), (x, Y1)])).length
    cand = np.arange(-W / 2 + W - 2 * max_w, -W / 2 + max_w + 0.1, 2.0)   # first cut range
    prof = {round(x, 1): crossed(x) for x in np.arange(-W / 2 + 50, W / 2 - 49, 2.0)}
    best = None
    for c1 in cand:
        for c2 in np.arange(max(c1 + 50, W / 2 - max_w), min(c1 + max_w, W / 2 - 50) + 0.1, 2.0):
            cost = prof[round(c1, 1)] + prof[round(c2, 1)]
            if best is None or cost < best[0]:
                best = (cost, c1, c2)
    return [-W / 2, best[1], best[2], W / 2]


def tiles(frame, logo):
    """Split into COLS x ROWS tiles; dovetails on the frame at every cut. -> {(r, c): (frame_part, logo_part)}"""
    xs = np.array(column_cuts(logo))
    ys = np.linspace(Y0, Y1, ROWS + 1)
    tabs = {}  # (r, c) -> list of tab polygons owned by that tile
    for r in range(ROWS):
        for c in range(COLS):
            tabs[(r, c)] = []
    for c in range(1, COLS):          # vertical cuts: tabs in the top and bottom frame bands, left tile -> right
        for yc in (Y1 - FRAME / 2, Y0 + FRAME / 2):
            r = ROWS - 1 if yc > 0 else 0
            tabs[(r, c - 1)].append(dovetail((xs[c], yc), DOVE, (1, 0)))
    for r in range(1, ROWS):          # horizontal cuts: tabs in the left and right frame bands, lower tile -> upper
        for xc in (-W / 2 + FRAME / 2, W / 2 - FRAME / 2):
            c = 0 if xc < 0 else COLS - 1
            tabs[(r - 1, c)].append(dovetail((xc, ys[r]), DOVE, (0, 1)))
    out = {}
    for r in range(ROWS):
        for c in range(COLS):
            cell = box(xs[c], ys[r], xs[c + 1], ys[r + 1])
            f = frame.intersection(cell)
            own = unary_union(tabs[(r, c)]) if tabs[(r, c)] else Polygon()
            f = unary_union([f, own])
            for (r2, c2), tl in tabs.items():
                if (r2, c2) != (r, c) and tl:
                    f = f.difference(unary_union(tl).buffer(CLEAR, join_style="mitre"))
            out[(r, c)] = (f, logo.intersection(cell).difference(f))
    return out, xs, ys


BED = (220.0, 215.0)      # K2 SE bed, for the plate grid of the project file


def pack_project(stl_paths, out, title):
    """All tiles in one 3MF project: one tile per plate (r1c1 = plate 1), black filament.

    Creality Print / OrcaSlicer lay plates in a grid (3 columns for 9 plates, 1.2 x bed apart) and read the
    plate list from Metadata/model_settings.config, so each tile opens on its own plate, ready to slice.
    """
    import re
    import zipfile
    import trimesh
    tiles = sorted(stl_paths, key=lambda p: [int(n) for n in re.findall(r"r(\d+)c(\d+)", p)[-1]])
    n = len(tiles)
    cols = int(np.ceil(np.sqrt(n)))
    res, items, cfg, plates = [], [], [], []
    for i, path in enumerate(tiles):
        m = trimesh.load(path)
        lo, hi = m.bounds
        m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
        name = os.path.splitext(os.path.basename(path))[0]
        tag = re.findall(r"r\d+c\d+", name)[-1]
        mesh_id, obj_id = 2 * i + 1, 2 * i + 2
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        res.append(f'<object id="{mesh_id}" name="{tag}" type="model"><mesh><vertices>{v}</vertices>'
                   f'<triangles>{t}</triangles></mesh></object>'
                   f'<object id="{obj_id}" name="{tag}" type="model"><components><component objectid="{mesh_id}"/>'
                   f'</components></object>')
        row, col = divmod(i, cols)
        x = col * BED[0] * 1.2 + BED[0] / 2
        y = -row * BED[1] * 1.2 + BED[1] / 2
        items.append(f'<item objectid="{obj_id}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0"/>')
        cfg.append(f' <object id="{obj_id}">\n  <metadata key="name" value="{tag}"/>\n'
                   f'  <metadata key="extruder" value="1"/>\n'
                   f'  <part id="{mesh_id}" subtype="normal_part">\n   <metadata key="name" value="{name}"/>\n'
                   f'   <metadata key="extruder" value="1"/>\n  </part>\n </object>\n')
        plates.append(f' <plate>\n  <metadata key="plater_id" value="{i + 1}"/>\n'
                      f'  <metadata key="plater_name" value="{tag}"/>\n  <metadata key="locked" value="false"/>\n'
                      f'  <model_instance>\n   <metadata key="object_id" value="{obj_id}"/>\n'
                      f'   <metadata key="instance_id" value="0"/>\n   <metadata key="identify_id" value="{100 + i}"/>\n'
                      f'  </model_instance>\n </plate>\n')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><resources>' + "".join(res) + '</resources><build>'
             + "".join(items) + '</build></model>')
    settings = '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + "".join(cfg) + "".join(plates) + '</config>\n'
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in [("[Content_Types].xml", ct), ("_rels/.rels", rels), ("3D/3dmodel.model", model),
                           ("Metadata/model_settings.config", settings)]:
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)
    return n


def draw(ax, g, color):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    from shapely.geometry.polygon import orient
    for p in parts(g):
        if p.geom_type != "Polygon":
            continue
        p = orient(p, 1)
        rings = [np.asarray(p.exterior.coords)] + [np.asarray(i.coords) for i in p.interiors]
        codes = np.concatenate([[MPath.MOVETO] + [MPath.LINETO] * (len(r) - 2) + [MPath.CLOSEPOLY] for r in rings])
        ax.add_patch(PathPatch(MPath(np.concatenate(rings), codes), color=color, lw=0))


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    frame, art, bars = design()
    logo = unary_union([art, bars]).difference(frame)
    tl, xs, ys = tiles(frame, logo)
    stl_dir = OUT or os.path.join(ROOT, "stl")
    img_dir = OUT or os.path.join(ROOT, "images")
    os.makedirs(stl_dir, exist_ok=True)
    total, info = 0.0, []
    for (r, c), (f, lg) in sorted(tl.items()):
        meshes = [kc.extrude(f, T_FRAME, 0)] if not f.is_empty else []
        if not lg.is_empty and lg.area > 0.5:
            meshes.append(kc.extrude(lg, T_ART, 0))
        m = trimesh.boolean.union(meshes, engine="manifold") if len(meshes) > 1 else meshes[0]
        assert m.is_volume, (r, c)
        name = f"{NAME}_r{ROWS - r}c{c + 1}.stl"          # row 1 = top
        m.export(os.path.join(stl_dir, name))
        total += m.volume
        info.append((name, np.round(m.extents[:2], 1).tolist(), round(m.volume / 1000, 1)))
    print("column cuts at x =", np.round(xs[1:-1], 1).tolist(), "(logo crossed: %.0f mm)" % sum(
        logo.intersection(LineString([(x, Y0), (x, Y1)])).length for x in xs[1:-1]))
    for i in info:
        print(*i)
    import glob
    proj = os.path.join(stl_dir, f"{NAME}_project.3mf")
    pack_project(glob.glob(os.path.join(stl_dir, f"{NAME}_r*c*.stl")), proj, f"{NAME} wall art")
    print("project file", proj)
    print("total volume %.0f cm3 -> about %.0f g PLA at ~75 %% fill (4-5 mm parts are mostly walls)" % (total / 1000, total / 1000 * 1.24 * 0.75))
    # previews: the panel on a light wall, and the tile layout
    for fn, show_tiles in ((f"{NAME}_preview.png", False), (f"{NAME}_tiles.png", True)):
        fig, ax = plt.subplots(figsize=(6, 11))
        fig.patch.set_facecolor("#20242a")
        draw(ax, box(-W / 2, Y0, W / 2, Y1), "#d9d4ca")          # the wall behind the panel
        draw(ax, frame, "#111")
        draw(ax, logo, "#111")
        if show_tiles:
            for x in xs[1:-1]:
                ax.plot([x, x], [Y0, Y1], color="#e33", lw=0.8)
            for y in ys[1:-1]:
                ax.plot([-W / 2, W / 2], [y, y], color="#e33", lw=0.8)
            for r in range(ROWS):
                for c in range(COLS):
                    ax.text((xs[c] + xs[c + 1]) / 2, (ys[r] + ys[r + 1]) / 2, f"r{ROWS - r}c{c + 1}",
                            color="#e33", ha="center", va="center", fontsize=9)
        ax.set_xlim(-W / 2 - 10, W / 2 + 10)
        ax.set_ylim(Y0 - 10, Y1 + 10)
        ax.set_aspect("equal")
        ax.axis("off")
        title = "tiles (row 1 = top)" if show_tiles else f"Sons of Anarchy wall art  {W / 10:.0f} x {(Y1 - Y0) / 10:.1f} cm"
        ax.set_title(title, color="w")
        plt.savefig(os.path.join(img_dir, fn), dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-3mf")
    ap.add_argument("--part")
    ap.add_argument("--out")
    ap.add_argument("--image")
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--pack-only", action="store_true", help="only build NAME_project.3mf from the existing tiles")
    a = ap.parse_args()
    IMAGE, NAME = a.image, a.name
    if a.pack_only:
        import glob
        d = a.out or os.path.join(ROOT, "stl")
        out = os.path.join(d, f"{NAME}_project.3mf")
        print(pack_project(glob.glob(os.path.join(d, f"{NAME}_r*c*.stl")), out, f"{NAME} wall art"), "tiles ->", out)
        sys.exit(0)
    if a.from_3mf:
        SOURCE = (a.from_3mf, a.part)
    OUT = a.out
    main()
