"""One offline same-event1341 CPU step-candidate half check; no old-trajectory adoption."""
import argparse, csv, hashlib, importlib.util, json, re, struct
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
STAGE, N = "upl_damp_step_compare_r1", 1341
EVENT = 2621 * 2. ** -18
STEPS = np.array(sorted(set(range(0, 32769, 32)) | set(range(2560, 2689)) | set(range(33280, 131073, 512))), dtype=np.int64)
PARENT = T / "support/upl_damp_long_compare_r1.py"
PIN = "c838ed61d940c078339ac5b630718649e625731bd05f25304d80b16f659bd601"
NOTE_PIN = "3155d8dd579ed5d94ee7f5ef4102f710d5d628876d0d671ed798d99dc91a8780"
source = PARENT.read_bytes()
if hashlib.sha256(source).hexdigest() != PIN: raise ValueError("Pinned neutral helper source changed before import")
neutral = importlib.util.module_from_spec(importlib.util.spec_from_file_location("step_neutral_exports", PARENT))
exec(compile(source, str(PARENT), "exec"), neutral.__dict__)  # No old dataset/main is called; no globals are patched.
need, entry, readjson, bits = neutral.need, neutral.entry, neutral.readjson, neutral.base.bits
FIELDS = neutral.FIELDS
EXPORTS = set(neutral.BINARY) | set(neutral.IDENTITY) | set(neutral.TEXT) | {"last_poro.csv", "completion.json"}
BOUND = {}
for e in neutral.base.BOUND.values():
    key = str(Path(e["path"]).resolve()).casefold()
    need(key not in BOUND or all(BOUND[key][k] == e[k] for k in ("bytes", "sha256")), "Conflicting verified neutral dependency")
    BOUND[key] = e
BOUND[str(PARENT.resolve()).casefold()] = dict(path=str(PARENT.resolve()), bytes=len(source), sha256=PIN)

def bind(e):
    p = Path(e["path"]).resolve(); key = str(p).casefold()
    need(type(e["bytes"]) is int and e["bytes"] >= 0 and isinstance(e["sha256"], str), "Invalid bound Entry")
    if key not in BOUND: BOUND[key] = entry(p)
    a = BOUND[key]
    need(a["bytes"] == e["bytes"] and a["sha256"].lower() == e["sha256"].lower(), "Changed/conflicting bound Entry: " + str(p))
    return p

def adopt(path):
    p = Path(path).resolve(); key = str(p).casefold()
    if key not in BOUND: BOUND[key] = entry(p)
    return BOUND[key]

need(adopt(T / "notes/upl_damp_long_compare_r1.json")["sha256"] == NOTE_PIN, "Pinned neutral note changed")

def owned(e):
    c = readjson(bind(e))
    need(c["direct_native_call"] and c["owned_call_exited"] and c["typed_LASTEXITCODE_captured_immediately"] and type(c["exit_code"]) is int and c["exit_code"] == 0 and not c.get("invocation_failure"), "Actual direct owned typed exit0 required")
    bind(c["program"]); bind(c["log"])
    if c.get("target_program"): bind(c["target_program"])
    return c

def mapped(e, header, dtype):
    p = bind(e); dtype = np.dtype(dtype)
    with p.open("rb") as f: need(struct.unpack("<" + "I" * len(header), f.read(4 * len(header))) == header, "Typed binary header differs")
    need(p.stat().st_size == 4 * len(header) + N * dtype.itemsize, "Typed binary length differs")
    return np.memmap(p, mode="r", offset=4 * len(header), dtype=dtype, shape=(N,))

def xml_root(e):
    root = ET.parse(bind(e), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))).getroot()
    for node in root.iter():
        if node.text is not None and not node.text.strip(): node.text = None
        if node.tail is not None and not node.tail.strip(): node.tail = None
    return root

