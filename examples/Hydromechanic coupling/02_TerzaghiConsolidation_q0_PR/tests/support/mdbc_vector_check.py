"""Strict offline vector-boundary regression against the frozen scalar refactor.

Reuses mdbc_refactor_check without changing its module globals or files.
Reference production source/VS objects resolve through mdbc_scalar_base;
immutable test harness objects retain strict live-hash verification. There is
no missing-object waiver, drained exception, or prefix comparison.
This checker launches no solver and never overwrites a retained receipt.
"""
import argparse
import json
from pathlib import Path
import sys
from types import FunctionType

sys.dont_write_bytecode = True
import mdbc_refactor_check as strict

base = strict.base
TESTS = strict.TESTS
REFERENCES = ("mdbc_scalar_015_c", "mdbc_scalar_015_h", "mdbc_scalar_off01")
SOURCE = TESTS.parents[3] / "src/source"
INTERMEDIATE = SOURCE.parent / "VS/Intermediate"


class Evidence(strict.Evidence):
    def __init__(self):
        self.freeze_path = TESTS / "logs/mdbc_scalar_base.snapshot.json"
        self.freeze = base.load(self.freeze_path)
        base.require(self.freeze["status"] == "frozen_before_boundary_refactoring"
                     and self.freeze["source_and_copy_hashes_verified"],
                     "Unverified scalar-refactor snapshot")
        self.root = Path(self.freeze["snapshot"]).resolve()
        base.require(self.root == (TESTS / "outputs/mdbc_scalar_base").resolve(),
                     "Unexpected scalar-refactor snapshot location")
        self.archived = {str(Path(e["path"]).resolve()).lower(): e for e in self.freeze["entries"]}
        base.require(len(self.archived) == self.freeze["files"] == len(self.freeze["entries"]),
                     "Duplicate/incomplete scalar-refactor snapshot entries")
        self.checked, self.mapped = set(), []
        self.reference = False

    def verify(self, item, historical=False, build_driver=False):
        path = Path(item["path"]).resolve()
        if self.reference and (SOURCE.resolve() in path.parents
                               or (INTERMEDIATE.resolve() in path.parents and path.suffix.lower() == ".obj")):
            base.require(str(path).lower() in self.archived,
                         f"Reference source/object missing from scalar snapshot (no live fallback): {path}")
        # Inherited verification checks the expected hash, frozen file size,
        # root containment and actual frozen bytes; candidate files remain live.
        super().verify(item, historical=historical, build_driver=build_driver)


def bound(function):
    scope = dict(function.__globals__, Evidence=Evidence, REFERENCES=REFERENCES)
    return FunctionType(function.__code__, scope, function.__name__, function.__defaults__, function.__closure__)


review = bound(strict.review)
smoke = bound(strict.smoke)


def self_test():
    strict.self_test()  # Physical/drained/HG strict-bit rejection cases, no files.
    base.require(strict.Evidence is not Evidence and strict.REFERENCES != REFERENCES,
                 "Frozen checker globals were changed")
    base.require(review.__globals__["Evidence"] is Evidence and smoke.__globals__["Evidence"] is Evidence
                 and review.__globals__["REFERENCES"] == REFERENCES,
                 "Private review/smoke bindings are wrong")
    probe = Evidence.__new__(Evidence)
    probe.reference, probe.archived, probe.checked = True, {}, set()
    rejected = 0
    for path in (SOURCE / "JSphCpu.cpp", INTERMEDIATE / "DualSPHysics_ReleaseCPU_x64/JSphCpu.obj"):
        try:
            probe.verify(dict(path=str(path), sha256="0"*64))
        except ValueError as error:
            base.require("no live fallback" in str(error), "Wrong snapshot rejection")
            rejected += 1
    base.require(rejected == 2, "Missing source/object snapshot was accepted")
    try:
        review("unused_candidate", strict.REFERENCES[0])
    except ValueError as error:
        base.require("not an admitted" in str(error), "Wrong reference rejection")
    else:
        raise ValueError("Old pre-scalar reference was accepted")
    print(json.dumps(dict(vector_self_test_passed=True, missing_snapshot_rejections=rejected,
                          old_module_globals_unchanged=True, files_written=False, solver_launched=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=base.label)
    parser.add_argument("--reference", choices=REFERENCES)
    parser.add_argument("--tag", type=base.label)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        base.require(not any((args.candidate, args.reference, args.tag, args.smoke)), "Self-test takes no run arguments")
        self_test()
        return 0
    base.require(args.candidate and args.tag and (not args.reference if args.smoke else args.reference),
                 "Provide candidate/tag and reference for regression; omit reference for --smoke")
    target = TESTS / ("logs/" + args.tag + (".smoke.check.json" if args.smoke else ".check.json"))
    base.require(not target.exists(), "Refusing to overwrite review")
    result = dict(status="mdbc_vector_production_regression", passed=False, candidate=args.candidate,
                  reference=args.reference, prefix=False, reasons=[], physical_accuracy_accepted=False,
                  full_cycle_admitted=False, performance_measured=False, half_step_test=False,
                  checker=base.entry(__file__), scalar_checker=base.entry(strict.__file__),
                  retained_checker=base.entry(base.__file__))
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
