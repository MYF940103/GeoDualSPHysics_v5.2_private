"""Prepare retained-runtime CPU HG column clones only; never launch a program."""
import argparse
import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
ROOT = T.parents[3]
DC = 2.0 ** -19
EVENT = 5243 * DC
SEED_SHA = "f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac"
NORMAL_SHA = "0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97"
SCHEDULER_SHA = "b26c1b87f090b28bdc72c28d6ed7dfeee0ad7a0bcd28eb428f1ae72716d0c72f"
MANIFESTS = {
    "smoke": ("upl_damp_r1.inputs.json", 1043620,
              "8c26d84594fabb06ae26c00c2f2aab7489071ac877bf25675f2fa15ec7466793"),
    "long": ("upl_damp_long_r1.inputs.json", 1193147,
             "63465175d7e0c252c5580962048e8e5eacff33c7ddf1bcf8cacba24f311383a0"),
}
CONTROLS = {
    "smoke": ("upl_damp_CPU_smoke_r1", 616709,
              "a14bad62c3d5db79fd8b751a4bfbc84578bc73c2b7ef17878f3a27dce9e44cf4"),
    "coarse": ("upl_damp_long_CPU_coarse_r1", 1754310,
               "b2ecacb825ea8f98537237384529d21ef339386dad9386deae95cbe03e367497"),
    "half": ("upl_damp_long_CPU_half_r1", 1753746,
             "73d956be2d8fa8a39936d4f2e31d31a09b688e2780fd15db620dc6e51fcd1185"),
}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def entry(path):
    p = Path(path).resolve(strict=True)
    data = p.read_bytes()
    return dict(path=str(p), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def verify(e):
    need(set(("path", "bytes", "sha256")).issubset(e), "Incomplete bound identity")
    got = entry(e["path"])
    need(got["bytes"] == e["bytes"] and got["sha256"] == e["sha256"].lower(),
         "Changed bound artifact: " + e["path"])
    return Path(got["path"])


def read(e):
    return json.loads(verify(e).read_text(encoding="utf-8-sig"))


def pinned(path, size, sha):
    e = entry(path)
    need(e["bytes"] == size and e["sha256"] == sha, "Reviewed provenance differs: " + str(path))
    return e


def fresh(paths):
    for p in paths:
        need(not p.exists(), "Retained path protected: " + str(p))


def bits(x):
    return struct.pack("<d", x)


def one(root, path):
    nodes = root.findall(path)
    need(len(nodes) == 1, "Expected one runtime node: " + path)
    return nodes[0]


def value(root, key):
    return one(root, "./execution/parameters/parameter[@key='" + key + "']").get("value")


def runtime(raw, window, dt, end):
    root = ET.fromstring(raw)
    h = "./execution/special/hydromechanics/"
    for key, wanted in (("HydroMech", 1), ("HydroMechDynamicSeepage", 1),
                        ("HydroMechConductivityModel", 0), ("HydroMechConductivityCk", 0),
                        ("HydroMechDrainage", 1), ("HydroMechDrainageFixedGrid", 1),
                        ("HydroMechTopLoadRampTime", EVENT), ("HydroMechDrainageStartTime", EVENT)):
        need(float(one(root, h + key).get("value")) == wanted, "Retained hydro value differs: " + key)
    need(one(root, h + "HydroMechTopLoadMode").get("value") == "TopKernelBand", "Retained load mode differs")
    for key, wanted in (("SoilHourglassXi", 0), ("SoilDamping", 1), ("SoilDampingCoef", .02),
                        ("SoilBoundaryDerivativeSPR", 0), ("StepAlgorithm", 2), ("Kernel", 2),
                        ("Boundary", 2), ("SlipMode", 3), ("DtIni", dt), ("DtFixed", dt), ("TimeMax", end)):
        need(float(value(root, key)) == wanted, "Retained runtime value differs: " + key)
    timeout = root.findall("./execution/special/timeout")
    if window == "smoke":
        need(not timeout and float(value(root, "TimeOut")) == dt, "Retained smoke scheduling differs")
        return [(0.0, dt)]
    need(len(timeout) == 1 and timeout[0].get("active") == "true", "Retained long timeout missing")
    segments = [(float(n.get("time")), float(n.get("timeout"))) for n in timeout[0].findall("tout")]
    expected = [(0.0, 64 * DC), (5120 * DC, DC), (5376 * DC, 64 * DC), (.125, 1024 * DC)]
    need(segments == expected and float(value(root, "TimeOut")) == 64 * DC, "Retained long output clocks differ")
    return segments


def xi_only(raw):
    """Change only xi numerically; correct its old OFF comment with inverse proofs."""
    tags = []
    for match in re.finditer(rb"<parameter\b[^>]*>", raw):
        if re.search(rb"\bkey\s*=\s*(['\"])SoilHourglassXi\1", match.group()):
            tags.append(match)
    need(len(tags) == 1, "Unique retained SoilHourglassXi start tag required")
    tag = tags[0]
    values = list(re.finditer(rb"\bvalue\s*=\s*(['\"])([^'\"]*)\1", tag.group()))
    need(len(values) == 1 and float(values[0].group(2)) == 0, "Retained xi must be zero")
    match = values[0]
    first, last = tag.start() + match.start(2), tag.start() + match.end(2)
    changed = raw[:first] + b"0.1" + raw[last:]
    need(changed[:first] + raw[first:last] + changed[first + 3:] == raw, "Inverse byte proof failed")
    old_comment = b"Hourglass control OFF; not the formal stabilized setting"
    new_comment = b"Elastic GNOG ON for CPU dynamic-column tests; not a formal release"
    need(changed.count(old_comment) == 1, "Expected one historical HG OFF comment")
    updated = changed.replace(old_comment, new_comment)
    need(updated.replace(new_comment, old_comment) == changed, "Inverse comment proof failed")
    changed = updated
    need(float(value(ET.fromstring(changed), "SoilHourglassXi")) == .1, "New xi differs")
    return changed


def schedule(dt, steps, segments):
    # Literal GetNextTime behavior: duplicate input cache, anchor advance/clamp,
    # integer truncation, then the same next<=t loop. No clock snapping.
    state = dict(base=0, last_input=-1.0, last_output=0.0)

    def next_time(t):
        if state["last_input"] >= 0 and t == state["last_input"]:
            return state["last_output"]
        state["last_input"] = t
        b = state["base"]
        anchor = segments[b + 1][0] if b + 1 < len(segments) else sys.float_info.max
        while t >= anchor:
            b += 1
            anchor = segments[b + 1][0] if b + 1 < len(segments) else sys.float_info.max
        state["base"] = b
        tb, cadence = segments[b]
        if t < tb:
            nxt = tb
        else:
            n = int((t - tb) / cadence)
            nxt = tb + cadence * n
            while nxt <= t:
                nxt = tb + cadence * n
                n += 1
            nxt = min(nxt, anchor)
        state["last_output"] = nxt
        return nxt

    rows = [dict(part=0, completed_steps=0, saved_step=0, time_s=0.0)]
    t, nxt = 0.0, next_time(0.0)
    for completed in range(1, steps + 1):
        t += dt
        if t >= nxt or completed == steps:
            rows.append(dict(part=len(rows), completed_steps=completed, saved_step=completed - 1, time_s=t))
            nxt = next_time(t)
    need(bits(t) == bits(steps * dt), "Accumulated dyadic final time differs")
    need(all(bits(r["time_s"]) == bits(r["completed_steps"] * dt) for r in rows), "Replayed time bits differ")
    return rows


def owned(e, inputs):
    c = read(e)
    need(c.get("direct_native_call") and c.get("typed_LASTEXITCODE_captured_immediately")
         and c.get("owned_call_exited") and type(c.get("exit_code")) is int
         and c["exit_code"] == 0 and not c.get("invocation_failure"), "Retained actual typed exit0 required")
    inputs.extend([e, c["program"], c["log"]])
    return c


def control(window, source, inputs):
    tag, size, sha = CONTROLS[window]
    re = pinned(T / "logs" / (tag + ".run.json"), size, sha)
    r = read(re)
    need(r.get("passed") and r.get("backend") == "CPU" and r.get("public_project_main")
         and not r.get("fixture_or_Run_override") and r.get("source_inputs_objects_runtime_canonical_unchanged")
         and r["native_frames"] == source["expected_samples"] and r.get("physical_acceptance") is False,
         "Retained same-physics HG0 control owner rejected")
    need(r["job"]["runtime"] == source["runtime"] and r["job"]["initial_BI4"] == source["initial_BI4"]
         and r["job"]["normals"] == source["normals"], "Control is not bound to the selected runtime seed")
    c = owned(r["call"], inputs)
    need(c["program"] == r["program"] and c.get("public_project_main")
         and not c.get("fixture_or_Run_override"), "Retained project-main target differs")
    expected = ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", source["input_prefix"],
                str(T / "outputs" / tag), "-dirdataout", "data", "-svres", "-nsteps:" + str(source["steps"])]
    need(c["arguments"] == expected, "Retained control argv differs")
    ne = entry(T / "logs" / (tag + ".native.json"))
    n = read(ne)
    need(n.get("passed") and n.get("original_native_guards_passed") and n.get("bindings_unchanged")
         and n["source_run"] == re, "Retained typed native control owner rejected")
    owned(n["reader_call"], inputs)
    q = read(n["completion"])
    need(q.get("passed") and q["samples"] == source["expected_samples"] and q["native_total_arrays"] == 22
         and q["total_native_count"] == 1040 and q["public_master_on"] and q["PART_typed_public_metadata_verified"]
         and q["no_exclusions"] and q["all_exported_physical_fields_finite"] and q["actual_time_step_locked_dt_exact"]
         and q["planned_completed_steps"] == source["steps"] and bits(q["dt_s"]) == bits(source["dt_s"]),
         "Retained native22/control schedule rejected")
    inputs.extend([re, ne, n["completion"]])
    return dict(run=re, call=r["call"], native=ne, reader_call=n["reader_call"], completion=n["completion"],
                paths=n["paths"], raw_native_hashes_reverified_by_preparation=False)


