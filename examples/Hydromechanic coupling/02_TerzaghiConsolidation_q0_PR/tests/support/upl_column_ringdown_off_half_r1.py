"""One offline matched-OFF GPU coarse/half check; no solver, decoder or ON/OFF gate."""
import csv, hashlib, importlib.util, json, struct
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
parent = T / "support/upl_gpu_column_pair_r1.py"
parent_source = parent.read_bytes()
if hashlib.sha256(parent_source).hexdigest() != "1da9023466c34f3ab77287eb77ccec270b60d2e07389a48e1ea4466cf3bdea28":
    raise ValueError("Retained neutral comparison helpers changed before import")
spec = importlib.util.spec_from_file_location("retained_OFF_column_pair", parent)
base = importlib.util.module_from_spec(spec)
exec(compile(parent_source, str(parent), "exec"), base.__dict__)  # Pinned neutral helpers only; guarded main/dataset never called.
need, bind, adopt, readjson, entry = base.require, base.bind, base.adopt, base.readjson, base.entry
N, S = 1277, 1000
F = base.F[:8] + base.F[10:]  # Explicit OFF24: remove only native J/theta; ExcessPorePress moves21->19.
SCHEMA = "case02_OFF_common24_no_J_theta_column19_ExcessPorePress"
STEPS = np.array(sorted(set(range(0, 65537, 64)) | set(range(5120, 5377))), dtype=np.int64)
LEAVES = {"original15.bin", "common24.bin", "clock.bin", "native_ids.csv", "fixed_ids.csv", "history.csv", "fixed_samples.csv", "columns.csv", "completion.json"}

def owned(e):
    c = base.owned(e)
    need(c.get("invocation_failure") is None and "log" in c, "New owned call/log rejected")
    bind(c["log"])
    return c

def mapped(e, header, dtype):
    p = bind(e)
    with p.open("rb") as f:
        need(struct.unpack("<" + "I" * len(header), f.read(4 * len(header))) == header, "Binary header differs")
    dtype = np.dtype(dtype)
    need(p.stat().st_size == 4 * len(header) + N * dtype.itemsize, "Binary payload length differs")
    return np.memmap(p, mode="r", offset=4 * len(header), dtype=dtype, shape=(N,))

