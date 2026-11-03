"""Offline 0.5 s HG review; coarse is descriptive, pair adds independent-half gates.

Root must read this whole file and its note before explicitly authorizing execution.
This module never launches a solver, reader, build, GenCase, Git, or another run.
"""
import argparse
import csv
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parents[1]
NAME = "upl_hg_column_full_review_r1"
N, SHORT = 1469, 458
DC = 2.0 ** -19
EVENT = 5243 * DC
STEPS = np.array(sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) |
                        set(range(66560, 262145, 1024))), dtype=np.int64)
PROFILE_STEPS = (5242, 5243, 5244, 65536, 131072, 262144)
FIELDS = ["x", "y", "z", "vx", "vy", "vz", "PorePress", "PorePress0", "J", "theta",
          "sigma_xx", "sigma_xy", "sigma_xz", "sigma_yy", "sigma_yz", "sigma_zz",
          "Kplastic", "FSType", "FSNormal_x", "FSNormal_y", "FSNormal_z", "ExcessPorePress",
          "LoadAce_x", "LoadAce_y", "LoadAce_z", "legacy_Rhop"]
SCHEMA = "case02_common26_col21_ExcessPorePress_NOT_wave26"
SERIES = (("HG_c", "coarse", True, "#2166ac", "-"),
          ("HG_h", "half", True, "#b2182b", "--"),
          ("HG0_c", "coarse", False, "#4d9221", "-"),
          ("HG0_h", "half", False, "#762a83", "--"))
STRIDES = {"original15.bin": 166408, "physical.bin": 208008, "clock.bin": 28,
           "common_j_theta.bin": 16648, "soil_n.bin": 8008}
LEAVES = set(STRIDES) | {"native_ids.csv", "fixed_ids.csv", "history.csv", "ledger.csv",
                        "fixed_samples.csv", "last_poro.csv", "columns.csv", "completion.json"}
BOUND = {}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def entry(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def bind(expected):
    key = str(Path(expected["path"]).resolve())
    if key not in BOUND:
        BOUND[key] = entry(key)
    actual = BOUND[key]
    need(actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"].lower(),
         "Changed consumed artifact: " + key)
    return Path(key)


def adopt(path):
    expected = entry(path)
    bind(expected)
    return expected


def read(expected):
    return json.loads(bind(expected).read_text(encoding="utf-8-sig"))


def owned(expected):
    call = read(expected)
    need(call.get("direct_native_call") and call.get("owned_call_exited") and
         call.get("typed_LASTEXITCODE_captured_immediately") and type(call.get("exit_code")) is int and
         call["exit_code"] == 0 and not call.get("invocation_failure"), "Owned typed exit0 required")
    bind(call["program"])
    if call.get("log"):
        bind(call["log"])
    return call


def bits(a, b):
    return np.array_equal(np.asarray(a, dtype="<f8").view("<u8"),
                          np.asarray(b, dtype="<f8").view("<u8"))


def header(leaf, samples):
    return {"original15.bin": (1040, 15, samples), "physical.bin": (1000, 26, samples),
            "clock.bin": (samples, 28), "common_j_theta.bin": (1040, 2, samples),
            "soil_n.bin": (1000, 1, samples)}[leaf]


def binary(expected, leaf, samples):
    path = bind(expected)
    wanted = header(leaf, samples)
    offset = 4 * len(wanted)
    with path.open("rb") as stream:
        need(struct.unpack("<" + "I" * len(wanted), stream.read(offset)) == wanted,
             "Binary header differs: " + str(path))
    need(path.stat().st_size == offset + samples * STRIDES[leaf], "Binary length differs: " + str(path))
    return path, offset


def csv_rows(expected):
    with bind(expected).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), "CSV header differs")
        return list(reader)


