from pathlib import Path
import argparse
import csv
import math
import sys

import matplotlib.pyplot as plt


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
if str(ROOT_SUPPORT) not in sys.path:
    sys.path.insert(0, str(ROOT_SUPPORT))

import postprocess_self_weight_consolidation as pp


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def val(row, key):
    return float(row[key])


def theory_excess_kpa(z, tv, alpha=1.0):
    t_rel = alpha * tv * pp.H * pp.H / pp.CV_TERZAGHI
    return pp.terzaghi_excess(z, t_rel) / 1000.0


def rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


def fit_profile_alpha(rows, tv, alpha_min=0.5, alpha_max=1.5, step=0.001):
    best = None
    best_amp = None
    nstep = int(round((alpha_max - alpha_min) / step))
    for i in range(nstep + 1):
        alpha = alpha_min + i * step
        sph = [val(r, "excess_sph_kPa") for r in rows]
        th = [theory_excess_kpa(val(r, "z_m"), tv, alpha) for r in rows]
        err = rms([a - b for a, b in zip(sph, th)])
        den = sum(v * v for v in th)
        amp = sum(a * b for a, b in zip(sph, th)) / den if den else float("nan")
        err_amp = rms([a - amp * b for a, b in zip(sph, th)])
        if best is None or err < best[0]:
            best = (err, alpha)
        if best_amp is None or err_amp < best_amp[0]:
            best_amp = (err_amp, alpha, amp)
    return best, best_amp


def bottom_theory_kpa(z, tv, alpha=1.0):
    return theory_excess_kpa(z, tv, alpha)


def fit_bottom_alpha(rows, tv_min=0.02, tv_max=1.0, alpha_min=0.5, alpha_max=1.5, step=0.001):
    selected = [r for r in rows if tv_min <= val(r, "Tv") <= tv_max]
    best = None
    nstep = int(round((alpha_max - alpha_min) / step))
    for i in range(nstep + 1):
        alpha = alpha_min + i * step
        err = rms([
            val(r, "bottom_excess_sph_kPa") - bottom_theory_kpa(val(r, "bottom_z_m"), val(r, "Tv"), alpha)
            for r in selected
        ])
        if best is None or err < best[0]:
            best = (err, alpha)
    return best


def equivalent_bottom_tv(row, tv_max=2.0):
    sph = val(row, "bottom_excess_sph_kPa")
    z = val(row, "bottom_z_m")
    # Dense but cheap enough for diagnostics; monotone enough in this range.
    best_diff = float("inf")
    best_tv = 0.0
    for i in range(int(tv_max / 0.001) + 1):
        tv = i * 0.001
        diff = abs(bottom_theory_kpa(z, tv) - sph)
        if diff < best_diff:
            best_diff = diff
            best_tv = tv
    return best_tv


def group_profiles(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["target_Tv"], []).append(row)
    return {float(k): v for k, v in grouped.items()}


