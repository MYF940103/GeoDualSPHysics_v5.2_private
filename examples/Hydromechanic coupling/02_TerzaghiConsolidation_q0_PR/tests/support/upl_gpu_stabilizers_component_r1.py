"""Link two retained-style HG fixtures to the fresh authoritative GPU Debug objects."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import psutil

T = Path(__file__).resolve().parents[1]
REPO, LOGS = T.parents[3], T / "logs"


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
    build_path = LOGS / "upl_gpu_stabilizers_Debug_r1.build.json"
    build = json.loads(build_path.read_text())
    assert build["passed"] and build["object_count"] == 111 and build["canonical_programs_unchanged"]
    objects = [v for v in build["objects"] if Path(v["path"]).name != "main.obj"]
    assert len(objects) == 110 and all(entry(v["path"]) == v for v in objects)
    recipe = json.loads((LOGS / "upl_column_public_Debug_r1.build.json").read_text(encoding="utf-8-sig"))
    libraries = recipe["libraries"]
    assert len(libraries) == 6 and all(entry(v["path"]) == v for v in libraries)
    output = T / "outputs/upl_hg_gpu_checks_Debug_r1"
    assert not output.exists()
    output.mkdir()
    vs = "D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat"
    env = subprocess.run('"' + str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe") +
                         '" /d /c call "' + vs + '" -arch=x64 -host_arch=x64 >nul && set', capture_output=True)
    assert env.returncode == 0
    for line in env.stdout.decode("mbcs").splitlines():
        key, sep, value = line.partition("=")
        if key and sep:
            os.environ[key] = value
    compiler, linker = shutil.which("cl.exe"), shutil.which("link.exe")
    cuda = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7")
    sanitizer = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.3/compute-sanitizer/compute-sanitizer.exe")
    assert compiler and linker and sanitizer.exists()
    sources = [T / "support/upl_hg_gpu_j_r1.cpp", T / "support/hg_gpu_hourglass_test.cpp",
               T / "support/upl_hg_cpu_oracle_r2.cpp", T / "notes/upl_hg_gpu_j_r1.json"]
    inputs = [entry(build_path), *[entry(p) for p in sources], *libraries, *objects]
    calls = []

    def call(label, arguments):
        log, receipt = LOGS / (label + ".log"), LOGS / (label + ".call.json")
        assert not log.exists() and not receipt.exists()
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with log.open("xb") as stream:
            process = subprocess.Popen(arguments, cwd=output, stdout=stream, stderr=subprocess.STDOUT)
            identity = dict(pid=process.pid, creation_time=psutil.Process(process.pid).create_time())
            code = process.wait()
        result = dict(stage=label, program=entry(arguments[0]), arguments=arguments[1:], working_directory=str(output),
                      child=identity, started_utc=started, ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      direct_process_exit_captured=True, exit_code=code, log=entry(log))
        save(receipt, result)
        calls.append(entry(receipt))
        print(json.dumps(dict(stage=label, exit_code=code, receipt=str(receipt))), flush=True)
        assert code == 0, "Component invocation failed: " + str(receipt)

    executables = []
    system = [name + ".lib" for name in ("kernel32", "user32", "gdi32", "winspool", "comdlg32", "advapi32",
              "shell32", "ole32", "oleaut32", "uuid", "odbc32", "odbccp32")]
    for source in sources[:2]:
        label = source.stem + "_Debug_r1"
        obj, exe = output / (source.stem + ".obj"), output / (source.stem + ".exe")
        args = [compiler, "/nologo", "/c", "/std:c++17", "/EHsc", "/W3", "/openmp", "/fp:precise", "/DWIN32",
                "/D_CONSOLE", "/D_MBCS", "/D_WITHGPU", "/Od", "/MTd", "/Zi", "/RTC1",
                "/I" + str(REPO / "src/source"), "/I" + str(cuda / "include"), "/Fo" + str(obj),
                "/Fd" + str(output / (source.stem + ".pdb")), str(source)]
        call(label + ".compile", args)
        call(label + ".link", [linker, "/NOLOGO", "/MACHINE:X64", "/SUBSYSTEM:CONSOLE", "/DEBUG",
             "/OUT:" + str(exe), "/PDB:" + str(output / (source.stem + "_link.pdb")), str(obj),
             *[v["path"] for v in objects], *[v["path"] for v in libraries], *system])
        executables.append(exe)
    for runtime in build["runtime"]:
        copy = output / Path(runtime["path"]).name
        shutil.copy2(runtime["path"], copy)
        assert entry(copy)["sha256"] == runtime["sha256"]
    results = []
    for exe in executables:
        result = LOGS / (exe.stem + "_Debug_r1.check.json")
        assert not result.exists()
        call(exe.stem + "_Debug_r1.run", [str(exe), "--json", str(result)])
        assert json.loads(result.read_text())["passed"]
        results.append(entry(result))
    result = LOGS / "upl_hg_gpu_j_Debug_r1.memcheck.json"
    memlog = LOGS / "upl_hg_gpu_j_Debug_r1.memcheck.log"
    assert not result.exists() and not memlog.exists()
    call("upl_hg_gpu_j_Debug_r1.memcheck", [str(sanitizer), "--tool", "memcheck", "--error-exitcode", "86",
         "--log-file", str(memlog), str(executables[0]), "--json", str(result)])
    assert json.loads(result.read_text())["passed"] and "ERROR SUMMARY: 0 errors" in memlog.read_text()
    results.extend([entry(result), entry(memlog)])
    assert all(entry(v["path"]) == v for v in inputs)
    save(LOGS / "upl_gpu_stabilizers_component_r1.check.json", dict(stage="upl_gpu_stabilizers_component_r1",
         passed=True, physical_acceptance=False, solver_invoked=False, source_build=entry(build_path), inputs=inputs,
         calls=calls, results=results, executables=[entry(p) for p in executables],
         current_J_and_separate_legacy_NULL_J_executed=True, GPU_memcheck_zero_errors=True, bindings_unchanged=True))


if __name__ == "__main__":
    main()
