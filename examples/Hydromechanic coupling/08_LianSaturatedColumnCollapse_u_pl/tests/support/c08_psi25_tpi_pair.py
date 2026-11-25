"""Run the two independent 1.2 s receivers serially after both short native checks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from c08_psi25_tpi_run import CASE, EXE, TESTS, now, record

TAG = "c08_psi25_tpi_paper_pair_r1"
LOG = TESTS / "logs"


def invoke(script, *args):
    subprocess.run([sys.executable, "-B", "-X", "utf8", str(TESTS/"support"/script), *args],
                   cwd=CASE, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path)
    parser.add_argument("--thread")
    options = parser.parse_args()
    if options.codex and (not options.codex.is_file() or not options.thread
                          or options.thread != os.environ.get("CODEX_THREAD_ID")):
        raise ValueError("Notification must use the current thread")
    for label in ("b004", "b0"):
        receipt = json.loads((LOG / f"c08_psi25_tpi_short_{label}_r1.native_review.json").read_text())
        if receipt.get("passed") is not True:
            raise ValueError(f"Short receiver {label} has not passed")
    if not EXE.is_file():
        raise FileNotFoundError(EXE)
    record(LOG/(TAG+".start.json"), dict(pid=os.getpid(), start_utc=now(), thread=options.thread,
           executable=str(EXE), order=["0.04", "0"], group="psi2p5"))
    results = {}
    for label, beta in (("b004", "0.04"), ("b0", "0")):
        tag = f"c08_psi25_tpi_paper_{label}_r1"
        stage = "solver"
        try:
            invoke("c08_psi25_tpi_run.py", "paper", "--beta", beta)
            stage = "native"
            invoke("c08_psi25_tpi_native.py", tag, "--window", "paper", "--beta", beta,
                   "--prefix", f"c08_psi25_tpi_short_{label}_r1")
            results[label] = dict(stage="reviewed", exit_code=0)
        except (OSError, subprocess.CalledProcessError) as error:
            results[label] = dict(stage=stage, error=str(error), exit_code=getattr(error, "returncode", None))
    reviewed = [label for label, result in results.items() if result["stage"]=="reviewed"]
    if reviewed:
        args = []
        for label in reviewed:
            args.extend(["--run", label, str(TESTS/"outputs"/f"c08_psi25_tpi_paper_{label}_r1")])
        try:
            invoke("c08_psi25_tpi_shape.py", "--tag", "paper_pair_r1", *args)
            results["figures"] = dict(stage="reviewed", exit_code=0)
        except (OSError, subprocess.CalledProcessError) as error:
            results["figures"] = dict(stage="shape", error=str(error), exit_code=getattr(error,"returncode",None))
    rc = int(len(reviewed)!=2 or results.get("figures",{}).get("exit_code")!=0)
    terminal = LOG/(TAG+".terminal.json")
    record(terminal, dict(ended_utc=now(), exit_code=rc, results=results))
    if options.codex:
        record(LOG/(TAG+".queue_attempt.json"), dict(thread=options.thread, time_utc=now(), terminal=str(terminal)))
        message = (f"C08 +2.5 degree same-material TPI beta pair is terminal: {terminal}. "
                   "Review the original calls, native receipts and Lian morphology and pressure figures. "
                   "Failed solver or derived review may have partial evidence. Preserve it. Repair analysis offline. "
                   "Continue the user's original diagnosis until shape validation; do not duplicate runs or notifications.")
        try:
            queue = subprocess.run([str(options.codex), "queue", "--thread", options.thread, "--message", message],
                                   timeout=45, capture_output=True)
            notification = dict(exit_code=queue.returncode)
        except (subprocess.TimeoutExpired, OSError) as error:
            notification = dict(status="delivery_unknown", error=str(error))
        record(LOG/(TAG+".queue_result.json"), notification)
    return rc


if __name__=="__main__":
    sys.exit(main())
