"""
BMW M5 CS (F90) 1:64 snap-together kit - generator
==================================================

Same concept as the BMW E46 GTR kit by RolfBertz3D used as reference:
one flat plate, no supports, no glue.

    body     solid shell printed upright, pocket underneath for the chassis
    chassis  floor pan that clicks into the body pocket, two snap-in axle channels
    axles    2 x round axles printed lying on the bed (flat bottom)
    wheels   4 x Y-spoke wheels printed face up, tyre + rim as separate volumes
    frame    sprue frame with break-off gates and an "M5 CS" name tag

Multi-colour (optional, separate volumes inside the body object):
    1 body paint (Frozen Brands Hatch Grey)   2 black (glass, carbon roof, grilles, tyres)
    3 gold bronze (wheels, kidney surround)   4 red (tail lights)   5 white (headlights)
A single-colour print just ignores the extra volumes (all parts default to extruder 1).

Usage
-----
    pip install numpy scipy scikit-image trimesh manifold3d matplotlib fast_simplification
    python m5cs_generator.py [out_dir]

Outputs (mm): BMW_M5_CS_F90.3mf (whole plate, multi-volume) + one STL per part in stl/.
Car frame used while modelling: x forward, y left, z up, ground at z = 0.
"""
import math
import os
import sys
import zipfile

import numpy as np
import trimesh
import manifold3d as m3d
from scipy.interpolate import PchipInterpolator
from skimage import measure

# ----------------------------------------------------------------- PARAMETERS
SCALE = 64.0                  # 1:64, real F90 M5: L 4983, W 1903, H 1469, WB 2982 (mm)
LENGTH = 4983 / SCALE         # 77.9
HALF_W = 1903 / SCALE / 2     # 14.87
HEIGHT = 1469 / SCALE         # 22.95
WHEELBASE = 2982 / SCALE      # 46.6
X_FRONT = LENGTH / 2          # nose
X_FA = X_FRONT - 930 / SCALE  # front axle (930 mm front overhang)
X_RA = X_FA - WHEELBASE       # rear axle

TYRE_R = 5.5                  # 275/35 R20 -> ~700 mm
TYRE_W = 4.2
RIM_R = 3.95                  # 20 in rim
AXLE_Z = TYRE_R               # axle height above ground
WHEEL_OUT_Y = HALF_W - 0.25   # outer wheel face (nearly flush with the fender)
AXLE_D = 2.0                  # axle diameter
AXLE_FLAT = 0.1               # flat on the axle so it lies on the bed
HUB_HOLE_DEPTH = 2.6
PRESS_FIT = 0.05              # wheel hole = AXLE_D - PRESS_FIT (wheel is pressed on, axle turns)
AXLE_CLEAR = 0.25             # axle channel clearance (diameter)
SNAP_MOUTH = 1.55             # axle channel mouth width (axle clicks in)

BODY_Z0 = 2.0                 # underside of the body / chassis (ground clearance)
POCKET_HW = 10.25             # body pocket half width (wheels start just outside)
POCKET_Z = 4.6                # pocket ceiling (chassis plate top + clearance)
POCKET_X = 33.5               # pocket half length
CHASSIS_CLEAR = 0.2           # chassis to pocket clearance per side
RIDGE = 0.22                  # snap ridge height on the chassis sides

VOXEL = 0.12                  # body sampling (mm); 0.15 is faster for previews
SKIN = 0.6                    # depth of the colour volumes
SIMPLIFY_TOL = 0.006          # body mesh simplification tolerance (mm), keeps it manifold

FRAME_BAR = 1.4               # sprue frame bar width
FRAME_H = 1.2                 # sprue frame bar height

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.dirname(os.path.abspath(__file__))
PREVIEW = "--preview" in sys.argv
# ----------------------------------------------------------------------------

if PREVIEW:
    VOXEL = 0.2


def pchip(pts):
    p = np.array(sorted(pts), float)
    return PchipInterpolator(p[:, 0], p[:, 1], extrapolate=True)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ body shape
# Side-view profiles, sampled from F90 LCI side elevation scaled to 1:64.
BELT = pchip([(X_FRONT, 10.9), (37.0, 11.6), (30, 12.5), (20, 13.4), (11, 14.0), (0, 14.3),
              (-15, 14.4), (-27, 14.8), (-33, 15.15), (-37.2, 15.45), (-38.6, 15.75), (-39.5, 15.6)])
ROOF = pchip([(15, 13.7), (13, 14.2), (8, 16.6), (3, 19.2), (-1, 21.0), (-4, 22.1), (-8, 22.8),
              (-11, 22.95), (-14, 22.8), (-17, 22.2), (-20, 20.6), (-23.5, 18.2), (-27.5, 15.6), (-30, 15.0)])
X_WS, X_BL = 13.0, -27.5      # windshield base, back-light base


def x_front(z):
    """Front face of the car (x of the nose at height z)."""
    lo = 0.9 * ((6.5 - z) / 4.8).clip(0) ** 2
    hi = 1.3 * ((z - 7.5) / 3.6).clip(0) ** 2
    return X_FRONT - lo - hi


