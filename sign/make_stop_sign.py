"""Turn the hand 3MF into a stop-sign paddle: red octagon, white border, the hand as a white relief, and a handle.

Usage: python3 make_stop_sign.py original_hand.3mf out_dir

Writes stop_sign.3mf (Creality K2 SE project from the original file, with a colour change set
where the white starts) and stop_sign.stl. Printed flat: back of the sign on the bed, hand on top.
All sizes in mm.
"""
import os
import re
import sys
import zipfile

import manifold3d as mf
import numpy as np
import trimesh
from scipy import ndimage
from skimage import measure

SIGN_WIDTH = 130.0     # octagon, flat to flat (flat top like a real stop sign)
PLATE_T = 5.0          # red plate thickness
BORDER_INSET = 2.5     # white border distance from the edge
BORDER_W = 4.5
BORDER_H = 1.2         # raised above the plate
HAND_HEIGHT = 92.0     # hand relief, wrist to fingertip
HAND_OFFSET_Y = -2.0   # nudge the hand down a little in the octagon
RELIEF_MIN = 1.6       # thinnest part of the hand above the plate (the raised finger, it is furthest back)
RELIEF_MAX = 6.0       # knuckles
GRIP_W, GRIP_T, GRIP_L = 22.0, 11.0, 100.0  # handle cross-section and length
JOINT_L = 28.0         # tapered neck between handle and sign
JOINT_W = 46.0         # neck width where it enters the sign
RES = 0.25             # relief resolution
BED = (220.0, 215.0)

MODEL = "3D/3dmodel.model"
OBJ = "3D/Objects/object_4.model"
SETTINGS = "Metadata/model_settings.config"
GCODES = "Metadata/custom_gcode_per_layer.xml"


def octagon(apothem):
    r = apothem / np.cos(np.pi / 8)
    a = np.pi / 8 + np.arange(8) * np.pi / 4
    return mf.CrossSection([np.c_[r * np.cos(a), r * np.sin(a)]])


def to_manifold(v, f):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f, np.uint32)))


def hand_relief(v, f):
    """White relief of the palm side (the side seen from +y), as a heightfield lofted from the plate."""
    tri_c = v[f].mean(1)
    pts = np.vstack([v, tri_c])
    s = HAND_HEIGHT / np.ptp(v[:, 2])
    u, w, depth = -pts[:, 0] * s, pts[:, 2] * s, pts[:, 1] * s  # viewed from +y: right = -x, up = z
    u0, w0 = u.min(), w.min()
    i = ((u - u0) / RES).astype(int)
    j = ((w - w0) / RES).astype(int)
    H = np.full((i.max() + 1, j.max() + 1), -np.inf)
    np.maximum.at(H, (i, j), depth)
    seen = np.isfinite(H)
    mask = ndimage.binary_fill_holes(ndimage.binary_closing(seen, iterations=2))
    _, (ni, nj) = ndimage.distance_transform_edt(~seen, return_indices=True)
    H = ndimage.gaussian_filter(H[ni, nj], 1.0)
    dn = (H - H[mask].min()) / np.ptp(H[mask])
    h = RELIEF_MIN + (RELIEF_MAX - RELIEF_MIN) * np.clip(dn, 0, 1) ** 0.8

    sd = (ndimage.distance_transform_edt(mask) - ndimage.distance_transform_edt(~mask)) * RES
    sd = ndimage.gaussian_filter(sd, 1.0)
    z = np.arange(-1.0, RELIEF_MAX + 1.0, RES)  # relative to plate top
    vol = np.minimum(np.minimum(sd[..., None], h[..., None] - z), z - (-0.5))
    vol = np.pad(vol, 1, constant_values=-1.0)
    mv, mfaces, _, _ = measure.marching_cubes(vol, 0.0)
    mv = (mv - 1) * RES
    mv[:, 0] += u0 - (u0 + u.max()) / 2
    mv[:, 1] += w0 - (w0 + w.max()) / 2 + HAND_OFFSET_Y
    mv[:, 2] += z[0] + PLATE_T
    m = trimesh.Trimesh(mv, mfaces)
    m.merge_vertices()
    if m.volume < 0:
        m.invert()
    return to_manifold(m.vertices, m.faces)


def handle_section(width, thick):
    r = min(4.0, thick / 2 - 0.01)
    rounded = mf.CrossSection.square((width, 2 * thick), center=True).offset(-r, mf.JoinType.Round).offset(r, mf.JoinType.Round)
    return rounded ^ mf.CrossSection.square((width, thick)).translate((-width / 2, 0))


def slab(section, y, length=0.01):
    """Extrude an (x, z) section along -y starting at y."""
    return section.extrude(length).rotate((90, 0, 0)).translate((0, y, 0))


