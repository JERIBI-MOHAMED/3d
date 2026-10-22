"""
African club trophy replica (silver ribbon loop + gold Africa ball) - Blender generator
(Blender 4.x / 5.x)

Usage
-----
In Blender : Scripting tab -> Open this file -> Run Script
Headless   : blender -b -P trophy_blender.py -- [out_dir]

Exports 6 printable parts (units = mm, assembled height = HEIGHT):
    trophy_base.stl         flared foot with a D-shaped spigot on top
    trophy_ring.stl         collar between foot and body (print in gold)
    trophy_body.stl         the ribbon loop; gold ribs (raised) / silver grooves
    trophy_ball.stl         one-piece ball with Africa map (needs supports)
    trophy_ball_top.stl     same ball split at the equator, no supports:
    trophy_ball_bottom.stl  glue the halves with 2 filament pins
and trophy_k2se.3mf, a coloured Creality Print project for the K2 SE (needs k2se_3mf.py).
The ball slides into the loop from the front and is locked by 2 pins
(1.75 mm filament) pushed through the arms into the ball.

Everything is parametric: edit the PARAMETERS block and run again.
Shapes are given in units of the ball diameter (D), measured on the reference photo.
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402 (must come after bpy when run as a module)
import numpy as np

# ----------------------------------------------------------------- PARAMETERS
HEIGHT = 210.0           # assembled height (mm); everything scales with it (ball ~ HEIGHT / 4)
GAP = 0.3                # ball <-> arms clearance (mm)

# body (loop) outline, x = half width, z = height above the ring, both in D
OUTER = [(0.215, -0.3), (0.215, 0.0), (0.235, 0.2), (0.28, 0.45), (0.37, 0.72),
         (0.50, 0.97), (0.63, 1.22), (0.69, 1.47), (0.715, 1.77), (0.70, 1.97),
         (0.665, 2.15), (0.625, 2.33), (0.585, 2.48)]
HOLE = [(0.0, 0.85), (0.08, 0.97), (0.19, 1.17), (0.29, 1.37), (0.39, 1.57),
        (0.445, 1.77), (0.485, 1.97)]  # V point -> where the hole meets the ball circle
BALL_Z = 2.36            # ball centre height (D)
CRADLE = (-15.0, 25.0)   # arms hug the ball from this angle to the tip (deg from equator)
THICK = [(0.0, 0.215), (0.5, 0.2), (1.0, 0.19), (1.5, 0.16), (2.0, 0.13), (2.6, 0.11)]
EDGE_R = [(0.0, 0.215), (0.45, 0.12), (1.2, 0.12), (1.6, 0.08)]  # rounded edges (z, r) D

RIBS = [0.17, 0.12, 0.17, 0.12, 0.17, 0.12, 0.13]  # stripe widths: gold, silver, gold...
RIB_V = 0.28             # width of the striped ribbon along the V (D)
RIB_SPREAD = (1.15, 1.3)  # above this height band (D) the ribbon fills the whole arm
RIB_STEP = 0.8           # silver stripes are recessed by this (mm)
RIB_EDGE = 0.35          # half width of the stripe step (mm)

BASE_H = 1.04            # foot height (D)
BASE_R = 0.58            # foot bottom radius (D)
NECK_R = 0.215           # neck radius at the ring (D)
FLARE = 1.35             # >1 = more concave foot
PLINTH_H = 3.0           # vertical band at the bottom of the foot (mm)
PLINTH_STEP = 0.8        # small step above it (mm)
RING_H = 4.2             # collar height (mm)
RING_PROUD = 1.0         # collar sticks out of the neck by (mm)

SPIGOT_R = 6.5           # foot -> body spigot radius (mm)
SPIGOT_FLAT = 3.6        # D flat (keys the body to the front) at y = this (mm)
SOCKET_D = 15.0          # spigot length inside the body (mm)
CLR = 0.3                # sliding clearance (mm)

PIN_D = 1.95             # pin hole for 1.75 mm filament (mm)
PIN_IN_BALL = 8.0        # pin depth in the ball (mm)
ALIGN_R = 0.25           # alignment pins of the split ball, at y = +-ALIGN_R*D
ALIGN_DEPTH = 4.0        # per half (mm)

SEAM_W = 1.2             # soccer-ball seam groove width (mm)
SEAM_DEPTH = 0.6         # seam depth (mm)
AFRICA_H = 1.2           # Africa relief height (mm)
AFRICA_SCALE = 1.2       # Africa map size (1 = true size on a globe the size of the ball)
AFRICA_TILT = 50.0       # Africa centre elevation above the ball equator, facing front (deg)
BALL_SUBDIV = 8          # icosphere subdivisions (8 -> 0.35 mm triangles at D = 65)

# Creality K2 SE project (stl/trophy_k2se.3mf): filament 1 silver, filament 2 gold
K2SE_COLOURS = [("Silver silk", "#C4C7CC"), ("Gold silk", "#D9A93A")]
K2SE_FLUSH = [0, 280, 320, 0]           # purge volumes silver->gold, gold->silver (mm3)
K2SE_PROCESS = {                        # changes to "0.16mm Standard @Creality K2 SE"
    "wall_loops": "3",                  # strong thin arms around the pin holes
    "wall_generator": "arachne",        # clean thin ribs and arm tips
    "sparse_infill_pattern": "gyroid",
    "outer_wall_speed": "120",          # silk filament: slower outer wall = better shine
    "seam_position": "back",            # seam on the back of the trophy
    "xy_hole_compensation": "0.1",      # pin / socket / ring holes fit first time
    "flush_into_infill": "1",           # two-colour body: purge into its infill, less waste
}
K2SE_BODY = {"brim_type": "outer_only", "brim_width": "10"}  # tall part on a small neck
K2SE_BALL = {"layer_height": "0.12"}    # smoother dome

VOXEL = 0.3              # body sampling step (mm)
BODY_DECIMATE = 0.09     # keep this ratio of the body triangles (1 = no decimation)
BALL_DECIMATE = 0.35

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl") \
    if "__file__" in globals() else os.path.expanduser("~/trophy_stl")
if "--" in sys.argv:
    extra = sys.argv[sys.argv.index("--") + 1:]
    if extra:
        OUT_DIR = extra[0]
# ----------------------------------------------------------------------------

D = (HEIGHT - RING_H - AFRICA_H) / (BASE_H + BALL_Z + 0.5)   # ball diameter (mm)
R_BALL = D / 2
R_HOLE = R_BALL + GAP
ZB = BALL_Z * D

# simplified Africa coastline (lon, lat), clockwise from Tangier
AFRICA = [
    (-5.9, 35.8), (-2.0, 35.1), (3.0, 36.8), (10.2, 37.2), (11.0, 35.0), (10.1, 33.9),
    (11.5, 33.1), (15.2, 32.3), (19.0, 30.3), (20.1, 32.1), (23.0, 32.6), (25.1, 31.6),
    (29.9, 31.2), (32.3, 31.3), (32.6, 29.9), (33.9, 27.2), (35.5, 23.9), (37.2, 21.0),
    (38.5, 18.0), (39.5, 15.6), (41.7, 13.3), (43.4, 12.6), (44.0, 10.4), (51.3, 11.8),
    (51.0, 10.4), (48.0, 5.0), (45.3, 2.0), (42.6, -0.5), (39.7, -4.0), (39.2, -6.8),
    (39.5, -10.0), (40.5, -10.5), (40.6, -15.0), (37.0, -17.5), (34.8, -19.8),
    (35.4, -23.9), (32.9, -25.9), (32.4, -28.6), (30.9, -29.9), (27.9, -33.0),
    (25.6, -33.9), (20.0, -34.8), (18.4, -34.3), (18.0, -32.0), (16.5, -28.6),
    (15.2, -27.0), (14.5, -22.9), (11.8, -17.3), (13.5, -12.3), (13.2, -8.8),
    (12.2, -6.0), (11.8, -4.8), (9.0, -0.7), (9.5, 2.0), (9.7, 4.0), (8.5, 4.5),
    (6.0, 4.3), (3.4, 6.4), (1.2, 6.1), (-2.0, 4.8), (-4.0, 5.2), (-7.5, 4.4),
    (-10.8, 6.3), (-13.2, 8.5), (-16.5, 12.3), (-17.5, 14.7), (-16.5, 19.5),
    (-17.0, 21.0), (-14.5, 26.1), (-13.0, 27.7), (-9.6, 30.4), (-9.8, 31.5),
    (-7.6, 33.6), (-6.8, 34.1)]
MADAGASCAR = [(49.3, -12.0), (50.5, -15.5), (49.8, -17.0), (48.0, -22.0), (47.0, -25.1),
              (44.0, -25.0), (43.3, -22.0), (44.4, -19.5), (44.0, -17.0), (46.3, -15.7),
              (47.9, -13.6)]
AFRICA_CENTRE = (17.0, 2.0)  # (lon, lat) put at AFRICA_TILT on the front of the ball


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def make_object(name, verts, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(np.asarray(verts, dtype=float).tolist(), [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.faces.ensure_lookup_table()
    degenerate = [f for f in bm.faces if len(set(f.verts)) < 3 or f.calc_area() < 1e-9]
    bmesh.ops.delete(bm, geom=degenerate, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def lathe(name, profile, n_col=256):
    """Revolve a closed (r, z) polyline (axis points at r = 0) around Z."""
    th = np.arange(n_col) * 2 * math.pi / n_col
    verts = [(r * math.cos(t), r * math.sin(t), z) for r, z in profile for t in th]
    faces = []
    for i in range(len(profile) - 1):
        a, b = i * n_col, (i + 1) * n_col
        for j in range(n_col):
            j1 = (j + 1) % n_col
            faces.append([a + j, a + j1, b + j1, b + j])
    return make_object(name, verts, faces)


def cylinder(name, p0, p1, radius, n=32):
    """Closed cylinder between points p0 and p1 (cut tool)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = (p1 - p0) / np.linalg.norm(p1 - p0)
    u = np.cross(ax, [0, 0, 1] if abs(ax[2]) < 0.9 else [1, 0, 0])
    u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    ring = [radius * (math.cos(t) * u + math.sin(t) * v)
            for t in (np.arange(n) + 0.5) * 2 * math.pi / n]
    verts = [p0 + c for c in ring] + [p1 + c for c in ring]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[j, (j + 1) % n, n + (j + 1) % n, n + j] for j in range(n)]
    return make_object(name, verts, faces)


