"""Read-only comparison of both completed 15-s runs with all retained 1-s frames."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import numpy as np
from formal_release_sequence import TESTS, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe


def main():
    old, new = "k5em5_hg05_1s_cpu_r1", "k5em5_hg05_15s_cpu_r1"
    target = TESTS/"logs"/(new+".prefix1s.check.json")
    assert not target.exists()
    paths = [Path(__file__), Path(probe.__file__), probe.READER,
             TESTS/"logs"/(old+".review.json"), TESTS/"logs"/(old+".status.json"),
             TESTS/"logs"/(new+".status.json")]
    accepted, before, after = map(read, paths[-3:])
    assert accepted["passed"] and accepted["visual_inspected"]
    assert after["status"] == "pair_passed_pending_physical_review"
    for record in (before, after):
        verify(record["inputs"])
        for run in record["runs"]:
            assert run["completed"] and run["owned_exited"] and run["exit_code"] == 0
    evidence = [bound(p) for p in paths]

    def compare(job):
        variant, i = job
        frames = [probe.native(TESTS/"outputs"/(tag+"_"+variant), i) for tag in (old, new)]
        a, b = frames
        assert list(a.columns) == list(b.columns)
        assert np.array_equal(a.id, np.arange(40, 1040))
        numeric = a.select_dtypes(include="number").columns
        assert a[numeric].to_numpy(dtype="<f8").tobytes() == b[numeric].to_numpy(dtype="<f8").tobytes(), f"Native prefix mismatch: {variant}, PART {i}"
        assert a.drop(columns=numeric).equals(b.drop(columns=numeric)), f"Native metadata mismatch: {variant}, PART {i}"
        return list(a.columns)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, columns in enumerate(pool.map(compare, ((v, i) for v in ("c", "h") for i in range(1001))), 1):
            if n % 200 == 0:
                print(f"Verified {n}/2002 native prefix comparisons", flush=True)
    verify(evidence)
    result = dict(passed=True, utc=utc(), same_dt_native_fields_bitwise_equal=True,
                  frames_each=1001, compared_runs=["c", "h"], native_columns=columns,
                  limitation="Saved native fields only; not an exact HG-history restart proof.", evidence=evidence)
    save(target, result)
    print(json.dumps({k:v for k,v in result.items() if k != "evidence"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
