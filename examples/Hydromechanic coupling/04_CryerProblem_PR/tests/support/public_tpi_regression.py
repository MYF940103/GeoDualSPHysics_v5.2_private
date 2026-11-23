"""Short real-EXE comparisons to the retained same-backend C02/C04 particle frames."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

HYDRO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(HYDRO/"validation"))
from hydro_public_xml_r1 import read_part as read_plain_part

CASES={"02":HYDRO/"02_TerzaghiConsolidation_q0_PR/tests","04":HYDRO/"04_CryerProblem_PR/tests"}
PROFILES=("column","column25","column2mem","sphere","sphere64","sphere4hist","upw","upl","changing_k","restart")
REJECT="HydroMechModel=2 supports fresh symplectic constant-k columns"

def need(check,message):
    if not check:raise ValueError(message)

def sha(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def write(path,value):
    with path.open("x",encoding="utf8") as f:json.dump(value,f,indent=2,allow_nan=False)

def read_with_history(path):
    from cryer_live_history_review import CHILD,read_item,_Cursor
    raw=path.read_bytes()
    if CHILD.encode() not in raw:
        return (*read_plain_part(path),None)
    need(raw[:58].rstrip(b" ")==b"#FileJBD JPartDataBi4" and raw[58:64]==b"\n\0\0\0\0\0","Wrong BI4 header")
    c=_Cursor(raw,64);root=read_item(c,0,True);c.finish("native complete file")
    part,=root["children"];child,=part["children"]
    need(root["name"]=="JPartDataBi4" and part["name"]==path.stem.upper() and child["name"]==CHILD,"Wrong pressure-history location")
    r,m,a=root["values"],part["values"],part["arrays"]
    need(m["Nout"]==0 and r["CaseNp"]==m["Npok"] and np.array_equal(np.sort(a["Idp"]),np.arange(r["CaseNp"])),"Particle coverage")
    return r,m,a,child

def read_part(path):
    return read_with_history(path)[:3]

def setup(profile,backend,tag):
    col=profile in ("column","column25","column2mem","upw","changing_k","restart")
    area=CASES["02" if col else "04"]/"outputs"
    mode={"upw":0,"upl":1}.get(profile,2)
    threads=1
    if mode!=2:
        target="band" if mode==0 else "confinement"
        golden=area/f"drain_xml_r1_{backend}_{target}_new";seed=golden/"seed";steps=6
    elif profile=="column2mem":
        need(backend=="gpu","Memcheck requires the GPU backend")
        golden=area/"upl_tpi_p3_full_gpu_debug2_r1";seed=area/"upl_tpi_m0_dt_Bdebug2_GPU_r1_seed";steps=2
    elif col:
        cpu=backend=="cpu"
        golden=area/("upl_tpi_p3_full_cpu_debug2ms_r1" if cpu else "upl_tpi_p3_B10us_window2s_GPU_r1")
        seed=area/("upl_tpi_m0_dt_Bdebug2ms_CPU_r1_seed" if cpu else "upl_tpi_m0_dt_B10us_window2s_GPU_r1_seed")
        steps=25 if profile=="column25" else (200 if cpu else 1002)
    elif profile=="sphere4hist":
        golden=area/f"cryer_livehist_{backend}_r1_dense4";seed=area/(golden.name+"_seed");steps=4;threads=8
    else:
        seed=area/"cryer_p3_local_seed_r1";threads=8
        if profile=="sphere64":
            golden=area/("upl_tpi_cryer_p3_cpu_B64_r1" if backend=="cpu" else "cryer_p3_gpu_b64_r1");steps=64
        else:
            golden=area/("cryer_xml_cpu_refB_r1" if backend=="cpu" else "cryer_xml_gpu_r1_controlB");steps=2
    dest=area/f"public_tpi_{profile}_{backend}_{tag}"
    return mode,steps,threads,golden,seed,dest

def public_xml(raw,negative):
    tree=ET.fromstring(raw);hydro=tree.find("execution/special/hydromechanics")
    text=raw.decode("utf-8-sig");nl="\r\n" if "\r\n" in text else "\n"
    def pop(tag):
        entries=hydro.findall(tag);need(len(entries)==1,"Expected one "+tag)
        return entries[0].get("value")
    mode,q,ramp=[pop("HydroMechTopLoad"+t) for t in ("Mode","Q0","RampTime")]
    start=pop("HydroMechDrainageStartTime")
    need(pop("HydroMechDrainage")==pop("HydroMechDrainageFixedGrid")==pop("HydroMechDynamicSeepage")=="1","Unexpected private controls")
    for t in ["TopLoadMode","TopLoadQ0","TopLoadRampTime","DrainageStartTime","Drainage","DrainageFixedGrid"]:
        text,n=re.subn(r"(?m)^[ \t]*<HydroMech"+t+r"\s[^\n]*\n","",text);need(n==1,"Seed migration: "+t)
    text,n=re.subn(r'<HydroMechDynamicSeepage\s[^>]*/>','<HydroMechModel value="2" comment="Three endpoint iterations, M0 Eq.40 Rh=1" />',text)
    need(n==1,"Single model selector")
    anchor="            </hydromechanics>"
    need(text.count(anchor)==1,"One hydromechanics block")
    text=text.replace(anchor,anchor+nl+f'            <externalload mode="{mode}" q0="{q}" ramptime="{ramp}" />'+nl+
                      f'            <drainage mode="drained" start="{start}" clock="fixedStep" />')
    if negative:
        for tag in ("HydroMechConductivityModel","HydroMechConductivityCk"):
            text,n=re.subn("(<"+tag+' value=")0(")',r"\g<1>1\2",text)
            need(n==1,"One changing-permeability input "+tag)
    return text.encode("utf8")

def prepare(profile,backend,tag):
    mode,steps,threads,golden,seed,dest=setup(profile,backend,tag)
    xml,=seed.glob("*.xml")
    raw=xml.read_bytes();public=public_xml(raw,profile=="changing_k") if mode==2 and profile!="sphere4hist" else raw
    dest.mkdir();sub=dest/"seed";sub.mkdir()
    inputs={}
    for p in [xml.with_suffix(".bi4"),*seed.glob("*_Normals.nbi4")]:
        shutil.copy2(p,sub/p.name);inputs[p.name]=sha(p)
    (sub/xml.name).write_bytes(public);new=(sub/xml.name)
    need(ET.parse(new).find("execution/special/hydromechanics/HydroMechModel").get("value")==str(mode),"Wrong model in seed")
    # For a prefix of a longer run, every output step through the planned
    # endpoint must be present; the last 2-D GPU step is an archived Part.
    reference=[]
    for frame in sorted((golden/"data").glob("Part_*.bi4")):
        root,meta,fields=read_part(frame)
        actual=int(meta["Step"])+int(int(meta["Cpart"])>0)
        if actual>steps:break
        fs=np.isin(fields["FSType"],(2,3));pressure=fields["PorePress"]
        reference.append(dict(name=frame.name,sha256=sha(frame),step=actual,time_s=float(meta["TimeStep"]),
                 ids=len(pressure),native_fields=len(fields),surface_count=int(fs.sum()),
                 surface_absmax_Pa=float(np.max(abs(pressure[fs]),initial=0)),pressure_absmax_Pa=float(np.max(abs(pressure)))))
    need(reference and reference[-1]["step"]==steps,"No archived field frame at planned endpoint")
    if profile=="column" and backend=="gpu":
        obs={i["step"]:i for i in reference}
        need(obs[1000]["surface_absmax_Pa"]>0 and obs[1001]["surface_absmax_Pa"]==0.
             and obs[1001]["surface_count"]==10,"Wrong or inactive archived opening")
    write(dest/"prepared.json",dict(backend=backend,profile=profile,public_mode=mode,steps=steps,
         seed_prefix=new.stem,relative_original_seed=str(seed.relative_to(HYDRO)),original_xml_sha256=sha(xml),
         equivalent_public_xml_sha256=sha(new),same_particles_sha256=inputs,relative_golden=str(golden.relative_to(HYDRO)),
         reference=reference))
    print(dest/"prepared.json",flush=True)

def compare_one(candidate,old,mode):
    root,meta,a,h=read_with_history(candidate);old_root,old_meta,b=read_part(old)
    need(mode==2 or h is None,"Modes 0 and 1 must preserve their native metadata")
    need(a.keys()==b.keys(),"Different native field schema")
    clock={k:float(meta[k])-float(old_meta[k]) for k in ("Cpart","Step","TimeStep","SymplecticDtPre","dterror")}
    errors={}
    ia,ib=np.argsort(a["Idp"]),np.argsort(b["Idp"])
    for field in a:
        v,w=a[field][ia],b[field][ib]
        need(v.dtype==w.dtype and v.shape==w.shape and np.isfinite(v).all() and np.isfinite(w).all(),field+" type/shape/nonfinite")
        if v.tobytes()!=w.tobytes():
            delta=v.astype("f8")-w.astype("f8");i=int(np.argmax(np.abs(delta)))
            errors[field]=dict(max_abs=float(np.max(abs(delta))),rms=float(np.sqrt(np.mean(delta*delta))),
                     count_different_values=int(np.count_nonzero(v!=w)),largest_delta_id=int(a["Idp"][ia][i//(v.size//len(v))]))
    marker=meta.get("HydroMechModel",root.get("HydroMechModel"))
    fs=np.isin(a["FSType"],(2,3));pressure=a["PorePress"]
    return dict(part=int(meta["Cpart"]),step=int(meta["Step"])+int(meta["Cpart"]>0),time_s=float(meta["TimeStep"]),
         native_fields=len(a),id_count=len(ia),raw_exact_fields=len(a)-len(errors),different=errors,
         hydro_model_marker=None if marker is None else int(marker),marker_ok=bool(marker==2 if mode==2 else marker is None),
         clock_delta=clock,clock_exact={k:meta[k].tobytes()==old_meta[k].tobytes() for k in clock},
         surface_count=int(fs.sum()),surface_absmax_Pa=float(np.max(abs(pressure[fs]),initial=0)))

def checked_gpu_launch(args,sanitizer,dest,env,stream,info):
    import ctypes
    import ctypes.wintypes as wt
    import psutil
    k32=ctypes.WinDLL("kernel32",use_last_error=True)
    k32.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];k32.OpenProcess.restype=wt.HANDLE
    k32.GetExitCodeProcess.argtypes=[wt.HANDLE,ctypes.POINTER(wt.DWORD)];k32.CloseHandle.argtypes=[wt.HANDLE]
    k32.WaitForSingleObject.argtypes=[wt.HANDLE,wt.DWORD]
    report=dest/"memcheck.log"
    command=[str(sanitizer.resolve(strict=True)),"--tool","memcheck","--error-exitcode","86","--log-file",str(report)]+args
    info.update(sanitizer_sha256=sha(sanitizer),sanitizer_command=command)
    proc=subprocess.Popen(command,cwd=dest/"result",env=env,stdout=stream,stderr=subprocess.STDOUT)
    handle=None
    try:
        parent=psutil.Process(proc.pid)
        while not handle and proc.poll() is None:
            try:
                for child in parent.children(recursive=True):
                    if Path(child.exe()).resolve()==Path(args[0]):
                        handle=k32.OpenProcess(0x00100000|0x1000,False,child.pid)
                        if handle:info["solver_child_pid"]=child.pid;break
            except psutil.NoSuchProcess:pass
            if not handle:time.sleep(.05)
        code=proc.wait();info["sanitizer_exit"]=code
        need(handle,"Could not retain a Windows handle for the solver process")
        need(k32.WaitForSingleObject(handle,60000)==0,"Solver child still running")
        actual=wt.DWORD();need(k32.GetExitCodeProcess(handle,ctypes.byref(actual)),"Unable to read solver child exit")
        info["solver_child_exit"]=actual.value
        info["memcheck_zero_errors"]=bool(re.search(r"ERROR SUMMARY:\s*0 errors\b",report.read_text(errors="replace")))
        need(code==0 and info["memcheck_zero_errors"],"CUDA memcheck failed")
        return actual.value
    finally:
        if handle:k32.CloseHandle(handle)

def run(profile,backend,tag,exe,sanitizer=None):
    mode,steps,threads,golden,seed,dest=setup(profile,backend,tag)
    prepared=json.loads((dest/"prepared.json").read_text());prefix=dest/"seed"/prepared["seed_prefix"]
    need(sha(prefix.with_suffix(".xml"))==prepared["equivalent_public_xml_sha256"],"Public input changed")
    for name,digest in prepared["same_particles_sha256"].items():need(sha(prefix.parent/name)==digest,"Particle input changed")
    folder=dest/"result";folder.mkdir()
    options=["-cpu",f"-ompthreads:{threads}"] if backend=="cpu" else ["-gpu"]
    options.append("-stable")
    if profile in ("column","column25","column2mem","changing_k","restart"):options.append("-mdbc_freeslip")
    args=[str(exe.resolve(strict=True)),*options,str(prefix),str(folder),"-dirdataout","data","-svres",f"-nsteps:{steps}"]
    if profile=="restart":args.extend(["-partbegin:1",str(golden/"data")])
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    info=dict(exe_sha256=sha(exe),args=args,prepared_sha256=sha(dest/"prepared.json"),passed=False)
    start=time.perf_counter()
    try:
        with (dest/"console.log").open("xb") as stream:
            if profile=="column2mem":
                need(sanitizer is not None,"Pass the installed compute-sanitizer.exe")
                code=checked_gpu_launch(args,sanitizer,dest,env,stream,info)
            else:code=subprocess.run(args,cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        info.update(exit=code,wall_s=time.perf_counter()-start)
        if profile in ("changing_k","restart"):
            msg=(dest/"console.log").read_text(errors="replace")
            info["diagnostic"]=next((line.strip() for line in msg.splitlines() if REJECT in line),"")
            need(code==1 and info["diagnostic"] and not list((folder/"data").glob("Part_*.bi4")),"Expected normal solver rejection (exit 1) with zero particle frames")
        else:
            if not (folder/"Run.csv").is_file():raise ValueError("No solver summary; exit "+str(code))
            with (folder/"Run.csv").open(encoding="utf-8-sig",newline="") as f:summary,=csv.DictReader(f,delimiter=";")
            need(int(summary["Steps"])==steps and int(summary["PartsOut"])==0,"Wrong update/exclusion count")
            expected=prepared["reference"]
            files=sorted((folder/"data").glob("Part_*.bi4"))
            need([p.name for p in files]==[item["name"] for item in expected],"Different native clock/frame set")
            frames=[];info["native"]=frames
            for p,item in zip(files,expected):
                old=golden/"data"/p.name;need(sha(old)==item["sha256"],"Golden changed")
                frames.append(compare_one(p,old,mode))
            info["fields_and_clock_bitwise"]=all(not r["different"] and all(r["clock_exact"].values()) for r in frames)
            need(code==0,"Solver returned "+str(code))
            need(info["fields_and_clock_bitwise"] and all(r["marker_ok"] for r in frames),"Native fields, clocks or model marker differ; inspect per-frame report")
        info["passed"]=True
    except Exception as exc:info["error"]=str(exc);raise
    finally:write(dest/"review.json",info)
    print(dest/"review.json",flush=True)

def density_audit(profile,backend,tag):
    mode,steps,threads,golden,seed,dest=setup(profile,backend,tag)
    raw=json.loads((dest/"review.json").read_text())
    need(mode==2 and raw["exit"]==0 and "native" in raw,"No completed TPI state set")
    xml,=(dest/"seed").glob("*.xml")
    rho_water=float(ET.parse(xml).find("execution/special/hydromechanics/PoreWaterRho").get("value"))
    report=dict(source_review_sha256=sha(dest/"review.json"),model=2,raw_all_fields_exact=raw["fields_and_clock_bitwise"],
                density_formula="rho_w + (rho_0 - rho_w)/J; Rhop rounds to float32",
                water_density_kg_m3=rho_water,frames=[],passed=False)
    for frame in raw["native"]:
        name=f'Part_{frame["part"]:04d}.bi4'
        r,m,a=read_part(dest/"result/data"/name);gr,gm,b=read_part(golden/"data"/name)
        ia,ib=np.argsort(a["Idp"]),np.argsort(b["Idp"]);nfixed=int(r["CaseNfixed"])
        ids=a["Idp"][ia];soil=ids>=nfixed;wall=~soil
        need(int(r["CaseNmoving"])+int(r["CaseNfloat"])==0 and soil.sum()==r["CaseNfluid"],"Changed material set")
        J=a["PoroVolumeRatio"][ia][soil];expected=rho_water+(float(r["Rhop0"])-rho_water)/J
        current=a["Rhop"][ia];previous=b["Rhop"][ib]
        truth=bool(np.array_equal(expected,a["PoroMixtureDensity"][ia][soil]) and
                   np.array_equal(expected,b["PoroMixtureDensity"][ib][soil]) and
                   np.array_equal(expected.astype("f4"),current[soil]))
        wall_equal=current[wall].tobytes()==previous[wall].tobytes()
        difference=current[soil].astype("f8")-previous[soil]
        report["frames"].append(dict(step=frame["step"],soil_ids=int(soil.sum()),fixed_ids=int(wall.sum()),
            density_formula_exact_current_float_and_both_double=truth,all_fixed_Rhop_exact=wall_equal,
            other_raw_fields_and_clock_exact=bool(set(frame["different"])<={"Rhop"} and all(frame["clock_exact"].values()) and frame["marker_ok"]),
            legacy_Rhop_different_count=int(np.count_nonzero(difference)),legacy_Rhop_max_abs_kg_m3=float(np.max(abs(difference)))))
    report["passed"]=all(v["density_formula_exact_current_float_and_both_double"] and v["all_fixed_Rhop_exact"] and
                         v["other_raw_fields_and_clock_exact"] for v in report["frames"])
    write(dest/"density_audit.json",report)
    need(report["passed"],"Particle density, other native fields or clock failed independent audit")
    print(dest/"density_audit.json",flush=True)

def history_audit(profile,backend,tag,archived=False):
    from cryer_live_history_review import FIELDS
    mode,steps,threads,golden,seed,dest=setup(profile,backend,tag)
    prepared=json.loads((dest/"prepared.json").read_text())
    source=golden if archived else dest/"result"
    if not archived:need(json.loads((dest/"review.json").read_text())["exit"]==0,"Completed solver required")
    need(b"TpiPressureHistory" not in (source/"data/PartInfo.ibi4").read_bytes(),"RunInfo must not contain particle histories")
    frames=prepared["reference"];trace=None
    if profile.startswith("column"):
        name="UplTpiP3CpuR1.csv" if backend=="cpu" else "UplTpiP3GpuR1.round1.csv"
        trace=golden/name
    records=[];prior=None;count_trace=0
    stream=trace.open(newline="") if trace else None
    try:
        data=iter(csv.DictReader(stream)) if stream else None
        entry=next(data,None) if data else None
        for i,saved in enumerate(frames):
            step=saved["step"];f=source/"data"/saved["name"];root,m,a,h=read_with_history(f)
            soil=np.arange(int(root["CaseNfixed"]),int(root["CaseNp"]),dtype="<u4")
            owner=np.argsort(a["Idp"]);current=a["PorePress"][owner][soil]
            record=dict(part=i,step=step,native_sha256=sha(f),check_against_previous_native=False,
                        check_against_archived_history=False,source_trace_owner_checks=0)
            if i==0:
                need(h is None,"Initial history must be absent")
            else:
                need(h is not None and h["types"]==FIELDS and h["array_types"]=={"Idp":"DatUint","PorePressPrev":"DatFloat"},"Missing/mistyped history")
                v=h["values"];owners=h["arrays"]["Idp"];order=np.argsort(owners);p=h["arrays"]["PorePressPrev"][order]
                need(v["Valid"]==1 and v["Schema"]==1 and v["Scheme"]=="P3_B_alpha_half_beta_zero" and
                     v["RunCode"]==root["RunCode"] and v["CompletedUpdates"]==step and v["Dt"]==m["SymplecticDtPre"] and
                     v["SavedTime"]==m["TimeStep"] and v["PreviousTime"]+v["Dt"]==v["SavedTime"],"Invalid history clock or run identity")
                need(np.array_equal(owners[order],soil) and len(p)==len(soil) and np.isfinite(p).all(),"History owners and finite values")
                if prior and prior[0]==step-1:
                    need(prior[1]==v["PreviousTime"],"Source is not the previous completed-step time")
                    previous=prior[2];unequal=p!=previous
                    record.update(check_against_previous_native=True,preceding_native_exact=p.tobytes()==previous.tobytes(),
                        different_from_preceding_native=int(np.count_nonzero(unequal)))
                    if not record["preceding_native_exact"]:
                        fs=np.isin(a["FSType"][owner][soil],(2,3))
                        # At the real C02 drainage event the predictor reads the boundary
                        # projection of committed p_n. Keep both sides of this jump.
                        need(profile=="column" and step==1001 and np.array_equal(unequal,fs) and
                             np.all(p[fs]==0) and p[~fs].tobytes()==previous[~fs].tobytes(),
                             "Unexpected discrepancy with the preceding full field")
                        record["boundary_jump"]=dict(ids=soil[fs].tolist(),preceding_native_p_Pa=previous[fs].tolist(),
                            predictor_history_p_Pa=p[fs].tolist(),matching_interior_ids=int((~fs).sum()))
                if profile=="sphere4hist" and not archived:
                    gr,gm,ga,gh=read_with_history(golden/"data"/saved["name"])
                    q=gh["arrays"]["PorePressPrev"][np.argsort(gh["arrays"]["Idp"])]
                    need(q.tobytes()==p.tobytes() and all(v[k]==gh["values"][k] for k in FIELDS if k!="RunCode"),
                         "Archived pressure histories or source times differ")
                    record["check_against_archived_history"]=True
                if data is not None:
                    buf={};source_time=None
                    while entry is not None and int(entry["part"])<=i:
                        if int(entry["part"])==i and int(entry.get("pressure_round",entry.get("round"))) ==1:
                            pid=int(entry["native_id"]);need(pid not in buf and int(entry["completed_step"])==step,"Duplicate source or wrong trace step")
                            t=float(entry["source_time_s"]);need(source_time in (None,t),"Mixed source clocks")
                            source_time=t;buf[pid]=float(entry["pn_Pa"])
                        entry=next(data,None)
                    need(set(buf)==set(soil.tolist()) and source_time==v["PreviousTime"],"Trace IDs or source time differs")
                    double=np.array([buf[int(pid)] for pid in soil]);q=double.astype("<f4")
                    need(np.array_equal(double,q.astype(float)) and q.tobytes()==p.tobytes(),"Retained source pressure differs from saved history")
                    count_trace+=len(soil);record["source_trace_owner_checks"]=len(soil)
                record.update(previous_time_s=float(v["PreviousTime"]),saved_time_s=float(v["SavedTime"]),
                    nonzero_history=int(np.count_nonzero(p)),different_from_current=int(np.count_nonzero(p!=current)))
            records.append(record);prior=step,float(m["TimeStep"]),current
    finally:
        if stream:stream.close()
    report=dict(passed=True,archived_preflight=archived,frames=records,source_trace_owner_checks=count_trace,
                trace=None if trace is None else str(trace.relative_to(HYDRO)),
                scope="Source-time pressure actually consumed by the predictor, by original material ID. Drainage can project surface values after the previous PART was written.")
    file=dest/("history_reference.json" if archived else "history_audit.json");write(file,report);print(file,flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("action",choices=["prepare","run","audit","history","history-reference"])
    ap.add_argument("profile",choices=PROFILES);ap.add_argument("backend",choices=["cpu","gpu"])
    ap.add_argument("--tag",default="r1");ap.add_argument("--exe",type=Path);ap.add_argument("--sanitizer",type=Path)
    a=ap.parse_args();need(re.fullmatch("[a-zA-Z0-9_]+",a.tag),"Invalid new output label")
    if a.action=="prepare":prepare(a.profile,a.backend,a.tag)
    elif a.action=="audit":density_audit(a.profile,a.backend,a.tag)
    elif a.action.startswith("history"):history_audit(a.profile,a.backend,a.tag,a.action=="history-reference")
    else:
        if not a.exe:ap.error("--exe is required to run")
        run(a.profile,a.backend,a.tag,a.exe,a.sanitizer)
