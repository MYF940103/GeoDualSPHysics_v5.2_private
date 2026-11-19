"""Offline surface work on original C04 initial, closed, peak and last peak-window frames."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull, cKDTree

from cryer_p3_verify_r1 import SOIL, snapshot


TESTS = Path(__file__).resolve().parents[1]
NAME = "CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
DATA = TESTS.parent/NAME/NAME/"data"
TAG = "c04_surface_work_r1"
Q = 10000.
R = .05
VSPHERE = 4*np.pi*R**3/3
H = float(np.float32(.0045))
AXES = "xyz"


def capture(part):
    a, _ = snapshot(DATA/f"Part_{part:04d}.bi4",part,64*part,2**-19)
    return {k:a[k][SOIL] for k in ("Posd","PoroCurrentVolume","PoroMixtureDensity","HydroMechLoadAce","FSType","Idp")}


def outer_faces(x):
    hull=ConvexHull(x)
    assert len(hull.vertices)==len(x)
    tri=hull.simplices.copy()
    i,j,k=tri.T
    area=np.cross(x[j]-x[i],x[k]-x[i])
    reverse=np.einsum("ij,ij->i",area,hull.equations[:,:3])<0
    tri[reverse]=tri[reverse][:,[0,2,1]]
    edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1)
    assert np.all(np.unique(edges,axis=0,return_counts=True)[1]==2)
    return tri


def facet_measures(x,outer,tri):
    xs=x[outer]
    i,j,k=tri.T
    area=.5*np.cross(xs[j]-xs[i],xs[k]-xs[i])
    center=(xs[i]+xs[j]+xs[k])/3
    triple=np.einsum("ij,ij->i",area,center)
    assert np.all(triple>0)
    measure=triple.sum()/3
    boundary=np.zeros_like(xs)
    for vertex in (i,j,k):
        np.add.at(boundary,vertex,area/3)
    all_points=np.zeros_like(x)
    all_points[outer]=boundary
    assert np.max(abs(all_points.T@x-np.eye(3)*measure))<2e-16
    assert np.linalg.norm(all_points.sum(axis=0))<1e-14
    return all_points,measure,np.linalg.norm(area,axis=1).sum()


def replay_initial(x,vol):
    # Original A continuous arithmetic, not float CUDA ordering. The source has zero load at t=0.
    # Reuse the documented Wendland derivative and compare its *unit-load* scalar moment.
    pairs=cKDTree(x).query_pairs(2*H,output_type="ndarray")
    raw=np.zeros_like(x)
    for start in range(0,len(pairs),65536):
        i,j=pairs[start:start+65536].T
        dr=x[i]-x[j]
        rr=np.linalg.norm(dr,axis=1)
        fac=-2.08891/H**5*(1-.5*rr/H)**3
        ai=(-2*vol[i]*vol[j]*fac)[:,None]*dr
        for d in range(3):
            raw[:,d]+=np.bincount(i,weights=ai[:,d],minlength=len(x))
            raw[:,d]-=np.bincount(j,weights=ai[:,d],minlength=len(x))
    return raw


def load_tensors():
    yield "hydrostatic",np.eye(3)
    for i in range(3):
        for j in range(i,3):
            stress=np.zeros((3,3))
            stress[i,j]=stress[j,i]=1.
            yield AXES[i]+AXES[j],stress


def audit_tractions(part, source, x, area, outer, interior_weight):
    radial=np.linalg.norm(x,axis=1)
    unit=x/radial[:,None]
    rates=x/R
    v_inside=rates*interior_weight[:,None]
    magnitudes={}
    tensor=[]
    for name,stress in load_tensors():
        f=-Q*(area@stress.T)
        moment=-f.T@x
        result=f.sum(axis=0)
        torque=np.cross(x,f).sum(axis=0)
        row=dict(part=part,traction=source,stress_template=name)
        for d in range(3):
            row["net_force_"+AXES[d]+"_N"]=result[d]
            row["torque_"+AXES[d]+"_Nm"]=torque[d]
            for e in range(3):
                row["W_"+AXES[d]+AXES[e]+"_W"]=moment[d,e]
        tensor.append(row)
        if name=="hydrostatic":
            dilation=-np.einsum("ij,ij->i",rates,f)
            magnitudes=dict(dilation_W_per_unit_strainrate=float(np.trace(moment)),
                radial_unit_speed_W=float(-np.sum(unit*f)),radial_affine_W_per_1m_s_at_a=float(dilation.sum()),
                inner_radial_affine_work_W=float(dilation[~outer].sum()),
                inner_radial_affine_fraction=float(dilation[~outer].sum()/dilation.sum()),
                interior_test_W=float(-np.sum(v_inside*f)),
                net_force_norm_N=float(np.linalg.norm(result)),torque_norm_Nm=float(np.linalg.norm(torque)))
    return tensor,magnitudes


def analytic_tensors():
    rows=[]
    for name,stress in load_tensors():
        row=dict(part="reference",traction="nominal_radius_analytic",stress_template=name)
        for i in range(3):
            row["net_force_"+AXES[i]+"_N"]=row["torque_"+AXES[i]+"_Nm"]=0.
            for j in range(3):
                row["W_"+AXES[i]+AXES[j]+"_W"]=Q*VSPHERE*stress[i,j]
        rows.append(row)
    return rows


def run():
    base=capture(0)
    x0=base["Posd"]
    r0=np.linalg.norm(x0,axis=1)
    outer=np.isclose(r0,R,atol=1e-12,rtol=0)
    assert len(x0)==37173 and outer.sum()==5153 and not np.any(base["HydroMechLoadAce"])
    tri=outer_faces(x0[outer])
    assert len(tri)==10302
    interior_weight=1-(r0/R)**2
    interior_weight[outer]=0. # enforce the boundary condition exactly, including roundoff in r0
    rows=analytic_tensors()
    hist=[]
    for part in (0,64,416,576):
        a=capture(part) if part else base
        assert np.array_equal(base["Idp"],a["Idp"]) and np.array_equal(np.isin(a["FSType"],[2,3]),outer)
        x=a["Posd"]
        vol=a["PoroCurrentVolume"]
        area,vface,aface=facet_measures(x,outer,tri)
        raw=replay_initial(x,vol) if not part else -(
            (a["PoroMixtureDensity"]*vol/Q)[:,None]*a["HydroMechLoadAce"].astype(float))
        if not part:
            assert abs(np.trace(raw.T@x)/(3*VSPHERE)-1.0633079740977176)<1e-6
        factor=3*vface/np.trace(raw.T@x)
        entry=dict(part=part,time_s=part/8192,tau_s=part/8192-1/128,
                   volume_native_m3=float(vol.sum()),volume_facets_m3=vface,facets_area_m2=aface,
                   diagnostic_raw_scale_to_facet_affine=factor,
                   raw_definition="frozen_initial_unit_q" if not part else "saved_mass_times_stage_LoadAce_proxy")
        for label,vec in (("facet",area),("raw",raw),("raw_affine_matched",factor*raw)):
            tensors,items=audit_tractions(part,label,x,vec,outer,interior_weight)
            rows.extend(tensors)
            entry[label]=items
        assert entry["facet"]["interior_test_W"]==0.
        assert abs(entry["raw_affine_matched"]["dilation_W_per_unit_strainrate"]/entry["facet"]["dilation_W_per_unit_strainrate"]-1)<2e-12
        hist.append(entry)
    uold=float(hist[0]["volume_native_m3"])
    report=dict(tag=TAG,q_Pa=Q,radius_m=R,surface_nodes=int(outer.sum()),triangles=len(tri),
        native_soil_nodes=len(x0),sources=[str(DATA/f"Part_{part:04d}.bi4") for part in (0,64,416,576)],
        analytic_sphere_volume_m3=VSPHERE,analytic_sphere_area_m2=4*np.pi*R**2,
        affine_work_discrepancy_per_axis_W=Q*(uold-VSPHERE),
        affine_work_discrepancy_dilation_W=3*Q*(uold-VSPHERE),frames=hist)
    return rows,report


def draw(report,graph):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data=report["frames"]
    figs,axes=plt.subplots(1,2,figsize=(10.6,4.1),layout="constrained")
    names=["initial\nunit load","closed\nPart 64","peak\nPart 416","last\nPart 576"]
    pos=np.arange(4)
    for ax,key in zip(axes,["dilation_W_per_unit_strainrate","interior_test_W"]):
        for i,(basis,color,title) in enumerate([("facet","#366584","Triangular facets"),("raw","#bf6c35","Kernel"),
                                                ("raw_affine_matched","#54826b","Kernel, scaled to facet dilation")]):
            ax.bar(pos+(i-1)*.24,[row[basis][key] for row in data],.24,color=color,label=title)
        ax.set_xticks(pos, names)
        ax.grid(axis="y",alpha=.23)
    axes[0].set_title("Contraction at 1/s along each axis")
    axes[1].set_title("Interior motion, fixed outer surface")
    for ax in axes:
        ax.set_ylabel("Virtual power [W]")
    figs.legend(*axes[0].get_legend_handles_labels(),loc="outside lower center",ncol=3)
    figs.savefig(graph,dpi=160)
    plt.close(figs)


def write(rows,report):
    tab=TESTS/"figures"/(TAG+".csv")
    graph=tab.with_suffix(".png")
    result=TESTS/"logs"/(TAG+".json")
    if any(p.exists() for p in (tab,graph,result)):
        raise FileExistsError("Existing data preserved. Omit --write to recompute.")
    draw(report,graph)
    with tab.open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    with result.open("x") as f:
        json.dump(report,f,indent=2,allow_nan=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    rows,report=run()
    if args.write:
        write(rows,report)
    print(json.dumps(report))
