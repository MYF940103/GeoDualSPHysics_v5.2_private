"""Isolated authoritative builds only; no target-program execution or notification."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
C04 = TESTS.parent.parent/'04_CryerProblem_PR/tests'
sys.path.insert(0,str(C04/'support'))
import cryer_darcy_switch_build_r1 as recipe

TAG = 'sw_pore_cell_build_r1'
LOGS, ROOT = TESTS/'logs', TESTS/'outputs'/TAG
TEMP = Path(r'C:\Users\syosh\AppData\Local\Temp')/TAG
NOTE, BASE = TESTS/'notes'/(TAG+'.json'), LOGS/'sw_pore_cell_base_r1.json'
PREP, START, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json','.started.json','.check.json']]
CPU = C04/'logs/cryer_darcy_switch_build_r1_ReleaseCPU.build.json'
OLDPREP = C04/'logs/cryer_darcy_switch_build_r1.inputs.json'
UNIT = LOGS/'sw_cte_host_r1.check.json'
SOURCES = [REPO/'src/source'/n for n in ['JSph.h','JSph.cpp','JSphCpu.cpp','JSphGpu_ker.h','JSphGpu_ker.cu','JSphGpu.cpp']]
GUIDE = REPO/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml'
CANONICAL = [REPO/'bin/windows'/n for n in ['DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2_GEO_win64.exe']]
CONFIGS = [('DebugCPU',0,'DualSPHysics5.2CPU_win64_debug.exe'),('Debug',1,'DualSPHysics5.2_win64_debug.exe'),('Release',1,'DualSPHysics5.2_GEO_win64.exe')]


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def utc(): return datetime.now(timezone.utc).isoformat()
def bound(path):
    path=Path(path).resolve()
    with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path),bytes=path.stat().st_size,sha256=digest)
def verify(records):
    for item in records:
        actual=bound(item['path'])
        assert actual['bytes']==item['bytes'] and actual['sha256'].lower()==item['sha256'].lower(),('Changed bound input',item['path'])
def seal(path,value):
    with Path(path).open('x',encoding='utf8') as stream: json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def unique(records):
    result={}
    for item in records:
        key=str(Path(item['path']).resolve()).casefold()
        if key in result: assert result[key]['bytes']==item['bytes'] and result[key]['sha256'].lower()==item['sha256'].lower(),item['path']
        result[key]=item
    return list(result.values())


def command(config,index):
    replacements={'/p:OutDir=':(ROOT/config/'out').as_posix()+'/',
                  '/p:IntDir=':(TEMP/config/'int').as_posix()+'/',
                  '/bl:':str(LOGS/(TAG+'_'+config+'.binlog'))}
    return [next((prefix+value for prefix,value in replacements.items() if arg.startswith(prefix)),arg) for arg in recipe.command(config,index)]


def patch_identity():
    base=read(BASE);source=Path(base['source']);snapshot=Path(base['snapshot'])
    assert source.resolve()==SOURCES[4].resolve()
    record=dict(path=str(snapshot.resolve()),bytes=base['bytes'],sha256=base['sha256']);verify([record])
    before=snapshot.read_bytes();after=source.read_bytes()
    old=b'Double3(mapposmin),CTE.poscellsize,dvd.scelldiv'
    new=b'Double3(mapposmin),dvd.poscellsize,dvd.scelldiv'
    assert before.count(old)==1 and after==before.replace(old,new), 'Only the reviewed host launch argument may change'
    return record


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    assert ' ' not in str(TEMP) and [c[0] for c in CONFIGS]==['DebugCPU','Debug','Release']
    for config,index,name in CONFIGS:
        before,after=recipe.command(config,index),command(config,index)
        changes=[a for a,b in zip(before,after) if a!=b]
        assert len(changes)==3 and all(a.startswith(('/p:OutDir=','/p:IntDir=','/bl:')) for a in changes)
        assert '/m:1' in after and '/nr:false' in after and '/t:Build' in after
        assert '/p:BuildProjectReferences=false' in after and '/p:PostBuildEventUseInBuild=false' in after
        assert (ROOT/config/'out'/name).is_relative_to(ROOT)
    print('SELFTEST PASSED; no prepare/build/program/queue')


def prepare():
    selftest()
    assert not any(p.exists() for p in [PREP,START,CHECK,ROOT,TEMP]) and not list(LOGS.glob(TAG+'*')), 'Fresh stage only'
    snapshot=patch_identity();unit=read(UNIT);cpu=read(CPU);oldprep=read(OLDPREP)
    assert unit['build_exit']==0 and unit['run_exit']==0
    assert cpu['configuration']=='ReleaseCPU' and cpu['exit_code']==0 and cpu['owned_exited'] and cpu['protected_inputs_unchanged']
    assert cpu['status']=='built_not_run' and len(cpu['runtime'])==4
    cpu_sources=[next(r for r in oldprep['inputs'] if Path(r['path']).resolve()==p.resolve()) for p in SOURCES[:3]]
    verify(cpu_sources)  # CPU code is unchanged; do not follow the old current-GPU-source hash.
    records=[bound(p) for p in SOURCES+[GUIDE,NOTE,BASE,UNIT,CPU,OLDPREP,Path(__file__),Path(recipe.__file__)]+recipe.SOLUTIONS+recipe.PROJECTS+recipe.TOOLS+recipe.RUNTIME+CANONICAL]
    records += [snapshot,cpu['program'],cpu['log']]+cpu['artifacts']+cpu_sources
    records += [x[k] for x in cpu['runtime'] for k in ['source','target']]
    records += [unit['source'],unit['recipe'],unit['compiler']]+unit['artifacts']
    runlog=next(Path(r['path']) for r in unit['artifacts'] if Path(r['path']).name=='sw_cte_host_r1.run.log')
    raw=runlog.read_bytes()
    values=[float(v) for v in raw.decode('utf16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig').splitlines()[-1].split(',')]
    assert len(values)==4 and values[0]==values[1]==values[2] and values[1]>0 and values[3]==0
    records=unique(records);verify(records)
    seal(PREP,dict(status='prepared_not_built',utc=utc(),inputs=records,adopted_cpu_release=bound(CPU),
        adopted_cpu_compilation_sources=cpu_sources,old_gpu_current_path_reverified=False,pre_fix_snapshot=snapshot,
        commands=[dict(configuration=c,argv=command(c,i),expected_program=str(ROOT/c/'out'/n)) for c,i,n in CONFIGS],
        child_environment=dict(TEMP=str(TEMP),TMP=str(TEMP),CUDA_PATH_V11_7=str(recipe.CUDA)),
        tools=dict(vctools_version='14.36.32532',cuda='11.7',platform_toolset='v143'),
        programs_executed=False,implementation_regression_passed=False,physical_acceptance=False))
    print(PREP)


def build():
    prepared=read(PREP)
    assert not any(p.exists() for p in [START,CHECK,ROOT,TEMP])
    assert not [p for p in LOGS.glob(TAG+'*') if p!=PREP], 'Retained/orphan stage; never retry'
    verify(prepared['inputs']);patch_identity();ROOT.mkdir();TEMP.mkdir()
    seal(START,dict(utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),programs_executed=False))
    env=os.environ.copy();env.update(prepared['child_environment']);stages=[];error=None
    try:
        for config,index,name in CONFIGS:
            verify(prepared['inputs']);folder=ROOT/config;log=LOGS/(TAG+'_'+config+'.log')
            (folder/'out').mkdir(parents=True);(TEMP/config/'int').mkdir(parents=True)
            argv=command(config,index);assert argv==next(r['argv'] for r in prepared['commands'] if r['configuration']==config)
            clock=time.perf_counter();started=utc()
            with log.open('xb') as stream:
                child=subprocess.Popen(argv,cwd=recipe.VS,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                seal(LOGS/(TAG+'_'+config+'.process.json'),dict(utc=started,parent=os.getpid(),pid=child.pid,argv=argv))
                code=child.wait()
            protection_error=runtime_error=None;program=folder/'out'/name;runtime=[]
            try: verify(prepared['inputs'])
            except Exception as failure: protection_error=repr(failure)
            try:
                if code==0 and protection_error is None and program.is_file():
                    for source in recipe.RUNTIME:
                        target=folder/'out'/source.name;assert not target.exists(),'Never overwrite build output'
                        shutil.copy2(source,target);assert bound(source)['sha256']==bound(target)['sha256']
                        runtime.append(dict(source=bound(source),target=bound(target)))
            except Exception as failure: runtime_error=repr(failure)
            try: verify(prepared['inputs'])
            except Exception as failure: protection_error=repr(failure)
            raw=log.read_bytes();text=raw.decode('utf16' if raw.startswith(b'\xff\xfe') else 'utf8',errors='replace')
            warnings=[line for line in text.splitlines() if re.search(r'warning|警告',line,re.I)]
            passed=code==0 and protection_error is None and runtime_error is None and program.is_file() and len(runtime)==4
            receipt=LOGS/(TAG+'_'+config+'.build.json')
            seal(receipt,dict(configuration=config,status='built_not_run' if passed else 'build_rejected',utc=utc(),started_utc=started,
                elapsed_seconds=time.perf_counter()-clock,exit_code=code,owned_exited=child.poll() is not None,
                protected_inputs_unchanged=protection_error is None,protection_error=protection_error,runtime_error=runtime_error,
                argv=argv,program=bound(program) if program.is_file() else None,runtime=runtime,log=bound(log),
                artifacts=[bound(p) for p in [LOGS/(TAG+'_'+config+'.binlog')] if p.is_file()],
                warning_line_count=len(warnings),warning_excerpt=warnings[:30],programs_executed=False))
            stages.append(bound(receipt));assert passed,('Build failed; later configurations held',config,code,protection_error,runtime_error)
    except Exception as failure: error=repr(failure)
    passed=error is None and len(stages)==3
    seal(CHECK,dict(status='builds_passed_pending_implementation_regression' if passed else 'build_rejected_or_interrupted',utc=utc(),passed=passed,
        error=error,prepared=bound(PREP),adopted_cpu_release=prepared['adopted_cpu_release'],fresh_stages=stages,
        programs_executed=False,solver_executed=False,implementation_regression_passed=False,physical_acceptance=False,formal_admitted=False))
    print(CHECK);return 0 if passed else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);actions=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','build']: actions.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest:selftest()
    elif args.prepare:prepare()
    elif args.build:raise SystemExit(build())
    else:parser.print_help()
