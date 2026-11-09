"""Stylized standing dog figure on the black round base (like a collectible statue).

python3 statue/make_dog.py      -> stl/statue_dog.stl, stl/statue_dog_on_base.3mf, images/statue_dog_preview.png

Modeled after photos of the dog standing (side / 3/4 view): long snout, floppy ears, fluffy chest and the
big tail curled over the back. Built from smooth blended shapes (a signed distance field turned into a mesh
with marching cubes), so it is a smooth, toy-like figure, not a photo-real sculpture. Facing +x, paws flat
on z = 0, then set on statue/make_base.py's base.
"""
import os
import sys
import numpy as np
import trimesh
from skimage import measure

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "keychain"))

RES = 0.5           # grid step (mm)
K = 4.0             # blend radius between shapes (mm)
BASE_D = 150.0      # base diameter (mm): the dog is about 130 mm from nose to tail


def smin(a, b, k=K):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def sphere(p, c, r):
    return np.linalg.norm(p - np.array(c, np.float32), axis=-1) - r


def ellipsoid(p, c, radii):
    q = (p - np.array(c, np.float32)) / np.array(radii, np.float32)
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / np.array(radii, np.float32), axis=-1)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)


def capsule(p, a, b, ra, rb=None):
    """Rounded cone from a (radius ra) to b (radius rb)."""
    rb = ra if rb is None else rb
    a, b = np.array(a, np.float32), np.array(b, np.float32)
    pa, ba = p - a, b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)[..., None]
    return np.linalg.norm(pa - ba * h, axis=-1) - (ra + (rb - ra) * h[..., 0])


def dog_sdf(p):
    d = ellipsoid(p, (0, 0, 54), (31, 17, 17))                      # torso (sturdy, fluffy)
    d = smin(d, sphere(p, (22, 0, 52), 19.5), 5)                   # deep chest
    d = smin(d, ellipsoid(p, (28, 0, 44), (12, 13, 14)), 4)          # fluffy chest fur
    d = smin(d, sphere(p, (-23, 0, 55), 17), 5)                    # hips
    d = smin(d, capsule(p, (26, 0, 58), (39, 0, 80), 13, 11), 5)   # thick neck ruff
    d = smin(d, sphere(p, (43, 0, 86), 13.5), 4)                   # skull
    d = smin(d, capsule(p, (50, 0, 83), (61, 0, 79), 8.0, 5.8), 3) # snout (medium length)
    d = smin(d, sphere(p, (62.5, 0, 80.5), 4.0), 1.5)              # nose
    for s in (1, -1):
        d = smin(d, capsule(p, (40, s * 10.5, 95), (36, s * 15.5, 82), 3.6, 5.6), 2)  # floppy ears
        d = smin(d, capsule(p, (23, s * 8, 45), (25, s * 8, 6), 6.6, 5.6))           # front legs
        d = smin(d, ellipsoid(p, (27.5, s * 8, 3.8), (8, 6, 4.4)), 2.5)              # front paws
        d = smin(d, capsule(p, (-22, s * 9, 54), (-28, s * 9, 30), 10.5, 7))          # thighs
        d = smin(d, capsule(p, (-28, s * 9, 30), (-23, s * 9, 6), 6.4, 5.6), 3)      # hocks
        d = smin(d, ellipsoid(p, (-21, s * 9, 3.8), (8, 6, 4.4)), 2.5)               # back paws
    # big fluffy tail curled tight over the back
    c = np.array([-31.0, 0.0, 78.0])
    ang = np.radians(np.linspace(245, -10, 12))
    pts = [c + 11.5 * np.array([np.cos(a), 0, np.sin(a)]) for a in ang]
    rad = 7 + 4.5 * np.sin(np.linspace(0, np.pi, len(pts)))
    for i in range(len(pts) - 1):
        d = smin(d, capsule(p, pts[i], pts[i + 1], rad[i], rad[i + 1]), 3)
    for s in (1, -1):                                              # eye sockets
        d = np.maximum(d, -sphere(p, (53, s * 8.2, 89), 2.5))
    return np.maximum(d, -p[..., 2])                               # flat bottom: paws stand on z = 0


def dog_mesh():
    lo = np.array([-72.13, -30.07, -1.13], np.float32)    # off-grid, so no surface lies exactly on grid points
    hi = np.array([80, 30, 115], np.float32)
    axes = [np.arange(lo[i], hi[i] + RES, RES, dtype=np.float32) for i in range(3)]
    g = np.stack(np.meshgrid(*axes, indexing="ij"), -1)
    vol = dog_sdf(g.reshape(-1, 3)).reshape(g.shape[:3])
    vol = np.pad(vol, 1, constant_values=1.0)                       # outside on every side: closed surface
    v, f, _, _ = measure.marching_cubes(vol, 0.0, spacing=(RES, RES, RES))
    m = trimesh.Trimesh(v + lo - RES, f[:, ::-1], process=True)
    trimesh.smoothing.filter_taubin(m, iterations=10)
    m.fix_normals()
    return m


def main():
    import make_base
    import make_keychain as kc
    make_base.D = BASE_D                                            # wide enough for nose-to-tail length
    dog = dog_mesh()
    assert dog.is_watertight, "dog mesh is not closed"
    base = trimesh.creation.revolve(make_base.profile(), sections=256)
    top = base.bounds[1, 2]
    dog.apply_translation([-(dog.bounds[0, 0] + dog.bounds[1, 0]) / 2, 0, top - 0.6])  # paws sink 0.6 mm in
    out = os.path.join(ROOT, "stl")
    dog.export(os.path.join(out, "statue_dog.stl"))
    single = trimesh.boolean.union([base, dog], engine="manifold")
    single.export(os.path.join(out, "statue_dog_on_base.stl"))
    # 2 colors: black base (filament 2), dog in filament 1 (load golden / beige PLA there)
    kc.write_3mf(os.path.join(out, "statue_dog_on_base.3mf"), "Dog statue",
                 [("black_base", base, 2), ("dog", dog, 1)])
    print("dog", np.round(dog.extents, 1).tolist(), "mm, watertight", dog.is_watertight,
          "| statue", np.round(single.extents, 1).tolist(), "mm")
    preview(base, dog)


def preview(base, dog):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 6))
    for k, (elev, azim) in enumerate([(12, -70), (8, -10)]):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        for m, col in ((base, np.array([0.13, 0.13, 0.14])), (dog, np.array([0.93, 0.78, 0.52]))):
            mm = m.simplify_quadric_decimation(face_count=min(len(m.faces), 40000)) if len(m.faces) > 40000 else m
            light = np.clip(mm.face_normals @ np.array([0.4, -0.6, 0.7]), 0.1, 1)[:, None]
            ax.add_collection3d(Poly3DCollection(mm.triangles, facecolors=np.c_[col * (0.35 + 0.65 * light), np.ones(len(mm.faces))],
                                                 edgecolor="none"))
        ax.set_xlim(-78, 78); ax.set_ylim(-78, 78); ax.set_zlim(0, 156)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(os.path.join(ROOT, "images", "statue_dog_preview.png"), dpi=100, bbox_inches="tight")


if __name__ == "__main__":
    main()
