"""Build the release-Shepard native adapter from the sealed causal generated core; no decode."""
import os,subprocess,sys,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as old
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_shepard_native_r1';OUT=T/'outputs'/(TAG+'_build');BASE=L/'upl_c08_causal_native_r1.build.json'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke
REPLACEMENTS=[('&&!p->GetvBool("PoreShepardActive")','&&p->GetvBool("PoreShepardActive")',1),('Post-release damping/Shepard remained active','Post-release requires damping OFF and Shepard ON',1),('upl_c08_causal_native_r1','upl_c08_shepard_native_r1',1)]

def main():
 need(sys.argv[1:]==['--execution-authorized'],'Author-only until root full review');check=L/(TAG+'.build.json');need(not OUT.exists() and all(not (L/(TAG+s)).exists() for s in ('.build.json','.compile.call.json','.compile.log','.link.call.json','.link.log')),'Existing complete/partial reader build protected');consumed=[];calls=[]
 try:
  b=read(BASE);need(b['passed'] and b['consumed_stats_unchanged'] and b['actual_link_objects']==7 and not b['JSph_objects_linked'] and not b['Debug_objects_or_CRT_used'],'Closed Release causal reader required');objects=b['objects'];need(len(objects)==6 and {Path(e['path']).stem for e in objects}=={'JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'},'Exactly the sealed six Release BI4 utilities required')
  source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');core=Path(bind(b['generated_core'])['path']);archive=Path(bind(b['source_archive'])['path']);cc,lc=[read(bind(e)['path']) for e in b['calls']];need(all(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0 and c['ownership_failure'] is None for c in (cc,lc)),'Actual original CL/link calls must both have exited0')
  consumed=[stat(__file__),stat(old.__file__),stat(source),stat(note),stat(BASE),bind(b['source']),bind(b['generated_core']),bind(b['source_build']),bind(b['source_capture']),stat(archive),*[bind(e) for e in b['calls']],*[bind(e) for e in objects],stat(cc['program']),stat(lc['program'])]
  OUT.mkdir();rawbytes=core.read_bytes();original=rawbytes.decode('utf-8');revised=original
  for before,after,count in REPLACEMENTS:need(revised.count(before)==count,'Closed generated-core anchor differs: '+before);revised=revised.replace(before,after)
  normalized=revised
  for before,after,count in reversed(REPLACEMENTS):need(normalized.count(after)==count,'Reverse generated-core anchor differs');normalized=normalized.replace(after,before)
  need(normalized.encode('utf-8')==rawbytes,'Generated core changed outside PoreShepardActive expectation/message/stage');generated=OUT/'shepard_core_r1.cpp';generated.write_bytes(revised.encode('utf-8'));diff=OUT/'shepard_vs_causal_core_r1.diff';diff.write_text(''.join(difflib.unified_diff(original.splitlines(True),revised.splitlines(True),fromfile='closed/causal_core_r1.cpp',tofile='generated/shepard_core_r1.cpp')),encoding='utf-8')
  derivation=OUT/'core_derivation.json';save(derivation,dict(baseline_build=stat(BASE),baseline_generated_core=stat(core),generated_core=stat(generated),diff=stat(diff),declared_replacements=[dict(before=x,after=y,count=n) for x,y,n in REPLACEMENTS],reverse_normalized_bytes_exact=True,only_metadata_expectation_message_and_stage_changed=True,PoreShepardActive_expected=True,SoilDampingActive_expected=False,adapter_profiles=[dict(samples=2,end=4000080,cadence=40,final_only=False),dict(samples=90,end=4360000,cadence=4000,final_only=False)],all_original22_guards_and_budgets_unchanged=True,filter_call_counts_not_inferred_from_native=True));consumed += [stat(generated),stat(diff),stat(derivation)]
  headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     target=headers/Path(item.filename).name;need(not target.exists(),'Duplicate archived header leaf');target.write_bytes(z.read(item))
  oldout=Path(b['program']['path']).parent;ca=[str(source) if x==b['source']['path'] else x.replace(str(oldout),str(OUT)) for x in cc['arguments']];exe=OUT/'C08ShepardNative_win64.exe';la=[x.replace(str(oldout),str(OUT)).replace('C08CausalNative_win64.exe',exe.name) for x in lc['arguments']]
  need(all(x in ca for x in ('/O2','/MT','/fp:precise','/GL-','/D_HAS_STD_BYTE=0')) and sum(x.lower().endswith('.obj') for x in la)==7 and '/OUT:'+str(exe) in la,'Original Release main/six-utility recipe differs')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  calls.append(invoke(TAG+'.compile',[cc['program'],*ca],OUT,env));calls.append(invoke(TAG+'.link',[lc['program'],*la],OUT,env));need(all(stat(e['path'])==e for e in consumed),'Consumed source/object changed')
  save(check,dict(stage=TAG+'.build',passed=True,configuration='ReleaseCPU utility closure; O2 MT fp:precise GL-',program=stat(exe),source=stat(source),generated_core=stat(generated),core_diff=stat(diff),core_derivation=stat(derivation),baseline_causal_build=stat(BASE),source_build=b['source_build'],source_capture=b['source_capture'],source_archive=stat(archive),objects=objects,calls=calls,consumed=consumed,consumed_stats_unchanged=True,actual_link_objects=7,JSph_objects_linked=False,Debug_objects_or_CRT_used=False,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0));print('SHEPARD_NATIVE_BUILD_PASSED',exe,flush=True)
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=consumed,SHA_scans=0))
  raise
if __name__=='__main__':main()