def dataset(grid, hg, short=False):
    need(hg or not short, "Only current HG has a short-prefix owner")
    half = grid == "half"
    factor = 2 if half else 1
    samples = SHORT if short else N
    window = ("short_h" if half else "short_c") if short else grid
    tag = ("upl_hg_column_ReleaseCPU_" + window + "_r1") if hg else ("upl_damp_long_CPU_" + grid + "_r1")
    ce = adopt(T / "logs" / (tag + (".native_r2.json" if hg else ".native.json")))
    native = read(ce)
    need(native.get("passed") is True and native.get("physical_acceptance") is False and
         native.get("stage") == ("upl_hg_column_native_run_r2" if hg else "upl_damp_long_native_run_r1") and
         native.get("backend") == "CPU" and native.get("window") == window and
         native.get("bindings_unchanged") and native.get("original_native_guards_passed") and
         native.get("drainage_nonempty_per_frame_verified"), "Native owner rejected: " + tag)
    run = read(native["source_run"])
    solver_dir = (T / "outputs" / tag).resolve()
    native_dir = (T / "outputs" / (tag + "_native")).resolve()
    need(Path(native["source_run"]["path"]).resolve() == (T / "logs" / (tag + ".run.json")).resolve() and
         Path(native["paths"]["solver_dir"]).resolve() == solver_dir and
         Path(native["paths"]["native_dir"]).resolve() == native_dir and
         native["source_build"] == run["source_build"], "Native owner belongs to another Run/build/output")
    steps, dt = STEPS[:samples] * factor, DC / factor
    end = float(steps[-1] * dt)
    need(run.get("stage") == ("upl_hg_column_run_r2" if hg else "upl_damp_long_run_r1") and
         run.get("passed") is True and run.get("physical_acceptance") is False and
         run.get("backend") == "CPU" and run.get("configuration") == "ReleaseCPU" and
         run.get("window") == window and run.get("threads") == 8 and
         run.get("native_frames") == samples and run.get("public_project_main") and
         not run.get("fixture_or_Run_override") and
         run.get("bindings_unchanged" if hg else "source_inputs_objects_runtime_canonical_unchanged"),
         "Actual project-main Run rejected: " + tag)
    job = run["job"]
    need(job["dt_s"] == dt and job["steps"] == int(steps[-1]) and job["expected_samples"] == samples and
         abs(float(job["end_s"]) - end) <= 1e-14, "Prepared job differs")
    if hg:
        need(job["tag"] == tag and Path(job["output_directory"]).resolve() == solver_dir,
             "Current HG prepared job tag/output differs")
    table = job["saved_clock_table"]
    need(len(table) == samples and all((v["part"], v["completed_steps"], v["saved_step"]) ==
         (i, int(steps[i]), int(steps[i] - 1) if i else 0) for i, v in enumerate(table)),
         "Prepared integer schedule differs; JSON time round-trip values are not equality truth")
    manifest = read(run["input_manifest"])
    need(manifest.get("passed") and manifest.get("prepared") and manifest.get("physical_acceptance") is False,
         "Input preparation receipt rejected")
    if hg:
        need(native["input_manifest"] == run["input_manifest"] and
             manifest.get("stage") == "upl_hg_column_prepare_r1" and manifest.get("input_sources_unchanged"),
             "HG input owner differs")
        candidates = [v for v in manifest["variants"] if v["window"] == grid]
        need(len(candidates) == 1, "Unique HG runtime variant required")
        material = candidates[0]
        need(material.get("inverse_runtime_bytes_exact") and material.get("original_initial_particle_fields_unchanged") and
             material.get("changed_runtime_value_only") == "SoilHourglassXi:0->0.1", "HG-only runtime proof rejected")
        prepared = [v for v in manifest["jobs"] if v["tag"] == tag]
        need(len(prepared) == 1 and all(prepared[0][k] == job[k] for k in
             ("tag", "configuration", "window", "input_variant", "input_prefix", "output_directory", "threads",
              "steps", "expected_samples", "event_completed_step", "retained_HG0_control")),
             "Run job is not the declared prepared HG job")
        counters = run["HG"]
        expected = dict(forcecalls=2 * int(steps[-1]), ratecalls=2 * int(steps[-1]),
                        predictorupdates=int(steps[-1]), correctorupdates=int(steps[-1]),
                        ratecalculations=int(steps[-1]) + 1, ratecachehits=int(steps[-1]) - 1)
        need(all(counters.get(k) == v for k, v in expected.items()) and
             0 <= float(counters["max_dt_over_tau"]) <= .2 and 0 <= float(counters["spinbound"]) < .01 and
             counters.get("reference_history_is_Q_over_M0") and counters.get("actual_inertia_is_current_mi"),
             "Original HG stage/cache/dt-tau/spin guards rejected")
    else:
        need(manifest.get("stage") == "upl_damp_long_prepare_r1" and job["damping"] == 1 and
             job["damping_coef"] == .02, "Retained HG0 preparation differs")
        material = job
    for key in ("runtime", "initial_BI4", "normals"):
        bind(material[key])
    xml = ET.parse(bind(material["runtime"])).getroot()
    def parameter(key):
        nodes = xml.findall("./execution/parameters/parameter[@key='" + key + "']")
        need(len(nodes) == 1, "Unique runtime parameter required: " + key)
        return float(nodes[0].get("value"))
    need(parameter("SoilHourglassXi") == (.1 if hg else 0.) and parameter("SoilDamping") == 1 and
         parameter("SoilDampingCoef") == .02 and parameter("DtFixed") == dt,
         "Runtime xi/damping/locked dt differs")
    solver, reader = owned(run["call"]), owned(native["reader_call"])
    need(Path(run["call"]["path"]).resolve() == (T / "logs" / (tag + ".call.json")).resolve() and
         Path(native["reader_call"]["path"]).resolve() == (T / "logs" / (tag + "_reader.call.json")).resolve() and
         solver.get("public_project_main") and not solver.get("fixture_or_Run_override") and
         solver["program"] == run["program"] and solver.get("target_program") == run["program"],
         "Actual solver/reader call ownership differs")
    expected_args = ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip", job["input_prefix"],
                     native["paths"]["solver_dir"], "-dirdataout", "data", "-svres", "-nsteps:" + str(int(steps[-1]))]
    need(solver["arguments"] == expected_args and reader["arguments"] ==
         ["--read", "CPU", str(solver_dir / "data"), grid, native["paths"]["native_dir"]],
         "Actual solver/reader argument binding differs")
    need(reader.get("pure_native_reader") is True and reader.get("solver_or_build_invoked") is False,
         "Actual decoder call is not a pure native reader")
    if hg:
        need(solver.get("actual_solver_call") and solver.get("target_arguments") == expected_args and
             run.get("arguments") == expected_args, "Actual r2 direct solver target differs")
    if run.get("run_out"):
        bind(run["run_out"])
    build = read(run["source_build"])
    need(build.get("passed") and build.get("program") == run["program"], "Source build/program receipt differs")
    if hg:
        need(build.get("stage") == "upl_hg_column_build_r1" and build.get("configuration") == "ReleaseCPU" and
             build.get("backend") == "CPU" and build.get("source_bindings_unchanged") and
             build.get("exact_object_basename_closure") and build.get("objects_include_project_main") and
             len(build["objects"]) == 86 and build.get("non_main_object_count") == 85,
             "Current HG project-main build authority differs")
    helper = read(native["reader_helper"])
    helper_name = "upl_hg_column_short_native_ReleaseCPU_r1" if short else "upl_damp_long_reader_ReleaseCPU_r1"
    need(Path(native["reader_helper"]["path"]).resolve() == (T / "logs" / (helper_name + ".helper.json")).resolve() and
         helper.get("passed") and helper.get("physical_acceptance") is False and
         helper.get("stage") == ("upl_hg_column_short_native_build_r1" if short else "upl_damp_long_reader_build_r1") and
         helper.get("configuration") == "ReleaseCPU" and reader["program"] == helper["program"],
         "Actual decoder/helper ownership differs")
    reader_build = read(helper["source_build"])
    need(reader_build.get("passed") and reader_build.get("physical_acceptance") is False,
         "Decoder source-build receipt rejected")
    if short:
        need(helper.get("frozen_inputs_unchanged") and helper.get("actual_project_classes_no_stubs") and
             helper.get("object_count") == 85 and len(helper["project_objects"]) == 85 and
             helper["source_build"] == run["source_build"] and not helper.get("program_run"),
             "Current short-reader build authority differs")
    else:
        # The unchanged long reader has a historical build, distinct from the current HG solver build.
        need(helper.get("kind") == "reader" and helper.get("build_and_source_bindings_unchanged") and
             helper.get("exact_link_closure_verified") and len(helper["objects"]) == 85 and
             helper.get("CPU_non_main_objects") == 85 and helper.get("link_object_count") == 86 and
             not helper.get("solver_started"), "Retained long-reader build authority differs")
    if hg:
        need(native["reader_source_build"] == helper["source_build"] and
             native.get("historical_reader_source_originals_asserted_current") is False and
             native.get("native_fields_metadata_or_signed_dterror_masked") is False,
             "Native historical-reader or unmasked scope differs")
        need(native.get("reader_source_freeze") == helper.get("source_freeze"), "Reader source-freeze owner differs")
        if native.get("reader_source_freeze"):
            read(native["reader_source_freeze"])
    done = read(native["completion"])
    post_count = samples - 204
    expected = dict(stage="upl_hg_column_short_native_r1" if short else "upl_damp_long_native_r1",
                    backend="CPU_public", window="dyadic_short458" if short else "damped500", preset=grid,
                    grid="h" if half else "c", model="constant", conductivity_model=0, conductivity_Ck=0,
                    native_count=1000, fixed_count=40, total_native_count=1040, samples=samples,
                    physical_columns=26, physical_schema=SCHEMA, native_total_arrays=22,
                    original_typed_arrays=15, native_dynamic_double_arrays=6,
                    soil_ledger_checks=1000 * samples, fixed_public_zero_marker_checks=40 * samples,
                    all_native_J_theta_rows=1040 * samples, soil_native_n_rows=1000 * samples,
                    noninitial_signed_dterror_intervals=samples - 1, planned_completed_steps=int(steps[-1]),
                    post_open_completed_step_threshold=5243 * factor, post_open_frames=post_count,
                    post_open_drained_particle_checks=10 * post_count, max_activeDrainCount=10)
    need(done.get("passed") is True and done.get("physical_acceptance") is False and
         all(done.get(k) == v for k, v in expected.items()), "Typed native schema/coverage differs")
    required = ("public_schema", "public_master_on", "PART_typed_public_metadata_verified", "native_PosDiv_present",
                "native_PosDiv_is_float", "native_V_rho_k_present", "no_exclusions",
                "initial_rest_and_decimal_lattice_verified", "double_stress_and_float_display_verified",
                "all_exported_physical_fields_finite", "declared_saved_completed_steps_exact",
                "actual_time_step_locked_dt_exact", "initial_dterror_excluded_from_noninitial_summary",
                "fixed_J_theta_original15_not_zeroed_or_masked", "common26_column21_is_actual_ExcessPorePress",
                "pre_open_event_pressure_not_forced_zero", "density_and_J_not_frozen_on_drained_receivers",
                "event_is_declared_preset_not_BI4_metadata", "descriptive_saved_field_summaries")
    need(all(done.get(k) is True for k in required) and done["dt_s"] == dt and
         abs(done["actual_end_s"] - end) <= 1e-14 and abs(done["planned_end_s"] - end) <= 1e-14 and
         abs(done["declared_ramp_and_drain_event_s"] - EVENT) <= 1e-14 and
         0 <= done["max_ledger_relative_error"] <= 5e-13 and
         np.isfinite(done["max_noninitial_signed_dterror_s"]) and done["max_noninitial_signed_dterror_s"] <= 1e-14 and
         done.get("initial_empty_dterror_intervals") in (0, 1), "Original finite/ledger/signed-dterror guards rejected")
    forbidden = ("GPU_private_fixed_n_mirror_to_public_zero_is_schema_change", "PosDiv_fabricated_or_derived",
                 "new_scientific_acceptance_gate", "same_force_stage_load_budget_verified",
                 "force_stage_guard_independently_observed", "historical_private_comparison_performed_by_reader",
                 "live_final_compared_by_reader", "independent_half_performed")
    need(all(done.get(k) is False for k in forbidden), "Original native descriptive/unmasked scope differs")
    if short:
        need(done.get("declared_first458_full_schedule_only") and not done.get("full_half_second_complete") and
             done.get("post_open_native_receiver_coverage_verified"), "Short-only native scope differs")
    leaves = {Path(e["path"]).name: e for e in native["files"]}
    need(set(leaves) == LEAVES and len(native["files"]) == 13 and leaves["completion.json"] == native["completion"] and
         all(Path(e["path"]).resolve().parent == native_dir for e in leaves.values()), "Native leaf ownership differs")
    binaries = {leaf: binary(leaves[leaf], leaf, samples) for leaf in STRIDES}
    p = np.memmap(binaries["physical.bin"][0], mode="r", offset=12, shape=(samples,),
                  dtype=[("time", "<f8"), ("q", "<f8", (1000, 26))])
    clock = np.memmap(binaries["clock.bin"][0], mode="r", offset=8, shape=(samples,),
                      dtype=[("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    columns = csv_rows(leaves["columns.csv"])
    need([r["name"] for r in columns] == FIELDS and [int(r["column"]) for r in columns] == list(range(26)),
         "Unmasked common26 column semantics differ")
    ids = csv_rows(leaves["native_ids.csv"])
    need(len(ids) == 1000 and all((int(r["row"]), int(r["id"])) == (i, i + 40) for i, r in enumerate(ids)),
         "Original material ID membership/order differs")
    x0 = np.array([[float(r[k]) for k in ("x0", "y0", "z0")] for r in ids])
    layers = np.rint((x0[:, 2] - .005) / .01).astype(int)
    columns = np.rint((x0[:, 0] - .005) / .01).astype(int)
    need(np.isfinite(x0).all() and np.array_equal(np.unique(layers), np.arange(100)) and
         np.array_equal(np.unique(columns), np.arange(10)) and
         np.array_equal(np.sort(layers * 10 + columns), np.arange(1000)) and
         np.max(np.abs(x0[:, 2] - (.005 + layers * .01))) <= 1e-12 and
         np.max(np.abs(x0[:, 0] - (.005 + columns * .01))) <= 1e-12 and np.all(x0[:, 1] == 0),
         "Fixed initial10-column/100-layer lattice differs")
    times = steps * dt
    need(bits(p["time"], times) and bits(clock["time"], times) and bits(clock["dt"], np.full(samples, dt)) and
         np.array_equal(clock["step"], np.where(steps > 0, steps - 1, 0)) and bits(p["q"][0, :, :3], x0) and
         np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and
         np.all(clock["error"][1:] != -np.finfo(float).max), "Actual binary clocks/initial state/signed intervals differ")
    history = csv_rows(leaves["history.csv"])
    need(len(history) == samples, "Native history count differs")
    for i, row in enumerate(history):
        post = steps[i] > 5243 * factor
        need((int(row["part"]), int(row["completed_step"]), int(row["saved_step"]),
              int(row["post_open_by_completed_step"]), int(row["activeDrainCount"])) ==
             (i, int(steps[i]), int(clock["step"][i]), int(post), 10 if post else 0) and
             bits(float(row["time_s"]), times[i]) and bits(float(row["dt_s"]), dt) and
             bits(float(row["signed_dterror_s"]), clock["error"][i]) and
             int(row["dterror_used_in_noninitial_summary"]) == int(i > 0) and
             int(row["dterror_interval_empty"]) == int(clock["error"][i] == -np.finfo(float).max) and
             0 <= float(row["max_ledger_relative_error"]) <= 5e-13,
             "Per-frame actual history clock/drain/ledger/signed interval differs")
    return dict(tag=tag, check=ce, native=native, run_entry=native["source_run"], run=run, job=job,
                material=material, p=p, clock=clock, x0=x0, layers=layers, columns=columns,
                history=history, binaries=binaries, samples=samples)


def prefix_records(full, short):
    rows = []
    need(full["samples"] == N and short["samples"] == SHORT and
         full["run"]["source_build"] == short["run"]["source_build"] and
         full["run"]["program"] == short["run"]["program"], "Full/short current HG build/program differs")
    for leaf, stride in STRIDES.items():
        fp, offset = full["binaries"][leaf]
        sp, short_offset = short["binaries"][leaf]
        need(offset == short_offset, "Header layout differs")
        digest = hashlib.sha256()
        with fp.open("rb") as a, sp.open("rb") as b:
            a.seek(offset)
            b.seek(short_offset)
            for part in range(SHORT):
                av, bv = a.read(stride), b.read(stride)
                need(len(av) == stride and len(bv) == stride and av == bv,
                     "Full/short raw record differs: " + full["tag"] + "/" + leaf + "/part=" + str(part))
                digest.update(av)
        rows.append(dict(full_tag=full["tag"], short_tag=short["tag"], leaf=leaf,
                         full_header_samples=N, short_header_samples=SHORT, header_bytes=offset,
                         record_bytes=stride, compared_records=SHORT, compared_record_bytes=SHORT * stride,
                         all_declared_raw_record_bytes_equal=True, raw_record_SHA256=digest.hexdigest(),
                         metadata_rewritten=False, dterror_or_other_record_bytes_excluded=False))
    return rows


def differences(a, b, comparison, role):
    rows = []
    need(a["samples"] == b["samples"] == N and bits(a["x0"], b["x0"]), "All1469 material pair required")
    for part in range(N):
        av, bv = np.asarray(a["p"]["q"][part]), np.asarray(b["p"]["q"][part])
        need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite paired common26 field")
        delta = av - bv
        rms, maximum = np.sqrt(np.mean(delta * delta, axis=0)), np.max(np.abs(delta), axis=0)
        du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
        row = dict(comparison=comparison, role=role, part=part,
                   left_actual_time_s=float(a["clock"]["time"][part]), right_actual_time_s=float(b["clock"]["time"][part]),
                   time_difference_s=float(a["clock"]["time"][part] - b["clock"]["time"][part]),
                   pressure_RMS_Pa=float(rms[6]), material_XYZ_difference_max_mm=float(1000 * np.linalg.norm(du, axis=1).max()),
                   velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(delta[:, 3:6] ** 2, axis=1)))),
                   stress6_RMS_Pa=float(np.sqrt(np.mean(np.sum(delta[:, 10:16] ** 2, axis=1)))))
        row.update({name + "_RMS_difference": float(v) for name, v in zip(FIELDS, rms)})
        row.update({name + "_max_abs_difference": float(v) for name, v in zip(FIELDS, maximum)})
        need(all(np.isfinite(v) for k, v in row.items() if k not in ("comparison", "role")), "Nonfinite pair reduction")
        rows.append(row)
    maxima = dict(max_pressure_RMS_Pa=max(r["pressure_RMS_Pa"] for r in rows),
                  max_material_XYZ_difference_mm=max(r["material_XYZ_difference_max_mm"] for r in rows),
                  max_actual_time_difference_s=max(abs(r["time_difference_s"]) for r in rows))
    return rows, maxima


