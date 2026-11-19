"""C02 plane-wall velocity-gradient and finite-interval compatibility on saved geometry."""
import os
for key in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[key] = "1"

import json
import numpy as np
import pandas as pd

from upl_tpi_bottom_patch_r1 import DATA, FIG, TEST, Bed, dx_periodic, ordered, read, require

TAG = "upl_tpi_bed_rate_r1"
MODULUS = 1666666.75 + 4*769230.8125/3


def vtk_field(data, label, dtype, count):
    start = data.index(label.encode("ascii")+b"\n")+len(label)+1
    return np.frombuffer(data, dtype=dtype, count=count, offset=start).astype(float)


def walls(bed):
    def vtk(name):
        data = (DATA.parent / name).read_bytes()
        ids = vtk_field(data, "LOOKUP_TABLE default", ">u4", 40)
        order = np.argsort(ids)
        require(np.array_equal(ids[order], np.arange(40)), "Wrong native bed IDs")
        pos = vtk_field(data, "POINTS 40 double", ">f8", 120).reshape(40,3)[order]
        normal = vtk_field(data, "Normal 3 40 float", ">f4", 120).reshape(40,3)[order]
        require(np.array_equal(pos[:,0], bed.x[:40]) and np.array_equal(pos[:,2], bed.z[:40]),
                "Saved bed and normal anchor differ")
        return normal
    normal = vtk("CfgInit_Normals.vtk"); ghost_normal = vtk("CfgInit_NormalsGhost.vtk")
    require(np.allclose(ghost_normal, 2*normal, atol=2e-9, rtol=0)
            and np.all(ghost_normal[:,:2]==0.) and np.all(ghost_normal[:,2]>0)
            and np.max(abs(bed.z[:40]+normal[:,2])) < 2e-9, "Not the fixed z=0 mirror geometry")
    return ghost_normal[:,2]


def weights(h, delta):
    # Wendland W and (1/r) dW/dr, matching the frozen GPU definition except arithmetic precision.
    radius = np.linalg.norm(delta, axis=-1)
    shape = np.maximum(1-radius/(2*h), 0)
    return .557/h**2*(1+2*radius/h)*shape**4, -2.7852/h**4*shape**3


def spr_wall(x, z, J, bed, ghost_offset):
    # The dynamic-wall stage0 in the frozen JSphGpu_ker.cu supersedes the general SPR pass.
    # Original material IDs label the nearest soil anchor for each reflected ghost sample.
    dx = dx_periodic(x[:40,None]-x[None,40:])
    dz = z[:40,None]+ghost_offset[:,None]-z[None,40:]
    offsets = np.stack((dx,dz),axis=-1)
    W, fac = weights(bed.h, offsets)
    area = bed.v0*J[None,40:]
    basis = np.stack((np.ones_like(dx),dx,dz),axis=-1)
    rows = np.stack((W,fac*dx,fac*dz),axis=-1)*area[:,:,None]
    inverse = np.linalg.inv(np.einsum("wna,wnb->wab",rows,basis))
    nearest = np.argmin(dx*dx+dz*dz,axis=1)
    axis = np.arange(40)
    factors = -(dx[axis,nearest,None]*inverse[:,1,:]+dz[axis,nearest,None]*inverse[:,2,:])
    combination = np.einsum("wa,wna->wn",factors,rows)
    combination[axis,nearest] += 1.
    # Geometry-independent scalar and linear checks for the mirrored sampling part.
    require(np.max(abs(combination.sum(axis=1)-1.)) < 2e-11, "Constant wall sample")
    require(np.max(abs(combination@z[40:]-(z[:40]+ghost_offset))) < 1e-12,"Linear wall sample")
    return combination, nearest+40, np.count_nonzero(W,axis=1)


def gradient_rows(x, z, J, bed, ids):
    delta = np.stack((dx_periodic(x[ids,None]-x), z[ids,None]-z), axis=-1)
    w, fac = weights(bed.h, delta)
    g = fac[:,:,None]*delta*(bed.v0*J)[None,:,None]
    moment = np.einsum("rja,rjb->rab",g,-delta)
    g = np.einsum("rab,rjb->rja",np.linalg.inv(moment),g)
    return g, w


