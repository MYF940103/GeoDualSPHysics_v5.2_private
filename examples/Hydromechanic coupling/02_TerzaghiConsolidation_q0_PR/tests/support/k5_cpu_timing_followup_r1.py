"""One-shot same-thread continuation for the new CPU timing review, never the old GPU watcher."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from formal_release_sequence import CASE, TESTS, save, utc

TAG="k5_cpu_timing_followup_r1"
STATE=TESTS/"logs"/(TAG+".status.json")
REVIEW=TESTS/"logs/k5_cpu_timing_review_r1.status.json"


def worker(codex,thread):
    assert not STATE.exists()
    r=dict(status="waiting",pid=os.getpid(),review=str(REVIEW),thread=thread,started_utc=utc())
    save(STATE,r)
    while True:
        review=json.loads(REVIEW.read_text(encoding="utf8"))
        if review["status"] not in ("running","waiting_t1"):break
        time.sleep(10)
    message=(f"User-authorized same-thread CPU timing continuation {TAG}, not a new human observation. Detected {review['status']}. "
        f"Read {REVIEW}, tests/logs/k5_cpu_timing_r1.status.json, tests/notes/k5_cpu_timing_r1.md and current tests/logs/k5_full_r1.status.json before claims. "
        "Only fresh .15-s CPU 1/2/4-thread same-physics dt5e-6 tests were prepared; do not restart completed t1 or any old worker. The first wrapper's postprocessing rejected the absent CPU HydroMechLoadAce field, not solver failure; review adopted its normal .15-s result. "
        "Verify owned exits, actual times/native IDs/build-input-output hashes, all-sample geometry/drainage/post-.1s100-Pa stress/top-gap and HG guards, and 5-Pa/.005-mm CPU/GPU comparisons. CPU native force telemetry is absent: never report that force-observation guard passed. "
        "CPU1 loop was720.948547s for30000steps; retained GPU same-physics15-s loop16043.383789s for3000000steps. Compare actual t2/t4 timings; CPU ran alongside existing GPU/monitor, so do not label this a perfectly isolated whole-run benchmark. "
        "User Oct21 explicitly authorizes switching to CPU if measurably faster, and trying a larger step if both are too slow. Do not assume CPU is faster from the old small-grid runs. If CPU is chosen, first close the native load-observation gap with minimal output-only changes and validate; then fresh-start only, no exact HG PART restart. "
        "For excessive day-scale cost, a bounded new candidate6.25e-6/3.125e-6 is authorized: original geometry,width.025,dp.003125,eta.04,xi.1,1-ms dense .15-s coarse/half first, then1s/15s only after review, original all-sample5-Pa/.005-mm and100-Pa plus natural-step/HG gates unchanged. Old8e-6 failed; do not blindly reuse it, raise damping, relax thresholds or implement TPI merely for speed. "
        "The original k5_full_r1 GPU solver/worker are still active unless status proves otherwise; never start duplicate GPU solvers or rearm that watcher. Before any justified fresh replacement, verify exact ownership, record intentional retirement/actual sealed time, stop old watcher before its owned solver, preserve all partial output, and explicitly explain loss of exact-HG restart. "
        "Continue controlled backend/step decision and the user's authorized delivery without another progress question. Use one verified completion mechanism for a genuinely new admitted long stage. "
        "Root three formal TimeOut values now correspond toDeltaTv=.005; k3/k4 already complete, no reruns. Three retired BAT were recoverably moved to tests/outputs/retired_root_inputs_r1; old XML kept for dependencies, raw outputs unchanged. Verified local/remote checkpoint176b84e. Production source was not changed for this timing stage; new implementation regressions must be repaired, not published as accepted. "
        "Report the outcome proactively in Chinese. This timing watcher queues once; never restart/rearm it or send a connectivity self-test.")
    attempt=TESTS/"logs"/(TAG+".queue_attempt.json")
    with attempt.open("x",encoding="utf8") as stream:json.dump(dict(utc=utc(),thread=thread,terminal_status=review["status"],message=message),stream,indent=2)
    try:
        q=subprocess.run([codex,"queue","--thread",thread,"--message",message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(status="queued" if q.returncode==0 else "failed_no_retry",returncode=q.returncode,reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:r.update(status="uncertain_no_retry",reason=str(error))
    r["finished_utc"]=utc();save(STATE,r)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--worker",action="store_true");p.add_argument("--codex");p.add_argument("--thread");a=p.parse_args()
    if a.worker:worker(a.codex,a.thread)
    else:
        assert not STATE.exists() and REVIEW.exists()
        prior=json.loads((TESTS/"logs/k5_full_r1.launch.json").read_text(encoding="utf8"))
        codex=prior["argv"][prior["argv"].index("--codex")+1];thread=prior["thread"];assert Path(codex).is_file()
        with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
            argv=[sys.executable,"-B",str(Path(__file__).resolve()),"--worker","--codex",codex,"--thread",thread]
            child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        with (TESTS/"logs"/(TAG+".launch.json")).open("x",encoding="utf8") as stream:json.dump(dict(pid=child.pid,argv=argv,thread=thread),stream,indent=2)
        print(json.dumps(dict(pid=child.pid,state=str(STATE))))
