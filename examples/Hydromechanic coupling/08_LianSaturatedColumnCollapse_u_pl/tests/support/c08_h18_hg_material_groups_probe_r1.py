"""Separately authorized CPU-only build OR material probe; no automatic chained phase."""
import argparse
import os
import re
import subprocess
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T,L=m.T,m.L;S=T.parents[3]/'src';TAG='c08_h18_hg_material_groups_probe_r1'
CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md');OUT=T/'outputs'/(TAG+'_build')
RESULT=T/'outputs'/TAG;BUILD=L/(TAG+'.build.json');CHECK=L/(TAG+'.check.json')
RECIPE=L/'upl_material_unified_r1.build.call.json'
OLD_CPP=T/'support/upl_material_unified_probe_r1.cpp'
HEADERS=('FunSoilMaterial.h','DualSphDef.h','TypesDef.h')


def environment(record):
    intdir=Path(os.environ['TEMP'])/TAG
    m.need(' ' not in str(intdir) and not intdir.exists(),'Fresh no-space TEMP directory required; old setup evidence protected');intdir.mkdir()
    cmd=intdir/'env.cmd'
    with cmd.open('xb') as f:f.write(('@echo off\r\ncall "D:\\Program Files\\VS2022\\VC\\Auxiliary\\Build\\vcvarsall.bat" x64 10.0.22000.0 -vcvars_ver=14.36 >nul\r\nif errorlevel 1 exit /b %errorlevel%\r\nset\r\n').encode('ascii'))
    q=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/cmd.exe'),'/d','/c',str(cmd)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    record.update(environment_cmd=m.stat(cmd),actual_Popen_wait_exit=q.returncode)
    m.need(q.returncode==0,'Original MSVC environment setup failed')
    env={k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in (line.split('=',1) for line in q.stdout.decode('mbcs').splitlines() if '=' in line and not line.startswith('=')))
    m.need(env['VCTOOLSVERSION']=='14.36.32532' and env['WINDOWSSDKVERSION'].rstrip('\\/')=='10.0.22000.0','Authoritative MSVC14.36/SDK22000 recipe required');env.pop('CL',None);env.pop('_CL_',None);return env


def quoted_closure(first):
    todo=list(first);seen={}
    while todo:
        path=todo.pop().resolve()
        if path in seen:continue
        raw=path.read_bytes();seen[path]=raw
        for name in re.findall(rb'^\s*#\s*include\s*"([^"\r\n]+)"',raw,re.M):
            child=S/'source'/name.decode('ascii');m.need(child.is_file(),'Unresolved local material include: '+str(child));todo.append(child)
    return seen


