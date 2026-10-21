"""Add a hand-held stick under a 3MF model so it can be lifted like a sign.

Usage: python3 add_stick.py input.3mf output.3mf

The stick is added as a second part of the same object (the slicer merges the
two parts), so the model keeps its own mesh, paint and print settings, and the
stick scales with it if the object is rescaled in the slicer.
All sizes below are in mm at the scale the object has on the plate.
"""
import re
import sys
import zipfile

import numpy as np

STICK_LENGTH = 120.0  # visible length below the wrist
TOP_DIAMETER = 8.0    # where it meets the wrist (wrist is ~11.6 x 9.3 mm)
GRIP_DIAMETER = 12.0  # handle thickness at the bottom
KNOB_DIAMETER = 16.0  # rounded end, stops the hand slipping off, bigger bed contact
KNOB_HEIGHT = 8.0
INSERT_DEPTH = 6.0    # how far the stick goes up inside the wrist (hidden)
SEGMENTS = 64

MODEL = "3D/3dmodel.model"
OBJ = "3D/Objects/object_4.model"
SETTINGS = "Metadata/model_settings.config"


def revolve(profile, segments):
    """Closed mesh from a (radius, z) profile ordered top to bottom."""
    a = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    rings = [np.c_[r * np.cos(a), r * np.sin(a), np.full(segments, z)] for r, z in profile]
    verts = list(np.vstack(rings))
    faces = []
    for i in range(len(profile) - 1):
        for j in range(segments):
            k = (j + 1) % segments
            p, q = i * segments, (i + 1) * segments
            faces += [(p + j, q + j, q + k), (p + j, q + k, p + k)]
    top, bottom = len(verts), len(verts) + 1
    verts += [(0, 0, profile[0][1]), (0, 0, profile[-1][1])]
    last = (len(profile) - 1) * segments
    for j in range(segments):
        k = (j + 1) % segments
        faces += [(top, j, k), (bottom, last + k, last + j)]
    return np.array(verts), np.array(faces)


def main(src, dst):
    zin = zipfile.ZipFile(src)
    model = zin.read(MODEL).decode()
    obj = zin.read(OBJ).decode()
    settings = zin.read(SETTINGS).decode()

    m = re.search(r'<item objectid="2" ([^>]*)transform="([^"]+)"', model)
    t = np.array(m.group(2).split(), dtype=float)
    scale = t[0]

    v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', obj), dtype=float) * scale
    z_min = v[:, 2].min()
    wrist = v[v[:, 2] < z_min + 0.5]
    cx, cy = (wrist[:, :2].min(0) + wrist[:, :2].max(0)) / 2

    rt, rg, rk = TOP_DIAMETER / 2, GRIP_DIAMETER / 2, KNOB_DIAMETER / 2
    z_bot = z_min - STICK_LENGTH
    z_knob = z_bot + KNOB_HEIGHT
    profile = [(rt - 1, z_min + INSERT_DEPTH), (rt, z_min + INSERT_DEPTH - 1), (rt, z_min)]
    profile += [(rt + (rg - rt) * f, z_min + (z_knob - z_min) * f) for f in (0.25, 0.5, 0.75, 1.0)]
    for ang in np.linspace(0, np.pi / 2, 7)[1:]:  # rounded knob
        profile.append((rg + (rk - rg) * np.sin(ang), z_knob - (KNOB_HEIGHT - 2) * (1 - np.cos(ang))))
    profile += [(rk, z_bot + 1), (rk - 1, z_bot)]  # small chamfer against elephant foot
    sv, sf = revolve(profile, SEGMENTS)
    sv[:, 0] += cx
    sv[:, 1] += cy
    sv /= scale  # back into the object's unscaled coordinates

    stick = "\n".join(
        ['  <object id="2" p:UUID="00020000-81cb-4c03-9d28-80fed5dfa1dc" type="model">', "   <mesh>", "    <vertices>"]
        + [f'     <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in sv]
        + ["    </vertices>", "    <triangles>"]
        + [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in sf]
        + ["    </triangles>", "   </mesh>", "  </object>", " </resources>"]
    )
    obj = obj.replace(" </resources>", stick, 1)

    # Bambu/Creality layout: parts 1..n in the sub-model, assembled object gets id n+1.
    model = model.replace('<object id="2" ', '<object id="3" ')
    model = model.replace(
        "   </components>",
        '    <component p:path="/3D/Objects/object_4.model" objectid="2" '
        'p:UUID="00040001-b206-40ff-9872-83e8017abed1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n   </components>',
    )
    model = model.replace('<item objectid="2" ', '<item objectid="3" ')
    lift = -z_bot  # new bottom sits on the bed
    model = re.sub(r'(<item objectid="3" [^>]*transform="(?:\S+ ){11})\S+"', rf'\g<1>{lift:g}"', model)

    settings = settings.replace('<object id="2">', '<object id="3">')
    settings = settings.replace('value="quant_1"', 'value="hand_sign"', 1)
    settings = settings.replace(
        '    <metadata key="seam_position" value="back"/>',
        '    <metadata key="seam_position" value="back"/>\n'
        '    <metadata key="brim_type" value="outer_only"/>\n'
        '    <metadata key="brim_width" value="5"/>',
    )
    settings = settings.replace(
        "  </object>",
        '    <part id="2" subtype="normal_part">\n'
        '      <metadata key="name" value="stick"/>\n'
        '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
        '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
        "    </part>\n  </object>",
    )
    settings = settings.replace('key="object_id" value="2"', 'key="object_id" value="3"')
    settings = settings.replace('object_id="2" instance_id="0"', 'object_id="3" instance_id="0"')
    settings = re.sub(r'(assemble_item [^>]*transform="(?:\S+ ){11})\S+"', rf'\g<1>{lift:g}"', settings)

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = {MODEL: model, OBJ: obj, SETTINGS: settings}.get(item.filename)
            zout.writestr(item, data.encode() if data is not None else zin.read(item.filename))

    print(f"stick centred at ({cx:.2f}, {cy:.2f}), wrist bottom z={z_min:.2f}, total height {-z_bot + v[:, 2].max():.1f} mm")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
