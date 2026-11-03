"""Prepare one fresh larger-step full2Tv input after root's candidate review; no program call."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import xml.dom.minidom as DOM

T = Path(__file__).resolve().parents[1]
NAME, TAG = "upl_bigstep_full_r1_prepare", "upl_bigstep_2tv_CPU1_r1"
DT, EVENT, STEPS, N = float("6.2501430511474609e-6"), 1600, 11661219, 1682
TARGET, MAX_TEXT, ANCHOR_TEXT, INTERVAL_TEXT = 51019 / 700, "72.88428690075874", "2.0000457763671875", "0.18218571428571428"
ACTUAL_END, POST = 72.88428689946836, 1564
SEED, OUT = T / "outputs/upl_bigstep_full_r1_seed", T / "outputs" / TAG
PREFIX, CONFIG = SEED / TAG, T / "configs" / (TAG + ".xml")
CSV, RECORD = T / "logs/upl_bigstep_full_r1.clock.csv", T / "logs/upl_bigstep_full_r1.inputs.json"
PINS = {
    "support/upl_bigstep_r1_prepare.py": (14051, "af24ab0c96a88585bcda5c26589a829d21aa317054dcc5127311faa963b1fff2"),
    "notes/upl_bigstep_r1_prepare.json": (4043, "542f42bf3ef78c0939f1f94ea0e37d0159b860c0079b1a14246cf1cc5e7679da"),
    "logs/upl_bigstep_r1.inputs.json": (651239, "da17c2a094531df07b11e3bc9b2aeadb2a9e670836c4e5938a8a45f886888655"),
}
owner = None


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_bigstep_r1_prepare.py"
    data = path.read_bytes()
    need((len(data), hashlib.sha256(data).hexdigest()) == PINS["support/upl_bigstep_r1_prepare.py"], "Frozen candidate definitions changed")
    spec = importlib.util.spec_from_file_location("bigstep_full_frozen_input_helpers", path)
    p = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p)  # Only file/XML/next_time definitions; never its prepare/main or fixed schedule.
    u = p.definitions()
    for name, (size, sha) in PINS.items():
        u.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    return u, p


def candidate_proofs(u):
    entries = {key: u.adopt(T / "logs" / leaf) for key, leaf in
        (("run", "upl_bigstep_c625_r1.run.json"), ("native", "upl_bigstep_r1.native.json"), ("review", "upl_bigstep_r1.review.json"))}
    r, n, v = (u.read(entries[key]) for key in ("run", "native", "review"))
    for record, stage in ((r, "upl_bigstep_c625_r1.run"), (n, "upl_bigstep_review_r1.native"), (v, "upl_bigstep_review_r1.review")):
        need(record.get("stage") == stage and record.get("passed") is True and record.get("physical_acceptance") is False and
             record.get("bindings_unchanged") is True and record.get("independent_final_rehash_performed") is True, "Completed candidate prerequisite missing: " + stage)
    u.owned(r["call"], "upl_bigstep_c625_r1.run_call")
    size, sha = PINS["logs/upl_bigstep_r1.inputs.json"]
    manifest = dict(path=str(T / "logs/upl_bigstep_r1.inputs.json"), bytes=size, sha256=sha)
    m = u.read(manifest)
    need(m.get("passed") is True and m.get("stage") == "upl_bigstep_r1_prepare" and m["jobs"] == [r["job"]] and
         u.same(r["source_input_manifest"], manifest) and u.same(r["program"], m["program"]) and u.same(r["source_build"], m["source_build"]) and
         r["steps"] == 320000 and r["native_frames"] == 1292 and r["job"]["dt_s"] == DT and
         n.get("original_native_guards_passed") is True and n.get("reader_attempts") == 2 and
         n["candidate_counts"] == dict(samples=1292, post_frames=1174, drains=11740) and
         u.same(n["datasets"]["candidate"]["source_run"], entries["run"]) and u.same(v["source_native"], entries["native"]) and
         v.get("all100_material_layers_exported") is True and v.get("comparison_is_descriptive_not_5Pa_or_0p005mm_equivalence") is True,
         "Actual candidate execution/native/descriptive review association differs")
    return m, manifest, entries


def admission(u, path, stage, required, field, allowed):
    e = u.adopt(path)
    a = u.read(e)
    need(a.get("stage") == stage and a.get("passed") is True and a.get("physical_acceptance") is False and
         a.get("candidate_review_accepted_for_full") is True and a.get(field) == allowed and a.get("inputs"), "Separate root reviewed admission required")
    for item in required:
        need(any(u.same(item, x) for x in a["inputs"]), "Root admission omitted actual prerequisite: " + item["path"])
    for item in a["inputs"]:
        u.bind(item)
    return e


def transform(p, source):
    text, original = source.decode("utf-8"), DOM.parseString(source)
    need(p.element(original, "TimeMax").getAttribute("value") == "2.0000457763671875" and
         p.element(original, "TimeOut").getAttribute("value") == "0.001953125" and len(original.getElementsByTagName("tout")) == 4,
         "Actual prepared candidate timing differs")
    changes = [("TimeMax", "value", MAX_TEXT), ("TimeOut", "value", INTERVAL_TEXT),
        ("TimeMax", "comment", "Ceil 2Tv step-product cap; actual scalar endpoint is independently replayed"),
        ("TimeOut", "comment", "After candidate window, nominal DeltaTv=.005; actual saved clocks remain authoritative")]
    target, proof = text, []
    for key, attr, value in changes:
        target, old = p.edit(target, key, attr, value)
        proof.append(dict(setting=key, attribute=attr, old=old, new=value, numeric=attr == "value"))
    matches = list(re.finditer(r"(?m)^([ \t]*)</timeout>", target))
    need(len(matches) == 1, "Unique retained timeout closing line required")
    at, indent = matches[0].start(), matches[0].group(1)
    added = indent + '    <tout time="' + ANCHOR_TEXT + '" timeout="' + INTERVAL_TEXT + '" />' + ("\r\n" if "\r\n" in text else "\n")
    target = target[:at] + added + target[at:]
    need(target.count(added) == 1, "Unique fifth timeout insertion required")
    inverse = target.replace(added, "", 1)
    for row in reversed(proof):
        inverse, got = p.edit(inverse, row["setting"], row["attribute"], row["old"])
        need(got == row["new"], "Inverse timing attribute differs")
    after = DOM.parseString(target)
    need(inverse.encode("utf-8") == source and DOM.parseString(inverse).toxml() == original.toxml() and
         all(a.toxml() == b.toxml() for a, b in zip(original.getElementsByTagName("tout"), after.getElementsByTagName("tout")[:4])),
         "Inverse UTF8/DOM or all four retained timeout nodes differ")
    return target.encode("utf-8"), after, dict(attributes=proof, inserted_fifth_tout_UTF8=added, unchanged_first_four_tout=True)


def schedule(p, doc):
    segments = [(float(n.getAttribute("time")), float(n.getAttribute("timeout"))) for n in doc.getElementsByTagName("tout")]
    need(segments == [(0., .0001220703125), (.009765625, 2. ** -19), (.01025390625, .0001220703125),
         (.0250244140625, .001953125), (float(ANCHOR_TEXT), float(INTERVAL_TEXT))] and math.ceil(TARGET / DT) == STEPS,
         "Exact full segments/ceil-step count differ")
    table = [dict(zip(p.HEADER, (0, 0, 0, 0., DT, 0, 0., 0)))]
    time, target, max_roundoff = 0., p.next_time(0., segments), 0.
    for n in range(1, STEPS + 1):
        time += DT
        max_roundoff = max(max_roundoff, abs(time - n * DT))
        ordinary = time >= target or time >= float(MAX_TEXT)
        need(not (time >= float(MAX_TEXT) and n < STEPS), "Runtime TimeMax would stop before declared cap")
        if ordinary or n == STEPS:
            table.append(dict(zip(p.HEADER, (len(table), n, n - 1, time, DT, int(n > EVENT), target, int(n == STEPS and not ordinary)))))
            target = p.next_time(time, segments)
    need(len(table) == N and sum(r["post_open_by_completed_step"] for r in table) == POST and time == ACTUAL_END and
         time > TARGET and time < float(MAX_TEXT) and table[-1]["forced_final"] == 1 and table[-2]["completed_steps"] == 11658980 and
         table[117]["completed_steps"] == EVENT and table[118]["completed_steps"] == EVENT + 1 and
         table[1290]["completed_steps"] == 319935 and table[1291]["completed_steps"] == 320001 and not any(r["completed_steps"] == 320000 for r in table),
         "Declared1682 scalar/end/event/candidate-boundary coverage differs")
    return table, dict(method="binary64 scalar +=dt and unchanged JDsOutputTime arithmetic; never n*dt as clock",
        nominal_2Tv_target_s=TARGET, nominal_2Tv_fraction="51019/700", runtime_TimeMax_s=float(MAX_TEXT), actual_scalar_end_s=time,
        scalar_end_minus_runtime_cap_s=time - float(MAX_TEXT), scalar_end_minus_nominal_2Tv_s=time - TARGET,
        max_scalar_minus_n_dt_abs_s=max_roundoff, candidate_final_only_completed_step=320000,
        candidate_final_only_shared=False, planned_common_prefix_frames=1291, first_new_full_completed_step=320001)


def prepare(result, admission_path):
    global owner
    owner, p = definitions()
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        owner.adopt(path)
    m, source_manifest, proofs = candidate_proofs(owner)
    gate = admission(owner, admission_path, "upl_bigstep_full_prepare_admission_r1",
        [source_manifest, m["program"], m["source_build"], *proofs.values()], "allowed_actions", ["prepare"])
    job = m["jobs"][0]
    need((job["master"], job["SPR"], job["Visco"], job["eta"], job["HG"], job["SlipMode"]) == (1, 1, .1, .04, .1, 3) and
         (m["program"]["bytes"], m["program"]["sha256"]) == (5125120, "bee3e36348b2146b6532cc2d2edf2717c8f4ff657da75812c0bcd5bc2f6e931e"), "Frozen requested physics/program differs")
    build = owner.read(m["source_build"])
    need(build.get("stage") == "upl_spr_av_build_r1" and build.get("passed") is True and owner.same(build["program"], m["program"]) and
         build["object_count"] == 86 and build["non_main_object_count"] == 85 and len(m["immutable_source_archives"]) == 267 and
         len(m["isolated_runtime_copies"]) == 4, "Actual isolated source/object/runtime closure differs")
    for e in [m["program"], *m["files"], *m["immutable_source_archives"], *m["isolated_runtime_copies"]]:
        owner.bind(e)
    owner.fresh(SEED, OUT, CONFIG, CSV)
    payload, doc, changes = transform(p, owner.bind(job["runtime"]).read_bytes())
    table, clock = schedule(p, doc)
    need(table[:1291] == job["saved_clock_table"][:1291] and job["saved_clock_table"][-1]["completed_steps"] == 320000 and
         job["saved_clock_table"][-1]["forced_final"] == 1, "Honest common prefix/candidate-only final definition differs")
    SEED.mkdir()
    paths = [CONFIG, PREFIX.with_suffix(".xml"), PREFIX.with_suffix(".bi4"), Path(str(PREFIX) + "_Normals.nbi4")]
    for path, data in zip(paths, [payload, payload, owner.bind(job["initial_BI4"]).read_bytes(), owner.bind(job["normals"]).read_bytes()]):
        with path.open("xb") as stream:
            stream.write(data)
    with CSV.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=p.HEADER)
        writer.writeheader()
        writer.writerows(table)
    files = [owner.adopt(path) for path in paths + [CSV]]
    need(all(files[i][k] == job[key][k] for i, key in ((2, "initial_BI4"), (3, "normals")) for k in ("bytes", "sha256")), "Original seed/normals changed")
    full = dict(job, tag=TAG, window="candidate_full2Tv", input_variant="requested_ON_larger_step_full2Tv", input_prefix=str(PREFIX),
        output_directory=str(OUT), arguments=["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(PREFIX), str(OUT), "-dirdataout", "data", "-svres", "-nsteps:" + str(STEPS)],
        steps=STEPS, expected_samples=N, end_s=ACTUAL_END, nominal_end_s=float(MAX_TEXT), runtime_TimeMax_s=float(MAX_TEXT), nominal_2Tv_target_s=TARGET,
        saved_clock_table=table, configuration_file=files[0], runtime=files[1], initial_BI4=files[2], normals=files[3], planned_clock_CSV=files[4],
        post_open_frames=POST, post_open_drained_particle_checks_expected=10 * POST,
        expected_HG_counters=dict(forcecalls=2 * STEPS, ratecalls=2 * STEPS, predictorupdates=STEPS, correctorupdates=STEPS, ratecalculations=STEPS + 1, ratecachehits=STEPS - 1))
    result.update(prepared=True, prepare_admission=gate, candidate_proofs=proofs, source_input_manifest=source_manifest, source_job=job,
        source_build=m["source_build"], program=m["program"], jobs=[full], files=files, planned_clock_CSV=files[4], clock=clock, declared_changes=changes,
        immutable_source_archives=m["immutable_source_archives"], isolated_runtime_copies=m["isolated_runtime_copies"],
        inverse_UTF8_bytes_and_DOM_exact=True, original_seed_and_normals_bytes_exact=True, measured_common1291_prefix_bitwise_identity=False,
        candidate_final_only_save_not_present_in_full=True, future_native_counts=dict(soil_ledger=N * 1000, fixed_markers=N * 40,
            all_ID_J_theta=N * 1040, signed_noninitial_intervals=N - 1, post_open_frames=POST, actual_receivers=10 * POST))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Explicit preparation-only invocation required")
    need(not RECORD.exists(), "Retained full preparation receipt protected")
    result = dict(stage=NAME, passed=False, prepared=False, failure=None, physical_acceptance=False, full_run_admitted=False,
        source_formal_or_canonical_files_written=False, solver_reader_build_Git_watcher_or_queue_invoked=False)
    try:
        prepare(result, args.admission)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(owner is not None, "Pure definitions not initialized")
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
