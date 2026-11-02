"""Trace a dark logo on a light background into an SVG with a transparent background.

python3 svg/raster_to_svg.py input.jpg output.svg [--threshold 128] [--color #000000] [--invert]

The image is upsampled 4x and lightly blurred, then the outlines are traced with sub-pixel accuracy
(marching squares on the anti-aliased grey edges), smoothed and simplified to 0.05 px. Shapes with holes use fill-rule evenodd. Specks under 20 px
are dropped. Coordinates stay in the original image's pixels; the viewBox is cropped to the logo with a
small margin. --invert traces light artwork on a dark background instead.
"""
import argparse
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from skimage import measure


def smooth_ring(xy, passes=2):
    """Chaikin corner cutting on a closed ring: removes the last pixel steps, keeps the shape."""
    for _ in range(passes):
        nxt = np.roll(xy, -1, 0)
        xy = np.concatenate([0.75 * xy + 0.25 * nxt, 0.25 * xy + 0.75 * nxt], 1).reshape(-1, 2)
    return xy


def trace(path, threshold=128, invert=False, min_px=20, upsample=4):
    g = np.array(Image.open(path).convert("L")).astype(np.float32)
    if invert:
        g = 255 - g
    # drop specks first (on the thresholded image), then trace the anti-aliased grey edges at the threshold
    ink = g < threshold
    lab, n = ndi.label(ink)
    keep = np.r_[False, ndi.sum(ink, lab, range(1, n + 1)) >= min_px][lab]
    near = ndi.binary_dilation(keep, iterations=2)
    g = np.where(near, g, 255)
    up = cv2.resize(g, None, fx=upsample, fy=upsample, interpolation=cv2.INTER_CUBIC)
    up = cv2.GaussianBlur(np.pad(up, 2, constant_values=255), (0, 0), 1.0)
    rings = []
    for c in measure.find_contours(up, threshold):
        if len(c) < 8:
            continue
        xy = np.c_[c[:, 1] - 2, c[:, 0] - 2] / upsample          # back to original pixels, y down
        xy = smooth_ring(xy[:-1])
        p = Polygon(xy).simplify(0.05)
        if p.is_valid and p.area > 1:
            rings.append(np.asarray(p.exterior.coords))
    return rings, g.shape


def to_svg(rings, color="#000000", margin=10):
    pts = np.concatenate(rings)
    x0, y0 = pts.min(0) - margin
    x1, y1 = pts.max(0) + margin
    d = " ".join("M" + " L".join(f"{x - x0:.2f},{y - y0:.2f}" for x, y in r[:-1]) + " Z" for r in rings)
    w, h = x1 - x0, y1 - y0
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}" '
            f'width="{w:.0f}" height="{h:.0f}">\n'
            f'  <path fill="{color}" fill-rule="evenodd" d="{d}"/>\n</svg>\n')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--threshold", type=float, default=128)
    ap.add_argument("--color", default="#000000")
    ap.add_argument("--invert", action="store_true")
    a = ap.parse_args()
    rings, shape = trace(a.input, a.threshold, a.invert)
    open(a.output, "w").write(to_svg(rings, a.color))
    print(f"{len(rings)} outlines -> {a.output}")
