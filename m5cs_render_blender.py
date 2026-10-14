"""
BMW M5 CS (F90) 1:64 kit - Blender render (Blender 4.2+ / 5.x)

Loads the STLs written by m5cs_generator.py, snaps the parts together into the
finished car and renders studio shots with Cycles.

Usage
-----
In Blender : Scripting tab -> Open this file -> Run Script
Headless   : blender -b -P m5cs_render_blender.py -- [out_dir] [samples]
bpy module : python m5cs_render_blender.py [out_dir] [samples]   (pip install bpy, Python 3.11)

Writes images/m5cs_blender_3quarter.png, _rear.png, _plate.png
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
STL = os.path.join(HERE, "stl")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = args[0] if args else os.path.join(HERE, "images")
SAMPLES = int(args[1]) if len(args) > 1 else 192
RES_PCT = int(args[2]) if len(args) > 2 else 100
RES = (1920, 1080)

# layout constants, must match m5cs_generator.py
BODY_AT, CHASSIS_AT = (18.5, 0.0), (-12.5, 0.0)
WHEEL_AT, AXLE_AT = (-31.0, 50.5), (-29.0, 0.0)
BODY_Z0, AXLE_Z, AXLE_R = 2.0, 5.5, 1.0 - 0.1
X_FA, X_RA, TYRE_IN_Y = 24.398, -22.195, 10.417
REMESH = 0.07   # body voxel remesh for rendering (mm), hides simplification facets; 0 = off
S = 0.01   # 1 mm -> 1 cm in the scene, keeps lights and camera at friendly sizes

# plate -> car: car x = plate Y, car y = BODY_AT.x - plate X, car z = plate Z + BODY_Z0
PLATE_TO_CAR = lambda at: Matrix.Translation((0, 0, BODY_Z0)) @ Matrix.Rotation(-math.pi / 2, 4, "Z") @ \
    Matrix.Translation((-at[0], -at[1], 0))


# ----------------------------------------------------------------- materials
def principled(name, color, metallic=0.0, rough=0.5, coat=0.0, emit=0.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    if hasattr(m, "use_nodes") and bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


MAT = {}


def make_materials():
    MAT.update({
        "paint": principled("Frozen Brands Hatch Grey (matte)", (0.16, 0.18, 0.19), 0.3, 0.62),
        "black": principled("Glass / carbon", (0.01, 0.01, 0.012), 0.0, 0.18, coat=0.6),
        "gold": principled("Gold Bronze", (0.55, 0.38, 0.16), 1.0, 0.28),
        "red": principled("Tail light", (0.6, 0.01, 0.01), 0.0, 0.15, emit=1.5),
        "white": principled("Headlight", (0.95, 0.95, 1.0), 0.0, 0.1, emit=4.0),
        "rim": None, "tyre": principled("Rubber", (0.02, 0.02, 0.02), 0.0, 0.8),
        "chassis": principled("Chassis", (0.03, 0.03, 0.03), 0.0, 0.6),
        "plastic": principled("PLA grey", (0.16, 0.18, 0.19), 0.0, 0.5),
    })
    MAT["rim"] = MAT["gold"]


# ----------------------------------------------------------------- helpers
def load(name, mat, matrix, smooth=True, collection=None, remesh=0.0):
    bpy.ops.wm.stl_import(filepath=os.path.join(STL, f"m5cs_{name}.stl"))
    ob = bpy.context.selected_objects[0]
    ob.data.transform(matrix)
    ob.data.transform(Matrix.Scale(S, 4))
    ob.data.materials.append(mat)
    if remesh:
        mod = ob.modifiers.new("remesh", "REMESH")
        mod.mode = "VOXEL"
        mod.voxel_size = remesh * S
        mod.use_smooth_shade = True
        mod.adaptivity = 0.0
        smooth = False
    if smooth:
        with bpy.context.temp_override(selected_editable_objects=[ob], active_object=ob, object=ob):
            bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    if collection:
        for c in ob.users_collection:
            c.objects.unlink(ob)
        collection.objects.link(ob)
    return ob


def instance(ob, matrix, collection):
    o2 = ob.copy()
    o2.data = ob.data.copy()
    o2.data.transform(Matrix.Scale(1 / S, 4))
    o2.data.transform(matrix)
    o2.data.transform(Matrix.Scale(S, 4))
    collection.objects.link(o2)
    return o2


def build_car():
    car = bpy.data.collections.new("car")
    bpy.context.scene.collection.children.link(car)
    T = PLATE_TO_CAR(BODY_AT)
    for k in ("paint", "black", "gold", "red", "white"):
        load(f"body_{k}", MAT[k], T, collection=car, remesh=REMESH)
    load("chassis", MAT["chassis"], PLATE_TO_CAR(CHASSIS_AT), smooth=False, collection=car)
    to_origin = Matrix.Translation((-WHEEL_AT[0], -WHEEL_AT[1], 0))
    rim = load("wheel_rim", MAT["rim"], to_origin, collection=car)
    tyre = load("wheel_tyre", MAT["tyre"], to_origin, collection=car)
    axle = load("axle", MAT["chassis"], Matrix.Translation((-AXLE_AT[0], -AXLE_AT[1], -AXLE_R)), collection=car)
    for xa in (X_FA, X_RA):
        for sgn in (1, -1):   # wheel z axis -> outward, inner face at TYRE_IN_Y
            M = Matrix.Translation((xa, sgn * TYRE_IN_Y, AXLE_Z)) @ Matrix.Rotation(-sgn * math.pi / 2, 4, "X")
            instance(rim, M, car)
            instance(tyre, M, car)
        instance(axle, Matrix.Translation((xa, 0, AXLE_Z)) @ Matrix.Rotation(math.pi / 2, 4, "Z"), car)
    for ob in (rim, tyre):
        bpy.data.objects.remove(ob)
    bpy.data.objects.remove(axle)
    return car


def build_plate():
    plate = bpy.data.collections.new("plate")
    bpy.context.scene.collection.children.link(plate)
    I = Matrix.Identity(4)
    for k in ("paint", "black", "gold", "red", "white"):
        load(f"body_{k}", MAT[k], I, collection=plate)
    load("chassis", MAT["chassis"], I, smooth=False, collection=plate)
    load("frame", MAT["plastic"], I, smooth=False, collection=plate)
    load("tag", MAT["plastic"], I, smooth=False, collection=plate)
    rim = load("wheel_rim", MAT["rim"], I, collection=plate)
    tyre = load("wheel_tyre", MAT["tyre"], I, collection=plate)
    for i in range(1, 4):
        for ob in (rim, tyre):
            instance(ob, Matrix.Translation((12.0 * i, 0, 0)), plate)
    ax = load("axle", MAT["chassis"], I, smooth=False, collection=plate)
    instance(ax, Matrix.Translation((3.0, 0, 0)), plate)
    return plate


# ----------------------------------------------------------------- scene
def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = RES_PCT
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"

    world = bpy.data.worlds.new("studio")
    sc.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.9, 0.92, 0.95, 1)
    bg.inputs["Strength"].default_value = 0.12

    bpy.ops.mesh.primitive_plane_add(size=40)
    floor = bpy.context.active_object
    floor.name = "floor"
    floor.data.materials.append(principled("floor", (0.35, 0.36, 0.38), 0.0, 0.4))

    def area(name, loc, size, energy, color=(1, 1, 1)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        L = bpy.context.active_object
        L.name = name
        L.data.size = size
        L.data.energy = energy
        L.data.color = color
        L.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return L

    area("key", (1.2, -2.0, 2.2), 1.5, 90)
    area("fill", (-1.8, 1.4, 1.2), 2.0, 30, (0.85, 0.9, 1.0))
    area("top", (0, 0, 2.5), 2.5, 70)
    area("kick", (-2.0, -0.6, 0.6), 1.0, 25)

    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.lens = 85
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 11.0
    sc.camera = cam
    return cam


def shoot(cam, eye, target, path, lens=85, focus=None):
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.dof.focus_distance = focus or (Vector(target) - Vector(eye)).length
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("wrote", path)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_materials()
    os.makedirs(OUT, exist_ok=True)
    cam = setup_scene()
    car = build_car()
    shoot(cam, (1.3, -1.48, 0.6), (0.01, 0.0, 0.085), os.path.join(OUT, "m5cs_blender_3quarter.png"))
    if "--front-only" in sys.argv:
        return
    shoot(cam, (-1.42, -1.36, 0.66), (-0.02, 0.0, 0.085), os.path.join(OUT, "m5cs_blender_rear.png"))
    car.hide_render = True
    build_plate()
    shoot(cam, (0.6, -2.0, 2.75), (0.0, 0.08, 0.0), os.path.join(OUT, "m5cs_blender_plate.png"), lens=70)


main()
