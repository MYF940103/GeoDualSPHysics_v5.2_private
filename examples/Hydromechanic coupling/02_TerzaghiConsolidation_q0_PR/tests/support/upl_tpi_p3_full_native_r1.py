"""Separate full10us native read/review; no solver, build, VTK or follow-up action."""
from __future__ import annotations
import argparse
from array import array
import csv
import os
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode = True
import upl_tpi_p3_full_run_r1 as runmod
import upl_tpi_p3_full_short_r1 as short
import upl_tpi_p3_native_r1 as science
import upl_tpi_m0_full10us_native_build_r1 as readerbuild

c, T, L = runmod.c, runmod.T, runmod.L
TAG = "upl_tpi_p3_full_native_r1"
NOTE = T / "notes" / (TAG + ".md")
JOB = "upl_tpi_p3_B10us_full2tv_GPU_r1"
PROFILE = dict(steps=7288262, frames=1653, end=72.88428815806371, post=1549)
DT, CAP = 1.0000228881835938e-5, 72.88428690075874
READER_ROOT = L / "upl_tpi_m0_full10us_native_root_r1.review.json"
OLD_TAG = "upl_tpi_p3_B10us_window2s_GPU_r1"
OLD_REVIEW = L / (OLD_TAG + ".native_review_p3_r1.json")


class Admission(c.Admission):
    def __init__(self, action, path):
        self.entry, self.data, self.consumed = c.stat(path), c.read(path), {}
        c.need(self.data.get("stage") == TAG + "." + action + "_admission"
               and self.data.get("passed") is True and self.data.get("action_only") is True,
               "One independent exact native action admission is required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        c.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate admitted input")
        for p in (Path(__file__), NOTE, Path(runmod.__file__), runmod.NOTE,
                  Path(runmod.p3.__file__), runmod.p3.NOTE, Path(runmod.p3.old.__file__),
                  Path(runmod.gpu.__file__), Path(runmod.planmod.__file__), runmod.planmod.NOTE,
                  Path(short.__file__), short.NOTE, Path(science.__file__), science.NOTE,
                  Path(science.m0.__file__), Path(science.m0.b.__file__),
                  Path(science.m0.original.__file__), Path(c.__file__),
                  Path(readerbuild.__file__), readerbuild.CPP, readerbuild.NOTE, readerbuild.NEUTRAL):
            self.pin(p)


def pin_reader(ad):
    entry = ad.pin(readerbuild.BUILD)
    built = c.read(readerbuild.BUILD)
    c.need(built.get("stage") == readerbuild.TAG + ".build" and built.get("passed") is True
           and built.get("private_offline_reader") is True
           and built.get("configuration") == "CPU-only Release native utility (/O2 /MT)"
           and built.get("solver_invocations") == built.get("reader_invocations")
           == built.get("CUDA_compilations") == 0, "The genuine exact full10us reader build is required")
    re = ad.pin(READER_ROOT)
    root = c.read(READER_ROOT)
    program = ad.pin(readerbuild.PROGRAM)
    c.same(built["program"])
    c.need(root.get("stage") == "upl_tpi_m0_full10us_native_root_r1"
           and root.get("passed") is True and root["build"] == entry and root["program"] == program
           and root["body_predicates_bytewise_retained_from_M0"] is True
           and root["only_declared_full_profile_CLI_completion_label_changed"] is True,
           "Independent full-profile reader identity/body proof differs")
    for e in built["calls"]:
        ad.pin(e["path"]); c.same(e)
        call = c.read(e["path"])
        c.need(call.get("passed") is True and call.get("actual_Popen_wait_exit")
               == call.get("actual_Win32_exit") == 0, "Actual full reader build tool exits differ")
    for e in built["runtime"]:
        ad.pin(e["destination"]["path"]); c.same(e["destination"])
    return dict(build=entry, root_review=re, program=program)