def dataset(window):
    ce = adopt(T / ("logs/upl_column_ringdown_off_GPU_" + window + "_r1.native.json"))
    c = readjson(ce["path"])
    need(c["passed"] and c["stage"] == "upl_column_ringdown_off_native_run_r1" and c["backend"] == "GPU" and c["window"] == window and c["physical_acceptance"] is False, "OFF native owner rejected")
    need(c["source_inputs_raw_objects_runtime_canonical_unchanged"] and c["dynamic_arrays_metadata_absent"] and not c["J_ledger_or_dynamic_safety_inferred"], "OFF native ownership/absence contract rejected")
    q = readjson(bind(c["completion"]))
    dt = 2.0 ** (-20 if window == "half" else -19)
    need(q["passed"] and q["stage"] == "upl_column_ringdown_off_native_r1" and q["backend"] == "GPU_legacy_upw_OFF" and q["window"] == "ringdown125" and q["preset"] == window, "Wrong OFF native preset/backend")
    need((q["samples"], q["native_count"], q["fixed_count"], q["total_native_count"], q["common_columns"]) == (N, S, 40, 1040, 24), "Wrong OFF native identity")
    need(q["common_schema"] == SCHEMA and q["dt_s"] == dt and q["actual_end_s"] == 0.125, "Wrong OFF schema/clock/end")
    need(q["original_typed_arrays"] == 15 and q["native_total_arrays"] == 15 and q["dynamic_arrays_and_global_PART_metadata_absent"] and not q["absent_dynamic_fields_fabricated"] and not q["native_J_n_theta_V_rho_k_PosDiv_present"], "OFF arrays/metadata absence rejected")
    need(q["all_native_original15_finite_elastic_no_exclusions"] and q["fixed_positions_bit_exact"] and q["GPU_saved_fixed_velocity_zero_reference_density_verified"] and q["original_legacy_necessary_step_telemetry_checked"] and not q["dynamic_complete_rate_necessary_bound_inferred_for_OFF"] and q["physical_acceptance"] is False, "OFF saved finite/elastic/fixed/legacy telemetry gate rejected")
    for e in c["inputs"] + c["files"]:
        bind(e)
    r = readjson(bind(c["source_run"]))
    need(r["passed"] and r["stage"] == "upl_column_ringdown_off_run_r1" and r["backend"] == "GPU" and r["configuration"] == "Release" and r["window"] == window and r["matched_OFF_control_run"] and r["dynamic_master_on"] is False and r["legacy_u_pw_OFF"] and r["physical_acceptance"] is False, "Source OFF Run rejected")
    need(r["source_inputs_objects_runtime_canonical_unchanged"] and r["all_raw_outputs_hash_bound"] and r["native_frame_sequence_exact"] and r["native_frames"] == N and r["planned_samples"] == N, "Own complete OFF raw run required")
    for e in r["inputs"] + r["files"]:
        bind(e)
    call, reader_call = owned(r["call"]), owned(c["reader_call"])
    b = readjson(bind(r["source_build"]))
    need(b["passed"] and b["configuration"] == "Release" and b["source_and_protected_artifacts_unchanged"] and b["canonical_programs_unchanged"] and b["objects_exclude_main"] and len(b["objects"]) == 110 and b["isolated_GPU_program"] == r["program"] == call["program"] == call["target_program"], "Current project-main/build differs")
    need(call["public_project_main"] and call["direct_target_call"] and not call["fixture_or_Run_override"] and b["source_freeze"] == r["source_freeze"], "Actual direct OFF project main/source freeze required")
    source = readjson(bind(r["source_freeze"]))
    need(len(source["source"]) == len(source["current_source_snapshot"]) == 265 and len(source["canonical_programs_before"]) == 7 and len(source["runtime_before"]) == 4, "Current GPU265/canonical7/runtime4 closure rejected")
    for e in b["inputs"] + b["objects"] + b["tools"] + source["source"] + source["canonical_programs_before"] + source["runtime_before"]:
        bind(e)
    for row in source["current_source_snapshot"]:
        bind(row["original"]); bind(row["snapshot"]); need(row["original"]["sha256"] == row["snapshot"]["sha256"], "Current source/snapshot differs")
    for e in source["documentation_snapshot"].values():
        bind(e)
    for row in r["runtime"]:
        bind(row["original"]); bind(row["copy"])
    h = readjson(bind(c["reader_helper"]))
    need(h["passed"] and h["stage"] == "upl_column_ringdown_off_reader_build_r1" and h["exact_link_closure_verified"] and len(h["objects"]) == 85 and h["link_object_count"] == 86 and h["program"] == reader_call["program"], "Actual OFF reader85+1/program rejected")
    for e in h["inputs"] + h["author_files"] + h["objects"] + h["tools"] + h["libraries"] + [h["helper_object"], h["compiler_dependency_record"], h["program"]]:
        bind(e)
    owned(h["compile_call"]); owned(h["link_call"])
    for row in h["runtime"]:
        bind(row["original"]); bind(row["copy"])
    need(len(h["libraries"]) == 17 and len(h["runtime"]) == 4, "Reader runtime/library closure differs")
    admission = readjson(bind(r["off_admission_receipt"]))
    need(admission["stage"] == "upl_column_ringdown_off_admission_r1" and admission["passed"] and admission["physical_acceptance"] is False and admission["inputs"], "Explicit root OFF admission rejected")
    for e in admission["inputs"]:
        bind(e)
    files = {Path(e["path"]).name: e for e in c["files"]}
    need(len(c["files"]) == len(files) == 9 and set(files) == LEAVES and all(Path(e["path"]).parent == Path(c["paths"]["native_dir"]) for e in files.values()), "OFF nine-leaf scope differs")
    mapped(files["original15.bin"], (1040, 15, N), "V166408")
    p = mapped(files["common24.bin"], (S, 24, N), [("time", "<f8"), ("q", "<f8", (S, 24))])
    clock = mapped(files["clock.bin"], (N, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    fixed = np.genfromtxt(bind(files["fixed_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(S)), "Material soil ID order differs")
    need(np.array_equal(fixed["id"], np.arange(40)) and np.array_equal(fixed["row"], np.arange(40)), "Fixed ID order differs")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    fixed0 = np.column_stack([fixed[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f:
        cols = list(csv.DictReader(f))
    need([v["name"] for v in cols] == F and [int(v["column"]) for v in cols] == list(range(24)), "Explicit OFF24 column order differs")
    factor = 2 if window == "half" else 1
    done = np.where(np.arange(N) == 0, 0, clock["step"].astype(np.int64) + 1)
    need(np.array_equal(done, factor * STEPS) and np.all(clock["dt"] == dt), "Declared saved-step table differs")
    need(np.array_equal(clock["time"].view("<u8"), (STEPS * 2.0 ** -19).view("<u8")) and np.array_equal(p["time"].view("<u8"), clock["time"].view("<u8")), "Actual dyadic time bits differ")
    need(np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Original signed legacy necessary-step telemetry rejected")
    need(np.array_equal(p["q"][0, :, :3].view("<u8"), x0.view("<u8")), "Initial material coordinates differ")
    return dict(check=ce, run=c["source_run"], build=r["source_build"], program=r["program"], admission=r["off_admission_receipt"], p=p, clock=clock, x0=x0, fixed0=fixed0)

def main():
    check = T / "logs/upl_column_ringdown_off_half_r1.check.json"
    metrics = T / "figures/upl_column_ringdown_off_half_r1.csv"
    need(not check.exists() and not metrics.exists(), "Retained result protected")
    result = dict(stage="upl_column_ringdown_off_half_r1", passed=False, physical_acceptance=False, solver_or_decoder_invoked=False, ON_OFF_comparison=False, failure=None)
    try:
        adopt(__file__); adopt(T / "notes/upl_column_ringdown_off_half_r1.json"); adopt(parent)
        a, b = dataset("coarse"), dataset("half")
        need(a["build"] == b["build"] and a["program"] == b["program"] and a["admission"] == b["admission"], "OFF coarse/half current build/program/admission differs")
        need(np.array_equal(a["x0"].view("<u8"), b["x0"].view("<u8")) and np.array_equal(a["fixed0"].view("<u8"), b["fixed0"].view("<u8")), "Initial soil/fixed material coordinates differ")
        gap = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"])))
        pmax, umax = 0.0, 0.0
        field_max, field_rms = np.zeros(24), np.zeros(24)
        with metrics.open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["part", "coarse_actual_time_s", "half_actual_time_s", "pressure_RMS_Pa", "material_XYZ_displacement_difference_max_mm", "velocity_XYZ_RMS_m_s", "stress6_RMS_Pa", "LoadAce_XYZ_RMS_m_s2", "legacy_Rhop_max_abs_kg_m3"])
            for part in range(N):
                av, bv = np.asarray(a["p"]["q"][part]), np.asarray(b["p"]["q"][part])
                need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite original common fields")
                d = av - bv; rms = np.sqrt(np.mean(d * d, axis=0)); ma = np.max(np.abs(d), axis=0)
                need(np.isfinite(rms).all() and np.isfinite(ma).all(), "Nonfinite offline difference reduction")
                field_max = np.maximum(field_max, ma); field_rms = np.maximum(field_rms, rms)
                du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
                p = float(rms[6]); u = float(1000 * np.max(np.linalg.norm(du, axis=1)))
                pmax, umax = max(pmax, p), max(umax, u)
                w.writerow([part, float(a["clock"]["time"][part]), float(b["clock"]["time"][part]), p, u, float(np.sqrt(np.mean(np.sum(d[:, 3:6] ** 2, axis=1)))), float(np.sqrt(np.mean(np.sum(d[:, 8:14] ** 2, axis=1)))), float(np.sqrt(np.mean(np.sum(d[:, 20:23] ** 2, axis=1)))), float(ma[23])])
        gates = dict(pressure_RMS_all_times_le_5Pa=bool(pmax <= 5.0), material_XYZ_difference_all_times_le_0_005mm=bool(umax <= 0.005), actual_time_difference_le_1e_minus14_s=bool(gap <= 1e-14))
        for e in base.TRACKED.values():
            need(entry(e["path"]) == e, "Input changed during offline check")
        result.update(passed=bool(all(gates.values())), gates=gates, samples=N, native_count=S, common_columns=24, rows=N, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_build=a["build"], max_pressure_RMS_Pa=pmax, max_material_XYZ_displacement_difference_mm=umax, max_actual_time_difference_s=gap, max_field_RMS={k: float(v) for k, v in zip(F, field_rms)}, max_field_abs={k: float(v) for k, v in zip(F, field_max)}, all24_differences_descriptive_not_all24_gates=True, absent_J_n_theta_V_rho_k_PosDiv_not_fabricated=True, original_OFF_legacy_step_telemetry_not_dynamic_bound=True, full_cycle_half_acceptance=False)
    except Exception as exc:
        result["failure"] = str(exc)
    result.update(inputs=list(base.TRACKED.values()), files=[entry(metrics)] if metrics.exists() else [])
    with check.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps({"passed": result["passed"], "check": str(check)}))
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