def build():
    m.need(not BUILD.exists() and not OUT.exists(),'Existing build or partial assets protected');calls=[];before=[];setup_result={}
    try:
        recipe=m.read(RECIPE);m.need(recipe['actual_wait_exit']==recipe['actual_Win32_exit']==0,'Successful original standalone CPU compiler recipe required')
        compiler=Path(m.bind(recipe['program'])['path']);args=list(recipe['argv'][1:]);old=T/'outputs/upl_material_unified_CPU_r1'
        m.need(recipe['argv'][0]==str(compiler) and args.count(str(OLD_CPP))==1 and all(q in args for q in ('/MTd','/Od','/fp:precise','/std:c++17')),'Original precise CPU recipe changed')
        closure=quoted_closure([S/'source'/q for q in HEADERS]);before=[m.stat(p) for p in (Path(__file__),CPP,NOTE,RECIPE,OLD_CPP,Path(m.__file__),Path(m.invoke.__code__.co_filename),Path(m.verify.__code__.co_filename))]+[m.stat(p) for p in closure]+[m.stat(compiler)]
        m.verify(before);OUT.mkdir();frozen=OUT/'frozen';frozen.mkdir()
        for path,raw in closure.items():
            target=frozen/path.name
            with target.open('xb') as f:f.write(raw)
            m.need(target.read_bytes()==raw,'Frozen material header copy differs')
        argv=[]
        for value in args:
            if value==str(OLD_CPP):value=str(CPP)
            elif value=='/I'+str(S/'source'):value='/I'+str(frozen)
            else:value=value.replace(str(old),str(OUT))
            argv.append(value)
        exe=OUT/'upl_material_unified_r1.exe';dep=OUT/'dependencies.json'
        argv[argv.index('/link'):argv.index('/link')]=['/sourceDependencies',str(dep)]
        m.need(sum(q==str(CPP) for q in argv)==1 and '/I'+str(frozen) in argv and not any(not q.startswith('/') and q.lower().endswith(('.obj','.lib')) for q in argv),'Only one standalone source and no prebuilt objects/libraries allowed')
        env=environment(setup_result);before.append(m.bind(setup_result['environment_cmd']))
        calls.append(m.invoke(TAG+'.compile',[str(compiler),*argv],S,env))
        d=m.read(dep)['Data'];includes={Path(p).resolve() for p in d['Includes']}
        m.need(Path(d['Source']).resolve()==CPP.resolve() and all((frozen/q).resolve() in includes for q in HEADERS),'Actual compile did not consume frozen production material header')
        local={p.name.lower() for p in closure};m.need(all(p.parent==frozen.resolve() for p in includes if p.name.lower() in local),'Material include escaped its frozen closure')
        m.verify(before);m.save(BUILD,dict(stage=TAG+'.build',passed=True,configuration='DebugCPU',program=m.stat(exe),source=m.stat(CPP),note=m.stat(NOTE),recipe=m.stat(RECIPE),environment_setup=setup_result,dependencies=m.stat(dep),frozen_headers=[m.stat(frozen/p.name) for p in closure],source_headers=[m.stat(p) for p in closure],calls=calls,compile_link_invocations=1,engine_objects=0,project_libraries=0,material_probe_invocations=0,solver_invocations=0,GPU_actions=0,HGproducer_calls=0,SHA_scans=0,automatic_run=False,consumed=before,consumed_stats_unchanged=True,physical_acceptance=False))
    except Exception as error:
        if not BUILD.exists():m.save(BUILD,dict(stage=TAG+'.build',passed=False,first_failure=str(error),environment_setup=setup_result,calls=calls,consumed=before,partial_outputs_preserved=True,material_probe_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0))
        raise


def run():
    m.need(not CHECK.exists() and not RESULT.exists(),'Existing complete/partial material probe protected');before=[];call=None
    try:
        b=m.read(BUILD);m.need(b['passed'] and b['engine_objects']==b['project_libraries']==b['material_probe_invocations']==0 and b['consumed_stats_unchanged'] and b['automatic_run'] is False,'One passed separately admitted build required')
        before=[m.stat(p) for p in (Path(__file__),NOTE,BUILD)]+[m.bind(q) for q in b['consumed']]+[m.bind(q) for q in b['frozen_headers']]+[m.bind(b['program'])]
        m.verify(before);call=m.invoke(TAG+'.run',[b['program']['path'],'--out',str(RESULT)],S)
        completion=m.read(RESULT/'completion.json')
        m.need(completion['passed'] and completion['stage']==TAG and completion['points']==21 and completion['groups']==3 and completion['trigger_values_per_group']==2 and completion['EvaluateMaterial_calls']==21 and completion['invalid_ReturnMaterial_calls']==3 and completion['trigger_ON_smooth_points']==3,'Closed genuine21-point completion required')
        m.need(completion['original_tolerances_unchanged'] and completion['independent_manufactured_oracle'] and completion['GPU_calls']==completion['HGproducer_calls']==completion['spatial_solver_calls']==0,'CPU-only independent oracle scope changed');m.verify(before)
        m.save(CHECK,dict(stage=TAG,passed=True,build=m.stat(BUILD),actual_call=call,completion=completion,outputs=[m.stat(RESULT/q) for q in ('points.csv','completion.json')],material_probe_invocations=1,solver_invocations=0,native_reader_invocations=0,GPU_actions=0,HGproducer_calls=0,SHA_scans=0,automatic_next_job=False,consumed=before,consumed_stats_unchanged=True,physical_acceptance=False))
    except Exception as error:
        if not CHECK.exists():m.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(error),actual_call=call,consumed=before,partial_outputs_preserved=True,solver_invocations=0,GPU_actions=0,SHA_scans=0))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('build','run'));p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();m.need(a.execution_authorized,'Each build/run needs separate root authorization')
    (build if a.phase=='build' else run)()


if __name__=='__main__':main()
