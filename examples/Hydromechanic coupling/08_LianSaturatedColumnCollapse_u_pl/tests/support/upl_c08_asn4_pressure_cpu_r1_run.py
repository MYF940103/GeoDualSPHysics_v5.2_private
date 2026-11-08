"""One owned330-evaluation CPU component invocation; never solver/GenCase/native/VTK."""
import argparse,csv,math,struct,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_asn4_pressure_cpu_r1_build as b
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
   for part in (64,):f.seek(12+part*stride);need(f.read(8)==struct.pack('<d',float(clocks[part]['time_s'])),'Selected native timestamp differs')
  xml=Path(r['input_xml']['path']);root=ET.parse(xml).getroot();params={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')}
  need(all(float(params[k])==v for k,v in dict(ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=4,DtFixed=.0000025,TimeMax=10.9,TimeOut=.01).items()),'Existing n4 input parameters differ');gp=root.find('execution/special/gravitypreload');need(gp is not None and gp.get('keep_bed_overlap')=='true' and Path(gp.get('statefile')).samefile(r['source_pre_file']['path']),'Existing certified PRE/keep5 input differs')
  seed=xml.with_suffix('');need({Path(e['path']).resolve() for e in r['seed']}=={Path(str(seed)+suffix).resolve() for suffix in ('.xml','.bi4','_Normals.nbi4')},'Actual generated n4 seed/normal companions differ')
  prior=L/'upl_c08_asn4_zero_cpu_r2.check.json';proof=read(prior);need(proof['passed'] and proof['consumed_stats_unchanged'] and proof['evaluations']==4 and proof['actual_physical_steps']==0 and proof['source_n4_native']==stat(npth),'Actual passed r2 zero-step predecessor required')
  before += [stat(prior),bind(proof['component_build']),bind(proof['actual_call']),bind(proof['component_completion'])];reference=next(e for e in proof['files'] if Path(e['path']).name=='receivers.csv');before.append(bind(reference));reference_rows=table(reference['path'])
  oldrows={exp:[q for q in reference_rows if int(q['part'])==64 and float(q['AS_exp'])==exp] for exp in (4,3)};selected=[int(q['native_id']) for q in oldrows[4]];need(len(selected)==41 and len(set(selected))==41 and {7013,7015,6963,7014}<=set(selected) and selected==[int(q['native_id']) for q in oldrows[3]],'Exactly the existing part64 Select41 order required');base_p={int(q['native_id']):float(q['p_Pa']) for q in oldrows[4]};need(all(p<-32. for p in base_p.values()),'The declared perturbations must remain negative')
  for p in psutil.process_iter(['pid','exe']):
   try:need(not p.info['exe'] or Path(p.info['exe']).resolve()!=PROGRAM.resolve(),'Existing active helper protected')
   except (psutil.NoSuchProcess,psutil.AccessDenied):pass
  argv=[str(PROGRAM),'--check','--snapshot',str(NATIVE),'-cpu','-ompthreads:1','-stable','-svres','-mdbc_freeslip:1',str(seed),str(OUT)]
  call=b.invoke(TAG+'.run',argv,HELPER);done=read(OUT/'completion.json')
  expected=dict(source_part=64,source_completed_step=4260000,native_IDs=6805,soil=5000,fixed=1805,actual_ct_calls=330,actual_Darcy_calls=330,baseline_calls=2,central_calls=328,central_column_h_groups=164,rate_rows=13530,call_rows=330,FSType_baseline_checks=1640000,physical_steps=0,material_return_calls=0)
  need(done['passed'] and done['stage']==TAG and all(done[k]==v for k,v in expected.items()) and done['AS_exponents']==[4,3] and done['requested_h_Pa']==[16,32] and done['selected_native_IDs']==selected and struct.pack('<d',done['source_time_s'])==struct.pack('<d',float(clocks[64]['time_s'])) and done['all5000_soil_primary_bits_match_explicit_incoming_state'] and done['only_selected_float_pressure_perturbed'] and done['actual_float_pressure_deltas_exported'] and done['wall_state_C_Ace_rebuilt_each_call'] and done['actual_seed_PRE_handoff_and_keep5_release'] and done['five_term_sum_is_test_side_shadow'] and done['outside_soil_pressure_perturbations_held_zero'] and done['finite_difference_responses_not_analytic_AD'] and done['finite_difference_convergence_not_yet_analyzed'] and not done['full_coupled_spectrum_claimed'] and not done['original_GPU_rate_or_unsaved_stage_replay'] and not done['physical_acceptance'] and done['max_rate_shadow_budget_fraction']<=1,'Actual330-call conditional-pressure component completion differs')
  calls=table(OUT/'calls.csv');rates=table(OUT/'rates.csv');need(len(calls)==330 and len(rates)==13530,'Exact330/13530 output extents required')
  call_header='evaluation,part,time_s,tau_s,completed_step,AS_exp,kind,column_native_id,requested_h_Pa,sign,base_column_p_Pa,actual_column_p_Pa,actual_column_delta_Pa,base_column_float_bits,actual_column_float_bits,soil,selected,FS_baseline_changed,saved_FS_changed,max_actual_rate_abs_Pa_s,max_shadow_budget_fraction,primary_bits_unchanged'.split(',')
  rate_header='evaluation,AS_exp,kind,column_native_id,requested_h_Pa,sign,actual_column_delta_Pa,row_native_id,x,z,p_Pa,J,n,theta,actual_FS,Ace_x,Ace_z,actual_rate_Pa_s,compression_Pa_s,LP_Pa_s,defect_Pa_s,divAce_Pa_s,chain_Pa_s,shadow_sum_Pa_s,shadow_budget_Pa_s'.split(',')
  need(list(calls[0])==call_header and list(rates[0])==rate_header,'Literal call/rate field schema differs');by_eval={k:[] for k in range(1,331)}
  for row in rates:
   index=int(row['evaluation']);need(index in by_eval and all(math.isfinite(float(row[k])) for k in rate_header if k!='kind'),'Unknown/nonfinite rate row');by_eval[index].append(row)
  f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0];bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0];groups={};baselines={};baseline_FS={}
  for index,q in enumerate(calls,1):
   exp=float(q['AS_exp']);column=int(q['column_native_id']);h=int(q['requested_h_Pa']);sign=int(q['sign']);baseline=q['kind']=='baseline';rr=by_eval[index]
   need(int(q['evaluation'])==index and int(q['part'])==64 and int(q['completed_step'])==4260000 and struct.pack('<d',float(q['time_s']))==struct.pack('<d',float(clocks[64]['time_s'])) and struct.pack('<d',float(q['tau_s']))==struct.pack('<d',float(clocks[64]['time_s'])-d['source_actual_time_s']) and exp in (4,3) and int(q['soil'])==5000 and int(q['selected'])==41 and int(q['FS_baseline_changed'])==0 and q['primary_bits_unchanged']=='1' and math.isfinite(float(q['max_actual_rate_abs_Pa_s'])) and float(q['max_shadow_budget_fraction'])<=1 and [int(z['row_native_id']) for z in rr]==selected,'Actual call/41-row/FS/clock/isolation identity differs')
   if baseline:
    need(exp not in baselines and column==-1 and h==sign==0 and q['base_column_p_Pa']==q['actual_column_p_Pa']==q['base_column_float_bits']==q['actual_column_float_bits']=='' and float(q['actual_column_delta_Pa'])==0,'Baseline fields/applicability differ');baselines[exp]=index;baseline_FS[exp]={int(z['row_native_id']):int(z['actual_FS']) for z in rr};delta=0.
   else:
    need(q['kind']=='central' and exp in baselines and column in selected and h in (16,32) and sign in (1,-1),'Unplanned pressure column/h/sign');original=base_p[column];actual=f32(original+sign*h);delta=actual-original
    need(float(q['base_column_p_Pa'])==original and float(q['actual_column_p_Pa'])==actual and actual<0 and sign*delta>0 and float(q['actual_column_delta_Pa'])==delta and int(q['base_column_float_bits'])==bits(original) and int(q['actual_column_float_bits'])==bits(actual),'Actual float perturbation/pressure bits differ');key=(exp,column,h);groups.setdefault(key,[]).append(sign)
   for z in rr:
    identity=int(z['row_native_id']);expected_p=f32(base_p[identity]+sign*h) if not baseline and identity==column else base_p[identity]
    need(float(z['AS_exp'])==exp and z['kind']==q['kind'] and int(z['column_native_id'])==column and int(z['requested_h_Pa'])==h and int(z['sign'])==sign and float(z['actual_column_delta_Pa'])==delta and bits(float(z['p_Pa']))==bits(expected_p) and int(z['actual_FS'])==baseline_FS[exp][identity] and float(z['shadow_budget_Pa_s'])>0 and abs(float(z['actual_rate_Pa_s'])-float(z['shadow_sum_Pa_s']))<=float(z['shadow_budget_Pa_s']),'Rate-row call link/sole pressure change/finite arithmetic budget differs')
  need(set(baselines)=={4.,3.} and len(groups)==164 and all(sorted(v)==[-1,1] for v in groups.values()) and all(sum(float(q['AS_exp'])==exp for q in calls)==165 for exp in (4,3)),'Exact2 baselines +328 signs /164 column-h pairs required; no dropped columns')
  need(all(stat(e['path'])==e for e in before),'Consumed input/runtime/header changed');files=[stat(OUT/q) for q in ('completion.json','rates.csv','calls.csv','Run.out')]
  save(check,dict(stage=TAG,passed=True,component_build=stat(bp),prior_zero_step=stat(prior),source_n4_run=stat(runpath),source_n4_native=stat(npth),actual_call=call,component_completion=stat(OUT/'completion.json'),force_evaluations=330,selected_soil_pressure_rows_and_columns=41,central_column_h_groups=164,finite_difference_steps_Pa=[16,32],actual_float_deltas_preserved=True,finite_difference_convergence_or_spectrum_analyzed=False,actual_physical_steps=0,solver_invocations=0,GenCase_invocations=0,native_decodes=0,VTK_invocations=0,full_coupled_stability_claimed=False,physical_acceptance=False,consumed=before,consumed_stats_unchanged=True,files=files,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG,passed=False,first_failure=str(e),actual_call=call,consumed=before,solver_invocations=0,GenCase_invocations=0,native_decodes=0,SHA_scans=0))
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reads and authorizes one component invocation');run()
