"""Offline case02 smoke / typed OFF-prefix / independent short-half QC. Never runs a program."""
import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
FIELDS = ("x,y,z,vx,vy,vz,PorePress,PorePress0,J,theta,sigma_xx,sigma_xy,sigma_xz,"
          "sigma_yy,sigma_yz,sigma_zz,Kplastic,FSType,FSNormal_x,FSNormal_y,FSNormal_z,"
          "ExcessPorePress,LoadAce_x,LoadAce_y,LoadAce_z,legacy_Rhop").split(",")
CLOCK = np.dtype([("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
FRAME = np.dtype([("time", "<f8"), ("value", "<f8", (1000, 26))])
VERIFIED = {}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def bind(entry):
    need(isinstance(entry, dict) and all(k in entry for k in ("path", "bytes", "sha256")),
         "Expected a bound file Entry, not a nested receipt")
    key = str(Path(entry["path"]).resolve()).casefold()
    expected = dict(path=str(Path(entry["path"]).resolve()), bytes=entry["bytes"],
                    sha256=entry["sha256"].lower())
    if key in VERIFIED:
        need(VERIFIED[key] == expected, "Conflicting identities: " + entry["path"])
    else:
        need(identity(entry["path"]) == expected, "Changed bound file: " + entry["path"])
        VERIFIED[key] = expected
    return Path(entry["path"])


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def table(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def flag(record, *names):
    need(all(record.get(name) is True for name in names), "Required true flags: " + ",".join(names))


def header(path, wanted, header_bytes, dtype=None):
    blob = Path(path).read_bytes()
    need(struct.unpack("<" + "I" * len(wanted), blob[:header_bytes]) == tuple(wanted),
         "Binary header mismatch: " + str(path))
    if dtype is None:
        return blob[header_bytes:]
    need(len(blob) == header_bytes + wanted[-1] * dtype.itemsize, "Binary length mismatch")
    return np.frombuffer(blob, dtype=dtype, offset=header_bytes)


def native_clock(path, samples, dt):
    blob = path.read_bytes()
    need(struct.unpack("<II", blob[:8]) == (samples, 28) and
         len(blob) == 8 + samples * 28 and CLOCK.itemsize == 28, "Typed clock schema")
    clock = np.frombuffer(blob, dtype=CLOCK, offset=8)
    need(all(np.isfinite(clock[name]).all() for name in ("time", "dt", "error")), "Nonfinite clock")
    need(np.all(clock["dt"] == dt) and clock["time"][0] == 0 and clock["step"][0] == 0,
         "Locked dt / initial clock mismatch")
    need(np.all(np.diff(clock["time"]) > 0) and np.all(clock["error"][1:] > -np.finfo(float).max)
         and np.all(clock["error"][1:] <= 1e-14), "Noninitial signed necessary-step guard")
    return clock


def load_job(job, samples, dt, private):
    tag = "upl_case02_" + job + "_r1"
    check_path = TESTS / "logs" / (tag + ".native.check.json")
    bind(identity(check_path))
    check = read_json(check_path)
    flag(check, "passed", "direct_native_call", "typed_LASTEXITCODE_captured_immediately",
         "owned_call_exited", "owned_reader_exit0", "bindings_unchanged", "source_solver_exit_verified")
    need(check["job"] == job and type(check["exit_code"]) is int and check["exit_code"] == 0
         and check["failure"] is None and check["solver_started_by_this_action"] is False,
         "Reader ownership / scope mismatch")
    for key in ("reader_build", "sealed_solver", "program", "completion"):
        bind(check[key])
    if check.get("log") is not None:
        bind(check["log"])
    for key in ("bindings", "native_input_files", "files"):
        for entry in check[key]:
            bind(entry)
    build = read_json(check["reader_build"]["path"])
    flag(build, "passed", "exact_link_closure_verified")
    need(build["kind"] == "reader" and build["configuration"] == "ReleaseCPU" and
         build["program"] == check["program"], "Reader build / actual program mismatch")
    run = read_json(check["sealed_solver"]["path"])
    if job == "legacy_control":
        flag(run, "solver_finished", "owned_exited")
    else:
        flag(run, "passed", "direct_native_call", "typed_LASTEXITCODE_captured_immediately",
             "owned_call_exited", "bindings_unchanged")
    need(type(run["exit_code"]) is int and run["exit_code"] == 0, "Sealed solver did not exit0")
    out = Path(check["paths"]["native_dir"])
    need(out.resolve() == (TESTS / "outputs" / (tag + "_native")).resolve(), "Native output attribution")
    files = {Path(e["path"]).name: Path(e["path"]) for e in check["files"]}
    need(len(files) == len(check["files"]) and
         set(files) == {p.name for p in out.iterdir() if p.is_file()} and
         all(p.parent.resolve() == out.resolve() for p in files.values()), "Export file coverage")
    args = check["arguments"]
    need(args == ["--read" if private else "--read-off", str(Path(check["paths"]["solver_dir"]) / "data"),
                  str(samples), str(args[3]), str(out)] and float(args[3]) == dt, "Owned decoder argv")
    done = read_json(bind(check["completion"]))
    flag(done, "passed", "no_exclusions", "initial_rest_and_decimal_lattice_verified",
         "public_model_metadata_absent_global_and_part", "initial_dterror_excluded_from_noninitial_summary")
    need(done["samples"] == samples and done["native_count"] == 1000 and done["fixed_count"] == 40
         and done["total_native_count"] == 1040 and done["original_typed_arrays"] == 15
         and done["physical_acceptance"] is False and done["dt_s"] == dt
         and done["noninitial_signed_dterror_intervals"] == samples - 1, "Native completion schema")
    need(done["native_PosDiv_present"] is False and done["native_V_rho_k_present"] is False,
         "Unexpected public native extras")
    clock = native_clock(files["clock.bin"], samples, dt)
    history = table(files["history.csv"])
    need(len(history) == samples, "History length")
    for part, row in enumerate(history):
        need(int(row["part"]) == part and float(row["time_s"]) == clock["time"][part] and
             int(row["saved_step"]) == clock["step"][part] and float(row["dt_s"]) == dt and
             float(row["signed_dterror_s"]) == clock["error"][part], "History / typed clock mismatch")
    ids, fixed = table(files["native_ids.csv"]), table(files["fixed_ids.csv"])
    for rows, count, first in ((ids, 1000, 40), (fixed, 40, 0)):
        need(len(rows) == count and all(int(r["row"]) == i and int(r["id"]) == i + first
             and all(np.isfinite(float(r[k])) for k in ("x0", "y0", "z0"))
             for i, r in enumerate(rows)), "Native ID / initial material-coordinate schema")
    raw = header(files["original15.bin"], (1040, 15, samples), 12)
    need(len(raw) == samples * 166408, "Original15 full typed payload length")
    for part in range(samples):
        need(struct.unpack_from("<d", raw, part * 166408)[0] == clock["time"][part],
             "Original15 actual time differs")
    if not private:
        need(done["window"] == "legacy_OFF" and done["native_J_arrays"] == 0 and
             done["physical_columns"] == 0 and done["J_n_V_rho_k_theta_fabricated_or_derived"] is False,
             "OFF must not fabricate dynamic outputs")
        return dict(check=check, done=done, files=files, clock=clock, raw=raw, history=history)
    flag(done, "declared_saved_completed_steps_exact", "actual_time_step_locked_dt_exact",
         "double_stress_and_float_display_verified", "all_exported_physical_fields_finite",
         "V_rho_k_derived_not_native")
    need(done["native_J_arrays"] == 3 and done["physical_columns"] == 26 and
         done["physical_schema"] == "case02_private26_col21_ExcessPorePress_NOT_wave26" and
         done["soil_ledger_checks"] == samples * 1000 and done["fixed_marker_checks"] == samples * 40
         and done["max_ledger_relative_error"] <= 5e-13, "Private ledger/schema")
    columns = table(files["columns.csv"])
    need([(int(r["column"]), r["name"]) for r in columns] == list(enumerate(FIELDS)), "Not case02 physical26")
    frames = header(files["physical.bin"], (1000, 26, samples), 12, FRAME)
    x = frames["value"]
    x0 = np.array([[float(r[k]) for k in ("x0", "y0", "z0")] for r in ids])
    need(np.isfinite(x).all() and np.array_equal(frames["time"], clock["time"]) and
         np.array_equal(x[0, :, :3].copy().view("<u8"), x0.view("<u8")) and
         np.all(x[:, :, 7] == 0) and np.all(x[:, :, 16] == 0), "Physical native safety / initial position")
    live = [e for e in run["files"] if Path(e["path"]).name == "live_final.csv"]
    need(len(live) == 1, "Unique solver-owned live final missing")
    need(bind(live[0]).read_bytes() == files["last_poro.csv"].read_bytes(), "Last native J/n/theta != live final")
    return dict(check=check, done=done, files=files, clock=clock, raw=raw,
                history=history, x=x, x0=x0, live_final_byte_exact=True)


def saved_steps():
    return np.array(list(range(0, 3991, 10)) + list(range(3991, 4011)) +
                    list(range(4020, 5001, 10)), dtype=np.uint32)


def drain(job, factor):
    completed = np.where(np.arange(519) == 0, 0, job["clock"]["step"].astype(np.uint64) + 1)
    need(np.array_equal(completed, factor * saved_steps()), "Predeclared saved completed steps")
    post = completed > 4000 * factor
    active = np.isin(job["x"][:, :, 17], (2, 3)) & post[:, None]
    counts = active.sum(axis=1)
    need(post.any() and np.all(counts[post] > 0) and np.all(job["x"][:, :, 6][active] == 0),
         "Post-open drainage must be nonempty and actual FSType2/3 pressure zero")
    for part, row in enumerate(job["history"]):
        need(int(row["completed_step"]) == int(completed[part]) and
             int(row["post_open_by_completed_step"]) == int(post[part]) and
             int(row["activeDrainCount"]) == int(counts[part]), "Drain CSV / native fields disagree")
    need(job["done"]["post_open_frames"] == int(post.sum()) and
         job["done"]["post_open_drained_particle_checks"] == int(counts.sum()), "Drain completion coverage")
    return dict(post_open_frames=int(post.sum()), drained_native_frame_instances=int(counts.sum()),
                min_active_drained=int(counts[post].min()), max_active_drained=int(counts.max()))


def evaluate(mode):
    if mode == "smoke":
        a = load_job("smoke", 3, 2.5e-6, True)
        need(a["done"]["window"] == "smoke" and a["done"]["planned_completed_steps"] == 2,
             "Not the two-step smoke")
        return dict(passed=True, samples=3, native_count=1000, fixed_count=40,
                    native_live_final_byte_exact=True, completed_steps=2,
                    soil_ledger_checks=3000, fixed_marker_checks=120)
    if mode == "off":
        old = load_job("legacy_control", 151, 1e-5, False)
        new = load_job("legacy_off", 21, 1e-5, False)
        need(new["raw"] == old["raw"][:21 * 166408], "OFF original15 prefix differs (no field masks)")
        need(new["files"]["clock.bin"].read_bytes()[8:] ==
             old["files"]["clock.bin"].read_bytes()[8:8 + 21 * 28], "OFF full typed clock prefix differs")
        for name in ("native_ids.csv", "fixed_ids.csv"):
            need(new["files"][name].read_bytes() == old["files"][name].read_bytes(), "OFF IDs / initial geometry differ")
        return dict(passed=True, old_samples=151, compared_samples=21, all_original15_typed_prefix_byte_exact=True,
                    compared_original15_payload_bytes=21 * 166408, all_clock28_prefix_byte_exact=True,
                    compared_clock_payload_bytes=21 * 28, native_and_fixed_ID_files_byte_exact=True,
                    all_1040_native_including_fixed_Rhop_compared=True, fields_masked=0,
                    differing_sample_count_headers_verified_separately=True)
    a = load_job("short_coarse", 519, 2.5e-6, True)
    b = load_job("short_half", 519, 1.25e-6, True)
    for job, grid in ((a, "c"), (b, "h")):
        need(job["done"]["window"] == "short" and job["done"]["grid"] == grid, "Not the admitted short c/h")
    for name in ("native_ids.csv", "fixed_ids.csv"):
        need(a["files"][name].read_bytes() == b["files"][name].read_bytes(), "Half material ID map differs")
    need(np.array_equal(a["x"][0].view("<u8"), b["x"][0].view("<u8")), "Initial complete26 fields differ")
    time_error = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"])))
    need(time_error <= 1e-14, "Actual matched-time discrepancy exceeds declared clock budget")
    da, db = drain(a, 1), drain(b, 2)
    diff = a["x"] - b["x"]
    pressure = np.sqrt(np.mean(diff[:, :, 6] ** 2, axis=1))
    ua, ub = a["x"][:, :, :3] - a["x0"], b["x"][:, :, :3] - b["x0"]
    displacement = 1000 * np.max(np.linalg.norm(ua - ub, axis=2), axis=1)
    need(np.max(pressure) <= 5 and np.max(displacement) <= .005, "Original pressure/displacement half gate failed")
    return dict(passed=True, samples=519, native_count=1000, fixed_count=40,
                actual_time_max_difference_s=time_error, half_completed_steps_twice_coarse=True,
                initial_all26_bits_exact=True, both_live_final_byte_exact=True,
                max_pressure_RMS_Pa=float(pressure.max()), pressure_RMS_limit_Pa=5,
                max_material_displacement_difference_mm=float(displacement.max()), displacement_limit_mm=.005,
                pressure_RMS_Pa_all519=pressure.tolist(), material_displacement_difference_mm_all519=displacement.tolist(),
                column_max_abs_difference_descriptive=dict(zip(FIELDS, np.max(np.abs(diff), axis=(0, 1)).tolist())),
                velocity_RMS_max_descriptive=float(np.sqrt(np.mean(np.sum(diff[:, :, 3:6] ** 2, axis=2), axis=1)).max()),
                drainage_coarse=da, drainage_half=db)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "off", "half"), required=True)
    mode = parser.parse_args().mode
    leaf = {"smoke": "upl_case02_smoke_r1.qc.json", "off": "upl_case02_legacy_off_r1.exact.json",
            "half": "upl_case02_short_r1.half.json"}[mode]
    target = TESTS / "logs" / leaf
    need(not target.exists(), "Retained QC output protected: " + str(target))
    result = dict(stage="upl_case02_qc_r1", mode=mode, passed=False, physical_acceptance=False,
                  solver_or_reader_or_build_started=False, same_force_stage_load_budget_verified=False,
                  wave_normalized_or_energy_gates_applied=False)
    try:
        bind(identity(Path(__file__)))
        bind(identity(TESTS / "notes" / "upl_case02_qc_r1.json"))
        result.update(evaluate(mode))
        for expected in VERIFIED.values():
            need(identity(expected["path"]) == expected, "Bound file changed during offline QC")
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

