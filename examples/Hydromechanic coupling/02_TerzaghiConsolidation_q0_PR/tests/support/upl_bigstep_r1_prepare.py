"""Prepare one bounded larger-step CPU1 candidate, without invoking any program."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import xml.dom.minidom as DOM

T = Path(__file__).resolve().parents[1]
NAME, TAG, SOURCE_TAG = "upl_bigstep_r1_prepare", "upl_bigstep_c625_r1", "upl_spr_av_new_requested_ON_r1"
DT_TEXT, END_TEXT = "6.2501430511474609E-06", "2.0000457763671875"
DT, END, EVENT_TIME = float(DT_TEXT), float(END_TEXT), float("0.010000228881835938")
STEPS, N, EVENT = 320000, 1292, 1600
SEED = T / "outputs/upl_bigstep_r1_seed"
PREFIX, OUT = SEED / TAG, T / "outputs" / TAG
CONFIG = T / "configs" / (TAG + ".xml")
CSV, RECORD = T / "logs/upl_bigstep_r1.clock.csv", T / "logs/upl_bigstep_r1.inputs.json"
HEADER = "part,completed_steps,saved_step,time_s,dt_s,post_open_by_completed_step,target_time_s,forced_final".split(",")
PINS = {
    "support/upl_spr_av_run_r1.py": (15888, "574c3a4da7ade2c1fda97d93a95c1544d6dc05e6896a5f08594053992d2fb757"),
    "notes/upl_spr_av_run_r1.json": (3340, "42ceee38a1ba1230cb2475eda1d827c30d3c05fe4c7842a0a60b058d7cbadd59"),
    "logs/upl_spr_av_r1.inputs.json": (823007, "8ed0f935b0f7d602f6ee381d639fe9077ee173602b7c2878527828e12d5daa8b"),
}
owner = None


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_spr_av_run_r1.py"
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    need((path.stat().st_size, digest) == PINS["support/upl_spr_av_run_r1.py"], "Frozen generic file utilities changed")
    spec = importlib.util.spec_from_file_location("bigstep_frozen_file_utilities", path)
    u = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(u)  # File/hash/receipt definitions only; never its fixed short context or main.
    for name, (size, sha) in PINS.items():
        u.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    return u


def element(doc, key):
    nodes = list(doc.getElementsByTagName("tout")) if key == "tout3" else [
        n for n in doc.getElementsByTagName("parameter") if n.getAttribute("key") == key]
    need(len(nodes) == (4 if key == "tout3" else 1), "Unique retained setting required: " + key)
    return nodes[3 if key == "tout3" else 0]


def edit(text, key, attribute, value):
    pattern = r"<tout\b[^>]*>" if key == "tout3" else r'<parameter\s+key="' + re.escape(key) + r'"[^>]*>'
    matches = list(re.finditer(pattern, text))
    need(len(matches) == (4 if key == "tout3" else 1), "Unique literal setting required")
    match = matches[3 if key == "tout3" else 0]
    attrs = list(re.finditer(r'\b' + re.escape(attribute) + r'="([^"]*)"', match.group()))
    need(len(attrs) == 1, "Unique existing attribute required")
    a, tag = attrs[0], match.group()
    return text[:match.start()] + tag[:a.start(1)] + value + tag[a.end(1):] + text[match.end():], a.group(1)


def transform(source):
    text, original = source.decode("utf-8"), DOM.parseString(source)
    old = {"DtIni": "1.9073486328125E-06", "DtFixed": "1.9073486328125E-06", "TimeMax": "0.5",
           "TimeOut": "0.0001220703125", "tout3": "0.125"}
    for key, value in old.items():
        need(element(original, key).getAttribute("time" if key == "tout3" else "value") == value, "Actual requested short timing differs")
    changes = [("DtIni", "value", DT_TEXT), ("DtFixed", "value", DT_TEXT), ("TimeMax", "value", END_TEXT),
               ("TimeOut", "value", "0.001953125"), ("tout3", "time", "0.0250244140625"),
               ("DtIni", "comment", "Bounded larger-step candidate; current-state necessary bound remains mandatory"),
               ("DtFixed", "comment", "Original drainage time divided by 1600; no clock snapping or physical acceptance"),
               ("TimeMax", "comment", "Nominal 200 times original drainage time; 320000 scalar additions cap this candidate"),
               ("TimeOut", "comment", "Retained first three special segments; late interval 0.001953125 seconds")]
    target, proof = text, []
    for key, attr, new in changes:
        target, previous = edit(target, key, attr, new)
        proof.append(dict(setting=key, attribute=attr, old=previous, new=new, numeric=attr != "comment"))
    inverse, back, after = target, DOM.parseString(target), DOM.parseString(target)
    for row in reversed(proof):
        inverse, seen = edit(inverse, row["setting"], row["attribute"], row["old"])
        need(seen == row["new"], "Inverse replacement differs")
        element(back, row["setting"]).setAttribute(row["attribute"], row["old"])
    need(inverse.encode("utf-8") == source and back.toxml() == original.toxml() and sum(r["numeric"] for r in proof) == 5 and
         all(a.toxml() == b.toxml() for a, b in zip(original.getElementsByTagName("tout")[:3], after.getElementsByTagName("tout")[:3])),
         "Exact inverse bytes/DOM/five numeric changes/startup preservation failed")
    return target.encode("utf-8"), after, proof


def next_time(time, segments):
    base = 0
    while base + 1 < len(segments) and time >= segments[base + 1][0]:
        base += 1
    tb, interval = segments[base]
    if time < tb:
        target = tb
    else:
        nt = int((time - tb) / interval)
        target = tb + interval * nt
        while target <= time:
            nt += 1
            target = tb + interval * nt
    return min(target, segments[base + 1][0]) if base + 1 < len(segments) else target


def schedule(doc):
    segments = [(float(n.getAttribute("time")), float(n.getAttribute("timeout"))) for n in doc.getElementsByTagName("tout")]
    need(segments == [(0., .0001220703125), (.009765625, 2. ** -19), (.01025390625, .0001220703125),
                      (.0250244140625, .001953125)] and DT * EVENT == EVENT_TIME and END == 200 * EVENT_TIME,
         "Original event/early segments/exact fixed-grid ratio differ")
    rows = [dict(zip(HEADER, (0, 0, 0, 0., DT, 0, 0., 0)))]
    time, target, event_clock, max_roundoff = 0., next_time(0., segments), None, 0.
    for completed in range(1, STEPS + 1):
        time += DT  # Literal binary64 CPU accumulation, never completed*DT or clock snapping.
        max_roundoff = max(max_roundoff, abs(time - completed * DT))
        if completed == EVENT:
            event_clock = time
        ordinary = time >= target or time >= END
        need(not (time >= END and completed < STEPS), "TimeMax would end the solver before the declared step cap")
        if ordinary or completed == STEPS:
            rows.append(dict(zip(HEADER, (len(rows), completed, completed - 1, time, DT, int(completed > EVENT),
                                          target, int(completed == STEPS and not ordinary)))))
            target = next_time(time, segments)
    need(len(rows) == N and sum(r["post_open_by_completed_step"] for r in rows) == 1174 and rows[-1]["forced_final"] == 1 and
         rows[117]["completed_steps"] == EVENT and rows[118]["completed_steps"] == EVENT + 1 and
         rows[-2]["completed_steps"] == 319935 and time == 2.0000457763593587 and time < END,
         "Predeclared scalar schedule1292/event/final counts differ")
    return rows, dict(method="binary64 scalar += dt per completed step; literal JDsOutputTime GetNextTime arithmetic",
        nominal_TimeMax_s=END, actual_scalar_end_s=time, scalar_end_minus_nominal_s=time - END,
        event_scalar_time_s=event_clock, event_nominal_time_s=EVENT_TIME, max_scalar_minus_n_dt_abs_s=max_roundoff,
        forced_final_definition="terminal step cap only, when neither output target nor nominal TimeMax is reached")


def prepare(result):
    global owner
    owner = definitions()
    for p in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        owner.adopt(p)
    size, sha = PINS["logs/upl_spr_av_r1.inputs.json"]
    manifest = dict(path=str(T / "logs/upl_spr_av_r1.inputs.json"), bytes=size, sha256=sha)
    m = owner.read(manifest)
    need(m.get("stage") == "upl_spr_av_prepare_r1" and m.get("passed") is True and m.get("prepared") is True and
         m.get("bindings_unchanged") is True and m.get("independent_final_rehash_performed") is True, "Passed requested input preparation required")
    jobs = [j for j in m["jobs"] if j["tag"] == SOURCE_TAG]
    need(len(jobs) == 1, "Unique actual requested short source required")
    job = jobs[0]
    need((job["master"], job["SPR"], job["Visco"], job["eta"], job["HG"], job["SlipMode"]) == (1, 1, .1, .04, .1, 3) and
         (job["program"]["bytes"], job["program"]["sha256"]) ==
         (5125120, "bee3e36348b2146b6532cc2d2edf2717c8f4ff657da75812c0bcd5bc2f6e931e"), "Frozen current requested physics/program differ")
    build = owner.read(job["source_build"])
    need(build.get("stage") == "upl_spr_av_build_r1" and build.get("passed") is True and owner.same(build["program"], job["program"]) and
         build["object_count"] == 86 and build["non_main_object_count"] == 85 and len(m["immutable_source_archives"]["new"]) == 267 and
         len(m["isolated_runtime_copies"]["new"]) == 4, "Genuine isolated project-main archive/runtime closure differs")
    for e in [job["program"], job["configuration_file"], job["runtime"], job["initial_BI4"], job["normals"],
              *m["immutable_source_archives"]["new"], *m["isolated_runtime_copies"]["new"]]:
        owner.bind(e)  # Immutable archives/copies only; no stale original live source/canonical dependency claim.
    owner.fresh(SEED, OUT, CONFIG, CSV)
    payload, doc, changes = transform(owner.bind(job["runtime"]).read_bytes())
    for key in ("HydroMechTopLoadRampTime", "HydroMechDrainageStartTime"):
        nodes = list(doc.getElementsByTagName(key))
        need(len(nodes) == 1 and nodes[0].getAttribute("value") == "0.010000228881835938", "Original physical event changed")
    table, clock = schedule(doc)
    SEED.mkdir()
    paths = [CONFIG, PREFIX.with_suffix(".xml"), PREFIX.with_suffix(".bi4"), Path(str(PREFIX) + "_Normals.nbi4")]
    contents = [payload, payload, owner.bind(job["initial_BI4"]).read_bytes(), owner.bind(job["normals"]).read_bytes()]
    for path, content in zip(paths, contents):
        with path.open("xb") as stream:
            stream.write(content)
    with CSV.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(table)
    files = [owner.adopt(p) for p in paths + [CSV]]
    need(all(files[i][k] == job[key][k] for i, key in ((2, "initial_BI4"), (3, "normals")) for k in ("bytes", "sha256")), "Original BI4/normals copies changed")
    candidate = dict(job, tag=TAG, window="candidate2s", input_variant="requested_ON_bigstep", input_prefix=str(PREFIX),
        output_directory=str(OUT), arguments=["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(PREFIX), str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:320000"], steps=STEPS, dt_s=DT, end_s=clock["actual_scalar_end_s"],
        nominal_end_s=END, runtime_TimeMax_s=END, expected_samples=N, event_completed_step=EVENT, event_time_s=EVENT_TIME,
        saved_clock_table=table, configuration_file=files[0], runtime=files[1], initial_BI4=files[2], normals=files[3],
        planned_clock_CSV=files[4], post_open_frames=1174, post_open_drained_particle_checks_expected=11740,
        expected_HG_counters=dict(forcecalls=2*STEPS, ratecalls=2*STEPS, predictorupdates=STEPS,
            correctorupdates=STEPS, ratecalculations=STEPS+1, ratecachehits=STEPS-1))
    result.update(prepared=True, source_input_manifest=manifest, source_job=job, source_build=job["source_build"], program=job["program"],
        jobs=[candidate], files=files, planned_clock_CSV=files[4], clock=clock, declared_changes=changes,
        inverse_UTF8_bytes_and_DOM_exact=True, unchanged_first_three_tout_entries=True, original_seed_and_normals_bytes_exact=True,
        immutable_source_archives=m["immutable_source_archives"]["new"], isolated_runtime_copies=m["isolated_runtime_copies"]["new"],
        future_native_counts=dict(soil_ledger=1292000, fixed_markers=51680, all_ID_J_theta=1343680,
            signed_noninitial_intervals=1291, post_open_frames=1174, actual_receivers=11740))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Explicit preparation-only invocation required")
    need(not RECORD.exists(), "Retained preparation receipt protected")
    result = dict(stage=NAME, passed=False, prepared=False, failure=None, physical_acceptance=False, automatic_full_or_next_run=False,
        source_formal_or_canonical_files_written=False, solver_reader_build_Git_watcher_or_queue_invoked=False,
        historical_mutable_source_or_canonical_revalidated=False, native_scalar_clock_and_stability_acceptance_pending=True)
    try:
        prepare(result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(owner is not None, "Pinned definitions not initialized")
        result["inputs"] = owner.final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(owner.BOUND.values()) if owner else []
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = result["passed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    with RECORD.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], receipt=str(RECORD), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
