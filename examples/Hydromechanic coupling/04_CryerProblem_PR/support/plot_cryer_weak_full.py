"""Compare a reviewed weak Cryer full run with retained u-pw, dynamic and P3 data.

No solver or native BI4 decoder is called. The frozen reviewer must run first.
Default: comparison figures/CSVs, then all saved material VTKs. Completed figures
are verified and reused on resume; --particles-only skips plotting. Existing
verified VTKs are never replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plot_cryer_formal_four_nu_r1 import Reference

CASE = Path(__file__).resolve().parents[1]
FORMAL = CASE / "figures/formal_validation"
TESTS = CASE / "tests/figures"
DT, TD, N, R, Q = 2.**-19, 2.**-7, 37173, .05, 10000.
LABELS = {
    "weak_full": "Weak 3D, full saved states",
    "weak_peak": "Weak 3D, retained dense peak",
    "u_pw": "Retained u-pw, finite Kw",
    "dynamic": "Retained dynamic, finite Kw (peak only)",
    "p3": "Retained P3 (peak only)",
}
COLORS = dict(weak_full="#167b99", weak_peak="#167b99", u_pw="#be6625",
              dynamic="#738a36", p3="#96528a")


def need(ok, text):
    if not ok:
        raise ValueError(text)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path):
    return pd.read_csv(path, float_precision="round_trip")


def binding(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def write_json(path, value):
    with path.open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def reviewed(output, package):
    """Reuse the successful frozen all-state review; do not repeat its native read."""
    report = read_json(output / "review/review.json")
    seal = read_json(output / "server_run.json")
    hist = read_csv(output / "review/actual_vs_theory.csv")
    clock = read_csv(output / "actual_clock.csv")
    need(report["mode"] == seal["mode"] == "full" and report["full_cycle_measured"],
         "A completed full native review is required")
    need(seal["package"].lower() == binding(package / "manifest.json")["sha256"],
         "The reviewed output used a different frozen package")
    need((output / "complete.txt").read_text().strip() == "full" and
         len(hist) == report["frames"] == 269 and int(hist.step.iloc[-1]) == report["steps"] == 481685,
         "Incomplete full-cycle review")
    need(np.array_equal(hist.step, clock.step) and np.array_equal(hist.time_s, clock.time_s) and
         np.array_equal(hist.time_s, hist.step * DT) and np.array_equal(hist.tau_s, hist.time_s - TD),
         "Review and actual saved clocks differ")
    need(hist.step.is_unique and np.all(np.diff(hist.step) > 0), "Repeated or unsorted actual states")
    need(hist.center18_Pa.notna().all() and report["native_materials"] == N and
         report["drained_materials"] == 5153, "Unexpected material reduction")
    return hist, report, seal


def centre_series(frame, key, pressure, theory, source, reference):
    need(frame.time_s.is_unique and np.isfinite(frame.time_s).all(), "Bad saved clocks: " + key)
    out = pd.DataFrame(dict(series=key, time_s=frame.time_s, tau_s=frame.time_s - TD,
                            pressure_Pa=frame[pressure], reference_Pa=theory))
    ref = Reference(.3, finite=False)
    out["Tv"] = out.tau_s * ref.legacy_cv / R**2
    out["reference"] = reference
    out["source"] = str(source.relative_to(CASE))
    return out


def comparisons(hist, package, output):
    weak_source = output / "review/actual_vs_theory.csv"
    old_source = FORMAL / "cryer_formal_four_nu_r1_native.csv"
    dynamic_source = TESTS / "upl_cryer_freebody_peak_review_r1_history.csv"
    p3_source = TESTS / "cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv"
    surface_source = TESTS / "cryer_true_surface_old_r1.csv"
    dense_sources = [package / ("inputs/" + kind + "_history.csv") for kind in ("open", "peak")]
    old = read_csv(old_source)
    old = old[np.isclose(old.nu, .3)].reset_index(drop=True)
    dynamic = read_csv(dynamic_source)
    dynamic = dynamic[dynamic.series == "current_upl_GPU"].reset_index(drop=True)
    p3 = read_csv(p3_source)
    dense = pd.concat([read_csv(dense_sources[0]), read_csv(dense_sources[1]).iloc[1:]], ignore_index=True)
    need(dense.step.is_unique and np.array_equal(dense.time_s, dense.step * DT), "Dense peak seam or clock")
    ref = Reference(.3, finite=False)
    entries = [
        centre_series(hist, "weak_full", "center18_Pa", hist.M0_center18_Pa,
                      weak_source, "M0; g=9.81, r0/a=0.05"),
        centre_series(dense, "weak_peak", "center_Pa", ref.pressure(dense.time_s - TD),
                      dense_sources[0], "M0; g=9.81, r0/a=0.05; open + peak history"),
        centre_series(old, "u_pw", "center_pressure_pa", old.finite_Kw_fixed18_p_pa,
                      old_source, "Finite Kw=2e8; g=9.80665, r0/a=0.05"),
        centre_series(dynamic, "dynamic", "native_fixed18_pressure_Pa",
                      dynamic.finite_Kw_fixed_radius_reference_Pa, dynamic_source,
                      "Finite Kw=2e8; g=9.80665, r0/a=0.05"),
        centre_series(p3, "p3", "center18_Pa", p3.M0_r18_Pa, p3_source,
                      "Retained P3 M0; g=9.80665, r0/a=0.05"),
    ]
    data = pd.concat(entries, ignore_index=True)
    need(np.isfinite(data[["time_s", "tau_s", "Tv", "pressure_Pa"]].to_numpy()).all(),
         "Nonfinite observed centre values")
    surface = read_csv(surface_source)
    need(np.array_equal(surface.completed_step, p3.completed_step) and
         np.array_equal(surface.time_s, p3.time_s), "P3 true-surface clocks differ")
    surf = pd.concat([
        pd.DataFrame(dict(series="weak_full", time_s=hist.time_s, tau_s=hist.tau_s,
                          Tv=hist.legacy_Tv, surface_inward_mm=hist.surface_inward_mm,
                          M0_surface_inward_mm=hist.M0_surface_inward_mm)),
        pd.DataFrame(dict(series="p3", time_s=surface.time_s, tau_s=surface.tau_s,
                          Tv=surface.tau_s * ref.legacy_cv / R**2,
                          surface_inward_mm=surface.surface_mm, M0_surface_inward_mm=np.nan)),
    ], ignore_index=True)
    paths = [weak_source, old_source, dynamic_source, p3_source, surface_source, *dense_sources]
    return data, surf, paths


def metrics(data):
    records = []
    for key, frame in data.groupby("series", sort=False):
        rows = frame[frame.Tv >= .005]
        err = rows.pressure_Pa - rows.reference_Pa
        peak = rows.loc[rows.pressure_Pa.idxmax()]
        records.append(dict(series=key, samples=len(rows), first_Tv=float(rows.Tv.iloc[0]),
            last_Tv=float(rows.Tv.iloc[-1]), peak_Pa=float(peak.pressure_Pa),
            peak_actual_time_s=float(peak.time_s), peak_tau_s=float(peak.tau_s),
            peak_Tv=float(peak.Tv), reference_RMS_Pa=float(np.sqrt(np.mean(err**2))),
            reference_max_abs_Pa=float(np.max(np.abs(err))),
            endpoint_Pa=float(rows.pressure_Pa.iloc[-1]),
            endpoint_reference_Pa=float(rows.reference_Pa.iloc[-1]),
            endpoint_error_Pa=float(err.iloc[-1]), reference=rows.reference.iloc[0]))
    return pd.DataFrame(records)


def profiles_with_theory(path):
    data = read_csv(path)
    ref = Reference(.3, finite=False)
    data["tau_s"] = data.time_s - TD
    data["M0_pressure_Pa"] = [float(ref.pressure(t, radius=r * R)[0])
                              for t, r in zip(data.tau_s, data.r_over_a)]
    data["mean_minus_M0_Pa"] = data.p_mean_Pa - data.M0_pressure_Pa
    return data


def figures(dest, data, surface, profiles, xmax):
    ref = Reference(.3, finite=False)
    tv = np.geomspace(1e-5, xmax, 800)
    tau = tv * R**2 / ref.legacy_cv
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), layout="constrained")
    for ax in axes:
        ax.plot(tv, ref.pressure(tau) / Q, "k--", lw=1.3, label="M0 analytical (weak)")
        finite = Reference(.3)
        ax.plot(tv, finite.pressure(tau) / Q, ":", color="0.45", lw=1.2, label="Finite-Kw analytical")
        for key in ("u_pw", "dynamic", "p3", "weak_full"):
            frame = data[(data.series == key) & (data.Tv > 0)]
            ax.plot(frame.Tv, frame.pressure_Pa / Q, color=COLORS[key], lw=1.4,
                    marker="." if key == "weak_full" else None, ms=3, label=LABELS[key])
        ax.set(xscale="log", xlabel="Actual Tv after drainage", ylabel="Centre pressure / q0")
        ax.grid(alpha=.22, which="both")
        ax.legend(fontsize=7)
    axes[0].set(xlim=(1e-5, xmax), title="Full saved histories (no extension of numerical data)")
    axes[1].set(xlim=(.005, .09), title="Mandel peak range")
    fig.savefig(dest / "center_comparison_log.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), layout="constrained")
    for key in ("u_pw", "dynamic", "p3", "weak_peak"):
        frame = data[(data.series == key) & (data.tau_s >= 0) & (data.tau_s <= .0625)]
        axes[0].plot(frame.tau_s * 1000, frame.pressure_Pa / 1000,
                     color=COLORS[key], lw=1.4, label=LABELS[key])
    tau = np.linspace(0, .0625, 600)
    axes[0].plot(tau * 1000, ref.pressure(tau) / 1000, "k--", label="M0 analytical (weak)")
    axes[0].set(xlabel="Actual time after drainage (ms)", ylabel="Centre pressure (kPa)",
                title="Retained dense peak; same material centre")
    for key, frame in surface.groupby("series", sort=False):
        frame = frame[frame.Tv > 0]
        axes[1].plot(frame.Tv, frame.surface_inward_mm, color=COLORS[key], label=LABELS[key])
    weak = surface[(surface.series == "weak_full") & (surface.Tv > 0)]
    axes[1].plot(weak.Tv, weak.M0_surface_inward_mm, "k--", label="M0 at actual saved clocks")
    axes[1].axhline(.1, color="0.5", ls=":", label="Ultimate drained surface (0.1 mm)")
    axes[1].set(xscale="log", xlim=(1e-5, xmax), xlabel="Actual Tv after drainage",
                ylabel="True surface inward displacement (mm)",
                title="Native outer surface; outer-band averages excluded")
    for ax in axes:
        ax.legend(fontsize=7)
        ax.grid(alpha=.22, which="both")
    fig.savefig(dest / "peak_and_surface.png", dpi=180)
    plt.close(fig)

    groups = list(profiles.groupby("step", sort=True))
    fig, axes = plt.subplots(1, len(groups), figsize=(3.2 * len(groups), 3.5),
                             layout="constrained", squeeze=False)
    for ax, (step, frame) in zip(axes[0], groups):
        ax.plot(frame.r_over_a, frame.M0_pressure_Pa / 1000, "k--", label="M0 at actual clock")
        ax.plot(frame.r_over_a, frame.p_mean_Pa / 1000, ".-", color=COLORS["weak_full"], label="Shell mean")
        ax.fill_between(frame.r_over_a, (frame.p_mean_Pa - frame.p_sd_Pa) / 1000,
                        (frame.p_mean_Pa + frame.p_sd_Pa) / 1000, alpha=.2, color=COLORS["weak_full"],
                        label="Angular spread ±1 SD")
        ax.set(xlabel="Reference r/a", ylabel="Pressure (kPa)",
               title=f"Tv={frame.legacy_Tv.iloc[0]:.6g}\nstep {step}")
        ax.legend(fontsize=6)
        ax.grid(alpha=.2)
    fig.savefig(dest / "radial_profiles.png", dpi=180)
    plt.close(fig)


def publish(output, package, hist, report, dest, xmax):
    data, surface, paths = comparisons(hist, package, output)
    profile_path = output / "review/shell_profiles.csv"
    profiles = profiles_with_theory(profile_path)
    sources = [binding(p) for p in paths + [profile_path, output / "review/review.json",
                                            output / "server_run.json", package / "manifest.json"]]
    receipt_path = dest / "comparison.json"
    if receipt_path.exists():
        receipt = read_json(receipt_path)
        need(receipt["sources"] == sources and receipt["x_axis_max_Tv"] == xmax,
             "Existing comparison uses different inputs or axis limits")
        need(all(binding(Path(item["path"])) == item for item in receipt["artifacts"]),
             "Existing comparison artifacts changed")
        print("Existing comparison figures and tables verified; continuing particle export", flush=True)
        return
    need(not dest.exists(), "Preserve partial comparison directory; choose a fresh --figures directory")
    dest.mkdir(parents=True)
    for name, frame in (("center_history.csv", data), ("surface_history.csv", surface),
                        ("center_metrics.csv", metrics(data)), ("radial_profiles.csv", profiles)):
        frame.to_csv(dest / name, index=False, float_format="%.17g")
    figures(dest, data, surface, profiles, xmax)
    write_json(receipt_path, dict(
        sources=sources, artifacts=[binding(p) for p in sorted(dest.iterdir())],
        method="Retained weak full native review plus retained historical CSV reductions; no native decoder rerun.",
        x_axis_max_Tv=xmax, measured_weak_end_Tv=float(hist.legacy_Tv.iloc[-1]),
        full_review=report, physical_acceptance=False,
        comparisons="Same initial 18 centre IDs. Actual saved clocks, no pressure interpolation. "
                    "Peak-only dynamic/P3 histories are not extended to the 1-Tv endpoint. "
                    "Each error uses its own documented M0 or finite-Kw reference; unequal windows are reported.",
        surface="Weak and retained P3 true native surface only. Old u-pw/dynamic outer-band means are not substituted.",
        particles="Weak raw states contain soil materials only. Drained soil surface is not a separate Bound population."))


def material_fields(raw, mesh):
    """Exact frozen 15-double-per-material layout; current coordinates are X0+u."""
    ids, x0, shell, fs = (mesh[k] for k in ("native_ids", "x0", "material_shell", "native_surface"))
    need(raw.size == 15 * len(ids) and np.isfinite(raw).all(), "Invalid weak material state")
    p, prev, u, v, stress, jac = np.split(raw, np.array([1, 2, 5, 8, 14]) * len(ids))
    u, v, stress = u.reshape(-1, 3), v.reshape(-1, 3), stress.reshape(-1, 6)
    drained = np.zeros(len(ids), dtype=np.uint8)
    drained[fs] = 1
    fields = dict(Idp=np.asarray(ids, dtype=np.uint32), PorePress=p, PorePressPrevious=prev,
                  Displacement=u, Vel=v, SigmaEffective_xx_yy_zz_xy_yz_xz=stress, J=jac,
                  MaterialShell=np.asarray(shell, dtype=np.int32), DrainageSurface=drained)
    return x0 + u, fields


def vtk_blocks(positions, fields):
    """Legacy binary VTK POLYDATA; every point is a material node, no invented wall state."""
    n = len(positions)
    yield b"# vtk DataFile Version 3.0\nCryer weak material states\nBINARY\nDATASET POLYDATA\n"
    yield f"POINTS {n} double\n".encode("ascii")
    yield np.asarray(positions, dtype=">f8").tobytes()
    yield f"\nVERTICES {n} {2*n}\n".encode("ascii")
    vertices = np.column_stack((np.ones(n, dtype=np.int32), np.arange(n, dtype=np.int32)))
    yield vertices.astype(">i4").tobytes()
    yield f"\nPOINT_DATA {n}\nFIELD FieldData {len(fields)}\n".encode("ascii")
    for name, values in fields.items():
        values = np.asarray(values)
        width = 1 if values.ndim == 1 else values.shape[1]
        dtype, label = {("f", 8): (">f8", "double"), ("u", 4): (">u4", "unsigned_int"),
                        ("i", 4): (">i4", "int"), ("u", 1): ("u1", "unsigned_char")}[values.dtype.kind, values.dtype.itemsize]
        yield f"{name} {width} {n} {label}\n".encode("ascii")
        yield values.astype(dtype, copy=False).tobytes()
        yield b"\n"


def check_vtk(stream, positions, fields):
    for block in vtk_blocks(positions, fields):
        need(stream.read(len(block)) == block, "Existing VTK differs from reviewed raw material state")
    need(not stream.read(1), "Trailing data in material VTK")


def export_particles(output, package, hist, seal):
    with np.load(package / "inputs/reference_mesh.npz") as data:
        mesh = {key: data[key] for key in ("native_ids", "x0", "material_shell", "native_surface")}
    need(np.array_equal(mesh["native_ids"], np.arange(8, 37181)), "Unexpected material IDs")
    folder = output / "particles"
    folder.mkdir(exist_ok=True)
    files = {entry["name"]: entry for entry in seal["files"]}
    entries, table = [], []
    created = 0
    for part, row in enumerate(hist.itertuples(index=False)):
        step = int(row.step)
        raw_path = output / f"state_{step}.bin"
        raw = raw_path.read_bytes()
        entry = files[raw_path.name]
        need(len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"].lower(),
             f"Raw state changed after frozen review: {raw_path.name}")
        pos, fields = material_fields(np.frombuffer(raw, dtype="<f8"), mesh)
        target = folder / f"PartFluid_{part:04d}.vtk"
        if not target.exists():
            temporary = target.with_suffix(".vtk.writing")
            # Only this unfinished derived temporary may be replaced on resume.
            with temporary.open("wb") as stream:
                for block in vtk_blocks(pos, fields):
                    stream.write(block)
            temporary.rename(target)
            created += 1
        with target.open("rb") as stream:
            check_vtk(stream, pos, fields)
        entries.append(dict(name=target.name, time=float(row.time_s)))
        table.append(dict(part=part, step=step, time_s=float(row.time_s), tau_s=float(row.tau_s),
                          Tv=float(row.legacy_Tv), file=target.name))
        if (part + 1) % 50 == 0:
            print(f"Material VTK {part + 1}/{len(hist)}", flush=True)
    series = {"file-series-version": "1.0", "files": entries}
    path = folder / "PartFluid.vtk.series"
    if path.exists():
        need(read_json(path) == series, "Existing material series differs")
    else:
        write_json(path, series)
    path = folder / "actual_times.csv"
    frame = pd.DataFrame(table)
    if path.exists():
        old = read_csv(path)
        need(old.equals(frame), "Existing particle clock table differs")
    else:
        frame.to_csv(path, index=False, float_format="%.17g")
    receipt = dict(frames=len(hist), materials=N, series_time="Actual physical time_s since load start",
                   first_time_s=float(hist.time_s.iloc[0]), last_time_s=float(hist.time_s.iloc[-1]),
                   fields=list(fields), original_id_range=[8, 37180], physical_acceptance=False,
                   boundary_series=None,
                   boundary_reason="No native wall state in this weak solver. Drained soil nodes remain PartFluid materials.",
                   sources=[binding(output / "server_run.json"), binding(output / "review/review.json"),
                            binding(package / "inputs/reference_mesh.npz")])
    path = folder / "postprocess_weak_vtk.json"
    if path.exists():
        need(read_json(path) == receipt, "Existing particle receipt differs")
    else:
        write_json(path, receipt)
    print(f"Material VTK complete: {len(hist)} frames; {created} created, {len(hist)-created} verified existing", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package", type=Path, default=CASE / "support/weak_full_r1")
    parser.add_argument("--figures", type=Path, default=FORMAL / "weak_full_nu030")
    parser.add_argument("--xmax", type=float, default=5., help="Log-Tv display limit; never extends measured data")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--particles-only", action="store_true")
    mode.add_argument("--figures-only", action="store_true")
    args = parser.parse_args()
    need(args.xmax > 1., "The full comparison axis must include 1 Tv")
    output, package = args.output.resolve(), args.package.resolve()
    hist, report, seal = reviewed(output, package)
    if not args.particles_only:
        publish(output, package, hist, report, args.figures.resolve(), args.xmax)
    if not args.figures_only:
        export_particles(output, package, hist, seal)


if __name__ == "__main__":
    main()
