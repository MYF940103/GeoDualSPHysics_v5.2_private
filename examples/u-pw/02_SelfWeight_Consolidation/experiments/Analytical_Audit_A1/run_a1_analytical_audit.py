from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Arial"

ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
G9 = EXP / "GPU_G9_SelfWeightLong"
G9B = EXP / "GPU_G9b_SelfWeightLong_Xi005"
B5 = EXP / "GPU_B5_BoundaryOperatorLong_Xi005"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

TARGET_TIMES = [0.1, 0.5, 1.0, 2.0, 3.6]
NTERMS = 400

E = 2.0e6
NU = 0.3
KW = 2.0e8
POROSITY = 0.3
KPERM = 1.0e-3
RHO_SOIL = 2100.0
RHO_W = 1000.0
G = 9.81
DP = 0.01
KERNEL_H = 0.018
DRAIN_START = 0.002


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", errors="ignore") as fp:
        sample = fp.read(4096)
        fp.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        return list(csv.DictReader(fp, delimiter=delim))


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return math.nan


G9_ROWS = read_rows(G9 / "gpu_g9_frame_metrics.csv")
G9B_ROWS = read_rows(G9B / "gpu_g9b_frame_metrics.csv")
B5_ROWS = read_rows(B5 / "gpu_b5_boundary_operator_frame_metrics.csv")
B5_PROFILE_ROWS = read_rows(B5 / "gpu_b5_boundary_vs_analytical_profile_timeseries.csv")

ZMIN = f(G9B_ROWS[0], "zmin") if G9B_ROWS else 0.005
ZMAX = f(G9B_ROWS[0], "zmax") if G9B_ROWS else 0.995
H = ZMAX - ZMIN
K_BULK = E / (3.0 * (1.0 - 2.0 * NU))
G_SHEAR = E / (2.0 * (1.0 + NU))
M_1D = K_BULK + 4.0 * G_SHEAR / 3.0
STORAGE_MOD = (M_1D * (KW / POROSITY)) / (M_1D + (KW / POROSITY))
CV_ANALYTICAL = KPERM * M_1D / (RHO_W * G)
CV_STORAGE = KPERM * STORAGE_MOD / (RHO_W * G)
D_DIRECT_PR = (KW / POROSITY) * KPERM / (RHO_W * G)
P0_SLOPE = (KW / POROSITY) * RHO_SOIL * G / (M_1D + KW / POROSITY)
P0_BOTTOM = P0_SLOPE * H


def lambda_n(n: int) -> float:
    return (2 * n + 1) * math.pi / (2 * H)


def coeff_n(n: int) -> float:
    lam = lambda_n(n)
    return 2.0 * P0_SLOPE / (H * lam * lam)


COEFFS = [coeff_n(i) for i in range(NTERMS)]


def y_from_z(z: float) -> float:
    return max(0.0, min(H, z - ZMIN))


def z_from_y(y: float) -> float:
    return ZMIN + y


def hydrostatic_y(y: float) -> float:
    return RHO_W * G * max(H - y, 0.0)


def excess_series_y(y: float, t: float, shift: float = DRAIN_START, cv: float = CV_ANALYTICAL) -> float:
    tau = max(t - shift, 0.0)
    return sum(c * math.cos(lambda_n(n) * y) * math.exp(-lambda_n(n) ** 2 * cv * tau) for n, c in enumerate(COEFFS))


def tv(t: float, shift: float = DRAIN_START, cv: float = CV_ANALYTICAL) -> float:
    return cv * max(t - shift, 0.0) / (H * H)


def initial_excess_y(y: float) -> float:
    return P0_SLOPE * (H - y)


