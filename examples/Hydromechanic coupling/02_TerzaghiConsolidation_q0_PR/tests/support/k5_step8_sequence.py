"""One bounded 8/4-microsecond short candidate; retain the accepted 5/2.5 baseline."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import k5_cell_sequence as cell
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify

BASE = cell.TAG
TAG = "k5_step8_1s_r1"
STATE = TESTS/"logs"/(TAG+".status.json")
VARIANTS = [("015c", ".15", ".000008"), ("015h", ".15", ".000004"),
            ("1c", "1", ".000008"), ("1h", "1", ".000004")]


def prepare():
    patch = "*** Begin Patch\n"
    for suffix, duration, dt in VARIANTS:
        old, label = BASE+"_"+suffix, TAG+"_"+suffix
        xml = (TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        for key in ("DtIni", "DtFixed"):
            xml, count = re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")', lambda m: m[1]+dt+m[2], xml)
            assert count == 1
        xml = xml.replace("Initial step equals the validated fixed step", "Candidate initial step; short-window verification required")
        xml = xml.replace("Formal fixed step; conductivity-specific stability limit", "Candidate fixed step; not yet admitted to a long run")
        bat = (TESTS/"configs"/("x"+old+"_win64_GPU.bat")).read_text(encoding="utf8").replace("set case="+old, "set case="+label)
        steps = int(Decimal(duration)/Decimal(dt))
        bat, count = re.subn(r'-nsteps:\d+', '-nsteps:'+str(steps), bat); assert count == 1
        for path, content in ((TESTS/"configs"/(label+"_Def.xml"), xml), (TESTS/"configs"/("x"+label+"_win64_GPU.bat"), bat)):
            assert not path.exists()
            patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def compare_reference(report, suffix):
    """Different dt, same saved actual times; this is not a half-step comparison."""
    lf, rf = [TESTS/"outputs"/(tag+"_"+suffix) for tag in (BASE, TAG)]
    initial = cell.probe.native(lf, 0); top = initial.z > .996
    count = len(list((lf/"data").glob("Part_*.bi4")))
    peaks = dict(pressure_rms_pa=0., top_settlement_difference_mm=0., max_total_stress_difference_pa=0.)
    for i in range(count):
        a, b = cell.probe.native(lf, i), cell.probe.native(rf, i)
        assert np.array_equal(a.id, b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8
        p = float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
        u = abs(float((a.z[top]-b.z[top]).mean()*1000))
        s = float(abs((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)).max())
        peaks = {key:max(peaks[key], value) for key,value in zip(peaks,(p,u,s))}
        assert p <= 5 and u <= .005, "Reference-step pressure/settlement comparison failed"
    report["comparisons"].append(dict(kind="reference_step", left=BASE+"_"+suffix, right=TAG+"_"+suffix,
        samples=count, passed=True, **peaks)); save(STATE, report)


def worker(args):
    assert not STATE.exists()
    # Reuse the frozen cell runner and unchanged guards. Only the test identity
    # and status destination are selected in memory; no old source/state is edited.
    cell.TAG, cell.STATE = TAG, STATE
    report = dict(status="running", stage="prerequisites", worker_pid=os.getpid(), runs=[], comparisons=[], started_utc=utc())
    save(STATE, report)
    try:
        gate = TESTS/"logs/k5_cell_review_r1.check.json"
        visual = TESTS/"logs/k5_cell_review_r1.visual.json"
        reviewed = read(gate)
        assert reviewed["audit_passed"] and read(visual)["inspected"] and not reviewed["full_cycle_admitted"]
        verify(reviewed["evidence"])
        report["checkpoint"] = subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip()
        report["inputs"] = [bound(p) for p in (Path(__file__), Path(cell.__file__), Path(cell.probe.__file__), cell.probe.READER,
            TESTS/"support/k5_grid320_sequence.py", TESTS/"support/formal_release_sequence.py", TESTS/"support/mdbc_gpu_vector_run.py", gate, visual,
            REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe", REPO/"bin/windows/GenCase_win64.exe", REPO/"bin/windows/PartVTK_win64.exe")]
        for suffix, _, _ in VARIANTS:
            report["inputs"] += [bound(TESTS/"configs"/name) for name in (TAG+"_"+suffix+"_Def.xml", "x"+TAG+"_"+suffix+"_win64_GPU.bat")]
        for suffix,duration,dt in VARIANTS:
            cell.run(report,suffix,duration,dt)
            compare_reference(report,suffix)
            if suffix == "015h": cell.compare(report,TAG+"_015c",TAG+"_015h","half")
            if suffix == "1c": cell.compare(report,TAG+"_015c",TAG+"_1c","prefix")
            if suffix == "1h":
                cell.compare(report,TAG+"_015h",TAG+"_1h","prefix"); cell.compare(report,TAG+"_1c",TAG+"_1h","half")
        verify(report["inputs"])
        report.update(status="step8_1s_pairs_passed_pending_review",stage="review")
    except Exception as error:
        report.update(status="step8_sequence_rejected_or_interrupted",reason=str(error))
    report["finished_utc"] = utc(); save(STATE,report)
    message = (f"User-authorized same-thread bounded time-step/cost diagnostic {TAG}, not a new human observation. Detected {report['status']}. "
        f"Read {STATE}, its queue_attempt.json, tests/notes/formal_release_r1.md and logs/k5_cell_review_r1.check.json plus visual.json before claims. "
        "Only fresh .15/1-s 8e-6/4e-6 pairs, dp=.003125,width=.025,eta=.04,xi=.1 were admitted, using the unchanged frozen cell runner. "
        "Verify owned exits/stop reason, native IDs/actual times/build-input-output hashes, original geometry/drainage/100-Pa stress/top-gap/HG guards and equivalent1000N/m within.001(actual250). "
        "Inspect all-sample5-Pa/.005-mm half checks and the separate reference-step comparisons to accepted5e-6/2.5e-6 controls, plus same-dt .15-s native prefixes. "
        "Generate/inspect pressure/settlement/stress/Q comparison plots and observed timing before deciding a later15-s diagnostic. FixedDt is not automatically clipped by pore diffusion control; do not presume8e-6 stable. "
        "If failed, report exact reason/time and preserve evidence; retain accepted5e-6/2.5e-6 as fallback, no repeated dt search, raised damping, relaxed thresholds, duplicate solver or overwritten output. "
        "No automatic15-s/2Tv/formal admission. Oldformal k5 failed at.10001guard(lastPART.2), not2Tv; k3/k4 accepted delivery stands. "
        "Continue authorized delivery after causal/cost review without another progress question; no production/formal changes yet. Never restart/rearm this one-shot worker or send connectivity tests.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x",encoding="utf8") as stream:
        json.dump(dict(thread=args.thread,utc=utc(),terminal=report.copy(),message=message),stream,indent=2)
    try:
        q = subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True,queue_status="queued" if q.returncode == 0 else "failed_no_retry",queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True,queue_status="uncertain_no_retry",queue_error=str(error))
    save(STATE,report)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare",action="store_true");p.add_argument("--worker",action="store_true")
    p.add_argument("--codex");p.add_argument("--thread");args=p.parse_args()
    if args.prepare:return prepare()
    assert args.codex and Path(args.codex).is_file() and args.thread
    if args.worker:return worker(args)
    assert not STATE.exists() and read(TESTS/"logs/k5_cell_review_r1.check.json")["audit_passed"]
    count=subprocess.check_output(["powershell","-NoProfile","-Command","@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"],text=True).strip()
    assert count == "0"
    with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
        argv=[sys.executable,"-B",str(Path(__file__).resolve()),"--worker","--codex",args.codex,"--thread",args.thread]
        child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(TAG+".launch.json")).open("x",encoding="utf8") as stream:json.dump(dict(pid=child.pid,thread=args.thread,argv=argv),stream,indent=2)
    print(json.dumps(dict(pid=child.pid,state=str(STATE))))


if __name__ == "__main__":main()