def build(v, f):
    a = SIGN_WIDTH / 2
    plate = octagon(a).extrude(PLATE_T)
    border = (octagon(a - BORDER_INSET) - octagon(a - BORDER_INSET - BORDER_W)).extrude(BORDER_H + 0.5).translate((0, 0, PLATE_T - 0.5))
    grip = handle_section(GRIP_W, GRIP_T)
    y_grip = -a - JOINT_L
    neck = mf.Manifold.hull(mf.Manifold.batch_boolean(
        [slab(handle_section(JOINT_W, PLATE_T), -a + 6), slab(grip, y_grip)], mf.OpType.Add))
    bar = slab(grip, y_grip, GRIP_L - 3)
    end = mf.Manifold.hull(slab(grip, y_grip - GRIP_L + 3) + slab(handle_section(GRIP_W - 4, GRIP_T - 2), y_grip - GRIP_L))
    sign = mf.Manifold.batch_boolean([plate, border, neck, bar, end, hand_relief(v, f)], mf.OpType.Add)
    m = sign.to_mesh()
    return trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts)


def fit_on_bed(mesh):
    """Turn the sign (it is longer than the bed) to the angle that fits with the most margin, centred."""
    best = None
    hull = mesh.convex_hull.vertices
    for deg in np.arange(0, 90.5, 0.5):
        r = trimesh.transformations.rotation_matrix(np.radians(deg), (0, 0, 1))
        ext = np.ptp(trimesh.transform_points(hull, r)[:, :2], axis=0)
        margin = min(BED[0] - ext[0], BED[1] - ext[1])
        if best is None or margin > best[0]:
            best = (margin, deg, r)
    margin, deg, r = best
    assert margin > 4, f"sign does not fit on the bed (margin {margin:.1f} mm)"
    mesh.apply_transform(r)
    lo, hi = mesh.bounds
    mesh.apply_translation((BED[0] / 2 - (lo[0] + hi[0]) / 2, BED[1] / 2 - (lo[1] + hi[1]) / 2, -lo[2]))
    return deg, margin


def main(src, out_dir):
    zin = zipfile.ZipFile(src)
    obj = zin.read(OBJ).decode()
    v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', obj), float)
    f = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', obj), int)

    sign = build(v, f)
    assert sign.is_watertight
    deg, margin = fit_on_bed(sign)
    os.makedirs(out_dir, exist_ok=True)
    sign.export(os.path.join(out_dir, "stop_sign.stl"))

    mesh_xml = "\n".join(
        ["    <vertices>"]
        + [f'     <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in sign.vertices]
        + ["    </vertices>", "    <triangles>"]
        + [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in sign.faces]
        + ["    </triangles>"]
    )
    obj = re.sub(r"    <vertices>.*</triangles>", lambda _: mesh_xml, obj, flags=re.S)

    model = zin.read(MODEL).decode()
    model = re.sub(r'(<item objectid="2" [^>]*transform=")[^"]+"', r'\g<1>1 0 0 0 1 0 0 0 1 0 0 0"', model)

    settings = zin.read(SETTINGS).decode()
    settings = settings.replace('value="quant_1"', 'value="stop_sign"')
    settings = settings.replace('<metadata key="enable_support" value="1"/>', '<metadata key="enable_support" value="0"/>')
    settings = re.sub(r'\s*<metadata key="source_\w+" value="[^"]*"/>', "", settings)
    settings = re.sub(r'(assemble_item [^>]*transform=")[^"]+"', r'\g<1>1 0 0 0 1 0 0 0 1 0 0 0"', settings)

    first_white = PLATE_T + 0.2  # 0.2 mm layers: plate is red, everything above it white
    gcodes = (
        '<?xml version="1.0" encoding="utf-8"?>\n<custom_gcodes_per_layer>\n<plate>\n<plate_info id="1"/>\n'
        f'<layer top_z="{first_white:g}" type="0" extruder="1" color="#FFFFFF" extra="" gcode="M600"/>\n'
        '<mode value="SingleExtruder"/>\n</plate>\n</custom_gcodes_per_layer>\n'
    )

    out = os.path.join(out_dir, "stop_sign.3mf")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = {MODEL: model, OBJ: obj, SETTINGS: settings, GCODES: gcodes}.get(item.filename)
            zout.writestr(item, data.encode() if data is not None else zin.read(item.filename))

    print(f"{len(sign.faces)} triangles, size {np.round(sign.extents, 1).tolist()} mm, "
          f"turned {deg:g} deg on the bed ({margin:.1f} mm spare), colour change at z={first_white:g}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