def x_rear(z):
    lo = 0.7 * ((4.5 - z) / 2.5).clip(0) ** 1.5
    mid = 0.35 * sstep(8, 13, z) * (1 - sstep(14.2, 15.4, z))  # slight tuck below the ducktail
    return -LENGTH / 2 + 0.3 + lo + mid


def side_w(z):
    """Half width of the lower body vs height (tuck under, shoulder)."""
    lo = 0.8 * ((8.0 - z) / 6.0).clip(0) ** 2
    hi = 1.0 * ((z - 10.0) / 4.4).clip(0) ** 2
    return HALF_W - lo - hi


def plan(x, x0, length, p=3.4):
    t = (np.abs(x - x0) / length).clip(0, 1)
    return (1 - t ** p).clip(0) ** (1 / p)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def body_field(X, Y, Z):
    """Implicit body: < 0 inside, roughly in mm. Built from per-surface distances joined smoothly."""
    ay = np.abs(Y)
    pf = np.where(X > 31.5, plan(X, 31.5, X_FRONT + 0.2 - 31.5 + 0.08 * (Z - 6).clip(0)), 1.0)
    pr = np.where(X < -32.5, plan(X, -32.5, LENGTH / 2 + 0.3 - 32.5), 1.0)
    w = side_w(Z) * pf * pr
    for xa in (X_FA, X_RA):  # wheel arch flares
        w = w + 0.28 * np.exp(-((X - xa) / 7.0) ** 2) * sstep(3, 7, Z) * (1 - sstep(10, 12.5, Z))
    crown = 0.55 * (1 - (ay / HALF_W) ** 2).clip(0) * sstep(10, 20, X)
    dome = 0.35 * np.exp(-(Y / 5.0) ** 2) * sstep(14, 22, X) * (1 - sstep(30, 36, X))  # CS power dome
    top = BELT(X) + crown + dome
    lower = smax(smax(ay - w, Z - top, 0.9), smax(X - x_front(Z), x_rear(Z) - X, 0.5), 0.6)
    lower = np.maximum(lower, BODY_Z0 - Z)

    roof = ROOF(np.clip(X, -30, 15))
    zb = BELT(X)
    s = ((Z - zb) / np.maximum(roof - zb, 1e-3)).clip(0, 1)
    wb, wt = 13.0, 10.4
    wg = wb - (wb - wt) * s ** 1.3
    gh = smax(ay - wg, Z - (roof - 1.2 * (ay / 10.5) ** 2), 0.8)
    gh = np.maximum(gh, np.maximum(X - 15, -30 - X))
    body = smin(lower, gh, 0.5)

    # side mirrors: wedge underside at 45 deg, prints without supports
    xm, zm = 10.6, 15.2
    mir = np.maximum.reduce([np.abs(X - xm) - (1.1 - 0.25 * (Z - zm).clip(0)), ay - 16.1, 12.0 - ay,
                             Z - (zm + 1.0), (zm - 1.0 - (16.1 - ay)) - Z])
    return np.maximum(smin(body, mir, 0.25), BODY_Z0 - Z)


def recess(F, region, depth):
    """Remove the outer `depth` mm of the body inside `region` (< 0 inside). Works on curved skin."""
    return np.minimum(F + depth, np.maximum(F, -region))


def box2(u, v, u0, u1, v0, v1, r=0.0):
    """Rounded rectangle distance in a 2D plane."""
    du = np.abs(u - (u0 + u1) / 2) - ((u1 - u0) / 2 - r)
    dv = np.abs(v - (v0 + v1) / 2) - ((v1 - v0) / 2 - r)
    return np.hypot(du.clip(0), dv.clip(0)) + np.minimum(np.maximum(du, dv), 0) - r


def groove(u, v, pts, w):
    """Distance to a polyline in a 2D plane minus half width (panel gaps)."""
    d = np.full(u.shape, 1e3, np.float32)
    for (u0, v0), (u1, v1) in zip(pts[:-1], pts[1:]):
        du, dv = u1 - u0, v1 - v0
        t = (((u - u0) * du + (v - v0) * dv) / (du * du + dv * dv)).clip(0, 1)
        d = np.minimum(d, np.hypot(u - u0 - t * du, v - v0 - t * dv))
    return d - w / 2


def poly2(u, v, pts):
    """Signed distance to a closed polygon (2D)."""
    from matplotlib.path import Path
    inside = Path(pts).contains_points(np.c_[u.ravel(), v.ravel()]).reshape(u.shape)
    d = groove(u, v, list(pts) + [pts[0]], 0.0)
    return np.where(inside, -d, d)


