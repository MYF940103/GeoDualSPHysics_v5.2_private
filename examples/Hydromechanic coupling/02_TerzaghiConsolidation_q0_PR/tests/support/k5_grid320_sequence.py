"""Fresh 320-layer .15-s/1-s coarse-half admission; no automatic full-cycle run."""
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
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import bound, read, verify

TAG = "k5_grid320_1s_r1"
STATE = TESTS/"logs"/(TAG+".status.json")
VARIANTS = [("015c", ".15", ".000005"), ("015h", ".15", ".0000025"),
            ("1c", "1", ".000005"), ("1h", "1", ".0000025")]
FIELDS = ["x", "y", "z", "vx", "vy", "vz", "rho", "pressure", "sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz", "kplastic", "load_az", "fstype", "normal_z", "drained"]


def prepare():
    xml = (TESTS/"configs/k5_grid320_r1_Def.xml").read_text(encoding="utf8")
    bat = (TESTS/"configs/xk5_grid320_r1_win64_GPU.bat").read_text(encoding="utf8")
    patch = "*** Begin Patch\n"
    for suffix, duration, dt in VARIANTS:
        label = TAG+"_"+suffix
        text = xml
        for key, value in (("DtIni", dt), ("DtFixed", dt), ("TimeMax", duration), ("TimeOut", "0.004999999999")):
            text, count = re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")', lambda m: m[1]+value+m[2], text)
            assert count == 1
        text = text.replace("Formal 2Tv endpoint rounded up to the fixed-step grid", "Short controlled admission endpoint; not a full-cycle calculation")
        # Output thresholds just below the decimal grid retain the same physical
        # states, avoiding a one-step saved-time mismatch in this half-step test.
        steps = int(Decimal(duration)/Decimal(dt))
        batch = bat.replace("set case=k5_grid320_r1", "set case="+label).replace("-nsteps:20002", "-nsteps:"+str(steps))
        for path, content in ((TESTS/"configs"/(label+"_Def.xml"), text), (TESTS/"configs"/("x"+label+"_win64_GPU.bat"), batch)):
            assert not path.exists()
            patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run(report, suffix, duration, dt):
    label = TAG+"_"+suffix
    folder = TESTS/"outputs"/label
    bat = TESTS/"configs"/("x"+label+"_win64_GPU.bat")
    assert not folder.exists()
    item = dict(label=label, duration_s=float(duration), dt_s=float(dt))
    report["runs"].append(item); report["stage"] = label; save(STATE, report)
    log = TESTS/"logs"/(label+".log")
    with log.open("xb") as stream:
        p = subprocess.Popen(["cmd.exe", "/d", "/c", str(bat)], cwd=CASE, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        item["pid"] = p.pid; save(STATE, report)
        initial, index = None, 0
        try:
            while p.poll() is None:
                parts = sorted((folder/"data").glob("Part_*.bi4"))
                while index < len(parts)-1:
                    a = probe.native(folder, index)
                    if initial is None:
                        initial = a.copy()
                    m = probe.metrics(a, initial, .003125)
                    item.update(last_checked_time_s=m["time_s"], last_checked_step=m["step"], last_metrics=m)
                    assert m["stress_guard_passed"], "Original 100-Pa stress/top-gap guard failed: "+str(m)
                    index += 1
                report["updated_utc"] = utc(); save(STATE, report)
                time.sleep(15)
            assert p.returncode == 0, label+" failed; retained log "+str(log)
        finally:
            if p.poll() is None:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                p.wait(); item["stopped_by_monitor"] = True
            item.update(exit_code=p.returncode, owned_process_exited=True); save(STATE, report)
    parts = sorted((folder/"data").glob("Part_*.bi4"))
    initial = probe.native(folder, 0)
    rows = [probe.metrics(probe.native(folder, i), initial, .003125) for i in range(len(parts))]
    assert all(r["stress_guard_passed"] for r in rows)
    expected = int(Decimal(duration)/Decimal(dt))
    assert rows[-1]["step"] == expected and abs(rows[-1]["time_s"]-float(duration)) < 1e-7
    text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
    assert "Finished execution (code=0)." in text
    calls = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
    assert calls and list(map(int, calls.groups())) == [2*expected, expected, expected, 2*expected]
    assert limits and float(limits[1]) <= .2 and float(limits[2]) < .01
    item.update(completed=True, final=rows[-1], frames=len(parts),
        outputs=[bound(x) for x in parts+[folder/"Run.out", folder/"Run.csv", log]])
    save(STATE, report)


def compare(report, left, right, prefix=False):
    c, h = [TESTS/"outputs"/(TAG+"_"+v) for v in (left, right)]
    files = sorted((c/"data").glob("Part_*.bi4"))
    peak_p, peak_u = 0., 0.
    z0 = probe.native(c, 0).z.to_numpy()
    top = z0 > z0.max()-.003125*.5
    for i in range(len(files)):
        a, b = probe.native(c, i), probe.native(h, i)
        assert np.array_equal(a.id, b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8
        if prefix:
            assert a[FIELDS].to_numpy(dtype="<f8").tobytes() == b[FIELDS].to_numpy(dtype="<f8").tobytes(), "Same-dt physical prefix changed"
        else:
            assert 2*int(a.step.iloc[0]) == int(b.step.iloc[0])
            peak_p = max(peak_p, float(np.sqrt(np.mean((a.pressure-b.pressure)**2))))
            peak_u = max(peak_u, abs(float((a.z.to_numpy()[top]-b.z.to_numpy()[top]).mean()*1000)))
            assert peak_p <= 5 and peak_u <= .005, "Original 5-Pa/.005-mm half-step limit failed"
    report.setdefault("comparisons", []).append(dict(left=left, right=right, samples=len(files), passed=True,
        same_dt_prefix_0_ulp=prefix, max_pressure_rms_pa=peak_p, max_top_settlement_difference_mm=peak_u))
    save(STATE, report)


def worker(args):
    assert not STATE.exists()
    report = dict(status="running", worker_pid=os.getpid(), stage="prerequisites", runs=[], started_utc=utc())
    save(STATE, report)
    try:
        gate = TESTS/"logs/k5_grid320_r1.check.json"
        assert read(gate)["original_stress_guard_passed"]
        verify(read(gate)["evidence"])
        report["checkpoint"] = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        report["inputs"] = [bound(p) for p in (Path(__file__), Path(probe.__file__), probe.READER, gate,
            REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe")]
        for suffix, _, _ in VARIANTS:
            report["inputs"] += [bound(TESTS/"configs"/name) for name in (TAG+"_"+suffix+"_Def.xml", "x"+TAG+"_"+suffix+"_win64_GPU.bat")]
        for suffix, duration, dt in VARIANTS:
            run(report, suffix, duration, dt)
            if suffix == "015h": compare(report, "015c", "015h")
            if suffix == "1c": compare(report, "015c", "1c", True)
            if suffix == "1h":
                compare(report, "015h", "1h", True); compare(report, "1c", "1h")
        verify(report["inputs"])
        report.update(status="grid320_1s_pairs_passed_pending_review", stage="review")
    except Exception as error:
        report.update(status="grid320_sequence_rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = utc(); save(STATE, report)
    message = (f"User-authorized same-thread k1e-5 refined-grid diagnostic {TAG}, not a new human observation. Detected {report['status']}. "
        f"Read {STATE}, its .queue_attempt.json and tests/notes/formal_release_r1.md before claims. "
        "The old formal_release_k5_r1 was stopped by its original guard at t=.10001: stress139.46 Pa/topgap259.89 Pa; last complete PART=.2 s, not 2Tv. Never restart/rearm it. "
        "New tests use fresh dp=.003125, full width=.1, eta=.04 xi=.1, dt5e-6/2.5e-6. They do NOT alter production/formal XML/BAT or any thresholds. "
        "Inspect owned exits, actual times/native IDs, input/output hashes, original all-sample geometry/load/drainage and post-.1-s100-Pa guards, HG runtime checks, "
        ".15/1-s all-sample5-Pa/.005-mm half pairs and same-dt native physical prefixes (not exact-HG restart proof). "
        "On failure explain exact reason/time, retain evidence and continue diagnosis without relaxed gates, raised damping, overwritten outputs or duplicate solvers. "
        "On pass inspect/generate comparison figures, report quantified Chinese findings and evaluate the next gated validation. No automatic 15-s/2Tv admission. "
        "Uniform x-periodic cell reduction is only a possible cost-saving test, not yet verified or applied; the full-width refined run may take much longer than the old4-day estimate. "
        "k1e-3/1e-4 delivery remains accepted; old late-Q/KEEP must not indefinitely block it. Continue remaining authorized delivery, complex-boundary tests, cleanup/Git as justified. "
        "Use one verified same-thread completion for a genuinely new long stage; never rearm this worker or send connectivity tests.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(thread=args.thread, utc=utc(), terminal=report.copy(), message=message), stream, indent=2)
    try:
        q = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message], capture_output=True,
            timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True, queue_status="queued" if q.returncode == 0 else "failed_no_retry", queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True, queue_status="uncertain_no_retry", queue_error=str(error))
    save(STATE, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare", action="store_true"); p.add_argument("--worker", action="store_true")
    p.add_argument("--codex"); p.add_argument("--thread")
    args = p.parse_args()
    if args.prepare: return prepare()
    assert args.codex and Path(args.codex).is_file() and args.thread
    if args.worker: return worker(args)
    assert not STATE.exists() and read(TESTS/"logs/k5_grid320_r1.check.json")["original_stress_guard_passed"]
    count = subprocess.check_output(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip()
    assert count == "0"
    with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--codex", args.codex, "--thread", args.thread]
        child = subprocess.Popen(argv, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(TAG+".launch.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(pid=child.pid, thread=args.thread, argv=argv), stream, indent=2)
    print(json.dumps(dict(pid=child.pid, state=str(STATE))))


if __name__ == "__main__": main()
