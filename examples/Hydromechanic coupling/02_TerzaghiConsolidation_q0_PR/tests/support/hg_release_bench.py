"""Fresh old/new CPU production-loop benchmark; no SPR or event-policy change.

One .01-s warmup per binary, then .03-s AB/BA/AB batches, identical output policy.
Each pair must have byte-identical native, HG and sampled physical states. This
does not replace physical acceptance or establish a full-2Tv speedup.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import psutil
import hg_merge_run as base
import hg_bd_d04_15_r2 as retained

TESTS = base.TESTS
OLD, NEW = "hg_m1rel", "hg_release_rel_r3"
PHYSICAL_FILES = ("initial_state.bin", "final_state.bin", "initial_state.csv", "final_state.csv",
                  "state.csv", "hourglass_final.csv", "hourglass.csv")
DTYPE = np.dtype([("id", "<u4"), *[(k, "<f8") for k in ("x", "y", "z")],
    *[(k, "<f4") for k in ("vx", "vy", "vz", "rho", "pressure", "pressure0")],
    *[("sigma_"+k, "<f8") for k in ("xx", "yy", "zz", "xy", "yz", "xz")], ("kplastic", "<f4")])


def stages(tag, new_binary_label=NEW):
    result = [("warm", "old", ".01"), ("warm", "new", ".01")]
    for batch, order in enumerate((("old", "new"), ("new", "old"), ("old", "new")), 1):
        result.extend((f"b{batch}", role, ".03") for role in order)
    return [dict(batch=batch, role=role, duration=duration, name=f"{tag}_{batch}_{role}",
                 binary_label=OLD if role == "old" else new_binary_label) for batch, role, duration in result]


def arguments(stage):
    return SimpleNamespace(name=stage["name"], duration=stage["duration"], dt="0.00001",
        output_interval=stage["duration"], xi=.1, top_mode=5, engine="wrapper",
        binary_label=stage["binary_label"], exe=None, build_record=None, threads=1, save=0)


def fresh(stage):
    name = stage["name"]
    paths = [TESTS/f"outputs/{name}", TESTS/f"outputs/{name}_input", TESTS/f"configs/CaseTCq0_{name}_Def.xml"]
    paths += list((TESTS/"logs").glob(name+".*"))
    base.require(not any(p.exists() for p in paths), f"Existing evidence for {name}; use a fresh benchmark tag")


def quiet_machine():
    """Reject competing known solver/build benchmarks, never kill unrelated work."""
    busy = []
    for process in psutil.process_iter(["pid", "name"]):
        name = (process.info["name"] or "").lower()
        if name in {"cl.exe", "link.exe", "msbuild.exe", "hg_cpu_cache_test.exe", "mechanics.exe"} or name.startswith("dualsphysics"):
            busy.append(process.info)
    base.require(not busy, f"Competing solver/compiler/benchmark process: {busy}")


def preflight(tag, new_binary_label=NEW):
    plan = stages(tag, new_binary_label)
    inputs = [base.entry(Path(__file__)), base.entry(Path(base.__file__)), base.entry(Path(retained.__file__))]
    binaries = {}
    for role, label in (("old", OLD), ("new", new_binary_label)):
        args = arguments(next(s for s in plan if s["role"] == role))
        exe, runtime = base.runtime_inputs(args)
        record = TESTS/f"logs/mech_bin_{label}.build.json"
        build = base.load(record)
        base.require(build["configuration"] == "ReleaseCPU", role+": benchmark requires ReleaseCPU")
        # The retained old executable is authoritative. Do not compare its old
        # source/object paths to today's files or rewrite its provenance.
        inputs.extend(runtime)
        if role == "new":
            for item in build["inputs"]+build["resolved_compile_link_inputs"]:
                base.require(base.sha(item["path"]) == item["sha256"].lower(), "Changed new-build input: "+item["path"])
                inputs.append(base.entry(item["path"]))
        binaries[role] = dict(executable=str(exe), build_record=base.entry(record),
            executable_sha256=base.sha(exe), provenance="retained build/runtime" if role == "old" else "current build inputs and runtime verified")
    base.compare_initial(base.NATIVE_INITIAL)
    for stage in plan:
        fresh(stage)
        args = arguments(stage); settings = base.settings(args)
        _, prepared = base.prepare(settings, False)
        inputs.extend(prepared["frozen_source_inputs"])
        inputs.extend((prepared["template"], prepared["snapshot"]))
        root = ET.fromstring(base.render(base.TEMPLATE.read_text(encoding="utf-8-sig"), settings))
        parameters = {p.get("key"): p.get("value") for p in root.findall("execution/parameters/parameter")}
        base.require(Decimal(parameters["SoilDampingCoef"]) == Decimal(".02"), "Benchmark damping must remain .02")
        base.require(parameters.get("SoilDamping") == "1", "Retained damping flag changed")
        base.require("SoilBoundaryDerivativeSPR" not in parameters and "HydroMechDrainageFixedGrid" not in parameters,
                     "Do not introduce new XML controls in the default-off regression")
    inputs.append(base.entry(base.NATIVE_INITIAL))
    return dict(stages=plan, binaries=binaries, inputs=list({e["path"]: e for e in inputs}.values()),
        dt=1e-5, damping=.02, xi=.1, threads=1, save=0, spr=False, fixed_grid=False,
        benchmark_process_cpu_affinity=psutil.Process().cpu_affinity(),
        acceptance_rule="Every retained physical artifact byte-identical; both timing medians improve >5% and new maximum < old minimum")


def unchanged(inputs):
    changed = [e["path"] for e in inputs if not Path(e["path"]).is_file() or base.sha(e["path"]) != e["sha256"].lower()]
    base.require(not changed, f"Benchmark inputs changed: {changed}")


def audit(stage):
    name = stage["name"]; out = TESTS/f"outputs/{name}"
    manifest = TESTS/f"logs/{name}.run.json"; run = base.load(manifest)
    base.require(run["completion_valid"] and run["inputs_unchanged"] and run["exit_code"] == 0
                 and run["status"] == "completed_pending_physical_acceptance", name+": run incomplete")
    unchanged(run["inputs"]+run["outputs"])
    complete = base.load(out/"complete.json"); hg = base.load(out/"hourglass_complete.json")
    base.require(complete == run["completion"] and hg == run["hourglass"], name+": raw/embedded completion mismatch")
    steps = int(Decimal(stage["duration"])/Decimal(".00001"))
    base.require(complete["steps"] == complete["native_step_calls"] == complete["stride"] == steps
        and complete["dt"] == 1e-5 and complete["xi"] == .1 and complete["top_load_mode"] == 5
        and complete["stress_grad_corr"] and complete["normal_soil"] == 1000 and complete["initial_time"] == 0
        and not complete["save_parts"] and complete["sampled_frames"] == 2
        and abs(complete["final_time"]-float(stage["duration"])) < 1e-10
        and not complete["physical_configuration_overridden"], name+": runtime controls or actual endpoint mismatch")
    base.require(hg["hg_rate_calls"] == hg["hg_force_calls"] == hg["hg_updates"] == 2*steps
        and hg["predictor_updates"] == hg["corrector_updates"] == hg["endpoint_rate_calls"] == hg["predictor_rate_calls"] == steps,
        name+": incomplete HG history")
    base.require(complete["max_fixed_dt_minus_mechanical_limit_s"] <= 0 and complete["pore_dt_limit_s"] >= 1e-5
        and 0 <= hg["integrated_max_skew_rad"] < .01 and 0 <= hg["max_dt_over_hg_tau"] <= .2,
        name+": original time-scale/rotation guard failed")
    recorded = {str(Path(e["path"]).resolve()) for e in run["outputs"]}
    for file in PHYSICAL_FILES:
        base.require(str((out/file).resolve()) in recorded, name+": unrecorded physical artifact "+file)
    for stem in ("initial", "final"):
        data = np.fromfile(out/f"{stem}_state.bin", dtype=DTYPE)
        base.require(DTYPE.itemsize == 104 and len(data) == 1040 and np.array_equal(data["id"], np.arange(1040)), name+": native binary IDs")
        csv = pd.read_csv(out/f"{stem}_state.csv", float_precision="round_trip")
        base.require(np.array_equal(csv.id, data["id"]), name+": native CSV IDs")
        for field in DTYPE.names[1:]:
            base.require(np.isfinite(data[field]).all(), name+": nonfinite native binary")
            if field in csv:
                base.require(csv[field].to_numpy(dtype=DTYPE[field]).tobytes() == data[field].tobytes(), name+": native CSV/binary mismatch "+field)
    state = pd.read_csv(out/"state.csv", float_precision="round_trip")
    base.require(len(state) == 2000 and state.stage.eq("full_step").all() and set(state.step) == {0, steps}, name+": saved timeline")
    for step, frame in state.groupby("step"):
        base.require(np.array_equal(frame.id, np.arange(40, 1040)) and frame.time_s.nunique() == 1
            and abs(float(frame.time_s.iloc[0])-step*1e-5) < 1e-10, name+": sample native IDs/time")
    base.require(np.isfinite(state.drop(columns="stage").to_numpy(dtype=float)).all(), name+": nonfinite physical CSV")
    final_hg = pd.read_csv(out/"hourglass_final.csv", float_precision="round_trip")
    base.require(np.array_equal(final_hg.id, np.arange(40, 1040)) and np.isfinite(final_hg.to_numpy()).all(), name+": HG IDs/nonfinite")
    base.require(complete["elapsed_seconds"] > 0 and run["elapsed_seconds"] > 0, name+": invalid timer")
    return dict(name=name, role=stage["role"], batch=stage["batch"], run_manifest=base.entry(manifest),
        actual_final_time=complete["final_time"], native_particles=1040, soil_particles=1000,
        physical_files={file: base.entry(out/file) for file in PHYSICAL_FILES},
        solver_loop_seconds=complete["elapsed_seconds"], runner_elapsed_seconds=run["elapsed_seconds"],
        hg_completion=hg)


def pair(old, new):
    equal = {file: old["physical_files"][file]["sha256"] == new["physical_files"][file]["sha256"] for file in PHYSICAL_FILES}
    common_hg_equal = all(new["hg_completion"].get(k) == value for k, value in old["hg_completion"].items())
    base.require(all(equal.values()) and common_hg_equal, f"Old/new physical mismatch: {equal}; HG stats={common_hg_equal}")
    return dict(batch=old["batch"], old=old["name"], new=new["name"], byte_identical=equal,
                all_old_hg_statistics_equal=common_hg_equal, required_max_ulp=0, passed=True)


def timing(old, new):
    a, b = statistics.median(old), statistics.median(new)
    reduction = 1-b/a
    def describe(values):
        return dict(samples=values, median=statistics.median(values), minimum=min(values), maximum=max(values),
                    range=max(values)-min(values), population_stdev=statistics.pstdev(values))
    separated = max(new) < min(old)
    return dict(old=describe(old), new=describe(new), median_speedup=a/b, median_reduction_fraction=reduction,
                new_range_strictly_below_old=separated, improvement_over_five_percent=reduction > .05,
                passed=reduction > .05 and separated)


def execute(stage):
    quiet_machine()
    args = arguments(stage)
    command = [sys.executable, "-B", str(Path(base.__file__).resolve()), "--name", args.name,
        "--duration", args.duration, "--dt", args.dt, "--output-interval", args.output_interval,
        "--xi", ".1", "--top-mode", "5", "--engine", "wrapper", "--binary-label", args.binary_label,
        "--threads", "1", "--save", "0", "--run"]
    exe, _ = base.runtime_inputs(args)
    logs = TESTS/"logs"; stdout_path = logs/f"{args.name}.bench.stdout.log"; stderr_path = logs/f"{args.name}.bench.stderr.log"
    started = time.perf_counter()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        process = subprocess.Popen(command, cwd=base.CASE, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            child_affinity = psutil.Process(process.pid).cpu_affinity()
            base.require(child_affinity == psutil.Process().cpu_affinity(), "Runner did not inherit benchmark affinity")
            code = process.wait()
        except BaseException:
            retained.stop_owned(process, args.name, exe)
            raise
    base.require(code == 0, f"Runner {args.name} exited {code}; inspect its retained logs")
    base.require(retained.solver_absent(args.name, exe), args.name+": surviving owned solver")
    result = audit(stage)
    result.update(entry_cli_wall_seconds=time.perf_counter()-started, command=command,
                  runner_cpu_affinity=child_affinity,
                  wrapper_logs=[base.entry(stdout_path), base.entry(stderr_path)])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="hg_release_bench_r1")
    parser.add_argument("--cpu-index", type=int, help="Pin only this benchmark process and its children to one available logical CPU")
    parser.add_argument("--new-binary-label", default=NEW, help="Fresh ReleaseCPU wrapper build label; old reference remains hg_m1rel")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.cpu_index is not None:
        base.require(args.cpu_index in psutil.Process().cpu_affinity(), "Requested logical CPU is not available")
        if args.run:
            psutil.Process().cpu_affinity([args.cpu_index])
    base.require(__import__("re").fullmatch(r"[A-Za-z0-9_-]{1,48}", args.tag), "Use a short benchmark tag")
    base.require(__import__("re").fullmatch(r"[A-Za-z0-9_-]{1,48}", args.new_binary_label), "Use a short binary label")
    if args.self_test:
        assert timing([10, 10.2, 9.8], [8, 8.1, 7.9])["passed"]
        assert not timing([10, 9, 11], [8, 9.1, 8.5])["passed"]
        assert not timing([10, 10, 10], [9.6, 9.6, 9.6])["passed"]
        assert [s["role"] for s in stages("mock")][2:] == ["old", "new", "new", "old", "old", "new"]
        assert {s["binary_label"] for s in stages("mock") if s["role"] == "new"} == {"hg_release_rel_r3"}
        assert {s["binary_label"] for s in stages("mock", "custom") if s["role"] == "new"} == {"custom"}
        assert {s["binary_label"] for s in stages("mock", "custom") if s["role"] == "old"} == {"hg_m1rel"}
        print("PASS pure in-memory timing/order self-test; no solver, file or notification")
        return 0
    check = TESTS/f"logs/{args.tag}.check.json"; status = TESTS/f"logs/{args.tag}.status.json"
    base.require(not check.exists() and not status.exists(), "Benchmark evidence exists; use a fresh tag")
    plan = preflight(args.tag, args.new_binary_label)
    if args.dry_run:
        print(json.dumps(dict(status="checked_not_run", **plan), indent=2));return 0
    quiet_machine(); results = []; pairs = []; failure = None
    base.save_new(status, dict(status="running_not_accepted", plan=plan, started_utc=base.utc()))
    try:
        for stage in plan["stages"]:
            base.status(status, dict(status="running_not_accepted", current=stage, completed=[r["name"] for r in results]))
            results.append(execute(stage))
            group = [r for r in results if r["batch"] == stage["batch"]]
            if len(group) == 2:
                pairs.append(pair(next(r for r in group if r["role"] == "old"), next(r for r in group if r["role"] == "new")))
        unchanged(plan["inputs"])
    except BaseException as error:
        failure = f"{type(error).__name__}: {error}"
    measures = {}
    if failure is None:
        for key in ("solver_loop_seconds", "runner_elapsed_seconds", "entry_cli_wall_seconds"):
            measures[key] = timing(*[[r[key] for r in results if r["batch"] != "warm" and r["role"] == role] for role in ("old", "new")])
    speed_passed = failure is None and all(measures[k]["passed"] for k in ("solver_loop_seconds", "runner_elapsed_seconds"))
    record = dict(status="failed_or_incomplete" if failure else "equivalent_efficiency_gate_passed" if speed_passed else "equivalent_efficiency_benefit_not_established",
        completed_utc=base.utc(), failure=failure, physical_accuracy_accepted=False, full_cycle_admitted=False,
        plan=plan, runs=results, pair_checks=pairs, timing=measures, all_physical_pairs_byte_identical=failure is None,
        efficiency_gate_passed=speed_passed, warmups_excluded=True,
        limitations=["0.03-s fixed CPU workload only; no full-2Tv or GPU speed claim.",
            "Solver-loop timer includes two-endpoint sampling/cell division, not a kernel-only timer.",
            "Runner elapsed includes solver launch, initialization, final output and its verification; excludes prepare/import startup.",
            "Entry CLI wall also includes runner startup/preparation and independent offline audit; descriptive, not acceptance timer.",
            "Three batches describe observed spread, not a statistical confidence interval.",
            "Retained old build/runtime is used as recorded; old source/object paths are not asserted to match current files."])
    base.save_new(check, record)
    base.status(status, dict(status=record["status"], check=base.entry(check), failure=failure, efficiency_gate_passed=speed_passed))
    print(json.dumps(dict(status=record["status"], failure=failure, efficiency_gate_passed=speed_passed, check=str(check))))
    return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
