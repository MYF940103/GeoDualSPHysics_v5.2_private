"""Test a uniform 8-column periodic cell against retained 32-column native data."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
import k5_guard_probe as probe
from k5_grid320_sequence import TAG as FULL, VARIANTS, FIELDS
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify

TAG = "k5_cell8_1s_r1"
STATE = TESTS/"logs"/(TAG+".status.json")
DP, WIDTH, NX, NZ = .003125, .025, 8, 320


def metrics(a, initial):
    """Original guards, with the measured force explicitly scaled to 0.1-m width."""
    assert len(a) == NX*NZ and np.array_equal(a.id, np.arange(32, 2592))
    assert np.array_equal(a.id, initial.id) and np.isfinite(a.select_dtypes("number").to_numpy()).all()
    assert a.rho.gt(0).all() and a.kplastic.eq(0).all()
    layer = np.rint(initial.z.to_numpy()/DP-.5).astype(int)
    assert np.array_equal(np.bincount(layer), np.full(NZ, NX))
    total = np.bincount(layer, weights=a.sigma_zz-a.pressure)/NX
    disp = (initial.z-a.z).to_numpy()*1000
    dx = (a.x.to_numpy()-initial.x.to_numpy()+WIDTH/2) % WIDTH-WIDTH/2
    span = max(np.ptp(a.z.to_numpy()[layer == i]) for i in range(NZ))*1000
    assert abs(dx).max()*1000 < .5 and span < .5 and a.z.gt(0).all()
    assert a.load_available.eq(1).all()
    force = float(2100*DP*DP*a.load_az.sum())
    t = float(a.time_s.iloc[0])
    applicable = t >= .1-1e-7
    if applicable:
        assert set(a.id[a.drained.eq(1)]) == set(a.id[layer == NZ-1])
        assert a.pressure[layer == NZ-1].eq(0).all()
        assert abs(4*force+1000) < .001, "Original equivalent-width resultant tolerance failed"
    m = dict(time_s=t, step=int(a.step.iloc[0]), mean_pressure_pa=float(a.pressure.mean()),
        max_layer_total_error_pa=float(abs(total+10000).max()), top_gap_pa=float(abs(total[-1]-total[-2])),
        Q_pa=float(np.sqrt(np.mean(np.diff(total, n=2)**2))), top_settlement_mm=float(disp[layer == NZ-1].mean()),
        bottom_settlement_mm=float(disp[layer == 0].mean()), max_dx_mm=float(abs(dx).max()*1000), max_layer_span_mm=float(span),
        load_resultant_N_m=force, equivalent_full_width_resultant_N_m=4*force, stress_guard_applicable=applicable)
    m["stress_guard_passed"] = not applicable or (m["max_layer_total_error_pa"] <= 100 and m["top_gap_pa"] <= 100)
    assert m["stress_guard_passed"], "Original 100-Pa guard failed: "+str(m)
    return m


def prepare():
    patch = "*** Begin Patch\n"
    for suffix, _, _ in VARIANTS:
        label, old = TAG+"_"+suffix, FULL+"_"+suffix
        xml = (TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        for key in ("sizefx", "sizebx"):
            xml, count = re.subn(r'(<newvarcte '+key+r'=")[^"]*(")', lambda m: m[1]+"0.025"+m[2], xml)
            assert count == 1
        bat = (TESTS/"configs"/("x"+old+"_win64_GPU.bat")).read_text(encoding="utf8").replace("set case="+old, "set case="+label)
        for path, content in ((TESTS/"configs"/(label+"_Def.xml"), xml), (TESTS/"configs"/("x"+label+"_win64_GPU.bat"), bat)):
            assert not path.exists()
            patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run(report, suffix, duration, dt):
    label, folder = TAG+"_"+suffix, TESTS/"outputs"/(TAG+"_"+suffix)
    assert not folder.exists()
    log = TESTS/"logs"/(label+".log")
    item = dict(label=label, duration_s=float(duration), dt_s=float(dt))
    report["runs"].append(item); report["stage"] = label; save(STATE, report)
    with log.open("xb") as stream:
        p = subprocess.Popen(["cmd.exe", "/d", "/c", str(TESTS/"configs"/("x"+label+"_win64_GPU.bat"))],
            cwd=CASE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        item["pid"] = p.pid; save(STATE, report)
        initial, index = None, 0
        try:
            while p.poll() is None:
                files = sorted((folder/"data").glob("Part_*.bi4"))
                while index < len(files)-1:
                    a = probe.native(folder, index)
                    if initial is None: initial = a.copy()
                    m = metrics(a, initial)
                    item.update(last_checked_time_s=m["time_s"], last_metrics=m); index += 1
                report["updated_utc"] = utc(); save(STATE, report); time.sleep(15)
            assert p.returncode == 0, "BAT failed: "+str(log)
        finally:
            if p.poll() is None:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                p.wait(); item["stopped_by_monitor"] = True
            item.update(exit_code=p.returncode, owned_process_exited=True); save(STATE, report)
    files = sorted((folder/"data").glob("Part_*.bi4")); initial = probe.native(folder, 0)
    rows = [metrics(probe.native(folder, i), initial) for i in range(len(files))]
    expected = int(Decimal(duration)/Decimal(dt))
    assert rows[-1]["step"] == expected and abs(rows[-1]["time_s"]-float(duration)) < 1e-7
    text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
    assert "Finished execution (code=0)." in text
    period = re.search(r"PeriodicXinc=\(([^,]+),", text)
    assert period and abs(float(period[1])+WIDTH) < 1e-12 and 3.6*DP < WIDTH/2
    calls = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
    assert calls and list(map(int, calls.groups())) == [2*expected, expected, expected, 2*expected]
    assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
    item.update(completed=True, final=rows[-1], frames=len(files),
        outputs=[bound(p) for p in files+[folder/"Run.out", folder/"Run.csv", log]])
    save(STATE, report)


def compare(report, left, right, kind):
    """Native ordering is by x-column then initial z; tile only the periodic field."""
    lf = TESTS/"outputs"/left; rf = TESTS/"outputs"/right
    count = len(list((lf/"data").glob("Part_*.bi4")))
    li, ri = probe.native(lf, 0), probe.native(rf, 0)
    peaks = dict(pressure_rms_pa=0., top_settlement_difference_mm=0., max_total_stress_difference_pa=0.)
    for i in range(count):
        a, b = probe.native(lf, i), probe.native(rf, i)
        assert abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8
        if kind == "prefix":
            assert np.array_equal(a.id, b.id)
            assert a[FIELDS].to_numpy(dtype="<f8").tobytes() == b[FIELDS].to_numpy(dtype="<f8").tobytes()
            continue
        if kind == "half":
            assert np.array_equal(a.id, b.id) and int(b.step.iloc[0]) == 2*int(a.step.iloc[0])
            ap, bp = a.pressure.to_numpy(), b.pressure.to_numpy()
            at, bt = (a.sigma_zz-a.pressure).to_numpy(), (b.sigma_zz-b.pressure).to_numpy()
        else:
            assert kind == "periodic" and len(a) == 4*len(b) and a.step.iloc[0] == b.step.iloc[0]
            assert np.max(abs(li.z.to_numpy()-np.tile(ri.z.to_numpy(), 4))) < 1e-14
            translated_x = np.tile(ri.x.to_numpy(), 4)+np.repeat(np.arange(4)*WIDTH, NX*NZ)
            assert np.max(abs(li.x.to_numpy()-translated_x)) < 1e-14
            ap, bp = a.pressure.to_numpy(), np.tile(b.pressure.to_numpy(), 4)
            at, bt = (a.sigma_zz-a.pressure).to_numpy(), np.tile((b.sigma_zz-b.pressure).to_numpy(), 4)
        p = float(np.sqrt(np.mean((ap-bp)**2)))
        u = abs(float((li.z-a.z)[li.z > .996].mean()-(ri.z-b.z)[ri.z > .996].mean())*1000)
        s = float(abs(at-bt).max())
        peaks = {key: max(peaks[key], value) for key, value in zip(peaks, (p, u, s))}
        assert p <= 5 and u <= .005, kind+" original pressure/material-settlement comparison limits failed"
        if kind == "periodic": assert s <= 5, "Periodic-cell stress equivalence limit 5 Pa failed"
    report.setdefault("comparisons", []).append(dict(left=left, right=right, kind=kind, samples=count, passed=True, **peaks))
    save(STATE, report)


def worker(args):
    assert not STATE.exists()
    report = dict(status="running", stage="prerequisites", worker_pid=os.getpid(), started_utc=utc(), runs=[], comparisons=[])
    save(STATE, report)
    try:
        gate = TESTS/"logs/k5_grid320_review_r1.check.json"
        review = read(gate); assert review["audit_passed"] and not review["full_cycle_admitted"]
        verify(review["evidence"])
        report["checkpoint"] = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        report["inputs"] = [bound(p) for p in (Path(__file__), Path(probe.__file__), probe.READER, gate,
            TESTS/"support/k5_grid320_sequence.py", TESTS/"support/formal_release_sequence.py", TESTS/"support/mdbc_gpu_vector_run.py",
            REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe", REPO/"bin/windows/GenCase_win64.exe", REPO/"bin/windows/PartVTK_win64.exe")]
        for suffix, _, _ in VARIANTS:
            report["inputs"] += [bound(TESTS/"configs"/name) for name in (TAG+"_"+suffix+"_Def.xml", "x"+TAG+"_"+suffix+"_win64_GPU.bat")]
        for suffix, duration, dt in VARIANTS:
            run(report, suffix, duration, dt)
            compare(report, FULL+"_"+suffix, TAG+"_"+suffix, "periodic")
            if suffix == "015h": compare(report, TAG+"_015c", TAG+"_015h", "half")
            if suffix == "1c": compare(report, TAG+"_015c", TAG+"_1c", "prefix")
            if suffix == "1h":
                compare(report, TAG+"_015h", TAG+"_1h", "prefix"); compare(report, TAG+"_1c", TAG+"_1h", "half")
        verify(report["inputs"])
        report.update(status="cell8_1s_pairs_passed_pending_review", stage="review")
    except Exception as error:
        report.update(status="cell8_sequence_rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = utc(); save(STATE, report)
    message = (f"User-authorized same-thread periodic-cell cost/equivalence diagnostic {TAG}, not a new human observation. Detected {report['status']}. "
        f"Read {STATE}, its queue_attempt.json, tests/notes/formal_release_r1.md and logs/k5_grid320_review_r1.check.json before claims. "
        "Only fresh dp=.003125,width=.025,8x320 cells .15/1-s coarse/half were admitted, against retained full-width32-column controls. "
        "Verify owned exits, actual times/native IDs/hashes, all original geometry/drainage/100-Pa stress/top-gap/HG guards. Actual force is250N/m; four-cell equivalent must retain original1000N/m within .001. "
        "Inspect all-sample 5-Pa/.005-mm half and periodic comparisons, extra5-Pa pointwise total-stress equivalence and native prefixes. Generate/inspect plots and quantify measured loop timing; particle-count reduction is not assumed whole-run speedup. "
        "On failure report exact reason/time, preserve evidence and diagnose without relaxed gates, raised damping, duplicate solver or overwrite. No automatic15-s/2Tv/formal admission. "
        "Old formal k5 stopped at t=.10001 guard(lastcompletePART=.2), not2Tv; never restart it. k3/k4 accepted delivery stands; do not reopenKEEP. "
        "Continue authorized delivery after physical/cost review, no production/formal changes yet; never restart/rearm this one-shot worker or send connectivity tests.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(thread=args.thread, utc=utc(), terminal=report.copy(), message=message), stream, indent=2)
    try:
        q = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message], capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True, queue_status="queued" if q.returncode == 0 else "failed_no_retry", queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True, queue_status="uncertain_no_retry", queue_error=str(error))
    save(STATE, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare", action="store_true"); p.add_argument("--worker", action="store_true")
    p.add_argument("--codex"); p.add_argument("--thread"); args = p.parse_args()
    if args.prepare: return prepare()
    assert args.codex and Path(args.codex).is_file() and args.thread
    if args.worker: return worker(args)
    assert not STATE.exists() and read(TESTS/"logs/k5_grid320_review_r1.check.json")["audit_passed"]
    count = subprocess.check_output(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip()
    assert count == "0"
    with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--codex", args.codex, "--thread", args.thread]
        child = subprocess.Popen(argv, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(TAG+".launch.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(pid=child.pid, thread=args.thread, argv=argv), stream, indent=2)
    print(json.dumps(dict(pid=child.pid, state=str(STATE))))


if __name__ == "__main__": main()
