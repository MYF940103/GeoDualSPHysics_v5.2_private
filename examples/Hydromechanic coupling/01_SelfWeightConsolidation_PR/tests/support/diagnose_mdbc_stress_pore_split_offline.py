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
from diagnose_scenario2_baseline_oscillations import part_index, read_vtk_arrays


DP = 0.01
RHO_W = 1000.0
GRAVITY = 9.81


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def component(arrays, name, i, comp=0, default=0.0):
    if name not in arrays:
        return default
    value = arrays[name][i]
    if isinstance(value, (list, tuple)):
        return float(value[comp])
    return float(value)


def scalar(arrays, name, i, default=0.0):
    return component(arrays, name, i, 0, default)


def z_layer(z):
    return int(round(float(z) / DP))


def point_rows(kind, points, arrays, part, tv, time_rel_s, x_min, x_max):
    rows = []
    for i, pos in enumerate(points):
        x = float(pos[0])
        z = float(pos[2])
        if x < x_min - 1.0e-9 or x > x_max + 1.0e-9:
            continue
        sigma_zz = component(arrays, "Sigma_kk", i, 2)
        pore = scalar(arrays, "PorePress", i)
        pore0 = scalar(arrays, "PorePress0", i)
        # The solver stores tensile-positive effective stress and adds pore-pressure
        # feedback separately, so the equivalent total normal stress is sigma' - pw.
        total_zz = sigma_zz - pore
        rows.append({
            "part": part,
            "time_rel_s": time_rel_s,
            "tv": tv,
            "kind": kind,
            "id_local": i,
            "x_m": x,
            "z_m": z,
            "z_layer": z_layer(z),
            "sigma_eff_zz_kpa": sigma_zz / 1000.0,
            "porepress_kpa": pore / 1000.0,
            "porepress0_kpa": pore0 / 1000.0,
            "excess_porepress_kpa": (pore - pore0) / 1000.0,
            "sigma_total_zz_kpa": total_zz / 1000.0,
            "rhop_kg_m3": scalar(arrays, "Rhop", i, float("nan")),
            "vz_m_s": component(arrays, "Vel", i, 2, 0.0),
            "boundnormal_z_m": component(arrays, "BoundNormal", i, 2, 0.0),
        })
    return rows


def layer_rows(point_data):
    grouped = {}
    for row in point_data:
        key = (row["part"], row["time_rel_s"], row["tv"], row["kind"], row["z_layer"])
        grouped.setdefault(key, []).append(row)
    rows = []
    for (part, time_rel_s, tv, kind, layer), vals in sorted(grouped.items()):
        out = {
            "part": part,
            "time_rel_s": time_rel_s,
            "tv": tv,
            "kind": kind,
            "z_layer": layer,
            "z_mean_m": mean(v["z_m"] for v in vals),
            "count": len(vals),
        }
        for name in (
            "sigma_eff_zz_kpa",
            "porepress_kpa",
            "porepress0_kpa",
            "excess_porepress_kpa",
            "sigma_total_zz_kpa",
            "rhop_kg_m3",
            "vz_m_s",
            "boundnormal_z_m",
        ):
            out[name] = mean(v[name] for v in vals)
        rows.append(out)
    return rows


def nearest_layer(rows, kind, target_layer):
    candidates = [r for r in rows if r["kind"] == kind]
    if not candidates:
        return None
    return min(candidates, key=lambda r: abs(r["z_layer"] - target_layer))


def interface_rows(layers):
    by_part = {}
    for row in layers:
        by_part.setdefault(row["part"], []).append(row)
    rows = []
    for part, vals in sorted(by_part.items()):
        fluid = nearest_layer(vals, "fluid", 1)
        bound = nearest_layer(vals, "bound", -1)
        if not fluid or not bound:
            continue
        out = {
            "part": part,
            "time_rel_s": fluid["time_rel_s"],
            "tv": fluid["tv"],
            "fluid_layer": fluid["z_layer"],
            "bound_layer": bound["z_layer"],
            "fluid_count": fluid["count"],
            "bound_count": bound["count"],
            "fluid_z_m": fluid["z_mean_m"],
            "bound_z_m": bound["z_mean_m"],
        }
        for name in (
            "sigma_eff_zz_kpa",
            "porepress_kpa",
            "porepress0_kpa",
            "excess_porepress_kpa",
            "sigma_total_zz_kpa",
            "rhop_kg_m3",
            "vz_m_s",
        ):
            out[f"fluid_{name}"] = fluid[name]
            out[f"bound_{name}"] = bound[name]
            out[f"bound_minus_fluid_{name}"] = bound[name] - fluid[name]
        out["fluid_theory_total_zz_kpa"] = -(
            2100.0 * GRAVITY * max(0.0, 1.0 - fluid["z_mean_m"])
        ) / 1000.0
        out["bound_theory_total_zz_kpa"] = -(
            2100.0 * GRAVITY * max(0.0, 1.0 - bound["z_mean_m"])
        ) / 1000.0
        out["fluid_total_minus_theory_kpa"] = (
            out["fluid_sigma_total_zz_kpa"] - out["fluid_theory_total_zz_kpa"]
        )
        out["bound_total_minus_theory_kpa"] = (
            out["bound_sigma_total_zz_kpa"] - out["bound_theory_total_zz_kpa"]
        )
        rows.append(out)
    return rows


def selected_parts(all_parts, rows, targets):
    if targets:
        by_tv = {r["part"]: r["tv"] for r in rows if r["kind"] == "fluid"}
        selected = []
        for target in targets:
            selected.append(min(all_parts, key=lambda p: abs(by_tv.get(p, float("inf")) - target)))
        return sorted(set(selected))
    return sorted(all_parts)


