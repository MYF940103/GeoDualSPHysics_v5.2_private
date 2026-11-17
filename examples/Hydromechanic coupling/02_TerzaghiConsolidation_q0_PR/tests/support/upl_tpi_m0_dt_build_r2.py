"""One private M0 time-policy host build; do not run the resulting program."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
import upl_tpi_cpu_build_r2 as b
import upl_tpi_gpu_build_r1 as g

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_m0_dt_build_r2"
NOTE = T / "notes" / (TAG + ".md")
HOST_HEADER = "upl_tpi_m0_dt_r2.h"
CONFIG = {
    "DebugCPU": dict(backend="CPU", count=86, names=("JSphCpu.cpp", "JSphCpuSingle.cpp"),
        base="upl_tpi_cpu_DebugCPU_r2.build.json", exe="DualSPHysics5.2CPU_win64_debug"),
    "Debug": dict(backend="GPU", count=111, names=("JSphGpu.cpp", "JSphGpuSingle.cpp"),
        base="upl_tpi_gpu_Debug_r2.build.json", exe="DualSPHysics5.2_win64_debug",
        cl=("upl_tpi_gpu_Debug_r1.JSphGpu.call.json", "upl_tpi_gpu_Debug_r1.JSphGpuSingle.call.json"),
        link="upl_tpi_gpu_Debug_r2.link.call.json"),
    "Release": dict(backend="GPU", count=111, names=("JSphGpu.cpp", "JSphGpuSingle.cpp"),
        base="upl_tpi_gpu_full2tv_Release_r1.build.json", exe="DualSPHysics5.2_GEO_win64",
        cl=("upl_tpi_gpu_Release_r3.JSphGpu.call.json", "upl_tpi_gpu_full2tv_Release_r1.JSphGpuSingle.call.json"),
        link="upl_tpi_gpu_full2tv_Release_r1.link.call.json"),
}


class Admission:
    def __init__(self, path, configuration):
        self.entry, self.data = b.stat(path), b.read(path)
        b.need(self.data.get("stage") == TAG + ".build_admission" and self.data.get("passed") is True
               and self.data.get("build_only") is True and self.data.get("configuration") == configuration,
               "One reviewed configuration/build-only root admission required")
        self.frozen = {g.key(x["path"]): x for x in self.data["inputs"]}; self.used = {}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate root input")

    def pin(self, path):
        key = g.key(path); b.need(key in self.frozen, "Unadmitted build input: " + str(path))
        self.used[key] = b.same(self.frozen[key]); return self.used[key]

    def finish(self):
        b.same(self.entry)
        for entry in self.used.values(): b.same(entry)
        return list(self.used.values())


def genuine_call(ad, path):
    ad.pin(path); call = b.read(path)
    b.need(call.get("passed") is True and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0,
           "Original owned compiler/link call did not genuinely pass")
    for key in ("program", "log"):
        if key in call: ad.pin(call[key]["path"]); b.same(call[key])
    return call


def context(ad, configuration):
    spec = CONFIG[configuration]; backend = spec["backend"]
    tag = "upl_tpi_m0_dt_" + configuration + "_r2"
    prep_path = L / ("upl_tpi_m0_dt_" + backend + "_r2.prepare.json")
    base_path = L / spec["base"]
    for p in (Path(__file__), NOTE, Path(b.__file__), Path(g.__file__), g.VCVARS, prep_path, base_path): ad.pin(p)
    prep, base = b.read(prep_path), b.read(base_path)
    b.need(prep.get("stage") == "upl_tpi_m0_dt_r2.prepare" and prep.get("backend") == backend and prep.get("passed") is True
           and prep.get("other_base_files_byte_identical") is True and prep.get("public_class_or_virtual_ABI_changed") is False
           and prep.get("CUDA_source_and_cuh_byte_identical") is True and prep.get("shared_device_structures_or_inline_tokens_changed") is False,
           "Actual passed backend-specific M0 policy preparation required")
    b.need(base.get("passed") is True and base.get("configuration") == configuration and
           base.get("consumed_stats_unchanged", base.get("canonical_programs_stats_unchanged")) is True,
           "Actual passed same-configuration baseline build required")
    source = Path(prep["source_root"]).resolve()
    b.need(source == (T / "outputs" / ("upl_tpi_m0_dt_" + backend + "_r2_source")).resolve(), "Unexpected prepared root")
    expected_count = 267 if backend == "CPU" else 270
    files = {Path(e["path"]).name: e for e in prep["files"]}
    b.need(len(files) == len(prep["files"]) == expected_count and HOST_HEADER in files and
           {Path(e["path"]).name for e in prep["recompile_sources"]} == set(spec["names"]),
           "Exact prepared source closure/two-host rebuild boundary differs")
    for e in prep["files"]: ad.pin(e["path"]); b.same(e)
    for key in ("base_prepare", "base_build", "source_diff"):
        ad.pin(prep[key]["path"]); b.same(prep[key])
    originals = {}
    for e in prep["base_source_entries"]:
        old, new = e["original"], e["pinned_snapshot"]
        for x in (old, new): ad.pin(x["path"]); b.same(x)
        b.need(g.key(new["path"]) == g.key(source / Path(old["path"]).name), "Prepared snapshot/member association differs")
        originals[Path(old["path"]).name] = old
    b.need(set(originals) == set(files) - {HOST_HEADER}, "Complete prepared parent closure differs")
    b.need({Path(e["path"]).name for e in prep["changed_sources"]} == set(spec["names"]) and
           {Path(e["path"]).name for e in prep["changed_headers"]} == ({HOST_HEADER, "upl_tpi_gpu_r1.h"} if backend == "GPU" else {HOST_HEADER}),
           "Private host-only patch inventory differs")
    for name in ("JSph.h", "JSphCpu.h", "JSphGpu.h", "JSphHourglassGpu.h", "JSphGpu_ker.h"):
        if name in originals:
            b.need((source / name).read_bytes() == Path(originals[name]["path"]).read_bytes(), "Retained class/kernel ABI header changed: " + name)
    if backend == "GPU":
        for name in ("upl_tpi_gpu_r1.cuh", "JSphGpu_ker.cu", "JSphHourglassGpu.cpp"):
            b.need((source / name).read_bytes() == Path(originals[name]["path"]).read_bytes(), "Retained CUDA/HG body changed: " + name)
        marker = b"#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION"
        new_h, old_h = (source / "upl_tpi_gpu_r1.h").read_bytes(), Path(originals["upl_tpi_gpu_r1.h"]["path"]).read_bytes()
        b.need(new_h.count(marker) == old_h.count(marker) == 1 and new_h.split(marker)[0] == old_h.split(marker)[0],
               "GPU device-visible TPI declarations changed; two-host reuse is invalid")
    ad.pin(base["program"]["path"]); b.same(base["program"])
    objects = {Path(e["path"]).name.lower(): e for e in base["objects"]}
    b.need(len(objects) == len(base["objects"]) == spec["count"], "Actual baseline object closure differs")
    for e in objects.values(): ad.pin(e["path"]); b.same(e)
    pdbs = {Path(e["path"]).parent / "vc143.pdb" for e in objects.values()}
    pdbs = [p for p in sorted(pdbs) if p.is_file()]
    for p in pdbs: ad.pin(p)
    cl_args, original_calls, sdk_roots, sdk_headers = {}, [], [], []
    if backend == "CPU":
        project, solution = b.PROJECT, b.SOLUTION
        tlogs = base["compiler_linker_command_tlogs"]
        cllog = next(e for e in tlogs if Path(e["path"]).name.lower().startswith("cl."))
        linklog = next(e for e in tlogs if Path(e["path"]).name.lower().startswith("link."))
        for e in (*tlogs, *base["compiler_read_tlogs"], *base["linker_read_tlogs"]): ad.pin(e["path"]); b.same(e)
        for name in spec["names"]: cl_args[name] = g.cl_recipe(b, g.tlog_text(cllog["path"]), name)
        # This authoritative CPU project targeted Windows8.1/UCRT10240, whereas
        # the GPU recipe used SDK22000. Reproduce the actual CPU read closure.
        active = False; roots = set()
        for line in g.tlog_text(base["compiler_read_tlogs"][0]["path"]).splitlines():
            if line.startswith("^"): active = Path(line[1:]).name.lower() in {x.lower() for x in spec["names"]}
            elif active:
                match = re.match(r"(?i)(.*windows kits\\(?:8\.1\\include\\(?:um|shared)|10\\include\\10\.0\.10240\.0\\ucrt))(?:\\|$)", line)
                if match: roots.add(Path(match.group(1)).resolve()); sdk_headers.append(ad.pin(line))
        b.need(len(roots) == 3 and {p.name.lower() for p in roots} == {"um", "shared", "ucrt"},
               "Actual two-host CPU SDK include closure differs")
        sdk_roots = sorted(roots, key=lambda p: {"ucrt": 0, "shared": 1, "um": 2}[p.name.lower()])
        text = g.tlog_text(linklog["path"]).splitlines()
        b.need(text and text[0].startswith("^"), "Actual CPU linker tlog header absent")
        link_args = b.windows_argv(" ".join(text[1:]))
        libraries = base["actual_Debug_link_library_stats"]
        for e in base["calls"]: ad.pin(e["path"]); b.same(e)
        msbuild = next(b.read(e["path"]) for e in base["calls"] if e["path"].endswith(".msbuild.call.json"))
        b.need(msbuild.get("passed") is True and msbuild.get("actual_Popen_wait_exit") == msbuild.get("actual_Win32_exit") == 0,
               "Original actual authoritative CPU Debug MSBuild did not pass")
        original_calls = list(base["calls"])
        cl_tool, link_tool = g.TOOLS / "cl.exe", g.TOOLS / "link.exe"
    else:
        project, solution = g.PROJECT, g.SOLUTION
        for name, filename in zip(spec["names"], spec["cl"]):
            path = L / filename; call = genuine_call(ad, path); cl_args[name] = call["arguments"]; original_calls.append(ad.pin(path))
        path = L / spec["link"]; call = genuine_call(ad, path); link_args = call["arguments"]; original_calls.append(ad.pin(path))
        libraries = [e["first_existing_candidate"] for e in base["actual_library_search"]]
        cl_tool, link_tool = Path(genuine_call(ad, L / spec["cl"][0])["program"]["path"]), Path(call["program"]["path"])
    ad.pin(project); ad.pin(solution)
    linked = [x for x in link_args if x.lower().endswith(".obj") and not x.startswith("/")]
    b.need(len(linked) == len(set(map(g.key, linked))) == spec["count"] and
           {g.key(x) for x in linked} == {g.key(e["path"]) for e in objects.values()}, "Actual ordered linker objects differ from the adopted closure")
    for e in libraries: ad.pin(e["path"]); b.same(e)
    runtime = [e["destination"] for e in base["runtime"]]
    for e in runtime: ad.pin(e["path"]); b.same(e)
    cmd = Path(os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"))
    for p in (cmd, cl_tool, link_tool): ad.pin(p)
    root = T / "outputs" / tag; intdir = Path(tempfile.gettempdir()) / TAG / configuration / "int"
    b.need(not root.exists() and not intdir.exists(), "Existing or partial private build is protected")
    ad.finish(); root.mkdir(); (root / "out").mkdir(); intdir.mkdir(parents=True)
    return dict(tag=tag, backend=backend, configuration=configuration, root=root, out=root / "out", intdir=intdir,
        source_root=source, prepared=ad.pin(prep_path), base_build=ad.pin(base_path), source_files=list(files.values()),
        old_objects=objects, cl_args=cl_args, link_args=link_args, libraries=libraries, runtime_sources=runtime,
        tools={"cmd": b.stat(cmd), "cl": b.stat(cl_tool), "link": b.stat(link_tool)}, old_compiler_pdbs=[ad.pin(p) for p in pdbs],
        original_recipe_evidence=original_calls, authoritative_project=ad.pin(project), authoritative_solution=ad.pin(solution),
        prior_source_roots={Path(e["path"]).parent.resolve() for e in originals.values()},
        actual_CPU_sdk_include_roots=sdk_roots, actual_CPU_sdk_header_inputs=sdk_headers)


def cpu_debug_environment(ctx, env):
    if ctx["backend"] != "CPU": return dict(applied=False)
    old_include, old_lib = env["INCLUDE"], env["LIB"]
    includes = [str(p) for p in ctx["actual_CPU_sdk_include_roots"]]
    libraries = list(dict.fromkeys(str(Path(e["path"]).parent) for e in ctx["libraries"]))
    # Preserve every actual vcvars path, including implicit CRT directories.
    env["INCLUDE"] = ";".join([*includes, old_include])
    env["LIB"] = ";".join([*libraries, old_lib])
    return dict(applied=True, source="Actual passed CPU Debug CL.read/link.read, not GPU SDK assumptions",
        front_include_roots=includes, old_actual_sdk_header_inputs=ctx["actual_CPU_sdk_header_inputs"],
        front_actual_library_directories=libraries, vcvars_INCLUDE_preserved=True, vcvars_LIB_preserved=True,
        whole_vcvars_INCLUDE_suffix_unchanged=env["INCLUDE"].endswith(old_include),
        whole_vcvars_LIB_suffix_unchanged=env["LIB"].endswith(old_lib))


def compile_hosts(ad, ctx, env, calls):
    changed, dependencies = {}, []
    for name, original in ctx["cl_args"].items():
        obj, dep = ctx["intdir"] / (Path(name).stem + ".obj"), ctx["intdir"] / (name + ".sourceDependencies.json")
        args, counts, skip = [], dict(source=0, fo=0, fd=0), False
        for arg in original:
            if skip: skip = False; continue
            low = arg.lower()
            if low == "/sourcedependencies": skip = True
            elif Path(arg).name.lower() == name.lower(): args.append(str(ctx["source_root"] / name)); counts["source"] += 1
            elif low.startswith("/fo"): args.append("/Fo" + str(obj)); counts["fo"] += 1
            elif low.startswith("/fd"): args.append("/Fd" + str(ctx["intdir"] / "vc143.pdb")); counts["fd"] += 1
            elif low.startswith("/i") and not low.startswith("/incremental"):
                # Drop only the old private flat source include, preserving CUDA/toolchain includes.
                old_dir = Path(arg[2:])
                if old_dir.is_dir() and (old_dir / name).is_file(): continue
                args.append(arg)
            else: args.append(arg)
        b.need(all(x == 1 for x in counts.values()) and "/fp:precise" in args and "/openmp" in args,
               "Original exact host source/Fo/Fd/precise flags differ")
        expected_crt = "/MT" if ctx["configuration"] == "Release" else "/MTd"
        b.need(expected_crt in args and (("/O2" in args) if ctx["configuration"] == "Release" else ("/Od" in args)),
               "Actual configuration optimization/CRT flags differ")
        args = ["/I" + str(ctx["source_root"]), *args, "/sourceDependencies", str(dep)]
        ad.finish(); g.invoke(b, ctx["tag"] + "." + Path(name).stem,
            [ctx["tools"]["cl"]["path"], *args], S / "VS", env, calls)
        b.need(obj.is_file() and dep.is_file(), "New private host object/dependency record missing")
        data = b.read(dep)["Data"]; includes = [Path(x).resolve() for x in data["Includes"]]
        b.need(g.key(data["Source"]) == g.key(ctx["source_root"] / name) and ctx["source_root"] / HOST_HEADER in includes
               and ctx["source_root"] / "JSph.h" in includes and all(not p.is_relative_to((S / "source").resolve()) for p in includes),
               "Host compile did not use the new policy and frozen class source closure")
        b.need(not any(p.is_relative_to(root) for p in includes for root in ctx["prior_source_roots"]),
               "Host compile used the prior private source directory")
        changed[obj.name.lower()] = b.stat(obj); dependencies.append(b.stat(dep))
    b.need(len(changed) == 2, "Exactly two host translation units must be replaced")
    return changed, dependencies


def link_hosts(ad, ctx, changed, env, calls):
    name = CONFIG[ctx["configuration"]]["exe"]
    targets = {"/out:": ctx["out"] / (name + ".exe"), "/pdb:": ctx["out"] / (name + ".pdb"),
        "/implib:": ctx["out"] / (name + ".lib"), "/ltcgout:": ctx["intdir"] / (name + ".iobj"),
        "/ilk:": ctx["intdir"] / (name + ".ilk"), "/pgd:": ctx["intdir"] / (name + ".pgd")}
    counts = {x: 0 for x in targets}; args, objects, retained = [], [], []
    for arg in ctx["link_args"]:
        low = arg.lower(); option = next((x for x in targets if low.startswith(x)), None)
        if option: args.append(arg[:len(option)] + str(targets[option])); counts[option] += 1
        elif low.endswith(".obj") and not arg.startswith("/"):
            key = Path(arg).name.lower(); entry = changed.get(key, ctx["old_objects"][key]); args.append(entry["path"]); objects.append(entry)
            if key not in changed: retained.append(entry)
        else: args.append(arg)
    required = ("/out:", "/pdb:", "/implib:", "/ltcgout:", "/ilk:")
    b.need(all(counts[x] == 1 for x in required) and counts["/pgd:"] <= 1 and
           len(objects) == CONFIG[ctx["configuration"]]["count"] and len(retained) == len(objects)-2,
           "Exact ordered link closure/output redirects differ")
    ad.finish(); g.invoke(b, ctx["tag"] + ".link", [ctx["tools"]["link"]["path"], *args], S / "VS", env, calls)
    program = targets["/out:"]; b.need(program.is_file(), "New private program missing")
    identity = b.stat(program)
    with program.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024*1024), b""): digest.update(chunk)
    identity["sha256"] = digest.hexdigest()
    return identity, objects, retained


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", choices=tuple(CONFIG), required=True)
    parser.add_argument("--execution-authorized", action="store_true"); parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args(); b.need(args.execution_authorized, "Independent root build-only admission required")
    check = L / ("upl_tpi_m0_dt_" + args.configuration + "_r2.build.json")
    b.need(not check.exists(), "Existing build receipt/failure is protected")
    ad = ctx = None; calls = []
    result = dict(stage=TAG, passed=False, configuration=args.configuration, compile_invocations=0, link_invocations=0,
        new_CUDA_compile_invocations=0, solver_invocations=0, program_help_invocations=0, native_invocations=0, VTK_invocations=0,
        physical_acceptance=False, public_source_changed=False, canonical_programs_changed=False, following_action_launched=False,
        old_source_object_or_BI4_SHA_scans=0)
    try:
        ad = Admission(args.admission, args.configuration); ctx = context(ad, args.configuration)
        result.update(root_admission=ad.entry, backend=ctx["backend"], prepared=ctx["prepared"], source_prepare=ctx["prepared"], base_build=ctx["base_build"],
            source_files=ctx["source_files"], original_recipe_evidence=ctx["original_recipe_evidence"],
            authoritative_project=ctx["authoritative_project"], authoritative_solution=ctx["authoritative_solution"],
            old_compiler_pdbs=ctx["old_compiler_pdbs"], private_no_space_IntDir=str(ctx["intdir"]), private_output_root=str(ctx["root"]))
        env, result["environment"] = g.environment(b, ctx, calls)
        result["CPU_Debug_actual_SDK_adaptation"] = cpu_debug_environment(ctx, env)
        result["actual_library_search"] = g.validate_library_search(b, ctx, env)
        changed, deps = compile_hosts(ad, ctx, env, calls); program, objects, retained = link_hosts(ad, ctx, changed, env, calls)
        runtime = []
        for e in ctx["runtime_sources"]:
            destination = ctx["out"] / Path(e["path"]).name; b.need(not destination.exists(), "Runtime output exists")
            shutil.copy2(e["path"], destination); runtime.append(dict(source=e, destination=b.stat(destination)))
        result.update(passed=True, program=program, objects=objects, retained_objects=retained, object_count=len(objects),
            replacement_object_count=2, retained_effective_object_count=len(retained), compiler_dependencies=deps, runtime=runtime,
            new_program_identity_SHA256_count=1, class_layout_and_kernel_external_ABI_unchanged=True,
            adopted_CUDA_objects_unchanged=ctx["backend"] == "GPU")
    except Exception as exc: result["failure"] = str(exc); raise
    finally:
        result["calls"] = calls
        actual = [b.read(e["path"]) for e in calls]
        result["compile_invocations"] = sum(Path(c["program"]["path"]).name.lower() == "cl.exe" and isinstance(c.get("child"), dict) for c in actual)
        result["link_invocations"] = sum(Path(c["program"]["path"]).name.lower() == "link.exe" and isinstance(c.get("child"), dict) for c in actual)
        if ad is not None:
            try: result["consumed"] = ad.finish(); result["consumed_stats_unchanged"] = True
            except Exception as exc: result.update(passed=False, consumed_stats_unchanged=False, final_stat_failure=str(exc))
        if ctx is not None: result["outputs"] = [b.stat(p) for root in (ctx["root"], ctx["intdir"]) for p in root.rglob("*") if p.is_file()]
        b.write_new(check, result)


if __name__ == "__main__":
    main()
