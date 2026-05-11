from __future__ import annotations

import binascii
import csv
import math
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
G9B = ROOT.parent
G9 = G9B.parent / "GPU_G9_SelfWeightLong"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

TARGET_TIMES = [0.0, 0.1, 0.5, 1.0, 2.0, 3.6]
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

COLORS = {
    "xi010": "#2ca02c",
    "xi005": "#1f77b4",
    "analytical": "#111111",
    "hydro": "#777777",
    "cpu": "#ff7f0e",
}
RGB = {
    "#111111": (17, 17, 17),
    "#1f77b4": (31, 119, 180),
    "#2ca02c": (44, 160, 44),
    "#ff7f0e": (255, 127, 14),
    "#9467bd": (148, 103, 189),
    "#d62728": (214, 39, 40),
    "#777777": (119, 119, 119),
    "#bbbbbb": (187, 187, 187),
}


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


G9_ROWS = read_rows(G9 / "gpu_g9_frame_metrics.csv")
G9B_ROWS = read_rows(G9B / "gpu_g9b_frame_metrics.csv")
H = f(G9B_ROWS[0], "zmax") - f(G9B_ROWS[0], "zmin") if G9B_ROWS else 0.99
ZMIN = f(G9B_ROWS[0], "zmin") if G9B_ROWS else 0.005
ZMAX = f(G9B_ROWS[0], "zmax") if G9B_ROWS else 0.995
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
    total = 0.0
    for n, c in enumerate(COEFFS):
        lam = lambda_n(n)
        total += c * math.cos(lam * y) * math.exp(-lam * lam * CV * tau)
    return total


def porepress_analytical_y(y: float, t: float) -> float:
    return hydrostatic_y(y) + excess_analytical_y(y, t)


def tv(t: float) -> float:
    return CV * max(t - DRAIN_START, 0.0) / (H * H)


def parse_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def linear_fit(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(pairs)
    sx = sum(x for x, _ in pairs)
    sy = sum(y for _, y in pairs)
    sxx = sum(x * x for x, _ in pairs)
    sxy = sum(x * y for x, y in pairs)
    den = n * sxx - sx * sx
    if not pairs or abs(den) < 1e-12:
        return 1.0, 0.0
    a = (n * sxy - sx * sy) / den
    b = (sy - a * sx) / n
    return a, b


def extract_svg_profiles(path: Path) -> dict[float, list[tuple[float, float]]]:
    text = path.read_text(errors="ignore")
    x_ticks = []
    y_ticks = []
    for m in re.finditer(r"<text x='([^']+)' y='([^']+)'[^>]*>([^<]+)</text>", text):
        x = parse_float(m.group(1))
        y = parse_float(m.group(2))
        v = parse_float(m.group(3))
        if x is None or y is None or v is None:
            continue
        if y > 500:
            x_ticks.append((x, v))
        if x < 90:
            y_ticks.append((y, v))
    ax, bx = linear_fit(x_ticks)
    ay, by = linear_fit(y_ticks)
    polylines = re.findall(r"<polyline points='([^']+)'", text)
    labels = re.findall(r"<text [^>]*>(?:G9b xi=0.05 )?t=([0-9.]+)s</text>", text)
    out: dict[float, list[tuple[float, float]]] = {}
    for points, label in zip(polylines, labels):
        t = float(label)
        vals = []
        for token in points.split():
            try:
                px, py = [float(v) for v in token.split(",")]
            except ValueError:
                continue
            vals.append((ax * px + bx, ay * py + by))
        out[t] = vals
    return out


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
    padx = 0.04 * (xmax - xmin)
    pady = 0.08 * (ymax - ymin)
    return xmin - padx, xmax + padx, ymin - pady, ymax + pady


def svg_line_plot(path: Path, series, xlabel: str, ylabel: str, title: str, width=980, height=620) -> None:
    xmin, xmax, ymin, ymax = bounds(series)
    margin = dict(left=100, right=30, top=62, bottom=78)
    pw = width - margin["left"] - margin["right"]
    ph = height - margin["top"] - margin["bottom"]

    def sx(x): return margin["left"] + (x - xmin) / (xmax - xmin) * pw
    def sy(y): return margin["top"] + (ymax - y) / (ymax - ymin) * ph

    out = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{width/2}' y='32' text-anchor='middle' font-family='Arial' font-size='19'>{title}</text>",
        f"<line x1='{margin['left']}' y1='{height-margin['bottom']}' x2='{width-margin['right']}' y2='{height-margin['bottom']}' stroke='black'/>",
        f"<line x1='{margin['left']}' y1='{margin['top']}' x2='{margin['left']}' y2='{height-margin['bottom']}' stroke='black'/>",
        f"<text x='{width/2}' y='{height-28}' text-anchor='middle' font-family='Arial' font-size='14'>{xlabel}</text>",
        f"<text x='24' y='{height/2}' transform='rotate(-90 24 {height/2})' text-anchor='middle' font-family='Arial' font-size='14'>{ylabel}</text>",
    ]
    for i in range(6):
        x = xmin + (xmax - xmin) * i / 5
        y = ymin + (ymax - ymin) * i / 5
        out.append(f"<line x1='{sx(x):.1f}' y1='{margin['top']}' x2='{sx(x):.1f}' y2='{height-margin['bottom']}' stroke='#eeeeee'/>")
        out.append(f"<line x1='{margin['left']}' y1='{sy(y):.1f}' x2='{width-margin['right']}' y2='{sy(y):.1f}' stroke='#eeeeee'/>")
        out.append(f"<text x='{sx(x):.1f}' y='{height-margin['bottom']+19}' text-anchor='middle' font-family='Arial' font-size='10'>{x:.3g}</text>")
        out.append(f"<text x='{margin['left']-8}' y='{sy(y)+4:.1f}' text-anchor='end' font-family='Arial' font-size='10'>{y:.3g}</text>")
    legend_y = margin["top"] + 10
    for label, data, color in series:
        points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in clean_points(data))
        if points:
            dash = " stroke-dasharray='6 4'" if "analytical" in label.lower() else ""
            out.append(f"<polyline points='{points}' fill='none' stroke='{color}' stroke-width='2'{dash}/>")
        out.append(f"<line x1='{width-295}' y1='{legend_y}' x2='{width-270}' y2='{legend_y}' stroke='{color}' stroke-width='3'/>")
        out.append(f"<text x='{width-263}' y='{legend_y+4}' font-family='Arial' font-size='10'>{label}</text>")
        legend_y += 15
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