def box(name, lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    verts = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4],
             [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return make_object(name, verts, faces)


def join(name, objs):
    """Merge cut tools into one object (one boolean instead of many)."""
    verts, faces = [], []
    for o in objs:
        base = len(verts)
        verts += [tuple(v.co) for v in o.data.vertices]
        faces += [[base + i for i in p.vertices] for p in o.data.polygons]
        bpy.data.objects.remove(o, do_unlink=True)
    return make_object(name, verts, faces)


def apply_modifier(obj, mod):
    """Bake a modifier into the mesh without bpy.ops (works in any UI context)."""
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    new_mesh = bpy.data.meshes.new_from_object(evaluated)
    old_mesh = obj.data
    obj.modifiers.remove(mod)
    obj.data = new_mesh
    bpy.data.meshes.remove(old_mesh)


def boolean(target, tool, op, keep_tool=False):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.object = tool
    mod.solver = "EXACT"
    apply_modifier(target, mod)
    if not keep_tool:
        bpy.data.objects.remove(tool, do_unlink=True)


def decimate(obj, ratio):
    if ratio < 1:
        mod = obj.modifiers.new("decimate", "DECIMATE")
        mod.ratio = ratio
        apply_modifier(obj, mod)


# ----------------------------------------------------------------- 2D HELPERS
def catmull_rom(pts, n=16):
    """Smooth curve through all points (centripetal ends duplicated)."""
    p = np.asarray(pts, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (3 * p1 - p0 - 3 * p2 + p3) * t3))
    out.append(p[-2])
    return np.array(out)


