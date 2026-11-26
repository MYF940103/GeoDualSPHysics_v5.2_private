"""Frozen Eq. (32) pressure term versus the current operator on identical saved material states.

All pressure rows omit gravity, solid acceleration, compression and beta. The pressure
diagonal S is the one used with the correction/source held fixed, as in Eq. (35).
"""
import csv
import json
from functools import lru_cache

import numpy as np
from scipy.spatial import cKDTree

from c08_h18_wend_partial_review_r1 import kernel
from c08_positive_suction_sites import OUT, RUNS, checked
from c08_psi25_local_suction import DP, FIXED, H
from c08_psi25_suction_row import pressure_row
from c08_psi25_suction_stencil import V0, eq23
from c08_psi25_tpi_native import TESTS, require


def geometry(x, volumes, i):
    tree = cKDTree(x)

    @lru_cache(None)
    def donors(idx):
        js = np.asarray(sorted(tree.query_ball_point(x[idx], 2 * H)))
        js = js[js != idx]
        d = x[js] - x[idx]  # r_ji = x_j - x_i
        r2 = np.einsum("ij,ij->i", d, d)
        _, factor = kernel(r2, H, np.float32(.557 / H**2), np.float32(-2.7852 / H**3))
        return js, d, -factor[:, None] * d

    @lru_cache(None)
    def inverse_moment(idx):
        js, d, g = donors(idx)
        return np.linalg.inv((d.T * volumes[js]) @ g)

    js, d, g = donors(i)
    weighted_grad = volumes[js, None] * (g @ inverse_moment(i).T)
    r2 = np.sum(d*d, axis=1)
    b = 2 * np.sum(weighted_grad*d, axis=1) / r2
    neighbor_grad = np.einsum("nij,nj->ni", [inverse_moment(j) for j in js], g)
    eta2 = float(np.float32((.1 * H)**2))
    w = np.sum((weighted_grad + volumes[js, None] * neighbor_grad)*d, axis=1) / (r2 + eta2)
    # Check normalization and the earlier independent constant-k Eq. (23) implementation.
    simple, _ = eq23(d, volumes[js], "Wendland", H)
    require(np.max(abs(d.T @ weighted_grad - np.eye(2))) < 1e-12, "First moment")
    require(np.allclose(b - weighted_grad @ (b @ d), simple, rtol=3e-6, atol=1e-5),
            "Constant-k Eq. (23) independent reconstruction")
    return js, d, weighted_grad, b, w


def evaluate(d, grad, b, w, dp, ki, kj, grad_k):
    grad_p = dp @ grad
    # Lian Eqs. (32,33): k_ji multiplies A_ij, but k_i multiplies E_i.
    lian_a = (.5 * (ki + kj)) * b
    lian_raw = lian_a @ dp
    lian_e = ki * grad_p @ (b @ d)
    prod_raw = ki * w @ dp
    prod_e = ki * grad_p @ (w @ d)
    prod_cross = grad_k @ grad_p
    return dict(prod_R=prod_raw-prod_e+prod_cross, paper_R=lian_raw-lian_e,
                prod_S=ki * w.sum(), paper_S=lian_a.sum(), prod_raw=prod_raw,
                prod_E=prod_e, prod_gradk_gradp=prod_cross, paper_raw=lian_raw, paper_E=lian_e)


def fixtures():
    points = DP * np.array([(a,b) for a in range(-9,10) for b in range(-9,10)], float)
    center = len(points) // 2
    rng = np.random.default_rng(1908)
    perturbation = rng.uniform(-.16*DP,.16*DP,points.shape)
    perturbation[center] = 0.
    records = []
    for label, x in (("square",points),("disordered",points+perturbation)):
        js, d, grad, b, w = geometry(x, np.full(len(x),DP**2), center)
        ki = 2e-4
        xx, zz = d.T
        for name, dp, k_slope, exact in (
            ("constant",0*xx,0.,0.), ("affine_x",xx,0.,0.),
            ("affine_z",zz,0.,0.), ("quadratic_x",xx**2,0.,2*ki),
            ("quadratic_z",zz**2,0.,2*ki), ("quadratic_xz",xx*zz,0.,0.),
            ("affine_k_affine_p",xx,0.5,0.5*ki),
        ):
            # div(k grad x) = 0.5*k0 for k = k0*(1+0.5*x).
            row = evaluate(d,grad,b,w,dp,ki,ki*(1+k_slope*xx),np.array([ki*k_slope,0.]))
            if name.startswith("affine_") and name != "affine_k_affine_p" or name == "constant":
                require(max(abs(row["paper_R"]),abs(row["prod_R"])) < 1e-12,
                        "Constant or affine annihilation")
            if label == "square":
                require(abs(row["paper_R"]-exact)<1e-12, "Lian square manufactured solution")
                if name == "affine_k_affine_p":
                    require(abs(row["prod_R"]-exact)<1e-12, "Production variable-k identity")
            records.append(dict(cloud=label,fixture=name,n=len(js),analytic_R=exact,**row))
    return records


def run():
    manufacture = fixtures()
    tag = RUNS["beta004"]
    receipt = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text(encoding="utf8"))
    require(receipt["passed"] and receipt["tag"] == tag and receipt["frames"] == 132, "Unreviewed run")
    records = []
    for part in (42,72,100,132):
        m,a,_ = checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",receipt)
        x = a["Posd"][:,[0,2]]
        J = a["PoroVolumeRatio"]
        volumes = V0*J
        for rid in (6918,6919,6920):
            i = int(np.searchsorted(a["Idp"],rid))
            js,d,grad,b,w = geometry(x,volumes,i)
            require(a["Idp"][i]==rid and a["FSType"][i] not in (2,3) and all(js>=FIXED),
                    "This pressure row is for interior material with soil first neighbors")
            ki = a["PoroHydraulicConductivity"][i]
            kj = a["PoroHydraulicConductivity"][js]
            dp = a["PorePress"][js].astype(float)-float(a["PorePress"][i])
            grad_k = ki / (2*(1-float(np.float32(.35)))) * ((J[js]-J[i]) @ grad)
            row = evaluate(d,grad,b,w,dp,ki,kj,grad_k)
            old = pressure_row(a,i)
            require(np.isclose(row["prod_R"],old["pressure_total"],rtol=1e-12,atol=1e-8)
                    and abs(row["prod_S"]-old["S_inv_m_s"])<1e-12, "Retained production formula")
            rdiff = row["paper_R"]-row["prod_R"]
            sdiff = row["paper_S"]-row["prod_S"]
            records.append(dict(part=part,step=m["Step"]+1,time_s=m["TimeStep"],
                tau_s=m["TimeStep"]-receipt["release_time_s"],id=rid,fs=int(a["FSType"][i]),
                n_soil=int(sum(js>=FIXED)),n_fixed=int(sum(js<FIXED)),J=J[i],k_m_s=ki,
                p_kPa=float(a["PorePress"][i])/1000,**row,delta_R=rdiff,
                abs_delta_R=abs(rdiff),delta_R_over_abs_prod_percent=100*rdiff/abs(row["prod_R"]),
                delta_S=sdiff,delta_S_percent=100*sdiff/row["prod_S"]))
    for name,rows in (("pressure_operator_comparison",records),("pressure_operator_fixtures",manufacture)):
        with (OUT/(name+".csv")).open("x",encoding="utf8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)


if __name__=="__main__":
    run()
