"""One root-admitted full86 C04 DebugCPU build; never run a solver or reader.

The restored C04 project/source tree is a new candidate reconstruction. No old
C02/C04 object is reused or retroactively given a new source-content identity.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes as wt
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
S = R / "src"
L = T / "logs"
TAG = "upl_tpi_cryer_cpu_DebugCPU_r1"
STAGE = "upl_tpi_cryer_cpu_build_r1"
NOTE = T / "notes/upl_tpi_cryer_cpu_build_r1.md"
PREP = L / "upl_tpi_cryer_cpu_overlay_r1.prepare.json"
SOURCE_PREP = L / "upl_tpi_cryer_cpu_source_r1.prepare.json"
OLD_BUILD = L / "upl_cryer_freebody_r1_DebugCPU.build.json"
OLD_CALL = L / "upl_cryer_freebody_r1_DebugCPU.call.json"
OUTROOT = T / "outputs" / TAG
RECEIPT = L / (TAG + ".build.json")
MSBUILD = Path("D:/Program Files/VS2022/MSBuild/Current/Bin/amd64/MSBuild.exe")
VCVARS = Path("D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat")
DEBUG_OMP = Path("D:/Program Files/VS2022/VC/Redist/MSVC/14.36.32532/debug_nonredist/x64/Microsoft.VC143.DebugOpenMP/vcomp140d.dll")
NS = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def stat(path):
    p = Path(path).resolve(); s = p.stat()
    need(p.is_file(), "Not a file: " + str(p))
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def key(path):
    return str(Path(path).resolve()).casefold()


def same(entry):
    actual = stat(entry["path"])
    need(actual == {k: entry[k] for k in ("path", "bytes", "mtime_ns")}, "Frozen stat changed: " + entry["path"])
    return actual


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


class Admission:
    def __init__(self, path):
        self.entry = stat(path); self.data = read(path)
        need(self.data.get("stage") == STAGE + ".build_admission" and self.data.get("passed") is True
             and self.data.get("build_only") is True and self.data.get("configuration") == "DebugCPU",
             "One independent full86 DebugCPU build-only root admission required")
        self.frozen = {key(e["path"]): e for e in self.data["inputs"]}
        need(len(self.frozen) == len(self.data["inputs"]), "Duplicate frozen root input")
        self.consumed = {}

    def pin(self, path):
        k = key(path); need(k in self.frozen, "Consumed input absent from admission: " + str(path))
        self.consumed[k] = same(self.frozen[k]); return self.consumed[k]

    def finish(self):
        for entry in self.consumed.values(): same(entry)
        same(self.entry)
        return list(self.consumed.values())


def identity(pid):
    import psutil
    p = psutil.Process(pid)
    return dict(pid=pid, created=p.create_time(), exe=p.exe(), argv=p.cmdline(), parent=p.ppid())


def invoke(tag, argv, cwd, env, environment_output=False):
    """Own the original direct MSBuild/cmd child and preserve both actual exits."""
    call, log = L / (tag + ".call.json"), L / (tag + ".log")
    need(not call.exists() and not log.exists(), "Existing call/log is protected")
    entry = dict(stage=tag, owner=identity(os.getpid()), program=stat(argv[0]), arguments=list(argv[1:]),
                 cwd=str(cwd), started_utc=now(), raw_stdout_is_environment=environment_output,
                 passed=False, actual_Popen_wait_exit=None, actual_Win32_exit=None)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wt.HANDLE
    kernel.DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL, wt.DWORD]
    kernel.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    kernel.GetProcessTimes.argtypes = [wt.HANDLE, ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME), ctypes.POINTER(wt.FILETIME)]
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    handle = wt.HANDLE(); child = None; raw = b""; communicated = False
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen(argv, cwd=cwd, env=env,
                stdout=subprocess.PIPE if environment_output else stream,
                stderr=subprocess.PIPE if environment_output else subprocess.STDOUT,
                shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            current = kernel.GetCurrentProcess()
            need(kernel.DuplicateHandle(current, wt.HANDLE(int(child._handle)), current,
                 ctypes.byref(handle), 0, False, 2), "Original child handle duplication failed")
            entry["child"] = identity(child.pid)
            need(entry["child"]["parent"] == entry["owner"]["pid"]
                 and key(entry["child"]["exe"]) == key(argv[0])
                 and entry["child"]["argv"][1:] == list(argv[1:]), "Actual direct child/argv differs")
            times = [wt.FILETIME() for _ in range(4)]
            need(kernel.GetProcessTimes(handle, *[ctypes.byref(x) for x in times]), "Original native creation time unavailable")
            ticks = (int(times[0].dwHighDateTime) << 32) | int(times[0].dwLowDateTime)
            entry["creation_FILETIME_ticks"] = ticks
            need(abs((ticks - 116444736000000000) / 1e7 - entry["child"]["created"]) <= 1e-6,
                 "Native and observed child creation times differ")
            if environment_output:
                raw, stderr = child.communicate(); communicated = True; stream.write(stderr)
            else:
                child.wait()
            entry["actual_Popen_wait_exit"] = child.returncode
            value = wt.DWORD(); need(kernel.GetExitCodeProcess(handle, ctypes.byref(value)), "Actual native exit unavailable")
            entry["actual_Win32_exit"] = int(value.value)
            entry["passed"] = child.returncode == value.value == 0
    except Exception as exc:
        entry["failure"] = str(exc)
        if child is not None:
            if environment_output and not communicated:
                raw, stderr = child.communicate(); communicated = True
                with log.open("ab") as stream: stream.write(stderr)
            entry["actual_Popen_wait_exit"] = child.wait()
            if handle:
                value = wt.DWORD()
                if kernel.GetExitCodeProcess(handle, ctypes.byref(value)): entry["actual_Win32_exit"] = int(value.value)
    finally:
        if handle: kernel.CloseHandle(handle)
        entry["ended_utc"] = now()
        if log.exists(): entry["log"] = stat(log)
        write_new(call, entry)
    need(entry["passed"], "Actual owned tool failed; preserve " + str(call))
    return stat(call), raw


def windows_argv(text):
    shell, kernel = ctypes.WinDLL("shell32"), ctypes.WinDLL("kernel32")
    shell.CommandLineToArgvW.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wt.LPWSTR)
    kernel.LocalFree.argtypes = [wt.HLOCAL]
    count = ctypes.c_int(); args = shell.CommandLineToArgvW("dummy.exe " + text, ctypes.byref(count))
    need(bool(args), "Windows CL command parsing failed")
    try: return [args[i] for i in range(1, count.value)]
    finally: kernel.LocalFree(args)


def commands(path):
    lines = Path(path).read_text(encoding="utf-16").splitlines(); result = {}
    need(len(lines) % 2 == 0, "CL tlog command-pair schema differs")
    for i in range(0, len(lines), 2):
        need(lines[i].startswith("^") and "|" not in lines[i], "One genuine source per CL command required")
        leaf = Path(lines[i][1:]).name.casefold()
        need(leaf not in result, "Duplicate CL source entry")
        result[leaf] = windows_argv(lines[i + 1])
    return result


def normalized_flags(args, source):
    result = []; skip = False; sources = 0; dependencies = 0
    for arg in args:
        low = arg.casefold()
        if skip: skip = False; continue
        if low == "/sourcedependencies": dependencies += 1; skip = True
        elif low.startswith("/sourcedependencies:"): dependencies += 1
        elif low.startswith(("/fo", "/fd")): continue
        elif key(arg) == key(source): sources += 1
        else: result.append(arg.upper())
    need(sources == 1 and not skip, "Actual CL source or dependency argument malformed")
    return result, dependencies


def emit_targets(path, active, intdir, outdir, libdirs, evaluated):
    uri = NS["m"]; ET.register_namespace("", uri); root = ET.Element("{" + uri + "}Project")
    props = ET.SubElement(root, "PropertyGroup")
    for name in ("PreBuildEventUseInBuild", "PreLinkEventUseInBuild", "PostBuildEventUseInBuild"):
        ET.SubElement(props, name).text = "false"
    group = ET.SubElement(root, "ItemGroup")
    for include in active:
        leaf = Path(include.replace("\\", "/")).stem
        item = ET.SubElement(group, "ClCompile", Update=include)
        ET.SubElement(item, "AdditionalOptions").text = '/sourceDependencies "' + str(intdir / (leaf + ".dependencies.json")) + '" %(AdditionalOptions)'
    definitions = ET.SubElement(root, "ItemDefinitionGroup")
    cl = ET.SubElement(definitions, "ClCompile")
    ET.SubElement(cl, "ProgramDataBaseFileName").text = str(intdir / "vc143.pdb")
    link = ET.SubElement(definitions, "Link")
    ET.SubElement(link, "AdditionalLibraryDirectories").text = ";".join(map(str, libdirs)) + ";%(AdditionalLibraryDirectories)"
    ET.SubElement(link, "ProgramDatabaseFile").text = str(outdir / "candidate.pdb")
    ET.SubElement(link, "ImportLibrary").text = str(outdir / "candidate.lib")
    ET.SubElement(link, "LinkTimeCodeGenerationObjectFile").text = str(intdir / "candidate.iobj")
    ET.SubElement(link, "AdditionalOptions").text = '/ILK:"' + str(intdir / "candidate.ilk") + '" %(AdditionalOptions)'
    target = ET.SubElement(root, "Target", Name="C04PrivateDebugCompileList", BeforeTargets="ClCompile")
    ET.SubElement(target, "WriteLinesToFile", File=str(evaluated), Overwrite="true", Encoding="UTF-8",
                  Lines="@(ClCompile->'%(FullPath)|%(ExcludedFromBuild)')")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def context(ad):
    for path in (Path(__file__), NOTE, sys.executable, PREP, SOURCE_PREP, OLD_BUILD, OLD_CALL, MSBUILD, VCVARS, DEBUG_OMP): ad.pin(path)
    import psutil
    ad.pin(psutil.__file__)
    prep, recovered, old, oldcall = map(read, (PREP, SOURCE_PREP, OLD_BUILD, OLD_CALL))
    need(prep.get("passed") is True and prep.get("requires_full_DebugCPU_86_TU_compile") is True
         and prep.get("helper_unchanged_byte_copy") is True and prep.get("HG_adapters_called") is False
         and recovered.get("passed") is True and recovered.get("source_count") == 265,
         "Completed reconstructed source and narrow two-TU overlay required")
    need(old.get("passed") is True and old.get("objects") == 86 and oldcall.get("exit_code") == 0,
         "Original actual C04 Debug recipe required, not reusable objects")
    root = Path(prep["source_root"]).resolve(); source = root / "source"; vs = root / "VS"
    for entry in prep["files"]: ad.pin(entry["path"]); same(entry)
    for field in ("base_prepare_check", "base_manifest", "source_diff"): ad.pin(prep[field]["path"]); same(prep[field])
    need(key(prep["base_prepare_check"]["path"]) == key(SOURCE_PREP), "Overlay consumed a different source reconstruction")
    difference = read(prep["source_diff"]["path"])
    need(difference.get("passed") is True and set(difference["only_changed_TUs"]) == {"JSphCpu.cpp", "JSphCpuSingle.cpp"}
         and difference.get("unchanged_generic_helper_byte_copy") is True and difference.get("class_or_header_ABI_changed") is False,
         "Only the two reviewed CPU hooks and the exact tested generic helper are permitted")
    solution, project = vs / "DualSPHysics5ReCpu_vs2022.sln", vs / "DualSPHysics5ReCpu.vcxproj"
    ad.pin(solution); ad.pin(project)
    tree = ET.parse(project).getroot(); active, excluded = [], []
    for item in tree.findall(".//m:ClCompile[@Include]", NS):
        rejected = any("DebugCPU|x64" in e.get("Condition", "") and e.text == "true" for e in item.findall("m:ExcludedFromBuild", NS))
        (excluded if rejected else active).append(item.get("Include"))
    need(len(active) == 86 and len(excluded) == 10 and len(set(active)) == 86, "Restored authoritative 96-item/86CPU closure differs")
    leaves = [Path(x.replace("\\", "/")).name for x in active]
    need(len(set(leaves)) == 86 and all((source / x).is_file() for x in leaves), "Missing/duplicate full86 private source")
    tlogroot = Path(next(x.split("=", 1)[1] for x in oldcall["arguments"] if x.startswith("/p:IntDir="))) / "DualSPHysics.tlog"
    tlogs = {name: tlogroot / name for name in ("CL.command.1.tlog", "CL.read.1.tlog", "link.command.1.tlog", "link.read.1.tlog")}
    for path in tlogs.values(): ad.pin(path)
    old_commands = commands(tlogs["CL.command.1.tlog"])
    need(set(old_commands) == {x.casefold() for x in leaves}, "New project/old actual TU membership differs")
    libraries = sorted({Path(x).resolve() for x in tlogs["link.read.1.tlog"].read_text(encoding="utf-16").splitlines()
                        if not x.startswith("^") and x.casefold().endswith(".lib")}, key=key)
    need(len(libraries) == 23, "Original actual linker-library closure differs")
    for path in libraries: ad.pin(path)
    third = [x for x in libraries if key(x.parent) == key(S / "lib/vs2022")]
    need(len(third) == 5 and {x.name.casefold() for x in third} == {"dsphchrono.lib", "libjvtklib_x64_v143_debug.lib", "libjnumexlib_x64_v143_debug.lib", "libjwavegen_x64_v143_debug.lib", "libdsphmoordyn_x64_v143_debug.lib"}, "Five actual original Debug project libraries differ")
    for entry in old["runtime"]: ad.pin(entry["path"]); same(entry)
    intdir = Path(os.environ["LOCALAPPDATA"]) / "Temp" / TAG / "int"
    need(" " not in str(intdir) and not intdir.parent.exists() and not OUTROOT.exists() and not RECEIPT.exists(), "Existing private build/failure or non-private space-containing IntDir is protected")
    return dict(source_root=root, source=source, vs=vs, solution=solution, project=project, active=active, leaves=leaves,
                expected_objects=[Path(x).stem + ".obj" for x in leaves], old_commands=old_commands, old_libraries=libraries,
                third_party=third, runtime=old["runtime"], intdir=intdir, outdir=OUTROOT / "out", prepared=ad.pin(PREP),
                original_tlogs={k: ad.pin(v) for k, v in tlogs.items()})


def build(ad, ctx, result):
    OUTROOT.mkdir(); ctx["outdir"].mkdir(); ctx["intdir"].mkdir(parents=True)
    libdir = OUTROOT / "lib/vs2022"; libdir.mkdir(parents=True)
    copies = []
    for source in ctx["third_party"]:
        dest = libdir / source.name; shutil.copy2(source, dest)
        need(dest.read_bytes() == source.read_bytes(), "New private project library copy differs")
        copies.append(dict(source=stat(source), destination=stat(dest)))
    result["project_library_copies"] = copies
    batch = OUTROOT / "load_environment.cmd"
    with batch.open("xb") as f:
        f.write(('@echo off\r\ncall "' + str(VCVARS) + '" x64 8.1 -vcvars_ver=14.36 >nul\r\nif errorlevel 1 exit /b %errorlevel%\r\nset\r\n').encode("mbcs"))
    ad.finish()
    call, raw = invoke(TAG + ".environment", [os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"), "/d", "/s", "/c", batch.name], OUTROOT, os.environ.copy(), True)
    result["calls"].append(call)
    env = {k.upper(): v for k, v in os.environ.items()}
    env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in raw.decode("mbcs").splitlines() if "=" in line and not line.startswith("=")))
    for name in ("CL", "_CL_", "LINK", "_LINK_", "UPL_TPI_CPU_R1", "UPL_TPI_GPU_R1"): env.pop(name, None)
    need(env.get("VCTOOLSVERSION") == "14.36.32532" and "8.1" in env.get("WINDOWSSDKDIR", ""), "Original MSVC14.36/SDK8.1 selection differs")
    result["environment_batch"] = stat(batch)
    result["selected_toolchain"] = {name: env.get(name) for name in ("VCTOOLSVERSION", "VCTOOLSINSTALLDIR", "WINDOWSSDKDIR", "WINDOWSSDKVERSION")}
    result["vcvars_LIB_retained_not_overwritten"] = True
    system_libdirs = list(dict.fromkeys(p.parent for p in ctx["old_libraries"] if p not in ctx["third_party"]))
    targets, evaluated = OUTROOT / "private_debug.targets", OUTROOT / "evaluated_compile_sources.txt"
    emit_targets(targets, ctx["active"], ctx["intdir"], ctx["outdir"], [libdir, *system_libdirs], evaluated)
    binlog = L / (TAG + ".binlog")
    need(not binlog.exists(), "Existing MSBuild log is protected")
    args = [str(MSBUILD), str(ctx["solution"]), "/m", "/t:Build", "/p:Configuration=DebugCPU", "/p:Platform=x64",
            "/p:VCToolsVersion=14.36.32532", "/p:WindowsTargetPlatformVersion=8.1",
            "/p:OutDir=" + str(ctx["outdir"]) + "/", "/p:IntDir=" + str(ctx["intdir"]) + "/",
            "/p:ForceImportAfterCppTargets=" + str(targets), "/p:PostBuildEventUseInBuild=false", "/v:minimal", "/bl:" + str(binlog)]
    ad.finish(); call, _ = invoke(TAG + ".msbuild", args, ctx["vs"], env); result["calls"].append(call)
    actual = [Path(x.rsplit("|", 1)[0]).resolve() for x in evaluated.read_text(encoding="utf-8-sig").splitlines() if x.rsplit("|", 1)[1].lower() != "true"]
    need(len(actual) == 86 and {key(x) for x in actual} == {key(ctx["source"] / x) for x in ctx["leaves"]}, "Actual evaluated compile sources differ")
    objects = [stat(ctx["intdir"] / x) for x in ctx["expected_objects"]]
    need({key(x) for x in ctx["intdir"].glob("*.obj")} == {key(x["path"]) for x in objects}, "New object closure is not exactly86")
    dependencies, includes = [], set()
    for leaf in ctx["leaves"]:
        path = ctx["intdir"] / (Path(leaf).stem + ".dependencies.json"); data = read(path)["Data"]
        need(key(data["Source"]) == key(ctx["source"] / leaf), "Per-TU dependency source differs")
        for name in data["Includes"]:
            p = Path(name).resolve()
            need(not p.is_relative_to(S / "source") and (not p.is_relative_to(R) or p.is_relative_to(ctx["source"])), "Compiler consumed live or unrelated repository header")
            includes.add(p)
        dependencies.append(stat(path))
    need(ctx["source"] / "upl_tpi_cpu_r1.h" in includes, "Actual TPI helper was not consumed")
    logs = {}
    for name in ("CL.command.1.tlog", "CL.read.1.tlog", "link.command.1.tlog", "link.read.1.tlog"):
        found = list(ctx["intdir"].rglob(name)); need(len(found) == 1, "Missing/ambiguous actual MSBuild tlog: " + name); logs[name] = found[0]
    current_commands = commands(logs["CL.command.1.tlog"])
    need(set(current_commands) == set(ctx["old_commands"]), "Actual new86 CL closure differs")
    for leaf in ctx["leaves"]:
        old = ctx["old_commands"][leaf.casefold()]
        oldsource = next(x for x in old if x.casefold().endswith("\\" + leaf.casefold()))
        before, count0 = normalized_flags(old, oldsource)
        after, count1 = normalized_flags(current_commands[leaf.casefold()], ctx["source"] / leaf)
        need(before == after and count0 == 0 and count1 == 1, "Original Debug numerical/compiler flags changed: " + leaf)
    actual_libraries = {key(x): Path(x).resolve() for x in logs["link.read.1.tlog"].read_text(encoding="utf-16").splitlines() if not x.startswith("^") and x.casefold().endswith(".lib")}
    expected_libraries = {key(libdir / x.name if x in ctx["third_party"] else x) for x in ctx["old_libraries"]}
    need(set(actual_libraries) == expected_libraries, "Actual linker did not use precisely the bound original-system/private-project library closure")
    runtime = []
    for entry in [*ctx["runtime"], stat(DEBUG_OMP)]:
        dest = ctx["outdir"] / Path(entry["path"]).name; need(not dest.exists(), "Fresh runtime destination exists")
        shutil.copy2(entry["path"], dest); need(dest.read_bytes() == Path(entry["path"]).read_bytes(), "Private runtime copy differs")
        runtime.append(dict(source=entry, destination=stat(dest)))
    program = ctx["outdir"] / "DualSPHysics5.2CPU_win64_debug.exe"
    result.update(program=stat(program), runtime=runtime, objects=objects, object_count=86, original_objects_reused=0,
                  compile_invocations_via_authoritative_MSBuild=86, link_invocations_via_authoritative_MSBuild=1,
                  private_targets=stat(targets), evaluated_compile_sources=stat(evaluated), dependencies=dependencies,
                  actual_compiler_include_stats=[stat(p) for p in sorted(includes, key=key)],
                  actual_tlogs={name: stat(path) for name, path in logs.items()},
                  actual_link_library_stats=[stat(p) for p in actual_libraries.values()], binlog=stat(binlog),
                  CL_link_separately_owned_handle_exits=False,
                  compiler_exit_scope="Real MSBuild owner handles, per-TU sourceDependencies, original flags and actual CL/link tlogs; no invented subtool handles")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true"); parser.add_argument("--admission", required=True, type=Path)
    args = parser.parse_args(); need(args.execution_authorized, "Independent root build authorization required")
    ad, ctx = None, None
    result = dict(stage=STAGE, configuration="DebugCPU", passed=False, calls=[], solver_invocations=0,
                  program_help_invocations=0, native_invocations=0, VTK_invocations=0, SHA_scans=0,
                  historical_full_source_capture_claimed=False, old_objects_reused=0,
                  canonical_sources_or_programs_changed=False, physical_acceptance=False, following_action_launched=False)
    try:
        ad = Admission(args.admission); ctx = context(ad)
        result.update(root_admission=ad.entry, prepared=ctx["prepared"], source_prepare=ctx["prepared"],
                      source_root=str(ctx["source_root"]), authoritative_solution=stat(ctx["solution"]),
                      authoritative_project=stat(ctx["project"]), original_tlogs=ctx["original_tlogs"],
                      private_IntDir=str(ctx["intdir"]), private_output_root=str(OUTROOT))
        build(ad, ctx, result); result["consumed"] = ad.finish(); result["consumed_stats_unchanged"] = True; result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    finally:
        result["ended_utc"] = now()
        if ad is not None: result.setdefault("root_admission", ad.entry)
        result["actual_tool_call_receipts"] = [stat(p) for p in (L / (TAG + ".environment.call.json"), L / (TAG + ".msbuild.call.json")) if p.exists()]
        if not RECEIPT.exists(): write_new(RECEIPT, result)
        print(json.dumps(dict(passed=result["passed"], receipt=str(RECEIPT), failure=result.get("failure")), ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
