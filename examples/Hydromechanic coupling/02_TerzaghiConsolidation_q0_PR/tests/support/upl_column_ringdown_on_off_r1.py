"""Future descriptive same-setting full-framework ON/OFF plots; no solver or new accuracy gate."""
import csv, hashlib, importlib.util, json
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_column_ringdown_on_off_r1"
PINS = {
    "support/upl_column_ringdown_half_r1.py": "46e296d0e155c97c08946fdf7ef0d5a3e28fa50ca346ad88900baf3fd42cab14",
    "notes/upl_column_ringdown_half_r1.json": "3499009716b3232f70f64e83eb6b9d7ed1397cd46469fb7aa7c98c9cb0c8a1bb",
    "support/upl_column_ringdown_off_half_r1.py": "d8004ca7508f0befa6bcaf591aa45a88de5aa33b59690de5acb8aae5857e2c3b",
    "notes/upl_column_ringdown_off_half_r1.json": "c66bb37fda99c99f2cad3cf4a37a860b8c5bfb4fa0f0036c7ebf922a4bfab0ba"}
TIMES = (0.015625, 0.0625, 0.125)
STYLES = [("#2166ac", "-", "ON coarse"), ("#67a9cf", "--", "ON half"),
          ("#b35806", "-", "OFF coarse"), ("#e08214", "--", "OFF half")]

def module(relative, name):
    path = T / relative; source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != PINS[relative]:
        raise ValueError("Pinned helper changed before import: " + relative)
    obj = importlib.util.module_from_spec(importlib.util.spec_from_file_location(name, path))
    exec(compile(source, str(path), "exec"), obj.__dict__)  # Guarded main never called.
    return obj

def union_entries(caches):
    merged = {}
    for cache in caches:
        for path, e in cache.items():
            if path in merged and merged[path] != e:
                raise ValueError("Helpers observed conflicting file identities: " + path)
            merged[path] = e
    return merged

