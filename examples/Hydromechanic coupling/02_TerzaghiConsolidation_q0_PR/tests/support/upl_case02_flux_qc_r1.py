"""Thin offline flux-candidate QC; immutable case02 decoder checks are reused, not patched."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
MODULE = TESTS/"support/upl_case02_qc_r1.py"
MODULE_NOTE = TESTS/"notes/upl_case02_qc_r1.json"
for path, sha in ((MODULE, "0ed07dd825c4209bb580bef6af821a415112bc6d63c7502cf0ea4e50fa401c96"),
                  (MODULE_NOTE, "15b116e91c74dcde2d6eeefbb7492fad5b9efb3377690289d0abe1db67fee810")):
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError("Immutable QC dependency changed: "+str(path))
from upl_case02_qc_r1 import load_job, drain, saved_steps, identity, bind, VERIFIED, need, FIELDS


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def short_window(job, factor):
    need(job["done"]["window"] == "short" and job["done"]["grid"] == ("c" if factor == 1 else "h"),
         "Not the declared flux short grid")
    return drain(job, factor)  # Original519 saved steps, native FSType/p, history/completion counts.


def evaluate(mode):
    if mode == "smoke":
        job = load_job("flux_smoke", 3, 2.5e-6, True)
        need(job["done"]["window"] == "smoke" and job["done"]["planned_completed_steps"] == 2,
             "Not the flux two-step smoke")
        return dict(passed=True, samples=3, native_count=1000, fixed_count=40, completed_steps=2,
                    native_live_final_byte_exact=True, soil_ledger_checks=3000, fixed_marker_checks=120)
    if mode == "off":
        old = load_job("legacy_control", 151, 1e-5, False)  # Retained historical run; no old program invoked.
        new = load_job("flux_legacy_off", 21, 1e-5, False)
        need(new["raw"] == old["raw"][:21*166408], "OFF all-original15 typed prefix differs")
        need(new["files"]["clock.bin"].read_bytes()[8:] == old["files"]["clock.bin"].read_bytes()[8:8+21*28],
             "OFF actual clock/Step/locked-dt/signed-error prefix differs")
        for name in ("native_ids.csv", "fixed_ids.csv"):
            need(new["files"][name].read_bytes() == old["files"][name].read_bytes(), "OFF IDs/initial geometry differ")
        return dict(passed=True, old_samples=151, compared_samples=21, fields_masked=0,
                    all_original15_typed_prefix_byte_exact=True, compared_original15_payload_bytes=21*166408,
                    all_clock28_prefix_byte_exact=True, compared_clock_payload_bytes=21*28,
                    native_and_fixed_ID_files_byte_exact=True, all_1040_native_including_fixed_Rhop_compared=True,
                    differing_sample_count_headers_verified_separately=True)
    a = load_job("flux_short_coarse", 519, 2.5e-6, True)
    da = short_window(a, 1)
    if mode == "coarse":
        return dict(passed=True, samples=519, native_count=1000, fixed_count=40,
                    completed_steps=int(saved_steps()[-1]), native_live_final_byte_exact=True,
                    soil_ledger_checks=519000, fixed_marker_checks=20760, drainage_coarse=da,
                    original_all519_save_steps_and_nonempty_post_open_native_p_zero=True,
                    half_or_force_stage_or_theory_acceptance=False)
    gate_path = TESTS/"logs/upl_case02_flux_short_coarse_r1.qc.json"
    bind(identity(gate_path))
    gate = read_json(gate_path)
    need(gate["passed"] is True and gate["mode"] == "coarse" and gate["physical_acceptance"] is False
         and gate["bindings_unchanged_after_QC"] is True and gate["drainage_coarse"]["min_active_drained"] > 0,
         "Passed flux coarse single-window/nonempty-drain QC required before half QC")
    b = load_job("flux_short_half", 519, 1.25e-6, True)
    db = short_window(b, 2)
    for name in ("native_ids.csv", "fixed_ids.csv"):
        need(a["files"][name].read_bytes() == b["files"][name].read_bytes(), "Half material ID map differs")
    need(np.array_equal(a["x"][0].view("<u8"), b["x"][0].view("<u8")), "Initial all26 bits differ")
    time_error = float(np.max(abs(a["clock"]["time"]-b["clock"]["time"])))
    need(time_error <= 1e-14, "Actual paired-time difference exceeds original1e-14s budget")
    diff = a["x"]-b["x"]
    pressure = np.sqrt(np.mean(diff[:, :, 6]**2, axis=1))
    ua, ub = a["x"][:, :, :3]-a["x0"], b["x"][:, :, :3]-b["x0"]
    displacement = 1000*np.max(np.linalg.norm(ua-ub, axis=2), axis=1)
    need(float(pressure.max()) <= 5 and float(displacement.max()) <= .005,
         "Original5Pa/.005mm independent half limits failed")
    return dict(passed=True, samples=519, native_count=1000, fixed_count=40,
                actual_time_max_difference_s=time_error, half_completed_steps_twice_coarse=True,
                initial_all26_bits_exact=True, both_live_final_byte_exact=True,
                max_pressure_RMS_Pa=float(pressure.max()), pressure_RMS_limit_Pa=5,
                max_material_displacement_difference_mm=float(displacement.max()), displacement_limit_mm=.005,
                pressure_RMS_Pa_all519=pressure.tolist(), material_displacement_difference_mm_all519=displacement.tolist(),
                column_max_abs_difference_descriptive=dict(zip(FIELDS, np.max(abs(diff), axis=(0, 1)).tolist())),
                velocity_RMS_max_descriptive=float(np.sqrt(np.mean(np.sum(diff[:, :, 3:6]**2, axis=2), axis=1)).max()),
                drainage_coarse=da, drainage_half=db)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "off", "coarse", "half"), required=True)
    mode = parser.parse_args().mode
    leaf = {"smoke": "upl_case02_flux_smoke_r1.qc.json", "off": "upl_case02_flux_legacy_off_r1.exact.json",
            "coarse": "upl_case02_flux_short_coarse_r1.qc.json", "half": "upl_case02_flux_short_r1.half.json"}[mode]
    target = TESTS/"logs"/leaf
    need(not target.exists(), "Retained QC output protected: "+str(target))
    result = dict(stage="upl_case02_flux_qc_r1", mode=mode, passed=False, physical_acceptance=False,
                  solver_or_reader_or_build_started=False, same_force_stage_load_budget_verified=False,
                  wave_normalized_or_energy_gates_applied=False, immutable_loader_reused_without_monkeypatch=True,
                  old_control_rerun=False, same_solver_and_structural_reader_source_build_claimed=False)
    try:
        for path in (MODULE, MODULE_NOTE, Path(__file__), TESTS/"notes/upl_case02_flux_qc_r1.json"):
            bind(identity(path))
        result.update(evaluate(mode))
        for expected in VERIFIED.values():
            need(identity(expected["path"]) == expected, "Consumed file changed during QC")
        result["bindings_unchanged_after_QC"] = True
    except Exception as error:
        result.update(passed=False, failure=str(error))
    result["inputs"] = list(VERIFIED.values())
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(str(target)+" passed="+str(result["passed"]))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
