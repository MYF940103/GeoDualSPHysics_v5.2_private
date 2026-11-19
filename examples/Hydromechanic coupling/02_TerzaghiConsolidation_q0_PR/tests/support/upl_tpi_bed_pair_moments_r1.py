"""Geometry-only shared-edge correction on the first four material layers of C02."""
import os
for key in ("MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key]="1"

import json
import numpy as np
import pandas as pd
from scipy.linalg import lstsq

from upl_tpi_bottom_patch_r1 import DATA, FIG, TEST, Q0, PERIOD, Bed, dx_periodic, ordered, read, require

TAG="upl_tpi_bed_pair_moments_r1"


def solve(bed,state,layer,mode,replay=False):
    zone=(layer>=0)&(layer<4)
    members=np.flatnonzero(zone)
    local=np.full(1040,-1)
    local[members]=np.arange(len(members))
    pos=state["Posd"]
    x,z=pos[:,0],pos[:,2]
    vol=state["PoroVolumeRatio"]*bed.v0
    ii,jj=np.triu_indices(1040,1)
    dx,dz=dx_periodic(x[ii]-x[jj]), z[ii]-z[jj]
    r=np.hypot(dx,dz)
    keep=(r<2*bed.h)&(r>0.)&((ii>=40)|(jj>=40))
    i,j,dx,dz,r=[v[keep] for v in (ii,jj,dx,dz,r)]
    F=-2.7852/bed.h**4*(1.-r/(2*bed.h))**3
    g=np.stack((F*dx,F*dz),axis=1)
    # Use a geometry-derived bulk normalization for comparison. It uses the actual interior
    # z moment, evaluated without stress data. The same multiplier acts on both sides of each edge.
    if mode=="bulk-normalized":
        m=np.bincount(i,-vol[j]*F*dz*dz,minlength=1040)+np.bincount(j,-vol[i]*F*dz*dz,minlength=1040)
        normalization=1./m[layer==49].mean()
    elif mode=="raw":
        normalization=1.
    else:
        raise ValueError(mode)
    g*=normalization
    live=((zone[i]&zone[j]) | (zone[i]&(j<40)) | (zone[j]&(i<40)))
    variable=np.full(len(i),-1);variable[live]=np.arange(live.sum())
    full=np.zeros((len(members),5)); matrix=np.zeros((len(members),5,int(live.sum())))
    # Dimensionless constraints per receiver: h*sum(V_j grad W)=0 and
    # sum(V_j grad W (x_j-x_i)^T)=I. The two off-diagonals coincide for radial weights.
    for a,b,sign in ((i,j,1.),(j,i,-1.)):
        terms=np.stack((sign*bed.h*g[:,0],sign*bed.h*g[:,1],-g[:,0]*dx,-g[:,0]*dz,-g[:,1]*dz),axis=1)*vol[b,None]
        present=zone[a]
        np.add.at(full,local[a[present]],terms[present])
        change=present & live
        matrix[local[a[change]],:,variable[change]]=terms[change]
    target=np.broadcast_to([0.,0.,1.,0.,1.],full.shape)
    M=matrix.reshape(len(members)*5,-1)
    rhs=(target-full).ravel()
    # Minimum Euclidean change from unit pair weights; no reference pressure, stress,
    # known load or time-history error enters this solve. Do not clip negative weights.
    delta,_,rank,svals=lstsq(M,rhs,cond=1e-12,lapack_driver="gelsd")
    coeff=np.ones(len(i));coeff[live]+=delta
    resid=(M@delta-rhs).reshape(-1,5)
    # Independent assembly in forces (not reusing the design matrix).
    def scatter(edge):
        return np.bincount(i,edge,minlength=1040)-np.bincount(j,edge,minlength=1040)
    def traction(edge,level):
        foo=(layer[i]>=level)&(layer[j]<level); bar=(layer[j]>=level)&(layer[i]<level)
        return float((edge[foo].sum()-edge[bar].sum())/PERIOD)
    def force(c):
        area=(vol[i]*vol[j]*c)[:,None]*g
        Fz=-2*Q0*area[:,1]
        rho=1000.+(bed.rho0-1000.)/state["PoroVolumeRatio"]
        norm_x,norm_z=scatter(-2*Q0*area[:,0])/(rho*vol),scatter(Fz)/(rho*vol)
        moment=[(np.bincount(i,-area[:,u]*d,minlength=1040)
                 +np.bincount(j,-area[:,u]*d,minlength=1040))/vol
                 for u,d in ((0,dx),(0,dz),(1,dx),(1,dz))]
        # To test a locally affine symmetric stress field, only its value and derivatives at the
        # receiver are required, so wrapping x does not introduce a nonperiodic seam.
        grad_error=max(np.max(abs(m[zone]-tar)) for m,tar in zip(moment,(1.,0.,0.,1.)))
        return (norm_x,norm_z,grad_error,traction(Fz,0),traction(Fz,4),float(scatter(Fz).sum()))
    before=force(np.ones(len(i)));after=force(coeff)
    outside=(layer>=4)
    require(np.array_equal(before[0][outside],after[0][outside]) and np.array_equal(before[1][outside],after[1][outside]),"Nonlocal force change")
    require(abs(before[4]-after[4])<1e-9,"Outer-cut traction changed through local correction")
    if replay:
        require(rank==len(M) and np.max(abs(resid))<1e-12,"Inconsistent geometric moments")
        require(np.all(coeff[live]>0),"Observed edge weight lost positivity")
        require(after[2]<1e-12 and np.max(np.hypot(after[0][zone],after[1][zone]))<1e-8,
                "Constant or linear test field failed")
        return i,j,g,vol,coeff,normalization
    return dict(bulk=mode,normalization=float(normalization),variable_edges=int(live.sum()),
        matrix_rank=int(rank),rows=len(M),smallest_retained_singular_value=float(svals[rank-1]),
        min_coefficient=float(coeff[live].min()),max_coefficient=float(coeff[live].max()),
        max_abs_dimensionless_residual=float(np.abs(resid).max()),
        initial_max_uniform_accel_m_s2=float(np.hypot(before[0][zone],before[1][zone]).max()),
        final_max_uniform_accel_m_s2=float(np.hypot(after[0][zone],after[1][zone]).max()),
        initial_max_affine_error=before[2],final_max_affine_error=after[2],
        initial_bed_traction_Pa=before[3],final_bed_traction_Pa=after[3],
        final_outer_cut_traction_Pa=after[4],sum_closed_material_wall_force=after[5],
        outside_rows_bit_equal=True,all_coefficients_positive=bool(np.all(coeff[live]>0.)))


def main():
    paths=[FIG/(TAG+".csv"),TEST/"logs"/(TAG+".check.json")]
    require(not any(p.exists() for p in paths),"Preserve the existing review")
    b=Bed(read(DATA/"Part_0000.bi4"))
    layer=np.rint(b.z/.01-.5).astype(int)
    hist=pd.read_csv(TEST.parent/"figures/upl_tpi_p3_full_diagnostic_r1/history.csv",float_precision="round_trip")
    first=int(hist.loc[hist.stress_guard_failed,"part"].iloc[0])
    parts=[0,int((hist.time_s-2).abs().idxmin()),first-1,first,1652]
    result=[]
    for part in parts:
        frame=read(DATA/f"Part_{part:04d}.bi4")
        a=ordered(frame);t=float(frame["part"]["values"]["TimeStep"])
        require(t==hist.time_s.iloc[part],"Clock mismatch")
        for mode in ("raw","bulk-normalized"):
            result.append(dict(part=part,time_s=t,**solve(b,a,layer,mode)))
    pd.DataFrame(result).to_csv(paths[0],index=False)
    paths[1].write_text(json.dumps(dict(frozen_only=True,formal_physical_acceptance=False,rows=result),
                                   indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
