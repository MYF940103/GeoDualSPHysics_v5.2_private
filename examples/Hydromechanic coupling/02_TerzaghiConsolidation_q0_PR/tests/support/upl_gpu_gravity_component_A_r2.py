"""Read-only subcomponent A only; never relabel the original combined endpoint gate."""
import argparse, hashlib, json, pathlib, re
import numpy as np
import pandas as pd
T=pathlib.Path(__file__).resolve().parents[1]
F64=np.finfo(np.float64).eps
F32=np.finfo(np.float32).eps
H=float(np.float32(1.8/256))
END=2.0**-15
CAD=2.0**-23
TERMINAL="Wrong explicit +/-g chain is empty against100 original rate budgets; do not relax"
CPP_SHA="791dff7f2d5db3d689c7623affa7fad32a07dc7b94752d12f2d8870de0ef9379"
class Audit:
    def __init__(self):
        self.cache={}
    def entry(self,p):
        p=pathlib.Path(p).resolve(); key=str(p).lower()
        if key not in self.cache:
            with p.open("rb") as f: sha=hashlib.file_digest(f,"sha256").hexdigest()
            self.cache[key]={"path":str(p),"bytes":p.stat().st_size,"sha256":sha}
        return self.cache[key]
    def verify(self,e):
        a=self.entry(e["path"])
        need(a["bytes"]==int(e["bytes"]) and a["sha256"]==e["sha256"].lower(),"Changed bound artifact: "+e["path"])
        return a
    def many(self,es):
        for e in es: self.verify(e)
def need(ok,text):
    if not bool(ok): raise ValueError(text)