def write_png(path: Path, pixels: bytearray, width: int, height: int) -> None:
    rows = [b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height)]

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def png_line_plot(path: Path, series, width=980, height=620) -> None:
    xmin, xmax, ymin, ymax = bounds(series)
    margin = dict(left=96, right=30, top=60, bottom=74)
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
        dx, sxn = abs(x1 - x0), 1 if x0 < x1 else -1
        dy, syn = -abs(y1 - y0), 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                setpx(x0 + ox, y0 + oy, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sxn
            if e2 <= dx:
                err += dx
                y0 += syn

    grey, black = (232, 232, 232), (20, 20, 20)
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


def analytical_profile(t: float, npts: int = 100) -> list[tuple[float, float, float, float]]:
    out = []
    for i in range(npts):
        y = H * i / (npts - 1)
        z = z_from_y(y)
        ex = excess_analytical_y(y, t)
        hp = hydrostatic_y(y)
        out.append((z, y / H, ex, hp + ex))
    return out


def write_analytical_csvs() -> None:
    frame_times = [f(r, "time") for r in G9B_ROWS]
    with (ROOT / "analytical_profile_timeseries.csv").open("w", newline="") as fp:
        fields = ["time", "Tv", "z", "z_norm", "analytical_excess", "analytical_hydrostatic", "analytical_porepress"]
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for t in TARGET_TIMES:
            for z, zn, ex, pp in analytical_profile(t):
                writer.writerow({
                    "time": f"{t:.12g}",
                    "Tv": f"{tv(t):.12g}",
                    "z": f"{z:.12g}",
                    "z_norm": f"{zn:.12g}",
                    "analytical_excess": f"{ex:.12g}",
                    "analytical_hydrostatic": f"{hydrostatic_y(y_from_z(z)):.12g}",
                    "analytical_porepress": f"{pp:.12g}",
                })
    with (ROOT / "analytical_bottom_timeseries.csv").open("w", newline="") as fp:
        fields = [
            "time", "Tv", "analytical_bottom_excess", "analytical_bottom_porepress",
            "analytical_bottom_hydrostatic", "gpu_xi010_bottom_excess", "gpu_xi005_bottom_excess",
            "gpu_xi010_bottom_porepress", "gpu_xi005_bottom_porepress",
        ]
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        g9 = {round(f(r, "time"), 10): r for r in G9_ROWS}
        g9b = {round(f(r, "time"), 10): r for r in G9B_ROWS}
        for t in frame_times:
            key = round(t, 10)
            y = 0.0
            ex = excess_analytical_y(y, t)
            hp = hydrostatic_y(y)
            writer.writerow({
                "time": f"{t:.12g}",
                "Tv": f"{tv(t):.12g}",
                "analytical_bottom_excess": f"{ex:.12g}",
                "analytical_bottom_porepress": f"{hp + ex:.12g}",
                "analytical_bottom_hydrostatic": f"{hp:.12g}",
                "gpu_xi010_bottom_excess": g9.get(key, {}).get("bottom_Excess_mean", ""),
                "gpu_xi005_bottom_excess": g9b.get(key, {}).get("bottom_Excess_mean", ""),
                "gpu_xi010_bottom_porepress": g9.get(key, {}).get("bottom_PorePress_mean", ""),
                "gpu_xi005_bottom_porepress": g9b.get(key, {}).get("bottom_PorePress_mean", ""),
            })


def interp_analytical_profile(z: float, t: float, quantity: str) -> float:
    y = y_from_z(z)
    ex = excess_analytical_y(y, t)
    if quantity == "excess":
        return ex
    return hydrostatic_y(y) + ex


def error_stats(values: list[tuple[float, float]]) -> dict[str, float]:
    diffs = [a - b for a, b in values if math.isfinite(a) and math.isfinite(b)]
    refs = [b for _, b in values if math.isfinite(b)]
    if not diffs:
        return {"rmse": math.nan, "mean_abs": math.nan, "max_abs": math.nan, "rel_rmse": math.nan}
    rmse = math.sqrt(sum(d * d for d in diffs) / len(diffs))
    mean_abs = sum(abs(d) for d in diffs) / len(diffs)
    max_abs = max(abs(d) for d in diffs)
    ref_rms = math.sqrt(sum(r * r for r in refs) / len(refs)) if refs else math.nan
    return {
        "rmse": rmse,
        "mean_abs": mean_abs,
        "max_abs": max_abs,
        "rel_rmse": rmse / ref_rms if ref_rms else math.nan,
    }


def add_metric(rows: list[dict[str, str]], quantity: str, line: str, compared: list[tuple[float, float]], note: str) -> None:
    st = error_stats(compared)
    rows.append({
        "quantity": quantity,
        "line": line,
        "n": str(len(compared)),
        "rmse": f"{st['rmse']:.12g}",
        "mean_abs_error": f"{st['mean_abs']:.12g}",
        "max_abs_error": f"{st['max_abs']:.12g}",
        "relative_rmse": f"{st['rel_rmse']:.12g}",
        "note": note,
    })


def metrics() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label, sim_rows in (("gpu_xi010", G9_ROWS), ("gpu_xi005", G9B_ROWS)):
        pairs_ex = []
        pairs_pp = []
        pairs_env = []
        for r in sim_rows:
            t = f(r, "time")
            if t <= 0.0:
                continue
            y = 0.0
            ex = excess_analytical_y(y, t)
            hp = hydrostatic_y(y)
            pairs_ex.append((f(r, "bottom_Excess_mean"), ex))
            pairs_pp.append((f(r, "bottom_PorePress_mean"), hp + ex))
            pairs_env.append((f(r, "Excess_maxAbs"), ex))
        add_metric(rows, "bottom_excess_time", label, pairs_ex, "time-series metrics, t=0 omitted because saved GPU frame is pre-undrained initialization")
        add_metric(rows, "bottom_porepress_time", label, pairs_pp, "time-series metrics, t=0 omitted")
        add_metric(rows, "excess_envelope_time", label, pairs_env, "analytical envelope equals bottom excess for this 1D linear initial condition")

    for stem, quantity in (("excess", "excess"), ("porepress", "porepress")):
        for line, base, color in (
            ("gpu_xi010", G9 / "figures" / f"gpu_g9_{stem}_profiles.svg", COLORS["xi010"]),
            ("gpu_xi005", G9B / "figures" / f"gpu_g9b_{stem}_profiles.svg", COLORS["xi005"]),
        ):
            profs = extract_svg_profiles(base)
            for t in TARGET_TIMES:
                if t <= 0.0 or t not in profs:
                    continue
                pairs = []
                for z, sim in profs[t]:
                    pairs.append((sim, interp_analytical_profile(z, t, quantity)))
                add_metric(rows, f"{quantity}_profile_t{t:g}", line, pairs, "profile values recovered approximately from retained SVG because raw PartCsv profiles were cleaned")
    return rows


def profile_series(kind: str):
    g9_ex = extract_svg_profiles(G9 / "figures" / f"gpu_g9_{kind}_profiles.svg")
    g9b_ex = extract_svg_profiles(G9B / "figures" / f"gpu_g9b_{kind}_profiles.svg")
    series = []
    for t in TARGET_TIMES:
        if t == 0.0:
            continue
        if t in g9_ex:
            series.append((f"xi=0.10 t={t:g}s", g9_ex[t], COLORS["xi010"]))
        if t in g9b_ex:
            series.append((f"xi=0.05 t={t:g}s", g9b_ex[t], COLORS["xi005"]))
        aprof = analytical_profile(t)
        if kind == "excess":
            series.append((f"analytical t={t:g}s", [(z, ex) for z, _, ex, _ in aprof], COLORS["analytical"]))
        else:
            series.append((f"analytical t={t:g}s", [(z, pp) for z, _, _, pp in aprof], COLORS["analytical"]))
    return series


def series_from_rows(rows: list[dict[str, str]], xkey: str, ykey: str, label: str, color: str):
    return (label, [(f(r, xkey), f(r, ykey)) for r in rows], color)


def make_plots() -> None:
    save_plot(
        "gpu_g9_g9b_vs_analytical_porepress_profiles",
        profile_series("porepress"),
        "z (m)",
        "Pore pressure (Pa)",
        "GPU G9/G9b vs Analytical Pore Pressure Profiles",
    )
    save_plot(
        "gpu_g9_g9b_vs_analytical_excess_profiles",
        profile_series("excess"),
        "z (m)",
        "Excess pore pressure (Pa)",
        "GPU G9/G9b vs Analytical Excess Profiles",
    )
    bottom_rows = read_rows(ROOT / "analytical_bottom_timeseries.csv")
    save_plot(
        "gpu_g9_g9b_vs_analytical_bottom_porepress_time",
        [
            series_from_rows(G9_ROWS, "time", "bottom_PorePress_mean", "GPU xi=0.10", COLORS["xi010"]),
            series_from_rows(G9B_ROWS, "time", "bottom_PorePress_mean", "GPU xi=0.05", COLORS["xi005"]),
            series_from_rows(bottom_rows, "time", "analytical_bottom_porepress", "analytical", COLORS["analytical"]),
            series_from_rows(bottom_rows, "time", "analytical_bottom_hydrostatic", "hydrostatic end-state", COLORS["hydro"]),
        ],
        "time (s)",
        "bottom pore pressure (Pa)",
        "Bottom Pore Pressure vs Analytical",
    )
    save_plot(
        "gpu_g9_g9b_vs_analytical_bottom_excess_time",
        [
            series_from_rows(G9_ROWS, "time", "bottom_Excess_mean", "GPU xi=0.10", COLORS["xi010"]),
            series_from_rows(G9B_ROWS, "time", "bottom_Excess_mean", "GPU xi=0.05", COLORS["xi005"]),
            series_from_rows(bottom_rows, "time", "analytical_bottom_excess", "analytical", COLORS["analytical"]),
        ],
        "time (s)",
        "bottom excess pore pressure (Pa)",
        "Bottom Excess vs Analytical",
    )
    save_plot(
        "gpu_g9_g9b_vs_analytical_excess_envelope",
        [
            series_from_rows(G9_ROWS, "time", "Excess_maxAbs", "GPU xi=0.10", COLORS["xi010"]),
            series_from_rows(G9B_ROWS, "time", "Excess_maxAbs", "GPU xi=0.05", COLORS["xi005"]),
            series_from_rows(bottom_rows, "time", "analytical_bottom_excess", "analytical envelope", COLORS["analytical"]),
        ],
        "time (s)",
        "excess envelope (Pa)",
        "Excess Envelope vs Analytical",
    )
    norm = []
    p0b = excess_analytical_y(0.0, 0.0)
    for r in G9_ROWS:
        norm.append(("g9", tv(f(r, "time")), f(r, "bottom_Excess_mean") / p0b))
    for r in G9B_ROWS:
        norm.append(("g9b", tv(f(r, "time")), f(r, "bottom_Excess_mean") / p0b))
    analytical_norm = [(tv(f(r, "time")), f(r, "analytical_bottom_excess") / p0b) for r in bottom_rows]
    save_plot(
        "gpu_g9_g9b_vs_analytical_normalized_comparison",
        [
            ("GPU xi=0.10", [(x, y) for tag, x, y in norm if tag == "g9"], COLORS["xi010"]),
            ("GPU xi=0.05", [(x, y) for tag, x, y in norm if tag == "g9b"], COLORS["xi005"]),
            ("analytical", analytical_norm, COLORS["analytical"]),
        ],
        "Tv = cv(t-0.002)/H^2",
        "bottom excess / initial analytical bottom excess",
        "Normalized Bottom Excess Comparison",
    )


def write_notes() -> None:
    p0b = excess_analytical_y(0.0, 0.0)
    note = f"""# Analytical Solution Notes for GPU G9/G9b Scenario 2 Comparison

Source:

- `src/papers/u-p/supporting_information_implementation_notes.md`, Section 3.
- Initial self-weight pore pressure from Eq. (4) in the local notes:
  `p0(z) = [(Kw/n) rho g (H-z)] / [K + 4G/3 + Kw/n]`.
- Dissipation basis from the Supporting Information Scenario 1 cosine series:
  `u(z,t) = sum A_n cos(lambda_n z) exp(-lambda_n^2 c_v t)`,
  with `lambda_n=(2n+1)pi/(2H)`.
- Scenario 2 keeps gravity on, so total pore pressure is reconstructed as
  `p_total(z,t)=p_hydro(z)+u(z,t)` and tends toward hydrostatic pressure.

No machine-readable Supporting Information curve data were found in the
repository. Curves here are reconstructed from the formulas above.

Parameters used:

- `E={E:g} Pa`
- `nu={NU:g}`
- `K={K_BULK:.12g} Pa`
- `G={G_SHEAR:.12g} Pa`
- `M=K+4G/3={M_1D:.12g} Pa`
- `Kw={KW:g} Pa`
- `n={POROSITY:g}`
- `k={KPERM:g} m/s`
- `rho_w={RHO_W:g} kg/m3`
- `rho={RHO_SOIL:g} kg/m3`
- `g={G:g} m/s2`
- `zmin={ZMIN:.12g} m`
- `zmax={ZMAX:.12g} m`
- `H={H:.12g} m`
- `cv=k*M/(rho_w*g)={CV:.12g} m2/s`
- drainage clock starts at `t={DRAIN_START:g} s`
- analytical initial bottom excess `u(0,0)={p0b:.12g} Pa`

Important data limitation:

The G9/G9b raw `PartCsv_*.csv` profile data were intentionally cleaned after
the long runs. Time-series comparisons use retained frame-metrics CSV files.
Profile comparisons recover approximate profile curves from the retained SVG
figures; therefore profile error metrics are approximate and are marked as such
in `analytical_comparison_metrics.csv`.
"""
    (ROOT / "analytical_solution_notes.md").write_text(note, encoding="utf-8")


def main() -> None:
    write_analytical_csvs()
    rows = metrics()
    with (ROOT / "analytical_comparison_metrics.csv").open("w", newline="") as fp:
        fields = ["quantity", "line", "n", "rmse", "mean_abs_error", "max_abs_error", "relative_rmse", "note"]
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    write_notes()
    make_plots()


if __name__ == "__main__":
    main()
