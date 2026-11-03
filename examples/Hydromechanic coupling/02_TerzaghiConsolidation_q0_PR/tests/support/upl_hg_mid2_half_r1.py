"""Fixed independent2s half: separate prepare/build-reader/run/native/compare actions."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.dom.minidom as DOM

T = Path(__file__).resolve().parents[1]
SRC = T.parents[3] / "src"
NAME, TAG = "upl_hg_mid2_half_r1", "upl_hg_mid2_CPU1_half_r1"
N, STEPS, DT, EVENT = 1517, 2097152, 2.0 ** -20, 10486
PREFIX = T / "outputs/upl_hg_mid2_half_seed_r1/upl_hg_mid2_half_r1"
OUT, NATIVE = T / "outputs" / TAG, T / "outputs" / (TAG + "_native")
HNAME = "upl_hg_mid2_half_reader_ReleaseCPU_r1"
HFOLDER = T / "outputs" / HNAME
COUNTERS = dict(forcecalls=4194304, ratecalls=4194304, predictorupdates=2097152,
                correctorupdates=2097152, ratecalculations=2097153, ratecachehits=2097151)
PINS = {
    "support/upl_hg_mid2_run_r1.py": (27672, "1a0c59f65f207a08b96833b941c51eac270d7c9f527a3f4137b02df1796904ca"),
    "notes/upl_hg_mid2_run_r1.json": (4597, "b9d64c093500bfb7e70887ca5fe8ee4c384fd8f271367f9019523209fd39ebfd"),
    "support/upl_hg_mid2_review_r1.py": (50835, "42f2aa2b68d184533d2d0d17e2a46beb381693527b55409d1d7803cfc88d0970"),
    "notes/upl_hg_mid2_review_r1.json": (9764, "bb868714223e5002c76000592875b86ba6fbbf71505fc1377a18c89d76844757"),
    "logs/upl_hg_mid2_r1.inputs.json": (1593497, "b595ea644faf20d8dadaace5e58980066128a596db1c8ffa07edde2ce015da9f"),
    "logs/upl_hg_mid2_reader_ReleaseCPU_r1.helper.json": (532547, "d3d86f3ed7647d32b457a48bd253160b197ae8d955adae097b708aac8e5dab5c"),
    "logs/upl_hg_mid2_CPU1_coarse_r1.run.json": (1129301, "49962273717016b2e6a4996fa8471d636d4eb6803d7d79579e9fc15c6c2e3062"),
    "logs/upl_hg_mid2_CPU1_coarse_r1.native.json": (903743, "3ca8c2726c54899b1e8d030907dddbd7e827510ad52df92356fb57ecedbc20c0"),
    "logs/upl_hg_mid2_review_r1.check.json": (45828, "62f9241ac4e0ebf20cc7ff6d776412e8e674e90f75e6c478429a9ea44ea4d3e1"),
    "notes/upl_hg_mid2_root_r1.json": (7761, "5cddccbeecd1bed8fdb531bdb0849de7279b4e08b2671f1fbb6362fd349d3ff2"),
    "logs/upl_hg_column_ReleaseCPU_half_r1.native_r2.json": (1462479, "326942cc55d063e2ebc1fa1fc423747e961cb23f3afec9b4b86625e7d00bd3bf"),
    "logs/upl_hg_column_ReleaseCPU_half_r1.run.json": (1547615, "ed00e0f1e4f21a058329b65bbe5c8d68b0b6276eb37b28a05d891840a63b4fa3"),
    "support/upl_hg_mid2_native_r1.cpp": (18575, "194066fa3a332f511f434b38081eade1d4aa9f4a366de3f0a497f67c3007a4e4"),
    "support/upl_hg_mid2_half_native_r1.cpp": (18578, "f9644c3f52489687217fa013576624f5410f1160dcc06a6ac61b442b1387a987"),
}
CPP_CHANGES = (
    ("// Pure typed public bounded2s mid-window reader; one CPU coarse preset, never a solver.", "// Pure typed public bounded2s mid-window reader; one CPU half preset, never a solver."),
    ("namespace hgmid2 {", "namespace hgmid2half {"),
    ("const unsigned samples=Samples,drainStep=5243;const double dt=std::ldexp(1.,-19),end=1048576.*dt;", "const unsigned samples=Samples,drainStep=10486;const double dt=std::ldexp(1.,-20),end=2097152.*dt;"),
    ("const auto saveSteps=SaveSteps(false,false); // Only admitted coarse schedule; dormant parent branches are never exposed.", "const auto saveSteps=SaveSteps(false,true); // Only admitted half schedule; dormant parent branches are never exposed."),
    ("upl_hg_mid2_native_r1", "upl_hg_mid2_half_native_r1"),
    ("Use --read CPU DATA coarse NEW_REVIEW", "Use --read CPU DATA half NEW_REVIEW"),
    ('Need(backend=="CPU"&&preset=="coarse","Only declared CPU bounded2s coarse preset admitted");', 'Need(backend=="CPU"&&preset=="half","Only declared CPU bounded2s half preset admitted");'),
    ("hgmid2::Read(false,argv[3],false,false,argv[5]);", "hgmid2half::Read(false,argv[3],false,true,argv[5]);"),
    ("Bounded2s mid-window pure native read rejected", "Bounded2s half-window pure native read rejected"),
)
owner = review = np = None


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def pin(name):
    size, digest = PINS[name]
    e = dict(path=str((T / name).resolve()), bytes=size, sha256=digest)
    owner.bind(e)
    return e


def module(name, relative):
    size, digest = PINS[relative]
    path = T / relative
    e = entry(path)
    need((e["bytes"], e["sha256"]) == (size, digest), "Pinned definitions changed: " + relative)
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def initialize():
    global owner, review, np
    sys.dont_write_bytecode = True
    owner = module("frozen_coarse_owner_for_half", "support/upl_hg_mid2_run_r1.py")
    for name in PINS:
        pin(name)
    review = module("frozen_mid2_pure_review", "support/upl_hg_mid2_review_r1.py")
    review.initialize()  # Pure definitions/pins only, never its current/old dataset or main.
    np = review.np
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable, np.__file__):
        owner.adopt(path)


def final_bindings():
    unique = {}
    for e in list(owner.BOUND.values()) + review.gathered_bindings():
        key = str(Path(e["path"]).resolve()).casefold()
        need(key not in unique or owner.same_entry(unique[key], e), "Conflicting half bindings")
        unique[key] = e
    owner.reverify()
    review.closure()
    return list(unique.values())


def file_record(kind):
    return T / "logs" / (HNAME + ".helper.json" if kind == "build-reader" else
                          NAME + ".inputs.json" if kind == "prepare" else
                          NAME + ".compare.json" if kind == "compare" else TAG + "." + kind + ".json")


def context():
    build_e, build = owner.build_closure()
    manifest_e = pin("logs/upl_hg_mid2_r1.inputs.json")
    manifest = owner.read(manifest_e)
    native_e = pin("logs/upl_hg_mid2_CPU1_coarse_r1.native.json")
    native = owner.read(native_e)
    checked = owner.read(pin("logs/upl_hg_mid2_review_r1.check.json"))
    root_e = pin("notes/upl_hg_mid2_root_r1.json")
    root = owner.read(root_e)
    need(manifest.get("stage") == "upl_hg_mid2_prepare_r1" and manifest.get("passed") and manifest.get("prepared") and
         manifest["source_build"] == build_e and manifest["source_program"] == build["program"] and len(manifest["jobs"]) == 1 and
         native.get("stage") == "upl_hg_mid2_native_run_r1" and native.get("passed") and native.get("bindings_unchanged") and
         native.get("original_native_guards_passed") and native.get("drainage_nonempty_per_frame_verified") and
         native["source_build"] == build_e and checked.get("stage") == "upl_hg_mid2_review_r1" and checked.get("passed") and
         owner.same_entry(checked["current_native_check"], native_e) and checked.get("physical_acceptance") is False and
         root.get("stage") == "upl_hg_mid2_root_r1" and root.get("physical_acceptance") is False and root["root_visual_review"]["performed"] and
         root["next_decision"]["prepare_fresh_independent_2s_half"] and not root["next_decision"]["half_execution_admitted_by_this_note"],
         "Promising completed coarse native/physical review, never automatic half admission, required")
    source = manifest["jobs"][0]
    need(source["steps"] == 1048576 and source["expected_samples"] == N and source["dt_s"] == 2 * DT and source["end_s"] == 2 and
         source["event_completed_step"] == EVENT // 2 and source["threads"] == 1, "Own coarse2s source plan differs")
    saved = [dict(part=i, completed_steps=2 * int(v["completed_steps"]),
                  saved_step=2 * int(v["completed_steps"]) - 1 if i else 0,
                  time_s=2 * int(v["completed_steps"]) * DT) for i, v in enumerate(source["saved_clock_table"])]
    need(len(saved) == N and saved[-1]["completed_steps"] == STEPS and saved[-1]["time_s"] == 2 and
         all(v["completed_steps"] == 2 * review.FULL_STEPS[i] for i, v in enumerate(saved)) and
         sum(v["completed_steps"] > EVENT for v in saved) == 1313, "Independent doubled integer schedule differs")
    for key in ("runtime", "configuration_file", "initial_BI4", "normals"):
        owner.bind(source[key])
    completion = owner.read(native["completion"])
    need(completion.get("stage") == "upl_hg_mid2_native_r1" and completion.get("passed") and completion["samples"] == N and
         completion["native_total_arrays"] == 22 and completion["total_native_count"] == 1040 and completion["actual_end_s"] == 2,
         "Genuine coarse completion schema template required")
    return dict(build_e=build_e, build=build, coarse_manifest=manifest_e, coarse_native=native_e,
                coarse_review=pin("logs/upl_hg_mid2_review_r1.check.json"), root_review=root_e,
                source=source, saved=saved, schema=completion)


def expected_args():
    return ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(PREFIX), str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:2097152"]


def prepared(ctx):
    e = owner.adopt(file_record("prepare"))
    m = owner.read(e)
    need(m.get("stage") == "upl_hg_mid2_half_prepare_r1" and m.get("passed") and m.get("prepared") and m.get("bindings_unchanged") and
         m["source_build"] == ctx["build_e"] and m["source_program"] == ctx["build"]["program"] and
         m["source_input_manifest"] == ctx["coarse_manifest"] and len(m["jobs"]) == 1 and m["physical_acceptance"] is False,
         "Own new half preparation required")
    job = m["jobs"][0]
    expected = dict(tag=TAG, backend="CPU", configuration="ReleaseCPU", window="half", threads=1,
                    input_prefix=str(PREFIX), output_directory=str(OUT), arguments=expected_args(), steps=STEPS,
                    dt_s=DT, end_s=2, expected_samples=N, event_completed_step=EVENT, post_open_frames=1313,
                    post_open_drained_particle_checks_expected=13130, expected_native_total_arrays=22,
                    expected_total_native_count=1040, expected_HG_counters=COUNTERS, saved_clock_table=ctx["saved"])
    need(all(job.get(k) == v for k, v in expected.items()), "Fixed half job differs")
    for e_ in m["files"]:
        owner.bind(e_)
    return e, m, job


def prepare_action(result, ctx):
    cfg = T / "configs/upl_hg_mid2_half_r1.xml"
    owner.fresh(PREFIX.parent, cfg, OUT)
    source = owner.bind(ctx["source"]["runtime"]).read_bytes()
    text = source.decode("utf-8")
    changes = [(f'<parameter key="{key}" value="1.9073486328125E-06"',
                f'<parameter key="{key}" value="9.5367431640625E-07"') for key in ("DtIni", "DtFixed")]
    target = text
    for old, new in changes:
        need(target.count(old) == 1, "One exact locked-dt token required")
        target = target.replace(old, new)
    inverse = target
    for old, new in reversed(changes):
        need(inverse.count(new) == 1, "One exact inverse locked-dt token required")
        inverse = inverse.replace(new, old)
    before, after = DOM.parseString(text), DOM.parseString(target)
    inverse_dom = DOM.parseString(target)
    for node in inverse_dom.getElementsByTagName("parameter"):
        if node.getAttribute("key") in ("DtIni", "DtFixed"):
            node.setAttribute("value", "1.9073486328125E-06")
    timeouts = lambda doc: [node.toxml() for node in doc.getElementsByTagName("timeout")]
    need(inverse.encode("utf-8") == source and inverse_dom.toxml() == before.toxml() and
         timeouts(after) == timeouts(before) and len(after.getElementsByTagName("tout")) == 5,
         "Exact inverse-two text/UTF8/DOM and unchanged five timeouts required")
    PREFIX.parent.mkdir()
    files = []
    for path, payload in ((cfg, target.encode("utf-8")), (PREFIX.with_suffix(".xml"), target.encode("utf-8")),
                          (PREFIX.with_suffix(".bi4"), owner.bind(ctx["source"]["initial_BI4"]).read_bytes()),
                          (Path(str(PREFIX) + "_Normals.nbi4"), owner.bind(ctx["source"]["normals"]).read_bytes())):
        with path.open("xb") as stream:
            stream.write(payload)
        files.append(owner.adopt(path))
    job = dict(tag=TAG, backend="CPU", configuration="ReleaseCPU", window="half", threads=1, input_variant="half",
               input_prefix=str(PREFIX), output_directory=str(OUT), arguments=expected_args(), steps=STEPS, dt_s=DT, end_s=2,
               expected_samples=N, event_completed_step=EVENT, ramp_and_drain_event_s=EVENT * DT,
               post_open_frames=1313, post_open_drained_particle_checks_expected=13130, expected_native_total_arrays=22,
               expected_total_native_count=1040, expected_HG_counters=COUNTERS, saved_clock_table=ctx["saved"],
               configuration_file=files[0], runtime=files[1], initial_BI4=files[2], normals=files[3])
    need(all(files[2][k] == ctx["source"]["initial_BI4"][k] and files[3][k] == ctx["source"]["normals"][k] for k in ("bytes", "sha256")),
         "Unchanged seed/Normals bytes required")
    result.update(stage="upl_hg_mid2_half_prepare_r1", prepared=True, source_input_manifest=ctx["coarse_manifest"],
                  source_job=ctx["source"], source_build=ctx["build_e"], source_program=ctx["build"]["program"], jobs=[job], files=files,
                  inverse_two_value_text_UTF8_DOM_exact=True, all_five_physical_timeouts_unchanged=True,
                  old_JSON_times_used_as_equality_truth=False, only_DtIni_DtFixed_changed=True,
                  solver_reader_or_build_invoked=False)


def native_call(program, arguments, cwd, receipt, log, stage, extra=None, env=None):
    owner.fresh(receipt, log)
    code = failure = None
    started, wall = utc(), time.perf_counter()
    try:
        with log.open("xb") as stream:
            completed = subprocess.run([program["path"], *arguments], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                       shell=False, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            code = completed.returncode
    except Exception as exc:
        failure = str(exc)
    value = dict(stage=stage, tag=TAG, configuration="ReleaseCPU", window="half", program=program, target_program=program,
                 arguments=arguments, target_arguments=arguments, working_directory=str(cwd), started_utc=started, ended_utc=utc(),
                 direct_native_call=True, shell=False, typed_returncode_captured_immediately=type(code) is int,
                 owned_call_exited=type(code) is int, exit_code=code, invocation_failure=failure,
                 invocation_wall_seconds=time.perf_counter() - wall, log=entry(log) if log.exists() else None, physical_acceptance=False)
    value.update(extra or {})
    owner.seal(receipt, value)  # Original native result is sealed before any target output analysis.
    e = owner.adopt(receipt)
    return e, code, failure


def own_call(e, stage):
    c = owner.read(e)
    need(c.get("stage") == stage and c.get("direct_native_call") is True and c.get("owned_call_exited") is True and
         c.get("typed_returncode_captured_immediately") is True and type(c.get("exit_code")) is int and c["exit_code"] == 0 and
         c.get("invocation_failure") is None and c["program"] == c["target_program"] and c["arguments"] == c["target_arguments"],
         "Actual original half native integer exit0/target required")
    owner.bind(c["program"])
    owner.bind(c["log"])
    return c


def build_action(result, ctx):
    manifest_e, manifest, job = prepared(ctx)
    owner.fresh(HFOLDER)
    coarse_h_e = pin("logs/upl_hg_mid2_reader_ReleaseCPU_r1.helper.json")
    h = owner.read(coarse_h_e)
    need(h["passed"] and h["source_build"] == ctx["build_e"] and h["CPU_non_main_objects"] == len(h["objects"]) == 85 and
         h["link_object_count"] == 86 and len(h["libraries"]) == 17 and len(h["runtime"]) == 4 and
         h["actual_headers_archived_not_live"] and h["exact_link_closure_verified"], "Actual coarse reader recipe closure required")
    source_e, cpp_e = pin("support/upl_hg_mid2_native_r1.cpp"), pin("support/upl_hg_mid2_half_native_r1.cpp")
    expected = owner.bind(source_e).read_bytes().decode("utf-8")
    for old, new in CPP_CHANGES:
        need(expected.count(old) == 1, "Half CPP mechanical substitution occurrence differs")
        expected = expected.replace(old, new)
    need(expected.encode("utf-8") == owner.bind(cpp_e).read_bytes(), "Half CPP differs outside the exact nine clock/label changes")
    cc, lc = owner.typed_build(h["compile_call"], True), owner.typed_build(h["link_call"], True)
    obj, exe, deps = HFOLDER / "helper.obj", HFOLDER / "upl_hg_mid2_half_native_r1.exe", HFOLDER / "compile.dependencies.json"
    replacements = {str(owner.bind(h["mechanical_source_transform"]["derived"])): str(T / "support/upl_hg_mid2_half_native_r1.cpp"),
                    h["compiler_dependency_record"]["path"]: str(deps)}
    compile_args, remaps = [], dict(cpp=0, dependencies=0, obj=0, pdb=0)
    for arg in cc["arguments"]:
        if arg in replacements:
            compile_args.append(replacements[arg]); remaps["cpp" if arg.endswith(".cpp") else "dependencies"] += 1
        elif arg.lower().startswith("/fo"):
            compile_args.append("/Fo" + str(obj)); remaps["obj"] += 1
        elif arg.lower().startswith("/fd"):
            compile_args.append("/Fd" + str(HFOLDER / "compile.pdb")); remaps["pdb"] += 1
        else:
            compile_args.append(arg)
    need(all(v == 1 for v in remaps.values()), "Only CPP/dependency/Fo/Fd compile remaps admitted")
    need(sum(a == h["helper_object"]["path"] for a in lc["arguments"]) == 1 and
         sum(a.upper().startswith("/OUT:") for a in lc["arguments"]) == 1, "Exactly one helper-object and output link remap required")
    link_args = [str(obj) if a == h["helper_object"]["path"] else "/OUT:" + str(exe) if a.upper().startswith("/OUT:") else a for a in lc["arguments"]]
    actual_objects = [str(Path(a).resolve()).casefold() for a in link_args if a.lower().endswith(".obj")]
    need(len(actual_objects) == len(set(actual_objects)) == 86 and set(actual_objects) ==
         {str(Path(e["path"]).resolve()).casefold() for e in h["objects"]} | {str(obj.resolve()).casefold()} and
         [Path(a).name.lower() for a in link_args if a.lower().endswith(".lib")] == [Path(e["path"]).name.lower() for e in h["libraries"]],
         "Exact current85+1/ordered17 library link closure required")
    for group in (h["objects"], h["source_snapshots265"], h["libraries"], h["tools"], h["actual_project_headers"]):
        for e in group:
            owner.bind(e)
    for e in (h["neutral_include"], h["documentation_snapshot"], h["case_readme_snapshot"], h["environment_source"]):
        owner.bind(e)
    env = dict(os.environ)
    env.update(h["environment"]["selected"])
    env["PATH"] = str(Path(cc["program"]["path"]).parent) + ";" + env.get("PATH", "")
    owner.fresh(*(T / "logs" / (HNAME + suffix) for suffix in
                  ("_Compile.call.json", "_Compile.log", "_Link.call.json", "_Link.log")))
    owner.reverify()
    HFOLDER.mkdir()
    result.update(source_build=ctx["build_e"], prepared_inputs=manifest_e, retained_compiler_recipe=coarse_h_e,
                  kind="reader", objects=h["objects"], source_snapshots265=h["source_snapshots265"], libraries=h["libraries"],
                  tools=h["tools"], neutral_include=h["neutral_include"], archived_header_include_root=h["archived_header_include_root"],
                  mechanical_source_transform=dict(parent=source_e, derived=cpp_e, substitutions=CPP_CHANGES,
                      whole_source_text_and_UTF8_bytes_exact=True, original_numerical_guard_bodies_unchanged=True))
    e, _, _ = native_call(cc["program"], compile_args, SRC, T / "logs" / (HNAME + "_Compile.call.json"),
                          T / "logs" / (HNAME + "_Compile.log"), "upl_hg_mid2_half_compile_r1", env=env)
    result["compile_call"] = e
    own_call(e, "upl_hg_mid2_half_compile_r1")
    dependency_e = owner.adopt(deps)
    dependency = owner.read(dependency_e)["Data"]
    archive = Path(h["archived_header_include_root"]).resolve()
    project = {str(Path(e["path"]).resolve()).casefold(): e for e in h["source_snapshots265"]}
    headers = [project[str(Path(p).resolve()).casefold()] for p in dependency["Includes"] if Path(p).resolve().parent == archive]
    local = [Path(p).resolve() for p in dependency["Includes"] if Path(p).resolve().parent == (T / "support").resolve()]
    need(Path(dependency["Source"]).resolve() == Path(cpp_e["path"]).resolve() and local == [Path(h["neutral_include"]["path"]).resolve()] and
         headers and not any(Path(p).resolve().is_relative_to(SRC / "source") for p in dependency["Includes"]),
         "Actual half CPP/one neutral/archived headers only required")
    e, _, _ = native_call(lc["program"], link_args, SRC, T / "logs" / (HNAME + "_Link.call.json"),
                          T / "logs" / (HNAME + "_Link.log"), "upl_hg_mid2_half_link_r1", env=env)
    result["link_call"] = e
    own_call(e, "upl_hg_mid2_half_link_r1")
    runtime = []
    for pair in h["runtime"]:
        original = pair["copy"]
        dest = HFOLDER / Path(original["path"]).name
        with dest.open("xb") as stream:
            stream.write(owner.bind(original).read_bytes())
        copy = owner.adopt(dest)
        need(all(copy[k] == original[k] for k in ("bytes", "sha256")), "Half runtime copy differs")
        runtime.append(dict(original=original, copy=copy))
    result.update(stage="upl_hg_mid2_half_reader_build_r1", program=owner.adopt(exe), helper_object=owner.adopt(obj),
                  compiler_dependency_record=dependency_e, actual_project_headers=headers, runtime=runtime,
                  CPU_non_main_objects=85, link_object_count=86, exact_link_closure_verified=True,
                  actual_headers_archived_not_live=True, program_run=False, solver_started=False)


def helper(ctx, manifest_e):
    e = owner.adopt(file_record("build-reader"))
    h = owner.read(e)
    need(h.get("stage") == "upl_hg_mid2_half_reader_build_r1" and h.get("passed") and h.get("bindings_unchanged") and
         h["source_build"] == ctx["build_e"] and h["prepared_inputs"] == manifest_e and
         h["CPU_non_main_objects"] == len(h["objects"]) == 85 and h["link_object_count"] == 86 and h["exact_link_closure_verified"] and
         h["actual_headers_archived_not_live"] and len(h["libraries"]) == 17 and len(h["runtime"]) == 4 and h["program_run"] is False,
         "Own passed half85+1 typed reader helper required")
    for value in h["inputs"]:
        owner.bind(value)
    own_call(h["compile_call"], "upl_hg_mid2_half_compile_r1")
    own_call(h["link_call"], "upl_hg_mid2_half_link_r1")
    for value in [h["program"], h["helper_object"], h["compiler_dependency_record"], *h["actual_project_headers"]]:
        owner.bind(value)
    for pair in h["runtime"]:
        owner.bind(pair["original"]); owner.bind(pair["copy"])
    return e, h


def admission(path, ctx, manifest_e, helper_e):
    need(path is not None, "Run requires a separate root half admission")
    e = owner.adopt(path)
    a = owner.read(e)
    need(a.get("stage") == "upl_hg_mid2_half_admission_r1" and a.get("passed") is True and a.get("allowed_jobs") == [TAG] and
         a.get("physical_acceptance") is False and a.get("inputs"), "Only explicit fixed-half root admission required")
    for required in (manifest_e, helper_e, ctx["coarse_native"], ctx["coarse_review"], ctx["root_review"]):
        need(sum(owner.same_entry(x, required) for x in a["inputs"]) == 1, "Admission missing/duplicated exact own prerequisite")
    for value in a["inputs"]:
        owner.bind(value)
    return e


def output_checks(result):
    result["run_out"] = owner.adopt(OUT / "Run.out")
    text = owner.bind(result["run_out"]).read_text(encoding="utf-8-sig")
    need('RunMode="Stable - Pos-Double - Single core"' in text and "Finished execution (code=0)." in text and
         re.search(r"Steps of simulation[.]+:\s*2097152(?:\s|$)", text) and re.search(r"Excluded particles[.]+:\s*0(?:\s|$)", text) and
         re.search(r"SoilHourglassXi: 0\.1\s", text) and 'SoilDamping="BuiFukagawa2013"' in text and
         re.search(r"SoilDampingCoef=0\.02(?:\s|$)", text) and 'SoilBoundaryDerivativeSPR="None"' in text,
         "Actual half CPU1 finish/step/xi/eta/SPR/no-exclusion guards failed")
    counts = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    cached = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    need(counts and cached and tuple(map(int, counts.groups())) == (4194304, 2097152, 2097152, 4194304) and
         tuple(map(int, cached.groups())) == (2097153, 2097151), "Actual half HG stage/cache counts differ")
    diag = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    need(diag, "Actual half current-J force/inertia diagnostics missing")
    net, actual, tau, spin = map(float, diag.groups())
    need(all(math.isfinite(v) and v >= 0 for v in (net, actual, tau, spin)) and tau <= .2 and spin < .01, "Original HG finite/stiffness/spin guards failed")
    result["HG"] = dict(counters=COUNTERS, max_reference_history_net_force=net, max_actual_float_add_net_force=actual,
                        max_dt_over_tau=tau, spinbound=spin, reference_history_is_Q_over_M0=True, actual_inertia_is_current_mi=True)
    need(sorted(p.name for p in (OUT / "data").glob("Part_*.bi4")) == ["Part_%04d.bi4" % i for i in range(N)], "Actual1517 half PART sequence differs")
    result.update(steps=STEPS, native_frames=N)
    for key, label in (("simulation_runtime_seconds_reported", "Simulation Runtime"), ("total_runtime_seconds_reported", "Total Runtime")):
        m = re.search(re.escape(label) + r"[.]+:\s*([0-9.eE+-]+) sec\.", text)
        need(m and math.isfinite(float(m[1])) and float(m[1]) >= 0, "Actual half runtime missing")
        result[key] = float(m[1])


def run_action(result, ctx, admission_path):
    manifest_e, manifest, job = prepared(ctx)
    h_e, h = helper(ctx, manifest_e)
    a_e = admission(admission_path, ctx, manifest_e, h_e)
    start_path, call_path, log = (T / "logs" / (TAG + suffix) for suffix in (".start.json", ".call.json", ".log"))
    owner.fresh(OUT, start_path, call_path, log)
    import psutil
    owner.adopt(psutil.__file__)
    active = [p.info for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"])
              if (p.info["name"] or "").lower().startswith("dualsphysics") and "cpu" in (p.info["name"] or "").lower()]
    need(not active, "Another actual CPU solver is active")
    me = psutil.Process()
    identity = dict(pid=me.pid, created_epoch=me.create_time(), exe=me.exe(), command=me.cmdline(), cwd=str(Path.cwd().resolve()))
    result.update(job=job, input_manifest=manifest_e, source_build=ctx["build_e"], program=ctx["build"]["program"],
                  reader_helper=h_e, admission=a_e, arguments=job["arguments"], output_directory=str(OUT), CPU_processes_before=active)
    owner.seal(start_path, dict(stage="upl_hg_mid2_half_start_r1", tag=TAG, configuration="ReleaseCPU", window="half", utc=utc(),
        owner=identity, owner_script=owner.adopt(__file__), job=job, program=result["program"], arguments=job["arguments"],
        input_manifest=manifest_e, source_build=ctx["build_e"], reader_helper=h_e, admission=a_e, inputs=final_bindings(),
        direct_owner_no_scheduler=True, native_call_started_by_start_record=False, physical_acceptance=False))
    result["start_record"] = owner.adopt(start_path)
    owner.reverify()
    result["call"], _, _ = native_call(result["program"], job["arguments"], SRC, call_path, log, "upl_hg_mid2_half_call_r1",
        dict(start_record=result["start_record"], actual_solver_call=True, public_project_main=True, fixture_or_Run_override=False, restart=False))
    own_call(result["call"], "upl_hg_mid2_half_call_r1")
    output_checks(result)
    result["files"] = owner.inventory(OUT)


def completed_run(ctx):
    e = owner.adopt(file_record("run"))
    r = owner.read(e)
    manifest_e, manifest, job = prepared(ctx)
    h_e, h = helper(ctx, manifest_e)
    need(r.get("stage") == "upl_hg_mid2_half_run_r1" and r.get("passed") and r.get("bindings_unchanged") and
         r["job"] == job and r["source_build"] == ctx["build_e"] and r["program"] == ctx["build"]["program"] and
         r["reader_helper"] == h_e and r["steps"] == STEPS and r["native_frames"] == N and r["physical_acceptance"] is False,
         "Own completed half run required")
    admission(Path(r["admission"]["path"]), ctx, manifest_e, h_e)
    c = own_call(r["call"], "upl_hg_mid2_half_call_r1")
    need(c["arguments"] == job["arguments"] and c["program"] == r["program"] and c["start_record"] == r["start_record"], "Half own target/start differs")
    owner.bind(r["start_record"])
    need({Path(v["path"]).resolve() for v in r["files"]} == {p.resolve() for p in OUT.rglob("*") if p.is_file()}, "Half raw output membership changed")
    for value in r["files"] + r["inputs"]:
        owner.bind(value)
    return e, r, h_e, h


def exports(native, ctx):
    leaves = {Path(v["path"]).name: v for v in native["files"]}
    need(len(native["files"]) == len(leaves) == 13 and set(leaves) == review.full.LEAVES and leaves["completion.json"] == native["completion"] and
         all(Path(v["path"]).resolve().parent == NATIVE.resolve() for v in leaves.values()), "Own half13 output leaves required")
    for value in native["files"]:
        owner.bind(value)
    done = owner.read(native["completion"])
    template = ctx["schema"]
    need(set(done) == set(template), "Half completion key schema differs from mechanically unchanged coarse reader")
    same_keys = ("backend", "window", "model", "conductivity_model", "conductivity_Ck", "native_count", "fixed_count", "total_native_count",
                 "samples", "physical_columns", "physical_schema", "original_typed_arrays", "native_dynamic_double_arrays", "native_total_arrays",
                 "planned_end_s", "actual_end_s", "declared_ramp_and_drain_event_s", "noninitial_signed_dterror_intervals", "soil_ledger_checks",
                 "fixed_public_zero_marker_checks", "all_native_J_theta_rows", "soil_native_n_rows", "post_open_frames",
                 "post_open_drained_particle_checks", "max_activeDrainCount")
    need(all(done[k] == template[k] for k in same_keys) and all(done[k] is v for k, v in template.items() if type(v) is bool) and
         done["stage"] == "upl_hg_mid2_half_native_r1" and done["preset"] == "half" and done["grid"] == "h" and
         done["dt_s"] == DT and done["planned_completed_steps"] == STEPS and done["post_open_completed_step_threshold"] == EVENT and
         done["initial_empty_dterror_intervals"] in (0, 1) and math.isfinite(done["max_noninitial_signed_dterror_s"]) and
         done["max_noninitial_signed_dterror_s"] <= 1e-14 and 0 <= done["max_ledger_relative_error"] <= 5e-13,
         "Original half schema/typed guard flags/ledger/signed-clock coverage differ")
    binaries = {name: review.full.binary(leaves[name], name, N) for name in review.full.STRIDES}
    p = np.memmap(binaries["physical.bin"][0], mode="r", offset=12, shape=(N,), dtype=[("time", "<f8"), ("q", "<f8", (1000, 26))])
    clock = np.memmap(binaries["clock.bin"][0], mode="r", offset=8, shape=(N,), dtype=[("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    steps = np.asarray([v["completed_steps"] for v in ctx["saved"]])
    times = steps * DT
    need(review.full.bits(p["time"], times) and review.full.bits(clock["time"], times) and review.full.bits(clock["dt"], np.full(N, DT)) and
         np.array_equal(clock["step"], np.where(steps, steps - 1, 0)) and np.isfinite(clock["error"]).all() and
         np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Actual half native binary clocks/signed intervals differ")
    ids = review.full.csv_rows(leaves["native_ids.csv"])
    fixed = review.full.csv_rows(leaves["fixed_ids.csv"])
    need(len(ids) == 1000 and all((int(v["row"]), int(v["id"])) == (i, i + 40) for i, v in enumerate(ids)) and
         len(fixed) == 40 and all((int(v["row"]), int(v["id"])) == (i, i) for i, v in enumerate(fixed)), "All1040 original half IDs differ")
    columns = review.full.csv_rows(leaves["columns.csv"])
    need([v["name"] for v in columns] == review.full.FIELDS and [int(v["column"]) for v in columns] == list(range(26)), "Actual common26 half meanings differ")
    history = review.full.csv_rows(leaves["history.csv"])
    need(len(history) == N, "All1517 half history rows required")
    for i, row in enumerate(history):
        post = steps[i] > EVENT
        receiver = np.isin(p["q"][i, :, 17], (2., 3.)) if post else np.zeros(1000, dtype=bool)
        need((int(row["part"]), int(row["completed_step"]), int(row["saved_step"]), int(row["activeDrainCount"])) ==
             (i, int(steps[i]), int(clock["step"][i]), 10 if post else 0) and int(receiver.sum()) == (10 if post else 0) and
             np.all(p["q"][i, receiver, 6] == 0) and review.full.bits(float(row["time_s"]), times[i]) and
             review.full.bits(float(row["dt_s"]), DT) and review.full.bits(float(row["signed_dterror_s"]), clock["error"][i]) and
             int(row["dterror_used_in_noninitial_summary"]) == int(i > 0) and
             int(row["dterror_interval_empty"]) == int(clock["error"][i] == -np.finfo(float).max) and
             0 <= float(row["max_ledger_relative_error"]) <= 5e-13, "Per-frame true half drainage/clock/ledger differs")
    data = dict(samples=N, leaves=leaves, binaries=binaries, p=p, clock=clock, history=history, completion=done,
                x0=np.asarray([[float(v[k]) for k in ("x0", "y0", "z0")] for v in ids]),
                fixed_x0=np.asarray([[float(v[k]) for k in ("x0", "y0", "z0")] for v in fixed]))
    return review.geometry(review.extras(data, N))


def native_action(result, ctx):
    run_e, run, helper_e, h = completed_run(ctx)
    owner.fresh(NATIVE)
    result.update(job=run["job"], source_run=run_e, source_start=run["start_record"], source_call=run["call"], input_manifest=run["input_manifest"],
                  source_build=run["source_build"], program=run["program"], reader_helper=helper_e,
                  paths=dict(solver_dir=str(OUT), native_dir=str(NATIVE)))
    owner.reverify()
    result["reader_call"], _, _ = native_call(h["program"], ["--read", "CPU", str(OUT / "data"), "half", str(NATIVE)], T.parent,
        T / "logs" / (TAG + "_reader.call.json"), T / "logs" / (TAG + "_reader.log"), "upl_hg_mid2_half_reader_call_r1",
        dict(pure_native_reader=True, solver_or_build_invoked=False, source_run=run_e, source_start=run["start_record"]))
    own_call(result["reader_call"], "upl_hg_mid2_half_reader_call_r1")
    result.update(completion=owner.adopt(NATIVE / "completion.json"), files=owner.inventory(NATIVE))
    exports(result, ctx)
    result.update(original_native_guards_passed=True, drainage_nonempty_per_frame_verified=True,
                  physical_FSType_receiver_mask_independently_recounted=True, reader_executed_by_this_action=True,
                  typed_native_total_arrays=22, typed_native_total_ID_count=1040, typed_soil_ledger_checks=1517000,
                  typed_fixed_zero_marker_checks=60680, typed_all_native_J_theta_rows=1577680,
                  signed_noninitial_dterror_intervals_verified=1516, post_open_frames_verified=1313,
                  actual_drained_receiver_checks=13130, ledger_CSV_rows_reparsed=0, solver_or_build_invoked=False)


def compare_action(result, ctx):
    e = owner.adopt(file_record("native"))
    native = owner.read(e)
    need(native.get("stage") == "upl_hg_mid2_half_native_run_r1" and native.get("passed") and native.get("bindings_unchanged") and
         native.get("original_native_guards_passed") and native.get("drainage_nonempty_per_frame_verified") and not native["physical_acceptance"],
         "Own passed half native safety required")
    run_e, run, helper_e, h = completed_run(ctx)
    need(native["source_run"] == run_e and native["reader_helper"] == helper_e, "Half native/run/helper association differs")
    reader = own_call(native["reader_call"], "upl_hg_mid2_half_reader_call_r1")
    need(reader["program"] == h["program"] and reader["arguments"] == ["--read", "CPU", str(OUT / "data"), "half", str(NATIVE)], "Actual half decoder target differs")
    half, coarse = exports(native, ctx), review.current()
    cpu8 = review.full.dataset("half", True)
    cpu8["leaves"] = {Path(v["path"]).name: v for v in cpu8["native"]["files"]}
    need(coarse["run"]["program"] == run["program"] == cpu8["run"]["program"] and
         coarse["run"]["source_build"] == run["source_build"] == cpu8["run"]["source_build"], "Same current program/build required")
    need(review.full.bits(coarse["p"]["q"][0], half["p"]["q"][0]) and
         review.full.bits(half["p"]["q"][0], cpu8["p"]["q"][0]) and
         review.full.bits(coarse["jt"]["q"][0], half["jt"]["q"][0]) and
         review.full.bits(coarse["n"]["q"][0], half["n"]["q"][0]), "Same actual initial common26/all1040 J-theta/soil n required")
    paired, maxima = review.differences(coarse, half, N, "independent2s_coarse_vs_half")
    early, early_max = review.differences(half, cpu8, 1469, "half_same_dt_CPU1_vs_CPU8_prefix_only")
    for rows, left, right in ((paired, coarse, half), (early, half, cpu8)):
        for i, row in enumerate(rows):
            row["coarse_grid_reference_completed_step"] = row.pop("completed_step")
            row["left_actual_completed_step"] = int(left["clock"]["step"][i]) + 1 if i else 0
            row["right_actual_completed_step"] = int(right["clock"]["step"][i]) + 1 if i else 0
    gates = lambda m: dict(pressure_RMS_le_5Pa=m["max_pressure_RMS_Pa"] <= 5.,
                           material_XYZ_le_0_005mm=m["max_material_XYZ_difference_mm"] <= .005,
                           actual_time_le_1e_minus14_s=m["max_actual_time_difference_s"] <= 1e-14)
    prefixes = review.binary_prefix(half, cpu8, 1469, False, "half_CPU1_vs_genuine_CPU8_half1469_descriptive")
    csv_path, prefix_path = T / "logs" / (NAME + ".compare.csv"), T / "logs" / (NAME + ".prefix.csv")
    owner.fresh(csv_path, prefix_path)
    review.write_csv(csv_path, paired + early)
    review.write_csv(prefix_path, prefixes)
    result.update(source_runs=[coarse["run_entry"], run_e, cpu8["run_entry"]], native_checks=[coarse["check"], e, cpu8["check"]],
                  independent_2s_half_performed=True, samples=1517, independent_half_gates=gates(maxima), independent_half_maxima=maxima,
                  early_half_thread_gates=gates(early_max), early_half_thread_maxima=early_max,
                  genuine_CPU8_half_raw_prefix_equalities_descriptive=prefixes, nonexistent_CPU1_half_short_bitproof_claimed=False,
                  initial_common26_all1040_J_theta_soil_n_bit_equal=True,
                  initial_common26_genuine_CPU8_half_bit_equal=True,
                  all26_field_rows=len(paired), early_thread_rows=len(early), files=[owner.adopt(csv_path), owner.adopt(prefix_path)],
                  solver_reader_or_build_invoked=False, no_time_interpolation_smoothing_snap_or_periodic_unwrap=True)
    need(all(gates(maxima).values()) and all(gates(early_max).values()), "Original independent-half or same-dt early-thread gates failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("prepare", "build-reader", "run", "native", "compare"), required=True)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit authorization of this one action required")
    record = file_record(args.action)
    need(not record.exists(), "Retained action receipt protected")
    stage = {"prepare": "upl_hg_mid2_half_prepare_r1", "build-reader": "upl_hg_mid2_half_reader_build_r1",
             "run": "upl_hg_mid2_half_run_r1", "native": "upl_hg_mid2_half_native_run_r1", "compare": "upl_hg_mid2_half_compare_r1"}[args.action]
    result = dict(stage=stage, tag=TAG, action=args.action, passed=False, backend="CPU", configuration="ReleaseCPU", window="half", threads=1,
                  physical_acceptance=False, later_full_or_formal_admitted=False, automatic_follow_up=False, failure=None)
    if args.action == "run":
        result.update(direct_owner_no_scheduler=True, native_decoder_invoked=False, all22_native_fields_review_pending=True,
                      actual_native_clocks_review_pending=True, public_project_main=True, fixture_or_Run_override=False)
    try:
        initialize()
        ctx = context()
        if args.action == "run":
            run_action(result, ctx, args.admission)
        else:
            {"prepare": prepare_action, "build-reader": build_action, "native": native_action, "compare": compare_action}[args.action](result, ctx)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        if owner is None or review is None:
            raise ValueError("Pinned definitions were not initialized")
        result["inputs"] = final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(owner.BOUND.values()) if owner else []
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
        result["passed"] = False
    if args.action in ("run", "native") and "files" not in result:
        directory = OUT if args.action == "run" else NATIVE
        if directory.exists() and owner:
            result["files"] = owner.inventory(directory)
    result.update(source_or_formal_or_canonical_files_written=False, original_thresholds_relaxed=False,
                  same_force_stage_load_budget_verified=False, force_stage_guard_independently_observed=False,
                  following_action_launched=False, watcher_or_queue_invoked=False)
    with record.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], action=args.action, receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
