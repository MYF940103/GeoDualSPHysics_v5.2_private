"""Independent receipts/native-reader checks before the first stage backup."""
import ast
import io
import json
import subprocess
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,TAG,bound,native,write_json,utc


def main():
    path=TESTS/'logs/poromech_stage1_r1.check.json';assert not path.exists()
    inputs=[]
    def verify(receipt):
        r=json.loads(receipt.read_text(encoding='utf-8-sig'))
        for key in ('sources','artifacts','inputs'):
            for e in r.get(key,[]):
                assert bound(e['path'])['sha256'].lower()==e['sha256'].lower(),e['path']
        inputs.append(bound(receipt));return r
    build=verify(TESTS/'logs/hydro_native_r1.build.json')
    assert bound(READER)['sha256'].lower()==build['executable_sha256'].lower()
    state=verify(TESTS/'logs'/f'{TAG}_smoke.status.json')
    visual=verify(TESTS/'logs'/f'{TAG}_smoke.review.json')
    assert state['status']=='completed_pending_review' and state['half_passed'] and visual['visual_review_passed']
    for run in state['runs']:
        assert run['exit_code']==0 and run['owned_exited']
        for e in run['outputs']:assert bound(e['path'])['sha256']==e['sha256'],e['path']
    verify(TESTS/'logs/lian_legacy_audit_r1.json')
    cryer=CASE.parent/'04_CryerProblem_PR'
    verify(cryer/'tests/logs/cryer_load_audit_r1.json')
    old=native(CASE/'CaseLianFlexibleStrip2D_PR_out',0)
    folder=TESTS/'outputs'/f'{TAG}_smoke_gpu_c'
    new=native(folder,0)
    assert np.array_equal(old.id,new.id)
    assert np.array_equal(old[['x','y','z']].to_numpy(dtype=np.float32),new[['x','y','z']].to_numpy(dtype=np.float32))
    reference=CASE.parent/'06_Yao2DConsolidation_PR/tests/outputs/read_native_spr_r1/ReadHydroMechPart.exe'
    # Two independent C++ readers must decode every shared native field exactly.
    for part in (0,30):
        raw=subprocess.check_output([str(reference),str(folder/'data'),str(part)])
        a=pd.read_csv(io.BytesIO(raw),float_precision='round_trip');b=native(folder,part)
        assert list(a.id)==list(b.id)
        columns=[c for c in a if c in b]
        assert np.array_equal(a[columns].to_numpy(),b[columns].to_numpy()),('Reader mismatch',part)
    inputs.append(bound(reference))
    for script in [TESTS/'scripts'/name for name in ('lian_release_r1.py','lian_legacy_audit_r1.py','lian_drained_followup_r1.py','poromech_stage1_check_r1.py')]+[cryer/'tests/support/cryer_load_audit_r1.py']:
        ast.parse(script.read_text(encoding='utf8'));inputs.append(bound(script))
    subprocess.run(['git','diff','--exit-code','--','src/source','src/VS'],cwd=REPO,check=True,capture_output=True)
    result=dict(passed=True,utc=utc(),scope='First-stage evidence and short admission only; not Lian/Cryer full accuracy acceptance',
        production_modified=False,formal_modified=False,independent_reader_shared_fields_exact_frames=[0,30],
        initial_old_float_representable_geometry_equal=True,pressure_half_max_pa=state['pressure_rms_half_max_pa'],
        top_material_half_max_mm=state['top_material_half_max_mm'],inputs=inputs)
    write_json(path,result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
