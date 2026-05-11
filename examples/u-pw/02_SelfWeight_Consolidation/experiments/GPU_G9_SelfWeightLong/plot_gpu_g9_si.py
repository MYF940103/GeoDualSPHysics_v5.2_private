from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "CaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi010_gpu_out"
DATA = OUT / "data"
FIGDIR = ROOT / "figures"
FRAME_CSV = ROOT / "gpu_g9_frame_metrics.csv"
FIGDIR.mkdir(exist_ok=True)
TARGET_TIMES = [0.0, 0.1, 0.5, 1.0, 2.0, 3.6]
COLORS = ["#111111", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#d62728"]


def read_rows(path: Path, delim: str = ",") -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", errors="ignore") as f:
        if delim == "auto":
            sample = f.read(4096)
            f.seek(0)
            delim = ";" if sample.count(";") >= sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def val(row: dict[str, str], key: str, default: float = 0.0) -> float:
    if key in row and row[key] != "":
        return float(row[key])
    for k, v in row.items():
        if k.split("[")[0].strip() == key and v != "":
            return float(v)
    return default


def is_fluid(row: dict[str, str]) -> bool:
    return str(row.get("Type", "")).strip().lower() in ("3", "fluid")


def load_profile(frame: int) -> list[tuple[float, float, float, float]]:
    rows = [r for r in read_rows(DATA / f"PartCsv_{frame:04d}.csv", "auto") if is_fluid(r)]
    if not rows:
        return []
    bins: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)
    for r in rows:
        z = val(r, "Pos.z")
        p = val(r, "PorePress")
        h = 1000.0 * 9.81 * max(1.0 - z, 0.0)
        ex = val(r, "ExcessPorePress")
        bins[int(round(z * 100))].append((z, p, h, ex))
    prof = []
    for b in sorted(bins):
        arr = bins[b]
        n = len(arr)
        prof.append(tuple(sum(v[i] for v in arr) / n for i in range(4)))
    return prof


def svg_line_plot(path: Path, series, xlabel: str, ylabel: str, title: str, width=900, height=560):
    margin = dict(left=90, right=25, top=55, bottom=70)
    pts = [(x, y) for _, data, _ in series for x, y in data if math.isfinite(x) and math.isfinite(y)]
    if not pts:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
        return
    xmin, xmax = min(x for x, _ in pts), max(x for x, _ in pts)
    ymin, ymax = min(y for _, y in pts), max(y for _, y in pts)
    if xmin == xmax:
        xmax = xmin + 1
    if ymin == ymax:
        ymax = ymin + 1
    padx = 0.03 * (xmax - xmin)
    pady = 0.08 * (ymax - ymin)
    xmin -= padx
    xmax += padx
    ymin -= pady
    ymax += pady
    pw = width - margin["left"] - margin["right"]
    ph = height - margin["top"] - margin["bottom"]

    def sx(x):
        return margin["left"] + (x - xmin) / (xmax - xmin) * pw

    def sy(y):
        return margin["top"] + (ymax - y) / (ymax - ymin) * ph

    out = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{width/2}' y='28' text-anchor='middle' font-family='Arial' font-size='20'>{title}</text>",
        f"<line x1='{margin['left']}' y1='{height-margin['bottom']}' x2='{width-margin['right']}' y2='{height-margin['bottom']}' stroke='black'/>",
        f"<line x1='{margin['left']}' y1='{margin['top']}' x2='{margin['left']}' y2='{height-margin['bottom']}' stroke='black'/>",
        f"<text x='{width/2}' y='{height-25}' text-anchor='middle' font-family='Arial' font-size='15'>{xlabel}</text>",
        f"<text x='22' y='{height/2}' transform='rotate(-90 22 {height/2})' text-anchor='middle' font-family='Arial' font-size='15'>{ylabel}</text>",
    ]
    for i in range(6):
        x = xmin + (xmax - xmin) * i / 5
        y = ymin + (ymax - ymin) * i / 5
        out.append(f"<text x='{sx(x):.1f}' y='{height-margin['bottom']+20}' text-anchor='middle' font-family='Arial' font-size='11'>{x:.3g}</text>")
        out.append(f"<text x='{margin['left']-8}' y='{sy(y)+4:.1f}' text-anchor='end' font-family='Arial' font-size='11'>{y:.3g}</text>")
        out.append(f"<line x1='{sx(x):.1f}' y1='{margin['top']}' x2='{sx(x):.1f}' y2='{height-margin['bottom']}' stroke='#eee'/>")
        out.append(f"<line x1='{margin['left']}' y1='{sy(y):.1f}' x2='{width-margin['right']}' y2='{sy(y):.1f}' stroke='#eee'/>")
    legend_y = margin["top"] + 10
    for label, data, color in series:
        points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in data if math.isfinite(x) and math.isfinite(y))
        out.append(f"<polyline points='{points}' fill='none' stroke='{color}' stroke-width='2'/>")
        out.append(f"<line x1='{width-190}' y1='{legend_y}' x2='{width-165}' y2='{legend_y}' stroke='{color}' stroke-width='3'/>")
        out.append(f"<text x='{width-158}' y='{legend_y+4}' font-family='Arial' font-size='12'>{label}</text>")
        legend_y += 18
    out.append("</svg>")
    path.write_text("\n".join(out))


def profile_plots():
    pore_series = []
    excess_series = []
    for i, t in enumerate(TARGET_TIMES):
        frame = int(round(t / 0.1))
        prof = load_profile(frame)
        if not prof:
            continue
        pore_series.append((f"t={t:g}s", [(z, p) for z, p, _, _ in prof], COLORS[i % len(COLORS)]))
        excess_series.append((f"t={t:g}s", [(z, ex) for z, _, _, ex in prof], COLORS[i % len(COLORS)]))
    svg_line_plot(FIGDIR / "gpu_g9_porepress_profiles.svg", pore_series, "z (m)", "PorePress (Pa)", "GPU G9 Pore Pressure Profiles")
    svg_line_plot(FIGDIR / "gpu_g9_excess_profiles.svg", excess_series, "z (m)", "ExcessPorePress (Pa)", "GPU G9 Excess Pore Pressure Profiles")


def time_plots():
    rows = read_rows(FRAME_CSV)
    bottom = [
        ("bottom PorePress", [(val(r, "time"), val(r, "bottom_PorePress_mean")) for r in rows], "#1f77b4"),
        ("bottom hydrostatic", [(val(r, "time"), val(r, "bottom_hydrostatic_mean")) for r in rows], "#111111"),
    ]
    excess = [
        ("Excess maxAbs", [(val(r, "time"), val(r, "Excess_maxAbs")) for r in rows], "#d62728"),
        ("Excess mean", [(val(r, "time"), val(r, "Excess_mean")) for r in rows], "#1f77b4"),
        ("bottom Excess mean", [(val(r, "time"), val(r, "bottom_Excess_mean")) for r in rows], "#2ca02c"),
    ]
    svg_line_plot(FIGDIR / "gpu_g9_bottom_porepress_time.svg", bottom, "time (s)", "Pressure (Pa)", "GPU G9 Bottom Pressure Trend")
    svg_line_plot(FIGDIR / "gpu_g9_excess_time.svg", excess, "time (s)", "Excess pressure (Pa)", "GPU G9 Excess Pressure Trend")


def main() -> None:
    profile_plots()
    time_plots()


if __name__ == "__main__":
    main()
