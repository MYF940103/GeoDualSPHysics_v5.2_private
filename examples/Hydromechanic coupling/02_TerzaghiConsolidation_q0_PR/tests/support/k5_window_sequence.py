"""Dense short preflight and separately admitted 15-s periodic-cell pairs."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import pandas as pd
import k5_cell_sequence as cell
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify


def setup(stage):
    fast=stage.endswith("8")
    return dict(tag="k5_"+stage+"_r1", duration=".15" if stage.startswith("dense") else "15",
        steps=(".000008",".000004") if fast else (".000005",".0000025"),
        reference="k5_step8_1s_r1" if fast else "k5_cell8_1s_r1", family="8" if fast else "5")


def prepare(cfg):
    patch="*** Begin Patch\n"
    for suffix,dt in zip(("c","h"),cfg["steps"]):
        old=cfg["reference"]+"_1"+suffix; label=cfg["tag"]+"_"+suffix
        xml=(TESTS/"configs"/(old+"_Def.xml")).read_text(encoding="utf8")
        for key,value in (("TimeMax",cfg["duration"]),("TimeOut","0.000999999999")):
            xml,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],xml); assert n==1
        bat=(TESTS/"configs"/("x"+old+"_win64_GPU.bat")).read_text(encoding="utf8").replace("set case="+old,"set case="+label)
        nsteps=int(Decimal(cfg["duration"])/Decimal(dt))
        bat,n=re.subn(r'-nsteps:\d+', '-nsteps:'+str(nsteps),bat);assert n==1
        # Keep every native 1-ms frame for the gates, but export only the final
        # particles here. Other frames remain reproducible from retained BI4.
        last=int(Decimal(cfg["duration"])/Decimal(".001"))
        bat=bat.replace("%partvtk% -dirin",f"%partvtk% -first:{last} -last:{last} -dirin")
        for path,content in ((TESTS/"configs"/(label+"_Def.xml"),xml),(TESTS/"configs"/("x"+label+"_win64_GPU.bat"),bat)):
            assert not path.exists()
            patch+="*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def prefix(report,cfg,suffix):
    reference=TESTS/"outputs"/(cfg["reference"]+"_1"+suffix)
    current=TESTS/"outputs"/(cfg["tag"]+"_"+suffix)
    count=31 if cfg["duration"]==".15" else 201
    for i in range(count):
        a,b=cell.probe.native(reference,i),cell.probe.native(current,5*i)
        assert np.array_equal(a.id,b.id) and a.step.iloc[0]==b.step.iloc[0]
        assert abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
        assert a[cell.FIELDS].to_numpy(dtype="<f8").tobytes()==b[cell.FIELDS].to_numpy(dtype="<f8").tobytes(), f"Sampling-only native prefix changed at {a.time_s.iloc[0]:.17g} s"
    report.setdefault("prefixes",[]).append(dict(suffix=suffix,samples=count,native_0_ulp=True));save(cell.STATE,report)


def half(report,cfg):
    folders=[TESTS/"outputs"/(cfg["tag"]+"_"+s) for s in ("c","h")]
    first=cell.probe.native(folders[0],0);top=first.z>.996
    count=int(Decimal(cfg["duration"])/Decimal(".001"))+1; rows=[]
    failure=None
    for i in range(count):
        a,b=[cell.probe.native(f,i) for f in folders]
        assert np.array_equal(a.id,b.id) and b.step.iloc[0]==2*a.step.iloc[0]
        assert abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
        m=dict(time_s=float(a.time_s.iloc[0]),pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
            top_settlement_difference_mm=abs(float((a.z[top]-b.z[top]).mean()*1000)))
        rows.append(m)
        if m["pressure_rms_pa"]>5 or m["top_settlement_difference_mm"]>.005:
            failure=m;break
    h=pd.DataFrame(rows);csv=TESTS/"figures"/(cfg["tag"]+"_half.csv");h.to_csv(csv,index=False,mode="x")
    report["half"]=dict(passed=failure is None,samples_checked=len(rows),expected_samples=count,
        max_pressure_rms_pa=float(h.pressure_rms_pa.max()),max_top_settlement_difference_mm=float(h.top_settlement_difference_mm.max()),
        failure=failure,csv=bound(csv));save(cell.STATE,report)
    if failure:raise RuntimeError("Original dense 5-Pa/.005-mm half gate failed: "+json.dumps(failure))


def run(cfg):
    state=TESTS/"logs"/(cfg["tag"]+".status.json");assert not state.exists()
    cell.TAG,cell.STATE=cfg["tag"],state
    report=dict(status="running",stage="prerequisites",worker_pid=os.getpid(),started_utc=utc(),config=cfg,runs=[])
    save(state,report)
    try:
        review=TESTS/"logs"/("k5_step8_review_r1.check.json" if cfg["family"]=="8" else "k5_cell_review_r1.check.json")
        reviewed=read(review);assert reviewed["audit_passed"]
        visual=review.with_name(review.name.replace(".check.json",".visual.json"));assert read(visual)["inspected"]
        # Recheck the controls actually used by this stage, not every older
        # grid/width experiment nested in the review's provenance chain.
        source_path=TESTS/"logs"/(cfg["reference"]+".status.json")
        binding=[p for p in reviewed["evidence"] if Path(p["path"]).resolve()==source_path.resolve()]
        assert len(binding)==1;verify(binding)
        source=read(source_path);verify(source["inputs"])
        for r in source["runs"]:
            if r["label"] in (cfg["reference"]+"_1c",cfg["reference"]+"_1h"):verify(r["outputs"])
        required=[review,visual,source_path]
        if cfg["duration"]=="15":
            admission=TESTS/"logs/k5_window_admission_r1.json";a=read(admission)
            assert a["admit_15s"] and a["family"]==cfg["family"] and not a["admit_2tv"]
            dense=TESTS/"logs"/("k5_dense"+cfg["family"]+"_r1.status.json")
            d=read(dense);assert d["status"]=="pair_passed_pending_review" and d["half"]["passed"]
            verify(d["inputs"])
            for r in d["runs"]:verify(r["outputs"])
            required += [admission,dense]
        count=subprocess.check_output(["powershell","-NoProfile","-Command","@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"],text=True).strip();assert count=="0"
        report["checkpoint"]=subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip()
        report["inputs"]=[bound(p) for p in [Path(__file__),Path(cell.__file__),Path(cell.probe.__file__),cell.probe.READER,
            TESTS/"support/k5_grid320_sequence.py",TESTS/"support/formal_release_sequence.py",TESTS/"support/mdbc_gpu_vector_run.py",
            REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe",REPO/"bin/windows/GenCase_win64.exe",REPO/"bin/windows/PartVTK_win64.exe"]+required]
        for suffix in ("c","h"):
            report["inputs"] += [bound(TESTS/"configs"/name) for name in (cfg["tag"]+"_"+suffix+"_Def.xml","x"+cfg["tag"]+"_"+suffix+"_win64_GPU.bat")]
        for suffix,dt in zip(("c","h"),cfg["steps"]):
            cell.run(report,suffix,cfg["duration"],dt)
            assert report["runs"][-1]["frames"]==int(Decimal(cfg["duration"])/Decimal(".001"))+1
            prefix(report,cfg,suffix)
        half(report,cfg);verify(report["inputs"])
        report.update(status="pair_passed_pending_review",stage="review")
    except Exception as error:report.update(status="rejected_or_interrupted",reason=str(error))
    report["finished_utc"]=utc();save(state,report);return report


def worker(cfg,args):
    report=run(cfg);state=TESTS/"logs"/(cfg["tag"]+".status.json")
    message=(f"User-authorized same-thread k1e-5 15-s dense pair {cfg['tag']}, not a new human observation. Detected {report['status']}. "
        f"Read {state}, its queue_attempt.json, logs/k5_window_admission_r1.json and tests/notes/formal_release_r1.md before claims. "
        f"Only fresh width=.025,dp=.003125,eta=.04,xi=.1,dt={cfg['steps']} 15-s coarse/half were admitted, native1-ms output. "
        "Verify owned exits/stop reason, actual times/native IDs and all input-output-build hashes; original geometry/drainage/equivalent1000N/m within.001(actual250), post-.1s100-Pa stress/top-gap and HG guards. "
        "Verify both saved-output prefix0ULP against retained same-dt1-s states (201 matching samples), plus original full15001-sample5-Pa/.005-mm half gate; inspect any earlier failure before later result. "
        "Generate/inspect pressure/material settlement/stress/Q/bottom/HG runtime and theory comparisons at actual times, quantify observed loop cost. Only final particles exported; all1-msBI4 retained. "
        "No full-cycle acceptance or automatic2Tv/formal admission. Periodic-cell equivalence was short uniform1D only, not long-wavelength/general sliding validation. "
        "If failed, report exact reason/time, preserve accepted controls and diagnose without relaxed gates, increased damping, duplicate solver or overwrite; no repeated dt search. "
        "Old formal k5 failed at.10001guard(lastcompletePART.2), not2Tv; k3/k4 delivery stands and KEEP must not restart. Continue authorized delivery after physical/cost review without waiting for progress query. "
        "No production/formal changes yet. This worker queues once; never restart/rearm it or send connectivity tests.")
    with (TESTS/"logs"/(cfg["tag"]+".queue_attempt.json")).open("x",encoding="utf8") as stream:json.dump(dict(thread=args.thread,utc=utc(),terminal=report.copy(),message=message),stream,indent=2)
    try:
        q=subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True,queue_status="queued" if q.returncode==0 else "failed_no_retry",queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:report.update(queue_attempted=True,queue_status="uncertain_no_retry",queue_error=str(error))
    save(state,report)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--stage",choices=("dense8","dense5","long8","long5"),required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument("--prepare",action="store_true");g.add_argument("--run",action="store_true");g.add_argument("--launch",action="store_true");g.add_argument("--worker",action="store_true")
    p.add_argument("--codex");p.add_argument("--thread");args=p.parse_args();cfg=setup(args.stage)
    if args.prepare:return prepare(cfg)
    if args.run:
        assert args.stage.startswith("dense")
        r=run(cfg);print(json.dumps({k:v for k,v in r.items() if k not in ("inputs","runs")},indent=2));return
    assert args.stage.startswith("long") and args.codex and Path(args.codex).is_file() and args.thread
    if args.worker:return worker(cfg,args)
    assert not (TESTS/"logs"/(cfg["tag"]+".status.json")).exists()
    a=read(TESTS/"logs/k5_window_admission_r1.json");assert a["admit_15s"] and a["family"]==cfg["family"] and not a["admit_2tv"]
    with (TESTS/"logs"/(cfg["tag"]+".worker.log")).open("xb") as stream:
        argv=[sys.executable,"-B",str(Path(__file__).resolve()),"--stage",args.stage,"--worker","--codex",args.codex,"--thread",args.thread]
        child=subprocess.Popen(argv,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(cfg["tag"]+".launch.json")).open("x",encoding="utf8") as stream:json.dump(dict(pid=child.pid,argv=argv,thread=args.thread),stream,indent=2)
    print(json.dumps(dict(pid=child.pid,stage=args.stage)))


if __name__=="__main__":main()