def arc2d(c, r, a0, a1, n):
    a = np.radians(np.linspace(a0, a1, n))
    return np.column_stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)])


def seg_dist(p, a, b, chunk=8000):
    """Distance from points p (N,2) to segments a->b (M,2)."""
    ab = b - a
    ll = np.maximum((ab ** 2).sum(1), 1e-12)
    out = np.empty(len(p))
    for s in range(0, len(p), chunk):
        q = p[s:s + chunk, None, :]
        t = np.clip(((q - a) * ab).sum(2) / ll, 0, 1)
        d = q - (a + t[..., None] * ab)
        out[s:s + chunk] = np.sqrt((d ** 2).sum(2).min(1))
    return out


def inside(p, poly, chunk=8000):
    """Crossing-number point-in-polygon test, p (N,2), poly (M,2) closed implicitly."""
    a, b = poly, np.roll(poly, -1, axis=0)
    out = np.empty(len(p), bool)
    for s in range(0, len(p), chunk):
        x, z = p[s:s + chunk, 0:1], p[s:s + chunk, 1:2]
        cross = (a[:, 1] > z) != (b[:, 1] > z)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = a[:, 0] + (z - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1])
        out[s:s + chunk] = ((cross & (x < xi)).sum(1) % 2) == 1
    return out


