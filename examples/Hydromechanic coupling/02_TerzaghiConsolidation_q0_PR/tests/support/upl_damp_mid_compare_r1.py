"""One offline1746-to1469 typed-export prefix check; no solver/decoder/half/theory."""
import csv, hashlib, importlib.util, json, re, struct
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
STAGE, N, PREFIX, DT, END_STEP = "upl_damp_mid_compare_r1", 1746, 1469, 2. ** -19, 4798782
EVENT, END = 5243 * DT, END_STEP * DT
STEPS = np.array(sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) | set(range(66560, 262145, 1024)) | set(range(278528, 4784129, 16384)) | {END_STEP}), dtype=np.int64)
PINS = {"support/upl_damp_long_compare_r1.py": "c838ed61d940c078339ac5b630718649e625731bd05f25304d80b16f659bd601", "notes/upl_damp_long_compare_r1.json": "3155d8dd579ed5d94ee7f5ef4102f710d5d628876d0d671ed798d99dc91a8780"}
BOUND = {}  # Casefolded resolved path -> actually verified Entry, never an unverified expectation.

def need(ok, why):
    if not bool(ok): raise ValueError(why)
def entry(path):
    p = Path(path).resolve(); digest = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): digest.update(block)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest.hexdigest())
def register(e):
    e = dict(path=str(Path(e["path"]).resolve()), bytes=e["bytes"], sha256=e["sha256"].lower()); key = e["path"].casefold()
    if key in BOUND: need(all(BOUND[key][k] == e[k] for k in ("bytes", "sha256")), "Conflicting verified Entries: " + e["path"])
    else: BOUND[key] = e
    return BOUND[key]
def adopt(path):
    p = Path(path).resolve(); key = str(p).casefold()
    return BOUND[key] if key in BOUND else register(entry(p))
def bind(e):
    a = adopt(e["path"]); need(type(e["bytes"]) is int and a["bytes"] == e["bytes"] and a["sha256"] == e["sha256"].lower(), "Changed/conflicting bound artifact: " + e["path"]); return Path(a["path"])
def readjson(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))

# Verify the old source bytes before execution; neither old main nor data loader runs at import.
rel = "support/upl_damp_long_compare_r1.py"; source_path = T / rel; source = source_path.read_bytes()
need(hashlib.sha256(source).hexdigest() == PINS[rel], "Pinned retained loader source changed")
register(dict(path=str(source_path), bytes=len(source), sha256=PINS[rel]))
retained = importlib.util.module_from_spec(importlib.util.spec_from_file_location("mid_retained_long_exports", source_path))
exec(compile(source, str(source_path), "exec"), retained.__dict__)
for rel, pin in PINS.items(): need(adopt(T / rel)["sha256"] == pin, "Pinned retained dependency changed: " + rel)
def merge_retained_cache():
    for e in retained.base.BOUND.values(): register(e)  # These were verified by the pinned loader, not merely declared in a receipt.
merge_retained_cache()
FIELDS, bits = retained.FIELDS, retained.base.bits
BINARY, IDENTITY, TEXT = retained.BINARY, retained.IDENTITY, retained.TEXT

def owned(e):
    c = readjson(bind(e)); need(c["direct_native_call"] and c["owned_call_exited"] and c["typed_LASTEXITCODE_captured_immediately"] and type(c["exit_code"]) is int and c["exit_code"] == 0 and not c.get("invocation_failure"), "Own direct typed exit0 required")
    bind(c["program"]); bind(c["log"])
    if c.get("target_program"): bind(c["target_program"])
    return c
def mapped(e, header, dtype, count):
    p = bind(e); dtype = np.dtype(dtype)
    with p.open("rb") as f: need(struct.unpack("<" + "I" * len(header), f.read(4 * len(header))) == header, "Binary header differs: " + p.name)
    need(e["bytes"] == p.stat().st_size == 4 * len(header) + count * dtype.itemsize, "Binary payload length differs: " + p.name)
    return np.memmap(p, mode="r", offset=4 * len(header), dtype=dtype, shape=(count,))
def xml(e):
    root = ET.parse(bind(e), parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))).getroot()
    for node in root.iter():
        if node.text is not None and not node.text.strip(): node.text = None
        if node.tail is not None and not node.tail.strip(): node.tail = None
    return root