def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)
    return entry(path)


def prepare():
    started = datetime.now(timezone.utc).isoformat()
    note = T / "notes/upl_hg_column_r1.json"
    seed = T / "outputs/upl_hg_column_seed_r1"
    record = T / "logs/upl_hg_column_r1.inputs.json"
    scheduler = entry(ROOT / "src/source/JDsOutputTime.cpp")
    need(scheduler["sha256"] == SCHEDULER_SHA, "Literal scheduler source changed")
    inputs = [entry(__file__), entry(note), scheduler]
    manifests = {}
    for key, (name, size, sha) in MANIFESTS.items():
        e = pinned(T / "logs" / name, size, sha)
        m = read(e)
        need(m.get("passed") and m.get("prepared") and m.get("physical_acceptance") is False,
             "Retained input manifest rejected")
        manifests[key] = (e, m)
        inputs.append(e)
    plans = []
    for window in ("smoke", "coarse", "half"):
        me, manifest = manifests["smoke" if window == "smoke" else "long"]
        selected = [j for j in manifest["jobs"] if j["window"] == window]
        need(len(selected) == 1, "Unique retained same-window input required")
        source = selected[0]
        factor = 2 if window == "half" else 1
        dt, end, steps, count = DC / factor, (2 * DC if window == "smoke" else .5), (2 if window == "smoke" else 262144 * factor), (3 if window == "smoke" else 1469)
        need(source["dt_s"] == dt and source["end_s"] == end and source["steps"] == steps
             and source["expected_samples"] == count and source["damping"] == 1 and source["damping_coef"] == .02,
             "Retained window/eta declaration differs")
        for key in ("configuration", "runtime", "initial_BI4", "normals"):
            verify(source[key])
            inputs.append(source[key])
        need(source["configuration"]["sha256"] == source["runtime"]["sha256"]
             and source["initial_BI4"]["sha256"] == SEED_SHA and source["normals"]["sha256"] == NORMAL_SHA,
             "Retained runtime/BI4/normals identity differs")
        raw = Path(source["runtime"]["path"]).read_bytes()
        segments = runtime(raw, window, dt, end)
        rows = schedule(dt, steps, segments)
        wanted = [0, 1, 2] if window == "smoke" else [n * factor for n in sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) | set(range(66560, 262145, 1024)))]
        old_rows = source["saved_clock_table"]
        need(len(rows) == len(wanted) == count and len(old_rows) == count, "Retained sample counts differ")
        for i, (row, old) in enumerate(zip(rows, old_rows)):
            need(row["completed_steps"] == wanted[i] and old["part"] == i
                 and old["completed_steps"] == wanted[i] and old["saved_step"] == row["saved_step"],
                 "Retained integer saved-step provenance differs")
        control_evidence = control(window, source, inputs)
        prefix = seed / ("upl_hg_column_" + window + "_r1")
        plans.append(dict(window=window, source_manifest=me, source=source, raw=xi_only(raw),
                          configuration=T / "configs" / (prefix.name + ".xml"), prefix=prefix,
                          schedule=rows, segments=segments, control=control_evidence,
                          source_JSON_time_roundtrip_differences=sum(bits(float(o["time_s"])) != bits(r["time_s"]) for o, r in zip(old_rows, rows))))
    coarse, half = plans[1]["schedule"], plans[2]["schedule"]
    need(all(h["completed_steps"] == 2 * c["completed_steps"] and bits(h["time_s"]) == bits(c["time_s"])
             for c, h in zip(coarse, half)), "Full coarse/half clocks differ")
    jobs = []
    declarations = [("DebugCPU", "smoke", "smoke", 2), ("ReleaseCPU", "smoke", "smoke", 2),
                    ("ReleaseCPU", "short_c", "coarse", 13120), ("ReleaseCPU", "short_h", "half", 26240),
                    ("ReleaseCPU", "coarse", "coarse", 262144), ("ReleaseCPU", "half", "half", 524288)]
    for config, window, variant, steps in declarations:
        plan = next(p for p in plans if p["window"] == variant)
        rows = [r for r in plan["schedule"] if r["completed_steps"] <= steps]
        need(rows[-1]["completed_steps"] == steps, "Terminal step must be an existing scheduled point")
        count = 3 if variant == "smoke" else (458 if window.startswith("short") else 1469)
        factor = 2 if variant == "half" else 1
        need(len(rows) == count, "Declared fresh job sample count differs")
        post_open = sum(r["completed_steps"] > 5243 * factor for r in rows)
        need(post_open == (0 if variant == "smoke" else (254 if window.startswith("short") else 1265)),
             "Declared event/post-opening coverage differs")
        tag = "upl_hg_column_" + config + "_" + window + "_r1"
        output = T / "outputs" / tag
        jobs.append(dict(tag=tag, configuration=config, window=window, input_variant=variant,
                         input_prefix=str(plan["prefix"]), output_directory=str(output), threads=8,
                         dt_s=DC / factor, end_s=steps * DC / factor, steps=steps, expected_samples=count,
                         saved_clock_table=rows, event_completed_step=5243 * factor, ramp_and_drain_event_s=EVENT,
                         post_open_frames=post_open,
                         expected_native_total_arrays=22, expected_total_native_count=1040,
                         expected_HG_counters=dict(forcecalls=2 * steps, ratecalls=2 * steps,
                                                   predictorupdates=steps, correctorupdates=steps,
                                                   ratecalculations=steps + 1, ratecachehits=steps - 1),
                         arguments=["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", str(plan["prefix"]),
                                    str(output), "-dirdataout", "data", "-svres", "-nsteps:" + str(steps)],
                         retained_HG0_control=plan["control"], short_uses_unchanged_long_runtime=window.startswith("short"),
                         HG_ON_vs_OFF_bit_identity_expected=False, actual_HG_counters_observed=False, solver_started=False))
    targets = [seed, record] + [p["configuration"] for p in plans] + [Path(j["output_directory"]) for j in jobs]
    fresh(targets)
    for e in inputs:
        verify(e)
    files, variants, failure = [], [], None
    try:
        seed.mkdir(exist_ok=False)
        for p in plans:
            source, prefix = p["source"], p["prefix"]
            ce = write_new(p["configuration"], p["raw"])
            files.append(ce)
            re = write_new(prefix.with_suffix(".xml"), p["raw"])
            files.append(re)
            be = write_new(prefix.with_suffix(".bi4"), verify(source["initial_BI4"]).read_bytes())
            files.append(be)
            ne = write_new(Path(str(prefix) + "_Normals.nbi4"), verify(source["normals"]).read_bytes())
            files.append(ne)
            need(ce["sha256"] == re["sha256"] and be["sha256"] == SEED_SHA and ne["sha256"] == NORMAL_SHA,
                 "Fresh runtime or binary copy differs")
            variants.append(dict(window=p["window"], configuration=ce, runtime=re, initial_BI4=be, normals=ne,
                                 input_prefix=str(prefix), source_manifest=p["source_manifest"], source_runtime=source["runtime"],
                                 source_configuration=source["configuration"], source_initial_BI4=source["initial_BI4"],
                                 source_normals=source["normals"], inverse_runtime_bytes_exact=True,
                                 changed_runtime_value_only="SoilHourglassXi:0->0.1", original_comments_preserved=False,
                                 comment_only_change="Historical HG OFF comment corrected to CPU test ON, not formal release; inverse proved",
                                 original_initial_particle_fields_unchanged=True, source_saved_clock_table_integers_verified=True,
                                 source_JSON_time_roundtrip_differences_diagnostic=p["source_JSON_time_roundtrip_differences"],
                                 special_timeout=p["segments"], retained_HG0_control=p["control"]))
    except Exception as error:
        failure = str(error)
    unchanged = False
    try:
        for e in inputs + files:
            verify(e)
        unchanged = True
    except Exception as error:
        failure = failure or str(error)
    passed = failure is None and unchanged and len(variants) == 3 and len(files) == 12
    result = dict(stage="upl_hg_column_prepare_r1", passed=passed, prepared=passed, started_utc=started,
                  ended_utc=datetime.now(timezone.utc).isoformat(), variants=variants, jobs=jobs, inputs=inputs, files=files,
                  seed_directory=str(seed), all_full_windows_samples=1469, short_samples=458,
                  short_end_s=13120 * DC, short_post_open_frames=254, full_post_open_frames=1265,
                  paired_times_bit_exact=True, actual_native_clock_observed=False,
                  integer_steps_times_locked_binary_dt_are_clock_truth=True, input_sources_unchanged=unchanged,
                  canonical_program_installed=False, run_output_directories_created=False,
                  GenCase_invoked=False, solver_reader_or_build_invoked=False, formal_files_changed=False,
                  HG_ON_vs_OFF_bit_identity_claimed=False, physical_acceptance=False, failure=failure)
    write_new(record, (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    need(passed, "Preparation failed; preserve manifest and partials: " + str(record))
    print("Prepared three HG-only runtime clones and six declared CPU jobs; no program run: " + str(record))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    try:
        need(args.execution_authorized, "Root full-read and explicit preparation invocation required")
        prepare()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