def write_rows(path, fieldnames, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    profiles = group_profiles(read_csv(args.figdir / "scenario2_profiles_by_tv.csv"))
    bottom_rows = read_csv(args.figdir / "scenario2_bottom_dissipation.csv")

    profile_diag = []
    for target_tv in sorted(profiles):
        rows = profiles[target_tv]
        actual_tv = val(rows[0], "actual_Tv")
        best, best_amp = fit_profile_alpha(rows, actual_tv)
        theory_err = rms([val(r, "excess_sph_kPa") - val(r, "excess_theory_kPa") for r in rows])
        initial_amp = float("nan")
        if actual_tv == 0.0:
            den = sum(val(r, "excess_theory_kPa") ** 2 for r in rows)
            initial_amp = sum(val(r, "excess_sph_kPa") * val(r, "excess_theory_kPa") for r in rows) / den if den else float("nan")
        profile_diag.append({
            "target_Tv": target_tv,
            "actual_Tv": actual_tv,
            "rms_at_nominal_cv_kPa": theory_err,
            "best_cv_scale_fixed_amplitude": best[1],
            "best_rms_fixed_amplitude_kPa": best[0],
            "best_cv_scale_with_amplitude": best_amp[1],
            "best_amplitude_scale": best_amp[2],
            "best_rms_with_amplitude_kPa": best_amp[0],
            "initial_profile_amplitude_scale": initial_amp,
        })

    bottom_diag = []
    for row in bottom_rows:
        tv = val(row, "Tv")
        equiv_tv = equivalent_bottom_tv(row)
        bottom_diag.append({
            "time_s": val(row, "time_s"),
            "Tv": tv,
            "bottom_excess_sph_kPa": val(row, "bottom_excess_sph_kPa"),
            "bottom_excess_theory_kPa": val(row, "bottom_excess_theory_kPa"),
            "bottom_error_kPa": val(row, "bottom_excess_sph_kPa") - val(row, "bottom_excess_theory_kPa"),
            "equivalent_theory_Tv": equiv_tv,
            "equivalent_cv_scale": (equiv_tv / tv if tv > 0 else float("nan")),
        })

    global_fits = [
        ("bottom_Tv_0p02_1p00", 0.02, 1.0, *fit_bottom_alpha(bottom_rows, 0.02, 1.0)),
        ("bottom_Tv_0p05_0p50", 0.05, 0.5, *fit_bottom_alpha(bottom_rows, 0.05, 0.5)),
        ("bottom_Tv_0p50_1p00", 0.5, 1.0, *fit_bottom_alpha(bottom_rows, 0.5, 1.0)),
    ]
    global_rows = []
    for name, tvmin, tvmax, rms_fit, alpha_fit in global_fits:
        global_rows.append({
            "fit_range": name,
            "Tv_min": tvmin,
            "Tv_max": tvmax,
            "best_rms_kPa": rms_fit,
            "best_cv_scale": alpha_fit,
        })

    write_rows(args.outdir / "scenario2_profile_cv_fit.csv", list(profile_diag[0].keys()), profile_diag)
    write_rows(args.outdir / "scenario2_bottom_equivalent_tv.csv", list(bottom_diag[0].keys()), bottom_diag)
    write_rows(args.outdir / "scenario2_bottom_cv_global_fit.csv", list(global_rows[0].keys()), global_rows)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
    prof_nonzero = [r for r in profile_diag if r["actual_Tv"] > 0]
    axes[0].plot([r["actual_Tv"] for r in prof_nonzero], [r["best_cv_scale_fixed_amplitude"] for r in prof_nonzero], "o-", label="profile fit")
    axes[0].plot([r["Tv"] for r in bottom_diag if r["Tv"] > 0], [r["equivalent_cv_scale"] for r in bottom_diag if r["Tv"] > 0], ".", alpha=0.35, label="bottom equivalent")
    axes[0].axhline(1.0, color="k", linewidth=0.8)
    axes[0].set_xlabel("Tv")
    axes[0].set_ylabel("Equivalent cv / analytical cv")
    axes[0].set_title("Diffusion speed")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    axes[1].plot([r["actual_Tv"] for r in profile_diag], [r["rms_at_nominal_cv_kPa"] for r in profile_diag], "o-", label="nominal cv")
    axes[1].plot([r["actual_Tv"] for r in profile_diag], [r["best_rms_fixed_amplitude_kPa"] for r in profile_diag], "o-", label="best cv")
    axes[1].plot([r["actual_Tv"] for r in profile_diag], [r["best_rms_with_amplitude_kPa"] for r in profile_diag], "o-", label="best cv + amplitude")
    axes[1].set_xlabel("Tv")
    axes[1].set_ylabel("Profile RMS [kPa]")
    axes[1].set_title("Profile fit quality")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()

    axes[2].plot([r["Tv"] for r in bottom_diag], [r["bottom_excess_theory_kPa"] for r in bottom_diag], "k--", label="theory")
    axes[2].plot([r["Tv"] for r in bottom_diag], [r["bottom_excess_sph_kPa"] for r in bottom_diag], label="SPH")
    for row in global_rows:
      alpha = row["best_cv_scale"]
      axes[2].plot(
          [r["Tv"] for r in bottom_diag],
          [bottom_theory_kpa(val(r, "bottom_z_m"), val(r, "Tv"), alpha) for r in bottom_rows],
          linewidth=1.0,
          label=f"theory x{alpha:.3f} {row['fit_range']}",
      )
    axes[2].set_xlabel("Tv")
    axes[2].set_ylabel("Bottom excess [kPa]")
    axes[2].set_title("Bottom curve")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(fontsize=7)

    fig.suptitle(args.case)
    figpath = args.outdir / "scenario2_diffusion_speed_diagnostic.png"
    fig.savefig(figpath, dpi=220)
    plt.close(fig)

    md = args.outdir / "scenario2_diffusion_speed_diagnostic_summary.md"
    with md.open("w") as f:
        f.write(f"# Scenario 2 diffusion speed diagnostic: {args.case}\n\n")
        f.write("## Bottom global cv fits\n\n")
        for row in global_rows:
            f.write(f"- `{row['fit_range']}`: best `cv/cv_ref = {row['best_cv_scale']:.3f}`, RMS = `{row['best_rms_kPa']:.4f} kPa`.\n")
        f.write("\n## Profile cv fits\n\n")
        for row in profile_diag:
            f.write(
                f"- Tv `{row['actual_Tv']:.3f}`: nominal RMS `{row['rms_at_nominal_cv_kPa']:.4f} kPa`, "
                f"best fixed-amplitude `cv/cv_ref={row['best_cv_scale_fixed_amplitude']:.3f}` "
                f"with RMS `{row['best_rms_fixed_amplitude_kPa']:.4f} kPa`, "
                f"best amplitude `{row['best_amplitude_scale']:.3f}`.\n"
            )
        f.write("\nInterpretation: fixed-amplitude `cv/cv_ref < 1` means the numerical result is lagging the analytical Terzaghi dissipation at that stage.\n")

    print(f"Saved {figpath}")
    print(f"Saved {args.outdir / 'scenario2_profile_cv_fit.csv'}")
    print(f"Saved {args.outdir / 'scenario2_bottom_equivalent_tv.csv'}")
    print(f"Saved {args.outdir / 'scenario2_bottom_cv_global_fit.csv'}")
    print(f"Saved {md}")


if __name__ == "__main__":
    main()
