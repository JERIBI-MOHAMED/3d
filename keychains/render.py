"""Product-shot renders of the keychains (Blender/bpy, Cycles), for Instagram posts.

    pip install bpy        # or run inside Blender: blender -b -P render.py -- ...
    python render.py <stl_dir> <out_dir> [scene ...] [--samples N] [--size WxH]

Scenes are defined in SCENES below (positions in mm on the table, rotation in degrees).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
MM = 0.001

# id, x, y, rotation, key ring?
SCENES = {
    # target is the point the camera looks at; a target above the items leaves room for a headline
    "hero": {"bg": "#EFE4D2", "target": (2, 6), "dist": 0.60, "elev": 62, "azim": -90, "items": [
        ("flag_tunisia", -34, 24, -14, True), ("khomsa", 42, 26, -8, False),
        ("name_ahmed", -26, -14, 6, False), ("jersey_red_yellow", 46, -24, 12, False),
        ("name_yasmine_ar", -30, -42, -5, False), ("heart_initials", 18, -78, -8, False)]},
    "names": {"bg": "#F3E9DD", "target": (0, 22), "dist": 0.40, "elev": 64, "azim": -90, "items": [
        ("name_yasmine", -8, 36, -5, True), ("name_yasmine_ar", 10, 11, 4, True),
        ("name_ahmed", -8, -14, -3, True), ("name_ahmed_ar", 14, -40, 5, True)]},
    "souvenir": {"bg": "#E6EEF2", "target": (2, 10), "dist": 0.35, "elev": 62, "azim": -90, "items": [
        ("flag_tunisia", -14, -26, -10, True), ("khomsa", 20, 14, 8, False)]},
    "jerseys": {"bg": "#ECEEF0", "target": (0, 14), "dist": 0.47, "elev": 62, "azim": -90, "items": [
        ("jersey_red_white", -46, -6, -10, True), ("jersey_red_yellow", 0, -16, 0, True),
        ("jersey_white_red", 46, -6, 10, True)]},
    "wedding": {"bg": "#F7E8E6", "target": (0, 10), "dist": 0.42, "elev": 64, "azim": -90, "items": [
        ("heart_initials", -27, 4, -14, True), ("heart_initials", 25, 10, 12, False),
        ("heart_initials", 0, -34, 2, True)]},
}


def srgb(hexs):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hexs.lstrip("#")
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


_mats = {}


def pla(hexs):
    if hexs in _mats:
        return _mats[hexs]
    m = bpy.data.materials.new(f"PLA_{hexs}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = srgb(hexs)
    bsdf.inputs["Roughness"].default_value = 0.38
    bsdf.inputs["Specular IOR Level"].default_value = 0.45
    # 0.2 mm layer lines on the side walls
    coord = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 2 * math.pi / (20 * 0.2)  # object space is mm; period = 2pi/(20*scale)
    wave.inputs["Distortion"].default_value = 0.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.00004
    nt.links.new(coord.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    _mats[hexs] = m
    return m


def metal():
    m = bpy.data.materials.new("Steel")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.78, 0.78, 0.8, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.2
    return m


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup(scene_def, size, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()  # materials from the previous scene are gone
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.12

    bpy.ops.mesh.primitive_plane_add(size=3)
    floor = bpy.context.object
    fm = bpy.data.materials.new("Backdrop")
    fm.use_nodes = True
    fb = fm.node_tree.nodes["Principled BSDF"]
    fb.inputs["Base Color"].default_value = srgb(scene_def["bg"])
    fb.inputs["Roughness"].default_value = 0.9
    floor.data.materials.append(fm)

    tx, ty = (v * MM for v in scene_def["target"])
    target = (tx, ty, 0)

    def area(name, loc, size_, power, color=(1, 1, 1)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        L = bpy.context.object
        L.name = name
        L.data.size = size_
        L.data.energy = power
        L.data.color = color
        look_at(L, target)

    area("Key", (tx - 0.30, ty + 0.22, 0.42), 0.45, 5, (1.0, 0.97, 0.92))
    area("Fill", (tx + 0.40, ty - 0.10, 0.30), 0.6, 2.5, (0.92, 0.96, 1.0))
    area("Top", (tx, ty, 0.6), 0.5, 3)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 85
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 11
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    e, a, dist = math.radians(scene_def["elev"]), math.radians(scene_def["azim"]), scene_def["dist"]
    cam.location = (tx + dist * math.cos(e) * math.cos(a), ty + dist * math.cos(e) * math.sin(a), dist * math.sin(e))
    look_at(cam, target)
    cam_data.dof.focus_distance = dist
    sc.camera = cam
    return sc


def place(meta, stl_dir, x, y, rot, ring, steel):
    minx, miny, maxx, maxy = meta["bounds"]
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    hx, hy = meta["hole"]
    d = Vector((hx - cx, hy - cy, 0)).normalized()
    ring_r, wire = 12.0, 0.9

    # Resting on the ring: tilt about the far edge so the hole side lifts by the wire thickness
    corners = [Vector((px - hx, py - hy, 0)) for px in (minx, maxx) for py in (miny, maxy)]
    L = -min(c.dot(d) for c in corners)
    far = Vector((hx, hy, 0)) - d * L
    axis = Vector((-d.y, d.x, 0))
    tilt = (Matrix.Translation(far) @ Matrix.Rotation(-math.atan2(2 * wire, L), 4, axis)
            @ Matrix.Translation(-far)) if ring else Matrix.Identity(4)
    world = Matrix.Translation((x * MM, y * MM, 0)) @ Matrix.Rotation(math.radians(rot), 4, "Z") \
        @ Matrix.Scale(MM, 4) @ Matrix.Translation((-cx, -cy, 0))

    for p in meta["parts"]:
        bpy.ops.wm.stl_import(filepath=os.path.join(stl_dir, p["file"]))
        o = bpy.context.selected_objects[0]
        o.matrix_world = world @ tilt
        o.data.materials.append(pla(p["hex"]))
        bpy.ops.object.shade_auto_smooth(angle=math.radians(35))

    if ring:
        bpy.ops.mesh.primitive_torus_add(major_radius=ring_r, minor_radius=wire,
                                         major_segments=96, minor_segments=24)
        t = bpy.context.object
        c = Vector((hx, hy, wire)) + d * ring_r
        t.matrix_world = world @ Matrix.Translation(c)
        t.data.materials.append(steel)
        bpy.ops.object.shade_smooth()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    samples, size, names, pos = 128, (1080, 1350), [], []
    it = iter(argv)
    for a in it:
        if a == "--samples":
            samples = int(next(it))
        elif a == "--size":
            size = tuple(int(v) for v in next(it).split("x"))
        else:
            pos.append(a)
    stl_dir, out_dir, names = pos[0], pos[1], pos[2:] or list(SCENES)
    meta = {m["id"]: m for m in json.load(open(os.path.join(HERE, "parts.json"), encoding="utf-8"))}
    os.makedirs(out_dir, exist_ok=True)
    for name in names:
        sd = SCENES[name]
        sc = setup(sd, size, samples)
        steel = metal()
        for did, x, y, rot, ring in sd["items"]:
            place(meta[did], stl_dir, x, y, rot, ring, steel)
        sc.render.filepath = os.path.join(out_dir, f"render_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("wrote", sc.render.filepath)


if __name__ == "__main__":
    main()
