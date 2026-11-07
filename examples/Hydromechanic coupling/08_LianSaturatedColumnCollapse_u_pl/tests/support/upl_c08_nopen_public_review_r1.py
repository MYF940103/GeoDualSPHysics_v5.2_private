"""Finish the one public-program regression using actual r4 postprocessing, then exact native comparison."""
import argparse,json,sys
from pathlib import Path
import mdbc_partition_components_r3 as evidence
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_nopen_public_review_r1'
OUT=T/'outputs/upl_c08_nopen_public_reg_r1';OLD=T/'outputs/upl_c08_nopen_native_r1'
need,read,stat,bind,save,invoke=evidence.need,evidence.read,evidence.stat,evidence.bind,evidence.save,evidence.invoke
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root-reviewed regression completion only')
    check=L/(TAG+'.check.json');need(not check.exists(),'Existing review protected');result=dict(stage=TAG,passed=False,solver_invocations=0,physical_acceptance=False,SHA_scans=0);consumed=[];call=None
    try:
        rp=L/'upl_c08_nopen_public_reg_r1.run.json';r=read(rp);oldcheck=L/'upl_c08_nopen_native_r1.check.json';o=read(oldcheck)
        need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_GlobalStep']==4060000 and r['saved_frames']==15 and r['consumed_stats_unchanged'],'Actual public solver regression did not pass')
        need(o['passed'] and o['original_native_guards_passed'] and o['consumed_stats_unchanged'],'Retained isolated NoPen control was not admitted')
        cp=L/'upl_c08_nopen_public_reg_r1.call.json';c=read(cp);need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0 and c['ownership_errors']==[],'Actual solver owned exits differ')
        pre=Path(bind(r['actual_PRE'])['path']);script=C/'support/postprocess_lian_collapse_r4.py';consumed=[stat(p) for p in (Path(__file__),rp,oldcheck,cp,script,OLD/'typed22.bin',OLD/'typed22_layout.csv',OLD/'clocks.csv')]+[bind(e) for e in r['consumed']]+[bind(e) for e in r['PARTs']]
        need(not (OUT/'postprocess_r4.json').exists() and not (OUT/'native').exists(),'Existing/partial r4 postprocessing must be reviewed, not repeated')
        call=invoke(TAG+'.postprocess',[sys.executable,'-X','utf8','-B',str(script),'--group','psi0','--outdir',str(OUT),'--source-pre',str(pre),'--figdir',str(T/'figures/upl_c08_nopen_public_reg_r1')],C)
        post=read(OUT/'postprocess_r4.json');native=OUT/'native';d=read(native/'completion.json')
        need(post['passed'] and post['global_steps']==4060000 and post['PartFluid'] and post['PartBound'],'Actual r4 full postprocessing did not pass')
        need(d['passed'] and d['stage']=='c08_post_native_r4' and d['DynamicNoPenetrationActive'] and d['DynamicNoPenetrationPolicy']=='LegacyOperatorSplitReleaseOnly' and not d['DynamicNoPenetrationReactionClosed'],'New NoPen policy not proven by native data')
        need(d['samples']==15 and d['actual_native_IDs_per_frame']==6800 and d['typed_arrays']==22 and d['ledger_checks']==75000 and d['P0_bits_checks']==102000 and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14,'Original native coverage/safety differs')
        pairs=[]
        for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
            eq=(native/leaf).read_bytes()==(OLD/leaf).read_bytes();pairs.append(dict(file=leaf,actual_new=stat(native/leaf),retained=stat(OLD/leaf),byte_exact=eq));need(eq,'Public program changed original NoPen trajectory or signed clock: '+leaf)
        need(all(stat(e['path'])==e for e in consumed),'Input/control/program changed during public review')
        result.update(passed=True,actual_postprocess_call=call,actual_public_end_s=d['actual_end_s'],all15_time_and22_arrays_byte_exact=True,all_signed_clocks_byte_exact=True,native_policy_changed_as_declared_not_compared_as_raw_BI4=True,comparison=pairs,native_completion=stat(native/'completion.json'),postprocess=stat(OUT/'postprocess_r4.json'),separate_PartFluid_and_PartBound=True,consumed_stats_unchanged=True)
    except Exception as e:result.update(first_failure=str(e),actual_postprocess_call=call)
    result['consumed']=consumed;save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
