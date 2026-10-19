"""Run fresh GPU manufactured fields using retained ordinary GenCase inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

TESTS = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def bound(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.file_digest(path.open("rb"), "sha256").hexdigest().upper())


def verify(items):
    for item in items:
        if bound(item["path"])["sha256"] != item["sha256"].upper():
            raise RuntimeError("Bound input changed: " + item["path"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--geometry", default="all")
    parser.add_argument("--slip", type=int, choices=(1, 2, 3))
    args = parser.parse_args()
    if not args.tag.replace("_", "").isalnum():
        raise ValueError("Simple tag required")
    receipt = TESTS / "logs" / (args.tag + ".check.json")
    if receipt.exists():
        raise FileExistsError(receipt)
    build = read(args.build)
    assert build["built"] and build["fixture"] == "mdbc_gpu_vector"
    prepare_path = TESTS / "logs/mdbc_plane_r2.prepare.json"
    prepare = read(prepare_path)
    assert prepare["status"] == "gencase_prepared_not_solver_validated" and not prepare["solver_started"]
    variants = [v for v in prepare["variants"] if (args.geometry == "all" or v["geometry"] == args.geometry)
                and (args.slip is None or v["slip_mode"] == args.slip)]
    assert len(variants) == (18 if args.geometry == "all" and args.slip is None else len(variants)) and variants
    inputs = build["inputs"] + build["runtime"] + [dict(path=build["executable"], sha256=build["executable_sha256"]),
                bound(args.build), bound(prepare_path), bound(__file__)]
    for v in variants:
        prepared = next(p for p in prepare["runs"] if p["label"] == v["label"])
        assert prepared["exit_code"] == 0
        inputs.extend(prepared["outputs"])
        output = TESTS / "outputs" / (args.tag + "_" + v["geometry"] + "_s" + str(v["slip_mode"]))
        if output.exists():
            raise FileExistsError(output)
    verify(inputs)
    result = dict(passed=False, status="running", utc=datetime.now(timezone.utc).isoformat(),
                  inputs=inputs, runs=[], physical_acceptance=False, time_integrated=False)
    failure = None
    try:
        for v in variants:
            name = args.tag + "_" + v["geometry"] + "_s" + str(v["slip_mode"])
            output = TESTS / "outputs" / name
            stdout, stderr = (TESTS / "logs" / (name + suffix) for suffix in (".stdout.log", ".stderr.log"))
            argv = [build["executable"], str(v["dimension"]), str(v["slip_mode"]), str(v["native_count"]),
                    str(v["wall_count"]), str(v["wall_roi_count"])]
            argv += [repr(x) for row in v["rotation"] for x in row]
            argv += ["-gpu", "-stable", ("-mdbc", "-mdbc_noslip", "-mdbc_freeslip")[v["slip_mode"] - 1],
                     v["prefix"], str(output), "-dirdataout", "data", "-svres", "-sv:none"]
            run = dict(variant=v, argv=argv, output=str(output), completed=False)
            result["runs"].append(run)
            with stdout.open("xb") as out, stderr.open("xb") as err:
                child = subprocess.Popen(argv, cwd=Path(build["executable"]).parent, stdout=out, stderr=err,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                run["pid"] = child.pid
                try:
                    run["exit_code"] = child.wait(timeout=180)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait()
                run["owned_process_exited"] = child.poll() is not None
            run["outputs"] = [bound(p) for p in (stdout, stderr)] + [bound(p) for p in output.rglob("*") if p.is_file()]
            if run["exit_code"] != 0:
                raise RuntimeError(name + ": fixture failed, inspect stderr and Run.out")
            done = read(output / "vector_complete.json")
            assert done["passed"] and done["native_count"] == v["native_count"] and done["wall_roi_count"] == v["wall_roi_count"]
            assert done["soil_roi_count"] == (12 if v["dimension"] == 2 else 48)
            assert done["soil_r_0ulp_count"] == v["soil_count"] and done["all_native_density_mls_oracle_checked"]
            assert done["inactive_and_no_support_fallbacks_checked"] and not done["time_integrated"]
            run.update(completed=True, metrics=done)
            print(name + " PASS", flush=True)
        verify(inputs)
        result.update(passed=True, status="manufactured_fields_passed_pending_review", inputs_unchanged=True)
    except Exception as error:
        failure = error
        result.update(status="failed", failure=str(error))
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        with receipt.open("x", encoding="utf8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
    if failure:
        raise failure


if __name__ == "__main__":
    main()
