"""Locate pressure minima in the two retained positive-only TPI policies on actual saved frames."""
import csv
import json

import numpy as np
from scipy.spatial import cKDTree

from c08_psi25_tpi_native import CASE, PRE, RELEASE_IDS, SOIL_IDS, TESTS, native, read_frame, require


DP = .04
H = float(np.float32(.072))
RUNS = {"beta004":"c08_psi25_tpi_paper_b004_r1","beta0":"c08_psi25_tpi_paper_b0_r1"}
OUT = TESTS/"figures/c08_positive_suction"


def checked(path, receipt):
    st = path.stat()
    require([str(path.relative_to(CASE)),st.st_size,st.st_mtime_ns] in receipt["files"],
            "Changed native data: "+str(path))
    m,a,h,prev = read_frame(path)
    require(m["TimeStep"]==h["SavedTime"] and h["CompletedUpdates"]==m["Step"]+1 and
            np.array_equal(a["Idp"],RELEASE_IDS), "Unexpected native clock or owners")
    return m,a,prev


def select_materials(arrays, target_id):
    xyz=arrays["Posd"][-5000:][:,[0,2]]
    kappa=arrays["Kplastic"][-5000:]
    fs=arrays["FSType"][-5000:]
    tree=cKDTree(xyz)
    nn=tree.query(xyz,k=2)[0][:,1]/DP
    i=int(np.searchsorted(SOIL_IDS,target_id))
    # Closest current material of comparable depth/spacing with lower plastic strain.
    # Pressure does not enter the control selection once the peak reference is fixed.
    elig=(fs==fs[i])&(kappa<.5*kappa[i])
    controls=np.flatnonzero(elig)
    require(len(controls)>=2,"Not enough low-kappa depth/spacing matches")
    score=((xyz[controls,1]-xyz[i,1])/DP)**2+((nn[controls]-nn[i])/.05)**2
    score+=((xyz[controls,0]-xyz[i,0])/(5*DP))**2
    order=np.argsort(score,kind="stable")
    neigh=tree.query(xyz[i],k=3)[1][1:]
    targets={int(SOIL_IDS[j]):"nearest_at_peak" for j in neigh}
    targets.update({int(SOIL_IDS[j]):"depth_spacing_match_low_kappa" for j in controls[order[:2]]})
    targets.update({7010:"original_right_toe", 7012:"original_right", 7018:"right_neighbor",
                    6920:"adjacent_material_min_at_0.85", 6916:"earlier_material_min",int(target_id):"global_min"})
    return targets, [int(v) for v in SOIL_IDS[controls[order[:2]]]], [int(v) for v in SOIL_IDS[neigh]]


def summarize(mask,p,J,kappa,theta,fs,nn):
    count=int(mask.sum())
    if not count: return None
    return dict(n=count, negative=int(np.sum(p[mask]<0)),below10=int(np.sum(p[mask]<-10)),
                below20=int(np.sum(p[mask]<-20)),p_min_kPa=p[mask].min(),
                p01_kPa=np.percentile(p[mask],1),p05_kPa=np.percentile(p[mask],5),median_kPa=np.median(p[mask]),
                median_J=np.median(J[mask]),median_kappa=np.median(kappa[mask]),
                median_theta_s_inv=np.median(theta[mask]),median_nn_dp=np.median(nn[mask]),
                fs_count=int(np.sum(mask&fs)))


