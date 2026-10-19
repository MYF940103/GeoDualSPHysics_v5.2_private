"""Offline release regression with an exact fixed-grid event display audit.

The frozen checker still compares every physical bit and owns metadata/hash
verification. Only its documented .01-s drained-display case is generalized
from dt=1e-5 to the retained dt=5e-6; no time/field tolerance is introduced.
"""
import argparse
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
import hg_release_check as old


def event_exception(candidate,reference,c,r,raw):
    dt=Decimal(str(candidate["run"]["dt"]))
    event=Decimal(str(candidate["config"]["event"]))
    old.require(dt in (Decimal(".00001"),Decimal(".000005")) and event==Decimal(".01")
        and reference["run"]["dt"]==candidate["run"]["dt"]
        and reference["config"]["event"]==candidate["config"]["event"]
        and candidate["mode"]==reference["mode"]==3 and candidate["event"] and reference["event"],
        "Event display exception is restricted to the retained two dt values and .01-s SPR event")
    quotient=event/dt
    old.require(quotient==quotient.to_integral_value(),"Event is not on the exact decimal dt grid")
    step=int(quotient); policy=reference["complete"]["event_policy"]
    old.require(policy["name"]=="fixed_grid_aligned_snap" and policy["enabled"] is True
        and policy["snap_count"]==1 and policy["grid_step_zero_based"]==step
        and policy["original_threshold_s"]==policy["nominal_grid_time_s"]==float(event)
        and policy["effective_threshold_s"]==policy["observed_tn_s"]
        and policy["threshold_restored"] is True and policy["changes_time_accumulator"] is False
        and policy["changes_load_evaluation"] is False
        and policy["observation_phase"]=="outer_step_before_ComputeTrialStep_not_force_entry"
        and policy["scope"]=="ComputeTrialStep_and_outer_RunCellDivide_restored_before_Sample",
        "Retained event policy does not prove the restored-threshold display mechanism")
    old.require(raw["initial_binary_equal"] and raw["final_binary_equal"]
        and raw["actual_times_bit_equal"] and raw["hg_sample_csv_byte_equal"]
        and raw["final_hg_history_rate_csv_byte_equal"]
        and all(raw["fields_bit_equal"][key] for key in old.PHYSICAL+old.DIAGNOSTIC),
        "Physical/native/HG mismatch cannot be exempted")
    differences=raw["first_mismatches"]+raw["diagnostic_exceptions"]
    old.require(len(differences)==1 and differences[0]["field"]=="drained"
        and differences[0]["step"]==step and differences[0]["particles"]==10
        and differences[0]["actual_time"]==policy["observed_tn_s"],"Not the sole exact event display difference")
    old.require(c.step.eq(step).all() and r.step.eq(step).all()
        and c.time_s.eq(policy["observed_tn_s"]).all() and r.time_s.eq(policy["observed_tn_s"]).all()
        and old.bits(c.id,"id")==old.bits(r.id,"id"),"Event frame identity/time mismatch")
    changed=c.drained.ne(r.drained); ids=c.loc[changed,"id"].astype(int).tolist()
    old.require(ids==list(range(139,1040,100)) and c.loc[changed,"drained"].eq(1).all()
        and r.loc[changed,"drained"].eq(0).all() and c.loc[changed,"fstype"].eq(2).all()
        and r.loc[changed,"fstype"].eq(2).all(),"Event difference has wrong native IDs, classification or direction")
    return dict(field="drained",step=step,actual_time=policy["observed_tn_s"],particles=10,native_ids=ids,
        nominal_event_decimal=str(event),dt_decimal=str(dt),old_event_policy=copy.deepcopy(policy),
        reason="Display only: new nominal-grid predicate versus old threshold restored before sampling")


def compare(candidate,reference,raw):
    result=copy.deepcopy(raw)
    if raw["fields_bit_equal"]["drained"]:
        return result
    # Original compare scanned every frame. A second read selects only the one
    # exact event frame; the predicate cannot conceal another retained mismatch.
    step=int(Decimal(str(candidate["config"]["event"]))/Decimal(str(candidate["run"]["dt"])))
    c=next((f for f in old.frames(candidate) if int(f.step.iloc[0])==step),None)
    r=next((f for f in old.frames(reference) if int(f.step.iloc[0])==step),None)
    old.require(c is not None and r is not None,"Missing exact saved event frame")
    exception=event_exception(candidate,reference,c,r,raw)
    result.update(passed=True,unexpected_field_difference=False,first_mismatches=[],diagnostic_exceptions=[exception],
        exception_reason="Exact .01-s fixed-grid drained display audit for retained coarse/half dt; physical bits remain exact")
    return result


