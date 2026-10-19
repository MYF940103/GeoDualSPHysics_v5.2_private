"""Positive/negative tests for the long-run observer; no physical solver."""
import json
from pathlib import Path
import numpy as np
from gpu_coupled_run import Safety
from gpu_coupled_compare import records
from mdbc_gpu_vector_run import TESTS, bound


def main():
    receipt = TESTS / "logs/gpu_safety_r1.check.json"
    assert not receipt.exists()
    a = np.zeros((1000, 23))
    a[:, 2] = np.arange(40, 1040)
    a[:, 3] = .005 + .01 * (np.arange(1000) // 100)
    a[:, 5] = .005 + .01 * (np.arange(1000) % 100)
    a[:, 9], a[:, 10], a[:, 13], a[:, 18] = 2100, 1000, -9000, -1000 / 210
    top = np.arange(99, 1000, 100)
    a[top, 10], a[top, 13], a[top, 21] = 0, -10000, 1
    trials = dict(duplicate_id=(0, 2, 41), nonfinite=(0, 6, np.nan), density=(0, 9, 0),
                  plastic=(0, 17, .001), wall_crossing=(0, 5, -.001), lateral=(0, 3, .0056),
                  layer_span=(0, 5, .0056), stress=(0, 13, -11001), load=(0, 18, 0),
                  drainage_id=(99, 21, 0), top_pressure=(99, 10, 1))
    rejected = []
    for label, edit in trials.items():
        observer = Safety(Path("unused"));observer.observe(a.copy())
        b = a.copy();b[:, 0], b[:, 1] = .1 - 1e-14, 10000
        b[edit[0], edit[1]] = edit[2]
        try:
            observer.observe(b)
        except (AssertionError, RuntimeError):
            rejected.append(label)
    assert len(rejected) == len(trials)
    observer = Safety(Path("unused"));observer.observe(a.copy())
    b = a.copy();b[:, 0], b[:, 1] = .1 - 1e-14, 10000;observer.observe(b)
    _, _, path, evidence = records("mdbc_vector_015_c")
    actual = Safety(path);actual.poll();actual.stream.close()
    assert actual.frames == 151 and abs(actual.max_stress - 73.36486286275249) < 1e-8
    assert abs(actual.max_gap - 84.98438637645086) < 1e-8
    with receipt.open("x", encoding="utf8") as stream:
        json.dump(dict(passed=True, rejected=rejected, positive_synthetic=True,
                       retained_cpu_replay=actual.summary(), evidence=evidence,
                       sources=[bound(__file__), bound(Path(__file__).with_name("gpu_coupled_run.py"))], physical_acceptance=False), stream, indent=2)
    print(json.dumps(dict(passed=True, rejected_count=len(rejected), retained_cpu=actual.summary()), indent=2))


if __name__ == "__main__":
    main()
