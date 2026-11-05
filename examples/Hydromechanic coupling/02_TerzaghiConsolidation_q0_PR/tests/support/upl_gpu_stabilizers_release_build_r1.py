"""One fresh authoritative GPU Release build; stat checks and one final-exe hash."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import psutil

T = Path(__file__).resolve().parents[1]
REPO = T.parents[3]
SRC, LOGS = REPO / "src", T / "logs"
TAG = "upl_gpu_stabilizers_Release_r1"
CHECKPOINT = "295261305527e1d8b2fb76a3eb8d650bf3275a2b"
BASELINE = {}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def stat(path):
    path = Path(path).resolve()
    value = path.stat()
    assert path.is_file(), str(path)
    return dict(path=str(path), bytes=value.st_size, mtime_ns=value.st_mtime_ns)


def remember(path):
    value = stat(path)
    BASELINE[value["path"]] = value
    return value


def save(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def read(path):
    remember(path)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main():
    output = T / "outputs" / TAG / "gpu"
    intermediate = Path(tempfile.gettempdir()) / "upl_gpu_stabilizers_r1/Release/int"
    paths = {key: LOGS / (TAG + suffix) for key, suffix in (("start", ".start.json"), ("call", ".call.json"),
             ("check", ".build.json"), ("log", ".log"), ("binlog", ".binlog"))}
    assert " " not in str(intermediate) and not output.parent.exists() and not intermediate.exists()
    assert not any(path.exists() for path in paths.values())
    debug = read(LOGS / "upl_gpu_stabilizers_Debug_r1.build.json")
    recipe = read(LOGS / "upl_gpu_column_Release_r1_project.call.json")
    source = read(LOGS / "upl_gpu_stabilizers_r1.source.json")
    canonical = read(LOGS / "upl_gpu_stabilizers_r1.before.json")["canonical_programs_before"]
    assert debug["passed"] and debug["configuration"] == "Debug" and debug["exit_code"] == 0
    assert type(recipe["exit_code"]) is int and recipe["exit_code"] == 0
    assert source["source_count"] == 265 and len(source["files"]) == 267
    # This remains a historical receipt. Current compilation is bound to the
    # root-verified checkpoint and before/after source size/mtime, not a rehash.
    source_stats = [remember(item["source"]["path"]) for item in source["files"]]
    actual = sorted(str(p.resolve()) for p in (SRC / "source").iterdir() if p.suffix in (".cpp", ".h", ".cu", ".cuh"))
    assert actual == sorted(item["path"] for item in source_stats if Path(item["path"]).parent == SRC / "source")
    canonical_stats = [remember(item["path"]) for item in canonical]
    solution = SRC / "VS/DualSPHysics5Re.sln"
    for path in (solution, SRC / "VS/DualSPHysics5Re.vcxproj", Path(__file__), T / "notes/upl_gpu_stabilizers_release_build_r1.json"):
        remember(path)
    msbuild = Path(recipe["program"]["path"])
    vs = Path("D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat")
    cmd = Path(os.environ["SystemRoot"]) / "System32/cmd.exe"
    for path in (msbuild, vs, cmd):
        remember(path)
    # Reuse the repaired trusted CALL quoting, solely to obtain the VS environment.
    environment_command = '"' + str(cmd) + '" /d /c call "' + str(vs) + '" -arch=x64 -host_arch=x64 >nul && set'
    setup = subprocess.run(environment_command, capture_output=True)
    setup_exit = setup.returncode
    assert type(setup_exit) is int and setup_exit == 0, "VS environment setup failed"
    env = os.environ.copy()
    for line in setup.stdout.decode("mbcs").splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            env[key] = value
    env["CUDA_PATH_V11_7"] = "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7"
    args = []
    for arg in recipe["arguments"]:
        if arg.startswith("/p:Configuration="): arg = "/p:Configuration=Release"
        elif arg.startswith("/p:OutDir="): arg = "/p:OutDir=" + output.as_posix() + "/"
        elif arg.startswith("/p:IntDir="): arg = "/p:IntDir=" + intermediate.as_posix() + "/"
        elif arg.startswith("/bl:"): arg = "/bl:" + str(paths["binlog"])
        args.append(arg)
    assert Path(args[0]) == solution
    assert all(flag in args for flag in ("/m:1", "/nr:false", "/t:Rebuild", "/p:Configuration=Release", "/p:Platform=x64",
               "/p:PlatformToolset=v143", "/p:VCToolsVersion=14.36.32532", "/p:BuildProjectReferences=false", "/p:PostBuildEventUseInBuild=false"))
    runtime_sources = []
    for item in debug["runtime"]:
        original = remember(REPO / "bin/windows" / Path(item["path"]).name)
        old_copy = remember(item["path"])
        assert original["bytes"] == item["bytes"] and all(original[key] == old_copy[key] for key in ("bytes", "mtime_ns"))
        runtime_sources.append((original, item["sha256"]))
    assert len(runtime_sources) == 4
    output.mkdir(parents=True); intermediate.mkdir(parents=True)
    me = psutil.Process()
    owner = dict(pid=me.pid, creation_time=me.create_time(), exe=me.exe(), command=me.cmdline(), cwd=me.cwd())
    command, started = [str(msbuild), *args], now()
    with paths["log"].open("xb") as stream:
        child = subprocess.Popen(command, cwd=SRC, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        identity = dict(pid=child.pid, creation_time=psutil.Process(child.pid).create_time(), parent_pid=os.getpid())
        common = dict(owner=owner, child=identity, program_stat=stat(msbuild), arguments=args,
                      command_line=subprocess.list2cmdline(command), working_directory=str(SRC), started_utc=started)
        save(paths["start"], dict(stage=TAG + ".start", **common, root_verified_checkpoint=CHECKPOINT,
             environment_setup=dict(command=environment_command, original_typed_exit_code=setup_exit,
                 selected={key: env.get(key) for key in ("VCToolsInstallDir", "WindowsSDKVersion", "CUDA_PATH_V11_7")})))
        print(json.dumps(dict(event="Release_build_started", child=identity)), flush=True)
        code = child.wait()
    save(paths["call"], dict(stage=TAG + ".call", **common, ended_utc=now(),
         direct_process_exit_captured=True, exit_code=code, log_stat=stat(paths["log"])))
    objects = sorted(intermediate.glob("*.obj"))
    program, sealed, runtime, failure = output / "DualSPHysics5.2_GEO_win64.exe", None, [], None
    try:
        assert type(code) is int and code == 0 and len(objects) == 111 and program.is_file(), "Release build/output/count failed"
        for original, old_sha in runtime_sources:
            copy = output / Path(original["path"]).name
            assert not copy.exists(), str(copy)
            shutil.copy2(original["path"], copy)
            copied = stat(copy)
            assert all(copied[key] == original[key] for key in ("bytes", "mtime_ns"))
            runtime.append(dict(**copied, reused_sha256=old_sha, fresh_hash_performed=False, source_stat=original))
        assert all(stat(path) == before for path, before in BASELINE.items()), "Consumed/protected file stat changed"
        sealed = stat(program)
        with program.open("rb") as stream:  # Sole content digest: the final newly generated executable, once.
            sealed["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        assert stat(program) == {key: sealed[key] for key in ("path", "bytes", "mtime_ns")}
    except Exception as exc:
        failure = type(exc).__name__ + ": " + str(exc)
    changed = [path for path, before in BASELINE.items() if stat(path) != before]
    passed = failure is None and not changed
    save(paths["check"], dict(stage=TAG, passed=passed, configuration="Release", root_verified_checkpoint=CHECKPOINT,
         authoritative_solution=str(solution), isolated_GPU_OutDir=str(output), no_space_IntDir=str(intermediate),
         source_snapshot=debug["source_snapshot"], source_snapshot_fresh_hash_performed=False,
         source_stat_before=source_stats, consumed_stats_before=list(BASELINE.values()), changed_paths=changed,
         source_and_consumed_stats_unchanged=not changed, canonical_program_stats_before=canonical_stats,
         canonical_program_stats_unchanged=all(stat(item["path"]) == item for item in canonical_stats),
         owned_call_stat=stat(paths["call"]), exit_code=code, program=sealed, object_count=len(objects),
         expected_object_count=111, object_names=[path.name for path in objects], runtime=runtime,
         fresh_hash_scope="Only final new Release executable once; all other checks size/mtime; closed hashes are historical",
         physical_acceptance=False, solver_or_component_invoked=False, canonical_program_installed=False, failure=failure))
    print(json.dumps(dict(event="Release_build_finished", passed=passed, exit_code=code, object_count=len(objects), receipt=str(paths["check"]))), flush=True)
    if not passed:
        raise RuntimeError("Release build rejected; preserve outputs and original call")


if __name__ == "__main__":
    main()
