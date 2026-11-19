"""Cryer manufactured equilibrium using a conforming linear-tetrahedron weak form."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull

from cryer_load_pair_r1 import AFFINE_L
from cryer_p3_peak_shells import ordered
from cryer_peak_paired_manufactured import TAG as FORCE_TAG, radial_state
from cryer_shell_equilibrium import Q, R, TESTS, Reference, need, write


TAG = "cryer_tet_weak_force_r1"
DP = .0025


def tessellate(x, surface_ids):
    # Break co-spherical triangulation ties in the lifting coordinate only.
    # The physical nodes, natural coordinates, faces, volumes and masses never move.
    u = x/DP
    weight = 2.**-14*np.random.default_rng(20261119).uniform(-.5,.5,len(x))
    hull = ConvexHull(np.column_stack((u,np.sum(u*u,axis=1)+weight)))
    t = hull.simplices[hull.equations[:,3] < -1.e-9]
    a,b,c = np.moveaxis(u[t[:,1:]]-u[t[:,:1]],1,0)
    det = abs(np.einsum("ij,ij->i",a,np.cross(b,c)))
    vertical = det<1.e-10
    need(np.all(np.isin(t[vertical],surface_ids)),"Only nonvolumetric hull faces may be omitted")
    removed = int(vertical.sum())
    t = t[~vertical]
    need(np.array_equal(np.unique(t),np.arange(len(x))),"All real material nodes")
    vf = np.concatenate([t[:,np.arange(4)!=j] for j in range(4)])
    faces, multiplicity = np.unique(np.sort(vf,axis=1),axis=0,return_counts=True)
    need(np.all((multiplicity==1)|(multiplicity==2)),"Face incidence")
    b = faces[multiplicity==1]
    need(np.array_equal(np.unique(b),surface_ids),"Exactly native surface vertices")
    edges = np.concatenate([b[:,[0,1]],b[:,[0,2]],b[:,[1,2]]])
    ue, copies = np.unique(edges,axis=0,return_counts=True)
    need(np.all(copies==2) and len(surface_ids)-len(ue)+len(b)==2,"Closed boundary manifold")
    return t,b,len(faces)-len(b),removed


def geometry(x,t,faces):
    a,b,c = np.moveaxis(x[t[:,1:]]-x[t[:,:1]],1,0)
    bc = np.cross(b,c)
    det = np.einsum("ij,ij->i",a,bc)
    need(np.min(abs(det))/DP**3>1e-10,"Finite nonzero physical tetrahedra")
    vol = abs(det)/6
    # Integrated gradients V * grad(N); no inverses of small cell volumes.
    g = np.zeros((len(t),4,3))
    g[:,1:] = np.stack([bc,np.cross(c,a),np.cross(a,b)],axis=1)*np.sign(det)[:,None,None]/6
    g[:,0] = -g[:,1:].sum(axis=1)
    i,j,k = faces.T
    av = np.cross(x[j]-x[i],x[k]-x[i])/2
    orientation = np.sum(av*x[faces].mean(axis=1),axis=1)
    need(np.all(orientation!=0),"Interior origin and nonzero boundary areas")
    av *= np.sign(orientation)[:,None]
    return vol,g,av,np.sign(det)


def internal(total_stress,t,g,n):
    result = np.zeros((n,3))
    for j in range(4):
        f = -np.einsum("tab,tb->ta",total_stress,g[:,j])
        np.add.at(result,t[:,j],f)
    return result


def external(faces,uniform_stress,av,n):
    result = np.zeros((n,3))
    face_force = av@uniform_stress.T/3
    for j in range(3):
        np.add.at(result,faces[:,j],face_force)
    return result


def rms(v):
    return np.sqrt((v*v).sum(axis=1).mean())


def plot(shells,figfile,detail=False):
    import matplotlib.pyplot as plt
    a = pd.read_csv(TESTS/"figures"/(FORCE_TAG+"_shells.csv"))
    a = a.loc[a.geometry=="initial_reference_sphere"]
    b = pd.DataFrame(shells)
    b = b.loc[(b.geometry=="original")&(b.load=="M0_peak")&(b.inertia=="native_mass")]
    fig,axes = plt.subplots(1,2,figsize=(10.8,4.25),layout="constrained")
    for name,group in list(a.groupby("operator"))+[("Tetrahedra, surface traction",b)]:
        for ax,col in zip(axes,("vector_rms_m_s2","mean_inward_m_s2")):
            ax.plot(group.r0_over_a,group[col],label=name.replace("_"," "),marker="o",ms=3)
    for ax,y in zip(axes,("Vector RMS acceleration","Mean inward acceleration")):
        ax.set(xlabel="Material radius / sphere radius",ylabel=y+" (m/s²)")
        ax.grid(alpha=.2);ax.axhline(0,lw=.7,color="gray")
    if detail:
        axes[0].set_yscale("log")
        axes[1].set_yscale("symlog",linthresh=.05)
        axes[1].set_yticks([-100,-10,-1,-.1,0,.1,1,10],labels=["−100","−10","−1","−0.1","0","0.1","1","10"])
    axes[0].legend(fontsize=9)
    fig.savefig(figfile,dpi=180)
    plt.close(fig)


def export_mesh(output):
    """Share the reviewed connectivity for a separate dynamics test without retessellating there."""
    target = TESTS/"outputs"/"cryer_tet_reference_r1.npz"
    need(not target.exists(),"Preserve prior exported mesh")
    checked = json.loads((TESTS/"logs"/(TAG+".check.json")).read_text(encoding="utf8"))["mesh"][0]
    st = ordered(output/"data",0,["Posd","PoroCurrentVolume","PoroMixtureDensity","FSType"])
    x=st["Posd"]; outside=np.flatnonzero(np.isin(st["FSType"],(2,3)))
    t,faces,interior,vertical = tessellate(x,outside)
    vol,g,av,_=geometry(x,t,faces)
    need(len(t)==checked["tets"] and len(faces)==checked["outer_faces"] and interior==checked["interior_faces"]
         and vertical==checked["nonvolumetric_lifted_side_facets_omitted"]
         and vol.sum()==checked["volume_m3"],"Reproduce accepted connectivity and physical volumes")
    with target.open("xb") as f:
        np.savez_compressed(f,x0=x,tets=t,faces=faces,Ve=vol,Ve_gradN=g,face_area_out=av,
            native_ids=np.arange(8,8+len(x),dtype=np.int32),native_volume_m3=st["PoroCurrentVolume"],
            native_mass_kg=st["PoroCurrentVolume"]*st["PoroMixtureDensity"],
            native_surface=outside,material_shell=np.rint(np.linalg.norm(x,axis=1)/DP).astype(int))
    print(target)


def main(output):
    source = json.loads((TESTS/"logs"/(FORCE_TAG+".check.json")).read_text(encoding="utf8"))
    base = TESTS/"figures"/TAG
    csv = base.with_name(TAG+"_regions.csv"); byshell = base.with_name(TAG+"_shells.csv")
    figure = base.with_suffix(".png"); detail=base.with_name(TAG+"_detail.png")
    check = TESTS/"logs"/(TAG+".check.json")
    need(not any(p.exists() for p in (csv,byshell,figure,detail,check)),"Preserve existing work")
    fs = ["Posd","PoroCurrentVolume","PoroMixtureDensity","FSType"]
    original,peak = (ordered(output/"data",s,fs) for s in (0,source["part"]))
    x0 = original["Posd"]
    sids = np.rint(np.linalg.norm(x0,axis=1)/DP).astype(int)
    outside = np.flatnonzero(np.isin(original["FSType"],(2,3)))
    need(np.array_equal(outside,np.flatnonzero(sids==20)) and len(outside)==5153,
         "Native free surface topology")
    t,faces,interior,vertical = tessellate(x0,outside)
    ref = Reference(.3,finite=False)
    ref.cv=ref.H*ref.kappa;ref.decay=ref.xi**2*ref.cv/R**2
    p,srr,stt,_ = radial_state(ref,DP*np.arange(1,21),source["tau_s"])
    need(abs(p[0]-source["pressure_center_Pa"])<1e-7,"Same analytical peak")
    er = x0/np.linalg.norm(x0,axis=1)[:,None]
    total = ((stt-p)[sids-1,None,None]*np.eye(3)
             +(srr-stt)[sids-1,None,None]*er[:,:,None]*er[:,None,:])
    uniform = -Q*np.eye(3)
    dev = Q*np.array([[.33,-.13,.21],[-.13,.2,.11],[.21,.11,-.53]])
    loads = (("closed_10kPa",np.broadcast_to(uniform,(len(t),3,3)),uniform),
             ("constant_shear_fixture",np.broadcast_to(dev,(len(t),3,3)),dev),
             ("M0_peak",total[t].mean(axis=1),uniform))
    regions = [];shellrows = [];mesh = [];checks = [];original_sign = None
    for geometry_name,state in (("original",original),("mapped_peak",peak)):
        x = state["Posd"]; n=len(x); rho=state["PoroMixtureDensity"]
        mass = rho*state["PoroCurrentVolume"]
        vol,g,av,sign = geometry(x,t,faces)
        if original_sign is None:
            original_sign = sign
        need(np.array_equal(original_sign,sign),"No cell inverted in mapped state")
        need(np.array_equal(outside,np.flatnonzero(np.isin(state["FSType"],(2,3)))),"Same true surface")
        lump = np.bincount(t.ravel(),weights=np.repeat(vol/4,4),minlength=n)
        need(np.all(lump>0),"Nonzero nodal support")
        area=np.linalg.norm(av,axis=1).sum()
        v_surface=np.sum(av*x[faces].mean(axis=1))/3
        need(abs(vol.sum()-v_surface)<1e-13 and np.linalg.norm(av.sum(axis=0))<1e-13,
             "Volume/area divergence identities")
        if geometry_name=="original":
            cv=ConvexHull(x0)
            need(abs(vol.sum()-cv.volume)<1e-13 and abs(area-cv.area)<1e-11,
                 "Independent convex hull geometry")
        mesh.append(dict(geometry=geometry_name,tets=len(t),interior_faces=interior,outer_faces=len(faces),
            nonvolumetric_lifted_side_facets_omitted=vertical,
            hull_nodes=len(outside),volume_m3=vol.sum(),surface_area_m2=area,
            volume_fraction_ideal=vol.sum()/(4*np.pi*R**3/3),area_fraction_ideal=area/(4*np.pi*R**2),
            native_volume_sum_m3=float(np.sum(state["PoroCurrentVolume"])),native_mass_kg=float(mass.sum()),
            geometric_lumped_mass_kg=float(np.sum(lump*rho)),cell_det_over_dp3_percentiles=
                np.quantile(6*vol/DP**3,[0,.001,.01,.5,1]).tolist(),
            nodal_lumped_over_native_volume_min_median_max=np.quantile(lump/state["PoroCurrentVolume"],[0,.5,1]).tolist()))
        inward = -x/np.linalg.norm(x,axis=1)[:,None]
        for name,T,boundary in loads:
            fi = internal(T,t,g,n)
            fe = external(faces,boundary,av,n)
            force = fi+fe
            virtual=x@AFFINE_L.T
            worki=float(np.sum(fi*virtual))
            wi_ref=float(-np.sum(vol*np.einsum("nij,ij->n",T,AFFINE_L)))
            worke=float(np.sum(fe*virtual));we_ref=float(np.sum((av@boundary.T)*virtual[faces].mean(axis=1)))
            moment=np.cross(x,force).sum(axis=0)
            net=force.sum(axis=0)
            need(abs(worki-wi_ref)<1e-10 and abs(worke-we_ref)<1e-10
                 and np.linalg.norm(net)<1e-10 and np.linalg.norm(moment)<1e-10,
                 "Global force/torque and independent affine virtual work")
            tensor=force.T@x
            hydro=np.trace(tensor)/3
            shear=.5*(tensor+tensor.T)-hydro*np.eye(3)
            peakmag=np.linalg.norm(force/mass[:,None],axis=1).max()
            if name!="M0_peak":
                need(peakmag<1e-7,"Per-node constant stress with its prescribed traction")
            checks.append(dict(geometry=geometry_name,load=name,net_force_N=net.tolist(),net_torque_Nm=moment.tolist(),
                nodal_max_native_acceleration_m_s2=peakmag,volume_power_W=worki,surface_power_W=worke,
                independent_volume_power_W=wi_ref,independent_surface_power_W=we_ref,
                nodal_force_first_moment_Nm=tensor.tolist(),mean_dilatation_moment_Nm=hydro,
                symmetric_deviator_moment_norm_Nm=float(np.linalg.norm(shear))))
            for inertia,m in (("native_mass",mass),("tet_lumped_mass",rho*lump)):
                acc=force/m[:,None]
                signed=np.einsum("ij,ij->i",acc,inward)
                for region,mask in [("center18",sids==1),("inner10",sids<=10),("all",sids>0),
                                    ("true_surface",sids==20)]+[(str(j),sids==j) for j in range(1,21)]:
                    row=dict(geometry=geometry_name,load=name,inertia=inertia,region=region,count=int(mask.sum()),
                        vector_rms_m_s2=rms(acc[mask]),mean_inward_m_s2=signed[mask].mean(),
                        tangential_rms_m_s2=rms(acc[mask]-signed[mask,None]*inward[mask]),
                        max_m_s2=float(np.linalg.norm(acc[mask],axis=1).max()))
                    if region.isdigit():
                        shellrows.append(dict(row,r0_over_a=int(region)/20))
                    else:
                        regions.append(row)
    write(csv,regions);write(byshell,shellrows);plot(shellrows,figure);plot(shellrows,detail,True)
    with check.open("x",encoding="utf8") as f:
        json.dump(dict(time_s_after_open=source["tau_s"],mesh=mesh,checks=checks,
            force="Conforming P1 tetrahedral internal weak force; full nodal analytical Cauchy stress linear interpolation; exact uniform face traction integrated in equal thirds. Forces fixed for both reported inertia choices.",
            lifting="DP-scaled xyz, fixed PCG64 seed 20261119, squared lifting weight range [-2^-15,2^-15). Physical coordinates unchanged; all 37173 nodes present.",
            timing="Original closed analytical q and instantaneous peak analytical fields. Mapped geometry holds the same tensors at material IDs."),f,indent=2,allow_nan=False)
    print(pd.DataFrame(regions).query("geometry=='original' and load=='M0_peak'").to_string(index=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output",type=Path)
    ap.add_argument("--export-mesh-only",action="store_true")
    args=ap.parse_args()
    (export_mesh if args.export_mesh_only else main)(args.output)
