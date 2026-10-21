"""Same-physics CPU 1/2/4-thread .15-s timing and native GPU comparison."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
import pandas as pd
import k5_cell_sequence as cell
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import bound, verify

TAG="k5_cpu_timing_r1"
REFERENCE="k5_long5_r1_c"
STATE=TESTS/"logs"/(TAG+".status.json")


def prepare():
    xml=(TESTS/"configs"/(REFERENCE+"_Def.xml")).read_text(encoding="utf8")
    xml,n=re.subn(r'(<parameter key="TimeMax" value=")[^"]*(")',lambda m:m[1]+"0.15"+m[2],xml);assert n==1
    bat=(TESTS/"configs"/("x"+REFERENCE+"_win64_GPU.bat")).read_text(encoding="utf8")
    patch="*** Begin Patch\n"
    for threads in (1,2,4):
        label=TAG+"_t"+str(threads)
        content=bat.replace("set case="+REFERENCE,"set case="+label).replace("DualSPHysics5.2_GEO_win64.exe","DualSPHysics5.2CPU_win64.exe")
        content=content.replace("-gpu:0 -ompthreads:1",f"-cpu -ompthreads:{threads}").replace("-nsteps:3000000","-nsteps:30000")
        content=content.replace("-first:15000 -last:15000","-first:150 -last:150")
        for path,text in ((TESTS/"configs"/(label+"_Def.xml"),xml),(TESTS/"configs"/("x"+label+"_win64_CPU.bat"),content)):
            assert not path.exists()
            patch+="*** Add File: "+str(path)+"\n"+"\n".join("+"+s for s in text.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run():
    assert not STATE.exists()
    report=dict(status="running",started_utc=utc(),runs=[],physical_candidate_changed=False,
        gpu_long_run_retained=True,timing_limitation="CPU measured while the existing GPU run/monitor remain active; GPU reference is retained same-physics 15-s loop cost, not concurrent duplicate GPU timing.")
    report["inputs"]=[bound(p) for p in (REPO/"bin/windows/DualSPHysics5.2CPU_win64.exe",Path(__file__),cell.probe.READER)]
    save(STATE,report)
    reference=TESTS/"outputs"/REFERENCE
    control=json.loads((TESTS/"logs/k5_long5_r1.status.json").read_text(encoding="utf8"))["runs"][0]
    hashes={Path(x["path"]).name:x for x in control["outputs"]}
    reference_frames=[]
    for i in range(151):
        verify([hashes[f"Part_{i:04d}.bi4"]]);reference_frames.append(cell.probe.native(reference,i))
    try:
        for threads in (1,2,4):
            label=TAG+"_t"+str(threads);folder=TESTS/"outputs"/label
            bat=TESTS/"configs"/("x"+label+"_win64_CPU.bat")
            assert not folder.exists()
            inputs=[bound(bat),bound(TESTS/"configs"/(label+"_Def.xml"))]
            with (TESTS/"logs"/(label+".log")).open("xb") as stream:
                p=subprocess.Popen([os.environ["ComSpec"],"/d","/c",str(bat)],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                item=dict(threads=threads,label=label,owned_cmd_pid=p.pid,started_utc=utc());report["runs"].append(item);save(STATE,report)
                try:code=p.wait()
                finally:
                    if p.poll() is None:subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True);p.wait()
                item.update(exit_code=code,owned_exited=True);assert code==0,"CPU BAT failed: "+label
            files=sorted((folder/"data").glob("Part_*.bi4"));assert len(files)==151
            rows=[];pressure=settlement=stress=0.;initial=cell.probe.native(folder,0)
            for i in range(151):
                a=cell.probe.native(folder,i);b=reference_frames[i];m=cell.metrics(a,initial);rows.append(m)
                assert np.array_equal(a.id,b.id) and a.step.iloc[0]==b.step.iloc[0] and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
                pressure=max(pressure,float(np.sqrt(np.mean((a.pressure-b.pressure)**2))))
                settlement=max(settlement,abs(float((initial.z-a.z)[initial.z>.996].mean()-(reference_frames[0].z-b.z)[reference_frames[0].z>.996].mean())*1000))
                stress=max(stress,float(abs((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)).max()))
            assert rows[-1]["step"]==30000 and abs(rows[-1]["time_s"]-.15)<1e-8
            assert pressure<=5 and settlement<=.005,"Original cross-backend pressure/material-settlement comparison failed"
            text=(folder/"Run.out").read_text(encoding="utf-8-sig",errors="replace")
            assert "Finished execution (code=0)." in text
            hg=re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)",text);assert hg and float(hg[1])<=.2 and float(hg[2])<.01
            summary=pd.read_csv(folder/"Run.csv",sep=";").iloc[0];assert summary.Steps==30000 and summary.Np==2592 and summary.PartsOut==0
            verify(inputs+report["inputs"])
            item.update(passed=True,frames=151,loop_seconds=float(summary.TSimul),pressure_rms_max_pa=pressure,top_material_difference_mm=settlement,
                pointwise_total_stress_difference_pa=stress,final=rows[-1],inputs=inputs,outputs=[bound(p) for p in files+[folder/"Run.out",folder/"Run.csv"]])
            pd.DataFrame(rows).to_csv(TESTS/"figures"/(label+"_history.csv"),index=False,mode="x")
            save(STATE,report)
        report["status"]="cpu_short_timing_passed_pending_backend_decision"
    except Exception as error:
        report.update(status="failed",reason=str(error));raise
    finally:
        report["updated_utc"]=utc();save(STATE,report)
    print(json.dumps([{k:v for k,v in r.items() if k not in ("inputs","outputs")} for r in report["runs"]],indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepare",action="store_true");a=p.parse_args()
    prepare() if a.prepare else run()
