"""Adopt completed CPU timing t1; run only unrun t2/t4. Missing CPU force telemetry is explicit."""
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

STATE=TESTS/"logs/k5_cpu_timing_review_r1.status.json"


def cpu_metrics(a,initial):
    assert len(a)==2560 and np.array_equal(a.id,np.arange(32,2592)) and np.array_equal(a.id,initial.id)
    assert np.isfinite(a.select_dtypes("number").to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all()
    layer=np.rint(initial.z.to_numpy()/.003125-.5).astype(int)
    assert np.array_equal(np.bincount(layer),np.full(320,8))
    total=np.bincount(layer,weights=a.sigma_zz-a.pressure)/8
    disp=(initial.z-a.z).to_numpy()*1000
    dx=(a.x.to_numpy()-initial.x.to_numpy()+.0125)%.025-.0125
    span=max(np.ptp(a.z.to_numpy()[layer==i]) for i in range(320))*1000
    assert abs(dx).max()*1000<.5 and span<.5 and a.z.gt(0).all()
    t=float(a.time_s.iloc[0]);applicable=t>=.1-1e-7
    if applicable:
        assert set(a.id[a.drained.eq(1)])==set(a.id[layer==319]) and a.pressure[layer==319].eq(0).all()
        assert abs(total+10000).max()<=100 and abs(total[-1]-total[-2])<=100
    return dict(time_s=t,step=int(a.step.iloc[0]),mean_pressure_pa=float(a.pressure.mean()),
        max_layer_total_error_pa=float(abs(total+10000).max()),top_gap_pa=float(abs(total[-1]-total[-2])),
        Q_pa=float(np.sqrt(np.mean(np.diff(total,n=2)**2))),top_settlement_mm=float(disp[layer==319].mean()),
        bottom_settlement_mm=float(disp[layer==0].mean()),max_dx_mm=float(abs(dx).max()*1000),max_layer_span_mm=span,
        stress_guard_applicable=applicable,load_observation_available=bool(a.load_available.eq(1).all()))


def main():
    assert not STATE.exists()
    r=dict(status="waiting_t1",started_utc=utc(),runs=[],cpu_full_admitted=False)
    save(STATE,r)
    old=TESTS/"logs/k5_cpu_timing_r1.status.json"
    while json.loads(old.read_text(encoding="utf8"))["status"]=="running":time.sleep(10)
    before=json.loads(old.read_text(encoding="utf8"));assert len(before["runs"])==1 and before["runs"][0].get("exit_code")==0
    r["adopted_t1_attempt"]=bound(old)
    r["inputs"]=[bound(p) for p in (Path(__file__),REPO/"bin/windows/DualSPHysics5.2CPU_win64.exe",cell.probe.READER)]
    ref=TESTS/"outputs/k5_long5_r1_c"
    control=json.loads((TESTS/"logs/k5_long5_r1.status.json").read_text(encoding="utf8"))["runs"][0]
    hashes={Path(x["path"]).name:x for x in control["outputs"]};reference=[]
    for i in range(151):verify([hashes[f"Part_{i:04d}.bi4"]]);reference.append(cell.probe.native(ref,i))
    try:
        for threads in (1,2,4):
            label="k5_cpu_timing_r1_t"+str(threads);folder=TESTS/"outputs"/label
            item=dict(label=label,threads=threads,adopted_completed_run=threads==1);r["runs"].append(item)
            r.update(status="running",stage=label);save(STATE,r)
            if threads!=1:
                assert not folder.exists()
                bat=TESTS/"configs"/("x"+label+"_win64_CPU.bat")
                with (TESTS/"logs"/(label+".log")).open("xb") as stream:
                    p=subprocess.Popen([os.environ["ComSpec"],"/d","/c",str(bat)],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    item["owned_cmd_pid"]=p.pid;save(STATE,r)
                    try:code=p.wait()
                    finally:
                        if p.poll() is None:subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True);p.wait()
                    item.update(exit_code=code,owned_exited=True);assert code==0
            else:item.update(exit_code=0,owned_exited=True)
            files=sorted((folder/"data").glob("Part_*.bi4"));assert len(files)==151
            initial=cell.probe.native(folder,0);rows=[];pressure=settlement=stress=0.
            for i,b in enumerate(reference):
                a=cell.probe.native(folder,i);m=cpu_metrics(a,initial);rows.append(m)
                assert np.array_equal(a.id,b.id) and a.step.iloc[0]==b.step.iloc[0] and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
                pressure=max(pressure,float(np.sqrt(np.mean((a.pressure-b.pressure)**2))))
                settlement=max(settlement,abs(m["top_settlement_mm"]-float(((reference[0].z-b.z)[reference[0].z>.996]).mean())*1000))
                stress=max(stress,float(abs((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)).max()))
            assert pressure<=5 and settlement<=.005 and rows[-1]["step"]==30000 and abs(rows[-1]["time_s"]-.15)<1e-8
            text=(folder/"Run.out").read_text(encoding="utf-8-sig",errors="replace");assert "Finished execution (code=0)." in text
            hg=re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)",text);assert hg and float(hg[1])<=.2 and float(hg[2])<.01
            summary=pd.read_csv(folder/"Run.csv",sep=";").iloc[0];assert summary.Steps==30000 and summary.Np==2592 and summary.PartsOut==0
            item.update(saved_state_comparisons_passed=True,loop_seconds=float(summary.TSimul),frames=151,pressure_rms_max_pa=pressure,
                top_material_difference_mm=settlement,pointwise_total_stress_difference_pa=stress,final=rows[-1],
                force_observation_guard="not observed in CPU PART; not claimed passed",outputs=[bound(p) for p in files+[folder/"Run.out",folder/"Run.csv"]])
            pd.DataFrame(rows).to_csv(TESTS/"figures"/(label+"_review_history.csv"),index=False,mode="x")
            save(STATE,r)
        verify(r["inputs"])
        gpu=pd.read_csv(ref/"Run.csv",sep=";").iloc[0]
        r.update(status="timing_complete_pending_backend_decision",gpu_seconds_per_step=float(gpu.TSimul/gpu.Steps),
            timing_limitation="CPU with existing GPU/monitor active; GPU retained same-physics 15-s mean, not simultaneous duplicate GPU benchmark. CPU force telemetry absent, no full CPU admission.")
    except Exception as error:r.update(status="failed",reason=str(error));raise
    finally:r["updated_utc"]=utc();save(STATE,r)
    print(json.dumps([{k:v for k,v in x.items() if k!="outputs"} for x in r["runs"]],indent=2))


if __name__=="__main__":main()
