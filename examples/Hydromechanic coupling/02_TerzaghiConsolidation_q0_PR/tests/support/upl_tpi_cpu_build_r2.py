"""Build the isolated frozen-A P1 CPU candidate; never help/run/decode a program.

DebugCPU is a full 86-TU authoritative-project build. ReleaseCPU compiles the
two prepared overlays and links the original 84 untouched A objects. Both
require an independent root build admission; importing this file does nothing.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes as wt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
S = R / "src"
L = T / "logs"
PREP = L / "upl_tpi_cpu_r1.prepare.json"
BASE = L / "upl_spr_av_ReleaseCPU_r1.build.json"
NOTE = T / "notes/upl_tpi_cpu_build_r2.md"
PROJECT = S / "VS/DualSPHysics5ReCpu.vcxproj"
SOLUTION = S / "VS/DualSPHysics5ReCpu_vs2022.sln"
MSBUILD = Path("D:/Program Files/VS2022/MSBuild/Current/Bin/amd64/MSBuild.exe")
VCVARS = Path("D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat")
NS = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
CHANGED = {"JSphCpu.cpp", "JSphCpuSingle.cpp"}


def need(condition, text):
    if not condition:
        raise RuntimeError(text)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def same(entry):
    actual = stat(entry["path"])
    need(actual == {k: entry[k] for k in ("path", "bytes", "mtime_ns")},
         "Frozen stat changed: " + entry["path"])
    return actual


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def process_identity(pid):
    # No process is stopped, resumed or replaced by this script.
    import psutil
    p = psutil.Process(pid)
    return dict(pid=pid, created=p.create_time(), exe=p.exe(), argv=p.cmdline(),
                parent=p.ppid())


def invoke(tag, argv, cwd, env, environment_output=False):
    """Capture this genuine direct child's Popen and independent Win32 exits."""
    call = L / (tag + ".call.json")
    log = L / (tag + ".log")
    need(not call.exists() and not log.exists(), "An original tool call/log is protected")
    entry = dict(stage=tag, owner=process_identity(os.getpid()), program=stat(argv[0]),
                 arguments=list(argv[1:]), cwd=str(cwd), started_utc=now(),
                 raw_stdout_is_environment=environment_output)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel.OpenProcess.restype = wt.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    handle = None
    p = None
    raw = b""
    stderr = b""
    try:
        if environment_output:
            p = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            entry["child"] = process_identity(p.pid)
            handle = kernel.OpenProcess(0x100000 | 0x1000, False, p.pid)
            need(bool(handle), "Unable to acquire original direct-child process handle")
            raw, stderr = p.communicate()
            # `set` may contain credentials. Retain stderr and status, never raw environment.
            with log.open("xb") as f:
                f.write(stderr)
        else:
            with log.open("xb") as f:
                p = subprocess.Popen(argv, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                entry["child"] = process_identity(p.pid)
                handle = kernel.OpenProcess(0x100000 | 0x1000, False, p.pid)
                need(bool(handle), "Unable to acquire original direct-child process handle")
                p.wait()
        exit_code = wt.DWORD()
        need(bool(kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))),
             "Original process-handle exit unavailable")
        entry["actual_Popen_wait_exit"] = p.returncode
        entry["actual_Win32_exit"] = exit_code.value
        entry["passed"] = p.returncode == exit_code.value == 0
    except Exception as exc:
        entry["failure"] = str(exc)
        entry["passed"] = False
        if p is not None:
            entry["actual_Popen_poll_at_exception"] = p.poll()
        # No retry, inferred exit, termination, or replacement is performed.
        raise
    finally:
        if handle:
            kernel.CloseHandle(handle)
        entry["ended_utc"] = now()
        if log.exists():
            entry["log"] = stat(log)
        write_new(call, entry)
    need(entry["passed"], "Owned build tool failed: " + str(call))
    return stat(call), raw


def windows_argv(text):
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wt.LPWSTR)
    kernel.LocalFree.argtypes = [wt.HLOCAL]
    count = ctypes.c_int()
    p = shell.CommandLineToArgvW("dummy.exe " + text, ctypes.byref(count))
    need(bool(p), "Original Windows tool command cannot be parsed")
    try:
        return [p[i] for i in range(1, count.value)]
    finally:
        kernel.LocalFree(p)


