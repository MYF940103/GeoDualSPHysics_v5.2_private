"""Cold, ramp/hold/open Cryer radial shell response on two separately assembled mechanical operators."""
import os
for key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key]="1"
import json

import numpy as np
import pandas as pd
from scipy.linalg import expm, solve
from scipy.optimize import minimize_scalar

from cryer_coupled_shell_modes import T, DT, R, LONG, HYD, RHOW, N0, DAMP
from cryer_p3_peak_shells import ordered
from cryer_p3_verify_r1 import snapshot, SOIL, TOTAL
from cryer_live_history_review import read_frame

TAG="cryer_shell_ramp_open_r2"
TR=2.**-8
TD=2.**-7
Q=10000.
SHELLS=[0,16,17,19]


class Phase:
    def __init__(self,B,C,label,storage,closed):
        m=20 if closed else 19
        self.m=m
        self.storage=storage
        k=B["K"];D=B["D"];P=B["P"];F=B["F"][:,0]
        lap=B["La"].copy();dk=B["DK"].copy();dp=B["DP"].copy()
        df=B["DF"][:,0].copy();dv=D.copy()
        if closed:
            for dest,key in [(lap,"lap"),(dk,"Ku"),(dp,"P"),(dv,"vel")]:
                dest[-1]+=C[label+"_"+key]
            df[-1]+=C[label+"_F"][0]
        a=HYD*(lap+RHOW*dp)[:m,:m]
        b=HYD*RHOW*dk[:m]
        c=-D[:m]-HYD*RHOW*DAMP*dv[:m]
        h=HYD*RHOW*df[:m]
        n=40+(m if storage else 0)
        A=np.zeros((n,n));f=np.zeros(n);pi=np.zeros((m,n));dq=np.zeros(m)
        A[:20,20:40]=np.eye(20);A[20:40,:20]=k
        A[20:40,20:40]=-DAMP*np.eye(20);f[20:40]=F
        if storage:
            A[20:40,40:]=P[:,:m];A[40:]=np.c_[b,c,a]/storage;f[40:]=h/storage
            pi[:,40:]=np.eye(m)
        else:
            eliminate=-solve(a,np.column_stack((b,c,h)))
            pi=eliminate[:,:40];dq=eliminate[:,40]
            A[20:]+=P[:,:m]@pi;f[20:]+=P[:,:m]@dq
        units=np.r_[np.full(20,R/LONG),np.full(20,1000*R/LONG),np.ones(n-40)]
        self.units=units
        self.o=pi*units[None,:];self.dq=dq
        self.a=A*units[None,:]/units[:,None];self.f=f/units
        self.z=np.zeros((n+2,n+2))
        self.z[:n,:n]=self.a;self.z[:n,n]=self.f;self.z[n,n+1]=1
        march=expm(DT*self.z)
        self.E=march[:n,:n];self.g=march[:n,n];self.r=march[:n,n+1]
        self.D=D
        self.stats={"storage_Pa_inverse":storage,"n_pressure":m,"row_cond":float(np.linalg.cond(a)),
                    "row_rank":int(np.linalg.matrix_rank(a)),"spectral_abscissa_per_s":float(np.max(np.real(np.linalg.eigvals(self.a))))}
        if not storage:
            self.stats["M0_relative_residual"]=float(np.max(abs(a@eliminate+np.c_[b,c,h])/np.maximum(1.,np.max(abs(np.c_[b,c,h]),axis=0))))
            if self.stats["M0_relative_residual"]>1e-11:raise ValueError("M0 algebraic constraint")

    def pressure(self,y,q):
        p=self.o@y+self.dq*q
        return np.r_[p,0.] if self.m==19 else p

    def advance(self,y,q,r=0.):
        return self.E@y+self.g*q+self.r*r

    def direct(self,y,q,r,t):
        return (expm(t*self.z)@np.r_[y,q,r])[:-2]


