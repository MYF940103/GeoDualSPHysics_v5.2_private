"""Offline saved-history arithmetic review; no solver, reader, build, import of project tools or SHA."""
import argparse
import csv
import json
import struct
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_x0_history_review_r1"
RUN = "upl_tpi_x0_short_r2_on"
OUT = T / "outputs" / RUN
NATIVE = OUT / "native_r1"
PLAN = T / "configs/upl_tpi_x0_short_r1.clock.csv"
CHECK = T / "logs" / (TAG + ".check.json")
CSVOUT = T / "figures" / (TAG + "_summary.csv")
COUNT, SOIL, DT = 151, 1000, 5e-6
FIELDS = "part kind native_id source_time_s actual_save_time_s source_step_zero_based completed_step dt_s pn_Pa previous_Pa half_Pa guess_Pa raw_final_Pa final_Pa S_1_per_m_s Rgamma_Pa_per_m_s theta_h_for_J_1_per_s theta_endpoint_1_per_s Jn Jhalf Jfull endpoint_drained commit_drained commits endpoint_calls".split()

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def bind(entry):
    need(stat(entry["path"]) == entry, "Consumed stat changed: " + entry["path"])
    return entry

def same64(a, b):
    a, b = np.asarray(a, dtype="<f8"), np.asarray(b, dtype="<f8")
    return a.shape == b.shape and np.array_equal(a.view("<u8"), b.view("<u8"))

def same32(a, b):
    a, b = np.asarray(a, dtype="<f4"), np.asarray(b, dtype="<f4")
    return a.shape == b.shape and np.array_equal(a.view("<u4"), b.view("<u4"))

