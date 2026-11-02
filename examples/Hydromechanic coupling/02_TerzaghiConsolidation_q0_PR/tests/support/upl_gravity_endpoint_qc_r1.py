"""Offline CSV/receipt QC only; never launches a native program or reads BI4."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def entry(path):
    p = Path(path)
    return dict(path=str(p.resolve()), bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def verify(e):
    a = entry(e["path"])
    need(a["bytes"] == e["bytes"] and a["sha256"] == e["sha256"].lower(),
         "Frozen binding changed: " + e["path"])


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        out = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    need(all(math.isfinite(v) for r in out for v in r.values()), "Nonfinite CSV")
    return out


def close(a, b):
    # Offline serialization/arithmetic reproduction, NOT a physical gate change.
    need(abs(a-b) <= 512 * sys.float_info.epsilon * max(1., abs(a), abs(b)),
         f"Serialized calculation differs: {a!r} versus {b!r}")


def rms(values):
    v = list(values)
    return math.sqrt(math.fsum(x*x for x in v) / len(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--check", required=True)
    args = ap.parse_args()
    target = Path(args.check)
    need(not target.exists(), "Retained check protected")
    run = load(args.run)
    verify(run["call"])
    call = load(run["call"]["path"])
    need(run["owned_component_exit0"] and call["exit_code"] == 0 and
         call["typed_LASTEXITCODE_captured_immediately"] and
         call["owned_call_exited"] and call["invocation_failure"] is None,
         "Owned component typed exit0 required")
    verify(call["program"])
    verify(call["log"])
    verify(run["preflight"])
    pre = load(run["preflight"]["path"])
    for e in pre["bindings"] + run["files"]:
        verify(e)
    verify(pre["source_native_check"])
    source_check = load(pre["source_native_check"]["path"])
    need(source_check["passed"], "Sealed source native review required")
    verify(source_check["last_poro"])
    saved = {int(r["id"]): r for r in rows(source_check["last_poro"]["path"])}
    need(set(saved) == set(range(512)), "Source native IDs incomplete")
    out = Path(call["arguments"][-1])
    done = load(out / "completion.json")
    for k, v in dict(passed=True, stage="upl_gravity_endpoint_cpu_r1",
                     native_count=512, source_part=256, source_time_s=2.**-15,
                     source_saved_step=511, actual_endpoint_force_calls=1,
                     additional_complete_rate_calls=2, rate_rows=1536,
                     delta_rows=1024, completed_physical_steps=0,
                     Run_or_ComputeStep_called=False, PART_restart=False,
                     public_gravity_accepted=False, physical_acceptance=False,
                     input_SHA_before_after_checked_by_component=False).items():
        need(k in done and done[k] == v, "Completion differs: " + k)
    for k in ("wrong_g_both_signals_over_10_RMS_budget",
              "same_state_covered_physical_bytes_unchanged",
              "temporary_Ace_rate_cache_restored", "saved_theta_not_endpoint_theta",
              "actual_C_conditioned_reference", "q_difference_is_derived_conditional_not_native"):
        need(done.get(k) is True, "Actual component assertion absent: " + k)
    rate_rows, delta_rows, summary = [rows(out / f) for f in
                                    ("rates.csv", "delta.csv", "summary.csv")]
    need((len(rate_rows), len(delta_rows), len(summary)) == (1536, 1024, 2), "CSV counts")
    rates = {(int(r["side"]), int(r["id"])): r for r in rate_rows}
    deltas = {(int(r["sign"]), int(r["id"])): r for r in delta_rows}
    need(set(rates) == {(s, i) for s in (0, -1, 1) for i in range(512)}, "Rate IDs/sides")
    need(set(deltas) == {(s, i) for s in (-1, 1) for i in range(512)}, "Delta IDs/signs")
    need({int(r["sign"]) for r in summary} == {-1, 1}, "Summary signs")
    scale = 32 * 2.**-23 + 4096 * 2.**-52
    k0 = struct.unpack("f", struct.pack("f", .0001))[0]
    for (side, i), r in rates.items():
        budget = scale * max(1., r["raw_abs_rate"])
        error = abs(r["actual_rate"] - r["independent_rate"])
        need(r["raw_abs_rate"] >= 0 and error <= budget, "Original single-side gate")
        close(r["budget"], budget); close(r["error"], error); close(r["ratio"], error/budget)
        close(r["saved_last_stage_theta"], saved[i]["theta"])
        for key in ("endpoint_theta", "GJ_x", "GJ_y", "GJ_z"):
            close(r[key], rates[(0, i)][key])
    signs = []
    for sign in (-1, 1):
        group = [deltas[(sign, i)] for i in range(512)]
        for i, d in enumerate(group):
            b, s = rates[(0, i)], rates[(sign, i)]
            budget = b["budget"] + s["budget"]
            observed = s["actual_rate"] - b["actual_rate"]
            error = abs(observed - d["independent_delta_rate"])
            need(error <= budget, "Original combined-side gate")
            close(d["combined_budget"], budget); close(d["actual_rate_difference"], observed)
            close(d["error"], error); close(d["ratio"], error/budget)
            j, n = saved[i]["J"], saved[i]["n"]
            ki = k0 * math.exp((j-1.)/(.75 * 2.**-13))
            ideal = sign * (67108864./n) * 1000. / (1000.*9.80665) * ki / (.75*2.**-13) * (-8.*b["GJ_x"])
            close(d["ideal_GJ_dot_g_rate"], ideal)
            close(d["float_quantization_correction"],
                  d["independent_delta_rate"] - d["ideal_GJ_dot_g_rate"])
            for axis in "xyz":
                close(d["derived_conditional_delta_q"+axis],
                      -ki*1000./(1000.*9.80665) * d["actual_delta_A"+axis])
        signal = rms(d["actual_rate_difference"] for d in group)
        ideal = rms(d["ideal_GJ_dot_g_rate"] for d in group)
        budget = rms(d["combined_budget"] for d in group)
        need(signal > 10*budget and ideal > 10*budget, "Original nonempty >10 gate")
        original = next(r for r in summary if int(r["sign"]) == sign)
        computed = dict(sign=sign, actual_rate_difference_RMS=signal,
                        ideal_GJ_dot_g_rate_RMS=ideal, combined_budget_RMS=budget,
                        actual_signal_over_budget=signal/budget,
                        ideal_signal_over_budget=ideal/budget)
        for k, v in computed.items():
            close(original[k], v)
        computed["float_quantization_correction_RMS"] = rms(d["float_quantization_correction"] for d in group)
        signs.append(computed)
    single = max(r["ratio"] for r in rate_rows)
    delta = max(r["ratio"] for r in delta_rows)
    close(done["max_single_rate_error_over_original_budget"], single)
    close(done["max_delta_error_over_combined_budget"], delta)
    result = dict(passed=True, stage="upl_gravity_endpoint_cpu_offline_qc_r1",
                  analysis=entry(__file__), source_run=entry(args.run),
                  source_build=run["source_build"], helper=run["helper"],
                  preflight=run["preflight"], call=run["call"], files=run["files"],
                  completion=entry(out/"completion.json"),
                  source_last_poro=source_check["last_poro"],
                  current_binding_records_rehashed=len(pre["bindings"]),
                  original_budget="(32*FLT_EPS+4096*DBL_EPS)*max(1,raw_abs_rate)",
                  rate_rows=1536, delta_rows=1024, summary_rows=2,
                  max_single_rate_error_over_original_budget=single,
                  max_delta_error_over_combined_budget=delta, signs=signs,
                  saved_minus_endpoint_theta_RMS=rms(rates[(0,i)]["saved_last_stage_theta"]-rates[(0,i)]["endpoint_theta"] for i in range(512)),
                  source_part=256, source_time_s=2.**-15, source_saved_step=511,
                  actual_force_and_rollback_assertions_from_native_component=True,
                  C_conditioned_reference_not_independent_C_proof=True,
                  delta_q_derived_not_saved_native=True,
                  second_BI4_parser=False, new_native_program_executed=False,
                  Run_or_ComputeStep_called=False, completed_physical_steps=0,
                  public_gravity_accepted=False, physical_acceptance=False)
    target.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("passed", "rate_rows", "delta_rows", "max_single_rate_error_over_original_budget", "max_delta_error_over_combined_budget", "signs")}, indent=2))


if __name__ == "__main__":
    main()
