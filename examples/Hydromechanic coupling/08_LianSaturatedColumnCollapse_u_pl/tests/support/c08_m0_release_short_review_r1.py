"""Verify early in-process C08 wall retirement against completed native states."""
import argparse
import csv
import json
from pathlib import Path
from struct import pack

import numpy as np

import c08_m0_beta_compare as pre
from c08_m0_release_short_r1 import TAG, STEPS, TESTS

check = pre.require
DT = pre.DT
WALL = np.arange(1805, 2060, dtype=np.uint32)


def read(data, step):
    raw = (data / f"Part_{step:04d}.bi4").read_bytes()
    check(raw[:58].rstrip(b" ")==b"#FileJBD JPartDataBi4" and raw[58:64]==bytes([10,0,0,0,0,0]), "PART signature")
    cursor=pre._Cursor(raw,64)
    root=pre.read_item(cursor,0,step>0)
    cursor.finish("PART")
    part,=root["children"]
    check(root["name"]=="JPartDataBi4" and part["name"]==f"PART_{step:04d}","PART identity")
    return root,part


def review(beta, gpu=False):
    suffix="_b004" if beta else "_b0"
    if gpu:
        from c08_m0_release_gpu_r1 import TAG as gpu_tag
        from c08_m0_gpu_coupled_r1 import TAG as gpu_pre_tag
        from c08_m0_gpu_coupled_review import gpu_phases
    tag=(gpu_tag+("_b004" if beta else "_memcheck")) if gpu else TAG+suffix
    data=TESTS / "outputs" / tag / "data"
    old=TESTS / "outputs" / ((gpu_pre_tag if gpu else "c08_m0_coupled_r1")+suffix) / "data"
    check(json.loads((TESTS/"logs"/(tag+".call.json")).read_text())["returncode"]==0,"Solver exit")
    if gpu:
        gpu_phases(data.parent/"Run.out",STEPS)
        if not beta:
            check("ERROR SUMMARY: 0 errors" in (TESTS/"logs"/(tag+".console.log")).read_text(errors="replace"),"Memcheck")
    else:
        rounds,bounds=pre.run_trace(data,STEPS,beta)
    log=(data.parent/"Run.out").read_text(errors="replace")
    transition,=[line.split() for line in log.splitlines() if line.startswith("C08M0Release ")]
    check(len(transition)==8 and (int(transition[1]),*map(int,transition[3:6]))==(40,255,5000,1805), "Release native counts")
    check({f.name for f in data.glob("Part_*.bi4")}=={f"Part_{i:04d}.bi4" for i in range(STEPS+1)}, "PARTs")
    now=prev=0.
    rows=[]
    old_p=None
    old_kappa=None
    allids=np.arange(7060,dtype=np.uint32)
    active=np.concatenate((allids[:1805],allids[2060:]))
    prefix_fields=0
    for step in range(STEPS+1):
        root,part=read(data,step)
        meta=part["values"]
        geom=root["values"]
        check((geom["CaseNp"],geom["CaseNfixed"],geom["CaseNfluid"],geom["Dp"])==(7060,2060,5000,.04),"Initial geometry")
        released=step>40
        phase=int(released)
        check((meta["Step"],meta["Cpart"],meta["TimeStep"],meta["SymplecticDtPre"])==(max(step-1,0),step,now,DT),"Scalar clock")
        check(meta["HydroMechModel"]==2 and meta["HydroMechFreeSeepage"] and meta["HydroMechConductivityModel"]==1 and meta["HydroMechConductivityCk"]==2., "Hydraulic model")
        check((meta["GravityPreloadPhase"],meta["GravityPreloadTargetIdBegin"],meta["GravityPreloadTargetIdCount"])==(phase,1805,255),"Phase and MK range")
        check(meta["SoilDampingActive"]==(not released) and meta["PoreShepardActive"]==(not released),"Damping and Shepard phase")
        check(meta["GravityPreloadEventCompletedStep"]==40 and meta["GravityPreloadRequestedTime"]==.0002,"Event schedule")
        if released:
            check(meta["GravityPreloadActualCompletedStep"]==40 and meta["GravityPreloadActualTime"]==float(transition[2]),"Actual event")
        margin=meta["dterror"]
        check(np.isfinite(margin) and margin<=1e-14 and (not step or margin!=-np.finfo(float).max),"Signed dterror")
        registry=active if released else allids
        check(part["array_types"]==pre.EXPECTED_TYPES and meta["Nout"]==0 and meta["Npok"]==len(registry),"22 native arrays/ownership")
        arrays=part["arrays"]; order=np.argsort(arrays["Idp"])
        check(pre.equal(arrays["Idp"][order],registry),"Original IDs")
        check(all(len(v)==len(registry) and np.isfinite(v).all() for v in arrays.values()),"Finite arrays")
        soil={k:v[order[-5000:]] for k,v in arrays.items()}
        if step:
            child,=part["children"]
            md=child["values"]
            scheme="P3_B_alpha_half_beta_0p04" if beta else "P3_B_alpha_half_beta_zero"
            check(child["name"]==pre.CHILD and child["types"]==pre.FIELDS and child["array_types"]=={"Idp":"DatUint","PorePressPrev":"DatFloat"},"Typed history")
            check((md["Schema"],md["Valid"],md["RunCode"],md["Scheme"],md["CompletedUpdates"])==(1,1,geom["RunCode"],scheme,step),"Committed source owner")
            check((md["Dt"],md["SavedTime"],md["PreviousTime"])==(DT,now,prev),"Committed source clock")
            check(pre.equal(child["arrays"]["Idp"],pre.SOIL) and pre.equal(child["arrays"]["PorePressPrev"],old_p),"Prior pressure by native ID")
            check(np.all(soil["Kplastic"]>=old_kappa),"Plastic history decreased")
        else:
            initial=soil
        if step<=40:
            _,ref=read(old,step)
            check(all(pre.equal(a,ref["arrays"][k]) for k,a in arrays.items()) and pack("d",margin)==pack("d",ref["values"]["dterror"]), "Closed common prefix")
            if step:
                for k,a in part["children"][0]["arrays"].items():
                    check(pre.equal(a,ref["children"][0]["arrays"][k]),"Closed prefix history")
            prefix_fields+=len(arrays)
        stats=pre.describe(soil,initial)
        check(stats["positive_surface"]==0,"Completed free seepage")
        J=soil["PoroVolumeRatio"]
        v0=initial["PoroCurrentVolume"]
        density=1000.+(initial["PoroMixtureDensity"]-1000.)/J
        check(np.allclose(soil["PoroCurrentVolume"],J*v0,rtol=2e-14,atol=0) and np.allclose(soil["PoroMixtureDensity"],density,rtol=2e-14,atol=0),"Volume and density")
        if gpu:
            negative=(int(np.count_nonzero(old_p<0)) if step else 0)
            fs=int(np.count_nonzero(np.isin(soil["FSType"],(2,3))))
            clamped=None
        elif step:
            negative,fs,_,clamped,_=rounds[step,3]
        else:
            negative=fs=clamped=0
        if step==40:
            last_closed=soil
            check(now==float(transition[2]),"Release overlaps last closed clock")
        if step==41:
            opened=np.isin(soil["FSType"],(2,3)) & ~np.isin(last_closed["FSType"],(2,3))
            check(np.count_nonzero(opened)==int(transition[6]),"Newly exposed material rows")
            first_open=dict(count=int(opened.sum()),prior_positive=int((last_closed["PorePress"][opened]>0).sum()),minimum_prior_Pa=float(last_closed["PorePress"][opened].min()),maximum_prior_Pa=float(last_closed["PorePress"][opened].max()),positive_final=int((soil["PorePress"][opened]>0).sum()),negative_final=int((soil["PorePress"][opened]<0).sum()))
        rows.append(dict(step=step,t_s=now,phase=phase,active=len(registry),fixed=len(registry)-5000,signed_dterror_s=margin,negative_source=negative,iteration3_fs=fs,projected=clamped,**stats))
        old_p=soil["PorePress"]
        old_kappa=soil["Kplastic"]
        prev,now=now,now+DT
    result=dict(tag=tag,beta=beta,steps=STEPS,frames=len(rows),closed_prefix_frames=41,closed_prefix_array_comparisons=prefix_fields,
            previous_pressure_bit_comparisons=STEPS*5000,phase_checks=5*STEPS,endpoint_rounds=3*STEPS,
            first_new_FS=first_open,new_fs_waiting_for_completed_projection=int(transition[7]),end=rows[-1],
            negative_source_material_steps=sum(r["negative_source"] for r in rows),
            released_negative_source_material_steps=sum(r["negative_source"] for r in rows if r["phase"]),
            scope="One process, 200us gravity start and 40us released. HG/AS/NoPen off. No 10s equilibrium or separate-process continuation claim.")
    outfile=TESTS/"figures"/(tag+".csv")
    check(not outfile.exists(),"Existing result")
    with outfile.open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (TESTS/"logs"/(tag+".review.json")).open("x") as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("beta",choices=("0","0.04"))
    parser.add_argument("--gpu",action="store_true")
    args=parser.parse_args()
    review(float(args.beta),args.gpu)
