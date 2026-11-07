"""Decode one explicit normal bedkeep job; keepfalse uses the frozen6800 adapter, never adaptive IDs."""
import argparse,json,os
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as e
from upl_c08_bedkeep_run_r1 import SPECS,PRE,POLICY,BED_IDS,check_input
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_bedkeep_native_r1'
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root-reviewed single normal native read required')
 stem,conf,backend,nopen,ason,keep,updates,cadence,end,tout,memcheck=SPECS[a.action];tag='upl_c08_bedkeep_'+stem+'_r1';out=T/'outputs'/tag;native=out/'native';receipt=L/(tag+'.native.json');samples=updates//cadence;active=6805 if keep else 6800;fixed=1805 if keep else 1800;retired=255 if keep else 260;kept=list(BED_IDS) if keep else []
 e.need(nopen and ason and not native.exists() and not receipt.exists() and not (L/(tag+'.native.call.json')).exists() and not (L/(tag+'.native.log')).exists(),'NoPen1 AS1 and fresh native work required');before=[];actual=None;result=dict(stage=tag,passed=False,keep_bed_overlap=keep,expected_AS=True,expected_active_native_IDs=active,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0)
 try:
  rp=L/(tag+'.run.json');cp=L/(tag+'.call.json');sp=L/(tag+'.start.json');r,c,start=e.read(rp),e.read(cp),e.read(sp)
  e.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'] and r['actual_steps']==4000000+updates and r['saved_frames']==samples and r['ArtificialStress'] and r['policy']==POLICY and r['keep_bed_overlap']==keep and r['expected_retired_wall_IDs']==retired and r['expected_kept_bed_IDs']==kept and r['expected_active_native_IDs']==active,'Sealed actual solver/explicit geometry/window required')
  e.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and c['ownership_errors']==[] and start['actual_outer']==c['actual_outer'],'Actual solver/tool/start ownership or exit differs')
  admission=Path(e.bind(c['admission'])['path']);ad=e.read(admission);e.need(c['admission']==start['admission'] and c['arguments']==ad['argv'] and c['actual_solver']['argv']==ad['solver_argv'] and c['actual_outer']['parent_pid']==start['owner']['pid'] and ad['owner']==start['owner'],'Original actual owner admission/argv differs')
  e.need(Path(c['actual_solver']['exe']).samefile(r['program']['path']) and Path(ad['program']['path']).samefile(r['program']['path']) and ad['keep_bed_overlap']==keep and ad['expected_retired_wall_IDs']==retired and ad['expected_kept_bed_IDs']==kept and ad['expected_active_native_IDs']==active and ad['planned_global_end']==4000000+updates and ad['expected_saved_frames']==samples and ad['policy']==POLICY,'Executed target/program/explicit geometry differs')
  if memcheck:
   target=L/(tag+'.target.json');e.need(e.read(target)['actual_solver']==c['actual_solver'] and r['memcheck_zero_errors_and_leaks'],'Actual sanitizer target/zero-error closure missing')
  else:e.need(start['actual_solver']==c['actual_solver']==c['actual_outer'],'Direct target identity differs')
  check_input(Path(r['input_xml']['path']),end,tout,nopen,ason,keep);plan=out/'planned_steps.csv';e.need(Path(e.bind(ad['planned_steps'])['path']).samefile(plan) and Path(e.bind(ad['source_pre_file'])['path']).samefile(PRE),'Original source/plan binding differs')
  solverbuild=e.read(r['source_build']['path']);e.need(solverbuild['passed'] and solverbuild['actual_typed_exit_code']==solverbuild['actual_Win32_exit']==0 and (r['program']['bytes'],r['program']['mtime_ns'])==(solverbuild['program']['bytes'],solverbuild['program']['mtime_ns']),'Actual program differs from corresponding build')
  bp=L/((TAG if keep else 'upl_c08_as_plane_native_r2')+'.build.json');b=e.read(bp);e.need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Closed correct-geometry six-utility reader required');program=Path(e.bind(b['program'])['path'])
  for q in psutil.process_iter(['exe']):
   if q.info['exe']:e.need(os.path.normcase(os.path.abspath(q.info['exe'])) not in (os.path.normcase(str(program)),os.path.normcase(r['program']['path'])),'Exact reader/original solver still active; no process stopped')
  before=[e.stat(x) for x in (Path(__file__),T/'support/upl_c08_bedkeep_run_r1.py',T/'notes'/(TAG+'.md'),rp,cp,sp,admission,bp,plan,PRE,PRE.parent/'Part_Head.ibi4')]+r['consumed']+[r['Run_out'],r['Run_csv'],r['program'],r['source_build'],r['input_xml'],r['source_pre_file'],*r['PARTs']]+b['consumed']+[b['program']]
  if memcheck:before += [e.stat(target),r['memcheck_log']]
  e.need(all(e.stat(x['path'])==x for x in before),'Consumed source/build/runtime/input/output binding changed')
  argv=[str(program),'--read','psi0',backend,str(out/'data'),str(PRE),str(4000000+updates),str(samples),'1',str(plan)]
  if not keep:argv.append('1') # Explicit AS_EXPECT; frozen old6800 adapter CLI only.
  argv.append(str(native));result['decoder_invocations']=1;actual=e.invoke(tag+'.native',argv,T.parent)
  d=e.read(native/'completion.json');mp=native/('bedkeep_metadata.json' if keep else 'AS_metadata.json');m=e.read(mp)
  e.need(d['passed'] and d['stage']==(TAG if keep else 'upl_c08_plane_native_r1') and d['samples']==samples and d['completed_steps']==4000000+updates and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==active and d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']==POLICY and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['completed_runtime_Run_csv_checked'],'Core coverage/policy/normal completion differs')
  counts=dict(ledger_checks=5000*samples,fixed_marker_checks=fixed*samples,P0_bits_checks=active*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples,plane_gap_checks=10000*samples)
  e.need(all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['min_soil_x_m']>=-4e-8 and d['min_soil_z_m']>=-4e-8,'Original all-sample numerical safety/coverage differs')
  if keep:
   e.need(d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and not d['actual_retired_IDs_contiguous'] and d['kept_bed_IDs']==kept and d['kept_bed_count']==5 and d['actual_fixed_IDs']==1805 and d['kept_bed_source_geometry_checks']==5,'Explicit noncontiguous retirement/kept source geometry differs')
   e.need(m['passed'] and m['stage']==TAG+'.metadata' and m['keep_bed_overlap'] and m['original_target_count']==260 and m['actual_retired_count']==255 and m['kept_bed_IDs']==kept and m['kept_bed_count']==5 and m['keep_policy_headers']==samples and m['expected_AS'] and m['AS_policy']=='ReleaseOnly' and not m['core_original_numerical_budgets_changed'],'Keep-bed/AS typed metadata differs')
  else:e.need(d['retired_ID_begin']==1800 and d['retired_ID_count']==260 and m['passed'] and m['stage']=='upl_c08_as_plane_native_r2' and m['expected_AS'] and m['NoPenOn_required'] and not m['core_numerical_guards_modified'],'OFF must use the unchanged old6800/260-ID adapter')
  e.need(m['samples']==m['metadata_header_scans']==m['AS_active_true_headers']==samples and m['completed_steps']==4000000+updates and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'],'One metadata scan/core decode coverage differs')
  e.need(all(e.stat(x['path'])==x for x in before),'Consumed files changed during unique decode');result.update(passed=True,actual_call=actual,source_run=e.stat(rp),original_run=e.stat(rp),completion=e.stat(native/'completion.json'),AS_metadata=e.stat(mp),bedkeep_metadata=e.stat(mp) if keep else None,original_native_guards_passed=True,consumed_stats_unchanged=True,outputs=[e.stat(p) for p in sorted(native.iterdir()) if p.is_file()])
 except Exception as error:
  cp=L/(tag+'.native.call.json');result.update(first_failure=str(error),actual_call=e.stat(cp) if cp.exists() else actual)
 result['consumed']=before;e.save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