def body_detailed(X, Y, Z):
    """Full body field plus colour zone fields. Returns F, {zone: field}."""
    ay = np.abs(Y)
    F = F0 = body_field(X, Y, Z)
    xf = x_front(Z)
    xr = x_rear(Z)
    belt = BELT(X)
    roof = ROOF(np.clip(X, -30, 15))
    front = X - (xf - 1.6)          # > 0 near the nose
    rear = (xr + 1.6) - X           # > 0 near the tail
    side = ay - 11.0                # > 0 on the flanks

    # ---- front: kidneys with slats, gold surround, headlights, intakes
    kid = box2(ay, Z, 0.55, 6.1, 5.9, 10.2, 1.1)
    kid = np.maximum(kid, -front)
    F = recess(F, kid + 0.35, 0.55)
    slat = np.maximum.reduce([kid + 0.35, np.abs((ay % 0.62) - 0.31) - 0.11, -front])
    F = np.minimum(F, np.maximum(slat, F0 + 0.2))                   # slats 0.2 below the surface
    head = np.maximum(poly2(ay, Z, [(6.5, 9.4), (13.9, 10.1), (14.3, 10.8), (6.9, 10.9)]), -front + 0.8)
    F = recess(F, head, 0.2)
    intake_c = np.maximum(box2(ay, Z, -6.0, 6.0, 2.55, 4.9, 0.6), -front)
    intake_s = np.maximum(poly2(ay, Z, [(8.4, 2.5), (13.0, 2.6), (12.6, 6.6), (8.8, 6.0)]), -front + 0.4)
    F = recess(F, np.minimum(intake_c, intake_s), 0.6)
    gill = np.maximum(box2(X, Z, 18.6, 21.0, 9.3, 10.1, 0.35), -side)
    F = recess(F, gill, 0.3)
    vents = np.maximum(poly2(X, ay, [(26.6, 3.0), (31.2, 3.9), (30.6, 6.9), (26.2, 6.1)]), (belt - 1.0) - Z)  # CS hood vents
    F = recess(F, vents, 0.3)

    # ---- wheel wells (bridged arches) and the chassis pocket underneath
    for xa in (X_FA, X_RA):
        well = np.maximum(np.hypot(X - xa, Z - AXLE_Z) - (TYRE_R + 0.75), POCKET_HW - ay)
        F = np.maximum(F, -well)
    pocket = np.maximum.reduce([ay - POCKET_HW, np.abs(X) - POCKET_X, Z - POCKET_Z])
    for xa in (X_FA, X_RA):
        pocket = np.minimum(pocket, np.maximum.reduce([ay - POCKET_HW, np.abs(X - xa) - 3.2, Z - 7.4]))
    snap = np.maximum(np.hypot(ay - POCKET_HW, Z - (BODY_Z0 + 1.2)) - RIDGE - 0.05, np.abs(X - (X_FA + X_RA) / 2) - 12)
    F = np.maximum(F, -np.minimum(pocket, snap))

    # ---- side: door gaps, handles, sill line
    gap = groove(X, Z, [(13.6, belt.max()), (12.4, 11.5), (12.6, 3.0)], 0.18)
    gap = np.minimum(gap, groove(X, Z, [(-4.4, 16.0), (-4.6, 3.0)], 0.18))
    gap = np.minimum(gap, groove(X, Z, [(-19.6, 15.2), (-18.6, 12.0), (-16.4, 9.0), (-15.6, 6.0), (-15.8, 3.0)], 0.18))
    gap = np.minimum(gap, groove(X, Z, [(27.0, 14.9), (16.0, 14.4), (13.6, 14.3)], 0.18))      # hood / fender
    handle = np.minimum(box2(X, Z, 0.6, 2.4, 12.85, 13.35, 0.2), box2(X, Z, -12.6, -10.8, 12.95, 13.45, 0.2))
    F = recess(F, np.maximum(np.minimum(gap, handle), -side), 0.2)
    hood = groove(X, ay, [(14.0, 12.3), (37.0, 11.0)], 0.18)
    trunk = np.minimum.reduce([groove(X, Y, [(-28.3, -12.4), (-28.3, 12.4)], 0.18),
                               groove(X, Y, [(-28.3, -12.4), (-38.0, -12.4)], 0.18),
                               groove(X, Y, [(-28.3, 12.4), (-38.0, 12.4)], 0.18)])
    F = recess(F, np.maximum(np.minimum(hood, trunk), (belt - 1.2) - Z), 0.2)

    # ---- rear: tail lights, diffuser, quad exhausts, ducktail is in the BELT profile
    tail = np.maximum(poly2(ay, Z, [(7.4, 12.6), (14.6, 12.4), (14.6, 14.6), (7.0, 14.9)]), -rear + 0.3)
    tail_side = np.maximum(box2(X, Z, -40, -35.0, 12.4, 14.6, 0.3), -side - 2.5)
    tail = np.minimum(tail, tail_side)
    F = recess(F, tail, 0.2)
    diff = np.maximum(box2(ay, Z, -12.0, 12.0, 0, 5.0, 0.5), -rear)
    F = recess(F, diff, 0.35)
    fins = np.maximum.reduce([diff + 0.3, np.abs(ay - 3.0) - 0.15, -rear])
    F = np.minimum(F, np.maximum(fins, F0 + 0.1))
    pipes = np.full(X.shape, 1e3, np.float32)
    for yc in (7.9, 10.0):
        pipes = np.minimum(pipes, np.hypot(ay - yc, Z - 3.2) - 0.72)
    pipes = np.maximum(pipes, -rear)
    tips = np.maximum.reduce([pipes - 0.2, (xr - 0.25) - X, X + 34.0])
    F = np.minimum(F, tips)                                        # tips stick out 0.25
    F = np.maximum(F, -np.maximum(pipes, X - (xr + 1.2)))          # 1.2 deep bore

    # ---- colour zones (as fields, < 0 inside)
    gl_s = poly2(X, Z, [(12.4, 14.75), (-2.6, 21.0), (-6.0, 21.25), (-14.5, 21.1), (-19.0, 19.9),
                        (-23.6, 16.2), (-22.6, 15.25)]) * np.ones_like(Y)
    gl_s = np.maximum(np.maximum(gl_s, (belt + 0.5) - Z), 8.0 - ay)
    s_ = ((Z - belt) / np.maximum(roof - belt, 1e-3)).clip(0, 1)
    wg = 13.0 - 2.6 * s_ ** 1.3
    ws = np.maximum.reduce([ay - (wg - 0.9), (belt + 0.3) - Z, X - 13.2, -3.4 - X, Z - roof])
    bl = np.maximum.reduce([ay - (wg - 0.9), (belt + 0.8) - Z, X + 16.8, -27.0 - X])
    roofp = np.maximum.reduce([ay - 9.2, X + 3.0, -16.5 - X, (roof - 1.6) - Z])
    black = np.minimum.reduce([gl_s, ws, bl, roofp, kid + 0.35, intake_c, intake_s, gill, vents, diff + 0.0,
                               pipes + 0.3])
    gold = np.maximum(kid - 0.05, -(kid + 0.35))       # kidney surround
    zones = {"black": black, "gold": np.maximum(gold, -front), "red": tail, "white": head}
    return F, zones


