"""Decode one sealed AS/fixed-plane job through the metadata adapter; no automatic follow-on."""
import argparse,json,os
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as e
from upl_c08_asplane_run_r1 import SPECS,PRE,POLICY,check_input
T=Path(__file__).resolve().parents[1];L=T/'logs'
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root-reviewed single adapter read required')
    stem,conf,backend,nopen,ason,updates,cadence,end,tout,memcheck=SPECS[a.action];tag='upl_c08_asplane_'+stem+'_r1';out=T/'outputs'/tag;native=out/'native';receipt=L/(tag+'.native.json')
    e.need(not native.exists() and not receipt.exists() and not (L/(tag+'.native.call.json')).exists() and not (L/(tag+'.native.log')).exists(),'Existing/partial native work protected');before=[];actual=None;result=dict(stage=tag,passed=False,expected_AS=ason,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0)
    try:
        original=L/(tag+'.run.json');adopted=L/(tag+'.adopted_run.json');rp=adopted if adopted.exists() else original;cp=L/(tag+'.call.json');sp=L/(tag+'.start.json');r,c,start=e.read(rp),e.read(cp),e.read(sp)
        if rp==adopted:
            e.need(Path(e.bind(r['original_run'])['path']).samefile(original) and not e.read(original)['passed'],'Adopted run must preserve/bind the original failed owner');result['adopted_run_used']=True
        else:result['adopted_run_used']=False
        e.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'] and r['actual_steps']==4000000+updates and r['saved_frames']==updates//cadence and r['ArtificialStress']==ason and r['policy']==POLICY,'Sealed actual AS/fixed-plane solver required')
        e.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and c['ownership_errors']==[] and start['actual_outer']==c['actual_outer'],'Actual solver/tool/start ownership/exit differs')
        admission=Path(e.bind(c['admission'])['path']);ad=e.read(admission);e.need(c['admission']==start['admission'] and c['arguments']==ad['argv'] and c['actual_solver']['argv']==ad['solver_argv'] and c['actual_outer']['parent_pid']==start['owner']['pid'] and ad['owner']==start['owner'],'Original actual owner admission/argv differs')
        e.need(Path(c['actual_solver']['exe']).samefile(r['program']['path']) and Path(ad['program']['path']).samefile(r['program']['path']) and ad['ArtificialStress']==ason and ad['planned_global_end']==4000000+updates and ad['expected_saved_frames']==updates//cadence and ad['policy']==POLICY,'Executed target/program/declared window differs')
        if memcheck:
            target=L/(tag+'.target.json');e.need(e.read(target)['actual_solver']==c['actual_solver'] and r['memcheck_zero_errors_and_leaks'],'Actual sanitizer target/zero-error closure missing')
        else:e.need(start['actual_solver']==c['actual_solver']==c['actual_outer'],'Direct target identity differs')
        check_input(Path(r['input_xml']['path']),end,tout,nopen,ason);plan=out/'planned_steps.csv';e.need(Path(e.bind(ad['planned_steps'])['path']).samefile(plan) and Path(e.bind(ad['source_pre_file'])['path']).samefile(PRE),'Original source/plan binding differs')
        solverbuild=e.read(r['source_build']['path']);e.need(solverbuild['passed'] and solverbuild['actual_typed_exit_code']==solverbuild['actual_Win32_exit']==0 and (r['program']['bytes'],r['program']['mtime_ns'])==(solverbuild['program']['bytes'],solverbuild['program']['mtime_ns']),'Actual program differs from its corresponding build')
        bp=L/'upl_c08_as_plane_native_r2.build.json';b=e.read(bp);e.need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Closed adapter/six-utility build required');program=Path(e.bind(b['program'])['path'])
        for q in psutil.process_iter(['exe']):
            if q.info['exe']:e.need(os.path.normcase(os.path.abspath(q.info['exe'])) not in (os.path.normcase(str(program)),os.path.normcase(r['program']['path'])),'Exact reader/original target is still active; no process stopped')
        before=[e.stat(x) for x in (Path(__file__),T/'support/upl_c08_asplane_run_r1.py',T/'notes/upl_c08_as_plane_native_r2_run.md',rp,original,cp,sp,admission,bp,plan,PRE,PRE.parent/'Part_Head.ibi4')]+r['consumed']+[r['Run_out'],r['Run_csv'],r['program'],r['source_build'],r['input_xml'],r['source_pre_file'],*r['PARTs']]+b['consumed']+[b['program']]
        if memcheck:before += [e.stat(target),r['memcheck_log']]
        e.need(all(e.stat(x['path'])==x for x in before),'Consumed source/build/runtime/input/output binding changed')
        result['decoder_invocations']=1;actual=e.invoke(tag+'.native',[str(program),'--read','psi0',backend,str(out/'data'),str(PRE),str(4000000+updates),str(updates//cadence),'1',str(plan),str(int(ason)),str(native)],T.parent)
        d,m=e.read(native/'completion.json'),e.read(native/'AS_metadata.json');samples=updates//cadence
        e.need(d['passed'] and d['stage']=='upl_c08_plane_native_r1' and d['samples']==samples and d['completed_steps']==4000000+updates and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6800 and d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']==POLICY and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'],'Core coverage/policy differs')
        counts=dict(ledger_checks=5000*samples,fixed_marker_checks=1800*samples,P0_bits_checks=6800*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples,plane_gap_checks=10000*samples)
        e.need(all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original all-sample native safety/coverage differs')
        e.need(m['passed'] and m['stage']=='upl_c08_as_plane_native_r2' and m['expected_AS']==ason and m['NoPenOn_required'] and m['samples']==samples and m['completed_steps']==4000000+updates and m['metadata_header_scans']==samples and m['AS_active_true_headers']==(samples if ason else 0) and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['core_numerical_guards_modified'],'AS metadata adapter coverage differs')
        e.need(all(e.stat(x['path'])==x for x in before),'Consumed files changed during the unique decode');result.update(passed=True,actual_call=actual,source_run=e.stat(rp),original_run=e.stat(original),completion=e.stat(native/'completion.json'),AS_metadata=e.stat(native/'AS_metadata.json'),original_native_guards_passed=True,consumed_stats_unchanged=True,outputs=[e.stat(p) for p in sorted(native.iterdir()) if p.is_file()])
    except Exception as error:
        cp=L/(tag+'.native.call.json');result.update(first_failure=str(error),actual_call=e.stat(cp) if cp.exists() else actual)
    result['consumed']=before;e.save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
