"""Hand + thin stick, printed separately, joined by a twist lock (bayonet).

Usage: python3 make_twist_lock.py original_hand.3mf out_dir

A round cuff is added under the wrist with a socket in it. The stick has two lugs at its top:
push it in (lugs in the slots), twist ~90 deg until it clicks over the detent bump, and it is locked.
Writes twist_lock.3mf (both parts on one plate, from the original Creality K2 SE project),
hand_socket.stl and stick.stl. All sizes in mm at the hand's print scale.
"""
import os
import re
import sys
import zipfile

import manifold3d as mf
import numpy as np
import pymeshfix
import trimesh

HAND_SCALE = 0.35       # the scale the hand had in the original project (35 mm tall)
STICK_D = 6.0
STICK_L = 130.0         # total, 10 mm of it goes into the cuff
STICK_FLAT = 0.4        # flat cut on the side that lies on the bed
CLEAR = 0.2             # radial clearance stick/socket
CUFF_R = 6.2
CUFF_BELOW = 6.0        # cuff height under the wrist (it also goes 2 mm up into it)
BORE_DEPTH = 10.0
LUG_Z = (4.0, 6.0)      # lugs, measured from the cuff bottom once inserted
LUG_R = 4.0             # lug tip radius
GROOVE_R = 4.3
SLOT_HALF_W = 1.85
GROOVE_START, GROOVE_END = -25.0, 115.0  # degrees, slot at 0, lug ends at ~90
DETENT_ANGLE = 58.0     # bump the lug clicks over
DETENT_IN = 3.75        # bump reaches this radius (0.25 mm interference with the lug)
SEG = 96

MODEL = "3D/3dmodel.model"
HAND_OBJ = "3D/Objects/object_4.model"
STICK_OBJ = "3D/Objects/object_5.model"
RELS = "3D/_rels/3dmodel.model.rels"
SETTINGS = "Metadata/model_settings.config"


def M(v, f):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f, np.uint32)))


def T(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False)


def revolve(points, degrees=360.0):
    """Revolve an (r, z) outline about the z axis."""
    return mf.CrossSection([points]).revolve(SEG, degrees)


def socket():
    """Everything cut out of the hand, axis z, cuff bottom at z=0."""
    br = STICK_D / 2 + CLEAR
    bore = revolve([(0, -1), (br + 0.8, -1), (br + 0.8, 0), (br, 0.6), (br, BORE_DEPTH), (0, BORE_DEPTH + br)])
    g0, g1 = LUG_Z[0] - 0.2, LUG_Z[1] + 0.4
    slots = mf.Manifold.cube((2 * GROOVE_R, 2 * SLOT_HALF_W, g1 + 1)).translate((-GROOVE_R, -SLOT_HALF_W, -1))
    # 45 deg ceiling so nothing in the socket needs support when the hand prints upright
    groove = revolve([(0, g0), (GROOVE_R, g0), (GROOVE_R, g1), (br, g1 + GROOVE_R - br), (0, g1 + GROOVE_R - br)],
                     GROOVE_END - GROOVE_START).rotate((0, 0, GROOVE_START))
    groove = groove + groove.rotate((0, 0, 180))
    bump_r = 0.5
    bump = mf.Manifold.cylinder(g1 + 3, bump_r, bump_r, 24).translate((DETENT_IN + bump_r, 0, 0))
    bumps = mf.Manifold.batch_boolean([bump.rotate((0, 0, DETENT_ANGLE + k)) for k in (0, 180)], mf.OpType.Add)
    return bore + slots + (groove - bumps)


