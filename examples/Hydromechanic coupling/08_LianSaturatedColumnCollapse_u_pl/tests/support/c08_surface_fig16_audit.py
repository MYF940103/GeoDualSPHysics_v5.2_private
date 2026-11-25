"""Compare atmospheric gauge pressure near the printed Fig. 16 contours."""

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from c08_psi25_tpi_fields import CACHE, FIG16_TIMES, PDF, load_pages, palette_limits, paper_panels
from c08_psi25_tpi_native import read_frame
from postprocess_lian_release import native


def summarize(source, time, region, pressure):
    lower, median, upper = np.quantile(pressure, [.05, .5, .95])
    return dict(source=source, actual_elapsed_s=time, region=region, count=len(pressure),
                p05_kPa=lower, median_kPa=median, p95_kPa=upper,
                min_kPa=pressure.min(), max_kPa=pressure.max(),
                fraction_within_0p6_kPa=np.mean(np.abs(pressure) <= .6))


def paper_rows(page, tau):
    palette, lo, hi = palette_limits(page, "p", tau)
    tree = cKDTree(palette.astype(float))
    for label, image, extent in paper_panels(page, "p", tau):
        mask = image[:, :, 3] > 0
        h, w = mask.shape
        iy, ix = np.ogrid[:h, :w]
        xmin, xmax, zmin, zmax = extent
        x = xmin + (ix + .5) * (xmax - xmin) / w
        z = zmax - (iy + .5) * (zmax - zmin) / h
        top_edge = np.argmax(mask, axis=0)[None, :]
        right_edge = w - 1 - np.argmax(mask[:, ::-1], axis=1)[:, None]
        distance, index = tree.query(image[:, :, :3].reshape((-1, 3)).astype(float))
        valid = binary_erosion(mask, structure=np.ones((3, 3))) & (distance.reshape(h, w) <= 18)
        pressure = lo + index.reshape(h, w) * (hi - lo) / (len(palette) - 1)
        top = (iy >= top_edge + 2) & (iy <= top_edge + 4) & (x < x.max() - .12)
        side = (ix >= right_edge - 4) & (ix <= right_edge - 2) & (z > .18) & (z < 1.78)
        regions = {"top_left": top & (x > .2) & (x < 1.9),
                   "top_right": top & (x >= 2.) & (x <= 5.6),
                   "right_face": side}
        for name, region in regions.items():
            yield summarize(label, tau, name, pressure[valid & region])


def native_rows(tau, tag, tpi):
    part = int(round(tau * 100)) + (12 if tpi else 0)
    folder = CASE / "tests/outputs" / tag if tpi else CASE / tag
    reader = read_frame if tpi else native
    meta, fields, *_ = reader(folder / "data" / f"Part_{part:04d}.bi4")
    elapsed = meta["TimeStep"] - meta["GravityPreloadActualTime"]
    if abs(elapsed - tau) > 5.01e-6 or not meta["GravityPreloadPhase"]:
        raise ValueError(f"Unexpected clock or phase for {tag} part {part}")
    mask = (fields["Idp"] >= 2060) & np.isin(fields["FSType"], [2, 3])
    top = mask & (fields["FSNormal"][:, 2] > .7)
    side = mask & (fields["FSNormal"][:, 0] > .7)
    x, _, z = fields["Posd"].T
    pressure = fields["PorePress"].astype(float) / 1000
    regions = {"top_left": top & (x > .2) & (x < 1.9),
               "top_right": top & (x >= 2.) & (x <= 5.6),
               "right_face": side & (z > .18) & (z < 1.78), "all_native_surface": mask}
    for name, region in regions.items():
        yield summarize(tag, elapsed, name, pressure[region])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New CSV path")
    args = parser.parse_args()
    tag = "c08_psi25_tpi_paper_b004_r1"
    receipt = CASE / "tests/logs" / (tag + ".native_review.json")
    review = json.loads(receipt.read_text(encoding="utf8"))
    if args.output.exists() or review.get("passed") is not True or review.get("frames") != 132:
        raise ValueError("Need a new CSV and the complete TPI native review")
    page, _ = load_pages(CACHE, PDF)
    rows = []
    for tau in FIG16_TIMES:
        rows.extend(paper_rows(page, tau))
        for group in ("psi0", "psi2p5"):
            rows.extend(native_rows(tau, f"CaseLianCollapse_{group}_GPU_out", False))
        rows.extend(native_rows(tau, tag, True))
    with args.output.open("x", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
