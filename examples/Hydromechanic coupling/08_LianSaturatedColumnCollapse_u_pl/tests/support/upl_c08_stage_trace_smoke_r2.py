"""Native/review repair only: original solver and failed r1 reader-preflight remain immutable."""
import argparse,json,os,struct
from pathlib import Path
import psutil
import upl_c08_stage_trace_smoke_r1 as original
T,C,L,SPECS,base=original.T,original.C,original.L,original.SPECS,original.base
SOURCE,PRE=original.SOURCE,original.PRE
need,read,stat,bind,save,verify=original.need,original.read,original.stat,original.bind,original.save,original.verify

def normalized(path):return os.path.normcase(os.path.abspath(os.fspath(path)))
def locations(conf):
    tag,out,rp,oldnative,review=original.locations(conf)
    return tag,out,rp,L/(tag+'.native_r2.json'),review

def repair_proof(conf):
    tag=original.locations('Debug')[0];path=L/(tag+'.native.json');d=read(path)
    need(not d['passed'] and d['decoder_invocations']==0 and d['actual_call'] is None and '[WinError 2]' in d['first_failure'] and "'Registry'" in d['first_failure'],'Only the original zero-reader Registry preflight failure is repairable')
    need(not (L/(tag+'.native.call.json')).exists() and not (L/(tag+'.native.log')).exists(),'An original r1 reader invocation already exists; no duplicate')
    own=original.locations(conf)[0];prior=L/(own+'.native.json')
    if prior.exists():
        r=read(prior);need(not r['passed'] and r['decoder_invocations']==0 and r['actual_call'] is None and '[WinError 2]' in r['first_failure'] and "'Registry'" in r['first_failure'],'Current profile has a different prior native attempt')
    need(not (L/(own+'.native.call.json')).exists() and not (L/(own+'.native.log')).exists(),'Current profile has an original native invocation')
    return path