def stick():
    """Stick in socket coordinates (fully inserted, lugs at 0/180 deg = entry position)."""
    r = STICK_D / 2
    body = revolve([(0, BORE_DEPTH - STICK_L), (r - 0.6, BORE_DEPTH - STICK_L), (r, BORE_DEPTH - STICK_L + 0.6),
                    (r, BORE_DEPTH - 0.5), (r - 0.5, BORE_DEPTH), (0, BORE_DEPTH)])
    # lug: radial x, tangential y (y < 0 faces the bed when printed, 45 deg underside)
    lug = mf.CrossSection([[(r - 0.4, -1.6), (LUG_R, -0.2), (LUG_R, 1.2), (r - 0.4, 1.2)]]).extrude(LUG_Z[1] - LUG_Z[0])
    lug = lug.translate((0, 0, LUG_Z[0]))
    s = body + lug + lug.rotate((0, 0, 180))
    flat = mf.Manifold.cube((20, 20, STICK_L + 10)).translate((-10, -r + STICK_FLAT, BORE_DEPTH - STICK_L - 5))
    return s ^ flat


def load_hand(src):
    obj = zipfile.ZipFile(src).read(HAND_OBJ).decode()
    v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', obj), float) * HAND_SCALE
    f = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', obj), int)
    fix = pymeshfix.MeshFix(v, f)  # the scan has ~100 tiny non-manifold spots, close them so booleans work
    fix.repair()
    return np.asarray(fix.points), np.asarray(fix.faces).reshape(-1, 3)


def build(src):
    v, f = load_hand(src)
    z_min = v[:, 2].min()
    wrist = v[v[:, 2] < z_min + 0.5]
    cx, cy = (wrist[:, :2].min(0) + wrist[:, :2].max(0)) / 2
    h = CUFF_BELOW + 2
    cuff = revolve([(0, 0), (CUFF_R - 0.6, 0), (CUFF_R, 0.6), (CUFF_R, h - 1.2), (CUFF_R - 1.2, h), (0, h)])
    place = lambda m: m.translate((cx, cy, z_min - CUFF_BELOW))
    hand = (M(v, f) + place(cuff)) - place(socket())
    return hand, place(stick()), (cx, cy, z_min - CUFF_BELOW)


def fit_checks(hand, stk, axis):
    """Boolean interference tests of the lock."""
    cx, cy, _ = axis
    turn = lambda m, deg, dz=0.0: m.translate((-cx, -cy, 0)).rotate((0, 0, deg)).translate((cx, cy, dz))
    vol = lambda deg, dz=0.0: (hand ^ turn(stk, deg, dz)).volume()
    sweep = {deg: vol(deg) for deg in range(0, 96, 5)}
    res = {
        "insert straight (0 deg)": vol(0),
        "slide in from 12 mm out": max(vol(0, -dz) for dz in (2, 6, 12)),
        "locked (90 deg)": vol(90),
        "detent bump (55-62 deg)": max(vol(d) for d in (55, 58, 62)),
        "pull out when locked": vol(90, -1.0),
        "turn past the stop (100 deg)": vol(100),
    }
    for k, val in res.items():
        print(f"  {k:30s} interference {val:7.3f} mm3")
    print("  sweep 0-95 deg:", " ".join(f"{d}:{x:.2f}" for d, x in sweep.items()))
    assert res["insert straight (0 deg)"] < 1e-3 and res["locked (90 deg)"] < 1e-3 and res["slide in from 12 mm out"] < 1e-3
    assert res["detent bump (55-62 deg)"] > 0.01 and res["pull out when locked"] > 1 and res["turn past the stop (100 deg)"] > 0.01


