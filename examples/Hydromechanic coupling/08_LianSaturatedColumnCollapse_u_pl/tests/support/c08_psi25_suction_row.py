"""Pressure-dependent part of the frozen production row; accelerations/iterates are not saved."""
from functools import lru_cache
import csv
import json
import numpy as np
from scipy.spatial import cKDTree
from c08_psi25_local_suction import FIXED, H, OUT, RUNS, save
from c08_psi25_suction_stencil import GZ, PARTS, TARGET, V0, bed_fits, bed_pressure
from c08_psi25_tpi_native import CASE, TESTS, RELEASE_IDS, read_frame, require
from c08_h18_wend_partial_review_r1 import kernel


def pressure_row(a,i):
    xz=a["Posd"][:,[0,2]]
    vol=V0*a["PoroVolumeRatio"]
    tree=cKDTree(xz)
    def neighbors(idx):
        js=np.asarray(tree.query_ball_point(xz[idx],2*H),dtype=int)
        js=js[js!=idx]
        d=xz[js]-xz[idx]
        rr2=np.sum(d*d,axis=1)
        _,fac=kernel(rr2,H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
        return js,d,rr2,(-fac)[:,None]*d
    @lru_cache(None)
    def soil_moment(idx):
        js,d,_,g=neighbors(idx)
        return (d.T*vol[js])@g
    @lru_cache(None)
    def matrix(idx):
        if idx>=FIXED: return np.linalg.inv(soil_moment(idx))
        for owners,weights,_,_ in bed_fits(a,idx):
            cmat=np.tensordot(weights,[matrix(int(j)) for j in owners],axes=1)
            cmat[0,1]*=-1
            cmat[1,0]*=-1
            if np.linalg.det(cmat)>0: return cmat
        raise ValueError(f"Unresolved frozen bed C, ID {idx}")
    js,d,rr2,g=neighbors(i)
    ci=matrix(i)
    gi=g@ci.T
    gj=np.einsum("ijk,ik->ij",np.array([matrix(int(j)) for j in js]),g)
    eta2=float(np.float32((H*.1)**2))
    w=vol[js]*np.sum((gi+gj)*d,axis=1)/(rr2+eta2)
    grad=vol[js,None]*gi
    ki=a["PoroHydraulicConductivity"][i]
    gjstate=(a["PoroVolumeRatio"][js]-a["PoroVolumeRatio"][i])@grad
    chain=ki/(2*(1-float(np.float32(.35))))*(grad@gjstate)
    is_surface=a["FSType"][i] in (2,3)
    coeff=ki*w+chain
    if not is_surface:
        coeff-=ki*(grad@(w@d))
    dp=a["PorePress"][js].astype(float)-float(a["PorePress"][i])
    term=coeff*dp
    bed=js<FIXED
    diagonal=ki*w.sum()
    gamma=1000*abs(GZ)
    theta=-gamma*a["PoroThetaLastStage"][i]
    posdiv=np.trace(soil_moment(i))
    require(abs(posdiv-float(a["PosDiv"][i]))<.001 and diagonal>0, "Inconsistent saved geometry")
    return dict(fs_type=int(a["FSType"][i]), p_Pa=float(a["PorePress"][i]), S_inv_m_s=diagonal,
                beta_over_dtS=(.04/5e-6)/diagonal, posdiv_native=float(a["PosDiv"][i]),
                posdiv_frozen=posdiv, theta_source=theta, pressure_soil=term[~bed].sum(),
                pressure_wall=term[bed].sum(),pressure_total=term.sum(),
                pressure_804=term[js==804].sum(), coefficient_804=coeff[js==804].sum(),
                in_support_804=int(np.any(js==804)), effective_negative_weights=int((coeff<0).sum()))


if __name__=="__main__":
    with (OUT/"bed_extrapolation.csv").open() as f:
        retained=list(csv.DictReader(f))
    rows=[]
    for label in ("positive_only","all_zero"):
        tag=RUNS[label]
        rec=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
        for part in PARTS:
            path=TESTS/"outputs"/tag/"data"/f"Part_{part:04}.bi4"
            stat=path.stat()
            require(rec["passed"] and [str(path.relative_to(CASE)),stat.st_size,stat.st_mtime_ns] in rec["files"],"Changed input")
            m,a,_,_=read_frame(path)
            require(np.array_equal(a["Idp"],RELEASE_IDS),"Wrong owners")
            for ref in retained:
                if ref["run"]==label and int(ref["part"])==part:
                    wi=int(ref["wall_id"])
                    replay=bed_pressure(a,wi)
                    require(abs(replay["frozen_fit_kPa"]-float(ref["frozen_fit_kPa"]))<1e-9
                            and replay["fit_attempt"]==int(ref["fit_attempt"]), "Changed bed replay")
            i=int(np.searchsorted(a["Idp"],TARGET))
            rows.append(dict(run=label,part=part,step=m["Step"]+1,time_s=m["TimeStep"],
                             tau_s=m["TimeStep"]-rec["release_time_s"],id=TARGET,**pressure_row(a,i)))
    save("frozen_production_row.csv",rows)
