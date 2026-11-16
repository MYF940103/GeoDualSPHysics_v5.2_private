"""Root-admitted actual-GPU P1 unique read or offline review using the frozen r1 reader.

Each action is separate, requires its own frozen root admission, and has no
automatic follow-up. The retained neutral loader and old readers are read-only.
"""
from __future__ import annotations
import argparse
import csv
import math
from fractions import Fraction
import os
from pathlib import Path
import re
import shutil
import struct
import upl_tpi_cpu_build_r2 as b
import upl_tpi_gpu_completed_run_audit_r3 as audit

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_gpu_native_r4"
READER_TAG = "upl_tpi_gpu_native_r1"
CPP = T / "support" / (READER_TAG + ".cpp")
OLD_NOTE = T / "notes" / (READER_TAG + ".md")
NOTE = T / "notes" / (TAG + ".md")
SCRIPT = Path(__file__).resolve()
BASE = L / "upl_bigstep_native_r1.build.json"
COMPILE = L / "upl_bigstep_native_r1_Compile.call.json"
LINK = L / "upl_bigstep_native_r1_Link.call.json"
BUILDROOT = T / "outputs" / (READER_TAG + "_build")
BUILD = L / (READER_TAG + ".build.json")
PROGRAM = BUILDROOT / (READER_TAG + ".exe")
NEUTRAL = T / "support/upl_cpu_public_native_r1.cpp"
OLD_GPU_NATIVE = L / "upl_gpu_stabilizers_release_short_r1.native.json"
OLD_GPU_RUN = L / "upl_gpu_stabilizers_release_short_r1.run.json"
RETAINED = T / "outputs/upl_gpu_stabilizers_release_short_r1_native"
DT = 6.250143051147461e-6
WINDOWS = {
    "debug2steps": dict(steps=2, frames=2, end=1.2500286102294922e-5, post=0),
    "startup015": dict(steps=24000, frames=344, end=.1500034332275618, post=226),
}
SOURCE_FIXTURE_R2 = "UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0"
SIDECAR_COLUMNS = "part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_final_float_Pa,final_float_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks,hg_snapshot_checks".split(",")


def bits(value, kind="d"):
    return struct.pack("<" + kind, value)


def finite(value):
    x = float(value)
    b.need(math.isfinite(x), "Nonfinite native/pressure-sidecar field")
    return x


def f32(value):
    return struct.unpack("<f", bits(value, "f"))[0]


