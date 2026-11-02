"""Two descriptive scientific figures from three sealed column pair checks; never run physics."""
import argparse, csv, importlib.util, json, re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
PAIR_SHA = "1da9023466c34f3ab77287eb77ccec270b60d2e07389a48e1ea4466cf3bdea28"
NAMES = ("cross-coarse", "cross-half", "half")
LABELS = ("CPU coarse", "GPU coarse", "GPU half")
COLORS = ("#4477AA", "#EE7733", "#228833")
STYLES = ("-", "--", "-.")
TARGETS = (0.0099, 0.010, 0.010025, 0.0125, 0.025)
HIST = ("pressure_RMS_Pa", "top10_settlement_mean_mm", "bottom10_settlement_mean_mm",
        "stored_compression_zz_mean_Pa", "J_minus1_mean", "J_minus1_min",
        "J_minus1_max", "saved_theta_RMS_s_inv", "top10_pressure_mean_Pa", "bottom10_pressure_mean_Pa")

def writer(path, header, rows):
    with path.open("x", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

def histories(d, layers):
    q, z0 = d["values"]["q"], d["x0"][:, 2]
    out = np.empty((len(q), len(HIST)))
    for i, a in enumerate(q):
        settlement = -1000*(a[:, 2]-z0); j = a[:, 8]-1
        out[i] = (np.sqrt(np.mean(a[:, 6]**2)), np.mean(settlement[layers == 99]),
                  np.mean(settlement[layers == 0]), -np.mean(a[:, 15]),
                  np.mean(j), np.min(j), np.max(j), np.sqrt(np.mean(a[:, 9]**2)),
                  np.mean(a[layers == 99, 6]), np.mean(a[layers == 0, 6]))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="upl_gpu_column_plot_r1")
    tag = ap.parse_args().tag
    if not re.fullmatch(r"upl_gpu_column_plot_r[1-9][0-9]*", tag): raise ValueError("Invalid fresh output tag")
    paths = [T/"figures"/(tag+s) for s in ("_history.png", "_history.csv", "_profiles.png", "_profiles.csv")]
    check = T/"logs"/(tag+".check.json")
    if any(p.exists() for p in paths+[check]): raise FileExistsError("Retained plot outputs protected")
    spec = importlib.util.spec_from_file_location("sealed_column_pair", T/"support"/"upl_gpu_column_pair_r1.py")
    pair = importlib.util.module_from_spec(spec); spec.loader.exec_module(pair)
    result = dict(stage="upl_gpu_column_plot_r1", passed=False, physical_acceptance=False,
                  solver_or_decoder_invoked=False, new_scientific_acceptance_gate=False,
                  visual_QA_performed=False, failure=None)
    try:
        pe = pair.adopt(pair.__file__); pair.require(pe["sha256"] == PAIR_SHA, "Frozen pair implementation changed")
        pair.adopt(T/"notes"/"upl_gpu_column_pair_r1.json"); pair.adopt(__file__)
        pair.adopt(T/"notes"/"upl_gpu_column_plot_r1.json")
        proofs, differences = [], []
        for name in NAMES:
            stem = "upl_gpu_column_pair_"+name.replace("-", "_")+"_r1"
            cp = T/"logs"/(stem+".check.json"); ce = pair.adopt(cp); c = pair.readjson(cp)
            pair.require(c["passed"] and c["physical_acceptance"] is False and c["pair"] == name
                         and c["stage"] == "upl_gpu_column_pair_r1" and all(c["gates"].values()), "Pair not admitted")
            pair.require((c["samples"], c["native_count"], c["columns"], c["metric_rows"], c["field_rows"])
                         == (769, 1000, 26, 769, 19994), "Pair grain/schema changed")
            for e in c["inputs"]+c["files"]: pair.bind(e)
            metric = [e for e in c["files"] if Path(e["path"]).name == stem+".csv"]
            pair.require(len(metric) == 1, "Unique sealed pair metrics missing")
            m = np.genfromtxt(pair.bind(metric[0]), delimiter=",", names=True, encoding="utf-8")
            pair.require(len(m) == 769 and np.array_equal(m["part"], np.arange(769)), "Pair metric rows changed")
            pair.require(np.isfinite(m["pressure_RMS_Pa"]).all()
                         and np.isfinite(m["material_XYZ_displacement_diff_max_mm"]).all(), "Nonfinite pair curves")
            differences.append(m); proofs.append(ce)
        # One imported module/cache: each unique binary/raw/source binding is hashed once here.
        data = [pair.dataset("coarse", False), pair.dataset("coarse", True), pair.dataset("half", True)]
        x0 = data[0]["x0"]
        pair.require(all(np.array_equal(d["x0"].view("<u8"), x0.view("<u8")) for d in data), "Material IDs/x0 differ")
        layers = np.rint(x0[:, 2]/0.01-0.5).astype(int)
        pair.require(np.array_equal(np.unique(layers), np.arange(100))
                     and np.array_equal(np.bincount(layers), np.full(100, 10)), "100 material layers of 10 soil IDs required")
        h = [histories(d, layers) for d in data]
        pair.require(all(np.isfinite(v).all() for v in h), "Nonfinite descriptive histories")
        history_header = ["part"]
        for key in ("CPU_coarse", "GPU_coarse", "GPU_half"):
            history_header += [key+"_actual_time_s"]+[key+"_"+k for k in HIST]
        for name in NAMES:
            history_header += [name+"_"+k for k in ("time_a_s", "time_b_s", "pressure_RMS_Pa",
                                                   "material_XYZ_displacement_diff_max_mm")]
        writer(paths[1], history_header, ([i]+sum(([float(d["clock"]["time"][i])]+[float(v) for v in v[i]]
                for d, v in zip(data, h)), [])+sum(([float(m[k][i]) for k in
                ("time_a_s", "time_b_s", "pressure_RMS_Pa", "material_XYZ_displacement_diff_max_mm")]
                for m in differences), []) for i in range(769)))
        plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "legend.fontsize": 8, "figure.facecolor": "white"})
        fig, axes = plt.subplots(4, 2, figsize=(14, 15)); ax = axes.ravel()
        for d, v, label, color, style in zip(data, h, LABELS, COLORS, STYLES):
            tm = d["clock"]["time"]*1000
            for ai, col, scale in ((0, 0, 1e-3), (2, 3, 1e-3), (3, 4, 1e3), (4, 7, 1)):
                ax[ai].plot(tm, v[:, col]*scale, style, color=color, label=label, lw=1.4)
            for ai, top, bottom, scale in ((1, 1, 2, 1), (7, 8, 9, 1e-3)):
                ax[ai].plot(tm, v[:, top]*scale, "-", color=color, label=label+" top 10", lw=1.2)
                ax[ai].plot(tm, v[:, bottom]*scale, ":", color=color, label=label+" bottom 10", lw=1.2)
        titles = ("Soil pressure RMS (kPa)", "Material settlement: downward positive (mm)",
                  "Mean stored compression -sigma_zz (kPa)", "Mean (J - 1) x 1000",
                  "Saved last-force theta RMS (1/s)", "Pair pressure RMS difference (Pa)",
                  "Pair maximum XYZ material displacement difference (mm)", "Top/bottom soil mean pressure (kPa)")
        pair_labels = ("GPUc - CPUc", "GPUh - CPUh", "GPUc - GPUh")
        for ai, key, limit in ((5, "pressure_RMS_Pa", 5.0), (6, "material_XYZ_displacement_diff_max_mm", 0.005)):
            inset = ax[ai].inset_axes([0.15, 0.48, 0.48, 0.43])
            for m, label, color, style in zip(differences, pair_labels, COLORS, STYLES):
                tm = m["time_a_s"]*1000
                ax[ai].plot(tm, m[key], style, color=color, label=label, lw=1.3)
                inset.plot(tm, m[key], style, color=color, lw=1)
            ax[ai].axhline(limit, color="#AA3377", ls="--", lw=1, label="Prior limit "+str(limit))
            ax[ai].set_ylim(bottom=0); inset.set_title("Same complete data; autoscale", fontsize=7)
            inset.tick_params(labelsize=7); inset.grid(alpha=0.2); inset.set_xlim(0, 25)
        for a, title in zip(ax, titles):
            a.set_title(title, loc="left"); a.set_xlabel("Actual saved time (ms)"); a.set_xlim(0, 25)
            a.axvline(10, color="#666666", lw=0.8, alpha=0.65); a.grid(alpha=0.25); a.legend(loc="best")
        fig.suptitle("Private constant-k loaded column: retained CPUc and new GPUc/GPUh", fontsize=15)
        fig.text(0.5, 0.025, "Vertical line: 10 ms drain-start event (equality saved pre-open). All 769 actual frames; no interpolation.\n"
                 "Top/bottom = initial material layers (10 soil IDs each); fixed particles excluded. Difference insets repeat all points.\n"
                 "FreeSlip / g=0 / no HG, SPR, viscosity or damping; CPU OMP1. No theory or full-physical acceptance.", ha="center", fontsize=9)
        fig.tight_layout(rect=(0, 0.075, 1, 0.96)); fig.savefig(paths[0], dpi=180); plt.close(fig)
        fig, axes = plt.subplots(5, 3, figsize=(15, 19), sharey=True)
        profile_rows, selected = [], []
        for row, target in enumerate(TARGETS):
            times = []
            for d, label, color, style in zip(data, LABELS, COLORS, STYLES):
                part = int(np.argmin(np.abs(d["clock"]["time"]-target))); actual = float(d["clock"]["time"][part])
                a = np.asarray(d["values"]["q"][part]); values = []
                for layer in range(100):
                    mask = layers == layer; z0 = float(np.mean(x0[mask, 2])); z = float(np.mean(a[mask, 2]))
                    p = float(np.mean(a[mask, 6])); settlement = float(np.mean(-1000*(a[mask, 2]-x0[mask, 2])))
                    compression = float(-np.mean(a[mask, 15]))
                    values.append((p*1e-3, settlement, compression*1e-3, z0))
                    profile_rows.append([target, label, part, actual, int(d["clock"]["step"][part])+1 if part else 0,
                                         layer, int(np.sum(mask)), z0, z, p, settlement, compression,
                                         float(np.mean(a[mask, 8])), float(np.mean(a[mask, 9]))])
                v = np.asarray(values)
                for col in range(3): axes[row, col].plot(v[:, col], v[:, 3], style, color=color, label=label, lw=1.4)
                times.append(label+" "+format(actual*1000, ".6f")+" ms")
                selected.append(dict(requested_time_s=target, backend=label, part=part, actual_time_s=actual))
            axes[row, 0].set_ylabel("Initial material height z0 (m)")
            axes[row, 1].set_title("Requested "+format(target*1000, ".3f")+" ms; nearest saved only", fontsize=11)
            axes[row, 0].text(0, 1.025, "\n".join(times), transform=axes[row, 0].transAxes, fontsize=8, va="bottom")
            for a, title in zip(axes[row], ("Pressure (kPa)", "Downward material settlement (mm)", "Stored compression -sigma_zz (kPa)")):
                a.set_xlabel(title); a.grid(alpha=0.25)
        axes[0, 2].legend(loc="best")
        fig.suptitle("Nearest actual saved profiles: 10 soil IDs averaged per initial material layer", fontsize=15)
        fig.text(0.5, 0.012, "Each backend selects its own nearest saved part. Displayed times rounded; matching CSV retains exact actual times/steps.\n"
                 "No time interpolation, smoothing, analytical reference, fixed-field comparison or new acceptance gate.", ha="center", fontsize=10)
        fig.tight_layout(rect=(0, 0.04, 1, 0.965)); fig.savefig(paths[2], dpi=180); plt.close(fig)
        writer(paths[3], ["requested_time_s", "backend", "part", "actual_time_s", "completed_steps", "material_layer",
                         "soil_count", "initial_z_mean_m", "current_z_mean_m", "pressure_mean_Pa", "settlement_mean_mm",
                         "stored_compression_zz_mean_Pa", "J_mean", "saved_theta_mean_s_inv"], profile_rows)
        for e in list(pair.TRACKED.values()):
            now = pair.entry(e["path"]); pair.require(now["bytes"] == e["bytes"] and now["sha256"] == e["sha256"], "Input changed during plot")
        result.update(passed=True, pair_checks=proofs, samples_per_backend=769, soil_count=1000, physical_columns=26,
                      physical_schema=pair.SCHEMA, history_rows=769, profile_rows=len(profile_rows), material_layers=100,
                      soil_per_layer=10, profile_selection=selected, CPU_ompthreads=1, fixed_fields_compared=False,
                      limit_pressure_RMS_Pa=5.0, limit_material_XYZ_difference_mm=0.005,
                      descriptive_fields_not_acceptance=["stored_sigma_zz", "J", "saved_theta", "layer_means"],
                      input_bindings=len(pair.TRACKED), CPU_historical_original_sources_revalidated_as_current=False)
    except Exception as exc:
        result["failure"] = str(exc)
    finally:
        plt.close("all")
    result.update(inputs=list(pair.TRACKED.values()), files=[pair.entry(p) for p in paths if p.exists()])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check), output_files=len(result["files"]))))
    return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())

