"""Build the authoritative CPU/GPU Debug projects into fresh isolated outputs."""
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


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def entry(path):
    path = Path(path)
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha)


def save(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    base = json.loads((LOGS / "upl_gpu_stabilizers_r1.before.json").read_text())
    assert all(entry(v["path"]) == v for v in base["canonical_programs_before"])
    source_files = sorted(p for p in (SRC / "source").iterdir() if p.suffix in (".cpp", ".h", ".cu", ".cuh"))
    assert len(source_files) == 265
    snapshot_dir = T / "outputs/upl_gpu_stabilizers_r1_source"
    snapshot = LOGS / "upl_gpu_stabilizers_r1.source.json"
    if snapshot.exists():
        # The recorded first attempt stopped in environment setup, before MSBuild.
        assert not list(LOGS.glob("upl_gpu_stabilizers_Debug*.start.json"))
        repair = json.loads((LOGS / "upl_gpu_stabilizers_build_environment_repair_r1.json").read_text())
        assert repair["actual_probe_returncode"] == 0 and repair["no_prior_MSBuild_start_records"]
        bindings = json.loads(snapshot.read_text())["files"]
        assert len(bindings) == 267
        assert all(entry(v["source"]["path"]) == v["source"] and
                   entry(v["archive"]["path"]) == v["archive"] for v in bindings)
    else:
        assert not snapshot_dir.exists()
        snapshot_dir.mkdir()
        bindings = []
        for path in source_files + [REPO / "doc/xml_format/_FmtXML_ElastoplasticSoil.xml", T.parent / "README.md"]:
            copy = snapshot_dir / path.name
            shutil.copy2(path, copy)
            original, archived = entry(path), entry(copy)
            assert original["sha256"] == archived["sha256"]
            bindings.append(dict(source=original, archive=archived))
        save(snapshot, dict(stage="upl_gpu_stabilizers_r1.source", files=bindings, source_count=265, utc=now()))
    msbuild = Path("D:/Program Files/VS2022/MSBuild/Current/Bin/amd64/MSBuild.exe")
    vs = Path("D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat")
    cmd = Path(os.environ["SystemRoot"]) / "System32/cmd.exe"
    arguments = ["/d", "/c", 'call "' + str(vs) + '" -arch=x64 -host_arch=x64 >nul && set']
    command_line = '"' + str(cmd) + '" /d /c ' + arguments[-1]
    environment = subprocess.run(command_line, capture_output=True)
    assert environment.returncode == 0, "VS environment setup failed"
    for line in environment.stdout.decode("mbcs").splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            os.environ[key] = value
    save(LOGS / "upl_gpu_stabilizers_r1.environment.json", dict(program=entry(cmd), script=entry(vs),
         arguments=arguments, owned_exit_code=environment.returncode,
         selected={k: os.environ.get(k) for k in ("VCToolsInstallDir", "WindowsSdkDir", "WindowsSDKVersion")},
         full_environment_published=False))
    recipe = json.loads((LOGS / "upl_column_public_Debug_r1.build.json").read_text(encoding="utf-8-sig"))
    old_call = json.loads(Path(recipe["project_call"]["path"]).read_text(encoding="utf-8-sig"))
    for configuration in ("DebugCPU", "Debug"):
        gpu = configuration == "Debug"
        tag = "upl_gpu_stabilizers_" + configuration + "_r1"
        output = T / "outputs" / tag
        if gpu:
            output /= "gpu"
        intermediate = (Path(tempfile.gettempdir()) / "upl_gpu_stabilizers_r1" / configuration / "int"
                        if gpu else SRC / "VS/Intermediate" / tag)
        assert not output.exists() and not intermediate.exists()
        output.mkdir(parents=True)
        intermediate.mkdir(parents=True)
        log = LOGS / (tag + ".log")
        binlog = LOGS / (tag + ".binlog")
        call_file, check_file = LOGS / (tag + ".call.json"), LOGS / (tag + ".build.json")
        assert not any(p.exists() for p in (log, binlog, call_file, check_file))
        if gpu:
            args = []
            for arg in old_call["arguments"]:
                if arg.startswith("/p:OutDir="):
                    arg = "/p:OutDir=" + output.as_posix() + "/"
                elif arg.startswith("/p:IntDir="):
                    arg = "/p:IntDir=" + intermediate.as_posix() + "/"
                elif arg.startswith("/bl:"):
                    arg = "/bl:" + str(binlog)
                args.append(arg)
            assert " " not in str(intermediate)
        else:
            args = [str(SRC / "VS/DualSPHysics5ReCpu_vs2022.sln"), "/m", "/t:Build",
                    "/p:Configuration=DebugCPU", "/p:Platform=x64", "/v:minimal",
                    "/p:OutDir=" + output.as_posix() + "/", "/p:IntDir=" + intermediate.as_posix() + "/",
                    "/bl:" + str(binlog)]
        started = now()
        with log.open("xb") as stream:
            child = subprocess.Popen([str(msbuild), *args], cwd=SRC, stdout=stream, stderr=subprocess.STDOUT)
            identity = dict(pid=child.pid, creation_time=psutil.Process(child.pid).create_time(), parent_pid=os.getpid())
            save(LOGS / (tag + ".start.json"), dict(stage=tag, program=entry(msbuild), arguments=args,
                 working_directory=str(SRC), owner=dict(pid=os.getpid(), creation_time=psutil.Process().create_time()),
                 child=identity, started_utc=started, source_snapshot=entry(snapshot),
                 canonical_programs_before=base["canonical_programs_before"]))
            print(json.dumps(dict(event="build_started", configuration=configuration, child=identity)), flush=True)
            code = child.wait()
        save(call_file, dict(stage=tag + ".call", program=entry(msbuild), arguments=args,
             working_directory=str(SRC), child=identity, started_utc=started, ended_utc=now(),
             direct_process_exit_captured=True, exit_code=code, log=entry(log)))
        unchanged = all(entry(v["source"]["path"]) == v["source"] and
                        entry(v["archive"]["path"]) == v["archive"] for v in bindings)
        canonical = all(entry(v["path"]) == v for v in base["canonical_programs_before"])
        objects = sorted(intermediate.glob("*.obj"))
        expected = 111 if gpu else 86
        program = output / ("DualSPHysics5.2_win64_debug.exe" if gpu else "DualSPHysics5.2CPU_win64_debug.exe")
        passed = code == 0 and unchanged and canonical and len(objects) == expected and program.exists()
        runtime = []
        if passed:
            for leaf in ("DsphConfig.xml", "ChronoEngine.dll", "dsphchrono.dll", "vcomp140.dll"):
                original, copy = REPO / "bin/windows" / leaf, output / leaf
                if not copy.exists():
                    shutil.copy2(original, copy)
                assert entry(original)["sha256"] == entry(copy)["sha256"]
                runtime.append(entry(copy))
        save(check_file, dict(stage=tag, passed=passed, configuration=configuration, source_snapshot=entry(snapshot),
             owned_call=entry(call_file), exit_code=code, program=entry(program) if program.exists() else None,
             object_count=len(objects), expected_object_count=expected, objects=[entry(q) for q in objects],
             source_bindings_unchanged=unchanged, canonical_programs_unchanged=canonical, runtime=runtime,
             authoritative_solution=True, default_CPU_Debug_configuration=not gpu, isolated_output_override=True,
             physical_acceptance=False, solver_or_component_invoked=False))
        print(json.dumps(dict(event="build_finished", configuration=configuration, passed=passed,
              exit_code=code, objects=len(objects), receipt=str(check_file))), flush=True)
        if not passed:
            raise RuntimeError("Build rejected; preserve log and outputs: " + str(check_file))


if __name__ == "__main__":
    main()
