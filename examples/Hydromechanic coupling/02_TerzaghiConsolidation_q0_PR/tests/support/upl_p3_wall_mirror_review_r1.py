"""Independent CSV/analytic review only: no compiler, project object or solver."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

TESTS = Path(__file__).resolve().parent.parent
OUT = TESTS / "notes" / "upl_p3_wall_mirror_review_r1.json"
EPS = np.finfo(float).eps
EPSF = np.finfo(np.float32).eps
DP = 2.0 ** -6
RHOW = 1000.0
KH = float(np.float32(.0001))


def entry(path):
    path = Path(path).resolve()
    h = hashlib.sha256(path.read_bytes())
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def close(a, b, scale=0.):
    a, b = np.asarray(a), np.asarray(b)
    assert np.max(np.abs(a - b)) <= 4096 * EPS * max(float(np.max(np.abs(a))), float(np.max(np.abs(b))), scale, 1e-300)


def geometry(dim, rotated, disorder):
    n = np.array([.6, 0, .8] if dim == 2 and rotated else
                 ([2 / 3, 1 / 3, 2 / 3] if dim == 3 and rotated else [1., 0, 0]))
    if dim == 2:
        tangent = np.array([-n[2], 0, n[0]])
    else:
        tangent = np.cross(n, [0., 0, 1]) if rotated else np.array([0., 1, 0])
        tangent /= np.linalg.norm(tangent)
    second = np.cross(n, tangent)
    gravity = np.array([-4., 0 if dim == 2 else 2., -8.])
    seed = 0x71c3a591
    def jitter():
        nonlocal seed
        seed = (1664525 * seed + 1013904223) & 0xffffffff
        return .05 * DP * (2 * seed / 4294967295. - 1) if disorder else 0.
    points, probes = [], []
    for s in range(6):
        for u in range(-4, 5):
            for v in ([0] if dim == 2 else range(-4, 5)):
                sn, tn = (s + .5) * DP + jitter(), u * DP + jitter()
                bn = 0 if dim == 2 else v * DP + jitter()
                if s < 3 and u == v == 0:
                    probes.append(len(points))
                points.append(n * sn + tangent * tn + second * bn)
    xyz = np.asarray(points)
    mirrored = xyz - 2 * np.outer(xyz @ n, n)
    return n, tangent, gravity, np.vstack((xyz, mirrored)), probes


def main():
    assert not OUT.exists(), "Retained review protected"
    run_path = TESTS / "logs" / "upl_p3_wall_mirror_r2.check.json"
    run = load(run_path)
    assert run["passed"] and run["build_exit"] == run["program_exit"] == 0
    assert not run["production_dynamic_function_called"] and not run["project_solver_or_GenCase_started"]
    bindings = []
    def walk(v):
        if isinstance(v, dict):
            if all(k in v for k in ("path", "bytes", "sha256")):
                bindings.append(v)
            for value in v.values():
                walk(value)
        elif isinstance(v, list):
            for value in v:
                walk(value)
    walk(run)
    freeze = load(run["source_freeze"]["path"])
    walk(freeze)
    checked = {}
    for e in bindings:
        key = e["path"].casefold()
        if key not in checked:
            checked[key] = entry(e["path"])
        a = checked[key]
        assert a["bytes"] == e["bytes"] and a["sha256"] == e["sha256"]
    directory = TESTS / "outputs" / "upl_p3_wall_mirror_r2"
    cases = np.genfromtxt(directory / "cases.csv", delimiter=",", names=True)
    probes = np.genfromtxt(directory / "probes.csv", delimiter=",", names=True)
    done = load(directory / "complete.json")
    assert len(cases) == 48 and len(probes) == 144 and done["passed"] and done["probe_pairs"] == 144
    assert np.array_equal(cases["case"], np.arange(48))
    keys = [tuple(int(row[k]) for k in ("dimension", "rotation", "disorder", "Jmode", "fluxcase")) for row in cases]
    assert set(keys) == set(itertools.product((2, 3), (0, 1), (0, 1), (0, 1, 2), (0, 1)))
    bounds, negative, flux_ratios, rates, wrong_c = [], [], [], [], []
    for case in cases:
        cid = int(case["case"])
        dim, rot, disorder, jm, flow = keys[cid]
        n, tangent, g, xyz, expected_probes = geometry(dim, rot, disorder)
        native = len(xyz) // 2
        a0 = .25 * tangent if flow else np.zeros(3)
        grad = RHOW * (g - a0) + (1024 * tangent if flow else 0)
        ace = np.asarray(a0 - g, dtype=np.float32).astype(float)
        aceghost = np.asarray((ace + g) - 2 * n * np.dot(ace + g, n) - g, dtype=np.float32).astype(float)
        wrong = np.asarray(ace - 2 * n * np.dot(ace, n), dtype=np.float32).astype(float)
        gamma = RHOW * np.linalg.norm(g)  # Same production nonzero-g branch, not g=0 fallback.
        qtrue = -KH / gamma * (1024 * tangent if flow else np.zeros(3))
        close(case["normal_gravity"], np.dot(n, g))
        close(case["pressure_rounding_E"], 2 * EPSF * max(1., float(np.max(abs(4096 + xyz @ grad)))))
        close(case["acceleration_rounding_EA"], 4 * EPSF * max(1., np.linalg.norm(g), np.linalg.norm(a0 - g)))
        assert case["native"] == native
        selected = probes[probes["case"] == cid]
        assert np.array_equal(selected["probe"], expected_probes)
        close(selected["depth"], xyz[expected_probes] @ n)
        local_errors, local_rates = [], []
        for row in selected:
            vectors = {name: np.array([row[name + "_q" + axis] for axis in "xyz"])
                       for name in ("native", "ghost", "face", "analytic")}
            close(vectors["analytic"], qtrue)
            close(vectors["face"], .5 * (vectors["native"] + vectors["ghost"]))
            for name in ("native", "ghost", "face"):
                close(row[name + "_qn"], np.dot(vectors[name], n), np.linalg.norm(vectors[name]))
            bound = float(row["face_bound"])
            assert bound > 0 and abs(row["face_qn"]) <= bound and np.linalg.norm(vectors["face"] - qtrue) <= bound
            bad0 = .5 * (vectors["native"] + vectors["ghost"] + KH / gamma * RHOW * aceghost)
            badw = .5 * (vectors["native"] + vectors["ghost"] - KH / gamma * RHOW * (wrong - aceghost))
            close(row["negative_zero_face_qn"], np.dot(bad0, n))
            close(row["negative_wrong_g_face_qn"], np.dot(badw, n))
            assert row["negative_zero_native_qn"] == row["native_qn"] == row["negative_wrong_g_native_qn"]
            assert abs(row["negative_zero_face_qn"]) > bound and abs(row["negative_wrong_g_face_qn"]) > bound
            negative += [abs(row["negative_zero_face_qn"]) / bound, abs(row["negative_wrong_g_face_qn"]) / bound]
            bounds.append(abs(row["face_qn"]) / bound)
            if flow:
                assert bound < .01 * np.linalg.norm(qtrue)
                for name in ("native", "ghost", "face"):
                    assert abs(np.dot(vectors[name], tangent)) > .5 * np.linalg.norm(qtrue)
                flux_ratios.append(bound / np.linalg.norm(qtrue))
            for name in ("native", "ghost"):
                value, rb = row[name + "_rate"], row[name + "_rate_bound"]
                assert abs(value) <= rb and float(np.float32(value)) == value
                rates.append(abs(value) / rb)
                local_rates.append(abs(value))
                local_errors.append(np.linalg.norm(vectors[name] - qtrue))
            wrong_c.append((cid, int(row["probe"]), float(row["wrong_C_gradient_bound_ratio"]), disorder, jm))
        close(case["max_q_error"], max(local_errors))
        close(case["max_abs_rate"], max(local_rates))
        close(case["max_face_qn"], max(abs(selected["face_qn"])))
        for error, bound in (("max_gradient_error", "max_gradient_bound"), ("max_Lstar", "max_Lstar_bound"),
                             ("max_divAce", "max_divAce_bound"), ("max_abs_rate", "max_rate_bound"), ("max_q_error", "max_q_bound")):
            assert 0 <= case[error] <= case[bound] and case[bound] > 0
    detected = [x for x in wrong_c if x[2] > 1]
    assert len(detected) == done["wrong_C_detected_probes"] == 72
    assert any(x[3] == 1 and x[4] == 2 for x in detected)
    close(max(x[2] for x in wrong_c), done["max_wrong_C_gradient_bound_ratio"])
    r1 = load(TESTS / "logs" / "upl_p3_wall_mirror_r1.check.json")
    assert r1["build_exit"] != 0 and r1["program_exit"] is None
    old = (TESTS / "support" / "upl_p3_wall_mirror_r1.cpp").read_text()
    new = (TESTS / "support" / "upl_p3_wall_mirror_r2.cpp").read_text()
    assert old.replace("  StKWendlandCte kernel;", "  fsph::StKWendlandCte kernel;") == new
    result = dict(passed=True, scope="Read-only CSV, analytic flux/rounding-input reconstruction and frozen C++ formula review; no independent all-node C/Lstar reassembly.",
                  input=entry(run_path), review_script=entry(__file__), hash_binding_records=len(bindings), unique_bound_files=len(checked), hash_mismatches=0,
                  cases=48, probe_pairs=144, native_and_mirror_evaluations=288,
                  all_case_keys_and_seeded_probe_geometry_verified=True, all_E_EA_prior_inputs_independently_recomputed=True,
                  all_qn_and_face_vectors_independently_recomputed=True, all_correct_rates_inside_original_exported_bounds=True,
                  max_correct_face_normal_flux_m_s=float(np.max(abs(probes["face_qn"]))), max_correct_face_qn_over_bound=max(bounds),
                  maximum_flux_error_m_s=float(max(cases["max_q_error"])), maximum_flux_bound_m_s=float(max(cases["max_q_bound"])),
                  maximum_tangential_case_face_bound_over_qtrue=max(flux_ratios),
                  minimum_wrong_acceleration_face_qn_over_correct_bound=min(negative),
                  maximum_correct_abs_rate_Pa_s=float(max(cases["max_abs_rate"])), maximum_correct_rate_over_bound=max(rates),
                  wrong_C_detected_probes=len(detected), max_wrong_C_error_over_original_bound=max(x[2] for x in wrong_c),
                  maximum_C_reflection_change=float(max(cases["max_C_reflection_change"])),
                  wrong_zero_mirror_native_rate_max_abs_change_Pa_s=float(max(abs(probes["negative_zero_native_rate"] - probes["native_rate"]))),
                  wrong_gravity_reflection_native_rate_max_abs_change_Pa_s=float(max(abs(probes["negative_wrong_g_native_rate"] - probes["native_rate"]))),
                  prior_r1_compile_only_namespace_failure_preserved=True,
                  arithmetic_source_review="The weight w=Vj*d.(Ci*g+Cj*g)/(r2+Eta2),Lp-Gp.Lx+rho div(Ace),Kw/n and final float write agree with frozen production expressions. Gamma at JSphCpu.cpp:4193-4194 is rho*(|g|>0? |g|:9.80665); declared nonzero-g fixture uses the same branch. Previous g0 periodic reference fallback is not the nonzero-g formula.",
                  bounds_scope="Source and pre-run note were reviewed: E/EA and absolute-weight propagation are prior geometry/input bounds,not observed-error fits. CSV checks verify per-probe face/rate bounds and case aggregate gradient/Lstar/divAce bounds. Per-node Sg/Wsum/C moments are not exported,so their reconstruction/assertions remain frozen-C++ source evidence,not a second independent operator execution.",
                  not_production_helper_call=True, not_actual_mdbc_or_wall_integration=True, no_project_solver_or_GenCase=True, physical_acceptance=False,
                  limitations=["Static single plane only; face flux is the declared arithmetic native/mirror average,not an implemented production face flux.","Correct complete rate has a nonzero float-rounding residual; passing its prior bound is not exact equilibrium or strict zero rate.","No NoSlip/shear,moving-wall,corner,mechanical-force-balance,conservation,trajectory,physical-theory or public/GPU acceptance.","Correct bounded rate does not by itself prove no-flow: vector Darcy flux and nonzero tangential flux plus both acceleration negative controls are separately tested."])
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
