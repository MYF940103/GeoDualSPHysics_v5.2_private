"""Capture a frozen trace patch and build one isolated VS configuration; never run a program."""
import argparse,difflib,json,os,re,subprocess,zipfile
from pathlib import Path
import mdbc_partition_components_r3 as evidence

T=Path(__file__).resolve().parents[1];C=T.parent;R=T.parents[3];S=R/'src';L=T/'logs';TAG='upl_c08_stage_trace';CAP=T/'outputs'/(TAG+'_source_r1')
TRACE='C08_STAGE_TRACE';HEADER=S/'source/C08StageTrace.h';PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
CONFIGS={'DebugCPU':('upl_c08_bedkeep_DebugCPU_r1.call.json','DualSPHysics5.2CPU_win64_debug.exe',87),
         'Debug':('upl_c08_bedkeep_Debug_r1.call.json','DualSPHysics5.2_win64_debug.exe',113),
         'Release':('upl_c08_bedkeep_Release_r1.call.json','DualSPHysics5.2_GEO_win64.exe',113)}
DIFF=('src/source/C08StageTrace.h','src/source/JSphGpu.cpp','src/source/JSphGpu_ker.cu')
need,read,stat,bind,save,invoke=evidence.need,evidence.read,evidence.stat,evidence.bind,evidence.save,evidence.invoke

def unchanged(entries):return all(Path(e['path']).is_file() and stat(e['path'])==e for e in entries)

def protected_files():
    names=('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe')
    files=[R/'bin/windows'/name for name in names]+[PRE];runtime=C/'support/runtime_r5'
    need(runtime.is_dir() and all(p.is_file() for p in files),'Canonical four programs, runtime_r5 and original PRE required')
    files += [p for p in sorted(runtime.iterdir()) if p.is_file()]
    return [stat(p) for p in files] # Deliberately no old-program/object/lib/raw directory traversal.

