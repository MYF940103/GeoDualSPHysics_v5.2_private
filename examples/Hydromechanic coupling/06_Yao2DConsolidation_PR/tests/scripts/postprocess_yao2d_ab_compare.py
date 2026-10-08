from pathlib import Path
import csv
import importlib.util

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
SCRIPTS_DIR = SCRIPT_DIR if SCRIPT_DIR.name == "scripts" else ROOT
OUTPUTS_DIR = ROOT / "outputs"
FIGURES_DIR = ROOT / "figures"
A_OUT = OUTPUTS_DIR / "CaseYao2DConsolidation_PR_gpu2s_dp01_damp002_out"
B_OUT = OUTPUTS_DIR / "CaseYao2DConsolidation_PR_gpu02s_dp01_damp002_extrap_out"
PARTS = ((5, 0.1), (10, 0.2))

spec = importlib.util.spec_from_file_location("shortpp", SCRIPTS_DIR / "postprocess_yao2d_short.py")
shortpp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shortpp)


def read_part(out_dir, prefix, part):
    return shortpp.read_part(out_dir, prefix, part)


def build_initial_pairs(out_dir):
    pts, arrays = read_part(out_dir, "PartFluid", 0)
    idp = arrays["Idp"].astype(int)
    key_to_id = {
        (round(float(x), 5), round(float(z), 5)): int(pid)
        for pid, x, z in zip(idp, pts[:, 0], pts[:, 2])
    }
    pairs = []
    for pid, x, z in zip(idp, pts[:, 0], pts[:, 2]):
        if x < -1e-8:
            rid = key_to_id.get((round(float(-x), 5), round(float(z), 5)))
            if rid is not None:
                pairs.append((int(pid), rid, float(x), float(z)))
    return pairs


def summarize_case(label, out_dir, pairs, part, time_s):
    pts, arrays = read_part(out_dir, "PartFluid", part)
    idp = arrays["Idp"].astype(int)
    idmap = {int(v): i for i, v in enumerate(idp)}
    x, z = pts[:, 0], pts[:, 2]
    p = arrays["PorePress"]
    epwp = arrays["ExcessPorePress"]
    loadz = arrays["HydroMechLoadAce"][:, 2]
    fstype = arrays["FSType"].astype(int)

    top_strip = (np.abs(x) <= 3.05) & (z > 9.95)
    next_strip = (np.abs(x) <= 3.05) & (z > 9.85) & (z <= 9.95)
    open_top = (np.abs(x) > 3.05) & (z > 9.95)
    loaded = np.abs(loadz) > 1e-12

    pdiff = []
    top_pdiff = []
    signed = []
    top_signed = []
    for lid, rid, x0, z0 in pairs:
        il, ir = idmap[lid], idmap[rid]
        d = float(p[ir] - p[il])
        pdiff.append(abs(d))
        signed.append(d)
        if z0 > 9.85 and abs(x0) <= 3.05:
            top_pdiff.append(abs(d))
            top_signed.append(d)

    bpts, barrays = read_part(out_dir, "PartBound", part)
    btype_vals, btype_counts = np.unique(barrays["Type"].astype(int), return_counts=True)
    bmk_vals, bmk_counts = np.unique(barrays["Mk"].astype(int), return_counts=True)

    def stats(mask, arr):
        if not np.any(mask):
            return np.nan, np.nan, np.nan, 0
        vals = arr[mask]
        return float(np.min(vals)), float(np.max(vals)), float(np.mean(vals)), int(np.count_nonzero(mask))

    top_min, top_max, top_mean, top_n = stats(top_strip, p)
    next_min, next_max, next_mean, next_n = stats(next_strip, p)
    loaded_min, loaded_max, loaded_mean, loaded_n = stats(loaded, p)
    return {
        "case": label,
        "part": part,
        "time_s": time_s,
        "fluid_np": len(pts),
        "bound_np": len(bpts),
        "bound_type_counts": ";".join(f"{v}:{c}" for v, c in zip(btype_vals, btype_counts)),
        "bound_mk_counts": ";".join(f"{v}:{c}" for v, c in zip(bmk_vals, bmk_counts)),
        "pore_min_pa": float(np.min(p)),
        "pore_max_pa": float(np.max(p)),
        "epwp_min_pa": float(np.min(epwp)),
        "epwp_max_pa": float(np.max(epwp)),
        "loaded_count": loaded_n,
        "loaded_pore_min_pa": loaded_min,
        "loaded_pore_max_pa": loaded_max,
        "loaded_pore_mean_pa": loaded_mean,
        "loaded_zero_count": int(np.count_nonzero(loaded & (np.abs(p) < 1e-8))),
        "top_strip_count": top_n,
        "top_strip_pore_min_pa": top_min,
        "top_strip_pore_max_pa": top_max,
        "top_strip_pore_mean_pa": top_mean,
        "top_strip_fstype_values": ";".join(str(v) for v in sorted(set(fstype[top_strip].tolist()))) if top_n else "",
        "next_strip_count": next_n,
        "next_strip_pore_min_pa": next_min,
        "next_strip_pore_max_pa": next_max,
        "next_strip_pore_mean_pa": next_mean,
        "open_top_absmax_pa": float(np.max(np.abs(p[open_top]))) if np.any(open_top) else np.nan,
        "mirror_mean_abs_pa": float(np.mean(pdiff)),
        "mirror_max_abs_pa": float(np.max(pdiff)),
        "mirror_signed_mean_pa": float(np.mean(signed)),
        "top_mirror_mean_abs_pa": float(np.mean(top_pdiff)) if top_pdiff else np.nan,
        "top_mirror_max_abs_pa": float(np.max(top_pdiff)) if top_pdiff else np.nan,
        "top_mirror_signed_mean_pa": float(np.mean(top_signed)) if top_signed else np.nan,
    }


