"""
Creality Print project (.3mf) writer for the Creality K2 SE - used by trophy_blender.py

Writes a ready-to-print project: coloured filaments, objects assigned to filaments,
painted (two-colour) triangles, one plate per print job and the K2 SE system presets
with a few tuned settings marked as "changed", exactly like Creality Print 6/7 saves them.

The K2 SE base settings come from k2se_settings.json, flattened from the official
Creality Print profiles. To rebuild that file from a Creality Print source checkout:
    python3 k2se_3mf.py <crealityprint>/resources/profiles/Creality <template project_settings.config>
"""
import json
import os
import sys
import uuid
import zipfile

import numpy as np

PRINTER = "Creality K2 SE 0.4 nozzle"
PROCESS = "0.16mm Standard @Creality K2 SE 0.4 nozzle"
FILAMENT = "CR-Silk @Creality K2 SE 0.4 nozzle"
BED = (220.0, 215.0)
PLATE_GAP = 1.0 / 5.0                   # Creality Print draws plates side by side with this gap

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "k2se_settings.json")
APP_VERSION = "7.0.0.0"
META_KEYS = {"type", "name", "inherits", "from", "instantiation", "setting_id", "filament_id",
             "compatible_printers", "compatible_printers_condition", "compatible_prints",
             "compatible_prints_condition", "version", "description", "renamed_from"}


# ----------------------------------------------------------------- SETTINGS
def _flatten(folder, name):
    """Profile values after resolving the 'inherits' chain (parent first)."""
    path = os.path.join(folder, name + ".json")
    with open(path, encoding="utf-8") as f:
        prof = json.load(f)
    out = _flatten(folder, prof["inherits"]) if prof.get("inherits") else {}
    out.update({k: v for k, v in prof.items() if k not in META_KEYS})
    return out


def build_settings(profiles_dir, template_path, out_path=SETTINGS_FILE):
    """Full project config for 2 filaments: a Creality Print project as template for the
    key set, every key the K2 SE system profiles define overwritten with their values."""
    with open(template_path, encoding="utf-8") as f:
        cfg = json.load(f)
    machine = _flatten(os.path.join(profiles_dir, "machine"), PRINTER)
    process = _flatten(os.path.join(profiles_dir, "process"), PROCESS)
    filament = _flatten(os.path.join(profiles_dir, "filament"), FILAMENT)
    for src in (machine, process):
        for k, v in src.items():
            if isinstance(cfg.get(k), list) and not isinstance(v, list):
                v = [v]
            cfg[k] = v
    for k, v in filament.items():
        v = v[0] if isinstance(v, list) and len(v) == 1 else v
        cfg[k] = [v, v] if not isinstance(v, list) else v
    cfg.update({
        "printer_settings_id": PRINTER, "print_settings_id": PROCESS,
        "filament_settings_id": [FILAMENT, FILAMENT],
        "printer_model": "Creality K2 SE", "printer_variant": "0.4",
        "print_compatible_printers": [PRINTER],
        "filament_ids": [_raw(profiles_dir, FILAMENT)["filament_id"]] * 2,
        "from": "project", "name": "project_settings", "version": APP_VERSION,
    })
    for k in ("inherits", "inherits_group", "different_settings_to_system"):
        cfg.pop(k, None)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, sort_keys=True)
    return cfg


