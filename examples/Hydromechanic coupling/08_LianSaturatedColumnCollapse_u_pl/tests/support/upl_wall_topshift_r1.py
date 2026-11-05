"""Four initial top-side wall fits; no solver, production changes or hash scan."""
from pathlib import Path
import csv
import json
import os
import time
import xml.etree.ElementTree as ET
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
from upl_wall_geometry_r1 import cubic, support

T = Path(__file__).resolve().parents[1]
TAG = "upl_wall_topshift_r1"
IDS = (203, 254, 1851, 1903)
DP, H = .04, .048


def stat(path):
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def fit(at, target, soil):
    """Same raw matrix as retained audit; return values at the unchanged mirror."""
    raw = support(at, soil, H, DP*DP)
    d, w, g = cubic(at-soil, H, DP*DP)
    keep = np.linalg.norm(at-soil, axis=1) <= 2*H
    x = soil[keep]
    matrix = np.array([[w.sum(), np.dot(d[:, 0], w), np.dot(d[:, 1], w)],
                       [g[:, 0].sum(), np.dot(d[:, 0], g[:, 0]), np.dot(d[:, 1], g[:, 0])],
                       [g[:, 1].sum(), np.dot(d[:, 0], g[:, 1]), np.dot(d[:, 1], g[:, 1])]])
    assert float(np.linalg.det(matrix)) == raw["raw_mls_det"]
    assert int(np.linalg.matrix_rank(matrix)) == raw["raw_mls_rank"] == 3
    shift = at-target
    value_errors, anchor_errors, gradient_errors = [], [], []
    nearest = int(np.argmin(np.sum((at-soil)**2, axis=1)))
    # Constant, both affine basis directions, and an offset mixed affine field.
    for c, ax, az in ((128., 0., 0.), (128., 1., 0.), (128., 0., 1.), (128., 3., -2.)):
        field = c+ax*x[:, 0]+az*x[:, 1]
        rhs = np.array([np.dot(w, field), np.dot(g[:, 0], field), np.dot(g[:, 1], field)])
        q = np.linalg.inv(matrix) @ rhs
        expected = c+ax*target[0]+az*target[1]
        # d=fitcentre-source, so q[1:] is minus the physical gradient.
        value = q[0]+np.dot(q[1:], shift)
        sample = soil[nearest]
        anchored = c+ax*sample[0]+az*sample[1]-np.dot(q[1:], at-sample)+np.dot(q[1:], shift)
        value_errors.append(abs(float(value-expected)))
        anchor_errors.append(abs(float(anchored-expected)))
        gradient_errors.append(float(np.max(np.abs(-q[1:]-np.array([ax, az])))))
    assert np.all(np.isfinite(value_errors+anchor_errors+gradient_errors))
    return dict(raw, affine_fields=4, mirror_value_error_max=max(value_errors),
                anchored_mirror_value_error_max=max(anchor_errors),
                physical_gradient_error_max=max(gradient_errors))