def body_grid(vox):
    xs = np.arange(-LENGTH / 2 - 1.5, X_FRONT + 1.5, vox)
    ys = np.arange(-HALF_W - 2.5, HALF_W + 2.5, vox)
    zs = np.arange(BODY_Z0 - 1.0, HEIGHT + 1.5, vox)
    return xs, ys, zs


def build_body(vox=None):
    """Body meshes: {'paint': mesh, 'black': mesh, ...} in car coordinates."""
    vox = vox or VOXEL
    xs, ys, zs = body_grid(vox)
    F = np.empty((len(xs), len(ys), len(zs)), np.float32)
    Zf = {}
    step = 40
    for i in range(0, len(xs), step):
        X, Y, Z = np.meshgrid(xs[i:i + step], ys, zs, indexing="ij")
        f, zones = body_detailed(X, Y, Z)
        F[i:i + step] = f
        for k, z in zones.items():
            Zf.setdefault(k, np.empty_like(F))[i:i + step] = np.maximum.reduce([f, -(f + SKIN), z])
    F[[0, -1]] = F[:, [0, -1]] = F[:, :, [0, -1]] = 1.0
    out = {}
    union = np.full_like(F, 1e3)
    for k, z in Zf.items():
        z[[0, -1]] = z[:, [0, -1]] = z[:, :, [0, -1]] = 1.0
        # earlier zones win where zones overlap
        z = np.maximum(z, -union)
        if (z < 0).any():
            out[k] = mesh_from_field(z, xs, ys, zs, vox)
        union = np.minimum(union, z)
    out = {"paint": mesh_from_field(np.maximum(F, -union), xs, ys, zs, vox), **out}
    return out


def mesh_from_field(F, xs, ys, zs, vox):
    v, f, _, _ = measure.marching_cubes(F, 0.0, spacing=(vox, vox, vox))
    v += [xs[0], ys[0], zs[0]]
    m = trimesh.Trimesh(v, f[:, ::-1], process=False)
    if m.volume < 0:
        m.invert()
    return m


# ------------------------------------------------------------ mechanical parts
def simplify(tm):
    """Manifold-preserving mesh simplification."""
    man = m3d.Manifold(m3d.Mesh(np.asarray(tm.vertices, np.float32), np.asarray(tm.faces, np.uint32)))
    assert man.status() == m3d.Error.NoError, man.status()
    return to_trimesh(man.simplify(SIMPLIFY_TOL))


def to_trimesh(man):
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=False)


def box(x0, x1, y0, y1, z0, z1):
    return m3d.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_y(xc, zc, r, y0, y1, seg=48):
    """Cylinder along y."""
    return m3d.Manifold.cylinder(y1 - y0, r, r, seg).rotate([-90, 0, 0]).translate([xc, y0, zc])


def cs_polys(polys):
    return m3d.CrossSection([np.asarray(p, float) for p in polys], m3d.FillRule.EvenOdd)


def text_cs(text, size, family="DejaVu Sans", weight="bold"):
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    tp = TextPath((0, 0), text, size=size, prop=FontProperties(family=family, weight=weight))
    polys = [p for p in tp.to_polygons(closed_only=True) if len(p) > 2]
    cs = cs_polys(polys)
    (x0, y0), (x1, y1) = np.reshape(cs.bounds(), (2, 2))
    return cs.translate([-(x0 + x1) / 2, -(y0 + y1) / 2])


