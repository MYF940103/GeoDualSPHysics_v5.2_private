"""Fresh 1/15-s bounded HG=.05 pairs, original uniform-grid production solver."""
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
import numpy as np
import pandas as pd
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe


def stage(args):
    return "k5em5_hg05_"+str(args.end)+"s_"+args.backend+"_r1"


def prepare(args):
    tag = stage(args)
    patch = "*** Begin Patch\n"
    for v, dt in (("c", ".00001"), ("h", ".000005")):
        old = "k5em5_hg05_"+("r1" if args.backend == "cpu" else "gpu_r1")+"_"+v
        label = tag+"_"+v
        xml = (TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        xml, n = re.subn(r'(<parameter key="TimeMax" value=")[^"]*(" comment=")[^"]*',
                         lambda m:m[1]+str(args.end)+m[2]+"Bounded diagnostic endpoint; not 2Tv", xml)
        assert n == 1
        xml = xml.replace("Output interval corresponding to Delta Tv=0.005; references use actual saved times", "Dense 1-ms diagnostic output; formal output remains DeltaTv=.005")
        bat = (TESTS/"configs"/("x"+old+"_win64_"+args.backend.upper()+".bat")).read_text(encoding="utf8")
        steps = int(Decimal(args.end)/Decimal(dt))
        bat, n = re.subn(r'-nsteps:\d+', '-nsteps:'+str(steps), bat.replace(old, label))
        assert n == 1
        bat = re.sub(r'rem \.3-s HG-strength diagnostic[^\r\n]*', 'rem Gated bounded uniform-grid diagnostic; no full-cycle admission.', bat)
        for path, text in ((TESTS/"configs"/(label+"_Def.xml"), xml),
                           (TESTS/"configs"/("x"+label+"_win64_"+args.backend.upper()+".bat"), bat)):
            assert not path.exists()
            patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+s for s in text.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run_one(args, state, report, v):
    tag = stage(args)
    label = tag+"_"+v
    folder = TESTS/"outputs"/label
    bat = TESTS/"configs"/("x"+label+"_win64_"+args.backend.upper()+".bat")
    assert not folder.exists()
    item = dict(label=label, checked_frames=0, prefix_frames_equal=0)
    report["runs"].append(item)
    report["stage"] = label
    log = TESTS/"logs"/(label+".log")
    history = TESTS/"figures"/(label+"_runtime.csv")
    old = "k5em5_hg05_"+("r1" if args.backend == "cpu" else "gpu_r1")+"_"+v
    prior = TESTS/"outputs"/old
    with log.open("xb") as stream, history.open("x", newline="", encoding="utf8") as out:
        p = subprocess.Popen([os.environ["ComSpec"], "/d", "/c", str(bat)], cwd=CASE, stdout=stream,
                             stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        item["owned_cmd_pid"] = p.pid
        initial, writer, index = None, None, 0
        def consume(i):
            nonlocal initial, writer
            a = probe.native(folder, i)
            if initial is None:
                initial = a.copy()
            m = probe.metrics(a, initial, .01)
            if writer is None:
                writer = csv.DictWriter(out, fieldnames=list(m))
                writer.writeheader()
            writer.writerow(m)
            out.flush()
            item.update(checked_frames=i+1, last_metrics=m)
            assert m["stress_guard_passed"], "Original 100-Pa guard rejected at "+str(m["time_s"])
            assert m["load_available"], "Native force telemetry missing"
            if i <= 300:
                assert a.equals(probe.native(prior, i)), "Same-dt physical prefix differs at PART"+str(i)
                item["prefix_frames_equal"] = i+1
        try:
            while p.poll() is None:
                count = len(list((folder/"data").glob("Part_*.bi4")))
                while index < count-1:
                    consume(index)
                    index += 1
                report["updated_utc"] = utc()
                save(state, report)
                time.sleep(2)
            assert p.returncode == 0, "Solver/BAT failed; inspect "+str(log)
            count = len(list((folder/"data").glob("Part_*.bi4")))
            while index < count:
                consume(index)
                index += 1
        finally:
            if p.poll() is None:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                p.wait()
                item["stopped_by_monitor"] = True
            item.update(owned_exited=True, exit_code=p.returncode)
            save(state, report)
    dt = Decimal(".00001") if v == "c" else Decimal(".000005")
    steps = int(Decimal(args.end)/dt)
    assert index == args.end*1000+1 and item["last_metrics"]["step"] == steps
    assert abs(item["last_metrics"]["time_s"]-args.end) < 1e-7 and item["prefix_frames_equal"] == 301
    text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
    assert "Finished execution (code=0)." in text
    counts = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    cache = re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
    assert counts and tuple(map(int, counts.groups())) == (steps*2, steps, steps, steps*2)
    assert cache and tuple(map(int, cache.groups())) == (steps+1, steps-1)
    assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
    summary = pd.read_csv(folder/"Run.csv", sep=";").iloc[0]
    assert summary.Steps == steps and summary.Np == 1040 and summary.Nfixed == 40 and summary.PartsOut == 0
    item.update(completed=True, hg_runtime_passed=True, loop_seconds=float(summary.TSimul),
                outputs=[bound(p) for p in folder.rglob("*") if p.is_file()]+[bound(log), bound(history)])
    save(state, report)


def pair(args, report):
    peak_p, peak_z = 0., 0.
    for i in range(args.end*1000+1):
        a, b = [probe.native(TESTS/"outputs"/(stage(args)+"_"+v), i) for v in ("c", "h")]
        assert np.array_equal(a.id, b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8
        assert b.step.iloc[0] == 2*a.step.iloc[0]
        top = (a.id-40)%100 == 99
        pressure = float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
        settlement = abs(float((a.z[top]-b.z[top]).mean())*1000)
        peak_p, peak_z = max(peak_p, pressure), max(peak_z, settlement)
        assert pressure <= 5 and settlement <= .005, "Original half-step guard failed at PART"+str(i)
    result = dict(passed=True, samples=args.end*1000+1, pressure_rms_max_pa=peak_p, top_settlement_difference_max_mm=peak_z)
    save(TESTS/"logs"/(stage(args)+"_half.check.json"), result)
    report["half"] = result


def worker(args):
    tag = stage(args)
    state = TESTS/"logs"/(tag+".status.json")
    assert not state.exists()
    report = dict(status="running", worker_pid=os.getpid(), started_utc=utc(), runs=[], full_admitted=False,
                  backend=args.backend, dp_m=.01, conductivity=5e-5, xi=.05, eta=.04, production_modified=False)
    try:
        prior = TESTS/"logs"/("k5em5_hg05_gpu_review_r1.check.json" if args.end == 1 else "k5em5_hg05_1s_"+args.backend+"_r1.review.json")
        accepted = read(prior)
        assert accepted["passed"] and accepted["visual_inspected"]
        verify(accepted["evidence"])
        assert subprocess.check_output(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip() == "0"
        paths = [Path(__file__), Path(probe.__file__), probe.READER, prior,
                 REPO/"bin/windows"/("DualSPHysics5.2CPU_win64.exe" if args.backend == "cpu" else "DualSPHysics5.2_GEO_win64.exe")]
        paths += [TESTS/"configs"/name for v in ("c", "h") for name in (tag+"_"+v+"_Def.xml", "x"+tag+"_"+v+"_win64_"+args.backend.upper()+".bat")]
        report["inputs"] = [bound(p) for p in paths]
        save(state, report)
        for v in ("c", "h"):
            run_one(args, state, report, v)
        pair(args, report)
        verify(report["inputs"])
        report.update(status="pair_passed_pending_physical_review", stage="review")
    except Exception as error:
        report.update(status="rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = utc()
    save(state, report)
    message = (f"User-authorized same-thread uniform-dp k5e-5 HG .05 continuation {tag}, not a new human observation. Detected {report['status']}. "
               f"Read {state}, its queue_attempt.json, {TESTS/'notes/k5em5_uniform_r1.md'} and {tag}_half.check.json before claims. "
               "User stopped refined r3 and requires all three formal groups dp=.01,width=.1. Never restart old workers or use refinement as a workaround. "
               "This stage changes only XML HG xi .1 to .05; original float u-pw/Darcy,eta=.04,band/vectorSPR/fixed event unchanged; no production C++/CUDA changes. "
               "Density and normal-Darcy prototypes were rejected; do not merge them. Verify native IDs/actual times/owned exits/hashes, all 301 same-dt .3-s prefix fields, "
               "full-history 100Pa stress/top-gap, load1000N/m within.001, all-sample5Pa/.005mm half, HG cache/call/dt/spin. Inspect pressure/settlement/Q/theory figures before acceptance. "
               "CPU/GPU .3-s accepted comparison and actual timing are in k5em5_hg05_gpu_review_r1.check.json; do not reuse the old fine-grid backend timing. "
               "On failure report exact reason/time and diagnose without relaxed thresholds, increased damping, duplicate solver or overwrite. On pass report Chinese quantified findings and continue authorized gated 15-s and full uniform-grid2Tv delivery as justified. "
               "No automatic full-cycle acceptance; disclose HG strength differs from retained k3/k4 unless separately validated. Root TimeOut remainsDeltaTv=.005, old partial outputs preserved; no exactHG PART restart. "
               "This worker queues once; do not restart/rearm it or send connectivity tests. Continue without waiting for another progress question.")
    save(TESTS/"logs"/(tag+".queue_attempt.json"), dict(utc=utc(), terminal=report.copy(), thread=args.thread, message=message))
    q = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message], capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    report.update(queue_status="queued" if q.returncode == 0 else "failed_no_retry", queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    save(state, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end", type=int, choices=(1, 15), required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu"), required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--codex")
    parser.add_argument("--thread")
    args = parser.parse_args()
    if args.prepare:
        prepare(args)
    elif args.worker:
        worker(args)
    else:
        tag = stage(args)
        launch = TESTS/"logs"/(tag+".launch.json")
        assert not launch.exists() and not (TESTS/"logs"/(tag+".status.json")).exists()
        old = read(TESTS/"logs/k5em5_gpu_r3.launch.json")
        codex = old["argv"][old["argv"].index("--codex")+1]
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--end", str(args.end), "--backend", args.backend,
                "--worker", "--codex", codex, "--thread", old["thread"]]
        with (TESTS/"logs"/(tag+".worker.log")).open("xb") as stream:
            p = subprocess.Popen(argv, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        save(launch, dict(pid=p.pid, argv=argv, utc=utc(), thread=old["thread"]))
        print(json.dumps(dict(pid=p.pid, state=str(TESTS/"logs"/(tag+".status.json")))))
