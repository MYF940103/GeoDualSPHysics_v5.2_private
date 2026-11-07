"""One explicit helper build or one zero-step evaluation; no solver/build/decode retry."""
import argparse,csv,os,shutil,subprocess
from pathlib import Path
import mdbc_partition_components_r3 as old
T=Path(__file__).resolve().parents[1];S=T.parents[3]/'src';L=T/'logs';TAG='upl_lian_c08_darcy_zero_cpu_r1'
CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md')
HELPER=T/'outputs/upl_lian_c08_darcy_zero_CPU_helper_r1';OUT=T/'outputs/upl_lian_c08_darcy_zero_CPU_r1'
SNAP=T/'outputs/upl_prestress10_CPU_r1_native_r1';SEED=T/'outputs/upl_c08_observer_r1_seed/CaseLianSaturatedColumnCollapse_geometry_r1'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def build():
 check=L/(TAG+'.build.json');need(not HELPER.exists() and not check.exists(),'Existing/partial helper build protected');calls=[];consumed=[]
 try:
  bp=L/'mdbc_partition_DebugCPU_r1.build.json';b=read(bp)
  need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==87,'Passed current DebugCPU87 closure required')
  objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==86,'Exactly86 non-main project objects required')
  recipe=T/'outputs/upl_noslip_cpu_component_r1';cp=L/'upl_noslip_cpu_component_r1_compile.call.json';lp=L/'upl_noslip_cpu_component_r1_link.call.json';c,l=read(cp),read(lp)
  need(c['exit_code']==l['exit_code']==0 and c['owned_call_exited'] and l['owned_call_exited'],'Closed CPU Debug CL/link recipe required')
  consumed=[stat(bp),bind(b['source_capture']),*[bind(e) for e in objects],stat(cp),stat(lp),stat(CPP),stat(NOTE),stat(__file__),stat(old.__file__)]
  source=next(x for x in c['arguments'] if x.lower().endswith('.cpp'))
  ca=[str(CPP) if x==source else x.replace(str(recipe),str(HELPER)) for x in c['arguments']]
  la=[x.replace(str(recipe),str(HELPER)).replace('upl_noslip_cpu_component_r1.exe','component.exe') for x in l['arguments'] if not x.lower().endswith('.obj')]+[str(HELPER/'helper.obj'),*[e['path'] for e in objects]]
  need(all(x in ca for x in ('/Od','/MTd','/fp:precise','/std:c++17')) and '/D_WITHGPU' not in ca and sum(x.lower().endswith('.obj') for x in la)==87,'CPU Debug flags/link closure differ')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC environment setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  HELPER.mkdir();calls.append(invoke(TAG+'.compile',[c['program'],*ca],S,env));calls.append(invoke(TAG+'.link',[l['program'],*la],S,env));runtime=[]
  for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
   origin=stat(recipe/leaf);consumed.append(origin);shutil.copy2(origin['path'],HELPER/leaf);dest=stat(HELPER/leaf);need((origin['bytes'],origin['mtime_ns'])==(dest['bytes'],dest['mtime_ns']),'Matching Debug runtime copy differs');runtime.append(dest)
  need(all(stat(e['path'])==e for e in consumed),'Build consumed input changed')
  save(check,dict(stage=TAG+'.build',passed=True,program=stat(HELPER/'component.exe'),source=stat(CPP),source_build=stat(bp),source_capture=b['source_capture'],project_non_main_objects=86,actual_link_objects=87,runtime=runtime,calls=calls,consumed=consumed,consumed_stats_unchanged=True,solver_builds=0,component_invocations=0,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=consumed,SHA_scans=0))
  raise

def run():
 check=L/(TAG+'.check.json');need(not OUT.exists() and not check.exists(),'Existing/partial zero-step output protected');consumed=[];call=None
 try:
  bp=L/(TAG+'.build.json');b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'] and b['project_non_main_objects']==86,'Closed new helper build required')
  np=L/'upl_prestress10_CPU_r1_native_r1.check.json';n=read(np);need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'],'Closed original snapshot native check required')
  consumed=[stat(bp),bind(b['program']),bind(b['source']),bind(b['source_build']),bind(b['source_capture']),*[bind(e) for e in b['runtime']],stat(np),bind(n['source_run']),bind(n['source_run_call']),bind(n['reader_call']),bind(n['native_completion']),stat(NOTE),stat(__file__),stat(old.__file__)]
  source=read(n['source_run']['path']);rc=read(n['reader_call']['path']);done=read(SNAP/'completion.json')
  need(source['passed'] and source['actual_exit']==source['actual_Win32_exit']==0 and rc['actual_Popen_wait_exit']==rc['actual_Win32_exit']==0,'Original solver/native actual exits required')
  need(done['passed'] and done['stage']=='upl_prestress10_native_r1' and done['samples']==1001 and done['completed_steps']==4000000 and done['constant_conductivity_model']==0 and done['actual_scalar_clock_verified'] and done['all22_arrays_finite_and_ID_aligned'] and done['no_exclusions'],'Original snapshot numerical scope differs')
  consumed += [stat(SNAP/leaf) for leaf in ('typed22.bin','typed22_layout.csv','native_ids.csv','clocks.csv')]+[stat(str(SEED)+suffix) for suffix in ('.xml','.bi4','_Normals.nbi4')]
  args=[b['program']['path'],'--check','--snapshot',str(SNAP),'-cpu','-ompthreads:1','-stable','-mdbc_freeslip',str(SEED),str(OUT)]
  call=invoke(TAG+'.run',args,HELPER);d=read(OUT/'completion.json')
  need(d['passed'] and d['stage']==TAG and d['native_IDs']==7060 and d['soil']==5000 and d['fixed']==2060 and d['physical_steps']==0 and d['actual_ct_calls']==1 and d['Darcy_calls']==3 and d['receiver_rows']==162,'Actual zero-step completion differs')
  need(d['restored_baseline_soil_rate_bits_exact'] and d['upstream_fields_unchanged_between_rates'] and d['constant_k'] and d['pair_symmetric_C_retained'] and d['actual_finished_Ace_not_prescribed'] and not d['original_rate_replay'] and not d['physical_accuracy_or_acceptance'],'Original isolation/qualification guards failed')
  need(d['max_rate_over_retained_roundoff_budget']<=1 and d['max_trace_identity_over_budget']<=1,'Original arithmetic budgets failed')
  with (OUT/'receivers.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
  ids={v:{int(q['native_id']) for q in rows if q['variant']==v} for v in ('Cavg_Eta2','Cavg_Eta0')};need(len(rows)==162 and len(ids['Cavg_Eta2'])==len(ids['Cavg_Eta0'])==81 and ids['Cavg_Eta2']==ids['Cavg_Eta0'],'Expected same81 receiver coverage missing')
  need(all(stat(e['path'])==e for e in consumed),'Run consumed input changed')
  save(check,dict(stage=TAG,passed=True,component_build=stat(bp),actual_call=call,native_completion=stat(OUT/'completion.json'),receiver_CSV=stat(OUT/'receivers.csv'),original_completion=d,consumed=consumed,consumed_stats_unchanged=True,physical_steps=0,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG,passed=False,first_failure=str(e),actual_call=call,consumed=consumed,solver_invocations=0,native_decodes=0,SHA_scans=0))
  raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','run'));p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root has read and authorized one explicit action');(build if a.action=='build' else run)()
if __name__=='__main__':main()
