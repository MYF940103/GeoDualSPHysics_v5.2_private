"""Check only the current GPU program against retained old mode5 paths."""
import json
import subprocess
import numpy as np
from spr_planes_run import TESTS,REPO,bound
from k5_guard_probe import native


def main():
    tag='spr_gpu_paths_r2';receipt=TESTS/'logs'/(tag+'.check.json');assert not receipt.exists()
    prior=TESTS/'logs/spr_gpu_paths_r1.check.json';old=json.loads(prior.read_text());assert old['passed']
    exe=REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe';result=dict(passed=False,inputs=[bound(__file__),bound(prior),bound(exe)],pairs=[])
    try:
        for enabled in (0,1):
            for xi in ('0','.1'):
                stem='_s'+str(enabled)+'_hg'+('0' if xi=='0' else '1');oldname='spr_gpu_paths_r1'+stem;name=tag+stem
                control=TESTS/'outputs'/(oldname+'_old');prefix=TESTS/'outputs'/(oldname+'_input')/oldname
                out=TESTS/'outputs'/name;log=TESTS/'logs'/(name+'.log');assert not out.exists()
                pair=next(x for x in old['pairs'] if x['spr']==enabled and x['xi']==xi)
                for item in pair['outputs']:assert bound(item['path'])['sha256']==item['sha256']
                command=[str(exe),'-gpu','-stable',str(prefix),str(out),'-dirdataout','data','-svres']
                with log.open('xb') as stream:child=subprocess.run(command,cwd=exe.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
                assert child.returncode==0 and len(list((out/'data').glob('Part_*.bi4')))==31
                for i in range(31):
                    a,b=native(control,i),native(out,i);assert np.array_equal(a.id,np.arange(40,1040)) and a.shape==b.shape
                    fields=a.select_dtypes('number').columns
                    assert a[fields].to_numpy(dtype='<f8').tobytes()==b[fields].to_numpy(dtype='<f8').tobytes(),(name,i)
                    assert a.drop(columns=fields).equals(b.drop(columns=fields))
                result['pairs'].append(dict(spr=enabled,xi=xi,frames=31,native_soil_count=1000,all_fields_0ulp=True,exit_code=0,owned_exited=True,
                    outputs=[bound(p) for p in out.rglob('*') if p.is_file()]+[bound(log)]))
                print(name,'all 31 native fields 0 ULP',flush=True)
        result['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
