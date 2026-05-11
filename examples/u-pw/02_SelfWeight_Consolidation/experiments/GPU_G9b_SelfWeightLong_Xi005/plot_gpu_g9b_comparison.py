from __future__ import annotations

import binascii
import csv
import math
import struct
import zlib
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "CaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi005_gpu_out"
DATA = OUT / "data"
FIGDIR = ROOT / "figures"
FRAME_CSV = ROOT / "gpu_g9b_frame_metrics.csv"
GPU_XI010 = ROOT.parent / "GPU_G9_SelfWeightLong" / "gpu_g9_frame_metrics.csv"
CPU_SW3H = ROOT.parents[2] / "01_1D_Consolidation" / "SW3h_scenario2_T3p6_xi010" / "sw3h_frame_metrics.csv"
FIGDIR.mkdir(exist_ok=True)

TARGET_TIMES = [0.0, 0.1, 0.5, 1.0, 2.0, 3.6]
COLORS = ["#111111", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#d62728", "#17becf"]
RGB = {
    "#111111": (17, 17, 17),
    "#1f77b4": (31, 119, 180),
    "#2ca02c": (44, 160, 44),
    "#ff7f0e": (255, 127, 14),
    "#9467bd": (148, 103, 189),
    "#d62728": (214, 39, 40),
    "#17becf": (23, 190, 207),
    "#777777": (119, 119, 119),
}


def read_rows(path: Path, delim: str = "auto") -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", errors="ignore") as f:
        if delim == "auto":
            sample = f.read(4096)
            f.seek(0)
            delim = ";" if sample.count(";") >= sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def val(row: dict[str, str], key: str, default: float = math.nan) -> float:
    if key in row and row[key] != "":
        return float(row[key])
    for k, v in row.items():
        if k.split("[")[0].strip() == key and v != "":
            return float(v)
    return default


def is_fluid(row: dict[str, str]) -> bool:
    return str(row.get("Type", "")).strip().lower() in ("3", "fluid")


def load_profile(frame: int) -> list[tuple[float, float, float, float]]:
    rows = [r for r in read_rows(DATA / f"PartCsv_{frame:04d}.csv") if is_fluid(r)]
    bins: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)
    for r in rows:
        z = val(r, "Pos.z")
        p = val(r, "PorePress")
        hydro = 1000.0 * 9.81 * max(1.0 - z, 0.0)
        ex = val(r, "ExcessPorePress")
        if all(math.isfinite(v) for v in (z, p, hydro, ex)):
            bins[int(round(z * 100))].append((z, p, hydro, ex))
    prof = []
    for key in sorted(bins):
        arr = bins[key]
        n = len(arr)
        prof.append(tuple(sum(v[i] for v in arr) / n for i in range(4)))
    return prof


def clean_points(data: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(x, y) for x, y in data if math.isfinite(x) and math.isfinite(y)]


def bounds(series) -> tuple[float, float, float, float]:
    pts = [p for _, data, _ in series for p in clean_points(data)]
    if not pts:
        return 0.0, 1.0, 0.0, 1.0
    xmin, xmax = min(x for x, _ in pts), max(x for x, _ in pts)
    ymin, ymax = min(y for _, y in pts), max(y for _, y in pts)
    if xmin == xmax:
        xmax = xmin + 1.0
    if ymin == ymax:
        ymax = ymin + 1.0
    padx = 0.03 * (xmax - xmin)
    pady = 0.08 * (ymax - ymin)
    return xmin - padx, xmax + padx, ymin - pady, ymax + pady


