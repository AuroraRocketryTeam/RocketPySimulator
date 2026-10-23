"""
Puts a satellite screenshot with a yellow line drawn on it (Google Maps, north up) on the photo of the launch
site, and gives the vertices of the line in metres east/north of the launch point.

The screenshot is found on the site photo by normalized cross-correlation, trying every scale between
--min and --max metres per pixel (the drawn line is removed first). The vertices are the white dots with a
yellow ring that Google Maps draws; the order is the one of the line (nearest-neighbour chain from the first
end). Check the result on the picture it writes.

Usage:
    python FRED/FRED2.0/tools/safety/wind_limits/locate_screenshot.py <screenshot> <output>.csv
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import fftconvolve

HERE = Path(__file__).resolve().parent
FRED_DIR = HERE.parents[2]
sys.path.insert(0, str(FRED_DIR))
import fred_model as model  # noqa: E402


def grey(rgb):
    return rgb[..., :3].astype(float) @ [0.299, 0.587, 0.114]


def yellow_mask(rgb):
    r, g, b = (rgb[..., k].astype(int) for k in range(3))
    return (r > 190) & (g > 140) & (b < 110) & (r - b > 110)


def vertices(rgb):
    """Centres of the white dots ringed in yellow (the vertices drawn by Google Maps)."""
    r, g, b = (rgb[..., k].astype(int) for k in range(3))
    white = (r > 235) & (g > 235) & (b > 235)
    yellow = yellow_mask(rgb)
    labels, count = ndimage.label(white)
    found = []
    for k in range(1, count + 1):
        ys, xs = np.nonzero(labels == k)
        if not 8 <= len(ys) <= 300:
            continue
        cy, cx = ys.mean(), xs.mean()
        ring = yellow[max(int(cy) - 8, 0):int(cy) + 9, max(int(cx) - 8, 0):int(cx) + 9].sum()
        if ring > 15:
            found.append((cx, cy, len(ys)))
    # Google Maps draws big dots on the vertices and small ones on the midpoints
    sizes = np.array([f[2] for f in found])
    big = [f[:2] for f in found if f[2] >= 0.6 * sizes.max()]
    return np.array(big)


def chain(points):
    """Order the vertices along the line: start from an end (the point farthest from the others)."""
    points = list(map(tuple, points))
    start = max(points, key=lambda p: sorted(np.hypot(*(np.subtract(p, q))) for q in points)[1])
    ordered = [start]
    points.remove(start)
    while points:
        nearest = min(points, key=lambda q: np.hypot(*(np.subtract(ordered[-1], q))))
        ordered.append(nearest)
        points.remove(nearest)
    return np.array(ordered)


def ncc(image, template):
    template = template - template.mean()
    norm_t = np.sqrt((template ** 2).sum())
    ones = np.ones(template.shape)
    corr = fftconvolve(image, template[::-1, ::-1], mode="valid")
    sums = fftconvolve(image, ones, mode="valid")
    sums2 = fftconvolve(image ** 2, ones, mode="valid")
    var = np.maximum(sums2 - sums ** 2 / template.size, 1e-9)
    return corr / (np.sqrt(var) * norm_t)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("output", type=Path, help="csv with the vertices (east, north)")
    parser.add_argument("--min", type=float, default=0.2, help="m/px of the screenshot, lowest tried")
    parser.add_argument("--max", type=float, default=0.8, help="m/px of the screenshot, highest tried")
    args = parser.parse_args()
    from montecarlo import MAP_EXTENT

    photo_file = next(f for f in sorted(model.SITE_DIR.iterdir()) if f.suffix.lower() in (".jpg", ".png"))
    photo = np.asarray(Image.open(photo_file).convert("RGB"))
    shot = np.asarray(Image.open(args.screenshot).convert("RGB"))
    height, width = photo.shape[:2]
    photo_mpp = (MAP_EXTENT[1] - MAP_EXTENT[0]) / width

    # Remove the drawn line (replaced by a blurred copy of the picture) before matching
    clean = grey(shot)
    line = ndimage.binary_dilation(yellow_mask(shot), iterations=4)
    clean[line] = ndimage.median_filter(clean, size=15)[line]
    target = grey(photo)

    best = None
    for mpp in np.arange(args.min, args.max + 1e-9, 0.01):
        factor = mpp / photo_mpp
        size = (max(int(shot.shape[1] * factor), 8), max(int(shot.shape[0] * factor), 8))
        template = np.asarray(Image.fromarray(clean).resize(size, Image.LANCZOS), dtype=float)
        score = ncc(target, template)
        row, col = np.unravel_index(np.argmax(score), score.shape)
        if best is None or score[row, col] > best[0]:
            best = (score[row, col], mpp, col, row)
    score, mpp, col, row = best
    factor = mpp / photo_mpp
    pixels = chain(vertices(shot)) * factor + (col, row)
    east = MAP_EXTENT[0] + pixels[:, 0] / width * (MAP_EXTENT[1] - MAP_EXTENT[0])
    north = MAP_EXTENT[3] - pixels[:, 1] / height * (MAP_EXTENT[3] - MAP_EXTENT[2])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        f.write(f"# From {args.screenshot.name}: {mpp:.2f} m/px, correlation {score:.2f}, located on {photo_file.name}\n")
        f.write("east,north\n")
        for e, n in zip(east, north):
            f.write(f"{e:.1f},{n:.1f}\n")
    print(f"{mpp:.2f} m/px, correlation {score:.2f}; {len(east)} vertices -> {args.output}")
    for e, n in zip(east, north):
        print(f"  E {e:7.1f}  N {n:7.1f}")


if __name__ == "__main__":
    main()
