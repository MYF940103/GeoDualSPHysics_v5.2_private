"""Build only a failed51-state derivative of the sealed n3 causal core; six utility objects, no solver."""
import os,subprocess,sys,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as e
import upl_c08_causal_native_r1_build as normal
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_as_effective_partial_r1';OUT=T/'outputs'/(TAG+'_build')
REPLACEMENTS=[
 ('const auto steps=Planned(planned,samples,expected);Need(RunSamples(data.parent_path()/"Run.csv",expected)==samples,"Normal Run.csv end/count differs from the explicit owner plan");','Need(expected==4204000&&samples==51&&nopen,"Only failed GPU51/4204000/NoPen1 saved-state profile is admitted");const auto steps=Planned(planned,90,4360000);Need(steps[samples-1]==expected,"Original90 launch plan must have this genuine51-state prefix");'),
 ('upl_c08_causal_native_r1','upl_c08_as_effective_partial_r1'),
 (r'\"completed_runtime_Run_csv_checked\":true',r'\"completed_runtime_Run_csv_checked\":false,\"partial\":true,\"runtime_success_claimed\":false,\"original_planned_samples\":90,\"original_planned_end\":4360000,\"used_launch_plan_prefix_samples\":51,\"last_saved_step\":4203999,\"completed_steps_are_last_saved\":true,\"new_updates_are_to_last_saved\":true,\"AS_stress_space_proven_by_reader\":false,\"failure_unsaved_state_reconstructed\":false')]

def derive_core(previous):
 revised=previous
 for old,new in REPLACEMENTS:e.need(revised.count(old)==1,'Frozen n3 core anchor differs: '+old);revised=revised.replace(old,new,1)
 normalized=revised
 for old,new in reversed(REPLACEMENTS):e.need(normalized.count(new)==1,'Partial-core reverse anchor differs');normalized=normalized.replace(new,old,1)
 e.need(normalized==previous,'Partial core changed outside the three declared anchors')
 begin=previous.index('  Need(fs::is_directory(data)');end=previous.index('  std::ofstream done(out/"completion.json")');rb=revised.index('  Need(fs::is_directory(data)');re=revised.index('  std::ofstream done(out/"completion.json")');e.need(previous[begin:end]==revised[rb:re],'Original core61-99/PRE and all array/numeric checks must be literal unchanged')
 return revised

def main():
 e.need(sys.argv[1:]==['--execution-authorized'],'Root-reviewed single utility build required');check=L/(TAG+'.build.json');e.need(not OUT.exists() and not check.exists(),'Existing/partial build protected');consumed=[];calls=[]
 try:
  priorpath=L/'upl_c08_causal_native_r1.build.json';prior=e.read(priorpath);e.need(prior['passed'] and prior['consumed_stats_unchanged'] and len(prior['objects'])==6 and prior['actual_link_objects']==7 and not prior['JSph_objects_linked'],'Closed six-utility n3 normal reader closure required');objects=[e.bind(v) for v in prior['objects']];baseline=Path(e.bind(prior['generated_core'])['path']);previous=baseline.read_text(encoding='utf-8');revised=derive_core(previous);archive=Path(e.bind(prior['source_archive'])['path']);source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md')
  consumed=[e.stat(__file__),e.stat(e.__file__),e.stat(normal.__file__),e.stat(priorpath),e.stat(source),e.stat(note),e.stat(baseline),e.bind(prior['source_archive']),e.bind(prior['source_capture']),*objects];OUT.mkdir();generated=OUT/'effective_partial_core_r1.cpp';generated.write_text(revised,encoding='utf-8',newline='\n');diff=OUT/'effective_partial_vs_causal_r1.diff';diff.write_text(''.join(difflib.unified_diff(previous.splitlines(keepends=True),revised.splitlines(keepends=True),fromfile='sealed/causal_core_r1.cpp',tofile='generated/effective_partial_core_r1.cpp',n=3)),encoding='utf-8')
  derivation=OUT/'core_derivation.json';e.save(derivation,dict(baseline_normal_reader_build=e.stat(priorpath),baseline_core=e.stat(baseline),generated_core=e.stat(generated),diff=e.stat(diff),declared_replacements=[dict(before=x,after=y,count=1) for x,y in REPLACEMENTS],reverse_normalization_equal=True,original_core_lines61_to99_literal_unchanged=True,original_Planned_function_unchanged=True,original_plan_samples=90,original_plan_end=4360000,actual_saved_samples=51,actual_last_saved_completed_step=4204000,RuntimeCSV_called=False,source_PRE_and22_numeric_guards_unchanged=True,original_numerical_budgets_changed=False));consumed += [e.stat(generated),e.stat(diff),e.stat(derivation)];headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     target=headers/Path(item.filename).name;e.need(not target.exists(),'Duplicate archived header leaf');target.write_bytes(z.read(item))
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);e.need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));e.need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08ASEffectivePartial_win64.exe';ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)];la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[v['path'] for v in objects]]
  calls.append(e.invoke(TAG+'.compile',ca,OUT,env));calls.append(e.invoke(TAG+'.link',la,OUT,env));e.need(all(e.stat(v['path'])==v for v in consumed),'Consumed closed utility/source changed');e.save(check,dict(stage=TAG+'.build',passed=True,program=e.stat(exe),source=e.stat(source),generated_core=e.stat(generated),core_diff=e.stat(diff),core_derivation=e.stat(derivation),source_build=prior['source_build'],source_capture=prior['source_capture'],source_archive=prior['source_archive'],objects=objects,calls=calls,consumed=consumed,consumed_stats_unchanged=True,actual_link_objects=7,JSph_objects_linked=False,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0));print('EFFECTIVE_PARTIAL_READER_BUILD_PASSED',exe,flush=True)
 except Exception as error:
  if not check.exists():e.save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=consumed,SHA_scans=0))
  raise
if __name__=='__main__':main()
