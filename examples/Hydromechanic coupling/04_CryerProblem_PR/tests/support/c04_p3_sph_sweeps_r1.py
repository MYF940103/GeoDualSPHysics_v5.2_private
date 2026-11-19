"""Frozen original P3 pressure-only iteration. No eigensolver or native simulation."""
import argparse
import csv
import json
from pathlib import Path

from cryer_coupled_shell_modes import Graph, DP, T, np
from scipy import sparse


TAG = "c04_p3_sph_sweeps_r1"
SPH_SOURCE = "outputs/cryer_p3_gpu_r2_source/JSphGpu_ker.cu:1591-1661"
PREP_SOURCE = "outputs/cryer_p3_gpu_r2_source/upl_tpi_cryer_gpu_r1.cuh:144-151"


def iteration(g):
    # Pressure from the CUDA path is q+R/S, S=-k sum_j w_ij.
    # Corrections involving theta and div(a) are held fixed for this error map.
    # gp_i = C_i sum_j g_ij (p_j-p_i), Lp = sum w_ij(p_i-p_j)-lx_i.gp_i.
    # g.raw has the donor volume built in.
    W=g.W
    assert all(np.array_equal(G.indptr,W.indptr) and np.array_equal(G.indices,W.indices) for G in g.raw)
    weight=-g.sumw
    assert np.min(weight)>0
    a=np.einsum("ikl,ik->il",g.C,g.lx)
    diag=np.einsum("il,il->i",a,g.rows)/weight
    off=np.empty_like(W.data)
    for start in range(0,g.n,512):
        end=min(start+512,g.n)
        indices=np.repeat(np.arange(start,end),np.diff(W.indptr[start:end+1]))
        sl=slice(W.indptr[start],W.indptr[end])
        correction=sum(a[indices,k]*g.raw[k].data[sl] for k in range(3))
        off[sl]=(-W.data[sl]-correction)/weight[indices]
    full=sparse.csr_matrix((off,W.indices,W.indptr),shape=W.shape)+sparse.diags(diag)
    active=np.flatnonzero(g.shell<19)
    active_donors=full[active]
    return active,active_donors,active_donors[:,active].tocsr(),diag,weight


def extrema(values):
    return dict(min=float(min(values)),max=float(max(values)))


def check_rows(A):
    rows=A@np.ones(A.shape[1])
    off=A.copy()
    off.setdiag(0)
    off.eliminate_zeros()
    return dict(nnz=A.nnz,entries=extrema(A.data),row_sums=extrema(rows),
                negative=int(np.count_nonzero(A.data<0)),robust_negative_lt_minus1e_14=int(np.sum(A.data < -1e-14)),
                negative_offdiagonal=int(np.sum(off.data<0)),negative_diagonal=int(np.sum(A.diagonal()<0)),
                rows_with_negative_sum_terms=int(np.count_nonzero((abs(A)@np.ones(A.shape[1])-rows)>1e-13)),
                robust_positive_gt_1e_14=int(np.sum(A.data>1e-14)),
                abs_row_sum=extrema(abs(A)@np.ones(A.shape[1])),
                asymmetry_max=float(np.max(abs((A-A.T).data))))


def geometric_bounds(A):
    # Entrywise absolute values make an induced-norm bound even for a non-normal map.
    aa=abs(A); row=np.ones(A.shape[0]);col=row.copy();bounds=[]
    for k in (1,2,3):
        row=aa@row
        col=aa.T@col
        bounds.append(dict(round=k,linf_upper=float(row.max()),l1_upper=float(col.max()),
                           l2_upper=float(np.sqrt(row.max()*col.max()))))
    return bounds


