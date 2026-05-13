#!/usr/bin/env python3
"""C5o corrected Laplacian stabilization audit for strict Cryer."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
PLAN_ROOT = ROOT.parent
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

C5I = PLAN_ROOT / "C5i_SphericalDiffusionFluxCalibration"
C5J = PLAN_ROOT / "C5j_MLSBoundaryFlux"
C5K = PLAN_ROOT / "C5k_RadialShellFluxBoundary"
C5L = PLAN_ROOT / "C5l_RadialOperatorAudit"
C5M = PLAN_ROOT / "C5m_ConservativeShellExchange"
C5N = PLAN_ROOT / "C5n_CorrectedLaplacian"
C5H = PLAN_ROOT / "C5h_HigherResolutionSphere"

RADIUS = 0.05
DOMAIN_HALF = 0.16
HDP = 1.8
RADIAL_BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0)]
AUDIT_BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0), (1.0, 1.12)]

CASES = [
    {
        "label": "mode8_positivity_dp008",
        "case_name": "C5o_Pos",
        "resolution": "finer",
        "dp": 0.008,
        "mode": 8,
        "limiter": 1,
        "blend": 1.0,
        "prevent_negative": 1,
    },
    {
        "label": "mode8_blend025_dp008",
        "case_name": "C5o_B025",
        "resolution": "finer",
        "dp": 0.008,
        "mode": 8,
        "limiter": 3,
        "blend": 0.25,
        "prevent_negative": 0,
    },
    {
        "label": "mode8_blend050_dp008",
        "case_name": "C5o_B050",
        "resolution": "finer",
        "dp": 0.008,
        "mode": 8,
        "limiter": 3,
        "blend": 0.50,
        "prevent_negative": 0,
    },
    {
        "label": "mode8_blend050_positivity_dp008",
        "case_name": "C5o_B050Pos",
        "resolution": "finer",
        "dp": 0.008,
        "mode": 8,
        "limiter": 3,
        "blend": 0.50,
        "prevent_negative": 1,
    },
]
CASE = CASES[0]

MODE8_RE = re.compile(
    r"CPU curved drained corrected Laplacian: TimeStep=(?P<time>[-+0-9.eE]+), targets=(?P<targets>\d+), "
    r"corrected=(?P<corrected>\d+), fallback=(?P<fallback>\d+), material_samples=(?P<material_samples>\d+), "
    r"boundary_samples=(?P<boundary_samples>\d+), average_material_samples=(?P<avg_material>[-+0-9.eE]+), "
    r"average_boundary_samples=(?P<avg_boundary>[-+0-9.eE]+), support_radius=(?P<support>[-+0-9.eE]+), "
    r"r_min_factor=(?P<r_min_factor>[-+0-9.eE]+), r_threshold=(?P<r_threshold>[-+0-9.eE]+), "
    r"boundary_weight=(?P<boundary_weight>[-+0-9.eE]+), condition_limit=(?P<condition_limit>[-+0-9.eE]+), "
    r"cond_min=(?P<cond_min>[-+0-9.eE]+), cond_mean=(?P<cond_mean>[-+0-9.eE]+), cond_max=(?P<cond_max>[-+0-9.eE]+), "
    r"mean_laplacian=(?P<mean_lap>[-+0-9.eE]+), max_abs_laplacian=(?P<max_abs_lap>[-+0-9.eE]+), "
    r"mean_abs_replaced_lap=(?P<mean_abs_replaced>[-+0-9.eE]+), max_abs_replaced_lap=(?P<max_abs_replaced>[-+0-9.eE]+)"
)


def fnum(value, default=math.nan):
    try:
        if value is None or value == "":
            return default
        if isinstance(value, str):
            value = value.strip().rstrip(".,")
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        for row in rows:
            wr.writerow({field: row.get(field, "") for field in fields})


def split_line(line: str) -> list[str]:
    sep = ";" if ";" in line else ","
    return [v.strip() for v in line.split(sep)]


def find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    lower = [h.lower().split()[0] if h.strip() else "" for h in headers]
    for cand in candidates:
        cl = cand.lower()
        for i, header in enumerate(lower):
            if header == cl or header.endswith("." + cl) or header.endswith("_" + cl):
                return i
    return None


def percentile(values: list[float] | np.ndarray, pct: float) -> float:
    data = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not data:
        return math.nan
    x = (len(data) - 1) * pct / 100.0
    lo = int(math.floor(x))
    hi = int(math.ceil(x))
    if lo == hi:
        return data[lo]
    return data[lo] * (hi - x) + data[hi] * (x - lo)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    mask = np.isfinite(a) & np.isfinite(b)
    if not np.any(mask):
        return math.nan
    return float(np.sqrt(np.mean((a[mask] - b[mask]) ** 2)))


def savefig(name: str) -> None:
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(FIG / f"{name}.{ext}", dpi=180)
    plt.close()


@dataclass
class CloudSpec:
    label: str
    dp: float
    material_count: int
    surface_count_r085: int
    max_radius: float
    surface_roughness_std: float
    mean_surface_radius_error: float
    max_surface_radius_abs_error: float
    selected_boundary_particle_count: float
    material_boundary_pair_count: float


def load_cloud_specs() -> list[CloudSpec]:
    geom = read_csv(C5I / "c5i_geometry_flux_error_metrics.csv")
    sphere = read_csv(C5H / "c5h_sphere_quality_metrics.csv")
    wanted = [
        ("mode4_normalized_dp010", "coarse_diffusion", "dp=0.010"),
        ("mode4_normalized_dp008", "finer_diffusion", "dp=0.008"),
        ("mode4_normalized_dp0065", "higher_diffusion", "dp=0.0065"),
    ]
    out: list[CloudSpec] = []
    for case, sphere_case, label in wanted:
        row = next(r for r in geom if r["case_label"] == case)
        srow = next(r for r in sphere if r["case"] == sphere_case)
        out.append(
            CloudSpec(
                label=label,
                dp=fnum(row["configured_dp"]),
                material_count=int(fnum(row["material_particle_count"])),
                surface_count_r085=int(fnum(srow["surface_count_r085"])),
                max_radius=fnum(srow["max_radius"]),
                surface_roughness_std=fnum(row["surface_roughness_std"]),
                mean_surface_radius_error=fnum(row["mean_surface_radius_error"]),
                max_surface_radius_abs_error=fnum(row["max_surface_radius_abs_error"]),
                selected_boundary_particle_count=fnum(row["selected_boundary_particle_count"]),
                material_boundary_pair_count=fnum(row["material_boundary_pair_count"]),
            )
        )
    return out


def lattice_points(dp: float, offset_factor: float) -> np.ndarray:
    xs = np.arange(-DOMAIN_HALF + offset_factor * dp, DOMAIN_HALF + 1.0e-12, dp)
    return np.array([(x, y, z) for x in xs for y in xs for z in xs], dtype=float)


def cloud_score(r: np.ndarray, spec: CloudSpec) -> float:
    surf = r > 0.85 * RADIUS
    if not np.any(surf):
        return 1.0e99
    return (
        abs(float(np.max(r)) - spec.max_radius)
        + abs(int(np.sum(surf)) - spec.surface_count_r085) / 1000.0
        + abs(float(np.std(r[surf] - RADIUS)) - spec.surface_roughness_std)
        + abs(float(np.mean(r[surf] - RADIUS)) - spec.mean_surface_radius_error)
        + abs(float(np.max(np.abs(r[surf] - RADIUS))) - spec.max_surface_radius_abs_error)
    )


def reconstruct_cloud(spec: CloudSpec) -> tuple[np.ndarray, float]:
    best_score = 1.0e99
    best_pts: np.ndarray | None = None
    best_offset = 0.0
    for off in np.linspace(-0.5, 0.5, 81):
        pts = lattice_points(spec.dp, float(off))
        r = np.linalg.norm(pts, axis=1)
        idx = np.argsort(r)[: spec.material_count]
        cand = pts[idx]
        score = cloud_score(np.linalg.norm(cand, axis=1), spec)
        if score < best_score:
            best_score = score
            best_pts = cand
            best_offset = float(off)
    if best_pts is None:
        raise RuntimeError(f"Could not reconstruct cloud for {spec.label}")
    return best_pts, best_offset


def wendland_fac(rr2: np.ndarray, h: float) -> np.ndarray:
    rad = np.sqrt(rr2)
    qq = rad / h
    wqq1 = 1.0 - 0.5 * qq
    bwen = -2.08891 / (h**4)
    return bwen * qq * (wqq1**3) / rad


def sph_laplacian_material(pts: np.ndarray, u: np.ndarray, dp: float) -> np.ndarray:
    h = HDP * dp
    kernel_size2 = (2.0 * h) ** 2
    vol = dp**3
    out = np.zeros(len(pts), dtype=float)
    for i in range(len(pts)):
        d = pts[i] - pts
        rr2 = np.einsum("ij,ij->i", d, d)
        mask = (rr2 <= kernel_size2) & (rr2 > 1.0e-20)
        if not np.any(mask):
            continue
        fac = wendland_fac(rr2[mask], h)
        dotrgrad = rr2[mask] * fac
        out[i] = np.sum(2.0 * vol * (u[i] - u[mask]) * dotrgrad / (rr2[mask] + 1.0e-18))
    return out


def field_values(name: str, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r = np.linalg.norm(pts, axis=1)
    safe_r = np.maximum(r, 1.0e-12)
    x = r / RADIUS
    if name == "constant":
        return np.ones_like(r), np.zeros_like(r), np.ones_like(r, dtype=bool)
    if name == "quadratic_r2":
        return r * r, np.full_like(r, 6.0), np.ones_like(r, dtype=bool)
    if name == "linear_gap":
        return RADIUS - r, -2.0 / safe_r, r >= 0.10 * RADIUS
    if name == "smooth_quartic":
        return (1.0 - x * x) ** 2, -12.0 / (RADIUS**2) + 20.0 * (r * r) / (RADIUS**4), np.ones_like(r, dtype=bool)
    raise ValueError(name)


def fibonacci_sphere(n: int) -> np.ndarray:
    out = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        rr = math.sqrt(max(0.0, 1.0 - z * z))
        th = golden * i
        out.append((RADIUS * rr * math.cos(th), RADIUS * rr * math.sin(th), RADIUS * z))
    return np.array(out, dtype=float)


def corrected_mls_laplacian(pts: np.ndarray, field: str, dp: float, boundary_value_mode: str) -> tuple[np.ndarray, list[dict[str, float]]]:
    u, _, _ = field_values(field, pts)
    h = HDP * dp
    support = 2.0 * h
    support2 = support * support
    r = np.linalg.norm(pts, axis=1)
    boundary = fibonacci_sphere(max(24, int(12 * math.pi * RADIUS * RADIUS / (dp * dp))))
    ub_exact, _, _ = field_values(field, boundary)
    ub_zero = np.zeros(len(boundary))
    ub = ub_exact if boundary_value_mode == "exact_boundary" else ub_zero
    lap = sph_laplacian_material(pts, u, dp)
    diag: list[dict[str, float]] = []
    for i in range(len(pts)):
        if r[i] < 0.70 * RADIUS:
            continue
        normal = pts[i] / max(r[i], 1.0e-12)
        near = np.linalg.norm(pts - pts[i], axis=1) <= support
        bdist = np.linalg.norm(boundary - pts[i], axis=1)
        bnear = bdist <= support
        rows = []
        rhs = []
        weights = []
        for p, ui in zip(pts[near], u[near]):
            d = (p - pts[i]) / support
            q = max(0.0, 1.0 - float(np.linalg.norm(d)))
            rows.append([1.0, d[0], d[1], d[2], d[0] ** 2, d[1] ** 2, d[2] ** 2, d[0] * d[1], d[0] * d[2], d[1] * d[2]])
            rhs.append(float(ui))
            weights.append(q**4)
        for p, ui, dist in zip(boundary[bnear], ub[bnear], bdist[bnear]):
            d = (p - pts[i]) / support
            q = max(0.0, 1.0 - float(dist) / support)
            rows.append([1.0, d[0], d[1], d[2], d[0] ** 2, d[1] ** 2, d[2] ** 2, d[0] * d[1], d[0] * d[2], d[1] * d[2]])
            rhs.append(float(ui))
            weights.append(q**4)
        if len(rows) < 12:
            diag.append({"fallback": 1.0, "cond": math.nan, "materials": int(np.sum(near)), "boundaries": int(np.sum(bnear))})
            continue
        a = np.asarray(rows, dtype=float)
        y = np.asarray(rhs, dtype=float)
        w = np.sqrt(np.asarray(weights, dtype=float))
        aw = a * w[:, None]
        yw = y * w
        try:
            cond = float(np.linalg.cond(aw.T @ aw))
            coef = np.linalg.lstsq(aw, yw, rcond=None)[0]
        except np.linalg.LinAlgError:
            diag.append({"fallback": 1.0, "cond": math.nan, "materials": int(np.sum(near)), "boundaries": int(np.sum(bnear))})
            continue
        if not np.isfinite(cond) or cond > 1.0e12:
            diag.append({"fallback": 1.0, "cond": cond, "materials": int(np.sum(near)), "boundaries": int(np.sum(bnear))})
            continue
        lap[i] = 2.0 * (coef[4] + coef[5] + coef[6]) / (support * support)
        diag.append({"fallback": 0.0, "cond": cond, "materials": int(np.sum(near)), "boundaries": int(np.sum(bnear)), "normal_r": float(np.dot(normal, pts[i]))})
    return lap, diag


def positivity_limited_laplacian(lap: np.ndarray, u: np.ndarray, dp: float, cfl: float = 0.9) -> np.ndarray:
    """Static analogue of the mode-8 positivity limiter.

    The production limiter caps only negative diffusion rates. The static gate
    uses the same pressure-only diffusivity and a local h^2/cv time scale, so it
    reports whether the limiter would damage manufactured consistency.
    """

    cv = 0.0067957866
    dt = 0.0004021701 * (dp / 0.008)
    cap = -cfl * np.maximum(u, 0.0) / max(dt * cv, 1.0e-18)
    return np.maximum(lap, cap)


def audit_manufactured() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    summary: list[dict[str, object]] = []
    shell_rows: list[dict[str, object]] = []
    sample_rows: list[dict[str, object]] = []
    diag_rows: list[dict[str, object]] = []
    fields = ["constant", "quadratic_r2", "linear_gap", "smooth_quartic"]
    operators = [
        "material_only",
        "mode8_exact_boundary",
        "mode8_positivity",
        "mode8_blend025",
        "mode8_blend050",
        "mode8_drained_zero_boundary",
    ]
    for spec in load_cloud_specs():
        pts, offset = reconstruct_cloud(spec)
        r = np.linalg.norm(pts, axis=1)
        for field in fields:
            u, exact, valid = field_values(field, pts)
            results = {"material_only": sph_laplacian_material(pts, u, spec.dp)}
            lap_exact, diag_exact = corrected_mls_laplacian(pts, field, spec.dp, "exact_boundary")
            lap_zero, diag_zero = corrected_mls_laplacian(pts, field, spec.dp, "zero_boundary")
            results["mode8_exact_boundary"] = lap_exact
            results["mode8_positivity"] = positivity_limited_laplacian(lap_exact, u, spec.dp)
            results["mode8_blend025"] = 0.25 * lap_exact + 0.75 * results["material_only"]
            results["mode8_blend050"] = 0.50 * lap_exact + 0.50 * results["material_only"]
            results["mode8_drained_zero_boundary"] = lap_zero
            for label, diag in (("mode8_exact_boundary", diag_exact), ("mode8_drained_zero_boundary", diag_zero)):
                fallbacks = sum(int(d.get("fallback", 0)) for d in diag)
                conds = [d["cond"] for d in diag if math.isfinite(d.get("cond", math.nan))]
                diag_rows.append(
                    {
                        "dp_label": spec.label,
                        "dp": spec.dp,
                        "field": field,
                        "operator": label,
                        "targets": len(diag),
                        "fallback_count": fallbacks,
                        "fallback_fraction": fallbacks / len(diag) if diag else math.nan,
                        "condition_median": percentile(conds, 50) if conds else math.nan,
                        "condition_p95": percentile(conds, 95) if conds else math.nan,
                        "reconstruction_offset_factor": offset,
                    }
                )
            for op in operators:
                err = results[op] - exact
                for lo, hi in AUDIT_BINS:
                    mask = (r / RADIUS >= lo) & (r / RADIUS < hi) & valid
                    if hi == AUDIT_BINS[-1][1]:
                        mask = (r / RADIUS >= lo) & (r / RADIUS <= hi) & valid
                    vals = err[mask]
                    shell_rows.append(
                        {
                            "dp_label": spec.label,
                            "dp": spec.dp,
                            "field": field,
                            "operator": op,
                            "r_over_R_min": lo,
                            "r_over_R_max": hi,
                            "count": int(np.sum(mask)),
                            "bias": float(np.mean(vals)) if vals.size else math.nan,
                            "rmse": float(np.sqrt(np.mean(vals * vals))) if vals.size else math.nan,
                            "p95_abs_error": percentile(np.abs(vals), 95) if vals.size else math.nan,
                        }
                    )
                zones = {
                    "interior": (r / RADIUS < 0.6) & valid,
                    "middle": (r / RADIUS >= 0.6) & (r / RADIUS < 0.85) & valid,
                    "near_boundary": (r / RADIUS >= 0.85) & (r / RADIUS <= 1.12) & valid,
                    "all_valid": valid,
                }
                for zone, mask in zones.items():
                    vals = err[mask]
                    summary.append(
                        {
                            "dp_label": spec.label,
                            "dp": spec.dp,
                            "field": field,
                            "operator": op,
                            "zone": zone,
                            "count": int(np.sum(mask)),
                            "bias": float(np.mean(vals)) if vals.size else math.nan,
                            "rmse": float(np.sqrt(np.mean(vals * vals))) if vals.size else math.nan,
                            "p95_abs_error": percentile(np.abs(vals), 95) if vals.size else math.nan,
                            "max_abs_error": float(np.max(np.abs(vals))) if vals.size else math.nan,
                        }
                    )
            # Keep a compact particle sample for review.
            sample_idx = np.linspace(0, len(pts) - 1, min(300, len(pts)), dtype=int)
            for idx in sample_idx:
                sample_rows.append(
                    {
                        "dp_label": spec.label,
                        "dp": spec.dp,
                        "field": field,
                        "r_over_R": r[idx] / RADIUS,
                        "exact_laplacian": exact[idx],
                        "material_laplacian": results["material_only"][idx],
                        "mode8_exact_boundary_laplacian": results["mode8_exact_boundary"][idx],
                        "mode8_zero_boundary_laplacian": results["mode8_drained_zero_boundary"][idx],
                    }
                )
    write_csv(ROOT / "c5o_manufactured_limiter_metrics.csv", summary)
    write_csv(ROOT / "c5o_manufactured_laplacian_by_shell.csv", shell_rows)
    write_csv(ROOT / "c5o_manufactured_laplacian_particles_sample.csv", sample_rows)
    write_csv(ROOT / "c5o_corrected_laplacian_static_diagnostics.csv", diag_rows)
    return summary, shell_rows, sample_rows, diag_rows


def plot_manufactured(shell_rows: list[dict[str, object]], diag_rows: list[dict[str, object]]) -> None:
    for field, title, name in [
        ("constant", "constant field residual", "c5o_constant_laplacian_residual"),
        ("quadratic_r2", "quadratic field error", "c5o_quadratic_laplacian_error"),
        ("linear_gap", "drained-like gap error", "c5o_linear_gap_laplacian_error"),
    ]:
        plt.figure(figsize=(7, 4))
        for op in ["material_only", "mode8_exact_boundary", "mode8_positivity", "mode8_blend025", "mode8_blend050"]:
            rows = [r for r in shell_rows if r["dp_label"] == "dp=0.008" and r["field"] == field and r["operator"] == op]
            x = [0.5 * (float(r["r_over_R_min"]) + float(r["r_over_R_max"])) for r in rows]
            y = [float(r["p95_abs_error"]) for r in rows]
            plt.plot(x, y, marker="o", label=op)
        plt.xlabel("r/R")
        plt.ylabel("p95 |Laplacian error|")
        plt.title(title)
        plt.legend()
        savefig(name)
    plt.figure(figsize=(7, 4))
    rows = [r for r in diag_rows if r["dp_label"] == "dp=0.008" and r["operator"] == "mode8_exact_boundary"]
    plt.bar([r["field"] for r in rows], [float(r["condition_p95"]) for r in rows])
    plt.yscale("log")
    plt.ylabel("p95 condition estimate")
    plt.title("mode 8 MLS condition estimate")
    savefig("c5o_condition_number_stats")


def parse_runout() -> tuple[dict[str, object], list[dict[str, object]], dict[int, float]]:
    runout = ROOT / f"{CASE['case_name']}_cpu_out" / "Run.out"
    meta: dict[str, object] = {"case": CASE["label"], "code": "missing", "excluded": "missing", "runout_exists": runout.exists()}
    rows: list[dict[str, object]] = []
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return meta, rows, times
    text = runout.read_text(errors="ignore")
    meta["code"] = 0 if "Finished execution" in text else "unknown"
    m = re.search(r"Excluded particles\.*:\s*(\d+)", text)
    if m:
        meta["excluded"] = int(m.group(1))
    m = re.search(r"Steps of simulation\.*:\s*(\d+)", text)
    if m:
        meta["steps"] = int(m.group(1))
    m = re.search(r"Total Runtime\.*:\s*([-+0-9.eE]+)", text)
    if m:
        meta["runtime_s"] = float(m.group(1))
    for m in re.finditer(r"Part_(?P<idx>\d{4})\s+(?P<time>[-+0-9.eE]*\.[-+0-9.eE]+)\s+\d+", text):
        times[int(m.group("idx"))] = float(m.group("time"))
    for line in text.splitlines():
        m = MODE8_RE.search(line)
        if not m:
            continue
        row = {"case": CASE["label"]}
        for key, value in m.groupdict().items():
            row[key] = fnum(value)
        for key in (
            "limiter",
            "prevent_negative",
            "limiter_dt",
            "limiter_cfl",
            "blend",
            "limiter_targets",
            "blend_limited",
            "positivity_limited",
            "theta_mean",
            "theta_min",
            "theta_max",
            "mean_abs_limiter_delta",
            "max_abs_limiter_delta",
            "max_abs_diffusion_rate",
        ):
            km = re.search(rf"{key}=([-+0-9.eE]+)", line)
            if km:
                row[key] = fnum(km.group(1))
        rows.append(row)
    return meta, rows, times


def read_partcsv(times: dict[int, float]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    data_dir = ROOT / f"{CASE['case_name']}_cpu_out" / "data"
    frames: list[dict[str, object]] = []
    radials: list[dict[str, object]] = []
    surfaces: list[dict[str, object]] = []
    for iframe, path in enumerate(sorted(data_dir.glob("PartCsv_*.csv"))):
        lines = path.read_text(errors="ignore").splitlines()
        header_idx = next((i for i, line in enumerate(lines) if "PorePress" in line or "Pos" in line), None)
        if header_idx is None:
            continue
        headers = split_line(lines[header_idx])
        cols = {
            "x": find_col(headers, ("Pos.x", "posx", "x")),
            "y": find_col(headers, ("Pos.y", "posy", "y")),
            "z": find_col(headers, ("Pos.z", "posz", "z")),
            "type": find_col(headers, ("Type",)),
            "ex": find_col(headers, ("ExcessPorePress", "PorePress")),
            "rate": find_col(headers, ("PorePressRate",)),
            "kp": find_col(headers, ("Kplastic",)),
        }
        particles = []
        for line in lines[header_idx + 1 :]:
            if not line.strip() or line.startswith("#"):
                continue
            vals = split_line(line)
            if cols["x"] is None or cols["y"] is None or cols["z"] is None:
                continue
            if cols["type"] is not None and int(fnum(vals[cols["type"]], -1)) != 3:
                continue
            x = fnum(vals[cols["x"]])
            y = fnum(vals[cols["y"]])
            z = fnum(vals[cols["z"]])
            particles.append(
                {
                    "r": math.sqrt(x * x + y * y + z * z),
                    "ex": fnum(vals[cols["ex"]]) if cols["ex"] is not None else math.nan,
                    "rate": fnum(vals[cols["rate"]]) if cols["rate"] is not None else math.nan,
                    "kp": fnum(vals[cols["kp"]]) if cols["kp"] is not None else 0.0,
                }
            )
        time = times.get(iframe, float(iframe))
        ex = [p["ex"] for p in particles if math.isfinite(p["ex"])]
        nearest = min(particles, key=lambda p: p["r"], default={"r": math.nan, "ex": math.nan})
        shell = [p["ex"] for p in particles if 0.95 * RADIUS <= p["r"] <= 1.10 * RADIUS]
        p95 = percentile([abs(v) for v in shell], 95)
        frames.append(
            {
                "case": CASE["label"],
                "case_name": CASE["case_name"],
                "resolution": CASE["resolution"],
                "configured_dp": CASE["dp"],
                "mode": CASE["mode"],
                "time": time,
                "frame_index": iframe,
                "particle_count": len(particles),
                "center_pressure": nearest["ex"],
                "center_nearest_radius": nearest["r"],
                "volume_mean_pressure": sum(ex) / len(ex) if ex else math.nan,
                "surface_shell_mean": sum(shell) / len(shell) if shell else math.nan,
                "surface_shell_p95_abs": p95,
                "porepressrate_maxAbs": max((abs(p["rate"]) for p in particles), default=math.nan),
                "min_pressure": min(ex) if ex else math.nan,
                "negative_pressure_count": sum(1 for p in particles if math.isfinite(p["ex"]) and p["ex"] < 0.0),
                "kplastic_maxAbs": max((abs(p["kp"]) for p in particles), default=0.0),
            }
        )
        for lo, hi in RADIAL_BINS:
            vals = [p["ex"] for p in particles if lo <= p["r"] / RADIUS < hi or (hi == 1.0 and lo <= p["r"] / RADIUS <= hi)]
            radials.append(
                {
                    "case": CASE["label"],
                    "time": time,
                    "frame_index": iframe,
                    "r_over_R_min": lo,
                    "r_over_R_max": hi,
                    "r_over_R_mid": 0.5 * (lo + hi),
                    "count": len(vals),
                    "sph_mean_pressure": sum(vals) / len(vals) if vals else math.nan,
                    "sph_p95_abs_pressure": percentile([abs(v) for v in vals], 95) if vals else math.nan,
                }
            )
        surfaces.append(
            {
                "case": CASE["label"],
                "time": time,
                "frame_index": iframe,
                "sph_count": len(shell),
                "sph_mean_pressure": sum(shell) / len(shell) if shell else math.nan,
                "sph_p95_abs_pressure": p95,
            }
        )
    return frames, radials, surfaces


def interpolate_ref(times: np.ndarray, key: str) -> np.ndarray:
    ref = read_csv(C5I / "c5i_fv_reference_timeseries.csv")
    xs = np.asarray([fnum(r["time"]) for r in ref], dtype=float)
    ys = np.asarray([fnum(r[key]) for r in ref], dtype=float)
    order = np.argsort(xs)
    return np.interp(times, xs[order], ys[order])


def analyze_pressure(meta: dict[str, object], diag_rows: list[dict[str, object]], times: dict[int, float]) -> None:
    frames, radials, surfaces = read_partcsv(times)
    if not frames:
        cached_frames = read_csv(ROOT / "c5n_pressure_only_comparison.csv")
        cached_gate = read_csv(ROOT / "c5n_gate_metrics.csv")
        cached_radials = read_csv(ROOT / "c5n_radial_bin_profiles.csv")
        if cached_frames and cached_gate:
            plot_pressure(cached_frames, cached_gate, cached_radials)
        return
    t = np.asarray([fnum(r["time"]) for r in frames], dtype=float)
    center = np.asarray([fnum(r["center_pressure"]) for r in frames], dtype=float)
    volume = np.asarray([fnum(r["volume_mean_pressure"]) for r in frames], dtype=float)
    shell = np.asarray([fnum(r["surface_shell_mean"]) for r in frames], dtype=float)
    fv_center = interpolate_ref(t, "center_pressure")
    fv_volume = interpolate_ref(t, "volume_mean_pressure")
    fv_shell = interpolate_ref(t, "surface_shell_mean_095_100")
    fv_flux = interpolate_ref(t, "boundary_flux_integral")
    stored = volume * (4.0 * math.pi * RADIUS**3 / 3.0)
    apparent_flux = -np.gradient(stored, t, edge_order=1)
    flux_ratio = np.divide(apparent_flux, fv_flux, out=np.full_like(apparent_flux, np.nan), where=np.abs(fv_flux) > 1.0e-12)
    for i, row in enumerate(frames):
        row.update(
            {
                "fv_center_pressure": fv_center[i],
                "fv_volume_mean_pressure": fv_volume[i],
                "fv_surface_shell_mean": fv_shell[i],
                "apparent_flux_integral": apparent_flux[i],
                "fv_boundary_flux_integral": fv_flux[i],
                "flux_ratio": flux_ratio[i],
            }
        )
    write_csv(ROOT / "c5n_pressure_only_comparison.csv", frames)
    write_csv(ROOT / "c5n_radial_bin_profiles.csv", radials)
    write_csv(ROOT / "c5n_surface_shell_metrics.csv", surfaces)
    final = frames[-1]
    gate = {
        "case": CASE["label"],
        "case_name": CASE["case_name"],
        "resolution": CASE["resolution"],
        "configured_dp": CASE["dp"],
        "frames": len(frames),
        "final_time": final["time"],
        "code": meta.get("code"),
        "excluded": meta.get("excluded"),
        "final_center_pressure": final["center_pressure"],
        "fv_final_center_pressure": final["fv_center_pressure"],
        "final_volume_mean_pressure": final["volume_mean_pressure"],
        "fv_final_volume_mean_pressure": final["fv_volume_mean_pressure"],
        "final_surface_shell_mean": final["surface_shell_mean"],
        "fv_final_surface_shell_mean": final["fv_surface_shell_mean"],
        "final_surface_shell_p95_abs": final["surface_shell_p95_abs"],
        "center_pressure_rmse": rmse(center, fv_center),
        "volume_mean_pressure_rmse": rmse(volume, fv_volume),
        "surface_shell_pressure_rmse": rmse(shell, fv_shell),
        "median_flux_ratio": percentile(flux_ratio[np.isfinite(flux_ratio)], 50),
        "final_flux_ratio": flux_ratio[-1],
        "flux_reversal": bool(np.any(flux_ratio[1:] < 0.0)),
        "negative_pressure": bool(any(fnum(r["negative_pressure_count"]) > 0 for r in frames)),
        "final_porepressrate_maxAbs": final["porepressrate_maxAbs"],
        "final_kplastic_maxAbs": final["kplastic_maxAbs"],
        "runtime_diag_final_corrected": diag_rows[-1]["corrected"] if diag_rows else math.nan,
        "runtime_diag_final_fallback": diag_rows[-1]["fallback"] if diag_rows else math.nan,
        "runtime_diag_final_cond_mean": diag_rows[-1]["cond_mean"] if diag_rows else math.nan,
    }
    previous = []
    c5i_summary = read_csv(C5I / "c5i_sph_pressure_only_summary.csv")
    for r in c5i_summary:
        if r.get("case_label") == "mode4_normalized_dp008":
            previous.append(
                {
                    "case": "mode4_normalized_dp008",
                    "mode": 4,
                    "center_pressure_rmse": fnum(r["center_pressure_rmse"]),
                    "volume_mean_pressure_rmse": fnum(r["volume_mean_pressure_rmse"]),
                    "surface_shell_pressure_rmse": fnum(r["surface_shell_pressure_rmse"]),
                    "median_flux_ratio": fnum(r["median_flux_ratio"]),
                    "final_flux_ratio": fnum(r["final_flux_ratio"]),
                    "final_porepressrate_maxAbs": fnum(r["final_porepressrate_maxAbs"]),
                }
            )
    for source, case_name in [(C5J / "c5j_gate_metrics.csv", "mode5_mls_dp008"), (C5K / "c5k_gate_metrics.csv", "mode6_shell_dp008"), (C5M / "c5m_gate_metrics.csv", "mode7_shell_exchange_dp008")]:
        for r in read_csv(source):
            if r.get("case") == case_name:
                previous.append(
                    {
                        "case": case_name,
                        "mode": fnum(case_name.split("_")[0].replace("mode", "")),
                        "center_pressure_rmse": fnum(r["center_pressure_rmse"]),
                        "volume_mean_pressure_rmse": fnum(r["volume_mean_pressure_rmse"]),
                        "surface_shell_pressure_rmse": fnum(r["surface_shell_pressure_rmse"]),
                        "median_flux_ratio": fnum(r["median_flux_ratio"]),
                        "final_flux_ratio": fnum(r["final_flux_ratio"]),
                        "final_porepressrate_maxAbs": fnum(r["final_porepressrate_maxAbs"]),
                    }
                )
    previous.append(gate)
    write_csv(ROOT / "c5n_gate_metrics.csv", previous)
    write_csv(ROOT / "c5n_case_summary.csv", [gate])
    plot_pressure(frames, previous, radials)


def read_existing_comparison(path: Path, case: str) -> list[dict[str, str]]:
    return [r for r in read_csv(path) if r.get("case") == case]


def plot_pressure(frames: list[dict[str, object]], gate_rows: list[dict[str, object]], radials: list[dict[str, object]]) -> None:
    t = [fnum(r["time"]) for r in frames]
    ref = read_csv(C5I / "c5i_fv_reference_timeseries.csv")
    tr = [fnum(r["time"]) for r in ref]
    plt.figure(figsize=(7, 4))
    plt.plot(tr, [fnum(r["center_pressure"]) for r in ref], "k-", label="FV")
    for path, case, label in [
        (C5I / "c5i_volume_mean_decay.csv", "mode4_normalized_dp008", "mode4"),
        (C5J / "c5j_pressure_only_comparison.csv", "mode5_mls_dp008", "mode5"),
        (C5K / "c5k_pressure_only_comparison.csv", "mode6_shell_dp008", "mode6"),
        (C5M / "c5m_pressure_only_comparison.csv", "mode7_shell_exchange_dp008", "mode7"),
    ]:
        rows = read_existing_comparison(path, case)
        if rows and "center_pressure" in rows[0]:
            plt.plot([fnum(r["time"]) for r in rows], [fnum(r["center_pressure"]) for r in rows], "--", label=label)
    plt.plot(t, [fnum(r["center_pressure"]) for r in frames], "o-", label="mode8")
    plt.xlabel("time [s]")
    plt.ylabel("center pressure [Pa]")
    plt.legend()
    savefig("c5n_center_pressure_vs_fv")

    for key, fvkey, ylabel, name in [
        ("volume_mean_pressure", "volume_mean_pressure", "volume mean pressure [Pa]", "c5n_volume_mean_vs_fv"),
        ("surface_shell_mean", "surface_shell_mean_095_100", "surface shell mean [Pa]", "c5n_surface_shell_vs_fv"),
        ("porepressrate_maxAbs", None, "|PorePressRate| max [Pa/s]", "c5n_porepressrate_maxabs"),
        ("flux_ratio", None, "flux ratio", "c5n_flux_ratio_vs_time"),
        ("negative_pressure_count", None, "negative pressure count", "c5n_negative_pressure_indicator"),
    ]:
        plt.figure(figsize=(7, 4))
        if fvkey:
            plt.plot(tr, [fnum(r[fvkey]) for r in ref], "k-", label="FV")
        plt.plot(t, [fnum(r[key]) for r in frames], "o-", label="mode8")
        if key == "flux_ratio":
            plt.axhline(1.0, color="k", lw=1)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.legend()
        savefig(name)

    plt.figure(figsize=(7, 4))
    labels = [str(r["case"]).replace("_dp008", "").replace("mode", "m") for r in gate_rows]
    x = np.arange(len(labels))
    plt.bar(x - 0.25, [fnum(r["center_pressure_rmse"]) for r in gate_rows], width=0.25, label="center")
    plt.bar(x, [fnum(r["volume_mean_pressure_rmse"]) for r in gate_rows], width=0.25, label="volume")
    plt.bar(x + 0.25, [fnum(r["surface_shell_pressure_rmse"]) for r in gate_rows], width=0.25, label="surface")
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.ylabel("RMSE [Pa]")
    plt.legend()
    savefig("c5n_error_metrics_by_mode")

    if radials:
        final_time = max(fnum(r["time"]) for r in radials)
        final_rows = [r for r in radials if abs(fnum(r["time"]) - final_time) < 1.0e-12]
        profiles = read_csv(C5I / "c5i_fv_reference_profiles.csv")
        ref_times = sorted({fnum(r["time"]) for r in profiles})
        ref_time = min(ref_times, key=lambda v: abs(v - final_time))
        ref_rows = [r for r in profiles if abs(fnum(r["time"]) - ref_time) < 1.0e-12]
        plt.figure(figsize=(7, 4))
        plt.plot([fnum(r["r_over_R"]) for r in ref_rows], [fnum(r["pressure"]) for r in ref_rows], "k-", label="FV")
        plt.plot([fnum(r["r_over_R_mid"]) for r in final_rows], [fnum(r["sph_mean_pressure"]) for r in final_rows], "o-", label="mode8 bins")
        plt.xlabel("r/R")
        plt.ylabel("pressure [Pa]")
        plt.title(f"final radial profile, t={final_time:.6g} s")
        plt.legend()
        savefig("c5n_radial_pressure_profiles")


def pressure_case_metrics(meta: dict[str, object], diag_rows: list[dict[str, object]], times: dict[int, float]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    frames, radials, surfaces = read_partcsv(times)
    if not frames:
        gate = {
            "case": CASE["label"],
            "case_name": CASE["case_name"],
            "resolution": CASE["resolution"],
            "configured_dp": CASE["dp"],
            "code": meta.get("code"),
            "excluded": meta.get("excluded"),
            "status": "missing_frames",
        }
        return frames, radials, surfaces, gate
    t = np.asarray([fnum(r["time"]) for r in frames], dtype=float)
    center = np.asarray([fnum(r["center_pressure"]) for r in frames], dtype=float)
    volume = np.asarray([fnum(r["volume_mean_pressure"]) for r in frames], dtype=float)
    shell = np.asarray([fnum(r["surface_shell_mean"]) for r in frames], dtype=float)
    fv_center = interpolate_ref(t, "center_pressure")
    fv_volume = interpolate_ref(t, "volume_mean_pressure")
    fv_shell = interpolate_ref(t, "surface_shell_mean_095_100")
    fv_flux = interpolate_ref(t, "boundary_flux_integral")
    stored = volume * (4.0 * math.pi * RADIUS**3 / 3.0)
    apparent_flux = -np.gradient(stored, t, edge_order=1)
    flux_ratio = np.divide(apparent_flux, fv_flux, out=np.full_like(apparent_flux, np.nan), where=np.abs(fv_flux) > 1.0e-12)
    for i, row in enumerate(frames):
        row.update(
            {
                "fv_center_pressure": fv_center[i],
                "fv_volume_mean_pressure": fv_volume[i],
                "fv_surface_shell_mean": fv_shell[i],
                "apparent_flux_integral": apparent_flux[i],
                "fv_boundary_flux_integral": fv_flux[i],
                "flux_ratio": flux_ratio[i],
            }
        )
    final = frames[-1]
    diag_final = diag_rows[-1] if diag_rows else {}
    gate = {
        "case": CASE["label"],
        "case_name": CASE["case_name"],
        "resolution": CASE["resolution"],
        "configured_dp": CASE["dp"],
        "limiter": CASE["limiter"],
        "blend": CASE["blend"],
        "prevent_negative": CASE["prevent_negative"],
        "frames": len(frames),
        "final_time": final["time"],
        "code": meta.get("code"),
        "excluded": meta.get("excluded"),
        "steps": meta.get("steps", math.nan),
        "runtime_s": meta.get("runtime_s", math.nan),
        "final_center_pressure": final["center_pressure"],
        "fv_final_center_pressure": final["fv_center_pressure"],
        "final_volume_mean_pressure": final["volume_mean_pressure"],
        "fv_final_volume_mean_pressure": final["fv_volume_mean_pressure"],
        "final_surface_shell_mean": final["surface_shell_mean"],
        "fv_final_surface_shell_mean": final["fv_surface_shell_mean"],
        "final_surface_shell_p95_abs": final["surface_shell_p95_abs"],
        "center_pressure_rmse": rmse(center, fv_center),
        "volume_mean_pressure_rmse": rmse(volume, fv_volume),
        "surface_shell_pressure_rmse": rmse(shell, fv_shell),
        "median_flux_ratio": percentile(flux_ratio[np.isfinite(flux_ratio)], 50),
        "final_flux_ratio": flux_ratio[-1],
        "flux_reversal": bool(np.any(flux_ratio[1:] < 0.0)),
        "negative_pressure": bool(any(fnum(r["negative_pressure_count"]) > 0 for r in frames)),
        "max_negative_pressure_count": max((fnum(r["negative_pressure_count"], 0) for r in frames), default=0),
        "minimum_pressure_over_time": min((fnum(r["min_pressure"]) for r in frames), default=math.nan),
        "final_min_pressure": final["min_pressure"],
        "final_negative_pressure_count": final["negative_pressure_count"],
        "final_porepressrate_maxAbs": final["porepressrate_maxAbs"],
        "final_kplastic_maxAbs": final["kplastic_maxAbs"],
        "runtime_diag_final_corrected": diag_final.get("corrected", math.nan),
        "runtime_diag_final_fallback": diag_final.get("fallback", math.nan),
        "runtime_diag_final_cond_mean": diag_final.get("cond_mean", math.nan),
        "runtime_diag_final_limiter_targets": diag_final.get("limiter_targets", math.nan),
        "runtime_diag_final_blend_limited": diag_final.get("blend_limited", math.nan),
        "runtime_diag_final_positivity_limited": diag_final.get("positivity_limited", math.nan),
        "runtime_diag_final_theta_mean": diag_final.get("theta_mean", math.nan),
        "runtime_diag_final_limiter_delta_mean": diag_final.get("mean_abs_limiter_delta", math.nan),
        "runtime_diag_final_max_abs_diffusion_rate": diag_final.get("max_abs_diffusion_rate", math.nan),
        "runtime_diag_max_blend_limited": max((fnum(r.get("blend_limited", 0), 0) for r in diag_rows), default=0),
        "runtime_diag_max_positivity_limited": max((fnum(r.get("positivity_limited", 0), 0) for r in diag_rows), default=0),
        "runtime_diag_max_limiter_delta": max((fnum(r.get("max_abs_limiter_delta", 0), 0) for r in diag_rows), default=0),
        "status": "ok",
    }
    return frames, radials, surfaces, gate


def load_baseline_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    gates: list[dict[str, object]] = []
    frames: list[dict[str, object]] = []
    for r in read_csv(C5N / "c5n_pressure_only_comparison.csv"):
        row = dict(r)
        row["case"] = "mode8_limiter_off_dp008"
        frames.append(row)
    for r in read_csv(C5N / "c5n_gate_metrics.csv"):
        if r.get("case") == "mode8_corrected_laplacian_dp008":
            row = dict(r)
            row["case"] = "mode8_limiter_off_dp008"
            row["limiter"] = 0
            row["blend"] = 1.0
            row["prevent_negative"] = 0
            gates.append(row)
    c5i_summary = read_csv(C5I / "c5i_sph_pressure_only_summary.csv")
    for r in c5i_summary:
        if r.get("case_label") == "mode4_normalized_dp008":
            gates.append(
                {
                    "case": "mode4_normalized_dp008",
                    "limiter": "",
                    "blend": "",
                    "prevent_negative": "",
                    "center_pressure_rmse": fnum(r["center_pressure_rmse"]),
                    "volume_mean_pressure_rmse": fnum(r["volume_mean_pressure_rmse"]),
                    "surface_shell_pressure_rmse": fnum(r["surface_shell_pressure_rmse"]),
                    "median_flux_ratio": fnum(r["median_flux_ratio"]),
                    "final_flux_ratio": fnum(r["final_flux_ratio"]),
                    "final_porepressrate_maxAbs": fnum(r["final_porepressrate_maxAbs"]),
                }
            )
    for source, case_name in [
        (C5J / "c5j_gate_metrics.csv", "mode5_mls_dp008"),
        (C5K / "c5k_gate_metrics.csv", "mode6_shell_dp008"),
        (C5M / "c5m_gate_metrics.csv", "mode7_shell_exchange_dp008"),
    ]:
        for r in read_csv(source):
            if r.get("case") == case_name:
                row = dict(r)
                row["limiter"] = ""
                row["blend"] = ""
                row["prevent_negative"] = ""
                gates.append(row)
    return gates, frames


def plot_c5o_pressure(frames: list[dict[str, object]], gates: list[dict[str, object]]) -> None:
    ref = read_csv(C5I / "c5i_fv_reference_timeseries.csv")
    tr = [fnum(r["time"]) for r in ref]
    cases = ["mode8_limiter_off_dp008"] + [c["label"] for c in CASES]
    labels = {
        "mode8_limiter_off_dp008": "off",
        "mode8_positivity_dp008": "positivity",
        "mode8_blend025_dp008": "blend 0.25",
        "mode8_blend050_dp008": "blend 0.50",
        "mode8_blend050_positivity_dp008": "blend 0.50 + pos",
    }
    for key, fvkey, ylabel, name in [
        ("center_pressure", "center_pressure", "center pressure [Pa]", "c5o_center_pressure_vs_fv"),
        ("volume_mean_pressure", "volume_mean_pressure", "volume mean pressure [Pa]", "c5o_volume_mean_vs_fv"),
        ("surface_shell_mean", "surface_shell_mean_095_100", "surface shell mean [Pa]", "c5o_surface_shell_vs_fv"),
        ("porepressrate_maxAbs", None, "|PorePressRate| max [Pa/s]", "c5o_porepressrate_maxabs"),
        ("negative_pressure_count", None, "negative pressure count", "c5o_negative_pressure_indicator"),
        ("flux_ratio", None, "flux ratio", "c5o_flux_ratio_vs_time"),
    ]:
        plt.figure(figsize=(7, 4))
        if fvkey:
            plt.plot(tr, [fnum(r[fvkey]) for r in ref], "k-", label="FV")
        for case in cases:
            rows = [r for r in frames if r.get("case") == case and key in r]
            if not rows:
                continue
            rows.sort(key=lambda r: fnum(r["time"]))
            plt.plot([fnum(r["time"]) for r in rows], [fnum(r[key]) for r in rows], marker="o", label=labels.get(case, case))
        if key == "flux_ratio":
            plt.axhline(1.0, color="k", lw=1)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.legend()
        savefig(name)

    gate_cases = [g for g in gates if str(g.get("case", "")).startswith("mode8_")]
    plt.figure(figsize=(8, 4))
    x = np.arange(len(gate_cases))
    plt.bar(x - 0.25, [fnum(r.get("center_pressure_rmse", math.nan)) for r in gate_cases], width=0.25, label="center")
    plt.bar(x, [fnum(r.get("volume_mean_pressure_rmse", math.nan)) for r in gate_cases], width=0.25, label="volume")
    plt.bar(x + 0.25, [fnum(r.get("surface_shell_pressure_rmse", math.nan)) for r in gate_cases], width=0.25, label="surface")
    plt.xticks(x, [labels.get(str(r["case"]), str(r["case"])) for r in gate_cases], rotation=25, ha="right")
    plt.ylabel("RMSE [Pa]")
    plt.legend()
    savefig("c5o_limiter_error_metrics")

    plt.figure(figsize=(7, 4))
    for metric, marker in [("runtime_diag_final_blend_limited", "o"), ("runtime_diag_final_positivity_limited", "s")]:
        vals = [fnum(g.get(metric, math.nan)) for g in gate_cases]
        plt.plot(x, vals, marker=marker, label=metric.replace("runtime_diag_final_", ""))
    plt.xticks(x, [labels.get(str(r["case"]), str(r["case"])) for r in gate_cases], rotation=25, ha="right")
    plt.ylabel("final activation count")
    plt.legend()
    savefig("c5o_limiter_activation_stats")


def write_boundary_type_note() -> None:
    text = """# C5o Corrected Laplacian Stabilization Note

