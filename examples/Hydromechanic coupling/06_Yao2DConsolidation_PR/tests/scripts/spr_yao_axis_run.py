"""Fresh .1-s axis-NoPen CPU/GPU gates. No continuation of older solvers."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from spr_yao_short import TESTS,CASE,REPO,bound
from spr_yao_1s_run import batch,utc

TAG='spr_yao_axis01_r1'
RUNS=[('cpu_c','CPU','.00002'),('gpu_c','GPU','.00002'),('gpu_h','GPU','.00001')]


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true');args=parser.parse_args()
    state=TESTS/'logs'/(TAG+'.status.json');assert not state.exists()
    prereq=TESTS/'logs/spr_yao_cpu_gpu_1s_r1.visual.json';assert json.loads(prereq.read_text())['passed']
    if args.prepare:
        for key,backend,dt in RUNS:
            name=TAG+'_'+key
            root=ET.parse(TESTS/'configs'/('spr_yao_cpu_gpu_1s_r1_'+key+'_Def.xml')).getroot();params=root.find('execution/parameters')
            for param,value in [('NoPenetration','1'),('TimeMax','.1')]:
                p=params.find("parameter[@key='"+param+"']");p.set('value',value);p.set('comment','Independent axis-NoPen plus SPR startup diagnostic')
            ET.indent(root,space='    ')
            definition=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64_'+backend+'.bat')
            with definition.open('x',encoding='utf8') as f:f.write('<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='unicode')+'\n')
            binary='spr_yao_axis_'+backend+'_r1/axis_step.exe'
            text=batch(name,backend,binary,int(Decimal('.1')/Decimal(dt)),int(Decimal('.001')/Decimal(dt)))
            text=text.replace('Bounded 1-s','Bounded .1-s axis-NoPen')
            with bat.open('x',encoding='utf8') as f:f.write(text)
        print('Prepared three fresh .1-s XML/BAT pairs; no solver started');return
    inputs=[bound(__file__),bound(TESTS/'scripts/spr_yao_axis_check.py'),bound(TESTS/'scripts/spr_yao_1s_run.py'),
        bound(TESTS/'scripts/spr_yao_short.py'),bound(TESTS/'scripts/spr_yao_review.py'),bound(prereq),
        bound(TESTS/'outputs/read_native_spr_r1/ReadHydroMechPart.exe'),bound(TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe'),
        bound(REPO/'bin/windows/GenCase_win64.exe'),bound(TESTS/'scripts/spr_yao_axis_step.cpp'),bound(TESTS/'notes/spr_yao_axis_r1.md')]
    inputs += [bound(REPO/'src/source'/x) for x in ('JSphCpu.cpp','JSphCpu.h','JSphCpuSingle.cpp','JSphGpu.cpp','JSphGpu.h','JSphGpuSingle.cpp','JSphGpu_ker.cu','JSphGpu_ker.h')]
    for key,backend,dt in RUNS:
        name=TAG+'_'+key;binary=TESTS/'outputs'/('spr_yao_axis_'+backend+'_r1/axis_step.exe')
        build=TESTS/'logs'/('spr_yao_axis_'+backend+'_r1.build.json');b=json.loads(build.read_text(encoding='utf-8-sig'))
        assert b['built'] and bound(binary)['sha256']==b['executable_sha256']
        assert not (TESTS/'outputs'/name).exists() and not (TESTS/'outputs'/(name+'_input')).exists()
        inputs += [bound(binary),bound(build),bound(TESTS/'configs'/(name+'_Def.xml')),bound(TESTS/'configs'/('x'+name+'_win64_'+backend+'.bat'))]
        inputs += [bound(p) for p in binary.parent.glob('*.dll')]
        inputs += [bound(TESTS/'logs'/('spr_yao_cpu_gpu_1s_r1_'+key+'.run.json'))]
    r=dict(tag=TAG,status='running',owned_sequence_pid=os.getpid(),started_utc=utc(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),inputs=inputs,runs=[],checks={})
    def save():
        tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf8');os.replace(tmp,state)
    def check(arguments,label):
        r['stage']='checking_'+label;save();log=TESTS/'logs'/(TAG+'_'+label+'.check.log')
        with log.open('xb') as f:child=subprocess.run([sys.executable,'-B','-u',str(TESTS/'scripts/spr_yao_axis_check.py')]+arguments,cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert child.returncode==0,(label,'Review failed',str(log))
        path=TESTS/'logs'/(TAG+'_'+label+'.check.json');assert json.loads(path.read_text())['passed'];r['checks'][label]=bound(path);save()
    save()
    try:
        for key,backend,dt in RUNS:
            name=TAG+'_'+key;r['stage']='running_'+key;save();log=TESTS/'logs'/(name+'.log')
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64_'+backend+'.bat'))],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                r['owned_wrapper_pid']=child.pid;save();code=child.wait()
            assert code==0,(key,'Solver/BAT failed',str(log))
            folder=TESTS/'outputs'/name;done=json.loads((folder/'step_complete.json').read_text());assert done['completed']
            entry=dict(key=key,exit_code=code,owned_exited=True,completion=done,log=bound(log),outputs=[bound(p) for base in (folder,TESTS/'outputs'/(name+'_input')) for p in base.rglob('*') if p.is_file()])
            r['runs'].append(entry);save()
            with (TESTS/'logs'/(name+'.run.json')).open('x',encoding='utf8') as f:json.dump(dict(inputs=inputs,run=entry),f,indent=2)
            check(['--single',key],key)
            if key=='gpu_c':check(['--pair','cross'],'cross')
            if key=='gpu_h':check(['--pair','half'],'half')
        check(['--final'],'final')
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        r.update(status='completed_pending_review',stage='all_gates_passed_pending_visual_physical_review',finished_utc=utc())
    except Exception as error:r.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc());raise
    finally:save()


if __name__=='__main__':main()
