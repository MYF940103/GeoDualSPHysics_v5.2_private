"""Compare native constitutive volume, reference displacement and fixed-connectivity shell volumes."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
from cryer_shell_equilibrium import (NATIVE, TESTS, Q, R, SOIL, TOTAL, Reference, T_D, need,
                                     reference_fields, sphere_weights, write)

TAG="cryer_material_shell_volume_r1"


def faces(points):
    hull=ConvexHull(points)
    tri=hull.simplices.copy()
    need(len(hull.vertices)==len(points), "Missing initial surface vertices")
    i,j,k=tri.T
    n=np.cross(points[j]-points[i],points[k]-points[i])
    flip=np.sum(n*hull.equations[:,:3],axis=1)<0
    tri[flip]=tri[flip][:,[0,2,1]]
    return tri


def volume(points,tri):
    centered=points-points.mean(axis=0)
    i,j,k=tri.T
    v=np.sum(centered[i]*np.cross(centered[j],centered[k]),axis=1)/6
    need(np.all(v>0),"Shell folds or centroid no longer interior")
    return v.sum()


def plot(rows,path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    need(not path.exists(),"Preserve prior figure")
    frame=pd.DataFrame(rows)
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.2),layout="constrained")
    for part,ax,title in ((64,axes[0],"Before drainage"),(417,axes[1],"At sampled center pressure peak")):
        subset=frame.loc[frame.part==part]
        for field,style,label in (("hull_enclosed_volume_change","o-","Volume from material positions"),
                                  ("enclosed_J_change","s--","Enclosed mean from particle J"),
                                  ("reference_enclosed_eps","k:","Finite-Kw continuum")):
            ax.plot(subset.r0_over_a,subset[field]*100,style,label=label,ms=4)
        ax.set(xlabel="Reference shell radius / sphere radius",ylabel="Enclosed volume change (%)",title=title)
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8)
    fig.savefig(path,dpi=180);plt.close(fig)


def main():
    op=TESTS/"figures"/(TAG+".csv");report=TESTS/"logs"/(TAG+".check.json")
    need(not op.exists() and not report.exists(),"Preserve prior review")
    data=np.memmap(NATIVE/"common26.bin",offset=12,dtype="<f8",shape=(577,1+TOTAL*26),mode="r")
    ids=pd.read_csv(NATIVE/"native_ids.csv",float_precision="round_trip").iloc[SOIL]
    r=np.arange(1,21)*.0025
    shell=np.rint(ids.r0_m.to_numpy()/.0025).astype(int)-1
    x0=ids[["x0","y0","z0"]].to_numpy()
    initial=data[0,1:].reshape(TOTAL,26)[SOIL,:3]
    need(np.array_equal(initial,x0),"Initial materials and native order")
    face=[];V0=[];weights=[]
    F=np.array([[1.1,.03,.02],[.01,.9,.06],[0,-.01,1.02]])
    for i in range(len(r)):
        pos=x0[shell==i]
        tri=faces(pos)
        v0=volume(pos,tri)
        need(abs(volume(pos@F.T+np.array([1.,2.,3.]),tri)/v0-np.linalg.det(F))<2e-12,"Affine shape volume")
        face.append(tri);V0.append(v0)
        # Normalize the shell-edge integral using the current ball's radius.
        w=sphere_weights(r[:i+1]) if i==19 else sphere_weights(r[:i+1]/r[i]*R)
        weights.append(w)
    ref=Reference(.3)
    results=[]
    for part in (64,65,408,417,576):
        x=data[part,1:].reshape(TOTAL,26)[SOIL]
        tau=data[part,0]-T_D
        p,mean,c=reference_fields(ref,tau,r)
        local_ref=(p+c)/ref.H
        if tau==0:
            enclosed_ref=local_ref.copy()
        else:
            z=np.outer(r/R,ref.xi)
            phi=(np.sin(z)-z*np.cos(z))/z**3
            w=ref.amplitude*np.exp(-ref.decay*tau)
            enclosed_ref=-Q/ref.K+3*Q/ref.H*((phi+(ref.beta*ref.mean-ref.sx)/3)@w)
        logs=np.log(x[:,8]);eps=np.mean(x[:,[10,13,15]],axis=1)/ref.K
        J=np.array([x[shell==i,8].mean() for i in range(len(r))])
        for i,rs in enumerate(r):
            mask=shell==i
            change=volume(x[mask,:3],face[i])/V0[i]-1
            volume_by_J=weights[i]@(J[:i+1]-1)
            error_by_rule=weights[i]@local_ref[:i+1]-enclosed_ref[i]
            results.append(dict(part=part,tau_s=tau,r0_over_a=rs/R,shell_ids=int(mask.sum()),
              hull_enclosed_volume_change=change,shell_J_change=J[i]-1,enclosed_J_change=volume_by_J,
              enclosed_J_minus_shape=volume_by_J-change,reference_lib_local_eps=local_ref[i],
              reference_enclosed_eps=enclosed_ref[i],reference_rule_error=error_by_rule,
              tr_sigma_over_3K=float(eps[mask].mean()),logJ=float(logs[mask].mean()),
              max_abs_logJ_minus_tr_sigma_over_3K=float(abs(logs[mask]-eps[mask]).max())))
    write(op,results)
    with report.open("x",encoding="utf8") as f:
        json.dump(dict(affine_fixture=True,source="A_finiteKw",frames=[64,65,408,417,576],
          subsets=[z for z in results if z["part"] in (64,417) and int(round(20*z["r0_over_a"])) in (1,2,4,10,20)],
          interpolation="J from actual radial nodal means, constant inside first measured shell, linear between radii",
          signed_volume="same oriented polyhedral triangles through all times; each positive about centroid"),f,indent=2,allow_nan=False)
    plot(results,TESTS/"figures"/(TAG+".png"))
    print(report)


if __name__=="__main__":main()
