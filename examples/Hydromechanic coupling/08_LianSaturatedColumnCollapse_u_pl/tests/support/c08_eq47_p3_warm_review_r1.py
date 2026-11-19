"""Independent 80-digit checks of a consecutive-history C08 pressure transaction."""
import csv
from decimal import Decimal, localcontext
import json
from pathlib import Path
import struct
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "c08_eq47_p3_warm_r1"


def bits(value):
    return struct.pack("<f", value)


def nearest_float32(reference, actual):
    """Use the midpoints to the adjacent stored floats, including ties-to-even."""
    center = Decimal.from_float(actual)
    value = np.float32(actual)
    lower = Decimal.from_float(float(np.nextafter(value, np.float32(-np.inf))))
    upper = Decimal.from_float(float(np.nextafter(value, np.float32(np.inf))))
    left, right = (center + lower) / 2, (center + upper) / 2
    even = struct.unpack("<I", bits(actual))[0] % 2 == 0
    return left < reference < right or (even and reference in (left, right))


def read_records(path):
    with path.open(newline="", encoding="utf-8") as source:
        yield from csv.DictReader(source)


def native_history():
    base = T / "outputs/c08_h18_storage_debug2_GPU_r1/native_r1"
    clocks = list(read_records(base / "clocks.csv"))
    assert [int(row["completed_step"]) for row in clocks] == [2000001, 2000002]
    assert float(clocks[0]["time_s"]) + float(clocks[1]["dt_s"]) == float(clocks[1]["time_s"])
    data = (base / "typed22.bin").read_bytes()
    total, arrays, count = struct.unpack_from("<3I", data)
    assert (total, arrays, count) == (6805, 22, 2)
    stride = 8 + 212 * total
    assert len(data) == 12 + count * stride
    out = []
    for i, row in enumerate(clocks):
        start = 12 + stride * i
        assert struct.unpack_from("<d", data, start)[0] == float(row["time_s"])
        ids = np.frombuffer(data, "<u4", total, start + 8)
        # Id, Pos64x3, five Float3, rho and kappa precede pressure.
        pressure = np.frombuffer(data, "<f4", total, start + 8 + total * (4 + 24 + 5 * 12 + 2 * 4))
        assert np.unique(ids).size == total
        out.append(dict(zip(ids.tolist(), pressure.tolist())))
    return clocks, out


def main():
    out = T / "outputs" / TAG
    assert json.loads((T / "logs" / (TAG + ".run.json")).read_text())["passed"]
    clocks, (prev, current) = native_history()
    final = {}
    metrics = {}
    with localcontext() as arithmetic:
        arithmetic.prec = 80
        D = Decimal.from_float
        dt = D(float(clocks[1]["dt_s"]))
        seen = set()
        guess = {}
        for row in read_records(out / "rows.csv"):
            beta, j, i = float(row["beta"]), int(row["round"]), int(row["id"])
            key = (beta, j, i)
            assert key not in seen and beta in (0, .04) and 0 <= j <= 2 and 2060 <= i < 7060
            seen.add(key)
            pn, previous, alpha, q, diag, residual, next_q = (
                float(row[name]) for name in ("pn", "previous", "p_alpha", "q", "S", "R", "next"))
            assert bits(pn) == bits(current[i]) and bits(previous) == bits(prev[i])
            predicted = (3 * D(pn) - D(previous)) / 2
            assert D(alpha) == predicted
            expected_q = float(predicted) if j == 0 else guess[beta, i]
            assert bits(q) == bits(expected_q) and diag > 0.
            c = D(beta) / dt if pn < 0 else Decimal(0)
            result = (D(diag)*D(q) + D(residual) + c*predicted) / (D(diag) + c)
            assert nearest_float32(result, next_q), (key, result, next_q)
            guess[beta, i] = next_q
            k = (beta, j)
            counts = metrics.setdefault(k, [0, 0, 0, 0])
            counts[0] += int(pn < 0)
            counts[1] += int(q < 0)
            counts[2] += int((pn < 0) != (q < 0))
            counts[3] += int((q < 0) != (next_q < 0))
        assert len(seen) == 30000
        for row in read_records(out / "endpoints.csv"):
            beta, i, fs = float(row["beta"]), int(row["id"]), int(row["fs"])
            third, projected, rotated = (float(row[k]) for k in ("third", "projected", "rotated_previous"))
            assert (beta, i) not in final and bits(rotated) == bits(current[i])
            assert bits(third) == bits(guess[beta, i])
            assert bits(projected) == bits(0. if fs in (2,3) and third > 0. else third)
            final[beta, i] = projected
        assert len(final) == 10000
    ids = range(2060, 7060)
    delta = np.array([final[.04, i] - final[0., i] for i in ids])
    neg = np.array([current[i] < 0 for i in ids])
    def stats(values):
        return dict(ids=len(values), rms_Pa=float(np.sqrt(np.mean(values**2))),
                    max_abs_Pa=float(abs(values).max())) if len(values) else dict(ids=0)
    result = dict(passed=True, source_completed_steps=[int(r["completed_step"]) for r in clocks],
                  source_times_s=[float(r["time_s"]) for r in clocks], actual_CPU_force_calls=6,
                  spatial_geometry_frozen=True, physical_updates=0, assembled_rows=30000,
                  original_beta0_endpoint_bit_checks=15000, independent_decimal80_row_bit_checks=30000,
                  boundary_and_history_checks=10000, fixture_late_failures_preserved_both_histories=2,
                  source_negative_ids=int(neg.sum()), trigger_rule="native p_n < 0, fixed through all three rounds",
                  rounds=[dict(beta=k[0], round=k[1], source_negative=v[0], input_iterate_negative=v[1],
                               trigger_diff_if_using_iterate=v[2], input_to_output_sign_switches=v[3])
                          for k, v in metrics.items()],
                  beta04_minus_beta0_after_projection=dict(all=stats(delta), pn_negative=stats(delta[neg]),
                                                           pn_nonnegative=stats(delta[~neg])),
                  source_negative_history=False if not neg.any() else True, physical_acceptance=False)
    destination = T / "logs" / (TAG + ".check.json")
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
