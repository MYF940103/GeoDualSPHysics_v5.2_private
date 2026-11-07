"""R2 item-function import repair only; use original authoritative projects and unchanged three CPPs."""
import argparse,json,os,subprocess
from pathlib import Path
import upl_c08_nopen_build_r1 as base
T,C,R,S,L,TAG,CAP,FILES=base.T,base.C,base.R,base.S,base.L,base.TAG,base.CAP,base.FILES
need,read,stat,bind,save,invoke,check_report=base.need,base.read,base.stat,base.bind,base.save,base.invoke,base.check_report
def build(action,conf):
    gpu=conf=='Release';tag=TAG+'_'+conf+'_r2';receipt=L/(tag+('.evaluate.json' if action=='evaluate' else '.build.json'));need(not receipt.exists(),'Existing build/evaluation protected');prep=L/(TAG+'_source_r1.prepare.json');c=read(prep);need(c['passed'] and c['original_worktree_stats_unchanged'],'Prepared overlay source required');consumed=[stat(prep),*[bind(e) for e in c['files']],*[bind(e) for e in c['original_worktree']],stat(Path(__file__)),stat(T/'notes/upl_c08_nopen_build_r2.md'),stat(Path(base.__file__)),stat(CAP/'overlay_r2.props')]
    out=T/'outputs'/tag;inter=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_c08_nopen_r2'/conf/'int';need(' ' not in str(inter),'No-space CUDA IntDir required');template=L/('upl_c08_artstress_'+conf+'_r1.call.json');call=read(template);args=call['arguments'].copy();report=L/(tag+('.evaluate.items.txt' if action=='evaluate' else '.build.items.txt'));need(not report.exists(),'Existing evaluated items report protected');logtag=tag+'.'+action
    args=[('/t:C08NoPenValidateClCompileItems' if action=='evaluate' else '/t:Build') if x.startswith('/t:') else '/p:OutDir='+out.as_posix()+'/' if x.startswith('/p:OutDir=') else '/p:IntDir='+inter.as_posix()+'/' if x.startswith('/p:IntDir=') else '/bl:'+str(L/(logtag+'.binlog')) if x.startswith('/bl:') else x for x in args]
    # A solution metaproject does not expose arbitrary C++ targets: evaluate its actual authoritative project directly.
    if action=='evaluate':args[0]=str(S/'VS'/('DualSPHysics5Re.vcxproj' if gpu else 'DualSPHysics5ReCpu.vcxproj'))
    # Builds still use the original solution; only this evaluated item overlay is imported.
    args += ['/p:ForceImportBeforeCppTargets='+(CAP/'overlay_r2.props').as_posix(),'/p:C08NoPenItemsReport='+str(report)]
    need('/p:PostBuildEventUseInBuild=false' in args and '/p:VCToolsVersion=14.36.32532' in args,'Original isolated VS toolchain flags differ');consumed.append(stat(template));protected=[]
    for root in [R/'bin/windows',C/'support/runtime_r2',C/'support/runtime_r3']:
        protected += [stat(p) for p in root.iterdir() if p.is_file() and p.suffix.lower() in ('.exe','.dll','.pdb','.xml')]
    for name in ('DebugCPU','Debug','Release'):
        b=read(L/('upl_c08_artstress_'+name+'_r1.build.json'));need(b['passed'],'Original AS build not closed');protected += [bind(b['program']),*[bind(e) for e in b['project_objects']]]
    if action=='build':
        ev=read(L/(tag+'.evaluate.json'));need(ev['passed'] and ev['items']['passed'],'Explicit same-config evaluated-items pass required before compiling');consumed.append(stat(L/(tag+'.evaluate.json')));need(not out.exists() and not inter.parent.exists(),'Existing/partial isolated objects/output protected');out.mkdir();inter.mkdir(parents=True)
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required');actual=None;result=dict(stage=logtag,passed=False,programs_or_solvers_started=0,SHA_scans=0,physical_acceptance=False)
    try:
        actual=invoke(logtag,[call['program'],*args],S,env);items=check_report(report);need(all(stat(e['path'])==e for e in consumed+protected),'Frozen source, canonicals or old object stats changed');result.update(passed=True,actual_call=actual,items=items,consumed=consumed,protected=protected,source_stats_unchanged=True,canonical_runtime_old_objects_stats_unchanged=True)
        if action=='build':
            exe=out/('DualSPHysics5.2_GEO_win64.exe' if gpu else 'DualSPHysics5.2CPU_win64_debug.exe');objects=[stat(p) for p in sorted(inter.glob('*.obj'))];need(exe.is_file() and len(objects)==(113 if gpu else 87),'Original authoritative object/program closure differs');result.update(program=stat(exe),project_objects=objects,source_capture=stat(prep),source_archive=stat(CAP/'baselineAS_source.zip'),overlay_sources=[stat(CAP/p) for p in FILES],actual_typed_exit_code=0,actual_Win32_exit=0)
    except Exception as e:
        cp=L/(logtag+'.call.json')
        if cp.exists():
            actual=stat(cp);record=read(cp);result.update(actual_typed_exit_code=record['actual_Popen_wait_exit'],actual_Win32_exit=record['actual_Win32_exit'])
        result.update(passed=False,first_failure=str(e),actual_call=actual,consumed=consumed,protected=protected)
    save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('evaluate','build'));ap.add_argument('--configuration',choices=('DebugCPU','Release'),required=True);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full review and one explicit r2 action required');return build(a.action,a.configuration)
if __name__=='__main__':raise SystemExit(main())