class Admission:
    def __init__(self, action, path):
        self.entry = b.stat(path)
        self.data = b.read(path)
        b.need(self.data.get("stage") == TAG + "." + action + "_admission"
               and self.data.get("passed") is True and self.data.get("action_only") is True,
               "Independently reviewed exact-action root admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}
        for p in (SCRIPT, NOTE, CPP, OLD_NOTE, Path(b.__file__), Path(audit.__file__), audit.NOTE):
            self.pin(p)
        self.finish()

    def pin(self, path):
        key = str(Path(path).resolve())
        b.need(key in self.frozen, "Consumed input absent from root admission: " + key)
        return b.same(self.frozen[key])

    def finish(self):
        for x in self.frozen.values():
            b.same(x)
        b.same(self.entry)


def no_active_reader(program, data=None):
    import psutil
    target = Path(program).resolve()
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        info = p.info
        name = (info.get("name") or "").lower()
        exe = info.get("exe")
        if name == target.name.lower():
            b.need(exe is not None, "A same-name reader has inaccessible identity")
            b.need(Path(exe).resolve() != target, "Original reader is already active; do not decode twice")
        if data and info.get("cmdline"):
            args = [str(x).lower() for x in info["cmdline"]]
            b.need(not ("--read" in args and str(Path(data).resolve()).lower() in args),
                   "A native reader already owns this data directory")


def pin_reader(ad):
    """Bind the existing r1 executable/CPP/runtime; no compiler or copy path."""
    ad.pin(BUILD); built = b.read(BUILD)
    b.need(built.get("stage") == READER_TAG + ".build" and built.get("passed") is True and
           built.get("solver_invocations") == built.get("reader_invocations") == 0 and
           built.get("old_reader_or_loader_changed") is False and
           built.get("original_dependencies_stats_unchanged") is True,
           "Original completed r1 reader implementation build is required")
    ad.pin(PROGRAM); b.same(built["program"])
    b.need(Path(built["program"]["path"]).resolve() == PROGRAM.resolve(),
           "Existing r1 reader program path differs")
    for entry in built["runtime"]:
        ad.pin(entry["destination"]["path"]); b.same(entry["destination"])
    return built


def get_job(ad):
    job = dict(ad.data["job"])
    cfg, scheme, window = (job[x] for x in ("configuration", "scheme", "window"))
    b.need((cfg, scheme, window) == ("Debug", "B", "debug2steps") or
           (cfg == "Release" and scheme in ("A", "B", "C") and window == "startup015"),
           "Exact independently admitted actual-GPU bounded profile required")
    b.need(re.fullmatch("upl_tpi_gpu_" + cfg + "_" + scheme + "_" + window + r"_r[1-9][0-9]*", job["tag"]),
           "Actual owner tag/profile differs")
    job["native_output"] = str(T / "outputs" / (job["tag"] + "_native_r4"))
    for key in ("run_receipt", "call", "program", "plan", "run_out"):
        ad.pin(job[key]["path"])
        b.same(job[key])
    run, call = b.read(job["run_receipt"]["path"]), b.read(job["call"]["path"])
    start_path = L / (job["tag"] + ".start.json")
    ad.pin(start_path); start = b.read(start_path)
    completion_checks = run
    if run.get("passed") is not True:
        completion_checks = audit.accept_review(ad, job, run, call)
    else:
        b.need("completed_run_review" not in job, "Successful runs must use their original sealed completion")
    b.need(call.get("passed") is True and run.get("scheme") == scheme
           and run.get("window") == window and run.get("configuration") == cfg,
           "Original sealed GPU owner result/profile differs")
    program = Path(job["program"]["path"]).resolve()
    for entry in (run["program"], call["target_program"], start["program"]):
        b.same(entry)
    b.need(Path(run["program"]["path"]).resolve() == program
           and Path(call["target_program"]["path"]).resolve() == program
           and Path(call["target"]["exe"]).resolve() == program
           and Path(start["target"]["exe"]).resolve() == program
           and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") ==
               call.get("target_actual_Win32_exit") == 0
           and call.get("target_handle_acquired_before_wait") is True
           and call["target"] == start["target"] == run["target"],
           "Actual native tool/target handles, creation identity or exits differ")
    b.need(call["target"]["argv"][1:] == call["target_arguments"] == run["arguments"]
           and abs((call["target_creation_FILETIME_ticks"] - 116444736000000000) / 1e7 -
                   call["target"]["created"]) <= 1e-6,
           "Actual target argv/Win32 creation time differs")
    if cfg == "Debug":
        b.need(call.get("tool_is_solver") is False and
               Path(call["program"]["path"]).name.lower() == "compute-sanitizer.exe"
               and completion_checks.get("actual_memcheck_zero_errors") is True,
               "Actual Debug GPU target must have genuine zero-error memcheck tool evidence")
        mem = completion_checks["memcheck_log"]; ad.pin(mem["path"]); b.same(mem)
        b.need(re.search(r"ERROR SUMMARY:\s*0 errors", Path(mem["path"]).read_text(encoding="utf-8-sig", errors="replace")),
               "Bound actual sanitizer log lacks zero-error summary")
    else:
        b.need(call.get("tool_is_solver") is True and Path(call["program"]["path"]).resolve() == program,
               "Release must be the actual direct GPU target")
    b.need(run["actual_environment"].get("UPL_TPI_GPU_R1") == scheme
           and call["actual_environment"].get("UPL_TPI_GPU_R1") == scheme,
           "Owned actual GPU scheme environment differs")
    for key in ("source_build", "prepared"):
        ad.pin(run[key]["path"])
        b.same(run[key])
    built = b.read(run["source_build"]["path"])
    prepared = b.read(run["prepared"]["path"])
    built_prepare = built.get("source_prepare", built.get("prepared"))
    b.need(built.get("passed") is True and built.get("configuration") == cfg and
           Path(built["program"]["path"]).resolve() == program and isinstance(built_prepare, dict) and
           Path(built_prepare["path"]).resolve() == Path(run["prepared"]["path"]).resolve() and
           prepared.get("passed") is True and "base_prepare" in prepared and
           prepared.get("host_h_API_and_other_268_files_byte_identical") is True,
           "Unpatched GPU r1 cannot become the physical source baseline")
    b.same(built["program"]); b.same(built_prepare)
    output, data = Path(job["output_directory"]).resolve(), Path(job["data"]).resolve()
    b.need(output == Path(run["output_directory"]).resolve() and data == output / "data"
           and output.is_relative_to((T / "outputs").resolve()) and
           Path(job["run_out"]["path"]).resolve() == output / "Run.out", "Original GPU output/data ownership differs")
    text = Path(job["run_out"]["path"]).read_text(encoding="utf-8-sig")
    ad.pin(call["log"]["path"])
    console = Path(call["log"]["path"]).read_text(encoding="utf-8-sig", errors="replace")
    b.need('RunMode="Stable - Pos-Cell - Single-GPU"' in text and
           console.count(SOURCE_FIXTURE_R2) == (0 if scheme == "A" else 1),
           "Actual GPU backend/once-only source-role device fixture evidence differs")
    for p in data.glob("Part_*.bi4"):
        ad.pin(p)
    return job


def read_native(ad):
    job = get_job(ad)
    check = L / (job["tag"] + ".native_r4.json")
    target = Path(job["native_output"])
    protected = [check, target]
    protected += [L / (job["tag"] + ".native_" + version + ".json") for version in ("r1", "r2", "r3")]
    protected += [T / "outputs" / (job["tag"] + "_native_" + version) for version in ("r1", "r2", "r3")]
    protected += [L / (job["tag"] + ".native_" + version + suffix)
                  for version in ("r1", "r2", "r3", "r4") for suffix in (".call.json", ".log", ".stdout.log", ".stderr.log")]
    b.need(not any(p.exists() for p in protected), "Any existing native attempt/output is protected")
    pin_reader(ad)
    no_active_reader(PROGRAM, job["data"])
    result = dict(stage=TAG + ".read", passed=False, job=job, root_admission=ad.entry,
                  actual_common_reader_build_helper=ad.pin(Path(b.__file__)),
                  reader_program=b.stat(PROGRAM), reader_build=ad.pin(BUILD), reader_source=ad.pin(CPP),
                   reader_implementation_r1=READER_TAG, reviewer_r4=TAG, physical_acceptance=False,
                  solver_invocations=0, build_invocations=0, read_attempts=1)
    try:
        call, _ = b.invoke(job["tag"] + ".native_r4", [str(PROGRAM), "--read", "GPU", job["data"],
                           job["plan"]["path"], job["window"], str(target)], S / "VS", os.environ.copy())
        result["call"] = call
        done = b.read(target / "completion.json")
        w = WINDOWS[job["window"]]
        b.need(done.get("passed") is True and done["samples"] == w["frames"]
               and done.get("stage") == READER_TAG and done.get("backend") == "GPU_P1_private"
               and done.get("window") == job["window"] and done.get("native_total_arrays") == 22
               and done["actual_end_s"] == w["end"] and done["post_open_frames"] == w["post"]
               and done["post_open_drained_particle_checks"] == 10 * w["post"],
               "Independent bounded native completion differs")
        ad.finish()
        result.update(passed=True, completion=b.stat(target / "completion.json"),
                      files=[b.stat(p) for p in target.iterdir() if p.is_file()],
                      pressure_scheme_not_proven_by_legacy_BI4_metadata=True)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(check, result)


def hg_run(job):
    text = Path(job["run_out"]["path"]).read_text(encoding="utf-8-sig", errors="strict")
    steps = WINDOWS[job["window"]]["steps"]
    first = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    second = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    guard = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    b.need(first and second and guard and tuple(map(int, first.groups())) == (2 * steps, steps, steps, 2 * steps)
           and tuple(map(int, second.groups())) == (steps + 1, steps - 1), "Original logical/actual HG phase/cache counters differ")
    net, actual, tau, spin = map(finite, guard.groups())
    b.need(min(net, actual, tau, spin) >= 0 and tau <= .2 and spin < .01,
           "Original HG stiffness/small-spin safety failed")
    return dict(forcecalls=2 * steps, predictorupdates=steps, correctorupdates=steps,
                ratecalls=2 * steps, ratecalculations=steps + 1, cachehits=steps - 1,
                max_reference_net=net, max_actual_float_net=actual, max_dt_tau=tau, spinbound=spin)


def load_plan(path, window):
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8-sig", newline="")))
    w = WINDOWS[window]
    b.need(len(rows) == w["frames"] and int(rows[-1]["completed_steps"]) == w["steps"], "Exact bounded plan differs")
    clock = [0.]
    for _ in range(w["steps"]):
        clock.append(clock[-1] + DT)
    for part, row in enumerate(rows):
        n = int(row["completed_steps"])
        b.need(int(row["part"]) == part and bits(float(row["time_s"])) == bits(clock[n])
               and float(row["dt_s"]) == DT and int(row["saved_step"]) == (n - 1 if n else 0),
               "CSV exact scalar clock/zero-based step differs")
    return rows, clock


def prefix_A(ad, job):
    """True same-backend records joined by actual time bits AND native Step.

    Five exports cover their declared fields only, never all22 raw-array proof.
    Original distinct headers remain intact; no assumed final-frame sharing.
    """
    current = Path(job["native_output"])
    for p in (OLD_GPU_RUN, OLD_GPU_NATIVE, RETAINED / "completion.json"):
        ad.pin(p)
    oldrun, oldnative = b.read(OLD_GPU_RUN), b.read(OLD_GPU_NATIVE)
    olddone = b.read(RETAINED / "completion.json")
    b.need(oldrun.get("passed") is True and oldnative.get("passed") is True and
           olddone.get("passed") is True and olddone.get("backend") == "GPU_public",
           "Retained actual old GPU control and native receipt required")
    def read_clock(path, expected):
        ad.pin(path)
        with path.open("rb") as f:
            b.need(struct.unpack("<II", f.read(8)) == (expected, 28), "Original clock declaration differs")
            rows = [f.read(28) for _ in range(expected)]
            b.need(all(len(x) == 28 for x in rows) and f.read(1) == b"", "Clock payload truncated/extra")
        keys = [(x[:8], struct.unpack_from("<I", x, 8)[0]) for x in rows]
        b.need(len(set(keys)) == len(keys), "Duplicate actual time/step native key")
        return rows, keys
    oldcount, newcount = int(olddone["samples"]), WINDOWS[job["window"]]["frames"]
    oldclock, oldkeys = read_clock(RETAINED / "clock.bin", oldcount)
    newclock, newkeys = read_clock(current / "clock.bin", newcount)
    lookup = {key: i for i, key in enumerate(newkeys)}
    shared = [(i, lookup[key]) for i, key in enumerate(oldkeys) if key in lookup]
    b.need(shared and shared[0] == (0, 0), "Genuine actual-time/step control overlap missing")
    results = []
    declarations = {"original15.bin": ((1040, 15), 166408), "physical.bin": ((1000, 26), 208008),
                    "common_j_theta.bin": ((1040, 2), 16648), "soil_n.bin": ((1000, 1), 8008),
                    "clock.bin": (None, 28)}
    for name, (shape, stride) in declarations.items():
        old, new = RETAINED / name, current / name
        ad.pin(old); ad.pin(new); hsize = 8 if shape is None else 12
        with old.open("rb") as a, new.open("rb") as z:
            ah = struct.unpack("<" + "I" * (hsize // 4), a.read(hsize))
            zh = struct.unpack("<" + "I" * (hsize // 4), z.read(hsize))
            b.need((ah == (oldcount, 28) and zh == (newcount, 28)) if shape is None else
                   ah == (*shape, oldcount) and zh == (*shape, newcount), "Original separate binary headers differ")
            for oi, ni in shared:
                a.seek(hsize + stride * oi); z.seek(hsize + stride * ni)
                x, y = a.read(stride), z.read(stride)
                b.need(len(x) == len(y) == stride and x == y,
                       "Default-A oldGPU shared exported payload differs: " + name + " old/new=" + str((oi, ni)))
        results.append(dict(file=name, original_header=ah, new_header=zh, shared_records=len(shared),
                            all_shared_export_record_bytes_equal=True, header_rewritten=False))
    return dict(files=results, actual_shared_old_new_indices=shared,
                old_unshared_indices=[i for i, x in enumerate(oldkeys) if x not in lookup],
                record_join_uses_actual_time_bits_and_saved_Step=True,
                final_record_preclassified_as_shared=False, all22_raw_array_bit_proof=False)


def sidecar(ad, job, plan, clock):
    output = Path(job["output_directory"])
    paths = [output / ("UplTpiGpuR1" + suffix) for suffix in (".policy.json", ".csv", ".summary.json")]
    if job["scheme"] == "A":
        b.need(not any(p.exists() for p in paths), "Untaken default-A branch must not create TPI sidecars")
        return dict(expected_absent=True, native_scheme_evidence="Actual owned environment plus default-A branch")
    for p in paths:
        ad.pin(p)
    policy, summary = b.read(paths[0]), b.read(paths[2])
    scheme = "B_TPI_alpha_0p5_beta0" if job["scheme"] == "B" else "C_PPE_t_alpha0_beta0"
    alpha = .5 if job["scheme"] == "B" else 0.
    b.need(policy.get("stage") == "upl_tpi_gpu_r1" and policy.get("scheme") == scheme
           and policy.get("alpha") == alpha and policy.get("beta") == 0 and policy.get("M0") is True
           and policy.get("native_count") == 1040 and policy.get("soil_count") == 1000
           and policy.get("history_ID_owned") is True and policy.get("history_cold_start") is True
           and policy.get("half_equals_endpoint_history_guess") is True
           and policy.get("endpoint_source_clock_is_original_n") is True,
           "Actual private M0 scheme/history policy differs")
    for document in (policy, summary):
        b.need(document.get("full_restart_supported") is False and document.get("paper_literal_LF") is False
               and document.get("second_order_claimed") is False and document.get("true_implicit_solution") is False
               and document.get("physical_acceptance") is False, "Prototype limits must remain explicit")
    w = WINDOWS[job["window"]]
    b.need(summary.get("completed") is True and summary.get("scheme") == scheme and summary.get("alpha") == alpha
           and summary.get("beta") == 0 and summary.get("commits") == summary.get("endpoint_calls") == w["steps"]
           and summary.get("core_field_bit_checks") == 7000 * w["steps"]
           and summary.get("HG_readonly_snapshot_checks") == 2000 * w["steps"]
           and summary.get("PorePressRate_is_legacy_scaled_residual_not_dpdt") is True
           and bits(float(summary["actual_end"])) == bits(w["end"]), "Actual completed lifecycle summary differs")
    rowcount, max_rounding = 0, 0.
    J_nonfused_matches = J_fused_matches = J_both_matches = 0
    import numpy as np
    physical = Path(job["native_output"]) / "physical.bin"
    with paths[1].open(encoding="utf-8-sig", newline="") as f, physical.open("rb") as native:
        reader = csv.DictReader(f)
        b.need(reader.fieldnames == SIDECAR_COLUMNS, "Exact 28-column sidecar schema differs")
        b.need(struct.unpack("<III", native.read(12)) == (1000, 26, w["frames"]), "Case02 physical export header differs")
        for part, planned in enumerate(plan):
            n = int(planned["completed_steps"])
            actual_time = struct.unpack("<d", native.read(8))[0]
            state = np.frombuffer(native.read(1000 * 26 * 8), dtype="<f8").reshape(1000, 26)
            b.need(bits(actual_time) == bits(clock[n]), "Sidecar/native actual saved time differs")
            seen, source_count, endpoint_count, commit_count = set(), 0, 0, 0
            for _ in range(1000):
                row = next(reader, None)
                b.need(row is not None and list(row) == SIDECAR_COLUMNS, "Missing/extra sidecar columns or rows")
                values = {k: finite(v) for k, v in row.items()}
                k = int(values["native_id"])
                b.need(values["native_id"] == k and 40 <= k < 1040 and k not in seen and values["part"] == part,
                       "Sidecar native ownership/part duplicated or changed")
                seen.add(k)
                b.need(values["completed_step"] == values["commits"] == values["endpoint_calls"] == n
                       and values["source_step_zero_based"] == (n - 1 if n else 0)
                       and values["core_field_bit_checks"] == 7000 * n and values["hg_snapshot_checks"] == 2000 * n
                       and bits(values["source_time_s"]) == bits(clock[n - 1 if n else 0])
                       and bits(values["actual_save_time_s"]) == bits(clock[n]) and values["dt_s"] == DT,
                       "Saved actual source/commit/history counters or scalar clock differ")
                final, J = state[k - 40, 6], state[k - 40, 8]
                b.need(bits(values["final_float_Pa"], "f") == bits(final, "f")
                       and bits(values["Jfull"]) == bits(J), "Saved sidecar pressure/J differs from native state")
                flags = [values[x] for x in ("source_drained", "endpoint_drained", "commit_drained")]
                b.need(all(x in (0., 1.) for x in flags), "Dirichlet flags are not exact booleans")
                source_count += int(flags[0]); endpoint_count += int(flags[1]); commit_count += int(flags[2])
                if not n:
                    b.need(all(values[x] == 0. for x in ("pn_Pa", "previous_Pa", "prediction_double_Pa", "half_actual_float_Pa", "endpoint_q_actual_float_Pa", "S_1_per_m_s", "Rgamma_Pa_per_m_s", "raw_final_float_Pa", "final_float_Pa"))
                           and values["Jn"] == values["Jhalf"] == values["Jfull"] == 1., "Cold initial sidecar state differs")
                    rowcount += 1
                    continue
                prediction = values["pn_Pa"] if alpha == 0 else values["pn_Pa"] + alpha * (values["pn_Pa"] - values["previous_Pa"])
                b.need(bits(values["prediction_double_Pa"]) == bits(prediction), "Actual history pressure prediction differs")
                half = 0. if flags[0] else f32(prediction)
                b.need(bits(values["half_actual_float_Pa"], "f") == bits(half, "f"), "Mechanical half pressure history/Dirichlet differs")
                diagonal, residual, q = (values[x] for x in ("S_1_per_m_s", "Rgamma_Pa_per_m_s", "endpoint_q_actual_float_Pa"))
                b.need(bits(q, "f") == bits(0. if flags[1] else f32(prediction), "f"),
                       "Actual endpoint q is not the same history prediction under original endpoint BC")
                if flags[1]:
                    b.need(diagonal == residual == 0., "A constrained endpoint row must not claim an elliptic residual")
                    raw = 0.
                else:
                    b.need(diagonal > 0., "Nonpositive/nonfinite elliptic diagonal is not masked or regularized")
                    exact = q + residual / diagonal
                    raw = f32(exact)
                    max_rounding = max(max_rounding, abs(raw - exact))
                b.need(bits(values["raw_final_float_Pa"], "f") == bits(raw, "f")
                       and bits(values["final_float_Pa"], "f") == bits(0. if flags[2] else raw, "f"),
                       "Actual beta0 float writeback or original final Dirichlet policy differs")
                # Preserve original CUDA -use_fast_math/fmad. Original expression
                # is left-associated DT*Jhalf*theta followed by add to Jn.
                # First product is rounded binary64. Final multiply/add can be
                # separate or legally fused, both replayed exactly, no ULP slack.
                product = DT * values["Jhalf"]
                plain = values["Jn"] + product * values["theta_half_for_J_1_per_s"]
                fused = float(Fraction.from_float(values["Jn"]) + Fraction.from_float(product) *
                              Fraction.from_float(values["theta_half_for_J_1_per_s"]))
                nmatch = bits(values["Jfull"]) == bits(plain)
                fmatch = bits(values["Jfull"]) == bits(fused)
                b.need(nmatch or fmatch, "Original CUDA single J expression matches neither reviewed exact compiler path")
                J_nonfused_matches += int(nmatch); J_fused_matches += int(fmatch)
                J_both_matches += int(nmatch and fmatch)
                rowcount += 1
            expected_drain = 10 if n > 1600 else 0
            b.need(len(seen) == 1000 and source_count == endpoint_count == commit_count == expected_drain,
                   "All actual source/endpoint/commit Dirichlet owner counts differ")
        b.need(next(reader, None) is None and native.read(1) == b"", "Trailing sidecar or native records differ")
    return dict(rows=rowcount, expected_rows=1000 * w["frames"], actual_ID_owned_history=True,
                actual_M0_alpha=alpha, beta=0, max_actual_pressure_float_writeback_rounding_Pa=max_rounding,
                per_saved_row_formula_and_J_corrector_checked=True,
                J_noninitial_rows_checked=J_nonfused_matches + J_fused_matches - J_both_matches,
                J_nonfused_path_matches=J_nonfused_matches, J_fused_path_matches=J_fused_matches,
                J_both_paths_match=J_both_matches, J_added_ULP_tolerance=0,
                original_CUDA_fast_math_and_fmad_preserved=True,
                unsaved_history_values_independently_observed=False,
                PorePressRate_is_legacy_scaled_endpoint_residual_not_actual_dpdt=True,
                no_finite_Kw_or_half_equivalence_claim=True)


def cross_cpu(ad, job):
    import numpy as np
    control = ad.data["cpu_control"]
    for name in ("review", "native", "completion"):
        ad.pin(control[name]["path"])
    reviewed, native = b.read(control["review"]["path"]), b.read(control["native"]["path"])
    done = b.read(control["completion"]["path"])
    cj = reviewed["job"]
    b.need(reviewed.get("passed") is True and native.get("passed") is True and done.get("passed") is True
           and cj["scheme"] == job["scheme"] and cj["configuration"] == "ReleaseCPU"
           and cj["window"] == job["window"] == "startup015" and done.get("samples") == 344,
           "Passed actual same-scheme CPU startup control required")
    gpu, cpu = Path(job["native_output"]), Path(cj["native_output"])
    b.need(Path(control["completion"]["path"]).resolve() == cpu / "completion.json"
           and Path(native["job"]["native_output"]).resolve() == cpu,
           "CPU review/read/completion output bindings differ")
    for directory in (gpu, cpu):
        for name in ("physical.bin", "clock.bin", "native_ids.csv"):
            ad.pin(directory / name)
    b.need((gpu / "native_ids.csv").read_bytes() == (cpu / "native_ids.csv").read_bytes(),
           "Actual initial-material IDs/reference coordinates differ across backend")
    history = []
    with (gpu / "physical.bin").open("rb") as g, (cpu / "physical.bin").open("rb") as c, \
         (gpu / "clock.bin").open("rb") as gc, (cpu / "clock.bin").open("rb") as cc:
        b.need(g.read(12) == c.read(12) == struct.pack("<III", 1000, 26, 344)
               and gc.read(8) == cc.read(8) == struct.pack("<II", 344, 28), "CPU/GPU declaration differs")
        for part in range(344):
            grow, crow = gc.read(28), cc.read(28)
            b.need(len(grow) == len(crow) == 28 and grow[:20] == crow[:20],
                   "Same-scheme CPU/GPU actual time, saved Step or dt differs")
            gt, ct = g.read(8), c.read(8)
            b.need(gt == ct == grow[:8], "Physical/clock exact actual time differs")
            ga = np.frombuffer(g.read(208000), dtype="<f8").reshape(1000, 26)
            ca = np.frombuffer(c.read(208000), dtype="<f8").reshape(1000, 26)
            b.need(np.isfinite(ga).all() and np.isfinite(ca).all(), "Nonfinite same-scheme backend data")
            pressure = float(np.sqrt(np.mean((ga[:, 6] - ca[:, 6])**2)))
            difference = ga[:, :3] - ca[:, :3]
            difference[:, 0] -= .1 * np.floor(difference[:, 0] / .1 + .5)
            displacement = float(1000. * np.max(np.linalg.norm(difference, axis=1)))
            b.need(pressure <= 5. and displacement <= .005,
                   "Original same-scheme backend pressure/material-displacement budget failed at part=" + str(part))
            history.append(dict(part=part, time_s=struct.unpack("<d", gt)[0], pressure_RMS_Pa=pressure,
                                material_XYZ_displacement_max_mm=displacement))
        b.need(g.read(1) == c.read(1) == gc.read(1) == cc.read(1) == b"", "Trailing backend records")
    return dict(passed=True, scheme=job["scheme"], samples=344,
                max_pressure_RMS_Pa=max(x["pressure_RMS_Pa"] for x in history),
                max_material_XYZ_displacement_mm=max(x["material_XYZ_displacement_max_mm"] for x in history),
                all_sample_metrics=history, pressure_RMS_limit_Pa=5., material_displacement_limit_mm=.005,
                minimum_image_x_period_m=.1, Y_Z_displacements_direct=True,
                interpolation=False, native_22_array_cross_backend_bit_equality_claimed=False,
                cross_scheme_or_half_comparison=False)


def review(ad):
    job = get_job(ad)
    path = L / (job["tag"] + ".native_review_r4.json")
    b.need(not path.exists(), "Existing native review, including failure, is protected")
    native = L / (job["tag"] + ".native_r4.json"); ad.pin(native)
    pin_reader(ad)
    result = dict(stage=TAG + ".review", passed=False, root_admission=ad.entry, job=job,
                  actual_common_reader_build_helper=ad.pin(Path(b.__file__)), physical_acceptance=False,
                  reader_implementation_r1=READER_TAG, reviewer_r4=TAG,
                   cross_model_5Pa_or_half_equivalence_gate=False, solver_reader_or_build_invocations=0)
    try:
        b.need(b.read(native).get("passed") is True, "Independent unique native gate must pass first")
        for p in Path(job["native_output"]).iterdir():
            if p.is_file(): ad.pin(p)
        plan, clock = load_plan(job["plan"]["path"], job["window"])
        result["HG_original_guards"] = hg_run(job)
        result["sidecar"] = sidecar(ad, job, plan, clock)
        if job["scheme"] == "A":
            result["retained_actual_GPU_A_shared_records"] = prefix_A(ad, job)
        elif job["configuration"] == "Release":
            result["same_scheme_CPU_GPU"] = cross_cpu(ad, job)
        else:
            result["Debug_is_not_Release_bit_truth"] = True
        ad.finish()
        result.update(passed=True, original_native_guards_not_relaxed=True,
                      no_interpolation_or_header_clock_rewrite=True,
                      full_cycle_theory_restart_or_physical_acceptance=False,
                      later_pressure_settlement_stress_comparison_required=True)
    except Exception as exc:
        result["failure"] = str(exc); raise
    finally:
        b.write_new(path, result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["read", "review"])
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    a = p.parse_args()
    b.need(a.execution_authorized, "One independently reviewed root action required")
    ad = Admission(a.action, a.admission)
    {"read": read_native, "review": review}[a.action](ad)


if __name__ == "__main__":
    main()
