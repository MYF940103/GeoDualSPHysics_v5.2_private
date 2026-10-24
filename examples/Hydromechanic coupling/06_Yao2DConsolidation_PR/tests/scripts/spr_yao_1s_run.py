"""Fresh CPU coarse, then GPU coarse/half, with original gates between stages."""
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from spr_yao_short import TESTS,CASE,REPO,render,bound

TAG='spr_yao_cpu_gpu_1s_r1'
RUNS=[('cpu_c','faces_on','CPU','spr_yao_step_r2rel/spr_yao_step.exe','.00002','spr_yao_step_r2rel.build.json'),
      ('gpu_c','faces_on','GPU','spr_yao_gpu_step_Release_op2/spr_yao_gpu_step.exe','.00002','spr_yao_gpu_step_Release_op2.build.json'),
      ('gpu_h','faces_half','GPU','spr_yao_gpu_step_Release_op2/spr_yao_gpu_step.exe','.00001','spr_yao_gpu_step_Release_op2.build.json')]


def utc():return datetime.now(timezone.utc).isoformat()


def batch(name,backend,binary,steps,stride):
    return '\n'.join(['@echo off','setlocal EnableDelayedExpansion','pushd "%~dp0\\..\\.."','',
      'rem Bounded 1-s production-step companion, not formal 2D consolidation acceptance.',
      'rem Native BI4; single-run and pair reviews are separate. Existing outputs are protected.',
      'set name='+name,'set dirout=tests\\outputs\\%name%','set diroutdata=%dirout%\\data',
      'set dirbin=../../../bin/windows','set gencase="%dirbin%/GenCase_win64.exe"',
      'set stepcheck="tests/outputs/'+binary+'"','set dirinput=tests\\outputs\\%name%_input',
      'if exist %dirout% goto fail','if exist %dirinput% goto fail',
      '%gencase% tests/configs/%name%_Def %dirinput%/%name% -save:all','if not "%ERRORLEVEL%"=="0" goto fail',
      '%stepcheck% '+str(steps)+' '+str(stride)+(' -cpu -ompthreads:8 ' if backend=='CPU' else ' -gpu -stable ')+'%dirinput%/%name% %dirout% -dirdataout data -svres -svextraparts:1',
      'if not "%ERRORLEVEL%"=="0" goto fail','popd','exit /b 0',':fail',
      'echo Diagnostic refused or failed. Retained outputs were not deleted.','popd','exit /b 1',''])


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true');args=parser.parse_args()
    state=TESTS/'logs'/(TAG+'.status.json');assert not state.exists()
    prerequisites=[TESTS/'logs'/('spr_yao_gpu_post03_r1'+x) for x in ('.audit_r1.json','.visual.json')]
    assert all(json.loads(p.read_text())['passed'] for p in prerequisites)
    if args.prepare:
        for key,variant,backend,binary,dt,build in RUNS:
            name=TAG+'_'+key;root=ET.fromstring(render(variant));params=root.find('execution/parameters')
            for param,value in [('TimeMax','1'),('TimeOut','.001')]:params.find("parameter[@key='"+param+"']").set('value',value)
            params.find("parameter[@key='TimeMax']").set('comment','Bounded 1-s CPU/GPU comparison; not formal 2D validation')
            params.find("parameter[@key='TimeOut']").set('comment','Companion saves at actual integer-step 1-ms intervals')
            for node in root.iter():
                if 'comment' in node.attrib:node.set('comment',node.get('comment').replace('Independent CPU SPR','Independent '+backend+' SPR'))
            ET.indent(root,space='    ');steps=int(Decimal(1)/Decimal(dt));stride=int(Decimal('.001')/Decimal(dt))
            definition=TESTS/'configs'/(name+'_Def.xml');bat=TESTS/'configs'/('x'+name+'_win64_'+backend+'.bat')
            with definition.open('x',encoding='utf8') as stream:stream.write('<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='unicode')+'\n')
            with bat.open('x',encoding='utf8') as stream:stream.write(batch(name,backend,binary,steps,stride))
        print('Prepared three 1-s XML/BAT pairs; no solver started');return
    inputs=[bound(__file__),bound(TESTS/'scripts/spr_yao_1s_check.py'),bound(TESTS/'scripts/spr_yao_short.py'),bound(TESTS/'scripts/spr_yao_review.py'),
        bound(TESTS/'scripts/spr_yao_step_review.py'),bound(TESTS/'outputs/read_native_spr_r1/ReadHydroMechPart.exe'),bound(TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe'),
        bound(CASE/'CaseYao2DConsolidation_PR_Def.xml'),bound(REPO/'bin/windows/GenCase_win64.exe')]+[bound(p) for p in prerequisites]
    inputs += [bound(REPO/'src/source'/x) for x in ('JSphCpu.cpp','JSphCpu.h','JSphCpuSingle.cpp','JSphGpu.cpp','JSphGpu.h','JSphGpuSingle.cpp','JSphGpu_ker.cu','JSphGpu_ker.h')]
    for key,variant,backend,binary,dt,build in RUNS:
        name=TAG+'_'+key;exe=TESTS/'outputs'/binary;manifest=TESTS/'logs'/build;b=json.loads(manifest.read_text(encoding='utf-8-sig'))
        assert bound(exe)['sha256']==(b['exe_sha256'] if backend=='CPU' else b['executable_sha256'])
        assert not (TESTS/'outputs'/name).exists() and not (TESTS/'outputs'/(name+'_input')).exists()
        inputs += [bound(exe),bound(manifest),bound(TESTS/'configs'/(name+'_Def.xml')),bound(TESTS/'configs'/('x'+name+'_win64_'+backend+'.bat'))]
        inputs += [bound(p) for p in exe.parent.glob('*.dll')]
    record=dict(status='running',tag=TAG,duration_s='1',owned_sequence_pid=os.getpid(),started_utc=utc(),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),inputs=inputs,runs=[],checks={})
    def save():
        temporary=state.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2),encoding='utf8');os.replace(temporary,state)
    def check(arguments,label):
        record['stage']='checking_'+label;save();log=TESTS/'logs'/(TAG+'_'+label+'.check.log')
        with log.open('xb') as stream:
            child=subprocess.run([sys.executable,'-B','-u',str(TESTS/'scripts/spr_yao_1s_check.py')]+arguments,cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert child.returncode==0,(label,'Native/pair review failed; see',str(log))
        receipt=TESTS/'logs'/(TAG+'_'+label+'.check.json');assert json.loads(receipt.read_text())['passed']
        record['checks'][label]=bound(receipt);save()
    save()
    try:
        for key,variant,backend,binary,dt,build in RUNS:
            name=TAG+'_'+key;record['stage']='running_'+key;save();log=TESTS/'logs'/(name+'.log')
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64_'+backend+'.bat'))],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;save();code=child.wait()
            assert code==0,(key,'Solver/BAT failed',str(log))
            folder=TESTS/'outputs'/name;done=json.loads((folder/'step_complete.json').read_text());assert done['completed']
            item=dict(key=key,exit_code=code,owned_exited=True,completion=done,log=bound(log),outputs=[bound(p) for base in (folder,TESTS/'outputs'/(name+'_input')) for p in base.rglob('*') if p.is_file()])
            record['runs'].append(item);save()
            frozen=TESTS/'logs'/(name+'.run.json')
            with frozen.open('x',encoding='utf8') as stream:json.dump(dict(inputs=inputs,run=item),stream,indent=2)
            check(['--run',key],key)
            if key=='gpu_c':check(['--pair','cross'],'cross')
            if key=='gpu_h':check(['--pair','half'],'half')
        check(['--final'],'final')
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        record.update(status='completed_pending_review',stage='all_gates_passed_pending_visual_physical_review',finished_utc=utc())
    except Exception as error:record.update(status='rejected_or_interrupted',error=repr(error),finished_utc=utc());raise
    finally:save()


if __name__=='__main__':main()
