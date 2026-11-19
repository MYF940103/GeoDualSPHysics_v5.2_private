"""Screen one fixed, mass-preserving interior radial staggering on the actual Cryer sphere."""
import json
import argparse
from cryer_shell_equilibrium import TESTS, NATIVE, SOIL, need, write
from cryer_shell_gradient import H, DP, AMPLITUDE
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

TAG="cryer_shell_stagger_r1"


def stagger(x, shell, ids, volumes):
    out=x.copy()
    for j in range(2,17):
        use=shell==j
        radial=x[use]/np.linalg.norm(x[use],axis=1)[:,None]
        # A fixed deterministic phase per material ID avoids choosing an axis or
        # fitting to pressure. Remove the shell mean and three first moments.
        seed=np.cos(np.mod(ids[use]*((np.sqrt(5)-1)/2),1.)*2*np.pi)
        modes=np.column_stack((np.ones(len(radial)),radial))
        w=np.sqrt(volumes[use])
        coeff=np.linalg.lstsq(w[:,None]*modes,w*seed,rcond=None)[0]
        dr=seed-modes@coeff
        dr*=.25*DP/np.max(abs(dr))
        out[use]+=dr[:,None]*radial
        need(abs(np.average(dr,weights=w*w))<1e-16 and
             np.max(abs(np.average(out[use]-x[use],axis=0,weights=w*w)))<1e-16,
             "Per-shell volume-weighted mean radius or centroid changed")
    need(np.array_equal(out[(shell==1)|(shell>=17)],x[(shell==1)|(shell>=17)]),
         "Protected center or 2H exterior band changed")
    return out


def screen(label,x,shell,volumes,h=H):
    selected=np.flatnonzero(shell<=10)
    r=np.linalg.norm(x,axis=1)
    tree=cKDTree(x)
    nn=tree.query(x,k=2)[0][:,1]
    near=tree.query_ball_point(x[selected],2*h)
    waves={"affine":0.,"smooth":np.pi/(8*DP),"alternating":np.pi/DP}
    uw={};targets={};est={}
    for name,k in waves.items():
        z=k*r
        uw[name]=AMPLITUDE*np.cos(z)[:,None]*x
        targets[name]=AMPLITUDE*(3*np.cos(z[selected])-z[selected]*np.sin(z[selected]))
        est[name]=np.zeros(len(selected))
    worst_cond=0.
    for l,(i,jn) in enumerate(zip(selected,near)):
        j=np.array(jn);j=j[j!=i]
        d=x[j]-x[i]
        weighted=volumes[j,None]*np.maximum(1-np.linalg.norm(d,axis=1)/(2*h),0)[:,None]**3*d
        m=d.T@weighted
        worst_cond=max(worst_cond,np.linalg.cond(m))
        basis=weighted@np.linalg.inv(m)
        for name,u in uw.items():
            est[name][l]=np.einsum("ij,ij->",u[j]-u[i],basis)
    rows=[]
    for name in waves:
        for region,mask in (("center18",shell[selected]==1),("inner5121",shell[selected]<=10)):
            truth=targets[name][mask]; fitted=est[name][mask]
            rows.append(dict(layout=label,field=name,region=region,count=int(mask.sum()),
                projection=float(fitted@truth/(truth@truth)),
                normalized_RMS=float(np.linalg.norm(fitted-truth)/np.linalg.norm(truth)),
                moment_condition_max=float(worst_cond),all_soil_min_nearest_over_dp=float(nn.min()/DP),
                all_soil_p01_nearest_over_dp=float(np.quantile(nn,.01)/DP)))
    return rows


def main(h15_only=False):
    csvpath=TESTS/"figures"/(TAG+".csv")
    log=TESTS/"logs"/(TAG+".check.json")
    ids=pd.read_csv(NATIVE/"native_ids.csv",float_precision="round_trip").iloc[SOIL]
    x=ids[["x0","y0","z0"]].to_numpy()
    shell=np.rint(ids.r0_m.to_numpy()/DP).astype(int)
    v=ids.initial_native_volume_m3.to_numpy()
    if h15_only:
        target=TESTS/"figures/cryer_shell_h15_r1.csv"
        need(not target.exists(),"Preserve previous support test")
        write(target,screen("same_positions_h1p5",x,shell,v,1.5*DP))
        return
    need(not csvpath.exists() and not log.exists(),"Preserve previous test")
    candidate=stagger(x,shell,ids.id.to_numpy(),v)
    rows=screen("current",x,shell,v)+screen("interior_stagger",candidate,shell,v)
    base=pd.read_csv(TESTS/"figures/cryer_shell_gradient_r1.csv").iloc[0]
    for rec in rows:
        if rec["layout"]=="current" and rec["region"]=="inner5121":
            need(abs(rec["projection"]-base[rec["field"]+"_response_projection"])<1e-12,"Current field control")
    write(csvpath,rows)
    with log.open("x",encoding="utf8") as f:
        json.dump(dict(dp=DP,h=H,changed_ids=int(np.sum(np.any(candidate!=x,axis=1))),
            preserved_center_ids=18,fixed_outer_shells=[17,18,19,20],
            max_displacement_over_dp=float(np.linalg.norm(candidate-x,axis=1).max()/DP),
            scope="Manufactured gradient and geometry only; no solver or seeded input was changed.",
            observations=rows),f,indent=2,allow_nan=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--h15-only",action="store_true")
    main(ap.parse_args().h15_only)
