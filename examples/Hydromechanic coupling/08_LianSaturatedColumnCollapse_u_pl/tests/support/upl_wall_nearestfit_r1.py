"""One nearest-real-source retry for exactly ten initial weak wall samples."""
from pathlib import Path
import csv
import json
import time
from upl_wall_topshift_r1 import T, DP, H, stat, support, fit, np

TAG = "upl_wall_nearestfit_r1"
IDS = (203, 254, 274, 278, 279, 783, 1800, 1851, 1852, 1903)


def table(path, key):
    with path.open(encoding="utf-8", newline="") as f:
        return {int(r[key]):r for r in csv.DictReader(f)}


def main():
    started = time.perf_counter()
    output, check = T/"figures"/(TAG+".csv"), T/"logs"/(TAG+".check.json")
    assert not output.exists() and not check.exists(), "Preserve retained evidence"
    inputs = [Path(__file__).resolve(), T/"notes"/(TAG+".json"),
              Path(__file__).with_name("upl_wall_topshift_r1.py"),
              Path(__file__).with_name("upl_wall_geometry_r1.py"),
              Path(__file__).with_name("lian_collapse_geometry_review_r1.py"),
              T/"figures/lian_collapse_geometry_r1_particles.csv", T/"figures/upl_wall_geometry_r1.csv",
              T/"figures/upl_wall_topshift_r1.csv", T/"figures/upl_wall_cornerfit_r1.csv",
              T/"logs/upl_wall_geometry_r1.check.json"]
    before = [stat(p) for p in inputs]
    ledger = table(inputs[5], "GenCase_Idp")
    soil_rows = [(i,r) for i,r in ledger.items() if int(r["mk"]) == 1]
    soil_ids = np.array([i for i,r in soil_rows])
    soil = np.array([[float(r["x_m"]),float(r["z_m"])] for i,r in soil_rows])
    assert len(ledger) == 7060 and soil.shape == (5000,2) and len(set(soil_ids)) == 5000
    retained = table(inputs[6], "native_id")
    selected = tuple(i for i,r in retained.items() if r["physical_in_kernel_support"] == "True" and r["single_raw_det_gate"] == "False")
    assert selected == IDS
    previous = table(inputs[7], "native_id")
    top_ids = set(previous)
    previous.update(table(inputs[8], "native_id"))
    assert set(previous) == set(IDS) and len(top_ids) == 4
    old = json.loads(inputs[9].read_text(encoding="utf-8"))
    assert old["actual_seed_CSV_VTK_IDs_equal"] and old["physically_near"]["single_raw_det_failed"] == 10
    rows = []
    for identity in IDS:
        oldrow, prior, particle = retained[identity], previous[identity], ledger[identity]
        target = np.array([float(oldrow["single_target_x_m"]),float(oldrow["single_target_z_m"])])
        wall = np.array([float(particle["x_m"]),float(particle["z_m"])])
        physical_distance = float(np.linalg.norm(soil-wall, axis=1).min())
        assert physical_distance == float(oldrow["physical_nearest_soil_m"]) and physical_distance <= 2*H
        original = support(target, soil, H, DP*DP)  # Never invert an original failed fit.
        assert not original["raw_det_gate"] and original["raw_mls_det"] == float(oldrow["single_raw_mls_det"])
        d2 = np.sum((target-soil)**2, axis=1)
        k = int(np.argmin(d2))  # Exactly one candidate; native ledger order breaks exact ties.
        centre = soil[k].copy()
        assert float(np.linalg.norm(centre-target)) == float(oldrow["single_nearest_soil_m"])
        assert d2[k] < (2*H)**2
        nearest = support(centre, soil, H, DP*DP)
        valid = nearest["raw_det_gate"] and nearest["raw_mls_rank"] == 3
        if valid:
            nearest = fit(centre, target, soil)
        assert target[0] == float(prior["original_mirror_x_m"]) and target[1] == float(prior["original_mirror_z_m"])
        row = dict(native_id=identity, mk=int(particle["mk"]),
                   wall_x_m=wall[0], wall_z_m=wall[1], physical_nearest_soil_m=physical_distance,
                   physically_near=True, original_mirror_x_m=target[0], original_mirror_z_m=target[1],
                   nearest_source_id=int(soil_ids[k]), nearest_source_exact_ties=int(np.count_nonzero(d2 == d2[k])),
                   nearest_fit_x_m=centre[0], nearest_fit_z_m=centre[1],
                   fit_shift_x_m=centre[0]-target[0], fit_shift_z_m=centre[1]-target[1],
                   fit_shift_m=float(np.linalg.norm(centre-target)), evaluation_mirror_unchanged=True,
                   original_inverse_evaluated=False, nearest_centres_tried=1,
                   nearest_reproduction_evaluated=bool(valid), det_limit=1e-3,
                   prior_method="top_tangential_minus_dp" if identity in top_ids else "existing_SPR_halfspace_projection",
                   prior_fit_x_m=float(prior["shifted_fit_x_m"]), prior_fit_z_m=float(prior["shifted_fit_z_m"]),
                   prior_shift_m=float(prior["fit_shift_m"]),
                   prior_kernel_nodes=int(prior["shifted_kernel_nodes"]),
                   prior_raw_mls_det=float(prior["shifted_raw_mls_det"]),
                   prior_raw_mls_cond_inf=float(prior["shifted_raw_mls_cond_inf"]))
        row.update({"original_"+key:value for key,value in original.items()})
        row.update({"nearest_"+key:value for key,value in nearest.items()})
        rows.append(row)
    assert len(rows) == 10 and [stat(p) for p in inputs] == before
    with output.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader(); w.writerows(rows)
    evaluated = [r for r in rows if r["nearest_reproduction_evaluated"]]
    result = dict(stage=TAG, passed=True, scope="Completed ten-point initial binary64 offline check only",
                  native_ids=list(IDS), rows=10, inputs=before, original_inverse_evaluations=0,
                  centres_per_id=1, nearest_det_passes=sum(r["nearest_raw_det_gate"] for r in rows),
                  nearest_reproduction_evaluations=len(evaluated),
                  max_mirror_value_error=max((r["nearest_mirror_value_error_max"] for r in evaluated),default=None),
                  max_anchored_mirror_value_error=max((r["nearest_anchored_mirror_value_error_max"] for r in evaluated),default=None),
                  max_physical_gradient_error=max((r["nearest_physical_gradient_error_max"] for r in evaluated),default=None),
                  exact_tied_nearest_ids=[r["native_id"] for r in rows if r["nearest_source_exact_ties"] > 1],
                  det_limit=1e-3, numerical_reproduction_acceptance_threshold_added=False,
                  inputs_stat_unchanged=True, fresh_hashes=0, output=str(output),
                  new_wall_or_normal_or_images_added=False, production_or_inputs_modified=False,
                  solver_or_build_invoked=False, CPU_GPU_float_bit_equivalence=False,
                  far_wall_mask_resolved=False, nonlinear_accuracy_proved=False,
                  deformed_support_validity_claimed=False, physical_acceptance=False,
                  elapsed_s=time.perf_counter()-started)
    with check.open("x", encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False); f.write("\n")
    print(json.dumps(result,allow_nan=False))


if __name__ == "__main__":
    main()
