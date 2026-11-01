"""Offline recheck of the saved private smooth-k components, not a solver."""
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
REPORT = TESTS / "logs/upl_p3_perm_review_r1.check.json"
if REPORT.exists():
    raise RuntimeError("Retained review protected")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


bindings = {}


def verify_tree(value):
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys():
            path = Path(value["path"])
            actual = digest(path)
            assert actual["bytes"] == value["bytes"], path
            assert actual["sha256"] == value["sha256"].lower(), path
            bindings[str(path)] = actual
        for item in value.values():
            verify_tree(item)
    elif isinstance(value, list):
        for item in value:
            verify_tree(item)


def rows(path):
    bindings[str(path)] = digest(path)
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def f32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


default = TESTS / "logs/upl_p3_perm_off_r2.check.json"
assert read_json(default)["passed"]
verify_tree(read_json(default))
bindings[str(default)] = digest(default)
results = []
for config in ("DebugCPU", "ReleaseCPU"):
    check_path = TESTS / f"logs/upl_p3_perm_actual_{config}_r2.check.json"
    check = read_json(check_path)
    assert check["passed"] and not check["physical_trajectory"]
    verify_tree(check)
    build = read_json(Path(check["build"]["path"]))
    verify_tree(build)
    bindings[str(check_path)] = digest(check_path)
    base = TESTS / f"outputs/upl_p3_perm_actual_{config}_r2_on"
    rates = rows(base / "rates.csv")
    law = rows(base / "permeability.csv")
    scales = rows(base / "scales.csv")
    guards = rows(base / "guards.csv")
    periodic = rows(base / "periodic.csv")
    summary = rows(base / "summary.csv")
    assert len(rates) == len(law) == 728
    assert len(summary) == 40 and len(guards) == 10
    assert len(scales) == 2 and len(periodic) == 4
    ratios, law_relative, source_ratios, nulls, analytic_ratios = [], [], [], [], []
    for rate, item in zip(rates, law):
        for key in ("dimension", "jitter", "periodic", "field", "subcase", "native_id", "J"):
            assert rate[key] == item[key], key
        got, ref = float(rate["actual_rate_pa_s"]), float(rate["reference_rate_pa_s"])
        limit = 32 * 2**-23 * max(1, abs(ref)) + 1e-6
        assert math.isfinite(got) and abs(got-ref) <= limit
        assert abs(limit-float(rate["limit"])) <= 1e-15 * max(1, limit)
        ratios.append(abs(got-ref)/limit)
        j, ck = float(item["J"]), float(item["Ck"])
        k0 = 0 if rate["field"] == "k0_theta_sign" else f32(1e-5)
        reference_k = 0 if k0 == 0 else k0 * math.exp((j-1)/((1-f32(.3))*ck))
        k = float(item["actual_k"])
        ktol = 5e-13 * max(abs(reference_k), float.fromhex("0x1p-1022"))
        assert abs(k-reference_k) <= ktol
        if k0:
            law_relative.append(abs(k-reference_k)/abs(reference_k))
        if rate["field"] == "J1_known_k":
            assert j == 1 and k == k0
        if rate["field"] == "k0_theta_sign":
            n = 1-(1-f32(.3))/j
            assert got == f32(-2e8/n*float(rate["theta"])) and k == 0
        if rate["periodic"] == "0" and rate["field"] == "affineJ_zero_drive":
            nulls.append(abs(got))
            assert abs(got) <= .001
        if rate["periodic"] == "0" and rate["field"] in (
                "affineJ_affinep_source", "affineJ_constantp_Ace_sign"):
            gradient_j = (1/32, 1/128 if rate["dimension"] == "3" else 0, 1/64)
            drive = [float(item[f"reference_drive_{axis}"]) for axis in "xyz"]
            n = 1-(1-f32(.3))/j
            source = 2e8/n/(1000*9.80665)*reference_k/((1-f32(.3))*ck)*sum(
                x*y for x, y in zip(gradient_j, drive))
            tolerance = 32*2**-23*max(1, abs(source))+1e-6
            assert abs(got-source) <= tolerance
            analytic_ratios.append(abs(got-source)/tolerance)
            source_ratios.append(float(rate["source_effect_over_original_roundoff"]))
            assert source_ratios[-1] > 100
    for item in periodic:
        assert int(item["poisoned_images"]) == 2 and int(item["ghost_neighbor_pairs"]) > 0
        assert item["C_owner_exact"] == item["Ace_theta_rate_owner_exact"] == "true"
    for item in scales:
        for kind in ("wave", "pore"):
            actual = float(item[f"actual_{kind}_s"])
            reference = float(item[f"reference_{kind}_s"])
            assert abs(actual-reference) <= 64*2**-52*max(abs(reference), float.fromhex("0x1p-1022"))
        assert float(item["max_current_k"]) > float(item["k0"])
        assert abs(float(item["actual_pore_s"])/float(item["old_initial_k_pore_s"])-1) > .001
    off = TESTS / f"outputs/upl_p3_perm_actual_{config}_r2_off"
    old = TESTS / f"outputs/upl_p3_actual_{config}_r3_run"
    for name in ("rates.csv", "summary.csv", "ct_suppression.csv", "ct_values.csv", "periodic_c.csv", "complete.json"):
        assert (off/name).read_bytes() == (old/name).read_bytes(), name
    results.append({"configuration": config, "rate_rows": len(rates),
                    "max_reference_error_over_original_limit": max(ratios),
                    "max_relative_k_error": max(law_relative),
                    "max_affine_error_over_original_limit": max(analytic_ratios),
                    "minimum_nonempty_chain_effect_over_roundoff": min(source_ratios),
                    "max_zero_drive_rate_pa_s": max(nulls),
                    "old_constant_k_six_file_pairs_byte_exact": True})

report = {"passed": True, "scope": "Offline independent saved-table/formula/hash recheck; not a new rate evaluation or trajectory",
          "configurations": results, "unique_verified_artifacts": len(bindings),
          "bindings": list(bindings.values()), "physical_acceptance": False,
          "limits": "No actual RunPeriodic/integration/interface/wall variable-k or sufficient stability claim. Component scale force statistics were explicitly manufactured."}
REPORT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "bindings"}, indent=2))
