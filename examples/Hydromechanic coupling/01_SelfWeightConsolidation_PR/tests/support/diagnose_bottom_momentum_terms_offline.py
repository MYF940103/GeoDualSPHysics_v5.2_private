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
    central_derivative,
    part_index,
    read_vtk_arrays,
)


DP = 0.01
H = 1.8 * DP
KERNEL_SIZE2 = (2.0 * H) ** 2
ETA2 = (0.1 * H) ** 2
RHOP0 = 2100.0
MASS = RHOP0 * DP * DP
BWEN = -2.7852 / (H * H * H)
ALMOSTZERO = 1.0e-18


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def scalar(arrays, name, i, default=0.0):
    if name not in arrays:
        return default
    value = arrays[name][i]
    if isinstance(value, (list, tuple)):
        return float(value[0])
    return float(value)


def vector(arrays, name, i, default=(0.0, 0.0, 0.0)):
    if name not in arrays:
        return default
    return arrays[name][i]


def sigma_components(arrays, i):
    diag = vector(arrays, "Sigma_kk", i)
    shear = vector(arrays, "Sigma_ij", i)
    return {
        "xx": float(diag[0]),
        "yy": float(diag[1]),
        "zz": float(diag[2]),
        "xy": float(shear[0]),
        "yz": float(shear[1]),
        "xz": float(shear[2]),
    }


def wendland_fac(rr2):
    rad = math.sqrt(rr2)
    qq = rad / H
    wqq1 = 1.0 - 0.5 * qq
    return BWEN * qq * wqq1 * wqq1 * wqq1 / rad


def periodic_shifts(width):
    return (-width, 0.0, width) if width and width > 0 else (0.0,)


def iter_neighbors(p1_pos, fluid_points, fluid_arrays, bound_points, bound_arrays, periodic_x):
    for source, points, arrays in (
        ("fluid", fluid_points, fluid_arrays),
        ("bound", bound_points, bound_arrays),
    ):
        for shift in periodic_shifts(periodic_x):
            for j, pos in enumerate(points):
                dx = float(p1_pos[0]) - (float(pos[0]) + shift)
                dz = float(p1_pos[2]) - float(pos[2])
                rr2 = dx * dx + dz * dz
                if rr2 > KERNEL_SIZE2 or rr2 < ALMOSTZERO:
                    continue
                rho = scalar(arrays, "Rhop", j, RHOP0)
                if rho <= 0:
                    continue
                fac = wendland_fac(rr2)
                yield source, j, dx, dz, rr2, fac * dx, fac * dz, rho