def row(label,model,protocol,step,phase,y,q,kind):
    p=Q*phase.pressure(y,q);physical=y*phase.units*Q
    dJ=phase.D@physical[:20]
    result=dict(operator=label,model=model,load_clock=protocol,step=step,t_s=step*DT,
                tau_s=(step-4096)*DT,phase=kind,load_Pa=Q*q)
    for j in SHELLS:
        result[f"p{j+1}_Pa"]=p[j];result[f"u{j+1}_mm"]=1000*physical[j]
        result[f"v{j+1}_m_s"]=physical[20+j];result[f"Jlin{j+1}_minus1"]=dJ[j]
    return result


def native_observations():
    mesh=np.load(T/"outputs/cryer_tet_reference_r1.npz")
    mask=mesh["material_shell"]
    name="CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    server=T/"outputs"/name/name/"data"
    finite=np.memmap(T/"outputs/upl_cryer_freebody_peak_GPU_r1_native/common26.bin",offset=12,
                     dtype="<f8",mode="r",shape=(577,1+TOTAL*26))
    out=[]
    def extract(name,step,p):
        out.append(dict(observation=name,step_in_B_clock=step,time_s=step*DT,
                        **{f"p{j+1}_Pa":np.mean(p[mask==j+1],dtype=float) for j in SHELLS}))
    for part in [0,1,16,32,48,64,65,66,80,102,384,416,417,421,576]:
        p=ordered(server,part,["PorePress"])["PorePress"]
        extract("server_P3_B",part*64,p)
        if finite[part,0]!=part*64*DT:raise ValueError("Finite A clock")
        extract("explicit_A",part*64,finite[part,1:].reshape(TOTAL,26)[SOIL,6])
    dense=T/"outputs/cryer_livehist_gpu_r1_dense4"
    params=(dense/"Run.out").read_text(errors="replace")
    if not all(x in params for x in ["HydroMechTopLoadQ0: 10000","HydroMechTopLoadRampTime: 0.00390625",
                                    "HydroMechDrainageStartTime: 0.0078125","HydroMechModel=2"]):
        raise ValueError("Changed dense4 configuration")
    for part in [1,2,3,4]:
        _,_,a,_=read_frame(dense/"data"/f"Part_{part:04d}.bi4",part,part,DT,True)
        extract("local_cold_P3_B",part,a["PorePress"][SOIL])
    pp=T/"outputs/cryer_p3_gpu_drain4097_r1/data/Part_0065.bi4"
    a,_=snapshot(pp,65,4097,DT);extract("local_first_open_P3_B",4097,a["PorePress"][SOIL])
    return pd.DataFrame(out)


def unstable_closed(label,protocol,closed):
    # The finite-round original P3 is not this exactly eliminated continuous M0 equation.
    # Demonstrate an eigenmode independently of any accumulated roundoff or clipping.
    values,vecs=np.linalg.eig(closed.a)
    pos=np.argmax(values.real)
    lam=values[pos];vec=vecs[:,pos]
    if abs(lam.imag)>1e-8 or lam.real<1e4:raise ValueError("Expected real closed growing mode")
    lam=lam.real;vec=vec.real
    resid=np.linalg.norm(closed.a@vec-lam*vec)/np.linalg.norm(lam*vec)
    gain=np.exp(DT*lam)
    prop=np.linalg.norm(closed.E@vec-gain*vec)/np.linalg.norm(gain*vec)
    if max(resid,prop)>3e-10:raise ValueError("Unverified growing mode")
    p=closed.o@vec;p=p/p[np.argmax(abs(p))]
    report=dict(growth_per_s=lam,e_folding_us=1e6/lam,gain_single_dt=gain,
                relative_eigen_residual=resid,relative_independent_expm_gain_residual=prop,
                uniform_load_pmap_maxabs_per_Pa=float(np.max(abs(closed.dq-1))),
                scaled_mechanical_force_from_unit_load_maxabs=float(np.max(abs(closed.f))),
                eigen_pressure_by_shell_relative=p.tolist())
    y=np.zeros(40);records=[row(label,"M0",protocol,0,closed,y,0,"cold")]
    rate=1/TR if protocol=="continuous_linear" else 0.
    y=closed.advance(y,0,rate)
    records.append(row(label,"M0",protocol,1,closed,y,rate*DT,"closed"))
    return records,report


