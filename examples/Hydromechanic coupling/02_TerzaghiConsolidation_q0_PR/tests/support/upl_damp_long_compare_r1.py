"""Offline .5s CPU damping prefix/half checks; no solver, decoder or physical acceptance."""
import argparse, copy, csv, hashlib, importlib.util, json, re, struct
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
STAGE = "upl_damp_long_compare_r1"
PINS = {
    "support/upl_damp_compare_r3.py": "34b2cfe642505df3b5a537631d88acf5c353b816f6f0665c5d1a34ba40c99e73",
    "notes/upl_damp_compare_r3.json": "d3ab86391a3434d8b7680282c8887461f3a4a930004a9eee08360c3dd362965f",
}
parent_path = T / "support/upl_damp_compare_r3.py"
parent_bytes = parent_path.read_bytes()
if hashlib.sha256(parent_bytes).hexdigest() != PINS["support/upl_damp_compare_r3.py"]:
    raise ValueError("Pinned neutral comparator source changed before import")
parent = importlib.util.module_from_spec(importlib.util.spec_from_file_location("long_damping_neutral", parent_path))
exec(compile(parent_bytes, str(parent_path), "exec"), parent.__dict__)  # Its main/dataset are never invoked here.
base = parent.base
need, bind, entry, readjson, mapped = parent.need, parent.bind, parent.entry, parent.readjson, parent.mapped
FIELDS = base.FIELDS
STEPS = np.array(sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) | set(range(66560, 262145, 1024))), dtype=np.int64)
SHORT, LONG = 1277, 1469
BINARY = {"original15.bin": (12, 166408), "physical.bin": (12, 208008), "clock.bin": (8, 28), "common_j_theta.bin": (12, 16648), "soil_n.bin": (12, 8008)}
IDENTITY = ("native_ids.csv", "fixed_ids.csv", "columns.csv")
TEXT = ("history.csv", "ledger.csv", "fixed_samples.csv")

def adopt(path):
    """Hash each resolved input path once initially; bind() shares this same cache."""
    key = str(Path(path).resolve())
    if key not in base.BOUND: base.BOUND[key] = entry(key)
    return base.BOUND[key]

# Record already-read pinned bytes without reopening that file merely to hash it again.
base.BOUND[str(parent_path.resolve())] = dict(path=str(parent_path.resolve()), bytes=len(parent_bytes), sha256=PINS["support/upl_damp_compare_r3.py"])
for relative, pin in PINS.items(): need(adopt(T / relative)["sha256"] == pin, "Pinned dependency differs: " + relative)
adopt(parent.PARENT)  # r3 already verified this neutral source before compiling its bytes.

def xml_root(e):
    root = ET.parse(bind(e), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))).getroot()
    for node in root.iter():
        if node.text is not None and not node.text.strip(): node.text = None
        if node.tail is not None and not node.tail.strip(): node.tail = None
    return root

def input_proof(r, window, long):
    m = readjson(bind(r["input_manifest"])); j = r["job"]
    need(m["stage"] == ("upl_damp_long_prepare_r1" if long else "upl_damp_prepare_r1") and m["passed"] and m["prepared"] and m["physical_acceptance"] is False, "Own prepared input rejected")
    rows = [v for v in m["jobs"] if v["window"] == window]
    need(len(rows) == 1 and rows[0] == j and j["damping"] == 1 and j["damping_coef"] == .02, "Own prepared job/material differs")
    if not long:
        parent.input_proof(r, window)  # Frozen two-damping-node proof only, not its dataset/main.
        return j
    old = readjson(bind(j["source_manifest"])); rows = [v for v in old["jobs"] if v["window"] == window]
    need(old["stage"] == "upl_damp_prepare_r1" and old["passed"] and old["prepared"] and len(rows) == 1, "Retained short preparation rejected")
    o = rows[0]
    need(j["inverse_DOM_exact"] and j["physics_and_first_three_timeouts_unchanged"] and not j["initial_particle_fields_rewritten"] and j["retained_prefix_samples"] == SHORT, "Declared input changes differ")
    need(j["source_configuration"] == o["configuration"] and j["source_runtime"] == o["runtime"] and j["dt_s"] == o["dt_s"] and j["steps"] == 4 * o["steps"] and o["end_s"] == .125 and j["end_s"] == .5 and o["expected_samples"] == SHORT and j["expected_samples"] == LONG, "Retained same-dt input/clock provenance differs")
    for key in ("initial_BI4", "normals"):
        bind(j[key]); bind(o[key]); need(all(j[key][k] == o[key][k] for k in ("bytes", "sha256")), "Seed/Normals bytes changed")
    bind(j["configuration"]); bind(o["configuration"])
    need(j["runtime"]["sha256"] == j["configuration"]["sha256"] and o["runtime"]["sha256"] == o["configuration"]["sha256"], "Runtime/configuration copy differs")
    current, original = xml_root(j["runtime"]), xml_root(o["runtime"])
    cp, op = current.find("execution/parameters"), original.find("execution/parameters")
    need(cp is not None and op is not None, "XML parameters missing")
    cn, on = cp.findall("parameter[@key='TimeMax']"), op.findall("parameter[@key='TimeMax']")
    ct, ot = current.find("execution/special/timeout"), original.find("execution/special/timeout")
    need(len(cn) == len(on) == 1 and float(cn[0].get("value")) == .5 and float(on[0].get("value")) == .125 and ct is not None and ot is not None, "TimeMax/timeout differs")
    nt, oldt = ct.findall("tout"), ot.findall("tout")
    need(len(nt) == 4 and len(oldt) == 3 and set(nt[3].attrib) == {"time", "timeout"} and float(nt[3].get("time")) == .125 and float(nt[3].get("timeout")) == 1024 * 2. ** -19, "Only the declared fourth timeout may be appended")
    cn[0].set("value", on[0].get("value")); ct.remove(nt[3])
    need(ET.tostring(current) == ET.tostring(original), "Input changed outside TimeMax/fourth timeout (including comments)")
    return j

