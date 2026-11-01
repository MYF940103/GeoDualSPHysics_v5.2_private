"""Offline recovery of completed r1 periodic jobs; never runs a program."""
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np

TESTS = Path(__file__).resolve().parent.parent
LOGS = TESTS / "logs"
NAME = "upl_p3_perm_time_periodic_ReleaseCPU_r1"
TARGET = LOGS / "upl_p3_perm_time_periodic_r1_repair.check.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def entry(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(rows):
    for row in rows:
        assert entry(row["path"]) == dict(row), row["path"]


def frames(path):
    raw = Path(path).read_bytes()
    assert struct.unpack_from("<III", raw) == (512, 26, 257)
    dtype = np.dtype([("time", "<f8"), ("rows", "<f8", (512, 26))])
    assert len(raw) == 12 + 257 * dtype.itemsize
    result = np.frombuffer(raw, dtype=dtype, offset=12)
    assert np.array_equal(result["time"], np.arange(257) * 2.0**-23)
    assert np.isfinite(result["rows"]).all()
    return result


def main():
    assert not TARGET.exists(), "Retained offline receipt protected"
    build_path = LOGS / (NAME + ".build.json")
    build = read(build_path)
    assert build["status"] == "built_not_run"
    assert build["compile_exit"] == build["link_exit"] == 0
    verify(build["inputs"] + build["libraries"] + build["snapshots"])
    verify([build["program"], build["log"], build["source_freeze"]])
    for runtime in build["runtime"]:
        verify([runtime["original"], runtime["copy"]])
    freeze = read(build["source_freeze"]["path"])
    for source in freeze["source"]:
        verify([source["original"], source["snapshot"]])
    verify(freeze["programs"] + freeze["logs"])
    old_path = LOGS / "upl_p3_perm_wave_ReleaseCPU_r2.check.json"
    old = read(old_path)
    assert old["passed"] and old["actual_ComputeStep_Sym"]
    retained = {row["path"]: row for row in old["files"]}
    exact, bound, arrays, completion = [], [entry(build_path), entry(old_path)], [], []
    leaves = ("physical.bin", "native_ids.csv", "ledger.csv", "modes.csv",
              "endpoint_policy.csv", "initial_source.csv", "complete.json")
    for tag, steps, dt in (("c", 512, 2.0**-24), ("h", 1024, 2.0**-25)):
        output = TESTS / "outputs" / (NAME + "_on_" + tag)
        receipt_path = LOGS / (NAME + "_on_" + tag + ".run.json")
        receipt = read(receipt_path)
        assert receipt["exit_code"] == 0 and receipt["owned_call_exited"]
        verify([receipt["program"], receipt["build"], receipt["log"]])
        done = read(output / "complete.json")
        assert done["passed"] and done["actual_ComputeStep_Sym"]
        assert done["native_ids"] == 512 and done["samples"] == 257
        assert done["steps"] == steps and done["dt_actual"] == dt
        assert done["actual_end_s"] == 2.0**-15 and done["conductivity_switch"]
        assert not done["k0"] and not done["smoke"] and not done["physical_acceptance"]
        for leaf in leaves:
            old_file = TESTS / "outputs" / ("upl_p3_perm_wave_ReleaseCPU_r2_on_" + tag) / leaf
            saved = retained[str(old_file)]
            verify([saved])
            current = entry(output / leaf)
            assert current["bytes"] == saved["bytes"] and current["sha256"] == saved["sha256"]
            exact.append(dict(retained=saved, current=current, byte_identical=True))
        bound.append(entry(receipt_path))
        arrays.append(frames(output / "physical.bin"))
        completion.append(done)
    a, b = [v["rows"] for v in arrays]
    assert np.array_equal(a[0].view(np.uint64), b[0].view(np.uint64))
    d = a - b
    pressure = np.sqrt(np.mean(d[:, :, 6]**2, axis=1))
    displacement = np.linalg.norm(d[:, :, :3], axis=2)
    velocity = np.sqrt(np.mean(np.sum(d[:, :, 3:6]**2, axis=2), axis=1))
    rms_u = np.sqrt(np.mean(displacement**2, axis=1))
    pstar, ustar = completion[0]["Pstar"], completion[0]["Ustar"]
    assert np.max(pressure) <= 5 and np.max(displacement) * 1000 <= .005
    assert np.max(pressure) / pstar <= 1e-4
    assert np.max(velocity) / (2.0**-9) <= 1e-4 and np.max(rms_u) / ustar <= 1e-4
    measured = dict(max_pressure_RMS_Pa=float(np.max(pressure)),
                    max_material_displacement_mm=float(np.max(displacement) * 1000),
                    max_pressure_RMS_over_Pstar=float(np.max(pressure) / pstar),
                    max_velocity_vector_RMS_over_A=float(np.max(velocity) / 2.0**-9),
                    max_displacement_vector_RMS_over_Ustar=float(np.max(rms_u) / ustar),
                    max_J_difference=float(np.max(np.abs(d[:, :, 8]))))
    half_path = LOGS / (NAME + "_half.check.json")
    half = read(half_path)
    assert half["passed"] and half["samples"] == 257 and half["native_ids"] == 512
    for key, value in measured.items():
        assert math.isclose(value, half[key], rel_tol=2e-13, abs_tol=1e-20), (key, value, half[key])
    bound += [entry(half_path), entry(__file__)]
    result = dict(passed=True, geometry="Periodic", actual_ComputeStep_Sym=True,
                  solver_jobs_adopted=2, new_solver_or_comparator_calls=0,
                  matched_samples_per_job=257, native_ids=512, columns=26,
                  all_native_fields_and_actual_saved_clocks_bitwise_exact=True,
                  existing_diagnostics_byte_exact=True,
                  reason="Original r1 completed both jobs and comparator; zero stdout meant Tee created no log, so final receipt publication failed. No missing historical receipt/log was fabricated.",
                  independent_half_metrics=measured, exact_files=exact, files=bound,
                  gradient_bound_never_dominant_inferred=False,
                  physical_acceptance=False, public_or_formal_admission=False)
    TARGET.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(passed=True, receipt=str(TARGET), half=measured)))


if __name__ == "__main__":
    main()
