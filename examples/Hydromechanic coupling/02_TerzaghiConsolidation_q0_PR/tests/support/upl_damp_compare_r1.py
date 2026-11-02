"""Pure offline damping compatibility/paired checks; no solver, decoder or physical acceptance."""
import argparse, copy, csv, hashlib, importlib.util, json, re, struct
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
STAGE = "upl_damp_compare_r1"
PARENT = T / "support/upl_column_public_exact_r1.py"
PIN = "d41fdb6c4003bf6ca65212c4c11449ec0dee89ce721b00c4adec3dd23482482f"
source = PARENT.read_bytes()
if hashlib.sha256(source).hexdigest() != PIN:
    raise ValueError("Pinned neutral export helpers changed before import")
base = importlib.util.module_from_spec(importlib.util.spec_from_file_location("damping_neutral_exports", PARENT))
exec(compile(source, str(PARENT), "exec"), base.__dict__)  # Neutral helpers only; old main/proof never called.
need, bind, adopt, entry, readjson = base.need, base.bind, base.adopt, base.entry, base.readjson
EXPORTS = ("original15.bin", "physical.bin", "clock.bin", "common_j_theta.bin", "soil_n.bin", "native_ids.csv", "fixed_ids.csv", "history.csv", "ledger.csv", "fixed_samples.csv", "last_poro.csv", "columns.csv")
SCHEMA = "case02_common26_col21_ExcessPorePress_NOT_wave26"
DYADIC = np.array(sorted(set(range(0, 65537, 64)) | set(range(5120, 5377))), dtype=np.int64)
DECIMAL = np.array(list(range(0, 3991, 10)) + list(range(3991, 4011)) + list(range(4020, 5001, 10)) + list(range(5020, 10001, 20)), dtype=np.int64)

def mapped(e, header, dtype, count):
    p = bind(e)
    with p.open("rb") as f:
        need(struct.unpack("<" + "I" * len(header), f.read(4 * len(header))) == header, "Binary header differs")
    dtype = np.dtype(dtype)
    need(p.stat().st_size == 4 * len(header) + count * dtype.itemsize, "Binary payload length differs")
    return np.memmap(p, mode="r", offset=4 * len(header), dtype=dtype, shape=(count,))

def input_proof(r, window):
    m = readjson(bind(r["input_manifest"]))
    need(m["stage"] == "upl_damp_prepare_r1" and m["passed"] and m["prepared"], "Own damping preparation rejected")
    rows = [j for j in m["jobs"] if j["window"] == window]
    need(len(rows) == 1 and rows[0] == r["job"], "Own prepared job differs")
    j = rows[0]
    need(j["inverse_DOM_exact"] and j["physics_changed_only_in_declared_damping_nodes"] and j["damping"] == 1 and j["damping_coef"] == (0 if window == "eta0" else .02), "Declared damping-only input differs")
    old = readjson(bind(j["source_manifest"]))
    rows = [v for v in old["jobs"] if v["window"] == ("coarse" if window == "eta0" else window)]
    need(len(rows) == 1, "Retained source job ambiguous")
    o = rows[0]
    for key in ("dt_s", "end_s", "steps", "expected_samples"):
        need(j[key] == o[key], "Damping input changed retained clocks: " + key)
    need(j["source_runtime"] == o["runtime"] and j["runtime"]["sha256"] == j["configuration"]["sha256"], "Prepared XML provenance differs")
    for key in ("initial_BI4", "normals"):
        bind(j[key]); bind(o[key]); need(j[key]["bytes"] == o[key]["bytes"] and j[key]["sha256"] == o[key]["sha256"], "Prepared seed/Normals changed")
    current = ET.parse(bind(j["runtime"])).getroot(); original = ET.parse(bind(j["source_runtime"])).getroot()
    for root in (current, original):
        for n in root.iter():
            if n.text is not None and not n.text.strip(): n.text = None
            if n.tail is not None and not n.tail.strip(): n.tail = None
    cp, op = current.find("execution/parameters"), original.find("execution/parameters")
    need(cp is not None and op is not None, "Parameters missing")
    for key, value in (("SoilDamping", 1.), ("SoilDampingCoef", 0. if window == "eta0" else .02)):
        cn, on = cp.findall("parameter[@key='" + key + "']"), op.findall("parameter[@key='" + key + "']")
        need(len(cn) == len(on) == 1 and float(cn[0].get("value")) == value, "Damping node differs")
        index = list(cp).index(cn[0]); cp.remove(cn[0]); cp.insert(index, copy.deepcopy(on[0]))
    need(ET.tostring(current) == ET.tostring(original), "Input differs outside the two damping nodes")