def get_job(ad):
    c.need(ad.data["job"]["tag"] == JOB, "Only the exact future full P3 tag is supported")
    rp = L / (JOB + ".run.json")
    re = ad.pin(rp)
    run = c.read(rp)
    c.need(run.get("stage") == runmod.STAGE + ".run" and run.get("passed") is True
           and (run["tag"], run["mode"], run["window"], run["configuration"], run["scheme"])
           == (JOB, "full2tv", "full2tv", "Release", "B")
           and run.get("solver_invocations") == 1 and run["PART_restart"] is False
           and run["pressure_history_cold_start"] is True
           and run.get("full2Tv_solver_summary_completed") is True,
           "A genuinely completed owned full solver, not an old short run, is required")
    status_entry = ad.pin(L / (JOB + ".status.json"))
    status = c.read(status_entry["path"])
    c.need(status.get("stage") == JOB + ".status" and status.get("passed") is True
           and status["run"] == re, "Actual original full terminal status/run association differs")
    for key in ("call", "program", "source_build", "source_prepare", "root_admission", "plan",
                "full_plan_prepare", "reference_run"):
        ad.pin(run[key]["path"]); c.same(run[key])
    for e in [*run["runtime"], *run["seed"]]:
        ad.pin(e["path"]); c.same(e)
    rootad = c.read(run["root_admission"]["path"])
    c.need(rootad.get("stage") == runmod.STAGE + ".run_admission" and rootad.get("passed") is True
           and rootad.get("one_job_only") is True and rootad["job"]["tag"] == JOB
           and (rootad["job"]["mode"], rootad["job"]["configuration"], rootad["job"]["scheme"])
           == ("full2tv", "Release", "B"), "Actual full root admission differs")
    be, pe, program, runtime = short.source_build(ad, rootad["job"], "Release")
    c.need((be, pe, program, runtime) == (run["source_build"], run["source_prepare"], run["program"], run["runtime"]),
           "Actual new full-scope source/program/runtime provenance differs")
    c.need(Path(run["full_plan_prepare"]["path"]).resolve() == runmod.PREP.resolve(), "Wrong full plan preparation")
    prep = c.read(run["full_plan_prepare"]["path"])
    c.need(prep.get("stage") == runmod.planmod.TAG + ".prepare" and prep.get("passed") is True
           and prep.get("consumed_stats_unchanged") is True and prep.get("XML_only_TimeMax_value_changed") is True
           and prep.get("XML_comments_and_all_other_bytes_retained") is True
           and prep["clock"] == run["clock"] and prep["plan"] == run["plan"] and prep["seed"] == run["seed"]
           and prep["input_prefix"] == run["input_prefix"], "Bound immutable full input/plan differs")
    ad.pin(prep["config"]["path"]); c.same(prep["config"])
    w = run["clock"]
    c.need(w["completed_updates"] == PROFILE["steps"] and w["native_frames"] == PROFILE["frames"]
           and c.bits(w["actual_fixed_dt_s"]) == c.bits(DT)
           and c.bits(w["actual_scalar_end_s"]) == c.bits(PROFILE["end"])
           and c.bits(w["runtime_TimeMax_s"]) == c.bits(CAP) and w["nsteps_upper_cap"] == PROFILE["steps"]
           and w["event_completed_step"] == 1000 and w["event_step_is_preopen"] is True
           and w["post_open_frames"] == PROFILE["post"] and w["expected_true_drained_receivers"] == 15490
           and w["n_times_dt_clock_used"] is False, "Exact full scalar/count/drain declaration differs")
    c.need(Path(run["reference_run"]["path"]).resolve() == runmod.REFERENCE.resolve(), "Wrong original P3 window reference")
    ref = c.read(run["reference_run"]["path"])
    c.need(ref.get("stage") == "upl_tpi_p3_run_r1.run" and ref.get("passed") is True
           and (ref["tag"], ref["mode"], ref["scheme"], ref["configuration"])
           == (OLD_TAG, "window2s", "B", "Release"), "The genuine retained P3 2s reference is required")
    argv = list(ref["arguments"])
    for old, new in ((ref["input_prefix"], run["input_prefix"]),
                     (ref["output_directory"], run["output_directory"]), ("-nsteps:200000", "-nsteps:7288262")):
        c.need(argv.count(old) == 1, "Original argv source item is not unique")
        argv[argv.index(old)] = new
    c.need(argv == run["arguments"], "Full argv changed beyond its declared input/output/cap")
    out = T / "outputs" / JOB
    c.need(Path(run["output_directory"]).resolve() == out.resolve()
           and Path(run["data"]).resolve() == (out / "data").resolve(), "Full output/data association differs")
    se = ad.pin(L / (JOB + ".start.json"))
    start, call = c.read(se["path"]), c.read(run["call"]["path"])
    c.need(call.get("passed") is True and call["actual_Popen_wait_exit"] == call["actual_Win32_exit"]
           == call["target_actual_Win32_exit"] == run["actual_Popen_wait_exit"]
           == run["actual_Win32_exit"] == run["target_actual_Win32_exit"] == 0
           and start["owner"] == call["owner"] and start["program"] == program and start["source_build"] == be,
           "Actual full tool/target handle exits or owner/source differ")
    target = call["target"]
    ticks = call["target_creation_FILETIME_ticks"]
    c.need(call["tool_is_solver"] is True and call["target_handle_acquired_before_wait"] is True
           and target == start["target"] == run["target"] == call["child"] == start["tool"]
           and target["parent"] == call["owner"]["pid"] and Path(target["exe"]).resolve() == Path(program["path"]).resolve()
           and target["argv"][1:] == run["arguments"] == start["arguments"]
           and abs((ticks - 116444736000000000) / 1e7 - target["created"]) <= 1e-6,
           "Actual full target exe/argv/creation/pre-wait ownership differs")
    env = run["actual_environment"]
    expected = {k: None for k in runmod.p3.ENV_KEYS}
    expected.update(UPL_TPI_GPU_R1="B", UPL_TPI_M0_DT_R1="EQ40_RH1", UPL_TPI_P3_ROWS_R1="3")
    c.need(set(env) == set((*runmod.p3.ENV_KEYS, "OMP_NUM_THREADS", "OMP_DYNAMIC"))
           and all(env[k] == v for k, v in expected.items())
           and env == start["actual_environment"] == call["actual_environment"], "Actual complete full selectors differ")
    paths = {"log": L / (JOB + ".log"), "memcheck": L / (JOB + ".memcheck.log")}
    for p in (paths["log"], out / "Run.out", out / "Run.csv"):
        ad.pin(p)
    for prefix in ("UplTpiP3DtR1", "UplTpiP3GpuR1"):
        for suffix in (".policy.json", ".summary.json"):
            ad.pin(out / (prefix + suffix))
    runmod.p3.check_output(dict(run, paths=paths))  # Pure context-parameter runtime checks, no old get_job/main.
    clock = array("d", [0.])
    for _ in range(PROFILE["steps"]):
        clock.append(clock[-1] + DT)
    c.need(c.bits(clock[-1]) == c.bits(PROFILE["end"]) and clock[-2] < CAP <= clock[-1],
           "Actual binary64 scalar full TimeMax crossing differs")
    with Path(run["plan"]["path"]).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); rows = list(reader)
        c.need(reader.fieldnames == runmod.planmod.HEADER and len(rows) == PROFILE["frames"], "Exact eight-column full plan required")
    previous, target_time = -1, 0.
    for i, row in enumerate(rows):
        n = int(row["completed_steps"])
        c.need(previous < n <= PROFILE["steps"] and int(row["part"]) == i
               and int(row["saved_step"]) == (n - 1 if n else 0)
               and c.bits(float(row["time_s"])) == c.bits(clock[n]) and c.bits(float(row["dt_s"])) == c.bits(DT)
               and int(row["post_open_by_completed_step"]) == int(n > 1000)
               and c.bits(float(row["target_time_s"])) == c.bits(target_time), "Full actual plan clock/Step/dt/target differs")
        forced = int(row["forced_final"])
        c.need(forced in (0, 1), "Nonboolean forced final")
        if not i:
            c.need(n == 0 and forced == 0, "Original initial plan differs")
        elif clock[n] >= target_time:
            c.need(clock[n - 1] < target_time and forced == 0, "Not the first actual output target crossing")
        else:
            c.need(i == PROFILE["frames"] - 1 and n == PROFILE["steps"] and forced == 1,
                   "Unscheduled save is not the declared terminal-only full record")
        previous = n
        target_time = runmod.planmod.next_time(clock[n], runmod.planmod.SEGMENTS)
    c.need(previous == PROFILE["steps"] and int(rows[103]["completed_steps"]) == 1000
           and int(rows[104]["completed_steps"]) == 1001
           and sum(int(r["post_open_by_completed_step"]) for r in rows) == PROFILE["post"],
           "Exact full endpoint/event/post-open coverage differs")
    return dict(tag=JOB, mode="full2tv", window="full2tv", native_profile="full2tv10us", configuration="Release",
                scheme="B", backend="GPU", run_receipt=re, source_build=be, prepared=pe,
                source_root=c.read(pe["path"])["source_root"], run=run, output_directory=str(out), data=run["data"],
                run_out=c.stat(out / "Run.out"), plan=run["plan"], dt=DT, drain_step=1000,
                profile=dict(PROFILE), clock=clock, rows=rows,
                native_output=str(T / "outputs" / (JOB + "_native_full10us_r1")))


