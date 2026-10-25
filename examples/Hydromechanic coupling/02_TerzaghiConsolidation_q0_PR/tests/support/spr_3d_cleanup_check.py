"""Exact saved-field regression and CUDA exit-lifetime check, no solver runs."""
import io
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from spr_planes_run import TESTS,REPO,bound


def main():
    receipt=TESTS/'logs/spr_3d_cleanup_r1.check.json';assert not receipt.exists()
    evidence=[bound(__file__),bound(REPO/'src/source/JSphGpu.cpp'),bound(TESTS/'logs/spr_3d_precleanup_r1.snapshot.json')]
    logs=['spr_3d_gpu_prod_debug_r1','spr_3d_gpu_debug_smoke_r1','spr_3d_gpu_debug_prod_r2','spr_3d_gpu_debug_smoke_r2']
    for i,name in enumerate(logs):
        path=TESTS/'logs'/(name+'.memcheck.log');text=path.read_text();evidence.append(bound(path))
        assert ('ERROR SUMMARY: 1 error' if i<2 else 'ERROR SUMMARY: 0 errors') in text,name
    old=TESTS/'outputs/spr_3d_gpu_debug_smoke_r1/pulse.csv';new=TESTS/'outputs/spr_3d_gpu_debug_smoke_r2/pulse.csv'
    c=pd.read_csv(old,float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
    h=pd.read_csv(new,float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
    assert c.shape==h.shape==(4800,18) and list(c.columns)==list(h.columns)
    for column in c:assert c[column].to_numpy().tobytes()==h[column].to_numpy().tobytes(),column
    evidence.extend([bound(old),bound(new)])
    reader=REPO/'examples/Hydromechanic coupling/06_Yao2DConsolidation_PR/tests/outputs/read_native_spr_r1/ReadHydroMechPart.exe';evidence.append(bound(reader))
    root_pairs=[]
    for part in range(3):
        frames=[]
        for folder in ['spr_3d_gpu_prod_debug_r1','spr_3d_gpu_debug_prod_r2']:
            data=TESTS/'outputs'/folder/'data'
            result=subprocess.run([str(reader),str(data),str(part)],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            frame=pd.read_csv(io.BytesIO(result.stdout),float_precision='round_trip').sort_values('id').reset_index(drop=True);assert len(frame)==1600
            frames.append(frame);evidence.extend(bound(path) for path in sorted(data.glob('*')) if path.is_file())
        a,b=frames;assert list(a.columns)==list(b.columns) and np.isfinite(a.to_numpy()).all() and np.isfinite(b.to_numpy()).all()
        for column in a:assert a[column].to_numpy().tobytes()==b[column].to_numpy().tobytes(),(part,column)
        root_pairs.append(dict(part=part,soil_count=len(a),columns=len(a.columns),all_native_fields_0ulp=True))
    for path in ['spr_3d_cpu_debug_r2.build.log','spr_3d_gpu_debug_r2.build.log','spr_3d_gpu_release_r2.build.log','spr_3d_Debug_r2.build.json','spr_3d_Release_r2.build.json']:
        evidence.append(bound(TESTS/'logs'/path))
    result=dict(passed=True,original_memcheck_errors_each=1,new_memcheck_errors_each=0,nonzero_observer_samples=3,nonzero_observer_native_fields_0ulp=True,
        real_program_native_fields=root_pairs,production_change='Delete GaugeSystem before cudaDeviceReset; no numerical change',physical_acceptance=False,evidence=evidence)
    with receipt.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'},indent=2))


if __name__=='__main__':main()