def binary(path, header, dtype):
    with path.open("rb") as f:
        need(struct.unpack("<" + "I" * len(header), f.read(4 * len(header))) == header, "Binary header differs: " + str(path))
    need(path.stat().st_size == 4 * len(header) + COUNT * dtype.itemsize, "Binary length differs: " + str(path))
    return np.memmap(path, mode="r", offset=4 * len(header), dtype=dtype, shape=(COUNT,))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    need(parser.parse_args().execution_authorized, "Separate root offline-analysis admission required")
    need(not CHECK.exists() and not CSVOUT.exists(), "Existing/partial history review protected")
    ncpath = T / "logs" / (RUN + ".native.check.json"); nc = read(ncpath)
    need(nc["passed"] and nc["consumed_stats_unchanged"] and nc["reader_invocations"] == 1, "Completed unique native review required")
    run = read(bind(nc["run"])["path"]); done = read(bind(nc["completion"])["path"])
    need(run["passed"] and run["solver_completed"] and run["private_X0_requested"] and run["configuration_phase"] == "on"
         and run["actual_exit"] == run["actual_Win32_exit"] == 0 and Path(run["output"]).resolve() == OUT.resolve(), "Owned ReleaseON completion required")
    need(done["passed"] and done["stage"] == "upl_tpi_x0_short_r1_native" and done["backend"] == "CPU_public"
         and done["samples"] == COUNT and done["planned_completed_steps"] == 30000 and done["native_total_arrays"] == 22
         and done["total_native_count"] == 1040 and done["post_open_frames"] == 141 and done["post_open_drained_particle_checks"] == 1410,
         "Closed native 151/1040/22/30000/drain qualification differs")
    files = {Path(e["path"]).name: e for e in nc["files"]}
    used = [stat(Path(__file__)),stat(T/"notes/upl_tpi_x0_history_review_r1.md"),stat(T/"logs"/(RUN+".root_admission.json")),stat(ncpath), bind(nc["run"]), bind(nc["completion"])]
    for leaf in ("physical.bin", "clock.bin", "native_ids.csv"):
        need(Path(files[leaf]["path"]).resolve() == (NATIVE / leaf).resolve(), "Native file path differs")
        used.append(bind(files[leaf]))
    matches = [e for e in nc["consumed"] if Path(e["path"]).resolve() == PLAN.resolve()]
    need(len(matches) == 1, "Actual native review must bind the closed clock plan"); used.append(bind(matches[0]))
    side, summarypath = OUT / "C02TpiX0.csv", OUT / "C02TpiX0.summary.json"
    # These derived files are first sealed here, not asserted historically bound by the solver receipt.
    used += [stat(side), stat(summarypath)]; summary = read(summarypath)
    need(summary["completed"] and summary["stage"] == "c08_tpi_x0_r2" and summary["alpha"] == .5 and summary["beta"] == 0
         and summary["dt_s"] == DT and summary["native_save_events"] == COUNT and summary["sidecar_native_ids_per_save"] == SOIL,
         "X0 completed closed summary differs")
    for key in ("commits", "pre_calls", "corr_calls", "J_corrector_captures", "endpoint_calls"):
        need(summary[key] == 30000, "X0 complete internal counter differs: " + key)
    need(summary["finite_Kw_pressure_update_skipped"] and summary["J_solid_update_unchanged"]
         and summary["endpoint_source_clock_is_original_n"] and summary["endpoint_theta_is_not_J_integration_theta"]
         and summary["history_cold_start"] and not summary["full_restart_supported"] and not summary["paper_literal_LF"]
         and not summary["true_implicit_solution"] and not summary["physical_acceptance"], "X0 scope/commit declarations differ")
    q = binary(NATIVE / "physical.bin", (SOIL, 26, COUNT), np.dtype([("t", "<f8"), ("q", "<f8", (SOIL, 26))]))
    clock = binary(NATIVE / "clock.bin", (COUNT, 28), np.dtype([("t", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("signed", "<f8")]))
    need(same64(q["t"], clock["t"]) and np.all(clock["dt"] == DT) and np.all(clock["signed"][1:] <= 1e-14)
         and np.all(clock["signed"][1:] != -np.finfo("f8").max), "Actual binary clock/signed intervals differ")
    with (NATIVE / "native_ids.csv").open(encoding="utf-8-sig", newline="") as f:
        ids = list(csv.DictReader(f))
    need(len(ids) == SOIL and [int(r["row"]) for r in ids] == list(range(SOIL))
         and [int(r["id"]) for r in ids] == list(range(40, 1040)), "Native material ID ordering differs")
    with PLAN.open(encoding="utf-8-sig", newline="") as f:
        plan = list(csv.DictReader(f))
    need(len(plan) == COUNT, "Closed plan coverage differs")
    wanted = {int(r["completed_steps"]) for r in plan}; sources = {0: 0.}; ends = {0: 0.}; time = 0.
    for completed in range(1, 30001):
        source = time; time += DT
        if completed in wanted:
            sources[completed], ends[completed] = source, time
    need(len(sources) == COUNT and same64(time, summary["actual_end_s"]) and same64(time, done["actual_end_s"]), "Actual scalar end differs")
    with side.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); need(reader.fieldnames == FIELDS, "Exactly the original25 sidecar columns required")
        result, rows = [], 0
        for part, planned in enumerate(plan):
            block = []
            for j in range(SOIL):
                row = next(reader, None); need(row is not None, "Incomplete 151000-row sidecar")
                need(int(row["part"]) == part and int(row["native_id"]) == 40+j, "Sidecar material row order/ID differs")
                block.append(row); rows += 1
            initial = part == 0; completed = int(planned["completed_steps"]); saved = int(planned["saved_step"])
            need(int(planned["part"]) == part and saved == int(clock["step"][part])
                 and same64(float(planned["time_s"]), clock["t"][part]) and same64(ends[completed], clock["t"][part]), "Native/closed scalar plan differs")
            values = {key: np.array([float(r[key]) for r in block]) for key in FIELDS if key not in ("kind", "S_1_per_m_s", "Rgamma_Pa_per_m_s")}
            need(all(r["kind"] == ("initial" if initial else "committed") for r in block)
                 and np.all(values["source_step_zero_based"] == (0 if initial else completed-1))
                 and np.all(values["completed_step"] == completed) and np.all(values["commits"] == completed)
                 and np.all(values["endpoint_calls"] == completed) and np.all(values["dt_s"] == (0. if initial else DT)), "Sidecar saved step/counter/phase differs")
            need(same64(values["actual_save_time_s"], np.full(SOIL, clock["t"][part]))
                 and same64(values["source_time_s"], np.full(SOIL, sources[completed])), "Sidecar source/save scalar clocks differ")
            if not initial:
                need(same64(values["source_time_s"] + DT, values["actual_save_time_s"]), "sourceTime+dt is not actual save time")
            need(all(np.all(np.isfinite(v)) for v in values.values()), "Nonfinite sidecar value")
            for key in ("pn_Pa", "previous_Pa", "half_Pa", "guess_Pa", "raw_final_Pa", "final_Pa"):
                need(same64(values[key], values[key].astype("<f4").astype("<f8")), "Sidecar pressure is not an exact original float32: " + key)
            need(all(np.all(values[key] > 1.-float(np.float32(.3))) for key in ("Jn", "Jhalf", "Jfull")), "Original saturated-J domain differs")
            need(same64(values["final_Pa"], q["q"][part, :, 6]) and same64(values["Jfull"], q["q"][part, :, 8])
                 and same64(values["theta_endpoint_1_per_s"], q["q"][part, :, 9]), "Actual native final pressure/J/endpoint theta differs")
            post = completed > 2000; fs = np.isin(q["q"][part, :, 17], (2., 3.)); drain = fs & post
            need(np.array_equal(values["endpoint_drained"], drain.astype(float)) and np.array_equal(values["commit_drained"], drain.astype(float)), "True saved FS2/3/source-clock drainage differs")
            if initial:
                need(all(r["S_1_per_m_s"] == "" and r["Rgamma_Pa_per_m_s"] == "" for r in block), "Initial S/R must be blank, not fabricated zero")
                need(all(np.all(values[k] == 0.) for k in ("pn_Pa", "previous_Pa", "half_Pa", "guess_Pa", "raw_final_Pa", "final_Pa")), "Cold initial pressure history differs")
                result.append(dict(part=part, time_s=0., completed_step=0, rows=SOIL, unconstrained_S_min=None, J_reconcile_error_max=0., J_reconcile_budget_ratio_max=0.)); continue
            S = np.array([float(r["S_1_per_m_s"]) for r in block]); R = np.array([float(r["Rgamma_Pa_per_m_s"]) for r in block])
            need(np.all(np.isfinite(S)) and np.all(np.isfinite(R)) and np.all(S[~drain] > 0.)
                 and np.all(S[drain] == 0.) and np.all(R[drain] == 0.), "Original positive-S/finite/Dirichlet row gate differs")
            history = (values["pn_Pa"] + .5*(values["pn_Pa"]-values["previous_Pa"])).astype("<f4")
            guess = np.where(drain, np.float32(0.), history)
            need(same32(values["guess_Pa"], guess) and same32(values["half_Pa"], guess), "Saved history half/guess float arithmetic or drainage priority differs")
            raw = np.zeros(SOIL, dtype="<f4"); raw[~drain] = (values["guess_Pa"][~drain]+R[~drain]/S[~drain]).astype("<f4")
            need(same32(values["raw_final_Pa"], raw) and same32(values["final_Pa"], raw), "Actual float(guess+Rgamma/S)/final drainage differs")
            term = (DT*values["Jhalf"])*values["theta_h_for_J_1_per_s"]
            expectedJ = values["Jn"] + term
            budget = 4.*np.finfo("f8").eps*(np.abs(values["Jn"])+np.abs(term))
            error = np.abs(values["Jfull"]-expectedJ)
            need(np.all(error <= budget), "Original source-ordered Jn+dt*Jhalf*theta_h arithmetic exceeds four-epsilon budget")
            result.append(dict(part=part,time_s=float(clock["t"][part]),completed_step=completed,rows=SOIL,
                unconstrained_S_min=float(S[~drain].min()),J_reconcile_error_max=float(error.max()),J_reconcile_budget_ratio_max=float(np.max(error/budget))))
        need(next(reader, None) is None and rows == 151000, "Extra/missing sidecar rows")
    for entry in used:
        bind(entry)
    with CSVOUT.open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0])); writer.writeheader(); writer.writerows(result)
    report = dict(stage=TAG,passed=True,sidecar_rows=rows,columns=25,samples=COUNT,material_IDs=SOIL,internal_commits=30000,
        external_saved_history_states=COUNT,external_all30000_step_previous_identity_proven=False,all22_native_qualification_reused=True,
        all151_pressure_J_theta_actual_native_bits_equal=True,float_row_and_history_arithmetic_checked=True,
        half_FS_membership_independently_saved=False,half_drain_check_uses_qualified_column_saved_FS_membership=True,
        completed2000_event_native_save_observed=2000 in wanted,clock_replayed_by_scalar_addition=True,
        J_arithmetic_budget="4*binary64_epsilon*(abs(Jn)+abs((dt*Jhalf)*theta_h)); no physical tolerance",
        first_sidecar_stat_seal_in_this_review=True,sidecar_summary=summary,consumed=used,consumed_stats_unchanged=True,
        output=stat(CSVOUT),solver_invocations=0,native_invocations=0,SHA_scans=0,physical_acceptance=False,full_restart_acceptance=False,
        old_finite_Kw_all0ULP_or_5Pa_equivalence_claimed=False)
    with CHECK.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(str(CHECK))

if __name__ == "__main__":
    main()
