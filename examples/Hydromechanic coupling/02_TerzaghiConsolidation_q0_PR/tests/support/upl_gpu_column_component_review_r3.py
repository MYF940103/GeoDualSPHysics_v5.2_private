"""Offline adoption/QC of one sealed r2 native component; never launches a program."""
import argparse, csv, hashlib, json, math, re, struct
from pathlib import Path

T = Path(__file__).resolve().parents[1]
BOUND = {}
EPS32, EPS64 = 2.0**-23, 2.0**-52
F32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
N0, K0, MASS, RHOW, RHO0, KW = F32(0.3), F32(0.0001), F32(0.21), 1000.0, 2100.0, 2e8
CPP_SHA = '978999d900a4088ef3b6973ee8d6d7426cdec25291e9ea0f6e5c71cdd2a20ba5'
NOTE_SHA = 'c852b27db9a512edc1028245f13e13f2910e0bc03b6b92b1e8941f189586459c'
def need(ok, message):
    if not ok: raise ValueError(message)
def entry(path):
    p = Path(path).resolve(); need(p.is_file(), 'Missing file: '+str(p))
    digest = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): digest.update(chunk)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest.hexdigest())
def bind(e):
    need(isinstance(e, dict) and set(('path','bytes','sha256')) <= e.keys(), 'Expected flat Entry')
    key = str(Path(e['path']).resolve()).casefold()
    if key not in BOUND: BOUND[key] = entry(e['path'])
    a = BOUND[key]; need(a['bytes'] == e['bytes'] and a['sha256'] == e['sha256'].lower(), 'Changed artifact: '+e['path'])
    return a
def rows_bind(rows):
    need(isinstance(rows, list), 'Expected Entry array')
    for e in rows: bind(e)
def load(e):
    return json.loads(Path(bind(e)['path']).read_text(encoding='utf-8-sig'))
def numeric(row):
    a = {k:float(v) for k,v in row.items()}; need(all(math.isfinite(v) for v in a.values()), 'Nonfinite CSV value'); return a
def csv_rows(path):
    bind(entry(path))
    with Path(path).open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def close(a, b):
    return abs(a-b) <= 256*EPS64*max(1.0, abs(b))  # Existing double-arithmetic envelope only.
def force_budget(absolute, target):
    return 64*EPS32*absolute + 256*EPS64*max(1.0, abs(target)) + 1e-6
def typed_zero(call):
    need(call.get('owned_call_exited') is True and call.get('typed_LASTEXITCODE_captured_immediately') is True and type(call.get('exit_code')) is int and call['exit_code'] == 0 and call.get('invocation_failure') is None, 'Owned typed exit0 required')

