"""Bounded 6.25/3.125-us .15-s GPU pair; original guards and accepted controls retained."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import k5_cell_sequence as cell
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify

TAG="k5_dt625_short_r1"
STATE=TESTS/"logs"/(TAG+".status.json")
VARIANTS=(("c",".00000625"),("h",".000003125"))


def prepare():
    old="k5_long5_r1_c"
    source=(TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
    batch=(TESTS/"configs"/("x"+old+"_win64_GPU.bat")).read_text(encoding="utf8")
    patch="*** Begin Patch\n"
    for suffix,dt in VARIANTS:
        label=TAG+"_"+suffix;text=source
        for key,value in (("DtIni",dt),("DtFixed",dt),("TimeMax",".15")):
            text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],text);assert n==1
        text=text.replace("Formal fixed step; conductivity-specific stability limit","Candidate fixed step; short pair only, not admitted to a full run")
        bat=batch.replace("set case="+old,"set case="+label).replace("-nsteps:3000000","-nsteps:"+str(int(Decimal('.15')/Decimal(dt))))
        bat=bat.replace("-first:15000 -last:15000","-first:150 -last:150")
        for path,content in ((TESTS/"configs"/(label+"_Def.xml"),text),(TESTS/"configs"/("x"+label+"_win64_GPU.bat"),bat)):
            assert not path.exists()
            patch+="*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def prerequisites():
    retirement=TESTS/"logs/k5_full_r1_acceleration_stop.json"
    audit=read(retirement);assert audit["phase"]=="retired" and audit["owned_processes_exited"] and not audit["physical_failure"]
    assert read(TESTS/"logs/k5_full_r1.status.json")["status"]=="intentionally_stopped_for_step_trial"
    gate=TESTS/"logs/k5_long5_r1.review.json";visual=TESTS/"logs/k5_long5_r1.visual.json"
    assert read(gate)["audit_passed"] and read(visual)["inspected"]
    verify(read(TESTS/"logs/k5_long5_r1.status.json")["inputs"])
    assert read(TESTS/"logs/k5_cpu_backend_review_r1.check.json")["passed"]
    head=subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip()
    remote=subprocess.check_output(["git","-C",str(REPO),"ls-remote","origin","refs/heads/u-pw"],text=True).split()[0]
    assert head==remote
    assert not subprocess.check_output(["git","-C",str(REPO),"diff","--name-only","--","src/source","src/VS"],text=True).strip()
    paths=[Path(__file__),Path(cell.__file__),Path(cell.probe.__file__),cell.probe.READER,gate,visual,retirement,
        TESTS/"logs/k5_long5_r1.status.json",TESTS/"logs/k5_cpu_backend_review_r1.check.json",
        TESTS/"support/k5_grid320_sequence.py",TESTS/"support/formal_release_sequence.py",TESTS/"support/mdbc_gpu_vector_run.py"]
    paths += [REPO/"bin/windows"/name for name in ("DualSPHysics5.2_GEO_win64.exe","GenCase_win64.exe","PartVTK_win64.exe")]
    for suffix,dt in VARIANTS:
        paths += [TESTS/"configs"/name for name in (TAG+"_"+suffix+"_Def.xml","x"+TAG+"_"+suffix+"_win64_GPU.bat")]
        assert Decimal('.01')/Decimal(dt)==int(Decimal('.01')/Decimal(dt))
        assert Decimal('.001')/Decimal(dt)==int(Decimal('.001')/Decimal(dt))
    return head,[bound(p) for p in paths]


def compare(report,left,right,kind):
    lf,rf=[TESTS/"outputs"/label for label in (left,right)]
    assert len(list((lf/"data").glob("Part_*.bi4")))>=151 and len(list((rf/"data").glob("Part_*.bi4")))==151
    initial=cell.probe.native(lf,0);top=initial.z>.996
    hashes={}
    if kind=="reference_step":
        control=next(x for x in read(TESTS/"logs/k5_long5_r1.status.json")["runs"] if x["label"]==left)
        hashes={Path(x["path"]).name:x for x in control["outputs"]}
    peaks=dict(pressure_rms_pa=0.,top_settlement_difference_mm=0.,max_total_stress_difference_pa=0.)
    item=dict(left=left,right=right,kind=kind,samples=0,passed=False);report["comparisons"].append(item)
    for i in range(151):
        if hashes:verify([hashes[f"Part_{i:04d}.bi4"]])
        a,b=cell.probe.native(lf,i),cell.probe.native(rf,i)
        assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
        if kind=="half":assert b.step.iloc[0]==2*a.step.iloc[0]
        p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)));u=abs(float((a.z[top]-b.z[top]).mean()*1000))
        stress=float(abs((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)).max())
        peaks={key:max(peaks[key],value) for key,value in zip(peaks,(p,u,stress))}
        item.update(samples=i+1,**peaks)
        if p>5 or u>.005:
            item.update(failed_time_s=float(a.time_s.iloc[0]),failed_part=i,pressure_at_failure_pa=p,settlement_at_failure_mm=u)
            save(STATE,report);raise RuntimeError(f"{kind} original limit failed at actual t={a.time_s.iloc[0]:.17g}: pressure RMS={p:.9g} Pa, material settlement={u:.9g} mm")
    item["passed"]=True;save(STATE,report)


def worker(args):
    assert not STATE.exists();cell.TAG,cell.STATE=TAG,STATE
    r=dict(status="running",stage="prerequisites",worker_pid=os.getpid(),started_utc=utc(),runs=[],comparisons=[],full_run_admitted=False)
    save(STATE,r)
    try:
        r["checkpoint"],r["inputs"]=prerequisites()
        assert subprocess.check_output(["powershell","-NoProfile","-Command","@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"],text=True).strip()=="0"
        for suffix,dt in VARIANTS:
            cell.run(r,suffix,".15",dt)
            assert len(list((TESTS/"outputs"/(TAG+"_"+suffix)/"data").glob("Part_*.bi4")))==151
            compare(r,"k5_long5_r1_"+suffix,TAG+"_"+suffix,"reference_step")
        compare(r,TAG+"_c",TAG+"_h","half")
        verify(r["inputs"]);r.update(status="short_pair_passed_pending_review",stage="review")
    except Exception as error:r.update(status="rejected_or_interrupted",reason=str(error))
    r["finished_utc"]=utc();save(STATE,r)
    message=(f"User-authorized same-thread bounded6.25/3.125-us GPU short-pair continuation {TAG}, not a new human observation. Detected {r['status']}. "
        f"Read {STATE}, its queue_attempt.json, tests/notes/k5_dt625_short_r1.md, logs/k5_cpu_backend_review_r1.check.json and logs/k5_full_r1_acceleration_stop.json before claims. "
        "Only fresh .15-s coarse/half,1-ms native output,width.025,dp.003125,eta.04,xi.1 were admitted; no automatic1s/15s/2Tv. "
        "Verify owned exits/exact stop,actual times/native IDs,build-input-output hashes,all151-sample geometry/drainage/equivalent1000N/m within.001(actual250),post-.1s100-Pa stress/top-gap and HG/natural-step guards. "
        "Review original5-Pa/.005-mm half and separate reference-step comparisons against retained5/2.5-us first.15s; use actual matched times. Generate/inspect pressure/material settlement/stress/Q/HG plots. "
        "Original5-us GPU full run was intentionally retired after user authorized acceleration trials; retain its partial evidence and exact last readable time, never call it2Tv or restart its watcher. "
        "CPU1/2/4 were slower;8-thread .03s timing also slower, not a physical admission. CPU force telemetry is absent and not claimed passed. GPU remains selected; no production/source/formal inputs changed for this step candidate. "
        "If new candidate fails, report exact reason/time without relaxed thresholds,raised damping,duplicate solvers,old worker restart or automaticfailed-step long run. Preserve accepted5/2.5-us fallback; decide next safe delivery from evidence, not unbounded parameter search. "
        "If it passes, proactively report quantified Chinese results, then continue separately gated1-s candidate pair, later15s only after review; only after those gates consider a new full run with one verified same-thread completion.6.25us saves20% steps, not orders of magnitude. "
        "User authorized continued tasks without asking again; k3/k4 accepted delivery stands and must not be rerun. Never restart/rearm this one-shot worker or send connectivity tests.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x",encoding="utf8") as stream:json.dump(dict(utc=utc(),thread=args.thread,terminal=r.copy(),message=message),stream,indent=2)
    try:
        q=subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(queue_status="queued" if q.returncode==0 else "failed_no_retry",queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:r.update(queue_status="uncertain_no_retry",queue_error=str(error))
    save(STATE,r)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepare",action="store_true");p.add_argument("--check",action="store_true");p.add_argument("--worker",action="store_true");p.add_argument("--codex");p.add_argument("--thread");a=p.parse_args()
    if a.prepare:prepare()
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
