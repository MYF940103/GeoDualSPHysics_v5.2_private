"""Prepare four immutable input variants and five fixed CPU short jobs; never run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.dom.minidom as DOM

T = Path(__file__).resolve().parents[1]
NAME = "upl_spr_av_prepare_r1"
RECORD = T / "logs/upl_spr_av_r1.inputs.json"
SEEDS = T / "outputs/upl_spr_av_seed_r1"
NEW_BUILD = T / "logs/upl_spr_av_ReleaseCPU_r1.build.json"
N, STEPS, DT, EVENT = 458, 13120, 2.0 ** -19, 5243
SAVE = sorted(set(range(0, STEPS + 1, 64)) | set(range(5120, 5377)))
COUNTERS = dict(forcecalls=26240, ratecalls=26240, predictorupdates=13120,
                correctorupdates=13120, ratecalculations=13121, ratecachehits=13119)
PINS = {
    "logs/upl_hg_cpu1_short_r1.run.json": (624373, "a1b0b48a1f88573efa3fb4b48888534b6a4678b06d764bbb146b287ff263590d"),
    "logs/upl_hg_cpu1_short_r1.call.json": (2439, "4401245031382b83a660d9ef1cb4792204752dc7db9a700953620bd0d6285634"),
    "logs/upl_hg_column_r1.inputs.json": (628141, "c1d9ec4018fff42dd444caf4bca757e5e3d27ad546ca49a68596225abf68e187"),
    "logs/upl_hg_column_ReleaseCPU_r1.build.json": (455112, "f01ccdaf1c86ec036c598eba888a57d4d9b69d80839d76ccf7b4dc731cc19975"),
    "support/upl_spr_av_build_r1.ps1": (20679, "4d224523262a8f1b64b3426511ab9b8f12dd7bf39dc5fd61e712483431bda82f"),
    "notes/upl_spr_av_build_r1.json": (3080, "7aa01ec4c8e26d645c4874513f705fba75d77e02177b50f0e8ba73665a826668"),
}
OLD_PROGRAM = (5115392, "b5a44073b7303b7df917d01105d3cb0a20a0ca1a90a9a963ccb35be9b2b3530c")
PATCH = (267740, "6de7e04477e92ea141224b9df38e0860ae07efdc7b5d512ed30c318e7260236e")
TAGS = ("upl_spr_av_old_OFF_r1", "upl_spr_av_new_OFF_r1", "upl_spr_av_new_ON0_r1",
        "upl_spr_av_new_ONSPR_r1", "upl_spr_av_new_requested_ON_r1")
CHANGES = {
    "OFF": (("HydroMechDynamicSeepage", "1", "0"), ("SoilBoundaryDerivativeSPR", "0", "1"),
            ("Visco", "0", "0.1"), ("SoilDampingCoef", "0.02", "0.04")),
    "ON0": (),
    "ONSPR": (("SoilBoundaryDerivativeSPR", "0", "1"),),
    "requested_ON": (("SoilBoundaryDerivativeSPR", "0", "1"), ("Visco", "0", "0.1"),
                     ("SoilDampingCoef", "0.02", "0.04")),
}
BOUND = {}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def same(a, b):
    return (str(Path(a["path"]).resolve()).casefold(), a["bytes"], a["sha256"].lower()) == (
        str(Path(b["path"]).resolve()).casefold(), b["bytes"], b["sha256"].lower())


def bind(expected):
    key = str(Path(expected["path"]).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(expected["path"])
    need(same(BOUND[key], expected), "Changed consumed artifact: " + expected["path"])
    return Path(BOUND[key]["path"])


def adopt(path):
    value = entry(path)
    bind(value)
    return value


def read(expected):
    return json.loads(bind(expected).read_text(encoding="utf-8-sig"))


def pin(name):
    size, digest = PINS[name]
    value = dict(path=str((T / name).resolve()), bytes=size, sha256=digest)
    bind(value)
    return value


def fresh(*paths):
    need(all(not Path(p).exists() for p in paths), "Retained preparation/job path protected")


def final_bindings():
    for value in list(BOUND.values()):
        need(same(entry(value["path"]), value), "Consumed bytes changed during preparation")
    return list(BOUND.values())


def owned(expected, stage, python):
    c = read(expected)
    field = "typed_returncode_captured_immediately" if python else "typed_LASTEXITCODE_captured_immediately"
    need(c.get("stage") == stage and c.get("direct_native_call") is True and c.get("owned_call_exited") is True and
         c.get(field) is True and type(c.get("exit_code")) is int and c["exit_code"] == 0 and
         c.get("invocation_failure") is None, "Actual retained original typed exit0 required")
    bind(c["program"])
    if c.get("log"):
        bind(c["log"])
    return c


def archives(build):
    rows = build["source_snapshot"]
    need(len(rows) == 265 and len({Path(v["snapshot"]["path"]).name.lower() for v in rows}) == 265,
         "Exact265 immutable source snapshots required")
    result = []
    for pair in rows + [build["documentation_snapshot"], build["case_readme_snapshot"]]:
        # Compare historical claims to their own archive; never stat/hash the old mutable original.
        need(all(pair["original"][k] == pair["snapshot"][k] for k in ("bytes", "sha256")),
             "Recorded original/archive identity differs")
        bind(pair["snapshot"])
        result.append(pair["snapshot"])
    return result


def runtime_copies(build):
    need(len(build["runtime"]) == 4, "Four immutable isolated runtime copies required")
    copies = []
    for pair in build["runtime"]:
        need(all(pair["original"][k] == pair["copy"][k] for k in ("bytes", "sha256")),
             "Recorded isolated runtime copy differs")
        bind(pair["copy"])  # No historical canonical-runtime revalidation.
        copies.append(pair["copy"])
    need({Path(v["path"]).name.lower() for v in copies} ==
         {"dsphconfig.xml", "chronoengine.dll", "dsphchrono.dll", "vcomp140.dll"},
         "Actual four runtime basenames differ")
    return copies


def source_context():
    run_e = pin("logs/upl_hg_cpu1_short_r1.run.json")
    run = read(run_e)
    call_e = pin("logs/upl_hg_cpu1_short_r1.call.json")
    manifest_e = pin("logs/upl_hg_column_r1.inputs.json")
    build_e = pin("logs/upl_hg_column_ReleaseCPU_r1.build.json")
    need(run.get("stage") == "upl_hg_cpu1_short_r1.run" and run.get("passed") is True and
         run.get("bindings_unchanged") is True and run.get("public_project_main") is True and
         run.get("fixture_or_Run_override") is False and run.get("physical_acceptance") is False and
         same(run["call"], call_e) and same(run["source_input_manifest"], manifest_e) and
         same(run["source_build"], build_e) and run["steps"] == STEPS and run["native_frames"] == N,
         "Genuine completed retained CPU1 short source required")
    m, b = read(manifest_e), read(build_e)
    need(m.get("stage") == "upl_hg_column_prepare_r1" and m.get("passed") and m.get("prepared") and
         m.get("input_sources_unchanged") and m.get("physical_acceptance") is False and
         b.get("stage") == "upl_hg_column_build_r1" and b.get("passed") and
         b["configuration"] == "ReleaseCPU" and b["platform"] == "x64" and
         b["object_count"] == 86 and b["non_main_object_count"] == 85 and b["exact_object_basename_closure"] and
         (b["program"]["bytes"], b["program"]["sha256"]) == OLD_PROGRAM and same(run["program"], b["program"]),
         "Actual accepted isolated old program/source manifest required")
    bind(b["program"])
    candidates = [v for v in m["variants"] if v["window"] == "coarse"]
    need(len(candidates) == 1, "Unique retained coarse physical input variant required")
    v, j = candidates[0], run["job"]
    need(v["inverse_runtime_bytes_exact"] and v["original_initial_particle_fields_unchanged"] and
         v["changed_runtime_value_only"] == "SoilHourglassXi:0->0.1" and
         j["tag"] == "upl_hg_cpu1_short_r1" and j["backend"] == "CPU" and j["threads"] == 1 and
         j["configuration"] == "ReleaseCPU" and j["input_prefix"] == v["input_prefix"] and
         j["dt_s"] == DT and j["steps"] == STEPS and j["end_s"] == STEPS * DT and
         j["expected_samples"] == N and j["event_completed_step"] == EVENT and
         j["post_open_frames"] == 254 and j["expected_HG_counters"] == COUNTERS and
         j["expected_native_total_arrays"] == 22 and j["expected_total_native_count"] == 1040 and
         len(SAVE) == N and sum(s > EVENT for s in SAVE) == 254,
         "Actual retained CPU1 short physical settings differ")
    table = [dict(part=i, completed_steps=s, saved_step=s - 1 if s else 0, time_s=s * DT)
             for i, s in enumerate(SAVE)]
    need(len(j["saved_clock_table"]) == N and all(
        tuple(a[k] for k in ("part", "completed_steps", "saved_step")) ==
        tuple(w[k] for k in ("part", "completed_steps", "saved_step"))
        for a, w in zip(j["saved_clock_table"], table)), "Actual integer short schedule differs")
    c = owned(call_e, "upl_hg_cpu1_short_r1.run_call", True)
    want = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", v["input_prefix"],
            j["output_directory"], "-dirdataout", "data", "-svres", "-nsteps:13120"]
    need(c["arguments"] == c["target_arguments"] == j["arguments"] == want and
         same(c["program"], b["program"]) and same(c["target_program"], b["program"]) and
         Path(c["working_directory"]).resolve() == (T.parents[3] / "src").resolve(),
         "Actual retained project-main argv/program differs")
    for key in ("configuration", "runtime", "initial_BI4", "normals"):
        bind(v[key])
    need(v["runtime"]["bytes"] == 14776 and v["runtime"]["sha256"] ==
         "e1c187ea6d2f2c634a904cf60be20172bf1bd967a67d3f021a7181d83b8ff035" and
         Path(v["runtime"]["path"]) == Path(v["input_prefix"] + ".xml") and
         Path(v["initial_BI4"]["path"]) == Path(v["input_prefix"] + ".bi4") and
         Path(v["normals"]["path"]) == Path(v["input_prefix"] + "_Normals.nbi4"),
         "Exact retained physical prefix/file identities differ")
    return dict(run=run_e, call=call_e, manifest=manifest_e, build=build_e, program=b["program"],
                snapshots=archives(b), runtime=runtime_copies(b), variant=v, job=j, saved=table,
                working_directory=c["working_directory"])


def current_build(old):
    for name in ("support/upl_spr_av_build_r1.ps1", "notes/upl_spr_av_build_r1.json"):
        pin(name)
    e = adopt(NEW_BUILD)
    b = read(e)
    need(b.get("stage") == "upl_spr_av_build_r1" and b.get("passed") is True and
         b["configuration"] == "ReleaseCPU" and b["platform"] == "x64" and b["backend"] == "CPU" and
         b["build_target"] == "Build" and type(b["exit_code"]) is int and b["exit_code"] == 0 and
         all(b.get(k) is True for k in ("source_bindings_unchanged", "canonical_programs_unchanged", "runtime_unchanged",
             "objects_include_project_main", "exact_object_basename_closure", "same_control_MSBuild_vector_except_three_paths")) and
         all(b.get(k) is False for k in ("old_objects_reused", "historical_source_hashes_used_as_current",
             "pre_edit_live_source_or_canonical_identity_claimed", "helper_built", "solver_started",
             "program_or_component_run", "canonical_program_installed", "physical_acceptance")) and
         b["object_count"] == len(b["objects"]) == 86 and b["non_main_object_count"] == 85 and
         b["source_code_header_count"] == 265 and len(b["libraries"]) == 17 and
         same(b["accepted_ReleaseCPU_control"], old["build"]) and same(b["accepted_ReleaseCPU_program"], old["program"]),
         "Separately passed genuine new ReleaseCPU build required; preparation never builds")
    c = owned(b["project_call"], "upl_spr_av_build_r1.msbuild", False)
    need(same(b["project_call"], b["owned_exit_record"]) and same(c["program"], b["build_tool"]) and
         c["arguments"] == b["arguments"], "Actual new MSBuild owned call differs")
    need(Path(b["program"]["path"]).resolve() ==
         (T / "outputs/upl_spr_av_ReleaseCPU_r1/DualSPHysics5.2CPU_win64.exe").resolve() and
         b["program"]["bytes"] > 0 and b["program"]["sha256"] != OLD_PROGRAM[1] and
         len(b["current_source_differences_from_control"]) == 1 and
         same(b["current_source_differences_from_control"][0], b["reviewed_changed_source"]) and
         (b["reviewed_changed_source"]["bytes"], b["reviewed_changed_source"]["sha256"]) == PATCH,
         "Exact reviewed candidate program/source patch required")
    code = [v["snapshot"] for v in b["source_snapshot"] if Path(v["snapshot"]["path"]).name == "JSphCpu.cpp"]
    need(len(code) == 1 and (code[0]["bytes"], code[0]["sha256"]) == PATCH,
         "New archived JSphCpu.cpp differs from reviewed candidate")
    bind(b["program"])
    for value in [b["log"], b["binlog"], *b["author_files"], *b["objects"]]:
        bind(value)
    if b.get("environment") is not None:
        bind(b["environment"])  # The fixed CPU builder legitimately records null here.
    return dict(build=e, program=b["program"], snapshots=archives(b), runtime=runtime_copies(b))


def node(doc, key):
    nodes = list(doc.getElementsByTagName(key)) if key == "HydroMechDynamicSeepage" else [
        n for n in doc.getElementsByTagName("parameter") if n.getAttribute("key") == key]
    need(len(nodes) == 1, "One exact XML setting required: " + key)
    return nodes[0]


def token(key, value):
    return ('<HydroMechDynamicSeepage value="' if key == "HydroMechDynamicSeepage" else
            '<parameter key="' + key + '" value="') + value + '"'


def transform(source, changes):
    text = source.decode("utf-8")
    before = DOM.parseString(text)
    need(len(before.getElementsByTagName("tout")) == 4, "Actual source has four literal tout entries")
    for key, value in (("HydroMechDynamicSeepage", "1"), ("SlipMode", "3"), ("ViscoTreatment", "1"),
                       ("Visco", "0"), ("ViscoBoundFactor", "1"), ("SoilBoundaryDerivativeSPR", "0"),
                       ("SoilDamping", "1"), ("SoilDampingCoef", "0.02"), ("SoilHourglassXi", "0.1"),
                       ("DtIni", "1.9073486328125E-06"), ("DtFixed", "1.9073486328125E-06"),
                       ("TimeMax", "0.5"), ("TimeOut", "0.0001220703125")):
        need(node(before, key).getAttribute("value") == value, "Source setting differs: " + key)
    target = text
    for key, old, new in changes:
        need(target.count(token(key, old)) == 1, "One literal replacement required: " + key)
        target = target.replace(token(key, old), token(key, new))
    inverse = target
    for key, old, new in reversed(changes):
        need(inverse.count(token(key, new)) == 1, "One inverse replacement required: " + key)
        inverse = inverse.replace(token(key, new), token(key, old))
    after, back = DOM.parseString(target), DOM.parseString(target)
    for key, old, new in changes:
        need(node(after, key).getAttribute("value") == new, "Target XML setting differs")
        node(back, key).setAttribute("value", old)
    timeouts = lambda doc: [n.toxml() for n in doc.getElementsByTagName("timeout")]
    need(inverse.encode("utf-8") == source and back.toxml() == before.toxml() and
         timeouts(after) == timeouts(before) and
         all(node(after, k).toxml() == node(before, k).toxml() for k in ("DtIni", "DtFixed", "TimeMax", "TimeOut", "SoilHourglassXi")),
         "Inverse UTF8/text/DOM or unchanged dt/HG/timeouts/TimeMax proof failed")
    return target.encode("utf-8")


def prepare(result):
    adopt(__file__)
    adopt(T / "notes" / (NAME + ".json"))
    adopt(sys.executable)
    old = source_context()
    new = current_build(old)
    v = old["variant"]
    source = bind(v["runtime"]).read_bytes()
    fresh(SEEDS, *(T / "outputs" / tag for tag in TAGS))
    configs = {name: T / "configs" / ("upl_spr_av_" + name + "_r1.xml") for name in CHANGES if name != "ON0"}
    fresh(*configs.values())
    # Validate every planned text transformation before the first new physical-input write.
    payloads = {name: transform(source, changes) for name, changes in CHANGES.items()}
    SEEDS.mkdir()
    variants, files = [], []
    for name, changes in CHANGES.items():
        if name == "ON0":
            variant = dict(name=name, generated=False, input_prefix=v["input_prefix"], configuration_file=v["configuration"],
                           runtime=v["runtime"], initial_BI4=v["initial_BI4"], normals=v["normals"])
        else:
            prefix = SEEDS / ("upl_spr_av_" + name + "_r1")
            paths = [configs[name], prefix.with_suffix(".xml"), prefix.with_suffix(".bi4"),
                     Path(str(prefix) + "_Normals.nbi4")]
            payload = [payloads[name], payloads[name], bind(v["initial_BI4"]).read_bytes(), bind(v["normals"]).read_bytes()]
            for path, content in zip(paths, payload):
                with path.open("xb") as stream:
                    stream.write(content)
            made = [adopt(path) for path in paths]
            need(all(made[2][k] == v["initial_BI4"][k] and made[3][k] == v["normals"][k] for k in ("bytes", "sha256")),
                 "Fresh seed/normal copies changed bytes")
            files.extend(made)
            variant = dict(name=name, generated=True, input_prefix=str(prefix), configuration_file=made[0],
                           runtime=made[1], initial_BI4=made[2], normals=made[3])
        variant.update(source_runtime=v["runtime"], changed_values=[dict(key=k, old=o, new=n) for k, o, n in changes],
                       inverse_UTF8_bytes_and_DOM_exact=True, original_comments_and_XML_style_preserved=True,
                       only_declared_values_changed=True, original_seed_and_normals_bytes_exact=True,
                       literal_tout_count=4, default_TimeOut_and_all_tout_unchanged=True, runtime_TimeMax_s=.5,
                       runtime_TimeMax_was_not_repurposed_as_short_end=True,
                       master=0 if name == "OFF" else 1, SPR=0 if name == "ON0" else 1,
                       Visco=.1 if name in ("OFF", "requested_ON") else 0,
                       eta=.04 if name in ("OFF", "requested_ON") else .02, HG=.1, SlipMode=3)
        variants.append(variant)
    by_name = {x["name"]: x for x in variants}
    jobs = []
    for tag, name, program_set in zip(TAGS, ("OFF", "OFF", "ON0", "ONSPR", "requested_ON"), (old, new, new, new, new)):
        a = by_name[name]
        args = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", a["input_prefix"], str(T / "outputs" / tag),
                "-dirdataout", "data", "-svres", "-nsteps:13120"]
        job = dict(tag=tag, backend="CPU", configuration="ReleaseCPU", window="short458", threads=1,
                   input_variant=name, input_prefix=a["input_prefix"], output_directory=args[5], arguments=args,
                   program=program_set["program"], source_build=program_set["build"], working_directory=old["working_directory"],
                   steps=STEPS, dt_s=DT, end_s=STEPS * DT, expected_samples=N, saved_clock_table=old["saved"],
                   event_completed_step=EVENT, post_open_frames=254, expected_total_native_count=1040,
                   expected_native_total_arrays=15 if name == "OFF" else 22, expected_HG_counters=COUNTERS,
                   configuration_file=a["configuration_file"], runtime=a["runtime"], initial_BI4=a["initial_BI4"], normals=a["normals"],
                   master=a["master"], SPR=a["SPR"], Visco=a["Visco"], eta=a["eta"], HG=.1, SlipMode=3,
                   separate_root_run_native_and_proof_required=True, half_job=False)
        if name != "OFF":
            job.update(post_open_drained_particle_checks_expected=2540, expected_post_open_receivers_per_frame=10)
        jobs.append(job)
    need(len(variants) == 4 and len(files) == 12 and len(jobs) == 5 and
         jobs[0]["runtime"] == jobs[1]["runtime"] and jobs[0]["arguments"][4] == jobs[1]["arguments"][4] and
         jobs[2]["runtime"] == v["runtime"] and jobs[2]["input_prefix"] == old["job"]["input_prefix"],
         "Fixed four variants/five jobs/shared OFF/exact ON0 input coverage differs")
    result.update(prepared=True, source_CPU1_run=old["run"], source_CPU1_call=old["call"],
                  source_input_manifest=old["manifest"], source_job=old["job"], source_variant=v,
                  old_source_build=old["build"], new_source_build=new["build"],
                  programs=dict(old=old["program"], new=new["program"]),
                  immutable_source_archives=dict(old=old["snapshots"], new=new["snapshots"]),
                  isolated_runtime_copies=dict(old=old["runtime"], new=new["runtime"]),
                  historical_mutable_live_source_or_canonical_inputs_revalidated=False,
                  source_build_hashes_are_program_provenance_not_input_physics=True, variants=variants, jobs=jobs, files=files,
                  literal_source_tout_entries=4, source_default_TimeOut_also_preserved=True,
                  proofs_pending=["old_OFF_vs_new_OFF_original15_and_actual_clocks_exact",
                      "retained_CPU1_short_vs_new_ON0_all_native_exports_and_actual_clocks_exact",
                      "new_ON0_vs_new_ONSPR_all_native_exports_and_actual_clocks_exact",
                      "requested_ON_original_native_safety_and_descriptive_matched_FreeSlip_OFF_comparison"],
                  only_short_end_control_is_original_nsteps_argument=True, half_jobs_prepared=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit preparation authorization required")
    fresh(RECORD)
    result = dict(stage=NAME, passed=False, prepared=False, created_utc=datetime.now(timezone.utc).isoformat(),
                  failure=None, solver_reader_or_build_invoked=False, physical_acceptance=False,
                  run_native_or_full_2Tv_admitted=False, no_half_jobs=True, source_or_formal_or_canonical_files_written=False)
    try:
        prepare(result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        result["inputs"] = final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(BOUND.values())
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
        result["passed"] = False
    with RECORD.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], receipt=str(RECORD), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
