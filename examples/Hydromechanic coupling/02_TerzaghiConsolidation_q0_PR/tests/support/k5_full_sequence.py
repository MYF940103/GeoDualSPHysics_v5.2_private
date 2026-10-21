"""Separately admitted fresh k1e-5 periodic-cell 2Tv; no formal/source edits."""
import argparse
import collections
import csv
import itertools
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

TAG = "k5_full_r1"
STATE = TESTS/"logs"/(TAG+".status.json")
OUTPUT = TESTS/"outputs"/TAG
STEPS, DT, END = 145750572, .000005, 728.75286
ADMISSION = TESTS/"logs/k5_full_admission_r1.json"


def prepare():
    old = "k5_long5_r1_c"
    xml = (TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
    xml,n = re.subn(r'(<parameter key="TimeMax" value=")[^"]*(")',lambda m:m[1]+str(END)+m[2],xml);assert n==1
    xml = xml.replace("Short controlled admission endpoint; not a full-cycle calculation", "Fresh refined uniform-1D 2Tv diagnostic; actual saved times used in review")
    # Existing documented variable-output feature. No force, integration or dt
    # change. At the switch a possible extra frame is retained, not suppressed.
    xml = xml.replace("    <special>\n",'    <special>\n      <timeout>\n        <tout time="0" timeout="0.000999999999" />\n        <tout time="15" timeout="0.1" />\n      </timeout>\n',1)
    xml,n = re.subn(r'(<parameter key="TimeOut" value=")[^"]*(")',lambda m:m[1]+"0.1"+m[2],xml);assert n==1
    bat = (TESTS/"configs"/("x"+old+"_win64_GPU.bat")).read_text(encoding="utf8").replace("set case="+old,"set case="+TAG)
    bat = bat.replace("-nsteps:3000000","-nsteps:"+str(STEPS))
    bat = bat.replace("rem Short diagnostic only: original 100-Pa acceptance limits are unchanged.","rem Fresh uniform-1D 2Tv diagnostic; original safety limits and accepted fixed step unchanged.")
    bat = bat.replace("%partvtk% -first:15000 -last:15000",'set /a lastpart=0 >nul\nfor %%F in ("%diroutdata%/Part_*.bi4") do set /a lastpart+=1 >nul\nset /a lastpart-=1 >nul\n%partvtk% -first:!lastpart! -last:!lastpart!')
    patch="*** Begin Patch\n"
    for path,content in ((TESTS/"configs"/(TAG+"_Def.xml"),xml),(TESTS/"configs"/("x"+TAG+"_win64_GPU.bat"),bat)):
        assert not path.exists()
        patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+s for s in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def prerequisites():
    decision = read(ADMISSION)
    review = TESTS/"logs/k5_long5_r1.review.json"
    visual = TESTS/"logs/k5_long5_r1.visual.json"
    assert decision["admit_fresh_coarse_2tv"] and not decision["admit_formal_publication"]
    assert read(review)["audit_passed"] and read(visual)["inspected"]
    assert decision["dt_s"] == DT and decision["steps"] == STEPS
    verify(decision["basis"])
    head = subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip()
    remote = subprocess.check_output(["git","-C",str(REPO),"ls-remote","--heads","origin","u-pw"],text=True).split()[0]
    assert head == remote
    assert not subprocess.check_output(["git","-C",str(REPO),"diff","--name-only","--","src/source","src/VS"],text=True).strip()
    entries = [bound(p) for p in (Path(__file__),Path(cell.__file__),Path(cell.probe.__file__),cell.probe.READER,
        TESTS/"support/k5_grid320_sequence.py",TESTS/"support/formal_release_sequence.py",TESTS/"support/mdbc_gpu_vector_run.py",
        ADMISSION,review,visual,TESTS/"logs/k5_long5_r1.status.json",TESTS/"logs/k5_full_selftest_r1.check.json",
        TESTS/"configs"/(TAG+"_Def.xml"),TESTS/"configs"/("x"+TAG+"_win64_GPU.bat"),
        REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe",REPO/"bin/windows/GenCase_win64.exe",REPO/"bin/windows/PartVTK_win64.exe")]
    verify(read(TESTS/"logs/k5_long5_r1.status.json")["inputs"])
    assert read(TESTS/"logs/k5_full_selftest_r1.check.json")["passed"]
    return head,entries


def run(report):
    assert not OUTPUT.exists()
    control = read(TESTS/"logs/k5_long5_r1.status.json")["runs"][0]
    reference = TESTS/"outputs"/control["label"]
    control_hashes = {Path(e["path"]).name:e for e in control["outputs"]}
    csv_path = TESTS/"figures"/(TAG+"_runtime.csv")
    log = TESTS/"logs"/(TAG+".log")
    report.update(stage="fresh_coarse_2tv",checked_frames=0,prefix_samples_native_0_ulp=0)
    with log.open("xb") as stream, csv_path.open("x",newline="",encoding="utf8") as csv_stream:
        p=subprocess.Popen([os.environ["ComSpec"],"/d","/c",str(TESTS/"configs"/("x"+TAG+"_win64_GPU.bat"))],
            cwd=CASE,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        report["owned_cmd_pid"]=p.pid;save(STATE,report)
        initial,writer,index=None,None,0
        def consume(i):
            nonlocal initial,writer
            b=cell.probe.native(OUTPUT,i)
            if initial is None:initial=b.copy()
            try:m=cell.metrics(b,initial)
            except Exception as error:
                raise RuntimeError(f"Native guard failed at PART {i}, t={b.time_s.iloc[0]:.17g}, step={b.step.iloc[0]}: {error}") from error
            if i<=15000:
                verify([control_hashes[f"Part_{i:04d}.bi4"]])
                old=cell.probe.native(reference,i)
                assert np.array_equal(b.id,old.id) and b.step.iloc[0]==old.step.iloc[0]
                assert abs(b.time_s.iloc[0]-old.time_s.iloc[0])<1e-8
                assert b[cell.FIELDS].to_numpy(dtype="<f8").tobytes()==old[cell.FIELDS].to_numpy(dtype="<f8").tobytes(),f"15-s native prefix changed at PART {i}, actual t={b.time_s.iloc[0]:.17g}"
                report["prefix_samples_native_0_ulp"]=i+1
            m["part"]=i
            if writer is None:writer=csv.DictWriter(csv_stream,fieldnames=list(m));writer.writeheader()
            writer.writerow(m);csv_stream.flush()
            report.update(last_checked_time_s=m["time_s"],last_metrics=m,checked_frames=i+1)
        try:
            while p.poll() is None:
                count=len(list((OUTPUT/"data").glob("Part_*.bi4")))
                while index<count-1:consume(index);index+=1
                report["updated_utc"]=utc();save(STATE,report);time.sleep(15)
            report.update(exit_code=p.returncode,owned_process_exited=True)
            assert p.returncode==0,"BAT failed; inspect "+str(log)
            count=len(list((OUTPUT/"data").glob("Part_*.bi4")))
            while index<count:consume(index);index+=1
        finally:
            if p.poll() is None:
                subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True);p.wait()
                report["stopped_by_monitor"]=True
            report.update(exit_code=p.returncode,owned_process_exited=True);save(STATE,report)
    # Compare to the precomputed repeated-binary64 sum, not an incorrect 1e-7
    # nominal-time check after 145M additions. Step/physical gates stay exact.
    last=report["last_metrics"]
    assert last["step"]==STEPS and abs(last["time_s"]-report["expected_binary64_final_time_s"])<1e-8
    assert abs(last["time_s"]-END)<DT and .0027444522857366896*(last["time_s"]-.01)>=2
    assert report["prefix_samples_native_0_ulp"]==15001
    text=(OUTPUT/"Run.out").read_text(encoding="utf-8-sig",errors="replace")
    assert "Finished execution (code=0)." in text
    calls=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
    work=re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
    limits=re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)",text)
    assert list(map(int,calls.groups()))==[2*STEPS,STEPS,STEPS,2*STEPS]
    assert list(map(int,work.groups()))==[STEPS+1,STEPS-1]
    assert float(limits[1])<=.2 and float(limits[2])<.01
    assert "DTs adjusted to DtMin............: 0" in text
    period=re.search(r"PeriodicXinc=\(([^,]+),",text)
    assert abs(float(period[1])+.025)<1e-12
    summary=pd.read_csv(OUTPUT/"Run.csv",sep=";").iloc[0]
    assert summary.Steps==STEPS and summary.Np==2592 and summary.Nfixed==32
    assert summary.PartsOut==0 and summary.PartFiles==index
    verify(report["inputs"])
    files=list((OUTPUT/"data").glob("Part_*.bi4"))+list((OUTPUT/"particles").glob("*"))+[OUTPUT/"Run.out",OUTPUT/"Run.csv",OUTPUT/(TAG+".xml"),log,csv_path]
    report.update(frames=index,completed=True,final=last,outputs=[bound(f) for f in files],
        loop_seconds=float(summary.TSimul),hg_max_dt_tau=float(limits[1]),hg_spin_bound=float(limits[2]))


def worker(args):
    assert not STATE.exists()
    expected=collections.deque(itertools.accumulate(itertools.repeat(DT,STEPS)),maxlen=1)[0]
    report=dict(status="running",stage="prerequisites",worker_pid=os.getpid(),started_utc=utc(),dt_s=DT,
        expected_steps=STEPS,nominal_time_s=END,expected_binary64_final_time_s=expected)
    save(STATE,report)
    try:
        report["checkpoint"],report["inputs"]=prerequisites()
        assert subprocess.check_output(["powershell","-NoProfile","-Command","@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"],text=True).strip()=="0"
        run(report);report.update(status="full_2tv_completed_pending_physical_review",stage="review")
    except Exception as error:
        report.update(status="rejected_or_interrupted",reason=str(error))
        if OUTPUT.exists():
            partial=list((OUTPUT/"data").glob("Part_*.bi4"))+[p for p in (OUTPUT/"Run.out",OUTPUT/"Run.csv",TESTS/"figures"/(TAG+"_runtime.csv"),TESTS/"logs"/(TAG+".log")) if p.is_file()]
            report["retained_partial_hashes"]=[bound(p) for p in partial]
    report["finished_utc"]=utc();save(STATE,report)
    message=(f"User-authorized same-thread fresh refined k1e-5 2Tv continuation {TAG}, not a new human observation. Detected {report['status']}. "
        f"First read {STATE}, its queue_attempt.json, logs/k5_full_admission_r1.json and tests/notes/formal_release_r1.md. "
        "Only one fresh GPU coarse run was admitted: width .025,dp .003125,dt5e-6,eta.04,xi.1;145750572 steps,nominal728.75286 s. "
        "Expected repeated-binary64 final time728.75285851827402, not a failed 1e-7 nominal-duration test. No half/full physical acceptance from this notice. "
        "Verify owned exits/exact reason,actual time/Tv,native IDs,all input/build/output hashes,original geometry/drainage/equivalent1000N/m within.001(actual250),post-.1s100-Pa stress/top-gap and HG guards. "
        "Verify all15001 same-dt first15-s native physical prefixes0ULP and every runtime CSV row against recorded native outputs. Native1-ms to15 s,then .1 s plus transition/final frames;use actual times. "
        "If a completed solver analysis failed,repair only new analysis,not solver. Inspect full pressure/material settlement/stress/Q/bottom/HG and all-Tv profile plots versus theory. "
        "Report quantified Chinese full-cycle outcome and observed cost proactively. On pass continue reviewed formal k5 publication without overwriting old rejected output,all-three comparison plots,later planned complex-wall checks,dependency cleanup and verified selective final Git. "
        "On failure report exact checked time and last sealed PART,retain evidence and diagnose without relaxed guards,raised damping,duplicate solver,old worker restart or KEEP. "
        "k3/k4 accepted delivery stands. Reduced cell excludes longer horizontal modes;elastic small-rotation/fresh HG only,no full-cycle half/plastic/general sliding/complex-wall/exact-HG-restart claim. "
        "Never restart/rearm this one-shot worker or send connectivity tests. Continue authorized delivery without waiting for a progress question.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x",encoding="utf8") as stream:json.dump(dict(thread=args.thread,utc=utc(),terminal=report.copy(),message=message),stream,indent=2)
    try:
        q=subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True,queue_status="queued" if q.returncode==0 else "failed_no_retry",queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:report.update(queue_attempted=True,queue_status="uncertain_no_retry",queue_error=str(error))
    save(STATE,report)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    for mode in ("prepare","check","launch","worker"):g.add_argument("--"+mode,action="store_true")
    p.add_argument("--codex");p.add_argument("--thread");args=p.parse_args()
    if args.prepare:return prepare()
    if args.worker:return worker(args)
    assert not STATE.exists() and not OUTPUT.exists()
    head,entries=prerequisites()
    if args.check:print(json.dumps(dict(ready=True,checkpoint=head,inputs=len(entries))));return
    assert args.codex and Path(args.codex).is_file() and args.thread
    argv=[sys.executable,"-B",str(Path(__file__).resolve()),"--worker","--codex",args.codex,"--thread",args.thread]
    with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
        child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(TAG+".launch.json")).open("x",encoding="utf8") as stream:json.dump(dict(pid=child.pid,argv=argv,thread=args.thread,checkpoint=head,inputs=entries),stream,indent=2)
    print(json.dumps(dict(pid=child.pid,state=str(STATE))))


if __name__=="__main__":main()
