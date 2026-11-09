"""One failed53 original22 decode; real failed90 owner and saved-only sidecar audit, never solve."""
import argparse,csv,math,os,re,struct
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';JOB='upl_c08_rvisc90_GPU_r1'
TAG='upl_c08_rvisc53_native_r1_run';UTILITY='upl_c08_rvisc53_native_r1';OUT=T/'outputs'/JOB;NATIVE=OUT/'native_partial_r1';NOTE=T/'notes'/(TAG+'.md')
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4';END=4212000;SAMPLES=53;BED=[1800,1852,1904,1956,2008];POLICY='FixedPlaneStageProjectionReleaseOnly';DT=2.5e-6
ERROR='GPU porosity current step or DtMin exceeds its necessary bound: step=4212949 current=2.5000000000000002e-06 bound=2.4992403879125872e-06 DtMin=1e-08; final=1 force=0.00020763347710247654 wave_visc=6.2175271584135696e-06 pore=2.4992403879125872e-06 k_gradient=1.2609531021502092e-05 AceMax=44535.514996460974 VelMax=28.315700531005859 ViscDtMax=814.6298828125 conductivity_speed=380.66444382933383.'
def lexical(p):return os.path.normcase(os.path.abspath(p))
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def bits(x):return struct.pack('<d',float(x))

def reference30(run,before):
    path=L/'upl_c08_rvisc_window_GPU_r1.native_r1.json';r=e.read(path);e.need(r['passed'] and r['original_native_guards_passed'] and r['consumed_stats_unchanged'] and r['decoder_invocations']==1,'Closed completed30 native required')
    cp=Path(e.bind(r['completion'])['path']);d=e.read(cp);old=cp.parent;rp=Path(e.bind(r['source_run'])['path']);prior=e.read(rp)
    e.need(old.samefile(T/'outputs/upl_c08_rvisc_window_GPU_r1/native_r1') and d['passed'] and d['samples']==30 and d['completed_steps']==4120000 and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805,'Retained actual30 scope differs')
    e.need(prior['passed'] and prior['actual_exit']==prior['actual_Win32_exit']==0 and all(prior[k]==run[k] for k in ('program','source_build','source_capture','source_archive','source_pre_file')),'Same program/source/PRE as completed30 required')
    before += [e.stat(path),e.stat(cp),e.stat(rp),e.bind(r['metadata']),e.bind(r['actual_call'])];files={Path(q['path']).name:q for q in r['outputs']}
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):q=e.bind(files[leaf]);e.need(Path(q['path']).samefile(old/leaf),'Retained30 output differs');before.append(q)
    return path,old,prior