def completion(done):
    c.need(done.get("passed") is True and done.get("stage") == readerbuild.TAG
           and done.get("backend") == "GPU_M0_full10us_private" and done.get("window") == "full2tv10us"
           and done["samples"] == 1653 and done["planned_completed_steps"] == 7288262
           and done["total_native_count"] == 1040 and done["native_total_arrays"] == 22
           and done["native_count"] == 1000 and done["fixed_count"] == 40
           and c.bits(done["dt_s"]) == c.bits(DT) and c.bits(done["actual_end_s"]) == c.bits(PROFILE["end"])
           and done["noninitial_signed_dterror_intervals"] == 1652
           and done["post_open_completed_step_threshold"] == 1000 and done["event_part"] == 103
           and done["event_true_receiver_checks"] == 10 and done["event_true_receiver_max_abs_pressure_Pa"] > 0
           and done["first_post_open_part"] == 104 and done["post_open_frames"] == 1549
           and done["post_open_drained_particle_checks"] == 15490
           and done["soil_ledger_checks"] == 1653000 and done["fixed_public_zero_marker_checks"] == 66120
           and done["all_native_J_theta_rows"] == 1719120 and done["physical_acceptance"] is False,
           "Complete genuine full10us typed22/scalar/signed/ledger/drain profile differs")


