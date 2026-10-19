"""Fresh case-02 CPU/GPU production-step run with original safety limits."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace
import numpy as np

import hg_release_run as release
from mdbc_gpu_vector_run import TESTS, bound, read, verify


class Safety:
    def __init__(self, path):
        self.path, self.stream, self.pending, self.header = path, None, "", False
        self.frames, self.last_time, self.max_stress, self.max_gap = 0, None, 0., 0.
        self.initial = None
        self.max_dx = self.max_span = self.max_load_error = 0.

    def observe(self, a):
        assert a.shape == (1000, 23) and np.isfinite(a).all() and np.array_equal(a[:, 2], np.arange(40, 1040))
        assert np.all(a[:, 0] == a[0, 0]) and np.all(a[:, 1] == a[0, 1])
        assert np.all(a[:, 9] > 0) and np.all(a[:, 17] == 0)
        t = float(a[0, 0])
        assert self.last_time is None or t > self.last_time
        if self.initial is None:
            self.initial = a[:, [3, 5]].copy()
        dx = (a[:, 3] - self.initial[:, 0] + .05) % .1 - .05
        lateral = float(np.max(abs(dx)) * 1000)
        span = float(np.max(np.ptp(a[:, 5].reshape(10, 100), axis=0)) * 1000)
        self.max_dx, self.max_span = max(self.max_dx, lateral), max(self.max_span, span)
        if not np.all(a[:, 5] > 0) or lateral >= .5 or span >= .5:
            raise RuntimeError(f"Original geometry/wall-crossing guard failed at {t:.17g} s")
        self.frames += 1
        self.last_time = t
        if t >= .1 - 1e-7:
            total = (a[:, 10] - a[:, 13]).reshape(10, 100).mean(axis=0)
            error, gap = float(np.max(np.abs(total - 10000))), float(abs(total[-1] - total[-2]))
            self.max_stress, self.max_gap = max(self.max_stress, error), max(self.max_gap, gap)
            load_error = float(abs(.21 * a[:, 18].sum() + 1000))
            self.max_load_error = max(self.max_load_error, load_error)
            top = np.arange(99, 1000, 100)
            expected = np.zeros(1000)
            expected[top] = 1
            if error > 100 or gap > 100 or load_error >= .001 or not np.array_equal(a[:, 21], expected) or np.any(a[top, 10] != 0):
                raise RuntimeError(f"Original stress/load/drainage guard failed at {t:.17g} s: {error:.9g}/{gap:.9g} Pa, load {load_error:.9g} N/m")

    def poll(self):
        if self.stream is None:
            if not self.path.exists():
                return
            self.stream = self.path.open(encoding="utf8")
        self.pending += self.stream.read()
        if not self.header and "\n" in self.pending:
            first, self.pending = self.pending.split("\n", 1)
            assert first.startswith("time_s,step,stage,id,")
            self.header = True
        while self.pending.count("\n") >= 1000:
            lines = self.pending.split("\n", 1000)
            text, self.pending = "\n".join(lines[:1000]), lines[1000]
            a = np.fromstring(text.replace(",full_step,", ",").replace("\n", ","), sep=",").reshape(1000, 23)
            self.observe(a)

    def summary(self):
        return dict(frames=self.frames, last_time_s=self.last_time,
                    max_post01_layer_total_stress_error_pa=self.max_stress,
                    max_post01_top_layer_gap_pa=self.max_gap, limits_pa=100,
                    max_periodic_dx_mm=self.max_dx, max_layer_z_span_mm=self.max_span,
                    max_post01_load_error_N_m=self.max_load_error)


def prepare(args):
    base = release.base
    base.CHANGED_PARAMETERS.update(("SoilBoundaryDerivativeSPR", "SoilDampingCoef", "HydroMechDrainageFixedGrid"))
    base.signature, base.render = release.signature, release.render
    s = base.settings(SimpleNamespace(name=args.name, dt=args.dt, duration=args.duration, output_interval=args.interval,
                                     xi=.1, top_mode=5, engine=args.backend + "_production_step", threads=1, save=int(args.save)))
    s.update(spr=1, event_grid=1, damping_text="0.04")
    prefix, record = base.prepare(s, True)
    bat = TESTS / "configs" / ("xCaseTCq0_" + args.name + "_win64_" + args.backend.upper() + ".bat")
    if not bat.exists():
        command = f'"D:\\Anaconda3\\python.exe" -B "..\\support\\gpu_coupled_run.py" --name {args.name} --duration {args.duration} --dt {args.dt} --interval {args.interval} --build "{Path(args.build).resolve()}"'
        command += " --backend " + args.backend
        if args.save:
            command += " --save"
        command += " --run"
        with bat.open("x", encoding="ascii", newline="\r\n") as stream:
            stream.write('@echo off\nsetlocal EnableDelayedExpansion\npushd "%~dp0"\n\n'
                         'rem Fresh production-step diagnostic; existing output is protected.\n' + command + '\n'
                         'if not "%ERRORLEVEL%" == "0" goto fail\npopd\nexit /b 0\n\n:fail\npopd\nexit /b 1\n')
    return s, prefix, record, bat


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", required=True)
    p.add_argument("--duration", required=True)
    p.add_argument("--dt", default="0.00001")
    p.add_argument("--interval", default="0.001")
    p.add_argument("--build", required=True)
    p.add_argument("--backend", choices=("gpu", "cpu"), default="gpu")
    p.add_argument("--save", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    build = read(args.build)
    if args.backend == "gpu":
        assert build["built"] and build["fixture"] == "gpu_coupled"
        executable = build["executable"]
        executable_hash = build["executable_sha256"]
    else:
        assert build["status"] == "built_not_run" and build["configuration"] == "ReleaseCPU"
        assert build["production_build_confirmed"]
        executable = next(e["path"] for e in build["runtime"] if Path(e["path"]).name == "mechanics.exe")
        executable_hash = build["exe_sha256"]
    s, prefix, prepared, bat = prepare(args)
    if not args.run:
        print(json.dumps(dict(status="prepared_not_run", settings=s, prefix=str(prefix)), indent=2))
        return
    output, receipt = TESTS / "outputs" / args.name, TESTS / "logs" / (args.name + ".run.json")
    if output.exists() or receipt.exists():
        raise FileExistsError("Retained output or run receipt exists")
    inputs = build["inputs"] + build.get("resolved_compile_link_inputs", []) + build["runtime"] + prepared["inputs"] + [bound(args.build), bound(__file__), bound(bat),
               bound(Path(release.__file__)), bound(Path(release.base.__file__)), dict(path=executable, sha256=executable_hash)]
    verify(inputs)
    argv = [executable, str(s["steps"]), str(s["stride"]), str(int(args.save)), "-gpu:0" if args.backend == "gpu" else "-cpu", "-stable", "-ompthreads:1",
            "-mdbc", str(prefix), str(output), "-dirdataout", "data", "-svres:1", "-saveposdouble:1"]
    report = dict(passed=False, status="running", settings=s, inputs=inputs, argv=argv, output=str(output),
                  started_utc=datetime.now(timezone.utc).isoformat(), production_step_used=True, physical_acceptance=False)
    # This is a run receipt; status updates are atomic and limited to this fresh run.
    def publish():
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf8")
        for attempt in range(6):
            try:
                temporary.replace(receipt)
                return
            except PermissionError:
                if attempt == 5:
                    # A transient status-reader lock is not a physical failure.
                    # Leave the complete temporary receipt for later audit.
                    print("Status replace blocked; retained " + str(temporary), flush=True)
                    return
                time.sleep(.2)
    publish()
    stdout, stderr = [TESTS / "logs" / (args.name + suffix) for suffix in (".stdout.log", ".stderr.log")]
    checker, child = Safety(output / "state.csv"), None
    failure = None
    try:
        started = time.perf_counter()
        with stdout.open("xb") as out, stderr.open("xb") as err:
            child = subprocess.Popen(argv, cwd=Path(executable).parent, stdout=out, stderr=err,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            report["pid"] = child.pid
            publish()
            while child.poll() is None:
                checker.poll()
                report["safety"] = checker.summary()
                publish()
                time.sleep(5)
            report["exit_code"] = child.returncode
        checker.poll()
        report.update(wall_seconds=time.perf_counter() - started, safety=checker.summary(), owned_process_exited=True)
        if child.returncode != 0:
            raise RuntimeError(f"{args.backend} production-step harness exit {child.returncode}; inspect stderr/Run.out")
        complete = read(output / "complete.json")
        assert complete["steps"] == s["steps"] and complete["dt"] == s["dt"]
        if args.backend == "gpu":
            assert complete["completed"]
            lifecycle = complete
        else:
            assert complete["mode"] == "production_symplectic" and complete["normal_soil"] == 1000
            hg = read(output / "hourglass_complete.json")
            lifecycle = dict(max_dt_over_tau=hg["max_dt_over_hg_tau"], spin_bound=hg["integrated_max_skew_rad"],
                             force_calls=hg["hg_force_calls"], rate_calls=hg["hg_rate_calls"])
            report["cpu_hourglass_completion"] = hg
        assert complete["sampled_frames"] == checker.frames == 1 + math.ceil(s["steps"] / s["stride"])
        assert abs(complete["final_time"] - s["steps"] * s["dt"]) < max(1e-10, 2e-9 * s["duration_s"])
        assert lifecycle["max_dt_over_tau"] <= .2 and lifecycle["spin_bound"] < .01
        assert lifecycle["force_calls"] == lifecycle["rate_calls"] == 2 * s["steps"]
        assert complete["max_fixed_dt_minus_mechanical_limit_s"] <= 0
        verify(inputs)
        report.update(passed=True, status="completed_safety_passed_pending_comparison", completion=complete)
    except Exception as error:
        failure = error
        report.update(status="rejected_or_interrupted", reason=str(error), safety=checker.summary())
    finally:
        if child is not None:
            if child.poll() is None:
                child.kill()
                child.wait()
            report.update(exit_code=child.returncode, owned_process_exited=child.poll() is not None)
        if checker.stream:
            checker.stream.close()
        report["outputs"] = [bound(f) for f in (stdout, stderr) if f.exists()] + [bound(f) for f in output.rglob("*") if f.is_file()]
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        publish()
    print(json.dumps(dict(receipt=str(receipt), passed=report["passed"], safety=report["safety"], reason=report.get("reason")), indent=2))
    if failure:
        raise failure


if __name__ == "__main__":
    main()
