"""Raw versus pair-adjoint traction with the exact coupled M0 peak pressure and elastic stress."""
import argparse
import json
from pathlib import Path
from cryer_shell_equilibrium import TESTS, Reference, Q, R, T_D, need, write
from cryer_p3_peak_shells import ordered
from cryer_load_pair_r1 import correction, batches, add_pair, pair_components, AFFINE_L
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

TAG="cryer_peak_paired_manufactured_r1"


def radial_state(ref,r,tau):
    z=np.outer(r/R,ref.xi)
    weights=Q*ref.amplitude*np.exp(-ref.decay*tau)
    average=ref.mean@weights
    C=ref.beta*average-ref.H/ref.K*Q
    p=(np.sinc(z/np.pi)-ref.sx)@weights
    eps=(p+C)/ref.H
    phi=(np.sin(z)-z*np.cos(z))/z**3
    tang=(C/3+(phi-ref.sx/3)@weights)/ref.H
    radial=eps-2*tang
    lam=ref.K-2*ref.G/3
    return p,2*ref.G*radial+lam*eps,2*ref.G*tang+lam*eps,eps


def main(output,review):
    phys=json.loads((review/"physical"/"physical_review.json").read_text(encoding="utf8"))
    tau=phys["native_peak_tau_s"]
    part=round((tau+T_D)*8192)
    need(part==416 and part*2.**-13==tau+T_D,"Actual sampled peak")
    init=ordered(output/"data",0,["Posd","PoroCurrentVolume","PoroMixtureDensity","FSType"])
    current=ordered(output/"data",part,["Posd","PoroCurrentVolume","PoroMixtureDensity","FSType"])
    folder=TESTS/"figures"
    files=[folder/(TAG+s) for s in ("_regions.csv","_shells.csv",".png")]
    log=TESTS/"logs"/(TAG+".check.json")
    need(not any(f.exists() for f in files+[log]),"Preserve existing evidence")
    x0=init["Posd"];radius=np.linalg.norm(x0,axis=1)
    idx=np.rint(radius/.0025).astype(int)-1
    r=np.arange(1,21)*.0025
    ref=Reference(.3,finite=False);ref.cv=ref.H*ref.kappa;ref.decay=ref.xi**2*ref.cv/R**2
    p,rr,tt,eps=radial_state(ref,r,tau)
    d=1e-20
    cp,cr,_,_=radial_state(ref,r.astype(complex)+1j*d,tau)
    div_T=np.imag(cr-cp)/d+2*(rr-tt)/r
    need(np.max(abs(div_T))<1e-4 and abs(rr[-1]-p[-1]+Q)<1e-6 and abs(p[-1])<1e-7,
         "Analytical divergence, pressure and traction")
    trace_error=np.max(abs((rr+2*tt)/3-ref.K*eps))
    theory_table=pd.read_csv(review/"physical"/"native_and_theory.csv").set_index("part")
    need(trace_error<1e-7 and abs(p[0]-theory_table.loc[part,"M0_r18_Pa"])<1e-6,
         "Effective stress trace and same-time analytical center shell")
    unit=x0/radius[:,None]
    S=tt[idx,None,None]*np.eye(3)+(rr-tt)[idx,None,None]*unit[:,:,None]*unit[:,None,:]
    shifted=S+(Q-p[idx,None,None])*np.eye(3)
    h=float(np.float32(.0045))
    stats=[];regional=[];shellrows=[]
    for geometry,state in (("initial_reference_sphere",init),("mapped_same_reference_field_to_saved_geometry",current)):
        x=state["Posd"];V=state["PoroCurrentVolume"];rho=state["PoroMixtureDensity"];mass=V*rho
        pairs=cKDTree(x).query_pairs(2*h,output_type="ndarray")
        corr,cert=correction(x,mass,rho,h,pairs)
        out=np.zeros((2,len(x),3))
        for block,(i,j,dr,g) in enumerate(batches(x,pairs,h)):
            multiplier=V[i]*V[j]
            prod=lambda s,v:np.einsum("ijm,im->ij",s,v)
            raw=prod(shifted[i]+shifted[j],g)
            adj=prod(shifted[i],prod(corr[i],g))+prod(shifted[j],prod(corr[j],g))
            if block==0:
                sl=slice(0,128)
                ii,jj=i[sl],j[sl]
                prior_D=pair_components(S[ii],S[jj],p[idx[ii]],p[idx[jj]],rho[ii],rho[jj],
                                        corr[ii],corr[jj],g[sl])[2][0].sum(axis=0)
                need(np.allclose(prior_D*rho[ii,None]*rho[jj,None],adj[sl],rtol=1e-8,atol=1e-2),
                     "Equivalence to the retained coupled D operator")
            for force,F in zip(out,(raw,adj)):
                ff=multiplier[:,None]*F
                add_pair(force,i,j,ff,-ff)
        both={}
        for label,F in zip(("A_raw","D_pair_adjoint"),out):
            actual=F/mass[:,None]
            er=x/np.linalg.norm(x,axis=1)[:,None]
            inward=-np.einsum("ij,ij->i",actual,er)
            shell=np.array([inward[idx==j].mean() for j in range(20)])
            for j,mean in enumerate(shell):
                shellrows.append(dict(geometry=geometry,operator=label,shell=j+1,r0_over_a=(j+1)/20,
                    mean_inward_m_s2=mean,vector_rms_m_s2=np.sqrt(np.mean(np.sum(actual[idx==j]**2,axis=1)))))
            for name,mask in (("center18",idx==0),("inner10",idx<10),("all",idx>=0),("true_surface",np.isin(state["FSType"],(2,3)))):
                need(mask.any() and (name!="true_surface" or np.array_equal(mask,idx==19)),"True surface")
                regional.append(dict(geometry=geometry,operator=label,region=name,count=int(mask.sum()),
                    vector_rms_m_s2=np.sqrt(np.mean(np.sum(actual[mask]**2,axis=1))),
                    mean_inward_m_s2=inward[mask].mean(),max_vector_m_s2=np.max(np.linalg.norm(actual[mask],axis=1))))
            expected=-np.sum(V*np.einsum("nij,ij->n",shifted,AFFINE_L))
            measured=np.sum(F*(x@AFFINE_L.T))
            if label=="D_pair_adjoint":
                need(abs(measured-expected)<1e-10,"Affine power identity")
            both[label]=dict(net_force_N=float(np.linalg.norm(F.sum(axis=0))),
                             net_torque_Nm=float(np.linalg.norm(np.cross(x,F).sum(axis=0))),
                             measured_affine_power_W=measured,expected_affine_power_W=expected)
        stats.append(dict(geometry=geometry,pairs=len(pairs),correction=cert,force=both))
    write(files[0],regional);write(files[1],shellrows)
    with log.open("x",encoding="utf8") as f:
        json.dump(dict(part=part,tau_s=tau,pressure_center_Pa=p[0],surface_pressure_Pa=p[-1],
             surface_traction_plus_q_Pa=rr[-1]-p[-1]+Q,max_abs_analytic_div_total_Pa_per_m=np.max(abs(div_T)),
             trace_check_max_Pa=trace_error,geometries=stats,
             field="M0 pressure and small-strain radial/tangential Hookean stress at original material radii. For the mapped geometry only positions, volumes and mixture inertia change."),
             f,indent=2,allow_nan=False)
    frame=pd.DataFrame(shellrows)
    import matplotlib.pyplot as plt
    fig,(aa,bb)=plt.subplots(1,2,figsize=(11,4.3),layout="constrained")
    primary=frame[frame.geometry=="initial_reference_sphere"]
    for name,grp in primary.groupby("operator"):
        for ax,col in ((aa,"vector_rms_m_s2"),(bb,"mean_inward_m_s2")):
            ax.plot(grp.r0_over_a,grp[col],marker="o",ms=3,label=name.replace("_"," "))
    for ax,title in ((aa,"Vector RMS"),(bb,"Mean inward component")):
        ax.set(xlabel="Initial material radius / sphere radius",ylabel="Acceleration (m/s²)",title=title)
        ax.grid(alpha=.2);ax.axhline(0,color=".55",lw=.8);ax.legend()
    fig.savefig(files[2],dpi=180);plt.close(fig)
    print(pd.DataFrame(regional).to_string(index=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output",type=Path);ap.add_argument("review",type=Path)
    args=ap.parse_args();main(args.output,args.review)