def project_closure(configuration, expected):
    root = ET.parse(PROJECT).getroot()
    active = []
    for item in root.findall(".//m:ItemGroup/m:ClCompile", NS):
        exclusions = [x for x in item.findall("m:ExcludedFromBuild", NS)
                      if configuration + "|x64" in x.get("Condition", "") and x.text == "true"]
        if not exclusions:
            # Current active items carry no per-file options; reject future silent divergence.
            need(not list(item), "New active per-TU project options require root review")
            active.append(item.attrib["Include"])
    names = [Path(x.replace("\\", "/")).stem + ".obj" for x in active]
    need(len(names) == len(set(names)) == 87 and set(names) - set(expected) == {"JSphCpu_mdbc.obj"}
         and not set(expected) - set(names), "Current project no longer has the reviewed unique 87-to-86 adaptation")
    return active, dict(current_active_count=87, frozen_A_count=86,
                        unique_removed="JSphCpu_mdbc.cpp", missing_from_current=[],
                        original_project_changed=False)


def emit_targets(path, source, active, expected, intdir, evaluated):
    # Current project/configuration/targets remain authoritative. The private
    # import redirects its active compile items, preserving original CPU options.
    uri = NS["m"]
    ET.register_namespace("", uri)
    root = ET.Element("{" + uri + "}Project")
    props = ET.SubElement(root, "PropertyGroup")
    ET.SubElement(props, "PostBuildEventUseInBuild").text = "false"
    group = ET.SubElement(root, "ItemGroup")
    ET.SubElement(group, "ClCompile", Remove=";".join(active))
    for obj in expected:
        ET.SubElement(group, "ClCompile", Include=str(source / (Path(obj).stem + ".cpp")))
    defs = ET.SubElement(root, "ItemDefinitionGroup")
    cl = ET.SubElement(defs, "ClCompile")
    ET.SubElement(cl, "AdditionalIncludeDirectories").text = str(source) + ";%(AdditionalIncludeDirectories)"
    ET.SubElement(cl, "ProgramDataBaseFileName").text = str(intdir / "vc143.pdb")
    link = ET.SubElement(defs, "Link")
    ET.SubElement(link, "ProgramDatabaseFile").text = "$(OutDir)candidate.pdb"
    ET.SubElement(link, "ImportLibrary").text = "$(OutDir)candidate.lib"
    ET.SubElement(link, "LinkTimeCodeGenerationObjectFile").text = "$(IntDir)candidate.iobj"
    ET.SubElement(link, "AdditionalOptions").text = '/ILK:"$(IntDir)candidate.ilk" %(AdditionalOptions)'
    check = ET.SubElement(root, "Target", Name="UplTpiFrozenCompileList", BeforeTargets="ClCompile")
    ET.SubElement(check, "WriteLinesToFile", File=str(evaluated), Overwrite="true",
                  Lines="@(ClCompile->'%(FullPath)|%(ExcludedFromBuild)')", Encoding="UTF-8")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", required=True, choices=["DebugCPU", "ReleaseCPU"])
    parser.add_argument("--execution-authorized", action="store_true")
    parser.add_argument("--admission", required=True, type=Path)
    args = parser.parse_args()
    need(args.execution_authorized, "Independent root build admission required")
    tag = "upl_tpi_cpu_" + args.configuration + "_r2"
    root = T / "outputs" / tag
    receipt = L / (tag + ".build.json")
    need(not root.exists() and not receipt.exists(), "Existing candidate build/failure is protected")
    admission_entry = stat(args.admission)
    admission = read(args.admission)
    need(admission.get("stage") == "upl_tpi_cpu_r2.build_admission" and admission.get("passed") is True
         and admission.get("build_only") is True and admission.get("configuration") == args.configuration,
         "Reviewed configuration-specific root build-only admission required")
    frozen = {str(Path(x["path"]).resolve()): x for x in admission["inputs"]}
    required = [Path(__file__), NOTE, PREP, BASE, PROJECT, SOLUTION]
    for p in required:
        need(str(p.resolve()) in frozen, "Root admission lacks consumed author/recipe: " + str(p))
    consumed = [same(x) for x in frozen.values()] + [admission_entry]
    prep, base = read(PREP), read(BASE)
    need(prep.get("passed") is True and prep.get("stage") == "upl_tpi_cpu_r1.prepare"
         and prep.get("objects_unmodified") is True and prep.get("class_or_header_ABI_changed") is False,
         "Prepared unchanged-ABI final-A source overlay required")
    need(base.get("passed") is True and base.get("object_count") == 86
         and base.get("non_main_object_count") == 85 and base.get("exact_object_basename_closure") is True,
         "Original complete authoritative finite-Kw A build required")
    source = Path(prep["source_root"]).resolve()
    need(len(prep["files"]) == 266 and len(prep["base_source_entries"]) == 265,
         "Prepared flat 265-source plus one-helper closure differs")
    consumed += [same(x) for x in prep["files"]]
    consumed += [same(prep[k]) for k in ("base_build", "base_program", "private_header", "source_diff")]
    need({Path(x["path"]).name for x in prep["changed_sources"]} == CHANGED,
         "Only the two admitted CPU translation units may differ")
    # One independent bytewise ABI/source closure comparison; no legacy SHA scan.
    for entry in prep["base_source_entries"]:
        old = same(entry["snapshot"])
        consumed.append(old)
        p = Path(old["path"])
        need((source / p.name).is_file(), "Missing prepared frozen-A source member")
        if p.name not in CHANGED:
            need(p.read_bytes() == (source / p.name).read_bytes(),
                 "An unapproved source/header changed: " + p.name)
    expected = base["expected_object_basenames"]
    need(len(expected) == len(set(expected)) == 86, "A 86-object basename list changed")
    active, closure = project_closure(args.configuration, expected)
    old_objects = [stat(x["path"]) for x in base["objects"]]
    need(len(old_objects) == 86 and {Path(x["path"]).name for x in old_objects} == set(expected),
         "Retained complete A object closure differs")
    consumed += old_objects
    # Existing object identity is frozen once by stat, not a repeated old-object SHA sweep.
    canonical_before = [stat(p) for p in (R / "bin/windows").glob("DualSPHysics*.exe")]
    consumed += [stat(MSBUILD), stat(VCVARS)]
    cllog = L / "upl_spr_av_ReleaseCPU_r1_CL.command.tlog"
    linklog = L / "upl_spr_av_ReleaseCPU_r1_link.command.tlog"
    consumed += [stat(cllog), stat(linklog)]
    libraries = [stat(x["path"]) for x in base["libraries"]]
    consumed += libraries
    runtime = [stat(x["copy"]["path"]) for x in base["runtime"]]
    consumed += runtime
    for entry in consumed:
        same(entry)
    root.mkdir()
    intdir = root / "int"
    outdir = root / "out"
    intdir.mkdir()
    outdir.mkdir()
    result = dict(stage="upl_tpi_cpu_build_r2", passed=False, configuration=args.configuration,
                  root_admission=admission_entry, prepared=stat(PREP), original_build=stat(BASE),
                  frozen_A_reproduction_not_canonical_Debug=True, current_project=stat(PROJECT),
                  authoritative_solution=stat(SOLUTION), compile_closure=closure,
                  original_class_header_ABI_unchanged=True, legacy_SHA_scans=0,
                  public_source_changed=False, canonical_programs_changed=False,
                  solver_invocations=0, program_help_invocations=0, native_invocations=0,
                  physical_acceptance=False, calls=[], consumed=consumed,
                  base_Release_library_bindings_only=libraries,
                  base_Release_libraries_are_not_Debug_actual_dependency_proof=True,
                  all_new_outputs_root=str(root), started_utc=now())
    try:
        # A script path is one cmd token. Do not pass embedded quoted `call`
        # text through subprocess.list2cmdline: cmd does not unescape C quotes.
        environment_script = root / "load_environment.cmd"
        with environment_script.open("x", encoding="mbcs", newline="") as f:
            f.write('@echo off\r\ncall "' + str(VCVARS)
                    + '" x64 -vcvars_ver=14.36 >nul\r\n'
                    + 'if errorlevel 1 exit /b %errorlevel%\r\nset\r\n')
        result["environment_script"] = stat(environment_script)
        call, raw = invoke(tag + ".environment", [os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"),
                           "/d", "/s", "/c", environment_script.name], root, os.environ.copy(), True)
        result["calls"].append(call)
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in raw.decode("mbcs").splitlines()
                   if "=" in line and not line.startswith("=")))
        env.pop("CL", None)
        env.pop("_CL_", None)
        need(env.get("VCTOOLSVERSION") == "14.36.32532", "Original A MSVC v143 toolset changed")
        result["toolset"] = {k: env.get(k) for k in ("VCTOOLSVERSION", "VCTOOLSINSTALLDIR", "WINDOWSSDKVERSION")}
        tool = Path(env["VCTOOLSINSTALLDIR"]) / "bin/Hostx64/x64"
        exe = outdir / ("DualSPHysics5.2CPU_win64_debug.exe" if args.configuration == "DebugCPU"
                        else "DualSPHysics5.2CPU_win64.exe")
        if args.configuration == "DebugCPU":
            targets = root / "frozen_A_sources.targets"
            evaluated = root / "evaluated_compile_sources.txt"
            emit_targets(targets, source, active, expected, intdir, evaluated)
            binlog = L / (tag + ".binlog")
            argv = [str(MSBUILD), str(SOLUTION), "/m", "/t:Build", "/p:Configuration=DebugCPU", "/p:Platform=x64",
                    "/p:OutDir=" + str(outdir) + "/", "/p:IntDir=" + str(intdir) + "/",
                    "/p:ForceImportAfterCppTargets=" + str(targets), "/p:PostBuildEventUseInBuild=false",
                    "/p:VCToolsVersion=14.36.32532", "/v:minimal", "/bl:" + str(binlog)]
            call, _ = invoke(tag + ".msbuild", argv, S / "VS", env)
            result["calls"].append(call)
            actual = []
            for line in evaluated.read_text(encoding="utf-8-sig").splitlines():
                path, excluded = line.rsplit("|", 1)
                if excluded.lower() != "true":
                    actual.append(Path(path).resolve())
            need(len(actual) == 86 and set(actual) == {source / (Path(x).stem + ".cpp") for x in expected},
                 "Actual evaluated Debug compile sources differ from the frozen 86 closure")
            new_objects = [stat(intdir / x) for x in expected]
            tlogs = list(intdir.rglob("CL.command.1.tlog")) + list(intdir.rglob("link.command.1.tlog"))
            readlogs = list(intdir.rglob("CL.read.1.tlog"))
            link_readlogs = list(intdir.rglob("link.read.1.tlog"))
            need(len(tlogs) == 2 and len(readlogs) == len(link_readlogs) == 1,
                 "Original MSBuild CL/link evidence missing or ambiguous")
            for line in readlogs[0].read_text(encoding="utf-16").splitlines():
                if not line.startswith("^") and Path(line).is_absolute():
                    need(not Path(line).resolve().is_relative_to((S / "source").resolve()),
                         "Debug compilation consumed a live public source/header")
            # Observe the actual Debug linker reads, not the retained Release
            # recipe's library list. These stats are taken after the real link;
            # they are not invented pre-build identities or per-tool exits.
            debug_libraries = sorted({Path(line).resolve()
                for line in link_readlogs[0].read_text(encoding="utf-16").splitlines()
                if not line.startswith("^") and line.lower().endswith(".lib")})
            need(bool(debug_libraries), "Actual Debug linker library read closure is empty")
            result.update(compile_invocations_via_authoritative_MSBuild=86, original_objects_reused=0,
                          objects=new_objects, private_targets=stat(targets), evaluated_compile_sources=stat(evaluated),
                          compiler_linker_command_tlogs=[stat(p) for p in tlogs], compiler_read_tlogs=[stat(p) for p in readlogs],
                          linker_read_tlogs=[stat(p) for p in link_readlogs],
                          actual_Debug_link_library_stats=[stat(p) for p in debug_libraries],
                          Debug_library_stat_scope="Actual link.read.1.tlog paths observed after the genuine Debug link, not pre-build freezing",
                          binlog=stat(binlog), CL_link_separately_owned_handle_exits=False,
                          compiler_exit_scope="MSBuild child exit plus original command/read tlogs and binlog; no invented per-tool handle exits")
        else:
            lines = cllog.read_text(encoding="utf-16").splitlines()
            commands = {Path(lines[i][1:]).name.upper(): windows_argv(lines[i + 1]) for i in range(0, len(lines), 2)}
            linklines = linklog.read_text(encoding="utf-16").splitlines()
            linkargs = windows_argv(" ".join(linklines[1:]))
            linked = [Path(x).resolve() for x in linkargs if x.lower().endswith(".obj")]
            need(len(linked) == 86 and {x.name for x in linked} == set(expected), "Original Release link closure changed")
            env["LIB"] = ";".join(dict.fromkeys(str(Path(x["path"]).parent) for x in libraries))
            replacements, deps = {}, []
            for leaf in sorted(CHANGED):
                original = commands[leaf.upper()]
                need(original[-1].upper().endswith("\\" + leaf.upper()) and "/fp:precise" in original
                     and "/openmp" in original and "/MT" in original, "Original precise Release CPU flags differ")
                argv = [x for x in original[:-1] if not x.lower().startswith(("/fo", "/fd"))]
                obj = intdir / (Path(leaf).stem + ".obj")
                dep = intdir / (leaf + ".dependencies.json")
                argv += ["/I" + str(source), "/Fo" + str(obj), "/Fd" + str(intdir / (leaf + ".pdb")),
                         "/sourceDependencies", str(dep), str(source / leaf)]
                call, _ = invoke(tag + "." + Path(leaf).stem, [str(tool / "cl.exe"), *argv], S / "VS", env)
                result["calls"].append(call)
                data = read(dep)["Data"]
                includes = {Path(x).resolve() for x in data["Includes"]}
                need(Path(data["Source"]).resolve() == source / leaf and source / "upl_tpi_cpu_r1.h" in includes
                     and source / "JSphCpu.h" in includes and source / "JSph.h" in includes
                     and all(not x.is_relative_to((S / "source").resolve()) for x in includes),
                     "Private Release TU consumed live or missing frozen headers")
                replacements[obj.name.lower()] = obj
                deps.append(stat(dep))
            argv = []
            redirect = {"/pdb": outdir / "candidate.pdb", "/implib": outdir / "candidate.lib",
                        "/ltcgout": intdir / "candidate.iobj", "/pgd": intdir / "candidate.pgd", "/ilk": intdir / "candidate.ilk"}
            for arg in linkargs:
                low = arg.lower()
                if low.endswith(".obj"):
                    argv.append(str(replacements.get(Path(arg).name.lower(), Path(arg))))
                elif low.startswith("/out:"):
                    argv.append("/OUT:" + str(exe))
                elif ":" in arg and arg.split(":", 1)[0].lower() in redirect:
                    prefix = arg.split(":", 1)[0]
                    argv.append(prefix + ":" + str(redirect[prefix.lower()]))
                else:
                    argv.append(arg)
            argv += ["/ILK:" + str(intdir / "candidate.ilk")]
            final_objects = [Path(x).resolve() for x in argv if x.lower().endswith(".obj")]
            need(len(final_objects) == 86 and sum(x.parent == intdir for x in final_objects) == 2,
                 "Release must retain exactly 84 original objects and replace only two")
            call, _ = invoke(tag + ".link", [str(tool / "link.exe"), *argv], S / "VS", env)
            result["calls"].append(call)
            result.update(compile_invocations=2, link_invocations=1, original_objects_reused=84,
                          actual_link_objects=[stat(x) for x in final_objects], dependencies=deps,
                          CL_link_separately_owned_handle_exits=True)
        copied = []
        for entry in runtime:
            dest = outdir / Path(entry["path"]).name
            need(not dest.exists(), "Fresh runtime copy destination already exists")
            shutil.copy2(entry["path"], dest)
            copied.append(dict(source=entry, destination=stat(dest)))
        if args.configuration == "DebugCPU":
            debugomp = Path("D:/Program Files/VS2022/VC/Redist/MSVC/14.36.32532/debug_nonredist/x64/Microsoft.VC143.DebugOpenMP/vcomp140d.dll")
            dest = outdir / debugomp.name
            shutil.copy2(debugomp, dest)
            copied.append(dict(source=stat(debugomp), destination=stat(dest)))
        for entry in consumed:
            same(entry)
        for entry in canonical_before:
            same(entry)
        # A single identity digest of the newly linked executable, not old object/BI4 scans.
        program = stat(exe)
        program["sha256"] = hashlib.sha256(exe.read_bytes()).hexdigest()
        result.update(passed=True, program=program, runtime=copied, consumed_stats_unchanged=True,
                      original_objects_stats_unchanged=True, canonical_programs_stats_unchanged=True,
                      new_program_identity_SHA256_count=1, new_outputs=[stat(p) for p in root.rglob("*") if p.is_file()])
    except Exception as exc:
        result["failure"] = str(exc)
        result["following_action_launched"] = False
        raise
    finally:
        result["ended_utc"] = now()
        write_new(receipt, result)
    print(str(receipt))


if __name__ == "__main__":
    main()