def read_native(ad, job, result):
    identity = pin_reader(ad)
    out = Path(job["native_output"])
    callpath, log = [L / (JOB + ".native_full10us_r1" + suffix) for suffix in (".call.json", ".log")]
    c.need(not out.exists() and not callpath.exists() and not log.exists(), "Existing/partial read is protected; never decode twice")
    import psutil
    ad.pin(psutil.__file__)
    science.m0.original.no_active_reader(readerbuild.PROGRAM, job["data"])
    env = os.environ.copy()
    for key in runmod.p3.ENV_KEYS:
        env.pop(key, None)
    ad.finish()
    call, _ = science.m0.b.invoke(JOB + ".native_full10us_r1",
        [str(readerbuild.PROGRAM), "--read", "GPU", job["data"], job["plan"]["path"], "full2tv10us", str(out)],
        readerbuild.BUILDROOT, env)
    done = c.read(out / "completion.json")
    completion(done)
    result.update(passed=True, reader_invocations=1, reader_identity=identity, reader_call=call,
                  native_output=str(out), completion=done, products=[c.stat(p) for p in out.iterdir() if p.is_file()],
                  consumed=ad.finish(), consumed_stats_unchanged=True)


def equal_file(ad, old, new, label):
    a, z = ad.pin(old), ad.pin(new)
    c.need(a["bytes"] == z["bytes"], "Actual file length differs: " + label)
    with Path(old).open("rb") as x, Path(new).open("rb") as y:
        while True:
            av, zv = x.read(1024 * 1024), y.read(1024 * 1024)
            c.need(av == zv, "Actual file bytes differ: " + label)
            if not av:
                break
    return dict(file=label, old=a, new=z, all_bytes_equal=True)


