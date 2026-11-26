"""Frozen C08 toe: bed pressure extrapolation and a constant-k trace of Lian Eqs. 22–23."""
import json
import numpy as np
from scipy.spatial import cKDTree
from c08_psi25_local_suction import DP, FIXED, H, OUT, RUNS, save
from c08_psi25_tpi_native import CASE, TESTS, RELEASE_IDS, read_frame, require
from c08_h18_wend_partial_review_r1 import kernel

GZ = float(np.float32(-9.81))
V0 = float(np.float32(3.316)) / 2072.5
TARGET = 7010
PARTS = (32,41,52,60,61,63,72,78,80,81,82,94,132)


def bed_fits(a, wall_index):
    """Yield admissible geometric fits, including the nearest-source fallback."""
    bed = a["Posd"][wall_index,[0,2]]
    require(255<=a["Idp"][wall_index]<1805 and bed[1]<0, "Expected horizontal bed")
    mirror = bed + np.array([0.,np.float32(-2*bed[1])])
    pos = a["Posd"][FIXED:][:,[0,2]]
    centre = mirror.copy()
    for attempt in range(2):
        d = centre-pos
        rr2 = np.sum(d*d,axis=1).astype("f4")
        ix = np.flatnonzero(rr2<=np.float32(np.float32(2*H)**2))
        if not len(ix): return
        dx = d[ix]
        nearest = np.argmin(np.sum(dx*dx,axis=1))
        w,fac = kernel(rr2[ix],H,np.float32(.557/H**2),np.float32(-2.7852/H**3))
        vol = V0*a["PoroVolumeRatio"][FIXED:][ix]
        cols = np.column_stack((w,fac[:,None]*dx))*vol[:,None]
        basis = np.column_stack((np.ones(len(ix)),dx))
        moment = cols.T@basis
        if abs(np.linalg.det(moment))>=1e-3 and np.sum(w*vol)>0:
            weights = (pos[ix[nearest]]-mirror) @ np.linalg.solve(moment,cols.T)[1:]
            weights[nearest] += 1
            require(abs(weights.sum()-1)<1e-8 and np.max(abs(weights@pos[ix]-mirror))<1e-8,
                    "Bed constant or affine reproduction failed")
            yield ix+FIXED,weights,ix[nearest]+FIXED,attempt+1
        centre=pos[ix[nearest]]


def bed_pressure(a, wall_index):
    """Apply the pressure fit on saved positions and pressures, restoring normal gravity head."""
    for js,weights,anchor,attempt in bed_fits(a,wall_index):
        p=a["PorePress"][js].astype(float)
        head=1000*GZ
        predicted=weights@(p-head*a["Posd"][js,2])+head*a["Posd"][wall_index,2]
        return dict(mirror_donors=len(js), fit_attempt=attempt,
                    actual_bed_kPa=float(a["PorePress"][wall_index])/1000,
                    frozen_fit_kPa=predicted/1000, source_min_kPa=p.min()/1000,
                    source_max_kPa=p.max()/1000, sum_neg_weights=weights[weights<0].sum(),
                    weight_on_7010=weights[a["Idp"][js]==TARGET].sum(), largest_weight=weights.max(),
                    anchor_id=int(a["Idp"][anchor]), wall_id=int(a["Idp"][wall_index]))
    return None


def eq23(d, volumes, kind, h):
    r=np.linalg.norm(d,axis=1)
    q=r/h
    if kind=="Wendland":
        radial=5*(1-.5*q)**3
    else:
        radial=np.where(q<=1,3-2.25*q,.75*(2-q)**2/q)
    # Common kernel prefactors cancel in the inverse first moment.
    vg = d*(volumes*radial)[:,None]
    moment = d.T@vg
    vg_norm = np.linalg.solve(moment,vg.T).T
    b = 2*np.sum(vg_norm*d,axis=1)/(r*r)  # trace(4 u⊗u - I) = 2 in 2D
    a = b - vg_norm@(b@d)
    require(np.max(abs(a@d))<1e-8, "Affine null failed in frozen scalar stencil")
    return a,np.linalg.cond(moment)


def run():
    offsets=np.array([(i,j) for i in range(-4,5) for j in range(-4,5) if i or j])*DP
    for hdp in (1.2,1.8):
        d=offsets[np.linalg.norm(offsets,axis=1)<2*hdp*DP]
        for kind in ("Wendland","Cubic"):
            coeff,_=eq23(d,np.full(len(d),DP**2),kind,hdp*DP)
            require(abs(coeff@np.sum(d*d,axis=1)-4)<1e-10,"Regular cloud failed quadratic trace")
    beds, stencils = [],[]
    for part in PARTS:
        states = {}
        wall_indices = {804}
        for label in ("positive_only","all_zero"):
            tag=RUNS[label]
            rec=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
            path=TESTS/"outputs"/tag/"data"/f"Part_{part:04}.bi4"
            stat=path.stat()
            require(rec["passed"] and [str(path.relative_to(CASE)),stat.st_size,stat.st_mtime_ns] in rec["files"],"Changed source")
            m,a,_,_=read_frame(path)
            require(np.array_equal(a["Idp"],RELEASE_IDS),"Wrong material")
            xz=a["Posd"][:,[0,2]]
            i=int(np.searchsorted(a["Idp"],TARGET))
            donors=np.array(cKDTree(xz).query_ball_point(xz[i],2*H))
            donors=donors[donors!=i]
            bed=donors[donors<FIXED]
            wall_indices.add(int(bed[np.argmin(a["PorePress"][bed])]))
            states[label]=(m,a,i,xz,donors)
        require(states["all_zero"][0]["TimeStep"]==states["positive_only"][0]["TimeStep"],"Unmatched frames")
        for label,(m,a,i,xz,donors) in states.items():
            info=dict(run=label,part=part,step=m["Step"]+1,time_s=m["TimeStep"],tau_s=m["TimeStep"]-m["GravityPreloadActualTime"])
            for wi in sorted(wall_indices):
                if wi not in donors: continue  # do not interpret inactive or out-of-support walls
                row=bed_pressure(a,wi)
                require(row is not None,"No eligible primary or nearest frozen wall fit")
                beds.append(dict(info,**row))
            d=xz[donors]-xz[i]
            r=np.linalg.norm(d,axis=1)
            for hdp in (1.2,1.8):
                h=H if hdp==1.8 else hdp*DP
                keep=r<2*h
                dx=d[keep]
                js=donors[keep]
                bed=js<FIXED
                delta=(a["PorePress"][js].astype(float)-a["PorePress"][i])/1000
                for kind in ("Cubic","Wendland"):
                    weights,condition=eq23(dx,V0*a["PoroVolumeRatio"][js],kind,h)
                    component=weights*delta
                    stencils.append(dict(info,id=TARGET,hdp=hdp,kernel=kind,soil=len(js)-int(bed.sum()),
                                         wall=int(bed.sum()),moment_condition=condition,
                                         trace_r_squared=weights@np.sum(dx*dx,axis=1),
                                         trace_x_squared=weights@(dx[:,0]**2),trace_z_squared=weights@(dx[:,1]**2),
                                         trace_xz=weights@(dx[:,0]*dx[:,1]),
                                         soil_kPa_m2=component[~bed].sum(),wall_kPa_m2=component[bed].sum(),
                                         total_kPa_m2=component.sum(),negative_coefficients=int((weights<0).sum())))
    save("bed_extrapolation.csv",beds)
    save("frozen_pressure_stencil.csv",stencils)


if __name__=="__main__":
    run()