def march(label,model,protocol,closed,opened,theory):
    continuous=(protocol=="continuous_linear")
    y=np.zeros(len(closed.f));records=[]
    records.append(row(label,model,protocol,0,closed,y,0,"cold"))
    for step in range(1,4097):
        source=min((step-1)*DT/TR,1.);r=1/TR if continuous and step<=2048 else 0.
        q=source+r*DT
        y=closed.advance(y,source,r)
        if not np.isfinite(y).all():raise ValueError("Nonfinite state in closed integration")
        if step%64==0 or step in (1,2,2049,4095):
            records.append(row(label,model,protocol,step,closed,y,q,"closed"))
        if step==2048:ramp=y.copy()
        if step==1:p_first=Q*closed.pressure(y,q)[0]
    y_zero=np.zeros_like(y)
    if continuous:
        ramp2=closed.direct(y_zero,0.,1/TR,TR)
    else:
        n=len(y);block=np.eye(n+2)
        block[:n,:n]=closed.E;block[:n,n]=closed.g;block[n,n+1]=DT/TR
        ramp2=(np.linalg.matrix_power(block,2048)@np.r_[y_zero,0.,1.])[:n]
    close2=closed.direct(ramp2,1.,0,TD-TR)
    pp=closed.pressure(y,1)
    closed_check=Q*np.max(abs(pp-closed.pressure(close2,1)))
    if closed_check>5e-4:raise ValueError(f"Closed semigroup pressure {closed_check}")
    pre=records[-1]
    y0=y[:len(opened.f)].copy()
    pre_jump=Q*(opened.pressure(y0,1)-pp)
    records.append(row(label,model,protocol,4096,opened,y0,1,"open_right_limit"))
    npost=32768
    n=len(y0);press=np.empty(npost+1);press[0]=Q*opened.pressure(y0,1)[0]
    saved={};y=y0.copy();state_q=opened.dq[0]
    for step in range(1,npost+1):
        y=opened.advance(y,1)
        if not np.isfinite(y).all():raise ValueError("Nonfinite state in open integration")
        press[step]=Q*(opened.o[0]@y+state_q)
        if step%64==0 or step in (1,2,4,8,16,32):
            records.append(row(label,model,protocol,4096+step,opened,y,1,"open"))
        if step in (1,64,22016,32768):saved[step]=y.copy()
    cross=[]
    for step,ys in saved.items():
        yd=opened.direct(y0,1.,0.,step*DT)
        cross.append(Q*np.max(abs(opened.pressure(yd,1)-opened.pressure(ys,1))))
    if max(cross)>5e-3:raise ValueError(f"Open independent pressure {cross}")
    # True native save clocks define the peak window and RMS comparison.
    ids=np.rint(theory["tau_s"].to_numpy()/DT).astype(int)
    if not np.array_equal(ids,np.arange(0,npost+1,64)):raise ValueError("Actual server time ledger")
    active=theory.legacy_Tv.to_numpy()>=.005
    i0=ids[active][0];peakidx=i0+int(np.argmax(press[i0:]))
    peakrow=ids[active][np.argmax(press[ids[active]])]
    # Polishing is local to a sampled cycle and independently checked against its physical-state matrix exponential.
    fit=minimize_scalar(lambda tau:-Q*opened.pressure(opened.direct(y0,1,0.,tau),1)[0],
                        bounds=(max(peakidx-1,i0)*DT,min(peakidx+1,npost)*DT),method="bounded",options={"xatol":1e-14})
    trp,trt,ref=(12478.53263299281,.04192258568544373,"B_M0_Pa") if model=="M0" else (12439.176,.04205180291164746,"A_finite_Kw_Pa")
    mstart=int(np.argmax(press[:i0]));sstart=ids[1:][ids[1:]<i0]
    isaved=sstart[int(np.argmax(press[sstart]))]
    native_col="B_pressure_Pa" if model=="M0" else "A_pressure_Pa"
    summary=dict(operator=label,model=model,load_clock=protocol,first_cold_step_center_Pa=p_first,
                 closed_center_Pa=pre["p1_Pa"],closed_shell17_Pa=pre["p17_Pa"],closed_shell18_Pa=pre["p18_Pa"],
                 closed_shell20_Pa=pre["p20_Pa"],closed_outer_velocity_m_s=pre["v20_m_s"],
                 closed_outer_displacement_mm=pre["u20_mm"],center_jump_at_open_Pa=pre_jump[0],
                 first_open_step_Pa=press[1],first_server_open_save_Pa=press[64],
                 startup_including_right_limit_max_Pa=press[mstart],startup_max_tau_s=mstart*DT,
                 saved_startup_max_Pa=press[isaved],saved_startup_max_tau_s=isaved*DT,
                 mandel_sampled_peak_Pa=press[peakrow],mandel_sampled_tau_s=peakrow*DT,
                 continuous_local_peak_Pa=-fit.fun,continuous_local_tau_s=fit.x,
                 amplitude_error_pct=100*(-fit.fun/trp-1),peak_time_error_pct=100*(fit.x/trt-1),
                 mandel_theory_RMS_Pa=np.mean((press[ids[active]]-theory[ref].to_numpy()[active])**2)**.5,
                 mandel_actual_RMS_Pa=np.mean((press[ids[active]]-theory[native_col].to_numpy()[active])**2)**.5,
                 closed_direct_Pa=closed_check,open_direct_Pa=max(cross))
    return records,summary