def svg_line_plot(path: Path, series, xlabel: str, ylabel: str, title: str, width=900, height=560) -> None:
    xmin, xmax, ymin, ymax = bounds(series)
    margin = dict(left=92, right=26, top=58, bottom=72)
    pw = width - margin["left"] - margin["right"]
    ph = height - margin["top"] - margin["bottom"]

    def sx(x): return margin["left"] + (x - xmin) / (xmax - xmin) * pw
    def sy(y): return margin["top"] + (ymax - y) / (ymax - ymin) * ph

    out = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{width/2}' y='30' text-anchor='middle' font-family='Arial' font-size='20'>{title}</text>",
        f"<line x1='{margin['left']}' y1='{height-margin['bottom']}' x2='{width-margin['right']}' y2='{height-margin['bottom']}' stroke='black'/>",
        f"<line x1='{margin['left']}' y1='{margin['top']}' x2='{margin['left']}' y2='{height-margin['bottom']}' stroke='black'/>",
        f"<text x='{width/2}' y='{height-25}' text-anchor='middle' font-family='Arial' font-size='15'>{xlabel}</text>",
        f"<text x='23' y='{height/2}' transform='rotate(-90 23 {height/2})' text-anchor='middle' font-family='Arial' font-size='15'>{ylabel}</text>",
    ]
    for i in range(6):
        x = xmin + (xmax - xmin) * i / 5
        y = ymin + (ymax - ymin) * i / 5
        out.append(f"<line x1='{sx(x):.1f}' y1='{margin['top']}' x2='{sx(x):.1f}' y2='{height-margin['bottom']}' stroke='#eeeeee'/>")
        out.append(f"<line x1='{margin['left']}' y1='{sy(y):.1f}' x2='{width-margin['right']}' y2='{sy(y):.1f}' stroke='#eeeeee'/>")
        out.append(f"<text x='{sx(x):.1f}' y='{height-margin['bottom']+20}' text-anchor='middle' font-family='Arial' font-size='11'>{x:.3g}</text>")
        out.append(f"<text x='{margin['left']-8}' y='{sy(y)+4:.1f}' text-anchor='end' font-family='Arial' font-size='11'>{y:.3g}</text>")
    legend_y = margin["top"] + 12
    for label, data, color in series:
        points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in clean_points(data))
        if points:
            out.append(f"<polyline points='{points}' fill='none' stroke='{color}' stroke-width='2'/>")
        out.append(f"<line x1='{width-250}' y1='{legend_y}' x2='{width-225}' y2='{legend_y}' stroke='{color}' stroke-width='3'/>")
        out.append(f"<text x='{width-218}' y='{legend_y+4}' font-family='Arial' font-size='12'>{label}</text>")
        legend_y += 18
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def write_png(path: Path, pixels: bytearray, width: int, height: int) -> None:
    rows = []
    stride = width * 3
    for y in range(height):
        rows.append(b"\x00" + bytes(pixels[y * stride:(y + 1) * stride]))
    raw = b"".join(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def png_line_plot(path: Path, series, width=900, height=560) -> None:
    xmin, xmax, ymin, ymax = bounds(series)
    margin = dict(left=86, right=26, top=56, bottom=68)
    pw = width - margin["left"] - margin["right"]
    ph = height - margin["top"] - margin["bottom"]
    pixels = bytearray([255] * width * height * 3)

    def px(x): return int(round(margin["left"] + (x - xmin) / (xmax - xmin) * pw))
    def py(y): return int(round(margin["top"] + (ymax - y) / (ymax - ymin) * ph))
    def setpx(x, y, rgb):
        if 0 <= x < width and 0 <= y < height:
            i = (y * width + x) * 3
            pixels[i:i + 3] = bytes(rgb)
    def line(x0, y0, x1, y1, rgb):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for ox in (0, 1):
                for oy in (0, 1):
                    setpx(x0 + ox, y0 + oy, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    grey = (230, 230, 230)
    black = (20, 20, 20)
    for i in range(6):
        gx = margin["left"] + int(pw * i / 5)
        gy = margin["top"] + int(ph * i / 5)
        line(gx, margin["top"], gx, height - margin["bottom"], grey)
        line(margin["left"], gy, width - margin["right"], gy, grey)
    line(margin["left"], height - margin["bottom"], width - margin["right"], height - margin["bottom"], black)
    line(margin["left"], margin["top"], margin["left"], height - margin["bottom"], black)
    for _, data, color in series:
        pts = [(px(x), py(y)) for x, y in clean_points(data)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            line(x0, y0, x1, y1, RGB.get(color, black))
    write_png(path, pixels, width, height)


def save_plot(stem: str, series, xlabel: str, ylabel: str, title: str) -> None:
    svg_line_plot(FIGDIR / f"{stem}.svg", series, xlabel, ylabel, title)
    png_line_plot(FIGDIR / f"{stem}.png", series)


def profile_plots() -> None:
    pore_series = []
    excess_series = []
    for i, t in enumerate(TARGET_TIMES):
        frame = int(round(t / 0.1))
        prof = load_profile(frame)
        if not prof:
            continue
        color = COLORS[i % len(COLORS)]
        pore_series.append((f"G9b xi=0.05 t={t:g}s", [(z, p) for z, p, _, _ in prof], color))
        excess_series.append((f"G9b xi=0.05 t={t:g}s", [(z, ex) for z, _, _, ex in prof], color))
    save_plot("gpu_g9b_porepress_profiles", pore_series, "z (m)", "PorePress (Pa)", "GPU G9b xi=0.05 Pore Pressure Profiles")
    save_plot("gpu_g9b_excess_profiles", excess_series, "z (m)", "ExcessPorePress (Pa)", "GPU G9b xi=0.05 Excess Profiles")


def series_from_metrics(path: Path, key: str, label: str, color: str):
    rows = read_rows(path)
    return (label, [(val(r, "time"), val(r, key)) for r in rows], color)


def time_plots() -> None:
    rows = read_rows(FRAME_CSV)
    bottom_pressure = [
        ("GPU xi=0.05 bottom PorePress", [(val(r, "time"), val(r, "bottom_PorePress_mean")) for r in rows], "#1f77b4"),
        ("Hydrostatic bottom reference", [(val(r, "time"), val(r, "bottom_hydrostatic_mean")) for r in rows], "#111111"),
        series_from_metrics(GPU_XI010, "bottom_PorePress_mean", "GPU xi=0.10 bottom PorePress", "#2ca02c"),
        series_from_metrics(CPU_SW3H, "bottom_PorePress_mean", "CPU xi=0.10 bottom PorePress", "#ff7f0e"),
    ]
    bottom_excess = [
        ("GPU xi=0.05 bottom Excess", [(val(r, "time"), val(r, "bottom_Excess_mean")) for r in rows], "#1f77b4"),
        series_from_metrics(GPU_XI010, "bottom_Excess_mean", "GPU xi=0.10 bottom Excess", "#2ca02c"),
        series_from_metrics(CPU_SW3H, "bottom_Excess_mean", "CPU xi=0.10 bottom Excess", "#ff7f0e"),
        ("Zero excess reference", [(val(r, "time"), 0.0) for r in rows], "#111111"),
    ]
    envelope = [
        ("GPU xi=0.05 Excess maxAbs", [(val(r, "time"), val(r, "Excess_maxAbs")) for r in rows], "#1f77b4"),
        series_from_metrics(GPU_XI010, "Excess_maxAbs", "GPU xi=0.10 Excess maxAbs", "#2ca02c"),
        series_from_metrics(CPU_SW3H, "Excess_maxAbs", "CPU xi=0.10 Excess maxAbs", "#ff7f0e"),
    ]
    comparison = [
        ("GPU xi=0.05 total bottom", [(val(r, "time"), val(r, "bottom_PorePress_mean")) for r in rows], "#1f77b4"),
        series_from_metrics(GPU_XI010, "bottom_PorePress_mean", "GPU xi=0.10 total bottom", "#2ca02c"),
        series_from_metrics(CPU_SW3H, "bottom_PorePress_mean", "CPU xi=0.10 total bottom", "#ff7f0e"),
        ("Hydrostatic/theory reference", [(val(r, "time"), val(r, "bottom_hydrostatic_mean")) for r in rows], "#111111"),
    ]
    save_plot("gpu_g9b_bottom_porepress_time", bottom_pressure, "time (s)", "bottom pressure (Pa)", "Bottom Pore Pressure vs Time")
    save_plot("gpu_g9b_bottom_excess_time", bottom_excess, "time (s)", "bottom excess pressure (Pa)", "Bottom Excess Pore Pressure vs Time")
    save_plot("gpu_g9b_excess_envelope_comparison", envelope, "time (s)", "Excess maxAbs (Pa)", "Excess Envelope Decay Comparison")
    save_plot("gpu_g9b_cpu_gpu_theory_comparison", comparison, "time (s)", "bottom pressure (Pa)", "CPU/GPU/Hydrostatic Reference Comparison")


def main() -> None:
    profile_plots()
    time_plots()


if __name__ == "__main__":
    main()
