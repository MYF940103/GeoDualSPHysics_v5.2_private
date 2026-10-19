"""Pure-memory CSV rejection tests; never a run/hash or physical acceptance.

Loads one passed pilot's small JSON/CSV files, then invokes the actual review_run
with private in-memory readers and an explicitly mocked hash verifier. No
retained input is changed. Optional --tag writes one fresh exclusive receipt.
"""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from types import FunctionType

sys.dont_write_bytecode = True
import mdbc_vector_review as review


def entry(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def self_test(label):
    documents = {}

    def load(path):
        path = Path(path).resolve()
        documents[str(path)] = json.loads(path.read_text(encoding="utf-8-sig"))
        return documents[str(path)]

    run = load(review.TESTS / f"logs/{label}.run.json")
    load(run["build_manifest"]["path"])
    load(run["prepare_manifest"]["path"])
    output = Path(run["output"]).resolve()
    load(output / "vector_complete.json")
    originals = {}
    for name in ("vector_rows.csv", "pore_rows.csv", "consumer_rows.csv"):
        with (output / name).open(encoding="utf-8-sig", newline="") as stream:
            originals[name] = list(csv.DictReader(stream))
    bindings_before = (review.verify, review.read_json, review.csv_rows)

    def invoke(rows):
        # Only this function copy sees mocks. The real module/files stay intact.
        scope = dict(review.review_run.__globals__,
                     verify=lambda item: item,
                     read_json=lambda path: copy.deepcopy(documents[str(Path(path).resolve())]),
                     csv_rows=lambda path: copy.deepcopy(rows[Path(path).name]))
        function = FunctionType(review.review_run.__code__, scope, "review_run")
        return function(label)

    baseline = invoke(originals)
    results = []
    names = ("missing_vector_row", "duplicate_vector_key", "inactive_roi_wall",
             "inconsistent_pore_error", "self_consistent_consumer_over_limit", "nonfinite_vector")
    expected = ("Incomplete wall/component/trial rows", "Unexpected/duplicate vector key",
                "ROI wall inactive", "Pore error mismatch", "Independent preset-limit gate failed",
                "Nonfinite actual")
    for case, reason in zip(names, expected):
        rows = copy.deepcopy(originals)
        if case == names[0]:
            rows["vector_rows.csv"].pop()
        elif case == names[1]:
            rows["vector_rows.csv"][1] = copy.deepcopy(rows["vector_rows.csv"][0])
        elif case == names[2]:
            next(row for row in rows["vector_rows.csv"] if row["roi"] == "1")["active"] = "0"
        elif case == names[3]:
            row = rows["pore_rows.csv"][0]
            row["error"] = repr(float(row["error"]) + 1.0)
        elif case == names[4]:
            row = rows["consumer_rows.csv"][0]
            component = int(row["component_0to5_sigma_6_pore_7_rho"])
            group = 0 if component < 6 else component - 5
            oracle, exact = float(row["oracle"]), float(row["analytic"])
            tolerance = review.FLOORS[group] + 2e-5 * abs(oracle)
            mls = oracle + 1.01 * tolerance
            row.update(mls=repr(mls), mls_oracle_error=repr(abs(mls-oracle)),
                       analytic_error=repr(abs(mls-exact)), comparison_tolerance=repr(tolerance))
        else:
            rows["vector_rows.csv"][0]["actual"] = "nan"
        try:
            invoke(rows)
        except ValueError as error:
            review.require(reason in str(error), f"Wrong rejection for {case}: {error}")
            results.append(dict(case=case, rejected=True, reason=reason))
        else:
            raise ValueError(f"Invalid in-memory CSV accepted: {case}")
    review.require(bindings_before == (review.verify, review.read_json, review.csv_rows),
                   "Retained review module globals changed")
    return dict(status="passed_csv_logic_memory_selftest_only", passed=True, pilot=label,
                baseline_csv_row_counts=baseline["csv_rows"], positive_control_passed=True,
                negative_cases=results, hash_verification_mocked=True, run_integrity_verified=False,
                physical_accuracy_accepted=False, solver_launched=False, retained_files_modified=False,
                checker=entry(__file__), reviewed_checker=entry(review.__file__),
                loaded_pilot_files=[entry(path) for path in documents]
                  + [entry(output / name) for name in originals])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="Existing passed pilot; used only as the in-memory row baseline")
    parser.add_argument("--tag", help="Optional new logs/TAG.selftest.json; never overwritten")
    args = parser.parse_args()
    review.require(re.fullmatch(r"[A-Za-z0-9_-]+", args.label), "Unsafe pilot label")
    target = None
    if args.tag:
        review.require(re.fullmatch(r"[A-Za-z0-9_-]+", args.tag), "Unsafe selftest tag")
        target = review.TESTS / f"logs/{args.tag}.selftest.json"
        review.require(not target.exists(), "Refusing to overwrite selftest receipt")
    result = self_test(args.label)
    if target:
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], negative_cases=len(result["negative_cases"]),
                          hash_verification_mocked=True, physical_accuracy_accepted=False,
                          receipt=str(target) if target else None)))


if __name__ == "__main__":
    main()