TYRE_IN_Y = WHEEL_OUT_Y - TYRE_W          # inner wheel face
AXLE_LEN = 2 * (TYRE_IN_Y + HUB_HOLE_DEPTH - 0.1)
CH_HW = POCKET_HW - CHASSIS_CLEAR         # chassis half width
CH_X = POCKET_X - CHASSIS_CLEAR
CH_TOP = POCKET_Z - CHASSIS_CLEAR
BLOCK_X = 3.2 - CHASSIS_CLEAR
BLOCK_TOP = 7.4 - CHASSIS_CLEAR


def build_chassis():
    """Chassis in car coordinates (bottom at z = BODY_Z0)."""
    c = box(-CH_X, CH_X, -CH_HW, CH_HW, BODY_Z0, CH_TOP)
    ch = (AXLE_D + AXLE_CLEAR) / 2
    for xa in (X_FA, X_RA):
        c += box(xa - BLOCK_X, xa + BLOCK_X, -CH_HW, CH_HW, BODY_Z0, BLOCK_TOP)
        c -= cyl_y(xa, AXLE_Z, ch, -CH_HW - 1, CH_HW + 1)
        c -= box(xa - SNAP_MOUTH / 2, xa + SNAP_MOUTH / 2, -CH_HW - 1, CH_HW + 1, BODY_Z0 - 1, AXLE_Z)
        # lead-in chamfer at the mouth
        lead = m3d.CrossSection([np.array([[-SNAP_MOUTH / 2 - 0.35, -1], [SNAP_MOUTH / 2 + 0.35, -1],
                                           [SNAP_MOUTH / 2, 0.45], [-SNAP_MOUTH / 2, 0.45]])])
        c -= lead.extrude(2 * CH_HW + 2).rotate([90, 0, 0]).translate([xa, CH_HW + 1, BODY_Z0])
        for sgn in (-1, 1):  # relief slots so the lips can flex
            c -= box(xa + sgn * 1.55 - 0.25, xa + sgn * 1.55 + 0.25, -CH_HW - 1, CH_HW + 1, BODY_Z0 - 1, AXLE_Z - 0.3)
    mid = (X_FA + X_RA) / 2
    for sgn in (-1, 1):   # snap ridges (click into the grooves inside the body pocket)
        r = m3d.Manifold.cylinder(24, RIDGE, RIDGE, 24).rotate([0, 90, 0]).translate([mid - 12, sgn * CH_HW, BODY_Z0 + 1.2])
        c += r
    # mirrored engraving on the underside
    t = text_cs("M5 CS", 5.0).mirror([1, 0]).rotate(90).extrude(0.4).translate([mid + 0, 0, BODY_Z0 - 0.01])
    t2 = text_cs("F90  1:64", 2.6).mirror([1, 0]).rotate(90).extrude(0.4).translate([mid + 6.5, 0, BODY_Z0 - 0.01])
    c -= t + t2
    # weight relief pockets on top (hidden inside the body)
    for xc in (mid, X_FA + 9.5, X_RA - 7.5):
        c -= box(xc - 4, xc + 4, -6.5, 6.5, BODY_Z0 + 1.2, CH_TOP + 1)
    return c


def y_spokes():
    cs = m3d.CrossSection.circle(1.25, 40)
    for k in range(5):
        a = math.radians(90 + 72 * k)
        u = np.array([math.cos(a), math.sin(a)])
        v = np.array([-u[1], u[0]])
        stem = cs_polys([[0.6 * u + 0.33 * v, 2.35 * u + 0.30 * v, 2.35 * u - 0.30 * v, 0.6 * u - 0.33 * v]])
        cs += stem
        for sgn in (-1, 1):
            b = a + sgn * math.radians(15)
            w = np.array([math.cos(b), math.sin(b)])
            n = np.array([-w[1], w[0]])
            p0 = 2.1 * u
            p1 = (RIM_R - 0.2) * w
            arm = cs_polys([[p0 - 0.24 * n, p1 - 0.24 * n, p1 + 0.24 * n, p0 + 0.24 * n]])
            cs += arm
    return cs


