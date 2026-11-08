"""Build epsilon=.2 exponent=3 psi0 window66-state6805 reader; no solver/decode."""
import os,subprocess,sys,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as old
import upl_c08_bedkeep_native_r1_build as bounded
import upl_c08_bedkeep_formal_native_r1_build as formal
import upl_c08_stage_trace_window_native_r1_build as window
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_asn3_window_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

AS_CORE_REPLACEMENTS=[
 ('rightpart="2.55)"','rightpart="3)"',1),
 ('marker="AS_Bui2008(0.2;2.55)"','marker="AS_Bui2008(0.2;3)"',1),
 ('upl_c08_stage_trace_window_native_r1','upl_c08_asn3_window_native_r1',1)]

def derive_core(raw):
 raw=window.derive_core(raw) # Original epsilon=.2/exponent2.55 numerical window profile.
 for before,after,count in AS_CORE_REPLACEMENTS:
  need(raw.count(before)==count,'Frozen exponent3 profile anchor differs: '+before);raw=raw.replace(before,after)
 return raw

def main():
 need(sys.argv[1:]==['--execution-authorized'],'One root-reviewed Release reader build required');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial reader build protected');consumed=[];calls=[]
 try:
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==87,'Passed current ReleaseCPU87 project closure required')
  objects=[e for e in b['project_objects'] if Path(e['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six Release BI4 utility objects required')
  capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');consumed=[stat(__file__),stat(old.__file__),stat(bounded.__file__),stat(bounded.csvfix.__file__),stat(formal.__file__),stat(window.__file__),stat(source),stat(T/'support/upl_c08_plane_native_r1.cpp'),stat(note),stat(bp),bind(b['source_capture']),stat(archive),*[bind(e) for e in objects]]
  OUT.mkdir();core=T/'support/upl_c08_plane_native_r1.cpp';original=core.read_text(encoding='utf8');generated=OUT/'asn3_window_core_r1.cpp';previous=window.derive_core(original);revised=derive_core(original);normalized=revised
  for before,after,count in reversed(AS_CORE_REPLACEMENTS):
   need(normalized.count(after)==count,'Exponent3 core reverse anchor differs');normalized=normalized.replace(after,before)
  need(normalized==previous,'Exponent3 core changed outside the three declared anchors');generated.write_text(revised,encoding='utf8',newline='\n');profile_diff=OUT/'asn3_vs_stage_trace_window_core_r1.diff';profile_diff.write_text(''.join(difflib.unified_diff(previous.splitlines(keepends=True),revised.splitlines(keepends=True),fromfile='prior/stage_trace_window_core_r1.cpp',tofile='generated/asn3_window_core_r1.cpp',n=3)),encoding='utf8');diff=OUT/'asn3_window_core_r1.diff';diff.write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),generated.read_text(encoding='utf8').splitlines(keepends=True),fromfile='support/upl_c08_plane_native_r1.cpp',tofile='generated/asn3_window_core_r1.cpp',n=3)),encoding='utf8');derivation=OUT/'core_derivation.json';save(derivation,dict(baseline_core=stat(core),generated_core=stat(generated),diff=stat(diff),prior_window_profile_builder=stat(window.__file__),prior_window_core_diff=stat(profile_diff),declared_core_replacements=[dict(before=x,after=y,count=n) for x,y,n in AS_CORE_REPLACEMENTS],only_AS_CSV_expectation_and_stage_changed=True,normalized_core_equal=True,AS_coefficient_literal=".2f",AS_exponent_literal="3.f",recognized_AS_fragment="AS_Bui2008(0.2;3)",inherited_bedkeep_geometry=True,new_geometry_vs_prior_window=False,source_target_block_unchanged=260,kept_bed_IDs=[1800,1852,1904,1956,2008],actual_retired_count=255,actual_native_IDs=6805,typed_array_count=22,existing_AS_CSV_repair_reused=True,window_group="psi0",window_global_end=4264000,window_saved_samples=66,window_save_cadence_steps=4000,external_launch_plan_claimed=False,original_numerical_budgets_changed=False,raw_CSV_changed=False));consumed += [stat(generated),stat(diff),stat(profile_diff),stat(derivation)];headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     target=headers/Path(item.filename).name;need(not target.exists(),'Duplicate archived header leaf');target.write_bytes(z.read(item))
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08ASN3WindowNative_win64.exe'
  ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
  la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[e['path'] for e in objects]]
  calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(e['path'])==e for e in consumed),'Consumed reader source/object changed')
  save(check,dict(stage=TAG+'.build',passed=True,configuration='ReleaseCPU utility closure; O2 MT fp:precise GL-',program=stat(exe),source=stat(source),generated_core=stat(generated),core_diff=stat(diff),prior_window_core_diff=stat(profile_diff),core_derivation=stat(derivation),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),objects=objects,calls=calls,consumed=consumed,consumed_stats_unchanged=True,actual_link_objects=7,JSph_objects_linked=False,Debug_objects_or_CRT_used=False,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0));print('RELEASE_READER_BUILD_PASSED',exe,flush=True)
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=consumed,SHA_scans=0))
  raise
if __name__=='__main__':main()
