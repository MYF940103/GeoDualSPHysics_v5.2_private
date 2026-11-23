"""Exercise the C08 CUDA endpoint using recorded physical rows and an independent CPU reference."""
import argparse
import ctypes
import json
from pathlib import Path

import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
ROW = np.dtype([(s, "f8") for s in ("S", "compression", "darcy", "chain", "beta", "dt")]
               + [(s, "f4") for s in ("pn", "prev", "q")] + [("drained", "i4")], align=True)
RESULT = np.dtype([("R", "f8"), ("next", "f4"), ("valid", "i4")], align=True)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal_float(actual, expected):
    return np.array_equal(actual.view("u4"), np.asarray(expected, dtype="f4").view("u4"))


def replay(dll):
    library = ctypes.CDLL(str(dll.resolve()))
    run = library.C08PressureRows
    run.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
    run.restype = ctypes.c_int

    def evaluate(rows):
        out = np.empty(len(rows), RESULT)
        code = run(len(rows), rows.ctypes.data, out.ctypes.data)
        require(code == 0, f"CUDA error {code}")
        return out

    records = {}
    pre = pd.read_csv(TESTS / "outputs/c08_pre_m0_r1/rows.csv", float_precision="round_trip")
    require(sorted(pre.id) == list(range(2060, 7060)), "Incomplete preload material IDs")
    rows = np.zeros(len(pre), ROW)
    rows["S"], rows["compression"], rows["darcy"], rows["chain"] = pre.S_LP, pre.compression, pre.Darcy, pre.gradk
    rows["q"] = rows["prev"] = rows["pn"] = pre.p_Pa
    rows["dt"] = 5e-6
    out = evaluate(rows)
    require(out["valid"].all() and np.array_equal(out["R"], pre.Rgamma), "PRE residual differs")
    require(equal_float(out["next"], pre.p_Pa + pre.Rgamma / pre.S_LP), "PRE pressure differs")
    records["pre_source_rows"] = len(rows)

    # Decompose independently recorded finite-Kw rate terms into gamma-scaled
    # contributions. Their expanded sum can differ from the unexpanded double
    # operator by roundoff; the validated check here is the final float write.
    release = pd.read_csv(TESTS / "outputs/c08_tpi_state_r1/soil.csv", float_precision="round_trip")
    baseline = release[release.leg == "baseline"]
    for part, frame in baseline.groupby("part"):
        require(sorted(frame.native_id) == list(range(2060, 7060)), "Incomplete released material IDs")
        rows = np.zeros(len(frame), ROW)
        scale = (1000. * 9.80665 / 1.e9) * frame.n
        rows["S"] = frame.S_LP_1_per_m_s
        rows["compression"] = -1000. * 9.80665 * frame.theta_s_1
        rows["darcy"] = scale * (frame.LP_Pa_s + frame.Taylor_pressure_Pa_s + frame.Da_Pa_s + frame.FS_Ace_Lx_Pa_s)
        rows["chain"] = scale * (frame.chain_pressure_Pa_s + frame.chain_Ace_Pa_s)
        rows["dt"] = 5e-6
        rows["pn"] = rows["prev"] = rows["q"] = frame.p_actual_Pa
        out = evaluate(rows)
        require(out["valid"].all() and equal_float(out["next"], frame.p_conditional_raw_Pa),
                "Released beta-zero float write differs from physical CPU row")
        rows["chain"] = 0.
        omitted = evaluate(rows)
        delta = omitted["next"].astype(float) - out["next"]
        records[f"part{part}_gradient"] = dict(materials=len(frame), changed=int(np.count_nonzero(delta)),
                                              rms_Pa=float(np.mean(delta**2)**.5), max_Pa=float(np.max(abs(delta))))

    data = pd.read_csv(TESTS / "outputs/c08_eq47_p3_warm_r1/rows.csv", float_precision="round_trip")
    require(len(data) == 30000 and set(data.beta) == {0., .04}, "Expected two 3-round trajectories")
    for key, frame in data.groupby(["beta", "round"]):
        require(sorted(frame.id) == list(range(2060, 7060)), f"Missing round material ID at {key}")
    rows = np.zeros(len(data), ROW)
    rows["dt"], rows["S"], rows["darcy"], rows["beta"] = 5e-6, data.S, data.R, data.beta
    rows["pn"], rows["prev"], rows["q"] = data.pn, data.previous, data.q
    out = evaluate(rows)
    require(out["valid"].all() and equal_float(out["next"], data.next), "Three-round pressure differs")
    records["recorded_cpu_rows_bit_exact"] = len(data)
    records["active_negative_beta_rows"] = int(((data.pn < 0) & (data.beta > 0)).sum())

    # Deliberately give a negative source, but a positive iterate. Dirichlet
    # wins over Eq.47; an invalid physical diagonal must reject even for beta>0.
    rows = np.zeros(6, ROW)
    rows["S"], rows["dt"], rows["beta"], rows["darcy"] = 2., 5e-6, .04, 4.
    rows["pn"], rows["prev"], rows["q"] = -2., -1., 4.
    rows["drained"][0] = 1
    rows["S"][1] = -1.
    rows["dt"][2] = 0.
    rows["pn"][3] = 1.
    rows["beta"][4] = -1.
    out = evaluate(rows)
    require(out["valid"].tolist() == [1, 0, 0, 1, 0, 1] and out["next"][0] == 0
            and out["next"][3] == 6. and out["next"][5] < 0., "Boundary or gate fixture failed")
    records["boundary_and_invalid_rows"] = len(rows)
    records["scope"] = "Device endpoint on supplied physical rows; no GPU neighbour assembly or integrated dynamics"
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = json.dumps(replay(args.library), indent=2, allow_nan=False)
    with args.receipt.open("x", encoding="utf8") as output:
        output.write(result + "\n")
    print(result)