def main():
    start = time.perf_counter()
    output = T/"figures"/(TAG+".csv")
    check = T/"logs"/(TAG+".check.json")
    note = T/"notes"/(TAG+".json")
    assert not output.exists() and not check.exists(), "Preserve retained outputs"
    inputs = [Path(__file__).resolve(), note, Path(__file__).with_name("upl_wall_geometry_r1.py"),
              Path(__file__).with_name("lian_collapse_geometry_review_r1.py"),
              T/"figures/lian_collapse_geometry_r1_particles.csv", T/"figures/upl_wall_geometry_r1.csv",
              T/"logs/upl_wall_geometry_r1.check.json", T/"configs/CaseLianSaturatedColumnCollapse_geometry_r1_Def.xml"]
    before = [stat(p) for p in inputs]
    old = json.loads(inputs[6].read_text(encoding="utf-8"))
    assert old["actual_seed_CSV_VTK_IDs_equal"] and old["soil_ids"] == 5000 and old["raw_mls_det_limit"] == 1e-3
    root = ET.parse(inputs[7]).getroot()
    assert float(root.find("casedef/constantsdef/hdp").get("value")) == 1.2
    planes = root.findall("execution/special/initialize/boundnormal_plane")
    assert [p.get("mkbound") for p in planes] == ["0", "1", "2"]
    assert [tuple(p.find("normal").get(c) for c in ("x", "y", "z")) for p in planes] == [("1","0","0"),("0","0","1"),("-1","0","0")]
    with inputs[4].open(encoding="utf-8", newline="") as f:
        ledger = list(csv.DictReader(f))
    by_id = {int(r["GenCase_Idp"]):r for r in ledger}
    assert len(by_id) == len(ledger) == 7060
    soil = np.array([[float(r["x_m"]),float(r["z_m"])] for r in ledger if int(r["mk"]) == 1])
    assert soil.shape == (5000, 2)
    with inputs[5].open(encoding="utf-8", newline="") as f:
        retained = {int(r["native_id"]):r for r in csv.DictReader(f)}
    rows = []
    for identity in IDS:
        r, oldrow = by_id[identity], retained[identity]
        wall = np.array([float(r["x_m"]), float(r["z_m"])])
        target = np.array([float(oldrow["single_target_x_m"]), float(oldrow["single_target_z_m"])])
        mk = int(r["mk"])
        assert mk in (10, 12) and float(oldrow["candidate_face_count"]) == 1
        expected = np.array([-wall[0] if mk == 10 else 8-wall[0], wall[1]])
        assert np.array_equal(target, expected)
        nearest = float(np.linalg.norm(soil-wall, axis=1).min())
        assert nearest == float(oldrow["physical_nearest_soil_m"]) and nearest <= 2*H
        centre = target+np.array([0., -DP])
        assert target[0] >= 0 and target[0] <= 4 and target[1] >= 0
        original, shifted = fit(target, target, soil), fit(centre, target, soil)
        assert original["raw_mls_det"] == float(oldrow["single_raw_mls_det"])
        row = dict(native_id=identity, mk=mk, wall_x_m=wall[0], wall_z_m=wall[1],
                   physical_nearest_soil_m=nearest, physically_near=True,
                   original_mirror_x_m=target[0], original_mirror_z_m=target[1],
                   shifted_fit_x_m=centre[0], shifted_fit_z_m=centre[1],
                   fit_shift_x_m=0., fit_shift_z_m=-DP, fit_shift_m=DP,
                   evaluation_mirror_unchanged=True, det_limit=1e-3)
        row.update({"original_"+k:v for k,v in original.items()})
        row.update({"shifted_"+k:v for k,v in shifted.items()})
        rows.append(row)
    assert len(rows) == 4 and [stat(p) for p in inputs] == before
    with output.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    result = dict(stage=TAG, passed=True, scope="Completed four-point initial binary64 offline check only",
                  native_ids=list(IDS), inputs=before, rows=4, field_count_per_fit=4,
                  original_det_passes=sum(r["original_raw_det_gate"] for r in rows),
                  shifted_det_passes=sum(r["shifted_raw_det_gate"] for r in rows),
                  max_shifted_mirror_value_error=max(r["shifted_mirror_value_error_max"] for r in rows),
                  max_shifted_anchored_mirror_value_error=max(r["shifted_anchored_mirror_value_error_max"] for r in rows),
                  max_shifted_physical_gradient_error=max(r["shifted_physical_gradient_error_max"] for r in rows),
                  det_limit=1e-3, numerical_reproduction_acceptance_threshold_added=False,
                  inputs_stat_unchanged=True, fresh_hashes=0, output=str(output),
                  no_top_wall_or_normal_added=True, production_or_inputs_modified=False,
                  solver_or_build_invoked=False, CPU_GPU_float_bit_equivalence=False,
                  deformed_support_validity_claimed=False, physical_acceptance=False,
                  elapsed_s=time.perf_counter()-start)
    with check.open("x", encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False); f.write("\n")
    print(json.dumps(result,allow_nan=False))


if __name__ == "__main__":
    main()
