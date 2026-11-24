"""Reproduce the visible collapse-front positions in Lian et al. (2023), Figs. 14, 15 and 17."""

import argparse
from contextlib import contextmanager
import filecmp
import os
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
OUTLINE_FIELDS = ("group", "figure", "tau_s", "pixel_u", "pixel_v",
                  "x_m", "z_m", "edge_kind", "right_frame_clipped")


@contextmanager
def derived_file(path):
    """Publish a complete file atomically and retain existing identical products."""
    handle, name = tempfile.mkstemp(dir=path.parent, suffix=path.suffix)
    os.close(handle)
    temp = Path(name)
    try:
        yield temp
        if not path.is_file() or not filecmp.cmp(temp, path, shallow=False):
            temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def external_mask(mask):
    seed = np.zeros_like(mask)
    seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
    return ndimage.binary_propagation(seed & mask, mask=mask)


def classify_edge(x, z, sx, sz, clipped, paper_background):
    if clipped and x >= 8 - 2 * sx:
        return "frame_clipped"
    if x <= 3 * sx:
        return "left_wall"
    if z <= 3 * sz:
        return "bed"
    return "visible" if paper_background else "annotation_or_occlusion"


def store_paper_samples(samples, figure, tau, crop, body, left, top, x0, bed, sx, sz):
    # Take one original pixel in every 3×3 block. Only retained component pixels
    # have opacity; legends, text and background are omitted, without color inversion.
    stride = 3
    rgba = np.dstack((crop, body.astype(np.uint8) * 255))[::stride, ::stride].copy()
    rgba[rgba[:, :, 3] == 0] = 0
    key = f"f{figure}_t{int(round(10*tau))}"
    samples[key] = rgba
    height, width = rgba.shape[:2]
    samples[key + "_extent"] = np.array(((left - x0 - stride / 2) * sx,
        (left - x0 + (width - .5) * stride) * sx,
        (bed - top - (height - .5) * stride) * sz, (bed - top + stride / 2) * sz))


def figure14_samples(pdf, samples):
    saved = CASE / "tests/outputs/upl_c08_paper_scope_r1/page20.png"
    if saved.is_file():
        with Image.open(saved) as img:
            page = np.asarray(img.convert("RGB"))
    else:
        import fitz
        with fitz.open(pdf) as document:
            pix = document[19].get_pixmap(matrix=fitz.Matrix(2.3, 2.3), alpha=False)
            page = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    if page.shape != (1709, 1252, 3):
        raise ValueError("Figure 14 requires the original 2.3× page raster")
    samples["f14_palette"] = page[196, 910:1059].copy()
    for tau, x0, x8, y0, y2 in ((.3, 660, 1102.5, 298, 187), (.6, 660, 1102, 503, 391),
                                 (1.2, 660, 1106.5, 704, 592)):
        left, top = x0 - 3, y2 - 3
        crop = page[top:y0 + 4, left:math.ceil(x8) + 4]
        red, green, blue = crop.astype(np.int16).transpose(2, 0, 1)
        mask = (green >= 180) & (red <= 180) & (blue <= 190) & (green - np.maximum(red, blue) >= 40)
        labels, _ = ndimage.label(mask, structure=np.ones((3, 3), bool))
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        store_paper_samples(samples, 14, tau, crop, labels == sizes.argmax(), left, top,
                            x0, y0, 8 / (x8 - x0), 2 / (y0 - y2))


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


def extract_figure(page, figure, output, edges, samples):
    rows = []
    settings = PANELS[figure]
    # Centerline of the printed bar in the first right-hand panel.
    samples[f"f{figure}_palette"] = (page[214, 1003:1169] if figure == 15 else
                                      page[216, 995:1167]).copy()
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
        outside = external_mask(~body)
        edge = body & ndimage.binary_dilation(outside)
        # A note arrow emerging from the background can cut a notch in the color mask.
        # Only edges near actual exterior paper/grid pixels enter the geometry overlay.
        bright = crop.min(axis=2) >= 194
        neutral = np.ptp(crop, axis=2) <= 28
        paper = external_mask(bright & neutral & ~body)
        near_paper = ndimage.binary_dilation(paper, iterations=3)
        for v, u in zip(*np.nonzero(edge)):
            x, z = (left + int(u) - x0) * sx, (bed - top - int(v)) * sz
            kind = classify_edge(x, z, sx, sz, clipped, near_paper[v, u])
            edges.append((rows[-1]["group"], figure, tau, left + u, top + v,
                          f"{x:.6f}", f"{z:.6f}", kind, int(clipped)))
        store_paper_samples(samples, figure, tau, crop, body, left, top, x0, bed, sx, sz)
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
    with derived_file(output / f"figure{figure}_front_QA.png") as path:
        fig.savefig(path, dpi=170)
    plt.close(fig)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=CASE.parents[2] / "src/papers/PDF/Lian 2023 u-pl.pdf")
    parser.add_argument("--page-cache", type=Path, default=CASE / "tests/figures")
    parser.add_argument("--csv", type=Path, default=CASE / "support/lian_collapse_fronts.csv")
    parser.add_argument("--outline", type=Path, default=CASE / "support/lian_collapse_outline.csv")
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
    edges, samples = [], {}
    retained = existing.with_name("upl_c08_lian14_outline_r1_outline.csv")
    with retained.open(newline="", encoding="utf-8-sig") as file:
        for original in csv.DictReader(file):
            x, z = float(original["x_m"]), float(original["z_m"])
            kind = classify_edge(x, z, float(original["m_per_pixel_x"]),
                                 float(original["m_per_pixel_z"]), False, True)
            edges.append(("psi0", 14, original["requested_tau_s"], original["pixel_u"],
                          original["pixel_v"], f"{x:.6f}", f"{z:.6f}", kind, 0))
    figure14_samples(args.pdf, samples)
    pages = load_pages(args.page_cache, args.pdf)
    for figure, page in zip((15, 17), pages):
        rows.extend(extract_figure(page, figure, args.qa_dir, edges, samples))
    with derived_file(args.csv) as path, path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with derived_file(args.outline) as path, path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(OUTLINE_FIELDS)
        writer.writerows(edges)
    with derived_file(args.qa_dir / "paper_pressure_samples.npz") as path:
        np.savez_compressed(path, **samples)


if __name__ == "__main__":
    main()
