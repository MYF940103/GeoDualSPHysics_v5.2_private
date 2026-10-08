from pathlib import Path
import argparse
import csv
import math
import sys

import matplotlib.pyplot as plt


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
TEST_SUPPORT = Path(__file__).resolve().parent
for path in (ROOT_SUPPORT, TEST_SUPPORT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import postprocess_self_weight_consolidation as pp
from diagnose_scenario2_baseline_oscillations import (
    bottom_indices,
    bottom_mean,
    central_derivative,
    part_index,
    read_vtk_arrays,
)


DP = 0.01
H = 1.8 * DP
KERNEL_SIZE = 2.0 * H
KERNEL_SIZE2 = KERNEL_SIZE * KERNEL_SIZE
ETA2 = (0.1 * H) * (0.1 * H)
RHOP0 = 2100.0
MASS = RHOP0 * DP * DP
KW = 2.0e8
POROSITY = 0.3
KWN = KW / POROSITY
KHYD = 1.0e-3
RHOW = 1000.0
GHYD = 9.81
BWEN = -2.7852 / (H * H * H)
ALMOSTZERO = 1.0e-18


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def wendland_fac(rr2):
    rad = math.sqrt(rr2)
    qq = rad / H
    wqq1 = 1.0 - 0.5 * qq
    return BWEN * qq * wqq1 * wqq1 * wqq1 / rad


def inv2x2_xz(mat):
    a11, a13, a31, a33 = mat
    det = a11 * a33 - a13 * a31
    if abs(det) > 0:
        inv = (a33 / det, -a13 / det, -a31 / det, a11 / det)
    else:
        inv = (1.0, 0.0, 0.0, 1.0)
    return inv, det


def cond2x2(mat):
    a, b, c, d = mat
    # Singular values from eigenvalues of A^T A.
    s11 = a * a + c * c
    s12 = a * b + c * d
    s22 = b * b + d * d
    tr = s11 + s22
    det = s11 * s22 - s12 * s12
    disc = max(0.0, tr * tr - 4.0 * det)
    lam1 = 0.5 * (tr + math.sqrt(disc))
    lam2 = 0.5 * (tr - math.sqrt(disc))
    if lam2 <= 0:
        return float("inf")
    return math.sqrt(lam1 / lam2)


def scalar(arrays, name, i, default=0.0):
    if name not in arrays:
        return default
    v = arrays[name][i]
    if isinstance(v, (list, tuple)):
        return float(v[0])
    return float(v)


def vector(arrays, name, i):
    return arrays[name][i]


def periodic_shifts(width):
    if width and width > 0:
        return (-width, 0.0, width)
    return (0.0,)


def iter_neighbors(p1_pos, fluid_points, fluid_arrays, bound_points, bound_arrays, periodic_x):
    shifts = periodic_shifts(periodic_x)
    for source, points, arrays in (
        ("fluid", fluid_points, fluid_arrays),
        ("bound", bound_points, bound_arrays),
    ):
        mass = MASS
        for shift in shifts:
            for j, pos in enumerate(points):
                dx = float(p1_pos[0]) - (float(pos[0]) + shift)
                dz = float(p1_pos[2]) - float(pos[2])
                rr2 = dx * dx + dz * dz
                if rr2 > KERNEL_SIZE2 or rr2 < ALMOSTZERO:
                    continue
                rho = scalar(arrays, "Rhop", j, RHOP0)
                if rho <= 0:
                    if source == "bound":
                        vol2 = DP * DP
                    else:
                        continue
                else:
                    vol2 = mass / rho
                yield source, j, shift, dx, dz, rr2, vol2


def particle_diagnostics(p1, fluid_points, fluid_arrays, bound_points, bound_arrays, periodic_x):
    p1_pos = fluid_points[p1]
    p1_vel = vector(fluid_arrays, "Vel", p1)
    pwp1 = scalar(fluid_arrays, "PorePress", p1)

    count_fluid = 0
    count_bound = 0
    vol_fluid = 0.0
    vol_bound = 0.0
    posdiv = 0.0
    gradx = 0.0
    gradz = 0.0
    a11 = a13 = a31 = a33 = 0.0

    neigh_cache = []
    for source, j, shift, dx, dz, rr2, vol2 in iter_neighbors(
        p1_pos, fluid_points, fluid_arrays, bound_points, bound_arrays, periodic_x
    ):
        fac = wendland_fac(rr2)
        frx = fac * dx
        frz = fac * dz
        dot = dx * frx + dz * frz
        posdiv -= vol2 * dot
        gradx += vol2 * frx
        gradz += vol2 * frz
        a11 += -dx * frx * vol2
        a13 += -dx * frz * vol2
        a31 += -dz * frx * vol2
        a33 += -dz * frz * vol2
        if source == "fluid":
            count_fluid += 1
            vol_fluid += vol2
        else:
            count_bound += 1
            vol_bound += vol2
        neigh_cache.append((source, j, shift, dx, dz, rr2, vol2, frx, frz))

    corr, det = inv2x2_xz((a11, a13, a31, a33))
    c11, c13, c31, c33 = corr
    condition = cond2x2((a11, a13, a31, a33))
    gradcorr_x = gradx * c11 + gradz * c13
    gradcorr_z = gradx * c31 + gradz * c33
    gradcorr_norm = math.sqrt(gradcorr_x * gradcorr_x + gradcorr_z * gradcorr_z)

    out = {
        "count_fluid": count_fluid,
        "count_bound": count_bound,
        "vol_fluid": vol_fluid,
        "vol_bound": vol_bound,
        "posdiv": posdiv,
        "lcorr_xx": a11,
        "lcorr_xz": a13,
        "lcorr_zx": a31,
        "lcorr_zz": a33,
        "lcorr_det_xz": det,
        "lcorr_cond_xz": condition,
        "corr_xx": c11,
        "corr_xz": c13,
        "corr_zx": c31,
        "corr_zz": c33,
        "gradcorr_norm": gradcorr_norm,
        "comp_fluid_kpa_s": 0.0,
        "comp_bound_kpa_s": 0.0,
        "comp_fluid_x_kpa_s": 0.0,
        "comp_fluid_z_kpa_s": 0.0,
        "comp_bound_x_kpa_s": 0.0,
        "comp_bound_z_kpa_s": 0.0,
        "darcy_lapw_fluid_kpa_s": 0.0,
        "darcy_lapw_bound_kpa_s": 0.0,
        "gravity_head_fluid_kpa_s": 0.0,
        "gravity_head_bound_kpa_s": 0.0,
        "raw_comp_total_kpa_s": 0.0,
        "raw_darcy_lapw_total_kpa_s": 0.0,
    }

    for source, j, shift, dx, dz, rr2, vol2, frx, frz in neigh_cache:
        arrays = fluid_arrays if source == "fluid" else bound_arrays
        vel2 = vector(arrays, "Vel", j)
        pw2 = scalar(arrays, "PorePress", j)
        pcfrx = c11 * frx + c13 * frz
        pcfrz = c31 * frx + c33 * frz
        dvx = float(vel2[0]) - float(p1_vel[0])
        dvz = float(vel2[2]) - float(p1_vel[2])
        divv = vol2 * (dvx * pcfrx + dvz * pcfrz)
        pdotgrad = dx * pcfrx + dz * pcfrz
        lapw = vol2 * (pwp1 - pw2) * pdotgrad / (rr2 + ETA2)
        lapz = vol2 * dz * pdotgrad / (rr2 + ETA2)
        comp_x = KWN * (-(vol2 * dvx * pcfrx)) / 1000.0
        comp_z = KWN * (-(vol2 * dvz * pcfrz)) / 1000.0
        comp = comp_x + comp_z
        darcy = KWN * (2.0 * KHYD * lapw / (RHOW * GHYD)) / 1000.0
        ghead = KWN * (2.0 * KHYD * lapz) / 1000.0

        raw_divv = vol2 * (dvx * frx + dvz * frz)
        raw_pdotgrad = dx * frx + dz * frz
        raw_lapw = vol2 * (pwp1 - pw2) * raw_pdotgrad / (rr2 + ETA2)
        out["raw_comp_total_kpa_s"] += KWN * (-raw_divv) / 1000.0
        out["raw_darcy_lapw_total_kpa_s"] += KWN * (2.0 * KHYD * raw_lapw / (RHOW * GHYD)) / 1000.0

        if source == "fluid":
            out["comp_fluid_kpa_s"] += comp
            out["comp_fluid_x_kpa_s"] += comp_x
            out["comp_fluid_z_kpa_s"] += comp_z
            out["darcy_lapw_fluid_kpa_s"] += darcy
            out["gravity_head_fluid_kpa_s"] += ghead
        else:
            out["comp_bound_kpa_s"] += comp
            out["comp_bound_x_kpa_s"] += comp_x
            out["comp_bound_z_kpa_s"] += comp_z
            out["darcy_lapw_bound_kpa_s"] += darcy
            out["gravity_head_bound_kpa_s"] += ghead
    return out


def mean(vals):
    vals = list(vals)
    return sum(vals) / len(vals) if vals else float("nan")


def component_stats(points, arrays, idxs):
    if not idxs:
        return {}
    vel = arrays.get("Vel", [])
    ppw = arrays.get("PorePress", [])
    epwp = arrays.get("ExcessPorePress", [])
    stats = {
        "count": len(idxs),
        "vx_m_s": mean(float(vel[i][0]) for i in idxs) if vel else float("nan"),
        "vz_m_s": mean(float(vel[i][2]) for i in idxs) if vel else float("nan"),
        "abs_vx_m_s": max(abs(float(vel[i][0])) for i in idxs) if vel else float("nan"),
        "abs_vz_m_s": max(abs(float(vel[i][2])) for i in idxs) if vel else float("nan"),
        "porepress_kpa": mean(float(ppw[i]) for i in idxs) / 1000.0 if ppw else float("nan"),
        "epwp_kpa": mean(float(epwp[i]) for i in idxs) / 1000.0 if epwp else float("nan"),
    }
    return stats


def frame_diagnostics(idx, fluid_path, bound_path, args):
    fluid_points, fluid_arrays = read_vtk_arrays(fluid_path)
    bound_points, bound_arrays = read_vtk_arrays(bound_path)
    bottom = bottom_indices(fluid_points, thickness=args.bottom_thickness)
    per_particle = [
        particle_diagnostics(i, fluid_points, fluid_arrays, bound_points, bound_arrays, args.periodic_x)
        for i in bottom
    ]

    time_rel_s = min(args.tmax, idx * args.tout)
    tv = args.tv_offset + pp.CV_TERZAGHI * time_rel_s / (pp.H * pp.H)
    theory_time_s = tv * pp.H * pp.H / pp.CV_TERZAGHI
    b_excess, bz = bottom_mean(fluid_points, fluid_arrays, "ExcessPorePress")
    theory = pp.terzaghi_excess(bz, theory_time_s)
    bottom_stats = component_stats(fluid_points, fluid_arrays, bottom)
    max_bound_z = max(float(p[2]) for p in bound_points) if bound_points else float("nan")
    bound_top = [i for i, p in enumerate(bound_points) if abs(float(p[2]) - max_bound_z) <= DP * 0.25]
    bound_top_stats = component_stats(bound_points, bound_arrays, bound_top)
    bound_all_stats = component_stats(bound_points, bound_arrays, range(len(bound_points)))

    row = {
        "part_index": idx,
        "time_rel_s": time_rel_s,
        "tv": tv,
        "bottom_z_m": bz,
        "bottom_excess_sph_kpa": b_excess / 1000.0,
        "bottom_excess_theory_kpa": theory / 1000.0,
        "bottom_error_kpa": (b_excess - theory) / 1000.0,
        "bottom_particle_count": len(bottom),
        "bottom_vx_m_s": bottom_stats.get("vx_m_s", float("nan")),
        "bottom_vz_m_s": bottom_stats.get("vz_m_s", float("nan")),
        "bottom_abs_vx_m_s": bottom_stats.get("abs_vx_m_s", float("nan")),
        "bottom_abs_vz_m_s": bottom_stats.get("abs_vz_m_s", float("nan")),
        "bound_top_count": bound_top_stats.get("count", 0),
        "bound_top_vx_m_s": bound_top_stats.get("vx_m_s", float("nan")),
        "bound_top_vz_m_s": bound_top_stats.get("vz_m_s", float("nan")),
        "bound_top_porepress_kpa": bound_top_stats.get("porepress_kpa", float("nan")),
        "bound_top_epwp_kpa": bound_top_stats.get("epwp_kpa", float("nan")),
        "bound_all_vz_m_s": bound_all_stats.get("vz_m_s", float("nan")),
        "bound_all_epwp_kpa": bound_all_stats.get("epwp_kpa", float("nan")),
    }

    keys = list(per_particle[0])
    for key in keys:
        row[key] = mean(p[key] for p in per_particle)

    row["count_total"] = row["count_fluid"] + row["count_bound"]
    row["bound_count_fraction"] = row["count_bound"] / row["count_total"] if row["count_total"] else float("nan")
    row["vol_total"] = row["vol_fluid"] + row["vol_bound"]
    row["bound_vol_fraction"] = row["vol_bound"] / row["vol_total"] if row["vol_total"] else float("nan")
    row["comp_total_kpa_s"] = row["comp_fluid_kpa_s"] + row["comp_bound_kpa_s"]
    row["darcy_lapw_total_kpa_s"] = row["darcy_lapw_fluid_kpa_s"] + row["darcy_lapw_bound_kpa_s"]
    row["gravity_head_total_kpa_s"] = row["gravity_head_fluid_kpa_s"] + row["gravity_head_bound_kpa_s"]
    row["rate_total_kpa_s"] = row["comp_total_kpa_s"] + row["darcy_lapw_total_kpa_s"] + row["gravity_head_total_kpa_s"]
    row["raw_rate_total_kpa_s"] = row["raw_comp_total_kpa_s"] + row["raw_darcy_lapw_total_kpa_s"] + row["gravity_head_total_kpa_s"]
    return row


def make_plot(rows, fig_path, title):
    tv = [r["tv"] for r in rows]
    fig, axes = plt.subplots(6, 1, figsize=(13, 17), sharex=True, constrained_layout=True)

    axes[0].plot(tv, [r["bottom_excess_sph_kpa"] for r in rows], label="SPH bottom EPWP", color="#1f77b4")
    axes[0].plot(tv, [r["bottom_excess_theory_kpa"] for r in rows], "--", label="Terzaghi", color="#444444")
    axes[0].set_ylabel("EPWP [kPa]")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(tv, [r["bottom_error_kpa"] for r in rows], label="SPH - theory", color="#d62728")
    axes[1].plot(tv, [r["bottom_error_dtv_kpa"] for r in rows], label="d(error)/dTv", color="#9467bd")
    axes[1].axhline(0, color="k", linewidth=0.8)
    axes[1].set_ylabel("Residual")
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(tv, [r["count_fluid"] for r in rows], label="fluid neighbours", color="#1f77b4")
    axes[2].plot(tv, [r["count_bound"] for r in rows], label="boundary neighbours", color="#ff7f0e")
    axes[2].plot(tv, [r["bound_count_fraction"] for r in rows], label="boundary fraction", color="#2ca02c")
    axes[2].set_ylabel("Support count")
    axes[2].legend()
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(tv, [r["lcorr_det_xz"] for r in rows], label="det(lcorr x-z)", color="#1f77b4")
    axes[3].plot(tv, [r["lcorr_cond_xz"] for r in rows], label="cond(lcorr x-z)", color="#ff7f0e")
    axes[3].plot(tv, [r["posdiv"] for r in rows], label="posdiv", color="#2ca02c")
    axes[3].set_ylabel("Corr/support")
    axes[3].legend()
    axes[3].grid(True, alpha=0.25)

    axes[4].plot(tv, [r["comp_fluid_kpa_s"] for r in rows], label="compression fluid", color="#1f77b4")
    axes[4].plot(tv, [r["comp_bound_kpa_s"] for r in rows], label="compression boundary", color="#ff7f0e")
    axes[4].plot(tv, [r["comp_total_kpa_s"] for r in rows], "--", label="compression total", color="#111111")
    axes[4].set_ylabel("Comp. [kPa/s]")
    axes[4].legend()
    axes[4].grid(True, alpha=0.25)

    axes[5].plot(tv, [r["darcy_lapw_fluid_kpa_s"] for r in rows], label="Darcy lapw fluid", color="#1f77b4")
    axes[5].plot(tv, [r["darcy_lapw_bound_kpa_s"] for r in rows], label="Darcy lapw boundary", color="#ff7f0e")
    axes[5].plot(tv, [r["darcy_lapw_total_kpa_s"] for r in rows], "--", label="Darcy lapw total", color="#111111")
    axes[5].plot(tv, [r["rate_total_kpa_s"] for r in rows], ":", label="net rate", color="#9467bd")
    axes[5].set_ylabel("Darcy [kPa/s]")
    axes[5].set_xlabel("Time factor Tv")
    axes[5].legend()
    axes[5].grid(True, alpha=0.25)

    fig.suptitle(title)
    fig.savefig(fig_path, dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tout", required=True, type=float)
    parser.add_argument("--tmax", required=True, type=float)
    parser.add_argument("--tv-offset", required=True, type=float)
    parser.add_argument("--periodic-x", type=float, default=0.1)
    parser.add_argument("--bottom-thickness", type=float, default=0.1)
    args = parser.parse_args()

    fluid_paths = sorted(args.particles.glob("PartFluid_*.vtk"), key=part_index)
    if not fluid_paths:
        raise RuntimeError(f"No PartFluid VTK files found in {args.particles}")
    args.figdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for fluid_path in fluid_paths:
        idx = part_index(fluid_path)
        bound_path = args.particles / f"PartBound_{idx:04d}.vtk"
        if not bound_path.exists():
            raise RuntimeError(f"Missing matching boundary VTK: {bound_path}")
        rows.append(frame_diagnostics(idx, fluid_path, bound_path, args))

    for key, out_key in [
        ("bottom_error_kpa", "bottom_error_dtv_kpa"),
        ("rate_total_kpa_s", "rate_total_dtv_kpa_s"),
        ("count_bound", "count_bound_dtv"),
        ("lcorr_det_xz", "lcorr_det_dtv"),
        ("lcorr_cond_xz", "lcorr_cond_dtv"),
    ]:
        vals = central_derivative(rows, key, xkey="tv")
        for row, val in zip(rows, vals):
            row[out_key] = val

    csv_path = args.figdir / "support_composition_timeseries.csv"
    write_csv(csv_path, rows, list(rows[0]))
    fig_path = args.figdir / "support_composition_diagnostics.png"
    make_plot(rows, fig_path, f"{args.case}: offline support/correction diagnostics")

    print(f"Saved CSV: {csv_path}")
    print(f"Saved figure: {fig_path}")
    print(f"Rows: {len(rows)}, Tv range {rows[0]['tv']:.6f} to {rows[-1]['tv']:.6f}")
    print(
        "Mean boundary neighbours: "
        f"{mean(r['count_bound'] for r in rows):.3f}; "
        "Mean fluid neighbours: "
        f"{mean(r['count_fluid'] for r in rows):.3f}"
    )


if __name__ == "__main__":
    main()
