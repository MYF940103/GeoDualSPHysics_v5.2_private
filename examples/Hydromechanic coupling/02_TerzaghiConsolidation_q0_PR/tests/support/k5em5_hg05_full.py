"""Fresh uniform-grid CPU8 formal 2Tv; one owned solver and one terminal follow-up."""
import argparse
import csv
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import psutil
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe
sys.path.insert(0, str(CASE/"support"))
import release_case as formal

TAG = "k5em5_hg05_full_cpu_r1"
FORMAL = "CaseTerzaghiConsolidation_q0_PR_full_k5em5"
FOLDER = CASE/(FORMAL+"_release_CPU_uniform_out")
BAT = CASE/("x"+FORMAL+"_win64_CPU.bat")
STATE = TESTS/"logs"/(TAG+".status.json")
ADMISSION = TESTS/"logs/k5em5_hg05_15s_cpu_r1.review.json"
END, STEPS = 145.75858, 14575858


def completion(folder, steps, end, frames):
    text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
    assert "Finished execution (code=0)." in text
    summary = pd.read_csv(folder/"Run.csv", sep=";").iloc[0]
    assert summary.Steps == steps and summary.Np == 1040 and summary.Nfixed == 40 and summary.PartsOut == 0
    assert summary.PartFiles == frames
    calls = re.search(r"forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    cache = re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
    assert calls and tuple(map(int, calls.groups())) == (2*steps, steps, steps, 2*steps)
    assert cache and tuple(map(int, cache.groups())) == (steps+1, steps-1)
    assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
    assert "DTs adjusted to DtMin............: 0" in text
    last = probe.native(folder, frames-1)
    assert last.step.iloc[0] == steps and abs(float(last.time_s.iloc[0])-end) < 1e-7
    return dict(steps=steps, frames=frames, actual_final_time_s=float(last.time_s.iloc[0]),
                loop_seconds=float(summary.TSimul), hg_dt_tau_max=float(limits[1]), spin_bound=float(limits[2]))


def prerequisites():
    admission = read(ADMISSION)
    assert admission["passed"] and admission["visual_inspected"] and admission["next_run_admitted"] == TAG
    verify(admission["evidence"])
    assert read(TESTS/"logs/k5em5_hg05_15s_cpu_r1.prefix1s.check.json")["passed"]
    tree = ET.parse(CASE/(FORMAL+"_Def.xml"))
    params = {p.get("key"): p.get("value") for p in tree.findall("./execution/parameters/parameter")}
    control = ET.parse(TESTS/"configs/k5em5_hg05_15s_cpu_r1_c_Def.xml")
    old = {p.get("key"): p.get("value") for p in control.findall("./execution/parameters/parameter")}
    assert {k:Decimal(v) for k,v in params.items() if k not in ("TimeMax", "TimeOut")} == {k:Decimal(v) for k,v in old.items() if k not in ("TimeMax", "TimeOut")}
    assert ET.tostring(tree.find("./execution/special")) == ET.tostring(control.find("./execution/special"))
    assert Decimal(params["TimeMax"]) == Decimal("145.75858") and Decimal(params["DtFixed"]) == Decimal(".00001")
    assert Decimal(params["TimeMax"])/Decimal(params["DtFixed"]) == STEPS
    assert Decimal(params["TimeOut"]) == Decimal(".36437142857142857")
    assert tree.find("./execution/special/timeout") is None and float(params["SoilHourglassXi"]) == .05
    assert not FOLDER.exists(), "Retained output must not be overwritten"
    assert not any(p.info["name"].lower().startswith("dualsphysics") for p in psutil.process_iter(["name"]) if p.info["name"])
    assert not subprocess.check_output(["git", "-C", str(REPO), "diff", "--name-only", "--", "src/source", "src/VS"], text=True).strip()
    paths = [Path(__file__), Path(probe.__file__), probe.READER, Path(formal.__file__), CASE/"support/compare_precision_q0.py",
             TESTS/"support/formal_release_sequence.py", TESTS/"support/mdbc_gpu_vector_run.py", ADMISSION,
             TESTS/"logs"/(TAG+".selftest.json"),
             TESTS/"logs/k5em5_hg05_15s_cpu_r1.prefix1s.check.json", CASE/(FORMAL+"_Def.xml"), BAT]
    paths += [REPO/"bin/windows"/name for name in ("DualSPHysics5.2CPU_win64.exe", "GenCase_win64.exe", "PartVTK_win64.exe", "ReadHydroMechGridPart_win64.exe")]
    return [bound(p) for p in paths]


def run(report):
    history = TESTS/"figures"/(TAG+"_runtime.csv")
    log = TESTS/"logs"/(TAG+".log")
    index, initial, model, writer = 0, None, None, None
    with log.open("xb") as stream, history.open("x", newline="", encoding="utf8") as output:
        p = subprocess.Popen([os.environ["ComSpec"], "/d", "/c", str(BAT)], cwd=CASE,
                             stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(stage="formal_cpu_2tv", owned_cmd_pid=p.pid, owned_cmd_created=psutil.Process(p.pid).create_time(),
                      checked_frames=0, same_step_saved_prefix_matches=0)
        save(STATE, report)

        def consume(i):
            nonlocal initial, model, writer
            a = probe.native(FOLDER, i)
            if initial is None:
                initial = a.copy()
                model = formal.model(FOLDER/(FORMAL+".xml"))
                assert model["dp"] == .01 and model["width"] == .1 and model["k"] == 5e-5 and model["dt"] == 1e-5
            try:
                assert a.load_available.eq(1).all(), "Native load observation absent"
                value = formal.inspect(a, initial, model)
                value.update(step=int(a.step.iloc[0]), part=i)
                assert not i or value["time_s"] > report["last_metrics"]["time_s"]
                # Compare only identical saved integration steps; the formal cadence is not 1 ms.
                if value["step"] <= 1500000 and value["step"] % 100 == 0:
                    b = probe.native(TESTS/"outputs/k5em5_hg05_15s_cpu_r1_c", value["step"]//100)
                    cols = a.select_dtypes(include="number").columns
                    assert a[cols].to_numpy(dtype="<f8").tobytes() == b[cols].to_numpy(dtype="<f8").tobytes(), "Same-step saved native prefix changed"
                    assert a.drop(columns=cols).equals(b.drop(columns=cols))
                    report["same_step_saved_prefix_matches"] += 1
            except Exception as error:
                raise RuntimeError(f"Native guard failed at PART {i}, t={a.time_s.iloc[0]:.17g}: {error}") from error
            if writer is None:
                # Optional force metrics begin only after t=.1 s in the existing reviewer.
                fields = list(value)+[k for k in ("load_resultant_N_m", "equivalent_full_width_resultant_N_m") if k not in value]
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
            writer.writerow(value)
            output.flush()
            report.update(checked_frames=i+1, last_metrics=value)

        try:
            while p.poll() is None:
                count = len(list((FOLDER/"data").glob("Part_*.bi4")))
                while index < count-1:
                    consume(index)
                    index += 1
                report["owned_solver_processes"] = [dict(pid=q.pid, created=q.create_time(), name=q.name()) for q in psutil.Process(p.pid).children(recursive=True) if q.name().lower().startswith("dualsphysics")]
                report["updated_utc"] = utc()
                save(STATE, report)
                time.sleep(10)
            report["bat_exit_code"] = p.returncode
            count = len(list((FOLDER/"data").glob("Part_*.bi4")))
            while index < count:
                consume(index)
                index += 1
            assert p.returncode == 0, "Formal BAT failed; inspect solver versus postprocessing in "+str(log)
        finally:
            if p.poll() is None:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                p.wait()
                report["stopped_by_monitor"] = True
            report.update(owned_exited=True, exit_code=p.returncode)
            save(STATE, report)
    report["completion"] = completion(FOLDER, STEPS, END, index)
    assert index == 402 and report["last_metrics"]["tv"] >= 2-1e-6
    assert read(CASE/"figures/full_validation_release_k5em5_uniform_CPU.check.json")["passed"]
    verify(report["inputs"])
    report.update(solver_completed=True, outputs=[bound(p) for p in FOLDER.rglob("*") if p.is_file()]+[bound(log), bound(history)])


def worker(args):
    assert not STATE.exists()
    report = dict(status="running", stage="prerequisites", worker_pid=os.getpid(), started_utc=utc(), backend="CPU", threads=8,
                  conductivity_m_s=5e-5, dp_m=.01, width_m=.1, xi=.05, eta=.04, dt_s=1e-5,
                  nominal_time_s=END, expected_steps=STEPS, formal_delta_tv=.005, output=str(FOLDER), physical_acceptance=False)
    save(STATE, report)
    try:
        report["inputs"] = prerequisites()
        report["checkpoint"] = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        run(report)
        report.update(status="cpu_uniform_2tv_completed_pending_physical_review", stage="review")
    except Exception as error:
        report.update(status="rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = utc()
    save(STATE, report)
    message = (f"User-authorized same-thread uniform-dp k5e-5 CPU8 HG .05 full-cycle continuation {TAG}, not a new human observation. Detected {report['status']}. "
               f"Read {STATE}, its queue_attempt.json, tests/notes/k5em5_uniform_r1.md and logs/k5em5_hg05_15s_cpu_r1.review.json before claims. "
               "Fresh root CPU_uniform_out only: dp=.01,width=.1,xi=.05,eta=.04,original float u-pw/Darcy,band/vectorSPR/fixed event,dt10us,14575858steps,end145.75858s. "
               "All three groups have equal dp; accepted k3/k4 retain xi=.1, disclose that numerical-strength difference. No rejected density/Darcy prototype was merged. "
               "Verify exact exits/ownership,actual times/native IDs,input-output-build hashes,all saved geometry/drainage/100Pa stress/top-gap/load1000N/m within.001 and HG call/cache/dt/spin guards. "
               "Root cadence is DeltaTv=.005,402 native frames including final partial,not 1ms; same-step saved-prefix comparisons are only those actually shared with retained 15s. "
               "Inspect root full_validation_release_k5em5_uniform_CPU PNG/CSV/checks,all-Tv profiles including1.5/2,pressure,material settlement,stress/Q,bottom bias and late decay. Solver completion is not physical acceptance; only15s half-step evidence exists. "
               "If only postprocessing failed,repair new analysis without rerunning completed solver. On runtime failure report exact reason/time,preserve partial output,check surviving owned processes,no duplicate solver or relaxed gates. "
               "On pass continue authorized all-three comparison/publication,later boundary tests,dependency-aware cleanup and verified selective Git backup. k3/k4 stand; do not restart KEEP or old workers. "
               "No plastic/large-rotation/general-boundary/exact-HG-restart claim. Proactively report Chinese outcome and continue without progress prompts. This worker queues once; never rearm/restart it or send connectivity tests.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(utc=utc(), thread=args.thread, terminal=report.copy(), message=message), stream, indent=2)
    try:
        q = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message], capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_status="queued" if q.returncode == 0 else "failed_no_retry", queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:
        report.update(queue_status="uncertain_no_retry", queue_error=str(error))
    save(STATE, report)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--worker", action="store_true")
    p.add_argument("--codex")
    p.add_argument("--thread")
    args = p.parse_args()
    if args.selftest:
        result = completion(TESTS/"outputs/k5em5_hg05_15s_cpu_r1_c", 1500000, 15, 15001)
        target = TESTS/"logs"/(TAG+".selftest.json")
        assert not target.exists()
        save(target, dict(passed=True, utc=utc(), completion=result, evidence=[bound(Path(__file__)), bound(TESTS/"outputs/k5em5_hg05_15s_cpu_r1_c/Run.out"), bound(TESTS/"outputs/k5em5_hg05_15s_cpu_r1_c/Run.csv")]))
        print(json.dumps(dict(passed=True, scope="Completion parser on retained 15-s run; no solver launched", **result)))
    elif args.worker:
        worker(args)
    elif args.check:
        print(json.dumps(dict(ready=True, input_files=len(prerequisites()), solver_started=False)))
    else:
        launch = TESTS/"logs"/(TAG+".launch.json")
        assert not launch.exists() and not STATE.exists()
        prerequisites()
        old = read(TESTS/"logs/k5em5_hg05_15s_cpu_r1.launch.json")
        codex = old["argv"][old["argv"].index("--codex")+1]
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--codex", codex, "--thread", old["thread"]]
        with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
            child = subprocess.Popen(argv, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        with launch.open("x", encoding="utf8") as stream:
            json.dump(dict(pid=child.pid, argv=argv, thread=old["thread"], utc=utc()), stream, indent=2)
        print(json.dumps(dict(pid=child.pid, state=str(STATE))))
