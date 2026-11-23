"""GPU opening window using common Voronoi faces for pressure and acceleration flux."""
import argparse
import ctypes as ct
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import sparse

from c04_p3_pressure_component import GAMMA, K as CONDUCTIVITY
from cryer_pair_window import T, DT, DAMP, execute

RHO = 1000.
BETA = GAMMA/CONDUCTIVITY
INTERIOR = T/"outputs/cryer_voronoi_flux_interior_r1.npz"
SURFACE = T/"outputs/cryer_voronoi_surface_r1.npz"
DLL = T/"outputs/cryer_voronoi_window_build_r1/cryer_voronoi_window.dll"
OUT = T/"outputs/cryer_voronoi_window_open_r1"


def face_matrices(m):
    with np.load(INTERIOR) as inner, np.load(SURFACE) as wall:
        assert np.array_equal(inner["ids"], m.ids) and np.array_equal(wall["ids"], m.ids)
        assert np.array_equal(wall["surface_slots"], m.surface)
        assert np.array_equal(np.sort(np.r_[inner["interior_slots"],m.surface]),np.arange(m.n))
        ei, ej = inner["edges"].T
        ea = inner["area_m2"]
        wi, wj, wa = wall["i"], wall["j"], wall["area_m2"]
    fs = np.zeros(m.n, dtype=bool)
    fs[m.surface] = True
    assert np.all(ei < ej) and not np.any(fs[ei] & fs[ej]) and np.all(fs[wi])
    cross = fs[ei] | fs[ej]
    key = ei[cross].astype(np.int64)*m.n + ej[cross]
    core_wall = ~fs[wj]
    rev_key = (np.minimum(wi[core_wall], wj[core_wall]).astype(np.int64)*m.n
               + np.maximum(wi[core_wall], wj[core_wall]))
    order, rev = np.argsort(key), np.argsort(rev_key)
    assert np.array_equal(key[order], rev_key[rev])
    assert np.max(abs(ea[cross][order] - wa[core_wall][rev])) < 1e-13
    same_shell = fs[wj] & (wi < wj)
    i, j = np.r_[ei,wi[same_shell]], np.r_[ej,wj[same_shell]]
    area = np.r_[ea,wa[same_shell]]
    assert np.min(area) > 0 and len(np.unique(i.astype(np.int64)*m.n+j)) == len(i)
    sep = m.x[j] - m.x[i]
    length = np.linalg.norm(sep, axis=1)
    trans = area/length
    normal_area = trans[:,None]*sep
    # Impermeability sets the combined Darcy flux on physical faces to zero.
    # Open boundary vertices are prescribed unknowns, and all their neighbors remain in the solve.
    rows, cols = np.r_[i,i,j,j], np.r_[i,j,i,j]
    make = lambda data: sparse.coo_matrix((data,(rows,cols)),shape=(m.n,m.n)).tocsr()
    stiff = make(np.r_[trans,-trans,-trans,trans])
    flux = []
    for component in normal_area.T:
        flux.append(make(.5*np.r_[-component,-component,component,component]))
    return i, j, trans, normal_area, stiff, flux


def direct_flux(p,a,i,j,trans,normal_area):
    face = trans*(p[i]-p[j]) - .5*RHO*np.einsum("ij,ij->i", normal_area, a[i]+a[j])
    return np.bincount(i, face, minlength=len(p))-np.bincount(j, face, minlength=len(p))