def summarize(key, data):
    histories, modal, profiles = [], [], []
    layer, column, x0 = data["layers"], data["columns"], data["x0"]
    order = np.argsort(layer * 10 + column)
    sign = np.where(np.arange(10) % 2, -1., 1.)
    top, bottom = layer == 99, layer == 0  # Ten original material IDs each, not ten layers.
    for part in range(N):
        q = np.asarray(data["p"]["q"][part])
        need(np.isfinite(q).all(), "Nonfinite descriptive common26 field")
        time = float(data["clock"]["time"][part])
        uz = 1000 * (q[:, 2] - x0[:, 2])  # Up positive; settlement is -Uz.
        compression = q[:, 6] - q[:, 15]  # total sigma = effective sigma - p I.
        uz_grid = uz[order].reshape(100, 10)
        residual = uz_grid - uz_grid.mean(axis=1, keepdims=True)
        a_pi = (residual * sign).mean(axis=1)
        pressure_grid = q[order, 6].reshape(100, 10)
        stress_grid = compression[order].reshape(100, 10)
        source = data["history"][part]
        row = dict(series=key, part=part, actual_time_s=time, completed_step=int(source["completed_step"]),
                   pressure_mean_Pa=float(q[:, 6].mean()), pressure_RMS_Pa=float(np.sqrt(np.mean(q[:, 6] ** 2))),
                   pressure_min_Pa=float(q[:, 6].min()), pressure_max_Pa=float(q[:, 6].max()),
                   top10_pressure_mean_Pa=float(q[top, 6].mean()), bottom10_pressure_mean_Pa=float(q[bottom, 6].mean()),
                   top10_settlement_mean_mm=float(-uz[top].mean()), bottom10_settlement_mean_mm=float(-uz[bottom].mean()),
                   total_compression_zz_mean_Pa=float(compression.mean()), effective_compression_zz_mean_Pa=float(-q[:, 15].mean()),
                   velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(q[:, 3:6] ** 2, axis=1)))),
                   J_min=float(q[:, 8].min()), J_mean=float(q[:, 8].mean()), J_max=float(q[:, 8].max()),
                   A_pi_Uz_RMS_mm=float(np.sqrt(np.mean(a_pi ** 2))), A_pi_Uz_max_abs_mm=float(np.abs(a_pi).max()),
                   within_layer_Uz_RMS_mm=float(np.sqrt(np.mean(residual ** 2))),
                   max_within_layer_Uz_span_mm=float(np.ptp(uz_grid, axis=1).max()),
                   max_within_layer_pressure_span_Pa=float(np.ptp(pressure_grid, axis=1).max()),
                   max_within_layer_total_compression_span_Pa=float(np.ptp(stress_grid, axis=1).max()),
                   activeDrainCount=int(source["activeDrainCount"]), max_ledger_relative_error=float(source["max_ledger_relative_error"]))
        for axis in "xyz":
            name = "final_J_weighted_retained_load_" + axis + "_N_per_m"
            row[name + "_descriptive_only"] = float(source[name])
        need(all(np.isfinite(v) for k, v in row.items() if k != "series"), "Nonfinite saved-field reduction")
        histories.append(row)
        for level in range(100):
            modal.append(dict(series=key, part=part, actual_time_s=time, initial_material_layer=level,
                              initial_z_m=float(x0[layer == level, 2].mean()), A_pi_Uz_signed_mm=float(a_pi[level]),
                              within_layer_Uz_RMS_mm=float(np.sqrt(np.mean(residual[level] ** 2))),
                              within_layer_Uz_span_mm=float(np.ptp(uz_grid[level])),
                              settlement_down_mean_mm=float(-uz_grid[level].mean()),
                              pressure_mean_Pa=float(pressure_grid[level].mean()), pressure_span_Pa=float(np.ptp(pressure_grid[level])),
                              total_compression_mean_Pa=float(stress_grid[level].mean()),
                              total_compression_span_Pa=float(np.ptp(stress_grid[level]))))
        if int(STEPS[part]) in PROFILE_STEPS:
            for i in range(1000):
                profiles.append(dict(series=key, part=part, actual_time_s=time, soil_ID=i + 40,
                                     initial_material_layer=int(layer[i]), initial_material_column=int(column[i]),
                                     x0_m=float(x0[i, 0]), z0_m=float(x0[i, 2]),
                                     native_x_m=float(q[i, 0]), native_y_m=float(q[i, 1]), native_z_m=float(q[i, 2]),
                                     pressure_Pa=float(q[i, 6]), Uz_up_mm=float(uz[i]), settlement_down_mm=float(-uz[i]),
                                     effective_sigma_zz_Pa=float(q[i, 15]), total_compression_zz_Pa=float(compression[i]),
                                     layer_A_pi_Uz_signed_mm=float(a_pi[layer[i]])))
    need(len(profiles) == 1000 * len(PROFILE_STEPS), "All six actual saved profiles required")
    return histories, modal, profiles


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def draw(histories, modal, series, paths, phase):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .2})
    panels = (("pressure_mean_Pa", "Mean pore pressure (Pa)"),
              ("total_compression_zz_mean_Pa", "Total compression zz = p - sigma_zz (Pa)"),
              ("top10_settlement_mean_mm", "Top 10 material IDs: settlement down (mm)"),
              ("bottom10_settlement_mean_mm", "Bottom 10 material IDs: settlement down (mm)"),
              ("A_pi_Uz_RMS_mm", "Alternating X-column Uz amplitude RMS (mm)"),
              ("within_layer_Uz_RMS_mm", "All within-layer Uz residual RMS (mm)"))
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharex=True, constrained_layout=True)
    for key, _, _, color, style in series:
        rows = [r for r in histories if r["series"] == key]
        for ax, (field, label) in zip(axes.flat, panels):
            ax.plot([r["actual_time_s"] for r in rows], [r[field] for r in rows], color=color, ls=style, label=key)
            ax.set_ylabel(label)
            ax.axvline(EVENT, color=".5", ls=":", lw=.8)
    for ax in axes[-1]:
        ax.set_xlabel("Actual native time (s)")
    axes.flat[0].legend(ncol=2)
    fig.suptitle("CPU 0.5 s HG xi=.1: " + phase + " offline review; retained HG0 descriptive only\n"
                 "Raw actual samples. This window cannot establish suppression of the old late-growing mode.")
    with paths["history_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)
    variables = (("pressure_mean_Pa", "Pore pressure (Pa)"), ("settlement_down_mean_mm", "Settlement down (mm)"),
                 ("total_compression_mean_Pa", "Total compression zz (Pa)"), ("A_pi_Uz_signed_mm", "Signed alternating Uz (mm)"))
    fig, axes = plt.subplots(4, len(PROFILE_STEPS), figsize=(20, 13), sharey=True, constrained_layout=True)
    for col, step in enumerate(PROFILE_STEPS):
        part = int(np.flatnonzero(STEPS == step)[0])
        axes[0, col].set_title("Actual t=" + format(step * DC, ".12g") + " s")
        for key, _, _, color, style in series:
            selected = [r for r in modal if r["series"] == key and r["part"] == part]
            need(len(selected) == 100, "Complete material profile required for plot")
            for row, (field, label) in enumerate(variables):
                axes[row, col].plot([r[field] for r in selected], [r["initial_z_m"] for r in selected],
                                    color=color, ls=style, label=key)
                axes[row, col].set_xlabel(label)
        for row in range(4):
            axes[row, 0].set_ylabel("Initial material z0 (m)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Actual event bracket and .125/.25/.5 s material profiles\n"
                 "Ten-ID layer means and signed alternating-column projection; HG/HG0 differences are descriptive.")
    with paths["profiles_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(len(series), 1, figsize=(12, 3 * len(series)), sharex=True, constrained_layout=True)
    axes = np.atleast_1d(axes)
    limit = max(abs(r["A_pi_Uz_signed_mm"]) for r in modal)
    limit = max(limit, np.finfo(float).tiny)
    for ax, (key, _, _, _, _) in zip(axes, series):
        selected = [r for r in modal if r["series"] == key]
        values = np.array([r["A_pi_Uz_signed_mm"] for r in selected]).reshape(N, 100).T
        artist = ax.pcolormesh(STEPS * DC, .005 + np.arange(100) * .01, values,
                               shading="nearest", cmap="RdBu_r", vmin=-limit, vmax=limit, rasterized=True)
        ax.set_ylabel(key + "\nInitial material z0 (m)")
        ax.axvline(EVENT, color=".3", ls=":", lw=.8)
        ax.grid(False)
    axes[-1].set_xlabel("Actual native time (s); cells represent saved samples without interpolation")
    fig.colorbar(artist, ax=list(axes), label="Signed A_pi(Uz) (mm); common scale")
    fig.suptitle("All 100 material layers: signed alternating X-column Uz coefficient\n"
                 "No tiny-HG0 normalization, smoothing, or late-mode resolution claim.")
    with paths["heatmap_png"].open("xb") as stream:
        fig.savefig(stream, format="png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("coarse", "pair"), required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root must read the whole script/note and explicitly pass --execution-authorized; no outputs were created")
    tag = NAME + "_" + args.phase
    paths = {key: T / "figures" / (tag + suffix) for key, suffix in
             dict(history_png="_history.png", profiles_png="_profiles.png", heatmap_png="_mode_heatmap.png",
                  history_csv="_history.csv", profiles_csv="_profiles.csv", comparisons_csv="_comparisons.csv",
                  modal_csv="_modal.csv", prefix_csv="_short_prefix.csv").items()}
    check = T / "logs" / (tag + ".check.json")
    need(not check.exists() and all(not p.exists() for p in paths.values()), "Retained review artifacts protected")
    result = dict(stage=NAME, phase=args.phase, passed=False, physical_acceptance=False,
                  independent_half_performed=False, new_runs_or_later_windows_admitted=False,
                  solver_reader_build_GenCase_or_Git_invoked=False, failure=None)
    try:
        adopt(__file__)
        adopt(T / "notes" / (NAME + ".json"))
        need(len(STEPS) == N and int(STEPS[SHORT - 1]) == 13120 and int(STEPS[-1]) == 262144 and
             int(np.sum(STEPS > 5243)) == 1265, "Literal full1469 schedule differs")
        series = [s for s in SERIES if args.phase == "pair" or s[1] == "coarse"]
        data = {key: dataset(grid, hg) for key, grid, hg, _, _ in series}
        first = data["HG_c"]
        for d in data.values():
            need(bits(first["x0"], d["x0"]) and bits(first["p"]["q"][0], d["p"]["q"][0]),
                 "All initial26 fields/original material coordinates must match exactly")
            need(np.max(np.abs(first["clock"]["time"] - d["clock"]["time"])) <= 1e-14,
                 "All1469 actual HG/control clocks must match")
        prefix, comparisons, descriptive = [], [], {}
        for grid, suffix in (("coarse", "c"), ("half", "h")):
            if "HG_" + suffix not in data:
                continue
            new, old = data["HG_" + suffix], data["HG0_" + suffix]
            short = dataset(grid, True, short=True)
            prefix.extend(prefix_records(new, short))
            retained = new["job"]["retained_HG0_control"]
            need(retained["native"] == old["check"] and retained["run"] == old["run_entry"],
                 "Descriptive HG0 control must be the prepared retained owner")
            for field in ("initial_BI4", "normals"):
                need(all(new["material"][field][k] == old["material"][field][k] for k in ("bytes", "sha256")),
                     "HG/HG0 initial seed or normals differ")
            rows, maxima = differences(new, old, "HG_" + suffix + "_vs_HG0_" + suffix, "descriptive_operator_difference")
            comparisons.extend(rows)
            descriptive[suffix] = maxima
        gates, paired_maxima = {}, None
        if args.phase == "pair":
            need(data["HG_c"]["run"]["source_build"] == data["HG_h"]["run"]["source_build"] and
                 data["HG_c"]["run"]["program"] == data["HG_h"]["run"]["program"] and
                 data["HG_c"]["run_entry"] != data["HG_h"]["run_entry"] and
                 data["HG_c"]["run"]["call"] != data["HG_h"]["run"]["call"], "Independent HG pair ownership differs")
            rows, paired_maxima = differences(data["HG_c"], data["HG_h"], "HG_coarse_vs_HG_half", "independent_half_gate")
            comparisons.extend(rows)
            gates = dict(pressure_RMS_all1469_le_5Pa=paired_maxima["max_pressure_RMS_Pa"] <= 5.,
                         material_XYZ_all1469_le_0_005mm=paired_maxima["max_material_XYZ_difference_mm"] <= .005,
                         actual_time_all1469_le_1e_minus14_s=paired_maxima["max_actual_time_difference_s"] <= 1e-14)
        histories, modal, profiles = [], [], []
        for key, _, _, _, _ in series:
            h, m, p = summarize(key, data[key])
            histories.extend(h)
            modal.extend(m)
            profiles.extend(p)
        for key, rows in (("comparisons_csv", comparisons), ("history_csv", histories),
                          ("modal_csv", modal), ("profiles_csv", profiles), ("prefix_csv", prefix)):
            write_csv(paths[key], rows)
        draw(histories, modal, series, paths, args.phase)
        for expected in list(BOUND.values()):
            need(entry(expected["path"]) == expected, "Consumed artifact changed during independent final rehash")
        endpoint = {key: [r for r in histories if r["series"] == key][-1] for key in data}
        mode_maxima = {key: {field: max(r[field] for r in histories if r["series"] == key) for field in
                      ("A_pi_Uz_RMS_mm", "A_pi_Uz_max_abs_mm", "within_layer_Uz_RMS_mm", "max_within_layer_Uz_span_mm")}
                      for key in data}
        result.update(passed=all(gates.values()), independent_half_performed=args.phase == "pair",
                      independent_half_gates=gates, independent_half_maxima=paired_maxima,
                      coarse_phase_is_descriptive_only=args.phase == "coarse", samples_each_full_run=N,
                      actual_end_s=.5, post_open_frames_each=1265, current_HG_short_prefix_records_each=SHORT,
                      all_five_declared_raw_record_prefixes_bit_equal=True, prefix_checks=prefix,
                      native_checks=[d["check"] for d in data.values()], source_runs=[d["run_entry"] for d in data.values()],
                      source_builds=[d["run"]["source_build"] for d in data.values()],
                      HG_vs_HG0_descriptive_differences=descriptive, endpoints=endpoint, mode_maxima=mode_maxima,
                      history_rows=len(histories), modal_rows=len(modal), profile_rows=len(profiles),
                      comparison_rows=len(comparisons), consumed_files_rehashed_after_review=True,
                      original_native_guards_preserved=True, raw_PART_files_rehashed=False,
                      historical_mutable_source_originals_revalidated=False,
                      final_saved_J_weighted_load_descriptive_only=True, same_force_stage_load_guard_verified=False,
                      A_pi_definition="mean across10 original X columns of (-1)^column times (Uz minus its material-layer mean); up positive; RMS across all100 layers",
                      no_interpolation_smoothing_or_time_snap=True)
    except Exception as exc:
        result["failure"] = str(exc)
        result["passed"] = False
    result["limits"] = [
        "Coarse-phase pass means offline native ownership/safety and raw short-prefix checks passed; it is descriptive and cannot admit half or another run.",
        "Only an independently completed current HG coarse/half pair receives the5Pa/.005mm/all1469 actual-time gates. HG-vs-HG0 differences never receive half-step gates.",
        "The old HG0 alternating mode is tiny at0.5s; the previously observed late growth over1.5..6.875s reached about2.4mm. A0.5s comparison cannot establish its resolution or late stability.",
        "No theory acceptance, full-consolidation claim, physical/formal acceptance, unsaved-state stability proof, or later-window/run admission follows from this review.",
        "Top/bottom settlement uses the fixed original top/bottom10 soil IDs. XYZ differences use native saved coordinates without invented periodic unwrapping.",
        "Total compression is p-sigma_zz for stored effective stress. Final-J-weighted saved LoadAce is descriptive, not a same-force-stage load or energy guard.",
        "Native owners preserve all22 arrays/all1040 IDs and original ledger/drainage guards. Python checks all five export headers/lengths and full raw458-record prefixes; it does not reparse raw BI4 or every ledger row.",
        "All consumed artifacts are rehashed; mutable historical source originals and raw PART files are not revalidated here. Existing sealed native/build owners retain that historical provenance.",
    ]
    result.update(inputs=list(BOUND.values()), files=[entry(p) for p in paths.values() if p.exists()])
    with check.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], phase=args.phase, check=str(check), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