def particle_momentum_terms(p1, fluid_points, fluid_arrays, bound_points, bound_arrays, args):
    p1_pos = fluid_points[p1]
    vel1 = vector(fluid_arrays, "Vel", p1)
    rho1 = scalar(fluid_arrays, "Rhop", p1, RHOP0)
    pw1 = scalar(fluid_arrays, "PorePress", p1, 0.0)
    sig1 = sigma_components(fluid_arrays, p1)
    invrho1_2 = 1.0 / (rho1 * rho1)

    rows = {
        "ace_stress_z_m_s2": 0.0,
        "ace_stress_fluid_z_m_s2": 0.0,
        "ace_stress_bound_z_m_s2": 0.0,
        "ace_stress_zz_z_m_s2": 0.0,
        "ace_stress_xz_z_m_s2": 0.0,
        "ace_pore_z_m_s2": 0.0,
        "ace_pore_fluid_z_m_s2": 0.0,
        "ace_pore_bound_z_m_s2": 0.0,
        "ace_single_totalstress_z_m_s2": 0.0,
        "ace_single_totalstress_fluid_z_m_s2": 0.0,
        "ace_single_totalstress_bound_z_m_s2": 0.0,
        "ace_exact_totalstress_z_m_s2": 0.0,
        "ace_exact_totalstress_fluid_z_m_s2": 0.0,
        "ace_exact_totalstress_bound_z_m_s2": 0.0,
        "ace_exact_totalstress_ghostbound_z_m_s2": 0.0,
        "ace_exact_totalstress_ghostbound_fluid_z_m_s2": 0.0,
        "ace_exact_totalstress_ghostbound_bound_z_m_s2": 0.0,
        "ace_exact_totalstress_interfacebound_z_m_s2": 0.0,
        "ace_exact_totalstress_interfacebound_fluid_z_m_s2": 0.0,
        "ace_exact_totalstress_interfacebound_bound_z_m_s2": 0.0,
        "ace_visc_z_m_s2": 0.0,
        "ace_visc_fluid_z_m_s2": 0.0,
        "ace_visc_bound_z_m_s2": 0.0,
        "visc_active_count": 0.0,
        "visc_active_fluid_count": 0.0,
        "visc_active_bound_count": 0.0,
        "neigh_fluid_count": 0.0,
        "neigh_bound_count": 0.0,
    }

    for source, j, dx, dz, rr2, frx, frz, rho2 in iter_neighbors(
        p1_pos, fluid_points, fluid_arrays, bound_points, bound_arrays, args.periodic_x
    ):
        arrays = fluid_arrays if source == "fluid" else bound_arrays
        sig2 = sigma_components(arrays, j)
        invrho2_2 = 1.0 / (rho2 * rho2)
        mass2 = MASS
        vel2 = vector(arrays, "Vel", j)
        pw2 = scalar(arrays, "PorePress", j, 0.0)

        prszz = mass2 * (sig1["zz"] * invrho1_2 + sig2["zz"] * invrho2_2)
        prsxz = mass2 * (sig1["xz"] * invrho1_2 + sig2["xz"] * invrho2_2)
        stress_zz = prszz * frz
        stress_xz = prsxz * frx
        stress_z = stress_zz + stress_xz

        prspw = -mass2 * (pw1 + pw2) / (rho1 * rho2)
        pore_z = prspw * frz

        total1_zz = sig1["zz"] - pw1
        total2_zz = sig2["zz"] - pw2
        single_totalstress_z = mass2 * (
            (total1_zz * invrho1_2 + total2_zz * invrho2_2) * frz
            + (sig1["xz"] * invrho1_2 + sig2["xz"] * invrho2_2) * frx
        )
        exact1_zz = -RHOP0 * abs(args.gravity_z) * max(0.0, args.selfweight_top_z - float(p1_pos[2]))
        p2_pos = (bound_points if source == "bound" else fluid_points)[j]
        exact2_zz = -RHOP0 * abs(args.gravity_z) * max(0.0, args.selfweight_top_z - float(p2_pos[2]))
        exact_totalstress_z = mass2 * (exact1_zz * invrho1_2 + exact2_zz * invrho2_2) * frz
        p2_ghost_z = float(p2_pos[2])
        if source == "bound":
            p2_ghost_z += float(vector(arrays, "BoundNormal", j, (0.0, 0.0, 0.0))[2])
        exact2_ghost_zz = -RHOP0 * abs(args.gravity_z) * max(0.0, args.selfweight_top_z - p2_ghost_z)
        exact_totalstress_ghostbound_z = mass2 * (
            exact1_zz * invrho1_2 + exact2_ghost_zz * invrho2_2
        ) * frz
        p2_interface_z = 0.0 if source == "bound" and float(p2_pos[2]) < 0.0 else float(p2_pos[2])
        exact2_interface_zz = -RHOP0 * abs(args.gravity_z) * max(
            0.0, args.selfweight_top_z - p2_interface_z
        )
        exact_totalstress_interfacebound_z = mass2 * (
            exact1_zz * invrho1_2 + exact2_interface_zz * invrho2_2
        ) * frz

        dvx = float(vel1[0]) - float(vel2[0])
        dvz = float(vel1[2]) - float(vel2[2])
        dot = dx * dvx + dz * dvz
        visc_z = 0.0
        if dot < 0.0:
            dot_rr2 = dot / (rr2 + ETA2)
            amubar = H * dot_rr2
            robar = 0.5 * (rho1 + rho2)
            pi_visc = (-args.visco * args.cs0 * amubar / robar) * mass2
            visc_z = -pi_visc * frz
            rows["visc_active_count"] += 1.0
            rows[f"visc_active_{source}_count"] += 1.0

        rows["ace_stress_z_m_s2"] += stress_z
        rows[f"ace_stress_{source}_z_m_s2"] += stress_z
        rows["ace_stress_zz_z_m_s2"] += stress_zz
        rows["ace_stress_xz_z_m_s2"] += stress_xz
        rows["ace_pore_z_m_s2"] += pore_z
        rows[f"ace_pore_{source}_z_m_s2"] += pore_z
        rows["ace_single_totalstress_z_m_s2"] += single_totalstress_z
        rows[f"ace_single_totalstress_{source}_z_m_s2"] += single_totalstress_z
        rows["ace_exact_totalstress_z_m_s2"] += exact_totalstress_z
        rows[f"ace_exact_totalstress_{source}_z_m_s2"] += exact_totalstress_z
        rows["ace_exact_totalstress_ghostbound_z_m_s2"] += exact_totalstress_ghostbound_z
        rows[f"ace_exact_totalstress_ghostbound_{source}_z_m_s2"] += exact_totalstress_ghostbound_z
        rows["ace_exact_totalstress_interfacebound_z_m_s2"] += exact_totalstress_interfacebound_z
        rows[f"ace_exact_totalstress_interfacebound_{source}_z_m_s2"] += exact_totalstress_interfacebound_z
        rows["ace_visc_z_m_s2"] += visc_z
        rows[f"ace_visc_{source}_z_m_s2"] += visc_z
        rows[f"neigh_{source}_count"] += 1.0

    cd = args.soil_damping_coef * math.sqrt(args.modulus_e / (rho1 * H * H))
    rows["ace_damping_z_m_s2"] = -cd * float(vel1[2])
    rows["ace_gravity_z_m_s2"] = args.gravity_z
    rows["ace_total_z_m_s2"] = (
        rows["ace_stress_z_m_s2"]
        + rows["ace_pore_z_m_s2"]
        + rows["ace_visc_z_m_s2"]
        + rows["ace_damping_z_m_s2"]
        + rows["ace_gravity_z_m_s2"]
    )
    rows["ace_split_stress_pore_z_m_s2"] = rows["ace_stress_z_m_s2"] + rows["ace_pore_z_m_s2"]
    rows["ace_split_minus_single_totalstress_z_m_s2"] = (
        rows["ace_split_stress_pore_z_m_s2"] - rows["ace_single_totalstress_z_m_s2"]
    )
    rows["ace_actual_totalstress_minus_exact_z_m_s2"] = (
        rows["ace_single_totalstress_z_m_s2"] - rows["ace_exact_totalstress_z_m_s2"]
    )
    rows["ace_exact_balance_z_m_s2"] = (
        rows["ace_exact_totalstress_z_m_s2"] + rows["ace_gravity_z_m_s2"]
    )
    rows["ace_exact_balance_ghostbound_z_m_s2"] = (
        rows["ace_exact_totalstress_ghostbound_z_m_s2"] + rows["ace_gravity_z_m_s2"]
    )
    rows["ace_actual_totalstress_minus_exact_ghostbound_z_m_s2"] = (
        rows["ace_single_totalstress_z_m_s2"] - rows["ace_exact_totalstress_ghostbound_z_m_s2"]
    )
    rows["ace_exact_balance_interfacebound_z_m_s2"] = (
        rows["ace_exact_totalstress_interfacebound_z_m_s2"] + rows["ace_gravity_z_m_s2"]
    )
    rows["ace_actual_totalstress_minus_exact_interfacebound_z_m_s2"] = (
        rows["ace_single_totalstress_z_m_s2"] - rows["ace_exact_totalstress_interfacebound_z_m_s2"]
    )
    rows["ace_actual_balance_no_visc_damping_z_m_s2"] = (
        rows["ace_single_totalstress_z_m_s2"] + rows["ace_gravity_z_m_s2"]
    )
    rows["bottom_vz_m_s"] = float(vel1[2])
    rows["bottom_porepress_kpa"] = pw1 / 1000.0
    rows["bottom_sigma_zz_kpa"] = sig1["zz"] / 1000.0
    return rows


