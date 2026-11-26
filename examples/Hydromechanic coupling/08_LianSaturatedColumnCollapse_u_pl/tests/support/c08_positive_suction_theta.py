"""Reconstruct divergence and Lian (24) on saved C08 positive-only +2.5-degree TPI states.

The neighbor-weighted porosity rate is compared on identical geometry and velocities.
Equation (25) uses the unweighted velocity divergence for its compression source.
No constitutive history, force stage, particle field, or solver is advanced.
"""
import csv
import json

import numpy as np
from scipy.spatial import cKDTree

from c08_h18_wend_partial_review_r1 import kernel
from c08_psi25_local_suction import FIXED, H, RUNS
from c08_psi25_suction_stencil import V0, bed_fits
from c08_psi25_tpi_native import CASE, TESTS, RELEASE_IDS, read_frame, require

OUT = TESTS / "figures/c08_positive_suction_theta"
SOLID0 = 1 - float(np.float32(.35))
CK = 2.
# ComputeDynamicPorePressureRateGpu uses standard gravity, independently of XML body acceleration.
TPI_GAMMA = 1000 * 9.80665


def split_rates(pair_div, solid_i, solid_j):
    theta = pair_div.sum()
    # Jdot = J*theta, n = 1-(1-n0)/J.  Eq. (24) instead puts 1-n_j inside the sum.
    rate_j = solid_i*theta
    rate_24 = solid_j @ pair_div
    delta = (solid_j-solid_i) @ pair_div
    require(np.isclose(rate_24-rate_j, delta, rtol=1e-10, atol=1e-12), "Difference identity failed")
    return theta, rate_j, rate_24, delta


def affine_fixture():
    # Anisotropic affine velocity, irregular but symmetric supports, variable porosity.
    points = np.array([[.04,.01],[-.04,-.01],[.01,.05],[-.01,-.05],[.03,-.025],[-.03,.025]])
    weights = np.array([.8,.8,.7,.7,1.,1.])
    moment = (points.T*weights) @ points
    grad = np.linalg.solve(moment, (points*weights[:,None]).T).T
    affine = np.array([[.8,-.2],[.1,-.35]])
    pair = np.sum((points @ affine.T)*grad, axis=1)
    theta, dj, d24, delta = split_rates(pair, .65, np.full(len(pair),.65))
    require(abs(theta-affine.trace())<1e-14 and abs(delta)<1e-14, "Constant n or affine reproduction")
    variable = np.array([.60,.65,.67,.68,.62,.61])
    _, new_j, new_24, gap = split_rates(pair, .65, variable)
    require(new_j==dj and abs(new_24-d24)>1e-4 and abs(gap)>1e-4, "Variable n stencil")


