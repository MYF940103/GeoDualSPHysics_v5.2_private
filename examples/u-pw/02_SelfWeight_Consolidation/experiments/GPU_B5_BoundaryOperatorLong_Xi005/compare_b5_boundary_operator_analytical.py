from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Arial"

ROOT = Path(__file__).resolve().parent
CASE = "CaseSW_S2_GPU_B5_Xi005"
OUT = ROOT / f"{CASE}_gpu_out"
MODE0 = ROOT.parent / "GPU_G9b_SelfWeightLong_Xi005"
MODE010 = ROOT.parent / "GPU_G9_SelfWeightLong"
ANALYTICAL = MODE0 / "analytical_comparison"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

TARGET_TIMES = [0.1, 0.5, 1.0, 2.0, 3.6]
NTERMS = 300

E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO_SOIL = 2100.0
RHO_W = 1000.0
G = 9.81
DRAIN_START = 0.002
TIME_OUT = 0.1

COLORS = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e"]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", errors="ignore") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return math.nan


def read_part(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open(newline="", errors="ignore") as fp:
        reader = csv.reader(fp, delimiter=";")
        header = [h.strip().split()[0] for h in next(reader) if h.strip()]
        rows: list[dict[str, float]] = []
        for raw in reader:
            vals = [v.strip() for v in raw if v.strip()]
            if len(vals) != len(header):
                continue
            row: dict[str, float] = {}
            for key, val in zip(header, vals):
                try:
                    row[key] = float(val)
                except ValueError:
                    row[key] = math.nan
            if int(row.get("Type", -1)) == 3:
                rows.append(row)
        return header, rows


def parse_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def linear_fit(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(pairs)
    if n < 2:
        return 1.0, 0.0
    sx = sum(x for x, _ in pairs)
    sy = sum(y for _, y in pairs)
    sxx = sum(x * x for x, _ in pairs)
    sxy = sum(x * y for x, y in pairs)
    den = n * sxx - sx * sx
    if abs(den) < 1e-12:
        return 1.0, 0.0
    a = (n * sxy - sx * sy) / den
    b = (sy - a * sx) / n
    return a, b


def extract_legacy_svg_profiles(path: Path) -> dict[float, list[tuple[float, float]]]:
    """Recover approximate mode=0 profiles from retained simple SVG figures.

    G9b raw PartCsv files were intentionally cleaned after the earlier long run.
    The retained pre-analytical SVGs store line data as polylines, so this
    recovery is sufficient for visual mode=0/mode=1 comparison and is marked as
    approximate in the output metrics.
    """
    if not path.exists():
        return {}
    text = path.read_text(errors="ignore")
    x_ticks: list[tuple[float, float]] = []
    y_ticks: list[tuple[float, float]] = []
    for m in re.finditer(r"<text x='([^']+)' y='([^']+)'[^>]*>([^<]+)</text>", text):
        x = parse_float(m.group(1))
        y = parse_float(m.group(2))
        val = parse_float(m.group(3))
        if x is None or y is None or val is None:
            continue
        if y > 500:
            x_ticks.append((x, val))
        if x < 90:
            y_ticks.append((y, val))
    ax, bx = linear_fit(x_ticks)
    ay, by = linear_fit(y_ticks)
    polylines = re.findall(r"<polyline points='([^']+)'", text)
    labels = re.findall(r"<text [^>]*>(?:G9b xi=0.05 )?t=([0-9.]+)s</text>", text)
    out: dict[float, list[tuple[float, float]]] = {}
    for points, label in zip(polylines, labels):
        vals: list[tuple[float, float]] = []
        for token in points.split():
            try:
                px, py = [float(v) for v in token.split(",")]
            except ValueError:
                continue
            vals.append((ax * px + bx, ay * py + by))
        out[float(label)] = vals
    return out


B5_ROWS = read_rows(ROOT / "gpu_b5_boundary_operator_frame_metrics.csv")
MODE0_ROWS = read_rows(MODE0 / "gpu_g9b_frame_metrics.csv")
MODE010_ROWS = read_rows(MODE010 / "gpu_g9_frame_metrics.csv")
H = f(B5_ROWS[0], "zmax") - f(B5_ROWS[0], "zmin") if B5_ROWS else 0.99
ZMIN = f(B5_ROWS[0], "zmin") if B5_ROWS else 0.005
ZMAX = f(B5_ROWS[0], "zmax") if B5_ROWS else 0.995
K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_1D = K_BULK + 4.0 * G_SHEAR / 3.0
CV = KPERM * M_1D / (RHO_W * G)
KW_OVER_N = KW / POROSITY
P0_SCALE = KW_OVER_N * RHO_SOIL * G / (M_1D + KW_OVER_N)


def lambda_n(n: int) -> float:
    return (2 * n + 1) * math.pi / (2 * H)


def coeff_n(n: int) -> float:
    lam = lambda_n(n)
    return 2.0 * P0_SCALE / (H * lam * lam)


COEFFS = [coeff_n(i) for i in range(NTERMS)]


def y_from_z(z: float) -> float:
    return max(0.0, min(H, z - ZMIN))


def z_from_y(y: float) -> float:
    return ZMIN + y


def hydrostatic_y(y: float) -> float:
    return RHO_W * G * max(H - y, 0.0)


def excess_analytical_y(y: float, t: float) -> float:
    tau = max(t - DRAIN_START, 0.0)
    return sum(c * math.cos(lambda_n(n) * y) * math.exp(-(lambda_n(n) ** 2) * CV * tau) for n, c in enumerate(COEFFS))


def porepress_analytical_y(y: float, t: float) -> float:
    return hydrostatic_y(y) + excess_analytical_y(y, t)


def tv(t: float) -> float:
    return CV * max(t - DRAIN_START, 0.0) / (H * H)


def nearest_frame(time: float, rows: list[dict[str, str]]) -> dict[str, str]:
    return min(rows, key=lambda r: abs(f(r, "time") - time))


def b5_profile(time: float, quantity: str) -> list[tuple[float, float]]:
    frame = int(round(time / TIME_OUT))
    part = OUT / "data" / f"PartCsv_{frame:04d}.csv"
    if not part.exists():
        parts = sorted((OUT / "data").glob("PartCsv_*.csv"))
        if not parts:
            return []
        part = min(parts, key=lambda p: abs(int(p.stem.split("_")[-1]) * TIME_OUT - time))
    _, rows = read_part(part)
    buckets: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        z = row.get("Pos.z", math.nan)
        val = row.get(quantity, math.nan)
        if math.isfinite(z) and math.isfinite(val):
            buckets[round(z, 6)].append(val)
    return [(z, sum(vals) / len(vals)) for z, vals in sorted(buckets.items())]


def analytical_profile(time: float, quantity: str) -> list[tuple[float, float]]:
    data = []
    for i in range(180):
        y = H * i / 179
        if quantity == "ExcessPorePress":
            val = excess_analytical_y(y, time)
        else:
            val = porepress_analytical_y(y, time)
        data.append((z_from_y(y), val))
    return data


def interp(profile: list[tuple[float, float]], z: float) -> float:
    pts = sorted((x, y) for x, y in profile if math.isfinite(x) and math.isfinite(y))
    if not pts:
        return math.nan
    if z <= pts[0][0]:
        return pts[0][1]
    if z >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= z <= x1:
            a = (z - x0) / (x1 - x0) if x1 != x0 else 0.0
            return y0 + a * (y1 - y0)
    return math.nan


def error_stats(profile: list[tuple[float, float]], time: float, quantity: str, region: str = "all") -> dict[str, float]:
    errs = []
    vals = []
    for z, val in profile:
        y = y_from_z(z)
        if region == "bottom" and y > 2 * 0.018:
            continue
        if region == "interior" and not (2 * 0.018 < y < H - 2 * 0.018):
            continue
        if region == "top" and y < H - 2 * 0.018:
            continue
        ref = excess_analytical_y(y, time) if quantity == "ExcessPorePress" else porepress_analytical_y(y, time)
        if math.isfinite(val) and math.isfinite(ref):
            errs.append(val - ref)
            vals.append(ref)
    if not errs:
        return {"n": 0, "rmse": math.nan, "mae": math.nan, "max_abs": math.nan, "relative_rmse": math.nan}
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
    mae = sum(abs(e) for e in errs) / len(errs)
    max_abs = max(abs(e) for e in errs)
    denom = math.sqrt(sum(v * v for v in vals) / len(vals))
    return {"n": len(errs), "rmse": rmse, "mae": mae, "max_abs": max_abs, "relative_rmse": rmse / denom if denom else math.nan}


def write_profile_csv() -> None:
    fields = ["line", "time", "Tv", "z", "z_norm", "quantity", "value"]
    with (ROOT / "gpu_b5_boundary_vs_analytical_profile_timeseries.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        mode0_ex = extract_legacy_svg_profiles(MODE0 / "figures" / "gpu_g9b_excess_profiles.svg")
        mode0_pp = extract_legacy_svg_profiles(MODE0 / "figures" / "gpu_g9b_porepress_profiles.svg")
        for time in TARGET_TIMES:
            for line, quantity, profile in [
                ("gpu_mode0_xi005_approx", "ExcessPorePress", mode0_ex.get(time, [])),
                ("gpu_mode0_xi005_approx", "PorePress", mode0_pp.get(time, [])),
                ("gpu_mode1_xi005_b5", "ExcessPorePress", b5_profile(time, "ExcessPorePress")),
                ("gpu_mode1_xi005_b5", "PorePress", b5_profile(time, "PorePress")),
                ("analytical", "ExcessPorePress", analytical_profile(time, "ExcessPorePress")),
                ("analytical", "PorePress", analytical_profile(time, "PorePress")),
            ]:
                for z, val in profile:
                    writer.writerow({
                        "line": line,
                        "time": f"{time:.12g}",
                        "Tv": f"{tv(time):.12g}",
                        "z": f"{z:.12g}",
                        "z_norm": f"{(z - ZMIN) / H:.12g}",
                        "quantity": quantity,
                        "value": f"{val:.12g}",
                    })


def write_bottom_csv() -> None:
    fields = ["line", "time", "Tv", "bottom_porepress", "bottom_excess", "excess_envelope"]
    with (ROOT / "gpu_b5_boundary_vs_analytical_bottom_timeseries.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for line, rows in [("gpu_mode0_xi005", MODE0_ROWS), ("gpu_mode0_xi010", MODE010_ROWS), ("gpu_mode1_xi005_b5", B5_ROWS)]:
            for row in rows:
                time = f(row, "time")
                if not math.isfinite(time):
                    continue
                writer.writerow({
                    "line": line,
                    "time": f"{time:.12g}",
                    "Tv": f"{tv(time):.12g}",
                    "bottom_porepress": row.get("bottom_PorePress_mean", ""),
                    "bottom_excess": row.get("bottom_Excess_mean", ""),
                    "excess_envelope": row.get("Excess_maxAbs", ""),
                })
        for row in B5_ROWS:
            time = f(row, "time")
            if math.isfinite(time):
                y = 0.0
                ex = excess_analytical_y(y, time)
                writer.writerow({
                    "line": "analytical",
                    "time": f"{time:.12g}",
                    "Tv": f"{tv(time):.12g}",
                    "bottom_porepress": f"{hydrostatic_y(y) + ex:.12g}",
                    "bottom_excess": f"{ex:.12g}",
                    "excess_envelope": f"{ex:.12g}",
                })


def write_metrics() -> list[dict[str, str]]:
    mode0_ex = extract_legacy_svg_profiles(MODE0 / "figures" / "gpu_g9b_excess_profiles.svg")
    mode0_pp = extract_legacy_svg_profiles(MODE0 / "figures" / "gpu_g9b_porepress_profiles.svg")
    rows: list[dict[str, str]] = []
    for quantity, mode0_profiles in [("ExcessPorePress", mode0_ex), ("PorePress", mode0_pp)]:
        for time in TARGET_TIMES:
            for line, profile, note in [
                ("gpu_mode0_xi005", mode0_profiles.get(time, []), "mode=0 profile recovered approximately from retained SVG"),
                ("gpu_mode1_xi005_b5", b5_profile(time, quantity), "mode=1 profile from retained raw PartCsv"),
            ]:
                for region in ["all", "bottom", "interior", "top"]:
                    st = error_stats(profile, time, quantity, region)
                    rows.append({
                        "quantity": f"{quantity}_profile_t{time:g}",
                        "line": line,
                        "region": region,
                        "n": str(st["n"]),
                        "rmse": f"{st['rmse']:.12g}",
                        "mean_abs_error": f"{st['mae']:.12g}",
                        "max_abs_error": f"{st['max_abs']:.12g}",
                        "relative_rmse": f"{st['relative_rmse']:.12g}",
                        "note": note,
                    })

    def time_metrics(line: str, rows_in: list[dict[str, str]], key: str, analytical_key: str) -> None:
        errs = []
        refs = []
        for row in rows_in:
            time = f(row, "time")
            if not math.isfinite(time) or time <= 0:
                continue
            y = 0.0
            ref = excess_analytical_y(y, time)
            if analytical_key.startswith("bottom_porepress"):
                ref += hydrostatic_y(y)
            val = f(row, key)
            if math.isfinite(val):
                errs.append(val - ref)
                refs.append(ref)
        if errs:
            rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
            mae = sum(abs(e) for e in errs) / len(errs)
            max_abs = max(abs(e) for e in errs)
            denom = math.sqrt(sum(r * r for r in refs) / len(refs))
            rows.append({
                "quantity": analytical_key,
                "line": line,
                "region": "bottom_time",
                "n": str(len(errs)),
                "rmse": f"{rmse:.12g}",
                "mean_abs_error": f"{mae:.12g}",
                "max_abs_error": f"{max_abs:.12g}",
                "relative_rmse": f"{rmse / denom if denom else math.nan:.12g}",
                "note": "time-series metric, t=0 omitted",
            })

    for line, rows_in in [("gpu_mode0_xi005", MODE0_ROWS), ("gpu_mode0_xi010", MODE010_ROWS), ("gpu_mode1_xi005_b5", B5_ROWS)]:
        time_metrics(line, rows_in, "bottom_Excess_mean", "bottom_excess_time")
        time_metrics(line, rows_in, "bottom_PorePress_mean", "bottom_porepress_time")
        time_metrics(line, rows_in, "Excess_maxAbs", "excess_envelope_time")

    with (ROOT / "gpu_b5_boundary_vs_analytical_metrics.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def plot_profiles(quantity: str, outfile: str) -> None:
    mode0 = extract_legacy_svg_profiles(MODE0 / "figures" / ("gpu_g9b_excess_profiles.svg" if quantity == "ExcessPorePress" else "gpu_g9b_porepress_profiles.svg"))
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.2), sharey=True)
    lines = [("mode=0 xi=0.05", mode0, axes[0]), ("mode=1 xi=0.05", None, axes[1])]
    for title, legacy, ax in lines:
        for i, time in enumerate(TARGET_TIMES):
            color = COLORS[i % len(COLORS)]
            if legacy is not None:
                prof = legacy.get(time, [])
            else:
                prof = b5_profile(time, quantity)
            if prof:
                ax.plot([v / 1000.0 for _, v in prof], [(z - ZMIN) / H for z, _ in prof], color=color, lw=2, label=f"GPU t={time:g}s Tv={tv(time):.3g}")
            ana = analytical_profile(time, quantity)
            ax.plot([v / 1000.0 for _, v in ana], [(z - ZMIN) / H for z, _ in ana], color=color, ls="--", lw=1.4, label=f"Analytical t={time:g}s")
        ax.set_title(title)
        ax.set_xlabel(("excess pore pressure" if quantity == "ExcessPorePress" else "pore pressure") + " [kPa]")
        ax.grid(True, color="#e6e6e6", lw=0.8)
        ax.invert_yaxis()
    axes[0].set_ylabel("normalized depth z/H (top=1, bottom=0)")
    axes[1].legend(fontsize=7, loc="best")
    fig.suptitle(("Excess pressure" if quantity == "ExcessPorePress" else "Pore pressure") + " profiles: GPU vs analytical")
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{outfile}.svg")
    fig.savefig(FIGDIR / f"{outfile}.png", dpi=220)
    plt.close(fig)


def plot_timeseries(key: str, analytical: str, ylabel: str, outfile: str) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    for label, rows, color in [
        ("mode=0 xi=0.05", MODE0_ROWS, "#1f77b4"),
        ("mode=1 xi=0.05", B5_ROWS, "#d62728"),
        ("mode=0 xi=0.10", MODE010_ROWS, "#2ca02c"),
    ]:
        times = [f(r, "time") for r in rows]
        vals = [f(r, key) / 1000.0 for r in rows]
        ax.plot(times, vals, lw=2, label=label, color=color)
    times = [f(r, "time") for r in B5_ROWS]
    avals = []
    for t in times:
        y = 0.0
        ex = excess_analytical_y(y, t)
        avals.append((hydrostatic_y(y) + ex if analytical == "porepress" else ex) / 1000.0)
    ax.plot(times, avals, "k--", lw=2, label="analytical")
    ax.set_xlabel("time [s]")
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#e6e6e6")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{outfile}.svg")
    fig.savefig(FIGDIR / f"{outfile}.png", dpi=220)
    plt.close(fig)


def plot_error_depth(quantity: str, time: float, outfile: str) -> None:
    mode0 = extract_legacy_svg_profiles(MODE0 / "figures" / ("gpu_g9b_excess_profiles.svg" if quantity == "ExcessPorePress" else "gpu_g9b_porepress_profiles.svg")).get(time, [])
    b5 = b5_profile(time, quantity)
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    for label, profile, color in [("mode=0 xi=0.05", mode0, "#1f77b4"), ("mode=1 xi=0.05", b5, "#d62728")]:
        xs, ys = [], []
        for z, val in profile:
            ref = excess_analytical_y(y_from_z(z), time) if quantity == "ExcessPorePress" else porepress_analytical_y(y_from_z(z), time)
            xs.append((val - ref) / 1000.0)
            ys.append((z - ZMIN) / H)
        ax.plot(xs, ys, lw=2, label=label, color=color)
    ax.axvline(0, color="k", lw=1)
    ax.invert_yaxis()
    ax.set_xlabel("simulation - analytical [kPa]")
    ax.set_ylabel("normalized depth z/H")
    ax.grid(True, color="#e6e6e6")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / f"{outfile}.svg")
    fig.savefig(FIGDIR / f"{outfile}.png", dpi=220)
    plt.close(fig)


def plot_boundary_decomposition(rows: list[dict[str, str]]) -> None:
    final_time = 3.6
    labels = ["bottom", "interior", "top"]
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    width = 0.34
    xs = range(len(labels))
    vals0 = []
    vals1 = []
    for region in labels:
        vals0.append(next(float(r["rmse"]) / 1000.0 for r in rows if r["line"] == "gpu_mode0_xi005" and r["quantity"] == f"ExcessPorePress_profile_t{final_time:g}" and r["region"] == region))
        vals1.append(next(float(r["rmse"]) / 1000.0 for r in rows if r["line"] == "gpu_mode1_xi005_b5" and r["quantity"] == f"ExcessPorePress_profile_t{final_time:g}" and r["region"] == region))
    ax.bar([x - width / 2 for x in xs], vals0, width=width, label="mode=0 xi=0.05")
    ax.bar([x + width / 2 for x in xs], vals1, width=width, label="mode=1 xi=0.05")
    ax.set_xticks(list(xs), labels)
    ax.set_ylabel("excess profile RMSE at t=3.6s [kPa]")
    ax.grid(True, axis="y", color="#e6e6e6")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGDIR / "gpu_b5_boundary_layer_error_decomposition.svg")
    fig.savefig(FIGDIR / "gpu_b5_boundary_layer_error_decomposition.png", dpi=220)
    plt.close(fig)


def main() -> None:
    write_profile_csv()
    write_bottom_csv()
    metrics = write_metrics()
    plot_profiles("PorePress", "gpu_b5_mode0_mode1_vs_analytical_porepress_profiles")
    plot_profiles("ExcessPorePress", "gpu_b5_mode0_mode1_vs_analytical_excess_profiles")
    plot_timeseries("bottom_PorePress_mean", "porepress", "bottom pore pressure [kPa]", "gpu_b5_bottom_porepress_time")
    plot_timeseries("bottom_Excess_mean", "excess", "bottom excess pore pressure [kPa]", "gpu_b5_bottom_excess_time")
    plot_timeseries("Excess_maxAbs", "excess", "excess envelope [kPa]", "gpu_b5_excess_envelope")
    plot_error_depth("ExcessPorePress", 3.6, "gpu_b5_excess_error_vs_depth_t3p6")
    plot_boundary_decomposition(metrics)


if __name__ == "__main__":
    main()
