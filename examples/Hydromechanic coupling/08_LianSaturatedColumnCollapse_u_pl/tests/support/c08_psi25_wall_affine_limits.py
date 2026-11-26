"""Feasibility of convex, affine-exact bed extrapolation on the retained C08 donor sets."""
import csv
import json
from itertools import groupby

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull

from c08_psi25_local_suction import DP, OUT, RUNS, save
from c08_psi25_suction_stencil import bed_fits
from c08_psi25_tpi_native import CASE, TESTS, RELEASE_IDS, read_frame, require


def affine_limits(donors, target):
    # Normalize offsets to particle spacings so all moment constraints are dimensionless.
    offsets = (donors - target) / DP
    hull = ConvexHull(offsets)
    signed_distances = hull.equations[:, -1]
    edges = offsets[hull.vertices]
    segments = np.roll(edges, -1, axis=0) - edges
    along = np.clip(-np.sum(edges * segments, axis=1) / np.sum(segments**2, axis=1), 0, 1)
    outside = signed_distances.max() > 1e-9
    distance = np.min(np.linalg.norm(edges + along[:, None] * segments, axis=1)) if outside else 0.

    # w = positive - negative. Minimize total negative mass at fixed unit sum and first moment.
    n = len(donors)
    moments = np.vstack((np.ones(n), offsets.T))
    rhs = np.array([1., 0., 0.])
    sol = linprog(np.r_[np.zeros(n), np.ones(n)],
                  A_eq=np.hstack((moments, -moments)), b_eq=rhs,
                  bounds=(0, None), method="highs")
    require(sol.success, "Full affine constraints infeasible")
    require(np.max(np.abs(moments @ (sol.x[:n]-sol.x[n:]) - rhs)) < 1e-8,
            "Affine LP returned a non-reproducing stencil")
    require(outside == (sol.fun > 1e-8), "Hull and independent linear optimization disagree")

    # Tangential-only condition: a flat bed with a separately prescribed normal head gradient.
    lo, hi = np.min(offsets[:, 0]), np.max(offsets[:, 0])
    require(hi > lo, "No horizontal extent for the bed fit")
    tangential_gap = max(0., lo, -hi)
    return dict(outside_hull=int(outside), hull_distance_dp=distance,
                min_negative_full=float(sol.fun), tangent_distance_dp=tangential_gap,
                min_negative_tangent=tangential_gap/(hi-lo))


def run():
    square = DP * np.array([[0.,0.], [1.,0.], [1.,1.], [0.,1.]])
    for target, gap, full, tangent in (([.3,.2],0.,0.,0.), ([.3,-.5],.5,.5,0.),
                                        ([1.3,.3],.3,.3,.3)):
        result = affine_limits(square, DP*np.array(target))
        require(np.allclose([result["hull_distance_dp"], result["min_negative_full"],
                             result["min_negative_tangent"]], [gap,full,tangent],
                            rtol=0, atol=1e-10), "Failed manufactured bed geometry")
    with (OUT/"bed_extrapolation.csv").open() as f:
        rows = list(csv.DictReader(f))
    results = []
    for (part, label), entries in groupby(rows, key=lambda r: (int(r["part"]), r["run"])):
        tag = RUNS[label]
        path = TESTS/"outputs"/tag/"data"/f"Part_{part:04}.bi4"
        receipt = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
        stat = path.stat()
        require(receipt["passed"] and [str(path.relative_to(CASE)), stat.st_size, stat.st_mtime_ns]
                in receipt["files"], "Source binding changed")
        meta, arrays, _, _ = read_frame(path)
        require(np.array_equal(arrays["Idp"], RELEASE_IDS), "Native ID mismatch")
        for row in entries:
            wi = int(np.searchsorted(RELEASE_IDS, int(row["wall_id"])))
            bed = arrays["Posd"][wi, [0,2]]
            mirror = bed + [0., np.float32(-2*bed[1])]
            donors, weights, anchor, attempt = next(bed_fits(arrays, wi))
            require(attempt == int(row["fit_attempt"]) and int(arrays["Idp"][anchor]) == int(row["anchor_id"])
                    and float(row["time_s"]) == meta["TimeStep"], "Different native bed fit or clock")
            limits = affine_limits(arrays["Posd"][donors][:,[0,2]], mirror)
            used = float(-weights[weights < 0].sum())
            require(used >= limits["min_negative_full"]-1e-8 and
                    abs(used+float(row["sum_neg_weights"])) < 1e-9, "LP bound or reference weights differ")
            results.append(dict(run=label, part=part, step=int(row["step"]), tau_s=float(row["tau_s"]),
                                wall_id=int(row["wall_id"]), donors=len(donors), fit_attempt=attempt,
                                used_negative_mass=used, **limits))
    require(len(results)==49, "Expected the 49 previously reproduced bed fits")
    save("bed_affine_limits.csv", results)


if __name__ == "__main__":
    run()
