"""Current real GPU rejects unsupported geometry; retained GenCase inputs only."""
import json
import subprocess
from spr_planes_run import TESTS,REPO,bound


def main():
    tag='spr_gpu_scope_r1';receipt=TESTS/'logs'/(tag+'.check.json');assert not receipt.exists()
    exe=REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe';inputs=[bound(__file__),bound(exe)];cases=[]
    for key in ('curve2','sphere3','translate2','rotate3'):
        name='spr_boundary_admission_r2_'+key+'_1'
        message='one coplanar, consistently oriented fixed wall per mk' if key in ('curve2','sphere3') else 'fresh fixed-wall elastic cases only'
        cases.append((key,TESTS/'outputs'/(name+'_input')/name,message))
    for mode in (2,3):
        name='spr_nopen_on_r1_2d_t_s'+str(mode)
        cases.append(('inclined_nopen_s'+str(mode),TESTS/'outputs'/(name+'_input')/name,'inclined NoPen is not rotation-consistent'))
    record=dict(passed=False,scope='Expected input rejections only; not boundary dynamics acceptance',inputs=inputs,runs=[])
    try:
        for key,prefix,message in cases:
            inputs += [bound(p) for p in prefix.parent.iterdir() if p.is_file()]
            out=TESTS/'outputs'/(tag+'_'+key);assert not out.exists();log=TESTS/'logs'/(tag+'_'+key+'.log')
            command=[str(exe),'-gpu','-stable',str(prefix),str(out),'-dirdataout','data','-sv:none']
            with log.open('xb') as stream:
                child=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
            text=log.read_text(errors='replace');assert child.returncode!=0 and message in text,(key,child.returncode,message)
            assert not list((out/'data').glob('Part_*.bi4')),'Unsupported case integrated before rejection'
            record['runs'].append(dict(case=key,expected_rejection=True,exit_code=child.returncode,owned_exited=True,log=bound(log)))
            print(key,'expected rejection confirmed',flush=True)
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        record['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2)


if __name__=='__main__':main()