def window_prefix(ad, job):
    oe = ad.pin(OLD_REVIEW)
    oldreview = c.read(OLD_REVIEW)
    ref = oldreview["job"]
    c.need(oldreview.get("stage") == science.TAG + ".review" and oldreview.get("passed") is True
           and ref["tag"] == OLD_TAG and (ref["mode"], ref["scheme"], ref["configuration"])
           == ("window2s", "B", "Release") and ref["profile"]["steps"] == 199996
           and ref["profile"]["frames"] == 1263 and c.bits(ref["dt"]) == c.bits(DT), "Actual retained P3 window qualification differs")
    ad.pin(ref["run_receipt"]["path"]); c.same(ref["run_receipt"])
    c.need(ref["run_receipt"] == job["run"]["reference_run"], "Full argv and native reference point to different windows")
    oldread = ad.pin(L / (OLD_TAG + ".native_p3_r1.json"))
    decoded = c.read(oldread["path"])
    c.need(decoded.get("stage") == science.TAG + ".read" and decoded.get("passed") is True
           and decoded.get("reader_invocations") == 1 and decoded["job"]["run_receipt"] == ref["run_receipt"]
           and decoded["native_output"] == ref["native_output"], "Actual retained unique native read differs")
    ad.pin(decoded["reader_call"]["path"]); c.same(decoded["reader_call"])
    call = c.read(decoded["reader_call"]["path"])
    c.need(call["passed"] and call["actual_Popen_wait_exit"] == call["actual_Win32_exit"] == 0, "Actual retained reader exits differ")
    old, new, shared = Path(ref["native_output"]), Path(job["native_output"]), 1262
    planentry = ad.pin(ref["plan"]["path"]); c.same(ref["plan"])
    with Path(planentry["path"]).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); rows = list(reader)
        c.need(reader.fieldnames == runmod.planmod.HEADER and len(rows) == 1263, "Original window plan differs")
    for i in range(shared):
        c.need(all(c.bits(float(rows[i][key])) == c.bits(float(job["rows"][i][key])) for key in runmod.planmod.HEADER),
               "Actual shared eight-field plan record differs")
    c.need(int(rows[-1]["completed_steps"]) == 199996 and int(rows[-1]["forced_final"]) == 1
           and int(job["rows"][1262]["completed_steps"]) == 200000 and int(job["rows"][1262]["forced_final"]) == 0,
           "Old forced-final was wrongly treated as a shared full record")
    layout = {"original15.bin": ((1040, 15), 166408), "physical.bin": ((1000, 26), 208008),
              "common_j_theta.bin": ((1040, 2), 16648), "soil_n.bin": ((1000, 1), 8008), "clock.bin": (None, 28)}
    products = []
    for name, (shape, stride) in layout.items():
        a, z = ad.pin(old / name), ad.pin(new / name)
        oh = (1263, 28) if shape is None else (*shape, 1263)
        nh = (1653, 28) if shape is None else (*shape, 1653)
        headbytes = 4 * len(oh)
        c.need(a["bytes"] == headbytes + 1263 * stride and z["bytes"] == headbytes + 1653 * stride,
               "Actual declared full/window byte length differs: " + name)
        with (old / name).open("rb") as x, (new / name).open("rb") as y:
            c.need(x.read(headbytes) == struct.pack("<" + "I" * len(oh), *oh)
                   and y.read(headbytes) == struct.pack("<" + "I" * len(nh), *nh), "Original unequal headers were changed: " + name)
            for i in range(shared):
                av, zv = x.read(stride), y.read(stride)
                c.need(len(av) == len(zv) == stride and av == zv, "Actual same-step/time prefix differs: " + name + "/" + str(i))
            tail, following = x.read(stride), y.read(stride)
            c.need(len(tail) == len(following) == stride and x.read(1) == b""
                   and tail[:8] == c.bits(ref["profile"]["end"])
                   and following[:8] == c.bits(job["clock"][200000]) and tail[:8] != following[:8],
                   "Original forced-final/unshared next full payload differs: " + name)
            if name == "clock.bin":
                c.need(struct.unpack_from("<I", tail, 8)[0] == 199995
                       and struct.unpack_from("<I", following, 8)[0] == 199999, "Actual unshared saved-Step distinction differs")
        products.append(dict(file=name, old=a, new=z, old_header=list(oh), new_header=list(nh),
                             actual_shared_records=shared, all_shared_record_bytes_equal=True))
    ids = [equal_file(ad, old / name, new / name, name) for name in ("native_ids.csv", "fixed_ids.csv", "columns.csv")]
    return dict(original_review=oe, original_read=oldread, files=products, ID_and_column_exports=ids,
                actual_shared_records=shared, shared_indices=[0, 1261], old_forced_N199996_excluded=True,
                full_next_completed_N200000_not_shared=True, signed_clock_all_bytes_included=True,
                initial_record_included=True, headers_rewritten=False, interpolation=False,
                all22_raw_array_bit_proof=False, hidden_HG_history_cross_run_bit_proof=False)


