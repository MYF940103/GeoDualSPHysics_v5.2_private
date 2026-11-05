"""Six initial bottom corners: existing SPR centre projection, no fluid images."""
from pathlib import Path
import csv
import json
import time
from upl_wall_topshift_r1 import T, DP, H, stat, fit, support, np

TAG = "upl_wall_cornerfit_r1"
IDS = (274, 278, 279, 783, 1800, 1852)
# Existing map<mk,...> order: left, bottom, right. No top wall.
PLANES = ((1., 0., 0.), (0., 1., 0.), (-1., 0., 4.))


def project(target):
    """JSphCpuSingle.cpp:275-290, in the real XML x-z wall half-spaces."""
    outside = any(ax*target[0]+az*target[1]+offset < -1e-6*DP
                  for ax, az, offset in PLANES)
    centre = target.copy()
    if not outside:
        return centre, 0
    for iteration in range(128):
        residual = 0.
        for ax, az, offset in PLANES:
            gap = DP-(ax*centre[0]+az*centre[1]+offset)
            if gap > 0:
                centre = centre+np.array([ax, az])*gap
                residual = max(residual, gap)
        if residual <= 1e-6*DP:
            return centre, iteration+1
    raise AssertionError("Same SPR 128-iteration projection failed")


def main():
    start = time.perf_counter()
    output = T/"figures"/(TAG+".csv")
    check = T/"logs"/(TAG+".check.json")
    assert not output.exists() and not check.exists(), "Preserve retained evidence"
    inputs = [Path(__file__).resolve(), T/"notes"/(TAG+".json"),
              Path(__file__).with_name("upl_wall_topshift_r1.py"),
              Path(__file__).with_name("upl_wall_geometry_r1.py"),
              Path(__file__).with_name("lian_collapse_geometry_review_r1.py"),
              T/"figures/lian_collapse_geometry_r1_particles.csv", T/"figures/upl_wall_geometry_r1.csv",
              T/"logs/upl_wall_geometry_r1.check.json"]
    before = [stat(p) for p in inputs]
    with inputs[5].open(encoding="utf-8", newline="") as f:
        ledger = list(csv.DictReader(f))
    by_id = {int(r["GenCase_Idp"]):r for r in ledger}
    soil = np.array([[float(r["x_m"]),float(r["z_m"])] for r in ledger if int(r["mk"]) == 1])
    assert len(by_id) == len(ledger) == 7060 and soil.shape == (5000, 2)
    with inputs[6].open(encoding="utf-8", newline="") as f:
        retained = {int(r["native_id"]):r for r in csv.DictReader(f)}
    selected = tuple(k for k,r in retained.items() if r["physical_in_kernel_support"] == "True"
                     and r["single_raw_det_gate"] == "False" and r["candidate_face_count"] == "2")
    assert selected == IDS
    prior = json.loads(inputs[7].read_text(encoding="utf-8"))
    assert prior["actual_seed_CSV_VTK_IDs_equal"] and prior["eligible_two_face"]["rows"] == 6
    rows = []
    for identity in IDS:
        source, old = by_id[identity], retained[identity]
        wall = np.array([float(source["x_m"]),float(source["z_m"])])
        target = np.array([float(old["single_target_x_m"]),float(old["single_target_z_m"])])
        mk = int(source["mk"])
        own = wall.copy()
        if mk == 11: own[1] = -own[1]
        elif mk == 12: own[0] = 8-own[0]
        else: raise AssertionError("Unexpected corner wall mk")
        assert np.array_equal(target, own)
        nearest = float(np.linalg.norm(soil-wall, axis=1).min())
        assert nearest == float(old["physical_nearest_soil_m"]) and nearest <= 2*H
        original = support(target, soil, H, DP*DP)  # No inverse of a failed/singular raw fit.
        assert original["raw_mls_det"] == float(old["single_raw_mls_det"]) and not original["raw_det_gate"]
        centre, iterations = project(target)
        shifted = support(centre, soil, H, DP*DP)
        valid = shifted["raw_det_gate"] and shifted["raw_mls_rank"] == 3
        if valid:
            shifted = fit(centre, target, soil)
        row = dict(native_id=identity, mk=mk, wall_x_m=wall[0], wall_z_m=wall[1],
                   physical_nearest_soil_m=nearest, physically_near=True,
                   original_mirror_x_m=target[0], original_mirror_z_m=target[1],
                   shifted_fit_x_m=centre[0], shifted_fit_z_m=centre[1],
                   fit_shift_x_m=centre[0]-target[0], fit_shift_z_m=centre[1]-target[1],
                   fit_shift_m=float(np.linalg.norm(centre-target)), projection_iterations=iterations,
                   evaluation_mirror_unchanged=True, det_limit=1e-3,
                   original_inverse_evaluated=False, shifted_reproduction_evaluated=bool(valid))
        row.update({"original_"+k:v for k,v in original.items()})
        row.update({"shifted_"+k:v for k,v in shifted.items()})
        rows.append(row)
    assert len(rows) == 6 and [stat(p) for p in inputs] == before
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with output.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows)
    evaluated = [r for r in rows if r["shifted_reproduction_evaluated"]]
    result = dict(stage=TAG, passed=True, scope="Completed six-point initial binary64 offline check only",
                  native_ids=list(IDS), inputs=before, rows=6,
                  original_rank_counts={str(k):sum(r["original_raw_mls_rank"] == k for r in rows) for k in (2,3)},
                  original_det_passes=0, original_inverse_evaluations=0,
                  shifted_det_passes=sum(r["shifted_raw_det_gate"] for r in rows),
                  shifted_reproduction_evaluations=len(evaluated),
                  max_shifted_mirror_value_error=max((r["shifted_mirror_value_error_max"] for r in evaluated),default=None),
                  max_shifted_anchored_mirror_value_error=max((r["shifted_anchored_mirror_value_error_max"] for r in evaluated),default=None),
                  max_shifted_physical_gradient_error=max((r["shifted_physical_gradient_error_max"] for r in evaluated),default=None),
                  det_limit=1e-3, numerical_reproduction_acceptance_threshold_added=False,
                  inputs_stat_unchanged=True, fresh_hashes=0, output=str(output),
                  fluid_or_wall_images_added=False, new_wall_or_normal_added=False,
                  production_or_inputs_modified=False, solver_or_build_invoked=False,
                  CPU_GPU_float_bit_equivalence=False, deformed_support_validity_claimed=False,
                  physical_acceptance=False, elapsed_s=time.perf_counter()-start)
    with check.open("x", encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False); f.write("\n")
    print(json.dumps(result,allow_nan=False))


if __name__ == "__main__":
    main()
