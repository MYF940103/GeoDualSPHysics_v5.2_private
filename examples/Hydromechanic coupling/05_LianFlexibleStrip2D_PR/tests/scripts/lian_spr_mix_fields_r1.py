"""Check per-face constant/affine velocity reconstruction and S/P/R consumers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from lian_release_r1 import TESTS, REPO, bound, utc, write_json


def run(command,log):
    with log.open('xb') as f:
        p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=180,
            cwd=Path(command[0]).parent,creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode==0,(p.returncode,str(log))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--backend',choices=['cpu','gpu'],required=True)
    ap.add_argument('--configuration',choices=['Debug','Release'],required=True)
    ap.add_argument('--memcheck',type=Path)
    args=ap.parse_args()
    assert args.backend=='gpu' or args.configuration=='Debug'
    tag='lian_spr_mix_fields_r1_'+args.backend+'_'+args.configuration.lower()
    receipt=TESTS/'logs'/(tag+'.check.json'); assert not receipt.exists()
    prep=TESTS/'logs/lian_spr_mix_r1.prepare.json'; s=json.loads(prep.read_text())
    buildpath=TESTS/'logs'/('lian_spr_mix_cpu_r1dbg.build.json' if args.backend=='cpu' else
        'lian_spr_mix_gpu_'+args.configuration+'_r1.build.json')
    build=json.loads(buildpath.read_text(encoding='utf-8-sig'))
    exe=TESTS/'outputs'/('lian_spr_mix_cpu_r1dbg/lian_spr_mix_cpu.exe' if args.backend=='cpu' else
        'lian_spr_mix_gpu_'+args.configuration+'_r1/lian_spr_mix_gpu.exe')
    expected=build['exe_sha256'] if args.backend=='cpu' else build['executable_sha256']
    assert bound(exe)['sha256'].lower()==expected.lower()
    result=dict(passed=False,utc=utc(),inputs=[bound(__file__),bound(prep),bound(buildpath),bound(exe)],runs=[])
    try:
        for v in s['manufactured']:
            definition=Path(v['definition']['path'])
            assert bound(definition)['sha256']==v['definition']['sha256']
            folder=TESTS/'outputs'/(v['name']+'_input');prefix=folder/v['name']
            if not folder.exists():
                run([str(REPO/'bin/windows/GenCase_win64.exe'),str(definition.with_suffix('')),str(prefix),'-save:all'],
                    TESTS/'logs'/(v['name']+'.gencase.log'))
            output=TESTS/'outputs'/(tag+'_'+v['name'].replace('lian_spr_mix_r1_',''))
            assert not output.exists()
            command=[str(exe),'-cpu' if args.backend=='cpu' else '-gpu','-stable']
            if args.backend=='cpu':command+=['-ompthreads:1']
            command += [str(prefix),str(output),'-dirdataout','data','-sv:none']
            memory=args.memcheck is not None and 'edge3_swap' in v['name']
            if memory:command=[str(args.memcheck),'--tool','memcheck','--error-exitcode','99']+command
            log=TESTS/'logs'/(output.name+'.log')
            run(command,log)
            record=json.loads((output/'planes_complete.json').read_text())
            result['runs'].append(dict(name=v['name'],command=command,owned_exited=True,exit_code=0,metrics=record,
                inputs=[bound(p) for p in folder.iterdir() if p.is_file()],
                outputs=[bound(p) for p in output.rglob('*') if p.is_file()]+[bound(log)],memcheck=memory))
            assert record['passed'] and record['active_wall_count']==record['wall_count'],record
            if memory:assert 'ERROR SUMMARY: 0 errors' in log.read_text(errors='replace')
            print(output.name,'PASS',record['max_affine_error'],record['consumer_max'],flush=True)
        result['passed']=True
    finally:
        write_json(receipt,result)


if __name__=='__main__':main()
