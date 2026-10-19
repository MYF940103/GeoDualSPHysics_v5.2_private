"""Twenty-step SPR-off regression against both retained G3 HG states."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

from mdbc_gpu_vector_run import TESTS, bound, read, verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend", choices=("debug", "release"), required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--build-log", required=True)
    p.add_argument("--adopt-off", help="Adopt the completed solver from an earlier analysis-only rejection")
    args = p.parse_args()
    receipt = TESTS / "logs" / (args.tag + ".check.json")
    if receipt.exists():
        raise FileExistsError(receipt)
    snapshot = read(TESTS / "logs/gpu_g3_verified.snapshot.json")
    reader_path = TESTS / "logs/hg_gpu_off_compare_r2.build.json"
    reader = read(reader_path)
    inputs = [bound(__file__), bound(Path(__file__).with_name("mdbc_gpu_vector_run.py")), bound(args.build_log),
              bound(reader_path), dict(path=reader["executable"], sha256=reader["executable_sha256"])]
    runs = []
    for state in ("off", "on"):
        old_tag = "hg_gpu_g3_short_r1_" + state + "_gpu_" + args.backend
        old_record = TESTS / "logs" / (old_tag + ".run.json")
        old = read(old_record)
        assert old["completed"] and old["solver"]["exit_code"] == 0
        frozen = next(e for e in snapshot["entries"] if e["path"] == old["executable"])
        inputs += old["inputs"] + old["outputs"] + [bound(old_record), bound(old["executable"]),
                   dict(path=str(Path(snapshot["snapshot"]) / frozen["relative"]), sha256=frozen["sha256"])]
        name = args.tag + "_hg_" + state
        output = TESTS / "outputs" / name
        assert not output.exists()
        argv = [str(output) if str(value) == str(TESTS / "outputs" / old_tag) else str(value) for value in old["arguments"]]
        runs.append(dict(state=state, reference=old_tag, output=str(output), argv=[old["executable"]] + argv))
    if args.adopt_off:
        prior = read(args.adopt_off)
        adopted = prior["runs"][0]
        assert adopted["state"] == "off" and adopted["exit_code"] == 0 and adopted["owned_process_exited"]
        assert adopted["reference"] == runs[0]["reference"]
        verify(adopted["outputs"])
        inputs += [bound(args.adopt_off)] + adopted["outputs"]
        runs[0].update(adopted)
        runs[0]["adopted_from"] = args.adopt_off
    verify(inputs)
    result = dict(passed=False, status="running", inputs=inputs, runs=runs, utc=datetime.now(timezone.utc).isoformat())
    try:
        for run in runs:
            name = Path(run["output"]).name
            stdout, stderr = [TESTS / "logs" / (name + s) for s in (".stdout.log", ".stderr.log")]
            started = time.perf_counter()
            if not run.get("adopted_from"):
                with stdout.open("xb") as out, stderr.open("xb") as err:
                    child = subprocess.Popen(run["argv"], cwd=Path(run["argv"][0]).parent, stdout=out, stderr=err,
                                             creationflags=subprocess.CREATE_NO_WINDOW)
                    run["pid"] = child.pid
                    try:
                        run["exit_code"] = child.wait(timeout=180)
                    finally:
                        if child.poll() is None:
                            child.kill()
                            child.wait()
                    run["owned_process_exited"] = child.poll() is not None
                run["wall_seconds"] = time.perf_counter() - started
            assert run["exit_code"] == 0
            text = (Path(run["output"]) / "Run.out").read_text(errors="replace")
            assert "Finished execution (code=0)." in text
            check = TESTS / "logs" / (args.tag + "_hg_" + run["state"] + ".exact.json")
            argv = [reader["executable"], str(TESTS / "outputs" / run["reference"] / "data"),
                    str(Path(run["output"]) / "data"), str(check), "1040", "0.00001"]
            checked = subprocess.run(argv, capture_output=True, timeout=60)
            run["comparison_exit_code"] = checked.returncode
            run["comparison"] = read(check)
            run["outputs"] = [bound(f) for f in Path(run["output"]).rglob("*") if f.is_file()] + [bound(stdout), bound(stderr), bound(check)]
            assert checked.returncode == 0 and run["comparison"]["passed"]
            print(name + " all native arrays 0 ULP", flush=True)
        verify(inputs)
        result.update(passed=True, status="spr_off_both_hg_states_exact", physical_acceptance=False)
    except Exception as error:
        result["failure"] = str(error)
        raise
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        with receipt.open("x", encoding="utf8") as stream:
            json.dump(result, stream, indent=2)


if __name__ == "__main__":
    main()
