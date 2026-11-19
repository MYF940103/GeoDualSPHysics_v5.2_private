"""Hold the P3 snapshot fixed and change only pressure supplied to the soil momentum force."""
import argparse
import json
from pathlib import Path
from cryer_p3_peak_shells import ordered
from cryer_shell_equilibrium import TESTS, Reference, T_D, R, Q, need, reference_fields, write
from cryer_p3_verify_r1 import CENTER
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

TAG="cryer_peak_momentum_shadow_r2"


def apply_symmetric(kk,ij,g):
    out=kk*g
    # JSphGpuSingle.cpp writes SigmaState_ij as (xy, yz, xz).
    xy,yz,xz=ij.T
    out[:,0]+=xy*g[:,1]+xz*g[:,2]
    out[:,1]+=xy*g[:,0]+yz*g[:,2]
    out[:,2]+=xz*g[:,0]+yz*g[:,1]
    return out


def forces(st,p_ref):
    x=st["Posd"]; v=st["PoroCurrentVolume"];rho=st["PoroMixtureDensity"]
    mass=rho*v
    # Effective stress in the actual GPU momentum loop is read through a float display.
    kk=st["SigmaState_kk"].astype("f4").astype(float)
    ij=st["SigmaState_ij"].astype("f4").astype(float)
    p=st["PorePress"].astype(float)
    h=float(np.float32(.0045))
    pairs=cKDTree(x).query_pairs(2*h,output_type="ndarray")
    blocks=np.zeros((5,len(x),3))
    direct_delta=np.zeros_like(x)
    for start in range(0,len(pairs),65536):
        i,j=pairs[start:start+65536].T
        dr=x[i]-x[j]
        r=np.linalg.norm(dr,axis=1)
        w=float(np.float32(-2.08891/h**4))/h*np.maximum(1-r/(2*h),0.)**3
        g=(w*v[i]*v[j])[:,None]*dr
        stress=apply_symmetric(kk[i]+kk[j],ij[i]+ij[j],g)
        load=2*Q*g
        native=-(p[i]+p[j])[:,None]*g
        analytic=-(p_ref[i]+p_ref[j])[:,None]*g
        d=-((p_ref[i]-p[i])+(p_ref[j]-p[j]))[:,None]*g
        for store,F in zip(blocks,(stress,load,native,analytic,stress+load+native)):
            np.add.at(store,i,F);np.add.at(store,j,-F)
        np.add.at(direct_delta,i,d);np.add.at(direct_delta,j,-d)
    raw=(blocks[0]+blocks[1]+blocks[2])/mass[:,None]
    shadow=(blocks[0]+blocks[1]+blocks[3])/mass[:,None]
    d=direct_delta/mass[:,None]
    need(np.max(abs(raw-blocks[4]/mass[:,None]))<1e-9,"Stress/load/pore recombination")
    need(np.max(abs((shadow-raw)-d))<1e-9,"Independent delta-pressure kernel")
    # Pressure-only pair changes are central; check net force and torque explicitly.
    net=np.sum(direct_delta,axis=0)
    torque=np.sum(np.cross(x,direct_delta),axis=0)
    need(np.linalg.norm(net)<1e-8 and np.linalg.norm(torque)<1e-9,"Delta pair force and torque")
    return raw,shadow,d,blocks[1]/mass[:,None],len(pairs),np.linalg.norm(net),np.linalg.norm(torque)