# ----------------------------------------------------------------- BODY OUTLINE
def body_outline():
    """Closed outline of the loop in the XZ plane + the rib guide segments (mm)."""
    a0, a1 = CRADLE
    c = (0.0, ZB)
    hole = catmull_rom([(x * D, z * D) for x, z in HOLE] + [tuple(arc2d(c, R_HOLE, a0, a0, 1)[0])])
    inner = np.vstack([hole, arc2d(c, R_HOLE, a0, a1, 48)[1:]])       # V point -> tip
    outer = catmull_rom([(x * D, z * D) for x, z in OUTER])          # neck -> tip
    t_i, t_o = inner[-1], outer[-1]
    mid, rad = (t_i + t_o) / 2, np.linalg.norm(t_i - t_o) / 2
    n = np.array([-(t_i - t_o)[1], (t_i - t_o)[0]]) / (2 * rad)
    if np.dot(n, outer[-1] - outer[-4]) < 0:
        n = -n
    th = np.linspace(0, math.pi, 24)[1:-1]
    cap = mid + np.outer(np.cos(th), t_o - mid) + np.outer(np.sin(th) * rad, n)
    right = np.vstack([outer, cap, inner[::-1]])                      # neck -> tip -> V
    left = (right * [-1, 1])[::-1][1:]                                # V -> tip -> neck
    poly = np.vstack([right, left])

    # rib guides (right half, used with |x|): the opening edge with its lower leg
    # extended below the V, so the stripes fold into nested chevrons under the opening
    leg = (inner[1] - inner[0]) / np.linalg.norm(inner[1] - inner[0])
    guide = np.vstack([inner[0] - 0.8 * D * leg, inner])
    edge = np.vstack([outer, cap])
    return poly, (guide[:-1], guide[1:]), (edge[:-1], edge[1:])


def thickness(z):
    zs, hs = zip(*THICK)
    return np.interp(z, np.array(zs) * D, np.array(hs) * D)


def edge_radius(z):
    zs, rs = zip(*EDGE_R)
    return np.interp(z, np.array(zs) * D, np.array(rs) * D)


def ribbon(p, guide, edge):
    """Stripe coordinate u (0 at the opening, 1 at the ribbon edge) and the ribbon width (mm).

    On the arms the ribbon fills the arm (opening -> outer edge); below it narrows to
    RIB_V at the V, where the stripes fold into chevrons on the stem."""
    p = np.column_stack([np.abs(p[:, 0]), p[:, 1]])     # symmetric: work on the right half
    d_in, d_out = seg_dist(p, *guide), seg_dist(p, *edge)
    w_v = RIB_V * D
    t = smoothstep((p[:, 1] - RIB_SPREAD[0] * D) / ((RIB_SPREAD[1] - RIB_SPREAD[0]) * D))
    w = w_v + t * np.maximum(d_in + d_out - w_v, 0)
    return d_in / w, w


def gold_mask(u, w):
    """1 on the gold stripes, 0 on the silver ones."""
    e = RIB_EDGE / w                                     # step half width in u units
    g = np.zeros_like(u)
    edges = np.concatenate([[0], np.cumsum(RIBS) / sum(RIBS)])
    for k in range(0, len(RIBS), 2):
        lo = -1.0 if k == 0 else edges[k]
        hi = 2.0 if k == len(RIBS) - 1 else edges[k + 1]
        g += smoothstep((u - lo + e) / (2 * e)) - smoothstep((u - hi + e) / (2 * e))
    return g * (1 - smoothstep((u - 1 + e) / (2 * e)))


def rib_offset(p, guide, edge):
    """Silver stripes and the stem below the chevrons sit RIB_STEP lower than the gold ones."""
    u, w = ribbon(p, guide, edge)
    fade = smoothstep(p[:, 1] / (0.25 * D))              # keep the neck exactly round
    return -RIB_STEP * (1 - gold_mask(u, w)) * fade


# ----------------------------------------------------------------- MARCHING TETRAHEDRA
CORNERS = np.array([(i, j, k) for k in (0, 1) for j in (0, 1) for i in (0, 1)])
# 6 tetrahedra around the cell diagonal 0-7: every cell face is split the same way,
# so neighbouring cells always agree and the surface is closed and manifold
TETS = [(0, 1, 3, 7), (0, 2, 3, 7), (0, 2, 6, 7), (0, 4, 6, 7), (0, 4, 5, 7), (0, 1, 5, 7)]


