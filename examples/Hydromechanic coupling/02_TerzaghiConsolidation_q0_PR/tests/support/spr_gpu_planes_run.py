"""Fresh GPU manufactured tests on the already verified CPU GenCase point sets."""
from pathlib import Path
import argparse
import json
import subprocess
from spr_planes_run import TESTS,REPO,bound


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',required=True);parser.add_argument('--tag',required=True);args=parser.parse_args()
    buildpath=Path(args.build);build=json.loads(buildpath.read_text(encoding='utf-8-sig'));assert build['built'] and build['fixture']=='spr_gpu_planes'
    assert args.tag.replace('_','').isalnum();receipt=TESTS/'logs'/(args.tag+'.check.json');assert not receipt.exists()
    exe=Path(build['executable']);assert bound(exe)['sha256']==build['executable_sha256']
    inputs=[bound(__file__),bound(buildpath),bound(exe)]+build['inputs']+build['runtime'];variants=[]
    for geometry in ('corner2','wedge2','edge3'):
        cpu='spr_planes_r4_rel' if geometry=='wedge2' else 'spr_planes_r3_rel'
        for mode in (1,2,3):
            oldname=cpu+'_'+geometry+'_s'+str(mode);folder=TESTS/'outputs'/(oldname+'_input')
            inputs += [bound(p) for p in folder.iterdir() if p.is_file()]
            variants.append((geometry,mode,folder/oldname))
    for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
    result=dict(passed=False,inputs=inputs,runs=[])
    try:
        for geometry,mode,prefix in variants:
            name=args.tag+'_'+geometry+'_s'+str(mode);out=TESTS/'outputs'/name;assert not out.exists();log=TESTS/'logs'/(name+'.log')
            command=[str(exe),'-gpu','-stable',str(prefix),str(out),'-dirdataout','data','-sv:none']
            with log.open('xb') as stream:
                child=subprocess.run(command,cwd=exe.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
            assert child.returncode==0,(name,'runtime failure')
            metrics=json.loads((out/'planes_complete.json').read_text())
            result['runs'].append(dict(geometry=geometry,slip=mode,command=command,exit_code=child.returncode,owned_exited=True,metrics=metrics,
                outputs=[bound(p) for p in out.rglob('*') if p.is_file()]+[bound(log)]))
            assert metrics['passed'] and metrics['active_wall_count']==metrics['wall_count'],(name,metrics)
            print(name,'PASS',metrics['max_affine_error'],metrics['consumer_max'],flush=True)
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        result['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