def main(output,review):
    basis=np.eye(3)
    sample=apply_symmetric(np.tile([1,2,3],(3,1)),np.tile([4,5,6],(3,1)),basis)
    need(np.array_equal(sample,np.array([[1,4,6],[4,2,5],[6,5,3]])),"Native tensile/shear component layout")
    stage=json.loads((review/"peak_rejected.json").read_text(encoding="utf8"))
    need(not stage["peak_qualified"] and stage["native"]["frames"]==577,"Completed original peak review")
    figdir=TESTS/"figures"
    csvs=[figdir/(TAG+"_"+s+".csv") for s in ("shells","center18","regions")]
    log=TESTS/"logs"/(TAG+".check.json")
    figure=figdir/(TAG+".png")
    need(not any(p.exists() for p in csvs+[log,figure]),"Preserve prior force review")
    hist=pd.read_csv(review/"physical"/"native_and_theory.csv",float_precision="round_trip")
    initial=ordered(output/"data",0,["Posd"])["Posd"]
    bins=np.rint(np.linalg.norm(initial,axis=1)/.0025).astype(int)
    need(np.array_equal(np.flatnonzero(bins==1)+8,CENTER),"Material center IDs")
    r=np.arange(1,21)*.0025
    ref=Reference(.3,finite=False);ref.cv=ref.H*ref.kappa;ref.decay=ref.xi**2*ref.cv/R**2
    shells=[];local=[];regions=[];checks=[]
    for part in (64,139,416):
        tau=hist.iloc[part].tau_s
        st=ordered(output/"data",part,["Posd","PorePress","PoroCurrentVolume","PoroMixtureDensity",
            "SigmaState_kk","SigmaState_ij","HydroMechLoadAce","FSType"])
        analytic=reference_fields(ref,tau,r)[0][bins-1]
        fs=np.isin(st["FSType"],(2,3))
        need(np.array_equal(fs,bins==20),"True current drainage surface")
        if tau>0:
            need(np.max(abs(analytic[fs]))<1e-8 and np.all(st["PorePress"][fs]==0),"Open boundary")
            analytic[fs]=0.
        need(abs(np.mean(analytic[bins==1])-hist.iloc[part].M0_r18_Pa)<1e-7,"Reference center pressure")
        raw,shadow,d,load,pairs,net,torque=forces(st,analytic)
        outward=st["Posd"]/np.linalg.norm(st["Posd"],axis=1)[:,None]
        load_diff=np.linalg.norm(load-st["HydroMechLoadAce"],axis=1)
        checks.append(dict(part=part,tau_s=tau,pairs=pairs,delta_net_force_N=net,delta_net_torque_Nm=torque,
            saved_load_vector_RMS_difference_m_s2=float(np.sqrt(np.mean(load_diff**2))),
            saved_load_vector_RMS_m_s2=float(np.sqrt(np.mean(np.sum(st["HydroMechLoadAce"].astype(float)**2,axis=1))))))
        values={}
        for key,vec in (("raw",raw),("M0",shadow),("delta",d)):
            values[key]=-np.einsum("ij,ij->i",outward,vec)
        shell_mean={key:np.array([value[bins==j].mean() for j in range(1,21)]) for key,value in values.items()}
        hp={key:.5*(ave[1:-1]-.5*(ave[:-2]+ave[2:])) for key,ave in shell_mean.items()}
        for j in range(1,21):
            row=dict(part=part,tau_s=tau,shell=j,r0_over_a=j/20,count=int(sum(bins==j)))
            for key in values:
                row[key+"_mean_inward_m_s2"]=shell_mean[key][j-1]
                row[key+"_alternating_m_s2"]=hp[key][j-2] if 1<j<20 else None
            shells.append(row)
        for group,use in (("center18",bins==1),("inner10",bins<=10),("all",bins>0),("outer",bins==20)):
            row=dict(part=part,tau_s=tau,region=group,count=int(use.sum()))
            for key,vec in (("raw",raw),("M0",shadow),("delta",d)):
                row[key+"_mean_inward_m_s2"]=values[key][use].mean()
                row[key+"_vector_rms_m_s2"]=np.sqrt(np.mean(np.sum(vec[use]**2,axis=1)))
                row[key+"_alt_rms_m_s2"]=(np.sqrt(np.mean(hp[key][:9 if group=="inner10" else 18]**2))
                                             if group in ("all","inner10") else None)
            regions.append(row)
        for i in np.flatnonzero(bins==1):
            row=dict(part=part,tau_s=tau,native_id=int(i+8),p_native_Pa=float(st["PorePress"][i]),p_M0_Pa=analytic[i])
            for key,vec in (("raw",raw),("M0",shadow),("delta",d)):
                row[key+"_inward_m_s2"]=values[key][i]
                for axis,value in zip("xyz",vec[i]):row[key+"_"+axis+"_m_s2"]=value
            local.append(row)
    for csvpath,rows in zip(csvs,(shells,local,regions)):write(csvpath,rows)
    with log.open("x",encoding="utf8") as f:
        json.dump(dict(input="returned P3, already native-reviewed",checks=checks,
            term="J-volume, J-mixture-mass, saved effective stress, raw confinement and PorePress; only pressure in the mechanical pair changes.",
            limits="Frozen saved body; double distances and pair sums. Velocity/AV/damping and the unsaved force substages are excluded."),
            f,indent=2,allow_nan=False)
    import matplotlib.pyplot as plt
    df=pd.DataFrame(shells)
    fig,axes=plt.subplots(1,2,figsize=(11.6,4.3),layout="constrained")
    for ax,part,title in ((axes[0],139,"Before center peak"),(axes[1],416,"At center peak")):
        data=df.loc[df.part==part]
        for key,label,mark in (("raw","Native pressure","o"),("M0","Prescribed M0 pressure","x")):
            ax.plot(data.r0_over_a,data[key+"_mean_inward_m_s2"],marker=mark,ms=4,label=label)
        ax.set(xlabel="Initial material radius / sphere radius",ylabel="Mean inward acceleration (m/s²)",title=title)
        ax.grid(alpha=.2);ax.axhline(0,color=".55",lw=.8);ax.legend()
    fig.savefig(figure,dpi=180);plt.close(fig)
    print(pd.DataFrame(regions).to_string(index=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output",type=Path);ap.add_argument("review",type=Path)
    args=ap.parse_args();main(args.output,args.review)
