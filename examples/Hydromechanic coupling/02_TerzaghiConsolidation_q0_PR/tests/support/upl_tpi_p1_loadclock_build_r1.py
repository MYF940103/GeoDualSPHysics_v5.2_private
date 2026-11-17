"""One independently admitted two-host private P1 load-clock build; never run the program."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import tempfile
import upl_tpi_cpu_build_r2 as b
import upl_tpi_gpu_build_r1 as g
import upl_tpi_m0_dt_build_r3 as prior

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_p1_loadclock_build_r1"
NOTE = T/"notes"/(TAG+".md")
HEADER = "upl_tpi_p1_loadclock_r1.h"
CONFIG = {
    "DebugCPU": ("CPU", 86, "upl_tpi_m0_dt_DebugCPU_r3", "upl_tpi_m0_dt_DebugCPU_r3", "DualSPHysics5.2CPU_win64_debug"),
    "ReleaseCPU": ("CPU", 86, "upl_tpi_cpu_release_link_r3", "upl_tpi_cpu_ReleaseCPU_r2", "DualSPHysics5.2CPU_win64"),
    "Debug": ("GPU", 111, "upl_tpi_m0_dt_Debug_r2", "upl_tpi_m0_dt_Debug_r2", "DualSPHysics5.2_win64_debug"),
    "Release": ("GPU", 111, "upl_tpi_m0_dt_Release_r2", "upl_tpi_m0_dt_Release_r2", "DualSPHysics5.2_GEO_win64"),
}


class Admission:
    def __init__(self, path, configuration):
        self.entry, self.data = b.stat(path), b.read(path)
        b.need(self.data.get("stage") == TAG+".build_admission" and self.data.get("passed") is True
               and self.data.get("build_only") is True and self.data.get("configuration") == configuration,
               "Exact one-configuration build-only root admission required")
        self.frozen = {g.key(e["path"]): e for e in self.data["inputs"]}; self.used = {}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicated admitted input")

    def pin(self, path):
        key = g.key(path); b.need(key in self.frozen, "Unadmitted build input: "+str(path))
        self.used[key] = b.same(self.frozen[key]); return self.used[key]

    def finish(self):
        b.same(self.entry)
        for e in self.used.values(): b.same(e)
        return list(self.used.values())


def genuine(ad, path):
    entry = ad.pin(path); call = b.read(path)
    b.need(call.get("passed") is True and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0,
           "Original owned tool call did not actually pass")
    for key in ("program", "log"):
        if key in call: ad.pin(call[key]["path"]); b.same(call[key])
    return entry, call


def context(ad, configuration):
    backend, count, base_tag, cl_tag, exe = CONFIG[configuration]
    names = ("JSphCpu.cpp", "JSphCpuSingle.cpp") if backend == "CPU" else ("JSphGpu.cpp", "JSphGpuSingle.cpp")
    prep_path = L/("upl_tpi_p1_loadclock_"+backend+"_r1.prepare.json")
    base_path = L/(base_tag+".build.json")
    for p in (Path(__file__), NOTE, Path(b.__file__), Path(g.__file__), Path(prior.__file__), g.VCVARS, prep_path, base_path): ad.pin(p)
    prep, base = b.read(prep_path), b.read(base_path)
    b.need(prep.get("stage") == "upl_tpi_p1_loadclock_r1.prepare" and prep.get("passed") is True
        and prep.get("backend") == backend and prep.get("consumed_stats_unchanged") is True
        and prep.get("other_base_files_byte_identical") is True and prep.get("pressure_helpers_and_schema_byte_identical") is True
        and prep.get("M0_policy_header_byte_identical") is True and prep.get("CUDA_source_and_cuh_byte_identical") is True
        and prep.get("public_class_or_virtual_ABI_changed") is False and prep.get("shared_device_structures_or_inline_tokens_changed") is False,
        "Actual new host-only stage-load preparation required")
    b.need(base.get("passed") is True and base.get("configuration") == configuration
        and base.get("consumed_stats_unchanged", base.get("canonical_programs_stats_unchanged")) is True,
        "Actual passed same-configuration object/link baseline required")
    source = Path(prep["source_root"]).resolve()
    b.need(source == (T/"outputs"/("upl_tpi_p1_loadclock_"+backend+"_r1_source")).resolve(), "Unexpected new source root")
    files = {Path(e["path"]).name: e for e in prep["files"]}
    b.need(len(files) == len(prep["files"]) == (268 if backend == "CPU" else 271) and HEADER in files
        and set(prep["changed_sources"]) == set(prep["recompile_sources"]) == set(names)
        and prep["changed_headers"] == [HEADER], "Exact two-host/new-header source inventory differs")
    for e in prep["files"]: ad.pin(e["path"]); b.same(e)
    for key in ("base_prepare", "base_build", "source_diff"): ad.pin(prep[key]["path"]); b.same(prep[key])
    parent = b.read(prep["base_prepare"]["path"])
    b.need(parent.get("passed") is True and parent.get("stage") == "upl_tpi_m0_dt_r2.prepare" and parent.get("backend") == backend,
           "Real original M0 source lineage required")
    originals = {}
    for e in prep["base_source_entries"]:
        old, new = e["original"], e["pinned_snapshot"]
        for q in (old, new): ad.pin(q["path"]); b.same(q)
        b.need(g.key(new["path"]) == g.key(source/Path(old["path"]).name), "Source capture association differs")
        originals[Path(old["path"]).name] = old
    b.need(set(originals) == set(files)-{HEADER}, "Complete original source closure not preserved")
    for name in ("JSph.h", "JSphCpu.h", "JSphGpu.h", "JSphHourglassGpu.h", "JSphGpu_ker.h", "upl_tpi_cpu_r1.h", "upl_tpi_gpu_r1.h", "upl_tpi_gpu_r1.cuh", "JSphGpu_ker.cu", "upl_tpi_m0_dt_r2.h"):
        if name in originals:
            b.need((source/name).read_bytes() == Path(originals[name]["path"]).read_bytes(), "Retained ABI/pressure/device/policy member changed: "+name)
    if configuration == "ReleaseCPU":
        b.need(base.get("stage") == "upl_tpi_cpu_release_link_r3"
            and g.key(base["original_source_preparation"]["path"]) == g.key(parent["base_prepare"]["path"]),
            "ReleaseCPU must explicitly adopt the actual P1 r3 closure, not an invented M0 Release build")
        ad.pin(base["original_source_preparation"]["path"]); b.same(base["original_source_preparation"])
    ad.pin(base["program"]["path"]); b.same(base["program"])
    objects = {Path(e["path"]).name.lower(): e for e in base["objects"]}
    b.need(len(objects) == len(base["objects"]) == count, "Actual original object closure differs")
    for e in objects.values(): ad.pin(e["path"]); b.same(e)
    recipes, evidence, dependencies = {}, [], []
    for name in names:
        entry, call = genuine(ad, L/(cl_tag+"."+Path(name).stem+".call.json"))
        args = call["arguments"]
        source_args = [x for x in args if Path(x).name.lower() == name.lower()]
        b.need(len(source_args) == 1 and Path(source_args[0]).is_file(), "One complete actual CL source argument required")
        ad.pin(source_args[0]); recipes[name] = list(args); evidence.append(entry)
        dependencies.append(Path(source_args[0]).parent)
    link_entry, link_call = genuine(ad, L/(base_tag+".link.call.json")); evidence.append(link_entry)
    linked = [x for x in link_call["arguments"] if x.lower().endswith(".obj") and not x.startswith("/")]
    b.need(len(linked) == len(set(map(g.key, linked))) == count
        and {g.key(x) for x in linked} == {g.key(x["path"]) for x in objects.values()}, "Actual ordered link/object binding differs")
    tails = []
    for e in base.get("exact_CPU_tlog_source_tail_repairs", []):
        # Exact r3 ^source-header reconstruction; never split an unquoted source into two filenames.
        _, actual = prior.cpu_cl_source_tail(ad, e["tlog"]["path"], Path(e["source_header"]).name)
        b.need(actual["source_header"] == e["source_header"] and actual["original_tail_tokens"] == e["original_tail_tokens"], "Original CPU tlog source-tail proof changed")
        tails.append(actual)
    sdk = base.get("CPU_Debug_actual_SDK_adaptation", {}) if configuration == "DebugCPU" else {}
    for e in sdk.get("old_actual_sdk_header_inputs", []): ad.pin(e["path"]); b.same(e)
    if configuration == "ReleaseCPU":
        old_a = base["original_A_build"]; ad.pin(old_a["path"]); b.same(old_a); a_build = b.read(old_a["path"])
        # Legacy A libraries carry path/bytes/SHA only. Adopt their real frozen
        # stat from the passed r3 admission, never fabricate an old mtime or rehash.
        old_admission = base["root_admission"]; ad.pin(old_admission["path"]); b.same(old_admission)
        old_data = b.read(old_admission["path"])
        b.need(old_data.get("stage") == "upl_tpi_cpu_release_link_r3.admission" and old_data.get("passed") is True
            and base.get("original_object_paths_and_stats_unchanged") is True, "Actual passed P1r3 library-stat evidence required")
        old_stats = {g.key(e["path"]): e for e in old_data["inputs"]}; libraries = []
        for legacy in a_build["libraries"]:
            frozen = old_stats.get(g.key(legacy["path"]))
            b.need(frozen is not None and all(k in frozen for k in ("path", "bytes", "mtime_ns"))
                and frozen["bytes"] == legacy["bytes"], "Historical admitted library stat missing or legacy size differs")
            libraries.append(dict(entry={k: frozen[k] for k in ("path", "bytes", "mtime_ns")},
                evidence="passed_P1r3_admitted_library_stat", stat_source_admission=old_admission,
                legacy_reference={k: legacy[k] for k in ("path", "bytes")}))
        libraries.append(dict(entry=base["first_existing_libcpmt_search_candidate"], evidence="passed_P1r3_CRT_search_only"))
    else:
        libraries = [dict(entry=e["first_existing_candidate"], evidence="original_actual_link_read_binding") for e in base["actual_library_search"]]
    for e in libraries: ad.pin(e["entry"]["path"]); b.same(e["entry"])
    runtime = [e["destination"] for e in base["runtime"]]
    for e in runtime: ad.pin(e["path"]); b.same(e)
    project, solution = (b.PROJECT, b.SOLUTION) if backend == "CPU" else (g.PROJECT, g.SOLUTION)
    for p in (project, solution): ad.pin(p)
    cmd = Path(os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"))
    cl = Path(b.read(evidence[0]["path"])["program"]["path"]); link = Path(link_call["program"]["path"])
    for p in (cmd, cl, link): ad.pin(p)
    pdbs = sorted({Path(e["path"]).parent/"vc143.pdb" for e in objects.values() if (Path(e["path"]).parent/"vc143.pdb").is_file()})
    for p in pdbs: ad.pin(p)
    tag = "upl_tpi_p1_loadclock_"+configuration+"_r1"; root = T/"outputs"/tag
    intdir = Path(tempfile.gettempdir())/TAG/configuration/"int"
    b.need(not any(c.isspace() for c in str(intdir)) and not root.exists() and not intdir.exists(), "New private output/IntDir must be fresh and isolated")
    ad.finish(); root.mkdir(); (root/"out").mkdir(); intdir.mkdir(parents=True)
    return dict(tag=tag, backend=backend, configuration=configuration, count=count, exe=exe, root=root, out=root/"out", intdir=intdir,
        source_root=source, prepared=ad.pin(prep_path), base_build=ad.pin(base_path), source_files=list(files.values()),
        old_objects=objects, cl_args=recipes, link_args=link_call["arguments"], libraries=libraries, runtime_sources=runtime,
        tools=dict(cmd=b.stat(cmd), cl=b.stat(cl), link=b.stat(link)), sdk=sdk, original_recipe_evidence=evidence,
        prior_source_roots={Path(e["path"]).parent.resolve() for e in originals.values()}|set(dependencies),
        exact_CPU_tlog_source_tail_repairs=tails, authoritative_project=ad.pin(project), authoritative_solution=ad.pin(solution),
        old_compiler_pdbs=[ad.pin(p) for p in pdbs], ReleaseCPU_adopts_P1_not_prior_M0=configuration == "ReleaseCPU")


def environment(ad, ctx, calls):
    env, record = g.environment(b, ctx, calls)
    old_include, old_lib = env["INCLUDE"], env["LIB"]
    if ctx["configuration"] == "DebugCPU":
        b.need(ctx["sdk"].get("applied") is True, "Original DebugCPU SDK8.1/UCRT10240 adaptation absent")
        env["INCLUDE"] = ";".join([*ctx["sdk"]["front_include_roots"], old_include])
        env["LIB"] = ";".join([*ctx["sdk"]["front_actual_library_directories"], old_lib])
    elif ctx["configuration"] == "ReleaseCPU":
        env["LIB"] = ";".join(dict.fromkeys([*old_lib.split(";"), *[str(Path(x["entry"]["path"]).parent) for x in ctx["libraries"]]]))
    record.update(CPU_Debug_original_sdk_adaptation=ctx["sdk"], vcvars_INCLUDE_preserved=env["INCLUDE"].endswith(old_include),
                  vcvars_LIB_entries_preserved=all(x in env["LIB"].split(";") for x in old_lib.split(";")))
    search = [S/"VS"]
    for arg in ctx["link_args"]:
        if arg.lower().startswith("/libpath:"):
            p = Path(arg.split(":", 1)[1]); search.append(p if p.is_absolute() else S/"VS"/p)
    search += [Path(x) for x in env["LIB"].split(";") if x]
    bindings = []
    for x in ctx["libraries"]:
        old = x["entry"]; name = Path(old["path"]).name
        first = next((d/name for d in search if (d/name).is_file()), None)
        b.need(first is not None and g.key(first) == g.key(old["path"]), "Actual library search changed: "+name)
        bindings.append(dict(name=name, first_existing_candidate=ad.pin(first), evidence=x["evidence"], matches_inherited_binding=True,
            **{k: x[k] for k in ("stat_source_admission", "legacy_reference") if k in x}))
    return env, record, bindings


def compile_hosts(ad, ctx, env, calls):
    changed, deps = {}, []
    release = ctx["configuration"] in ("ReleaseCPU", "Release")
    for name, original in ctx["cl_args"].items():
        obj, dep = ctx["intdir"]/(Path(name).stem+".obj"), ctx["intdir"]/(name+".sourceDependencies.json")
        args, counts, skip = [], dict(source=0, fo=0, fd=0), False
        for arg in original:
            if skip: skip = False; continue
            low = arg.lower()
            if low == "/sourcedependencies": skip = True
            elif Path(arg).name.lower() == name.lower(): args.append(str(ctx["source_root"]/name)); counts["source"] += 1
            elif low.startswith("/fo"): args.append("/Fo"+str(obj)); counts["fo"] += 1
            elif low.startswith("/fd"): args.append("/Fd"+str(ctx["intdir"]/"vc143.pdb")); counts["fd"] += 1
            elif low.startswith("/i") and not low.startswith("/incremental") and (Path(arg[2:])/name).is_file(): continue
            else: args.append(arg)
        b.need(all(x == 1 for x in counts.values()) and "/fp:precise" in args and "/openmp" in args
            and ("/MT" if release else "/MTd") in args and ("/O2" if release else "/Od") in args,
            "Exact source/Fo/Fd/numerical/CRT/optimization flags differ")
        args = ["/I"+str(ctx["source_root"]), *args, "/sourceDependencies", str(dep)]
        ad.finish(); g.invoke(b, ctx["tag"]+"."+Path(name).stem, [ctx["tools"]["cl"]["path"], *args], S/"VS", env, calls)
        b.need(obj.is_file() and dep.is_file(), "Actual new object/dependency record missing")
        data = b.read(dep)["Data"]; includes = [Path(x).resolve() for x in data["Includes"]]
        b.need(g.key(data["Source"]) == g.key(ctx["source_root"]/name) and ctx["source_root"]/HEADER in includes
            and ctx["source_root"]/"JSph.h" in includes and ctx["source_root"]/"upl_tpi_m0_dt_r2.h" in includes
            and all(not p.is_relative_to((S/"source").resolve()) for p in includes)
            and not any(p.is_relative_to(q) for p in includes for q in ctx["prior_source_roots"]), "New host used live/prior headers or omitted staged clock")
        changed[obj.name.lower()] = b.stat(obj); deps.append(b.stat(dep))
    b.need(len(changed) == 2, "Only the two admitted host objects may be replaced")
    return changed, deps


def link_hosts(ad, ctx, changed, env, calls):
    targets = {"/out:": ctx["out"]/(ctx["exe"]+".exe"), "/pdb:": ctx["out"]/(ctx["exe"]+".pdb"),
        "/implib:": ctx["out"]/(ctx["exe"]+".lib"), "/ltcgout:": ctx["intdir"]/(ctx["exe"]+".iobj"),
        "/ilk:": ctx["intdir"]/(ctx["exe"]+".ilk"), "/pgd:": ctx["intdir"]/(ctx["exe"]+".pgd")}
    counts = dict.fromkeys(targets, 0); args, objects, retained = [], [], []
    for arg in ctx["link_args"]:
        low = arg.lower(); option = next((x for x in targets if low.startswith(x)), None)
        if option: args.append(arg[:len(option)]+str(targets[option])); counts[option] += 1
        elif low.endswith(".obj") and not arg.startswith("/"):
            name = Path(arg).name.lower(); entry = changed.get(name, ctx["old_objects"][name]); args.append(entry["path"]); objects.append(entry)
            if name not in changed: retained.append(entry)
        else: args.append(arg)
    b.need(all(counts[x] == 1 for x in ("/out:", "/pdb:", "/implib:", "/ltcgout:", "/ilk:"))
        and counts["/pgd:"] <= 1 and len(objects) == ctx["count"] and len(retained) == ctx["count"]-2, "Ordered closure/output redirection differs")
    ad.finish(); g.invoke(b, ctx["tag"]+".link", [ctx["tools"]["link"]["path"], *args], S/"VS", env, calls)
    b.need(targets["/out:"].is_file(), "New private linked program missing")
    return b.stat(targets["/out:"]), objects, retained


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--configuration", choices=tuple(CONFIG), required=True)
    p.add_argument("--execution-authorized", action="store_true"); p.add_argument("--admission", type=Path, required=True)
    args = p.parse_args(); b.need(args.execution_authorized, "Root build-only authorization required")
    check = L/("upl_tpi_p1_loadclock_"+args.configuration+"_r1.build.json")
    b.need(not check.exists(), "Existing build/failure receipt protected")
    ad = ctx = None; calls = []
    result = dict(stage=TAG, passed=False, configuration=args.configuration, compile_invocations=0, link_invocations=0,
        new_CUDA_compile_invocations=0, solver_invocations=0, program_help_invocations=0, native_invocations=0,
        VTK_invocations=0, Git_invocations=0, SHA_scans=0, physical_acceptance=False, following_action_launched=False,
        public_source_changed=False, canonical_programs_changed=False)
    try:
        ad = Admission(args.admission, args.configuration); ctx = context(ad, args.configuration)
        result.update(root_admission=ad.entry, backend=ctx["backend"], prepared=ctx["prepared"], source_prepare=ctx["prepared"], base_build=ctx["base_build"],
            source_files=ctx["source_files"], original_recipe_evidence=ctx["original_recipe_evidence"],
            exact_CPU_tlog_source_tail_repairs=ctx["exact_CPU_tlog_source_tail_repairs"], authoritative_project=ctx["authoritative_project"],
            authoritative_solution=ctx["authoritative_solution"], old_compiler_pdbs=ctx["old_compiler_pdbs"],
            private_no_space_IntDir=str(ctx["intdir"]), private_output_root=str(ctx["root"]),
            ReleaseCPU_adopts_P1_not_prior_M0=ctx["ReleaseCPU_adopts_P1_not_prior_M0"])
        env, result["environment"], result["actual_library_search"] = environment(ad, ctx, calls)
        changed, deps = compile_hosts(ad, ctx, env, calls); program, objects, retained = link_hosts(ad, ctx, changed, env, calls)
        runtime = []
        for e in ctx["runtime_sources"]:
            destination = ctx["out"]/Path(e["path"]).name; b.need(not destination.exists(), "Runtime destination protected")
            shutil.copy2(e["path"], destination); runtime.append(dict(source=e, destination=b.stat(destination)))
        result.update(passed=True, program=program, objects=objects, retained_objects=retained, object_count=len(objects),
            replacement_object_count=2, retained_effective_object_count=len(retained), compiler_dependencies=deps, runtime=runtime,
            new_program_identity_SHA256_count=0, new_program_identity_stat_only=True,
            class_layout_and_kernel_external_ABI_unchanged=True, adopted_CUDA_objects_unchanged=ctx["backend"] == "GPU")
    except Exception as exc: result["failure"] = str(exc); raise
    finally:
        result["calls"] = calls
        actual = [b.read(e["path"]) for e in calls]
        result["compile_invocations"] = sum(Path(c["program"]["path"]).name.lower() == "cl.exe" and isinstance(c.get("child"), dict) for c in actual)
        result["link_invocations"] = sum(Path(c["program"]["path"]).name.lower() == "link.exe" and isinstance(c.get("child"), dict) for c in actual)
        if ad is not None:
            try: result["consumed"] = ad.finish(); result["consumed_stats_unchanged"] = True
            except Exception as exc: result.update(passed=False, consumed_stats_unchanged=False, final_stat_failure=str(exc))
        if ctx is not None: result["outputs"] = [b.stat(p) for q in (ctx["root"], ctx["intdir"]) for p in q.rglob("*") if p.is_file()]
        b.write_new(check, result)


if __name__ == "__main__":
    main()