def input_proof(r):
    m = readjson(bind(r["input_manifest"])); j = r["job"]
    need(m["stage"] == "upl_damp_mid_prepare_r1" and m["passed"] and m["prepared"] and m["physical_acceptance"] is False and not m["step_candidate_adopted"] and m["source_build"] == r["source_build"] and m["source_program"] == r["program"] and len(m["jobs"]) == 1 and m["jobs"][0] == j, "Own fallback Prepare/job/build rejected")
    need((j["window"], j["backend"], j["threads"], j["dt_s"], j["end_s"], j["steps"], j["expected_samples"], j["damping"], j["damping_coef"]) == ("coarse", "CPU", 8, DT, END, END_STEP, N, 1, .02) and j["inverse_DOM_exact"] and j["inverse_text_and_bytes_exact"] and j["only_TimeMax_and_fifth_timeout_changed"] and not j["initial_particle_fields_rewritten"] and not j["step_candidate_adopted"] and j["planned_original_prefix_samples"] == PREFIX and not j["actual_prefix_proved"], "Own unchanged physics/dt/event declaration differs")
    need((j["event_completed_step"], j["event_part"], j["first_post_open_part"], j["post_open_frames"], j["samples_through_0p5"], j["ramp_and_drain_event_s"]) == (5243, 203, 204, 1542, PREFIX, EVENT), "Declared event/prefix differs")
    old = readjson(bind(j["source_manifest"])); rows = [v for v in old["jobs"] if v["window"] == "coarse"]
    need(old["stage"] == "upl_damp_long_prepare_r1" and old["passed"] and old["prepared"] and old["physical_acceptance"] is False and len(rows) == 1 and m["source_manifest"] == j["source_manifest"], "Accepted oldlong input provenance differs"); o = rows[0]
    need(j["source_configuration"] == o["configuration"] and j["source_runtime"] == o["runtime"] and (o["dt_s"], o["end_s"], o["steps"], o["expected_samples"]) == (DT, .5, 262144, PREFIX), "Accepted same-dt coarse source differs")
    for k in ("configuration", "runtime", "initial_BI4", "normals"): bind(j[k]); bind(o[k])
    for k in ("initial_BI4", "normals"): need(all(j[k][v] == o[k][v] for v in ("bytes", "sha256")), "Unchanged seed/Normals differ")
    need(all(j["configuration"][v] == j["runtime"][v] and o["configuration"][v] == o["runtime"][v] for v in ("bytes", "sha256")), "Runtime/configuration copy differs")
    current, original = xml(j["runtime"]), xml(o["runtime"]); cp, op = current.find("execution/parameters"), original.find("execution/parameters")
    cn, on = cp.findall("parameter[@key='TimeMax']"), op.findall("parameter[@key='TimeMax']"); ct, ot = current.find("execution/special/timeout"), original.find("execution/special/timeout")
    need(len(cn) == len(on) == 1 and float(cn[0].get("value")) == END and float(on[0].get("value")) == .5 and ct is not None and ot is not None, "TimeMax/timeout differs")
    nt, oldt = ct.findall("tout"), ot.findall("tout"); need(len(nt) == 5 and len(oldt) == 4 and all(a.attrib == b.attrib for a, b in zip(nt[:4], oldt)) and nt[4].attrib == {"time": "0.5", "timeout": "0.03125"}, "Only fifth late timeout may change")
    cn[0].set("value", on[0].get("value")); ct.remove(nt[4]); need(ET.tostring(current) == ET.tostring(original), "XML differs beyond TimeMax/fifth timeout, including comments")
    table = j["saved_clock_table"]; need(len(table) == N, "Raw JSON schedule length differs")
    for i, row in enumerate(table): need(all(type(row[k]) is int for k in ("part", "completed_steps", "saved_step")) and (row["part"], row["completed_steps"], row["saved_step"]) == (i, int(STEPS[i]), int(STEPS[i] - 1) if i else 0) and struct.pack("<d", row["time_s"]) == struct.pack("<d", float(STEPS[i] * DT)), "Raw JSON integer/dyadic schedule differs")
    return j