def main():
    check = T / "logs" / (TAG + ".check.json")
    paths = {k: T / "figures" / (TAG + "_" + k.replace("_png", "") + ext) for k, ext in
             (("history", ".csv"), ("profiles", ".csv"), ("history_png", ".png"), ("profiles_png", ".png"))}
    if check.exists() or any(p.exists() for p in paths.values()):
        raise ValueError("Retained output protected")
    result = dict(stage=TAG, passed=False, physical_acceptance=False, solver_or_decoder_invoked=False,
                  descriptive_framework_comparison_only=True, new_ON_OFF_accuracy_gate=False, failure=None)
    tracked, caches, entry = {}, [], None
    try:
        for rel, digest in PINS.items():
            if hashlib.sha256((T / rel).read_bytes()).hexdigest() != digest:
                raise ValueError("Pinned source/note changed: " + rel)
        on = module("support/upl_column_ringdown_half_r1.py", "retained_ON_ringdown_half")
        off = module("support/upl_column_ringdown_off_half_r1.py", "retained_OFF_ringdown_half")
        caches = [on.base.TRACKED, off.base.TRACKED]  # Independent pinned helpers; no shared or patched module state.
        need, bind, adopt, readjson, entry = on.need, on.bind, on.adopt, on.readjson, on.entry
        adopt(__file__); adopt(T / "notes" / (TAG + ".json")); adopt(on.parent)
        for rel in PINS:
            adopt(T / rel)
        half_entries, half_proofs = [], []
        for model, stage in (("ON", "upl_column_ringdown_half_r1"), ("OFF", "upl_column_ringdown_off_half_r1")):
            e = adopt(T / "logs" / (stage + ".check.json")); proof = readjson(e["path"])
            need(proof["stage"] == stage and proof["passed"] and proof["physical_acceptance"] is False and proof["samples"] == 1277 and proof["native_count"] == 1000 and len(proof["gates"]) == 3 and all(v is True for v in proof["gates"].values()), model + " independent half not passed")
            for item in proof["inputs"] + proof["files"]:
                bind(item)
            half_entries.append(e); half_proofs.append(proof)
        data = [(model, window, helper.dataset(window)) for model, helper in (("ON", on), ("OFF", off)) for window in ("coarse", "half")]
        need(half_proofs[0]["native_checks"] == [data[0][2]["check"], data[1][2]["check"]] and half_proofs[1]["native_checks"] == [data[2][2]["check"], data[3][2]["check"]], "Half proofs refer to different actual native exports")
        tracked = union_entries(caches)  # Initial union of independently verified bindings; rehashed after plotting below.
        common_fields = off.F
        mapping = [on.base.F.index(name) for name in common_fields]
        need(len(common_fields) == len(mapping) == 24 and common_fields[19] == "ExcessPorePress", "ON26/OFF24 name map differs")
        reference = data[0][2]; identity = None; summaries = []; profiles = []
        for model, window, d in data:
            need(d["build"] == reference["build"] and np.array_equal(d["x0"].view("<u8"), reference["x0"].view("<u8")) and np.array_equal(d["clock"]["time"].view("<u8"), reference["clock"]["time"].view("<u8")), "Same-grid clock/material/current build identity differs")
            c = readjson(bind(d["check"])); leaves = {Path(e["path"]).name: e for e in c["files"]}
            ids = tuple(bind(leaves[name]).read_bytes() for name in ("native_ids.csv", "fixed_ids.csv"))
            if identity is None: identity = ids
            need(ids == identity, "Soil/fixed ID and initial-position files differ")
            layer = np.rint(d["x0"][:, 2] / 0.01 - 0.5).astype(int)
            need(np.array_equal(np.unique(layer), np.arange(100)) and all(np.count_nonzero(layer == k) == 10 for k in range(100)), "Initial material ten-column layers differ")
            top, bottom = layer == 99, layer == 0
            take = mapping if model == "ON" else list(range(24)); rows = []
            selected = {}
            for wanted in TIMES:
                match = np.flatnonzero(d["clock"]["time"] == wanted); need(len(match) == 1, "Exact requested actual profile time missing")
                selected[int(match[0])] = wanted
            for part in range(1277):
                q = np.asarray(d["p"]["q"][part])[:, take]; need(np.isfinite(q).all(), "Nonfinite shared field")
                time = float(d["clock"]["time"][part]); settle = -1000 * (q[:, 2] - d["x0"][:, 2])
                sigma = np.mean(q[:, 8:14], axis=0); speed = float(np.sqrt(np.mean(np.sum(q[:, 3:6] ** 2, axis=1))))
                row = [model, window, part, time, float(np.mean(q[:, 6])), float(np.mean(q[bottom, 6])), float(np.mean(q[top, 6])),
                       float(np.sqrt(np.mean(q[:, 6] ** 2))), float(np.mean(settle)), float(np.mean(settle[top])), float(np.mean(settle[bottom])),
                       *[float(v) for v in sigma], speed, float(np.mean(q[:, 5]))]
                need(np.isfinite(np.asarray(row[2:], dtype=float)).all(), "Nonfinite history reduction"); rows.append(row)
                if part in selected:
                    for k in range(100):
                        mask = layer == k
                        profiles.append([model, window, part, time, k, float(np.mean(d["x0"][mask, 2])), float(np.mean(q[mask, 6])),
                                         float(np.mean(settle[mask])), float(-np.mean(q[mask, 13])), float(np.sqrt(np.mean(np.sum(q[mask, 3:6] ** 2, axis=1))))])
            summaries.append(rows)
        for window in ("coarse", "half"):
            ond = next(d for model, w, d in data if model == "ON" and w == window)
            offd = next(d for model, w, d in data if model == "OFF" and w == window)
            onrun, offrun = readjson(bind(ond["run"])), readjson(bind(offd["run"]))
            need(onrun["program"] == offrun["program"], "ON/OFF did not use the same actual project main")
            manifest = readjson(bind(offrun["input_manifest"])); jobs = [j for j in manifest["jobs"] if j["window"] == window]
            need(manifest["passed"] and manifest["declared_master_only_change"] and len(jobs) == 1, "Matched master-only input proof missing")
            j = jobs[0]
            need(j["declared_master_only_change"] and j["inverse_DOM_exact"] and j["inverse_whole_text_exact"] and j["master_value"] == 0 and j["conductivity_model"] == 0 and j["conductivity_Ck"] == 0 and not j["initial_particle_fields_rewritten"] and j["retained_runtime"] == onrun["runtime_input"] and j["runtime"] == offrun["runtime_input"], "Matched actual ON/OFF runtime proof differs")
            need(all(j["retained_" + key]["sha256"] == j[key]["sha256"] and j["retained_" + key]["bytes"] == j[key]["bytes"] for key in ("initial_BI4", "normals")), "Matched seed/normal bytes differ")
        history_header = ["model", "grid", "part", "actual_time_s", "pressure_mean_Pa", "bottom10_pressure_mean_Pa", "top10_pressure_mean_Pa",
                          "pressure_RMS_Pa", "settlement_mean_mm", "top10_settlement_mean_mm", "bottom10_settlement_mean_mm",
                          "sigma_xx_mean_Pa", "sigma_xy_mean_Pa", "sigma_xz_mean_Pa", "sigma_yy_mean_Pa", "sigma_yz_mean_Pa", "sigma_zz_mean_Pa",
                          "velocity_XYZ_RMS_m_s", "velocity_z_mean_m_s"]
        with paths["history"].open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(history_header); w.writerows(row for rows in summaries for row in rows)
        with paths["profiles"].open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["model", "grid", "part", "actual_time_s", "initial_material_layer", "initial_z_m", "pressure_mean_Pa", "settlement_mean_mm", "stored_compression_zz_mean_Pa", "velocity_XYZ_RMS_m_s"]); w.writerows(profiles)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.25})
        fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharex=True)
        panels = [(4, 1, "Mean soil pressure (Pa)"), (5, 1, "Bottom10 material pressure (Pa)"),
                  (9, 1, "Top10 settlement, down positive (mm)"), (10, 1, "Bottom10 settlement, down positive (mm)"),
                  (16, -1, "Stored compression -sigma_zz (Pa)"), (17, 1, "Soil XYZ velocity RMS (m/s)")]
        for rows, (color, style, label) in zip(summaries, STYLES):
            a = np.asarray([row[2:] for row in rows], dtype=float)
            for ax, (column, sign, ylabel) in zip(axes.flat, panels):
                ax.plot(a[:, 1] * 1000, a[:, column - 2] * sign, color=color, linestyle=style, linewidth=1.3, label=label)
                ax.set_ylabel(ylabel); ax.axvline(5243 * 2.0 ** -19 * 1000, color="0.45", linestyle=":", linewidth=0.8)
        for ax in axes[-1]: ax.set_xlabel("Actual time (ms)")
        fig.suptitle("Matched noaux column: full-framework ON versus legacy u-pw OFF", y=0.995)
        fig.legend(*axes.flat[0].get_legend_handles_labels(), ncol=4, loc="upper center", bbox_to_anchor=(0.5, 0.967))
        fig.text(0.5, 0.015, "Descriptive A/B, not isolated acceleration-term causality or exact theory. Event = 10.00022888 ms.\nAll1277 samples drawn; ordinary122.0703125 us cadence does not certify full high-frequency ringing.", ha="center", fontsize=9)
        fig.tight_layout(rect=(0, 0.065, 1, 0.925)); fig.savefig(paths["history_png"], dpi=180); plt.close(fig)
        fig, axes = plt.subplots(4, 3, figsize=(13, 11), sharey=True)
        variables = [(6, "Pore pressure (Pa)"), (7, "Settlement, down positive (mm)"), (8, "Stored compression -sigma_zz (Pa)"), (9, "Layer XYZ velocity RMS (m/s)")]
        for col, time in enumerate(TIMES):
            axes[0, col].set_title("Actual t = " + format(time, ".6g") + " s")
            for model, window, (color, style, label) in zip(("ON", "ON", "OFF", "OFF"), ("coarse", "half", "coarse", "half"), STYLES):
                a = np.asarray([r[4:] for r in profiles if r[0] == model and r[1] == window and r[3] == time], dtype=float)
                need(a.shape == (100, 6) and np.isfinite(a).all(), "Complete100-layer profile missing")
                for row, (column, xlabel) in enumerate(variables):
                    axes[row, col].plot(a[:, column - 4], a[:, 1], color=color, linestyle=style, linewidth=1.3, label=label)
                    axes[row, col].set_xlabel(xlabel)
        for ax in axes[:, 0]: ax.set_ylabel("Initial material height z0 (m)")
        fig.suptitle("Same-setting ON/OFF: actual saved-time material-layer profiles", y=0.995)
        fig.legend(*axes[0, 0].get_legend_handles_labels(), ncol=4, loc="upper center", bbox_to_anchor=(0.5, 0.967))
        fig.text(0.5, 0.012, "Each point is the arithmetic mean (speed: RMS) of the10 original material IDs in one layer; no time interpolation/smoothing.\nMaster switch changes full J-inertia/quadrature, Darcy and closed-FS closure together. No ON/OFF accuracy gate.", ha="center", fontsize=9)
        fig.tight_layout(rect=(0, 0.06, 1, 0.925)); fig.savefig(paths["profiles_png"], dpi=180); plt.close(fig)
        tracked = union_entries(caches)
        for e in tracked.values():
            need(entry(e["path"]) == e, "Input changed during plotting")
        result.update(passed=True, half_checks=half_entries, native_checks=[d["check"] for _, _, d in data], source_runs=[d["run"] for _, _, d in data],
                      source_build=reference["build"], trajectories=4, samples_each=1277, native_count=1000, shared_columns=common_fields,
                      ON26_to_OFF24_name_mapping=mapping, exact_time_bits_and_material_IDs=True, history_rows=4*1277, profile_rows=4*3*100,
                      actual_profile_times_s=list(TIMES), independent_half_gates_required=True, acceleration_term_causally_isolated=False,
                      full_framework_J_inertia_quadrature_Darcy_closed_FS_A_B=True, absent_dynamic_OFF_fields_fabricated=False,
                      ordinary_cadence_us=122.0703125, full_high_frequency_certification=False, exact_theory_acceptance=False, visual_review_performed=False)
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        tracked = union_entries(caches)
    except Exception as exc:
        result["passed"] = False; result["failure"] = str(exc)
    result.update(inputs=list(tracked.values()), files=[entry(p) for p in paths.values() if p.exists()] if entry else [])
    with check.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps({"passed": result["passed"], "check": str(check)}))
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
