"""Read one completed legacy-NoPen bounded result once. No solver or notification."""
import argparse, json
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as evidence
from upl_c08_resume_native_r1_run import check_input
T=Path(__file__).resolve().parents[1]; C=T.parent; L=T/'logs'; TAG='upl_c08_nopen_native_r1'
OUT=T/'outputs'/TAG; SOURCE=T/'outputs/upl_c08_nopen_short_r2'
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
need,read,stat,bind,save,invoke=evidence.need,evidence.read,evidence.stat,evidence.bind,evidence.save,evidence.invoke

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--execution-authorized',action='store_true'); a=ap.parse_args()
    need(a.execution_authorized,'Root full review before one independent native read')
    check=L/(TAG+'.check.json'); need(not OUT.exists() and not check.exists() and not (L/(TAG+'.reader.call.json')).exists(),'Existing complete/partial reader evidence protected')
    consumed=[]; call=None; result=dict(stage=TAG,passed=False,physical_acceptance=False,legacy_projection_only=True,solver_invocations=0,reader_invocations=0,SHA_scans=0)
    try:
        run=L/'upl_c08_nopen_short_r2.run.json'; cp=L/'upl_c08_nopen_short_r2.call.json'; rp=L/(TAG+'.build.json')
        r,c,b=read(run),read(cp),read(rp)
        need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_GlobalStep']==4060000 and r['saved_frames']==15,'Actual bounded solver did not complete safely')
        need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0 and c['ownership_errors']==[] and c['child']['argv']==c['argv'] and c['argv'][3]=='-mdbc_freeslip:1' and c['child']['parent_pid']==c['owner']['pid'],'Actual NoPen owner/CLI/exits differ')
        need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Closed utility reader build required')
        xml=Path(bind(r['actual_input'])['path']); check_input(xml,PRE)
        need(xml.parent.samefile(SOURCE) and Path(bind(r['actual_PRE'])['path']).samefile(PRE),'Actual source/input result binding differs')
        consumed=[stat(x) for x in (Path(__file__),T/'notes'/(TAG+'.md'),run,cp,rp,SOURCE/'data/Part_Head.ibi4',PRE,PRE.parent/'Part_Head.ibi4')]+[bind(x) for x in r['consumed']]+[bind(x) for x in r['PARTs']]+[bind(x) for x in (r['actual_program'],r['actual_input'],b['program'],b['source'],b['source_archive'],b['source_capture'])]
        reader=Path(b['program']['path']); need(not any(q.info['exe'] and Path(q.info['exe']).resolve()==reader for q in psutil.process_iter(['exe'])),'This exact reader is active; do not duplicate')
        result['reader_invocations']=1; call=invoke(TAG+'.reader',[str(reader),'--read','psi0','GPU',str(SOURCE/'data'),str(PRE),'4060000',str(OUT)],T)
        d=read(OUT/'completion.json'); counts=dict(samples=15,completed_steps=4060000,last_saved_zero_based_step=4059999,typed_arrays=22,actual_native_IDs_per_frame=6800,soil_IDs=5000,ledger_checks=75000,fixed_marker_checks=27000,P0_bits_checks=102000,rho_cache_bits_checks=75000,kappa_nondecreasing_from_PRE_checks=75000,nonempty_signed_intervals=15)
        need(d['passed'] and d['stage']==TAG and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original full native safety or coverage failed')
        need(all(stat(e['path'])==e for e in consumed),'Consumed program/input/native records changed')
        result.update(passed=True,original_native_guards_passed=True,actual_completion=d,native_completion=stat(OUT/'completion.json'),reader_call=call,consumed_stats_unchanged=True,files=[stat(x) for x in OUT.iterdir() if x.is_file()])
    except Exception as e: result.update(first_failure=str(e),reader_call=call)
    result['consumed']=consumed; save(check,result); print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
