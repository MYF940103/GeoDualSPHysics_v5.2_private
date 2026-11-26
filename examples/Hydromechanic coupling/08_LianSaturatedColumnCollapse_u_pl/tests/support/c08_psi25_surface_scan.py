"""Replay saved 2-D free-surface masks and rotate only the geometric scan."""
import json
import numpy as np
from scipy.spatial import cKDTree
from c08_psi25_local_suction import DP, FIXED, H, RUNS, save
from c08_psi25_tpi_native import CASE, TESTS, RELEASE_IDS, read_frame, require

ROT=np.array([[1.,-1.],[1.,1.]])/np.sqrt(2.)


def cover(d,n,projected=False):
    # Nondimensionalized by h. q is the displacement from the scan center.
    q=d-n
    tangent=np.array([-n[1],n[0]])
    if projected:
        near_metric=abs(q@n)+abs(q@tangent)
    else:
        near_metric=np.linalg.norm(q*n,axis=1)+np.linalg.norm(q*tangent,axis=1)
    return np.where(np.sum(d*d,axis=1)>2.,np.linalg.norm(q,axis=1),near_metric)<1.


def run():
    n=np.array([1.,0.])
    d=np.array([[.2,0.]])
    require(cover(d,n)[0] and not cover(d@ROT.T,ROT@n)[0] and
            cover(d,n,True)[0] and cover(d@ROT.T,ROT@n,True)[0],"Rotation fixture failed")
    summaries,points=[],[]
    for label in ("positive_only","all_zero"):
        tag=RUNS[label]
        rec=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
        sealed={name:(size,mtime) for name,size,mtime in rec["files"]}
        for part in range(5,133):
            path=TESTS/"outputs"/tag/"data"/f"Part_{part:04}.bi4"
            stat=path.stat()
            require(rec["passed"] and sealed[str(path.relative_to(CASE))]==(stat.st_size,stat.st_mtime_ns),"Changed input")
            m,a,_,_=read_frame(path)
            require(np.array_equal(a["Idp"],RELEASE_IDS),"Wrong release data")
            xz=a["Posd"][:,[0,2]]
            tree=cKDTree(xz)
            posdiv=a["PosDiv"][FIXED:]
            candidates=np.where(posdiv<np.float32(1.7))[0]+FIXED
            require(np.all(np.isin(a["FSType"][FIXED:][posdiv>=np.float32(1.7)],[0,1])),"Uncovered surface label")
            info=dict(run=label,part=part,tau_s=m["TimeStep"]-rec["release_time_s"])
            total=dict(candidates=len(candidates),mismatches=0,rotated_changes=0,dot_changes=0,
                       severe_dot_changes=0, soil_only_changes=0)
            for i,nb in zip(candidates,tree.query_ball_point(xz[candidates],2*H)):
                js=np.array([j for j in nb if j!=i],dtype=int)
                d=(xz[js]-xz[i])/H
                n=a["FSNormal"][i,[0,2]].astype(float)
                isolated=(not len(js) or (a["PosDiv"][i]<1.1 and np.pi*(2*H/DP)**2/len(js)<.4))
                if isolated or np.linalg.norm(n)<=1e-6:
                    old=rot=dot=np.zeros(len(js),bool)
                else:
                    old=cover(d,n)
                    rot=cover(d@ROT.T,ROT@n)
                    dot=cover(d,n,True)
                    require(np.array_equal(dot,cover(d@ROT.T,ROT@n,True)), "Dot scan lost rotation invariance")
                native=bool(a["FSType"][i] in (2,3))
                total["mismatches"]+=int(native != (not old.any()))
                total["rotated_changes"]+=int(old.any()!=rot.any())
                total["dot_changes"]+=int(old.any()!=dot.any())
                total["severe_dot_changes"]+=int(old.any()!=dot.any() and a["PorePress"][i]<-50000)
                total["soil_only_changes"]+=int(old.any() and not np.any(old & (js>=FIXED)))
                if a["Idp"][i]==7010 or a["PorePress"][i]<-50000:
                    points.append(dict(info,id=int(a["Idp"][i]),p_kPa=float(a["PorePress"][i])/1000,
                                       native_FS=int(native),PosDiv=float(a["PosDiv"][i]),nx=n[0],nz=n[1],
                                       blocking_soil=" ".join(map(str,a["Idp"][js[old&(js>=FIXED)]])),
                                       blocking_fixed=" ".join(map(str,a["Idp"][js[old&(js<FIXED)]])),
                                       rotated_FS=int(not rot.any()),dot_FS=int(not dot.any())))
            summaries.append(dict(info,**total))
    save("surface_scan.csv",summaries)
    save("surface_scan_toe.csv",points)


if __name__=="__main__":
    run()