def fd_reference(times: list[float], cv: float = CV_ANALYTICAL, shift: float = DRAIN_START, ny: int = 401) -> dict[float, list[tuple[float, float]]]:
    """Implicit finite-volume diffusion for u_t=cv*u_yy, u(H)=0, u_y(0)=0."""
    ys = [H * i / (ny - 1) for i in range(ny)]
    dy = ys[1] - ys[0]
    u = [initial_excess_y(y) for y in ys]
    out: dict[float, list[tuple[float, float]]] = {}
    sorted_times = sorted(times)
    current = 0.0

    def solve_tridiag(a: list[float], b: list[float], c: list[float], d: list[float]) -> list[float]:
        n = len(d)
        cp = [0.0] * n
        dp = [0.0] * n
        cp[0] = c[0] / b[0]
        dp[0] = d[0] / b[0]
        for i in range(1, n):
            den = b[i] - a[i] * cp[i - 1]
            cp[i] = c[i] / den if i < n - 1 else 0.0
            dp[i] = (d[i] - a[i] * dp[i - 1]) / den
        x = [0.0] * n
        x[-1] = dp[-1]
        for i in range(n - 2, -1, -1):
            x[i] = dp[i] - cp[i] * x[i + 1]
        return x

    for t in sorted_times:
        target = max(t - shift, 0.0)
        if target <= 0.0:
            out[t] = list(zip(ys, u))
            continue
        while current < target - 1e-14:
            dt = min(0.0005, target - current)
            r = cv * dt / (dy * dy)
            a = [0.0] * ny
            b = [0.0] * ny
            c = [0.0] * ny
            d = u[:]
            # bottom no-flux: u_-1 = u_1 -> second derivative 2*(u1-u0)/dy^2
            b[0] = 1.0 + 2.0 * r
            c[0] = -2.0 * r
            for i in range(1, ny - 1):
                a[i] = -r
                b[i] = 1.0 + 2.0 * r
                c[i] = -r
            # top drained Dirichlet
            b[-1] = 1.0
            d[-1] = 0.0
            u = solve_tridiag(a, b, c, d)
            current += dt
        out[t] = list(zip(ys, u))
    return out


def nearest_frame(rows: list[dict[str, str]], time: float) -> dict[str, str]:
    return min(rows, key=lambda r: abs(f(r, "time") - time))


def interp(profile: list[tuple[float, float]], y: float) -> float:
    pts = sorted(profile)
    if y <= pts[0][0]:
        return pts[0][1]
    if y >= pts[-1][0]:
        return pts[-1][1]
    for (y0, v0), (y1, v1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            s = (y - y0) / (y1 - y0) if y1 != y0 else 0.0
            return v0 + s * (v1 - v0)
    return math.nan


def profile_from_csv(line: str, time: float, quantity: str) -> list[tuple[float, float]]:
    rows = []
    for row in B5_PROFILE_ROWS:
        if row.get("line") == line and row.get("quantity") == quantity and abs(f(row, "time") - time) < 1e-9:
            z = f(row, "z")
            v = f(row, "value")
            if math.isfinite(z) and math.isfinite(v):
                rows.append((y_from_z(z), v))
    return sorted(rows)


def write_parameter_audit() -> None:
    rows = [
        ("H / material height", f"{H:.12g}", f"{H:.12g}", "frame metrics zmax-zmin", "consistent with comparison, nominal SI H=1.0 differs by one particle spacing", "The code material centers span 0.005..0.995 m, so H=0.99 m was used."),
        ("Drainage path Hdr", f"{H:.12g}", f"{H:.12g}", "top drained + bottom no-flux", "consistent", "Single drainage to top."),
        ("Coordinate", "hydraulic elevation from bottom upward", "z measured bottom upward", "code helper / SI notes", "consistent", "Plots use z/H=0 bottom, 1 top."),
        ("dp", f"{DP:.12g}", "not in continuum analytical", "XML", "not applicable", "Particle spacing affects SPH operator but not analytical curve."),
        ("KernelH", f"{KERNEL_H:.12g}", "not in continuum analytical", "GenCase H", "not applicable", "Boundary layer corrections use KernelH."),
        ("Porosity0 n", f"{POROSITY:.12g}", f"{POROSITY:.12g}", "XML/material and analytical notes", "consistent", ""),
        ("HydraulicConductivity k", f"{KPERM:.12g}", f"{KPERM:.12g}", "XML/material and analytical notes", "consistent", ""),
        ("WaterBulkModulus Kw", f"{KW:.12g}", f"{KW:.12g}", "XML/material and analytical notes", "consistent for p0; not used in simplified cv", "Analytical cv used M*k/(rho_w*g), relying on Kw/n >> M."),
        ("WaterDensity rho_w", f"{RHO_W:.12g}", f"{RHO_W:.12g}", "XML/material and analytical notes", "consistent", ""),
        ("Gravity magnitude", f"{G:.12g}", f"{G:.12g}", "XML", "consistent", ""),
        ("M constrained modulus", f"{M_1D:.12g}", f"{M_1D:.12g}", "E, nu", "consistent", ""),
        ("cv analytical", "", f"{CV_ANALYTICAL:.12g}", "analytical reconstruction", "assumption", "Uses k*M/(rho_w*g)."),
        ("cv finite-Kw storage", "", f"{CV_STORAGE:.12g}", "derived check", "near-consistent", "Using M*Kw/n/(M+Kw/n) changes cv by less than 0.5%."),
        ("Direct PR hydraulic diffusivity", f"{D_DIRECT_PR:.12g}", "not used", "code hydraulic term before mechanical storage elimination", "not the analytical equation", "Direct pressure-only PR hydraulic coefficient is much larger; coupled mechanics supplies effective storage."),
        ("Top drained start", f"{DRAIN_START:.12g}", f"{DRAIN_START:.12g}", "XML and comparison script", "consistent in current reconstruction", "A1 also tests no-shift and best-fit offsets."),
        ("Initial excess profile", "generated dynamically during first 0.002 s, not saved", "linear self-weight p0(y)=P0*(H-y)", "SI Eq. 4", "partly inconsistent / unobserved", "Saved Part_0000 is hydrostatic excess=0, not the analytical post-undrained initial state."),
        ("Bottom extraction", "mean of bottom KernelH layer", "point y=0 bottom value", "analysis scripts", "approximation", "Layer averaging can contribute small systematic bias."),
    ]
    with (ROOT / "analytical_parameter_audit.csv").open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["parameter", "value_used_in_code", "value_used_in_analytical", "source", "consistency_status", "notes"])
        writer.writerows(rows)