def frame_terms(idx, fluid_path, bound_path, args):
    fluid_points, fluid_arrays = read_vtk_arrays(fluid_path)
    bound_points, bound_arrays = read_vtk_arrays(bound_path)
    bottom = bottom_indices(fluid_points, thickness=args.bottom_thickness)
    per_particle = [
        particle_momentum_terms(i, fluid_points, fluid_arrays, bound_points, bound_arrays, args)
        for i in bottom
    ]

    time_rel_s = min(args.tmax, idx * args.tout)
    tv = args.tv_offset + pp.CV_TERZAGHI * time_rel_s / (pp.H * pp.H)
    row = {
        "part_index": idx,
        "time_rel_s": time_rel_s,
        "tv": tv,
        "bottom_particle_count": len(bottom),
    }
    for key in per_particle[0]:
        row[key] = mean(p[key] for p in per_particle)
    return row


def make_plot(rows, path, title):
    tv = [r["tv"] for r in rows]
    fig, axes = plt.subplots(5, 1, figsize=(13, 15), sharex=True, constrained_layout=True)

    axes[0].plot(tv, [r["bottom_vz_m_s"] for r in rows], label="bottom mean vz", color="#1f77b4")
    axes[0].set_ylabel("vz [m/s]")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(tv, [r["dvz_dt_fd_m_s2"] for r in rows], label="finite-diff dvz/dt", color="#111111")
    axes[1].plot(tv, [r["ace_total_z_m_s2"] for r in rows], "--", label="offline sum", color="#9467bd")
    axes[1].set_ylabel("accel [m/s2]")
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(tv, [r["ace_stress_z_m_s2"] for r in rows], label="stress total", color="#1f77b4")
    axes[2].plot(tv, [r["ace_pore_z_m_s2"] for r in rows], label="pore feedback", color="#ff7f0e")
    axes[2].plot(tv, [r["ace_gravity_z_m_s2"] for r in rows], label="gravity", color="#444444")
    axes[2].set_ylabel("accel [m/s2]")
    axes[2].legend()
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(tv, [r["ace_stress_bound_z_m_s2"] for r in rows], label="stress from bound", color="#1f77b4")
    axes[3].plot(tv, [r["ace_pore_bound_z_m_s2"] for r in rows], label="pore from bound", color="#ff7f0e")
    axes[3].plot(tv, [r["ace_visc_bound_z_m_s2"] for r in rows], label="visc from bound", color="#2ca02c")
    axes[3].set_ylabel("boundary accel")
    axes[3].legend()
    axes[3].grid(True, alpha=0.25)

    axes[4].plot(tv, [r["ace_visc_z_m_s2"] for r in rows], label="artificial viscosity total", color="#2ca02c")
    axes[4].plot(tv, [r["visc_active_count"] for r in rows], label="active visc neighbor count", color="#d62728")
    axes[4].plot(tv, [r["ace_damping_z_m_s2"] for r in rows], label="soil damping", color="#9467bd")
    axes[4].set_ylabel("visc / count")
    axes[4].set_xlabel("Time factor Tv")
    axes[4].legend()
    axes[4].grid(True, alpha=0.25)

    for ax in axes:
        ax.axvspan(0.520, 0.523, color="#f2c94c", alpha=0.16, linewidth=0)
    fig.suptitle(title)
    fig.savefig(path, dpi=220)
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
    parser.add_argument("--cs0", type=float, default=35.80574408560461)
    parser.add_argument("--visco", type=float, default=0.4)
    parser.add_argument("--soil-damping-coef", type=float, default=4e-5)
    parser.add_argument("--modulus-e", type=float, default=2e6)
    parser.add_argument("--gravity-z", type=float, default=-9.81)
    parser.add_argument("--selfweight-top-z", type=float, default=1.0)
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
        rows.append(frame_terms(idx, fluid_path, bound_path, args))

    for key, out_key in [
        ("bottom_vz_m_s", "dvz_dtv_m_s"),
        ("ace_total_z_m_s2", "ace_total_dtv_m_s2"),
        ("ace_stress_z_m_s2", "ace_stress_dtv_m_s2"),
        ("ace_pore_z_m_s2", "ace_pore_dtv_m_s2"),
        ("ace_visc_z_m_s2", "ace_visc_dtv_m_s2"),
    ]:
        vals = central_derivative(rows, key, xkey="tv")
        for row, val in zip(rows, vals):
            row[out_key] = val
    for row in rows:
        row["dvz_dt_fd_m_s2"] = row["dvz_dtv_m_s"] * pp.CV_TERZAGHI / (pp.H * pp.H)

    csv_path = args.figdir / "bottom_momentum_terms_timeseries.csv"
    write_csv(csv_path, rows, list(rows[0]))
    fig_path = args.figdir / "bottom_momentum_terms_diagnostics.png"
    make_plot(rows, fig_path, f"{args.case}: bottom momentum terms")

    print(f"Saved CSV: {csv_path}")
    print(f"Saved figure: {fig_path}")
    print(f"Rows: {len(rows)}, Tv range {rows[0]['tv']:.6f} to {rows[-1]['tv']:.6f}")
    for tv_target in (0.500, 0.520, 0.523, 0.540):
        nearest = min(rows, key=lambda r: abs(r["tv"] - tv_target))
        print(
            f"Tv={nearest['tv']:.6f}: vz={nearest['bottom_vz_m_s']:.6e}, "
            f"dvz/dt={nearest['dvz_dt_fd_m_s2']:.6e}, "
            f"stress={nearest['ace_stress_z_m_s2']:.6e}, "
            f"pore={nearest['ace_pore_z_m_s2']:.6e}, "
            f"visc={nearest['ace_visc_z_m_s2']:.6e}, "
            f"total={nearest['ace_total_z_m_s2']:.6e}"
        )


if __name__ == "__main__":
    main()
