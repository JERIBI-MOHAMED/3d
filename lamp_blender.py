"""
Twisted textured table lamp - Blender generator (Blender 3.6+ / 4.x / 5.x)

Usage
-----
In Blender : Scripting tab -> Open this file -> Run Script
Headless   : blender -b -P lamp_blender.py -- [out_dir]

Creates 3 printable parts (units = mm) and exports one STL per part:
    lamp_shade.stl  twisted textured shade, print upright, vase mode NOT needed
    lamp_base.stl   squircle base with socket hole and spigot for the shade
    lamp_cap.stl    bottom cover, 4 x M3 screws

Everything is parametric: edit the PARAMETERS block and run again.
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402 (must come after bpy when run as a module)
import numpy as np

# ----------------------------------------------------------------- PARAMETERS
SHADE_WIDTH = 84.0       # width of the squircle section (mm)
SHADE_HEIGHT = 155.0     # shade height (mm)
TWIST_DEG = 60.0         # total twist bottom -> top
WALL = 1.2               # shade wall at the bottom of the texture (mm) -> light diffusion
SQUIRCLE_N = 4.0         # 2 = circle, 4 = rounded square, higher = squarer

TEXTURE = True           # pyramid texture (False = smooth shade, light file)
TEX_PITCH = 2.4          # size of one pyramid (mm)
TEX_AMP = 0.9            # pyramid height (mm)
FLAT_BAND = 3.0          # smooth band at top / bottom of the shade (mm)

BASE_WIDTH = 100.0       # base width (mm)
BASE_HEIGHT = 55.0       # base height (mm)
BASE_WALL = 3.0          # base wall (mm)
BASE_TOP = 4.0           # base top plate thickness (mm)
BASE_BEVEL = 5.0         # rounded edges (mm)
SOCKET_HOLE = 36.0       # hole for lamp holder: E14 ~ 36, E27 ~ 44 (mm)
SPIGOT_H = 6.0           # lip that centers the shade (mm)
CLEARANCE = 0.3          # fit tolerance (mm)

CAP_T = 3.0              # bottom cap thickness (mm)
POST_POS = 34.0          # screw post position from centre (mm)
SCREW_PILOT = 2.6        # pilot hole for M3 self-tapping screw (mm)
SCREW_HEAD = 3.4         # clearance hole in the cap (mm)
CABLE_W = 7.0            # cable slot width (mm)
CABLE_H = 6.0            # cable slot height (mm)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl") \
    if "__file__" in globals() else os.path.expanduser("~/lamp_stl")
if "--" in sys.argv:
    extra = sys.argv[sys.argv.index("--") + 1:]
    if extra:
        OUT_DIR = extra[0]
# ----------------------------------------------------------------------------


def squircle_r(theta, half, n=SQUIRCLE_N):
    """Radius of a superellipse of half-width `half` at polar angle theta."""
    c, s = np.abs(np.cos(theta)), np.abs(np.sin(theta))
    return half / (c ** n + s ** n) ** (1.0 / n)


def make_object(name, verts, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(np.asarray(verts, dtype=float).tolist(), [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return obj


def prism(name, half, z0, z1, n_seg=160):
    """Squircle prism (closed, with n-gon caps)."""
    th = np.linspace(0, 2 * math.pi, n_seg, endpoint=False)
    r = squircle_r(th, half)
    x, y = r * np.cos(th), r * np.sin(th)
    verts = [(x[i], y[i], z0) for i in range(n_seg)] + \
            [(x[i], y[i], z1) for i in range(n_seg)]
    faces = [[i, (i + 1) % n_seg, n_seg + (i + 1) % n_seg, n_seg + i]
             for i in range(n_seg)]
    faces.append(list(range(n_seg))[::-1])
    faces.append([n_seg + i for i in range(n_seg)])
    return make_object(name, verts, faces)


def cylinder(name, x, y, z0, z1, d, seg=48):
    th = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    r = d / 2
    verts = [(x + r * math.cos(t), y + r * math.sin(t), z0) for t in th] + \
            [(x + r * math.cos(t), y + r * math.sin(t), z1) for t in th]
    faces = [[i, (i + 1) % seg, seg + (i + 1) % seg, seg + i] for i in range(seg)]
    faces.append(list(range(seg))[::-1])
    faces.append([seg + i for i in range(seg)])
    return make_object(name, verts, faces)


def box(name, cx, cy, cz, sx, sy, sz):
    h = (sx / 2, sy / 2, sz / 2)
    verts = [(cx + a * h[0], cy + b * h[1], cz + c * h[2])
             for c in (-1, 1) for b in (-1, 1) for a in (-1, 1)]
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1],
             [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return make_object(name, verts, faces)


def boolean(target, tool, op="DIFFERENCE", delete_tool=True):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.object = tool
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if delete_tool:
        bpy.data.objects.remove(tool, do_unlink=True)


def union(a, b):
    boolean(a, b, "UNION")


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------- SHADE
def build_shade():
    half = SHADE_WIDTH / 2
    # arc length of the base squircle -> texture follows the surface
    fine = np.linspace(0, 2 * math.pi, 20001)
    rf = squircle_r(fine, half)
    seg = np.hypot(np.diff(rf * np.cos(fine)), np.diff(rf * np.sin(fine)))
    perim = seg.sum()

    # beads form a regular grid; the mesh is sampled 6x per bead so they stay round
    SUB = 6
    n_u = max(1, round(perim / TEX_PITCH))
    pitch = perim / n_u
    n_v = max(1, round(SHADE_HEIGHT / TEX_PITCH))
    pitch_z = SHADE_HEIGHT / n_v
    n_theta = n_u * SUB if TEXTURE else 240
    n_out = n_v * SUB + 1 if TEXTURE else 80
    n_in = 80

    s_cum = np.concatenate([[0], np.cumsum(seg)])
    s = np.arange(n_theta) * perim / n_theta           # equal arc length steps
    th = np.interp(s, s_cum, fine)
    r0 = squircle_r(th, half)

    def ring_points(z, radius_offset, bump):
        t = z / SHADE_HEIGHT
        phi = math.radians(TWIST_DEG) * smoothstep(t)
        r = r0 + radius_offset + bump
        return np.stack([r * np.cos(th + phi), r * np.sin(th + phi),
                         np.full_like(th, z)], axis=1)

    def bump_at(z):
        if not TEXTURE:
            return np.zeros_like(th)
        u = s / pitch
        v = z / pitch_z + 0.5 * (np.floor(u) % 2)       # brick offset, woven look
        bead = (0.5 + 0.5 * np.cos(2 * math.pi * u)) * (0.5 + 0.5 * np.cos(2 * math.pi * v))
        win = smoothstep(min(z, SHADE_HEIGHT - z) / FLAT_BAND)
        return TEX_AMP * bead * win

    outer = [ring_points(z, 0.0, bump_at(z))
             for z in np.linspace(0, SHADE_HEIGHT, n_out)]
    inner = [ring_points(z, -WALL, 0)
             for z in np.linspace(0, SHADE_HEIGHT, n_in)]
    # valleys of the texture sit at radius r0, wall is measured from there
    verts = np.concatenate(outer + inner)
    N = n_theta
    off_in = n_out * N

    faces = []
    j = np.arange(N)
    j1 = (j + 1) % N
    for i in range(n_out - 1):
        a, b = i * N, (i + 1) * N
        faces += np.stack([a + j, a + j1, b + j1, b + j], axis=1).tolist()
    for i in range(n_in - 1):
        a, b = off_in + i * N, off_in + (i + 1) * N
        faces += np.stack([a + j, b + j, b + j1, a + j1], axis=1).tolist()
    # bottom and top rims
    o0, i0 = 0, off_in
    o1, i1 = (n_out - 1) * N, off_in + (n_in - 1) * N
    faces += np.stack([i0 + j, i0 + j1, o0 + j1, o0 + j], axis=1).tolist()
    faces += np.stack([o1 + j, o1 + j1, i1 + j1, i1 + j], axis=1).tolist()
    return make_object("lamp_shade", verts, faces)


# ----------------------------------------------------------------- BASE
def build_base():
    half = BASE_WIDTH / 2
    base = prism("lamp_base", half, 0, BASE_HEIGHT)

    # rounded edges
    bev = base.modifiers.new("bevel", "BEVEL")
    bev.width = BASE_BEVEL
    bev.segments = 5
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(50)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.modifier_apply(modifier=bev.name)

    # hollow body: open at the bottom, closed by the cap
    boolean(base, prism("cavity", half - BASE_WALL, -1, BASE_HEIGHT - BASE_TOP))

    # screw posts under the top plate
    for sx in (-1, 1):
        for sy in (-1, 1):
            union(base, cylinder("post", sx * POST_POS, sy * POST_POS,
                                 CAP_T, BASE_HEIGHT - BASE_TOP + 0.5, 8.0))

    # spigot: centres the shade (shade inner size at its bottom - clearance)
    inner_half = SHADE_WIDTH / 2 - WALL - CLEARANCE
    union(base, prism("spigot", inner_half, BASE_HEIGHT - 0.5,
                      BASE_HEIGHT + SPIGOT_H))

    # socket hole through top plate + spigot
    boolean(base, cylinder("socket", 0, 0, BASE_HEIGHT - BASE_TOP - 1,
                           BASE_HEIGHT + SPIGOT_H + 1, SOCKET_HOLE, 72))
    # pilot holes for the screws
    for sx in (-1, 1):
        for sy in (-1, 1):
            boolean(base, cylinder("pilot", sx * POST_POS, sy * POST_POS,
                                   CAP_T - 1, CAP_T + 14, SCREW_PILOT, 24))
    # cable slot in the -Y wall, just above the cap
    boolean(base, box("slot", 0, -half, CAP_T + CABLE_H / 2,
                      CABLE_W, BASE_WALL * 4, CABLE_H))
    return base


# ----------------------------------------------------------------- CAP
def build_cap():
    cap = prism("lamp_cap", BASE_WIDTH / 2 - BASE_WALL - CLEARANCE, 0, CAP_T)
    for sx in (-1, 1):
        for sy in (-1, 1):
            boolean(cap, cylinder("hole", sx * POST_POS, sy * POST_POS,
                                  -1, CAP_T + 1, SCREW_HEAD, 24))
    return cap


# ----------------------------------------------------------------- MAIN
def export_stl(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if hasattr(bpy.ops.wm, "stl_export"):          # Blender 4.x / 5.x
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              ascii_format=False)
    else:                                          # Blender 3.x
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    shade = build_shade()
    base = build_base()
    cap = build_cap()

    # lay the parts out side by side for viewing (STL are exported as-is)
    for o in (shade, base, cap):
        export_stl(o, os.path.join(OUT_DIR, o.name + ".stl"))
    shade.location.z = BASE_HEIGHT + SPIGOT_H - 0.5     # assembled preview
    cap.location = (BASE_WIDTH + 20, 0, 0)

    print("Exported to", OUT_DIR)
    for o in (shade, base, cap):
        d = o.dimensions
        print(f"{o.name}: {d.x:.1f} x {d.y:.1f} x {d.z:.1f} mm, "
              f"{len(o.data.polygons)} faces")


main()