def frame_rows(part, path, receipt):
    st = path.stat()
    require([str(path.relative_to(CASE)), st.st_size, st.st_mtime_ns] in receipt["files"], "Changed native file")
    m,a,_,_ = read_frame(path)
    require(np.array_equal(a["Idp"], RELEASE_IDS), "Native owner identity differs")
    xz = a["Posd"][:,[0,2]]
    tree = cKDTree(xz)
    J = a["PoroVolumeRatio"]
    vel = a["Vel"][:,[0,2]].copy()
    p = a["PorePress"]
    worst = FIXED + int(np.argmin(p[FIXED:]))
    ring = {int(j) for j in tree.query_ball_point(xz[worst],2*H) if j>=FIXED}
    selected = ring | set(np.searchsorted(RELEASE_IDS, [6918, 7010]))
    prepared_walls = set()
    result = []
    for i in sorted(selected):
        js = np.asarray(tree.query_ball_point(xz[i],2*H),dtype=int)
        js = js[js!=i]
        d = xz[js]-xz[i]
        _,fac = kernel(np.sum(d*d,axis=1),H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
        g = -d*fac[:,None]
        vg = g*(V0*J[js])[:,None]
        moment = d.T@vg
        require(np.linalg.det(moment)>0 and abs(np.trace(moment)-a["PosDiv"][i])<.001,
                "Singular/mismatched saved moment")
        corr_grad = np.linalg.solve(moment,vg.T).T
        bed = js<FIXED
        for wall in set(js[bed])-prepared_walls:
            # This sample is supported only by the NoSlip bed, not the retired right wall.
            require(255<=a["Idp"][wall]<1805, "Unexpected wall for these right-side material owners")
            owners, w, _, _ = next(bed_fits(a,int(wall)))
            # The same mirror extrapolation is used in stage zero for J and NoSlip ghost velocity.
            require(abs(w@J[owners]-J[wall])<1e-4, "Frozen bed J differs from native")
            vel[wall]=-(w@vel[owners])
            prepared_walls.add(wall)
        pair = np.sum((vel[js]-vel[i]).astype(float)*corr_grad,axis=1)
        solid_j = SOLID0/J[js]
        solid_i = SOLID0/J[i]
        theta, dj, d24, delta = split_rates(pair,solid_i,solid_j)
        native_theta = float(a["PoroThetaLastStage"][i])
        # Log-conductivity is proportional to J-1; map n-dot only to a local tangent at this state.
        dlogk_delta = J[i]*delta/(solid_i*CK*SOLID0)
        result.append(dict(part=part,step=m["Step"]+1,tau_s=m["TimeStep"]-receipt["release_time_s"],
                           id=int(a["Idp"][i]),min_pressure_owner=int(i==worst),
                           min_pressure_neighborhood=int(i in ring),x_m=xz[i,0],z_m=xz[i,1],
                           p_kPa=float(p[i])/1000.,fs=int(a["FSType"][i]),J=J[i],n=1-solid_i,
                           soil_neighbors=int((~bed).sum()),bed_neighbors=int(bed.sum()),
                           moment_trace_difference=np.trace(moment)-float(a["PosDiv"][i]),
                           theta_saved_per_s=native_theta,theta_frozen_per_s=theta,
                           theta_difference_per_s=theta-native_theta,
                           theta_soil_per_s=pair[~bed].sum(),theta_bed_per_s=pair[bed].sum(),
                           ndot_from_J_per_s=dj,ndot_eq24_per_s=d24,ndot_delta_per_s=delta,
                           ndot_delta_soil_per_s=(solid_j[~bed]-solid_i)@pair[~bed],
                           ndot_delta_bed_per_s=(solid_j[bed]-solid_i)@pair[bed],
                           frozen_dlogk_per_s=J[i]*theta/(CK*SOLID0),
                           dlogk_delta_per_s=dlogk_delta,
                           compression_saved_Pa_per_m_s=-TPI_GAMMA*native_theta,
                           compression_frozen_Pa_per_m_s=-TPI_GAMMA*theta))
    return result


def write_csv(path, rows):
    with path.open("x",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def main():
    target = OUT/"material_rates.csv"
    summary = OUT/"sampled_neighborhoods.csv"
    require(not target.exists() and not summary.exists(), "Retained analysis already exists")
    affine_fixture()
    tag = RUNS["positive_only"]
    receipt = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
    require(receipt["passed"] and receipt["frames"]==132 and receipt["tag"]==tag,"Wrong branch")
    all_rows, stats = [], []
    for part in range(5,133):
        path = TESTS/"outputs"/tag/"data"/f"Part_{part:04}.bi4"
        rows = frame_rows(part,path,receipt)
        all_rows.extend(rows)
        ring = [r for r in rows if r["min_pressure_neighborhood"]]
        center, = [r for r in ring if r["min_pressure_owner"]]
        def rms(key):
            return float(np.sqrt(np.mean([r[key]**2 for r in ring])))
        stats.append(dict(part=part, step=center["step"], tau_s=center["tau_s"], worst_id=center["id"],
                          worst_pressure_kPa=center["p_kPa"], sampled_soil=len(ring),
                          rms_theta_difference_per_s=rms("theta_difference_per_s"),
                          rms_ndot_J_per_s=rms("ndot_from_J_per_s"),
                          rms_ndot_difference_per_s=rms("ndot_delta_per_s"),
                          rms_dlogk_difference_per_s=rms("dlogk_delta_per_s"),
                          max_abs_ndot_difference_per_s=max(abs(r["ndot_delta_per_s"]) for r in ring)))
    OUT.mkdir(exist_ok=True,parents=True)
    write_csv(target,all_rows)
    write_csv(summary,stats)
    print(f"Reviewed {len(stats)} native frames and {len(all_rows)} material-frame rates")


if __name__=="__main__":
    main()
