"""Saved-field .125s GPU ringdown plots; requires the own half check, never runs a decoder."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_column_ringdown_plot_r1"
EVENT = 5243 * 2.0 ** -19
LOCKS = {
    "support/upl_column_ringdown_half_r1.py": "46e296d0e155c97c08946fdf7ef0d5a3e28fa50ca346ad88900baf3fd42cab14",
    "notes/upl_column_ringdown_half_r1.json": "3499009716b3232f70f64e83eb6b9d7ed1397cd46469fb7aa7c98c9cb0c8a1bb",
}
# Chosen before data: event-equality pre-open, first PAIRED post-open, then three exact dyadic times.
PROFILE_STEPS = (5243, 5244, 8192, 32768, 65536)
PROFILE_LABELS = ("event equality (pre-open)", "first paired post-open", "15.625 ms", "62.5 ms", "125 ms")
RHO_FIELDS = ("native_current_rho_min_kg_m3", "native_current_rho_mean_kg_m3", "native_current_rho_max_kg_m3")


def dependency():
    sources = {}
    for leaf, sha in LOCKS.items():
        sources[leaf] = (T / leaf).read_bytes()
        if hashlib.sha256(sources[leaf]).hexdigest() != sha:
            raise ValueError("Frozen offline dependency changed before import: " + leaf)
    spec = importlib.util.spec_from_file_location("frozen_ringdown_half", T / "support/upl_column_ringdown_half_r1.py")
    mod = importlib.util.module_from_spec(spec)
    exec(compile(sources["support/upl_column_ringdown_half_r1.py"], str(spec.origin), "exec"), mod.__dict__)
    return mod  # Only pinned bytes; its main/dataset are not invoked by this load.


def summarize(h, grid, data):
    check = h.readjson(h.bind(data["check"]))
    leaves = {Path(e["path"]).name: e for e in check["files"]}
    with h.bind(leaves["history.csv"]).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        h.need(reader.fieldnames is not None and len(set(reader.fieldnames)) == len(reader.fieldnames), "Duplicate/missing history header")
        required = {"part", "time_s", "completed_step", "activeDrainCount", *RHO_FIELDS}
        h.need(required <= set(reader.fieldnames), "Native rho/time/drainage history fields missing")
        rows = list(reader)
    h.need(len(rows) == h.N, "Incomplete native history")
    rho = {k: np.array([float(row[k]) for row in rows]) for k in RHO_FIELDS}
    h.need(all(np.isfinite(v).all() for v in rho.values()), "Nonfinite native rho summary")
    x0 = data["x0"]
    layers = np.rint(x0[:, 2] / .01 - .5).astype(np.int64)
    h.need(np.array_equal(np.unique(layers), np.arange(100)) and np.all(np.bincount(layers) == 10), "Initial material layers differ")
    series, profiles, rho_gap = [], [], 0.0
    selection = {}
    for step, label in zip(PROFILE_STEPS, PROFILE_LABELS):
        indices = np.flatnonzero(h.STEPS == step)
        h.need(len(indices) == 1, "Predeclared profile time absent from native schedule")
        selection[int(indices[0])] = label
    factor = 2 if grid == "half" else 1
    for part in range(h.N):
        q = np.asarray(data["p"]["q"][part])
        h.need(np.isfinite(q).all(), "Nonfinite common26 field")
        time = float(data["clock"]["time"][part])
        completed = int(h.STEPS[part]) * factor
        h.need(int(rows[part]["part"]) == part and float(rows[part]["time_s"]) == time and int(rows[part]["completed_step"]) == completed, "History/native clock differs")
        active = int(rows[part]["activeDrainCount"])
        h.need(active == (10 if completed > 5243 * factor else 0), "Original nonempty drainage guard differs")
        p, theta, j = q[:, 6], q[:, 9], q[:, 8]
        down = -1000.0 * (q[:, 2] - x0[:, 2])
        du = 1000.0 * (q[:, :3] - x0)
        velocity = np.sqrt(np.mean(q[:, 3:6] ** 2, axis=0))
        frobenius2 = np.sum(q[:, (10, 13, 15)] ** 2, axis=1) + 2.0 * np.sum(q[:, (11, 12, 14)] ** 2, axis=1)
        total_compression = p - q[:, 15]  # -total sigma_zz for total sigma = effective sigma - p I.
        p_layer = np.bincount(layers, weights=p) / 10.0
        row = dict(grid=grid, part=part, actual_time_s=time, completed_step=completed,
                   post_open=int(completed > 5243 * factor), activeDrainCount=active,
                   pressure_mean_Pa=float(p.mean()), pressure_RMS_Pa=float(np.sqrt(np.mean(p * p))),
                   pressure_min_Pa=float(p.min()), pressure_max_Pa=float(p.max()), pressure_spatial_STD_Pa=float(p.std()),
                   top10_pressure_mean_Pa=float(p[layers == 99].mean()), bottom10_pressure_mean_Pa=float(p[layers == 0].mean()),
                   interior10_pressure_mean_Pa=float(p[layers == 49].mean()), top_minus_bottom_pressure_Pa=float(p_layer[99] - p_layer[0]),
                   settlement_mean_mm=float(down.mean()), top10_settlement_mean_mm=float(down[layers == 99].mean()),
                   bottom10_settlement_mean_mm=float(down[layers == 0].mean()), material_XYZ_displacement_RMS_mm=float(np.sqrt(np.mean(np.sum(du * du, axis=1)))),
                   vx_RMS_m_s=float(velocity[0]), vy_RMS_m_s=float(velocity[1]), vz_RMS_m_s=float(velocity[2]),
                   velocity_XYZ_RMS_m_s=float(np.sqrt(np.sum(velocity * velocity))),
                   J_min=float(j.min()), J_mean=float(j.mean()), J_max=float(j.max()),
                   saved_theta_min_s_inv=float(theta.min()), saved_theta_mean_s_inv=float(theta.mean()),
                   saved_theta_max_s_inv=float(theta.max()), saved_theta_RMS_s_inv=float(np.sqrt(np.mean(theta * theta))),
                   effective_compression_zz_mean_Pa=float(-q[:, 15].mean()), total_compression_zz_mean_Pa=float(total_compression.mean()),
                   stored_stress_Frobenius_RMS_Pa=float(np.sqrt(frobenius2.mean())))
        for col in (10, 11, 12, 13, 14, 15):
            row[h.base.F[col] + "_mean_Pa"] = float(q[:, col].mean())
        for key in RHO_FIELDS:
            row[key] = float(rho[key][part])  # Actual native rho statistics from the sealed typed reader, not new per-node observations.
        derived = 1000.0 + 1100.0 / j
        rho_gap = float(max(rho_gap, *(abs(float(rho[key][part]) - ref) for key, ref in zip(RHO_FIELDS, (derived.min(), derived.mean(), derived.max())))))
        series.append(row)
        if part in selection:
            profiles.append(dict(grid=grid, part=part, time_s=time, completed_step=completed, label=selection[part],
                                 layers=layers, x0=x0, pressure=p.copy(), compression=total_compression.copy(), settlement=down.copy()))
    return series, profiles, rho_gap


def figures(series, profiles, paths):
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .25})
    panels = [
        (("pressure_mean_Pa", "pressure_RMS_Pa", "top10_pressure_mean_Pa", "bottom10_pressure_mean_Pa"), "Native pressure [kPa]", 1e-3),
        (("settlement_mean_mm", "top10_settlement_mean_mm", "bottom10_settlement_mean_mm"), "Downward material settlement [mm]", 1),
        (("vx_RMS_m_s", "vy_RMS_m_s", "vz_RMS_m_s", "velocity_XYZ_RMS_m_s"), "Native velocity RMS [m/s]", 1),
        (("J_min", "J_mean", "J_max"), "Native volume ratio J", 1),
        (("saved_theta_min_s_inv", "saved_theta_mean_s_inv", "saved_theta_max_s_inv", "saved_theta_RMS_s_inv"), "Saved last-stage theta [1/s]", 1),
        (("effective_compression_zz_mean_Pa", "total_compression_zz_mean_Pa", "stored_stress_Frobenius_RMS_Pa"), "Stored stress / derived total compression [kPa]", 1e-3),
        (RHO_FIELDS, "Actual native current-density summary [kg/m3]", 1),
        (("pressure_spatial_STD_Pa", "top_minus_bottom_pressure_Pa"), "Spatial pressure contrast, not temporal amplitude [kPa]", 1e-3),
    ]
    fig, axes = plt.subplots(4, 2, figsize=(12, 13))
    for ax, (keys, title, scale) in zip(axes.flat, panels):
        for grid in ("coarse", "half"):
            rows = series[grid]
            for i, key in enumerate(keys):
                ax.plot([r["actual_time_s"] * 1000 for r in rows], [r[key] * scale for r in rows], color="C" + str(i),
                        ls="-" if grid == "coarse" else "--", lw=1, label=grid + " " + key)
        ax.axvline(EVENT * 1000, color="black", ls=":", lw=.8)
        ax.set(title=title, xlabel="Actual native time [ms]")
        ax.legend(fontsize=5.5)
    fig.suptitle("Public GPU .125 s dyadic coarse/half: saved fields only, not physical validation\n"
                 "Raw sampled histories; no smoothing, theory, force-stage budget or high-frequency decay certification.", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, .95))
    with paths["history_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 6), sharey=True)
    fields = (("pressure", "Native pore pressure [kPa]", 1e-3), ("compression", "Derived total compression p - sigma_zz [kPa]", 1e-3),
              ("settlement", "Downward material settlement [mm]", 1))
    for sample in profiles:
        color = "C" + str(PROFILE_LABELS.index(sample["label"]))
        layers, z0 = sample["layers"], sample["x0"][:, 2]
        level = np.array([z0[layers == i][0] for i in range(100)])
        for ax, (key, title, scale) in zip(axes, fields):
            value = sample[key] * scale
            ax.scatter(value, z0, color=color, s=1, alpha=.15, edgecolors="none")  # Every native soil point; no spatial mask.
            ax.plot(np.bincount(layers, weights=value) / 10.0, level, color=color,
                    ls="-" if sample["grid"] == "coarse" else "--", lw=1)
            ax.set(xlabel=title)
    axes[0].set_ylabel("Initial material z [m]")
    handles = [Line2D([], [], color="C" + str(i), label=f"{profiles[i]['time_s'] * 1000:.6f} ms: {label}")
               for i, label in enumerate(PROFILE_LABELS)]
    handles += [Line2D([], [], color="black", ls=style, label=grid + " layer means") for grid, style in (("coarse", "-"), ("half", "--"))]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7)
    fig.suptitle("Five actual saved instants; dots = every soil node, lines = ten-ID material-layer means\n"
                 "Event-equality state is pre-open; first paired post-open is not the first half integration step.", fontsize=10)
    fig.tight_layout(rect=(0, .15, 1, .92))
    with paths["profiles_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)


def main():
    paths = {k: T / "figures" / (TAG + suffix) for k, suffix in {
        "history_png": "_history.png", "profiles_png": "_profiles.png", "history_csv": "_history.csv", "profiles_csv": "_profiles.csv"}.items()}
    target = T / "logs" / (TAG + ".check.json")
    if target.exists() or any(p.exists() for p in paths.values()):
        raise ValueError("Retained plot/check output protected")
    result = dict(stage=TAG, passed=False, physical_acceptance=False, additional_scientific_gate=False,
                  solver_decoder_build_or_Git_invoked=False, failure=None)
    h = None
    try:
        h = dependency()
        for leaf in (*LOCKS, "support/upl_column_ringdown_plot_r1.py", "notes/upl_column_ringdown_plot_r1.json"):
            h.adopt(T / leaf)
        h.adopt(h.parent)
        half_entry = h.adopt(T / "logs/upl_column_ringdown_half_r1.check.json")
        half_check = h.readjson(half_entry["path"])
        gates = ("pressure_RMS_all_times_le_5Pa", "material_XYZ_difference_all_times_le_0_005mm", "actual_time_difference_le_1e_minus14_s")
        h.need(half_check["passed"] is True and half_check["stage"] == "upl_column_ringdown_half_r1" and half_check["physical_acceptance"] is False
               and half_check["samples"] == 1277 and set(half_check["gates"]) == set(gates)
               and all(half_check["gates"][key] is True for key in gates), "Own complete half check required before any dataset read")
        for e in half_check["inputs"] + half_check["files"]:
            h.bind(e)
        a, b = h.dataset("coarse"), h.dataset("half")
        h.need(half_check["native_checks"] == [a["check"], b["check"]] and half_check["source_runs"] == [a["run"], b["run"]]
               and half_check["source_build"] == a["build"] == b["build"] and np.array_equal(a["x0"].view("<u8"), b["x0"].view("<u8")), "Half proof binds a different native pair")
        sc, pc, rc = summarize(h, "coarse", a)
        sh, ph, rh = summarize(h, "half", b)
        h.need([r["actual_time_s"] for r in sc] == [r["actual_time_s"] for r in sh], "Actual paired times differ")
        with paths["history_csv"].open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(sc[0]))
            writer.writeheader(); writer.writerows(sc); writer.writerows(sh)
        profiles = pc + ph
        with paths["profiles_csv"].open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["grid", "part", "actual_time_s", "completed_step", "instant", "soil_ID", "initial_material_layer", "x0_m", "y0_m", "z0_m", "native_pressure_Pa", "derived_total_compression_Pa", "material_downward_settlement_mm"])
            for sample in profiles:
                for i in range(1000):
                    writer.writerow([sample["grid"], sample["part"], sample["time_s"], sample["completed_step"], sample["label"], i + 40,
                                     int(sample["layers"][i]), *sample["x0"][i], sample["pressure"][i], sample["compression"][i], sample["settlement"][i]])
        figures(dict(coarse=sc, half=sh), profiles, paths)
        for e in list(h.base.TRACKED.values()):
            h.need(h.entry(e["path"]) == e, "Input changed during descriptive plotting")
        result.update(passed=True, half_check=half_entry, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]],
                      source_build=a["build"], history_rows=2554, profile_rows=10000, actual_end_s=.125,
                      original_half_metrics={k: half_check[k] for k in ("max_pressure_RMS_Pa", "max_material_XYZ_displacement_difference_mm", "max_actual_time_difference_s")},
                      profile_instants=[dict(grid=p["grid"], part=p["part"], actual_time_s=p["time_s"], completed_step=p["completed_step"], label=p["label"]) for p in profiles],
                      actual_native_rho_history_vs_J_derived_summary_max_abs_kg_m3=dict(coarse=rc, half=rh),
                      bindings_unchanged_after_review=True)
    except Exception as exc:
        result["failure"] = str(exc)
    finally:
        plt.close("all")
    result.update(inputs=list(h.base.TRACKED.values()) if h is not None else [], files=[h.entry(p) for p in paths.values() if p.exists()] if h is not None else [])
    result["limitations"] = ["Typed-export review, not a second BI4 parser or physical/theory/ON-OFF validation.",
        "No CPU cohort ran here; no CPU/GPU performance or speedup claim.", "Absolute pressure RMS and spatial STD are not temporal oscillation amplitudes.",
        "No clipping, temporal smoothing, envelope fit, interpolation, reference curve or new physical threshold.",
        "Outside the dense event burst,122.0703125us storage cannot certify every acoustic/high-frequency decay mode; connecting saved points does not reconstruct them.",
        "Theta is the native saved last-stage value,not independently recomputed endpoint/all-stage data; native pdot is unavailable in common26.",
        "Total compression p-sigma_zz is derived from native effective stress/pressure; density summary comes from sealed native-history output,not a new per-node rho decoder.",
        "No actual force-stage load/resultant,wall flux,balance or energy budget is measured; no full-consolidation acceptance."]
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": result["passed"], "check": str(target)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
