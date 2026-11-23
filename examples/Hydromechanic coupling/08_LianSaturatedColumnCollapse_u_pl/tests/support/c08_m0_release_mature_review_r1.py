"""Review actual C08 pressure/motion, native ownership and five stage bounds across the mature release."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

import c08_m0_beta_compare as native
from c08_m0_release_short_review_r1 import read
from c08_m0_release_mature_gpu_r1 import TAG, CAPS, OPEN, SOURCE, hold, gpu
from c08_m0_coupled_hold_review_r1 import rows, read_with_history

DT=5e-6
SOIL=native.SOIL
check=native.require
eq=native.equal


def soils(arrays):
    order=np.argsort(arrays["Idp"])
    return {k:a[order[-5000:]] for k,a in arrays.items()}


def rms(a):
    x=np.asarray(a,dtype=np.float64)
    return np.sqrt(np.mean(x*x)).item()


def verify(beta,window):
    tag=TAG+"_"+window+("_b004" if beta else "_b0")
    cap=CAPS[window]
    data=gpu.T/"outputs"/tag/"data"
    checked=gpu.T/"logs"/(tag+".review.json")
    table=gpu.T/"figures"/(tag+".csv")
    check(not checked.exists() and not table.exists(),"Existing derived result")
    log=(data.parent/"Run.out").read_text(errors="replace")
    call=json.loads((gpu.T/"logs"/(tag+".call.json")).read_text())
    check(call["returncode"]==0 and call["capped_step"]==cap and call["PRE"]==str(hold.PRE),"True solver or PRE binding")
    check("Finished execution (code=0)" in log and "C08Mature imported 7060 fixed 2060 material 5000" in log,"Device restore")
    check("history=cold_actual_p" in log and "M0_wall_hold=200" in log,"Cold history")
    trans,=rows(log,"C08M0Release")
    check(tuple(trans[[0,2,3,4]])==(OPEN,255,5000,1805),"Actual release")
    dt,rounds=rows(log,"C08M0Dt"),rows(log,"C08GpuRound")
    want=np.arange(SOURCE+1,cap+1)
    check(np.array_equal(dt[:,0],np.repeat(want,5)) and np.array_equal(dt[:,1],np.tile([0,1,0,0,0],len(want))),"Mechanical/hydraulic stages")
    check(np.isfinite(dt).all() and (dt[:,2]==DT).all() and (dt[:,3]>=DT).all() and np.array_equal(dt[:,3],np.min(dt[:,4:7],axis=1)) and (dt[:,7]>=0).all(),"Actual allowed step")
    check(np.array_equal(rounds[:,0],np.repeat(want,3)) and np.array_equal(rounds[:,1],np.tile([1,2,3],len(want))),"Endpoint stages")
    check(np.array_equal(rounds[:,2],(rounds[:,1]==3)&(rounds[:,0]%40==0)&(rounds[:,0]<=OPEN)),"Completed-only preload Shepard")
    _,m0,a0,h0=read_with_history(hold.PRE)
    check(h0 is None and m0["Step"]+1==SOURCE and m0["GravityPreloadHandoffSchema"]==2,"Actual original PRE")
    initial=soils(a0)
    previous_p=initial["PorePress"]
    prior_kappa=initial["Kplastic"]
    J0=initial["PoroVolumeRatio"];v0=initial["PoroCurrentVolume"]/J0
    clock=[m0["TimeStep"]]
    for _ in want:clock.append(clock[-1]+DT)
    check(trans[1]==clock[OPEN-SOURCE],"Retirement time")
    plan=[s for s in want if s<=OPEN+8 or s>OPEN and (s-OPEN)%100==0 or s==cap]
    check(sorted(part.name for part in data.glob("Part_????.bi4"))==[f"Part_{i+1:04d}.bi4" for i in range(len(plan))],"All planned PARTs")
    adjacent=prefix=0
    history_rows=[]
    cpu_control=hold.OUT/"data"
    cpu_saved={}
    if not beta:
        for path in sorted(cpu_control.glob("Part_????.bi4")):
            _,mc,ac,_=read_with_history(path)
            cpu_saved[mc["Step"]+1]=soils(ac)
    oldstep=SOURCE
    for i,svalue in enumerate(plan,1):
        step=int(svalue);phase=int(step>OPEN)
        root,item=read(data,i)
        m=item["values"];arrays=item["arrays"];child,=item["children"]
        h=child["values"]
        size=(6805 if phase else 7060)
        check(item["array_types"]==native.EXPECTED_TYPES and child["types"]==native.FIELDS and m["Npok"]==size and not m["Nout"],"Typed native rows")
        check(child["name"]==native.CHILD and child["array_types"]=={"Idp":"DatUint","PorePressPrev":"DatFloat"},"TPI child arrays")
        check(m["Step"]+1==step==h["CompletedUpdates"] and m["Cpart"]==i and m["TimeStep"]==h["SavedTime"]==clock[step-SOURCE],"Real step/clock")
        check(h["PreviousTime"]==clock[step-SOURCE-1] and h["Dt"]==DT and h["Schema"]==1 and h["Valid"]==1 and h["Scheme"]==("P3_B_alpha_half_beta_0p04" if beta else "P3_B_alpha_half_beta_zero") and h["RunCode"]==root["values"]["RunCode"],"History clock and policy")
        check(m["dterror"]!= -np.finfo(float).max and np.isfinite(m["dterror"]) and m["dterror"]<=1e-14,"Signed interval")
        check(m["GravityPreloadPhase"]==phase and m["GravityPreloadEventCompletedStep"]==OPEN and
              m["SoilDampingActive"]==(not phase) and m["PoreShepardActive"]==(not phase) and m["HydroMechFreeSeepage"],"Retirement and hydraulic policy")
        ids=np.arange(7060,dtype=np.uint32)
        registry=np.r_[ids[:1805],ids[2060:]] if phase else ids
        check(eq(np.sort(arrays["Idp"]),registry) and eq(child["arrays"]["Idp"],SOIL),"Original active IDs")
        check(all(len(a)==size and np.isfinite(a).all() for a in arrays.values()),"Finite native arrays")
        f=soils(arrays)
        if step==oldstep+1:
            check(eq(child["arrays"]["PorePressPrev"],previous_p),"Committed source pressure by owner")
            adjacent+=1
        stats=native.describe(f,initial)
        J=f["PoroVolumeRatio"]
        check(np.allclose(f["PoroCurrentVolume"],v0*J,rtol=2e-14,atol=0) and np.allclose(f["PoroMixtureDensity"],1000.+1072.5/J,rtol=2e-14,atol=0),"Mass-volume ledger")
        check(stats["positive_surface"]==0 and np.all(f["Kplastic"]>=prior_kappa),"Free seepage or plastic history")
        if window=="w03" and i<=208:
            refdata=gpu.T/"outputs"/(TAG+"_short"+("_b004" if beta else "_b0"))/"data"
            if refdata.exists():
                _,ref=read(refdata,i)
                check(all(eq(a,ref["arrays"][k]) for k,a in arrays.items()) and
                      m["TimeStep"]==ref["values"]["TimeStep"] and m["dterror"]==ref["values"]["dterror"] and
                      eq(child["arrays"]["PorePressPrev"],ref["children"][0]["arrays"]["PorePressPrev"]),"Actual short prefix")
                prefix+=1
        cpudiff=rms(f["PorePress"].astype(float)-cpu_saved[step]["PorePress"]) if step in cpu_saved else None
        if step==OPEN:
            closed=f
        if step==OPEN+1:
            newmask=np.isin(f["FSType"],(2,3)) & ~np.isin(closed["FSType"],(2,3))
            open_stats=dict(new_FS=int(newmask.sum()),prior_pressure_min_Pa=float(closed["PorePress"][newmask].min()),
                 prior_pressure_max_Pa=float(closed["PorePress"][newmask].max()),first_post_positive=int((f["PorePress"][newmask]>0).sum()))
            check(open_stats["new_FS"]==int(trans[5]) and (closed["PorePress"][newmask]>0).sum()==int(trans[6]),"Exposure and committed projection")
        sigma=f["SigmaState_kk"].astype(float)
        oldstep=step;prior_kappa=f["Kplastic"];previous_p=f["PorePress"]
        d=dict(step=step,t_s=m["TimeStep"],elapsed_from_release_s=m["TimeStep"]-trans[1],phase=phase,
               previous_negative_sources=int((child["arrays"]["PorePressPrev"]<0).sum()),dterror_s=m["dterror"],
               p_rms_change_from_PRE_Pa=rms(f["PorePress"].astype(float)-initial["PorePress"]),cpu_closed_p_rms_difference_Pa=cpudiff,
               stress_zz_min_Pa=float(sigma[:,2].min()),stress_zz_max_Pa=float(sigma[:,2].max()),**stats)
        history_rows.append(d)
    summary=dict(tag=tag,source_actual_time=clock[0],saved_frames=len(plan),release_actual_time=trans[1],end_actual_time=clock[-1],
       device_exact_import_owners=7060,soil_ids=5000,released_fixed=1805,retired_right=255,
       minimum_allowed_dt_s=dt[:,3].min().item(),checks_5phase=len(dt),checks_3round=len(rounds),closed_filter_calls=int(rounds[:,2].sum()),
       exact_adjacent_history_frames=adjacent,exact_previous_rows=adjacent*5000,actual_short_prefix=prefix,
       cpu_closed_common=len(cpu_saved),cpu_closed_max_p_rms_Pa=max((r["cpu_closed_p_rms_difference_Pa"] for r in history_rows if r["cpu_closed_p_rms_difference_Pa"] is not None),default=None),
       opened=open_stats,first_closed=history_rows[0],last_closed=next(r for r in history_rows if r["step"]==OPEN),final=history_rows[-1],
       most_negative_saved_Pa=min(r["minimum_total_Pa"] for r in history_rows),max_speed_saved_m_s=max(r["maximum_speed_m_s"] for r in history_rows),
       min_spacing_saved_dp=min(r["minimum_spacing_dp"] for r in history_rows),
       scope="Real finite-Kw PRE with cold M0 previous pressure, 1ms closed adaptation. HG/AS/NoPen off. No restart of a previous M0 history or formal collapse verification.")
    with table.open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=history_rows[0]);writer.writeheader();writer.writerows(history_rows)
    checked.write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(checked)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("window",choices=CAPS)
    ap.add_argument("--beta",choices=("0","0.04"),default="0")
    args=ap.parse_args();verify(float(args.beta),args.window)