def calculate(frame, bed, layer, ghosts):
    fields = ordered(frame)
    x = fields["Posd"][:,0]; z = fields["Posd"][:,2]; J=fields["PoroVolumeRatio"]
    order = np.argsort(frame["arrays"]["Idp"])
    vel = frame["arrays"]["Vel"][order][:,[0,2]].astype(float)
    saved_theta = frame["arrays"]["PoroThetaLastStage"][order]
    wall, anchors, supports = spr_wall(x,z,J,bed,ghosts)
    ids = np.flatnonzero(np.isin(layer,(0,1,2,3,49,50)))
    g, w = gradient_rows(x,z,J,bed,ids)
    near = z[ids] < 2*bed.h
    # Restricted 1-D comparison. Impose v_z(0)=0 and fit a*z+b*z^2 in the real
    # neighbouring soil, with coordinates scaled by h and positive W*V weights.
    # Examine this derivative separately, without feeding it back into the saved state.
    ss = z[40:]/bed.h
    basis = np.stack((ss, ss**2),axis=1)
    area = w[near,40:]*(bed.v0*J[40:])
    normal = np.einsum("rj,ja,jb->rab",area,basis,basis)
    require(np.all(np.linalg.cond(normal)<1e5),"Ill-conditioned wall-constrained fit")
    def derivatives(v):
        image = wall@v[40:]
        v = v.copy(); v[:40]=image*np.array([1.,-1.])
        dv = v[None,:,:]-v[ids,None,:]
        tensor=np.einsum("rja,rjb->rab",dv,g)
        theta = tensor[:,0,0]+tensor[:,1,1]
        alternative = tensor[:,1,1].copy()
        rhs=np.einsum("rj,ja,j->ra",area,basis,v[40:,1])
        beta=np.linalg.solve(normal,rhs[...,None])[:,:,0]
        alternative[near]=(beta[:,0]+2*(z[ids[near]]/bed.h)*beta[:,1])/bed.h
        return theta,tensor[:,1,1],alternative
    fixed = np.ones_like(z)
    zeros = np.zeros_like(z)
    profiles = (("constant_tangent",np.column_stack((fixed,zeros)),zeros),
                ("linear_normal",np.column_stack((zeros,z)),fixed),
                ("quadratic_normal",np.column_stack((zeros,z*z)),2*z))
    result = []
    for name,v,exact in profiles:
        theta,raw,alt=derivatives(v)
        for k in (0,1,2,3,49):
            inside=layer[ids]==k
            for mode,r in (("original",raw),("plane_quadratic",alt)):
                result.append(dict(field=name,operator=mode,layer=k,
                    abs_max_gradient_error_s1=float(np.max(abs(r[inside]-exact[ids[inside]]))),
                    mean_rate_s1=float(r[inside].mean()),mean_exact_s1=float(exact[ids[inside]].mean()),
                    original_Jtheta_max_error_s1=float(np.max(abs(J[ids[inside]]*(theta[inside]-exact[ids[inside]]))))))
    theta,raw,alt=derivatives(vel)
    stats = dict(actual_saved_theta_min=float(saved_theta[ids].min()),actual_saved_theta_max=float(saved_theta[ids].max()),
        bed_original_theta_minus_last_stage=float(np.mean((theta-saved_theta[ids])[layer[ids]==0])),
        bed_Jtheta_difference_if_using_quadratic=float(np.mean((J[ids]*(alt-raw))[layer[ids]==0])),
        bed_stress_rate_difference_if_using_quadratic_Pa_s=MODULUS*float(np.mean((alt-raw)[layer[ids]==0])),
        wall_anchor_matches_initial=int(np.sum(anchors==bed.partner)),wall_ids=40,
        wall_support_min=int(supports.min()),wall_support_max=int(supports.max()))
    mean=lambda a,k: float(a[layer[ids]==k].mean())
    for k,k1,tag in ((0,1,"bed"),(49,50,"middle")):
        z0,z1=mean(z[ids],k),mean(z[ids],k1)
        v0,v1=mean(vel[ids,1],k),mean(vel[ids,1],k1)
        stats[tag+"_upper_interval_rate_s1"]=(v1-v0)/(z1-z0)
        # Midpoint of the interval between layer centers is the upper face of the first cell;
        # its velocity is evaluated by linear interpolation, so the upper-half secant is
        # exactly the center-to-center secant under this explicit geometric convention.
        if k==0: stats["bed_lower_half_rate_s1"]=v0/z0
        for mode,r in (("original",raw),("plane_quadratic",alt)):
            d0,d1=mean(r,k),mean(r,k1)
            stats[f"{tag}_{mode}_point_s1"]=d0
            stats[f"{tag}_{mode}_upper_rate_error_s1"]=(d0+d1)*.5-(v1-v0)/(z1-z0)
            if k==0:
                # Mean extrapolated derivative on wall-to-center half interval; both operators
                # use the identical first and second center locations and the same quadrature.
                stats[f"bed_{mode}_lower_half_error_s1"]=d0-.5*z0*(d1-d0)/(z1-z0)-v0/z0
    return result,stats,anchors