def probe(A,z):
    original=z.copy()
    l2=np.linalg.norm(original);sup=max(abs(original))
    rows=[]
    for k in (1,2,3):
        z=A@z
        rows.append(dict(round=k,l2_gain=float(np.linalg.norm(z)/l2),linf_gain=float(max(abs(z))/sup)))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    receipt=T/"logs"/(TAG+".json")
    if args.write and receipt.exists():
        raise FileExistsError(receipt)
    g=Graph()
    active,M,A,diag,weight=iteration(g)
    assert len(active)==32020
    fs=g.shell==19
    assert np.sum(fs)==5153
    # Verify all unrestricted unknown rows against the separately coded pressure and gradient path.
    rng=np.random.default_rng(20261120)
    field=np.column_stack([np.ones(g.n),g.x/DP,rng.normal(size=g.n)])
    gradient=g.grad(field)
    lp=g.sumw[:,None]*field-g.W@field
    lap=lp-sum(gradient[k]*g.lx[:,k,None] for k in range(3))
    direct=(field+lap/weight[:,None])[active]
    eps=float(np.max(abs(M@field-direct)))
    affine=float(np.max(abs((M@field-field[active])[:,:4])))
    assert eps<1e-10 and affine<1e-10

    shell=g.shell[active];x=g.x[active]
    fields={"alternating_material_shell":np.where(shell%2,1.,-1.),
            "cartesian_three_axis_cos_pi_per_dp":np.cos(np.pi*x/DP).prod(axis=1),
            "id_parity":np.where((active+8)%2,1.,-1.),
            "random_rademacher_seed_20261120":np.random.default_rng(20261120).choice([-1.,1.],size=len(x))}
    top=np.zeros(len(active));lookup={int(k+8):i for i,k in enumerate(active)}
    path=T/"figures/cryer_tet_darcy_spectrum_r1_high_mode.csv"
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            top[lookup[int(row["native_id"])]]=float(row["pressure_mode_unit_max"])
    assert np.count_nonzero(top)==8
    fields["tet_eight_archived_pressure_entries_with_all_others_zero"]=top
    probes={name:probe(A,z) for name,z in fields.items()}
    z=np.full(len(active),10000.);opening=[]
    for k in (1,2,3):
        z=A@z
        j=int(np.argmax(z))
        opening.append(dict(round=k,min_Pa=float(min(z)),max_Pa=float(z[j]),max_native_id=int(active[j]+8),
                            above_10000_plus1e_8Pa=int(np.sum(z>10000+1e-8)),below_min1e_8Pa=int(np.sum(z< -1e-8))))

    stats=check_rows(A)
    bounds=geometric_bounds(A)
    with (T/"logs/cryer_tet_darcy_spectrum_r1.check.json").open() as f:
        tet=json.load(f)
    report=dict(tag=TAG,stage="frozen reference geometry, pressure-only original P3 Eq40 row split",
                source=SPH_SOURCE,round=PREP_SOURCE,points=g.n,free=len(active),surface=int(sum(fs)),
                material_volume_m3=g.volume,unscaled_S_over_k=extrema(weight[active]),
                full_L_diagonal_over_sumw=extrema(1-diag[active]),
                update_diagonal=extrema(diag[active]),
                direct_independent_row_action_max_error=eps,affine_reproduction_error=affine,
                row_sum_all_donors=extrema(M@np.ones(g.n)),open_matrix=stats,
                induced_norm_upper= bounds,probe_gains=probes,uniform_10kPa_open=opening,
                retained_tetrahedral_normalized_high_mode_gains=tet["direct_three_sweep_normalized_mode_norms"],
                scope=["Frozen original positions and their double-precision Graph kernel reconstruction; no native GPU bit identity.",
                       "Only interior rows. Surface prescribed zero. Closed Neumann surface rows are not involved.",
                       "Solid, acceleration, three-round mechanical recomputation, dt and time extrapolation excluded.",
                       "Probe ratios are not spectral bounds. Norm bounds use absolute matrix powers; no eigensolve.",
                       "Tet check used full pressure stiffness diagonal and its energy-weighted norm. Eight archived entries do not reconstruct its full eigenvector."])
    if args.write:
        with receipt.open("x") as f:
            json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps(report))


if __name__=="__main__":
    main()
