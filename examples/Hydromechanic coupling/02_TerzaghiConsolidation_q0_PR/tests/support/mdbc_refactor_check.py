"""Strict offline production-to-production mDBC naming-refactor regression.

Uses retained metadata/native/trajectory checks, but never inherits a drained
display exception, missing-object waiver, prefix comparison, or half-step claim.
Only the reference may resolve frozen source/object evidence through mdbc_base.
No solver is launched and retained records are never overwritten.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import hg_release_check as base

TESTS = base.TESTS
REFERENCES = ("hg_release_sequence_r1_spr015_c", "hg_release_sequence_r1_spr015_h",
              "hg_release_hgoff_r1")


class Evidence:
    def __init__(self):
        self.freeze_path = TESTS / "logs/mdbc_base.snapshot.json"
        self.freeze = base.load(self.freeze_path)
        base.require(self.freeze["status"] == "frozen_before_boundary_refactoring"
                     and self.freeze["source_and_copy_hashes_verified"], "Unverified mDBC snapshot")
        self.root = Path(self.freeze["snapshot"]).resolve()
        base.require(self.root == (TESTS / "outputs/mdbc_base").resolve(), "Unexpected snapshot location")
        self.archived = {str(Path(e["path"]).resolve()).lower(): e for e in self.freeze["entries"]}
        base.require(len(self.archived) == self.freeze["files"] == len(self.freeze["entries"]),
                     "Duplicate/incomplete snapshot entries")
        self.checked, self.mapped = set(), []
        self.reference = False

    def verify(self, item, historical=False, build_driver=False):
        base.require(not historical, "Both runs must use production metadata checks")
        path, wanted = Path(item["path"]), item["sha256"].lower()
        key = str(path.resolve()).lower()
        identity = (self.reference, key, wanted)
        if identity in self.checked:
            return
        saved = self.archived.get(key) if self.reference else None
        if saved is not None:
            base.require(saved["sha256"].lower() == wanted, f"Reference differs from mdbc_base: {path}")
            frozen = (self.root / saved["relative"]).resolve()
            base.require(self.root in frozen.parents and frozen.is_file()
                         and frozen.stat().st_size == saved["bytes"] and base.sha(frozen) == wanted,
                         f"Changed/missing snapshot copy: {frozen}")
            self.mapped.append(dict(original=str(path), copy=str(frozen), sha256=wanted))
        else:
            base.require(path.is_file() and base.sha(path) == wanted,
                         f"Hash mismatch or missing evidence (no waiver): {path}")
        self.checked.add(identity)


def strict_bits(comparison, hg_active):
    expected = set(base.PHYSICAL + base.DIAGNOSTIC + ["drained"])
    fields = comparison["fields_bit_equal"]
    return bool(comparison["passed"] and comparison["actual_times_bit_equal"]
                and comparison["initial_binary_equal"] and comparison["final_binary_equal"]
                and set(fields) == expected and all(fields.values())
                and not comparison["diagnostic_exceptions"]
                and not comparison["unexpected_field_difference"]
                and not comparison["first_mismatches"]
                and (comparison["hg_sample_csv_byte_equal"] is True
                     and comparison["final_hg_history_rate_csv_byte_equal"] is True if hg_active
                     else comparison["hg_disabled_zero_state_verified"] is True))


def production_summary(meta):
    # Wall-clock timing may differ; every other completion/cache/HG value must agree.
    complete = dict(meta["complete"])
    complete.pop("elapsed_seconds")
    return dict(completion=complete,
                release=base.load(meta["out"] / "release_integration.json"),
                hourglass=base.load(meta["out"] / "hourglass_complete.json"))


def hash_receipt(evidence):
    return dict(snapshot=base.entry(evidence.freeze_path),
                processed_entries=len(evidence.checked), verified_entries=len(evidence.checked),
                mapped_snapshot_entries=evidence.mapped, historical_object_unavailable=[],
                historical_build_driver_unavailable=[], missing_evidence_permitted=False)


def review(candidate_name, reference_name):
    base.require(reference_name in REFERENCES, "Reference is not an admitted frozen production run")
    base.require(candidate_name != reference_name, "Candidate must be a fresh independent run")
    evidence = Evidence()
    candidate = base.metadata(candidate_name, evidence, historical=False)
    evidence.reference = True
    reference = base.metadata(reference_name, evidence, historical=False)
    base.require(candidate["receipt"]["configuration"] == reference["receipt"]["configuration"] == "ReleaseCPU",
                 "This gate compares ReleaseCPU against ReleaseCPU")
    # compare() checks identical XML physics, dt, stride, mode, actual sample times,
    # native IDs and all fields. No prefix, relaxed tolerance or exception is admitted.
    raw = base.compare(candidate, reference, prefix=False)
    summaries_equal = production_summary(candidate) == production_summary(reference)
    comparison = dict(raw)
    comparison["passed"] = strict_bits(raw, candidate["hg_active"]) and summaries_equal
    comparison["diagnostic_exceptions_permitted"] = False
    comparison["exception_reason"] = "None: both sides are production; drained must also be bit-identical."
    comparison["completion_cache_hg_summary_equal_excluding_wall_time"] = summaries_equal
    return dict(passed=comparison["passed"], candidate_evidence=candidate["receipt"],
                reference_evidence=reference["receipt"], comparison=comparison, raw_comparison=raw,
                hash_evidence=hash_receipt(evidence))


def smoke(name):
    import hg_release_sequence as sequence
    import hg_merge_sequence as sampled_guard
    evidence = Evidence()
    meta = base.metadata(name, evidence, historical=False)
    run = meta["run"]
    base.require(meta["receipt"]["configuration"] == "DebugCPU" and meta["mode"] == 3
                 and meta["event"] and run["steps"] == 3000 and run["dt"] == 1e-5
                 and run["stride"] == 100 and meta["hg_active"],
                 "Smoke requires the planned fresh DebugCPU 0.03-s SPR/event/HG case")
    base.native(meta, "initial")
    base.native(meta, "final")
    count = sum(1 for _ in base.frames(meta))
    sampled = {}
    samples = sampled_guard.Samples(name, run["dt"], run["steps"], run["stride"], sampled)
    samples.poll()
    samples.finish()
    sequence.completion_guard(run, run["steps"], run["dt"])
    base.require(count == sampled["checked_full_step_frames"] == 31, "Incomplete smoke sampling")
    info = base.load(meta["out"] / "release_integration.json")
    base.require(info["rate_logical_calls"] == 6000 and info["rate_calculations"] == 3001
                 and info["rate_cache_hits"] == 2999, "Smoke cache-call regression")
    return dict(passed=True, status="debug_smoke_passed_not_physical_acceptance", name=name,
                evidence=meta["receipt"], native_initial_final_ids_and_binary_csv_verified=True,
                sampled_safety=sampled, cache=info, hash_evidence=hash_receipt(evidence),
                post_0_1s_stress_load_drainage_guards_exercised=False,
                cross_configuration_bitwise_comparison=False,
                safety_scripts=[base.entry(module.__file__) for module in
                                (sequence, sampled_guard, sequence.gate,
                                 sys.modules[sampled_guard.read_new.__module__])],
                sampled_limits=sampled_guard.LIMITS)


def self_test():
    import hg_merge_sequence as sampled_guard
    base.require(sampled_guard.Samples.__module__ == sampled_guard.__name__
                 and isinstance(sampled_guard.LIMITS, dict), "Smoke safety-module binding failed")
    good = dict(passed=True, actual_times_bit_equal=True, initial_binary_equal=True, final_binary_equal=True,
                fields_bit_equal={key: True for key in base.PHYSICAL + base.DIAGNOSTIC + ["drained"]},
                diagnostic_exceptions=[], unexpected_field_difference=False, first_mismatches=[],
                hg_sample_csv_byte_equal=True, final_hg_history_rate_csv_byte_equal=True,
                hg_disabled_zero_state_verified=False)
    base.require(strict_bits(good, True), "HG strict self-test failed")
    bad = []
    value = copy.deepcopy(good); value["fields_bit_equal"]["drained"] = False; bad.append(value)
    value = copy.deepcopy(good); value["diagnostic_exceptions"] = [dict(field="drained")]; bad.append(value)
    value = copy.deepcopy(good); value["final_binary_equal"] = None; bad.append(value)
    value = copy.deepcopy(good); value["final_hg_history_rate_csv_byte_equal"] = False; bad.append(value)
    value = copy.deepcopy(good); del value["fields_bit_equal"]["pressure"]; bad.append(value)
    value = copy.deepcopy(good); value["fields_bit_equal"]["rho"] = False; bad.append(value)
    base.require(all(not strict_bits(item, True) for item in bad), "Strict rejection self-test failed")
    off = copy.deepcopy(good)
    off.update(hg_sample_csv_byte_equal=None, final_hg_history_rate_csv_byte_equal=None,
               hg_disabled_zero_state_verified=True)
    base.require(strict_bits(off, False), "Disabled-HG self-test failed")
    print(json.dumps(dict(self_test_passed=True, negative_cases=len(bad), solver_launched=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=base.label)
    parser.add_argument("--reference", choices=REFERENCES)
    parser.add_argument("--tag", type=base.label)
    parser.add_argument("--smoke", action="store_true", help="Validate only the planned DebugCPU 0.03-s run")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        base.require(not any((args.candidate, args.reference, args.tag, args.smoke)), "Self-test takes no run arguments")
        self_test()
        return 0
    base.require(args.candidate and args.tag and (not args.reference if args.smoke else args.reference),
                 "Provide candidate/tag and reference for regression; omit reference for --smoke")
    suffix = ".smoke.check.json" if args.smoke else ".check.json"
    target = TESTS / ("logs/" + args.tag + suffix)
    base.require(not target.exists(), "Refusing to overwrite review")
    result = dict(status="mdbc_naming_refactor_production_regression", passed=False,
                  candidate=args.candidate, reference=args.reference, prefix=False, reasons=[],
                  physical_accuracy_accepted=False, full_cycle_admitted=False,
                  performance_measured=False, half_step_test=False,
                  checker=base.entry(__file__), retained_checker=base.entry(base.__file__))
    try:
        result.update(smoke(args.candidate) if args.smoke else review(args.candidate, args.reference))
        if not result["passed"]:
            result["reasons"].append("Nonzero-bit production difference or changed completion/cache/HG summary")
    except Exception as error:
        result["reasons"].append(f"{type(error).__name__}: {error}")
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], path=str(target), reasons=result["reasons"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
