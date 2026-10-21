"""User-selected fresh CPU8 k1e-5 full run; output-only regression precedes launch."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
import pandas as pd
import k5_cell_sequence as cell
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify

TAG="k5_cpu_full_r1"
SMOKE="k5_cpu_loadout_smoke_r1"
STATE=TESTS/"logs"/(TAG+".status.json")
STEPS=145750572
END=728.75286


def prepare():
    patch="*** Begin Patch\n"
    for old,label,backend in (("k5_full_r1",TAG,"GPU"),("k5_cpu_timing_r1_t8",SMOKE,"CPU")):
        xml=(TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        bat=(TESTS/"configs"/("x"+old+"_win64_"+backend+".bat")).read_text(encoding="utf8").replace("set case="+old,"set case="+label)
        if backend=="GPU":
            bat=bat.replace("DualSPHysics5.2_GEO_win64.exe","DualSPHysics5.2CPU_win64.exe").replace("-gpu:0 -ompthreads:1","-cpu -ompthreads:8")
        for path,content in ((TESTS/"configs"/(label+"_Def.xml"),xml),(TESTS/"configs"/("x"+label+"_win64_CPU.bat"),bat)):
            assert not path.exists()
            patch+="*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def smoke():
    folder=TESTS/"outputs"/SMOKE;check=TESTS/"logs"/(SMOKE+".check.json")
    assert not folder.exists() and not check.exists()
    bat=TESTS/"configs"/("x"+SMOKE+"_win64_CPU.bat")
    inputs=[bound(p) for p in (Path(__file__),REPO/"src/source/JSphCpuSingle.cpp",REPO/"bin/windows/DualSPHysics5.2CPU_win64.exe",bat,
        TESTS/"configs"/(SMOKE+"_Def.xml"),cell.probe.READER,TESTS/"outputs/k5_cpu_loadout_base_r1/DualSPHysics5.2CPU_win64.exe",
        TESTS/"outputs/k5_cpu_loadout_base_r1/JSphCpuSingle.cpp")]
    with (TESTS/"logs"/(SMOKE+".log")).open("xb") as stream:
        p=subprocess.Popen([os.environ["ComSpec"],"/d","/c",str(bat)],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        code=p.wait()
    assert code==0
    files=sorted((folder/"data").glob("Part_*.bi4"));assert len(files)==31
    old=TESTS/"outputs/k5_cpu_timing_r1_t8";initial=cell.probe.native(folder,0)
    fields=[x for x in cell.FIELDS if x!="load_az"]
    max_force_error=0.
    for i in range(31):
        a,b=cell.probe.native(folder,i),cell.probe.native(old,i)
        assert np.array_equal(a.id,b.id) and a.step.iloc[0]==b.step.iloc[0] and a.time_s.iloc[0]==b.time_s.iloc[0]
        assert a[fields].to_numpy(dtype="<f8").tobytes()==b[fields].to_numpy(dtype="<f8").tobytes(),"Output-only patch changed physical state"
        assert a.load_available.eq(1).all()
        cell.metrics(a,initial)
        if a.time_s.iloc[0]>=.02-1e-8:
            error=abs(4*float(2100*.003125**2*a.load_az.sum())+1000)
            max_force_error=max(max_force_error,error);assert error<.001
    summary=pd.read_csv(folder/"Run.csv",sep=";").iloc[0]
    assert summary.Steps==6000 and summary.PartsOut==0 and abs(a.time_s.iloc[0]-.03)<1e-8
    verify(inputs)
    r=dict(passed=True,utc=utc(),exit_code=code,owned_exited=True,frames=31,actual_time_s=float(a.time_s.iloc[0]),steps=6000,
        physical_saved_fields_0_ulp=True,excluded_new_observation_fields=["load_az","load_available"],cpu_load_array_available=True,
        equivalent_full_force_error_max_N_m=max_force_error,force_test_window_s=[.02,.03],post_point1_s_guard_exercised=False,
        loop_seconds=float(summary.TSimul),full_admission_basis="Output-only equivalence plus retained same-physics short validation; long-run physical acceptance remains pending.",
        inputs=inputs,outputs=[bound(p) for p in files+[folder/"Run.out",folder/"Run.csv"]])
    save(check,r);print(json.dumps({k:v for k,v in r.items() if k not in ("inputs","outputs")},indent=2))


def prerequisites():
    smoke_path=TESTS/"logs"/(SMOKE+".check.json");s=read(smoke_path)
    assert s["passed"] and s["physical_saved_fields_0_ulp"] and s["cpu_load_array_available"]
    verify(s["inputs"]+s["outputs"])
    retired=TESTS/"logs/k5_full_r1_acceleration_stop.json"
    assert read(retired)["owned_processes_exited"] and read(retired)["phase"]=="retired"
    head=subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip()
    assert head==subprocess.check_output(["git","-C",str(REPO),"ls-remote","origin","refs/heads/u-pw"],text=True).split()[0]
    assert not subprocess.check_output(["git","-C",str(REPO),"diff","--name-only","--","src/source","src/VS"],text=True).strip()
    paths=[Path(__file__),Path(cell.__file__),Path(cell.probe.__file__),cell.probe.READER,smoke_path,retired,
        REPO/"src/source/JSphCpuSingle.cpp",TESTS/"support/k5_grid320_sequence.py",TESTS/"support/formal_release_sequence.py",TESTS/"support/mdbc_gpu_vector_run.py",
        TESTS/"logs/k5_long5_r1.status.json",TESTS/"logs/k5_long5_r1.review.json",TESTS/"logs/k5_long5_r1.visual.json",
        TESTS/"configs"/(TAG+"_Def.xml"),TESTS/"configs"/("x"+TAG+"_win64_CPU.bat")]
    assert read(TESTS/"logs/k5_long5_r1.review.json")["audit_passed"] and read(TESTS/"logs/k5_long5_r1.visual.json")["inspected"]
    paths += [REPO/"bin/windows"/name for name in ("DualSPHysics5.2CPU_win64.exe","GenCase_win64.exe","PartVTK_win64.exe")]
    return head,[bound(p) for p in paths]


def run(r):
    folder=TESTS/"outputs"/TAG;assert not folder.exists()
    ref=TESTS/"outputs/k5_long5_r1_c"
    control=read(TESTS/"logs/k5_long5_r1.status.json")["runs"][0]
    control_hashes={Path(x["path"]).name:x for x in control["outputs"]}
    log=TESTS/"logs"/(TAG+".log");history=TESTS/"figures"/(TAG+"_runtime.csv")
    r.update(stage="fresh_cpu8_2tv",checked_frames=0,prefix_comparison_samples=0,prefix_pressure_rms_max_pa=0.,prefix_top_difference_max_mm=0.)
    with log.open("xb") as stream,history.open("x",newline="",encoding="utf8") as output:
        p=subprocess.Popen([os.environ["ComSpec"],"/d","/c",str(TESTS/"configs"/("x"+TAG+"_win64_CPU.bat"))],
            cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        r["owned_cmd_pid"]=p.pid;save(STATE,r)
        initial=writer=None;index=0
        def consume(i):
            nonlocal initial,writer
            a=cell.probe.native(folder,i)
            if initial is None:initial=a.copy()
            try:m=cell.metrics(a,initial)
            except Exception as error:raise RuntimeError(f"Native safety failed at PART {i}, actual t={a.time_s.iloc[0]:.17g}: {error}") from error
            if i<=15000:
                verify([control_hashes[f"Part_{i:04d}.bi4"]]);b=cell.probe.native(ref,i)
                assert np.array_equal(a.id,b.id) and a.step.iloc[0]==b.step.iloc[0] and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
                pressure=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
                settlement=abs(float((a.z[initial.z>.996]-b.z[initial.z>.996]).mean())*1000)
                assert pressure<=5 and settlement<=.005,f"CPU/GPU prefix comparison failed at actual t={a.time_s.iloc[0]:.17g}, pressure={pressure}, material settlement={settlement}"
                r["prefix_pressure_rms_max_pa"]=max(r["prefix_pressure_rms_max_pa"],pressure)
                r["prefix_top_difference_max_mm"]=max(r["prefix_top_difference_max_mm"],settlement)
                r["prefix_comparison_samples"]=i+1
            m["part"]=i
            if writer is None:writer=csv.DictWriter(output,fieldnames=list(m));writer.writeheader()
            writer.writerow(m);output.flush();r.update(checked_frames=i+1,last_checked_time_s=m["time_s"],last_metrics=m)
        try:
            while p.poll() is None:
                count=len(list((folder/"data").glob("Part_*.bi4")))
                while index<count-1:consume(index);index+=1
                r["updated_utc"]=utc();save(STATE,r);time.sleep(15)
            assert p.returncode==0,"CPU BAT failed; inspect "+str(log)
            count=len(list((folder/"data").glob("Part_*.bi4")))
            while index<count:consume(index);index+=1
        finally:
            if p.poll() is None:subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True);p.wait();r["stopped_by_monitor"]=True
            r.update(exit_code=p.returncode,owned_exited=True);save(STATE,r)
    last=r["last_metrics"]
    assert last["step"]==STEPS and abs(last["time_s"]-728.75285851827402)<1e-8 and abs(last["time_s"]-END)<5e-6
    assert .0027444522857366896*(last["time_s"]-.01)>=2 and r["prefix_comparison_samples"]==15001
    text=(folder/"Run.out").read_text(encoding="utf-8-sig",errors="replace");assert "Finished execution (code=0)." in text
    calls=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
    work=re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
    limits=re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)",text)
    assert list(map(int,calls.groups()))==[2*STEPS,STEPS,STEPS,2*STEPS] and list(map(int,work.groups()))==[STEPS+1,STEPS-1]
    assert float(limits[1])<=.2 and float(limits[2])<.01 and "DTs adjusted to DtMin............: 0" in text
    summary=pd.read_csv(folder/"Run.csv",sep=";").iloc[0]
    assert summary.Steps==STEPS and summary.Np==2592 and summary.Nfixed==32 and summary.PartsOut==0 and summary.PartFiles==index
    verify(r["inputs"])
    r.update(completed=True,frames=index,loop_seconds=float(summary.TSimul),outputs=[bound(p) for p in folder.rglob("*") if p.is_file()]+[bound(log),bound(history)])


def worker(args):
    assert not STATE.exists()
    r=dict(status="running",stage="prerequisites",worker_pid=os.getpid(),started_utc=utc(),backend="CPU",threads=8,dt_s=5e-6,
        expected_steps=STEPS,nominal_time_s=END,physical_acceptance=False)
    save(STATE,r)
    try:
        r["checkpoint"],r["inputs"]=prerequisites()
        assert subprocess.check_output(["powershell","-NoProfile","-Command","@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"],text=True).strip()=="0"
        run(r);r.update(status="cpu_2tv_completed_pending_physical_review",stage="review")
    except Exception as error:
        r.update(status="rejected_or_interrupted",reason=str(error))
        folder=TESTS/"outputs"/TAG
        if folder.exists():r["retained_partial_files"]=[bound(p) for p in folder.rglob("*") if p.is_file()]
    r["finished_utc"]=utc();save(STATE,r)
    message=(f"User-authorized same-thread fresh CPU8 k1e-5 full-cycle followup {TAG}, not a new human observation. Detected {r['status']}. "
        f"Read {STATE}, its queue_attempt.json, tests/notes/k5_cpu_full_r1.md and logs/k5_cpu_loadout_smoke_r1.check.json before claims. "
        "User explicitly stopped backend/step comparisons and selected CPU on Oct21. Only fresh CPU8 full,width.025,dp.003125,dt5e-6,eta.04,xi.1,145750572steps was launched; no6.25-us test. GPU oldfull intentionally retired at native6.055999999855318s,not2Tv,never restart its watcher. "
        "CPU output-only patch now exports existing HydroMechLoadAce;31-smoke physical fields0ULP against retained CPU8,force telemetry verified. No force equations or integration were changed. "
        "Verify actual times/native IDs/build-input-output hashes,owned exits,all geometry/drainage/equivalent1000N/m within.001(actual250),post-.1s100-Pa stress/top-gap,HG/natural-step guards and first15001 saved CPU/GPU prefix comparisons5-Pa/.005-mm. These are backend comparisons,not half-step convergence or full acceptance. "
        "Expected repeated-binary64 endpoint728.75285851827402s near2Tv,not an incorrect nominal1e-7 duration failure. Native1ms to15s then.1s and final partial;use actual times. "
        "On normal solver completion,independently review full pressure/material settlement/stress/Q/bottom/late dissipation and all-Tv profiles,generate and inspect plots before physical acceptance. No half-cycle/plastic/general-boundary/exactHG restart claim. "
        "If analysis alone fails,repair only new analysis,not solver. If runtime fails,report exact cause/checked time and last readable PART,preserve evidence,no duplicate solver,relaxed guards,raised damping or old worker restart. "
        "Report terminal outcome proactively in Chinese and continue authorized delivery/formal publication when justified;k3/k4 already accepted,never rerun them. This CPU worker queues once;never restart/rearm it or send connectivity tests.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x",encoding="utf8") as stream:json.dump(dict(utc=utc(),thread=args.thread,terminal=r.copy(),message=message),stream,indent=2)
    try:
        q=subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(queue_status="queued" if q.returncode==0 else "failed_no_retry",queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:r.update(queue_status="uncertain_no_retry",queue_error=str(error))
    save(STATE,r)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepare",action="store_true");p.add_argument("--smoke",action="store_true");p.add_argument("--check",action="store_true");p.add_argument("--worker",action="store_true");p.add_argument("--codex");p.add_argument("--thread");a=p.parse_args()
    if a.prepare:prepare()
    elif a.smoke:smoke()
    elif a.worker:worker(a)
    else:
        assert not STATE.exists()
        head,entries=prerequisites()
        if a.check:print(json.dumps(dict(ready=True,checkpoint=head,input_count=len(entries))))
        else:
            old=read(TESTS/"logs/k5_full_r1.launch.json");codex=old["argv"][old["argv"].index("--codex")+1];thread=old["thread"]
            with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
                argv=[sys.executable,"-B",str(Path(__file__).resolve()),"--worker","--codex",codex,"--thread",thread]
                child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            with (TESTS/"logs"/(TAG+".launch.json")).open("x",encoding="utf8") as stream:json.dump(dict(pid=child.pid,argv=argv,thread=thread,checkpoint=head),stream,indent=2)
            print(json.dumps(dict(pid=child.pid,state=str(STATE))))
