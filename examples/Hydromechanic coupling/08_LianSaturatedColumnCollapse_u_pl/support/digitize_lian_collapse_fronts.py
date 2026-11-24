"""Reproduce the visible collapse-front positions in Lian et al. (2023), Figs. 14, 15 and 17."""

import argparse
import csv
import math
from pathlib import Path
import subprocess
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage


CASE = Path(__file__).resolve().parents[1]
PANELS = {
    # Right panels of the 180-dpi raster. Per-row calibration in original pixel coordinates:
    # elapsed seconds, x=0, x=8, z=2, top of the bed (z=0), front clipped by right frame.
    15: [(0.3, 723, 1217.5, 204, 327, False),
         (0.6, 721.5, 1211, 421, 544, False),
         (1.2, 718.5, 1216.5, 648, 772, False)],
    17: [(0.2, 706, 1217, 206, 333, False),
         (0.5, 707.5, 1212, 433, 559, False),
         (1.6, 705.5, 1210.5, 650, 776, True),
         (3.0, 707, 1208, 868, 993, True)],
}
FIELDS = ("group", "figure", "tau_s", "front_x_m", "kind", "digitization_m")


def load_pages(cache, pdf):
    files = [cache / f"c08_h18_lian2023_ref-{page}.png" for page in (21, 22)]
    with tempfile.TemporaryDirectory() as scratch:
        if not all(p.is_file() for p in files):
            prefix = Path(scratch) / "page"
            subprocess.run(["pdftoppm", "-f", "21", "-l", "22", "-r", "180", "-png",
                            str(pdf), str(prefix)], check=True)
            files = [Path(scratch) / f"page-{page}.png" for page in (21, 22)]
        result = []
        for path in files:
            with Image.open(path) as page:
                if page.size != (1361, 1857):
                    raise ValueError(f"Tick calibration requires a 1361 × 1857 raster: {path}")
                result.append(np.asarray(page.convert("RGB")))
    return result


def connected_body(rgb, figure, threshold):
    color = rgb.astype(np.int16)
    red, green, blue = color.transpose(2, 0, 1)
    chromatic = color.max(axis=2) - color.min(axis=2) >= threshold
    if figure == 15:
        # Material spans green/cyan/blue. Red leader arrows can touch the body.
        chromatic &= np.maximum(green, blue) - red >= 20
    labels, count = ndimage.label(chromatic, structure=np.ones((3, 3), bool))
    if not count:
        raise ValueError("No colored body found")
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    body = labels == sizes.argmax()
    if body.sum() < 2000 or not body[:, :10].any() or not body[-8:, :].any():
        raise ValueError("Largest component does not contact both left wall and bed")
    return body


def extract_figure(page, figure, output):
    rows = []
    settings = PANELS[figure]
    fig, axes = plt.subplots(len(settings), 2, figsize=(9, len(settings) * 1.75 + .75),
                             width_ratios=(2.4, 1), layout="constrained")
    for (tau, x0, x8, y2, bed, clipped), (profile, inset) in zip(settings, axes):
        left, right, top = math.floor(x0) - 3, math.ceil(x8) + 3, y2 - 4
        crop = page[top:bed + 2, left:right + 1]
        body = connected_body(crop, figure, 55)
        tip = left + int(np.nonzero(body)[1].max())
        sx, sz = 8 / (x8 - x0), 2 / (bed - y2)
        # Threshold sensitivity covers anti-aliased edge choices. Two pixels cover manual
        # tick and edge placement at this raster scale. This is not a model uncertainty.
        alt_tips = [left + np.nonzero(connected_body(crop, figure, threshold))[1].max()
                    for threshold in (30, 80)]
        allowance = max(2, *(abs(v - tip) + 1 for v in alt_tips)) * sx
        if (abs(tip - x8) <= 2) != clipped:
            raise ValueError(f"Paper frame clipping disagrees with connected color in Fig. {figure}, t={tau}")
        front = 8.0 if clipped else (tip - x0) * sx
        rows.append(dict(group="psi2p5" if figure == 15 else "psim5", figure=figure,
                         tau_s=tau, front_x_m=front, kind="lower_bound" if clipped else "visible",
                         digitization_m=allowance))
        # The full profile shows only our extracted binary component. The inset shows a
        # narrow original-pixel strip at the toe for independent inspection of its edge.
        bounds = ((left - x0 - .5) * sx, (right - x0 + .5) * sx,
                  (bed - (top + crop.shape[0]) + .5) * sz, (bed - top + .5) * sz)
        silhouette = np.where(body, .76, 0.)
        profile.imshow(silhouette, extent=bounds, origin="upper", interpolation="nearest",
                       vmin=0, vmax=1, cmap="Blues")
        profile.axvline(front, color="#bf3b16", lw=1.2, ls="--")
        profile.set(xlim=(-.05, 8.12), ylim=(-.04, 2.13), xlabel="x (m)", ylabel="z (m)")
        relation = "≥" if clipped else "="
        profile.set_title(f"{tau:g} s     visible front  {relation} {front:.2f} m", loc="left", fontsize=10)
        inset.imshow(crop, extent=bounds, origin="upper", interpolation="nearest")
        inset.axvline(front, color="#683a96", lw=1, ls="--")
        inset.set(xlim=(front - .9, min(8.05, front + .45)), ylim=(-.01, .60),
                  xlabel="x (m)")
        inset.set_title("Original tip pixels" if not clipped else "Original frame edge", fontsize=9)
    fig.suptitle(f"Lian et al. (2023), Fig. {figure}   |   colored soil outline and tip", fontsize=12)
    fig.savefig(output / f"figure{figure}_front_QA.png", dpi=170)
    plt.close(fig)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=CASE.parents[2] / "src/papers/PDF/Lian 2023 u-pl.pdf")
    parser.add_argument("--page-cache", type=Path, default=CASE / "tests/figures")
    parser.add_argument("--csv", type=Path, default=CASE / "support/lian_collapse_fronts.csv")
    parser.add_argument("--qa-dir", type=Path, default=CASE / "figures/validation_explicit/reference")
    args = parser.parse_args()
    args.qa_dir.mkdir(exist_ok=True, parents=True)
    existing = CASE / "tests/figures/upl_c08_lian14_outline_r1_summary.csv"
    rows = []
    with existing.open(newline="", encoding="utf-8-sig") as file:
        for original in csv.DictReader(file):
            rows.append(dict(group="psi0", figure=14, tau_s=original["requested_tau_s"],
                             front_x_m=original["front_colored_extent_m"], kind="visible",
                             digitization_m=original["front_digitization_allowance_m"]))
    if len(rows) != 3:
        raise ValueError("Expected the three retained Figure 14 paper readings")
    pages = load_pages(args.page_cache, args.pdf)
    for figure, page in zip((15, 17), pages):
        rows.extend(extract_figure(page, figure, args.qa_dir))
    with args.csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
