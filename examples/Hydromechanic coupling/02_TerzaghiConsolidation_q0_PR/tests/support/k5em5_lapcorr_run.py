"""Isolated near-drainage Darcy moments. No full-run or production admission."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import time
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify
import k5_guard_probe as probe

TAG = "k5em5_lapcorr_r1"
BUILD = TESTS/"logs/k5em5_lapcorr_r1.build.json"


def prepare():
    patch = "*** Begin Patch\n"
    for v in ("c", "h"):
        old = "k5em5_uniform_dt_r1_"+v
        label = TAG+"_"+v
        xml = (TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        bat = (TESTS/"configs"/("x"+old+"_win64_GPU.bat")).read_text(encoding="utf8")
        bat = bat.replace(old, label).replace("-gpu:0 -ompthreads:1", "-cpu -ompthreads:8")
        bat = bat.replace('set dualsphysics="%dirbin%/DualSPHysics5.2_GEO_win64.exe"',
                          'set dualsphysics="tests/outputs/k5em5_lapcorr_r1_bin/DualSPHysicsCpuProbe.exe"')
        bat = bat.replace("rem Fresh uniform-1D 2Tv diagnostic; original safety limits and accepted fixed step unchanged.",
                          "rem Isolated .3-s Darcy-moment diagnostic only; no full-cycle admission.")
        for path, text in ((TESTS/"configs"/(label+"_Def.xml"), xml),
                           (TESTS/"configs"/("x"+label+"_win64_CPU.bat"), bat)):
            assert not path.exists()
            patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+s for s in text.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run(v):
    label = TAG+"_"+v
    state = TESTS/"logs"/(label+".status.json")
    folder = TESTS/"outputs"/label
    assert not state.exists() and not folder.exists()
    build = read(BUILD)
    assert build["built"] and not build["production_modified"]
    verify(build["inputs"]+[dict(path=build["executable"], sha256=build["executable_sha256"])])
    assert subprocess.check_output(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip() == "0"
    bat = TESTS/"configs"/("x"+label+"_win64_CPU.bat")
    inputs = [bound(p) for p in (Path(__file__), BUILD, bat, TESTS/"configs"/(label+"_Def.xml"), probe.READER, Path(build["executable"]))]
    r = dict(status="running", started_utc=utc(), worker_pid=os.getpid(), full_admitted=False,
             production_modified=False, inputs=inputs, first_stress_failure=None, numerical_safety_passed=True)
    log = TESTS/"logs"/(label+".log")
    history = TESTS/"figures"/(label+"_runtime.csv")
    p = None
    try:
        with log.open("xb") as stream, history.open("x", newline="", encoding="utf8") as out:
            p = subprocess.Popen([os.environ["ComSpec"], "/d", "/c", str(bat)], cwd=CASE, stdout=stream,
                                 stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            r["owned_cmd_pid"] = p.pid
            initial, writer, index = None, None, 0
            def consume(i):
                nonlocal initial, writer
                a = probe.native(folder, i)
                if initial is None:
                    initial = a.copy()
                m = probe.metrics(a, initial, .01)
                if not m["stress_guard_passed"]:
                    r["numerical_safety_passed"] = False
                    if r["first_stress_failure"] is None:
                        r["first_stress_failure"] = m.copy()
                if writer is None:
                    writer = csv.DictWriter(out, fieldnames=list(m))
                    writer.writeheader()
                writer.writerow(m)
                out.flush()
                r.update(checked_frames=i+1, last_metrics=m)
            while p.poll() is None:
                count = len(list((folder/"data").glob("Part_*.bi4")))
                while index < count-1:
                    consume(index)
                    index += 1
                r["updated_utc"] = utc()
                save(state, r)
                time.sleep(2)
            assert p.returncode == 0, "Solver/BAT failed; inspect "+str(log)
            count = len(list((folder/"data").glob("Part_*.bi4")))
            while index < count:
                consume(index)
                index += 1
        steps = 30000 if v == "c" else 60000
        assert index == 301 and r["last_metrics"]["step"] == steps and abs(r["last_metrics"]["time_s"]-.3) < 1e-7
        text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
        assert "Finished execution (code=0)." in text
        counts = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
        assert counts and tuple(map(int, counts.groups())) == (steps*2, steps, steps, steps*2)
        cache = re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
        assert cache and tuple(map(int, cache.groups())) == (steps+1, steps-1)
        tau = re.search(r"max\(dt/tau\)=([\d.eE+-]+)", text)
        assert tau and float(tau[1]) <= .2
        verify(inputs)
        r.update(status="completed_pending_causal_review", hg_runtime_passed=True,
                 outputs=[bound(p) for p in folder.rglob("*") if p.is_file()]+[bound(log), bound(history)])
    except Exception as error:
        r.update(status="diagnostic_failed_or_interrupted", reason=str(error))
    finally:
        if p is not None:
            if p.poll() is None:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                p.wait()
            r.update(exit_code=p.returncode, owned_exited=True)
        r["finished_utc"] = utc()
        save(state, r)
    print(json.dumps({k:r[k] for k in ("status", "first_stress_failure", "full_admitted")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--variant", choices=("c", "h"))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        assert args.variant
        run(args.variant)