Mode 8 remains a boundary-aware quadratic MLS Laplacian. C5o adds optional
limiters that act only on the recovered Laplacian before it is assigned to
`LapPorePress`.

- `CurvedDrainedCorrectedLaplacianLimiter=1` caps negative diffusion rates so
  the pressure-only update cannot drain more than a CFL-scaled local pressure
  gap in one pore-pressure time scale.
- `CurvedDrainedCorrectedLaplacianLimiter=3` blends the MLS Laplacian with the
  pre-existing material SPH Laplacian using `CurvedDrainedLimiterBlend`.
- `CurvedDrainedLimiterPreventNegative=1` can apply the positivity cap after a
  blend limiter.

No limiter clamps material pore pressure and no limiter counts dummy boundary
volume. `c5o_case_summary.csv` and `c5o_pressure_only_limiter_metrics.csv`
classify the pressure-only gate.
"""
    (ROOT / "c5o_boundary_type_diagnosis.md").write_text(text, encoding="utf-8")


def main() -> None:
    global CASE
    _summary, shell_rows, _sample_rows, static_diag = audit_manufactured()
    plot_manufactured(shell_rows, static_diag)

    baseline_gates, baseline_frames = load_baseline_rows()
    all_gates = list(baseline_gates)
    all_frames = list(baseline_frames)
    all_radials: list[dict[str, object]] = []
    all_surfaces: list[dict[str, object]] = []
    all_diag: list[dict[str, object]] = []
    for case in CASES:
        CASE = case
        meta, diag, times = parse_runout()
        for row in diag:
            row.update({"limiter": case["limiter"], "blend": case["blend"], "prevent_negative": case["prevent_negative"]})
        frames, radials, surfaces, gate = pressure_case_metrics(meta, diag, times)
        all_frames.extend(frames)
        all_radials.extend(radials)
        all_surfaces.extend(surfaces)
        all_gates.append(gate)
        all_diag.extend(diag)

    write_csv(ROOT / "c5o_pressure_only_limiter_metrics.csv", all_frames)
    write_csv(ROOT / "c5o_radial_bin_profiles.csv", all_radials)
    write_csv(ROOT / "c5o_surface_shell_metrics.csv", all_surfaces)
    write_csv(ROOT / "c5o_case_summary.csv", all_gates)
    write_csv(ROOT / "c5o_limiter_activation_stats.csv", all_diag)
    write_csv(ROOT / "c5o_negative_pressure_metrics.csv", [{"case": r["case"], "time": r["time"], "negative_pressure_count": r.get("negative_pressure_count", ""), "min_pressure": r.get("min_pressure", "")} for r in all_frames if "negative_pressure_count" in r])
    write_csv(ROOT / "c5o_porepressrate_artifact_metrics.csv", [{"case": r["case"], "time": r["time"], "porepressrate_maxAbs": r.get("porepressrate_maxAbs", "")} for r in all_frames if "porepressrate_maxAbs" in r])
    write_csv(ROOT / "c5o_flux_ratio_metrics.csv", [{"case": r["case"], "time": r["time"], "flux_ratio": r.get("flux_ratio", ""), "apparent_flux_integral": r.get("apparent_flux_integral", ""), "fv_boundary_flux_integral": r.get("fv_boundary_flux_integral", "")} for r in all_frames if "flux_ratio" in r])
    plot_c5o_pressure(all_frames, all_gates)
    write_boundary_type_note()
    print("C5o analysis complete.")


if __name__ == "__main__":
    main()