def tet_cases():
    """For each inside-mask of a tetrahedron: triangles as triples of (corner, corner) edges."""
    table = {}
    for m in range(1, 15):
        ins = [c for c in range(4) if m >> c & 1]
        out = [c for c in range(4) if not m >> c & 1]
        if len(ins) == 1 or len(out) == 1:
            lone, rest = (ins[0], out) if len(ins) == 1 else (out[0], ins)
            table[m] = [[(lone, r) for r in rest]]
        else:
            (a, b), (c, d) = ins, out
            table[m] = [[(a, c), (a, d), (b, d)], [(a, c), (b, d), (b, c)]]
    return table


def marching_tets(f, origin, step):
    """Closed manifold triangle mesh of the zero level of the sampled field f (negative inside)."""
    f = np.where(f == 0, np.float32(1e-6), f)
    s = f < 0
    nx, ny, nz = s.shape
    sl = [s[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in CORNERS]
    any_in, all_in = sl[0].copy(), sl[0].copy()
    for c in sl[1:]:
        any_in |= c
        all_in &= c
    ci, cj, ck = np.nonzero(any_in & ~all_in)
    del sl, any_in, all_in
    flat = f.ravel()
    corner_id = [np.ravel_multi_index((ci + a, cj + b, ck + c), f.shape) for a, b, c in CORNERS]
    cases = tet_cases()
    tri_keys, tri_side = [], []
    for tet in TETS:
        g = np.column_stack([corner_id[c] for c in tet])            # (n, 4) grid indices
        ins = flat[g] < 0
        mask = (ins * [1, 2, 4, 8]).sum(1)
        for m, tris in cases.items():
            sel = g[mask == m]
            if not len(sel):
                continue
            ins_m = np.array([m >> c & 1 for c in range(4)], bool)
            side = np.column_stack([sel[:, ~ins_m][:, 0], sel[:, ins_m][:, 0]])  # out, in corner
            for tri in tris:
                keys = [np.sort(sel[:, list(e)], axis=1) for e in tri]
                tri_keys.append(np.stack(keys, axis=1))               # (n, 3, 2)
                tri_side.append(side)
    keys = np.vstack(tri_keys)                                        # (T, 3, 2)
    side = np.vstack(tri_side)                                        # (T, 2) outside, inside
    pair = keys[..., 0].astype(np.int64) * flat.size + keys[..., 1]
    uniq, tri = np.unique(pair.ravel(), return_inverse=True)
    tri = tri.reshape(-1, 3)
    a, b = uniq // flat.size, uniq % flat.size
    fa, fb = flat[a].astype(float), flat[b].astype(float)
    t = np.clip(fa / (fa - fb), 1e-3, 1 - 1e-3)
    pa = np.column_stack(np.unravel_index(a, f.shape))
    pb = np.column_stack(np.unravel_index(b, f.shape))
    verts = (pa + t[:, None] * (pb - pa)) * step + origin
    # orient: the normal must point from the inside corner towards the outside one
    v0, v1, v2 = verts[tri[:, 0]], verts[tri[:, 1]], verts[tri[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    out_dir = np.column_stack(np.unravel_index(side[:, 0], f.shape)) \
        - np.column_stack(np.unravel_index(side[:, 1], f.shape))
    flip = (n * out_dir).sum(1) < 0
    tri[flip] = tri[flip][:, ::-1]
    return verts, tri


# ----------------------------------------------------------------- BODY
def body_field():
    poly, guide, edge = body_outline()
    v = VOXEL
    xmax = np.abs(poly[:, 0]).max() + 3 * v
    hmax = thickness(0.0) + 3 * v
    ztop = poly[:, 1].max() + 3 * v
    xs = np.arange(-xmax, xmax + v, v)
    ys = np.arange(-hmax, hmax + v, v)
    zs = np.arange(-3 * v, ztop + v, v)
    gx, gz = np.meshgrid(xs, zs, indexing="ij")
    p = np.column_stack([gx.ravel(), gz.ravel()])

    r2 = seg_dist(p, poly, np.roll(poly, -1, axis=0))
    r2[inside(p, poly)] *= -1                            # signed distance to the outline
    shape2 = (len(xs), 1, len(zs))
    r2 = r2.reshape(shape2).astype(np.float32)
    h = (thickness(gz).ravel() + rib_offset(p, guide, edge)).reshape(shape2).astype(np.float32)
    rr = edge_radius(zs).astype(np.float32)[None, None, :]
    ay = np.abs(ys).astype(np.float32)[None, :, None]

    # rounded extrusion of the 2D outline: flat faces, edges rounded by rr
    qx = r2 + rr
    qy = ay - h + rr
    f = np.minimum(np.maximum(qx, qy), 0) \
        + np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) - rr
    del qx, qy
    z3 = zs.astype(np.float32)[None, None, :]
    x3 = xs.astype(np.float32)[:, None, None]
    y3 = ys.astype(np.float32)[None, :, None]
    f = np.maximum(f, -z3)                               # flat bottom on the ring

    # D-shaped socket for the foot spigot, 45 deg cone roof (prints without support)
    rs = SPIGOT_R + CLR
    rad = np.sqrt(x3 ** 2 + y3 ** 2)
    sock = np.maximum(np.maximum(rad - rs, y3 - (SPIGOT_FLAT + CLR)),
                      z3 - (SOCKET_D + CLR) - np.maximum(rs - rad, 0))
    f = np.maximum(f, -sock)
    # pin holes along X at the ball centre height, through both arms
    pin = np.sqrt(y3 ** 2 + (z3 - ZB) ** 2) - PIN_D / 2 + 0 * x3
    f = np.maximum(f, -pin)
    return f, np.array([xs[0], ys[0], zs[0]]), guide, edge


def build_body():
    f, origin, guide, edge = body_field()
    verts, tris = marching_tets(f, origin, VOXEL)
    del f
    body = make_object("trophy_body", verts, tris.tolist())
    decimate(body, BODY_DECIMATE)
    # remember which part is a gold stripe (for the preview material)
    co = np.array([v.co[:] for v in body.data.vertices])
    gold = gold_mask(*ribbon(co[:, [0, 2]], guide, edge))
    attr = body.data.attributes.new("gold", "FLOAT", "POINT")
    attr.data.foreach_set("value", gold.astype(np.float32))
    return body


# ----------------------------------------------------------------- BALL
def icosahedron():
    t = (1 + 5 ** 0.5) / 2
    v = np.array([(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
                  (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)], float)
    v /= np.linalg.norm(v, axis=1)[:, None]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4),
         (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8),
         (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    return v, f


def soccer_seams():
    """Edges of a truncated icosahedron projected on the unit sphere -> (U, V) arc ends."""
    v, faces = icosahedron()
    seg = {}
    for a, b, c in faces:
        p = {}
        for x, y in ((a, b), (b, c), (c, a)):
            p[(x, y)] = v[x] + (v[y] - v[x]) / 3          # third point near x
            p[(y, x)] = v[y] + (v[x] - v[y]) / 3
        for x, y, z in ((a, b, c), (b, c, a), (c, a, b)):
            seg[frozenset([(x, y), (y, x)])] = (p[(x, y)], p[(y, x)])      # hex-hex seam
            seg[frozenset([(x, y), (x, z)])] = (p[(x, y)], p[(x, z)])      # pentagon seam
    u = np.array([s[0] for s in seg.values()])
    w = np.array([s[1] for s in seg.values()])
    return u / np.linalg.norm(u, axis=1)[:, None], w / np.linalg.norm(w, axis=1)[:, None]


def arc_dist(p, u, w, chunk=6000):
    """Angular distance from unit vectors p (N,3) to great-circle arcs u->w (M,3)."""
    n = np.cross(u, w)
    n /= np.linalg.norm(n, axis=1)[:, None]
    nu, wn = np.cross(n, u), np.cross(w, n)
    out = np.empty(len(p))
    for s in range(0, len(p), chunk):
        q = p[s:s + chunk]
        on = ((q @ nu.T) >= 0) & ((q @ wn.T) >= 0)
        d_line = np.arcsin(np.clip(np.abs(q @ n.T), 0, 1))
        d_end = np.arccos(np.clip(np.maximum(q @ u.T, q @ w.T), -1, 1))
        out[s:s + chunk] = np.where(on, d_line, d_end).min(1)
    return out


def africa_frame():
    """Rotation taking ball directions to Earth (lon/lat) directions."""
    lon, lat = np.radians(AFRICA_CENTRE)
    e_c = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    e_east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    e_north = np.cross(e_c, e_east)
    el = math.radians(AFRICA_TILT)
    t_c = np.array([0.0, -math.cos(el), math.sin(el)])  # front (-Y) and up
    t_east = np.array([1.0, 0.0, 0.0])
    t_north = np.cross(t_c, t_east)
    return np.column_stack([e_c, e_east, e_north]) @ np.vstack([t_c, t_east, t_north])


def lonlat_to_ball(ll):
    lon, lat = np.radians(np.asarray(ll, float)).T
    e = np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    return e @ africa_frame()                       # row vectors: earth -> ball


def africa_relief(p):
    """0..1 mask of the raised Africa map for unit directions p."""
    m = np.zeros(len(p))
    near = np.nonzero(p @ lonlat_to_ball([AFRICA_CENTRE])[0] > math.cos(math.radians(55)))[0]
    q = p[near]
    e = q @ africa_frame().T                        # ball -> earth
    ll = np.degrees(np.column_stack([np.arctan2(e[:, 1], e[:, 0]),
                                     np.arcsin(np.clip(e[:, 2], -1, 1))]))
    for shape in (AFRICA, MADAGASCAR):
        poly = AFRICA_CENTRE + (np.array(shape, float) - AFRICA_CENTRE) * AFRICA_SCALE
        b = lonlat_to_ball(poly)
        d = arc_dist(q, b, np.roll(b, -1, axis=0)) * R_BALL
        sd = np.where(inside(ll, poly), d, -d)      # mm, positive inside
        m[near] = np.maximum(m[near], smoothstep((sd + 0.4) / 0.8))
    return m


def build_ball():
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=BALL_SUBDIV, radius=1.0)
    p = np.array([v.co[:] for v in bm.verts])
    p /= np.linalg.norm(p, axis=1)[:, None]
    a, b = math.radians(7.3), math.radians(11.9)      # no vertex exactly on the split plane
    p = p @ np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]) \
        @ np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    u, w = soccer_seams()
    seam = arc_dist(p, u, w) * R_BALL                                   # mm to nearest seam
    groove = SEAM_DEPTH * np.clip(1 - (seam / (SEAM_W / 2)) ** 2, 0, 1)
    africa = africa_relief(p)
    r = R_BALL - groove * (1 - africa) + AFRICA_H * africa
    for v, co in zip(bm.verts, p * r[:, None]):
        v.co = co
    mesh = bpy.data.meshes.new("trophy_ball")
    bm.to_mesh(mesh)
    bm.free()
    ball = bpy.data.objects.new("trophy_ball", mesh)
    bpy.context.scene.collection.objects.link(ball)
    decimate(ball, BALL_DECIMATE)

    ext = R_BALL + AFRICA_H + 1
    tools = [cylinder("pin", (s * (R_BALL - PIN_IN_BALL), 0, 0), (s * ext, 0, 0), PIN_D / 2)
             for s in (1, -1)]
    boolean(ball, join("pins", tools), "DIFFERENCE")
    return ball


