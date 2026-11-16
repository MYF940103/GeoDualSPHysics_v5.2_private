"""Author-only isolated P1 GPU build: four TUs + 107 frozen objects, no program run."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
S = R / "src"
L = T / "logs"
PREP = L / "upl_tpi_gpu_r1.prepare.json"
NOTE = T / "notes/upl_tpi_gpu_build_r1.md"
COMMON = T / "support/upl_tpi_cpu_build_r2.py"
PROJECT = S / "VS/DualSPHysics5Re.vcxproj"
SOLUTION = S / "VS/DualSPHysics5Re.sln"
VCVARS = Path("D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat")
TOOLS = Path("D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/HostX64/x64")
NS = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
RECOMPILE = {"JSphGpu.cpp", "JSphGpuSingle.cpp", "JSphGpu_ker.cu", "JSphHourglassGpu.cpp"}
NUMERICAL_PATCHES = {"JSphGpu.cpp", "JSphGpuSingle.cpp", "JSphGpu_ker.cu"}


def common_module():
    spec = importlib.util.spec_from_file_location("upl_tpi_gpu_build_common_r2", COMMON)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Definitions only, never CPU main/build.
    return module


def invoke(b, tag, argv, cwd, env, calls, environment_output=False):
    """Retain even the already-sealed failed actual tool call; never retry it."""
    try:
        entry, raw = b.invoke(tag, argv, cwd, env, environment_output)
    except Exception:
        path = L / (tag + ".call.json")
        if path.is_file():
            calls.append(b.stat(path))
        raise
    calls.append(entry)
    return raw


def key(path):
    return os.path.normcase(str(Path(path).resolve()))


class Admission:
    def __init__(self, b, configuration, path):
        self.b = b
        self.entry = b.stat(path)
        self.data = b.read(path)
        b.need(self.data.get("stage") == "upl_tpi_gpu_build_r1.build_admission"
               and self.data.get("configuration") == configuration
               and self.data.get("passed") is True and self.data.get("build_only") is True,
               "Independent one-configuration root GPU build-only admission required")
        self.frozen = {key(e["path"]): e for e in self.data["inputs"]}
        self.consumed = {}

    def pin(self, path):
        k = key(path)
        self.b.need(k in self.frozen, "Build input absent from root admission: " + str(path))
        self.consumed[k] = self.b.same(self.frozen[k])
        return self.consumed[k]

    def finish(self):
        self.b.same(self.entry)
        for entry in self.consumed.values():
            self.b.same(entry)
        return list(self.consumed.values())


def tlog_text(path):
    payload = Path(path).read_bytes()
    return payload.decode("utf-16") if payload.startswith(b"\xff\xfe") else payload.decode("utf-8-sig")


def object_name(source):
    name = Path(source.replace("\\", "/")).name
    if name.lower().endswith(".cpp"):
        return name[:-4] + ".obj"
    if name.lower().endswith((".cu", ".h")):
        return name + ".obj"  # Preserve both original *.h.obj compile items.
    raise RuntimeError("Unreviewed GPU compile item extension: " + name)


def project_closure(b, expected):
    root = ET.parse(PROJECT).getroot()
    result = {}
    for configuration in ("Debug", "Release"):
        active = []
        for kind in ("ClCompile", "CudaCompile"):
            for item in root.findall(".//m:ItemGroup/m:" + kind, NS):
                exclusions = [x for x in item.findall("m:ExcludedFromBuild", NS)
                              if configuration + "|x64" in x.get("Condition", "") and x.text == "true"]
                if not exclusions:
                    active.append(item.attrib["Include"])
        names = {object_name(x).lower() for x in active}
        b.need(len(active) == len(names) == 113 and names - expected == {"jsphcpu_mdbc.obj", "jsphgpu_mdbc.obj"}
               and not expected - names, "Current authoritative GPU project no longer has the reviewed 113-to-111 closure")
        result[configuration] = dict(current_active_items=113, frozen_items=111,
            excluded_only_from_private_recipe=["JSphCpu_mdbc.cpp", "JSphGpu_mdbc.cpp"], public_project_changed=False)
    return result


def cl_recipe(b, text, name):
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines)
            if line.startswith("^") and Path(line[1:]).name.lower() == name.lower()]
    b.need(len(hits) == 1 and hits[0] + 1 < len(lines), "Unique original CL recipe absent: " + name)
    args = b.windows_argv(lines[hits[0] + 1])
    b.need(sum(Path(x).name.lower() == name.lower() for x in args) == 1,
           "Original CL source argument closure differs")
    return args


def nvcc_recipe(b, log):
    lines = [x for x in Path(log).read_text(encoding="utf-8-sig", errors="strict").splitlines()
             if "nvcc.exe" in x.lower() and '"' in x and "JSphGpu_ker.cu" in x]
    b.need(len(lines) == 1 and ">" in lines[0], "One genuine original JSphGpu_ker NVCC command required")
    args = b.windows_argv(lines[0].split(">", 1)[1].strip())
    b.need(Path(args[0]).name.lower() == "nvcc.exe" and Path(args[-1]).name == "JSphGpu_ker.cu"
           and "--compile" in args and "-use_fast_math" in args and "-cudart" in args,
           "Original CUDA command identity/options differ")
    return args


def library_paths(b, text):
    entries = [Path(x) for x in text.splitlines() if x.lower().endswith(".lib")]
    b.need(len(entries) == len({key(x) for x in entries}) and len(entries) in (26, 27),
           "Original GPU linker-read library closure differs")
    return entries


def context(b, ad, configuration):
    tag = "upl_tpi_gpu_" + configuration + "_r1"
    destination = T / "outputs" / tag
    intdir = Path(tempfile.gettempdir()) / "upl_tpi_gpu_build_r1" / configuration / "int"
    b.need(not re.search(r"\s", str(intdir)), "CUDA IntDir must have no whitespace")
    record = L / (tag + ".build.json")
    b.need(not destination.exists() and not intdir.exists() and not record.exists(),
           "New private GPU build/partial is protected; never overwrite or retry")
    ad.pin(__file__)
    ad.pin(NOTE)
    ad.pin(COMMON)
    ad.pin(PROJECT)
    ad.pin(SOLUTION)
    ad.pin(VCVARS)
    prepared_entry = ad.pin(PREP)
    prepared = b.read(PREP)
    b.need(prepared.get("passed") is True and prepared.get("class_layout_or_virtual_ABI_changed") is False
           and prepared.get("old_kernel_external_signatures_changed") is False,
           "Reviewed private GPU preparation with unchanged class layout/kernel external signatures required")
    source_manifest = ad.pin(prepared["base_source_manifest"]["path"])
    manifest = b.read(source_manifest["path"])
    b.need(manifest.get("source_count") == 265 and len(manifest.get("files", [])) == 267,
           "Original GPU manifest must contain 265 code/header files plus two document archives")
    source = Path(prepared["source_root"]).resolve()
    b.need(source == (T / "outputs/upl_tpi_gpu_r1_source").resolve()
           and len(prepared["files"]) == 269 and len(prepared["base_source_entries"]) == 267,
           "Private 267-source plus two-helper closure differs")
    files = [ad.pin(e["path"]) for e in prepared["files"]]
    b.need(len({Path(x["path"]).name for x in files}) == 269
           and all(Path(x["path"]).parent == source for x in files), "Private GPU source tree is not flat and exact")
    b.need({Path(x["path"]).name for x in prepared["changed_sources"]} == NUMERICAL_PATCHES
           and {Path(x["path"]).name for x in prepared["changed_headers"]} == {"JSphHourglassGpu.h"}
           and {Path(x["path"]).name for x in prepared["recompile_sources"]} == RECOMPILE,
           "Four-TU same-header ODR closure differs")
    old_hg_entries = [x["pinned_snapshot"] for x in prepared["base_source_entries"]
                      if Path(x["pinned_snapshot"]["path"]).name == "JSphHourglassGpu.cpp"]
    b.need(len(old_hg_entries) == 1, "Original unchanged HG host body identity absent")
    old_hg = ad.pin(old_hg_entries[0]["path"])
    b.need((source / "JSphHourglassGpu.cpp").read_bytes() == Path(old_hg["path"]).read_bytes(),
           "Fourth same-header TU must retain the original HG method bodies bytewise")
    ad.pin(prepared["source_diff"]["path"])
    base_entry = ad.pin(prepared["base_build_debug" if configuration == "Debug" else "base_build_release"]["path"])
    base = b.read(base_entry["path"])
    b.need(base.get("passed") is True and base.get("configuration") == configuration and base.get("object_count") == 111,
           "Actual matching frozen GPU build required")
    old_program = ad.pin(base["program"]["path"])
    old_int = Path("C:/Users/syosh/AppData/Local/Temp/upl_gpu_stabilizers_r1") / configuration / "int"
    old_objects = sorted(old_int.glob("*.obj"))
    b.need(len(old_objects) == 111 and len({p.name.lower() for p in old_objects}) == 111,
           "Matching old GPU 111 objects missing or duplicated")
    objects = {p.name.lower(): ad.pin(p) for p in old_objects}
    if configuration == "Debug":
        b.need({Path(e["path"]).name.lower() for e in base["objects"]} == set(objects)
               and all(objects[Path(e["path"]).name.lower()]["bytes"] == e["bytes"] for e in base["objects"]),
               "Debug original per-object recorded size/name closure differs")
    else:
        b.need({x.lower() for x in base["object_names"]} == set(objects), "Release original recorded object-name closure differs")
    old_pdb = ad.pin(old_int / "vc143.pdb")
    logs = old_int / "DualSPHysics.tlog"
    cllog, linklog, readlog = [ad.pin(logs / n) for n in ("CL.command.1.tlog", "link.command.1.tlog", "link.read.1.tlog")]
    original_call = ad.pin(L / ("upl_gpu_stabilizers_" + configuration + "_r1.call.json"))
    call = b.read(original_call["path"])
    b.need(call.get("exit_code") == 0, "Actual original GPU MSBuild call did not pass")
    original_log = ad.pin(call["log"]["path"])
    text = tlog_text(linklog["path"])
    link_args = b.windows_argv(" ".join(x for x in text.splitlines() if x and not x.startswith("^")))
    linked_objects = [Path(x) for x in link_args if x.lower().endswith(".obj")]
    b.need(len(linked_objects) == 111 and {p.name.lower() for p in linked_objects} == set(objects),
           "Original linker object recipe differs from matching object directory")
    libs = library_paths(b, tlog_text(readlog["path"]))
    libraries = [ad.pin(p) for p in libs]
    cl_text = tlog_text(cllog["path"])
    cl = {name: cl_recipe(b, cl_text, name) for name in sorted(RECOMPILE) if name.endswith(".cpp")}
    nvcc = nvcc_recipe(b, original_log["path"])
    tools = dict(cl=ad.pin(TOOLS / "cl.exe"), link=ad.pin(TOOLS / "link.exe"), nvcc=ad.pin(nvcc[0]),
                 cmd=ad.pin(os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe")))
    runtime_sources = [ad.pin(x["path"]) for x in base["runtime"]]
    if configuration == "Debug":
        omp = Path("D:/Program Files/VS2022/VC/Redist/MSVC/14.36.32532/debug_nonredist/x64/Microsoft.VC143.DebugOpenMP/vcomp140d.dll")
        if not any(Path(x["path"]).name.lower() == "vcomp140d.dll" for x in runtime_sources):
            runtime_sources.append(ad.pin(omp))
    current_closure = project_closure(b, set(objects))
    destination.mkdir()
    intdir.mkdir(parents=True)
    out = destination / "out"
    out.mkdir()
    return dict(tag=tag, root=destination, intdir=intdir, out=out, record=record,
        configuration=configuration, source_root=source, prepared=prepared_entry, source_files=files,
        base_source_manifest=source_manifest,
        base_build=base_entry, old_program=old_program, old_objects=objects, old_compiler_pdb=old_pdb,
        original_CL_tlog=cllog, original_link_tlog=linklog, original_link_read_tlog=readlog,
        original_MSBuild_call=original_call, original_MSBuild_log=original_log,
        cl_args=cl, nvcc_args=nvcc, link_args=link_args, libraries=libraries,
        runtime_sources=runtime_sources, tools=tools, current_project_closure=current_closure)


def environment(b, ctx, calls):
    batch = ctx["root"] / "environment.cmd"
    # Literal CRLF batch + simple relative filename/cwd avoids nested-call quote
    # expansion. vcvars LIB is preserved; never replace it with an older receipt.
    text = ('@echo off\r\ncall "' + str(VCVARS)
            + '" x64 10.0.22000.0 -vcvars_ver=14.36 >nul\r\n'
              'if errorlevel 1 exit /b %errorlevel%\r\nset\r\n')
    with batch.open("x", encoding="mbcs", newline="") as f:
        f.write(text)
    raw = invoke(b, ctx["tag"] + ".environment", [ctx["tools"]["cmd"]["path"],
        "/d", "/s", "/c", batch.name], ctx["root"], os.environ.copy(), calls, environment_output=True)
    env = {k.upper(): v for k, v in os.environ.items()}
    for line in raw.decode("mbcs", errors="strict").splitlines():
        if "=" in line and not line.startswith("="):
            name, value = line.split("=", 1)
            env[name.upper()] = value
    get = lambda name: env.get(name.upper())
    b.need(get("VCToolsVersion") == "14.36.32532" and (get("WindowsSDKVersion") or "").rstrip("/\\") == "10.0.22000.0"
           and get("LIB") and get("PATH"), "Original MSVC14.36/SDK10.0.22000 environment required")
    preserved_lib = get("LIB")
    removed = []
    for name in ("CL", "_CL_", "LINK", "_LINK_", "NVCC_PREPEND_FLAGS", "NVCC_APPEND_FLAGS"):
        if name in env:
            env.pop(name);removed.append(name)
    # Only own transient compiler files use the new no-space directory.
    env["TEMP"] = env["TMP"] = str(ctx["intdir"])
    return env, dict(batch=b.stat(batch), VCToolsVersion=get("VCToolsVersion"),
        WindowsSDKVersion=get("WindowsSDKVersion"), vcvars_LIB_dirs=preserved_lib.split(";"),
        vcvars_LIB_preserved=True, removed_compiler_override_variable_names=removed, raw_environment_saved=False)


def validate_library_search(b, ctx, env):
    explicit = []
    for arg in ctx["link_args"]:
        if arg.lower().startswith("/libpath:"):
            p = Path(arg.split(":", 1)[1])
            explicit.append(p if p.is_absolute() else S / "VS" / p)
    library_env = next(v for k, v in env.items() if k.lower() == "lib")
    search = [S / "VS", *explicit, *[Path(x) for x in library_env.split(";") if x]]
    evidence = []
    for old in ctx["libraries"]:
        name = Path(old["path"]).name
        candidate = next((d / name for d in search if (d / name).is_file()), None)
        b.need(candidate is not None and key(candidate) == key(old["path"]),
               "Actual library search no longer resolves to the original linker-read input: " + name)
        evidence.append(dict(name=name, first_existing_candidate=b.stat(candidate), matches_original_linker_read=True))
    return evidence


def compile_sources(b, ad, ctx, env, calls):
    new_objects = {}
    for name, original in ctx["cl_args"].items():
        obj = ctx["intdir"] / object_name(name)
        args, source_count, fo_count, fd_count = [], 0, 0, 0
        for arg in original:
            lower = arg.lower()
            if Path(arg).name.lower() == name.lower():
                args.append(str(ctx["source_root"] / name));source_count += 1
            elif lower.startswith("/fo"):
                args.append("/Fo" + str(obj));fo_count += 1
            elif lower.startswith("/fd"):
                args.append("/Fd" + str(ctx["intdir"] / "vc143.pdb"));fd_count += 1
            else:
                args.append(arg)
        b.need(source_count == fo_count == fd_count == 1, "Original CL source/output-PDB rewrite closure differs")
        deps = ctx["intdir"] / (name + ".sourceDependencies.json")
        args.extend(["/sourceDependencies", str(deps)])
        ad.finish()
        invoke(b, ctx["tag"] + "." + name[:-4], [ctx["tools"]["cl"]["path"], *args], S / "VS", env, calls)
        b.need(obj.is_file() and deps.is_file(), "New private CL object/dependency evidence missing")
        data = b.read(deps)
        includes = [Path(x) for x in data["Data"]["Includes"]]
        b.need(all(not key(p).startswith(key(S / "source") + os.sep) for p in includes),
               "Private host source read a live public source header")
        new_objects[obj.name.lower()] = b.stat(obj)
    args = list(ctx["nvcc_args"])
    program, args = args[0], args[1:]
    b.need(key(program) == key(ctx["tools"]["nvcc"]["path"]), "Original CUDA tool changed")
    source_count = sum(Path(arg).name == "JSphGpu_ker.cu" for arg in args)
    b.need(source_count == 1 and args.count("-o") == args.count("--keep-dir") == 1, "Original CUDA source/output options differ")
    obj = ctx["intdir"] / "JSphGpu_ker.cu.obj"
    args[args.index("-o") + 1] = str(obj)
    args[args.index("--keep-dir") + 1] = ctx["intdir"].as_posix() + "/"
    args = [str(ctx["source_root"] / "JSphGpu_ker.cu") if Path(x).name == "JSphGpu_ker.cu" else x for x in args]
    fd_replacements = 0
    for i, arg in enumerate(args):
        changed, count = re.subn(r"(?i)/Fd[^ ]+", "/Fd" + (ctx["intdir"] / "vc143.pdb").as_posix(), arg)
        args[i] = changed;fd_replacements += count
    b.need(fd_replacements == 1, "Original CUDA host PDB rewrite must occur exactly once")
    ad.finish()
    invoke(b, ctx["tag"] + ".JSphGpu_ker", [program, *args], S / "VS", env, calls)
    b.need(obj.is_file(), "New private CUDA object missing")
    new_objects[obj.name.lower()] = b.stat(obj)
    b.need(set(new_objects) == {object_name(x).lower() for x in RECOMPILE}, "Exactly four new objects required")
    return new_objects


def link(b, ad, ctx, env, objects, calls):
    name = "DualSPHysics5.2_win64_debug" if ctx["configuration"] == "Debug" else "DualSPHysics5.2_GEO_win64"
    program = ctx["out"] / (name + ".exe")
    replacements = {"/out:": program, "/pdb:": ctx["out"] / (name + ".pdb"),
                    "/implib:": ctx["out"] / (name + ".lib"), "/ltcgout:": ctx["intdir"] / (name + ".iobj")}
    counts = {x: 0 for x in replacements}
    args, all_objects, retained = [], [], []
    for arg in ctx["link_args"]:
        lower = arg.lower()
        option = next((x for x in replacements if lower.startswith(x)), None)
        if option:
            args.append(arg[:len(option)] + str(replacements[option]));counts[option] += 1
        elif lower.endswith(".obj"):
            old = ctx["old_objects"][Path(arg).name.lower()]
            entry = objects.get(Path(arg).name.lower(), old)
            args.append(entry["path"]);all_objects.append(entry)
            if Path(arg).name.lower() not in objects:
                retained.append(old)
        else:
            args.append(arg)
    b.need(all(x == 1 for x in counts.values()) and len(all_objects) == 111 and len(retained) == 107,
           "Exact 111-object linker closure/new-output rewrites differ")
    b.need(not any(x.lower().startswith("/ilk:") for x in args), "Unexpected old explicit ILK requires review")
    args.append("/ILK:" + str(ctx["intdir"] / (name + ".ilk")))
    ad.finish()
    invoke(b, ctx["tag"] + ".link", [ctx["tools"]["link"]["path"], *args], S / "VS", env, calls)
    b.need(program.is_file(), "Actual private linked GPU program missing")
    # One new sealed-program identity only; no old-source/object/BI4 hash sweep.
    identity = b.stat(program)
    with program.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    identity["sha256"] = digest.hexdigest()
    return identity, all_objects, retained


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", choices=("Debug", "Release"), required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("One independently reviewed root build invocation required")
    b = common_module()
    ad, ctx, calls = None, None, []
    result = dict(stage="upl_tpi_gpu_build_r1", passed=False, configuration=args.configuration,
        compile_invocations=0, link_invocations=0, program_help_invocations=0, solver_invocations=0,
        native_invocations=0, VTK_invocations=0, physical_acceptance=False, following_action_launched=False,
        old_source_object_or_BI4_SHA_scans=0, public_source_changed=False, canonical_programs_changed=False)
    try:
        ad = Admission(b, args.configuration, args.admission)
        ctx = context(b, ad, args.configuration)
        result.update(root_admission=ad.entry, prepared=ctx["prepared"], base_build=ctx["base_build"],
            authoritative_solution=ad.pin(SOLUTION), authoritative_project=ad.pin(PROJECT),
            current_project_closure=ctx["current_project_closure"], source_files=ctx["source_files"],
            base_source_manifest=ctx["base_source_manifest"],
            original_MSBuild_call=ctx["original_MSBuild_call"], original_MSBuild_log=ctx["original_MSBuild_log"],
            original_CL_tlog=ctx["original_CL_tlog"], original_link_tlog=ctx["original_link_tlog"],
            original_link_read_tlog=ctx["original_link_read_tlog"], old_compiler_pdb=ctx["old_compiler_pdb"],
            original_objects=list(ctx["old_objects"].values()), private_no_space_IntDir=str(ctx["intdir"]),
            private_output_root=str(ctx["root"]), class_layout_and_kernel_external_ABI_unchanged=True,
            all_direct_HG_class_definition_consumers_recompiled=True)
        env, env_record = environment(b, ctx, calls)
        result["environment"] = env_record
        result["actual_library_search"] = validate_library_search(b, ctx, env)
        objects = compile_sources(b, ad, ctx, env, calls)
        result["compile_invocations"] = 4
        program, all_objects, retained = link(b, ad, ctx, env, objects, calls)
        result.update(program=program, objects=all_objects, retained_objects=retained,
                      object_count=111, new_object_count=4, retained_object_count=107,
                      link_invocations=1, new_program_identity_SHA256_count=1)
        runtime = []
        for source in ctx["runtime_sources"]:
            destination = ctx["out"] / Path(source["path"]).name
            b.need(not destination.exists(), "New runtime destination unexpectedly exists")
            shutil.copy2(source["path"], destination)
            runtime.append(dict(source=source, destination=b.stat(destination)))
        result["runtime"] = runtime
        result["consumed"] = ad.finish()
        result["consumed_stats_unchanged"] = True
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    finally:
        result["calls"] = calls
        actual_calls = [b.read(x["path"]) for x in calls]
        actual_children = [x for x in actual_calls if isinstance(x.get("child"), dict)]
        result["compile_invocations"] = sum(Path(x["program"]["path"]).name.lower() in ("cl.exe", "nvcc.exe") for x in actual_children)
        result["link_invocations"] = sum(Path(x["program"]["path"]).name.lower() == "link.exe" for x in actual_children)
        if ad is not None:
            try:
                result["consumed"] = ad.finish()
                result["consumed_stats_unchanged"] = True
            except Exception as exc:
                result["passed"] = False
                result["consumed_stats_unchanged"] = False
                result["failure"] = (result.get("failure", "") + "; " + str(exc)).lstrip("; ")
        if ctx is not None:
            result["outputs"] = [b.stat(p) for parent in (ctx["root"], ctx["intdir"]) for p in sorted(parent.rglob("*")) if p.is_file()]
            result["ended_utc"] = b.now()
            b.write_new(ctx["record"], result)
        print(json.dumps(dict(passed=result["passed"], configuration=args.configuration, failure=result.get("failure")), ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
