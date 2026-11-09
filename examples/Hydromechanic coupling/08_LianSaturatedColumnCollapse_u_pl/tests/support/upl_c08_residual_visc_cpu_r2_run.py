"""One admitted four-call OFF/alpha.1 actual CPU numerical-viscosity component; no time integration."""
import argparse,csv,math,os,struct
from pathlib import Path
import psutil
import upl_c08_residual_visc_cpu_r2_build as b
T,L,TAG,HELPER,PROGRAM=b.T,b.L,b.TAG,b.HELPER,b.PROGRAM;OUT=T/'outputs'/TAG
need,read,stat,bind,save=b.need,b.read,b.stat,b.bind,b.save


def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def bits(x):return struct.pack('<d',float(x))


def run():
    check=L/(TAG+'.check.json');need(not OUT.exists() and not check.exists(),'Existing complete/partial component protected');before=[];call=None
    try:
        bp=L/(TAG+'.build.json');build=read(bp);priorp=L/'upl_c08_pair_force_cpu_r1.check.json';prior=read(priorp);need(build['passed'] and build['consumed_stats_unchanged'] and build['project_non_main_objects']==86 and build['retained_physical_objects']==85 and build['physical_objects_recompiled']==0 and build['adopted_physical_objects']==build['helper_objects_compiled']==build['compile_invocations']==build['link_invocations']==1 and build['actual_link_objects']==87 and build['numerical_damping_candidate'] and build['candidate_macro']=='C08_RESIDUAL_VISCOSITY_CANDIDATE','Actual private Single+helper closure required');need(prior['passed'] and prior['consumed_stats_unchanged'] and prior['source_parts']==[13,14] and prior['force_evaluations']==6 and prior['actual_physical_steps']==0,'Retained actual two-state pair-force baseline required')
        rp=Path(bind(prior['source_run'])['path']);npth=Path(bind(prior['source_native'])['path']);r,n=read(rp),read(npth);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and n['passed'] and n['original_native_guards_passed'] and n['source_run']==stat(rp),'Closed actual total-AS/n3 source run/native required');directory=Path(bind(n['completion'])['path']).parent;need(directory.resolve()==(T/'outputs/upl_c08_causal_window_GPU_r1/native').resolve(),'Only true causal90 source admitted');seed=Path(bind(r['input_xml'])['path']).with_suffix('')
        before=[stat(p) for p in (Path(__file__),Path(b.__file__),b.NOTE,Path(b.old.__file__),bp,priorp,rp,npth)]+[bind(build[k]) for k in ('program','source','source_build','runtime_r6_GPU_build','source_capture','source_archive','private_source_capture','private_source_archive','private_cpu_source','adopted_physical_object','adopted_physical_compile_call','prior_failed_build')]+[bind(v) for v in build['runtime']]+[bind(prior[k]) for k in ('actual_call','component_completion','source_prefix_proof')]+[bind(r[k]) for k in ('source_pre_file','input_xml')]+[bind(v) for v in r['seed']]
        before.extend(bind(v) for v in n['outputs'] if Path(v['path']).name in ('typed22.bin','typed22_layout.csv','clocks.csv'));oldfiles={Path(v['path']).name:bind(v) for v in prior['files']};before.extend(oldfiles.values())
        for proc in psutil.process_iter(['exe']):
            try:need(not proc.info['exe'] or os.path.normcase(os.path.abspath(proc.info['exe']))!=os.path.normcase(os.path.abspath(PROGRAM)),'Exact helper active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        need(all(stat(v['path'])==v for v in before),'Closed component inputs changed');argv=[str(PROGRAM),'--check','--snapshot',str(directory),'-cpu','-ompthreads:1','-stable','-svres','-mdbc_freeslip:1',str(seed),str(OUT)];call=b.invoke(TAG+'.run',argv,HELPER);done=read(OUT/'completion.json')
        counts=dict(actual_ct_calls=4,actual_Darcy_calls=4,call_rows=4,pair_rows=8,focus_rows=16,soil_force_rows=20000,baseline_rate_restore_bits_checks=20000,actual_DtVariable_false_calls=4,ON_Rsigma_theta_C_FS_bits_checks=10000,hook_OFF_calls=2,hook_ON_calls=2,manufactured_rows=6,physical_steps=0,material_return_calls=0,filter_calls=0,extra_Darcy_calls=0)
        need(done['passed'] and done['stage']==TAG and done['source_parts']==[13,14] and done['focus_IDs']==[7011,7012,6230,6231] and done['alpha']==.1 and all(done[k]==v for k,v in counts.items()) and done['hook_before_original_Darcy_wrapper'] and done['soil_only_matched_eta0_LS'] and done['unregularized_rank_checked'] and not done['node_skip_or_regularization'] and done['double_force_and_float_commit_budgets_separate'] and not done['ViscDtMax_altered_by_candidate'] and not done['physical_acceptance'],'Actual candidate hook/four-call/zero-step scope differs')
        calls,soil,focus,pairs,damping,manufactured=(table(OUT/leaf) for leaf in ('calls.csv','soil_force.csv','focus.csv','pairs.csv','damping.csv','manufactured.csv'));need([len(x) for x in (calls,soil,focus,pairs,damping,manufactured)]==[4,20000,16,8,4,6],'CSV call coverage differs');need(all(math.isfinite(float(v)) for rows in (calls,soil,focus,pairs,damping,manufactured) for q in rows for k,v in q.items() if k not in ('mode','manufacture')),'Nonfinite actual component CSV')
        oldsoil={(int(q['part']),int(q['native_id'])):q for q in table(Path(oldfiles['soil_force.csv']['path'])) if q['mode']=='baseline'};oldfocus={(int(q['part']),int(q['native_id'])):q for q in table(Path(oldfiles['focus.csv']['path'])) if q['mode']=='baseline'};oldpairs={int(q['part']):q for q in table(Path(oldfiles['pairs.csv']['path'])) if q['mode']=='baseline'};alignment=dict(soil_rows=0,focus_rows=0,pair_rows=0,field_checks=0,mismatched_fields=0,first_mismatches=[])
        def compare(q,ref):
            for key in ref:
                if key in ('call','mode') or key not in q:continue
                alignment['field_checks']+=1
                if bits(q[key])!=bits(ref[key]):
                    alignment['mismatched_fields']+=1
                    if len(alignment['first_mismatches'])<8:alignment['first_mismatches'].append(dict(part=int(q['part']),native_id=q.get('native_id'),field=key,new=q[key],old=ref[key]))
        baseline={};fs_checks=derivative_checks=0
        for index,c in enumerate(calls,1):
            part=13+(index-1)//2;mode='OFF' if index%2 else 'ON';need(int(c['call'])==index and int(c['part'])==part and c['mode']==mode and c['primary_bits_unchanged']==c['operator_flags_restored']=='1' and int(c['AS_enabled'])==1 and float(c['AS_exponent'])==3 and struct.pack('<f',float(c['AS_coefficient']))==struct.pack('<f',.2) and struct.pack('<f',float(c['AV_coefficient']))==struct.pack('<f',.1),'Actual OFF/ON context/AS/AV differs');need(float(c['actual_DtVariable_s'])==float(c['SymplecticDtPre_s'])==.0000025 and float(c['necessary_bound_s'])>=.0000025,'Original actual necessary-step guard failed')
            rows=[q for q in soil if int(q['call'])==index];ff=[q for q in focus if int(q['call'])==index];pp=[q for q in pairs if int(q['call'])==index];need(len(rows)==5000 and {int(q['native_id']) for q in rows}==set(range(2060,7060)) and len(ff)==4 and len(pp)==2,'Actual fullsoil/focus/pair coverage differs')
            if mode=='OFF':baseline[part]={int(q['native_id']):q for q in rows}
            for q in rows:
                identity=int(q['native_id']);ref=baseline[part][identity]
                if mode=='OFF':compare(q,oldsoil[part,identity]);alignment['soil_rows']+=1
                else:
                    for key in ('theta_s_1','Rsigma_xx_Pa_s','Rsigma_yy_Pa_s','Rsigma_zz_Pa_s','Rsigma_xy_Pa_s','Rsigma_yz_Pa_s','Rsigma_xz_Pa_s'):need(bits(q[key])==bits(ref[key]),'ON altered actual theta/stress rate');derivative_checks+=1
                    need(q['actual_FS']==ref['actual_FS'],'ON altered actual FS');fs_checks+=1
                for axis in ('x','y','z'):need(float(q['switch_minus_baseline_Ace_'+axis+'_m_s2'])==float(q['Ace_'+axis+'_m_s2'])-float(ref['Ace_'+axis+'_m_s2']),'Actual Ace change readback differs')
                need(float(q['switch_minus_baseline_rate_Pa_s'])==float(q['rate_Pa_s'])-float(ref['rate_Pa_s']),'Actual Darcy change readback differs')
            if mode=='OFF':
                for q in ff:
                    key=part,int(q['native_id'])
                    if key in oldfocus:compare(q,oldfocus[key]);alignment['focus_rows']+=1
                for q in pp:
                    if int(q['id_i'])==7011:compare(q,oldpairs[part]);alignment['pair_rows']+=1
            d=damping[index-1];need(int(d['call'])==index and d['mode']==mode and float(d['alpha'])==(.1 if mode=='ON' else 0.),'Applied alpha/meter context differs')
            if mode=='ON':need(0<float(d['alpha_dt_dmax'])<=1 and float(d['work'])<=float(d['work_budget']) and abs(float(d['work_plus_2form']))<=float(d['work_budget']) and float(d['net_force_norm'])<=float(d['net_force_budget']) and abs(float(d['torque_y']))<=float(d['torque_budget']),'Declared matched-LS/damping proof readback failed')
        need(alignment['soil_rows']==10000 and alignment['focus_rows']==4 and alignment['pair_rows']==2 and alignment['mismatched_fields']==0 and derivative_checks==70000 and fs_checks==10000,'OFF strict0ULP baseline or ON unchanged constitutive fields failed; no signedzero exceptions')
        need({(int(q['part']),q['manufacture']) for q in manufactured}=={(part,name) for part in (13,14) for name in ('constant','affine','rigid_rotation')},'Manufactured case coverage differs')
        for q in manufactured:need(q['manufacture'] in ('constant','affine','rigid_rotation') and float(q['manufacture_max_residual'])<=float(q['manufacture_residual_budget']) and float(q['max_force'])<=float(q['manufacture_force_budget']),'Manufactured null check failed')
        need(all(stat(v['path'])==v for v in before),'Closed inputs changed during four actual calls');save(check,dict(stage=TAG,passed=True,component_build=stat(bp),source_run=prior['source_run'],source_native=prior['source_native'],source_prefix_proof=prior['source_prefix_proof'],source_pair_force_check=stat(priorp),actual_call=call,component_completion=stat(OUT/'completion.json'),source_parts=[13,14],force_evaluations=4,Darcy_evaluations=4,actual_physical_steps=0,material_return_calls=0,filter_calls=0,solver_invocations=0,GenCase_invocations=0,native_decodes=0,operator_modes=['OFF','alpha0.1'],alpha=.1,OFF_baseline_alignment=alignment,ON_derivative_field_checks=derivative_checks,ON_FS_checks=fs_checks,actual_new_Darcy_response_included=True,numerical_damping_not_GNOG=True,coupled_stability_or_physics_acceptance_claimed=False,physical_acceptance=False,consumed=before,consumed_stats_unchanged=True,files=[stat(OUT/leaf) for leaf in ('completion.json','calls.csv','pairs.csv','focus.csv','soil_force.csv','damping.csv','manufactured.csv','Run.out')],SHA_scans=0))
    except Exception as error:
        cp=L/(TAG+'.run.call.json');actual=read(cp) if cp.exists() else None
        if not check.exists():save(check,dict(stage=TAG,passed=False,first_failure=str(error),actual_call=stat(cp) if cp.exists() else call,actual_Popen_wait_exit=actual.get('actual_Popen_wait_exit') if actual else None,actual_Win32_exit=actual.get('actual_Win32_exit') if actual else None,partial_outputs_preserved=True,consumed=before,physical_acceptance=False,actual_physical_steps=0,SHA_scans=0))
        raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Author-only until root full-read and one explicit component invocation');run()
