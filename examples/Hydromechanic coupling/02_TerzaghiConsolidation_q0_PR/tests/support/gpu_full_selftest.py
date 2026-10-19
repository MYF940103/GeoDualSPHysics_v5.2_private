"""No solver: test final-partial-frame metadata and unchanged safety logic."""
import ast
import json
import math
from unittest.mock import patch
import numpy as np
import pandas as pd
import gpu_coupled_compare as compare
import gpu_coupled_run as runner
from mdbc_gpu_vector_run import TESTS, bound


def main():
    settings = dict(dt=1e-5, steps=250, stride=100)
    def data(step):
        return pd.DataFrame(dict(id=np.arange(40, 1040), stage="full_step", step=step,
                                 time_s=step * 1e-5, rho=2100., kplastic=0.))
    with patch.object(compare.pd, "read_csv", return_value=iter([data(i) for i in (0, 100, 200, 250)])):
        valid = list(compare.frames("unused", settings))
        assert len(valid) == 1 + math.ceil(settings["steps"] / settings["stride"]) == 4
        assert valid[-1].step.iloc[0] == 250
    rejected = False
    try:
        with patch.object(compare.pd, "read_csv", return_value=iter([data(i) for i in (0, 100, 200, 300)])):
            list(compare.frames("unused", settings))
    except AssertionError:
        rejected = True
    assert rejected
    old = TESTS / "outputs/gpu_spr_15_verified/support/gpu_coupled_run.py"
    new = TESTS / "support/gpu_coupled_run.py"
    def safety(path):
        tree = ast.parse(path.read_text(encoding="utf8"))
        return ast.dump(next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Safety"))
    assert safety(old) == safety(new)
    result = dict(passed=True, partial_final_frame=True, overshooting_frame_rejected=True,
                  original_safety_class_ast_identical=True, solver_started=False,
                  evidence=[bound(p) for p in (old, new, TESTS / "support/gpu_coupled_compare.py", __file__)])
    with (TESTS / "logs/gpu_full_selftest_r1.check.json").open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
