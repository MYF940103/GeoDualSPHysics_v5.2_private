"""Capture fixed-plane contact source; build one explicit authoritative VS configuration, never run a solver."""
import argparse,json,os,re,subprocess,zipfile
from pathlib import Path
import mdbc_partition_components_r3 as evidence
T=Path(__file__).resolve().parents[1];C=T.parent;R=T.parents[3];S=R/'src';L=T/'logs'
TAG='upl_c08_plane';CAP=T/'outputs'/(TAG+'_source_r1');POLICY='FixedPlaneStageProjectionReleaseOnly'
need,read,stat,bind,save,invoke=evidence.need,evidence.read,evidence.stat,evidence.bind,evidence.save,evidence.invoke
CONFIGS={
    'DebugCPU':('upl_c08_artstress_DebugCPU_r1.call.json','DualSPHysics5.2CPU_win64_debug.exe',87),
    'ReleaseCPU':('mdbc_partition_ReleaseCPU_r1.call.json','DualSPHysics5.2CPU_win64.exe',87),
    'Debug':('upl_c08_artstress_Debug_r1.call.json','DualSPHysics5.2_win64_debug.exe',113),
    'Release':('upl_c08_artstress_Release_r1.call.json','DualSPHysics5.2_GEO_win64.exe',113)}
DIFF=('src/source/JSph.h','src/source/JSph.cpp','src/source/JSphCpu.h','src/source/JSphCpu.cpp',
      'src/source/JSphGpu.h','src/source/JSphGpu.cpp','src/source/JSphGpuSimple_ker.h',
      'src/source/JSphGpuSimple_ker.cu','src/source/FunFixedPlaneContact.h',
      'doc/xml_format/_FmtXML_ElastoplasticSoil.xml')

def unchanged(entries):
    return all(Path(e['path']).is_file() and stat(e['path'])==e for e in entries)

def protected_files():
    roots=(R/'bin/windows',C/'support/runtime_r3',C/'support/runtime_r4')
    need(all(p.is_dir() for p in roots),'Canonical and both retained runtime directories required')
    return [stat(p) for root in roots for p in sorted(root.rglob('*')) if p.is_file()]

def capture():
    need(not CAP.exists(),'Existing source capture protected')
    need((S/'source/FunFixedPlaneContact.h').is_file(),'Finish and review the new contact helper before capture')
    names=subprocess.check_output(['rg','--files','source','-g','*.h','-g','*.hpp','-g','*.cpp','-g','*.cu','-g','*.cuh','-g','*.inl','-g','*.c','-g','*.tpp'],cwd=S,text=True).splitlines()
    projects=('DualSPHysics5Re.sln','DualSPHysics5Re.vcxproj','DualSPHysics5ReCpu_vs2022.sln','DualSPHysics5ReCpu.vcxproj')
    files=sorted({S/n for n in names}|{S/'VS'/n for n in projects}|{R/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml',Path(__file__).resolve(),Path(evidence.__file__).resolve()})
    before=[stat(p) for p in files];CAP.mkdir()
    with zipfile.ZipFile(CAP/'source.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(R).as_posix())
    need(unchanged(before),'Compilation inputs changed during capture')
    # git diff omits an untracked new helper; the full source archive includes it regardless.
    diff=subprocess.check_output(['git','diff','--binary','--',*DIFF],cwd=R)
    (CAP/'production.diff').write_bytes(diff)
    need(unchanged(before),'Compilation inputs changed while recording the diff')
    save(CAP/'source.json',dict(stage=TAG+'_source_r1',policy=POLICY,files=before,archive=stat(CAP/'source.zip'),production_diff=stat(CAP/'production.diff'),diff_paths=list(DIFF),new_contact_helper=stat(S/'source/FunFixedPlaneContact.h'),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),source_worktree_captured_not_claimed_committed=True,SHA_scans=0))
    print('PRODUCTION_SOURCE_CAPTURED',CAP,flush=True)

def build(conf):
    tag=TAG+'_'+conf+'_r1';out=T/'outputs'/tag;inter=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_c08_plane_r1'/conf/'int';receipt=L/(tag+'.build.json')
    need(not out.exists() and not inter.parent.exists() and not receipt.exists() and not any((L/(tag+s)).exists() for s in ('.log','.call.json','.binlog')),'Existing configuration, partial output or invocation protected')
    before=[];protected=[];actual=None
    result=dict(stage=tag,passed=False,configuration=conf,policy=POLICY,physical_acceptance=False,solver_invocations=0,SHA_scans=0)
    try:
        source=read(CAP/'source.json');need(source['policy']==POLICY,'Matching reviewed plane-contact capture required')
        before=[bind(x) for x in source['files']]+[stat(CAP/'source.json'),bind(source['archive']),bind(source['production_diff'])]
        template,leaf,expected=CONFIGS[conf];template=L/template;b=read(template);before.append(stat(template))
        need(b['actual_Popen_wait_exit']==b['actual_Win32_exit']==0,'Closed successful same-configuration build recipe required')
        args=[('/p:OutDir='+out.as_posix()+'/') if x.startswith('/p:OutDir=') else ('/p:IntDir='+inter.as_posix()+'/') if x.startswith('/p:IntDir=') else '/bl:'+str(L/(tag+'.binlog')) if x.startswith('/bl:') else x for x in b['arguments']]
        solution=S/'VS'/('DualSPHysics5ReCpu_vs2022.sln' if conf.endswith('CPU') else 'DualSPHysics5Re.sln')
        need(Path(args[0]).samefile(solution) and '/t:Build' in args and '/p:Configuration='+conf in args and '/p:Platform=x64' in args,'Authoritative matching solution/configuration required')
        need('/p:PostBuildEventUseInBuild=false' in args and '/p:VCToolsVersion=14.36.32532' in args and ' ' not in str(inter),'Original toolchain and isolated no-space IntDir required')
        protected=protected_files()
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
        need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required');out.mkdir();inter.mkdir(parents=True)
        actual=invoke(tag,[b['program'],*args],S,env)
        exe=out/leaf;objects=[stat(p) for p in sorted(inter.glob('*.obj'))]
        need(exe.is_file() and len(objects)==expected and sum(Path(e['path']).name.lower()=='main.obj' for e in objects)==1,'Actual authoritative program/object closure differs')
        text=(L/(tag+'.log')).read_bytes().decode('mbcs',errors='replace');errors=[x for x in text.splitlines() if re.search(r'\b(?:fatal )?error [A-Z]+\d+|nvcc fatal',x,re.I)]
        need(not errors and unchanged(before) and protected_files()==protected,'Source changed, protected files changed, or compile error')
        result.update(passed=True,actual_typed_exit_code=0,actual_Win32_exit=0,actual_call=actual,program=stat(exe),project_objects=objects,source_capture=stat(CAP/'source.json'),source_archive=stat(CAP/'source.zip'),warning_lines=[x for x in text.splitlines() if re.search(r'\bwarning [A-Z]+\d+',x,re.I)])
    except Exception as e:
        result.update(first_failure=str(e),actual_call=actual)
        cp=L/(tag+'.call.json')
        if cp.exists():
            q=read(cp);result.update(actual_typed_exit_code=q['actual_Popen_wait_exit'],actual_Win32_exit=q['actual_Win32_exit'])
    result.update(compilation_inputs=before,protected=protected,source_stats_unchanged=bool(before) and unchanged(before),canonical_runtime_old_programs_unchanged=bool(protected) and protected_files()==protected)
    save(receipt,result)
    print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('capture',*CONFIGS));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Reviewed explicit capture/build action required')
    if a.action=='capture':capture()
    else:raise SystemExit(build(a.action))
