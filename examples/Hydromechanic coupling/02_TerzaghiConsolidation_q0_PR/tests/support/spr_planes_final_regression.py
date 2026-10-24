"""Final CPU admission-only edit: reuse frozen controls, run only fresh new outputs."""
from pathlib import Path
import json
import subprocess
import numpy as np
from spr_planes_run import TESTS,REPO,bound
from k5_guard_probe import native


def main():
    tag='spr_planes_final_regression_r1';receipt=TESTS/'logs'/(tag+'.check.json');assert not receipt.exists()
    prior=TESTS/'logs/spr_planes_regression_r1.check.json';r=json.loads(prior.read_text());assert r['passed']
    pin=TESTS/'logs/spr_planes_cpu_short_verified.snapshot.json';p=json.loads(pin.read_text(encoding='utf-8-sig'))
    for x in p['files']:assert bound(x['snapshot'])['sha256']==x['sha256'] and bound(x['source'])['sha256']==x['sha256']
    exe=TESTS/'outputs/spr_planes_cpu_short_verified/DualSPHysics5.2CPU_win64.exe'
    result=dict(passed=False,inputs=[bound(__file__),bound(prior),bound(pin),bound(exe)],pairs=[])
    try:
        for enabled in (0,1):
            record=next(x for x in r['native_pairs'] if x['spr_enabled']==enabled)
            for x in record['outputs']:assert bound(x['path'])['sha256']==x['sha256']
            oldname='spr_planes_regression_r1_oneplane_'+str(enabled)
            prefix=TESTS/'outputs'/(oldname+'_input')/oldname;control=TESTS/'outputs'/(oldname+'_old')
            out=TESTS/'outputs'/(tag+'_spr'+str(enabled));assert not out.exists()
            log=TESTS/'logs'/(tag+'_spr'+str(enabled)+'.log')
            command=[str(exe),'-cpu','-ompthreads:1',str(prefix),str(out),'-dirdataout','data','-svres']
            with log.open('xb') as stream:process=subprocess.run(command,cwd=REPO/'bin/windows',stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
            assert process.returncode==0 and len(list((out/'data').glob('Part_*.bi4')))==31
            for i in range(31):
                a,b=native(control,i),native(out,i);assert np.array_equal(a.id,np.arange(40,1040)) and a.shape==b.shape
                numeric=a.select_dtypes('number').columns
                assert a[numeric].to_numpy(dtype='<f8').tobytes()==b[numeric].to_numpy(dtype='<f8').tobytes(),(enabled,i)
                assert a.drop(columns=numeric).equals(b.drop(columns=numeric))
            result['pairs'].append(dict(spr=enabled,frames=31,soil_native_ids=1000,all_fields_0ulp=True,actual_final_time_s=float(a.time_s.iloc[0]),
                owned_exited=True,exit_code=process.returncode,command=command,outputs=[bound(x) for x in out.rglob('*') if x.is_file()]))
            print('Current CPU SPR',enabled,'31 frames all native fields 0 ULP',flush=True)
        result['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
