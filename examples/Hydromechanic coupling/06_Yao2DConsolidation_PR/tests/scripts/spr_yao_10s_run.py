"""Fresh, sequential 10-s GPU SPR off/on/half delivery with gates between runs."""
import argparse
from decimal import Decimal
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from spr_yao_short import TESTS,CASE,REPO,render,bound
from spr_yao_1s_run import batch,utc

TAG='spr_yao_10s_r1'
RUNS=[('off','faces_off','.00002'),('on','faces_on','.00002'),('half','faces_half','.00001')]
BINARY='spr_yao_gpu_step_Release_op2/spr_yao_gpu_step.exe'


def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--prepare',action='store_true');g.add_argument('--run',action='store_true');a=p.parse_args()
    state=TESTS/'logs'/(TAG+'.status.json');assert not state.exists()
    prereq=[TESTS/'logs/spr_yao_cpu_gpu_1s_r1.visual.json',TESTS/'logs/spr_yao_axis01_r1.visual.json']
    assert all(json.loads(p.read_text())['passed'] for p in prereq)
    if a.prepare:
        for key,variant,dt in RUNS:
            name=TAG+'_'+key;root=ET.fromstring(render(variant));params=root.find('execution/parameters')
            for keyparam,value in [('TimeMax','10'),('TimeOut','.01')]:
                node=params.find("parameter[@key='"+keyparam+"']");node.set('value',value);node.set('comment','Bounded 10-s GPU SPR comparison; native integer-step .01-s saves')
            ET.indent(root,space='    ')
            with (TESTS/'configs'/(name+'_Def.xml')).open('x',encoding='utf8') as f:f.write('<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='unicode')+'\n')
            text=batch(name,'GPU',BINARY,int(Decimal('10')/Decimal(dt)),int(Decimal('.01')/Decimal(dt))).replace('Bounded 1-s','Bounded 10-s')
            with (TESTS/'configs'/('x'+name+'_win64_GPU.bat')).open('x',encoding='utf8') as f:f.write(text)
        print('Prepared three 10-s XML/BAT pairs, no solver started');return
    exe=TESTS/'outputs'/BINARY;build=TESTS/'logs/spr_yao_gpu_step_Release_op2.build.json';b=json.loads(build.read_text(encoding='utf-8-sig'))
    assert bound(exe)['sha256']==b['executable_sha256'] and shutil.disk_usage(TESTS).free>25*1024**3
    inputs=[bound(__file__),bound(TESTS/'scripts/spr_yao_10s_check.py'),bound(TESTS/'scripts/spr_yao_1s_run.py'),bound(TESTS/'scripts/spr_yao_short.py'),
        bound(TESTS/'scripts/spr_yao_review.py'),bound(TESTS/'scripts/spr_yao_step_review.py'),bound(TESTS/'notes/spr_yao_10s_r1.md'),
        bound(exe),bound(build),bound(REPO/'bin/windows/GenCase_win64.exe'),bound(CASE/'CaseYao2DConsolidation_PR_Def.xml'),
        bound(TESTS/'outputs/read_native_spr_r1/ReadHydroMechPart.exe'),bound(TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe')]+[bound(p) for p in prereq]
    inputs += [bound(p) for p in exe.parent.glob('*.dll')]
    inputs += [bound(REPO/'src/source'/f) for f in ('JSphCpu.cpp','JSphCpu.h','JSphCpuSingle.cpp','JSphGpu.cpp','JSphGpu.h','JSphGpuSingle.cpp','JSphGpu_ker.cu','JSphGpu_ker.h')]
    for key,variant,dt in RUNS:
        name=TAG+'_'+key;assert not (TESTS/'outputs'/name).exists() and not (TESTS/'outputs'/(name+'_input')).exists()
        inputs += [bound(TESTS/'configs'/(name+'_Def.xml')),bound(TESTS/'configs'/('x'+name+'_win64_GPU.bat'))]
    r=dict(tag=TAG,status='running',duration_s='10',cadence_s='.01',owned_sequence_pid=os.getpid(),started_utc=utc(),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),inputs=inputs,runs=[],checks={})
    def save():
        tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf8');os.replace(tmp,state)
    def check(args,label):
        r['stage']='checking_'+label;save();log=TESTS/'logs'/(TAG+'_'+label+'.check.log')
        with log.open('xb') as f:child=subprocess.run([sys.executable,'-B','-u',str(TESTS/'scripts/spr_yao_10s_check.py')]+args,cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert child.returncode==0,(label,'Native review failed',str(log))
        path=TESTS/'logs'/(TAG+'_'+label+'.check.json');assert json.loads(path.read_text())['passed'];r['checks'][label]=bound(path);save()
    save()
    try:
        for key,variant,dt in RUNS:
            name=TAG+'_'+key;r['stage']='running_'+key;save();log=TESTS/'logs'/(name+'.log')
            with log.open('xb') as f:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64_GPU.bat'))],cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                r['owned_wrapper_pid']=child.pid;save();code=child.wait()
            assert code==0,(key,'Solver/BAT failed',str(log))
            folder=TESTS/'outputs'/name;done=json.loads((folder/'step_complete.json').read_text());assert done['completed']
            entry=dict(key=key,exit_code=code,owned_exited=True,completion=done,log=bound(log),outputs=[bound(p) for base in (folder,TESTS/'outputs'/(name+'_input')) for p in base.rglob('*') if p.is_file()])
            r['runs'].append(entry);save()
            with (TESTS/'logs'/(name+'.run.json')).open('x',encoding='utf8') as f:json.dump(dict(inputs=inputs,run=entry),f,indent=2)
            check(['--single',key],key)
        check(['--pair'],'pair');check(['--final'],'final')
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        r.update(status='completed_pending_review',stage='all_gates_passed_pending_visual_physical_review',finished_utc=utc())
    except Exception as error:r.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc());raise
    finally:save()


if __name__=='__main__':main()
