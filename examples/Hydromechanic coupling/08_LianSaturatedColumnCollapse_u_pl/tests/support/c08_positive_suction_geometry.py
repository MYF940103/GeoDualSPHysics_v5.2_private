"""Late positive-only C08 toe support against same-frame local controls and native PosDiv."""
import argparse
import csv
import json

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

from c08_h18_wend_partial_review_r1 import kernel
from c08_positive_suction_sites import DP, H, OUT, RUNS, checked
from c08_psi25_tpi_native import PRE, SOIL_IDS, TESTS, native, require


def geom(a):
    pos=a["Posd"][:,[0,2]]
    n=len(SOIL_IDS)
    fix=len(pos)-n
    xyz=pos[fix:]
    native_v=a["PoroCurrentVolume"]
    v=float(np.float32(3.316))/2072.5*a["PoroVolumeRatio"]
    require(np.allclose(native_v[fix:],v[fix:],rtol=1e-12,atol=0), "Changed soil ledger volumes")
    # Directed soil rows from symmetric all-particle neighbor pairs, skipping self.
    left,right=cKDTree(pos).query_pairs(2*H,output_type="ndarray").T
    dst=np.r_[left[left>=fix],right[right>=fix]]-fix
    src=np.r_[right[left>=fix],left[right>=fix]]
    dr=pos[src]-xyz[dst]
    r2=np.einsum("ij,ij->i",dr,dr)
    _,fac=kernel(r2,H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
    weight=v[src]*(-fac)
    soil=src>=fix
    def moment(sub):
        r,w,idx=dr[sub],weight[sub],dst[sub]
        xx=np.bincount(idx,weights=r[:,0]**2*w,minlength=n)
        zz=np.bincount(idx,weights=r[:,1]**2*w,minlength=n)
        xz=np.bincount(idx,weights=r[:,0]*r[:,1]*w,minlength=n)
        trace=xx+zz
        delta=np.hypot(xx-zz,2*xz)
        require(np.all(trace>0) and np.all(trace>=delta-1e-10), "Indefinite direction matrix")
        return (trace-delta)/(trace+delta),trace
    both,trace=moment(slice(None))
    soil_ratio,_=moment(soil)
    nn=cKDTree(xyz).query(xyz,k=2)[0][:,1]/DP
    fs=np.isin(a["FSType"][fix:],[2,3])
    fdist=cKDTree(xyz[fs]).query(xyz)[0]
    wall=np.bincount(dst[~soil],minlength=n)
    return dict(nn=nn,nn_over_local=nn/np.sqrt(a["PoroVolumeRatio"][fix:]),
                soil_n=np.bincount(dst[soil],minlength=n),wall_n=wall,
                all_ratio=both,soil_ratio=soil_ratio,trace=trace,fs_dist=fdist)


def match(xz,fs,g,kappa,p,plastic_match):
    # Matching uses geometry and boundary classes, never the outputs being assessed.
    deep=np.flatnonzero((p<-20)&(fs==0))
    ctrl=np.flatnonzero((p>=-20)&(fs==0))
    if not len(deep): return deep,deep
    # Candidate is local to the toe: horizontal separation <= 0.5 m; vertical <= 1 dp.
    ctrl=ctrl[(xz[ctrl,0]>=xz[deep,0].min()-.5)&(xz[ctrl,0]<=xz[deep,0].max()+.5)]
    dx=abs(xz[deep,0,None]-xz[None,ctrl,0])
    dz=abs(xz[deep,1,None]-xz[None,ctrl,1])
    ok=(dx<=.5)&(dz<=DP)
    for cls in (g["wall_n"]>0,g["fs_dist"]<2*H):
        ok &= cls[deep,None]==cls[None,ctrl]
    if plastic_match:
        high=(kappa>0)&(kappa>=np.quantile(kappa,.90))
        ok &= high[deep,None]==high[None,ctrl]
    # Lexicographic goal: maximize number of distinct pairs first, minimize position cost second.
    cost=(dx/.5)**2+(dz/DP)**2
    unmatched=3.*(1+len(deep))
    all_cost=np.c_[np.where(ok,cost,3*unmatched),np.full((len(deep),len(deep)),unmatched)]
    ii,jj=linear_sum_assignment(all_cost)
    valid=jj<len(ctrl)
    ii,jj=ii[valid],jj[valid]
    require(np.all(ok[ii,jj]),"Mismatched support strata")
    return deep[ii],ctrl[jj]


def close_pairs():
    """Identify physical pairs behind the unmatched short distances; keep both material histories."""
    tag=RUNS["beta004"]
    receipt=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Unexpected run")
    _,initial=native(PRE.with_name("Part_0000.bi4"))
    origin=initial["Posd"][-len(SOIL_IDS):][:,[0,2]]
    pairs={}
    for part in range(72,133):
        m,a,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",receipt)
        sl=slice(-len(SOIL_IDS),None)
        pos=a["Posd"][sl][:,[0,2]]
        p=a["PorePress"][sl].astype(float)/1000
        fs=a["FSType"][sl]
        nearest,ix=cKDTree(pos).query(pos,k=2)
        focal=np.flatnonzero((fs==0)&(p<-20)&(nearest[:,1]<DP*.5))
        if not len(focal):
            continue
        fsd=cKDTree(pos[np.isin(fs,[2,3])]).query(pos[focal])[0]
        wd=cKDTree(a["Posd"][:-len(SOIL_IDS)][:,[0,2]]).query(pos[focal])[0]
        tau=m["TimeStep"]-receipt["release_time_s"]
        for k,i in enumerate(focal):
            j=ix[i,1]
            lo,hi=sorted((int(i),int(j)))
            row=pairs.setdefault((lo,hi),dict(id1=int(SOIL_IDS[lo]),id2=int(SOIL_IDS[hi]),
                                    initial_separation_dp=np.linalg.norm(origin[lo]-origin[hi])/DP,
                                    first_tau_s=tau,last_tau_s=tau,focal_samples=0,distinct_frames=0,
                                    near_fs_samples=0,wall_in_support_samples=0,min_nn_dp=np.inf,
                                    lowest_focal_pressure_kPa=np.inf,last_part=-1))
            row["focal_samples"]+=1
            row["distinct_frames"]+=int(row["last_part"]!=part)
            row["last_part"]=part
            row["last_tau_s"]=tau
            row["near_fs_samples"]+=int(fsd[k]<2*H)
            row["wall_in_support_samples"]+=int(wd[k]<2*H)
            row["lowest_focal_pressure_kPa"]=min(row["lowest_focal_pressure_kPa"],p[i])
            if nearest[i,1]/DP<row["min_nn_dp"]:
                row.update(min_nn_dp=nearest[i,1]/DP,closest_tau_s=tau,p1_at_closest_kPa=p[lo],
                           p2_at_closest_kPa=p[hi],x_at_closest_m=pos[i,0],z_at_closest_m=pos[i,1])
    with (OUT/"support_coverage.csv").open(encoding="utf8") as stream:
        expected=sum(int(r["nn_lt_half_dp"]) for r in csv.DictReader(stream) if r["group"]=="all_deep_internal")
    require(expected==sum(r["focal_samples"] for r in pairs.values()), "Unequal number of short-neighbor events")
    both=sorted(pairs.values(),key=lambda r:r["min_nn_dp"])
    for r in both: del r["last_part"]
    with (OUT/"closest_material_pairs.csv").open("x",encoding="utf8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=both[0])
        writer.writeheader()
        writer.writerows(both)


def affine_donors(xz,vol,tree,i,j,one_side):
    """Reference cloud of soil IDs; omit i,j and look outward from i for the one-sided fit."""
    ids=np.asarray(tree.query_ball_point(xz[i],2*H),int)
    ids=ids[(ids!=i)&(ids!=j)]
    d=xz[ids]-xz[i]
    if one_side:
        outward=(d@(xz[j]-xz[i]))<=1e-14*DP**2
        ids,d=ids[outward],d[outward]
    r2=np.sum(d*d,axis=1)
    _,fac=kernel(r2,H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
    w=(-fac)*vol[ids]
    good=w>0
    ids,d,w=ids[good],d[good],w[good]
    if not len(ids): return ids,d,w,0.,np.inf
    w=w/w.sum()
    moment=(d.T*w)@d
    return ids,d,w,1/(w@w),np.linalg.cond(moment)


def affine_predict(x0,x1,i,j,donors):
    ids,d,w,neff,cond=donors
    limits=dict(n=len(ids),effective_n=neff,condition=cond)
    if len(ids)<6 or neff<4 or cond>20:
        return dict(limits,valid=0,gap_dp="",vector_error_per_ref_gap="",donor_residual_dp="")
    y=x1[ids]-x1[i]
    F=np.linalg.solve((d.T*w)@d,(d.T*w)@y)
    pair=x0[j]-x0[i]
    predicted=pair@F
    residual=y-d@F
    return dict(limits,valid=1,gap_dp=np.linalg.norm(predicted)/DP,
                vector_error_per_ref_gap=np.linalg.norm(predicted-(x1[j]-x1[i]))/np.linalg.norm(pair),
                donor_residual_dp=np.sqrt(w@np.sum(residual**2,axis=1))/DP)


def affine_history():
    tag=RUNS["beta004"]
    receipt=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Unexpected run")
    parts=[4,*range(71,133)]
    states={}
    interior=np.ones(len(SOIL_IDS),bool)
    for part in parts:
        path=TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4"
        if part==4:
            st=path.stat()
            require([str(path.relative_to(TESTS.parent)),st.st_size,st.st_mtime_ns] in receipt["files"],
                    "Changed last wall-closed frame")
            from c08_psi25_tpi_native import OPEN, read_frame
            m,a,_,_=read_frame(path)
            require(m["Step"]+1==OPEN and not m["GravityPreloadPhase"], "Wrong wall-closed state")
        else:
            m,a,_=checked(path,receipt)
        require(np.array_equal(a["Idp"][-len(SOIL_IDS):], SOIL_IDS),"Wrong material IDs")
        sl=slice(-len(SOIL_IDS),None)
        xz=np.ascontiguousarray(a["Posd"][sl][:,[0,2]])
        fs=np.isin(a["FSType"][sl],[2,3])
        if part>=72:
            fs_dist=cKDTree(xz[fs]).query(xz)[0]
            wall_dist=cKDTree(a["Posd"][:-len(SOIL_IDS)][:,[0,2]]).query(xz)[0]
            interior&=(a["FSType"][sl]==0)&(fs_dist>=2*H)&(wall_dist>=2*H)
        states[part]=(m["TimeStep"]-receipt["release_time_s"],xz,a["PoroCurrentVolume"][sl],cKDTree(xz))
    # Exact affine fixture including rigid translation and shear, with the partner removed.
    square=DP*np.asarray([(i,j) for i in range(-4,5) for j in range(-4,5)],float)
    i,j=40,41
    trial=square@np.array([[1.2,-.35],[.7,.8]])+[.26,-.17]
    for center,other in ((i,j),(j,i)):
        fitted=affine_donors(square,np.full(len(square),DP**2),cKDTree(square),center,other,True)
        res=affine_predict(square,trial,center,other,fitted)
        require(res["valid"] and res["vector_error_per_ref_gap"]<1e-12 and res["donor_residual_dp"]<1e-12,
                "Manufactured two-sided test of local affine prediction failed")
    _,source=native(PRE.with_name("Part_0000.bi4"))
    origin=source["Posd"][-len(SOIL_IDS):][:,[0,2]]
    vertical=np.all(np.isclose(np.diff(origin,axis=0),[0.,DP],atol=1e-8,rtol=0),axis=1)
    eligible=np.flatnonzero(vertical&interior[:-1]&interior[1:])
    pairs=[]
    with (OUT/"closest_material_pairs.csv").open(encoding="utf8") as f:
        for r in csv.DictReader(f):
            pairs.append(("short_pair",int(r["id1"])-int(SOIL_IDS[0]),int(r["id2"])-int(SOIL_IDS[0])))
    short=list(pairs)
    require(len(short)==3,"Expected three actual short pairs")
    used={s for _,i,j in short for s in (i,j)}
    x60=states[72][1]
    controls=[]
    for _,i,j in short:
        mid=(x60[i]+x60[j])/2
        rank=np.argsort(np.linalg.norm((x60[eligible]+x60[eligible+1])/2-mid,axis=1),kind="stable")
        for k in eligible[rank]:
            candidate_mid=(x60[k]+x60[k+1])/2
            if k in used or k+1 in used or any(np.linalg.norm(candidate_mid-z)<2*DP for z in controls):
                continue
            pairs.append(("deep_control_for_"+str(int(SOIL_IDS[i])),k,k+1))
            used.update((k,k+1))
            controls.append(candidate_mid)
            break
    require(len(pairs)==6, "Missing continuously deep, initially adjacent control")
    from functools import lru_cache
    @lru_cache(None)
    def fits(ref,i,j,one_side):
        _,xref,volume,tree=states[ref]
        return affine_donors(xref,volume,tree,i,j,one_side)
    rows=[]
    for part in range(72,133):
        tau,x,_,_=states[part]
        for role,i,j in pairs:
            for rname,ref in (("wall_release",4),("t0p60",72),("previous_saved",part-1)):
                rt,xr,_,_=states[ref]
                row=dict(part=part,tau_s=tau,ref=rname,ref_tau_s=rt,role=role,
                         id1=int(SOIL_IDS[i]),id2=int(SOIL_IDS[j]),ref_gap_dp=np.linalg.norm(xr[j]-xr[i])/DP,
                         actual_gap_dp=np.linalg.norm(x[j]-x[i])/DP)
                for name,idx,other in (("a",i,j),("b",j,i)):
                    one=affine_predict(xr,x,idx,other,fits(ref,idx,other,True))
                    row.update({name+"_"+k:v for k,v in one.items()})
                    whole=affine_predict(xr,x,idx,other,fits(ref,idx,other,False))
                    row.update({name+"_full_"+k:whole[k] for k in ("n","condition","valid","gap_dp","donor_residual_dp")})
                rows.append(row)
    with (OUT/"pair_affine_history.csv").open("x",encoding="utf8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def run(coverage=False):
    tag=RUNS["beta004"]
    receipt=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Unexpected run")
    rows=[]
    for part in range(72,133):
        m,a,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",receipt)
        sl=slice(-len(SOIL_IDS),None)
        p=a["PorePress"][sl].astype(float)/1000
        xz=a["Posd"][sl][:,[0,2]]
        fs=a["FSType"][sl]
        kappa=a["Kplastic"][sl]
        g=geom(a)
        err=abs(g["trace"]-a["PosDiv"][sl])
        require(err.max()<.001,"Frozen geometric trace differs from saved PosDiv")
        if coverage:
            # Quantify all omitted deep internal sites, not just the majority with a local control.
            inside=np.flatnonzero((p<-20)&(fs==0))
            matched,_=match(xz,fs,g,kappa,p,True)
            unmatched=np.setdiff1d(inside,matched)
            for label,indices in (("all_deep_internal",inside),("unmatched",unmatched)):
                if not len(indices):
                    continue
                nn=g["nn"][indices]
                ratio=g["all_ratio"][indices]
                row=dict(part=part,step=m["Step"]+1,tau_s=m["TimeStep"]-receipt["release_time_s"],
                         group=label,count=len(indices),nn_lt_half_dp=int((nn<.5).sum()),nn_min=nn.min(),
                         nn_median=np.median(nn),ratio_min=ratio.min(),ratio_median=np.median(ratio),
                         n_all_min=int((g["soil_n"][indices]+g["wall_n"][indices]).min()),
                         near_wall=int(np.sum(g["wall_n"][indices]>0)),
                         near_fs=int(np.sum(g["fs_dist"][indices]<2*H)))
                if label=="all_deep_internal" and part==100:
                    i=int(np.argmin(p))
                    require(int(SOIL_IDS[i])==6918, "Deepest saved point changed")
                    row.update(peak_id=int(SOIL_IDS[i]),peak_p_kPa=p[i],
                               peak_matched=int(i in matched),peak_fs_dist_dp=g["fs_dist"][i]/DP)
                    for key in ("nn","soil_n","wall_n","all_ratio","soil_ratio","trace"):
                        row["peak_"+key]=g[key][i]
                rows.append(row)
            continue
        for mode in (False,True):
            lo,hi=match(xz,fs,g,kappa,p,mode)
            require(len(lo)>0,"No geometry-matched deep toe pairs in late interval")
            common=dict(part=part,step=m["Step"]+1,tau_s=m["TimeStep"]-receipt["release_time_s"],
                        match="boundary_depth_high_kappa" if mode else "boundary_depth",
                        deep_all=int((p<-20).sum()),deep_internal=int(((p<-20)&(fs==0)).sum()),
                        matched=len(lo),median_dz_dp=np.median(abs(xz[lo,1]-xz[hi,1]))/DP,
                        median_dx_m=np.median(abs(xz[lo,0]-xz[hi,0])),max_trace_error=err.max())
            for group,rowsel in (("deep",lo),("control",hi)):
                nn=g["nn"][rowsel]
                n_soil=g["soil_n"][rowsel]
                n_wall=g["wall_n"][rowsel]
                vals=dict(nn_dp=nn,nn_local=g["nn_over_local"][rowsel],n_soil=n_soil,n_all=n_soil+n_wall,
                          both_ratio=g["all_ratio"][rowsel],soil_ratio=g["soil_ratio"][rowsel],
                          trace=g["trace"][rowsel],J=a["PoroVolumeRatio"][sl][rowsel],kappa=kappa[rowsel],
                          p_kPa=p[rowsel])
                rows.append(dict(common,group=group,close_nn_half_dp=int((nn<.5).sum()),
                                 near_wall=int((n_wall>0).sum()),near_fs=int((g["fs_dist"][rowsel]<2*H).sum()),
                                 **{k+"_median":float(np.median(v)) for k,v in vals.items()},
                                 nn_p10=np.quantile(nn,.1),both_ratio_p10=np.quantile(vals["both_ratio"],.1)))
            # Keep the actual lowest material point and the matched local control at the critical frame.
            if part==100:
                i=int(np.argmin(p))
                if i in lo:
                    j=hi[np.flatnonzero(lo==i)[0]]
                    for name,idx in (("lowest_id",i),("paired_id",j)):
                        rows[-2][name]=int(SOIL_IDS[idx])
                        for key in ("nn","soil_n","wall_n","all_ratio","soil_ratio","trace"):
                            rows[-2][name+"_"+key]=g[key][idx]
                        rows[-2][name+"_p_kPa"]=p[idx]
                        rows[-2][name+"_kappa"]=kappa[idx]
    require(abs(rows[0]["tau_s"]-.6)<1e-9 and abs(rows[-1]["tau_s"]-1.2)<1e-9,"Unexpected late window")
    keys=list(dict.fromkeys(k for row in rows for k in row))
    path=OUT/("support_coverage.csv" if coverage else "matched_support.csv")
    with path.open("x",encoding="utf8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--coverage",action="store_true",help="Summarise every deep internal sample, including unmatched")
    group.add_argument("--close-pairs",action="store_true",help="Identify pairs in the coverage table below half dp")
    group.add_argument("--affine-pairs",action="store_true",help="Test whether local deformation predicts pair closure")
    args=parser.parse_args()
    if args.affine_pairs:
        affine_history()
    elif args.close_pairs:
        close_pairs()
    else:
        run(args.coverage)
