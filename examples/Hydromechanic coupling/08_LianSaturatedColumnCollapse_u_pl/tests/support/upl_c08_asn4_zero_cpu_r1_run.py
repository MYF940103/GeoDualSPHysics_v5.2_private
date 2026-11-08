"""One owned four-evaluation CPU component invocation; never solver/GenCase/native/VTK."""
import argparse,csv,math,struct,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_asn4_zero_cpu_r1_build as b
from upl_c08_fsmask_r1 import SCHEMA,TYPES
T,L,TAG,HELPER,PROGRAM=b.T,b.L,b.TAG,b.HELPER,b.PROGRAM
OUT=T/'outputs'/TAG;JOB='upl_c08_asn4_window_GPU_r1';NATIVE=T/'outputs'/JOB/'native_partial_r1'
need,read,stat,bind,save=b.need,b.read,b.stat,b.bind,b.save

def table(path):
 with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def run():
 check=L/(TAG+'.check.json');need(not OUT.exists() and not check.exists(),'Existing complete/partial component output protected');before=[];call=None
 try:
  bp=L/(TAG+'.build.json');build=read(bp);runpath=L/(JOB+'.run.json');npth=L/(JOB+'.native_partial_r1.json');r,n=read(runpath),read(npth)
  need(build['passed'] and build['consumed_stats_unchanged'] and build['project_non_main_objects']==86 and build['actual_link_objects']==87 and build['solver_builds']==0,'Closed matching helper build required')
  before=[stat(bp),bind(build['program']),bind(build['source']),bind(build['source_build']),bind(build['runtime_r6_GPU_build']),bind(build['source_capture']),bind(build['source_archive']),*[bind(e) for e in build['frozen_headers']],*[bind(e) for e in build['runtime']],stat(runpath),stat(npth),stat(__file__),stat(b.__file__),stat(b.NOTE),stat(b.old.__file__)]
  need(not r['passed'] and not r['solver_completed'] and r['failed_stage']=='solver' and r['actual_exit']==r['actual_Win32_exit']==1 and not r['ownership_errors'] and r['consumed_stats_unchanged'] and r['ArtificialStress'] and r['ArtificialStressCoef']==.2 and r['ArtificialStressExp']==4. and r['keep_bed_overlap'] and r['expected_active_native_IDs']==6805,'Actual failed n4 runtime must remain a failure')
  need(n['passed'] and n['partial'] and not n['runtime_success_claimed'] and not n['source_run_passed'] and n['source_solver_exit']==1 and n['original_saved_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1 and not n['failure_unsaved_state_reconstructed'] and n['failure_reported_step']==4265004,'Closed unique66-save partial/native scope required')
  need(r['source_capture']==build['source_capture'] and r['source_archive']==build['source_archive'] and r['source_build']==build['runtime_r6_GPU_build'],'n4 runtime and CPU helper must have the SAME frozen source capture/archive')
  for key in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','actual_call','owner_admission'):before.append(bind(r[key]))
  before += [bind(e) for e in r['seed']]+[bind(n[k]) for k in ('completion','metadata','actual_call','source_run','original_solver_call','original_owner_admission')]
  need(Path(n['source_run']['path']).samefile(runpath) and Path(n['completion']['path']).parent.samefile(NATIVE),'Actual sealed n4 partial path differs');d=read(n['completion']['path']);meta=read(n['metadata']['path']);rc=read(n['actual_call']['path'])
  counts=dict(samples=66,completed_steps=4264000,new_updates=264000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=330000,fixed_marker_checks=119130,P0_bits_checks=449130,rho_cache_bits_checks=330000,kappa_nondecreasing_from_PRE_checks=330000,nonempty_signed_intervals=66,plane_gap_checks=660000)
  need(d['passed'] and d['stage']=='upl_c08_asn4_partial_r1' and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['partial'] and not d['runtime_success_claimed'] and d['original_planned_samples']==90 and d['original_planned_end']==4360000 and d['used_launch_plan_prefix_samples']==66 and d['saved_steps_checked_against_launch_plan'] and not d['failure_unsaved_state_reconstructed'],'Original66/22/ledger/P0/clock/signed/plane native guards differ')
  need(d['kept_bed_IDs']==[1800,1852,1904,1956,2008] and d['actual_retired_count']==255 and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'],'Actual retained IDs/boundary policy differ')
  need(meta['passed'] and meta['stage']=='upl_c08_asn4_partial_r1.metadata' and meta['samples']==meta['keep_policy_headers']==meta['AS_active_true_headers']==meta['ponding_policy_keys_absent_headers']==66 and meta['AS_policy']=='ReleaseOnly' and meta['AS_coefficient_float_reference']==struct.unpack('<f',struct.pack('<f',.2))[0] and meta['AS_exponent_float_reference']==4. and meta['expected_ponding_policy']=='CompletedOnly','Frozen AS4/keep/CompletedOnly headers differ')
  need(rc['actual_Popen_wait_exit']==rc['actual_Win32_exit']==0 and rc['ownership_failure'] is None,'Original reader actual exits differ')
  for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
   before.append(bind(next(e for e in n['outputs'] if Path(e['path']).samefile(NATIVE/leaf))))
  layout=table(NATIVE/'typed22_layout.csv');need(len(layout)==22,'Exactly22 arrays required')
  for q,(name,kind,width) in zip(layout,SCHEMA):need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Original22 native layout differs')
  stride=8+6805*212;clocks=table(NATIVE/'clocks.csv');need(len(clocks)==66 and (NATIVE/'typed22.bin').stat().st_size==12+66*stride,'Actual66 native extent differs');scalar=d['source_actual_time_s']
  for update in range(1,264001):
   scalar+=.0000025
   if update%4000==0:
    q=clocks[update//4000-1];need(int(q['completed_step'])==4000000+update and int(q['saved_step'])+1==int(q['completed_step']) and struct.pack('<d',float(q['time_s']))==struct.pack('<d',scalar) and q['dterror_interval_empty']=='0' and math.isfinite(float(q['signed_dterror_s'])) and float(q['signed_dterror_s'])<=1e-14,'Actual global clock/signed interval differs')
  with (NATIVE/'typed22.bin').open('rb') as f:
   need(struct.unpack('<III',f.read(12))==(6805,22,66),'Actual66 header differs')
   for part in (29,64):f.seek(12+part*stride);need(f.read(8)==struct.pack('<d',float(clocks[part]['time_s'])),'Selected native timestamp differs')
  xml=Path(r['input_xml']['path']);root=ET.parse(xml).getroot();params={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')}
  need(all(float(params[k])==v for k,v in dict(ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=4,DtFixed=.0000025,TimeMax=10.9,TimeOut=.01).items()),'Existing n4 input parameters differ');gp=root.find('execution/special/gravitypreload');need(gp is not None and gp.get('keep_bed_overlap')=='true' and Path(gp.get('statefile')).samefile(r['source_pre_file']['path']),'Existing certified PRE/keep5 input differs')
  seed=xml.with_suffix('');need({Path(e['path']).resolve() for e in r['seed']}=={Path(str(seed)+suffix).resolve() for suffix in ('.xml','.bi4','_Normals.nbi4')},'Actual generated n4 seed/normal companions differ')
  for p in psutil.process_iter(['pid','exe']):
   try:need(not p.info['exe'] or Path(p.info['exe']).resolve()!=PROGRAM.resolve(),'Existing active helper protected')
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  argv=[str(PROGRAM),'--check','--snapshot',str(NATIVE),'-cpu','-ompthreads:1','-stable','-mdbc_freeslip:1',str(seed),str(OUT)]
  call=b.invoke(TAG+'.run',argv,HELPER);done=read(OUT/'completion.json')
  need(done['passed'] and done['stage']==TAG and done['source_parts']==[29,64] and done['AS_exponents']==[4,3] and done['native_IDs']==6805 and done['soil']==5000 and done['fixed']==1805 and done['actual_ct_calls']==done['actual_Darcy_calls']==4 and done['physical_steps']==done['material_return_calls']==0 and done['all5000_soil_primary_bits_unchanged_each_call'] and done['actual_seed_PRE_handoff_and_keep5_release'] and done['actual_CPU_finished_Ace_used'] and done['five_term_sum_is_test_side_shadow'] and not done['original_GPU_rate_or_unsaved_stage_replay'] and not done['pressure_Jacobian_or_spectrum'] and not done['physical_acceptance'] and done['max_rate_shadow_budget_fraction']<=1,'Actual four-evaluation numerical/isolation completion differs')
  evaluations=table(OUT/'evaluations.csv');receivers=table(OUT/'receivers.csv');walls=table(OUT/'walls.csv');need(len(evaluations)==4 and len(receivers)==done['receiver_rows'] and len(walls)==done['wall_rows'],'Actual output counts differ')
  for part in (29,64):
   selected=[]
   for exp in (4,3):
    v=[q for q in evaluations if int(q['part'])==part and float(q['AS_exp'])==exp];rr=[q for q in receivers if int(q['part'])==part and float(q['AS_exp'])==exp];need(len(v)==1 and 4<=len(rr)<=81 and len(rr)==int(v[0]['selected']) and v[0]['primary_bits_unchanged']=='1' and int(v[0]['soil'])==5000,'One complete force evaluation/receiver set missing');ids={int(q['native_id']) for q in rr};need(len(ids)==len(rr) and {7013,7015,6963,7014}<=ids,'Explicit focus IDs missing');selected.append(ids)
   need(selected[0]==selected[1],'Same snapshot AS4/3 output receiver IDs differ')
  need(all(stat(e['path'])==e for e in before),'Consumed input/runtime/header changed');files=[stat(OUT/q) for q in ('completion.json','receivers.csv','walls.csv','evaluations.csv','Run.out')]
  save(check,dict(stage=TAG,passed=True,component_build=stat(bp),source_n4_run=stat(runpath),source_n4_native=stat(npth),actual_call=call,component_completion=stat(OUT/'completion.json'),evaluations=4,actual_physical_steps=0,solver_invocations=0,GenCase_invocations=0,native_decodes=0,VTK_invocations=0,pressure_spectrum_claimed=False,physical_acceptance=False,consumed=before,consumed_stats_unchanged=True,files=files,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG,passed=False,first_failure=str(e),actual_call=call,consumed=before,solver_invocations=0,GenCase_invocations=0,native_decodes=0,SHA_scans=0))
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reads and authorizes one component invocation');run()
