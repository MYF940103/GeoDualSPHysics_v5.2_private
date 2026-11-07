"""Build the psi0 formal300-state6805 reader; six sealed utilities, no solver/decode."""
import os,subprocess,sys,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as old
import upl_c08_bedkeep_native_r1_build as bounded
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_bedkeep_formal_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def derive_core(raw):
 raw=bounded.derive_core(raw) # Already-reviewed6805 ID/geometry and strict AS CSV repair.
 a=raw.index('static std::vector<unsigned> Planned(');b=raw.index('int wmain(',a)
 need(raw[a:b].count('static std::vector<unsigned> Planned(')==1,'Old unused external-plan helper scope changed');raw=raw[:a]+raw[b:]
 replacements=[
  ('argc==11','argc==8'),
  ('Use --read psi0 CPU|GPU DATA PRE ENDSTEP SAMPLES NOPEN STEPS_CSV FRESHOUT','Use --read psi0 CPU|GPU DATA PRE 5200000 FRESHOUT'),
  ('Only the bounded psi0 material is admitted','Only the formal3s psi0 material is admitted'),
  ('const fs::path data=argv[4],pre=argv[5],planned=argv[9],out=argv[10];const unsigned expected=Number(argv[6]),samples=Number(argv[7]);Need(expected>EventStep&&samples>0&&samples<=expected-EventStep,"Positive explicit post-PRE end/count required");Need(std::wstring(argv[8])==L"0"||std::wstring(argv[8])==L"1","NOPEN must be literal0 or1");const bool nopen=std::wstring(argv[8])==L"1";const auto steps=Planned(planned,samples,expected);Need(RunSamples(data.parent_path()/"Run.csv",expected)==samples,"Normal Run.csv end/count differs from the explicit owner plan");',
   'const fs::path data=argv[4],pre=argv[5],out=argv[7];const unsigned expected=Number(argv[6]),samples=300;Need(expected==5200000,"Only global5200000 is admitted for the formal psi0 diagnostic");const bool nopen=true;std::vector<unsigned> steps(samples);for(unsigned part=0;part<samples;part++)steps[part]=EventStep+4000*(part+1);Need(RunSamples(data.parent_path()/"Run.csv",expected)==samples,"Normal Run.csv must have global5200000 and300 actual saved frames");'),
  ('upl_c08_bedkeep_native_r1','upl_c08_bedkeep_formal_native_r1'),
  ('Actual saved Step differs from the launch owner planned steps','Actual saved Step differs from the explicit formal4000-step save profile'),
  (r'"saved_steps_checked_against_launch_plan\":true',r'"saved_steps_checked_against_formal_profile\":true,\"save_profile_origin\":\"explicit formal constants; not an external launch plan\",\"formal_save_cadence_steps\":4000,\"formal_saved_samples\":300,\"formal_material_groups_admitted\":[\"psi0\"],\"full_3s_diagnostic_only\":true')]
 for before,after in replacements:
  need(raw.count(before)==1,'Frozen formal profile anchor differs: '+before);raw=raw.replace(before,after,1)
 return raw

def main():
 need(sys.argv[1:]==['--execution-authorized'],'One root-reviewed Release reader build required');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial reader build protected');consumed=[];calls=[]
 try:
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==87,'Passed current ReleaseCPU87 project closure required')
  objects=[e for e in b['project_objects'] if Path(e['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six Release BI4 utility objects required')
  capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');consumed=[stat(__file__),stat(old.__file__),stat(bounded.__file__),stat(bounded.csvfix.__file__),stat(source),stat(T/'support/upl_c08_plane_native_r1.cpp'),stat(note),stat(bp),bind(b['source_capture']),stat(archive),*[bind(e) for e in objects]]
  OUT.mkdir();core=T/'support/upl_c08_plane_native_r1.cpp';original=core.read_text(encoding='utf8');generated=OUT/'bedkeep_formal_core_r1.cpp';generated.write_text(derive_core(original),encoding='utf8',newline='\n');diff=OUT/'bedkeep_formal_core_r1.diff';diff.write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),generated.read_text(encoding='utf8').splitlines(keepends=True),fromfile='support/upl_c08_plane_native_r1.cpp',tofile='generated/bedkeep_formal_core_r1.cpp',n=3)),encoding='utf8');derivation=OUT/'core_derivation.json';save(derivation,dict(baseline_core=stat(core),generated_core=stat(generated),diff=stat(diff),explicit_new_geometry=True,source_target_block_unchanged=260,kept_bed_IDs=[1800,1852,1904,1956,2008],actual_retired_count=255,actual_native_IDs=6805,typed_array_count=22,existing_AS_CSV_repair_reused=True,formal_group="psi0",formal_global_end=5200000,formal_saved_samples=300,formal_save_cadence_steps=4000,external_launch_plan_claimed=False,original_numerical_budgets_changed=False,raw_CSV_changed=False));consumed += [stat(generated),stat(diff),stat(derivation)];headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     target=headers/Path(item.filename).name;need(not target.exists(),'Duplicate archived header leaf');target.write_bytes(z.read(item))
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08Native_win64.exe'
  ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
  la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[e['path'] for e in objects]]
  calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(e['path'])==e for e in consumed),'Consumed reader source/object changed')
  save(check,dict(stage=TAG+'.build',passed=True,configuration='ReleaseCPU utility closure; O2 MT fp:precise GL-',program=stat(exe),source=stat(source),generated_core=stat(generated),core_diff=stat(diff),core_derivation=stat(derivation),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),objects=objects,calls=calls,consumed=consumed,consumed_stats_unchanged=True,actual_link_objects=7,JSph_objects_linked=False,Debug_objects_or_CRT_used=False,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0));print('RELEASE_READER_BUILD_PASSED',exe,flush=True)
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=consumed,SHA_scans=0))
  raise
if __name__=='__main__':main()