def capture():
    need(not CAP.exists(),'Existing complete/partial source capture protected');need(HEADER.is_file(),'Root must apply, freeze and review the trace header/patch before capture')
    names=subprocess.check_output(['rg','--files','source','-g','*.h','-g','*.hpp','-g','*.cpp','-g','*.cu','-g','*.cuh','-g','*.inl','-g','*.c','-g','*.tpp'],cwd=S,text=True).splitlines()
    projects=('DualSPHysics5Re.sln','DualSPHysics5Re.vcxproj','DualSPHysics5ReCpu_vs2022.sln','DualSPHysics5ReCpu.vcxproj')
    files=sorted({S/n for n in names}|{S/'VS'/n for n in projects}|{HEADER,Path(__file__).resolve(),Path(evidence.__file__).resolve(),T/'notes/upl_c08_stage_trace_build_r1.md'})
    before=[stat(p) for p in files];CAP.mkdir()
    with zipfile.ZipFile(CAP/'source.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.relative_to(R).as_posix())
    need(unchanged(before),'Compilation inputs changed during capture')
    diff=subprocess.check_output(['git','diff','--binary','--',*DIFF],cwd=R)
    tracked=subprocess.run(['git','ls-files','--error-unmatch','--',DIFF[0]],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    need(tracked.returncode in (0,1),'Trace header tracking query failed')
    if tracked.returncode!=0:
        body=HEADER.read_bytes().decode('utf-8');extra='diff --git a/'+DIFF[0]+' b/'+DIFF[0]+'\nnew file mode 100644\n'+''.join(difflib.unified_diff([],body.splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+DIFF[0]))
        diff+=extra.encode('utf-8') # Include the one new untracked header without staging or hashing it.
    with (CAP/'production.diff').open('xb') as out:out.write(diff)
    need(unchanged(before),'Compilation inputs changed while recording the diff')
    save(CAP/'source.json',dict(stage=TAG+'_source_r1',files=before,archive=stat(CAP/'source.zip'),production_diff=stat(CAP/'production.diff'),diff_paths=list(DIFF),trace_header=stat(HEADER),untracked_header_diff_added=(tracked.returncode!=0),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),source_worktree_captured_not_claimed_committed=True,CPU_Debug_trace_macro=False,GPU_Debug_Release_trace_macro=True,solver_invocations=0,SHA_scans=0))
    print('STAGE_TRACE_SOURCE_CAPTURED',CAP,flush=True)

def build(conf):
    tag=TAG+'_'+conf+'_r1';out=T/'outputs'/tag;inter=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_c08_stage_trace_r1'/conf/'int';receipt=L/(tag+'.build.json');gpu=conf!='DebugCPU'
    need(not out.exists() and not inter.parent.exists() and not receipt.exists() and not any((L/(tag+s)).exists() for s in ('.log','.call.json','.binlog')),'Existing configuration/partial output/invocation protected')
    before=[];protected=[];actual=None
    result=dict(stage=tag,passed=False,configuration=conf,trace_macro=TRACE,trace_macro_enabled=gpu,physical_acceptance=False,solver_invocations=0,help_invocations=0,reader_invocations=0,SHA_scans=0)
    try:
        source=read(CAP/'source.json');need(source['stage']==TAG+'_source_r1' and not source['CPU_Debug_trace_macro'] and source['GPU_Debug_Release_trace_macro'],'Matching reviewed trace capture required')
        before=[bind(e) for e in source['files']]+[stat(CAP/'source.json'),bind(source['archive']),bind(source['production_diff'])]
        template,leaf,expected=CONFIGS[conf];template=L/template;old=read(template);before.append(stat(template));need(old['actual_Popen_wait_exit']==old['actual_Win32_exit']==0,'Closed same-configuration bedkeep recipe required')
        args=[('/p:OutDir='+out.as_posix()+'/') if x.startswith('/p:OutDir=') else ('/p:IntDir='+inter.as_posix()+'/') if x.startswith('/p:IntDir=') else '/bl:'+str(L/(tag+'.binlog')) if x.startswith('/bl:') else x for x in old['arguments']]
        solution=S/'VS'/('DualSPHysics5Re.sln' if gpu else 'DualSPHysics5ReCpu_vs2022.sln')
        need(Path(args[0]).samefile(solution) and '/t:Build' in args and '/p:Configuration='+conf in args and '/p:Platform=x64' in args and '/p:VCToolsVersion=14.36.32532' in args and '/p:PostBuildEventUseInBuild=false' in args and ' ' not in str(inter),'Authoritative isolated solution/configuration/toolchain differs')
        if gpu:
            project=(S/'VS/DualSPHysics5Re.vcxproj').read_text(encoding='utf-8-sig');need('CUDA 11.7.props' in project and 'CUDA 11.7.targets' in project and 'compute_86,sm_86' in project,'Captured authoritative CUDA11.7/sm86 project required')
        protected=protected_files()
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        need(all(TRACE not in env.get(key,'') for key in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS')),'Inherited trace macro override is outside this explicit build recipe')
        additions={'CL':'/D'+TRACE,'NVCC_PREPEND_FLAGS':'-D'+TRACE} if gpu else {}
        for key,value in additions.items():env[key]=(env.get(key,'')+' '+value).strip()
        result['environment_macro']=dict(enabled=gpu,appended=additions,inherited_trace_override=False,CPU_Debug_undefined=(not gpu),full_environment_not_recorded=True)
        out.mkdir();inter.mkdir(parents=True);actual=invoke(tag,[old['program'],*args],S,env)
        exe=out/leaf;objects=[stat(p) for p in sorted(inter.glob('*.obj'))];need(exe.is_file() and len(objects)==expected and sum(Path(e['path']).name.lower()=='main.obj' for e in objects)==1,'Actual program/object closure differs')
        text=(L/(tag+'.log')).read_bytes().decode('mbcs',errors='replace');errors=[x for x in text.splitlines() if re.search(r'\b(?:fatal )?error [A-Z]+\d+|nvcc fatal',x,re.I)]
        need(not errors and unchanged(before) and protected_files()==protected,'Compilation error, changed input or protected artifact')
        result.update(passed=True,actual_typed_exit_code=0,actual_Win32_exit=0,actual_call=actual,program=stat(exe),project_objects=objects,source_capture=stat(CAP/'source.json'),source_archive=stat(CAP/'source.zip'),error_lines=errors,warning_lines=[x for x in text.splitlines() if re.search(r'\bwarning [A-Z]+\d+',x,re.I)])
    except Exception as error:
        result.update(first_failure=str(error),actual_call=actual);cp=L/(tag+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_typed_exit_code=call['actual_Popen_wait_exit'],actual_Win32_exit=call['actual_Win32_exit'])
        log=L/(tag+'.log')
        if log.exists():
            text=log.read_bytes().decode('mbcs',errors='replace');result.update(error_lines=[x for x in text.splitlines() if re.search(r'\b(?:fatal )?error [A-Z]+\d+|nvcc fatal',x,re.I)],warning_lines=[x for x in text.splitlines() if re.search(r'\bwarning [A-Z]+\d+',x,re.I)])
    result.update(compilation_inputs=before,protected=protected,source_stats_unchanged=bool(before) and unchanged(before),canonical_runtime_PRE_unchanged=bool(protected) and protected_files()==protected)
    save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('capture',*CONFIGS));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read/freeze and explicit single-action authorization required')
    if a.action=='capture':capture()
    else:raise SystemExit(build(a.action))
