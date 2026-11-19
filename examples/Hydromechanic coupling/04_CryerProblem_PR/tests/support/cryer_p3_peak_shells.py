"""Material-shell follow-up on the already qualified/rejected native peak, at selected frames only."""
import argparse
import json
from pathlib import Path

from cryer_shell_equilibrium import NATIVE, TOTAL, SOIL, T_D, R, Reference, need, reference_fields, write
from cryer_material_shell_volume import faces, volume
from upl_tpi_partial_bi4_r1 import read
import numpy as np
import pandas as pd


def ordered(data, part, fields):
    raw=read(data/f"Part_{part:04d}.bi4")
    meta=raw["part"]["values"]
    need(meta["Cpart"]==part and meta["TimeStep"]==part*2.**-13
         and meta["Step"]==max(0,64*part-1),"Physical clock")
    arr=raw["arrays"]
    order=np.argsort(arr["Idp"])
    need(np.array_equal(arr["Idp"][order],np.arange(TOTAL)),"Actual native material IDs")
    return {k:arr[k][order[SOIL]] for k in fields}


def main(output,review):
    path=review/"physical"
    doc=json.loads((path/"physical_review.json").read_text(encoding="utf8"))
    target=path/"matched_material_shells.csv"
    figpath=path/"matched_material_shells.png"
    need(not target.exists() and not figpath.exists(),"Preserve prior review")
    hist=pd.read_csv(path/"native_and_theory.csv",float_precision="round_trip")
    wb=hist[(hist.legacy_Tv>=.005)&(hist.tau_s<=.0625)]
    peak=int(wb.loc[wb.center18_Pa.idxmax(),"part"])
    shape_A=pd.read_csv(NATIVE/"summary.csv",float_precision="round_trip")
    wa=shape_A.iloc[wb.part.to_numpy()]
    peak_A=int(wa.loc[wa.center_pressure_Pa.idxmax(),"part"])
    need(peak_A==417 and wb.center18_Pa.max()==doc["native_peak_Pa"],"Actual peak frames")
    ids=pd.read_csv(NATIVE/"native_ids.csv",float_precision="round_trip").iloc[SOIL]
    x0=ordered(output/"data",0,["Posd"])["Posd"]
    need(np.array_equal(x0,ids[["x0","y0","z0"]].to_numpy()),"Same original material IDs/initial positions in A and B")
    r=np.arange(1,21)*.0025
    shells=np.rint(np.linalg.norm(x0,axis=1)/.0025).astype(int)
    maps=[]
    for j in range(1,21):
        member=shells==j
        tri=faces(x0[member])
        maps.append((member,tri,volume(x0[member],tri)))
    explicit=np.memmap(NATIVE/"common26.bin",offset=12,dtype="<f8",mode="r",shape=(577,1+TOTAL*26))
    a,b=Reference(.3),Reference(.3,finite=False)
    b.cv=b.H*b.kappa
    b.decay=b.xi**2*b.cv/R**2
    rows=[]
    for part in sorted({64,peak,peak_A}):
        # Only process four physical arrays at the three frames identified by both original histories.
        st=ordered(output/"data",part,["Posd","PorePress","PoroVolumeRatio","SigmaState_kk"])
        ta=explicit[part,1:].reshape(TOTAL,26)[SOIL]
        t=part*2.**-13
        need(explicit[part,0]==t,"Matched A/B clock")
        for name,ref,pos,p,J,eff in (
            ("P3_M0",b,st["Posd"],st["PorePress"],st["PoroVolumeRatio"],st["SigmaState_kk"].mean(axis=1)),
            ("explicit_finite_Kw",a,ta[:,:3],ta[:,6],ta[:,8],ta[:,[10,13,15]].mean(axis=1))):
            pre,mean,c=reference_fields(ref,t-T_D,r)
            for j,(mask,tri,v0) in enumerate(maps):
                local=eff[mask].mean()
                pressure=p[mask].mean(dtype=np.float64)
                change=volume(pos[mask],tri)/v0-1
                rows.append(dict(model=name,part=part,time_s=t,tau_s=t-T_D,material_shell=j+1,
                    r0_over_a=r[j]/R,ids=int(mask.sum()),pressure_Pa=pressure,
                    reference_pressure_Pa=pre[j],pressure_error_Pa=pressure-pre[j],
                    effective_tensile_Pa=local,total_compression_Pa=pressure-local,
                    dC_Pa=ref.H/ref.K*local-pressure-c,J_minus_1=J[mask].mean()-1,enclosed_shape_change=change))
                if not j and name=="P3_M0":
                    checked=hist.iloc[part]
                    need(abs(pressure-checked.center18_Pa)<1e-8 and abs(change-checked.center18_enclosed_volume_change)<1e-12,
                         "Independent same-18-ID fixed triangles")
    write(target,rows)
    import matplotlib.pyplot as plt
    df=pd.DataFrame(rows)
    fig,(ax,shape)=plt.subplots(1,2,figsize=(11.4,4.2),layout="constrained")
    ax.set(ylabel="Pressure error (Pa)",title="Pressure error at the P3 peak")
    shape.set(ylabel="Enclosed volume change (%)",title="Fixed material surfaces at the P3 peak")
    for code,color,label,marker in (("explicit_finite_Kw","#aa531c","Explicit finite Kw","o"),("P3_M0","#2a638e","TPI P3","x")):
        d=df[(df.part==peak)&(df.model==code)]
        ax.plot(d.r0_over_a,d.pressure_error_Pa,color=color,label=label,marker=marker,ms=4)
        shape.plot(d.r0_over_a,d.enclosed_shape_change*100,color=color,label=label,marker=marker,ms=4)
    for ax in (ax,shape):
        ax.axhline(0,color=".6",lw=.8);ax.grid(alpha=.2);ax.legend()
        ax.set_xlabel("Initial material shell radius / sphere radius")
    fig.savefig(figpath,dpi=185);plt.close(fig)
    print(df[(df.part==peak)&(df.material_shell<=6)].to_string(index=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("review",type=Path)
    args=parser.parse_args()
    main(args.output,args.review)