def saved_sidecar(run,text,prior,before):
    policy=e.bind(run['observed_policy_file']);meter=e.bind(run['observed_meter_file']);p=e.read(policy['path']);before += [policy,meter,e.bind(prior['meter_file'])]
    boolkeys=('active','Cubic_2D_normal_soil_only','ephemeral_GPU_scratch_per_stage','host_sync_before_Ace_commit','LS_regularized','wall_bonds','BI4_metadata','native_22_schema_changed','PRE_contract_changed','physical_acceptance')
    e.need(type(p['schema']) is int and type(p['alpha']) in (int,float) and all(type(p[k]) is bool for k in boolkeys) and p['policy']=='C08ResidualViscosityPolicy' and p['schema']==1 and p['alpha']==.1 and p['active'] and p['phase_policy']=='ReleaseOnly' and all(p[k] for k in boolkeys[1:4]) and not any(p[k] for k in boolkeys[4:]),'Actual typed candidate sidecar differs; not BI4 metadata')
    sc=e.read(e.bind(run['source_capture'])['path'])
    with Path(meter['path']).open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    e.need(fields==sc['CSV_fields'] and len(fields)==26 and len(rows)==106,'Exactly53 saved Pre/Cor pairs required, not the planned180 rows')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=4000000;',text);e.need(len(imported)==1,'One actual source-clock import required');source=float(imported[0]);e.need(source==prior['actual_source_time_from_loader'],'Actual PRE scalar clock differs')
    scalar=source;clocks={}
    for update in range(1,212001):
        start=scalar;scalar+=DT
        if update%4000==0:clocks[4000000+update]=(start,scalar)
    running={'Pre':(0.,0.),'Cor':(0.,0.)};maxbound=0.
    for index,q in enumerate(rows):
        phase=('Pre','Cor')[index%2];completed=4000000+4000*(index//2+1);start,time=clocks[completed];count=completed-4000000
        e.need(q['record']=='save' and q['phase']==phase and all(k in ('record','phase') or math.isfinite(float(v)) for k,v in q.items()),'Unexpected failed/nonfinite sidecar row cannot be certified as a saved stage')
        e.need(int(q['active'])==1 and float(q['alpha'])==.1 and int(q['step_start_global'])==completed-1 and int(q['completed_global'])==completed and all(int(q[k])==count for k in ('phase_calls','phase_commits','pre_calls','cor_calls','pre_commits','cor_commits')),'Actual saved-only counters differ')
        e.need(bits(q['step_start_time_s'])==bits(start) and bits(q['force_stage_time_s'])==bits(start+(0. if phase=='Pre' else DT*.5)) and bits(q['save_time_s'])==bits(time) and float(q['operator_dt_s'])==DT,'Actual saved-stage scalar clocks differ')
        e.need(int(q['committed'])==1 and int(q['validated_soil_nodes'])==5000 and int(q['error_bits'])==int(q['cuda_status'])==0 and int(q['invalid_sorted_index'])==int(q['invalid_native_id'])==4294967295,'Actual saved candidate guard/status differs')
        lam,bound,rl,rb=[float(q[k]) for k in ('last_lambda_max_s_1','last_dt_lambda_half','running_lambda_max_s_1','running_dt_lambda_half')]
        e.need(lam>0 and bits(bound)==bits(DT*lam*.5) and 0<bound<=rb<=1 and rl>=lam and rl>=running[phase][0] and rb>=running[phase][1],'Saved isolated damping bound differs');running[phase]=(rl,rb);maxbound=max(maxbound,rb)
    raw=Path(meter['path']).read_bytes().splitlines(keepends=True);old=Path(prior['meter_file']['path']).read_bytes().splitlines(keepends=True)
    e.need(len(old)==61 and raw[:61]==old,'Header and first60 actual saved meter rows differ from completed30')
    return dict(passed=True,partial=True,policy_file=policy,meter_file=meter,not_BI4_metadata=True,CSV_columns=26,CSV_rows=106,saved_frames=53,saved_completed_global=END,actual_saved_Pre_calls=212000,actual_saved_Cor_calls=212000,actual_saved_Pre_commits=212000,actual_saved_Cor_commits=212000,max_saved_dt_lambda_half=maxbound,actual_source_time_s=source,last_saved_scalar_time_s=scalar,old30_meter_header_and_first60_rows_byte_exact=True,unsaved_stage_counters_or_failure_time_reconstructed=False)

def prefix30(old,reference):
    layout=(NATIVE/'typed22_layout.csv').read_bytes()==(old/'typed22_layout.csv').read_bytes();size=8+6805*212;first=None
    with (NATIVE/'typed22.bin').open('rb') as a,(old/'typed22.bin').open('rb') as b:
        ha,hb=struct.unpack('<III',a.read(12)),struct.unpack('<III',b.read(12));e.need(ha==(6805,22,53) and hb==(6805,22,30) and (NATIVE/'typed22.bin').stat().st_size==12+53*size and (old/'typed22.bin').stat().st_size==12+30*size,'Genuine53/30 headers/extents must remain unchanged')
        for part in range(30):
            x,y=a.read(size),b.read(size);e.need(len(x)==len(y)==size,'Truncated native prefix')
            if x!=y and first is None:first=dict(part=part,record_byte=next(i for i,(u,v) in enumerate(zip(x,y)) if u!=v))
        e.need(b.read(1)==b'','Extra retained30 payload')
    clocks=(NATIVE/'clocks.csv').read_bytes().splitlines(keepends=True);prior=(old/'clocks.csv').read_bytes().splitlines(keepends=True);e.need(len(clocks)==54 and len(prior)==31,'Original53/30 clock row count differs');same_clock=clocks[:31]==prior
    return dict(passed=first is None and layout and same_clock,reference_native=e.stat(reference),actual_common_saved_frames=30,new_original_header=list(ha),reference_original_header=list(hb),headers_rewritten=False,all22_and_actual_time_payload_byte_exact=first is None,typed_layout_byte_exact=layout,clock_and_signed_header_and_first30_rows_byte_exact=same_clock,first_different_record_byte=first,physical_acceptance=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();e.need(a.execution_authorized,'Root full-read, passed reader build and separate one-read authorization required')
    label=JOB+'.partial_native_r1';receipt=L/(label+'.json');callpath=L/(label+'.call.json');log=L/(label+'.log')
    e.need(not NATIVE.exists() and not (OUT/'native_r1').exists() and not (OUT/'native').exists() and not any(q.exists() for q in (receipt,callpath,log)),'Existing/partial decode protected; normal90 output is reserved')
    before=[];actual=None;result=dict(stage=TAG,passed=False,partial=True,runtime_success_claimed=False,physical_acceptance=False,source_job=JOB,original_planned_samples=90,original_planned_end=4360000,used_launch_plan_prefix_samples=53,completed_steps_are_last_saved=True,failure_unsaved_state_reconstructed=False,solver_invocations=0,GenCase_invocations=0,decoder_invocations=0,VTK_invocations=0,queue_invocations=0,SHA_scans=0,candidate_operator_is_not_BI4_metadata=True,candidate_sidecar_revalidated_by_reader=False)
    try:
        rp,cp,sp=(L/(JOB+x) for x in ('.run.json','.call.json','.start.json'));r,c,s=e.read(rp),e.read(cp),e.read(sp)
        e.need(not r['passed'] and not r['solver_completed'] and r['profile']=='window90' and r['configuration']=='Release' and r['actual_exit']==r['actual_Win32_exit']==r['actual_tool_exit']==1 and r['ownership_errors']==[] and r['failed_stage']=='solver' and r['consumed_stats_unchanged'],'Actual failed90 solver1 required, not a fabricated normal53 run')
        e.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==1 and c['ownership_errors']==[] and c['actual_outer']==c['actual_solver']==s['actual_outer']==s['actual_solver'] and c['admission']==s['admission'] and e.bind(r['actual_call'])==e.stat(cp),'Failed tool/start/actual solver identity differs')
        adpath=Path(e.bind(c['admission'])['path']);ad=e.read(adpath);rootentry=e.bind(ad['root_admission']);root=e.read(rootentry['path']);identity=c['actual_solver']
        e.need(c['stage']==s['stage']==ad['stage']==JOB and s['owner']==ad['owner'] and identity['parent_pid']==ad['owner']['pid'] and identity['pid']>0 and identity['creation_filetime_100ns']>0 and root['passed'] and root['allowed_job']==JOB and ad['planned_global_end']==4360000 and ad['planned_new_updates']==360000 and ad['expected_saved_frames']==90 and e.bind(r['owner_admission'])==e.stat(adpath),'Actual failed owner/root original90 admission differs')
        e.need(all(ad[k]==r[k] for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','seed','planned_steps')),'Original failed program/input binding differs');program_entry=e.bind(r['program']);e.need(Path(identity['exe']).samefile(program_entry['path']) and Path(e.bind(r['source_pre_file'])['path']).samefile(PRE),'Actual original PRE/private program differs')
        prefix=OUT/JOB;solver_argv=[program_entry['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:4360000'];e.need(identity['argv']==ad['argv']==ad['solver_argv']==c['arguments']==solver_argv and Path(e.bind(r['input_xml'])['path']).samefile(Path(str(prefix)+'.xml')),'Failed actual90 argv/input differs')
        genpath=Path(e.bind(r['GenCase_call'])['path']);gen=e.read(genpath);e.need(gen['actual_Popen_wait_exit']==gen['actual_Win32_exit']==0 and gen['ownership_failure'] is None,'Actual GenCase closure differs')
        plan=Path(e.bind(r['planned_steps'])['path']);e.need(plan.samefile(OUT/'planned_steps.csv'),'Original90 plan path differs')
        with plan.open(encoding='utf-8',newline='') as f:planned=list(csv.DictReader(f))
        e.need(planned==[dict(part=str(i),completed_step=str(4000000+4000*(i+1))) for i in range(90)],'Do not replace or truncate the original90 plan')
        parts=sorted((OUT/'data').glob('Part_*.bi4'));text=(OUT/'Run.out').read_text(encoding='utf-8-sig');errors=re.findall(r'^Text: (.+)$',text,re.M)
        e.need(len(parts)==r['saved_PART_files_on_disk']==53 and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(53)] and r['PARTs_on_disk']==[e.stat(q) for q in parts] and e.bind(r['Run_out'])==e.stat(OUT/'Run.out'),'Actual53 saved PART identity differs')
        e.need(errors==[ERROR] and r['first_engine_exception_text']==ERROR and '*** Exception (JSphGpuSingle::DtVariable)' in text and 'Finished execution (code=1).' in text and re.match(r'^Part_0052\s+10\.530000\s+4212000\s+4000\b',r['last_original_console_line']) and not r['unsaved_failure_time_known'],'Exact original necessary-pore-bound error/last console differs')
        sbpath=Path(e.bind(r['source_build'])['path']);sb=e.read(sbpath);e.need(sbpath.samefile(L/'upl_c08_residual_visc_gpu_Release_r1.build.json') and sb['passed'] and sb['consumed_stats_unchanged'] and sb['profile']=='Release' and sb['alpha']==.1 and all(sb[k]==r[k] for k in ('program','source_capture','source_archive','private_sources','runtime')) and sb['physical_objects_recompiled']==2 and sb['retained_physical_objects']==111 and sb['actual_link_objects']==113,'Exact private Release alpha.1 source/build closure differs')
        reference,old,prior=reference30(r,before);side=saved_sidecar(r,text,prior,before)
        bp=L/(UTILITY+'.build.json');b=e.read(bp);e.need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and b['actual_link_objects']==7 and not b['JSph_objects_linked'],'Closed six-utility Release partial53 build required');program=Path(e.bind(b['program'])['path']);e.need(program.samefile(T/'outputs'/(UTILITY+'_build')/'C08RVisc53Native_win64.exe'),'Wrong partial53 reader')
        for process in psutil.process_iter(['exe','cmdline']):
            try:
                exe=process.info['exe'];args=process.info['cmdline'] or [];e.need(not (exe and lexical(exe) in (lexical(program),lexical(program_entry['path']))) and not any(lexical(x) in (lexical(NATIVE),lexical(OUT/'data')) for x in args[1:]),'Active exact solver/reader/DATA consumer protected; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        before += [e.stat(q) for q in (Path(__file__),NOTE,Path(e.__file__),rp,cp,sp,adpath,Path(rootentry['path']),genpath,bp,plan)]+r['consumed']+[e.bind(r[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','Run_out')]+[e.bind(q) for q in r['seed']+r['PARTs_on_disk']]+[e.bind(b[k]) for k in ('program','source','generated_core','core_diff','core_derivation')]+[e.bind(q) for q in b['objects']+b['calls']]
        rawcsv=OUT/'Run.csv'
        if rawcsv.exists():before.append(e.stat(rawcsv)) # Retain/stat only; never demand a normal completion summary.
        e.need(all(e.stat(q['path'])==q for q in before),'Closed failed evidence/reader/retained30 changed')
        argv=[str(program),'--read','psi0','GPU',str(OUT/'data'),str(PRE),str(END),'53','1',str(plan),str(NATIVE)];result['decoder_invocations']=1;actual=e.invoke(label,argv,C);call=e.read(actual['path'])
        e.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and call['child']['argv']==argv and Path(call['child']['exe']).samefile(program) and call['child']['parent_pid']==os.getpid() and call['child']['creation_filetime_100ns']>0,'Unique partial reader actual exit/exe/argv/creation differs')
        d,m=e.read(NATIVE/'completion.json'),e.read(NATIVE/'bedkeep_metadata.json');counts=dict(samples=53,completed_steps=END,new_updates=212000,typed_arrays=22,typed_bytes_per_particle=212,original_ID_domain=7060,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=265000,fixed_marker_checks=95665,P0_bits_checks=360665,rho_cache_bits_checks=265000,kappa_nondecreasing_from_PRE_checks=265000,nonempty_signed_intervals=53,plane_gap_checks=530000)
        e.need(d['passed'] and d['stage']==UTILITY and d['backend_argument']=='GPU' and not d['backend_proven_by_reader'] and all(d[k]==v for k,v in counts.items()) and not d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_launch_plan'] and d['FS23_pressure_checks']>0,'Original saved53/22 physical guards/counts differ')
        e.need(d['partial'] and not d['runtime_success_claimed'] and d['original_planned_samples']==90 and d['original_planned_end']==4360000 and d['used_launch_plan_prefix_samples']==53 and d['last_saved_step']==4211999 and d['completed_steps_are_last_saved'] and d['new_updates_are_to_last_saved'] and not d['AS_stress_space_proven_by_reader'] and not d['failure_unsaved_state_reconstructed'],'Partial saved-state scope differs')
        e.need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['geometry_tolerance_m']==1e-6*.04 and d['min_soil_x_m']>=-d['geometry_tolerance_m'] and d['min_soil_z_m']>=-d['geometry_tolerance_m'] and d['source_actual_time_s']==side['actual_source_time_s'] and d['actual_end_s']==side['last_saved_scalar_time_s'] and d['source_completed_step']==4000000 and d['source_PREs_read']==1 and d['source_material_law_version']==1 and d['target_material_law_version']==2,'Original scalar/signed/ledger/geometry/PRE guards differ')
        e.need(d['NoPenOn_argument'] and d['DynamicNoPenetrationActive'] and d['DynamicNoPenetrationPolicy']==POLICY and not d['DynamicNoPenetrationReactionClosed'] and d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and d['kept_bed_IDs']==BED and d['kept_bed_count']==d['kept_bed_source_geometry_checks']==5 and not d['actual_retired_IDs_contiguous'] and not d['native_rewritten'],'Original keep5/fixed-plane guards differ')
        e.need(m['passed'] and m['partial'] and not m['runtime_success_claimed'] and m['stage']==UTILITY+'.metadata' and m['profile']=='failed_window_partial' and not m['smoke_final_only'] and m['planned_cadence_steps']==4000 and m['completed_steps']==END and m['original_planned_samples']==90 and m['original_planned_end']==4360000 and m['used_launch_plan_prefix_samples']==53 and all(m[k]==53 for k in ('samples','metadata_header_scans','keep_policy_headers','AS_active_true_headers','ponding_policy_keys_absent_headers')),'Partial lazy metadata profile differs')
        e.need(m['keep_bed_overlap'] and m['actual_retired_count']==255 and m['kept_bed_IDs']==BED and m['kept_bed_count']==5 and m['expected_AS'] and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==f32(.2) and m['AS_exponent_float_reference']==3. and m['expected_ponding_policy']=='CompletedOnly' and m['core_array_decode_passes']==1 and not any(m[k] for k in ('metadata_scans_decode_field_arrays','PRE_arrays_reloaded_by_adapter','core_original_numerical_budgets_changed','AS_stress_space_proven_by_reader','failure_unsaved_state_reconstructed','physical_acceptance')),'Original typed AS/CompletedOnly/single22 decode guards differ')
        prefix=prefix30(old,reference);e.need(prefix['passed'],'Actual53 vs completed30 full22/time/layout/signed prefix differs; preserve read, never retry')
        e.need(all(e.stat(q['path'])==q for q in before),'Closed artifacts changed during unique partial read')
        result.update(passed=True,source_run=e.stat(rp),source_failed_run=e.stat(rp),actual_failed_solver_call=e.stat(cp),utility_build=e.stat(bp),actual_call=actual,completion=e.stat(NATIVE/'completion.json'),metadata=e.stat(NATIVE/'bedkeep_metadata.json'),partial_sidecar_audit=side,original_saved_native_guards_passed=True,retained_rvisc30_prefix=prefix,retained30_all22_time_layout_signed_byte_exact=True,first_actual_engine_exception=ERROR,last_actual_console=r['last_original_console_line'],raw_Run_csv=e.stat(rawcsv) if rawcsv.exists() else None,consumed_stats_unchanged=True,outputs=[e.stat(q) for q in sorted(NATIVE.iterdir()) if q.is_file()])
    except Exception as error:result.update(first_failure=str(error),actual_call=e.stat(callpath) if callpath.exists() else actual)
    result['consumed']=before;e.save(receipt,result);print(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure')));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
