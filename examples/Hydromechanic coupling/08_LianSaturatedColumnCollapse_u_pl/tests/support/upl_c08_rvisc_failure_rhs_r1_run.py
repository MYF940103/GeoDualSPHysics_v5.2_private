"""Six zero-time CPU force/Darcy calls on three sealed baseline/candidate snapshots; no trajectory."""
import argparse, csv, math, os, struct
from pathlib import Path
import psutil
import upl_c08_rvisc_failure_rhs_r1_build as b

T,L,TAG,HELPER,PROGRAM=b.T,b.L,b.TAG,b.HELPER,b.PROGRAM
OUT=T/'outputs'/TAG
need,read,stat,bind,save=b.need,b.read,b.stat,b.bind,b.save
FOCUS=[7011,7012,6230,6231,5941,5897,5895,5294]
SPECS=[('baseline_control',13,90),('baseline52',51,90),('rvisc52',51,53)]


def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def bits(value):return struct.pack('<d',float(value))


def run():
    check=L/(TAG+'.check.json'); need(not OUT.exists() and not check.exists(),'Existing complete/partial component protected'); before=[]; call=None
    try:
        bp=L/(TAG+'.build.json'); build=read(bp)
        need(build['passed'] and build['consumed_stats_unchanged'] and build['project_non_main_objects']==86 and build['retained_physical_objects']==85 and build['physical_objects_recompiled']==0 and build['adopted_physical_objects']==build['helper_objects_compiled']==build['compile_invocations']==build['link_invocations']==1 and build['actual_link_objects']==87 and build['same_candidate_physical_object_as_closed_r2'] and build['math_and_restore_blocks_byte_exact'] and build['candidate_macro']=='C08_RESIDUAL_VISCOSITY_CANDIDATE','Closed matching private Single+helper build required')
        priorp=L/'upl_c08_residual_visc_cpu_r2.check.json'; prior=read(priorp)
        need(prior['passed'] and prior['consumed_stats_unchanged'] and prior['source_parts']==[13,14] and prior['force_evaluations']==prior['Darcy_evaluations']==4 and prior['actual_physical_steps']==0,'Retained R2 actual implementation control required')
        np0=Path(bind(prior['source_native'])['path']); n0=read(np0); rp0=Path(bind(n0['source_run'])['path']); r0=read(rp0)
        np1=L/'upl_c08_rvisc90_GPU_r1.partial_native_r1.json'; n1=read(np1); rp1=Path(bind(n1['source_run'])['path']); r1=read(rp1)
        need(n0['passed'] and n0['original_native_guards_passed'] and n0['consumed_stats_unchanged'] and n0['source_run']==prior['source_run'] and r0['passed'] and r0['solver_completed'] and r0['actual_exit']==r0['actual_Win32_exit']==0,'Actual completed baseline90 source binding differs')
        need(n1['passed'] and n1['partial'] and not n1['runtime_success_claimed'] and not n1['physical_acceptance'] and n1['original_saved_native_guards_passed'] and n1['consumed_stats_unchanged'] and n1['source_run']==n1['source_failed_run'] and n1['retained30_all22_time_layout_signed_byte_exact'] and not n1['failure_unsaved_state_reconstructed'],'Actual failed53 native/unchanged-guard closure differs')
        need(not r1['passed'] and not r1['solver_completed'] and r1['actual_exit']==r1['actual_Win32_exit']==r1['actual_tool_exit']==1 and r1['ownership_errors']==[] and r1['consumed_stats_unchanged'] and r1['failed_stage']=='solver' and r1['source_pre_file']==r0['source_pre_file'],'Failed candidate run or common original PRE binding differs')
        need(n1['partial_sidecar_audit']['passed'] and n1['partial_sidecar_audit']['saved_frames']==53 and n1['partial_sidecar_audit']['saved_completed_global']==4212000 and n1['partial_sidecar_audit']['actual_saved_Pre_commits']==n1['partial_sidecar_audit']['actual_saved_Cor_commits']==212000,'Only saved53 candidate scope admitted')
        dirs=[Path(bind(n['completion'])['path']).parent for n in (n0,n1)]
        need(dirs==[T/'outputs/upl_c08_causal_window_GPU_r1/native',T/'outputs/upl_c08_rvisc90_GPU_r1/native_partial_r1'],'Only explicit closed90/53 native sources admitted')
        clocks=[]
        for n,samples in ((n0,90),(n1,53)):
            d=read(bind(n['completion'])['path']); m=read(bind(n['metadata'])['path'])
            need(d['passed'] and d['samples']==samples and d['completed_steps']==4000000+4000*samples and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['actual_native_IDs_per_frame']==6805 and d['soil_IDs']==5000 and d['actual_fixed_IDs']==1805 and d['kept_bed_IDs']==[1800,1852,1904,1956,2008] and d['actual_retired_count']==255 and d['max_scalar_clock_error_s']==d['max_ledger_relative_error']==0 and d['ledger_checks']==d['rho_cache_bits_checks']==d['kappa_nondecreasing_from_PRE_checks']==5000*samples and d['P0_bits_checks']==6805*samples and d['fixed_marker_checks']==1805*samples and d['nonempty_signed_intervals']==samples and d['plane_gap_checks']==10000*samples,'Original all22/ID/ledger/P0/clock/geometry qualification differs')
            need(m['passed'] and m['samples']==samples and m['AS_active_true_headers']==m['keep_policy_headers']==m['ponding_policy_keys_absent_headers']==samples,'Original AS/keep5/CompletedOnly metadata qualification differs')
            if samples==53:need(d['partial'] and not d['runtime_success_claimed'] and d['last_saved_step']==4211999 and d['used_launch_plan_prefix_samples']==53 and not d['failure_unsaved_state_reconstructed'],'Saved partial must not claim failed-state reconstruction')
            folder=Path(n['completion']['path']).parent; rows=table(folder/'clocks.csv'); need(len(rows)==samples,'Closed clock row count differs'); clocks.append(rows)
        need(bits(clocks[0][51]['time_s'])==bits(clocks[1][51]['time_s']),'Actual same-part baseline/candidate clocks differ')
        seed=Path(bind(r0['input_xml'])['path']).with_suffix('')
        oldfiles={Path(e['path']).name:bind(e) for e in prior['files']}
        before=[stat(p) for p in (Path(__file__),Path(b.__file__),b.NOTE,Path(b.old.__file__),Path(b.old.old.__file__),bp,priorp,np0,np1,rp0,rp1)]+[bind(build[k]) for k in ('program','source','source_build','source_capture','source_archive','private_cpu_source','private_source_capture','private_source_archive','adopted_physical_object','adopted_physical_compile_call','prior_build')]+[bind(e) for e in build['runtime']]+list(oldfiles.values())+[bind(prior[k]) for k in ('actual_call','component_completion','source_prefix_proof')]
        before.extend(bind(r0[k]) for k in ('source_pre_file','input_xml')); before.extend(bind(e) for e in r0['seed']); before.extend(bind(r1[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','actual_call'))
        before.extend(bind(n1[k]) for k in ('actual_failed_solver_call','actual_call','utility_build')); before.extend(bind(n1['partial_sidecar_audit'][k]) for k in ('policy_file','meter_file'))
        for n in (n0,n1):
            before.extend(bind(n[k]) for k in ('actual_call','completion','metadata')); before.extend(bind(e) for e in n['outputs'] if Path(e['path']).name in ('typed22.bin','typed22_layout.csv','clocks.csv'))
        for proc in psutil.process_iter(['exe']):
            try:need(not proc.info['exe'] or os.path.normcase(os.path.abspath(proc.info['exe']))!=os.path.normcase(os.path.abspath(PROGRAM)),'Exact helper active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        need(all(stat(e['path'])==e for e in before),'Closed inputs changed')
        argv=[str(PROGRAM),'--check','--baseline-native',str(dirs[0]),'--candidate-native',str(dirs[1]),'-cpu','-ompthreads:1','-stable','-svres','-mdbc_freeslip:1',str(seed),str(OUT)]
        call=b.invoke(TAG+'.run',argv,HELPER); done=read(OUT/'completion.json')
        counts=dict(actual_ct_calls=6,actual_Darcy_calls=6,call_rows=6,pair_rows=12,focus_rows=48,soil_force_rows=30000,baseline_rate_restore_bits_checks=30000,actual_DtVariable_false_calls=6,ON_Rsigma_theta_C_FS_bits_checks=15000,hook_OFF_calls=3,hook_ON_calls=3,manufactured_rows=0,physical_steps=0,material_return_calls=0,filter_calls=0,extra_Darcy_calls=0)
        need(done['passed'] and done['stage']==TAG and done['source_parts']==[13,51,51] and done['source_snapshots']==[s[0] for s in SPECS] and done['focus_IDs']==FOCUS and done['alpha']==.1 and all(done[k]==v for k,v in counts.items()) and done['all5000_soil_primary_bits_preserved_each_call'] and done['hook_before_original_Darcy_wrapper'] and done['soil_only_matched_eta0_LS'] and done['unregularized_rank_checked'] and not done['node_skip_or_regularization'] and not done['ViscDtMax_altered_by_candidate'] and not done['physical_acceptance'],'Actual six-call/zero-step scope differs')
        calls,soil,focus,pairs,damping=(table(OUT/leaf) for leaf in ('calls.csv','soil_force.csv','focus.csv','pairs.csv','damping.csv'))
        need([len(x) for x in (calls,soil,focus,pairs,damping)]==[6,30000,48,12,6],'CSV coverage differs')
        need(all(math.isfinite(float(value)) for rows in (calls,soil,focus,pairs,damping) for row in rows for key,value in row.items() if key not in ('mode','snapshot')),'Nonfinite actual CSV')
        oldtables={leaf:table(Path(oldfiles[leaf]['path'])) for leaf in ('soil_force.csv','focus.csv','pairs.csv')}
        alignment=dict(soil_rows=0,focus_rows=0,pair_rows=0,field_checks=0,mismatched_fields=0,first_mismatches=[])
        def compare(row,ref):
            for key in ref:
                if key in ('call','mode','snapshot') or key not in row:continue
                alignment['field_checks']+=1
                if bits(row[key])!=bits(ref[key]):
                    alignment['mismatched_fields']+=1
                    if len(alignment['first_mismatches'])<8:alignment['first_mismatches'].append(dict(mode=row['mode'],native_id=row.get('native_id'),field=key,new=row[key],old=ref[key]))
        baselines={}; derivative_checks=fs_checks=0
        for index,c in enumerate(calls,1):
            label,part,samples=SPECS[(index-1)//2]; mode='OFF' if index%2 else 'ON'; clock=clocks[0 if samples==90 else 1][part]
            need(int(c['call'])==index and int(c['part'])==part and c['snapshot']==label and c['mode']==mode and bits(c['time_s'])==bits(clock['time_s']) and bits(c['tau_s'])==bits(clock['tau_from_actual_release_s']) and int(c['completed_step'])==int(clock['completed_step']) and c['primary_bits_unchanged']==c['operator_flags_restored']=='1' and int(c['AS_enabled'])==1 and float(c['AS_exponent'])==3 and struct.pack('<f',float(c['AS_coefficient']))==struct.pack('<f',.2) and struct.pack('<f',float(c['AV_coefficient']))==struct.pack('<f',.1),'Actual snapshot/mode/clock/AS/AV context differs')
            need(float(c['actual_DtVariable_s'])==float(c['SymplecticDtPre_s'])==.0000025 and float(c['necessary_bound_s'])>=.0000025,'Original actual necessary-step guard failed')
            rows=[q for q in soil if int(q['call'])==index]; ff=[q for q in focus if int(q['call'])==index]; pp=[q for q in pairs if int(q['call'])==index]
            need(len(rows)==5000 and {int(q['native_id']) for q in rows}==set(range(2060,7060)) and {int(q['native_id']) for q in ff}==set(FOCUS) and len(ff)==8 and len(pp)==2 and all(q['snapshot']==label and q['mode']==mode and int(q['part'])==part and bits(q['time_s'])==bits(clock['time_s']) for q in rows+ff+pp),'Fullsoil/focus/pair context coverage differs')
            if mode=='OFF':baselines[label]={int(q['native_id']):q for q in rows}
            for q in rows:
                ref=baselines[label][int(q['native_id'])]
                if mode=='ON':
                    for key in ('theta_s_1','Rsigma_xx_Pa_s','Rsigma_yy_Pa_s','Rsigma_zz_Pa_s','Rsigma_xy_Pa_s','Rsigma_yz_Pa_s','Rsigma_xz_Pa_s','capacity_Kw_over_n_Pa','compression_Pa_s'):need(bits(q[key])==bits(ref[key]),'ON changed constitutive/compression source'); derivative_checks+=1
                    need(q['actual_FS']==ref['actual_FS'],'ON changed FS'); fs_checks+=1
                for axis in ('x','y','z'):need(float(q['switch_minus_baseline_Ace_'+axis+'_m_s2'])==float(q['Ace_'+axis+'_m_s2'])-float(ref['Ace_'+axis+'_m_s2']),'Actual finishedAce difference readback differs')
                need(float(q['switch_minus_baseline_rate_Pa_s'])==float(q['rate_Pa_s'])-float(ref['rate_Pa_s']),'Actual Darcy difference readback differs')
                need(float(q['capacity_Kw_over_n_Pa'])>0 and bits(q['compression_Pa_s'])==bits(-float(q['capacity_Kw_over_n_Pa'])*float(q['theta_s_1'])),'Read-only absolute compression arithmetic differs')
            if label=='baseline_control':
                for leaf,newrows,countkey,keys in [('soil_force.csv',rows,'soil_rows',('native_id',)),('focus.csv',ff[:],'focus_rows',('native_id',)),('pairs.csv',pp,'pair_rows',('id_i','id_j'))]:
                    refs={tuple(q[k] for k in keys):q for q in oldtables[leaf] if int(q['part'])==13 and q['mode']==mode}
                    for q in newrows:
                        key=tuple(q[k] for k in keys)
                        if key in refs:compare(q,refs[key]); alignment[countkey]+=1
            d=damping[index-1]; need(int(d['call'])==index and d['snapshot']==label and d['mode']==mode and float(d['alpha'])==(.1 if mode=='ON' else 0.),'Candidate meter context differs')
            if mode=='ON':need(0<float(d['alpha_dt_dmax'])<=1 and float(d['work'])<=float(d['work_budget']) and abs(float(d['work_plus_2form']))<=float(d['work_budget']) and float(d['net_force_norm'])<=float(d['net_force_budget']) and abs(float(d['torque_y']))<=float(d['torque_budget']),'Original matched-LS damping certificate failed')
        need(alignment['soil_rows']==10000 and alignment['focus_rows']==8 and alignment['pair_rows']==4 and alignment['mismatched_fields']==0 and derivative_checks==135000 and fs_checks==15000,'Retained control or unchanged same-state fields failed; no dropped rows or signed-zero exceptions')
        need(all(stat(e['path'])==e for e in before),'Closed inputs changed during six actual calls')
        save(check,dict(stage=TAG,passed=True,component_build=stat(bp),actual_call=call,component_completion=stat(OUT/'completion.json'),source_run=stat(rp0),source_native=stat(np0),source_prefix_proof=prior['source_prefix_proof'],candidate_failed_run=stat(rp1),candidate_partial_native=stat(np1),source_implementation_control=stat(priorp),source_snapshots=[dict(label=label,part=part,native_samples=samples) for label,part,samples in SPECS],force_evaluations=6,Darcy_evaluations=6,actual_physical_steps=0,material_return_calls=0,filter_calls=0,solver_invocations=0,GenCase_invocations=0,native_decodes=0,operator_modes=['OFF','alpha0.1'],alpha=.1,retained_part13_alignment=alignment,ON_derivative_field_checks=derivative_checks,ON_FS_checks=fs_checks,actual_new_Darcy_response_included=True,same_state_delta_rate_is_acceleration_path_response=True,original_necessary_step_guards_preserved=True,failed_GPU_unsaved_state_reconstructed=False,physical_acceptance=False,consumed=before,consumed_stats_unchanged=True,files=[stat(OUT/leaf) for leaf in ('completion.json','calls.csv','pairs.csv','focus.csv','soil_force.csv','damping.csv','Run.out')],SHA_scans=0))
    except Exception as error:
        cp=L/(TAG+'.run.call.json'); actual=read(cp) if cp.exists() else None
        if not check.exists():save(check,dict(stage=TAG,passed=False,first_failure=str(error),actual_call=stat(cp) if cp.exists() else call,actual_Popen_wait_exit=actual.get('actual_Popen_wait_exit') if actual else None,actual_Win32_exit=actual.get('actual_Win32_exit') if actual else None,partial_outputs_preserved=True,actual_physical_steps=0,physical_acceptance=False,consumed=before,SHA_scans=0))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--execution-authorized',action='store_true'); a=p.parse_args(); need(a.execution_authorized,'Author-only until root full-read and explicit invocation'); run()
