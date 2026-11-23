"""Closed-wall C08 pressure and mechanical drift over a genuine cold-M0 hold."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

from c08_m0_beta_compare import (TESTS,DP,DT,SOIL,EXPECTED_TYPES,CHILD,FIELDS,
                                 _Cursor,read_item,require,equal,describe)
from upl_tpi_partial_bi4_r1 import read

PRE=TESTS/"outputs/c08_h18_wend_psi0_pre_r2/data"
START=2000000
N=200


def sorted_fields(arrays):
    order=np.argsort(arrays["Idp"])
    require(equal(arrays["Idp"][order],np.arange(7060,dtype=np.uint32)),"All original boundary and soil IDs required")
    require(all(len(v)==7060 and np.isfinite(v).all() for v in arrays.values()),"Nonfinite or missing native data")
    return {k:v[order[2060:]] for k,v in arrays.items()}


def reference(part):
    d=read(PRE/f"Part_{part:04d}.bi4")
    require({k:spec["type_name"] for k,spec in d["types"].items()}==EXPECTED_TYPES,"Reference native fields")
    return d["part"]["values"],sorted_fields(d["arrays"])


def hold_frame(path,clock):
    part=int(path.stem.split("_")[-1])
    payload=path.read_bytes()
    cursor=_Cursor(payload,64)
    require(payload[:58].rstrip(b" ")==b"#FileJBD JPartDataBi4" and payload[58:64]==b"\n\0\0\0\0\0","Native file header")
    root=read_item(cursor,0,True)
    cursor.finish("Complete held PART")
    item,=root["children"]
    m=item["values"]
    rel=int(m["Step"])+1-START
    require(1<=rel<=N and m["TimeStep"]==clock[rel] and m["SymplecticDtPre"]==DT,"Actual accumulated native clock")
    require(root["name"]=="JPartDataBi4" and root["values"]["CaseNfluid"]==5000 and root["values"]["CaseNfixed"]==2060,"Particle ownership")
    require(item["name"]==path.stem.upper() and m["Cpart"]==part and m["Npok"]==7060 and m["Nout"]==0 and
            m["HydroMechModel"]==2 and m["GravityPreloadPhase"]==0 and m["HydroMechFreeSeepage"] and m["SoilDampingActive"]
            and m["PoreShepardActive"] and m["HydroMechConductivityModel"]==1 and m["HydroMechConductivityCk"]==2,"Held policies")
    require(np.isfinite(m["dterror"]) and -sys.float_info.max<m["dterror"]<=1e-14 and item["array_types"]==EXPECTED_TYPES,"Native type or signed dt")
    ch,=item["children"]
    hv=ch["values"]
    require(ch["name"]==CHILD and ch["types"]==FIELDS and ch["array_types"]=={"Idp":"DatUint","PorePressPrev":"DatFloat"}
            and hv["Schema"]==1 and hv["Valid"] and hv["Scheme"]=="P3_B_alpha_half_beta_zero"
            and hv["RunCode"]==root["values"]["RunCode"] and hv["CompletedUpdates"]==rel+START
            and hv["Dt"]==DT and hv["PreviousTime"]==clock[rel-1] and hv["SavedTime"]==clock[rel],"Held history contract")
    require(equal(ch["arrays"]["Idp"],SOIL) and np.isfinite(ch["arrays"]["PorePressPrev"]).all(),"History materials")
    return rel,sorted_fields(item["arrays"]),ch["arrays"]["PorePressPrev"]


def rms(x):
    return float(np.sqrt(np.mean(np.square(x,dtype=np.float64))))


def metrics(a,pre,initial,groups):
    row=describe(a,initial)
    p=a["PorePress"].astype(float)
    v=a["Vel"].astype(float)
    dp=p-pre["PorePress"]
    sigma=a["SigmaState_kk"]-pre["SigmaState_kk"]-dp[:,None]
    sij=a["SigmaState_ij"]-pre["SigmaState_ij"]
    disp=a["Posd"]-pre["Posd"]
    z0=initial["Posd"][:,2]
    fixed_head=9810*(2.-a["Posd"][:,2])
    require(np.min(a["Kplastic"]-pre["Kplastic"])>=0,"Plastic history decreased")
    require(equal(a["SigmaState_kk"].astype(np.float32),a["Sigma_kk"]) and equal(a["SigmaState_ij"].astype(np.float32),a["Sigma_ij"]),"Displayed stress")
    speed2=np.sum(v*v,axis=1)
    mass=a["PoroMixtureDensity"]*a["PoroCurrentVolume"]
    row.update(velocity_rms_m_s=float(np.sqrt(np.mean(speed2))),kinetic_J_per_m=float(.5*np.sum(mass*speed2)),
               fixed_H2m_p_minus_current_hydrostatic_rms_Pa=rms(p-fixed_head),p_minus_P0_rms_Pa=rms(a["ExcessPorePress"]),
               pressure_drift_rms_Pa=rms(dp),position_drift_rms_m=float(np.sqrt(np.mean(np.sum(disp**2,axis=1)))),
               total_stress_drift_rms_Pa=float(np.sqrt(np.mean(np.sum(sigma**2+2*sij**2,axis=1)))),
               min_pressure_change_Pa=float(dp.min()),max_pressure_change_Pa=float(dp.max()))
    for name,ix in groups.items():
        row[name+"_pressure_drift_rms_Pa"]=rms(dp[ix])
        row[name+"_dzz_total_mean_Pa"]=float(np.mean(sigma[ix,2]))
        row[name+"_settlement_mm"]=float(np.mean(z0[ix]-a["Posd"][ix,2])*1000)
        row[name+"_displacement_drift_max_mm"]=float(np.max(np.linalg.norm(disp[ix],axis=1))*1000)
    return row


def study(output):
    m,pre=reference(1000)
    before,late=reference(999)
    _,initial=reference(0)
    z0=initial["Posd"][:,2]
    x0=initial["Posd"][:,0]
    support=2*DP*1.8
    groups={"bottom_material":np.isclose(z0,z0.min()),"top_material":np.isclose(z0,z0.max()),
            "untouched_interior":(x0>support)&(x0<4-support)&(z0>support)&(z0<2-support)}
    clocks=[float(m["TimeStep"])]
    for _ in range(N):
        clocks.append(clocks[-1]+DT)
    run=(output/"Run.out").read_text(encoding="utf-8",errors="replace")
    require("Finished execution (code=0)" in run and "history=cold_actual_p" in run,"Missing completed closed-wall hold")
    rows=[]
    source=metrics(pre,pre,initial,groups)
    rows.append(dict(rel=0,t=clocks[0],tau=0.,**source))
    last_rel=0
    last=pre
    shared=0
    for path in sorted((output/"data").glob("Part_*.bi4")):
        rel,a,src=hold_frame(path,clocks)
        require(rel>last_rel,"Repeated or reversed physical step")
        if rel==last_rel+1:
            require(equal(src,last["PorePress"]),"Previous actual pressure at adjacent native state")
            shared+=1
        vals=metrics(a,pre,initial,groups)
        require(not vals["positive_surface"],"Positive P on completed free surface")
        rows.append(dict(rel=rel,t=clocks[rel],tau=clocks[rel]-clocks[0],**vals))
        last_rel,last=rel,a
    require(rows[1]["rel"]==1 and last_rel==N,"First step and endpoint required")
    old=metrics(pre,late,initial,groups)
    durations=dict(finite_Kw_s=clocks[0]-float(before["TimeStep"]),M0_s=rows[-1]["tau"])
    summary=dict(reference="Wendland finite Kw PRE, ψ=0, original Part999 and Part1000",duration=durations,
                 saved_new_frames=len(rows)-1,adjacent_pairs=shared,groups={k:int(v.sum()) for k,v in groups.items()},
                 finite_Kw_previous_to_PRE=old,source=source,last=rows[-1],
                 history_verified_with_adjacent_material_pressure=shared*len(SOIL))
    return rows,summary


def plot(rows,target):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(9,6),layout="constrained")
    x=[r["tau"]*1000 for r in rows]
    panels=(("Pressure drift from PRE (Pa RMS)",("bottom_material_pressure_drift_rms_Pa","untouched_interior_pressure_drift_rms_Pa","top_material_pressure_drift_rms_Pa"),("Bottom layer","Interior","Top layer"),1.),
            ("Speed (µm/s)",("velocity_rms_m_s","maximum_speed_m_s"),("RMS","Maximum"),1e6),
            ("Total stress drift (Pa)",("total_stress_drift_rms_Pa",),("Frobenius RMS",),1.),
            ("Column settlement (mm)",("bottom_material_settlement_mm","top_material_settlement_mm"),("Bottom layer","Top layer"),1.))
    for ax,(label,fields,names,scale) in zip(axes.flat,panels):
        for field,name in zip(fields,names):ax.plot(x,[r[field]*scale for r in rows],".-",label=name,markersize=3)
        ax.set(xlabel="Closed M0 hold after imported PRE (ms)",ylabel=label)
        ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.savefig(target,dpi=180)
    plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("prefix",type=Path)
    args=parser.parse_args()
    targets=[args.prefix.with_suffix(ext) for ext in (".csv",".json",".png")]
    require(not any(p.exists() for p in targets),"Existing review outputs")
    rows,summary=study(args.output)
    with targets[0].open("x",encoding="utf8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    targets[1].write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf8")
    plot(rows,targets[2])
