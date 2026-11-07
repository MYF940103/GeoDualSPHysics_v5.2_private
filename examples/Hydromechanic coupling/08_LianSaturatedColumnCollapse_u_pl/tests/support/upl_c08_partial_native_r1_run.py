"""Read this original failed C08 saved prefix once. No solver, restart, edits or success receipt fiction."""
import argparse,csv,json,shutil,struct
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as old
from upl_c08_resume_native_r1_run import check_input
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_partial_native_r1';OUT=T/'outputs'/TAG
FAILED=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r3_GPU_out';PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
RUN=L/'upl_c08_formal_psi0_r1.run.json';CALL=L/'upl_c08_formal_psi0_r1.call.json';STATUS=L/'upl_c08_formal_psi0_r1.status.json'
SHORT=T/'outputs/upl_c08_resume_r1_psi0_GPU_short_native_r1';SHORTCHECK=L/'upl_c08_resume_r1_psi0_GPU_short_native_r1.check.json'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def common_prefix():
    stride=8+6800*212;binary_equal=[]
    with (OUT/'typed22.bin').open('rb') as a,(SHORT/'typed22.bin').open('rb') as b:
        ha=struct.unpack('<III',a.read(12));hb=struct.unpack('<III',b.read(12));need(ha==(6800,22,11) and hb==(6800,22,10),'Original actual partial/short headers differ')
        for part in range(10):
            x,y=a.read(stride),b.read(stride);need(len(x)==len(y)==stride,'Incomplete actual common binary record');binary_equal.append(x==y)
        need(len(a.read(stride))==stride and a.read(1)==b'' and b.read(1)==b'','Original11/10 actual record counts differ')
    a=(OUT/'clocks.csv').read_bytes().splitlines(keepends=True);b=(SHORT/'clocks.csv').read_bytes().splitlines(keepends=True)
    need(len(a)==12 and len(b)==11,'Original clock CSV record count differs')
    # Header +10 real records. The partial record11 remains unmodified and is not a prefix pair.
    clock_equal=[a[i]==b[i] for i in range(11)]
    return dict(actual_common_records=10,typed_arrays_per_record=22,binary_record_bytes=stride,binary_time_and_all22_bytes_equal_by_part=binary_equal,signed_clock_header_and_10_rows_bytes_equal=clock_equal,actual_original_headers=[list(ha),list(hb)],header_count_rewritten=False,partial_extra_record_not_compared_as_prefix=True,passed=all(binary_equal) and all(clock_equal))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read and explicit single-reader authorization required');check=L/(TAG+'.check.json');need(not OUT.exists() and not check.exists(),'Existing/partial diagnostic protected')
    consumed=[];call=None;result=dict(stage=TAG,passed=False,diagnostic_partial=True,runtime_success_claimed=False,failure_stage_reproduced=False,unsaved_failure_time_known=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0,physical_acceptance=False)
    try:
        r,c,status=read(RUN),read(CALL),read(STATUS);need(not r['passed'] and r['actual_exit']==r['actual_Win32_exit']==1 and not r['solver_completed'] and r['consumed_stats_unchanged'],'Original failure owner was not sealed as expected')
        need(c['actual_wrapper_Popen_wait_exit']==c['actual_wrapper_Win32_exit']==1 and c['ownership_errors']==[],'Original wrapper exit/ownership differs');solvers=[x for x in c['children'] if x['role']=='solver'];gens=[x for x in c['children'] if x['role']=='GenCase']
        need(len(solvers)==len(gens)==1 and solvers[0]['actual_Win32_exit']==1 and gens[0]['actual_Win32_exit']==0 and r['owned_children']==c['children'],'Original actual solver/GenCase handle evidence differs')
        need(status['state']=='terminal_failure' and not status['owned_wrapper_alive'] and all(not x['owned_alive'] for x in status['children']),'Original status is not terminal')
        need(Path(r['output']).samefile(FAILED) and Path(r['source_pre_file']['path']).samefile(PRE),'Failed output/PRE identity differs');text=(FAILED/'Run.out').read_text(encoding='utf-8-sig')
        need('Finished execution (code=1).' in text and 'GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.' in text,'Original failure first cause differs')
        data=FAILED/'data';parts=sorted(data.glob('Part_*.bi4'));need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(11)],'Original eleven saved files differ');need(not (FAILED/'Run.csv').exists(),'Unexpected success summary present; diagnose instead of relabeling this source')
        bp=L/(TAG+'.build.json');b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Closed six-utility-object reader build required');sc=read(SHORTCHECK);need(sc['passed'] and sc['original_native_guards_passed'] and sc['consumed_stats_unchanged'],'Retained exact short control not admitted')
        xml=FAILED/'CaseLianSaturatedColumnCollapse_psi0_shared_r3.xml';check_input(xml,PRE);normals=FAILED/'CfgInit_NormalsGhost.vtk'
        consumed=[stat(p) for p in (RUN,CALL,STATUS,bp,SHORTCHECK,Path(__file__),Path(old.__file__),T/'support/upl_c08_resume_native_r1_run.py',T/'notes'/(TAG+'.md'),FAILED/'Run.out',xml,normals,PRE,PRE.parent/'Part_Head.ibi4',data/'Part_Head.ibi4',*parts)]
        consumed += [bind(e) for e in (r['program'],r['source_build'],r['source_pre_file'],b['program'],b['source'],b['source_capture'],b['source_archive'])]
        consumed += [bind(e) for e in r['consumed']]+[stat(SHORT/p) for p in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json')]
        exe=Path(b['program']['path']);need(not any(q.info['exe'] and Path(q.info['exe']).resolve()==exe for q in psutil.process_iter(['exe'])),'This exact reader is already active')
        result['decoder_invocations']=1;call=invoke(TAG+'.reader',[str(exe),'--read','psi0','GPU',str(data),str(PRE),'4044000',str(OUT)],T);d=read(OUT/'completion.json')
        need(d['passed'] and d['stage']==TAG and d['diagnostic_partial'] and not d['runtime_success_claimed'] and not d['failure_stage_reproduced'] and not d['unsaved_failure_time_known'],'Partial saved-state completion scope differs')
        expected=dict(samples=11,completed_steps=4044000,last_saved_zero_based_step=4043999,typed_arrays=22,actual_native_IDs_per_frame=6800,soil_IDs=5000,ledger_checks=55000,fixed_marker_checks=19800,P0_bits_checks=74800,rho_cache_bits_checks=55000,kappa_nondecreasing_from_PRE_checks=55000,nonempty_signed_intervals=11)
        need(all(d[k]==v for k,v in expected.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original native saved-state safety/coverage failed')
        copy=OUT/normals.name;shutil.copy2(normals,copy);need(normals.read_bytes()==copy.read_bytes(),'Actual initial normals copy changed');prefix=common_prefix();save(OUT/'common_short_prefix.json',prefix)
        need(all(stat(e['path'])==e for e in consumed),'Consumed failed source/program/control changed')
        result.update(passed=prefix['passed'],original_saved_native_guards_passed=True,actual_saved_end_s=d['actual_end_s'],last_saved_zero_based_step=4043999,last_saved_completed_step=4044000,reader_call=call,native_completion=stat(OUT/'completion.json'),actual_completion=d,source_normals=stat(normals),copied_initial_normals=stat(copy),normals_are_not_FSNormal=True,common_short_prefix=prefix,files=[stat(p) for p in sorted(OUT.iterdir()) if p.is_file()],consumed=consumed,consumed_stats_unchanged=True)
        if not prefix['passed']:result['first_failure']='The actual ten-record common binary/signed-clock prefix differs; inspect the exported data without rerunning the reader.'
    except Exception as e:result.update(first_failure=str(e),reader_call=call,consumed=consumed)
    save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'),runtime_success_claimed=False)),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
