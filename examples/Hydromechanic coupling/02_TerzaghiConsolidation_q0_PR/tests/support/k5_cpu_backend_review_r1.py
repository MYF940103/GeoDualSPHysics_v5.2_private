"""Read-only audit of retained CPU timings; no full-cycle backend admission."""
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import k5_cell_sequence as cell
from k5_cpu_timing_review_r1 import cpu_metrics
from formal_release_sequence import TESTS, save, utc
from mdbc_gpu_vector_run import read, bound, verify


def main():
    result=TESTS/"logs/k5_cpu_backend_review_r1.check.json"
    assert not result.exists()
    status_path=TESTS/"logs/k5_cpu_timing_review_r1.status.json"
    s=read(status_path);assert s["status"]=="timing_complete_pending_backend_decision"
    verify(s["inputs"]+[s["adopted_t1_attempt"]])
    old=read(TESTS/"logs/k5_cpu_timing_r1.status.json");verify(old["inputs"])
    evidence=[bound(status_path),bound(Path(__file__)),bound(TESTS/"support/k5_cpu_timing_review_r1.py")]
    ref=TESTS/"outputs/k5_long5_r1_c";gpu=pd.read_csv(ref/"Run.csv",sep=";").iloc[0]
    assert gpu.Steps==3000000 and gpu.Np==2592
    table=[];samples=[]
    for run in s["runs"]:
        assert run["exit_code"]==0 and run["owned_exited"] and run["saved_state_comparisons_passed"]
        verify(run["outputs"]);evidence+=run["outputs"]
        folder=TESTS/"outputs"/run["label"];text=(folder/"Run.out").read_text(encoding="utf-8-sig",errors="replace")
        hg=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
        work=re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
        assert list(map(int,hg.groups()))==[60000,30000,30000,60000]
        assert list(map(int,work.groups()))==[30001,29999] and "Finished execution (code=0)." in text
        history=pd.read_csv(TESTS/"figures"/(run["label"]+"_review_history.csv"),float_precision="round_trip")
        assert len(history)==151 and history.time_s.is_monotonic_increasing
        assert np.array_equal(history.step,np.arange(151)*200)
        post=history[history.time_s>=.1-1e-7]
        assert post.max_layer_total_error_pa.le(100).all() and post.top_gap_pa.le(100).all()
        assert not history.load_observation_available.any()
        initial=cell.probe.native(folder,0)
        for i in (0,10,100,150):
            a=cell.probe.native(folder,i);m=cpu_metrics(a,initial);b=cell.probe.native(ref,i)
            assert np.array_equal(a.id,b.id) and a.step.iloc[0]==b.step.iloc[0] and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
            for key in ("time_s","step","mean_pressure_pa","top_settlement_mm","max_layer_total_error_pa","top_gap_pa","Q_pa"):
                assert np.isclose(m[key],history.iloc[i][key],rtol=1e-13,atol=1e-12),key
            pressure=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
            assert pressure<=5
            samples.append(dict(threads=run["threads"],part=i,time_s=m["time_s"],pressure_rms_pa=pressure))
        assert run["pressure_rms_max_pa"]<=5 and run["top_material_difference_mm"]<=.005
        table.append(dict(backend="CPU",threads=run["threads"],duration_s=.15,steps=30000,loop_seconds=run["loop_seconds"],
            milliseconds_per_step=1000*run["loop_seconds"]/30000,equivalent_015s_loop_seconds=run["loop_seconds"],
            pressure_rms_max_pa=run["pressure_rms_max_pa"],top_material_difference_mm=run["top_material_difference_mm"]))
    table.append(dict(backend="GPU retained 15-s mean",threads=1,duration_s=15.,steps=3000000,loop_seconds=float(gpu.TSimul),
        milliseconds_per_step=1000*float(gpu.TSimul/gpu.Steps),equivalent_015s_loop_seconds=float(gpu.TSimul)/100))
    output=TESTS/"figures/k5_cpu_backend_review_r1_timing.csv"
    pd.DataFrame(table).to_csv(output,index=False,mode="x")
    report=dict(passed=True,utc=utc(),scope="Timing and retained .15-s native comparison audit, not full CPU admission",cpu_full_admitted=False,
        cpu_force_observation_passed=False,cpu_force_observation="not available, never interpreted as zero applied force",table=table,
        independent_native_samples=samples,full_saved_history_samples_per_cpu=151,all_retained_cpu_output_hashes_verified=True,
        timing_limitation=s["timing_limitation"],evidence=evidence+[bound(output)])
    save(result,report);print(json.dumps({k:v for k,v in report.items() if k!="evidence"},indent=2))


if __name__=="__main__":main()
