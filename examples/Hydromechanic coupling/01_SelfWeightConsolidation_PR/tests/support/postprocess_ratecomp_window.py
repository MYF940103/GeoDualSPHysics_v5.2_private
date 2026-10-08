from pathlib import Path
import argparse
import csv
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
    bottom_mean,
    central_derivative,
    layer_average,
    linear_slope,
    part_index,
    read_vtk_arrays,
)


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tout", required=True, type=float)
    parser.add_argument("--tmax", required=True, type=float)
    parser.add_argument("--tv-offset", required=True, type=float)
    args = parser.parse_args()

    paths = sorted(args.particles.glob("PartFluid_*.vtk"), key=part_index)
    if not paths:
        raise RuntimeError(f"No PartFluid VTK files found in {args.particles}")
    args.figdir.mkdir(parents=True, exist_ok=True)

    rows = []
    available_arrays = None
    for path in paths:
        idx = part_index(path)
        time_rel_s = min(args.tmax, idx * args.tout)
        tv = args.tv_offset + pp.CV_TERZAGHI * time_rel_s / (pp.H * pp.H)
        theory_time_s = tv * pp.H * pp.H / pp.CV_TERZAGHI
        points, arrays = read_vtk_arrays(path)
        if available_arrays is None:
            available_arrays = sorted(arrays)
        if "HydroMechLoadAce" not in arrays:
            raise RuntimeError(
                f"{path} does not contain HydroMechLoadAce. Add +hydromechloadace to PartVTK vars "
                "and run with the temporary rate-component diagnostic build."
            )

        b_excess, bz = bottom_mean(points, arrays, "ExcessPorePress")
        theory = pp.terzaghi_excess(bz, theory_time_s)
        comp, _ = bottom_mean(points, arrays, "HydroMechLoadAce", component=0)
        lapw, _ = bottom_mean(points, arrays, "HydroMechLoadAce", component=1)
        ghead, _ = bottom_mean(points, arrays, "HydroMechLoadAce", component=2)
        b_vz, _ = bottom_mean(points, arrays, "Vel", component=2)
        b_sigma_zz, _ = bottom_mean(points, arrays, "Sigma_kk", component=2)

        layer_vz = layer_average(points, arrays, "Vel", component=2)
        dvz_bottom = linear_slope(layer_vz[:6])
        dvz_lower = linear_slope(layer_vz[2:12])

        rows.append({
            "part": path.name,
            "part_index": idx,
            "time_rel_s": time_rel_s,
            "tv": tv,
            "bottom_z_m": bz,
            "bottom_excess_sph_kpa": b_excess / 1000.0,
            "bottom_excess_theory_kpa": theory / 1000.0,
            "bottom_error_kpa": (b_excess - theory) / 1000.0,
            "rate_compression_kpa_s": comp,
            "rate_darcy_lapw_kpa_s": lapw,
            "rate_gravity_head_kpa_s": ghead,
            "rate_component_total_kpa_s": comp + lapw + ghead,
            "bottom_vz_m_s": b_vz,
            "dvz_dz_bottom_proxy_1_s": dvz_bottom,
            "dvz_dz_lower_proxy_1_s": dvz_lower,
            "bottom_sigma_zz_pa": b_sigma_zz,
            "bottom_sigma_zz_theory_pa": pp.effective_sigma_zz(bz),
            "bottom_sigma_zz_error_pa": b_sigma_zz - pp.effective_sigma_zz(bz),
        })

    for key, out_key in [
        ("bottom_excess_sph_kpa", "actual_bottom_dpw_dt_kpa_s"),
        ("bottom_error_kpa", "bottom_error_dtv_kpa"),
        ("bottom_vz_m_s", "bottom_vz_dtv_m_s"),
        ("dvz_dz_bottom_proxy_1_s", "dvz_dz_bottom_dtv_1_s"),
    ]:
        vals = central_derivative(rows, key, xkey="time_rel_s" if out_key.endswith("_dt_kpa_s") else "tv")
        for row, val in zip(rows, vals):
            row[out_key] = val

    fields = list(rows[0].keys())
    csv_path = args.figdir / "rate_component_window_timeseries.csv"
    write_csv(csv_path, rows, fields)

    arrays_path = args.figdir / "available_vtk_arrays.txt"
    arrays_path.write_text("\n".join(available_arrays or []) + "\n", encoding="utf-8")

    tv = [r["tv"] for r in rows]
    fig, axes = plt.subplots(5, 1, figsize=(13, 15), sharex=True, constrained_layout=True)
    axes[0].plot(tv, [r["bottom_excess_sph_kpa"] for r in rows], label="SPH bottom excess", color="#1f77b4")
    axes[0].plot(tv, [r["bottom_excess_theory_kpa"] for r in rows], "--", label="Terzaghi theory", color="#464C55")
    axes[0].set_ylabel("EPWP [kPa]")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(tv, [r["bottom_error_kpa"] for r in rows], label="SPH - theory", color="#d62728")
    axes[1].plot(tv, [r["bottom_error_dtv_kpa"] for r in rows], label="d(error)/dTv", color="#9467bd")
    axes[1].axhline(0, color="k", linewidth=0.8)
    axes[1].set_ylabel("Residual")
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(tv, [r["rate_compression_kpa_s"] for r in rows], label="compression", color="#1f77b4")
    axes[2].plot(tv, [r["rate_darcy_lapw_kpa_s"] for r in rows], label="Darcy lapw", color="#ff7f0e")
    axes[2].plot(tv, [r["rate_gravity_head_kpa_s"] for r in rows], label="gravity head", color="#2ca02c")
    axes[2].set_ylabel("Rate [kPa/s]")
    axes[2].legend()
    axes[2].grid(True, alpha=0.25)

    axes[3].plot(tv, [r["rate_component_total_kpa_s"] for r in rows], "--", label="component total", color="#111111")
    axes[3].plot(tv, [r["actual_bottom_dpw_dt_kpa_s"] for r in rows], "o-", markersize=2.5, label="actual bottom dEPWP/dt", color="#1f77b4")
    axes[3].axhline(0, color="k", linewidth=0.8)
    axes[3].set_ylabel("Net rate [kPa/s]")
    axes[3].legend()
    axes[3].grid(True, alpha=0.25)

    axes[4].plot(tv, [r["bottom_vz_m_s"] for r in rows], label="bottom mean vz", color="#17becf")
    axes[4].plot(tv, [r["dvz_dz_bottom_proxy_1_s"] for r in rows], label="bottom dvz/dz proxy", color="#ff7f0e")
    axes[4].plot(tv, [r["dvz_dz_lower_proxy_1_s"] for r in rows], label="lower-column dvz/dz proxy", color="#bcbd22")
    axes[4].axhline(0, color="k", linewidth=0.8)
    axes[4].set_ylabel("Kinematic")
    axes[4].set_xlabel("Time factor Tv")
    axes[4].legend()
    axes[4].grid(True, alpha=0.25)

    fig.suptitle(f"{args.case}: high-frequency pore-rate component diagnostic")
    fig_path = args.figdir / "rate_component_window_diagnostics.png"
    fig.savefig(fig_path, dpi=220)

    print(f"Saved CSV: {csv_path}")
    print(f"Saved figure: {fig_path}")
    print(f"Saved arrays list: {arrays_path}")
    print(f"Rows: {len(rows)}, Tv range {rows[0]['tv']:.6f} to {rows[-1]['tv']:.6f}")
    print(
        "Max abs net component rate: "
        f"{max(abs(r['rate_component_total_kpa_s']) for r in rows):.6g} kPa/s; "
        "Max abs actual bottom rate: "
        f"{max(abs(r['actual_bottom_dpw_dt_kpa_s']) for r in rows if r['actual_bottom_dpw_dt_kpa_s']==r['actual_bottom_dpw_dt_kpa_s']):.6g} kPa/s"
    )


if __name__ == "__main__":
    main()