def build_wheel():
    """Wheel in print orientation: inner face on the bed (z = 0), axis = z. Returns (rim, tyre)."""
    seg = 96
    lip = RIM_R - 0.38
    rim = m3d.Manifold.cylinder(TYRE_W - 0.15, RIM_R, RIM_R, seg)
    window = (m3d.CrossSection.circle(lip, seg) - y_spokes()).extrude(5).translate([0, 0, 1.5])
    rim -= window
    # concave face: spokes drop towards the hub
    rim -= m3d.Manifold.cylinder(0.45, 0.6, lip - 0.1, seg).translate([0, 0, TYRE_W - 0.6])     # concave face
    rim += m3d.Manifold.cylinder(TYRE_W - 0.25, 0.75, 0.75, 32)               # centre cap
    for k in range(5):                                                       # lug nuts
        a = math.radians(54 + 72 * k)
        rim += m3d.Manifold.cylinder(TYRE_W - 0.4, 0.17, 0.17, 12).translate([0.95 * math.cos(a), 0.95 * math.sin(a), 0])
    hole_d = AXLE_D - PRESS_FIT
    rim -= m3d.Manifold.cylinder(HUB_HOLE_DEPTH, hole_d / 2, hole_d / 2, 32).translate([0, 0, -0.01])
    rim -= m3d.Manifold.cylinder(0.3, hole_d / 2 + 0.25, hole_d / 2, 32).translate([0, 0, -0.01])
    # tyre: 45 deg chamfer on the bed side, rounded shoulder on top, two tread grooves
    prof = [(RIM_R, 0.0), (TYRE_R - 0.6, 0.0), (TYRE_R, 0.6), (TYRE_R, 1.5), (TYRE_R - 0.18, 1.6),
            (TYRE_R - 0.18, 1.85), (TYRE_R, 1.95), (TYRE_R, 2.75), (TYRE_R - 0.18, 2.85), (TYRE_R - 0.18, 3.1),
            (TYRE_R, 3.2), (TYRE_R, TYRE_W - 0.5), (TYRE_R - 0.2, TYRE_W - 0.15), (TYRE_R - 0.5, TYRE_W),
            (RIM_R + 0.35, TYRE_W), (RIM_R, TYRE_W - 0.15)]
    tyre = m3d.CrossSection([np.array(prof)]).revolve(seg)
    return rim, tyre


def build_axle():
    """Axle lying along x on the bed, chamfered ends, small flat underneath."""
    r, ch = AXLE_D / 2, 0.25
    core = m3d.Manifold.cylinder(AXLE_LEN - 2 * ch, r, r, 32)
    end = m3d.Manifold.cylinder(ch, r, r - ch, 32)
    a = core.translate([0, 0, ch]) + end.translate([0, 0, AXLE_LEN - ch]) + end.mirror([0, 0, 1]).translate([0, 0, ch])
    a = a.translate([0, 0, -AXLE_LEN / 2]).rotate([0, 90, 0]).translate([0, 0, r - AXLE_FLAT])
    return a ^ box(-AXLE_LEN, AXLE_LEN, -2, 2, 0, 3)


# ------------------------------------------------------------------ plate layout
BODY_AT = (18.5, 0.0)          # plate position of the car centre (car x -> plate +Y)
CHASSIS_AT = (-12.5, 0.0)
AXLES_AT = [(-29.0, 0.0), (-26.0, 0.0)]
WHEELS_AT = [(-31.0, 50.5), (-19.0, 50.5), (-7.0, 50.5), (5.0, 50.5)]
TAG_AT = (24.5, 50.5)
FRAME = (-38.0, 37.0, -44.0, 60.0)
FRAME_MID_X, FRAME_MID_Y = 0.5, 41.0