def read(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8-sig"))
def zero_exit(c):
    need(c.get("owned_call_exited") is True and c.get("typed_LASTEXITCODE_captured_immediately") is True and type(c.get("exit_code")) is int and c["exit_code"]==0 and c.get("invocation_failure") is None,"Missing actual owned typed exit0")
def rel(a,b): return np.abs(a-b)/np.abs(b)
def run(window,out,a):
    dt=2.0**(-24 if window=="coarse" else -25)
    check=T/"logs"/("upl_gpu_gravity_endpoint_variable_"+window+("_r1" if window=="coarse" else "_r2")+".check.json")
    a.entry(check); c=read(check)
    need(c["job"]=="variable_"+window and c["configuration"]=="Release" and not c["physical_acceptance"],"Wrong endpoint identity/scope")
    for key in ("source_solve","source_single_check","source_build","helper","call"): a.verify(c[key])
    a.many(c["inputs"]); a.many(c["files"])
    h=read(c["helper"]["path"]); b=read(c["source_build"]["path"]); a.verify(b["source_freeze"]); s=read(b["source_freeze"]["path"])
    need(h["fixture"]=="GravityPeriodicEndpoint" and h["exact_link_closure_verified"] and h["link_object_count"]==111 and len(h["objects"])==110 and len(s["source"])==265,"Wrong frozen helper/object/source closure")
    for key in ("author_files","transitive_author_include_files","objects","tools","libraries"): a.many(h[key])
    a.many(s["source"]); a.many(s["canonical_GPU_six_and_CPU_two"])
    for r in h["runtime"]: a.many([r["original"],r["copy"]])
    for key in ("compile_call","link_call"): a.verify(h[key]); zero_exit(read(h[key]["path"]))
    cpp=[e for e in h["author_files"] if pathlib.Path(e["path"]).name=="upl_gpu_gravity_endpoint_r1.cpp"]
    need(len(cpp)==1 and cpp[0]["sha256"]==CPP_SHA,"The reviewed immutable endpoint assertions changed")
    call=read(c["call"]["path"]); a.verify(call["program"]); a.verify(call["log"]); a.verify(h["program"])
    need(call["program"]["sha256"]==h["program"]["sha256"] and call["owned_call_exited"] is True and call["typed_LASTEXITCODE_captured_immediately"] is True and type(call["exit_code"]) is int and call.get("invocation_failure") is None,"Unowned endpoint call or changed helper program")
    need(call["arguments"][:3]==["--audit","variable",window] and float(call["arguments"][4])==dt and call["arguments"][6]=="--","Endpoint argv model/window/dt differs")
    sr=read(c["source_solve"]["path"]); single=read(c["source_single_check"]["path"])
    need(single["passed"] and sr["job"]=="variable_"+window,"Passed matching source Run/native review required")
    need(single["source_run"]["sha256"]==c["source_solve"]["sha256"] and single["source_build"]["sha256"]==c["source_build"]["sha256"]==h["source_build"]["sha256"],"Source solve/native review/endpoint build linkage differs")
    for key in ("helper","call","completion"): a.verify(single[key])
    zero_exit(read(single["call"]["path"]))
    for key in ("call","actual_completion"): a.verify(sr[key])
    zero_exit(read(sr["call"]["path"]))
    actual=read(sr["actual_completion"]["path"])
    need(actual["passed"] and actual["actual_production_Run"] and actual["model"]=="variable" and actual["window"]==window,"Wrong retained physical solve completion")
    a.many(sr["files"]); a.many(single["files"])
    need(pathlib.Path(call["arguments"][3]).resolve()==(pathlib.Path(sr["actual_completion"]["path"]).parent/"data").resolve(),"Audit did not read its retained source data")
    selected=[e for e in c["inputs"] if pathlib.Path(e["path"]).suffix.lower()==".xml"]
    need(len(selected)==1 and pathlib.Path(call["arguments"][5]).resolve()==pathlib.Path(selected[0]["path"]).resolve(),"Selected runtime provenance mismatch")
    need(any(e["sha256"]==selected[0]["sha256"] for e in sr["inputs"]),"Endpoint XML was not the owned solver input")
    if call["exit_code"]==0:
        need(c["passed"] and c.get("completion") is not None,"Missing successful combined completion")
        a.verify(c["completion"]); complete=read(c["completion"]["path"])
        need(complete["passed"] and complete["samples"]==257 and complete["actual_endpoint_force_calls"]==257 and complete["rate_rows"]==131584 and complete["native33_rollback_frames"]==257,"Incomplete successful original completion")
        terminal_only=False
    else:
        need(call["exit_code"]==1 and c["passed"] is False and c.get("completion") is None,"Only exact terminal-signal exit1 can be separated")
        text=pathlib.Path(call["log"]["path"]).read_bytes()
        text=text.decode("utf-16") if text.startswith((b"\xff\xfe",b"\xfe\xff")) else text.decode("utf-8-sig")
        native=[line.strip().split("upl_gpu_gravity_endpoint_r1.exe : ",1)[-1] for line in text.splitlines() if line.strip()==TERMINAL or "upl_gpu_gravity_endpoint_r1.exe : " in line]
        need(native==[TERMINAL],"Rejection was not solely the exact reviewed terminal100-budget message")
        terminal_only=True
    files={pathlib.Path(e["path"]).name:e for e in c["files"]}
    need("endpoint.csv" in files and "endpoint_rates.csv" in files,"Retained full CSVs required")
    need(pathlib.Path(call["arguments"][10]).resolve()==pathlib.Path(files["endpoint.csv"]["path"]).parent.resolve(),"CSV folder is not the owned endpoint output")
    rates=pd.read_csv(files["endpoint_rates.csv"]["path"],float_precision="round_trip")
    history=pd.read_csv(files["endpoint.csv"]["path"],float_precision="round_trip")
    required="part,time_s,saved_step,id,saved_theta,endpoint_theta,actual_rate,independent_rate,error,budget,error_over_budget,chain_reference,gradient_speed_reference,Gp_x,Gp_y,Gp_z,GJ_x,GJ_y,GJ_z,Ace_x,Ace_y,Ace_z,physical_a_x,physical_a_y,physical_a_z,conditional_qx,conditional_qy,conditional_qz,wrong_explicit_plus_g_rate,wrong_explicit_minus_g_rate,wrong_g_delta_rate,wrong_g_delta_over_original_budget".split(",")
    need(list(rates.columns)==required and len(rates)==257*512 and len(history)==257,"Wrong CSV schema/coverage")
    need(np.isfinite(rates.to_numpy(dtype=float)).all() and np.isfinite(history.drop(columns=["physical33_rollback_exact"]).to_numpy(dtype=float)).all(),"Nonfinite endpoint CSV")
    rates=rates.sort_values(["part","id"])
    need(np.array_equal(rates.part,np.repeat(np.arange(257),512)) and np.array_equal(rates.id,np.tile(np.arange(512),257)),"Missing/duplicate native part/ID")
    times=np.arange(257)*CAD; steps=np.where(np.arange(257)==0,0,np.arange(257)*int(CAD/dt)-1)
    need(np.array_equal(history.part,np.arange(257)) and np.array_equal(history.time_s,times) and np.array_equal(history.saved_step,steps),"Endpoint exact257 clock/Step failed")
    need(np.array_equal(rates.time_s,np.repeat(times,512)) and np.array_equal(rates.saved_step,np.repeat(steps,512)),"Rate rows disagree with declared source clock")
    need(history.physical33_rollback_exact.map(lambda x:str(x).lower()=="true").all(),"Incomplete native33 rollback")
    ghosts=history.periodic_ghost_checks.to_numpy()
    need((ghosts>0).all() and np.equal(ghosts,np.floor(ghosts)).all() and np.array_equal(history.actual_slots,512+ghosts),"Actual owner/periodic slot coverage incomplete")
    need((history.source_signed_dterror<=1e-14).all() and np.array_equal(history.audit_fixed_error_before,history.audit_fixed_error_after),"Original signed dt/telemetry safety failed")
    rerr=np.abs(rates.actual_rate-rates.independent_rate).to_numpy(); budget=rates.budget.to_numpy()
    need((budget>0).all() and np.array_equal(rerr,rates.error) and np.array_equal(rerr/budget,rates.error_over_budget) and (rerr<=budget).all(),"Original rate/reference/raw-budget check failed")
    rratio=(rerr/budget).reshape(257,512)
    need(np.array_equal(rratio.max(axis=1),history.max_rate_error_over_budget),"Endpoint rate maxima mismatch")
    wrong=np.abs(rates.wrong_g_delta_rate.to_numpy())/budget
    need(np.array_equal(wrong,rates.wrong_g_delta_over_original_budget) and np.array_equal(wrong.reshape(257,512).max(axis=1),history.wrong_g_signal_over_original_budget),"Preserved wrong-g diagnostic summaries differ")
    physical=[e for e in single["files"] if pathlib.Path(e["path"]).name=="physical.bin"]
    need(len(physical)==1,"Source native33 export required")
    a.verify(physical[0]); p=pathlib.Path(physical[0]["path"])
    with p.open("rb") as f: header=np.frombuffer(f.read(12),dtype="<u4")
    need(np.array_equal(header,[512,33,257]) and p.stat().st_size==12+257*(1+512*33)*8,"Source native33 header/bytes mismatch")
    native=np.memmap(p,dtype="<f8",mode="r",offset=12,shape=(257,1+512*33))
    need(np.array_equal(native[:,0],times),"Source native33 times mismatch")
    field=native[:,1:].reshape(257,512,33); j=np.asarray(field[:,:,8]).reshape(-1); n=1-.75/j; B=67108864/n
    need((j>.75).all() and (np.abs(j-1)<=1e-4).all() and (n>0).all() and (n<1).all(),"Source current-J domain failed")
    floor=256*F64*np.maximum(1,np.abs(B*rates.endpoint_theta.to_numpy()))+1e-6
    need((budget>=floor).all(),"Output budget is below the immutable original rounding floor")
    k=float(np.float32(1e-4))*np.exp((j-1)/(.75/8192))
    gj=rates[["GJ_x","GJ_y","GJ_z"]].to_numpy(); speed=B/(1000*9.80665)*k/(.75/8192)*np.linalg.norm(gj,axis=1)
    need((np.abs(speed-rates.gradient_speed_reference)<=64*F32*np.maximum(1,speed)).all(),"Independent current-J/GJ gradient speed differs")
    reference=rates.gradient_speed_reference.to_numpy().reshape(257,512).max(axis=1)
    need(np.array_equal(reference,history.independent_gradient_speed) and (np.abs(history.actual_gradient_speed-reference)<=64*F32*np.maximum(1,reference)).all(),"Actual endpoint cache original budget failed")
    for name in ("wave","pore"):
        x=history["actual_"+name+"_scale_s"].to_numpy(); y=history["independent_"+name+"_scale_s"].to_numpy()
        need((x>0).all() and (y>0).all() and (rel(x,y)<=64*F64).all(),"Original "+name+" scale agreement failed")
    pore=float(np.float32(.1))*H*H/(B*k/(1000*9.80665)).reshape(257,512).max(axis=1)
    need((rel(history.independent_pore_scale_s.to_numpy(),pore)<=64*F64).all(),"Independent current-k diffusion differs")
    bound=history.necessary_bound_s.to_numpy()
    need((bound>0).all() and (dt<=bound).all() and (1e-10<=bound).all(),"Original necessary locked-step/DtMin bound failed")
    decision=a.entry(T/"notes/upl_gpu_gravity_gate_components_r2.json")
    need(read(decision["path"])["thresholds_relaxed"] is False,"Versioned forward gate decision missing")
    if window=="half":
        ac=T/"logs/upl_gpu_gravity_component_A_coarse_r2.check.json"; a.entry(ac); need(read(ac)["passed"] and read(ac)["component"]=="A","Coarse subcomponent A missing")
    return dict(stage="upl_gpu_gravity_component_A_r2",component="A",passed=True,window=window,scope="Saved endpoint conditional operator/source assertions only",combined_check=a.entry(check),original_combined_passed=c["passed"],original_owned_endpoint_exit=call["exit_code"],only_exact_terminal_signal_failure_accepted_for_A=terminal_only,original_combined_failure_overridden=False,actual_endpoint_force_calls=257,rate_rows=131584,periodic_ghost_checks=int(ghosts.sum()),native33_rollback_frames=257,max_rate_error_over_original_budget=float(rratio.max()),max_rate_reference_error_Pa_s=float(rerr.max()),max_wrong_g_over_original_budget=float(wrong.max()),original_wrong_g_threshold=100,postinitial_wrong_g_witnesses_gt100=int((wrong[512:]>100).sum()),max_gradient_CFL=float((history.actual_gradient_speed*dt/H).max()),max_dt_over_necessary_bound=float((dt/bound).max()),raw_majorant_independently_regenerated=False,owner_bits_and_rollback_are_bound_original_GPU_assertions_not_new_device_observations=True,old_helper_CPP=a.verify(cpp[0]),versioned_gate_decision=decision,files=list(a.cache.values()),unique_bindings=len(a.cache),physical_steps_advanced=0,physical_acceptance=False,wall_gravity_accepted=False,public_gravity_accepted=False,old_solver_rerun=False)
def main():
    p=argparse.ArgumentParser(); p.add_argument("--window",choices=["coarse","half"],required=True);p.add_argument("--out",type=pathlib.Path); args=p.parse_args()
    out=args.out or T/"logs"/("upl_gpu_gravity_component_A_"+args.window+"_r2.check.json")
    need(out.parent.is_dir() and not out.exists(),"Fresh existing-parent audit output required")
    a=Audit(); a.entry(__file__); a.entry(T/"notes/upl_gpu_gravity_component_A_r2.json")
    try: result=run(args.window,out,a)
    except Exception as e:
        result=dict(stage="upl_gpu_gravity_component_A_r2",component="A",window=args.window,passed=False,error=str(e),files=list(a.cache.values()),physical_acceptance=False,original_combined_failure_overridden=False)
        out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8"); raise
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
if __name__=="__main__": main()