def rmse_for_shift(rows: list[dict[str, str]], shift: float, key: str = "bottom_Excess_mean", cv: float = CV_ANALYTICAL) -> tuple[float, float, float, float, int]:
    errs = []
    refs = []
    for row in rows:
        t = f(row, "time")
        if not math.isfinite(t) or t <= 0:
            continue
        ref = excess_series_y(0.0, t, shift=shift, cv=cv)
        val = f(row, key)
        if math.isfinite(val) and math.isfinite(ref):
            errs.append(val - ref)
            refs.append(ref)
    if not errs:
        return math.nan, math.nan, math.nan, math.nan, 0
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
    mae = sum(abs(e) for e in errs) / len(errs)
    maxabs = max(abs(e) for e in errs)
    denom = math.sqrt(sum(r * r for r in refs) / len(refs))
    return rmse, mae, maxabs, rmse / denom if denom else math.nan, len(errs)


def write_time_shift_metrics() -> None:
    shifts = [0.0, DRAIN_START] + [x / 1000 for x in range(-20, 51)]
    rows_out = []
    for line, data in [("gpu_mode0_xi005", G9B_ROWS), ("gpu_mode1_xi005_b5", B5_ROWS), ("gpu_mode0_xi010", G9_ROWS)]:
        best = None
        for shift in shifts:
            rmse, mae, maxabs, rel, n = rmse_for_shift(data, shift)
            row = {
                "line": line,
                "shift": f"{shift:.12g}",
                "n": str(n),
                "rmse": f"{rmse:.12g}",
                "mean_abs_error": f"{mae:.12g}",
                "max_abs_error": f"{maxabs:.12g}",
                "relative_rmse": f"{rel:.12g}",
                "kind": "diagnostic_bestfit_grid" if shift not in (0.0, DRAIN_START) else ("no_shift" if shift == 0.0 else "drain_start_shift"),
            }
            rows_out.append(row)
            if best is None or rmse < float(best["rmse"]):
                best = row
        if best:
            best2 = dict(best)
            best2["kind"] = "best_shift_for_line"
            rows_out.append(best2)
    with (ROOT / "time_shift_sensitivity_metrics.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)


def write_fd_metrics() -> None:
    times = [f(r, "time") for r in B5_ROWS if f(r, "time") > 0]
    variants = {
        "series_homogeneous_cvM_shift0p002": (CV_ANALYTICAL, DRAIN_START),
        "fd_homogeneous_cvM_shift0p002": (CV_ANALYTICAL, DRAIN_START),
        "fd_storage_cvFiniteKw_shift0p002": (CV_STORAGE, DRAIN_START),
        "fd_direct_PR_hydraulic_only_shift0p002": (D_DIRECT_PR, DRAIN_START),
        "fd_homogeneous_cvM_no_shift": (CV_ANALYTICAL, 0.0),
    }
    fd_profiles = {name: fd_reference(TARGET_TIMES + times, cv=cv, shift=shift) for name, (cv, shift) in variants.items() if name.startswith("fd_")}
    rows_out = []
    for variant, (cv, shift) in variants.items():
        if variant.startswith("series"):
            def ref_bottom(t): return excess_series_y(0.0, t, shift=shift, cv=cv)
        else:
            def ref_bottom(t, variant=variant): return interp(fd_profiles[variant][t], 0.0)
        for line, data in [("gpu_mode0_xi005", G9B_ROWS), ("gpu_mode1_xi005_b5", B5_ROWS), ("gpu_mode0_xi010", G9_ROWS)]:
            errs = []
            refs = []
            for row in data:
                t = f(row, "time")
                if not math.isfinite(t) or t <= 0:
                    continue
                ref = ref_bottom(t)
                val = f(row, "bottom_Excess_mean")
                if math.isfinite(ref) and math.isfinite(val):
                    errs.append(val - ref)
                    refs.append(ref)
            rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
            denom = math.sqrt(sum(r * r for r in refs) / len(refs))
            rows_out.append({
                "reference": variant,
                "line": line,
                "n": str(len(errs)),
                "rmse": f"{rmse:.12g}",
                "mean_abs_error": f"{sum(abs(e) for e in errs)/len(errs):.12g}",
                "max_abs_error": f"{max(abs(e) for e in errs):.12g}",
                "relative_rmse": f"{rmse/denom if denom else math.nan:.12g}",
                "cv": f"{cv:.12g}",
                "shift": f"{shift:.12g}",
            })
    with (ROOT / "fd_reference_metrics.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)


def write_initial_condition() -> None:
    b5_t01 = profile_from_csv("gpu_mode1_xi005_b5", 0.1, "ExcessPorePress")
    mode0_t01 = profile_from_csv("gpu_mode0_xi005_approx", 0.1, "ExcessPorePress")
    rows = []
    ys = [H * i / 150 for i in range(151)]
    for y in ys:
        rows.append({
            "z": f"{z_from_y(y):.12g}",
            "z_norm": f"{y/H:.12g}",
            "analytical_initial_excess": f"{initial_excess_y(y):.12g}",
            "saved_frame0_excess": "0",
            "analytical_t0p1_excess": f"{excess_series_y(y, 0.1):.12g}",
            "fd_t0p1_excess": f"{interp(fd_reference([0.1])[0.1], y):.12g}",
            "gpu_mode0_t0p1_excess_approx": f"{interp(mode0_t01, y):.12g}" if mode0_t01 else "",
            "gpu_mode1_t0p1_excess": f"{interp(b5_t01, y):.12g}" if b5_t01 else "",
        })
    with (ROOT / "initial_condition_comparison.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_bottom_and_profile_csv() -> None:
    fd = fd_reference(TARGET_TIMES + [f(r, "time") for r in B5_ROWS if f(r, "time") > 0])
    with (ROOT / "analytical_vs_fd_vs_gpu_bottom_excess.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["line", "time", "Tv", "bottom_excess"])
        writer.writeheader()
        for name, data in [("gpu_mode0_xi005", G9B_ROWS), ("gpu_mode1_xi005_b5", B5_ROWS), ("gpu_mode0_xi010", G9_ROWS)]:
            for row in data:
                t = f(row, "time")
                if math.isfinite(t):
                    writer.writerow({"line": name, "time": f"{t:.12g}", "Tv": f"{tv(t):.12g}", "bottom_excess": row.get("bottom_Excess_mean", "")})
        for row in B5_ROWS:
            t = f(row, "time")
            if math.isfinite(t):
                writer.writerow({"line": "analytical_series", "time": f"{t:.12g}", "Tv": f"{tv(t):.12g}", "bottom_excess": f"{excess_series_y(0.0,t):.12g}"})
                if t in fd:
                    writer.writerow({"line": "fd_homogeneous", "time": f"{t:.12g}", "Tv": f"{tv(t):.12g}", "bottom_excess": f"{interp(fd[t],0.0):.12g}"})
    with (ROOT / "analytical_vs_fd_vs_gpu_profiles.csv").open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["line", "time", "Tv", "z", "z_norm", "excess"])
        writer.writeheader()
        for t in TARGET_TIMES:
            for line in ["gpu_mode0_xi005_approx", "gpu_mode1_xi005_b5"]:
                for y, val in profile_from_csv(line, t, "ExcessPorePress"):
                    writer.writerow({"line": line, "time": f"{t:.12g}", "Tv": f"{tv(t):.12g}", "z": f"{z_from_y(y):.12g}", "z_norm": f"{y/H:.12g}", "excess": f"{val:.12g}"})
            for y in [H * i / 180 for i in range(181)]:
                writer.writerow({"line": "analytical_series", "time": f"{t:.12g}", "Tv": f"{tv(t):.12g}", "z": f"{z_from_y(y):.12g}", "z_norm": f"{y/H:.12g}", "excess": f"{excess_series_y(y,t):.12g}"})
                writer.writerow({"line": "fd_homogeneous", "time": f"{t:.12g}", "Tv": f"{tv(t):.12g}", "z": f"{z_from_y(y):.12g}", "z_norm": f"{y/H:.12g}", "excess": f"{interp(fd[t],y):.12g}"})


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIGDIR / f"{name}.svg")
    plt.savefig(FIGDIR / f"{name}.png", dpi=220)
    plt.close()


def plot_all() -> None:
    # initial condition
    init_rows = read_rows(ROOT / "initial_condition_comparison.csv")
    plt.figure(figsize=(6.5, 4.8))
    for key, label, style in [
        ("analytical_initial_excess", "analytical initial at drain start", "k-"),
        ("saved_frame0_excess", "saved frame 0 (pre-undrained)", "k:"),
        ("analytical_t0p1_excess", "analytical t=0.1s", "C0--"),
        ("gpu_mode0_t0p1_excess_approx", "GPU mode=0 t=0.1s approx", "C1-"),
        ("gpu_mode1_t0p1_excess", "GPU mode=1 t=0.1s", "C3-"),
    ]:
        xs = [f(r, key) / P0_BOTTOM for r in init_rows if r.get(key, "")]
        ys = [f(r, "z_norm") for r in init_rows if r.get(key, "")]
        plt.plot(xs, ys, style, label=label)
    plt.xlabel("normalized excess pressure")
    plt.ylabel("z/H")
    plt.grid(True, color="#e6e6e6")
    plt.legend(fontsize=7)
    savefig("initial_excess_profile_comparison")

    # bottom excess
    bottom_rows = read_rows(ROOT / "analytical_vs_fd_vs_gpu_bottom_excess.csv")
    plt.figure(figsize=(7.0, 4.6))
    for line, label, style in [
        ("gpu_mode0_xi005", "GPU mode=0 xi=0.05", "C0-"),
        ("gpu_mode1_xi005_b5", "GPU mode=1 xi=0.05", "C3-"),
        ("analytical_series", "analytical series", "k--"),
        ("fd_homogeneous", "FD homogeneous", "C2:"),
    ]:
        rows = [r for r in bottom_rows if r["line"] == line]
        plt.plot([f(r, "Tv") for r in rows], [f(r, "bottom_excess") / P0_BOTTOM for r in rows], style, label=label)
    plt.xlabel("Tv")
    plt.ylabel("bottom excess / analytical initial bottom excess")
    plt.grid(True, color="#e6e6e6")
    plt.legend(fontsize=8)
    savefig("bottom_excess_analytical_vs_fd_vs_gpu")

    # profile comparison
    prof_rows = read_rows(ROOT / "analytical_vs_fd_vs_gpu_profiles.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.0), sharey=True)
    for ax, time in zip(axes, [0.1, 3.6]):
        for line, label, style in [
            ("gpu_mode0_xi005_approx", "GPU mode=0 approx", "C0-"),
            ("gpu_mode1_xi005_b5", "GPU mode=1", "C3-"),
            ("analytical_series", "analytical", "k--"),
            ("fd_homogeneous", "FD", "C2:"),
        ]:
            rows = [r for r in prof_rows if r["line"] == line and abs(f(r, "time") - time) < 1e-9]
            ax.plot([f(r, "excess") / P0_BOTTOM for r in rows], [f(r, "z_norm") for r in rows], style, label=label)
        ax.set_title(f"t={time:g}s, Tv={tv(time):.3g}")
        ax.set_xlabel("normalized excess pressure")
        ax.grid(True, color="#e6e6e6")
    axes[0].set_ylabel("z/H")
    axes[1].legend(fontsize=8)
    savefig("excess_profiles_analytical_vs_fd_vs_gpu")

    # time shift
    shift_rows = read_rows(ROOT / "time_shift_sensitivity_metrics.csv")
    plt.figure(figsize=(7.0, 4.6))
    for line, label in [("gpu_mode0_xi005", "mode=0 xi=0.05"), ("gpu_mode1_xi005_b5", "mode=1 xi=0.05")]:
        rows = [r for r in shift_rows if r["line"] == line and r["kind"] == "diagnostic_bestfit_grid"]
        plt.plot([f(r, "shift") for r in rows], [f(r, "relative_rmse") for r in rows], label=label)
    plt.axvline(DRAIN_START, color="k", ls="--", lw=1, label="drain start 0.002s")
    plt.xlabel("analytical time shift [s]")
    plt.ylabel("bottom excess relative RMSE")
    plt.grid(True, color="#e6e6e6")
    plt.legend(fontsize=8)
    savefig("time_shift_sensitivity")

    # FD variants
    fd_rows = read_rows(ROOT / "fd_reference_metrics.csv")
    plt.figure(figsize=(7.2, 4.8))
    variants = sorted({r["reference"] for r in fd_rows})
    vals = []
    for variant in variants:
        row = next(r for r in fd_rows if r["reference"] == variant and r["line"] == "gpu_mode0_xi005")
        vals.append(f(row, "relative_rmse"))
    plt.bar(range(len(variants)), vals)
    plt.xticks(range(len(variants)), variants, rotation=25, ha="right", fontsize=8)
    plt.ylabel("bottom excess relative RMSE vs GPU mode=0")
    plt.grid(True, axis="y", color="#e6e6e6")
    savefig("fd_reference_variants")

    # error ranking
    ranking = [
        ("time factor / offset", 0.0005),
        ("finite-Kw cv correction", 0.002),
        ("initial state not saved / dynamic build-up", 0.04),
        ("mechanical coupling damping/Shepard", 0.06),
        ("SPH operator/discretization", 0.08),
        ("boundary layer/projection", 0.001),
    ]
    plt.figure(figsize=(7.2, 4.8))
    plt.barh([x[0] for x in ranking], [x[1] for x in ranking])
    plt.xlabel("estimated priority / relative contribution indicator")
    plt.grid(True, axis="x", color="#e6e6e6")
    savefig("error_source_ranking")


def main() -> None:
    write_parameter_audit()
    write_time_shift_metrics()
    write_fd_metrics()
    write_initial_condition()
    write_bottom_and_profile_csv()
    plot_all()


if __name__ == "__main__":
    main()
