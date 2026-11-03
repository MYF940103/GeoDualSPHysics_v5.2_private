"""Explicit offline full-window decode and descriptive review; never advance a solver."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
NAME, TAG, CANDIDATE = "upl_bigstep_full_review_r1", "upl_bigstep_2tv_CPU1_r1", "upl_bigstep_c625_r1"
WINDOW, N, STEPS, POST, COMMON = "candidate_full2Tv", 1682, 11661219, 1564, 1291
NATIVE = T / "outputs" / (TAG + "_native_r1")
PINS = {
    "support/upl_bigstep_full_r1_run.py": (16765, "74c26315d254a99b6f4fdac62fb6c957c3d90fa18e2cde7601fb8fa15f5bf62f"),
    "notes/upl_bigstep_full_r1_run.json": (4808, "74e3a547627df8b5822386cc27f861c36599c58009daad7443703e1ef5b14aa1"),
    "support/upl_bigstep_review_r1.py": (31098, "e54e28708a0dfcf2f170d05a5edad63d5edfc078ad202670f0be53c55ef0da0b"),
    "notes/upl_bigstep_review_r1.json": (6875, "7335aff103cb86f455cd4f4fdebe32f614fc81cc517386ffb4ec7e7a069dbec3"),
    "logs/upl_bigstep_full_r1.inputs.json": (1090183, "c072b9945893f6a148d6c645991bf7b19c2ca6f4c12e7ee44007670af6229569"),
    "logs/upl_bigstep_2tv_CPU1_r1.start.json": (598516, "91a253a23d031e721eca4f67140bf456a4426b4b89feb0aeba2a504036fd05ff"),
    "logs/upl_bigstep_r1.native.json": (727018, "a8fa37ea11cacd5ed8488e8e3cc47c9fdce967d9ff0e2816d2751eecfb9235fe"),
    "logs/upl_bigstep_r1.review.json": (727492, "8f748abc246739fc55e146f874b818e5f263364b2c993909e4fcfced8ea37bd8"),
}
REFERENCE_PINS = {
    "notes/upl_damp_long_root_r1.json": (8888, "3d9c9436cf9a73d322f2ca4afb5981779cdc47fc04822b2befc7452ea9f921f9"),
    "support/upl_reference_snapshot_r1.py": (13372, "3bcc1929a0bbf491af4b44461e218e25f917268561e907df64b09750f7a0f00b"),
    "notes/upl_reference_snapshot_r1.json": (3879, "e0f00f273678c9de16aace279e16c9dd7481e01dcd64a117cf7a08b41806bd89"),
    "logs/upl_reference_snapshot_r1.check.json": (15762, "cc04f6ef65818b7439f2f747bb1ad9405387ad2a3d9327e4c73d3496f94bdbe0"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def pinned(u, name):
    size, sha = PINS[name]
    entry = dict(path=str(T / name), bytes=size, sha256=sha)
    u.bind(entry)
    return entry


def load(name, module):
    path = T / name
    data = path.read_bytes()
    need((len(data), hashlib.sha256(data).hexdigest()) == PINS[name], "Pinned pure definitions changed: " + name)
    spec = importlib.util.spec_from_file_location(module, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def definitions():
    sys.dont_write_bytecode = True
    owner = load("support/upl_bigstep_full_r1_run.py", "frozen_full_offline_owner")
    u, f, p = owner.definitions()  # Definitions only: no run/main, preparation, queue or live-control guard.
    old = load("support/upl_bigstep_review_r1.py", "frozen_bigstep_offline_exports")
    for name in PINS:
        pinned(u, name)
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        u.adopt(path)
    return u, f, p, owner, old


def full_source(u, f, p, owner, old):
    start_e = pinned(u, "logs/" + TAG + ".start.json")
    start = u.read(start_e)
    ctx = owner.context(u, f, p, start["admission"]["path"])
    entry = u.adopt(T / "logs" / (TAG + ".run.json"))
    run = u.read(entry)
    need(run.get("stage") == TAG + ".run" and run.get("tag") == TAG and run.get("passed") is True and
         run.get("failure") is None and run.get("bindings_unchanged") is True and run.get("independent_final_rehash_performed") is True and
         (run.get("backend"), run.get("configuration"), run.get("window"), run.get("threads")) == ("CPU", "ReleaseCPU", WINDOW, 1) and
         run.get("steps") == STEPS and run.get("native_frames") == N and run.get("public_project_main") is True and
         run.get("fixture_or_Run_override") is False and run.get("native_decoder_invoked") is False and
         run.get("physical_acceptance") is False and run.get("automatic_follow_up") is False and
         run.get("direct_owner_no_scheduler") is True, "A sealed passed genuine full Run is required before any reader attempt")
    for key, expected in (("job", ctx["job"]), ("source_input_manifest", ctx["manifest"]), ("source_build", ctx["source_build"]),
                          ("program", ctx["program"]), ("admission", ctx["admission"]), ("planned_clock_CSV", ctx["clock_CSV"]),
                          ("clock", ctx["clock"]), ("candidate_proofs", ctx["candidate_proofs"]), ("start_record", start_e)):
        need(run[key] == expected, "Sealed full association differs: " + key)
    call = u.owned(run["call"], TAG + ".run_call")
    need(call["program"] == call["target_program"] == run["program"] and
         call["arguments"] == call["target_arguments"] == run["job"]["arguments"] and call["start_record"] == start_e and
         call["solver"] == run["solver"] == start["solver"] and call.get("actual_solver_call") is True and
         call.get("public_project_main") is True and call.get("fixture_or_Run_override") is False and call.get("shell") is False and
         call.get("owner_exception_terminated_owned_child") is False and Path(call["working_directory"]).resolve() == u.SRC.resolve(),
         "Original typed full solver call/start/argv differs")
    need(start.get("stage") == TAG + ".start" and start.get("actual_solver_identity_verified") is True and
         start.get("direct_owner_no_scheduler") is True and start.get("physical_acceptance") is False and
         start["owner_script"] == pinned(u, "support/upl_bigstep_full_r1_run.py") and start["job"] == run["job"] and
         start["source_input_manifest"] == ctx["manifest"] and start["source_build"] == ctx["source_build"] and
         start["program"] == ctx["program"] and start["admission"] == ctx["admission"] and start["clock"] == ctx["clock"] and
         start["planned_clock_CSV"] == ctx["clock_CSV"] and start["candidate_proofs"] == ctx["candidate_proofs"] and
         Path(start["working_directory"]).resolve() == u.SRC.resolve() and start["owner_pid"] == 73076 and
         start["owner_created_epoch"] == 1793726502.8094437 and start["solver_pid"] == 38440 and
         start["solver_created_epoch"] == 1793726513.835409 and start["solver"]["parent_pid"] == start["owner_pid"] and
         start["solver"]["pid"] == start["solver_pid"] and start["solver"]["created_epoch"] == start["solver_created_epoch"] and
         start["solver"]["exe"] == start["solver_executable"] and start["solver"]["command"] == start["solver_command"] and
         start["solver"]["parent_pid"] == start["solver_parent_pid"] and
         Path(start["solver_executable"]).resolve() == Path(ctx["program"]["path"]).resolve() and
         start["solver_command"] == [ctx["program"]["path"], *ctx["job"]["arguments"]] and
         Path(start["owner_command"][0]).resolve() == Path(start["owner_executable"]).resolve() and
         start["owner_command"][1:] == ["-u", "-B", str(T / "support/upl_bigstep_full_r1_run.py"),
             "--admission", ctx["admission"]["path"], "--execution-authorized"], "Frozen actual full owner PID/creation/executable/argv differs")
    for item in [*start["inputs"], *run["inputs"], call["log"], run["run_out"]]:
        u.bind(item)
    need(all(run[key] == value for key, value in owner.check_output().items()), "Actual full HG/counters/normal finish/steps changed")
    old.raw(u, run, N)
    need(run["run_out"] in run["files"] and ctx["job"]["post_open_frames"] == POST and
         ctx["job"]["post_open_drained_particle_checks_expected"] == POST * 10, "Full raw Run.out/drainage association differs")
    return ctx, entry, run


def candidate_exports(u, ctx, old, helper_e, h):
    entry = pinned(u, "logs/upl_bigstep_r1.native.json")
    receipt = u.read(entry)
    need(receipt.get("stage") == "upl_bigstep_review_r1.native" and receipt.get("passed") is True and
         receipt.get("reader_attempts") == 2 and receipt.get("original_native_guards_passed") is True and
         receipt.get("bindings_unchanged") is True and receipt.get("independent_final_rehash_performed") is True and
         receipt.get("physical_acceptance") is False and receipt["reader_helper"] == helper_e and
         receipt["candidate_counts"] == dict(samples=1292, post_frames=1174, drains=11740), "Retained genuine candidate native phase differs")
    item = receipt["datasets"]["candidate"]
    run = u.read(item["source_run"])
    solver_call = u.owned(run["call"], CANDIDATE + ".run_call")
    call = u.owned(item["reader_call"], "upl_bigstep_review_r1.candidate.reader_call")
    directory = T / "outputs" / (CANDIDATE + "_native_r1")
    need(item["source_run"] == ctx["candidate_proofs"]["run"] and item["source_solver_call"] == run["call"] and
         run.get("passed") is True and run.get("physical_acceptance") is False and run.get("steps") == 320000 and
         run.get("native_frames") == 1292 and run.get("bindings_unchanged") is True and
         run.get("independent_final_rehash_performed") is True and run["program"] == ctx["program"] and
         run["source_build"] == ctx["source_build"] and solver_call["program"] == run["program"] and
         solver_call["arguments"] == run["job"]["arguments"] and solver_call["start_record"] == run["start_record"] and
         item["window"] == "candidate2s" and Path(item["directory"]).resolve() == directory.resolve() and
         call["program"] == h["program"] and call["arguments"] == ["--read", "CPU", str(Path(run["job"]["output_directory"]) / "data"),
             item["clock_CSV"]["path"], "candidate2s", str(directory)] and call.get("shell") is False,
         "Retained candidate decoder/source/typed solver call association differs")
    for value in [*run["inputs"], solver_call["log"], call["log"]]:
        u.bind(value)
    old.raw(u, run, 1292)
    table = run["job"]["saved_clock_table"]
    need(old.rows(u.bind(item["clock_CSV"])) == [{k: str(v) for k, v in row.items()} for row in table] and
         table[:COMMON] == ctx["job"]["saved_clock_table"][:COMMON] and table[-1]["completed_steps"] == 320000 and
         table[-1]["forced_final"] == 1 and ctx["job"]["saved_clock_table"][COMMON]["completed_steps"] == 320001 and
         not any(v["completed_steps"] == 320000 for v in ctx["job"]["saved_clock_table"]), "Ordinary shared prefix/candidate-only final frame differs")
    return entry, old.exports(u, directory, item["files"], item["completion"], table, "candidate2s")


def prefix(full, candidate):
    specs = {"original15.bin": ((1040, 15), 166408), "physical.bin": ((1000, 26), 208008),
             "common_j_theta.bin": ((1040, 2), 16648), "soil_n.bin": ((1000, 1), 8008), "clock.bin": ((), 28)}
    proof = {}
    for name, (shape, stride) in specs.items():
        head_a, head_b = (shape + (N,), shape + (1292,)) if shape else ((N, 28), (1292, 28))
        offset = 4 * len(head_a)
        length, remaining, compared, first = COMMON * stride, COMMON * stride, 0, None
        ha, hb = hashlib.sha256(), hashlib.sha256()
        with Path(full["leaves"][name]["path"]).open("rb") as a, Path(candidate["leaves"][name]["path"]).open("rb") as b:
            need(struct.unpack("<" + "I" * len(head_a), a.read(offset)) == head_a and
                 struct.unpack("<" + "I" * len(head_b), b.read(offset)) == head_b, "Honest distinct full/candidate headers required: " + name)
            while remaining:
                size = min(1024 * 1024, remaining)
                x, y = a.read(size), b.read(size)
                need(len(x) == len(y) == size, "Short shared payload: " + name)
                ha.update(x); hb.update(y)
                if x != y and first is None:
                    first = compared + next(i for i, (left, right) in enumerate(zip(x, y)) if left != right)
                compared += size
                remaining -= size
        proof[name] = dict(full_header=list(head_a), candidate_header=list(head_b), header_bytes_excluded=offset,
            full_records=N, candidate_records=1292, compared_records=COMMON, record_bytes=stride, compared_payload_bytes=length,
            full_prefix_sha256=ha.hexdigest(), candidate_prefix_sha256=hb.hexdigest(), bit_exact=first is None,
            first_differing_payload_byte=first)
    return dict(files=proof, all_five_bit_exact=all(v["bit_exact"] for v in proof.values()), shared_frames=COMMON,
        includes_original15_physical_J_theta_n_and_actual_clock_dt_signed_dterror=True, clocks_or_fields_rewritten=False,
        full_total_frames=N, candidate_total_frames=1292, candidate_forced_final_completed_step_320000_excluded=True,
        first_new_full_completed_step=320001, full_file_or_header_identity_claimed=False)


def native(u, f, p, owner, old, result):
    ctx, run_e, run = full_source(u, f, p, owner, old)
    helper_e, h = old.helper(u, ctx["source_build"])
    candidate_e, candidate = candidate_exports(u, ctx, old, helper_e, h)
    call_path, log, start_path = (T / "logs" / ("upl_bigstep_full_r1.native" + s) for s in (".call.json", ".log", ".start.json"))
    u.fresh(NATIVE, call_path, log, start_path)
    args = ["--read", "CPU", str(Path(run["job"]["output_directory"]) / "data"), ctx["clock_CSV"]["path"], WINDOW, str(NATIVE)]
    result.update(source_run=run_e, source_solver_call=run["call"], source_start=run["start_record"], reader_helper=helper_e,
        retained_candidate_native=candidate_e, clock_CSV=ctx["clock_CSV"], reader_attempts=0, directory=str(NATIVE))
    u.final_bindings()
    u.seal(start_path, dict(stage=NAME + ".native_start", source_run=run_e, source_solver_call=run["call"],
        source_start=run["start_record"], reader_helper=helper_e, program=h["program"], arguments=args,
        working_directory=str(T.parent), inputs=list(u.BOUND.values()), native_call_started_by_start_record=False,
        physical_acceptance=False))
    result["start_record"] = u.adopt(start_path)
    code = failure = None
    started, wall = u.utc(), time.perf_counter()
    result["reader_attempts"] = 1
    try:
        with log.open("xb") as stream:
            completed = subprocess.run([h["program"]["path"], *args], cwd=T.parent, stdout=stream,
                stderr=subprocess.STDOUT, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            code = completed.returncode
    except Exception as exc:
        failure = str(exc)
    u.seal(call_path, dict(stage=NAME + ".reader_call", program=h["program"], target_program=h["program"],
        arguments=args, target_arguments=args, working_directory=str(T.parent), start_record=result["start_record"],
        source_run=run_e, source_solver_call=run["call"], started_utc=started, ended_utc=u.utc(), direct_native_call=True,
        shell=False, owned_call_exited=type(code) is int, typed_returncode_captured_immediately=type(code) is int,
        exit_code=code, invocation_failure=failure, log=u.entry(log) if log.exists() else None,
        invocation_wall_seconds=time.perf_counter() - wall, physical_acceptance=False))
    result["reader_call"] = u.adopt(call_path)
    u.owned(result["reader_call"], NAME + ".reader_call")  # Seal the actual typed exit before any output postcheck.
    files = [u.adopt(path) for path in sorted(NATIVE.iterdir()) if path.is_file()]
    completion = u.adopt(NATIVE / "completion.json")
    result.update(files=files, completion=completion)
    full = old.exports(u, NATIVE, files, completion, ctx["job"]["saved_clock_table"], WINDOW)
    result["common_prefix"] = prefix(full, candidate)
    need(result["common_prefix"]["all_five_bit_exact"], "Measured first1291 native payload records differ; preserve actual exports")
    result.update(original_native_guards_passed=True, counts=dict(samples=N, steps=STEPS, total_IDs=1040, arrays=22,
        soil_ledger=N * 1000, fixed_markers=N * 40, all_ID_J_theta=N * 1040, signed_noninitial_intervals=N - 1,
        post_open_frames=POST, drained_particle_checks=10 * POST), measured_common1291_prefix_bitwise_identity=True)


def reviewed_exports(u, f, p, owner, old):
    ctx, run_e, run = full_source(u, f, p, owner, old)
    helper_e, h = old.helper(u, ctx["source_build"])
    candidate_e, candidate = candidate_exports(u, ctx, old, helper_e, h)
    entry = u.adopt(T / "logs/upl_bigstep_full_r1.native.json")
    receipt = u.read(entry)
    need(receipt.get("stage") == NAME + ".native" and receipt.get("passed") is True and receipt.get("failure") is None and
         receipt.get("reader_attempts") == 1 and receipt.get("original_native_guards_passed") is True and
         receipt.get("measured_common1291_prefix_bitwise_identity") is True and receipt.get("physical_acceptance") is False and
         receipt.get("bindings_unchanged") is True and receipt.get("independent_final_rehash_performed") is True and
         receipt["source_run"] == run_e and receipt["source_solver_call"] == run["call"] and
         receipt["source_start"] == run["start_record"] and receipt["reader_helper"] == helper_e and
         receipt["retained_candidate_native"] == candidate_e and receipt["clock_CSV"] == ctx["clock_CSV"] and
         Path(receipt["directory"]).resolve() == NATIVE.resolve(), "Passed one-call full native phase required; review never decodes")
    call = u.owned(receipt["reader_call"], NAME + ".reader_call")
    start = u.read(receipt["start_record"])
    args = ["--read", "CPU", str(Path(run["job"]["output_directory"]) / "data"), ctx["clock_CSV"]["path"], WINDOW, str(NATIVE)]
    need(call["program"] == call["target_program"] == h["program"] and call["arguments"] == call["target_arguments"] == args and
         call["start_record"] == receipt["start_record"] and call["source_run"] == run_e and call["source_solver_call"] == run["call"] and
         call.get("shell") is False and Path(call["working_directory"]).resolve() == T.parent.resolve() and
         start.get("stage") == NAME + ".native_start" and start["source_run"] == run_e and start["source_start"] == run["start_record"] and
         start["source_solver_call"] == run["call"] and start["program"] == h["program"] and start["arguments"] == args and
         start["reader_helper"] == helper_e and start.get("physical_acceptance") is False,
         "Original full reader start/call/program/arguments association differs")
    for value in [*receipt["inputs"], *start["inputs"], call["log"]]:
        u.bind(value)
    full = old.exports(u, NATIVE, receipt["files"], receipt["completion"], ctx["job"]["saved_clock_table"], WINDOW)
    actual = prefix(full, candidate)
    need(actual == receipt["common_prefix"] and actual["all_five_bit_exact"], "Measured full/candidate common payload proof changed")
    return ctx, entry, full, actual


def native_rho(u, data, np):
    rho = np.empty((N, 1000))
    count = 0
    with u.bind(data["leaves"]["ledger.csv"]).open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            part, slot = divmod(count, 1000)
            need(part < N and int(row["part"]) == part and int(row["id"]) == slot + 40 and
                 float(row["time_s"]) == data["table"][part]["time_s"] and
                 float(row["J"]) == data["p"]["q"][part, slot, 8], "Actual native ledger order/time/J differs")
            rho[part, slot] = float(row["rho_native_kg_m3"])
            count += 1
    need(count == N * 1000 and np.isfinite(rho).all() and np.all(rho > 0), "Full actual native rho coverage differs")
    return rho


def review(u, f, p, owner, old, result):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    u.adopt(np.__file__); u.adopt(matplotlib.__file__)
    ctx, native_e, data, common = reviewed_exports(u, f, p, owner, old)
    reference_provenance = [dict(path=str(T / name), bytes=size, sha256=sha) for name, (size, sha) in REFERENCE_PINS.items()]
    for entry in reference_provenance:
        u.bind(entry)
    products = {name: T / "figures" / ("upl_bigstep_full_r1." + name) for name in
        ("history.csv", "layers.csv", "theory.csv", "profile_times.csv", "profiles.csv", "history.png", "modes.png", "profiles.png")}
    u.fresh(*products.values())
    xml = ET.parse(u.bind(ctx["job"]["runtime"])).getroot()
    value = lambda name: float(next(xml.iter(name)).get("value"))
    E, nu, k, water, Kw, n0, q0, tD = (value(name) for name in ("ModulusE", "PRvs", "HydraulicConductivity", "PoreWaterRho",
        "PoreWaterBulkModulus", "Porosity", "HydroMechTopLoadQ0", "HydroMechDrainageStartTime"))
    H, g = 1., 9.81
    M = E * (1 - nu) / ((1 + nu) * (1 - 2 * nu))
    Cv, B = k * M / (water * g), 1 / (1 + n0 * M / Kw)
    lam = (np.arange(512) + .5) * np.pi
    coef = 2 * (-1.) ** np.arange(512) / lam
    basis = {}

    def companions(clock, z, height=H):
        elapsed = clock - tD
        need(elapsed >= 0, "Quasi-static drainage companions require an actual post-event clock")
        z = np.asarray(z)
        decay = np.exp(-Cv * lam ** 2 * elapsed / height ** 2)
        finite = np.exp(-(B * Cv) * lam ** 2 * elapsed / height ** 2)
        key = (height, tuple(z))
        if key not in basis:
            basis[key] = (np.cos(lam[:, None] * z[None, :] / height), np.sin(lam[:, None] * z[None, :] / height))
        c, s = basis[key]
        return dict(classical_P=q0 * np.sum((coef * decay)[:, None] * c, axis=0),
            finite_P=B * q0 * np.sum((coef * finite)[:, None] * c, axis=0),
            classical_settlement=1000 * q0 / M * (z - height * np.sum((coef / lam * decay)[:, None] * s, axis=0)),
            finite_settlement=1000 * q0 / M * (z - height * B * np.sum((coef / lam * finite)[:, None] * s, axis=0)),
            classical_mean_P=float(q0 * np.sum(2 * decay / lam ** 2)),
            finite_mean_P=float(B * q0 * np.sum(2 * finite / lam ** 2)))

    order = np.argsort(10 * data["layer"] + data["column"])
    sign, components = np.where(np.arange(10) % 2, -1., 1.), ("xx", "xy", "xz", "yy", "yz", "zz")
    z0 = data["x0"][order, 2].reshape(100, 10).mean(axis=1)
    unique_z, material_index = np.unique(data["x0"][:, 2], return_inverse=True)
    rho = native_rho(u, data, np)
    times = data["clock"]["t"]
    requested = (.005, .05, .1, .25, .4, .5, .7, 1., 1.5, 2.)
    selections, profile_times = {}, []
    for Tv in requested:
        target = tD + Tv * H ** 2 / Cv
        need(times[0] <= target <= times[-1], "Requested Tv falls outside actual full saved coverage")
        part = int(np.argmin(np.abs(times - target)))
        clock = float(times[part])
        selections.setdefault(part, []).append(Tv)
        profile_times.append(dict(requested_Tv=Tv, target_time_s=target, actual_part=part, actual_time_s=clock,
            signed_time_gap_s=clock - target, actual_Tv=Cv * (clock - tD) / H ** 2,
            signed_Tv_gap=Cv * (clock - tD) / H ** 2 - Tv,
            sensitivity_H995_actual_Tv=Cv * (clock - tD) / .995 ** 2,
            target_time_uses_primary_H1=1, completed_steps=int(data["table"][part]["completed_steps"]), interpolation_used=0))
    history, layers, theory, profiles = [], [], [], []
    for i, q in enumerate(data["p"]["q"]):
        clock = float(times[i])
        uz = 1000 * (q[:, 2] - data["x0"][:, 2])
        total = q[:, 10:16].copy()
        total[:, [0, 3, 5]] -= q[:, 6, None]
        uzg, tg = uz[order].reshape(100, 10), total[order].reshape(100, 10, 6)
        alternate_u = ((uzg - uzg.mean(axis=1, keepdims=True)) * sign).mean(axis=1)
        alternate_t = ((tg - tg.mean(axis=1, keepdims=True)) * sign[None, :, None]).mean(axis=1)
        J, n = q[order, 8].reshape(100, 10), data["n"]["n"][i][order].reshape(100, 10)
        rg, P = rho[i, order].reshape(100, 10), q[order, 6].reshape(100, 10)
        row = dict(part=i, time_s=clock, completed_steps=data["table"][i]["completed_steps"],
            legacy_Tv_since_drain=Cv * (clock - tD) / H ** 2, pressure_mean_Pa=float(P.mean()),
            pressure_J_weighted_mean_Pa=float(np.sum(q[:, 6] * q[:, 8]) / np.sum(q[:, 8])),
            pressure_RMS_Pa=float(np.sqrt(np.mean(P ** 2))), top_pressure_Pa=float(P[-1].mean()), bottom_pressure_Pa=float(P[0].mean()),
            top_settlement_mm=float(-uzg[-1].mean()), bottom_settlement_mm=float(-uzg[0].mean()),
            J_min=float(J.min()), J_mean=float(J.mean()), J_max=float(J.max()), n_min=float(n.min()), n_mean=float(n.mean()), n_max=float(n.max()),
            rho_native_min_kg_m3=float(rg.min()), rho_native_mean_kg_m3=float(rg.mean()), rho_native_max_kg_m3=float(rg.max()),
            A_pi_Uz_RMS_mm=float(np.sqrt(np.mean(alternate_u ** 2))),
            A_pi_total_sigma_components_RMS_Pa=float(np.sqrt(np.mean(alternate_t ** 2))),
            total_compression_zz_mean_Pa=float(-total[:, 5].mean()),
            **{"total_sigma_" + key + "_mean_Pa": float(total[:, j].mean()) for j, key in enumerate(components)})
        history.append(row)
        for level in range(100):
            layers.append(dict(part=i, time_s=clock, initial_layer=level, z0_m=float(z0[level]),
                current_z_mean_m=float(q[order, 2].reshape(100, 10)[level].mean()),
                P_mean_Pa=float(P[level].mean()), P_std_across_X_Pa=float(P[level].std()),
                settlement_mean_mm=float(-uzg[level].mean()), A_pi_Uz_signed_mm=float(alternate_u[level]),
                **{"A_pi_total_sigma_" + key + "_Pa": float(alternate_t[level, j]) for j, key in enumerate(components)},
                **{"total_sigma_" + key + "_mean_Pa": float(tg[level, :, j].mean()) for j, key in enumerate(components)},
                J_mean=float(J[level].mean()), n_mean=float(n[level].mean()), rho_native_mean_kg_m3=float(rg[level].mean())))
        references = {}
        if clock >= tD:
            summary = dict(time_s=clock, primary_H1_actual_Tv=Cv * (clock - tD) / H ** 2,
                sensitivity_H995_actual_Tv=Cv * (clock - tD) / .995 ** 2,
                native_same_node_mean_P_Pa=row["pressure_mean_Pa"], native_same_node_J_weighted_mean_P_Pa=row["pressure_J_weighted_mean_Pa"],
                native_material_top_settlement_mm=row["top_settlement_mm"], native_material_bottom_settlement_mm=row["bottom_settlement_mm"])
            for label, height in (("H1", H), ("H995", .995)):
                companion = companions(clock, unique_z, height)
                references[label] = companion
                for method, field in (("classical", "classical"), ("finite_Kw", "finite")):
                    pressure = companion[field + "_P"][material_index]
                    settle = companion[field + "_settlement"][material_index][order].reshape(100, 10)
                    stem = label + "_" + method
                    summary.update({stem + "_continuum_mean_P_Pa": companion[field + "_mean_P"],
                        stem + "_same_node_mean_P_Pa": float(pressure.mean()),
                        stem + "_same_node_J_weighted_mean_P_Pa": float(np.sum(pressure * q[:, 8]) / np.sum(q[:, 8])),
                        stem + "_material_top_settlement_mm": float(settle[-1].mean()),
                        stem + "_material_bottom_settlement_mm": float(settle[0].mean()),
                        stem + "_same_node_P_profile_RMS_difference_Pa": float(np.sqrt(np.mean((q[:, 6] - pressure) ** 2))),
                        stem + "_native_minus_same_node_mean_P_Pa": float(q[:, 6].mean() - pressure.mean()),
                        stem + "_native_minus_same_node_J_weighted_mean_P_Pa": float(np.sum((q[:, 6] - pressure) * q[:, 8]) / np.sum(q[:, 8])),
                        stem + "_native_minus_material_top_settlement_mm": float(-uzg[-1].mean() - settle[-1].mean())})
            theory.append(summary)
        if i in selections:
            profile_reference = {}
            for label, companion in references.items():
                for method, field in (("classical", "classical"), ("finite_Kw", "finite")):
                    for quantity in ("P", "settlement"):
                        profile_reference[label + "_" + method + "_" + quantity] = companion[field + "_" + quantity][material_index][order].reshape(100, 10).mean(axis=1)
            for Tv in selections[i]:
                timing = next(v for v in profile_times if v["requested_Tv"] == Tv)
                for level in range(100):
                    profiles.append(dict(**timing, initial_layer=level, z0_m=float(z0[level]),
                        current_z_mean_m=float(q[order, 2].reshape(100, 10)[level].mean()),
                        actual_P_mean_Pa=float(P[level].mean()), actual_P_min_Pa=float(P[level].min()), actual_P_max_Pa=float(P[level].max()),
                        actual_settlement_mean_mm=float(-uzg[level].mean()),
                        **{key + "_at_actual_time_" + ("Pa" if key.endswith("_P") else "mm"): float(values[level]) for key, values in profile_reference.items()},
                        actual_total_compression_zz_mean_Pa=float(-tg[level, :, 5].mean()),
                        J_mean=float(J[level].mean()), n_mean=float(n[level].mean()), rho_native_mean_kg_m3=float(rg[level].mean())))
    for name, values in (("history.csv", history), ("layers.csv", layers), ("theory.csv", theory),
                         ("profile_times.csv", profile_times), ("profiles.csv", profiles)):
        old.write_csv(products[name], values)
    reference_label = lambda name: name.replace("H995", "H=.995").replace("H1", "H=1").replace("_", " ")
    fig, axes = plt.subplots(4, 2, figsize=(12, 14), constrained_layout=True)
    fields = (("pressure_mean_Pa", "Same-node arithmetic P (Pa)"), ("top_settlement_mm", "Material-layer settlement (mm)"),
        ("J_mean", "J"), ("n_mean", "Porosity"), ("rho_native_mean_kg_m3", "Actual current rho (kg/m3)"),
        ("total_compression_zz_mean_Pa", "Mean total compression zz (Pa)"),
        ("pressure_J_weighted_mean_Pa", "Same-node current-J-weighted P (Pa)"),
        (None, "Continuum mean P over0..H (Pa); references only"))
    for ax, (field, label) in zip(axes.flat, fields):
        if field is not None:
            ax.plot(times, [v[field] for v in history], label="full actual")
        if field == "top_settlement_mm":
            ax.plot(times, [v["bottom_settlement_mm"] for v in history], label="material bottom")
            for name, style in (("H1_classical", "--"), ("H1_finite_Kw", ":"), ("H995_finite_Kw", "-.")):
                ax.plot([v["time_s"] for v in theory], [v[name + "_material_top_settlement_mm"] for v in theory], style, label=reference_label(name) + " quasi-static top")
        if field in ("pressure_mean_Pa", "pressure_J_weighted_mean_Pa", None):
            suffix = {"pressure_mean_Pa": "_same_node_mean_P_Pa", "pressure_J_weighted_mean_Pa": "_same_node_J_weighted_mean_P_Pa", None: "_continuum_mean_P_Pa"}[field]
            curves = (("H1_classical", "--"), ("H1_finite_Kw", ":"), ("H995_finite_Kw", "-."))
            if field is None:
                curves = curves + (("H995_classical", "-"),)
            for name, style in curves:
                ax.plot([v["time_s"] for v in theory], [v[name + suffix] for v in theory], style, label=reference_label(name) + (" continuum" if field is None else " same IDs"))
        if field in ("J_mean", "n_mean", "rho_native_mean_kg_m3"):
            lo, hi = {"J_mean": ("J_min", "J_max"), "n_mean": ("n_min", "n_max"),
                "rho_native_mean_kg_m3": ("rho_native_min_kg_m3", "rho_native_max_kg_m3")}[field]
            ax.fill_between(times, [v[lo] for v in history], [v[hi] for v in history], alpha=.2, label="actual min/max")
        ax.set(xlabel="Actual saved time (s)", ylabel=label); ax.grid(True); ax.legend(fontsize=7)
    fig.suptitle("H1 primary and unfitted H.995 sensitivity; same-node/J-weighted means distinct from continuum means")
    fig.savefig(products["history.png"], dpi=160); plt.close(fig)
    fig, axes = plt.subplots(4, 2, figsize=(13, 13), constrained_layout=True)
    mode_fields = ["A_pi_Uz_signed_mm"] + ["A_pi_total_sigma_" + key + "_Pa" for key in components]
    for ax, field in zip(axes.flat, mode_fields):
        for level in range(100):
            rr = layers[level::100]
            ax.plot(times, [v[field] for v in rr], lw=.5, alpha=.45)
        ax.set(xlabel="Actual saved time (s)", ylabel=field); ax.grid(True)
    axes.flat[-1].plot(times, [v["A_pi_Uz_RMS_mm"] for v in history], label="Uz RMS over100 layers (mm)")
    axes.flat[-1].set(xlabel="Actual saved time (s)", ylabel="Alternating Uz RMS (mm)"); axes.flat[-1].grid(True)
    fig.suptitle("All100 original material layers; signed alternating original X columns, saved states")
    fig.savefig(products["modes.png"], dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, len(requested), figsize=(24, 7), constrained_layout=True)
    for column, Tv in enumerate(requested):
        rr = [v for v in profiles if v["requested_Tv"] == Tv]
        for ax, quantity, unit, actual in ((axes[0, column], "P", "Pa", "actual_P_mean_Pa"),
                                          (axes[1, column], "settlement", "mm", "actual_settlement_mean_mm")):
            curves = [(actual, "-", "actual same IDs")] + [(name + "_" + quantity + "_at_actual_time_" + unit, style, reference_label(name))
                for name, style in (("H1_classical", "--"), ("H1_finite_Kw", ":"), ("H995_classical", (0, (1, 1))), ("H995_finite_Kw", "-."))]
            for field, style, label in curves:
                ax.plot([v[field] for v in rr], [v["z0_m"] for v in rr], linestyle=style, lw=1., label=label)
            ax.grid(True); ax.set_ylabel("Original material z0 (m)")
        timing = next(v for v in profile_times if v["requested_Tv"] == Tv)
        axes[0, column].set_title("Tv=%g\nt=%.6g s\ngap=%+.3g s" % (Tv, timing["actual_time_s"], timing["signed_time_gap_s"]), fontsize=8)
        axes[0, column].set_xlabel("P (Pa)"); axes[1, column].set_xlabel("Settlement (mm)")
    axes[0, 0].legend(fontsize=6); axes[1, 0].legend(fontsize=6)
    fig.suptitle("Primary H1 Tv targets; both unfitted heights evaluated at the same actual time and material IDs")
    fig.savefig(products["profiles.png"], dpi=160); plt.close(fig)
    result.update(source_native=native_e, common_prefix=common, requested_profile_times=profile_times,
        files=[u.adopt(path) for path in products.values()], all100_material_layers_exported=True,
        all6_total_stress_alternating_components_exported=True, native_rho_source="actual ledger.csv rho_native_kg_m3 by original ID",
        theory_constants=dict(E=E, nu=nu, M=M, k=k, rho_w=water, g_reference=g, Kw=Kw, n0=n0, q0=q0, H=H, tD=tD,
            Cv_legacy=Cv, B_finite_Kw=B, Cv_finite_Kw=B * Cv, modes=512),
        theory_reference_provenance=reference_provenance, sensitivity_pressure_plane_H_m=.995,
        theory_mean_definitions="Same-node arithmetic means evaluate all1000 original IDs at actual initial z0. Current-J-volume-weighted means use those same profiles and the native current J weights. Continuum means integrate0..H and divide byH; they are separate reference observables and never substituted for native arithmetic means.",
        theory_limits="H1 remains primary; H.995 is the pre-existing unfitted constrained-pressure-plane sensitivity, with identical XML constants, same material IDs, actual times and no fit. Both are quasi-static closed-loading then single-top-drainage companions. Dynamic inertia, finite ramp, top kernel traction, J evolution and the current dynamic step handler remain distinct. Neither height is selected as matched truth or a proof of residual cause; no theory accuracy acceptance.",
        rows=dict(history=len(history), layers=len(layers), theory=len(theory), profile_times=len(profile_times), profiles=len(profiles)),
        actual_saved_time_bounds_s=[float(times[0]), float(times[-1])],
        interpolation_or_clock_rewrite=False, new_accuracy_or_half_gate=False,
        old_formal_overlay_performed=False,
        old_formal_comparison_status="Deferred to root's separately qualified comparison after reading the actual retained u-pw summary CSV source; no matched truth or interpolation claimed.",
        comparison_is_descriptive_not_5Pa_or_0p005mm_equivalence=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("native", "review"), required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Explicit invocation of this one future offline phase required")
    record = T / "logs" / ("upl_bigstep_full_r1." + args.phase + ".json")
    need(not record.exists(), "Retained phase receipt protected; no retry, rearm or automatic follow-up")
    u = None
    result = dict(stage=NAME + "." + args.phase, passed=False, failure=None, physical_acceptance=False,
        solver_build_Git_queue_or_watcher_invoked=False, current_dynamic_step_handler_retained=True,
        old_control_resumed=False, source_run_or_raw_rewritten=False, automatic_follow_up=False, reader_attempts=0)
    try:
        u, f, p, owner, old = definitions()
        (native if args.phase == "native" else review)(u, f, p, owner, old, result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(u is not None, "Pinned pure definitions not initialized")
        result["inputs"] = u.final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(u.BOUND.values()) if u else []
        result["passed"] = result["bindings_unchanged"] = result["independent_final_rehash_performed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    with record.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], phase=args.phase, receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
