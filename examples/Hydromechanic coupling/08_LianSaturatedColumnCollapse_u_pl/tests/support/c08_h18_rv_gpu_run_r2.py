"""Future root-admitted RV Release window only; prior OFF/Debug results stay protected."""
import argparse
import csv
import datetime
import os
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m

T,C,L=m.T,m.C,m.L
SCRIPT=Path(__file__).resolve();NOTE=T/"notes/c08_h18_rv_gpu_run_r2.md"
CONTROL="c08_h18_as03_n255_r1"
SAN=Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe")
THREAD="01a07683-bc64-7463-8db7-9ee6243967d8"
DT,PRESTEP=5e-6,2000000
JOBS={"off1":dict(tag="c08_h18_rv_off1_GPU_r1",configuration="Release",steps=(2000001,),frames=1,updates=1,on=False),
      "debug2":dict(tag="c08_h18_rv_debug2_GPU_r1",configuration="Debug",steps=(2000001,2000002),frames=2,updates=2,on=True),
      "window":dict(tag="c08_h18_rv_window_GPU_r1",configuration="Release",steps=None,frames=91,updates=180000,on=True)}
RVFILES=("C08H18ResidualViscosityPolicy.json","C08H18ResidualViscosity.csv","C08H18ResidualManufactured.csv")
HEADER=("record,phase,active,alpha,step_start_global,completed_global,step_start_time_s,force_stage_time_s,save_time_s,operator_dt_s,phase_calls,phase_commits,pre_calls,cor_calls,pre_commits,cor_commits,last_lambda_max_s_1,running_lambda_max_s_1,last_dt_lambda_half,running_dt_lambda_half,validated_soil_nodes,committed,error_bits,invalid_sorted_index,invalid_native_id,cuda_status,"
"directed_edges,reverse_memberships,max_degree,gamma64,max_condition,max_normal_budget_ratio,max_commit_budget_ratio,work_W_per_m,form_W_per_m,work_defect_prediction_W_per_m,work_certificate_error_W_per_m,work_certificate_budget_W_per_m,work_budget_W_per_m,net_force_norm_N_per_m,net_force_budget_N_per_m,torque_N,torque_defect_prediction_N,torque_certificate_error_N,torque_certificate_budget_N,torque_budget_N,committed_work_W_per_m,committed_work_budget_W_per_m,committed_net_force_norm_N_per_m,committed_net_force_budget_N_per_m,committed_torque_N,committed_torque_budget_N,"
"running_normal_ratio,running_float_commit_ratio,running_work_certificate_ratio,running_work_budget_ratio,running_net_force_ratio,running_torque_certificate_ratio,running_torque_budget_ratio,running_committed_work_ratio,running_committed_net_force_ratio,running_committed_torque_ratio,max_residual_m_s,residual_budget_m_s,max_force_N_per_m,force_budget_N_per_m").split(",")

def paths(job):
    tag=job["tag"]
    return {k:L/(tag+s) for k,s in dict(prep=".prepare.json",prepare_admission=".root_prepare_admission.json",run_admission=".root_run_admission.json",run=".run.json",start=".start.json",status=".status.json",call=".call.json",log=".log",queue=".queue_attempt.json",reply=".queue_result.json").items()}

def copy_exact(source,target):
    m.need(not target.exists(),"Existing copied input protected");shutil.copy2(source,target)
    m.need(target.read_bytes()==Path(source).read_bytes(),"Copied input bytes differ");return m.stat(target)

def root_admission(path,profile,phase):
    a=m.read(path)
    m.need(a["authorized"] and a["allowed_job"]==JOBS[profile]["tag"] and a["profile"]==profile and a["phase"]==phase
        and a["execution_script"]==m.stat(SCRIPT) and a["note"]==m.stat(NOTE)
        and a["root_thread_id"]==os.environ.get("CODEX_THREAD_ID")==THREAD
        and not a["automatic_native"] and not a["automatic_next_job"],"Exact independent current-root admission required")
    if profile=="window":
        m.need(a["single_window_only"] and a["terminal_queue_once"] and len(a["implementation_gates"])>=2,"Future window needs separately reviewed OFF/Debug implementation gates")
        for entry in a["implementation_gates"]:
            q=m.read(m.bind(entry)["path"]);m.need(q["passed"] and not q.get("physical_acceptance",False),"Passed separately selected implementation gate required")
    return a

