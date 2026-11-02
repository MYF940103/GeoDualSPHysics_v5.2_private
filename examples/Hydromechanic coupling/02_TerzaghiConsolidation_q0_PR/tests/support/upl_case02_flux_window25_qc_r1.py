"""Offline window25 QC: immutable loader, exact retained prefix, original half limits."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
MODULE = TESTS / "support/upl_case02_qc_r1.py"
MODULE_NOTE = TESTS / "notes/upl_case02_qc_r1.json"
for path, sha in ((MODULE, "0ed07dd825c4209bb580bef6af821a415112bc6d63c7502cf0ea4e50fa401c96"),
                  (MODULE_NOTE, "15b116e91c74dcde2d6eeefbb7492fad5b9efb3377690289d0abe1db67fee810")):
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError("Immutable QC dependency changed: " + str(path))
from upl_case02_qc_r1 import load_job, saved_steps, identity, bind, VERIFIED, need, FIELDS, FRAME


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def same_path(a, b):
    return Path(a).resolve() == Path(b).resolve()


def prior_gate(leaf, stage, mode, jobs):
    path = TESTS / "logs" / leaf
    bind(identity(path))
    gate = read_json(path)
    need(gate["passed"] is True and gate["stage"] == stage and gate["mode"] == mode
         and gate["bindings_unchanged_after_QC"] is True and gate["physical_acceptance"] is False,
         "Passed unchanged original QC required: " + leaf)
    for entry in gate["inputs"]:
        bind(entry)
    for name in jobs:
        for suffix in (".native.check.json", ".run.json"):
            expected = TESTS / "logs" / ("upl_case02_" + name + "_r1" + suffix)
            need(sum(same_path(e["path"], expected) for e in gate["inputs"]) == 1,
                 "QC lacks the corresponding bound native/solver record")
    return gate


def old_gates():
    prior_gate("upl_case02_flux_short_coarse_r1.qc.json", "upl_case02_flux_qc_r1", "coarse",
               ("flux_short_coarse",))
    prior_gate("upl_case02_flux_short_r1.half.json", "upl_case02_flux_qc_r1", "half",
               ("flux_short_coarse", "flux_short_half"))


def owned_call(entry, program, arguments):
    call = read_json(bind(entry))
    need(all(call.get(k) is True for k in ("direct_native_call", "typed_LASTEXITCODE_captured_immediately",
                                         "owned_call_exited")) and type(call["exit_code"]) is int
         and call["exit_code"] == 0 and call.get("invocation_failure") is None
         and call["program"] == program and call["arguments"] == arguments,
         "Actual typed owned call/program/argv attribution differs")


def load_window(name, samples, dt):
    job = load_job(name, samples, dt, True)  # Full original native/ledger/live-final checks, unmodified.
    tag = "upl_case02_" + name + "_r1"
    check = job["check"]
    run_path = TESTS / "logs" / (tag + ".run.json")
    need(check["stage"] == tag and same_path(check["sealed_solver"]["path"], run_path)
         and same_path(check["paths"]["solver_dir"], TESTS / "outputs" / tag),
         "New native/solver stage or output attribution differs")
    run = read_json(run_path)
    need(run["stage"] == tag, "New solver stage differs")
    owned_call(run["owned_exit_record"], run["program"], run["arguments"])
    owned_call(check["owned_exit_record"], check["program"], check["arguments"])
    return job


def window_steps():
    return np.concatenate((saved_steps(), np.arange(5020, 10001, 20, dtype=np.uint32)))


def drainage(job, factor):
    steps = window_steps()
    need(steps.size == 769 and job["done"]["window"] == "window25"
         and job["done"]["grid"] == ("c" if factor == 1 else "h"), "Window25 grid/schema differs")
    completed = np.where(np.arange(769) == 0, 0, job["clock"]["step"].astype(np.uint64) + 1)
    need(np.array_equal(completed, factor * steps), "Original519 plus declared250 saved steps differ")
    need(job["done"]["planned_completed_steps"] == 10000 * factor
         and job["done"]["post_open_completed_step_threshold"] == 4000 * factor,
         "Window25 completed-step/drain threshold metadata differs")
    post = completed > 4000 * factor
    active = np.isin(job["x"][:, :, 17], (2, 3)) & post[:, None]
    counts = active.sum(axis=1)
    need(post.any() and np.all(counts[post] > 0) and np.all(job["x"][:, :, 6][active] == 0),
         "Window25 post-open true FSType2/3 drainage must be nonempty and p zero")
    for part, row in enumerate(job["history"]):
        need(int(row["completed_step"]) == int(completed[part])
             and int(row["post_open_by_completed_step"]) == int(post[part])
             and int(row["activeDrainCount"]) == int(counts[part]), "Window25 history/native drainage differs")
    need(job["done"]["post_open_frames"] == int(post.sum())
         and job["done"]["post_open_drained_particle_checks"] == int(counts.sum()),
         "Window25 completion drainage coverage differs")
    return dict(post_open_frames=int(post.sum()), drained_native_frame_instances=int(counts.sum()),
                min_active_drained=int(counts[post].min()), max_active_drained=int(counts.max()))


def native_three(job):
    """Round-trip actual17-digit J/n/theta exports, including genuine fixed zero markers."""
    samples = job["done"]["samples"]
    values = np.empty((samples, 1040, 3), dtype="<f8")
    specs = (("ledger.csv", 1000, 40, ("J", "n_native", "theta_native"),
              "part,time_s,id,J,n_native,theta_native,V_derived_m2,rho_derived_kg_m3,k_derived_m_s,legacy_Rhop,PosDiv_native_present"),
             ("fixed_samples.csv", 40, 0, ("J", "n_zero_marker", "theta_zero_marker"),
              "part,time_s,id,x,y,z,vx,vy,vz,J,n_zero_marker,theta_zero_marker,p"))
    for name, count, first, fields, header in specs:
        rows = 0
        with job["files"][name].open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            need(reader.fieldnames == header.split(","), "Native3 CSV schema differs: " + name)
            for ordinal, row in enumerate(reader):
                part, local = divmod(ordinal, count)
                need(part < samples and int(row["part"]) == part and int(row["id"]) == first + local
                     and float(row["time_s"]) == job["clock"]["time"][part], "Native3 CSV part/ID/time order differs")
                values[part, first + local] = [float(row[k]) for k in fields]
                rows += 1
        need(rows == samples * count, "Incomplete native3 CSV coverage: " + name)
    need(np.isfinite(values).all() and np.all(values[:, :40, 1:] == 0), "Nonfinite native3 or fixed marker differs")
    need(np.array_equal(values[:, 40:, 0].copy().view("<u8"), job["x"][:, :, 8].copy().view("<u8"))
         and np.array_equal(values[:, 40:, 2].copy().view("<u8"), job["x"][:, :, 9].copy().view("<u8")),
         "CSV round-trip native J/theta bits differ from physical26")
    return values


def prefix(new, old_name, dt):
    old = load_job(old_name, 519, dt, True)
    need(old["done"]["window"] == "short" and old["done"]["grid"] == new["done"]["grid"],
         "Retained original prefix grid differs")
    # Count headers differ intentionally; validated separately by immutable load_job.
    need(new["raw"][:519 * 166408] == old["raw"], "All original15 typed prefix differs")
    need(new["files"]["clock.bin"].read_bytes()[8:8 + 519 * 28]
         == old["files"]["clock.bin"].read_bytes()[8:], "All clock28 typed prefix differs")
    need(new["files"]["physical.bin"].read_bytes()[12:12 + 519 * FRAME.itemsize]
         == old["files"]["physical.bin"].read_bytes()[12:], "All physical26 typed prefix differs")
    for name in ("native_ids.csv", "fixed_ids.csv", "columns.csv"):
        need(new["files"][name].read_bytes() == old["files"][name].read_bytes(), "Prefix ID/geometry/schema differs")
    new_three, old_three = native_three(new), native_three(old)
    need(np.array_equal(new_three[:519].view("<u8"), old_three.view("<u8")),
         "All1040 native J/n/theta prefix bits differ")
    return dict(retained_job=old_name, samples=519, all_original15_payload_bit_exact=True,
                original15_payload_bytes=519 * 166408, clock28_payload_bit_exact=True,
                clock_payload_bytes=519 * 28, physical26_payload_bit_exact=True,
                physical_payload_bytes=519 * FRAME.itemsize, native_J_n_theta_all1040_bit_exact=True,
                native_double_values_compared=519 * 1040 * 3,
                CSV_native_double_roundtrip_17_digits=True, new_native3_rows_checked=new_three.shape[0] * 1040,
                sample_count_headers_checked_separately=True, fields_masked=0,
                whole_BI4_or_file_hash_equality_claimed=False)


def evaluate(mode):
    old_gates()  # Both already completed original coarse and independent-half QC are prerequisites.
    if mode == "smoke":
        job = load_window("flux_window25_smoke", 3, 2.5e-6)
        need(job["done"]["window"] == "smoke" and job["done"]["planned_completed_steps"] == 2,
             "Not the new window25 two-step smoke")
        native_three(job)
        return dict(passed=True, samples=3, completed_steps=2, native_count=1000, fixed_count=40,
                    native_live_final_byte_exact=True, native3_rows_checked=3120,
                    soil_ledger_checks=3000, fixed_marker_checks=120)
    a = load_window("flux_window25_coarse", 769, 2.5e-6)
    da = drainage(a, 1)
    pa = prefix(a, "flux_short_coarse", 2.5e-6)
    if mode == "coarse":
        return dict(passed=True, samples=769, completed_steps=10000, native_count=1000, fixed_count=40,
                    native_live_final_byte_exact=True, soil_ledger_checks=769000, fixed_marker_checks=30760,
                    drainage_coarse=da, prefix_coarse=pa, half_or_theory_acceptance=False)
    prior_gate("upl_case02_flux_window25_coarse_r1.qc.json", "upl_case02_flux_window25_qc_r1", "coarse",
               ("flux_window25_coarse",))
    b = load_window("flux_window25_half", 769, 1.25e-6)
    db = drainage(b, 2)
    pb = prefix(b, "flux_short_half", 1.25e-6)
    for name in ("native_ids.csv", "fixed_ids.csv"):
        need(a["files"][name].read_bytes() == b["files"][name].read_bytes(), "Window25 half material ID map differs")
    need(np.array_equal(a["x"][0].view("<u8"), b["x"][0].view("<u8")), "Initial all26 bits differ")
    time_error = float(np.max(abs(a["clock"]["time"] - b["clock"]["time"])))
    need(time_error <= 1e-14, "Original1e-14s paired actual-time budget failed")
    pressure = np.sqrt(np.mean((a["x"][:, :, 6] - b["x"][:, :, 6]) ** 2, axis=1))
    ua, ub = a["x"][:, :, :3] - a["x0"], b["x"][:, :, :3] - b["x0"]
    displacement = 1000 * np.max(np.linalg.norm(ua - ub, axis=2), axis=1)
    need(float(pressure.max()) <= 5 and float(displacement.max()) <= .005, "Original5Pa/.005mm independent-half limits failed")
    return dict(passed=True, samples=769, native_count=1000, fixed_count=40,
                actual_time_max_difference_s=time_error, half_completed_steps_twice_coarse=True,
                initial_all26_bits_exact=True, both_live_final_byte_exact=True,
                max_pressure_RMS_Pa=float(pressure.max()), pressure_RMS_limit_Pa=5,
                max_material_displacement_difference_mm=float(displacement.max()), displacement_limit_mm=.005,
                pressure_RMS_Pa_all769=pressure.tolist(), material_displacement_difference_mm_all769=displacement.tolist(),
                column_max_abs_difference_descriptive=dict(zip(FIELDS, np.max(abs(a["x"] - b["x"]), axis=(0, 1)).tolist())),
                drainage_coarse=da, drainage_half=db, prefix_coarse=pa, prefix_half=pb)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "coarse", "half"), required=True)
    mode = parser.parse_args().mode
    leaf = {"smoke": "upl_case02_flux_window25_smoke_r1.qc.json", "coarse": "upl_case02_flux_window25_coarse_r1.qc.json",
            "half": "upl_case02_flux_window25_r1.half.json"}[mode]
    target = TESTS / "logs" / leaf
    need(not target.exists(), "Retained QC output protected: " + str(target))
    result = dict(stage="upl_case02_flux_window25_qc_r1", mode=mode, passed=False, physical_acceptance=False,
                  solver_or_reader_or_build_started=False, immutable_loader_reused_without_monkeypatch=True,
                  new_native_and_solver_attribution_checked=False, interpolation_or_time_snapping=False,
                  whole_BI4_or_file_hash_equality_claimed=False, same_force_stage_load_budget_verified=False,
                  wave_normalized_or_energy_gates_applied=False)
    try:
        for path in (MODULE, MODULE_NOTE, Path(__file__), TESTS / "notes/upl_case02_flux_window25_qc_r1.json"):
            bind(identity(path))
        result.update(evaluate(mode))
        result["new_native_and_solver_attribution_checked"] = True
        for expected in VERIFIED.values():
            need(identity(expected["path"]) == expected, "Consumed file changed during QC")
        result["bindings_unchanged_after_QC"] = True
    except Exception as error:
        result.update(passed=False, failure=str(error))
    result["inputs"] = list(VERIFIED.values())
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(str(target) + " passed=" + str(result["passed"]))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
