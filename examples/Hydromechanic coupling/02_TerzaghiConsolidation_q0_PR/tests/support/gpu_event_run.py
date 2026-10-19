"""Execute the two built event-predicate fixtures; no physical solver."""
import json
from pathlib import Path
import subprocess
from mdbc_gpu_vector_run import TESTS, bound, read, verify


def main():
    receipt = TESTS / "logs/gpu_drainage_event_r1.check.json"
    assert not receipt.exists()
    inputs = [bound(__file__), bound(Path(__file__).with_name("mdbc_gpu_vector_run.py"))]
    result = dict(passed=False, runs=[], inputs=inputs, coupled_validation=False)
    try:
        for config in ("Release", "Debug"):
            tag = "gpu_drainage_event_" + config + "_r1"
            manifest = TESTS / "logs" / (tag + ".build.json")
            build = read(manifest)
            assert build["built"] and build["fixture"] == "gpu_drainage_event"
            entries = build["inputs"] + build["runtime"] + [bound(manifest), dict(path=build["executable"], sha256=build["executable_sha256"])]
            verify(entries)
            inputs.extend(entries)
            check = TESTS / "logs" / (tag + ".check.json")
            out, err = (TESTS / "logs" / (tag + suffix) for suffix in (".stdout.log", ".stderr.log"))
            assert not check.exists()
            run = dict(configuration=config, completed=False)
            result["runs"].append(run)
            with out.open("xb") as stdout, err.open("xb") as stderr:
                child = subprocess.Popen([build["executable"], str(check)], stdout=stdout, stderr=stderr,
                                         cwd=Path(build["executable"]).parent, creationflags=subprocess.CREATE_NO_WINDOW)
                run["pid"] = child.pid
                try:
                    run["exit_code"] = child.wait(timeout=60)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait()
                run["owned_process_exited"] = child.poll() is not None
            assert run["exit_code"] == 0
            verify(entries)
            run.update(completed=True, metrics=read(check), outputs=[bound(f) for f in (check, out, err)])
            assert run["metrics"]["passed"] and run["metrics"]["cpu_gpu_predicates_equal"]
        result.update(passed=True, status="cpu_gpu_grid_event_predicates_passed")
    finally:
        with receipt.open("x", encoding="utf8") as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps([r["metrics"] for r in result["runs"]], indent=2))


if __name__ == "__main__":
    main()