def main():
    paths=[FIG/(TAG+s) for s in ("_manufactured.csv","_actual.csv","_ids.csv")] + [TEST/"logs"/(TAG+".check.json")]
    require(not any(p.exists() for p in paths),"Use existing review")
    history=pd.read_csv(TEST.parent/"figures/upl_tpi_p3_full_diagnostic_r1/history.csv",float_precision="round_trip")
    bed=Bed(read(DATA/"Part_0000.bi4"));ghosts=walls(bed)
    layer=np.rint(bed.z/.01-.5).astype(int)
    samples=[0,.001,.002,.005,.008,.01,.012,.02,.05,.1,.15,.3,.5,1.,1.5,2.,4.,8.,15.,25.,32.,40.,50.,60.,72.89]
    parts=sorted(set(int((history.time_s-t).abs().idxmin()) for t in samples)|{1427,1428,1652})
    manufactured=[]; actual=[]; mappings=[]
    for part in parts:
        f=read(DATA/f"Part_{part:04d}.bi4");time=float(f["part"]["values"]["TimeStep"])
        require(time==history.time_s.iloc[part],"Clock changed")
        results,metrics,anchors=calculate(f,bed,layer,ghosts)
        for row in results: manufactured.append(dict(part=part,time_s=time,**row))
        actual.append(dict(part=part,time_s=time,**metrics))
        for p,(anchor,dz) in enumerate(zip(anchors,ghosts)):
            mappings.append(dict(part=part,time_s=time,bound_id=p,mirror_anchor_id=int(anchor),
                                 wall_z_m=bed.z[p],normal_ghost_z_m=dz,ghost_z_m=bed.z[p]+dz))
    m=pd.DataFrame(manufactured);a=pd.DataFrame(actual)
    require(m[m.field.isin(["constant_tangent","linear_normal"])].abs_max_gradient_error_s1.max()<1e-6,
            "Admissible patch fixture failed")
    summary={}
    for k in (0,49):
        sm=m[(m.field=="quadratic_normal") & (m.layer==k)]
        summary[str(k)]=sm.groupby("operator").abs_max_gradient_error_s1.max().to_dict()
    # Sample times are deliberately not evenly spaced; compare both the signed final differences and
    # time-weighted RMS on the same intervals. Do not interpolate any native time or close substeps.
    bins={}
    for lo,hi in ((0,.1),(.1,2),(2,72.89),(32,72.89)):
        s=a[(a.time_s>=lo)&(a.time_s<=hi)]
        if len(s)<2:continue
        dt=np.diff(s.time_s)
        bins[str((lo,hi))]={}
        for c in (f"bed_{mode}_{w}_error_s1" for mode in ("original","plane_quadratic") for w in ("lower_half","upper_rate")):
            y2=s[c].to_numpy()**2
            bins[str((lo,hi))][c]=float(np.sqrt(np.dot(dt,.5*(y2[1:]+y2[:-1]))/dt.sum()))
    for p,table in zip(paths,(m,a,pd.DataFrame(mappings))):table.to_csv(p,index=False)
    paths[3].write_text(json.dumps(dict(frames=len(parts),frozen_geometry_only=True,
        quadratic_cases_s1=summary,actual_window_time_weighted_samples=bins,final=actual[-1],
        formal_physical_acceptance=False),indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__ == "__main__":main()