def dataset(window, long=True):
    """Known CPU-only native schema; verify consumed immutable artifacts, not historical mutable originals."""
    need(window in ("coarse", "half"), "Unsupported window")
    tag = "upl_damp_long_CPU_" + window + "_r1" if long else "upl_damp_CPU_" + window + "_r2"
    ce = adopt(T / "logs" / (tag + ".native.json")); c = readjson(ce["path"])
    need(c["passed"] and c["stage"] == ("upl_damp_long_native_run_r1" if long else "upl_damp_native_r2") and c["physical_acceptance"] is False and c["backend"] == "CPU" and c["window"] == window and c["bindings_unchanged"] and c["original_native_guards_passed"] and c["drainage_nonempty_per_frame_verified"], "Sealed CPU native owner rejected")
    r = readjson(bind(c["source_run"])); n = LONG if long else SHORT; factor = 2 if window == "half" else 1
    steps = STEPS * factor if long else STEPS[:SHORT] * factor; dt = 2. ** (-20 if factor == 2 else -19); times = steps * dt; post = (1265 if long else 1073)
    need(r["passed"] and r["stage"] == ("upl_damp_long_run_r1" if long else "upl_damp_run_r1") and r["backend"] == "CPU" and r["window"] == window and r["configuration"] == "ReleaseCPU" and r["physical_acceptance"] is False and r["public_project_main"] and not r["fixture_or_Run_override"] and r["source_inputs_objects_runtime_canonical_unchanged"] and r["native_frames"] == n, "Own actual project-main Run rejected")
    if long: need(r["threads"] == 8 and c["source_build"] == r["source_build"], "Long CPU8/source identity differs")
    j = input_proof(r, window, long)
    need((j["dt_s"], j["end_s"], j["steps"], j["expected_samples"]) == (dt, float(times[-1]), int(steps[-1]), n), "Prepared preset differs")
    table = j["saved_clock_table"]; need(len(table) == n, "Manifest saved table length differs")
    for i, row in enumerate(table):
        need(type(row["part"]) is int and type(row["completed_steps"]) is int and type(row["saved_step"]) is int and (row["part"], row["completed_steps"], row["saved_step"]) == (i, int(steps[i]), int(steps[i] - 1) if i else 0) and struct.pack("<d", row["time_s"]) == struct.pack("<d", times[i]), "Raw JSON dyadic schedule differs")
    solver, reader = base.owned(r["call"]), base.owned(c["reader_call"])
    need(solver["target_program"] == r["program"] and solver["public_project_main"] and not solver["fixture_or_Run_override"], "Actual solver target differs")
    need(solver["arguments"] == ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", j["input_prefix"], c["paths"]["solver_dir"], "-dirdataout", "data", "-svres", "-nsteps:" + str(int(steps[-1]))], "Actual CPU8 solver argv differs")
    h = readjson(bind(c["reader_helper"])); need(h["passed"] and h["exact_link_closure_verified"] and h["program"] == reader["program"] and len(h["objects"]) == 85 and h["link_object_count"] == 86, "Real reader/helper85+1 differs")
    if long: need(h["stage"] == "upl_damp_long_reader_build_r1" and h["source_build"] == r["source_build"] and h["build_and_source_bindings_unchanged"] and not h["solver_started"], "Same-source long reader authority differs")
    for e in h["author_files"]: bind(e)
    for key in ("compile_call", "link_call"): base.owned(h[key])
    need(reader["arguments"] == ["--read", "CPU", str(Path(c["paths"]["solver_dir"]) / "data"), window, c["paths"]["native_dir"]], "Real reader CLI differs")
    b = readjson(bind(r["source_build"])); need(b["passed"] and b["stage"] == "upl_damp_build_r2" and b["configuration"] == "ReleaseCPU" and b["program"] == r["program"] and b["source_snapshot"] == r["source_snapshot"] and b["source_bindings_unchanged"] and b["canonical_programs_unchanged"] and b["runtime_unchanged"] and b["exact_object_basename_closure"] and b["objects_include_project_main"] and len(b["objects"]) == 86, "Actual same current CPU build86/source differs")
    bc = readjson(bind(b["project_call"])); need(bc["owned_call_exited"] and bc["typed_LASTEXITCODE_captured_immediately"] and type(bc["exit_code"]) is int and bc["exit_code"] == 0 and not bc.get("invocation_failure") and bc["program"] == b["build_tool"] and bc["arguments"] == b["arguments"], "Real project build exit/vector differs")
    bind(b["build_tool"]); bind(b["log"]); bind(b["binlog"]); bind(r["run_out"])
    need(len(r["source_snapshot"]) == 265 and len(r["runtime"]) == 4 and len(r["canonical_programs_before"]) == 7, "265/runtime4/canonical7 recorded scope differs")
    for row in r["source_snapshot"]:
        bind(row["snapshot"]); need(all(row["original"][k] == row["snapshot"][k] for k in ("bytes", "sha256")), "Retained source snapshot differs")
    bind(r["documentation_snapshot"]["snapshot"]); bind(b["case_readme_snapshot"]["snapshot"])
    for row in r["runtime"] + h["runtime"]: bind(row["copy"])
    raw = [Path(e["path"]).name for e in r["files"] if re.fullmatch(r"Part_\d{4}\.bi4", Path(e["path"]).name)]
    need(len(raw) == n and set(raw) == {f"Part_{i:04d}.bi4" for i in range(n)}, "Recorded raw PART ownership/sequence differs")
    # Run/native receipts already bind raw bytes/current closure. Do not rehash every raw PART or historical mutable original here.
    q = readjson(bind(c["completion"])); need(q["passed"] and q["stage"] == ("upl_damp_long_native_r1" if long else "upl_column_ringdown_native_r1") and q["window"] == ("damped500" if long else "ringdown125") and q["preset"] == window and q["backend"] == "CPU_public" and q["physical_acceptance"] is False and q["physical_schema"] == parent.SCHEMA and q["model"] == "constant", "Typed native completion/preset differs")
    need((q["samples"], q["native_count"], q["fixed_count"], q["total_native_count"], q["physical_columns"], q["native_total_arrays"]) == (n, 1000, 40, 1040, 26, 22) and q["PART_typed_public_metadata_verified"] and q["public_master_on"] and q["no_exclusions"] and q["all_exported_physical_fields_finite"], "Typed22/finite/no-loss schema guard rejected")
    need(q["max_ledger_relative_error"] <= 5e-13 and q["soil_ledger_checks"] == n * 1000 and q["fixed_public_zero_marker_checks"] == n * 40 and q["dt_s"] == dt and q["actual_end_s"] == float(times[-1]) and q["planned_completed_steps"] == int(steps[-1]) and q["declared_saved_completed_steps_exact"] and q["actual_time_step_locked_dt_exact"] and q["noninitial_signed_dterror_intervals"] == n - 1 and q["max_noninitial_signed_dterror_s"] <= 1e-14, "Original ledger/signed-step/clock guards rejected")
    need((q["post_open_frames"], q["post_open_drained_particle_checks"], q["max_activeDrainCount"], q["post_open_completed_step_threshold"]) == (post, post * 10, 10, 5243 * factor), "Nonempty original drainage coverage differs")
    files = base.leaves(c); need(set(files) == set(parent.EXPORTS) | {"completion.json"} and files["completion.json"] == c["completion"], "Native13 leaf set differs")
    p = mapped(files["physical.bin"], (1000, 26, n), [("time", "<f8"), ("q", "<f8", (1000, 26))], n)
    clock = mapped(files["clock.bin"], (n, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")], n)
    jt = mapped(files["common_j_theta.bin"], (1040, 2, n), [("time", "<f8"), ("q", "<f8", (1040, 2))], n)
    por = mapped(files["soil_n.bin"], (1000, 1, n), [("time", "<f8"), ("q", "<f8", (1000,))], n)
    with bind(files["original15.bin"]).open("rb") as f: need(struct.unpack("<III", f.read(12)) == (1040, 15, n) and files["original15.bin"]["bytes"] == 12 + n * 166408, "Original15 header/length differs")
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f: cols = list(csv.DictReader(f))
    need([v["name"] for v in cols] == FIELDS and [int(v["column"]) for v in cols] == list(range(26)), "Common26 field order differs")
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8"); fixed = np.genfromtxt(bind(files["fixed_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(1000)) and np.array_equal(fixed["id"], np.arange(40)) and np.array_equal(fixed["row"], np.arange(40)), "1040 original native IDs/order differs")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    need(np.array_equal(clock["step"].astype(np.int64), np.where(steps > 0, steps - 1, 0)) and base.bits(clock["dt"], np.full(n, dt)).all() and base.bits(clock["time"], times).all(), "Actual dyadic clock/zero-based saved Step differs")
    need(all(base.bits(v["time"], clock["time"]).all() for v in (p, jt, por)) and base.bits(p["q"][0, :, :3], x0).all() and np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Cross-export native time bits/initial coordinates/signed dterror differ")
    with bind(files["history.csv"]).open(encoding="utf-8-sig", newline="") as f: history = list(csv.DictReader(f))
    need(len(history) == n, "History row count differs")
    for i, row in enumerate(history):
        need(int(row["part"]) == i and int(row["completed_step"]) == int(steps[i]) and int(row["saved_step"]) == int(clock["step"][i]) and struct.pack("<d", float(row["time_s"])) == struct.pack("<d", times[i]) and float(row["dt_s"]) == dt and int(row["activeDrainCount"]) == (10 if steps[i] > 5243 * factor else 0), "Actual history clock/nonempty drain differs")
    return dict(check=ce, run=c["source_run"], build=r["source_build"], program=r["program"], files=files, p=p, clock=clock, x0=x0, n=n, job=j, history=history)

def prefix_bytes(new, old, offset, count):
    """Bounded exact comparison; offsets omit independently validated sample-count headers."""
    compared = 0
    with bind(new).open("rb") as a, bind(old).open("rb") as b:
        a.seek(offset); b.seek(offset)
        while compared < count:
            size = min(1024 * 1024, count - compared); av, bv = a.read(size), b.read(size)
            if len(av) != size or len(bv) != size: return False, compared
            if av != bv:
                return False, compared + next(i for i, (x, y) in enumerate(zip(av, bv)) if x != y)
            compared += size
    return True, None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--case", required=True, choices=("coarse_prefix", "half_prefix", "half")); case = ap.parse_args().case
    stem = "upl_damp_long_" + case + "_r1"; check = T / "logs" / (stem + ".check.json"); metrics = T / "logs" / (stem + ".csv")
    need(not check.exists() and not metrics.exists(), "Retained offline artifacts protected")
    result = dict(stage=STAGE, case=case, passed=False, physical_acceptance=False, solver_decoder_or_build_invoked=False, failure=None)
    try:
        adopt(__file__); adopt(T / "notes/upl_damp_long_compare_r1.json")
        prefix_checks = []
        if case == "half":
            for window in ("coarse", "half"):
                e = adopt(T / "logs" / ("upl_damp_long_" + window + "_prefix_r1.check.json")); proof = readjson(e["path"])
                need(proof["stage"] == STAGE and proof["case"] == window + "_prefix" and proof["passed"] and proof["physical_acceptance"] is False and proof["compared_prefix_samples"] == SHORT and proof["long_samples"] == LONG and all(proof["gates"][k] for k in ("all5_binary_payload_prefix_exact", "all3_identity_files_exact", "all3_text_prefix_exact", "same_build_program")), "Both exact prefix gates must precede half")
                for output in proof["files"]: bind(output)
                prefix_checks.append(e)
            a, b = dataset("coarse"), dataset("half")
            for e, d in zip(prefix_checks, (a, b)): need(readjson(e["path"])["long_native_check"] == d["check"], "Prefix gate belongs to another long native output")
        else: a, b = dataset(case.split("_")[0]), dataset(case.split("_")[0], long=False)
        same_program = a["build"] == b["build"] and a["program"] == b["program"]
        need(same_program, "Same retained current program/build required")
        if case != "half":
            rows = []
            for leaf, (offset, record) in BINARY.items():
                equal, first = prefix_bytes(a["files"][leaf], b["files"][leaf], offset, SHORT * record)
                rows.append([leaf, "payload_after_validated_header", SHORT * record, SHORT, equal, first])
            for leaf in IDENTITY:
                equal = all(a["files"][leaf][key] == b["files"][leaf][key] for key in ("bytes", "sha256")); rows.append([leaf, "whole_file", b["files"][leaf]["bytes"], None, equal, None])
            for leaf in TEXT:
                equal, first = prefix_bytes(a["files"][leaf], b["files"][leaf], 0, b["files"][leaf]["bytes"]); rows.append([leaf, "entire_retained_file_is_new_beginning", b["files"][leaf]["bytes"], SHORT, equal, first])
            with metrics.open("x", encoding="utf-8", newline="") as f:
                w = csv.writer(f); w.writerow(["export", "comparison", "compared_bytes", "prefix_frames", "exact", "first_differing_payload_or_file_byte"]); w.writerows(rows)
            gates = dict(all5_binary_payload_prefix_exact=all(row[4] for row in rows[:5]), all3_identity_files_exact=all(row[4] for row in rows[5:8]), all3_text_prefix_exact=all(row[4] for row in rows[8:]), same_build_program=same_program)
            result.update(long_native_check=a["check"], retained_short_native_check=b["check"], compared_prefix_samples=SHORT, long_samples=LONG, exact_prefix_rows=rows, binary_headers_independently_validated=True, last_poro_endpoint_compared_as_prefix=False, completion_whole_bytes_compared=False, signed_dterror_in_clock_prefix=True, all22_raw_BI4_arrays_exact_claimed=False)
        else:
            need(base.bits(a["x0"], b["x0"]).all() and base.bits(a["p"]["q"][0], b["p"]["q"][0]).all(), "All26 initial fields/material coordinates must match bitwise")
            gap = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"]))); pmax = umax = 0.; rmsmax = np.zeros(26); absmax = np.zeros(26)
            with metrics.open("x", encoding="utf-8", newline="") as f:
                w = csv.writer(f); w.writerow(["part", "A_actual_time_s", "B_actual_time_s", "pressure_RMS_Pa", "material_XYZ_difference_max_mm", "velocity_XYZ_RMS_m_s", "stress6_RMS_Pa"])
                for i in range(LONG):
                    av, bv = np.asarray(a["p"]["q"][i]), np.asarray(b["p"]["q"][i]); need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite common26 field")
                    d = av - bv; rms, ma = np.sqrt(np.mean(d * d, axis=0)), np.max(np.abs(d), axis=0); need(np.isfinite(rms).all() and np.isfinite(ma).all(), "Nonfinite paired reduction")
                    rmsmax, absmax = np.maximum(rmsmax, rms), np.maximum(absmax, ma); du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
                    p, u = float(rms[6]), float(1000 * np.max(np.linalg.norm(du, axis=1))); pmax, umax = max(pmax, p), max(umax, u)
                    w.writerow([i, float(a["clock"]["time"][i]), float(b["clock"]["time"][i]), p, u, float(np.sqrt(np.mean(np.sum(d[:, 3:6] ** 2, axis=1)))), float(np.sqrt(np.mean(np.sum(d[:, 10:16] ** 2, axis=1))))])
            gates = dict(pressure_RMS_all_times_le_5Pa=pmax <= 5., material_XYZ_difference_all_times_le_0_005mm=umax <= .005, actual_time_difference_le_1e_minus14_s=gap <= 1e-14)
            result.update(prefix_checks=prefix_checks, initial26_bit_exact=True, samples=LONG, max_pressure_RMS_Pa=pmax, max_material_XYZ_displacement_difference_mm=umax, max_actual_time_difference_s=gap, max_common26_RMS=dict(zip(FIELDS, map(float, rmsmax))), max_common26_abs=dict(zip(FIELDS, map(float, absmax))), other_common26_metrics_descriptive=True, no_interpolation_or_time_snap=True)
        for e in list(base.BOUND.values()): need(entry(e["path"]) == e, "Consumed artifact changed during offline comparison")
        result.update(passed=bool(all(gates.values())), gates=gates, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_builds=[a["build"], b["build"]], native_count=1000, fixed_count=40, historical_mutable_originals_checked_as_current=False, raw_PART_file_hashes_recomputed=False, raw_PART_byte_equivalence_claimed=False, consumed_artifacts_rehashed_after_comparison=True)
    except Exception as exc: result["failure"] = str(exc)
    result.update(inputs=list(base.BOUND.values()), files=[entry(metrics)] if metrics.exists() else [])
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check))))
    return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
