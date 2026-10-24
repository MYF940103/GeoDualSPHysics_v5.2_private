"""GPU Yao raw-program/pinned production-step short runs; no new integrator."""
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from spr_yao_short import TESTS,CASE,REPO,render,bound

VARIANTS=('faces_off','faces_on','faces_half')
EXE=TESTS/'outputs/spr_yao_gpu_step_Release_op1/spr_yao_gpu_step.exe'


def batch(name,steps,stride,raw=False):
    return '\n'.join(['@echo off','setlocal EnableDelayedExpansion','pushd "%~dp0\\..\\.."','',
      ('rem Real GPU program with ordinary save events.' if raw else 'rem Integer-save diagnostic: the companion calls the production Symplectic step.'),
      'rem Native BI4 only. Offline comparisons are separate; retained outputs are never deleted.',
      'set name='+name,'set dirout=tests\\outputs\\%name%','set diroutdata=%dirout%\\data',
      'set dirbin=../../../bin/windows','set gencase="%dirbin%/GenCase_win64.exe"',
      ('set stepcheck="%dirbin%/DualSPHysics5.2_GEO_win64.exe"' if raw else 'set stepcheck="tests/outputs/spr_yao_gpu_step_Release_op1/spr_yao_gpu_step.exe"'),
      'set dirinput=tests\\outputs\\%name%_input',
      'if exist %dirout% goto fail','if exist %dirinput% goto fail',
      '%gencase% tests/configs/%name%_Def %dirinput%/%name% -save:all',
      'if not "%ERRORLEVEL%"=="0" goto fail',
      '%stepcheck% '+('' if raw else str(steps)+' '+str(stride)+' ')+'-gpu -stable %dirinput%/%name% %dirout% -dirdataout data -svres -svextraparts:1',
      'if not "%ERRORLEVEL%"=="0" goto fail','popd','exit /b 0',':fail',
      'echo Diagnostic refused or failed. Retained outputs were not deleted.','popd','exit /b 1',''])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--duration',required=True)
    parser.add_argument('--raw',action='store_true');parser.add_argument('--prepare',action='store_true');parser.add_argument('--run',action='store_true');args=parser.parse_args()
    assert args.tag.replace('_','').isalnum() and Decimal(args.duration) in (Decimal('.02'),Decimal('.1'))
    if args.raw:assert Decimal(args.duration)==Decimal('.02')
    exe=REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe' if args.raw else EXE
    tag=args.tag;state=TESTS/'logs'/(tag+'.status.json');assert not state.exists()
    if args.prepare:
        for variant in VARIANTS:
            dt=Decimal('.00001') if variant=='faces_half' else Decimal('.00002')
            steps=Decimal(args.duration)/dt;stride=Decimal('.001')/dt;assert steps==int(steps) and stride==int(stride)
            name=tag+'_'+variant;root=ET.fromstring(render(variant))
            for node in root.iter():
                if 'comment' in node.attrib:node.set('comment',node.get('comment').replace('Independent CPU SPR','Independent GPU SPR'))
            params=root.find('execution/parameters')
            for key,value,comment in [('TimeMax',args.duration,'Bounded multi-plane SPR risk window; not formal validation'),('TimeOut','.001','Ordinary 1-ms save-event interval' if args.raw else 'Companion saves on the integer-step 1-ms grid')]:
                node=params.find("parameter[@key='"+key+"']");node.set('value',value);node.set('comment',comment)
            ET.indent(root,space='    ')
            for path,text in [(TESTS/'configs'/(name+'_Def.xml'),'<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='unicode')+'\n'),
                              (TESTS/'configs'/('x'+name+'_win64_CPU.bat'),batch(name,int(steps),int(stride),args.raw))]:
                with path.open('x',encoding='utf8') as stream:stream.write(text)
        print('Prepared three bounded XML/BAT pairs; no solver started');return
    assert args.run
    inputs=[bound(__file__),bound(TESTS/'scripts/spr_yao_short.py'),bound(TESTS/'scripts/spr_yao_gpu_step_test.cpp'),bound(exe),bound(TESTS/'logs/spr_yao_gpu_step_Release_op1.build.json')]
    inputs += [bound(REPO/'src/source'/x) for x in ('JSphGpu.cpp','JSphGpu.h','JSphGpuSingle.cpp','JSphGpu_ker.cu','JSphGpu_ker.h')]
    inputs += [bound(CASE/'CaseYao2DConsolidation_PR_Def.xml'),bound(REPO/'bin/windows/GenCase_win64.exe')]
    for variant in VARIANTS:
        name=tag+'_'+variant
        assert not (TESTS/'outputs'/name).exists() and not (TESTS/'outputs'/(name+'_input')).exists()
        inputs += [bound(TESTS/'configs'/(name+'_Def.xml')),bound(TESTS/'configs'/('x'+name+'_win64_CPU.bat'))]
    record=dict(status='running',raw_program=args.raw,tag=tag,duration_s=args.duration,inputs=inputs,runs=[],started_utc=datetime.now(timezone.utc).isoformat())
    def save():state.write_text(json.dumps(record,indent=2),encoding='utf8')
    save()
    try:
        for variant in VARIANTS:
            name=tag+'_'+variant;record['active_variant']=variant;save();log=TESTS/'logs'/(name+'.log')
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64_CPU.bat'))],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;save();code=child.wait()
            assert code==0,(name,'companion/BAT failure')
            out=TESTS/'outputs'/name
            if args.raw:
                assert 'Finished execution (code=0)' in log.read_text(errors='replace')
                count=len(list((out/'data').glob('Part_*.bi4')));assert count==21
                from spr_yao_review import native
                final=native(out,count-1);actual=float(final.time_s.iloc[0]);dt=1e-5 if variant=='faces_half' else 2e-5
                assert float(args.duration)<=actual+1e-11 and actual<=float(args.duration)+dt+1e-11
                done=dict(completed=True,raw_program=True,actual_time_s=actual,dt_s=dt,saved_frames=count,actual_steps=int(final.saved_step.iloc[0])+1,loop_seconds=None)
            else:
                done=json.loads((out/'step_complete.json').read_text());assert done['completed']
                assert abs(done['actual_time_s']-float(args.duration))<1e-10 and done['saved_frames']==round(float(args.duration)/.001)+1
            record['runs'].append(dict(variant=variant,exit_code=code,owned_exited=True,completion=done,log=bound(log),outputs=[bound(p) for base in (out,TESTS/'outputs'/(name+'_input')) for p in base.rglob('*') if p.is_file()]))
            save();print(name+' completed',flush=True)
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        record.update(status='completed_pending_review',finished_utc=datetime.now(timezone.utc).isoformat())
    except Exception as error:record.update(status='rejected_or_interrupted',error=repr(error));raise
    finally:save()


if __name__=='__main__':main()