def mesh_xml(oid, uuid, m):
    return "\n".join(
        [f'  <object id="{oid}" p:UUID="{uuid}" type="model">', "   <mesh>", "    <vertices>"]
        + [f'     <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in m.vertices]
        + ["    </vertices>", "    <triangles>"]
        + [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces]
        + ["    </triangles>", "   </mesh>", "  </object>"]
    )


def write_3mf(src, out, hand, stk):
    zin = zipfile.ZipFile(src)
    head = zin.read(HAND_OBJ).decode().split(" <resources>")[0]
    sub = lambda body: f"{head} <resources>\n{body}\n </resources>\n <build/>\n</model>\n"
    hand_obj = sub(mesh_xml(1, "00010000-81cb-4c03-9d28-80fed5dfa1dc", hand))
    stick_obj = sub(mesh_xml(3, "00030000-81cb-4c03-9d28-80fed5dfa1dc", stk))

    model = zin.read(MODEL).decode()
    model = model.replace(" </resources>", (
        '  <object id="4" p:UUID="00000005-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n   <components>\n'
        '    <component p:path="/3D/Objects/object_5.model" objectid="3" p:UUID="00050000-b206-40ff-9872-83e8017abed1" '
        'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n   </components>\n  </object>\n </resources>'))
    model = re.sub(r'(<item objectid="2" [^>]*transform=")[^"]+"', r'\g<1>1 0 0 0 1 0 0 0 1 0 0 0"', model)
    model = model.replace(" </build>", (
        '  <item objectid="4" p:UUID="00000004-b1ec-4553-aec9-835e5b724bb4" transform="1 0 0 0 1 0 0 0 1 0 0 0" '
        'printable="1"/>\n </build>'))

    rels = zin.read(RELS).decode().replace("</Relationships>", (
        '<Relationship Target="/3D/Objects/object_5.model" Id="rel-5" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>'))

    settings = zin.read(SETTINGS).decode()
    settings = settings.replace('value="quant_1"', 'value="hand_socket"')
    settings = re.sub(r'\s*<metadata key="source_\w+" value="[^"]*"/>', "", settings)
    settings = settings.replace('    <metadata key="seam_position" value="back"/>', (
        '    <metadata key="seam_position" value="back"/>\n'
        '    <metadata key="brim_type" value="outer_only"/>\n    <metadata key="brim_width" value="4"/>'), 1)
    settings = settings.replace("  <plate>", (
        '  <object id="4">\n    <metadata key="name" value="stick"/>\n    <metadata key="enable_support" value="0"/>\n'
        '    <metadata key="extruder" value="1"/>\n    <part id="3" subtype="normal_part">\n'
        '      <metadata key="name" value="stick"/>\n'
        '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
        '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
        '    </part>\n  </object>\n  <plate>'))
    settings = settings.replace("  </plate>", (
        '    <model_instance>\n      <metadata key="object_id" value="4"/>\n      <metadata key="instance_id" value="0"/>\n'
        '      <metadata key="identify_id" value="189"/>\n    </model_instance>\n  </plate>'))
    settings = re.sub(r'(assemble_item [^>]*transform=")[^"]+"', r'\g<1>1 0 0 0 1 0 0 0 1 0 0 0"', settings)
    settings = settings.replace("  </assemble>", (
        '   <assemble_item object_id="4" instance_id="0" transform="1 0 0 0 1 0 0 0 1 0 0 0" offset="0 0 0" />\n'
        '  </assemble>'))

    files = {MODEL: model, HAND_OBJ: hand_obj, RELS: rels, SETTINGS: settings}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = files.get(item.filename)
            zout.writestr(item, data.encode() if data is not None else zin.read(item.filename))
        zout.writestr(STICK_OBJ, stick_obj)


def main(src, out_dir):
    hand, stk, axis = build(src)
    print("fit checks:")
    fit_checks(hand, stk, axis)

    cx, cy, z0 = axis
    hand_t = T(hand)
    hand_t.apply_translation((50 - cx, 107.5 - cy, -z0))  # upright, cuff on the bed
    stick_t = T(stk.translate((-cx, -cy, 0)))
    # lay the stick down: its axis along X, lugs sideways, flat side on the bed
    stick_t.apply_transform(np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
    lo, hi = stick_t.bounds
    stick_t.apply_translation((145 - (lo[0] + hi[0]) / 2, 107.5 - (lo[1] + hi[1]) / 2, -lo[2]))
    for m in (hand_t, stick_t):
        assert m.is_watertight and m.volume > 0

    os.makedirs(out_dir, exist_ok=True)
    hand_t.export(os.path.join(out_dir, "hand_socket.stl"))
    stick_t.export(os.path.join(out_dir, "stick.stl"))
    write_3mf(src, os.path.join(out_dir, "twist_lock.3mf"), hand_t, stick_t)
    print("hand", np.round(hand_t.extents, 1).tolist(), "stick", np.round(stick_t.extents, 1).tolist())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