def write_figures(rows_by_case, fig_dir):
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), constrained_layout=True)
    plot_order = []
    for part, time_s in PARTS:
        for label, out_dir in rows_by_case.items():
            plot_order.append((label, out_dir, part, time_s))
    for ax, (label, out_dir, part, time_s) in zip(axes.flat, plot_order):
        pts, arrays = read_part(out_dir, "PartFluid", part)
        x, z = pts[:, 0], pts[:, 2]
        p = arrays["PorePress"] / 1000.0
        tri = mtri.Triangulation(x, z)
        cf = ax.tricontourf(tri, np.clip(p, 0, 5), levels=np.linspace(0, 5, 21), cmap="turbo", extend="max")
        ax.plot([-3, 3], [10, 10], color="black", lw=1.8)
        ax.set_xlim(-10, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{label}, t={time_s:g} s")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")
    fig.colorbar(cf, ax=axes, shrink=0.82, pad=0.02).set_label("PorePress (kPa), clipped 0-5")
    fig.savefig(fig_dir / "yao2d_ab_contours_0p1_0p2s.png", dpi=240)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.0), constrained_layout=True)
    for col, (part, time_s) in enumerate(PARTS):
        for label, out_dir in rows_by_case.items():
            pts, arrays = read_part(out_dir, "PartFluid", part)
            x, z = pts[:, 0], pts[:, 2]
            p = arrays["PorePress"] / 1000.0
            top = (np.abs(x) <= 3.05) & (z > 9.95)
            nxt = (np.abs(x) <= 3.05) & (z > 9.85) & (z <= 9.95)
            axes[0, col].plot(x[top], p[top], ".", label=label, ms=4)
            axes[1, col].plot(x[nxt], p[nxt], ".", label=label, ms=4)
        axes[0, col].set_title(f"top contact row, t={time_s:g} s")
        axes[1, col].set_title(f"next row, t={time_s:g} s")
        for row in range(2):
            axes[row, col].set_xlim(-3.2, 3.2)
            axes[row, col].set_xlabel("x (m)")
            axes[row, col].set_ylabel("PorePress (kPa)")
            axes[row, col].grid(True, alpha=0.25)
            axes[row, col].legend()
    fig.savefig(fig_dir / "yao2d_ab_top_next_profiles.png", dpi=240)
    plt.close(fig)


def main():
    if not A_OUT.exists():
        raise SystemExit(f"Missing A output: {A_OUT}")
    if not B_OUT.exists():
        raise SystemExit(f"Missing B output: {B_OUT}")
    pairs = build_initial_pairs(A_OUT)
    cases = {
        "A_no_extrap": A_OUT,
        "B_extrap": B_OUT,
    }
    rows = []
    for label, out_dir in cases.items():
        for part, time_s in PARTS:
            rows.append(summarize_case(label, out_dir, pairs, part, time_s))

    fig_dir = FIGURES_DIR / "figures_gpu02s_ab_compare"
    write_figures(cases, fig_dir)
    metrics = fig_dir / "yao2d_ab_compare_metrics.csv"
    with metrics.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(metrics)
    for row in rows:
        print(row)
    print(fig_dir / "yao2d_ab_contours_0p1_0p2s.png")
    print(fig_dir / "yao2d_ab_top_next_profiles.png")


if __name__ == "__main__":
    main()