def run():
    previous=TESTS/"figures/c08_psi25_local_suction/all_soil.csv"
    with previous.open(encoding="utf8") as stream:
        earlier={(r["run"],int(r["part"])):r for r in csv.DictReader(stream)}
    ref=min((r for (mode,_),r in earlier.items() if mode=="positive_only"),key=lambda r:float(r["min_kPa"]))
    refpart=int(ref["part"])
    receipts={key:json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
              for key,tag in RUNS.items()}
    require(all(r["passed"] and r["frames"]==132 and r["tag"]==RUNS[key] for key,r in receipts.items()),
            "Unexpected archived native review")
    primary=TESTS/"outputs"/RUNS["beta004"]/"data"/f"Part_{refpart:04d}.bi4"
    _,peak,_=checked(primary,receipts["beta004"])
    targets,_,_=select_materials(peak,int(ref["min_id"]))
    _,a0=native(PRE.with_name("Part_0000.bi4"))
    _,pre=native(PRE)
    require(np.array_equal(pre["Idp"][-5000:],SOIL_IDS) and np.array_equal(a0["Idp"][-5000:],SOIL_IDS),
            "Unexpected source IDs")
    origin=a0["Posd"][-5000:][:,[0,2]]
    clocks={}
    strata,sites=[],[]
    for label,tag in RUNS.items():
        rec=receipts[label]
        for part in range(5,133):
            m,a,prev=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",rec)
            tau=m["TimeStep"]-rec["release_time_s"]
            step=m["Step"]+1
            require(clocks.setdefault(part,(step,m["TimeStep"],tau))==(step,m["TimeStep"],tau),
                    "Actual matched clocks differ")
            sl=slice(-5000,None)
            pos=a["Posd"][sl][:,[0,2]]
            tree=cKDTree(pos)
            nn=tree.query(pos,k=2)[0][:,1]/DP
            bed=pos[:,1] < 2*H
            raw_fs=a["FSType"][sl]
            fs=np.isin(raw_fs,[2,3])
            kappa=a["Kplastic"][sl]
            high=(kappa>0)&(kappa>=np.percentile(kappa,90))
            J=a["PoroVolumeRatio"][sl]
            theta=a["PoroThetaLastStage"][sl]
            p=a["PorePress"][sl].astype(float)/1000
            imin=np.argmin(p)
            old=earlier[("positive_only" if label=="beta004" else "beta0",part)]
            require(float(old["min_kPa"])==p[imin] and int(old["min_id"])==int(SOIL_IDS[imin]),
                    "Earlier global minimum differs")
            info=dict(policy=label,part=part,step=step,time_s=m["TimeStep"],tau_s=tau)
            masks={"all":np.ones(len(p),bool),"near_bed":bed,"above_bed":~bed,
                   "high_kappa":high,"near_bed_high_kappa":bed&high,"above_bed_high_kappa":~bed&high,
                   "near_bed_other":bed&~high,"above_bed_other":~bed&~high,"p_below_minus20":p<-20}
            for group,mask in masks.items():
                values=summarize(mask,p,J,kappa,theta,fs,nn)
                if values:
                    strata.append(dict(info,group=group, kappa_p90=np.percentile(kappa,90),**values))
            walls=a["Posd"][:-5000][:,[0,2]]
            wtree=cKDTree(walls)
            for rid in sorted(set(targets)|{int(SOIL_IDS[imin])}):
                i=int(rid-SOIL_IDS[0])
                other=np.array(tree.query_ball_point(pos[i],2*H),int)
                other=other[other!=i]
                wb=np.array(wtree.query_ball_point(pos[i],2*H),int)
                op=p[other]
                wp=a["PorePress"][wb].astype(float)/1000
                sites.append(dict(info,id=rid,role=targets.get(rid,"frame_min"),is_frame_min=int(i==imin),
                           x0_m=origin[i,0],z0_m=origin[i,1],x_m=pos[i,0],z_m=pos[i,1],fs=int(raw_fs[i]),
                           p_kPa=p[i],p_prev_kPa=float(prev[i])/1000,p0_kPa=float(a["PorePress0"][sl][i])/1000,
                           J=J[i],J_pre=pre["PoroVolumeRatio"][sl][i],kappa=float(kappa[i]),theta_s_inv=theta[i],
                           k_m_s=a["PoroHydraulicConductivity"][sl][i],v_m_s=np.linalg.norm(a["Vel"][sl][i]),
                           effective_compression_kPa=-np.mean(a["SigmaState_kk"][sl][i])/1000,nn_dp=nn[i],
                           n_soil=len(other),n_wall=len(wb),soil_min_kPa=op.min(),soil_med_kPa=np.median(op),
                           n_soil_below20=int((op<-20).sum()),wall_min_kPa=wp.min() if len(wp) else ""))
    OUT.mkdir(exist_ok=True)
    for name,rows in (("spatial_groups.csv",strata),("material_sites.csv",sites)):
        with (OUT/name).open("x",encoding="utf8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)


if __name__=="__main__":
    run()
