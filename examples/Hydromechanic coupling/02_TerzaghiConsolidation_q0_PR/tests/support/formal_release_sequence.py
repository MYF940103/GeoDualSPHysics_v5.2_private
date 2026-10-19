"""Fresh formal-program short equivalence, publish verified k1e-4, then formal k1e-3."""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from mdbc_gpu_vector_run import TESTS, bound, read, verify

CASE, REPO = TESTS.parent, TESTS.parents[3]
sys.path.insert(0, str(CASE/"support"))
import release_case as review

TAG = "formal_release_k3_r1"
STATE = TESTS/"logs"/(TAG+".status.json")
STEM = "CaseTerzaghiConsolidation_q0_PR_full_"
READER = REPO/"bin/windows/ReadHydroMechPart_win64.exe"


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf8")
    for i in range(6):
        try:
            tmp.replace(path); return
        except PermissionError:
            if i == 5:
                print("Retained status temporary: "+str(tmp), flush=True); return
            time.sleep(.2)


def prerequisites():
    assert read(TESTS/"logs/gpu_full_2tv_r1.visual.json")["passed"]
    assert read(TESTS/"logs/release_reader_r1.check.json")["passed"]
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    remote = subprocess.check_output(["git", "-C", str(REPO), "ls-remote", "--heads", "origin", "u-pw"], text=True).split()[0]
    assert head == remote, "Verified source checkpoint must exist locally and remotely"
    assert not subprocess.check_output(["git", "-C", str(REPO), "diff", "--name-only", "--", "src/source", "src/VS"], text=True).strip()
    entries = [bound(p) for p in (Path(__file__), CASE/"support/release_case.py", READER,
        REPO/"bin/windows/DualSPHysics5.2CPU_win64.exe", REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe",
        REPO/"bin/windows/GenCase_win64.exe", REPO/"bin/windows/PartVTK_win64.exe",
        TESTS/"logs/gpu_full_2tv_r1.visual.json", TESTS/"logs/release_reader_r1.check.json")]
    for key in ("k1em3", "k1em4", "k1em5"):
        entries += [bound(CASE/(STEM+key+"_Def.xml"))]
        entries += [bound(CASE/("x"+STEM+key+"_win64_"+b+".bat")) for b in ("CPU", "GPU")]
    assert not (CASE/(STEM+"k1em3_release_GPU_out")).exists()
    assert not (CASE/(STEM+"k1em4_release_GPU_out")).exists()
    verify(entries)
    return head, entries


def child(report, key, argv, output=None):
    report.update(stage=key, updated_utc=utc()); save(STATE, report)
    log = TESTS/"logs"/(TAG+"_"+key+".log")
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=CASE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        item = dict(stage=key, pid=process.pid, argv=argv)
        report["children"].append(item); save(STATE, report)
        next_part, initial = 0, None
        try:
            while process.poll() is None:
                if output and (output/"data").exists():
                    parts = sorted((output/"data").glob("Part_*.bi4"))
                    # A successor PART proves the previous file has finished writing.
                    while next_part < max(0, len(parts)-1):
                        a = review.native(READER, output, next_part)
                        if initial is None:
                            initial = a.copy()
                            xml = next(x for x in output.glob("*.xml") if ET.parse(x).find("execution/particles") is not None)
                            m = review.model(xml)
                        metrics = review.inspect(a, initial, m)
                        report.update(last_checked_time_s=metrics["time_s"], last_checked_tv=metrics["tv"], checked_frames=next_part+1)
                        next_part += 1
                report["updated_utc"] = utc(); save(STATE, report)
                time.sleep(15)
            item.update(exit_code=process.returncode, owned_process_exited=True, log=bound(log))
            assert process.returncode == 0, key+" failed; inspect its retained log"
        finally:
            if process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                process.wait()
                item.update(exit_code=process.returncode, owned_process_exited=True, stopped_by_monitor=True)
            save(STATE, report)