def input_proof(r, window, dt):
    m = readjson(bind(r["input_manifest"])); j = r["job"]
    need(m["stage"] == "upl_damp_step_prepare_r1" and m["passed"] and m["prepared"] and m["physical_acceptance"] is False and m["new_experiment"] and not m["old_half_or_prefix_adopted"] and m["input_sources_unchanged"] and m["source_build"] == r["source_build"] and m["source_program"] == r["program"], "Own new-experiment Prepare/program rejected")
    jobs = [v for v in m["jobs"] if v["window"] == window]
    need(len(jobs) == 1 and jobs[0] == j and j["damping"] == 1 and j["damping_coef"] == .02 and j["inverse_DOM_exact"] and j["only_declared_clock_event_changes"] and not j["initial_particle_fields_rewritten"] and not j["old_trajectory_prefix_equivalence_claimed"], "Own prepared job/material differs")
    need(j["ramp_and_drain_event_s"] == EVENT and j["event_completed_step"] == (5242 if window == "half" else 2621) and j["event_part"] == 141 and j["first_post_open_part"] == 142 and j["post_open_frames"] == 1199 and j["samples_through_0p125"] == 1149 and j["necessary_current_state_step_bound_still_required"], "Declared same-event experiment differs")
    need(j["initial_BI4"]["sha256"] == "f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac" and j["normals"]["sha256"] == "0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97", "Unchanged initial BI4/Normals identity differs")
    for key in ("configuration", "runtime", "initial_BI4", "normals", "source_configuration", "source_runtime"): bind(j[key])
    need(j["configuration"]["sha256"] == j["runtime"]["sha256"] and j["source_configuration"]["sha256"] == j["source_runtime"]["sha256"] and str(Path(j["runtime"]["path"]).with_suffix("")) == j["input_prefix"], "Runtime/configuration/prefix differs")
    current, original = xml_root(j["runtime"]), xml_root(j["source_runtime"])
    prefix = "/case/execution/parameters/parameter[@key='"
    hydro = "/case/execution/special/hydromechanics/"
    for path, value in ((prefix + "TimeMax']", .5), (prefix + "SoilDamping']", 1.), (prefix + "SoilDampingCoef']", .02), (hydro + "HydroMechDynamicSeepage", 1.), (hydro + "HydroMechConductivityModel", 0.), (hydro + "HydroMechConductivityCk", 0.)):
        nodes = current.findall(path[len("/case/"):]); need(len(nodes) == 1 and float(nodes[0].get("value")) == value, "Own current public/material window differs")
    changes = [(prefix + key + "']", "value", dt / 2, dt) for key in ("DtIni", "DtFixed")]
    changes += [(hydro + key, "value", 5243 * 2. ** -19, EVENT) for key in ("HydroMechTopLoadRampTime", "HydroMechDrainageStartTime")]
    changes += [("/case/execution/special/timeout/tout[2]", "timeout", 2. ** -19, 2. ** -18)]
    declared = {(v["xpath"].replace('"', "'"), v["attribute"]): v for v in j["changes"]}
    need(len(j["changes"]) == len(declared) == 5 and set(declared) == {(p, a) for p, a, _, _ in changes}, "Only five clock/event attributes may change")
    for path, attribute, old, new in changes:
        a, b = current.findall(path[len("/case/"):]), original.findall(path[len("/case/"):])
        need(len(a) == len(b) == 1 and float(a[0].get(attribute)) == new and float(b[0].get(attribute)) == old and float(declared[(path, attribute)]["new_value"]) == new and float(declared[(path, attribute)]["old_value"]) == old, "Declared XML attribute differs")
        a[0].set(attribute, b[0].get(attribute))
    need(ET.tostring(current) == ET.tostring(original), "Input changed outside the five declared clock/event attributes")
    return j