def _raw(profiles_dir, name):
    with open(os.path.join(profiles_dir, "filament", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def project_settings(colours, overrides, flush, towers):
    """K2 SE system presets + overrides (listed as changed so Creality Print keeps them)."""
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.update(overrides)
    cfg["filament_colour"] = list(colours)
    cfg["flush_volumes_matrix"] = [str(v) for v in flush]
    cfg["wipe_tower_x"] = [str(t[0]) for t in towers]
    cfg["wipe_tower_y"] = [str(t[1]) for t in towers]
    cfg["inherits_group"] = ["", "", "", ""]
    cfg["different_settings_to_system"] = [";".join(sorted(overrides)), "", "", ""]
    return cfg


# ----------------------------------------------------------------- 3MF
def plate_origin(index, count):
    """Lower-left corner of plate `index` (0-based) as laid out by Creality Print."""
    v = count ** 0.5
    cols = int(round(v)) + (1 if v > round(v) else 0)
    row, col = divmod(index, cols)
    return np.array([col * BED[0] * (1 + PLATE_GAP), -row * BED[1] * (1 + PLATE_GAP), 0.0])


def _uuid(*key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "/".join(map(str, key))))


def _mesh_xml(oid, verts, tris, paint):
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
            'requiredextensions="p">',
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
            ' <resources>',
            f'  <object id="{oid}" p:UUID="{_uuid("mesh", oid)}" type="model">',
            '   <mesh>', '    <vertices>']
    rows += [f'     <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in verts]
    rows += ['    </vertices>', '    <triangles>']
    for i, (a, b, c) in enumerate(tris):
        p = f' paint_color="{paint[i]}"' if paint is not None and paint[i] else ""
        rows.append(f'     <triangle v1="{a}" v2="{b}" v3="{c}"{p}/>')
    rows += ['    </triangles>', '   </mesh>', '  </object>', ' </resources>', ' <build/>',
             '</model>']
    return "\n".join(rows)


def write_project(path, plates, filaments, overrides, flush, title, thumbnails=()):
    """plates: [(plate name, [part, ...])], part = dict(name, verts, tris, extruder,
    xy (centre on the plate), paint (per triangle '' / '4' / '8' ...), settings {key: value},
    assembly (4x4 matrix for the assembly view)). filaments: [(name, '#RRGGBB')]."""
    objects, oid = [], 0
    for p_idx, (_, parts) in enumerate(plates):
        origin = plate_origin(p_idx, len(plates))
        for part in parts:
            v = np.asarray(part["verts"], float)
            lo, hi = v.min(0), v.max(0)
            centre = (lo + hi) / 2
            oid += 2
            objects.append(dict(part, id=oid, mesh_id=oid - 1, plate=p_idx + 1,
                                local=v - centre, centre=centre,
                                pos=origin + [part["xy"][0], part["xy"][1], (hi[2] - lo[2]) / 2]))

    model = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
             'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
             'requiredextensions="p">',
             f' <metadata name="Application">Creality_Print V{APP_VERSION}</metadata>',
             ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
             f' <metadata name="Title">{title}</metadata>',
             ' <metadata name="Thumbnail_Middle">/Metadata/plate_1.png</metadata>',
             ' <metadata name="Thumbnail_Small">/Metadata/plate_1_small.png</metadata>',
             ' <resources>']
    for o in objects:
        model += [f'  <object id="{o["id"]}" p:UUID="{_uuid("obj", o["id"])}" type="model">',
                  '   <components>',
                  f'    <component p:path="/3D/Objects/object_{o["id"]}.model" '
                  f'objectid="{o["mesh_id"]}" p:UUID="{_uuid("cmp", o["id"])}" '
                  'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>',
                  '   </components>', '  </object>']
    model += [' </resources>', f' <build p:UUID="{_uuid("build")}">']
    for o in objects:
        x, y, z = o["pos"]
        model.append(f'  <item objectid="{o["id"]}" p:UUID="{_uuid("item", o["id"])}" '
                     f'transform="1 0 0 0 1 0 0 0 1 {x:.4f} {y:.4f} {z:.4f}" printable="1"/>')
    model += [' </build>', '</model>']

    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>']
    for o in objects:
        cfg += [f'  <object id="{o["id"]}">',
                f'    <metadata key="name" value="{o["name"]}"/>',
                f'    <metadata key="extruder" value="{o["extruder"]}"/>']
        cfg += [f'    <metadata key="{k}" value="{v}"/>' for k, v in o.get("settings", {}).items()]
        cfg += [f'    <part id="{o["mesh_id"]}" subtype="normal_part">',
                f'      <metadata key="name" value="{o["name"]}"/>',
                '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>',
                '      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" '
                'facets_reversed="0" backwards_edges="0"/>',
                '    </part>', '  </object>']
    for p_idx, (name, _) in enumerate(plates):
        n = p_idx + 1
        cfg += ['  <plate>', f'    <metadata key="plater_id" value="{n}"/>',
                f'    <metadata key="plater_name" value="{name}"/>',
                '    <metadata key="locked" value="false"/>']
        if n <= len(thumbnails):
            cfg.append(f'    <metadata key="thumbnail_file" value="Metadata/plate_{n}.png"/>')
        for o in objects:
            if o["plate"] == n:
                cfg += ['    <model_instance>',
                        f'      <metadata key="object_id" value="{o["id"]}"/>',
                        '      <metadata key="instance_id" value="0"/>',
                        f'      <metadata key="identify_id" value="{100 + o["id"]}"/>',
                        '    </model_instance>']
        cfg.append('  </plate>')
    cfg.append('  <assemble>')
    for o in objects:
        m = np.asarray(o.get("assembly", np.eye(4)), float).copy()
        m[:3, 3] += m[:3, :3] @ o["centre"]            # meshes are stored centred
        t = " ".join(f"{v:.6g}" for v in list(m[:3, :3].T.ravel()) + list(m[:3, 3]))
        cfg.append(f'   <assemble_item object_id="{o["id"]}" instance_id="0" '
                   f'transform="{t}" offset="0 0 0" />')
    cfg += ['  </assemble>', '</config>']

    settings = project_settings([c for _, c in filaments], overrides, flush,
                                [(150, 150)] * len(plates))
    rels_model = ['<?xml version="1.0" encoding="UTF-8"?>',
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    rels_model += [f' <Relationship Target="/3D/Objects/object_{o["id"]}.model" Id="rel-{i + 1}" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                   for i, o in enumerate(objects)]
    rels_model.append('</Relationships>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
            + (' <Relationship Target="/Metadata/plate_1.png" Id="rel-4" '
               'Type="http://schemas.bambulab.com/package/2021/cover-thumbnail-middle"/>\n'
               if thumbnails else '') +
            '</Relationships>')
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
             ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
             ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
             ' <Default Extension="png" ContentType="image/png"/>\n'
             ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n'
             '</Types>')
    creality = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
                '    <metadata key="Company" value="Creality"/>\n'
                '    <metadata key="Application" value="Creality_Print"/>\n'
                f'    <metadata key="AppVersion" value="{APP_VERSION}"/>\n'
                '    <metadata key="FileVersion" value="1.0"/>\n</config>')
    custom_gcode = ('<?xml version="1.0" encoding="utf-8"?>\n<custom_gcodes_per_layer>\n'
                    + "".join(f'<plate>\n<plate_info id="{i + 1}"/>\n<mode value="MultiExtruder"/>\n</plate>\n'
                              for i in range(len(plates)))
                    + '</custom_gcodes_per_layer>')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "\n".join(model))
        z.writestr("3D/_rels/3dmodel.model.rels", "\n".join(rels_model))
        for o in objects:
            z.writestr(f"3D/Objects/object_{o['id']}.model",
                       _mesh_xml(o["mesh_id"], o["local"], o["tris"], o.get("paint")))
        z.writestr("Metadata/model_settings.config", "\n".join(cfg))
        z.writestr("Metadata/project_settings.config", json.dumps(settings, indent=4))
        z.writestr("Metadata/creality.config", creality)
        z.writestr("Metadata/custom_gcode_per_layer.xml", custom_gcode)
        for i, png in enumerate(thumbnails):
            z.write(png, f"Metadata/plate_{i + 1}.png")
    return objects


if __name__ == "__main__":
    build_settings(sys.argv[1], sys.argv[2])
    print("wrote", SETTINGS_FILE)