def plan(job,source_time,oldrows):
    m.need(len(oldrows)==91 and list(oldrows[0])==["part","completed_step","saved_step","time_s","dt_s"],"Original unchanged91 plan required")
    steps=[int(r["completed_step"]) for r in oldrows] if job["steps"] is None else job["steps"]
    clock=source_time;previous=PRESTEP;rows=[];source_clocks=[]
    for part,step in enumerate(steps):
        m.need(step>previous,"Nonincreasing closed global plan")
        for _ in range(previous,step):source=clock;clock+=DT
        rows.append(dict(part=part,completed_step=step,saved_step=step-1,time_s=clock,dt_s=DT));source_clocks.append(source);previous=step
    m.need(previous-PRESTEP==job["updates"] and len(rows)==job["frames"],"Physical update/global step count differs")
    for part,row in enumerate(rows if job["steps"] is None else rows[:1]):
        old=oldrows[part];m.need(int(old["completed_step"])==row["completed_step"] and abs(float(old["time_s"])-row["time_s"])<=1e-14,"Actual shared scalar clock differs")
    return rows,source_clocks,clock

def prepare(profile):
    job=JOBS[profile];p=paths(job);out=T/"outputs"/job["tag"];config=T/"configs"/(job["tag"]+"_Def.xml")
    stepfile=T/"configs"/(job["tag"]+".steps.csv")
    m.need(not out.exists() and not config.exists() and not p["prep"].exists() and (profile=="window" or not stepfile.exists())
        and not any(p[k].exists() for k in ("run","call","log","start","status","queue","reply")),"Existing/failed/partial profile protected")
    before=[]
    try:
        ad=root_admission(p["prepare_admission"],profile,"prepare")
        cr=L/(CONTROL+".run.json");cp=L/(CONTROL+".prepare.json");cn=L/"c08_h18_as03_n255_native_r1.check.json";cv=L/"c08_h18_as03n255_review_r1.check.json"
        original,prepared,native,review=map(m.read,(cr,cp,cn,cv))
        m.need(original["passed"] and original["solver_completed"] and original["consumed_stats_unchanged"] and original["actual_steps"]==2180000 and original["saved_frames"]==91
            and original["actual_exit"]==original["actual_Win32_exit"]==original["actual_tool_exit"]==0
            and original["AS_coefficient"]==.3 and original["AS_exponent"]==2.55 and original["hdp"]==1.8 and original["fixed_dt_s"]==DT
            and not original["keep_bed_overlap"] and native["passed"] and native["reader_invocations"]==1 and native["consumed_stats_unchanged"]
            and review["analysis_complete"] and review["consumed_stats_unchanged"],"Actual passed original AS03 seed/native/control required")
        before=[m.stat(q) for q in (SCRIPT,NOTE,p["prepare_admission"],cr,cp,cn,cv)]
        before += [m.bind(original[k]) for k in ("program","source_build","source_capture","source_archive","source_pre_file","source_run","source_native","input_xml","planned_steps","native_profile","actual_call")]
        before += [m.bind(native[k]) for k in ("actual_call","native_completion","metadata","reader_build")]
        source=m.read(original["source_native"]["path"])
        m.need(source["passed"] and source["certified_PRE"] and source["expected_handoff_schema"]==2 and source["same_material_plastic_PRE"]
            and source["completed_steps"]==PRESTEP and source["samples"]==1001 and source["soil_IDs"]==5000 and source["fixed_IDs"]==2060
            and source["declared_Kernel_XML_CSV"]==2,"Original certified schema2 Wendland PRE required")
        bp=L/("c08_h18_rv_gpu_"+job["configuration"]+"_r2.build.json");b=m.read(bp);before.append(m.stat(bp))
        m.need(ad["source_build"]==m.stat(bp) and b["passed"] and b["configuration"]==job["configuration"] and b["consumed_stats_unchanged"]
            and b["retained_original_objects"]==112 and b["private_objects"]==2 and b["actual_link_objects"]==114
            and b["baseline_source_capture"]==original["source_capture"] and b["source_archive"]==original["source_archive"],"Separately passed exact private RV GPU build required")
        before += [m.bind(b[k]) for k in ("program","source_capture","source_archive","baseline_source_capture")]
        m.need(set(b["private_sources"])=={"host","CUDA","header"},"Actual three private source captures required")
        before += [m.bind(q) for q in b["private_sources"].values()]
        capture=m.read(b["source_capture"]["path"]);m.need(capture["passed"],"Passed actual private source capture required")
        runtime=[m.bind(q) for q in b["runtime"]];before += runtime
        definition=m.bind(prepared["configuration"]);before.append(definition)
        x=ET.parse(original["input_xml"]["path"]).getroot();pars={q.get("key"):q.get("value") for q in x.findall("execution/parameters/parameter")}
        m.need(all(m.f32(pars[k])==m.f32(v) for k,v in dict(Kernel=2,DtFixed=DT,Visco=.1,ArtificialStressCoef=.3,ArtificialStressExp=2.55,TimeMax=10.9,TimeOut=.01).items()),"Original generated XML physics/cadence differs")
        material=m.table(original["native_profile"]["path"]);m.need(len(material)==17 and all(list(r)==["key","value"] for r in material) and len({r["key"] for r in material})==17,"Original seventeen-key receiver profile required")
        seed=Path(original["input_xml"]["path"]).with_suffix("");m.need(len(original["seed"])==3,"Original seed triple required")
        seedentries=[]
        for suffix in (".xml",".bi4","_Normals.nbi4"):
            q=Path(str(seed)+suffix);entry=next(e for e in original["seed"] if Path(e["path"]).resolve()==q.resolve());seedentries.append(m.bind(entry));before.append(entry)
        rows,sources,end=plan(job,float(source["actual_end_s"]),m.table(original["planned_steps"]["path"]))
        m.verify(before);out.mkdir();newconfig=copy_exact(definition["path"],config)
        prefix=out/seed.name;seeds=[copy_exact(e["path"],out/Path(e["path"]).name) for e in seedentries]
        profile_entry=copy_exact(original["native_profile"]["path"],out/"native_profile.csv")
        if profile=="window":planned=original["planned_steps"]
        else:
            with stepfile.open("x",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            planned=m.stat(stepfile)
        argv=[b["program"]["path"],"-gpu:0","-stable","-mdbc_freeslip:1",str(prefix),str(out),"-dirdataout","data","-svres","-nsteps:"+str(rows[-1]["completed_step"])]
        m.verify(before)
        m.save(p["prep"],dict(stage=job["tag"]+".prepare",passed=True,prepared_only=True,profile=profile,configuration=job["configuration"],program=b["program"],source_build=m.stat(bp),
            source_capture=b["source_capture"],source_archive=b["source_archive"],baseline_source_capture=b["baseline_source_capture"],private_sources=b["private_sources"],runtime=runtime,
            source_pre_file=original["source_pre_file"],source_run=original["source_run"],source_native=original["source_native"],control_run=m.stat(cr),control_native=m.stat(cn),control_review=m.stat(cv),control_original_plan=original["planned_steps"],
            configuration_xml=newconfig,input_xml=seeds[0],seed=seeds,native_profile=profile_entry,planned_steps=planned,planned_rows=rows,save_source_clocks_s=sources,actual_source_time_s=source["actual_end_s"],planned_actual_end_s=end,
            global_nsteps_limit=rows[-1]["completed_step"],new_updates=job["updates"],expected_saved_frames=job["frames"],RV_requested=job["on"],environment_override={"C08_RV_H18":"1" if job["on"] else None},output=str(out),argv=argv,cwd=str(C),
            execution_script=m.stat(SCRIPT),note=m.stat(NOTE),root_prepare_admission=m.stat(p["prepare_admission"]),implementation_gates=ad.get("implementation_gates",[]),consumed=before,consumed_stats_unchanged=True,
            seed_copied_byte_identical=True,generated_basename_preserved=seed.name,old91_plan_unchanged=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_next_job=False))
    except Exception as error:
        if not p["prep"].exists():m.save(p["prep"],dict(stage=job["tag"]+".prepare",passed=False,first_failure=str(error),consumed=before,partial_outputs_preserved=True,solver_invocations=0,automatic_retry=False))
        raise

def run_summary(path):
    lines=path.read_text(encoding="utf-8-sig").splitlines();m.need(len(lines)==2 and lines[0].startswith("#RunName;"),"One real Run.csv row required")
    keys,values=lines[0][1:].split(";"),lines[1].split(";");i=keys.index("Configuration")
    m.need(len(values)==len(keys)+1 and len(set(keys))==len(keys),"Only original embedded AS semicolon admitted")
    values=values[:i]+[values[i]+";"+values[i+1]]+values[i+2:];row=dict(zip(keys,values))
    hit=re.findall(r"(?:^| - )AS_Bui2008\(([^;]+);([^\)]+)\)(?= - |$)",row["Configuration"])
    m.need(len(hit)==1 and row["Configuration"].count(";")==1 and all(m.f32(a)==m.f32(b) for a,b in zip(hit[0],(.3,2.55))),"Actual AS03/n255 configuration differs")
    return row

def telemetry(out,job,prep):
    files=[out/n for n in RVFILES]
    if not job["on"]:
        m.need(not any(q.exists() for q in files),"OFF unexpectedly wrote an RV sidecar")
        return dict(RV_files_absent=True,OFF_no_alloc_launch_proof="source-only plus later same-backend native OFF comparison; absence is not allocation telemetry")
    policy=m.read(files[0]);expected=dict(schema=2,policy="C08H18ResidualViscosityPolicy",phase_policy="ReleaseOnly",active=True,alpha=.1,main_columns=66,main_schema="C08H18RV66-r1",kernel="Wendland",kernel_h_sph_float=struct.unpack("<f",struct.pack("<f",.072))[0],dp_m=.04,requested_hdp=1.8,operator_dt_s=DT,source_schema=2,keep_bed_overlap=False,geometry_profile="bedroles",first_stage_global_step=PRESTEP,retired_begin=1805,retired_count=255,force_clock="original_TimeStep_both_stages",reaction_closed=False,BI4_metadata=False,native_22_schema_changed=False,manufactured_mode_count=3)
    m.need(all(policy.get(k)==v for k,v in expected.items()),"Actual schema2 RV policy differs")
    with files[1].open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f);m.need(reader.fieldnames==HEADER and len(HEADER)==66,"Exact new66-column RV telemetry required, not old26")
        rows=list(reader)
    m.need(len(rows)==2*job["frames"],"Actual Pre/Cor saved telemetry coverage differs")
    for part,planned in enumerate(prep["planned_rows"]):
        pair=rows[2*part:2*part+2];m.need({r["phase"] for r in pair}=={"Pre","Cor"},"Actual saved phase pair differs")
        updates=int(planned["completed_step"])-PRESTEP
        for row in pair:
            m.need(row["active"]=="1" and float(row["alpha"])==.1 and int(row["step_start_global"])==int(planned["completed_step"])-1 and int(row["completed_global"])==int(planned["completed_step"])
                and float(row["step_start_time_s"])==float(prep["save_source_clocks_s"][part]) and float(row["force_stage_time_s"])==float(row["step_start_time_s"]) and float(row["save_time_s"])==float(planned["time_s"])
                and float(row["operator_dt_s"])==DT,"Real RV source-n/scalar save clock differs")
            for key in ("phase_calls","phase_commits","pre_calls","cor_calls","pre_commits","cor_commits"):
                m.need(int(row[key])==updates,"Manufactures or skipped stage polluted physical counters: "+key)
            m.need(int(row["validated_soil_nodes"])==5000 and row["committed"]=="1" and int(row["error_bits"])==int(row["cuda_status"])==0 and float(row["running_dt_lambda_half"])<=1.,"Actual RV stage safety/commit failed")
    with files[2].open(encoding="utf-8-sig",newline="") as f:
        manufactured=list(csv.DictReader(f))
    m.need(len(manufactured)==3,"Actual first-stage scratch manufacture rows missing/extra")
    return dict(rv_policy=m.stat(files[0]),rv_sidecar=m.stat(files[1]),rv_manufactured=m.stat(files[2]),main_columns=66,main_rows=len(rows),manufactured_rows=3,
        final_Pre_calls=job["updates"],final_Cor_calls=job["updates"],RV_numeric_certificate_review_pending=True,manufactured_is_not_a_physical_stage=True)

