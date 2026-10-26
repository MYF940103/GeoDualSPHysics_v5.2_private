"""Actual-program SPR-OFF regression; original mixed normals and inputs."""
import json
from pathlib import Path
import subprocess
import numpy as np
from lian_release_r1 import CASE, TESTS, REPO, bound, native, write_json, utc

TAG='lian_spr_mix_regression_r1'


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    result=dict(passed=False,utc=utc(),inputs=[bound(__file__)],runs=[])
    try:
        for backend,stage,count in [('cpu','debug',3),('gpu','smoke',31)]:
            oldname='lian_opt3_r1_grad_'+stage; old=TESTS/'outputs'/oldname
            manifest=TESTS/'logs'/(oldname+'.run.json');m=json.loads(manifest.read_text())
            assert m['passed'] and m['exit_code']==0
            expected={str(Path(e['path']).resolve()).lower():e['sha256'] for e in m['outputs']}
            exe=REPO/'bin/windows'/('DualSPHysics5.2CPU_win64_debug.exe' if backend=='cpu' else 'DualSPHysics5.2_GEO_win64.exe')
            out=TESTS/'outputs'/(TAG+'_'+backend);assert not out.exists()
            log=TESTS/'logs'/(out.name+'.log')
            command=[str(exe),'-'+backend,'-stable','-mdbc_freeslip']
            if backend=='cpu':command+=['-ompthreads:8']
            command += [str(old/oldname),str(out),'-dirdataout','data','-svres','-svextraparts:1']
            with log.open('xb') as f:
                p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,cwd=CASE,timeout=360,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            assert p.returncode==0 and 'Finished execution (code=0)' in (out/'Run.out').read_text(errors='replace')
            assert len(list((out/'data').glob('Part_*.bi4')))==count
            for i in range(count):
                oldpart=old/'data'/f'Part_{i:04d}.bi4'
                assert bound(oldpart)['sha256']==expected[str(oldpart.resolve()).lower()]
                a,b=native(old,i),native(out,i)
                assert list(a.columns)==list(b.columns)
                assert a.to_numpy(dtype='<f8').tobytes()==b.to_numpy(dtype='<f8').tobytes(),(backend,i,'native bits differ')
            result['runs'].append(dict(backend=backend,exit_code=0,owned_exited=True,all_native_fields0ulp=True,
                saved_frames=count,actual_final_time_s=float(b.time_s.iloc[0]),command=command,
                reference=bound(manifest),program=bound(exe),
                outputs=[bound(p) for p in out.rglob('*') if p.is_file()]+[bound(log)]))
            print(backend,count,'native frames 0 ULP',flush=True)
        result['passed']=True
    finally:write_json(receipt,result)


if __name__=='__main__':main()
