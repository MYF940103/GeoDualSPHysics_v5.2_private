"""Read-only five-save C08 startup comparison; consumes closed typed22 exports only."""
import argparse
import csv
import json
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from upl_c08_fsmask_r1 import SCHEMA, TYPES, need

TOTAL, FIXED, SOIL = 7060, 2060, 5000
DT = 1. / 262144.
TIMES = np.array([0, 32, 64, 96, 128], dtype="<f8") * DT
TAGS = {
    "baseline_CPU": "upl_c08_elastic_start_CPU_r2",
    "baseline_GPU": "upl_c08_elastic_start_GPU_r2",
    "free_CPU": "upl_c08_free_seepage_start_CPU_r1",
    "free_GPU": "upl_c08_free_seepage_start_GPU_r1",
}
BANDS = ("all", "top_2h", "bottom_2h")


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return {"path": str(path), "bytes": s.st_size, "mtime_ns": s.st_mtime_ns}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bound_stat(item):
    need(stat(item["path"]) == item, "Closed consumed stat changed: " + item["path"])
    return item


def table(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    need(rows, "Empty comparison table")
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_closed(tests, label, tag):
    directory = tests / "outputs" / (tag + "_native_r1")
    receipt_path = tests / "logs" / (tag + "_native_r1.check.json")
    receipt = load_json(receipt_path)
    need(receipt.get("passed") is True and receipt.get("original_native_guards_passed") is True
         and receipt.get("all22_typed_arrays_independently_reloaded") is True
         and receipt.get("consumed_stats_unchanged") is True, "Native check is not closed/passed: " + tag)
    for key in ("source_run_check", "source_run_call", "source_input_manifest", "source_build", "native_completion", "reader_call"):
        bound_stat(receipt[key])
    for item in receipt["outputs"]:
        bound_stat(item)
    run_check = load_json(receipt["source_run_check"]["path"])
    run_call = load_json(receipt["source_run_call"]["path"])
    reader_call = load_json(receipt["reader_call"]["path"])
    need(run_check.get("passed") is True and run_check.get("actual_solver_exit") == 0
         and run_call.get("actual_solver_Win32_exit") == 0
         and run_call.get("solver_exit_queried_from_retained_handle") is True
         and reader_call.get("exit_code") == 0, "Original solver/reader exits not sealed: " + tag)
    done = load_json(directory / "completion.json")
    expected_stage = "upl_c08_free_seepage_start_native_r1" if label.startswith("free") else "upl_c08_elastic_start_native_r1"
    need(done.get("passed") is True and done.get("stage") == expected_stage
         and done.get("input_run_tag") == tag and done.get("samples") == 5
         and done.get("completed_steps") == 128 and done.get("total_native_IDs") == TOTAL
         and done.get("soil_IDs") == SOIL and done.get("fixed_IDs") == FIXED
         and done.get("typed_arrays") == 22, "Native completion scope differs: " + tag)
    if label.startswith("free"):
        need(done.get("free_seepage_candidate") is True and done.get("free_seepage_metadata_checks") == 5,
             "Free-policy metadata not independently checked")
    layout = table(directory / "typed22_layout.csv")
    need(len(layout) == len(SCHEMA), "Layout array count differs")
    for row, (name, kind, nc) in zip(layout, SCHEMA):
        need((row["array"], row["type"], int(row["components"]), int(row["bytes_per_particle"]))
             == (name, kind, nc, TYPES[kind].itemsize * nc), "Closed typed22 layout changed")
    raw = directory / "typed22.bin"
    need(raw.stat().st_size == 12 + 5 * (8 + TOTAL * 212), "Typed22 size differs")
    frames = []
    with raw.open("rb") as f:
        need(struct.unpack("<III", f.read(12)) == (TOTAL, 22, 5), "Typed22 header differs")
        for part in range(5):
            clock = f.read(8)
            need(clock == TIMES[part:part + 1].tobytes(), "Actual time is not the exact declared dyadic save")
            frame = {}
            for name, kind, nc in SCHEMA:
                a = np.fromfile(f, dtype=TYPES[kind], count=TOTAL * nc)
                frame[name] = a.reshape(TOTAL, nc) if nc > 1 else a
                need(np.all(np.isfinite(a)), "Nonfinite typed data after closed reader")
            need(np.array_equal(frame["Idp"], np.arange(TOTAL)), "Native IDs no longer aligned")
            frames.append(frame)
        need(not f.read(1), "Trailing typed22 bytes")
    ids = table(directory / "native_ids.csv")
    need(len(ids) == TOTAL and all(int(r["id"]) == i and int(r["is_fixed"]) == int(i < FIXED)
         for i, r in enumerate(ids)), "Original fixed/soil ID table changed")
    x0 = np.array([[float(r[k]) for k in ("x0", "y0", "z0")] for r in ids])
    need(np.array_equal(x0, frames[0]["Posd"]), "Initial material coordinates differ")
    clocks = table(directory / "clocks.csv")
    need(len(clocks) == 5 and all(int(r["part"]) == i and int(r["completed_step"]) == 32 * i
         and int(r["saved_step"]) == (32 * i - 1 if i else 0)
         and struct.pack("<d", float(r["time_s"])) == TIMES[i:i + 1].tobytes()
         for i, r in enumerate(clocks)), "Actual saved clocks/steps differ")
    history = {(int(r["part"]), r["initial_material_band"]): r for r in table(directory / "history.csv")}
    need(len(history) == 25, "Closed five-band history incomplete")
    consumed = [stat(receipt_path)] + [receipt[k] for k in ("source_run_check", "source_run_call", "source_build", "native_completion", "reader_call")] + receipt["outputs"]
    return {"label": label, "tag": tag, "frames": frames, "x0": x0, "history": history, "consumed": consumed}


def total_stress(frame):
    # Saved shear order is xy,yz,xz. Compression-positive p subtracts from tension-positive stress diagonals.
    return np.column_stack((frame["SigmaState_kk"] - frame["PorePress"][:, None], frame["SigmaState_ij"]))


def metrics(a, b, select, name, part, band):
    fa, fb = a["frames"][part], b["frames"][part]
    dp = fb["PorePress"][select].astype(float) - fa["PorePress"][select]
    du = 1000 * (fb["Posd"][select] - fa["Posd"][select])
    ds = (total_stress(fb) - total_stress(fa))[select]
    row = {"comparison": name, "difference_sign": "second_minus_first", "part": part,
           "time_s": float(TIMES[part]), "initial_material_band": band, "IDs": int(select.sum()),
           "p_difference_mean_Pa": float(dp.mean()), "p_difference_RMS_Pa": float(np.sqrt(np.mean(dp * dp))),
           "p_difference_max_abs_Pa": float(np.max(np.abs(dp))),
           "material_XYZ_difference_RMS_mm": float(np.sqrt(np.mean(np.sum(du * du, axis=1)))),
           "material_XYZ_difference_max_norm_mm": float(np.sqrt(np.sum(du * du, axis=1)).max())}
    for n, axis in enumerate("xyz"):
        row["max_abs_d" + axis + "_mm"] = float(np.max(np.abs(du[:, n])))
    for field, key in (("PoroVolumeRatio", "J"), ("PoroPorosity", "n"), ("PoroMixtureDensity", "rho_mix_kg_m3")):
        difference = fb[field][select] - fa[field][select]
        row[key + "_difference_RMS"] = float(np.sqrt(np.mean(difference * difference)))
        row[key + "_difference_max_abs"] = float(np.max(np.abs(difference)))
    row["total_stress_difference_Frobenius_RMS_Pa"] = float(np.sqrt(np.mean(np.sum(ds[:, :3] ** 2, axis=1) + 2 * np.sum(ds[:, 3:] ** 2, axis=1))))
    for n, component in enumerate(("xx", "yy", "zz", "xy", "yz", "xz")):
        row["total_sigma_" + component + "_difference_max_abs_Pa"] = float(np.max(np.abs(ds[:, n])))
    return row


def run(tests, prefix):
    outputs = {name: Path(str(prefix) + suffix) for name, suffix in {
        "history": "_history.csv", "comparisons": "_comparisons.csv", "surface": "_surface.csv",
        "final_surface": "_final_surface.csv", "figure": ".png", "check": ".check.json"}.items()}
    need(prefix.parent.is_dir() and not any(p.exists() for p in outputs.values()), "Fresh prefix and existing figures parent required")
    data = {label: read_closed(tests, label, tag) for label, tag in TAGS.items()}
    x0 = data["baseline_CPU"]["x0"]
    need(all(np.array_equal(d["x0"], x0) for d in data.values()), "Four original material coordinate tables differ")
    soil = np.arange(TOTAL) >= FIXED
    h = float(np.float32(.048))
    zmin, zmax = x0[soil, 2].min(), x0[soil, 2].max()
    bands = {"all": soil, "top_2h": soil & (x0[:, 2] >= zmax - 2 * h), "bottom_2h": soil & (x0[:, 2] <= zmin + 2 * h)}
    need([int(bands[k].sum()) for k in BANDS] == [5000, 300, 300], "Original initial-material bands differ")
    history_rows, surface_rows, final_rows, comparison_rows = [], [], [], []
    for label, d in data.items():
        for part, frame in enumerate(d["frames"]):
            for band, select in bands.items():
                p = frame["PorePress"][select].astype(float)
                settlement = -1000 * (frame["Posd"][select, 2] - x0[select, 2])
                row = {"dataset": label, "part": part, "time_s": float(TIMES[part]), "initial_material_band": band,
                       "IDs": int(select.sum()), "p_mean_Pa": float(p.mean()), "p_RMS_Pa": float(np.sqrt(np.mean(p * p))),
                       "p_min_Pa": float(p.min()), "p_max_Pa": float(p.max()),
                       "material_settlement_mean_mm": float(settlement.mean()),
                       "material_settlement_RMS_mm": float(np.sqrt(np.mean(settlement * settlement)))}
                saved = d["history"][(part, band)]
                need(int(saved["count"]) == row["IDs"] and np.isclose(row["p_mean_Pa"], float(saved["p_mean_Pa"]), rtol=5e-13, atol=5e-13)
                     and np.isclose(row["material_settlement_mean_mm"], -1000 * float(saved["mean_dz_m"]), rtol=5e-13, atol=5e-13),
                     "Descriptive reduction no longer matches the existing native history")
                history_rows.append(row)
            surface = soil & np.isin(frame["FSType"], [2, 3])
            p = frame["PorePress"][surface]
            need(p.size > 0, "Empty actual native free surface")
            if label.startswith("free"):
                need(np.all(p <= 0), "Saved free-policy surface violates its existing sign guard")
            surface_rows.append({"dataset": label, "part": part, "time_s": float(TIMES[part]), "FS2_count": int((soil & (frame["FSType"] == 2)).sum()),
                                 "FS3_count": int((soil & (frame["FSType"] == 3)).sum()), "FS23_count": int(surface.sum()),
                                 "raw_p_min_Pa": float(p.min()), "raw_p_max_Pa": float(p.max()),
                                 "negative_count": int((p < 0).sum()), "zero_count": int((p == 0).sum()), "positive_count": int((p > 0).sum())})
            if part == 4:
                for native_id in np.flatnonzero(surface):
                    final_rows.append({"dataset": label, "native_id": int(native_id), "FSType_native": int(frame["FSType"][native_id]),
                                       "x0_m": float(x0[native_id, 0]), "z0_m": float(x0[native_id, 2]),
                                       "x_m": float(frame["Posd"][native_id, 0]), "z_m": float(frame["Posd"][native_id, 2]),
                                       "raw_pressure_Pa": float(frame["PorePress"][native_id]),
                                       "pressure_float32_bits": int(frame["PorePress"].view("<u4")[native_id])})
    pairs = (("free_CPU", "free_GPU", "free_GPU_minus_CPU"),
             ("baseline_CPU", "free_CPU", "CPU_free_minus_baseline"),
             ("baseline_GPU", "free_GPU", "GPU_free_minus_baseline"))
    for first, second, name in pairs:
        for part in range(5):
            for band, select in bands.items():
                comparison_rows.append(metrics(data[first], data[second], select, name, part, band))
    for name, rows in (("history", history_rows), ("comparisons", comparison_rows), ("surface", surface_rows), ("final_surface", final_rows)):
        write_csv(outputs[name], rows)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    palette = {"all": "#222222", "top_2h": "#0072b2", "bottom_2h": "#d55e00"}
    styles = {"baseline_CPU": (":", "o"), "baseline_GPU": ("--", "x"), "free_CPU": ("-", "s"), "free_GPU": ("-.", "+")}
    by_history = {(r["dataset"], r["initial_material_band"], r["part"]): r for r in history_rows}
    for label in data:
        ls, marker = styles[label]
        for band in BANDS:
            rows = [by_history[label, band, part] for part in range(5)]
            axes[0, 0].plot(TIMES * 1000, [r["p_mean_Pa"] / 1000 for r in rows], color=palette[band], linestyle=ls, marker=marker, markersize=5)
            axes[0, 1].plot(TIMES * 1000, [r["material_settlement_mean_mm"] for r in rows], color=palette[band], linestyle=ls, marker=marker, markersize=5)
        rows = [r for r in surface_rows if r["dataset"] == label]
        axes[1, 0].plot(TIMES * 1000, [r["FS23_count"] for r in rows], linestyle=ls, marker=marker, label=label)
        rows = [r for r in final_rows if r["dataset"] == label]
        axes[1, 1].scatter([r["x0_m"] for r in rows], [r["raw_pressure_Pa"] for r in rows], marker=marker, s=18, label=label)
    axes[0, 0].set(title="Native material-band mean pressure", xlabel="Actual saved time [ms]", ylabel="p mean [kPa]")
    axes[0, 1].set(title="Native material settlement (down positive)", xlabel="Actual saved time [ms]", ylabel="Mean settlement [mm]")
    axes[1, 0].set(title="Actual native FS2/3 counts", xlabel="Actual saved time [ms]", ylabel="Soil particles")
    axes[1, 1].set(title="Final native free-surface pressure (raw, no clipping)", xlabel="Initial material x [m]", ylabel="p [Pa]")
    axes[1, 1].ticklabel_format(axis="y", style="sci", scilimits=(0, 0), useOffset=False)
    for ax in axes.flat:
        ax.grid(alpha=.22)
    axes[0, 0].legend(handles=[Line2D([], [], color=palette[b], label=b) for b in BANDS], fontsize=8)
    axes[1, 0].legend(fontsize=8)
    fig.suptitle("C08 five-save startup: baseline boundary vs free-seepage candidate, CPU/GPU\n"
                 "Different boundary operators are descriptive controls; no equilibrium or physical-accuracy claim", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .92), h_pad=2)
    fig.savefig(outputs["figure"], dpi=180)
    plt.close(fig)
    inputs = [e for d in data.values() for e in d["consumed"]]
    need(all(stat(e["path"]) == e for e in inputs), "Consumed closed receipt/export changed during offline review")
    summary = {name: {key: max(float(r[key]) for r in comparison_rows if r["comparison"] == name and r["initial_material_band"] == "all")
                     for key in ("p_difference_RMS_Pa", "p_difference_max_abs_Pa", "material_XYZ_difference_max_norm_mm", "J_difference_max_abs", "n_difference_max_abs", "rho_mix_kg_m3_difference_max_abs", "total_stress_difference_Frobenius_RMS_Pa")}
               for _, _, name in pairs}
    check = {"stage": "upl_c08_free_start_compare_r1", "analysis_completed": True, "physical_acceptance": False,
             "exact_saved_times_s": TIMES.tolist(), "samples_each": 5, "original_IDs_each": TOTAL,
             "soil_IDs_each": SOIL, "typed_arrays_each": 22, "history_rows": len(history_rows),
             "comparison_rows": len(comparison_rows), "surface_history_rows": len(surface_rows),
             "final_surface_rows": len(final_rows), "maximum_all_soil_descriptors": summary,
             "surface_history": surface_rows, "inputs": inputs, "outputs": [stat(p) for k, p in outputs.items() if k != "check"],
             "same_backend_baseline_is_different_boundary_not_half_truth": True, "negative_or_signed_zero_data_modified": False,
             "new_5Pa_or_FSNormal_bit_gate": False, "constant_k_elastic_scope_only": True,
             "BI4_decoder_solver_build_Git_SHA_invocations": 0}
    with outputs["check"].open("x", encoding="utf-8") as f:
        json.dump(check, f, indent=2)
    print(json.dumps({"stage": check["stage"], "analysis_completed": True, "maximum_all_soil_descriptors": summary}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args()
    run(args.tests.resolve(), args.out_prefix.resolve())