def codex_path():
    q=shutil.which("codex")
    if q and Path(q).is_file() and Path(q).suffix.lower()==".exe":return Path(q).resolve()
    candidates=list((Path.home()/".vscode/extensions").glob("openai.chatgpt-*/bin/windows-x86_64/codex.exe"))
    return max(candidates,key=lambda p:p.stat().st_mtime_ns) if candidates else None

def terminal_once(job,p):
    m.need(job["tag"]==JOBS["window"]["tag"] and os.environ.get("CODEX_THREAD_ID")==THREAD and not p["queue"].exists() and not p["reply"].exists(),"One current-root terminal attempt only; never rearm/resend")
    program=codex_path();message=("The one admitted H1.8 RV GPU window is terminal: "+str(p["run"])+". Read original start/call/run/status/root admissions, actual ownership/exits, frozen private program/source, original schema2 PRE/input/91 scalar plan. This is AS.3/n2.55/AV.1/WendlandH1.8/5us, RV ReleaseOnly alpha.1, 180000 new updates/global2180000/91 saves, not physical acceptance. Native22/6805/P0/J/kappa/FS/ledger/clock/signed review is separate; check existing/active reader before one independently admitted read. RV schema2 main is66 columns/182 Pre-Cor rows plus3 separate manufactured rows; final Pre/Cor counts180000 each. Preserve genuine errors/partials/last raw console, never infer unsaved state or rerun a completed solver. No automatic native/VTK/PRE/otherpsi/half/next job. This direct owner queues once45s; timeout may have delivered, never resend/rearm/watch/self-test.")
    argv=[str(program) if program else "codex","queue","--thread",THREAD,"--message",message]
    m.save(p["queue"],dict(stage=job["tag"],run=m.stat(p["run"]),thread=THREAD,program=m.stat(program) if program else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=job["tag"],attempts=1,do_not_resend=True)
    try:
        m.need(program is not None,"Current Codex CLI absent; preserve terminal evidence without retry")
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(status="queued" if q.returncode==0 else "queue_failed",actual_exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status="delivery_uncertain",error=str(error))
    except Exception as error:result.update(status="queue_failed",error=str(error))
    m.save(p["reply"],result)

def surviving(call):
    found=[]
    for role,identity in (("tool",call.get("child")),("solver",call.get("actual_target"))):
        if not identity:continue
        q=dict(role=role,original=identity)
        try:
            proc=psutil.Process(identity["pid"]);actual=dict(pid=proc.pid,created_epoch=proc.create_time(),exe=proc.exe(),argv=proc.cmdline(),parent_pid=proc.ppid())
            expected=identity["creation_filetime_100ns"]/1e7-11644473600.
            q.update(observed=actual,original_identity_matches=Path(actual["exe"]).resolve()==Path(identity["exe"]).resolve() and abs(actual["created_epoch"]-expected)<=5e-6)
        except psutil.NoSuchProcess:q["observed_exited"]=True
        except Exception as error:q["observation_error"]=str(error)
        found.append(q)
    return found

def run(profile):
    job=JOBS[profile];p=paths(job);out=T/"outputs"/job["tag"]
    m.need(not any(p[k].exists() for k in ("run","start","call","log","status","queue","reply")),"Existing/partial owned attempt protected")
    result=dict(stage=job["tag"],passed=False,solver_completed=False,profile=profile,solver_invocations=0,solver_launch_attempts=0,reader_invocations=0,VTK_invocations=0,GenCase_invocations=0,SHA_scans=0,native_review_pending=True,physical_acceptance=False,automatic_next_job=False,unsaved_failure_time_reconstructed=False)
    before=[];prep=None;call=None
    try:
        prep=m.read(p["prep"]);ad=root_admission(p["run_admission"],profile,"run")
        m.need(prep["passed"] and prep["prepared_only"] and prep["consumed_stats_unchanged"] and prep["profile"]==profile and prep["RV_requested"]==job["on"]
            and ad["preparation"]==m.stat(p["prep"]) and prep["execution_script"]==m.stat(SCRIPT) and prep["note"]==m.stat(NOTE),"Exact independently reviewed preparation required")
        if profile=="window":m.need(ad["implementation_gates"]==prep["implementation_gates"] and codex_path() is not None,"Reviewed future physical-window gates and terminal mechanism required")
        before=[m.stat(q) for q in (SCRIPT,NOTE,p["prep"],p["run_admission"])]
        before += [m.bind(prep[k]) for k in ("program","source_build","source_capture","source_archive","baseline_source_capture","source_pre_file","source_run","source_native","configuration_xml","input_xml","native_profile","planned_steps","control_run","control_native","control_review","control_original_plan")]
        before += [m.bind(q) for q in prep["seed"]+prep["runtime"]+list(prep["private_sources"].values())]
        m.need(out.is_dir() and not (out/"data").exists() and not (out/"Run.out").exists() and not any((out/n).exists() for n in RVFILES),"Fresh prepared directory only")
        program=Path(prep["program"]["path"]);argv=list(prep["argv"])
        m.need(argv[0]==str(program) and argv[-1]=="-nsteps:"+str(prep["global_nsteps_limit"]) and prep["global_nsteps_limit"]==PRESTEP+job["updates"],"Actual private program/global limit differs")
        for proc in psutil.process_iter(["pid","exe"]):
            try:m.need(not proc.info["exe"] or Path(proc.info["exe"]).resolve()!=program.resolve(),"Existing exact private GPU program protected; no duplicate launch")
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        tool=list(argv)
        if profile=="debug2":
            before.append(m.stat(SAN));tool=[str(SAN),"--tool","memcheck","--leak-check","full","--target-processes","all","--error-exitcode","99",*argv]
        env=dict(os.environ)
        for key in list(env):
            if key.upper()=="C08_RV_H18":env.pop(key)
        if job["on"]:env["C08_RV_H18"]="1"
        ownerproc=psutil.Process();owner=dict(pid=os.getpid(),created_epoch=ownerproc.create_time(),exe=ownerproc.exe(),argv=ownerproc.cmdline(),parent_pid=ownerproc.ppid())
        m.verify(before);m.save(p["start"],dict(stage=job["tag"]+".start",owner=owner,preparation=m.stat(p["prep"]),root_admission=m.stat(p["run_admission"]),program=prep["program"],source_build=prep["source_build"],source_capture=prep["source_capture"],source_archive=prep["source_archive"],source_pre_file=prep["source_pre_file"],input_xml=prep["input_xml"],planned_steps=prep["planned_steps"],argv=tool,solver_argv=argv,cwd=prep["cwd"],environment_override=prep["environment_override"],consumed=before,automatic_next_job=False,physical_acceptance=False))
        result.update({k:prep[k] for k in ("program","source_build","source_capture","source_archive","baseline_source_capture","private_sources","source_pre_file","source_run","source_native","runtime","input_xml","seed","planned_steps","native_profile","actual_source_time_s","planned_actual_end_s","global_nsteps_limit","new_updates","expected_saved_frames","environment_override")})
        result.update(owner=owner,preparation=m.stat(p["prep"]),root_admission=m.stat(p["run_admission"]),argv=tool,solver_argv=argv,output=str(out),fixed_dt_s=DT,RV_requested=job["on"],solver_launch_attempts=1)
        result["actual_call"]=m.invoke(job["tag"],tool,Path(prep["cwd"]),env=env,target=program if profile=="debug2" else None)
    except Exception as error:result["first_failure"]=str(error)
    if p["call"].exists():
        result["actual_call"]=m.stat(p["call"]);call=m.read(p["call"])
        target=call.get("actual_target") if profile=="debug2" else call.get("child")
        result.update(actual_exit=call.get("actual_target_Win32_exit") if profile=="debug2" else call.get("actual_Win32_exit"),actual_Win32_exit=call.get("actual_target_Win32_exit") if profile=="debug2" else call.get("actual_Win32_exit"),actual_tool_exit=call.get("actual_Popen_wait_exit"),ownership_failure=call.get("ownership_failure"),solver_invocations=int(target is not None))
        if target:mismatch=Path(target["exe"]).resolve()!=Path(prep["program"]["path"]).resolve();result["solver_program_identity_matches"]=not mismatch
    try:
        m.need(call is not None and result.get("solver_program_identity_matches") and result["actual_exit"]==result["actual_Win32_exit"]==0,"Actual owned solver normal exit required")
        text=(out/"Run.out").read_text(encoding="utf-8-sig")
        m.need("Finished execution (code=0)." in text and "[Simulation INTERRUPTED" not in text and "certified same-material plastic schema/contract2" in text,"Actual normal schema2 completion required")
        # Seal physical program completion before any derived summary/coverage/RV/memcheck check.
        # A later review failure must never imply permission to rerun this completed solver.
        result.update(solver_completed=True,Run_out=m.stat(out/"Run.out"))
        row=run_summary(out/"Run.csv")
        frames=sorted((out/"data").glob("Part_*.bi4"))
        m.need(int(row["Steps"])==prep["global_nsteps_limit"] and int(row["PartFiles"])==job["frames"] and int(row["PartsOut"])==0 and "Wendland" in row["Configuration"]
            and [q.name for q in frames]==["Part_%04d.bi4"%i for i in range(job["frames"])],"Actual saved frame/global-step coverage differs")
        result.update(solver_completed=True,summary=row,actual_steps=int(row["Steps"]),saved_frames=len(frames),PARTs=[m.stat(q) for q in frames],Run_out=m.stat(out/"Run.out"),Run_csv=m.stat(out/"Run.csv"))
        m.need(result["actual_tool_exit"]==0 and result["ownership_failure"] is None and "first_failure" not in result,"Actual tool/handle ownership must also pass")
        result.update(telemetry(out,job,prep))
        if profile=="debug2":
            log=Path(call["log"]["path"]).read_text(encoding="mbcs",errors="replace")
            errors=re.findall(r"ERROR SUMMARY: ([0-9,]+) errors",log);leaks=re.findall(r"LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations",log)
            m.need(errors and leaks and all(int(x.replace(",",""))==0 for x in errors) and all(int(x.replace(",",""))==int(y.replace(",",""))==0 for x,y in leaks),"Actual memcheck zero errors/leaks absent")
            result.update(memcheck_zero_errors_and_leaks=True,memcheck_actual_call=result["actual_call"])
        m.verify(before);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as error:result.setdefault("first_failure",str(error))
    if (out/"Run.out").exists():
        text=(out/"Run.out").read_text(encoding="utf-8-sig",errors="replace");hit=re.search(r"^Text: (.*)$",text,re.M)
        result.update(Run_out=m.stat(out/"Run.out"),first_engine_exception_text=hit[1] if hit else None,observed_saved_files=len(list((out/"data").glob("Part_*.bi4"))))
    unchanged=False
    try:unchanged=all(m.stat(e["path"])==e for e in before)
    except Exception as error:result["terminal_stat_error"]=str(error)
    if not unchanged:result["passed"]=False
    result.update(consumed=before,consumed_stats_unchanged=unchanged,last_original_console_line=m.base.last_part(out),unsaved_state_reconstructed=False)
    if result["solver_launch_attempts"] and call is None:result.update(solver_invocations=None,solver_launch_outcome_not_handle_proven=True)
    if call is not None and not result["passed"]:result["surviving_owned_process_observations"]=surviving(call)
    m.save(p["run"],result);m.save(p["status"],dict(stage=job["tag"],status="completed_pending_unique_native_and_RV_review" if result["passed"] else "completed_solver_review_failed" if result["solver_completed"] else "failed_preserved_no_next_job",run=m.stat(p["run"]),automatic_next_job=False,physical_acceptance=False))
    if profile=="window" and p["call"].exists():terminal_once(job,p)
    return 0 if result["passed"] else 1

if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("phase",choices=("prepare","run"));a.add_argument("--profile",choices=("window",),required=True);a.add_argument("--execution-authorized",action="store_true");args=a.parse_args()
    m.need(args.execution_authorized,"Separate root prepare/run admission required")
    if args.phase=="prepare":prepare(args.profile)
    else:raise SystemExit(run(args.profile))