def car_to_plate(at):
    """4x4: car coordinates -> plate (rotate +90 deg about z, body underside on the bed)."""
    T = np.eye(4)
    T[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    T[:3, 3] = [at[0], at[1], -BODY_Z0]
    return T


def gate(p0, p1):
    """Sprue gate between two plate points with a thin break-off neck at p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    assert L > 1.0, (p0, p1)
    ang = math.degrees(math.atan2(d[1], d[0]))
    neck = 0.7
    g = box(0, L - neck, -0.4, 0.4, 0, 0.6) + box(L - neck - 0.01, L, -0.25, 0.25, 0, 0.4)
    return g.rotate([0, 0, ang]).translate([p0[0], p0[1], 0])


def build_frame():
    x0, x1, y0, y1 = FRAME
    b, h = FRAME_BAR, FRAME_H
    f = (box(x0, x1, y0, y0 + b, 0, h) + box(x0, x1, y1 - b, y1, 0, h) + box(x0, x0 + b, y0, y1, 0, h)
         + box(x1 - b, x1, y0, y1, 0, h) + box(x0, x1, FRAME_MID_Y - b / 2, FRAME_MID_Y + b / 2, 0, h)
         + box(FRAME_MID_X - b / 2, FRAME_MID_X + b / 2, y0, FRAME_MID_Y, 0, h))
    xi0, xi1, yi0, yi1 = x0 + b - 0.1, x1 - b + 0.1, y0 + b - 0.1, y1 - b + 0.1
    mxl, mxr = FRAME_MID_X - b / 2 + 0.1, FRAME_MID_X + b / 2 - 0.1
    myl, myh = FRAME_MID_Y - b / 2 + 0.1, FRAME_MID_Y + b / 2 - 0.1
    bx, by = BODY_AT
    w0 = float(side_w(np.float64(BODY_Z0)))
    gates = [((mxr, by + 2), (bx - w0 + 0.3, by + 2)), ((mxr, by - 10), (bx - w0 + 0.3, by - 10)),
             ((xi1, by + 2), (bx + w0 - 0.3, by + 2)), ((xi1, by - 10), (bx + w0 - 0.3, by - 10)),
             ((bx, myl), (bx, by + float(x_front(np.float64(BODY_Z0))) - 0.3)), ((bx, yi0), (bx, by + float(x_rear(np.float64(BODY_Z0))) + 0.3))]
    cx, cy = CHASSIS_AT
    gates += [((mxl, cy + 15), (cx + CH_HW - 0.3, cy + 15)), ((mxl, cy - 15), (cx + CH_HW - 0.3, cy - 15)),
              ((cx, myl), (cx, cy + CH_X - 0.3)), ((cx, yi0), (cx, cy - CH_X + 0.3))]
    for sgn in (-1, 1):   # side runner to the chassis, axles hang off it by their ends
        ry = cy + sgn * 16
        f += box(xi0, cx - CH_HW + 0.3, ry - 0.4, ry + 0.4, 0, 0.6)
        for ax, ay in AXLES_AT:
            gates.append(((ax, ry), (ax, ay + sgn * (AXLE_LEN / 2 - 0.3))))
    for wx, wy in WHEELS_AT:
        r0 = TYRE_R - 0.6
        gates += [((wx, yi1), (wx, wy + r0 - 0.3)), ((wx, myh), (wx, wy - r0 + 0.3))]
    tx, ty = TAG_AT
    gates += [((tx, yi1), (tx, ty + 6.4)), ((tx, myh), (tx, ty - 6.4))]   # its right edge sits on the frame
    for p0, p1 in gates:
        f += gate(p0, p1)
    return f


def build_tag():
    tx, ty = TAG_AT
    plate = (m3d.CrossSection.square([21.0, 11.0], True).offset(1.0, m3d.JoinType.Round)).extrude(1.0)
    rim_ = (m3d.CrossSection.square([21.0, 11.0], True).offset(1.0, m3d.JoinType.Round)
            - m3d.CrossSection.square([21.0, 11.0], True).offset(0.4, m3d.JoinType.Round)).extrude(0.5).translate([0, 0, 1.0])
    t1 = text_cs("M5 CS", 5.6).extrude(0.6).translate([0, 1.6, 1.0])
    t2 = text_cs("F90  1:64", 2.2, weight="bold").extrude(0.5).translate([0, -3.2, 1.0])
    return (plate + rim_ + t1 + t2).translate([tx, ty, 0])


# ------------------------------------------------------------------ 3MF writer
EXTRUDER = {"paint": 1, "black": 2, "gold": 3, "red": 4, "white": 5, "tyre": 2, "rim": 3,
            "chassis": 2, "axle": 2, "frame": 1, "tag": 1}
COLOURS = ["#8E979E", "#1A1A1A", "#A8854A", "#C0141A", "#F2F2F0"]


def write_3mf(path, objects, thumb=None):
    """objects: [(name, [(part_name, extruder, trimesh)])], plate coordinates. Bambu/Orca/Creality style."""
    import uuid
    ns = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
          'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
          'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"')
    obj_xml, root_res, build, cfg, inst = [], [], [], [], []
    oid = 1
    pid = 1000
    lo = np.min([m.bounds[0] for _, parts in objects for _, _, m in parts], axis=0)
    hi = np.max([m.bounds[1] for _, parts in objects for _, _, m in parts], axis=0)
    shift = np.array([128.0, 128.0, 0]) - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]
    for name, parts in objects:
        comps, pcfg = [], []
        for pname, ext, m in parts:
            v = "\n".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
            t = "\n".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
            obj_xml.append(f' <object id="{pid}" p:UUID="{uuid.uuid4()}" type="model"><mesh><vertices>\n{v}\n'
                           f'</vertices><triangles>\n{t}\n</triangles></mesh></object>')
            comps.append(f'<component p:path="/3D/Objects/object_1.model" objectid="{pid}" '
                         f'p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
            pcfg.append(f'    <part id="{pid}" subtype="normal_part">\n'
                        f'      <metadata key="name" value="{pname}"/>\n'
                        f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                        f'      <metadata key="extruder" value="{ext}"/>\n    </part>')
            pid += 1
        root_res.append(f'  <object id="{oid}" p:UUID="{uuid.uuid4()}" type="model"><components>'
                        + "".join(comps) + '</components></object>')
        build.append(f'  <item objectid="{oid}" p:UUID="{uuid.uuid4()}" '
                     f'transform="1 0 0 0 1 0 0 0 1 {shift[0]:.4f} {shift[1]:.4f} {shift[2]:.4f}" printable="1"/>')
        cfg.append(f'  <object id="{oid}">\n    <metadata key="name" value="{name}"/>\n'
                   f'    <metadata key="extruder" value="{parts[0][1]}"/>\n' + "\n".join(pcfg) + '\n  </object>')
        inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n'
                    f'      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{100 + oid}"/>\n'
                    '    </model_instance>')
        oid += 1
    root = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {ns}>\n'
            ' <metadata name="Application">m5cs_generator.py</metadata>\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            ' <metadata name="Title">BMW M5 CS (F90) 1:64 kit</metadata>\n'
            ' <metadata name="Description">Supportless, glueless 1:64 kit card. Body, chassis, axles, wheels on one plate.</metadata>\n'
            + (' <metadata name="Thumbnail_Middle">/Metadata/plate_1.png</metadata>\n' if thumb else '')
            + ' <resources>\n' + "\n".join(root_res) + '\n </resources>\n <build>\n' + "\n".join(build)
            + '\n </build>\n</model>\n')
    sub = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" {ns}>\n'
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n' + "\n".join(obj_xml)
           + '\n </resources>\n <build/>\n</model>\n')
    model_cfg = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + "\n".join(cfg) + '\n  <plate>\n'
                 '    <metadata key="plater_id" value="1"/>\n    <metadata key="plater_name" value="BMW M5 CS F90"/>\n'
                 '    <metadata key="locked" value="false"/>\n'
                 + ('    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>\n' if thumb else '')
                 + "\n".join(inst) + '\n  </plate>\n</config>\n')
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
              ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
              ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
              ' <Default Extension="png" ContentType="image/png"/>\n</Types>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
            + (' <Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>\n' if thumb else '')
            + '</Relationships>\n')
    mrels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
             ' <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
             '</Relationships>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", root)
        z.writestr("3D/_rels/3dmodel.model.rels", mrels)
        z.writestr("3D/Objects/object_1.model", sub)
        z.writestr("Metadata/model_settings.config", model_cfg)
        if thumb:
            z.write(thumb, "Metadata/plate_1.png")


# ------------------------------------------------------------------ main
def build_all(vox=None):
    """Returns {object_name: [(part_name, extruder, mesh in plate coords)]} and car-assembly meshes."""
    body = build_body(vox)
    T = car_to_plate(BODY_AT)
    objs = {"body": []}
    for k, m in body.items():
        if not PREVIEW:
            m = simplify(m)
        objs["body"].append((f"body_{k}", EXTRUDER[k], m.copy().apply_transform(T)))
    chassis = to_trimesh(build_chassis())
    objs["chassis"] = [("chassis", EXTRUDER["chassis"], chassis.copy().apply_transform(car_to_plate(CHASSIS_AT)))]
    rim, tyre = build_wheel()
    rim, tyre = to_trimesh(rim), to_trimesh(tyre)
    for i, (wx, wy) in enumerate(WHEELS_AT):
        objs[f"wheel_{i + 1}"] = [("rim", EXTRUDER["rim"], rim.copy().apply_translation([wx, wy, 0])),
                                  ("tyre", EXTRUDER["tyre"], tyre.copy().apply_translation([wx, wy, 0]))]
    axle = to_trimesh(build_axle())
    for i, (ax, ay) in enumerate(AXLES_AT):
        R = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 0, 1])
        objs[f"axle_{i + 1}"] = [("axle", EXTRUDER["axle"], axle.copy().apply_transform(R).apply_translation([ax, ay, 0]))]
    objs["frame"] = [("frame", EXTRUDER["frame"], to_trimesh(build_frame()))]
    objs["tag"] = [("tag", EXTRUDER["tag"], to_trimesh(build_tag()))]

    # assembled car (car coordinates) for previews and fit checks
    asm = [(k, m) for k, m in body.items()] + [("chassis", chassis)]
    for xa in (X_FA, X_RA):
        for sgn in (-1, 1):
            # wheel print z axis -> car +-y, inner face at TYRE_IN_Y
            R = trimesh.transformations.rotation_matrix(-sgn * math.pi / 2, [1, 0, 0])
            off = [xa, sgn * TYRE_IN_Y, AXLE_Z]
            asm += [("rim", rim.copy().apply_transform(R).apply_translation(off)),
                    ("tyre", tyre.copy().apply_transform(R).apply_translation(off))]
        a = axle.copy().apply_translation([0, 0, -(AXLE_D / 2 - AXLE_FLAT)])
        a.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 0, 1]))
        asm.append(("axle", a.apply_translation([xa, 0, AXLE_Z])))
    return objs, asm


def main(objs=None):
    os.makedirs(os.path.join(OUT_DIR, "stl"), exist_ok=True)
    asm = None
    if objs is None:
        objs, asm = build_all()
    for name, parts in objs.items():
        if name.startswith(("wheel_", "axle_")) and not name.endswith("_1"):
            continue
        for pname, _, m in parts:
            base = name.split("_")[0]
            fn = pname if name.startswith("body") or base == pname else f"{base}_{pname}"
            m.export(os.path.join(OUT_DIR, "stl", f"m5cs_{fn}.stl"))
    write_3mf(os.path.join(OUT_DIR, "BMW_M5_CS_F90.3mf"), list(objs.items()),
              thumb=os.path.join(OUT_DIR, "images", "m5cs_plate_thumb.png")
              if os.path.exists(os.path.join(OUT_DIR, "images", "m5cs_plate_thumb.png")) else None)
    return objs, asm


if __name__ == "__main__":
    main()