def split_ball(ball):
    """Two hemispheres (flat face down on the bed) with holes for 2 alignment pins."""
    halves = []
    big = R_BALL + AFRICA_H + 2
    for name, z0, z1 in (("trophy_ball_top", 0, big), ("trophy_ball_bottom", -big, 0)):
        half = ball.copy()
        half.data = ball.data.copy()
        half.name = half.data.name = name
        bpy.context.scene.collection.objects.link(half)
        boolean(half, box("cut", (-big, -big, z0), (big, big, z1)), "INTERSECT")
        holes = [cylinder("align", (0, s * ALIGN_R * D, -ALIGN_DEPTH - 0.3),
                          (0, s * ALIGN_R * D, ALIGN_DEPTH + 0.3), PIN_D / 2) for s in (1, -1)]
        boolean(half, join("align", holes), "DIFFERENCE")
        halves.append(half)
    return halves


# ----------------------------------------------------------------- FOOT + RING
def build_base():
    h, r0, rn = BASE_H * D, BASE_R * D, NECK_R * D
    prof = [(0.0, 0.0), (r0, 0.0), (r0, PLINTH_H)]
    for t in np.linspace(0, 1, 60):
        prof.append((rn + (r0 - PLINTH_STEP - rn) * (1 - t) ** FLARE,
                     PLINTH_H + t * (h - PLINTH_H)))
    top = h + RING_H + SOCKET_D
    prof += [(SPIGOT_R, h), (SPIGOT_R, top - 0.8), (SPIGOT_R - 0.8, top), (0.0, top)]
    base = lathe("trophy_base", prof)
    boolean(base, box("flat", (-10, SPIGOT_FLAT, h + 0.3), (10, 10, top + 1)), "DIFFERENCE")
    return base