def main():
    ops={"original":"cryer_coupled_shell_modes_r1_blocks","paired":"cryer_shell_tet_pair_r1_sph"}
    names=[T/"figures"/(TAG+s) for s in ("_history.csv","_summary.csv","_native.csv",".png")]
    check=T/"logs"/(TAG+".check.json")
    if any(x.exists() for x in [*names,check]):raise FileExistsError(TAG)
    theory=pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/matched_center_diagnosis.csv",float_precision="round_trip")
    C=np.load(T/"figures/cryer_shell_closed_rows_r1.npz")
    records=[];summary=[];checks={}
    obs=native_observations()
    for name,path in ops.items():
        B=np.load(T/"figures"/(path+".npz"))
        for label,storage in (("M0",0.),("finite_Kw",N0/2.e8)):
            closed=Phase(B,C,name,storage,True);opened=Phase(B,C,name,storage,False)
            checks[name+"_"+label]=dict(closed=closed.stats,opened=opened.stats)
            for policy in ("continuous_linear","source_n_held"):
                if closed.stats["spectral_abscissa_per_s"]>1.e-5:
                    rec,diagnosis=unstable_closed(name,policy,closed)
                    records.extend(rec)
                    checks[name+"_"+label]["closed_growth"]=diagnosis
                    continue
                rec,grp=march(name,label,policy,closed,opened,theory)
                records.extend(rec);summary.append(grp)
    hist=pd.DataFrame(records);metrics=pd.DataFrame(summary)
    fig_history(hist,obs,theory,names[3])
    hist.to_csv(names[0],index=False);metrics.to_csv(names[1],index=False);obs.to_csv(names[2],index=False)
    check.write_text(json.dumps(dict(phases=checks,dt_s=DT,closed_steps=4096,ramp_steps=2048,post_steps=32768,
        initial_state="zero displacements, velocities, pressure and effective stress",actual_first_open_step=4097,
        server_first_open_saved_step=4160,solver_runs=0,reduced_dimension=20,
        same_p3_integration=False,mean_pressure_inputs="frozen sphere operators and true initial FSType/FSNormal",
        three_dimensions_evolved=False,same_stage_nonlinear_av_included=False,
        source_clock="q_n held through step on committed clock, compared with exactly integrated linear forcing",
        finite_capacity_solutions=4,closed_M0_handoff_admitted=False,
        supersedes_failed_r1_derived=True,metrics=summary),indent=2,allow_nan=False)+"\n")
    print(metrics[["operator","model","load_clock","closed_center_Pa","first_open_step_Pa","first_server_open_save_Pa","mandel_sampled_peak_Pa","amplitude_error_pct","peak_time_error_pct"]].to_string(index=False))


