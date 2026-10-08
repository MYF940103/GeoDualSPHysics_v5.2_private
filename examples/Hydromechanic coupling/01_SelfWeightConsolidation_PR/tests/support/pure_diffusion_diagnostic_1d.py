from pathlib import Path
import argparse
import csv
import math
import sys

import matplotlib.pyplot as plt
import numpy as np


CASE_ROOT = Path(__file__).resolve().parents[2]
ROOT_SUPPORT = CASE_ROOT / "support"
if str(ROOT_SUPPORT) not in sys.path:
    sys.path.insert(0, str(ROOT_SUPPORT))

import postprocess_self_weight_consolidation as pp


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fval(row, key):
    return float(row[key])


def group_profiles(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(float(row["target_Tv"]), []).append(row)
    return grouped


def theory_excess_kpa(z, tv):
    return pp.terzaghi_excess(z, tv * pp.H * pp.H / pp.CV_TERZAGHI) / 1000.0


def undrained_excess_kpa(z):
    return pp.undrained_excess(z) / 1000.0


def rms(values):
    values = list(values)
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else float("nan")


class PureDiffusion1D:
    """Cell-centered 1D diffusion with bottom no-flow and top drained."""

    def __init__(self, z, u0_kpa, cv):
        self.z = np.asarray(z, dtype=float)
        self.u0 = np.asarray(u0_kpa, dtype=float)
        self.cv = float(cv)
        self.dz = float(np.median(np.diff(self.z)))
        self.matrix = self._build_matrix(len(self.z), self.dz)
        eigval, eigvec = np.linalg.eig(self.matrix)
        self.eigval = eigval
        self.eigvec = eigvec
        self.coeff = np.linalg.solve(eigvec, self.u0)

    @staticmethod
    def _build_matrix(n, dz):
        a = np.zeros((n, n), dtype=float)
        inv_dz2 = 1.0 / (dz * dz)
        # Bottom boundary: no flux.
        a[0, 0] = -inv_dz2
        a[0, 1] = inv_dz2
        # Interior.
        for i in range(1, n - 1):
            a[i, i - 1] = inv_dz2
            a[i, i] = -2.0 * inv_dz2
            a[i, i + 1] = inv_dz2
        # Top boundary: drained u(H)=0 at a half-cell above the top center.
        a[n - 1, n - 2] = inv_dz2
        a[n - 1, n - 1] = -3.0 * inv_dz2
        return a

    def values_at_tv(self, tv):
        time_s = float(tv) * pp.H * pp.H / pp.CV_TERZAGHI
        decay = np.exp(self.cv * self.eigval * time_s)
        values = self.eigvec @ (decay * self.coeff)
        return np.real_if_close(values, tol=1000).real

    def value_at_z_tv(self, z, tv):
        return float(np.interp(z, self.z, self.values_at_tv(tv)))


def build_initial_profiles(profile_rows):
    grouped = group_profiles(profile_rows)
    if 0.0 not in grouped:
        raise RuntimeError("The profile CSV does not contain target_Tv=0.0 rows")
    initial = sorted(grouped[0.0], key=lambda row: fval(row, "z_m"))
    z = [fval(row, "z_m") for row in initial]
    sph_initial = [fval(row, "excess_sph_kPa") for row in initial]
    ideal_initial = [undrained_excess_kpa(zi) for zi in z]
    return z, sph_initial, ideal_initial, grouped


def compare_profiles(grouped, pure_sph, pure_ideal):
    rows = []
    for target_tv in sorted(grouped):
        selected = sorted(grouped[target_tv], key=lambda row: fval(row, "z_m"))
        if not selected:
            continue
        actual_tv = fval(selected[0], "actual_Tv")
        z = [fval(row, "z_m") for row in selected]
        sph = [fval(row, "excess_sph_kPa") for row in selected]
        theory = [fval(row, "excess_theory_kPa") for row in selected]
        same_initial = [pure_sph.value_at_z_tv(zi, actual_tv) for zi in z]
        ideal_initial = [pure_ideal.value_at_z_tv(zi, actual_tv) for zi in z]
        rows.append({
            "target_Tv": target_tv,
            "actual_Tv": actual_tv,
            "rms_full_sph_vs_theory_kPa": rms(a - b for a, b in zip(sph, theory)),
            "rms_pure_same_initial_vs_theory_kPa": rms(a - b for a, b in zip(same_initial, theory)),
            "rms_pure_ideal_initial_vs_theory_kPa": rms(a - b for a, b in zip(ideal_initial, theory)),
            "rms_full_sph_vs_pure_same_initial_kPa": rms(a - b for a, b in zip(sph, same_initial)),
            "bottom_full_sph_kPa": sph[0],
            "bottom_theory_kPa": theory[0],
            "bottom_pure_same_initial_kPa": same_initial[0],
            "bottom_pure_ideal_initial_kPa": ideal_initial[0],
        })
    return rows


def compare_bottom(bottom_rows, pure_sph, pure_ideal):
    rows = []
    for row in bottom_rows:
        tv = fval(row, "Tv")
        z = fval(row, "bottom_z_m")
        sph = fval(row, "bottom_excess_sph_kPa")
        theory = fval(row, "bottom_excess_theory_kPa")
        same_initial = pure_sph.value_at_z_tv(z, tv)
        ideal_initial = pure_ideal.value_at_z_tv(z, tv)
        rows.append({
            "time_s": fval(row, "time_s"),
            "Tv": tv,
            "bottom_z_m": z,
            "full_sph_kPa": sph,
            "theory_kPa": theory,
            "pure_same_initial_kPa": same_initial,
            "pure_ideal_initial_kPa": ideal_initial,
            "full_minus_theory_kPa": sph - theory,
            "pure_same_initial_minus_theory_kPa": same_initial - theory,
            "full_minus_pure_same_initial_kPa": sph - same_initial,
        })
    return rows


def plot_diagnostic(outdir, case, grouped, bottom_diag, profile_diag, pure_sph, pure_ideal):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.1), constrained_layout=True)
    ax_profile, ax_bottom, ax_error = axes

    colors = plt.cm.viridis(np.linspace(0.0, 1.0, max(1, len(grouped))))
    for color, target_tv in zip(colors, sorted(grouped)):
        selected = sorted(grouped[target_tv], key=lambda row: fval(row, "z_m"))
        actual_tv = fval(selected[0], "actual_Tv")
        z = np.array([fval(row, "z_m") for row in selected])
        sph = np.array([fval(row, "excess_sph_kPa") for row in selected])
        theory = np.array([fval(row, "excess_theory_kPa") for row in selected])
        pure = np.array([pure_sph.value_at_z_tv(zi, actual_tv) for zi in z])
        label = f"Tv={actual_tv:.3f}"
        ax_profile.plot(sph, z / pp.H, color=color, linewidth=1.25, label=f"full {label}")
        ax_profile.plot(pure, z / pp.H, "--", color=color, linewidth=0.9, alpha=0.9)
        ax_profile.plot(theory, z / pp.H, ":", color=color, linewidth=0.85, alpha=0.8)

    ax_profile.set_xlabel("Excess pore pressure [kPa]")
    ax_profile.set_ylabel("z/H")
    ax_profile.set_title("Profiles: full / pure / theory")
    ax_profile.grid(True, alpha=0.25)
    ax_profile.legend(fontsize=7)

    tv = [row["Tv"] for row in bottom_diag]
    ax_bottom.plot(tv, [row["theory_kPa"] for row in bottom_diag], "k--", label="theory")
    ax_bottom.plot(tv, [row["pure_ideal_initial_kPa"] for row in bottom_diag], color="0.55", linestyle=":", label="pure, ideal init")
    ax_bottom.plot(tv, [row["pure_same_initial_kPa"] for row in bottom_diag], "b-", label="pure, SPH init")
    ax_bottom.plot(tv, [row["full_sph_kPa"] for row in bottom_diag], "r-", label="full coupled SPH")
    ax_bottom.set_xlabel("Tv")
    ax_bottom.set_ylabel("Bottom excess [kPa]")
    ax_bottom.set_title("Bottom dissipation")
    ax_bottom.grid(True, alpha=0.25)
    ax_bottom.legend(fontsize=8)

    ax_error.plot(tv, [row["full_minus_theory_kPa"] for row in bottom_diag], "r-", label="full - theory")
    ax_error.plot(tv, [row["pure_same_initial_minus_theory_kPa"] for row in bottom_diag], "b-", label="pure(SPH init) - theory")
    ax_error.plot(tv, [row["full_minus_pure_same_initial_kPa"] for row in bottom_diag], "m-", label="full - pure(SPH init)")
    ax_error.axhline(0.0, color="k", linewidth=0.8)
    ax_error.set_xlabel("Tv")
    ax_error.set_ylabel("Bottom difference [kPa]")
    ax_error.set_title("Bottom error split")
    ax_error.grid(True, alpha=0.25)
    ax_error.legend(fontsize=8)

    fig.suptitle(case)
    figpath = outdir / "scenario2_pure_diffusion_diagnostic.png"
    fig.savefig(figpath, dpi=220)
    plt.close(fig)

    fig2, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
    ax.plot([row["actual_Tv"] for row in profile_diag], [row["rms_full_sph_vs_theory_kPa"] for row in profile_diag], "o-", label="full vs theory")
    ax.plot([row["actual_Tv"] for row in profile_diag], [row["rms_pure_same_initial_vs_theory_kPa"] for row in profile_diag], "o-", label="pure(SPH init) vs theory")
    ax.plot([row["actual_Tv"] for row in profile_diag], [row["rms_full_sph_vs_pure_same_initial_kPa"] for row in profile_diag], "o-", label="full vs pure(SPH init)")
    ax.set_xlabel("Tv")
    ax.set_ylabel("Profile RMS [kPa]")
    ax.set_title("Pure-diffusion error decomposition")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig2path = outdir / "scenario2_pure_diffusion_rms.png"
    fig2.savefig(fig2path, dpi=220)
    plt.close(fig2)
    return figpath, fig2path


