"""Read the two C08 M0 gravity trajectories at the same elapsed integration steps."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

TESTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TESTS.parents[1]/"04_CryerProblem_PR/tests/support"))
from cryer_live_history_review import CHILD, FIELDS, EXPECTED_TYPES, _Cursor, read_item

DT=5e-6
DP=.04
SOIL=np.arange(2060,7060,dtype=np.uint32)


def require(flag,message):
    if not flag:
        raise ValueError(message)


def equal(a,b):
    return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()


def native(data,part,now,previous,beta):
    path=data/f"Part_{part:04d}.bi4"
    payload=path.read_bytes()
    require(payload[:58].rstrip(b" ")==b"#FileJBD JPartDataBi4" and payload[58:64]==b"\n\0\0\0\0\0",f"Invalid PART header: {path}")
    c=_Cursor(payload,64)
    root=read_item(c,0,part>0)
    c.finish("PART")
    item,=root["children"]
    m=item["values"]
    rv=root["values"]
    require(root["name"]=="JPartDataBi4" and item["name"]==path.stem.upper(),"Native item identity")
    require((rv["CaseNp"],rv["CaseNfixed"],rv["CaseNfluid"],rv["Data2d"],rv["Dp"])==(7060,2060,5000,1,DP),"Cold-start column geometry")
    require(m["HydroMechModel"]==2 and m["HydroMechConductivityModel"]==1 and m["HydroMechConductivityCk"]==2,"M0 and conductivity identity")
    require(m["GravityPreloadPhase"]==0 and m["HydroMechFreeSeepage"] and m["SoilDampingActive"] and m["PoreShepardActive"],"Preload policies")
    require(m["Cpart"]==part and m["Step"]==max(0,part-1) and m["TimeStep"]==now and m["SymplecticDtPre"]==DT,"Dense integration clock")
    err=float(m["dterror"])
    require(np.isfinite(err) and err<=1e-14 and (not part or err!=-sys.float_info.max),"Signed timestep margin")
    require(m["Nout"]==0 and m["Npok"]==7060 and item["array_types"]==EXPECTED_TYPES,"Particle/array coverage")
    vals=item["arrays"]
    require(all(len(v)==7060 and np.isfinite(v).all() for v in vals.values()),"Invalid native field")
    order=np.argsort(vals["Idp"])
    require(equal(vals["Idp"][order],np.arange(7060,dtype=np.uint32)),"Original IDs")
    all_ids={k:v[order] for k,v in vals.items()}
    fields={k:v[2060:] for k,v in all_ids.items()}
    if part:
        child,=item["children"]
        require(child["name"]==CHILD and child["types"]==FIELDS and child["array_types"]=={"Idp":"DatUint","PorePressPrev":"DatFloat"},"Typed history")
        md=child["values"]
        require(md["Schema"]==1 and md["Valid"]==1 and md["RunCode"]==rv["RunCode"] and md["CompletedUpdates"]==part,"Committed history")
        scheme="P3_B_alpha_half_beta_zero" if beta==0 else "P3_B_alpha_half_beta_0p04"
        require(md["Scheme"]==scheme,"Wrong beta-specific integration history")
        require(md["PreviousTime"]==previous and md["SavedTime"]==now and md["Dt"]==DT,"Source and target clock")
        require(equal(child["arrays"]["Idp"],SOIL),"Source pressure ID order")
        source=child["arrays"]["PorePressPrev"]
    else:
        source=None
    return fields,source,all_ids


def run_trace(data,steps,beta):
    lines=(data.parent/"Run.out").read_text(encoding="utf-8",errors="replace").splitlines()
    require(any("Finished execution (code=0)" in line for line in lines),"Incomplete solver")
    rounds={}
    bounds={}
    for line in lines:
        cols=line.split()
        if not cols:
            continue
        if cols[0]=="C08M0Round":
            require(len(cols)==10 and float(cols[3])==beta,"Pressure policy")
            step,iteration=map(int,cols[1:3])
            count,negative,fs,positive,projected,filtered=map(int,cols[4:])
            require(count==len(SOIL) and 0<=negative<=count and 0<=positive<=fs<=count,"Pressure population")
            require(projected==(positive if iteration==3 else 0) and filtered==int(iteration==3 and step%40==0),"Projection or filter at wrong round")
            require((step,iteration) not in rounds,"Duplicate pressure round")
            rounds[step,iteration]=(negative,fs,positive,projected,filtered)
        elif cols[0]=="C08M0Dt":
            require(len(cols)==9,"Timestep trace shape")
            step,final=int(cols[1]),int(cols[2])
            dt,bound,force,visc,pore,kspeed=map(float,cols[3:])
            require(np.isfinite((dt,bound,force,visc,pore,kspeed)).all() and kspeed>=0 and dt==DT and
                    dt<=bound and bound==min(force,visc,pore),"Unmet phase timestep bound")
            bounds.setdefault(step,[]).append((final,bound,kspeed))
    require(set(rounds)=={(s,r) for s in range(1,steps+1) for r in (1,2,3)},"Missing pressure stages")
    require(set(bounds)==set(range(1,steps+1)) and all([x[0] for x in group]==[0,1,0,0,0] for group in bounds.values()),"Force phases")
    return rounds,bounds


def describe(fields,initial):
    p=fields["PorePress"].astype(float)
    fs=np.isin(fields["FSType"],(2,3))
    pos=fields["Posd"]
    j=fields["PoroVolumeRatio"]
    n0=float(np.float32(.35))
    k0=float(np.float32(2e-4))
    require(np.all(j>0) and np.allclose(fields["PoroPorosity"],1-(1-n0)/j,rtol=2e-14,atol=2e-15),"Porosity ledger")
    require(np.allclose(fields["PoroHydraulicConductivity"],k0*np.exp((j-1)/((1-n0)*2)),rtol=2e-14,atol=0),"Conductivity ledger")
    require(equal(fields["PorePress0"],initial["PorePress0"]) and equal(fields["ExcessPorePress"],fields["PorePress"]-fields["PorePress0"]),"Reference/excess pressure")
    # Original C08 spacing diagnostic, all soil owners in the XZ plane.
    spacing=cKDTree(pos[:,[0,2]]).query(pos[:,[0,2]],k=2)[0][:,1]/DP
    dz=pos[:,2]-initial["Posd"][:,2]
    kappa=fields["Kplastic"]
    return dict(negative_total=int(np.count_nonzero(p<0)),negative_interior=int(np.count_nonzero((p<0)&~fs)),
        negative_surface=int(np.count_nonzero((p<0)&fs)),positive_surface=int(np.count_nonzero((p>0)&fs)),
        minimum_total_Pa=float(p.min()),minimum_native_id=int(SOIL[np.argmin(p)]),maximum_total_Pa=float(p.max()),
        maximum_speed_m_s=float(np.linalg.norm(fields["Vel"],axis=1).max()),front_x_m=float(pos[:,0].max()),
        top_z_m=float(pos[:,2].max()),maximum_abs_dz_m=float(np.abs(dz).max()),minimum_spacing_dp=float(spacing.min()),
        spacing_below_0p7dp=int(np.count_nonzero(spacing<.7)),plastic_owners=int(np.count_nonzero(kappa>0)),
        max_kappa=float(kappa.max()),minimum_J=float(j.min()),maximum_J=float(j.max()))


def compare(off_path,on_path,steps):
    for path in (off_path,on_path):
        require(sorted(p.name for p in path.glob("Part_*.bi4"))==[f"Part_{i:04d}.bi4" for i in range(steps+1)],"Incomplete same-step pair")
    rows=[]
    initial=old_a=old_b=None
    first_active=first_split=None
    active_soil_steps=0
    traces=[run_trace(path,steps,beta) for path,beta in ((off_path,0.),(on_path,.04))]
    previous=now=0.
    for step in range(steps+1):
        off,sa,all_off=native(off_path,step,now,previous,0.)
        on,sb,all_on=native(on_path,step,now,previous,.04)
        if not step:
            initial=off
        else:
            require(equal(sa,old_a["PorePress"]) and equal(sb,old_b["PorePress"]),"PRE extrapolator source differs from previous committed field")
        neg=0 if not step else int(np.count_nonzero(sb<0))
        if neg and first_active is None:
            first_active=step
        active_soil_steps+=neg
        different=[k for k in all_off if not equal(all_off[k],all_on[k])]
        if first_active is None:
            require(not different,f"β branch changes state before activation at step {step}: {different}")
        if different and first_split is None:
            first_split=dict(step=step,fields=different)
        metrics={"step":step,"time_s":now,"eligible_negative_sources":neg,"different_fields":len(different)}
        for (tag,field,src),(rounds,bounds) in zip((("beta0",off,sa),("beta004",on,sb)),traces):
            values=describe(field,initial)
            require(not step or not values["positive_surface"],f"Positive free-surface pressure at completed step {step}")
            if step:
                expected=int(np.count_nonzero(src<0))
                require(all(rounds[step,r][0]==expected for r in (1,2,3)),"Signed source ID count changed inside a step")
                ms=rounds[step,3]
                require(ms[1]==int(np.count_nonzero(np.isin(field["FSType"],(2,3)))),"Final FS count")
                min_dt=min(x[1] for x in bounds[step])
            else:
                min_dt=None
            values["applied_FS_zeros"]=rounds[step,3][3] if step else 0
            values["shepard_applied"]=rounds[step,3][4] if step else 0
            values["phase_dt_bound_s"]=min_dt
            metrics.update({tag+"_"+name:value for name,value in values.items()})
        dp=on["PorePress"].astype(float)-off["PorePress"].astype(float)
        metrics["pressure_difference_rms_Pa"]=float(np.sqrt(np.mean(dp**2)))
        for field,label in (("Posd","position_m"),("SigmaState_kk","normal_stress_Pa"),("SigmaState_ij","shear_stress_Pa"),
                            ("PoroHydraulicConductivity","conductivity_m_s"),("Kplastic","kappa")):
            metrics["max_abs_difference_"+label]=float(np.max(np.abs(on[field].astype(float)-off[field].astype(float))))
        rows.append(metrics)
        old_a,old_b=off,on
        previous,now=now,now+DT
    return rows,dict(steps=steps,soil=5000,first_eligible_step=first_active,eligible_soil_steps=active_soil_steps,first_field_divergence=first_split)


def plot(table):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with table.open(newline="",encoding="utf-8") as f:
        values=list(csv.DictReader(f))
    x=[float(r["time_s"])*1e6 for r in values]
    panels=(("maximum_total_Pa",1e-3,"Maximum total pore pressure (kPa)"),
            ("maximum_speed_m_s",1e3,"Maximum speed (mm/s)"))
    fig,axes=plt.subplots(1,2,figsize=(9,3.5),layout="constrained")
    for ax,(key,scale,label) in zip(axes,panels):
        for tag,color,style in (("beta0","#245799","-"),("beta004","#b34c19","o")):
            y=[float(r[tag+"_"+key])*scale for r in values]
            ax.plot(x,y,style,color=color,markerfacecolor="white",markersize=4,
                    markevery=max(1,len(y)//9),label="β = 0" if tag=="beta0" else "β = 0.04")
        for r,clock in zip(values,x):
            if int(r["beta0_shepard_applied"]):
                ax.axvline(clock,color="0.45",linestyle=":",linewidth=1)
        ax.set(xlabel="Time from start of gravity loading (µs)",ylabel=label)
        ax.grid(alpha=.2)
    axes[0].legend()
    target=table.with_suffix(".png")
    require(not target.exists(),"Existing plot")
    fig.savefig(target,dpi=180)
    plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("off",type=Path)
    parser.add_argument("on",type=Path)
    parser.add_argument("steps",type=int)
    parser.add_argument("prefix",type=Path)
    args=parser.parse_args()
    require(args.off.resolve()!=args.on.resolve() and args.steps>0,"Two independent positive-length runs required")
    rows,summary=compare(args.off,args.on,args.steps)
    csvpath=args.prefix.with_suffix(".csv")
    jsonpath=args.prefix.with_suffix(".json")
    require(not csvpath.exists() and not jsonpath.exists(),"Existing review output")
    with csvpath.open("x",encoding="utf-8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    summary.update(off=str(args.off),on=str(args.on),last=rows[-1])
    jsonpath.write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    plot(csvpath)
