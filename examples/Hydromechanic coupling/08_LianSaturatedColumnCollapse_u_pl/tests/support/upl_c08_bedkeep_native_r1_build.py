"""Build the explicit6805 keep-bed reader; six sealed utilities, no solver/decode."""
import os,subprocess,sys,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as old
import upl_c08_as_plane_native_r2_build as csvfix
repair_csv=csvfix.derive_core
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_bedkeep_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def derive_core(raw):
 # The already-reviewed repair recognizes only AS_Bui2008(0.2;2.55) in Configuration.
 raw=repair_csv(raw)
 replacements=[
  ('RetireCount=260,Active=6800','RetireCount=260,Active=6805'),
  ('static constexpr double Dt=', 'static constexpr unsigned KeptBed[]={1800,1852,1904,1956,2008};\nstatic bool Kept(unsigned id){return std::binary_search(KeptBed,KeptBed+5,id);}\nstatic bool Retired(unsigned id){return id>=RetireBegin&&id<RetireBegin+RetireCount&&!Kept(id);}\nstatic constexpr double Dt='),
  ('Only a legacyMR1/unifiedv2 certified elastic 10s PRE/event is admitted");', 'Only a legacyMR1/unifiedv2 certified elastic 10s PRE/event is admitted");\n  for(unsigned id:KeptBed){Need(id>=RetireBegin&&id<RetireBegin+RetireCount&&id<Fixed,"Kept ID must belong to the original certified right-wall target");const auto x=certified.Pos[certified.ById[id]];Need(std::abs(x.z+.5*Dp)<=1e-6*Dp&&std::abs(x.z+.5*double(float(Dp)))<=1e-6*Dp,"Kept source position is not the original half-dp shallow bed row on plane zero");}'),
  ('Original registry/current6800 IDs/no-exclusion differs','Original registry/current6805 IDs/no-exclusion differs'),
  ('!(id>=RetireBegin&&id<RetireBegin+RetireCount),"Unknown/duplicate/retired native ID"','!Retired(id),"Unknown/duplicate/retired native ID"'),
  ('seen[id]==!(id>=RetireBegin&&id<RetireBegin+RetireCount)','seen[id]==!Retired(id)'),
  (r',0,6800,1\n',r',0,6805,1\n'),
  ('fixedChecks==1800*samples','fixedChecks==1805*samples'),
  ('upl_c08_plane_native_r1','upl_c08_bedkeep_native_r1'),
  (r'actual_native_IDs_per_frame\":6800',r'actual_native_IDs_per_frame\":6805'),
  (r'\"retired_ID_begin\":1800,\"retired_ID_count\":260',r'\"release_target_ID_begin\":1800,\"release_target_ID_count\":260,\"actual_retired_count\":255,\"actual_retired_IDs_contiguous\":false,\"kept_bed_IDs\":[1800,1852,1904,1956,2008],\"kept_bed_count\":5,\"actual_fixed_IDs\":1805,\"kept_bed_source_geometry_checks\":5,\"GravityPreloadReleasePolicy\":\"KeepBedOverlap\"')]
 for before,after in replacements:
  need(raw.count(before)==1,'Frozen normal core anchor differs: '+before);raw=raw.replace(before,after,1)
 return raw

def main():
 need(sys.argv[1:]==['--execution-authorized'],'One root-reviewed Release reader build required');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial reader build protected');consumed=[];calls=[]
 try:
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==87,'Passed current ReleaseCPU87 project closure required')
  objects=[e for e in b['project_objects'] if Path(e['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six Release BI4 utility objects required')
  capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');consumed=[stat(__file__),stat(old.__file__),stat(csvfix.__file__),stat(source),stat(T/'support/upl_c08_plane_native_r1.cpp'),stat(note),stat(bp),bind(b['source_capture']),stat(archive),*[bind(e) for e in objects]]
  OUT.mkdir();core=T/'support/upl_c08_plane_native_r1.cpp';original=core.read_text(encoding='utf8');generated=OUT/'bedkeep_core_r1.cpp';generated.write_text(derive_core(original),encoding='utf8',newline='\n');diff=OUT/'bedkeep_core_r1.diff';diff.write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),generated.read_text(encoding='utf8').splitlines(keepends=True),fromfile='support/upl_c08_plane_native_r1.cpp',tofile='generated/bedkeep_core_r1.cpp',n=3)),encoding='utf8');derivation=OUT/'core_derivation.json';save(derivation,dict(baseline_core=stat(core),generated_core=stat(generated),diff=stat(diff),explicit_new_geometry=True,source_target_block_unchanged=260,kept_bed_IDs=[1800,1852,1904,1956,2008],actual_retired_count=255,actual_native_IDs=6805,typed_array_count=22,existing_AS_CSV_repair_reused=True,original_numerical_budgets_changed=False,raw_CSV_changed=False));consumed += [stat(generated),stat(diff),stat(derivation)];headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     target=headers/Path(item.filename).name;need(not target.exists(),'Duplicate archived header leaf');target.write_bytes(z.read(item))
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08NativeBedKeep_win64.exe'
  ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
  la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[e['path'] for e in objects]]
  calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(e['path'])==e for e in consumed),'Consumed reader source/object changed')
  save(check,dict(stage=TAG+'.build',passed=True,configuration='ReleaseCPU utility closure; O2 MT fp:precise GL-',program=stat(exe),source=stat(source),generated_core=stat(generated),core_diff=stat(diff),core_derivation=stat(derivation),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),objects=objects,calls=calls,consumed=consumed,consumed_stats_unchanged=True,actual_link_objects=7,JSph_objects_linked=False,Debug_objects_or_CRT_used=False,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0));print('RELEASE_READER_BUILD_PASSED',exe,flush=True)
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=consumed,SHA_scans=0))
  raise
if __name__=='__main__':main()