def dataset(window):
    need(window in ("coarse", "half"), "Only the new completed coarse/half pair is supported")
    tag = "upl_damp_step_CPU_" + window + "_r1"; ce = adopt(T / "logs" / (tag + ".native.json")); c = readjson(ce["path"])
    need(c["stage"] == "upl_damp_step_native_run_r1" and c["passed"] and c["physical_acceptance"] is False and c["backend"] == "CPU" and c["window"] == window and c["bindings_unchanged"] and c["original_native_guards_passed"] and c["drainage_nonempty_per_frame_verified"] and c["drainage_check_applicable"] and not c["old_trajectory_prefix_adopted"], "Own completed new native safety receipt rejected")
    r = readjson(bind(c["source_run"])); factor = 2 if window == "half" else 1; steps = STEPS * factor; dt = 2. ** (-19 if factor == 2 else -18); times = steps * dt
    need(r["stage"] == "upl_damp_step_run_r1" and r["passed"] and r["physical_acceptance"] is False and r["backend"] == "CPU" and r["threads"] == 8 and r["window"] == r["input_window"] == window and r["configuration"] == "ReleaseCPU" and r["public_project_main"] and not r["fixture_or_Run_override"] and r["source_inputs_objects_runtime_canonical_unchanged"] and not r["old_trajectory_prefix_adopted"], "Own same-window CPU8 project-main Run rejected")
    need(r["source_build"] == c["source_build"] and (r["planned_completed_steps"], r["planned_end_s"], r["expected_native_frames"], r["native_frames"]) == (int(steps[-1]), .5, N, N), "Actual completed full-window scope differs")
    j = input_proof(r, window, dt); need((j["dt_s"], j["end_s"], j["steps"], j["expected_samples"]) == (dt, .5, int(steps[-1]), N), "Own prepared schedule differs")
    need(len(j["saved_clock_table"]) == N, "Prepared clock-table count differs")
    for i, row in enumerate(j["saved_clock_table"]):
        need(all(type(row[k]) is int for k in ("part", "completed_steps", "saved_step")) and (row["part"], row["completed_steps"], row["saved_step"]) == (i, int(steps[i]), int(steps[i] - 1) if i else 0) and struct.pack("<d", row["time_s"]) == struct.pack("<d", times[i]), "Raw JSON integer/dyadic schedule differs")
    solver, reader = owned(r["call"]), owned(c["reader_call"])
    need(solver["program"] == solver["target_program"] == r["program"] and solver["public_project_main"] and not solver["fixture_or_Run_override"] and solver["arguments"] == ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", j["input_prefix"], c["paths"]["solver_dir"], "-dirdataout", "data", "-svres", "-nsteps:" + str(int(steps[-1]))], "Real project-main target/argv differs")
    need(reader["pure_native_reader"] and not reader["solver_or_build_invoked"] and reader["arguments"] == ["--read", "CPU", str(Path(c["paths"]["solver_dir"]) / "data"), window, c["paths"]["native_dir"]], "Real reader invocation differs")
    h = readjson(bind(c["reader_helper"])); need(h["passed"] and h["stage"] == "upl_damp_step_reader_build_r1" and h["kind"] == "reader" and h["configuration"] == "ReleaseCPU" and h["program"] == reader["program"] and h["source_build"] == r["source_build"] and h["exact_link_closure_verified"] and h["build_and_source_bindings_unchanged"] and len(h["objects"]) == 85 and h["link_object_count"] == 86 and not h["solver_started"], "Actual same-source reader85+1 authority differs")
    for key in ("compile_call", "link_call"): owned(h[key])
    for e in h["author_files"]: bind(e)
    bind(h["compiler_dependency_record"])
    b = readjson(bind(r["source_build"])); need(b["passed"] and b["stage"] == "upl_damp_build_r2" and b["configuration"] == "ReleaseCPU" and b["program"] == r["program"] and b["source_snapshot"] == r["source_snapshot"] and b["source_bindings_unchanged"] and b["canonical_programs_unchanged"] and b["runtime_unchanged"] and b["exact_object_basename_closure"] and b["objects_include_project_main"] and len(b["objects"]) == 86, "Own actual main build86/source identity differs")
    bc = readjson(bind(b["project_call"])); need(bc["direct_native_call"] and bc["owned_call_exited"] and bc["typed_LASTEXITCODE_captured_immediately"] and type(bc["exit_code"]) is int and bc["exit_code"] == 0 and not bc.get("invocation_failure") and bc["program"] == b["build_tool"] and bc["arguments"] == b["arguments"], "Original authoritative build typed exit/vector differs")
    for e in (b["build_tool"], b["log"], b["binlog"], r["run_out"]): bind(e)
    need(len(r["source_snapshot"]) == 265 and len(r["runtime"]) == len(h["runtime"]) == 4 and len(r["canonical_programs_before"]) == 7, "265/runtime4/canonical7 recorded scope differs")
    for row in r["source_snapshot"]:
        bind(row["snapshot"]); need(all(row["original"][k] == row["snapshot"][k] for k in ("bytes", "sha256")), "Frozen source snapshot differs")
    for pair in (r["documentation_snapshot"], r["case_readme_snapshot"]): bind(pair["snapshot"])
    for row in r["runtime"] + h["runtime"]: bind(row["copy"])
    raw = [Path(e["path"]).name for e in r["files"] if re.fullmatch(r"Part_\d{4}\.bi4", Path(e["path"]).name)]
    need(len(raw) == N and set(raw) == {f"Part_{i:04d}.bi4" for i in range(N)}, "Recorded own raw PART ownership/count differs")
    q = readjson(bind(c["completion"])); need(q["passed"] and q["stage"] == "upl_damp_step_native_r1" and q["window"] == "step500" and q["preset"] == window and q["grid"] == ("h" if factor == 2 else "c") and q["backend"] == "CPU_public" and q["physical_acceptance"] is False and q["physical_schema"] == neutral.parent.SCHEMA and q["model"] == "constant", "Own typed completion/preset differs")
    need((q["samples"], q["native_count"], q["fixed_count"], q["total_native_count"], q["physical_columns"], q["native_total_arrays"], q["native_dynamic_double_arrays"]) == (N, 1000, 40, 1040, 26, 22, 6) and all(q[k] for k in ("PART_typed_public_metadata_verified", "public_master_on", "public_schema", "native_PosDiv_present", "native_PosDiv_is_float", "native_V_rho_k_present", "no_exclusions", "all_exported_physical_fields_finite", "initial_rest_and_decimal_lattice_verified", "double_stress_and_float_display_verified")) and q["conductivity_model"] == 0 and q["conductivity_Ck"] == 0, "Public22/native1040/finite/elastic schema guards rejected")
    need(q["max_ledger_relative_error"] <= 5e-13 and q["soil_ledger_checks"] == N * 1000 and q["fixed_public_zero_marker_checks"] == N * 40 and q["dt_s"] == dt and q["actual_end_s"] == .5 and q["planned_completed_steps"] == int(steps[-1]) and q["declared_saved_completed_steps_exact"] and q["actual_time_step_locked_dt_exact"] and q["noninitial_signed_dterror_intervals"] == N - 1 and q["max_noninitial_signed_dterror_s"] <= 1e-14 and q["declared_ramp_and_drain_event_s"] == EVENT, "Original ledger/necessary-step/actual clock guards rejected")
    need((q["post_open_frames"], q["post_open_drained_particle_checks"], q["max_activeDrainCount"], q["post_open_completed_step_threshold"]) == (1199, 11990, 10, 2621 * factor), "Original nonempty drainage coverage differs")
    directory = Path(c["paths"]["native_dir"]).resolve(); files = {}
    for e in c["files"]:
        p = bind(e); need(p.parent == directory and p.name not in files, "Duplicate/escaped native leaf"); files[p.name] = e
    need(set(files) == EXPORTS and files["completion.json"] == c["completion"], "Native13 leaf identity differs")
    p = mapped(files["physical.bin"], (1000, 26, N), [("time", "<f8"), ("q", "<f8", (1000, 26))])
    clock = mapped(files["clock.bin"], (N, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    jt = mapped(files["common_j_theta.bin"], (1040, 2, N), [("time", "<f8"), ("q", "<f8", (1040, 2))])
    por = mapped(files["soil_n.bin"], (1000, 1, N), [("time", "<f8"), ("q", "<f8", (1000,))])
    raw15 = mapped(files["original15.bin"], (1040, 15, N), [("time", "<f8"), ("payload", "V166400")])
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f: cols = list(csv.DictReader(f))
    need([v["name"] for v in cols] == FIELDS and [int(v["column"]) for v in cols] == list(range(26)), "Common26 columns/ExcessPorePress21 differ")
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8"); fixed = np.genfromtxt(bind(files["fixed_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(1000)) and np.array_equal(fixed["id"], np.arange(40)) and np.array_equal(fixed["row"], np.arange(40)), "1040 original native IDs/order differs")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    need(np.array_equal(clock["step"].astype(np.int64), np.where(steps > 0, steps - 1, 0)) and bits(clock["dt"], np.full(N, dt)).all() and bits(clock["time"], times).all() and all(bits(a["time"], clock["time"]).all() for a in (p, jt, por, raw15)) and bits(p["q"][0, :, :3], x0).all(), "Exact native clock/zero-based Step/material coordinates differ")
    need(np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Signed necessary-step diagnostic rejected")
    with bind(files["history.csv"]).open(encoding="utf-8-sig", newline="") as f: history = list(csv.DictReader(f))
    need(len(history) == N, "History row count differs")
    for i, row in enumerate(history):
        need(int(row["part"]) == i and int(row["completed_step"]) == int(steps[i]) and int(row["saved_step"]) == int(clock["step"][i]) and struct.pack("<d", float(row["time_s"])) == struct.pack("<d", times[i]) and float(row["dt_s"]) == dt and struct.pack("<d", float(row["signed_dterror_s"])) == struct.pack("<d", clock["error"][i]) and int(row["activeDrainCount"]) == (10 if steps[i] > 2621 * factor else 0), "Actual history clock/signed diagnostic/nonempty drainage differs")
    return dict(check=ce, run=c["source_run"], build=r["source_build"], program=r["program"], files=files, p=p, clock=clock, x0=x0, n=N, job=j, history=history)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--case", choices=("half",), default="half"); ap.parse_args()
    check = T / "logs/upl_damp_step_half_r1.check.json"; metrics = T / "logs/upl_damp_step_half_r1.csv"
    need(not check.exists() and not metrics.exists(), "Retained comparison artifacts protected")
    result = dict(stage=STAGE, case="half", passed=False, physical_acceptance=False, solver_decoder_or_build_invoked=False, old_half_or_prefix_inherited=False, old_new_trajectory_comparison_performed=False, failure=None)
    try:
        adopt(__file__); adopt(T / "notes/upl_damp_step_compare_r1.json"); a, b = dataset("coarse"), dataset("half")
        need(a["build"] == b["build"] and a["program"] == b["program"] and bits(a["x0"], b["x0"]).all() and bits(a["p"]["q"][0], b["p"]["q"][0]).all(), "Same own build/program/material IDs/all26 initial bits required")
        gap = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"]))); pmax = umax = 0.; rmsmax = np.zeros(26); absmax = np.zeros(26); ppart = upart = 0
        with metrics.open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["part", "A_actual_time_s", "B_actual_time_s", "pressure_RMS_Pa", "material_XYZ_difference_max_mm", "velocity_XYZ_RMS_m_s", "stress6_RMS_Pa"])
            for i in range(N):
                av, bv = np.asarray(a["p"]["q"][i]), np.asarray(b["p"]["q"][i]); need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite common26 state")
                d = av - bv; rms, ma = np.sqrt(np.mean(d * d, axis=0)), np.max(np.abs(d), axis=0); need(np.isfinite(rms).all() and np.isfinite(ma).all(), "Nonfinite paired reduction")
                rmsmax, absmax = np.maximum(rmsmax, rms), np.maximum(absmax, ma); du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
                p, u = float(rms[6]), float(1000 * np.max(np.linalg.norm(du, axis=1)))
                if p > pmax: pmax, ppart = p, i
                if u > umax: umax, upart = u, i
                w.writerow([i, float(a["clock"]["time"][i]), float(b["clock"]["time"][i]), p, u, float(np.sqrt(np.mean(np.sum(d[:, 3:6] ** 2, axis=1)))), float(np.sqrt(np.mean(np.sum(d[:, 10:16] ** 2, axis=1))))])
        gates = dict(pressure_RMS_all_times_le_5Pa=pmax <= 5., material_XYZ_difference_all_times_le_0_005mm=umax <= .005, actual_time_difference_le_1e_minus14_s=gap <= 1e-14)
        for e in list(BOUND.values()):
            actual = entry(e["path"]); need(actual["bytes"] == e["bytes"] and actual["sha256"] == e["sha256"], "Consumed artifact changed during independent final rehash")
        result.update(passed=bool(all(gates.values())), gates=gates, samples=N, native_count=1000, fixed_count=40, total_native_count=1040, initial26_bit_exact=True, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_builds=[a["build"], b["build"]], same_event_s=EVENT, max_pressure_RMS_Pa=pmax, max_pressure_part=ppart, max_pressure_time_s=float(a["clock"]["time"][ppart]), max_material_XYZ_displacement_difference_mm=umax, max_displacement_part=upart, max_displacement_time_s=float(a["clock"]["time"][upart]), max_actual_time_difference_s=gap, max_common26_RMS=dict(zip(FIELDS, map(float, rmsmax))), max_common26_abs=dict(zip(FIELDS, map(float, absmax))), other_common26_metrics_descriptive=True, no_interpolation_or_time_snap=True, unique_consumed_files=len(BOUND), consumed_artifacts_rehashed_after_comparison=True, raw_PART_files_rehashed_or_reparsed=False, historical_mutable_originals_checked_as_current=False, all22_raw_BI4_arrays_exact_claimed=False)
    except Exception as exc: result["failure"] = str(exc)
    result.update(inputs=list(BOUND.values()), files=[entry(metrics)] if metrics.exists() else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check))))
    return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