def smoke(report, backend):
    name = "formal_program_"+backend+"_r1"
    path = TESTS/"logs"/(name+".check.json")
    if path.exists():
        completed = read(path)
        assert completed["passed"] and completed["initial_final_physical_fields_0_ulp"] and completed["nondivisible_final_output_passed"]
        verify(completed["evidence"])
        report.setdefault("adopted_smokes", []).append(bound(path))
        return
    definition = TESTS/"configs"/(name+"_Def.xml")
    output = TESTS/"outputs"/name
    assert not definition.exists() and not output.exists()
    text = (CASE/(STEM+"k1em4_Def.xml")).read_text(encoding="utf8")
    import re
    text, count = re.subn(r'(<parameter key="TimeMax" value=")[^"]*(")', r'\g<1>0.15\2', text)
    assert count == 1
    text, count = re.subn(r'(<parameter key="TimeOut" value=")[^"]*(")', r'\g<1>0.1\2', text)
    assert count == 1  # TimeMax deliberately not divisible by TimeOut.
    with definition.open("x", encoding="utf8") as stream:
        stream.write(text)
    prefix = output/name
    child(report, backend+"_gencase", [str(REPO/"bin/windows/GenCase_win64.exe"), str(definition.with_suffix("")), str(prefix), "-save:all"])
    exe = "DualSPHysics5.2CPU_win64.exe" if backend == "cpu" else "DualSPHysics5.2_GEO_win64.exe"
    child(report, backend+"_smoke", [str(REPO/"bin/windows"/exe), "-cpu" if backend == "cpu" else "-gpu:0",
        "-ompthreads:1", "-stable", "-mdbc", str(prefix), str(output), "-dirdataout", "data", "-svres", "-svextraparts:1", "-nsteps:15000"], output)
    parts = sorted((output/"data").glob("Part_*.bi4"))
    assert len(parts) == 3, "Require initial, 0.1-s and nondivisible 0.15-s final PART"
    reference_path = TESTS/"outputs"/("gpu_full_save_"+backend+"_r1")/"state.csv"
    reference = pd.read_csv(reference_path, float_precision="round_trip")
    fields = ["x", "y", "z", "vx", "vy", "vz", "rho", "pressure", "sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz", "kplastic"]
    for i, b in ((0, reference.iloc[:1000]), (len(parts)-1, reference.iloc[-1000:])):
        a = review.native(READER, output, i)
        assert abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-7
        assert a[fields].to_numpy(dtype="<f8").tobytes() == b[fields].to_numpy(dtype="<f8").tobytes(), backend+" real-program physical fields differ"
    with path.open("x", encoding="utf8") as stream:
        json.dump(dict(passed=True, backend=backend, initial_final_physical_fields_0_ulp=True,
            nondivisible_final_output_passed=True,
            final_time_s=float(a.time_s.iloc[0]), saved_frames=len(parts),
            scope="Initial/final real-program versus production-step companion, not every differently scheduled output",
            evidence=[bound(p) for p in (definition, parts[0], parts[-1], reference_path, REPO/"bin/windows"/exe,
                READER, REPO/"src/source/JSphCpuSingle.cpp", REPO/"src/source/JSphGpuSingle.cpp")]), stream, indent=2)


def publish_k4(report):
    report.update(stage="publish_k4_copy", updated_utc=utc()); save(STATE, report)
    source = TESTS/"outputs/gpu_full_2tv_gpu_r1"
    output = CASE/(STEM+"k1em4_release_GPU_out")
    assert not output.exists()
    output.mkdir()
    shutil.copytree(source/"data", output/"data")
    for name in ("Run.out", "complete.json", "hourglass.csv", "hourglass_final.csv"):
        shutil.copy2(source/name, output/name)
    original = TESTS/"outputs/gpu_full_2tv_gpu_r1_input/CaseTCq0_gpu_full_2tv_gpu_r1.xml"
    shutil.copy2(original, output/"published_case.xml")
    hashes = []
    for path in output.rglob("*"):
        if path.is_file():
            src = original if path.name == "published_case.xml" else source/path.relative_to(output)
            assert review.digest(path) == review.digest(src)
            hashes.append(dict(path=str(path), sha256=review.digest(path)))
    receipt = TESTS/"logs/gpu_full_2tv_gpu_r1.run.json"
    with (output/"release_provenance.json").open("x", encoding="utf8") as stream:
        json.dump(dict(accepted_k1em4_adoption=True, formal_program_short_equivalence_passed=True,
            source=str(source), source_receipt=str(receipt), source_receipt_sha256=review.digest(receipt),
            source_checkpoint=report["checkpoint"], files=hashes,
            limitation="Published validated production-step companion data after actual CPU/GPU program short equivalence; not a second formal-BAT solver run."), stream, indent=2)
    bat = CASE/("x"+STEM+"k1em4_win64_GPU.bat")
    child(report, "publish_k4_plots", [os.environ["ComSpec"], "/d", "/c", str(bat), "-postprocess"])