def configure(g,m,h):
    ptr = ct.c_void_p
    for name, types in {
        "startWeak":[], "advanceWeak":[ct.c_int], "uploadWeak":[ct.c_int]+[ptr]*5,
        "uploadVoronoiFlux":[ct.c_int]+[ptr]*3, "weakFixture":[ptr,ptr,ptr,ct.c_int,ptr],
        "weakClosedFixture":[ptr,ptr,ct.c_double,ptr], "releaseWeak":[]
    }.items():
        getattr(g.lib,name).argtypes = types
    i,j,trans,normal_area,stiff,F = face_matrices(m)
    flux_acc = lambda a: sum(B@a[:,k] for k,B in enumerate(F))
    P = [B.multiply((1/m.mass)[:,None]).tocsr() for B in m.HT]
    # The trial pressure changes endpoint velocity by dt*P dq. Only damping reacts
    # to that velocity change in endpoint acceleration; AV and stress are frozen.
    jac = stiff + RHO*(1-DAMP*DT)*sum(B@Pj for B,Pj in zip(F,P))
    jac += (BETA*DT)*sum(D@Pj for D,Pj in zip(m.D,P)).multiply(m.volume[:,None])
    denom = np.asarray(abs(jac).sum(axis=1)).ravel()
    assert np.isfinite(denom).all() and np.min(denom) > 0
    g.call("uploadWeak",stiff.nnz,stiff.indptr,stiff.indices,stiff.data,m.volume,denom)
    assert all(np.array_equal(B.indptr,F[0].indptr) and np.array_equal(B.indices,F[0].indices) for B in F)
    packed = np.ascontiguousarray(np.column_stack([B.data for B in F]))
    g.call("uploadVoronoiFlux",F[0].nnz,F[0].indptr,F[0].indices,packed)
    g.call("startWeak")
    report = dict(edges=len(i),stiffness_nnz=stiff.nnz,acceleration_nnz=F[0].nnz,
                  native_mass_kg=m.mass.sum(),mechanical_work_volume_m3=m.volume.sum(),
                  denominator_min=denom.min(),denominator_max=denom.max(),
                  damping_s_inv=DAMP,step_s=DT,three_pressure_sweeps=True,
                  surface_boundary="closed zero total flux; open surface p=0",
                  volume_for_velocity_divergence="original P1 weak V",
                  inputs_sha256={str(path.relative_to(T)):hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (INTERIOR,SURFACE,DLL)})
    rng = np.random.default_rng(37173)
    dp = rng.standard_normal(m.n)
    da = np.column_stack([B@dp for B in P])
    derivative = direct_flux(dp,(1-DAMP*DT)*da,i,j,trans,normal_area) + BETA*DT*m.volume*m.divergence(da)
    report["coupled_directional_derivative_max_error"] = np.max(abs(jac@dp-derivative))
    assert report["coupled_directional_derivative_max_error"] < 1e-12
    face_energy = np.sum(trans*(dp[i]-dp[j])**2)
    ke = dp@(stiff@dp)
    assert abs(ke-face_energy) < 1e-12*ke and ke > 0
    report.update(positive_pressure_energy=ke,pressure_edge_energy_difference=ke-face_energy,
                  total_random_closed_flux=float(np.sum(derivative - BETA*DT*m.volume*m.divergence(da))))
    assert abs(report["total_random_closed_flux"]) < 1e-10
    ones = np.ones(m.n)
    zero = np.zeros(m.n)
    out = zero.copy()
    constant_a = np.broadcast_to([2.,-3.,4.],(m.n,3)).copy()
    # Linear gradient and constant acceleration, plus a full quadratic and its linear acceleration.
    grad = np.array([1.3,-2.7,.9])
    mat = np.array([[11.,-4.,3.],[-4.,8.,5.],[3.,5.,-15.]])
    quadratic_a = -(m.x@mat + grad)
    for name,q,a in (("constant_p",ones*1e4,np.zeros_like(m.x)),
                     ("linear_p",1000*(m.x@(-constant_a[0])),constant_a),
                     ("quadratic_p",1000*(m.x@grad+.5*np.einsum("ij,jk,ik->i",m.x,mat,m.x)),quadratic_a)):
        residual = stiff@q + RHO*flux_acc(a)
        independent = direct_flux(q,a,i,j,trans,normal_area)
        key = name+"_hydraulic_residual_max"
        report[key] = max(np.max(abs(residual)),np.max(abs(independent)))
        assert report[key] < 2e-11
    uniform_flux = flux_acc(constant_a)
    report["constant_a_only_interior_max"] = np.max(abs(uniform_flux[~h.fs]))
    report["constant_a_only_full_sum"] = uniform_flux.sum()
    assert report["constant_a_only_interior_max"] < 1e-13 and abs(uniform_flux.sum()) < 1e-13
    with np.load(T/"outputs/cryer_tet_step_reference_r1.npz") as fields:
        q,a,theta = (np.ascontiguousarray(fields[k].astype(np.float32).astype(float)) for k in
                     ("p_Pa","acceleration_m_s2","divergence_v_per_s"))
    for drain in (False,True):
        q_test = q.copy()
        if drain:
            q_test[h.fs] = 0
        independent = direct_flux(q_test,a,i,j,trans,normal_area)
        expected = (q_test-(independent+BETA*m.volume*theta)/denom).astype(np.float32).astype(float)
        if drain:
            expected[h.fs] = 0
        g.call("weakFixture",q_test,a,theta,int(drain),out)
        err = np.max(abs(out-expected))
        report["open_all_id_max_Pa" if drain else "closed_all_id_max_Pa"] = err
        if err > 2e-6:
            raise ArithmeticError(f"Per-particle GPU face row error {err} Pa")
    base = np.ascontiguousarray(m.surface_force(10000.)/m.mass[:,None])
    g.call("weakClosedFixture",zero,base,0.,out)
    report["uniform_multiplier_max_Pa"] = np.max(abs(out-10000))
    b = m.pressure_force(ones)
    c = -np.sum(b*(a+m.pressure_force(q)/m.mass[:,None]))/np.sum(b*b/m.mass[:,None])
    g.call("weakClosedFixture",q,a,0.,out)
    report["nonuniform_multiplier_max_Pa"] = np.max(abs((q+c).astype(np.float32).astype(float)-out))
    assert max(report["uniform_multiplier_max_Pa"],report["nonuniform_multiplier_max_Pa"]) < 2e-6
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll",type=Path,default=DLL)
    parser.add_argument("--out",type=Path,default=OUT)
    args = parser.parse_args()
    execute(args.dll,args.out,4160,weak=configure)