def dataset():
    """Own completed1746 coarse only. No current-production-original/canonical or raw-PART rehash."""
    tag = "upl_damp_mid_CPU_coarse_r1"; ce = adopt(T / "logs" / (tag + ".native.json")); c = readjson(bind(ce))
    need(c["stage"] == "upl_damp_mid_native_run_r1" and c["passed"] and c["physical_acceptance"] is False and c["backend"] == "CPU" and c["window"] == "coarse" and c["original_native_guards_passed"] and c["drainage_nonempty_per_frame_verified"] and c["frozen_build_program_inputs_runtime_unchanged"] and not c["live_production_sources_frozen_by_this_run"] and not c["adopted_completed_reader"] and not c["actual_prefix_proved"], "Own completed frozen native authority rejected")
    r = readjson(bind(c["source_run"])); need(r["stage"] == "upl_damp_mid_run_r1" and r["passed"] and r["physical_acceptance"] is False and (r["backend"], r["threads"], r["window"], r["configuration"], r["native_frames"]) == ("CPU", 8, "coarse", "ReleaseCPU", N) and (r["planned_completed_steps"], r["planned_end_s"], r["expected_native_frames"]) == (END_STEP, END, N) and r["locked_runtime_clock_values_verified"] and r["public_project_main"] and not r["fixture_or_Run_override"] and r["frozen_build_program_inputs_runtime_unchanged"] and not r["live_production_sources_frozen_by_this_run"] and not r["step_candidate_adopted"] and not r["actual_prefix_proved"] and c["source_build"] == r["source_build"], "Own actual CPU8 frozen project-main Run rejected")
    j = input_proof(r); solver, reader = owned(r["call"]), owned(c["reader_call"])
    need(solver["program"] == solver["target_program"] == r["program"] and solver["public_project_main"] and not solver["fixture_or_Run_override"] and solver["direct_target_call"], "Own actual solver target differs")
    need(solver["arguments"] == ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", j["input_prefix"], c["paths"]["solver_dir"], "-dirdataout", "data", "-svres", "-nsteps:" + str(END_STEP)] and reader["arguments"] == ["--read", "CPU", str(Path(c["paths"]["solver_dir"]) / "data"), "coarse", c["paths"]["native_dir"]] and reader["pure_native_reader"] and not reader["solver_or_build_invoked"], "Actual solver/reader argv differs")
    bind(r["run_out"]); gate = readjson(bind(r["admission"])); need(gate["stage"] == "upl_damp_mid_admission_r1" and gate["passed"] and gate["physical_acceptance"] is False and gate["allowed_jobs"] == [tag], "Singleton own Run admission differs")
    for e in r["inputs"]: bind(e)  # NEW flat frozen inputs, not old r.inputs or native c.inputs containing all raw PARTs.
    b = readjson(bind(r["source_build"])); need(b["stage"] == "upl_damp_build_r2" and b["passed"] and b["configuration"] == "ReleaseCPU" and b["program"] == r["program"] and b["objects_include_project_main"] and b["exact_object_basename_closure"] and len(b["objects"]) == 86, "Actual frozen main build86 differs")
    bc = readjson(bind(b["project_call"])); need(bc["direct_native_call"] and bc["owned_call_exited"] and bc["typed_LASTEXITCODE_captured_immediately"] and type(bc["exit_code"]) is int and bc["exit_code"] == 0 and not bc.get("invocation_failure") and bc["program"] == b["build_tool"] and bc["arguments"] == b["arguments"], "Original real project exit/vector differs")
    for e in (b["build_tool"], b["log"], b["binlog"]): bind(e)
    snaps = [v["snapshot"] for v in b["source_snapshot"]]; need(len(snaps) == 265 and r["source_snapshots265"] == snaps and r["retained_build_objects"] == b["objects"] and len(r["runtime_copies"]) == 4 and r["runtime_copies"] == [v["copy"] for v in b["runtime"]], "NEW flat snapshots265/objects86/runtime4 differ")
    for row in b["source_snapshot"]: need(all(row["original"][k] == row["snapshot"][k] for k in ("bytes", "sha256")), "Recorded as-of-build source snapshot identity differs")
    need(r["documentation_snapshot"] == b["documentation_snapshot"]["snapshot"] and r["case_readme_snapshot"] == b["case_readme_snapshot"]["snapshot"], "Archived doc/README identity differs")
    for e in snaps + r["retained_build_objects"] + r["runtime_copies"] + [r["documentation_snapshot"], r["case_readme_snapshot"]]: bind(e)
    h = readjson(bind(c["reader_helper"])); need(h["stage"] == "upl_damp_mid_reader_build_r1" and h["passed"] and h["status"] == "frozen_damp_mid_CPU_reader_linked_not_run" and h["kind"] == "reader" and h["configuration"] == "ReleaseCPU" and h["source_build"] == r["source_build"] and h["program"] == reader["program"] and h["exact_link_closure_verified"] and h["frozen_build_program_inputs_runtime_unchanged"] and h["actual_headers_archived_not_live"] and h["project_header_include_remaps"] == 1 and not h["solver_started"] and h["source_snapshots265"] == snaps and h["documentation_snapshot"] == r["documentation_snapshot"] and h["case_readme_snapshot"] == r["case_readme_snapshot"], "Own archived-header reader authority differs")
    expected = [e for e in b["objects"] if Path(e["path"]).name.lower() != "main.obj"]; need(h["objects"] == expected and len(expected) == 85 and h["link_object_count"] == 86 and len(h["libraries"]) == 17 and len(h["runtime"]) == 4 and len(h["actual_project_headers"]) == 8, "Actual reader85+1/library17/header8 closure differs")
    for e in h["author_files"] + h["tools"] + h["libraries"] + h["actual_project_headers"] + [h["helper_object"], h["compiler_dependency_record"], h["neutral_include"]]: bind(e)
    cc, lc = owned(h["compile_call"]), owned(h["link_call"]); objects = [str(Path(a).resolve()).casefold() for a in lc["arguments"] if a.lower().endswith(".obj")]
    need(len(objects) == 86 and len(set(objects)) == 86 and set(objects) == {str(Path(e["path"]).resolve()).casefold() for e in expected + [h["helper_object"]]}, "Actual linker did not use exact85+1 objects")
    need([Path(a).name.lower() for a in lc["arguments"] if a.lower().endswith(".lib")] == [Path(e["path"]).name.lower() for e in h["libraries"]], "Actual ordered17 libraries differ")
    dep = readjson(bind(h["compiler_dependency_record"]))["Data"]; root = Path(h["archived_header_include_root"]).resolve(); includes = {str(Path(v).resolve()).casefold() for v in dep["Includes"]}; project = {str(Path(v).resolve()).casefold() for v in dep["Includes"] if Path(v).resolve().parent == root}
    need(Path(dep["Source"]).resolve() == (T / "support/upl_damp_mid_native_r1.cpp").resolve() and project == {str(Path(e["path"]).resolve()).casefold() for e in h["actual_project_headers"]} and all(e in snaps for e in h["actual_project_headers"]) and h["neutral_include"]["sha256"] == "9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38" and str(Path(h["neutral_include"]["path"]).resolve()).casefold() in includes, "Actual archived header/neutral include dependency differs")
    for pair in h["runtime"]:
        need(pair["original"] in r["runtime_copies"] and all(pair["original"][k] == pair["copy"][k] for k in ("bytes", "sha256")), "Own reader runtime copy differs"); bind(pair["original"]); bind(pair["copy"])
    raw = [Path(e["path"]) for e in r["files"] if re.fullmatch(r"Part_\d{4}\.bi4", Path(e["path"]).name)]; need(len(raw) == N and {p.name for p in raw} == {f"Part_{i:04d}.bi4" for i in range(N)} and all(p.resolve().parent == (Path(c["paths"]["solver_dir"]) / "data").resolve() for p in raw), "Recorded actual raw PART ownership/sequence differs")
    q = readjson(bind(c["completion"])); need(q["passed"] and (q["stage"], q["backend"], q["window"], q["preset"], q["grid"], q["model"], q["physical_schema"]) == ("upl_damp_mid_native_r1", "CPU_public", "mid", "coarse", "c", "constant", retained.parent.SCHEMA) and q["physical_acceptance"] is False, "Own typed completion/preset differs")
    need((q["samples"], q["native_count"], q["fixed_count"], q["total_native_count"], q["physical_columns"], q["native_total_arrays"], q["native_dynamic_double_arrays"]) == (N, 1000, 40, 1040, 26, 22, 6) and q["conductivity_model"] == 0 and q["conductivity_Ck"] == 0 and all(q[k] for k in ("PART_typed_public_metadata_verified", "public_master_on", "public_schema", "native_PosDiv_present", "native_PosDiv_is_float", "native_V_rho_k_present", "no_exclusions", "all_exported_physical_fields_finite", "initial_rest_and_decimal_lattice_verified", "double_stress_and_float_display_verified")), "Original22 typed/finite/elastic/identity guards rejected")
    need(q["max_ledger_relative_error"] <= 5e-13 and (q["soil_ledger_checks"], q["fixed_public_zero_marker_checks"], q["dt_s"], q["actual_end_s"], q["planned_completed_steps"], q["noninitial_signed_dterror_intervals"]) == (N * 1000, N * 40, DT, END, END_STEP, N - 1) and q["declared_saved_completed_steps_exact"] and q["actual_time_step_locked_dt_exact"] and q["max_noninitial_signed_dterror_s"] <= 1e-14, "Original ledger/signed-step/end guards rejected")
    need((q["post_open_frames"], q["post_open_drained_particle_checks"], q["max_activeDrainCount"], q["post_open_completed_step_threshold"]) == (1542, 15420, 10, 5243), "Original nonempty drainage coverage differs")
    files = {}; directory = Path(c["paths"]["native_dir"]).resolve()
    for e in c["files"]:
        pth = bind(e); need(pth.parent == directory and pth.name not in files, "Escaped/duplicate native leaf"); files[pth.name] = e
    need(set(files) == set(retained.parent.EXPORTS) | {"completion.json"} and files["completion.json"] == c["completion"], "Own native13 leaves differ")
    p = mapped(files["physical.bin"], (1000, 26, N), [("time", "<f8"), ("q", "<f8", (1000, 26))], N); clock = mapped(files["clock.bin"], (N, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")], N)
    jt = mapped(files["common_j_theta.bin"], (1040, 2, N), [("time", "<f8"), ("q", "<f8", (1040, 2))], N); por = mapped(files["soil_n.bin"], (1000, 1, N), [("time", "<f8"), ("q", "<f8", (1000,))], N)
    with bind(files["original15.bin"]).open("rb") as f: need(struct.unpack("<III", f.read(12)) == (1040, 15, N) and files["original15.bin"]["bytes"] == 12 + N * 166408, "Original15 header/length differs")
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f: cols = list(csv.DictReader(f))
    need([v["name"] for v in cols] == FIELDS and [int(v["column"]) for v in cols] == list(range(26)), "Original common26 order differs")
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8"); fixed = np.genfromtxt(bind(files["fixed_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(1000)) and np.array_equal(fixed["id"], np.arange(40)) and np.array_equal(fixed["row"], np.arange(40)), "Native1040 IDs/order differ"); x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    times = STEPS * DT; need(np.array_equal(clock["step"].astype(np.int64), np.where(STEPS > 0, STEPS - 1, 0)) and bits(clock["dt"], np.full(N, DT)).all() and bits(clock["time"], times).all() and all(bits(v["time"], times).all() for v in (p, jt, por)) and bits(p["q"][0, :, :3], x0).all(), "Actual binary dyadic clock/Step/cross-export time differs")
    need(np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Original signed necessary-step interval guard rejected")
    with bind(files["history.csv"]).open(encoding="utf-8-sig", newline="") as f: history = list(csv.DictReader(f))
    need(len(history) == N, "History count differs")
    for i, row in enumerate(history): need((int(row["part"]), int(row["completed_step"]), int(row["saved_step"]), int(row["activeDrainCount"])) == (i, int(STEPS[i]), int(clock["step"][i]), 10 if STEPS[i] > 5243 else 0) and all(struct.pack("<d", float(row[k])) == struct.pack("<d", float(v)) for k, v in (("time_s", times[i]), ("dt_s", DT), ("signed_dterror_s", clock["error"][i]))), "Actual history clock/signed diagnostic/nonempty drain differs")
    return dict(check=ce, run=c["source_run"], build=r["source_build"], program=r["program"], files=files, p=p, clock=clock, x0=x0, n=N, job=j, history=history)

def prefix_bytes(new, old, offset, count):
    compared = 0
    with bind(new).open("rb") as a, bind(old).open("rb") as b:
        a.seek(offset); b.seek(offset)
        while compared < count:
            size = min(1024 * 1024, count - compared); av, bv = a.read(size), b.read(size)
            if len(av) != size or len(bv) != size: return False, compared
            if av != bv: return False, compared + next(i for i, (x, y) in enumerate(zip(av, bv)) if x != y)
            compared += size
    return True, None

def main():
    stem = "upl_damp_mid_prefix_r1"; check, metrics = T / "logs" / (stem + ".check.json"), T / "logs" / (stem + ".csv")
    need(not check.exists() and not metrics.exists(), "Retained offline artifacts protected")
    result = dict(stage=STAGE, case="coarse_prefix", passed=False, physical_acceptance=False, solver_decoder_or_build_invoked=False, failure=None)
    try:
        adopt(__file__); adopt(T / "notes/upl_damp_mid_compare_r1.json")
        try: old = retained.dataset("coarse")  # Only this actual accepted1469 loader is reused; never its main/half/short dataset.
        finally: merge_retained_cache()
        new = dataset(); same = new["build"] == old["build"] and new["program"] == old["program"]; need(same and old["n"] == PREFIX and bits(new["clock"]["time"][:PREFIX], old["clock"]["time"]).all(), "Same program/build/actual1469 clocks required")
        rows = []
        for leaf, (offset, record) in BINARY.items():
            equal, first = prefix_bytes(new["files"][leaf], old["files"][leaf], offset, PREFIX * record); rows.append([leaf, "payload_after_independently_validated_header", PREFIX * record, PREFIX, equal, first])
        for leaf in IDENTITY: rows.append([leaf, "whole_file", old["files"][leaf]["bytes"], None, all(new["files"][leaf][k] == old["files"][leaf][k] for k in ("bytes", "sha256")), None])
        for leaf in TEXT:
            equal, first = prefix_bytes(new["files"][leaf], old["files"][leaf], 0, old["files"][leaf]["bytes"]); rows.append([leaf, "entire_retained_file_is_new_beginning", old["files"][leaf]["bytes"], PREFIX, equal, first])
        with metrics.open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["export", "comparison", "compared_bytes", "prefix_frames", "exact", "first_differing_payload_or_file_byte"]); w.writerows(rows)
        gates = dict(all5_binary_payload_prefix_exact=all(v[4] for v in rows[:5]), all3_identity_files_exact=all(v[4] for v in rows[5:8]), all3_text_prefix_exact=all(v[4] for v in rows[8:]), same_build_program=same)
        for e in list(BOUND.values()): need(entry(e["path"]) == e, "Consumed artifact changed during offline prefix comparison")
        result.update(passed=bool(all(gates.values())), gates=gates, mid_native_check=new["check"], retained_long_native_check=old["check"], native_checks=[new["check"], old["check"]], source_runs=[new["run"], old["run"]], source_builds=[new["build"], old["build"]], programs=[new["program"], old["program"]], compared_prefix_samples=PREFIX, mid_samples=N, native_count=1000, fixed_count=40, exact_prefix_rows=rows, initial26_bit_exact=bool(bits(new["p"]["q"][0], old["p"]["q"][0]).all()), binary_headers_independently_validated=True, signed_dterror_in_clock_prefix=True, last_poro_endpoint_compared_as_prefix=False, completion_whole_bytes_compared=False, all22_raw_BI4_arrays_exact_claimed=False, raw_PART_files_rehashed_or_reparsed=False, current_production_originals_or_canonical_asserted=False, consumed_artifacts_rehashed_after_comparison=True)
    except Exception as exc: result["failure"] = str(exc)
    result.update(inputs=list(BOUND.values()), files=[entry(metrics)] if metrics.exists() else [], unique_consumed_files=len(BOUND), limits="Exact decoded-export1469 compatibility plus original1746 native safety only; no9.15s half, continuum/physical/high-frequency stability, force-stage or raw-BI4-byte acceptance.")
    with check.open("x", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps(dict(passed=result["passed"], check=str(check)))); return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