def make_interface_plot(rows, path, title):
    tv = [r["tv"] for r in rows]
    fig, axes = plt.subplots(4, 1, figsize=(12, 12), sharex=True, constrained_layout=True)

    axes[0].plot(tv, [r["fluid_sigma_eff_zz_kpa"] for r in rows], label="fluid sigma'_zz")
    axes[0].plot(tv, [r["bound_sigma_eff_zz_kpa"] for r in rows], label="bound sigma'_zz")
    axes[0].set_ylabel("sigma'_zz [kPa]")
    axes[0].legend()

    axes[1].plot(tv, [r["fluid_porepress_kpa"] for r in rows], label="fluid pw")
    axes[1].plot(tv, [r["bound_porepress_kpa"] for r in rows], label="bound pw")
    axes[1].set_ylabel("pw [kPa]")
    axes[1].legend()

    axes[2].plot(tv, [r["fluid_sigma_total_zz_kpa"] for r in rows], label="fluid sigma'-pw")
    axes[2].plot(tv, [r["bound_sigma_total_zz_kpa"] for r in rows], label="bound sigma'-pw")
    axes[2].plot(tv, [r["fluid_theory_total_zz_kpa"] for r in rows], "--", label="theory total at fluid layer")
    axes[2].set_ylabel("total zz [kPa]")
    axes[2].legend()

    axes[3].plot(tv, [r["bound_minus_fluid_sigma_eff_zz_kpa"] for r in rows], label="bound-fluid sigma'_zz")
    axes[3].plot(tv, [r["bound_minus_fluid_porepress_kpa"] for r in rows], label="bound-fluid pw")
    axes[3].plot(tv, [r["bound_minus_fluid_sigma_total_zz_kpa"] for r in rows], label="bound-fluid total")
    axes[3].set_xlabel("Tv")
    axes[3].set_ylabel("interface jump [kPa]")
    axes[3].legend()

    for ax in axes:
        ax.grid(True, alpha=0.25)
    fig.suptitle(title)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_profile_plot(rows, selected, path, title):
    fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True, constrained_layout=True)
    labels = [
        ("sigma_eff_zz_kpa", "sigma'_zz [kPa]"),
        ("porepress_kpa", "pw [kPa]"),
        ("sigma_total_zz_kpa", "sigma'_zz - pw [kPa]"),
    ]
    cmap = plt.get_cmap("viridis", max(1, len(selected)))
    for c, part in enumerate(selected):
        vals = [r for r in rows if r["part"] == part and r["z_layer"] <= 5]
        tv = vals[0]["tv"] if vals else float("nan")
        for ax, (name, xlabel) in zip(axes, labels):
            fluid = sorted((r for r in vals if r["kind"] == "fluid"), key=lambda r: r["z_mean_m"])
            bound = sorted((r for r in vals if r["kind"] == "bound"), key=lambda r: r["z_mean_m"])
            color = cmap(c)
            ax.plot([r[name] for r in fluid], [r["z_mean_m"] for r in fluid], "-", color=color, label=f"Tv={tv:.3f}")
            ax.plot([r[name] for r in bound], [r["z_mean_m"] for r in bound], "x", color=color)
            ax.set_xlabel(xlabel)
            ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("z [m]")
    axes[0].legend()
    fig.suptitle(title)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", required=True, type=Path)
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    parser.add_argument("--tout", required=True, type=float)
    parser.add_argument("--tmax", required=True, type=float)
    parser.add_argument("--tv-offset", required=True, type=float)
    parser.add_argument("--x-min", type=float, default=0.0)
    parser.add_argument("--x-max", type=float, default=0.1)
    parser.add_argument("--target-tv", type=float, nargs="*", default=[0.500, 0.520, 0.523, 0.540])
    args = parser.parse_args()

    args.figdir.mkdir(parents=True, exist_ok=True)
    fluid_files = sorted(args.particles.glob("PartFluid_*.vtk"), key=part_index)
    point_data = []
    for fluid_path in fluid_files:
        idx = part_index(fluid_path)
        bound_path = args.particles / f"PartBound_{idx:04d}.vtk"
        if not bound_path.exists():
            continue
        time_rel_s = min(args.tmax, idx * args.tout)
        tv = args.tv_offset + pp.CV_TERZAGHI * time_rel_s / (pp.H * pp.H)
        f_points, f_arrays = read_vtk_arrays(fluid_path)
        b_points, b_arrays = read_vtk_arrays(bound_path)
        point_data.extend(point_rows("fluid", f_points, f_arrays, idx, tv, time_rel_s, args.x_min, args.x_max))
        point_data.extend(point_rows("bound", b_points, b_arrays, idx, tv, time_rel_s, args.x_min, args.x_max))

    layers = layer_rows(point_data)
    interface = interface_rows(layers)
    selected = selected_parts({r["part"] for r in layers}, layers, args.target_tv)

    layer_fields = list(layers[0].keys()) if layers else []
    interface_fields = list(interface[0].keys()) if interface else []
    write_csv(args.figdir / "mdbc_stress_pore_layers.csv", layers, layer_fields)
    write_csv(args.figdir / "mdbc_stress_pore_interface.csv", interface, interface_fields)

    if interface:
        make_interface_plot(
            interface,
            args.figdir / "mdbc_stress_pore_interface.png",
            f"{args.case}: bottom fluid and mDBC inner-layer split",
        )
    if layers and selected:
        make_profile_plot(
            layers,
            selected,
            args.figdir / "mdbc_stress_pore_profiles.png",
            f"{args.case}: effective stress, pore pressure, and total stress near bottom",
        )


if __name__ == "__main__":
    main()
