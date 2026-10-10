"""
Ribbed round jar with lid - Blender generator (Blender 3.6+ / 4.x / 5.x)

Usage
-----
In Blender : Scripting tab -> Open this file -> Run Script
Headless   : blender -b -P jar_blender.py -- [out_dir]

Exports (mm):
    jar_body.stl   ribbed container with a collar that carries 3 snap lugs
    jar_lid.stl    ribbed lid with 3 matching notches

Two heights from the reference photo:
    tall jar  -> BODY_H = 75   (the green one in the back)
    short jar -> BODY_H = 40   (the mint one in front)
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402 (must come after bpy when run as a module)
import numpy as np

# ----------------------------------------------------------------- PARAMETERS
DIAMETER = 90.0        # outer diameter (mm)
BODY_H = 60.0          # height of the ribbed body (mm)
LID_H = 25.0           # height of the lid (mm)
WALL = 2.4             # body wall thickness (mm)
FLOOR = 2.5            # body floor thickness (mm)
LID_TOP = 3.0          # lid top thickness (mm)

N_RIBS = 72            # number of vertical ribs
RIB_DEPTH = 1.2        # groove depth between ribs (mm)
RIB_FLAT = 1.2         # >1 = wider flat ribs, narrower grooves
EDGE_R = 4.0           # rounded bottom edge of the body / top edge of the lid

COLLAR_OD = 80.0       # collar outer diameter (mm)
COLLAR_ID = 74.0       # collar inner diameter (mm)
COLLAR_H = 8.0         # collar height above the body (mm)
LUG_W = 7.0            # snap lug width (mm)
LUG_PROUD = 0.9        # how far the lugs stick out (mm)
LUG_Z = (2.0, 5.0)     # lug height range on the collar (mm above body top)
CLEARANCE = 0.4        # fit tolerance (mm)

COLS_PER_RIB = 10      # mesh resolution around the circumference

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl") \
    if "__file__" in globals() else os.path.expanduser("~/jar_stl")
if "--" in sys.argv:
    extra = sys.argv[sys.argv.index("--") + 1:]
    if extra:
        OUT_DIR = extra[0]
# ----------------------------------------------------------------------------

R = DIAMETER / 2
RI = R - WALL
RC_OUT, RC_IN = COLLAR_OD / 2, COLLAR_ID / 2


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def arc(cx, cz, r, a0, a1, n=8):
    """Points (r, z) on a circular arc in the (radius, z) plane."""
    return [(cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


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


def lathe(name, profile):
    """Revolve a (r, z, rib_weight) polyline around Z, ribbing where weight > 0."""
    n_col = N_RIBS * COLS_PER_RIB
    th = np.arange(n_col) * 2 * math.pi / n_col
    plateau = smoothstep(0.5 + RIB_FLAT * np.cos(N_RIBS * th))   # 1 = rib top, 0 = groove
    groove = 1.0 - plateau
    verts, faces = [], []
    for r, z, w in profile:
        rr = r - RIB_DEPTH * w * groove
        verts += [(rr[j] * math.cos(th[j]), rr[j] * math.sin(th[j]), z)
                  for j in range(n_col)] if isinstance(rr, np.ndarray) else \
                 [(rr * math.cos(t), rr * math.sin(t), z) for t in th]
    for i in range(len(profile) - 1):
        a, b = i * n_col, (i + 1) * n_col
        for j in range(n_col):
            j1 = (j + 1) % n_col
            faces.append([a + j, a + j1, b + j1, b + j])
    return make_object(name, verts, faces)


def box_at_angle(name, r0, r1, z0, z1, width, angle_deg):
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(rad, off, z) for z in (z0, z1) for off in (-width / 2, width / 2)
           for rad in (r0, r1)]
    verts = [(rad * ca - off * sa, rad * sa + off * ca, z) for rad, off, z in pts]
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1],
             [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return make_object(name, verts, faces)


def boolean(target, tool, op):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.object = tool
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)


# ----------------------------------------------------------------- BODY
def build_body():
    fr = EDGE_R
    prof = [(0.0, 0.0, 0.0), (R - fr, 0.0, 0.0)]
    for a in np.linspace(-90, 0, 9)[1:]:                  # rounded bottom edge
        (r, z), = arc(R - fr, fr, fr, a, a, 1)
        prof.append((r, z, float(smoothstep((a + 90) / 90))))
    prof += [(R, BODY_H, 1.0),                            # ribbed wall
             (RC_OUT, BODY_H, 0.0),                       # ledge the lid sits on
             (RC_OUT, BODY_H + COLLAR_H, 0.0),            # collar
             (RC_IN, BODY_H + COLLAR_H, 0.0),
             (RC_IN, BODY_H - 1.0, 0.0),
             (RI, BODY_H - 1.0 - (RI - RC_IN), 0.0),      # 45 deg chamfer, no overhang
             (RI, FLOOR, 0.0),
             (0.0, FLOOR, 0.0)]
    body = lathe("jar_body", prof)

    for ang in (0, 120, 240):                             # snap lugs on the collar
        lug = box_at_angle("lug", RC_OUT - 0.5, RC_OUT + LUG_PROUD,
                           BODY_H + LUG_Z[0], BODY_H + LUG_Z[1], LUG_W, ang)
        boolean(body, lug, "UNION")
    return body


# ----------------------------------------------------------------- LID
def build_lid():
    fr = EDGE_R
    ri_l = RC_OUT + CLEARANCE
    prof = [(0.0, LID_H - LID_TOP, 0.0),
            (ri_l, LID_H - LID_TOP, 0.0),
            (ri_l, 0.0, 0.0),
            (R, 0.0, 1.0),
            (R, LID_H - fr, 1.0)]
    for a in np.linspace(0, 90, 9)[1:]:                   # rounded top edge
        (r, z), = arc(R - fr, LID_H - fr, fr, a, a, 1)
        prof.append((r, z, float(smoothstep((90 - a) / 90))))
    prof.append((0.0, LID_H, 0.0))
    lid = lathe("jar_lid", prof)

    for ang in (0, 120, 240):                             # notches that catch the lugs
        notch = box_at_angle("notch", ri_l - 0.5, RC_OUT + LUG_PROUD + CLEARANCE,
                             LUG_Z[0] - 0.2, LUG_Z[1] + 0.4, LUG_W + 0.8, ang)
        boolean(lid, notch, "DIFFERENCE")
    return lid


# ----------------------------------------------------------------- MAIN
def export_stl(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              ascii_format=False)
    else:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    body, lid = build_body(), build_lid()
    for o in (body, lid):
        export_stl(o, os.path.join(OUT_DIR, o.name + ".stl"))
    lid.location.x = DIAMETER + 20          # lid beside the body for viewing
    print("Exported to", OUT_DIR)
    for o in (body, lid):
        d = o.dimensions
        print(f"{o.name}: {d.x:.1f} x {d.y:.1f} x {d.z:.1f} mm, {len(o.data.polygons)} faces")


main()
