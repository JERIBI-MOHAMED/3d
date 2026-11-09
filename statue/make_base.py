"""Round black display base for a pet statue (like a collectible figure stand).

python3 statue/make_base.py [diameter_mm]        -> stl/statue_base.stl, images/statue_base_preview.png

A wide disc with a rounded top edge and a slightly smaller raised step on top, made by revolving a profile.
Later, the dog model (from an image-to-3D tool) is placed on the step and joined to it.
"""
import os
import sys
import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

D = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0   # base diameter (mm)
H = 12.0          # main disc height
R_EDGE = 3.0      # rounded top edge of the main disc
STEP_IN = 5.0     # the top step is this much smaller in radius
STEP_H = 3.0      # top step height
R_STEP = 1.5      # rounded edge of the step
CHAMFER = 0.6     # small bottom chamfer (no elephant foot)


def arc(cx, cy, r, a0, a1, n=16):
    t = np.radians(np.linspace(a0, a1, n))
    return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]


def profile():
    R = D / 2
    Rs = R - STEP_IN
    pts = [(0, 0), (R - CHAMFER, 0), (R, CHAMFER), (R, H - R_EDGE)]
    pts += arc(R - R_EDGE, H - R_EDGE, R_EDGE, 0, 90).tolist()[1:]
    pts += [(Rs, H)]
    pts += [(Rs, H + STEP_H - R_STEP)]
    pts += arc(Rs - R_STEP, H + STEP_H - R_STEP, R_STEP, 0, 90).tolist()[1:]
    pts += [(0, H + STEP_H)]
    return np.array(pts, float)


def main():
    m = trimesh.creation.revolve(profile(), sections=256)
    assert m.is_volume
    out = os.path.join(ROOT, "stl", "statue_base.stl")
    m.export(out)
    print("base", np.round(m.extents, 1).tolist(), "mm, volume %.0f cm3" % (m.volume / 1000), "->", out)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(projection="3d")
    tri = m.triangles
    light = np.clip(m.face_normals @ np.array([0.3, -0.5, 0.8]), 0.15, 1)
    ax.add_collection3d(Poly3DCollection(tri, facecolors=np.c_[0.12 + 0.35 * light[:, None] * [1, 1, 1], np.ones(len(tri))], edgecolor="none"))
    r = D / 2
    ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(-r * 0.8, r * 0.8)
    ax.view_init(elev=22, azim=-60)
    ax.set_axis_off()
    ax.set_title(f"Statue base  Ø{D:.0f} x {H + STEP_H:.0f} mm")
    plt.savefig(os.path.join(ROOT, "images", "statue_base_preview.png"), dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()