def dataset(backend, window, historical=False):
    tag = ("upl_column_public_" + backend + "_coarse_r1" if historical == "public" else "upl_column_cost_r1_" + ("cpu1" if backend == "CPU" else "gpu")) if historical else "upl_damp_" + backend + "_" + window + "_r1"
    ce = adopt(T / "logs" / (tag + ".native.json")); c = readjson(ce["path"])
    need(c["passed"] and c["physical_acceptance"] is False and c["backend"] == backend and c["window"] == ("coarse" if historical else window), "Native owner/backend/window rejected")
    need(c["source_inputs_raw_objects_runtime_canonical_unchanged"] if historical else c["bindings_unchanged"] and c["original_native_guards_passed"], "Native sealed closure rejected")
    if not historical:
        need(c["stage"] == "upl_damp_native_r1", "Wrong current native stage")
        for e in c["inputs"]: bind(e)
    q = readjson(bind(c["completion"])); n = 769 if historical or window == "eta0" else (3 if window == "smoke" else 1277)
    dt = 2.5e-6 if n == 769 else 2. ** (-20 if window == "half" else -19)
    steps = DECIMAL if n == 769 else (np.arange(3, dtype=np.int64) if n == 3 else DYADIC * (2 if window == "half" else 1))
    times = steps * dt; end = .025 if n == 769 else (2 * dt if n == 3 else .125)
    need(q["passed"] and q["physical_acceptance"] is False and q["backend"] == backend + "_public" and q["physical_schema"] == SCHEMA and q["model"] == "constant", "Typed completion differs")
    need((q["samples"], q["native_count"], q["fixed_count"], q["total_native_count"], q["physical_columns"], q["native_total_arrays"]) == (n, 1000, 40, 1040, 26, 22), "Native22/1040/header scope differs")
    need(q["PART_typed_public_metadata_verified"] and q["public_master_on"] and q["no_exclusions"] and q["all_exported_physical_fields_finite"] and q["actual_time_step_locked_dt_exact"] and q["planned_completed_steps"] == int(steps[-1]) and q["dt_s"] == dt and abs(q["actual_end_s"] - end) <= 1e-14 and q["max_ledger_relative_error"] <= 5e-13, "Native safety/clock/ledger rejected")
    if n != 769: need(q["stage"] == "upl_column_ringdown_native_r1" and q["preset"] == window, "Dyadic reader preset differs")
    else: need(q["stage"] == "upl_column_public_native_r1" and q["window"] == "window25" and q["grid"] == "c", "Public025 reader preset differs")
    r = readjson(bind(c["source_run"]))
    need(r["passed"] and r["physical_acceptance"] is False and r["backend"] == backend and r["public_project_main"] and not r["fixture_or_Run_override"] and r["source_inputs_objects_runtime_canonical_unchanged"] and r["native_frames"] == n, "Own actual main Run rejected")
    if not historical:
        need(r["stage"] == "upl_damp_run_r1" and r["window"] == window, "Wrong current Run job")
        for e in r["inputs"]: bind(e)
        input_proof(r, window)
    solver, reader = base.owned(r["call"]), base.owned(c["reader_call"])
    need(solver["target_program"] == r["program"] and solver["public_project_main"] and not solver["fixture_or_Run_override"], "Actual target/main differs")
    if backend == "GPU" and window == "smoke": need(r["memcheck_executed"] and r["memcheck_zero_errors_and_leaks"], "GPU smoke memory check missing")
    h = readjson(bind(c["reader_helper"])); need(h["passed"] and h["exact_link_closure_verified"] and h["program"] == reader["program"], "Owned reader/helper differs")
    expected_argv = ["--read", backend, str(Path(c["paths"]["solver_dir"]) / "data")] + (["769", "0.0000025"] if n == 769 else [window]) + [c["paths"]["native_dir"]]
    need(reader["arguments"] == expected_argv, "Actual reader argv differs")
    for e in r["files"]: bind(e)
    need({Path(e["path"]).name for e in r["files"] if re.fullmatch(r"Part_\d{4}\.bi4", Path(e["path"]).name)} == {f"Part_{i:04d}.bi4" for i in range(n)}, "Raw owned PART sequence differs")
    b = readjson(bind(r["source_build"])); need(b["passed"], "Actual source build rejected")
    if not historical:
        need(b["program"] == r["program"] and b["source_snapshot"] == r["source_snapshot"] and b["source_bindings_unchanged"] and b["canonical_programs_unchanged"] and b["exact_object_basename_closure"] and b["objects_include_project_main"] and len(b["objects"]) == (86 if backend == "CPU" else 111), "Own new build/program/source differs")
        bc = readjson(bind(b["project_call"])); need(bc["owned_call_exited"] and bc["typed_LASTEXITCODE_captured_immediately"] and type(bc["exit_code"]) is int and bc["exit_code"] == 0 and bc["program"] == b["build_tool"] and bc["arguments"] == b["arguments"] and not bc.get("invocation_failure"), "Actual project build exit/vector rejected")
    else: need((b.get("program") or b.get("isolated_GPU_program")) == r["program"], "Historical build/actual main identity differs")
    need(len(r["source_snapshot"]) == 265 and len(r["runtime"]) == 4 and len(r["canonical_programs_before"]) == 7, "265/runtime4/canonical7 closure differs")
    for row in r["source_snapshot"]:
        bind(row["snapshot"]); need(row["original"]["sha256"] == row["snapshot"]["sha256"], "Source snapshot differs")
        if not historical: bind(row["original"])
    bind(r["documentation_snapshot"]["snapshot"])
    for row in r["runtime"]: bind(row["copy"])
    # Historical current-source originals, canonical files and old inputs are deliberately not traversed.
    files = base.leaves(c); need(set(files) == set(EXPORTS) | {"completion.json"}, "Native13 leaves differ")
    p = mapped(files["physical.bin"], (1000, 26, n), [("time", "<f8"), ("q", "<f8", (1000, 26))], n)
    clock = mapped(files["clock.bin"], (n, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")], n)
    jt = mapped(files["common_j_theta.bin"], (1040, 2, n), [("time", "<f8"), ("q", "<f8", (1040, 2))], n)
    por = mapped(files["soil_n.bin"], (1000, 1, n), [("time", "<f8"), ("q", "<f8", (1000,))], n)
    with bind(files["original15.bin"]).open("rb") as f: need(struct.unpack("<III", f.read(12)) == (1040, 15, n) and files["original15.bin"]["bytes"] == 12 + n * 166408, "Original1040 typed15 header/length differs")
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f: cols = list(csv.DictReader(f))
    need([v["name"] for v in cols] == base.FIELDS and [int(v["column"]) for v in cols] == list(range(26)), "Common26 columns/ExcessPorePress21 differ")
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8"); fixed = np.genfromtxt(bind(files["fixed_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(1000)) and np.array_equal(fixed["id"], np.arange(40)) and np.array_equal(fixed["row"], np.arange(40)), "Original1040 native IDs/order differs")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    need(np.array_equal(np.where(np.arange(n) == 0, 0, clock["step"].astype(np.int64) + 1), steps) and np.all(clock["dt"] == dt) and np.isfinite(clock["time"]).all() and np.max(np.abs(clock["time"] - times)) <= 1e-14, "Actual saved steps/dt/time differ")
    need(all(base.bits(a["time"], clock["time"]).all() for a in (p, jt, por)) and base.bits(p["q"][0, :, :3], x0).all() and np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Native time bits/initial coordinates/signed-step safety differ")
    return dict(check=ce, run=c["source_run"], build=r["source_build"], program=r["program"], files=files, p=p, clock=clock, x0=x0, n=n)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--case", required=True, choices=("CPU_eta0_exact", "GPU_eta0_exact", "CPU_half", "cross_smoke", "cross_coarse")); case = ap.parse_args().case
    stem = "upl_damp_" + case + "_r1"; check = T / "logs" / (stem + ".check.json"); metrics = T / "logs" / (stem + ".csv")
    need(not check.exists() and not metrics.exists(), "Retained comparison protected")
    result = dict(stage=STAGE, case=case, passed=False, physical_acceptance=False, solver_decoder_or_build_invoked=False, failure=None)
    try:
        adopt(__file__); adopt(T / "notes/upl_damp_plan_r1.json"); need(adopt(PARENT)["sha256"] == PIN, "Neutral helper pin differs")
        exact = case.endswith("_eta0_exact")
        if exact:
            backend = case.split("_")[0]; a, b = dataset(backend, "eta0"), dataset(backend, "eta0", True)
            proof = adopt(T / "logs" / ("upl_column_cost_r1_" + ("cpu1" if backend == "CPU" else "gpu") + ".exact.json")); old = readjson(proof["path"])
            need(old["passed"] and old["gates"]["all12_named_exports_exact"] and old["native_checks"][0] == b["check"], "Retained cost-to-original-public025 exact proof rejected")
            public = dataset(backend, "eta0", "public"); need(old["native_checks"][1] == public["check"], "Original public025 control identity differs")
            equal = {leaf: all(a["files"][leaf][k] == e[k] for e in (b["files"][leaf], public["files"][leaf]) for k in ("bytes", "sha256")) for leaf in EXPORTS}
            with metrics.open("x", encoding="utf-8", newline="") as f:
                w = csv.writer(f); w.writerow(["export", "bytes", "new_eta0_equals_cost_and_original_public_bytes"]); w.writerows((k, a["files"][k]["bytes"], v) for k, v in equal.items())
            gates = dict(all12_saved_export_representations_exact=all(equal.values()))
            result.update(whole_export_files=equal, retained_cost_exact_proof=proof, original_public_native=public["check"], original_public_source_run=public["run"], original_public_source_build=public["build"], completion_whole_bytes_compared=False, all22_raw_BI4_arrays_exact_claimed=False, old_and_new_program_or_build_equality_required=False)
        else:
            a, b = (dataset("CPU", "coarse"), dataset("CPU", "half")) if case == "CPU_half" else (dataset("CPU", case.split("_")[1]), dataset("GPU", case.split("_")[1]))
            need(a["n"] == b["n"] and base.bits(a["x0"], b["x0"]).all() and base.bits(a["p"]["q"][0], b["p"]["q"][0]).all(), "Paired material/initial common26 differs")
            if case == "CPU_half": need(a["build"] == b["build"] and a["program"] == b["program"], "Half must use one actual build/program")
            gap = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"]))); pmax = umax = 0.; field_rms = np.zeros(26); field_abs = np.zeros(26)
            with metrics.open("x", encoding="utf-8", newline="") as f:
                w = csv.writer(f); w.writerow(["part", "A_actual_time_s", "B_actual_time_s", "pressure_RMS_Pa", "material_XYZ_difference_max_mm", "velocity_XYZ_RMS_m_s", "stress6_RMS_Pa"])
                for part in range(a["n"]):
                    av, bv = np.asarray(a["p"]["q"][part]), np.asarray(b["p"]["q"][part]); need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite common26 state")
                    d = av - bv; rms = np.sqrt(np.mean(d * d, axis=0)); ma = np.max(np.abs(d), axis=0); need(np.isfinite(rms).all() and np.isfinite(ma).all(), "Nonfinite paired reduction")
                    field_rms = np.maximum(field_rms, rms); field_abs = np.maximum(field_abs, ma); du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
                    p, u = float(rms[6]), float(1000 * np.max(np.linalg.norm(du, axis=1))); pmax, umax = max(pmax, p), max(umax, u)
                    w.writerow([part, float(a["clock"]["time"][part]), float(b["clock"]["time"][part]), p, u, float(np.sqrt(np.mean(np.sum(d[:, 3:6] ** 2, axis=1)))), float(np.sqrt(np.mean(np.sum(d[:, 10:16] ** 2, axis=1))))])
            gates = dict(pressure_RMS_all_times_le_5Pa=pmax <= 5., material_XYZ_difference_all_times_le_0_005mm=umax <= .005, actual_time_difference_le_1e_minus14_s=gap <= 1e-14)
            result.update(max_pressure_RMS_Pa=pmax, max_material_XYZ_displacement_difference_mm=umax, max_actual_time_difference_s=gap, max_common26_RMS=dict(zip(base.FIELDS, map(float, field_rms))), max_common26_abs=dict(zip(base.FIELDS, map(float, field_abs))), other_common26_metrics_descriptive=True, no_interpolation_or_time_snap=True)
        for e in list(base.BOUND.values()): need(entry(e["path"]) == e, "Input changed during offline comparison")
        result.update(passed=bool(all(gates.values())), gates=gates, samples=a["n"], native_count=1000, fixed_count=40, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_builds=[a["build"], b["build"]], historical_mutable_originals_checked_as_current=False)
    except Exception as exc: result["failure"] = str(exc)
    result.update(inputs=list(base.BOUND.values()), files=[entry(metrics)] if metrics.exists() else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check))))
    return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