def build_ring():
    ri, ro, ch = SPIGOT_R + CLR, NECK_R * D + RING_PROUD, 0.6
    prof = [(ri, 0.0), (ro - ch, 0.0), (ro, ch), (ro, RING_H - ch), (ro - ch, RING_H),
            (ri, RING_H), (ri, 0.0)]
    return lathe("trophy_ring", prof)


# ----------------------------------------------------------------- MAIN
def export_stl(obj, path):
    for other in bpy.context.scene.objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              ascii_format=False)
    else:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)


def metal(name, color, rough):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.metallic, mat.roughness = 1.0, rough
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def body_material(gold, silver):
    """Silver body with gold stripes, driven by the 'gold' point attribute."""
    mat = bpy.data.materials.new("body")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.2
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "gold"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*silver, 1)
    mix.inputs["B"].default_value = (*gold, 1)
    nt.links.new(attr.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def assemble(base, ring, body, ball, halves=()):
    """Stack the parts like the real trophy (split halves hidden), coloured gold / silver."""
    gold, silver = (1.0, 0.72, 0.32), (0.85, 0.86, 0.88)
    ring.location.z = BASE_H * D
    body.location.z = BASE_H * D + RING_H
    ball.location.z = BASE_H * D + RING_H + ZB
    for o in halves:
        o.hide_set(True)
        o.hide_render = True
    parts = (base, ring, body, ball, *halves)
    for o in parts:
        o.data.materials.clear()                # booleans leave an empty slot behind
    base.data.materials.append(metal("silver", silver, 0.18))
    for o in (ring, ball, *halves):
        o.data.materials.append(bpy.data.materials.get("gold") or metal("gold", gold, 0.22))
    body.data.materials.append(body_material(gold, silver))
    for o in parts:
        for poly in o.data.polygons:
            poly.use_smooth = o.name != "trophy_ring"


def mesh_arrays(obj, attr=None):
    """Triangles of an object (and a per-vertex float attribute) as numpy arrays."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.verts.index_update()
    verts = np.array([v.co[:] for v in bm.verts])
    tris = np.array([[v.index for v in f.verts] for f in bm.faces])
    vals = None
    if attr:
        layer = bm.verts.layers.float.get(attr)
        vals = np.array([v[layer] for v in bm.verts])
    bm.free()
    return verts, tris, vals


def export_k2se(base, ring, body, top, bottom):
    """Creality Print project for the K2 SE: 3 plates, colours, two-colour body."""
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
    sys.path.insert(0, here)
    try:
        import k2se_3mf
    except ImportError:
        print("k2se_3mf.py not found next to this script: no K2 SE project written")
        return
    z_ring, z_body = BASE_H * D, BASE_H * D + RING_H

    def part(obj, extruder, xy, settings=None, flip=False, z=0.0, paint=False):
        v, t, g = mesh_arrays(obj, "gold" if paint else None)
        if flip:                                       # flat face down on the bed
            v = v * [1, -1, -1]
        asm = np.eye(4)
        asm[2, 3] = z
        return dict(name=obj.name, verts=v, tris=t, extruder=extruder, xy=xy,
                    settings=settings or {}, assembly=asm,
                    paint=np.where(g[t].mean(1) > 0.5, "8", "") if paint else None)

    imgs = [os.path.join(here, "images", n + ".png")
            for n in ("trophy_ball", "trophy_front", "trophy_three_quarter")]
    plates = [
        ("Gold - ball halves + ring", [part(top, 2, (55, 107), K2SE_BALL, z=z_body + ZB),
                                       part(bottom, 2, (122, 107), K2SE_BALL, flip=True,
                                            z=z_body + ZB),
                                       part(ring, 2, (182, 107), z=z_ring)]),
        ("Silver - base + body (paint the stripes)", [part(base, 1, (60, 107)),
                                                      part(body, 1, (150, 107), K2SE_BODY,
                                                           z=z_body)]),
        ("Two-colour body - CFS gold stripes", [part(body, 1, (90, 107), K2SE_BODY, z=z_body,
                                                     paint=True)]),
    ]
    path = os.path.join(OUT_DIR, "trophy_k2se.3mf")
    k2se_3mf.write_project(path, plates, K2SE_COLOURS, K2SE_PROCESS, K2SE_FLUSH,
                           "African club trophy", [i for i in imgs if os.path.exists(i)])
    print("Creality K2 SE project:", path)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    base, ring, body, ball = build_base(), build_ring(), build_body(), build_ball()
    halves = split_ball(ball)
    parts = (base, ring, body, ball, *halves)
    for o in parts:
        export_stl(o, os.path.join(OUT_DIR, o.name + ".stl"))
    print("Exported to", OUT_DIR)
    for o in parts:
        d = o.dimensions
        print(f"{o.name}: {d.x:.1f} x {d.y:.1f} x {d.z:.1f} mm, {len(o.data.polygons)} faces")
    export_k2se(base, ring, body, *halves)
    assemble(base, ring, body, ball, halves)


main()