def fig_history(hist,obs,theory,path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(10.8,7.2),layout="constrained")
    for (op,model),data in hist[(hist.load_clock=="source_n_held")&(hist.phase!="open_right_limit")].groupby(["operator","model"]):
        if model=="M0":continue
        color="#b05a19" if op=="original" else "#12668d";ls="-"
        lab=("SPH" if op=="original" else "paired mechanics")+" / "+model.replace("_"," ")
        c=data[data.phase.isin(["closed","cold"])];o=data[data.phase=="open"]
        axes[0,0].plot(1000*c.t_s,c.p1_Pa/1000,color=color,ls=ls,label=lab)
        axes[0,1].plot(1e6*o.tau_s,o.p1_Pa/1000,color=color,ls=ls)
        axes[1,0].plot(1e6*o.tau_s,o.p18_Pa/1000,color=color,ls=ls)
        axes[1,1].plot(1000*o.tau_s,o.p1_Pa/1000,color=color,ls=ls)
    for a,x,y in ((axes[0,1],"early","p1_Pa"),(axes[1,0],"early","p18_Pa")):
        s=obs[(obs.observation!="explicit_A")&(obs.step_in_B_clock>4096)]
        a.scatter(1e6*(s.time_s-TD),s[y]/1000,color="black",s=16,zorder=4)
    a_saved=obs[(obs.observation=="explicit_A")&(obs.step_in_B_clock>4096)]
    for ax,field in [(axes[0,1],"p1_Pa"),(axes[1,0],"p18_Pa")]:
        ax.scatter(1e6*(a_saved.time_s-TD),a_saved[field]/1000,color="#2e8950",marker="x",s=29,zorder=4,label="saved finite Kw")
    axes[0,1].plot([],[],"k.",label="saved P3")
    axes[0,1].legend(fontsize=8)
    axes[1,1].plot(theory.tau_s*1000,theory.A_finite_Kw_Pa/1000,"k:",label="finite Kw quasi-static reference")
    axes[1,1].plot(theory.tau_s*1000,theory.A_pressure_Pa/1000,".",color="0.4",ms=1.8,label="saved finite Kw")
    axes[0,0].set(xlabel="Time since start (ms)",ylabel="Center pressure (kPa)",title="Ramp and closed hold")
    axes[0,1].set(xlabel="Time since opening (µs)",ylabel="Center pressure (kPa)",xlim=(-5,275),title="Opening transient")
    axes[1,0].set(xlabel="Time since opening (µs)",ylabel="Shell 18 pressure (kPa)",xlim=(-5,275),title="Original material radius 0.90 R")
    axes[1,1].set(xlabel="Time since opening (ms)",ylabel="Center pressure (kPa)",xlim=(4,63),ylim=(9.4,13.2),title="Mandel window")
    axes[0,0].legend(fontsize=8);axes[1,1].legend(fontsize=8)
    for a in axes.flat:a.grid(alpha=.2)
    fig.savefig(path,dpi=160);plt.close(fig)


if __name__=="__main__":main()