def review(ad, job, result):
    identity = pin_reader(ad)
    rp = L / (JOB + ".native_full10us_r1.json")
    ad.pin(rp)
    decoded = c.read(rp)
    c.need(decoded.get("stage") == TAG + ".read" and decoded.get("passed") is True
           and decoded.get("reader_invocations") == 1 and decoded["job"]["run_receipt"] == job["run_receipt"]
           and decoded["native_output"] == job["native_output"] and decoded["reader_identity"] == identity,
           "One genuine completed new full-profile read is required")
    ad.pin(decoded["reader_call"]["path"]); c.same(decoded["reader_call"])
    call = c.read(decoded["reader_call"]["path"])
    c.need(call.get("passed") is True and call["actual_Popen_wait_exit"] == call["actual_Win32_exit"] == 0
           and Path(call["program"]["path"]).resolve() == readerbuild.PROGRAM.resolve()
           and call["arguments"] == ["--read", "GPU", job["data"], job["plan"]["path"], "full2tv10us", job["native_output"]],
           "Actual exact full reader program/argv/handle exits differ")
    for e in decoded["products"]:
        ad.pin(e["path"]); c.same(e)
    done = c.read(Path(job["native_output"]) / "completion.json")
    completion(done)
    c.need(done == decoded["completion"], "Actual native completion differs from the sealed read")
    result["HG_original_guards"] = science.m0.hg_run(job)
    result["method_intervals"] = science.intervals(ad, job)
    result["actual_retained_pressure_PTX"] = science.m0.original.ptx_evidence(ad, job)
    result["pressure_three_rounds"] = science.pressure(ad, job)
    result["window_prefix"] = window_prefix(ad, job)
    result.update(passed=True, reader_invocations=0, native_read_receipt=c.stat(rp), reader_identity=identity,
                  completion=done, all22_original_guards_not_relaxed=True, raw22_all_array_bit_proof=False,
                  cross_option_half_or_5Pa_equivalence_claimed=False, physical_theory_or_full_cycle_acceptance=False,
                  consumed=ad.finish(), consumed_stats_unchanged=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("read", "review"))
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    c.need(args.execution_authorized, "One separately root-reviewed native action is required")
    ad = Admission(args.action, args.admission)
    suffix = ".native_full10us_r1.json" if args.action == "read" else ".native_review_full10us_r1.json"
    path = L / (JOB + suffix)
    c.need(not path.exists(), "Existing complete/failed/partial native receipt is protected")
    result = dict(stage=TAG + "." + args.action, passed=False, tag=JOB, root_admission=ad.entry,
                  reader_implementation=readerbuild.TAG, solver_invocations=0, build_invocations=0,
                  reader_invocations=0, VTK_invocations=0, Git_invocations=0, SHA_scans=0,
                  queue_invocations=0, physical_acceptance=False, automatic_follow_up=False)
    try:
        job = get_job(ad)
        result["job"] = {k: v for k, v in job.items() if k not in ("run", "rows", "clock")}
        if args.action == "read":
            read_native(ad, job, result)
        else:
            review(ad, job, result)
    except Exception as exc:
        result.update(passed=False, first_error=str(exc), partials_preserved=True)
    c.write_new(path, result)
    print(c.json.dumps(dict(passed=result["passed"], receipt=str(path), first_error=result.get("first_error")), ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