def review(candidate_name,reference_name,tag):
    target=old.TESTS/f"logs/{tag}.check.json";old.require(not target.exists(),"Refusing review overwrite")
    result=dict(status="same_physics_merge_regression_exact_event_display",passed=False,candidate=candidate_name,
        reference=reference_name,prefix=False,reasons=[],physical_accuracy_accepted=False,full_cycle_admitted=False,
        performance_measured=False,half_step_test=False,checker=old.entry(__file__),frozen_checker=old.entry(old.__file__))
    evidence=None
    try:
        evidence=old.Evidence();candidate=old.metadata(candidate_name,evidence)
        reference=old.metadata(reference_name,evidence,historical=True)
        raw=old.compare(candidate,reference,False)
        result.update(candidate_evidence=candidate["receipt"],reference_evidence=reference["receipt"],raw_comparison=raw)
        result["comparison"]=compare(candidate,reference,raw);result["passed"]=result["comparison"]["passed"]
        if not result["passed"]:result["reasons"].append("Physical or unapproved diagnostic bit difference")
    except Exception as error:result["reasons"].append(f"{type(error).__name__}: {error}")
    if evidence:
        result["hash_evidence"]=dict(snapshot=old.entry(evidence.freeze_path),processed_entries=len(evidence.checked),
            mapped_snapshot_entries=evidence.mapped,historical_object_unavailable=evidence.missing_objects,
            historical_build_driver_unavailable=evidence.missing_drivers)
    with target.open("x",encoding="utf-8") as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result["passed"],path=str(target),reasons=result["reasons"])))
    return 0 if result["passed"] else 1


def self_test():
    import pandas as pd
    for dt,step in ((1e-5,1000),(5e-6,2000)):
        policy=dict(name="fixed_grid_aligned_snap",enabled=True,snap_count=1,grid_step_zero_based=step,
            original_threshold_s=.01,nominal_grid_time_s=.01,effective_threshold_s=.0099999999999997,
            observed_tn_s=.0099999999999997,threshold_restored=True,changes_time_accumulator=False,
            changes_load_evaluation=False,observation_phase="outer_step_before_ComputeTrialStep_not_force_entry",
            scope="ComputeTrialStep_and_outer_RunCellDivide_restored_before_Sample")
        candidate=dict(run=dict(dt=dt),config=dict(event=.01),mode=3,event=True)
        reference=copy.deepcopy(candidate);reference["complete"]=dict(event_policy=policy)
        c=pd.DataFrame(dict(id=range(40,1040),step=step,time_s=policy["observed_tn_s"],drained=0,fstype=2))
        r=c.copy();c.loc[c.id.isin(range(139,1040,100)),"drained"]=1
        raw=dict(initial_binary_equal=True,final_binary_equal=True,actual_times_bit_equal=True,
            hg_sample_csv_byte_equal=True,final_hg_history_rate_csv_byte_equal=True,
            fields_bit_equal={key:True for key in old.PHYSICAL+old.DIAGNOSTIC},diagnostic_exceptions=[],
            first_mismatches=[dict(field="drained",step=step,particles=10,actual_time=policy["observed_tn_s"])])
        event_exception(candidate,reference,c,r,raw)
        changes=[lambda a,b,x,y,z:z["first_mismatches"][0].update(step=step+1),
            lambda a,b,x,y,z:x.__setitem__("id",x.id+1),lambda a,b,x,y,z:x.__setitem__("drained",0),
            lambda a,b,x,y,z:z["first_mismatches"][0].update(field="pressure"),
            lambda a,b,x,y,z:z["fields_bit_equal"].update(pressure=False),
            lambda a,b,x,y,z:b["complete"]["event_policy"].update(snap_count=2),
            lambda a,b,x,y,z:b["complete"]["event_policy"].update(observed_tn_s=.01),
            lambda a,b,x,y,z:a["run"].update(dt=2e-5),lambda a,b,x,y,z:a["config"].update(event=.02)]
        for change in changes:
            values=copy.deepcopy((candidate,reference,c,r,raw));change(*values)
            try:event_exception(*values)
            except ValueError:pass
            else:raise AssertionError("Unapproved event/physical mismatch admitted")
    print("PASS both exact dt event steps; wrong step/IDs/direction/field/physical bits/policy/time/dt/event rejected; no artifacts")


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--self-test",action="store_true")
    for key in ("candidate","reference","tag"):parser.add_argument("--"+key,type=old.label)
    args=parser.parse_args()
    if args.self_test:self_test();return 0
    old.require(all((args.candidate,args.reference,args.tag)),"Candidate/reference/fresh tag required")
    return review(args.candidate,args.reference,args.tag)


if __name__=="__main__":raise SystemExit(main())
