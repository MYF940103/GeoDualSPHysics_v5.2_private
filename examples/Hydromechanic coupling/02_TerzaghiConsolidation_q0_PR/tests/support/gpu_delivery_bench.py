"""Serial CPU/GPU production timing: one warmup and three alternating pairs."""
import csv
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import re
import statistics
import subprocess
import time
from mdbc_gpu_vector_run import TESTS, bound, read, verify


def main():
    tag = "gpu_delivery_bench_r1"
    receipt = TESTS / "logs" / (tag + ".check.json")
    assert not receipt.exists()
    repo = TESTS.parents[3]
    executables = dict(cpu=repo / "bin/windows/DualSPHysics5.2CPU_win64.exe",
                       gpu=repo / "bin/windows/DualSPHysics5.2_GEO_win64.exe")
    prefix = TESTS / "outputs/gpu_spr_015_c_r1_input/CaseTCq0_gpu_spr_015_c_r1"
    inputs = [bound(p) for p in [Path(__file__), *executables.values(), prefix.with_suffix(".xml"),
              prefix.with_suffix(".bi4"), prefix.with_name(prefix.name + "_Normals.nbi4"),
              *executables["cpu"].parent.glob("*.dll")]]
    args = ["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*','gpu_coupled' -ErrorAction SilentlyContinue).Count"]
    assert subprocess.check_output(args, text=True).strip() == "0"
    verify(inputs)
    set_affinity = ctypes.windll.kernel32.SetProcessAffinityMask
    set_affinity.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
    set_affinity.restype = wintypes.BOOL
    plan = [(True, "cpu"), (True, "gpu"), (False, "cpu"), (False, "gpu"),
            (False, "gpu"), (False, "cpu"), (False, "cpu"), (False, "gpu")]
    result = dict(passed=False, inputs=inputs, runs=[], pinned_logical_cpu=0, physical_steps=3000,
                  dt_s=1e-5, save_fields=False, physical_accuracy_test=False)
    try:
        for index, (warm, backend) in enumerate(plan):
            name = f"{tag}_{index:02d}_{backend}"
            output = TESTS / "outputs" / name
            stdout, stderr = [TESTS / "logs" / (name + suffix) for suffix in (".stdout.log", ".stderr.log")]
            assert not output.exists()
            argv = [str(executables[backend]), "-cpu" if backend == "cpu" else "-gpu:0", "-stable", "-ompthreads:1", "-mdbc",
                    "-nsteps:3000", "-sv:none", "-svres:1", str(prefix), str(output), "-dirdataout", "data"]
            run = dict(backend=backend, warmup=warm, argv=argv, completed=False)
            result["runs"].append(run)
            with stdout.open("xb") as out, stderr.open("xb") as err:
                started = time.perf_counter()
                child = subprocess.Popen(argv, cwd=executables[backend].parent, stdout=out, stderr=err,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                run["pid"] = child.pid
                try:
                    assert set_affinity(wintypes.HANDLE(int(child._handle)), 1)
                    run["exit_code"] = child.wait(timeout=300)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait()
                run["owned_process_exited"] = child.poll() is not None
                run["wall_seconds"] = time.perf_counter() - started
            assert child.returncode == 0
            text = (output / "Run.out").read_text(errors="replace")
            with (output / "Run.csv").open(encoding="utf-8-sig") as stream:
                table = list(csv.DictReader(stream, delimiter=";"))
            assert len(table) == 1
            summary = table[0]
            assert int(summary["Steps"]) == 3000 and int(summary["Np"]) == 1040 and int(summary["PartsOut"]) == 0
            assert "Finished execution (code=0)." in text and "MirroredWallDerivatives" in text and "TopKernelBand" in text
            counts = re.search(r"forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
            assert counts and tuple(map(int, counts.groups())) == (6000, 3000, 3000, 6000)
            run.update(completed=True, loop_seconds=float(summary["TSimul"]), summary=summary,
                       outputs=[bound(p) for p in (stdout, stderr)] + [bound(p) for p in output.rglob("*") if p.is_file()])
            print(f"{name}: loop={run['loop_seconds']:.6f} s, wall={run['wall_seconds']:.6f} s", flush=True)
        verify(inputs)
        medians = {b: statistics.median(r["loop_seconds"] for r in result["runs"] if r["backend"] == b and not r["warmup"]) for b in executables}
        result.update(passed=True, medians_seconds=medians, cpu_over_gpu_speed_ratio=medians["cpu"] / medians["gpu"],
                      loop_ranges_seconds={b: [min(r["loop_seconds"] for r in result["runs"] if r["backend"] == b and not r["warmup"]),
                                               max(r["loop_seconds"] for r in result["runs"] if r["backend"] == b and not r["warmup"])] for b in executables},
                      limitations="Short 1000-soil-particle case only. No field output/CSV sampling. Not a full-run speedup, CPU-thread scaling or large-model benchmark.")
    finally:
        with receipt.open("x", encoding="utf8") as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps(dict(medians=medians, cpu_over_gpu_speed_ratio=result["cpu_over_gpu_speed_ratio"]), indent=2))


if __name__ == "__main__":
    main()