def write_summary(path, case, profile_diag, bottom_diag):
    last = bottom_diag[-1]
    tv_targets = [0.1, 0.5, 1.0]
    nearest = []
    for target in tv_targets:
        nearest.append(min(bottom_diag, key=lambda row: abs(row["Tv"] - target)))

    with path.open("w") as f:
        f.write(f"# Pure diffusion diagnostic: {case}\n\n")
        f.write("This diagnostic evolves the numerical initial excess pore-pressure profile with a 1D diffusion equation only.\n")
        f.write("Boundary conditions are bottom no-flow and top drained. It does not update displacement, strain, stress, porosity, or mDBC state.\n\n")
        f.write("## Bottom comparison\n\n")
        for row in nearest:
            f.write(
                f"- Tv `{row['Tv']:.3f}`: theory `{row['theory_kPa']:.4f}` kPa, "
                f"pure(SPH init) `{row['pure_same_initial_kPa']:.4f}` kPa, "
                f"full coupled `{row['full_sph_kPa']:.4f}` kPa, "
                f"full-pure `{row['full_minus_pure_same_initial_kPa']:.4f}` kPa.\n"
            )
        f.write(
            f"- Final Tv `{last['Tv']:.3f}`: theory `{last['theory_kPa']:.4f}` kPa, "
            f"pure(SPH init) `{last['pure_same_initial_kPa']:.4f}` kPa, "
            f"full coupled `{last['full_sph_kPa']:.4f}` kPa.\n\n"
        )
        f.write("## Profile RMS\n\n")
        for row in profile_diag:
            f.write(
                f"- Tv `{row['actual_Tv']:.3f}`: full-theory `{row['rms_full_sph_vs_theory_kPa']:.4f}` kPa, "
                f"pure-theory `{row['rms_pure_same_initial_vs_theory_kPa']:.4f}` kPa, "
                f"full-pure `{row['rms_full_sph_vs_pure_same_initial_kPa']:.4f}` kPa.\n"
            )
        f.write("\n## Interpretation\n\n")
        f.write("If pure(SPH init) stays near theory while full coupled SPH lags, the late-time error is not mainly caused by the inherited initial pore-pressure profile.\n")
        f.write("It then points to the coupled update path: effective storage/compressibility, stress-pore coupling, mDBC/shepard interaction, or an SPH diffusion-operator coefficient mismatch.\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--figdir", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    profile_rows = read_csv(args.figdir / "scenario2_profiles_by_tv.csv")
    bottom_rows = read_csv(args.figdir / "scenario2_bottom_dissipation.csv")
    z, sph_initial, ideal_initial, grouped = build_initial_profiles(profile_rows)

    pure_sph = PureDiffusion1D(z, sph_initial, pp.CV_TERZAGHI)
    pure_ideal = PureDiffusion1D(z, ideal_initial, pp.CV_TERZAGHI)
    profile_diag = compare_profiles(grouped, pure_sph, pure_ideal)
    bottom_diag = compare_bottom(bottom_rows, pure_sph, pure_ideal)

    profile_csv = args.outdir / "scenario2_pure_diffusion_profile_diagnostic.csv"
    bottom_csv = args.outdir / "scenario2_pure_diffusion_bottom_diagnostic.csv"
    write_csv(profile_csv, profile_diag)
    write_csv(bottom_csv, bottom_diag)

    figpath, fig2path = plot_diagnostic(args.outdir, args.case, grouped, bottom_diag, profile_diag, pure_sph, pure_ideal)
    summary = args.outdir / "scenario2_pure_diffusion_diagnostic_summary.md"
    write_summary(summary, args.case, profile_diag, bottom_diag)

    print(f"Saved {profile_csv}")
    print(f"Saved {bottom_csv}")
    print(f"Saved {figpath}")
    print(f"Saved {fig2path}")
    print(f"Saved {summary}")


if __name__ == "__main__":
    main()