def native(conf):
    tag,out,rp,npth,review=locations(conf);updates,cadence,end,tout,memcheck=SPECS[conf];samples=updates//cadence;folder=out/'native';need(not folder.exists() and not npth.exists() and not any((L/(tag+s)).exists() for s in ('.native_r2.call.json','.native_r2.log')),'Existing/partial native work preserved')
    before=[];actual=None;result=dict(stage=tag+'.native_r2',implementation_revision=2,passed=False,solver_invocations=0,decoder_invocations=0,physical_acceptance=False,SHA_scans=0)
    try:
        repair=repair_proof(conf);r=read(rp);cp=L/(tag+'.call.json');sp=L/(tag+'.start.json');c,s=read(cp),read(sp);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==SOURCE+updates and r['saved_frames']==samples and r['consumed_stats_unchanged'],'Closed actual normal trace run required')
        need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and not c['ownership_errors'] and c['actual_outer']==s['actual_outer'],'Actual original solver/tool ownership differs')
        adpath=Path(bind(c['admission'])['path']);ad=read(adpath);need(c['admission']==s['admission'] and c['arguments']==ad['argv'] and c['actual_solver']['argv']==ad['solver_argv'] and ad['owner']==s['owner'],'Actual original admission/argv differs')
        if memcheck:need(r['memcheck_zero_errors_and_leaks'] and read(L/(tag+'.target.json'))['actual_solver']==c['actual_solver'],'Actual memcheck closure missing')
        else:need(s['actual_solver']==c['actual_solver']==c['actual_outer'],'Direct target identity differs')
        base.check_input(Path(r['input_xml']['path']),end,tout,True,True,True);plan=out/'planned_steps.csv';need(bind(ad['planned_steps'])==stat(plan),'Original planned saves changed')
        bp=L/'upl_c08_bedkeep_native_r1.build.json';b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Existing closed six-utility reader required');program=Path(bind(b['program'])['path'])
        for q in psutil.process_iter(['exe']):
            try:
                exe=q.info['exe']
                if exe and os.path.isabs(exe):need(normalized(exe) not in {normalized(program),normalized(r['program']['path'])},'Exact reader/solver still active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_trace_smoke_r2.md',Path(original.__file__),Path(base.__file__),repair,rp,cp,sp,adpath,bp,plan)]+[bind(e) for e in r['consumed']]+[bind(r[k]) for k in ('Run_out','Run_csv','program','source_build','input_xml','source_pre_file','trace_file')]+[bind(b['program'])]+[bind(e) for e in b['consumed']]
        result['decoder_invocations']=1;actual=base.invoke(tag+'.native_r2',[str(program),'--read','psi0','GPU',str(out/'data'),str(PRE),str(SOURCE+updates),str(samples),'1',str(plan),str(folder)],C)
        d=read(folder/'completion.json');m=read(folder/'bedkeep_metadata.json');counts=dict(samples=samples,completed_steps=SOURCE+updates,typed_arrays=22,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=5000*samples,fixed_marker_checks=1805*samples,P0_bits_checks=6805*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples,plane_gap_checks=10000*samples)
        need(d['passed'] and d['stage']=='upl_c08_bedkeep_native_r1' and all(d[k]==v for k,v in counts.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_launch_plan'] and d['DynamicNoPenetrationPolicy']==base.POLICY and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['min_soil_x_m']>=-4e-8 and d['min_soil_z_m']>=-4e-8 and d['kept_bed_IDs']==list(base.BED_IDS) and d['actual_retired_count']==255 and d['kept_bed_source_geometry_checks']==5,'Original22/6805/ledger/P0/FS/kappa/clock/plane guards differ')
        need(m['passed'] and m['stage']=='upl_c08_bedkeep_native_r1.metadata' and m['keep_bed_overlap'] and m['expected_AS'] and m['kept_bed_IDs']==list(base.BED_IDS) and m['actual_retired_count']==255 and m['samples']==m['metadata_header_scans']==m['keep_policy_headers']==m['AS_active_true_headers']==samples and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==struct.unpack('<f',struct.pack('<f',.2))[0] and m['AS_exponent_float_reference']==struct.unpack('<f',struct.pack('<f',2.55))[0] and m['core_array_decode_passes']==1 and not m['core_original_numerical_budgets_changed'],'Original keep/AS metadata differs')
        verify(before);result.update(passed=True,original_r1_preflight_failure=stat(repair),original_r1_decoder_invocations=0,process_inventory_method='normalized absolute exe strings; no samefile on OS pseudo paths',original_native_guards_passed=True,source_run=stat(rp),actual_call=actual,completion=stat(folder/'completion.json'),bedkeep_metadata=stat(folder/'bedkeep_metadata.json'),outputs=[stat(p) for p in sorted(folder.iterdir()) if p.is_file()],consumed_stats_unchanged=True)
    except Exception as error:
        cp=L/(tag+'.native_r2.call.json');result.update(first_failure=str(error),actual_call=stat(cp) if cp.exists() else actual)
    result['consumed']=before;save(npth,result);print(json.dumps(dict(passed=result['passed'],receipt=str(npth),first_failure=result.get('first_failure'))),flush=True);return result['passed']

def review(conf):
    tag,out,rp,npth,check=locations(conf);frames=1 if conf=='Debug' else 3;need(not check.exists(),'Existing review preserved');before=[];result=dict(stage=tag+'.review',implementation_revision=2,native_receipt=stat(npth),passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0)
    try:
        n=read(npth);need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'],'Closed new native required');before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_trace_smoke_r2.md',npth)]+[bind(e) for e in n['outputs']];new=out/'native'
        if conf=='Debug':
            old=T/'outputs/upl_c08_bedkeep_smoke_GPU_r1/native';cp=L/'upl_c08_bedkeep_smoke_GPU_r1.native.json';c=read(cp);need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'],'Retained same-dt GPU Debug native control required');before.append(stat(cp));before.extend(bind(e) for e in c['outputs']);control_samples=1
        else:
            old=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out/native';cp=old.parent/'postprocess_r5.json';c=read(cp);need(c['passed'] and c['global_steps']==5200000 and c['saved_frames']==300 and c['KeepBedOverlap'] and c['AS_policy']=='ReleaseOnly','Retained normal root r5 control required');nativecall=old.parent/'logs/native.call.json';rc=read(nativecall);need(rc['passed'] and rc['actual_exit']==rc['actual_Win32_exit']==0,'Actual old root native exit differs');before.extend((stat(cp),stat(nativecall)));before.extend(bind(next(e for e in rc['outputs'] if Path(e['path']).samefile(old/leaf))) for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv'));control_samples=300
        d=read(old/'completion.json');need(d['passed'] and d['samples']==control_samples and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22,'Actual control coverage differs');stride=8+6805*212
        with (new/'typed22.bin').open('rb') as a,(old/'typed22.bin').open('rb') as b:
            hnew=struct.unpack('<III',a.read(12));hold=struct.unpack('<III',b.read(12));need(hnew==(6805,22,frames) and hold==(6805,22,control_samples),'Original unequal-sample headers must remain real');left=a.read(frames*stride);right=b.read(frames*stride)
        need(len(left)==len(right)==frames*stride,'Actual prefix payload size differs');equal=left==right;result.update(typed22_time_payload_byte_exact=equal,first_different_payload_byte=None if equal else next(i for i,(x,y) in enumerate(zip(left,right)) if x!=y),new_header=list(hnew),control_header=list(hold),headers_rewritten=False)
        nclock=(new/'clocks.csv').read_bytes().splitlines(keepends=True);oclock=(old/'clocks.csv').read_bytes().splitlines(keepends=True);need(len(nclock)==frames+1 and len(oclock)==control_samples+1,'Actual raw clock row counts differ');clocks=nclock==oclock[:frames+1];layout=(new/'typed22_layout.csv').read_bytes()==(old/'typed22_layout.csv').read_bytes();result.update(actual_common_saved_frames=frames,typed_layout_byte_exact=layout,signed_clock_header_and_rows_byte_exact=clocks,control_directory=str(old),comparison='same-backend actual saved fields, not half-step error')
        need(equal and clocks and layout,'Trace changed original22/time/signed-clock bytes; preserve and diagnose, no retry');verify(before);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;save(check,result);print(json.dumps(dict(passed=result['passed'],receipt=str(check),first_failure=result.get('first_failure'))),flush=True);return result['passed']

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('native','review'));ap.add_argument('configuration',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one explicit reader/review action; no solver call');raise SystemExit(0 if {'native':native,'review':review}[args.action](args.configuration) else 1)