def worker(args):
    assert not STATE.exists(), "One-shot worker must not be restarted"
    report = dict(status="running", stage="prerequisites", worker_pid=os.getpid(), started_utc=utc(), children=[])
    save(STATE, report)
    try:
        report["checkpoint"], report["inputs"] = prerequisites()
        smoke(report, "gpu"); smoke(report, "cpu")
        publish_k4(report)
        bat = CASE/("x"+STEM+"k1em3_win64_GPU.bat")
        child(report, "formal_k1em3", [os.environ["ComSpec"], "/d", "/c", str(bat)], CASE/(STEM+"k1em3_release_GPU_out"))
        assert read(CASE/"figures/full_validation_release_k1em3_GPU.check.json")["passed"]
        verify(report["inputs"])
        report.update(status="formal_k3_completed_k4_published_pending_visual_review", stage="review")
    except Exception as error:
        report.update(status="formal_release_rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = utc(); save(STATE, report)
    message = (f"User-authorized same-thread formal delivery continuation {TAG}, not a new human observation. Detected {report['status']}. "
        f"Read {STATE}, {TESTS/'logs'/(TAG+'.queue_attempt.json')} and tests/notes/formal_release_r1.md before claims. "
        "Do not restart/rearm this worker or duplicate solvers. CPU/GPU full k1e-4 was accepted within the user's Oct16 1D scope; "
        "code checkpoint was verified local/remote. This stage first tests real CPU/GPU programs against saved companion initial/final fields, "
        "then publishes the already accepted k1e-4 dataset without rerunning 2Tv, and runs the actual formal k1e-3 GPU BAT including native plots. "
        "Inspect exact stop/time, owned exits, hashes, real-program smoke receipts, published provenance and all native safety/summary checks. "
        "Inspect root figures/full_validation_release_k1em3_GPU and k1em4_GPU PNGs, quantify theory errors, settlement and Q, and report proactively in Chinese. "
        "If analysis failed, repair only new analysis, not a completed solver. If runtime failed, explain actual reason/time and continue diagnosis without relaxed guards, "
        "overwrite or duplicate processes. On pass continue the authorized formal k1e-5 calculation using its own Cv and stable step, then all-three final plots, "
        "later complex-boundary validation, dependency-aware cleanup and final verified Git backup. k1e-5 is not yet run; no full-cycle half validation, plasticity, "
        "large-rotation, complex-boundary or exact-HG-restart claim. Old late-Q does not indefinitely block the provisionally accepted 1D delivery. "
        "Use one verified same-thread completion mechanism for the next long stage; do not wait for another progress request or send connectivity tests.")
    intent = TESTS/"logs"/(TAG+".queue_attempt.json")
    with intent.open("x", encoding="utf8") as stream:
        json.dump(dict(thread=args.thread, terminal=report.copy(), message=message, utc=utc()), stream, indent=2)
    try:
        q = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message], capture_output=True,
                           timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True, queue_status="queued" if q.returncode == 0 else "failed_no_retry",
                      queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True, queue_status="uncertain_no_retry", queue_error=str(error))
    save(STATE, report)


def main():
    global STATE
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--codex", required=True)
    p.add_argument("--thread", default=os.environ.get("CODEX_THREAD_ID"))
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true"); modes.add_argument("--launch", action="store_true"); modes.add_argument("--worker", action="store_true")
    modes.add_argument("--smoke-only", action="store_true")
    args = p.parse_args()
    assert args.thread and Path(args.codex).is_file()
    if args.smoke_only:
        STATE = TESTS/"logs/formal_program_gate_r1.status.json"
        assert not STATE.exists()
        report = dict(status="running", stage="real_program_smoke", children=[], started_utc=utc())
        try:
            smoke(report, "gpu"); smoke(report, "cpu")
            report.update(status="passed", nondivisible_final_output_passed=True)
        except Exception as error:
            report.update(status="failed", reason=str(error)); save(STATE, report); raise
        report["finished_utc"] = utc(); save(STATE, report)
        print(json.dumps(dict(passed=True, state=str(STATE))))
        return
    if args.worker:
        return worker(args)
    assert not STATE.exists()
    checkpoint, entries = prerequisites()
    if args.check:
        print(json.dumps(dict(checked=True, checkpoint=checkpoint, inputs=len(entries)))); return
    idle = subprocess.run(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*','gpu_coupled','mechanics' -ErrorAction SilentlyContinue).Count"], capture_output=True, text=True)
    assert idle.returncode == 0 and idle.stdout.strip() == "0"
    log = TESTS/"logs"/(TAG+".worker.log")
    with log.open("xb") as stream:
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--codex", args.codex, "--thread", args.thread]
        process = subprocess.Popen(argv, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(TAG+".launch.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(pid=process.pid, thread=args.thread, argv=argv, checkpoint=checkpoint, inputs=entries), stream, indent=2)
    print(json.dumps(dict(pid=process.pid, state=str(STATE))))


if __name__ == "__main__":
    main()