def review(run_entry, result):
    run = load(run_entry); cfg = run.get('configuration'); need(cfg in ('Debug','Release'), 'Configuration must be Debug/Release')
    result['configuration'] = cfg
    adopted = cfg == 'Debug' and Path(run_entry['path']).name == 'upl_gpu_column_component_Debug_r2.run.json' and run.get('stage') == 'upl_gpu_column_component_run_r2' and run.get('passed') is False and run.get('failure') == 'Actual-normal horizontal analytic term differs'
    normal = run.get('passed') is True and run.get('failure') is None and run.get('stage') == ('upl_gpu_column_component_run_r2' if cfg == 'Debug' else 'upl_gpu_column_component_run_r3')
    need(adopted or normal, 'Only exact Debug-r2 wrapper failure or successful current owner may be adopted')
    need(run.get('source_inputs_objects_runtime_canonical_unchanged') is True and run.get('physical_acceptance') is False and run.get('physical_solver_invoked') is False and run.get('physical_steps_advanced') == 0, 'Owner bindings/held scope required')
    rows_bind(run['inputs']); rows_bind(run['files']); call = load(run['call']); typed_zero(call); bind(call['log']); bind(call['program']); bind(call['target_program'])
    helper = load(run['helper']); build = load(run['source_build']); frozen = load(run['source_freeze'])
    need(helper.get('passed') is True and helper.get('configuration') == cfg and helper.get('kind') == 'component' and helper.get('status') == 'current_column_GPU_helper_linked_not_run' and helper.get('exact_link_closure_verified') is True and helper.get('link_object_count') == 111 and len(helper['objects']) == 110 and helper.get('source_and_protected_artifacts_unchanged') is True, 'Current111-object component helper required')
    need(build.get('passed') is True and build.get('configuration') == cfg and build.get('objects_exclude_main') is True and len(build['objects']) == 110 and build.get('source_and_protected_artifacts_unchanged') is True, 'Current110-non-main source build required')
    need(helper['source_build'] == run['source_build'] and helper['source_freeze'] == run['source_freeze'] and build['source_freeze'] == run['source_freeze'] and call['target_program'] == helper['program'], 'Native/helper/build/source attribution differs')
    for key in ('inputs','author_files','objects','tools','libraries'): rows_bind(helper[key])
    rows_bind(build['objects'])
    for e in (helper['neutral_include'],helper['program'],helper['helper_object']): bind(e)
    authors = {Path(e['path']).name:e['sha256'] for e in helper['author_files']}
    need(authors.get('upl_gpu_column_component_r2.cpp') == CPP_SHA and authors.get('upl_gpu_column_component_r2.json') == NOTE_SHA, 'Reviewed immutable r2 fixture identities required')
    for key in ('compile_call','link_call'):
        owned = load(helper[key]); typed_zero(owned); bind(owned['program']); bind(owned['log'])
    need(len(frozen['source']) == len(frozen['current_source_snapshot']) == 265 and len(frozen['canonical_programs_before']) == 7 and len(frozen['runtime_before']) == 4, 'Current265/source/canonical7/runtime4 closure required')
    for key in ('source','canonical_programs_before','runtime_before'): rows_bind(frozen[key])
    originals = []
    for pair in frozen['current_source_snapshot']+[frozen['documentation_snapshot']]:
        a,b = bind(pair['original']),bind(pair['snapshot']); need((a['bytes'],a['sha256']) == (b['bytes'],b['sha256']), 'Current snapshot pair differs'); originals.append(a)
    need(len({e['path'].casefold() for e in originals[:-1]}) == 265 and {e['path'].casefold() for e in originals[:-1]} == {str(Path(e['path']).resolve()).casefold() for e in frozen['source']}, 'Current source membership differs')
    for owner in (helper,build):
        need(len(owner['runtime']) == 4, 'Four runtime copies required')
        for pair in owner['runtime']:
            a,b = bind(pair['original']),bind(pair['copy']); need((a['bytes'],a['sha256']) == (b['bytes'],b['sha256']), 'Runtime pair differs')
    argv = call['target_arguments']; need(len(argv) == 4 and argv[0] == '--input' and argv[2] == '--out', 'Exact component CLI required')
    folder = Path(argv[3]).resolve(); need(folder.parent == T/'outputs' and Path(run['completion']['path']).resolve() == folder/'completion.json', 'Component output attribution differs')
    need(str(Path(argv[1]).resolve()).casefold() in BOUND, 'Input XML not bound by owner')
    if cfg == 'Debug':
        rawlog = Path(call['log']['path']).read_bytes()
        text = rawlog.decode('utf-16' if rawlog.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
        need(call.get('memcheck_executed') is True and call.get('memcheck_zero_errors_and_leaks') is True and run.get('memcheck_zero_errors_and_leaks') is True and re.search(r'ERROR SUMMARY:\s*0 errors',text) and re.search(r'LEAK SUMMARY:\s*0 bytes leaked in 0 allocations',text), 'Owned Debug memcheck0/0 required')
        need(call['arguments'] == ['--tool','memcheck','--leak-check','full','--error-exitcode','99',helper['program']['path']]+argv, 'Memcheck target argv differs')
    else: need(call.get('direct_target_call') is True and call['program'] == helper['program'] and call['arguments'] == argv, 'Release direct target call required')
    result.update(adopted_wrapper_failure_only=adopted, original_run_passed=run['passed'], original_run_failure=run.get('failure'), memcheck_executed=(cfg=='Debug'), memcheck_zero_errors_and_leaks=(cfg=='Debug'), call=run['call'], completion=run['completion'], helper=run['helper'], source_build=run['source_build'], source_freeze=run['source_freeze'], files=run['files'])
    done = load(run['completion']); counts = dict(native_count=1000,fixed_count=40,actual_force_calls=5,explicit_complete_rate_calls=15,rate_rows=12000,affine_summary_rows=12,load_rows=4000,load_summary_rows=4,pressure_API_calls=4,normal_exact_method_rejections=2,bad_owner_invalid_index_rejections=1)
    need(done.get('passed') is True and done.get('stage') == 'upl_gpu_column_component_r2' and all(done.get(k)==v for k,v in counts.items()) and done.get('named_scratch_restores') == 8 and done.get('periodic_owner_checks',0)>0 and done.get('public_master') == 0 and done.get('physical_acceptance') is False and done.get('physical_steps_advanced') == 0 and done.get('host_PreCorr_or_Run_or_ComputeStep_or_SaveData_called') is False and done.get('actualRun_initial_field_overwritten') is False, 'Native completion coverage/scope differs')
    listed = {str(Path(e['path']).resolve()).casefold() for e in run['files']}; names = ('rates.csv','affine.csv','loads.csv','load_summary.csv','probes.csv')
    need(all(str((folder/n).resolve()).casefold() in listed for n in names+('completion.json','Run.out')), 'Native outputs not sealed by owner')
    rates,affine,loads,summary,probes = [csv_rows(folder/n) for n in names]; need([len(x) for x in (rates,affine,loads,summary,probes)] == [12000,12,4000,4,4], 'Exact CSV counts differ')
    rates = [numeric(r) for r in rates]; groups={}; base={}; first_top=None
    for i,r in enumerate(rates):
        f,v,ident = i//3000,(i//1000)%3,40+i%1000; need((r['field'],r['normal_variant'],r['id']) == (f,v,ident), 'Rate field/variant/ID order differs')
        a,b = r['actual_rate'],r['budget']; key=(f,ident); raw_budget=64*EPS32*r['raw_abs_rate']+(256*EPS64+1e-6); need(b>0 and r['old_budget']>0 and r['raw_abs_rate']>=0 and close(b,raw_budget), 'Original raw-term budget differs')
        if v==0: base[key]=(a,b)
        ib=max(base[key][1],b); ie=abs(a-base[key][0]); error=abs(a-r['independent_rate']); signal=abs(a-r['old_rate'])/max(b,r['old_budget']); upper=r['z']>0.5; surface=r['FSType'] in (2,3)
        expected3=0.0
        if f==3 and upper and surface:
            nx,ny,nz=r['Normal_x'],r['Normal_y'],r['Normal_z']; norm=nx*nx+ny*ny+nz*nz; need(norm>0,'Invalid actual normal'); dot=nx*r['Lx_x']+ny*r['Lx_y']+nz*r['Lx_z']; expected3=(KW/N0)*K0/(RHOW*9.80665)*RHOW*nx*dot/norm
        expected=expected3 if f==3 and upper else (0.0 if upper and f in (0,2) else r['independent_rate'])
        need(error<=b and abs(r['expectationResidual'])<=b and abs(a-expected)<=b and ie<=ib and 0<=r['invariance_error']<=r['invariance_budget'] and close(ie,r['invariance_error']) and close(ib,r['invariance_budget']) and close(error/b,r['error_ratio']) and close(signal,r['signal_ratio']) and abs(r['analyticField3']-expected3)<=b and abs(r['expectationResidual']-(a-expected))<=b, 'Original rate/expectation/invariance budget rejected')
        if upper and f==2 and surface: need(r['Normal_x']==r['Normal_y']==0,'Exact-plane scratch normal differs')
        if upper and f==3: need(r['Gp_x']==r['Gp_y']==r['Gp_z']==r['DA']==0,'Analytic field3 premises differ')
        if not surface or f in (0,2): need(abs(a-r['old_rate'])<=max(b,r['old_budget']),'Original unchanged-action gate rejected')
        groups.setdefault((f,v),[]).append((r,error/b,ie/ib,signal))
        if (f,v,ident)==(3,0,139): first_top={k:r[k] for k in ('id','Normal_x','actual_rate','independent_rate','budget','analyticField3','expectationResidual')}
    maxima=[]
    for i,raw in enumerate(affine):
        r=numeric(raw); key=(i//3,i%3); g=groups[key]; peaks=(max(x[1] for x in g),max(x[2] for x in g),max(x[3] for x in g if x[0]['FSType'] in (2,3))); need((r['field'],r['normal_variant'],r['rows'],r['upper_rows'],r['top_rows'])==(*key,1000,500,10) and sum(x[0]['z']>0.5 for x in g)==500 and sum(x[0]['FSType'] in (2,3) for x in g)==10 and all(close(r[k],p) for k,p in zip(('max_error_ratio','max_invariance_ratio','max_signal_ratio'),peaks)), 'Affine aggregation differs')
        if key[0]==1: need(peaks[2]>100,'Each incompatible variant needs100budget witness')
        maxima.append(peaks)
    loads=[numeric(r) for r in loads]; wrong=[]; load_peaks=[]; force_peaks=[]
    for trial,raw in enumerate(summary):
        s=numeric(raw); g=loads[trial*1000:(trial+1)*1000]; need(s['case']==trial and all((r['case'],r['id'])==(trial,40+j) for j,r in enumerate(g)), 'Load case/ID coverage differs'); load=force=bad=al=af=0.0
        for r in g:
            need(r['in_actual_band'] in (0,1) and abs(r['mass']-MASS/RHO0*(RHO0-RHOW+RHOW*r['J']))<=5e-13*abs(r['mass']), 'Mixture ledger/band differs'); x=r['mass']*r['LoadAce_z']; y=r['mass']*r['Ace_z']; load+=x; force+=y; bad+=MASS*r['LoadAce_z']; al+=abs(x); af+=abs(y)
        lb,fb=force_budget(al,s['retained_target_N']),force_budget(af,s['retained_target_N']); lr=max(abs(s['rhoV_LoadAce_N']-s['retained_target_N']),abs(s['rhoV_LoadAce_N']-s['analytic_qA0_N']))/s['load_budget_N']; fr=max(abs(s['rhoV_Ace_N']-s['retained_target_N']),abs(s['rhoV_Ace_N']-s['analytic_qA0_N']))/s['force_budget_N']; wr=abs(s['wrong_MassFluid_N']-s['retained_target_N'])/max(s['load_budget_N'],s['force_budget_N'])
        need(close(lb,s['load_budget_N']) and close(fb,s['force_budget_N']) and lr<=1 and fr<=1 and max(abs(load-s['retained_target_N']),abs(load-s['analytic_qA0_N']))<=lb and max(abs(force-s['retained_target_N']),abs(force-s['analytic_qA0_N']))<=fb and abs(load-s['rhoV_LoadAce_N'])<=lb and abs(force-s['rhoV_Ace_N'])<=fb and abs(bad-s['wrong_MassFluid_N'])<=max(lb,fb) and close(lr,s['load_error_ratio']) and close(fr,s['force_error_ratio']) and close(wr,s['wrong_weight_ratio']), 'Original load/resultant budget rejected')
        if trial>=2: need(wr>100,'Each non-J1 wrong-mass witness must exceed100budgets'); wrong.append(wr)
        load_peaks.append(lr); force_peaks.append(fr)
    need([r['probe'] for r in probes]==['zero_normal','NaN_normal','active_host_p_rate_and_owner','bad_owner_kernel_invalid_index'] and all(r['passed']=='true' and math.isfinite(float(r['witness_count_or_invalid_index'])) for r in probes) and float(probes[2]['witness_count_or_invalid_index'])==10 and float(probes[3]['witness_count_or_invalid_index'])>=0,'Exact guard/owner probes differ')
    values=dict(max_rate_error_over_original_budget=max(p[0] for p in maxima),max_normal_invariance_over_original_budget=max(p[1] for p in maxima),incompatible_signal_over_original_budget=max(p[2] for p in maxima),max_load_resultant_over_original_budget=max(load_peaks),max_finished_force_over_original_budget=max(force_peaks),minimum_wrong_mass_over_original_budget=min(wrong))
    need(all(close(done[k],v) for k,v in values.items()),'Completion/CSV maxima differ'); result.update(values); result.update(counts); result['first_actual_normal_top139']=first_top; result['exact_plane_upper_max_abs_rate']=max(abs(r['actual_rate']) for r in rates if r['field']==2 and r['z']>0.5); result['CSV_QC_complete']=True

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-receipt',required=True); p.add_argument('--tag',required=True); a=p.parse_args(); need(re.fullmatch(r'upl_gpu_column_component_[A-Za-z0-9_]+',a.tag),'Tag must be a safe component leaf'); out=T/'logs'/(a.tag+'.check.json'); need(not out.exists(),'Retained check protected')
    result=dict(stage='upl_gpu_column_component_review_r3',passed=False,physical_acceptance=False,programs_launched=False,source_inputs_objects_runtime_canonical_unchanged=False); complete=False
    try:
        bind(entry(__file__)); bind(entry(T/'notes'/'upl_gpu_column_component_review_r3.json')); review(entry(a.run_receipt),result); need(a.tag.startswith('upl_gpu_column_component_'+result['configuration']+'_'),'Tag configuration differs'); complete=True
    except Exception as e: result['failure']=str(e)
    try:
        need(all(entry(e['path'])==e for e in BOUND.values()),'Bound artifact changed during offline review'); result['source_inputs_objects_runtime_canonical_unchanged']=complete
    except Exception as e: complete=False; result['failure']=str(e)
    result['passed']=complete; result['inputs']=list(BOUND.values())
    with out.open('x',encoding='utf-8',newline='\n') as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
    print(str(out)); return 0 if complete else 1
if __name__=='__main__': raise SystemExit(main())
