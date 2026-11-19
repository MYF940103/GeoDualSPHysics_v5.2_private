"""Independent all-pair traction cuts and affine-consistency probes on selected C02 saves."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from upl_tpi_bottom_patch_r1 import DATA, FIG, TEST, Q0, PERIOD, Bed, dx_periodic, ordered, read, require

TAG = "upl_tpi_bottom_cut_r1"


def evaluate(bed, state, layer, reflected, corrected):
    x,z = (state["Posd"][:,axis].copy() for axis in (0,2))
    volume = bed.v0*state["PoroVolumeRatio"]
    if reflected:
        x[:40],z[:40] = x[bed.partner], -z[bed.partner]
    # Enumerate each unordered pair once, use one signed area contribution at its two ends.
    ii,jj=np.triu_indices(1040,k=1)
    dx,dz=dx_periodic(x[ii]-x[jj]), z[ii]-z[jj]
    r=np.hypot(dx,dz)
    use=(r<2.*bed.h)&(r>0.)&((ii>=40)|(jj>=40))
    i,j,dx,dz,r=(a[use] for a in (ii,jj,dx,dz,r))
    fac=-2.7852/bed.h**4*(1.-r/(2*bed.h))**3
    gx,gz=fac*dx,fac*dz
    if corrected:
        # Test the symmetric first-moment correction on both components, with an even/odd
        # reflected tensor for each wall quadrature point. It is a private algebraic trial.
        def moment(f):
            return (np.bincount(i,volume[j]*f,minlength=1040)
                    +np.bincount(j,volume[i]*f,minlength=1040))
        xx,xz,zz=moment(-dx*gx),moment(-dx*gz),moment(-dz*gz)
        det=xx*zz-xz*xz
        require(np.all(det[40:]>0.), "Singular soil correction tensor")
        a,b,c=np.zeros(1040),np.zeros(1040),np.zeros(1040)
        a[40:],b[40:],c[40:] = (v[40:]/det[40:] for v in (zz,-xz,xx))
        a[:40],b[:40],c[:40] = a[bed.partner],-b[bed.partner],c[bed.partner]
        gx,gz=.5*((a[i]+a[j])*gx+(b[i]+b[j])*gz),.5*((b[i]+b[j])*gx+(c[i]+c[j])*gz)
    s=state["SigmaState_kk"][:,2].astype(np.float32).astype(float)-state["PorePress"]
    sxz=state["SigmaState_ij"][:,2].astype(np.float32).astype(float)
    pair=volume[i]*volume[j]
    real=pair*((s[i]+s[j])*gz+(sxz[i]+sxz[j])*gx)
    patch=pair*(-2*Q0)*gz
    # The sum of oriented forces on the upper body is the transmitted upward resultant.
    # A pair connecting layers lo and hi contributes over cuts lo+1 ... hi.
    def cut(force):
        lo=np.minimum(layer[i],layer[j])+1;hi=np.maximum(layer[i],layer[j])+1
        val=np.sign(layer[i]-layer[j])*force/PERIOD
        out=np.zeros(101)
        np.add.at(out,np.maximum(0,lo),val)
        np.add.at(out,np.maximum(0,hi),-val)
        return np.cumsum(out)[:100]
    def nodal(force):
        return np.bincount(i,force,minlength=1040)-np.bincount(j,force,minlength=1040)
    bottom=bed.recv[:10]
    mass=volume*(1000.+(bed.rho0-1000.)/state["PoroVolumeRatio"])
    row=(nodal(patch)[bottom]/mass[bottom]).mean()
    return cut(real),cut(patch),float(row)


def main():
    dst=[FIG/(TAG+".csv"),FIG/(TAG+".png"),TEST/"logs"/(TAG+".check.json")]
    require(not any(p.exists() for p in dst),"Use retained outputs")
    initial=read(DATA/"Part_0000.bi4");bed=Bed(initial)
    layer=np.rint(bed.z/.01-.5).astype(int)
    history=pd.read_csv(TEST.parent/"figures/upl_tpi_p3_full_diagnostic_r1/history.csv",float_precision="round_trip")
    first=history.loc[history.stress_guard_failed,"part"].iloc[0]
    picks=[0, int((history.time_s-2.).abs().idxmin()), first-1,first,1652]
    rows=[]
    for part in picks:
        frame=read(DATA/f"Part_{part:04d}.bi4")
        time=float(frame["part"]["values"]["TimeStep"])
        require(time==history.time_s.iloc[part],"Frame pairing")
        state=ordered(frame)
        for reflected,corrected,name in ((False,False,"native"),(True,False,"mirror"),
                                         (False,True,"pairC"),(True,True,"mirror_pairC")):
            real,patch,acc=evaluate(bed,state,layer,reflected,corrected)
            for k in range(100):
                rows.append(dict(part=int(part),time_s=time,cut=k,operator=name,transmitted_Pa=real[k],
                                 uniform_patch_transmitted_Pa=patch[k],bottom_row_uniform_accel_m_s2=acc))
    df=pd.DataFrame(rows)
    df.to_csv(dst[0],index=False)
    end=df[df.part==1652]
    verify=pd.read_csv(FIG/"upl_tpi_bottom_patch_r1.csv")
    actual=end[(end.operator=="native")&(end.cut==0)].iloc[0]
    require(abs(actual.bottom_row_uniform_accel_m_s2-verify.native_const_bottom_m_s2.iloc[-1])<1e-9,
            "Independent full-pair enumeration differs from compact neighbour row")
    res={}
    for op,sub in end.groupby("operator"):
        sub=sub.set_index("cut")
        res[op]={name:float(sub.at[ix,col]) for name,ix,col in (
                ("bottom_actual_Pa",0,"transmitted_Pa"),("middle_actual_Pa",50,"transmitted_Pa"),
                ("bottom_patch_Pa",0,"uniform_patch_transmitted_Pa"),("middle_patch_Pa",50,"uniform_patch_transmitted_Pa"),
                ("bottom_row_uniform_accel_m_s2",0,"bottom_row_uniform_accel_m_s2"))}
    fig,axs=plt.subplots(1,2,figsize=(10,4),layout="constrained")
    labels={"native":"Original","mirror":"Mirror locations","pairC":"Pair correction","mirror_pairC":"Mirror + pair correction"}
    for op,sub in end.groupby("operator",sort=False):
        sub=sub[sub.cut<=6]
        for ax,k in zip(axs,("transmitted_Pa","uniform_patch_transmitted_Pa")):
            ax.plot(sub.cut,sub[k]-Q0,marker="o",label=labels[op])
    for ax,title in zip(axs,("Saved terminal stress","Manufactured uniform stress")):
        ax.axhline(0,color="k",linewidth=.7);ax.grid(alpha=.25);ax.set(title=title,xlabel="Material cut (0 = bed)",ylabel="Transmitted traction minus 10 kPa (Pa)")
    axs[1].legend(fontsize=8);fig.savefig(dst[1],dpi=165);plt.close(fig)
    dst[2].write_text(json.dumps(dict(frames=list(map(int,picks)),final=res,physical_acceptance=False),indent=2)+"\n",
                      encoding="utf-8")


if __name__=="__main__":main()
