"""One root-admitted Lstar OFF1/Debug2 native read; no solver, build, VTK or chaining."""
import argparse, os, struct
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
import c08_h18_storage_review_r2 as core
T,L=m.T,m.L
SCRIPT=Path(__file__).resolve();TAG='c08_h18_lstar_gpu_native_r1';NOTE=T/'notes'/(TAG+'.md')
READER_BUILD=L/'c08_h18_rv_native_r1.build.json'
PRE=T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
JOBS={'off1':('c08_h18_lstar_gpu_off1_r1',1,2000001,'Release','off'),'debug2':('c08_h18_lstar_gpu_debug2_r1',2,2000002,'Debug','on')}
need,read,stat,bind,entry,owned,same=core.need,core.read,core.stat,core.bind,core.entry,core.owned,core.same
def bits(x):return struct.pack('<d',float(x))
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def frozen(rows):
    for q in rows:bind(q)
def admission(path,profile,runpath):
    a=read(path);thread=os.environ.get('CODEX_THREAD_ID')
    need(thread and a['authorized']is True and a['phase']=='native'and a['profile']==profile and a['allowed_job']==JOBS[profile][0]and a['execution_script']==stat(SCRIPT)and a['note']==stat(NOTE)and a['source_run']==stat(runpath)and a['reader_build']==stat(READER_BUILD)and a['root_thread_id']==thread and a['automatic_solver']is False and a['automatic_next_job']is False,'Exact independent current-root native admission required')

def inputs(profile,runpath,consumed):
    job,count,end,configuration,mode=JOBS[profile];r=read(runpath);startpath=L/(job+'.start.json');start=read(startpath)
    need(r['passed']and r['solver_completed']and r['stage']==job and r['profile']==profile and r['configuration']==configuration and r['mode']==mode and r['consumed_stats_unchanged']and r['actual_steps']==end and r['saved_frames']==count and r['new_updates']==count and r['actual_exit']==r['actual_Win32_exit']==r['actual_tool_exit']==r['actual_tool_Win32_exit']==0 and r['ownership_failure']is None and not r['unsaved_state_reconstructed'],'Actual completed owned Lstar smoke required')
    callstat=entry(r,'actual_call');call=read(callstat['path']);owned(call)
    need(call['owner']['pid']==r['owner']['pid']and call['owner']['created_epoch']==r['owner']['created_epoch']and call['child']['parent_pid']==r['owner']['pid']and call['child']['argv']==r['argv']and start['owner']==r['owner']and start['argv']==r['argv']and start['solver_argv']==r['solver_argv'],'Actual owner/start/child/tool argv differs')
    for k in('program','source_build','source_capture','source_archive','source_pre_file','input_xml','planned_steps'):need(start[k]==r[k],'Original start binding differs: '+k)
    target=r['solver_identity'];need(target and target['creation_filetime_100ns']>0 and same(target['exe'],r['program']['path'])and r['solver_program_identity_matches']and r['actual_solver_argv_observed']and len(target['argv'])==len(r['solver_argv'])and same(target['argv'][0],r['solver_argv'][0])and target['argv'][1:]==r['solver_argv'][1:],'Actual solver creation/program/argv differs')
    need(r['solver_argv'][-1]=='-nsteps:'+str(end),'Actual bounded global-step cap differs')
    if profile=='debug2':need(r['memcheck_zero_errors_and_leaks']and entry(r,'memcheck_actual_call')==callstat and call['actual_target']==target and call['actual_target_Win32_exit']==0,'Actual Debug memcheck and target evidence required')
    else:need(call['child']==target and same(call['program'],r['program']['path']),'Actual Release direct solver differs')
    consumed.extend([stat(runpath),stat(startpath),callstat,entry(r,'console_log'),bind(call['log'])])
    buildstat=entry(r,'source_build');b=read(buildstat['path']);need(b['passed']and b['consumed_stats_unchanged']and b['configuration']==configuration and b['mode']==mode and b['receiver_C_bare_enabled']==(mode=='on')and b['original_objects']==113 and b['retained_original_objects']==112 and b['private_objects']==1 and b['actual_link_objects']==113 and b['host_compiles']==0 and b['CUDA_compiles']==1 and b['exact_reversible_private_weight_block']and b['original_sm86_fast_math_retained']and not b['CUDA_arithmetic_flags_changed']and not b['class_or_CTE_layout_changed']and b['changed_Darcy_terms']==['LP','Lx']and b['unchanged_expression_terms']==['Gp','Da','gradJ','chain','FS','wall','force','material'],'Current113-object private one-kernel build required')
    for k in('program','source_capture','source_archive','baseline_source_capture','private_physical_source'):need(entry(b,k)==entry(r,k),'Run/build source binding differs: '+k)
    cap=read(r['source_capture']['path']);macro='C08_H18_LSTAR_ON='+str(int(mode=='on'))
    need(cap['passed']and cap['prepared_only']and cap['configuration']==configuration and cap['mode']==mode and cap['compile_macro']==macro and b['compile_macro']==macro and cap['changed_source_blocks']==1 and cap['exact_reverse_original_kernel_bytes']and cap['all_other_members_byte_equal']and cap['private_kernel']==r['private_physical_source']and not cap['host_main_material_objects_replaced']and not cap['class_or_CTE_layout_changed']and not cap['public_source_changed'],'Actual private kernel/source/macro differs; no RV host/CU allowed')
    for i,q in enumerate(b['calls']):
        tool=read(bind(q)['path']);owned(tool);consumed.append(q)
        if i==0:need('-D'+macro in tool['arguments'],'Actual original-flag NVCC mode macro missing')
    need(len(b['calls'])==2,'Exactly one NVCC and one link required');consumed.extend([buildstat,entry(b,'private_physical_object')])
    consumed.extend(entry(r,k)for k in('program','source_capture','source_archive','baseline_source_capture','private_physical_source','source_pre_file','source_run','source_native','input_xml','planned_steps','native_profile','Run_out','Run_csv','control_run','control_native'))
    control=read(r['control_run']['path']);need(control['passed']and control['solver_completed']and control['source_archive']==r['source_archive']and control['source_pre_file']==r['source_pre_file'],'Original AS03 control/source archive differs')
    material=entry(r,'native_profile');need(Path(material['path']).read_bytes()==Path(bind(control['native_profile'])['path']).read_bytes(),'Original17-key AS03 material profile bytes differ')
    source=read(r['source_native']['path']);need(source['passed']and source['certified_PRE']and source['samples']==1001 and source['completed_steps']==2000000 and same(r['source_pre_file']['path'],PRE),'Original same-material full PRE qualification required')
    rows=core.table(r['planned_steps']['path']);steps=[2000001]if profile=='off1'else[2000001,2000002]
    need(len(rows)==count and list(rows[0])==['part','completed_step','saved_step','time_s','dt_s']and[int(q['completed_step'])for q in rows]==steps,'Closed true1/2-update scalar launch plan differs')
    out=T/'outputs'/job;need(same(r['output'],out)and same(Path(r['Run_out']['path']).parent,out),'Actual output root differs')
    raw=r['PARTs'];need(len(raw)==count and[Path(q['path']).name for q in raw]==['Part_%04d.bi4'%i for i in range(count)],'Actual1/2-frame native list differs');consumed.extend(bind(q)for q in raw)
    need(len(r['particle_data_files'])>=count,'Actual native file inventory absent');consumed.extend(bind(q)for q in r['particle_data_files'])
    reader=read(READER_BUILD);need(reader['passed']and reader['consumed_stats_unchanged']and reader['stage']=='c08_h18_rv_native_r1.build'and reader['actual_typed_exit_code']==reader['actual_Win32_exit']==0 and reader['actual_link_objects']==7 and not reader['JSph_objects_linked']and reader['source_and_receiver_numeric_cores_byte_identical']and not reader['original_numeric_guards_changed']and reader['profiles']==['off1','debug2','window']and reader['receiver_material_CSV_keys']==17,'Passed unchanged seven-object reader required')
    program=entry(reader,'program');need(program['bytes']==603648,'Exact existing reader binary required');consumed.extend([stat(READER_BUILD),program]);return r,program,out,rows,source

def off_proof(bundle,consumed):
    path=L/'c08_h18_as03_n255_native_r1.check.json';g=read(path);need(g['passed']and g['consumed_stats_unchanged']and g['reader_invocations']==1,'Passed original AS03 native control required')
    done=entry(g,'native_completion');d=read(done['path']);root=Path(done['path']).parent;need(d['passed']and d['samples']==91 and d['completed_steps']==2180000,'Original genuine91-frame reference required')
    sealpath=L/'c08_h18_lstar_cpu_off_r1.build.json';seal=read(sealpath);need(seal['passed']and seal['consumed_stats_unchanged'],'Passed existing reference-export stat seal required')
    for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):
        refs=[q for q in seal['consumed']if same(q['path'],root/leaf)];need(refs and all(q==refs[0]for q in refs),'One previously sealed original typed export required');consumed.append(bind(refs[0]))
    ref=core.typed(root,6805,91,consumed)
    need(bundle['count']==1 and bundle['dtype']==ref['dtype']and(bundle['root']/'typed22_layout.csv').read_bytes()==(root/'typed22_layout.csv').read_bytes(),'True one-record original22 layout differs')
    with(bundle['root']/'typed22.bin').open('rb')as a,(root/'typed22.bin').open('rb')as b:
        need(struct.unpack('<III',a.read(12))==(6805,22,1)and struct.unpack('<III',b.read(12))==(6805,22,91),'Preserve actual1/91 headers');need(a.read(bundle['dtype'].itemsize)==b.read(bundle['dtype'].itemsize)and not a.read(1),'Actual first time+all22 record bytes differ')
    with(bundle['root']/'clocks.csv').open('rb')as a,(root/'clocks.csv').open('rb')as b:need(a.readline()==b.readline()and a.readline()==b.readline()and not a.readline(),'Original first signed-clock header/row bytes differ')
    consumed.extend([stat(path),done,stat(sealpath)]);return dict(compared_records=1,new_header_samples=1,reference_header_samples=91,all22_and_actual_time_bytes_equal=True,literal_layout_bytes_equal=True,literal_signed_clock_bytes_equal=True,reference_export_stat_seal=stat(sealpath),reference_seal_is_original_reader_exit=False,headers_rewritten=False,interpolation=False)

def review(profile,out,plan,source,consumed):
    count,end=JOBS[profile][1:3];donepath=out/'completion.json';metapath=out/'bedkeep_metadata.json';d,a=read(donepath),read(metapath)
    need(d['passed']and d['stage']=='c08_h18_wend_native_r1.receiver'and d['samples']==count and d['completed_steps']==end and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212,'Original native22 completion differs')
    expected={'actual_native_IDs_per_frame':6805,'actual_fixed_IDs':1805,'soil_IDs':5000,'ledger_checks':5000*count,'fixed_marker_checks':1805*count,'P0_bits_checks':6805*count,'rho_cache_bits_checks':5000*count,'kappa_nondecreasing_from_PRE_checks':5000*count,'nonempty_signed_intervals':count}
    for k,v in expected.items():need(d[k]==v,'Original native coverage differs: '+k)
    need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['FS23_pressure_checks']>0 and d['negative_x_ID_observations']==d['negative_z_ID_observations']==0 and d['NoPenOn_argument']is True and not d['native_rewritten'],'Original native safety/geometry/FS failed')
    need(a['passed']and a['stage']=='c08_h18_rv_native_r1.metadata'and a['profile']==profile and a['samples']==count and a['backend_argument']=='GPU'and a['receiver_material_CSV_keys']==17 and a['AS_coefficient_float_reference']==f32(.3)and a['AS_exponent_float_reference']==f32(2.55)and a['original_AV_private_keys_absent_headers']==count and not a['residual_viscosity_proven_by_reader']and not a['debug_profile_is_Release_bit_truth'],'Original body metadata differs; legacy RV note is not a sidecar requirement')
    bundle=core.typed(out,6805,count,consumed);scalar=float(source['actual_end_s']);previous=2000000
    for i,(clock,row)in enumerate(zip(bundle['clocks'],plan)):
        step=int(row['completed_step'])
        for _ in range(previous,step):scalar+=5e-6
        need(int(clock['part'])==int(row['part'])==i and int(clock['completed_step'])==step and int(clock['saved_step'])==int(row['saved_step'])==step-1 and bits(clock['time_s'])==bits(row['time_s'])==bits(scalar)==bits(bundle['frames'][i]['time'])and bits(clock['dt_s'])==bits(row['dt_s'])==bits(5e-6)and float(clock['signed_dterror_s'])<=1e-14 and clock['dterror_interval_empty']=='0'and int(clock['native_IDs'])==6805,'Actual scalar clock/Step/signed interval differs');need((bundle['frames'][i]['Idp'][:,0]==bundle['expected']).all(),'All fixed native IDs required');previous=step
    consumed.extend([stat(donepath),stat(metapath)]);proof=off_proof(bundle,consumed)if profile=='off1'else dict(Debug_is_Release_bit_truth=False,old_R_bit_equivalence_claimed=False)
    proof.update(Lstar_operator_proven_by_native=False,Lstar_operator_bound_by_actual_private_source_and_program=True,legacy_RV_metadata_unchanged=True,legacy_RV_sidecar_note_applied_to_this_job=False,actual_RV_sidecars_required=False);return donepath,metapath,proof

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=tuple(JOBS),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Separate root native admission required')
    job=JOBS[a.profile][0];runpath=L/(job+'.run.json');tag=job+'.native_r1';check=L/(tag+'.check.json');adpath=L/(tag+'.admission.json');out=T/'outputs'/job/'native_r1'
    if check.exists():
        old=read(check);need(old['passed']and old['source_run']==stat(runpath)and old['reader_invocations']==1,'Existing failed/changed native receipt protected');frozen(old['consumed']);frozen(old['files']);print('Existing valid native receipt; no reader launched',flush=True);return
    need(not out.exists()and not any((L/(tag+s)).exists()for s in('.start.json','.call.json','.log')),'Existing reader or partial output protected; no retry')
    consumed=[];result=dict(stage=tag,profile=a.profile,passed=False,native_completed=False,reader_program_completed=False,reader_launch_attempts=0,reader_invocations=0,solver_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_next_job=False)
    try:
        admission(adpath,a.profile,runpath);consumed=[stat(q)for q in(SCRIPT,NOTE,adpath,Path(m.__file__),Path(core.__file__),Path(core.core.__file__))];run,reader,runout,rows,source=inputs(a.profile,runpath,consumed)
        for proc in psutil.process_iter(['pid','exe','cmdline']):
            try:
                exe=proc.info.get('exe');argv=proc.info.get('cmdline')or[];need(not(exe and same(exe,reader['path']))and not any(same(v,out)for v in argv if isinstance(v,str)and str(out).lower()in v.lower()),'Existing exact reader/output owner active; no duplicate decode')
            except(psutil.NoSuchProcess,psutil.AccessDenied):continue
        argv=[str(reader['path']),'--receiver',str(a.profile),'psi0',str(runout/'data'),str(run['source_pre_file']['path']),str(run['planned_steps']['path']),str(run['native_profile']['path']),str(out)];p0=psutil.Process();owner=dict(pid=p0.pid,created_epoch=p0.create_time(),exe=p0.exe(),argv=p0.cmdline(),parent_pid=p0.ppid());frozen(consumed)
        m.save(L/(tag+'.start.json'),dict(stage=tag+'.start',owner=owner,source_run=stat(runpath),root_admission=stat(adpath),reader_build=stat(READER_BUILD),argv=argv,output=str(out),consumed=consumed,automatic_next_job=False,physical_acceptance=False));result.update(source_run=stat(runpath),reader_build=stat(READER_BUILD),root_admission=stat(adpath),owner=owner,argv=argv,reader_launch_attempts=1)
        result['actual_call']=m.invoke(tag,argv,T.parent);call=read(result['actual_call']['path']);result['reader_invocations']=int(call.get('child')is not None);owned(call);consumed.extend([stat(L/(tag+'.start.json')),result['actual_call'],bind(call['log'])]);need(call['owner']['pid']==owner['pid']and call['owner']['created_epoch']==owner['created_epoch']and call['child']['parent_pid']==owner['pid']and call['child']['argv']==argv and same(call['child']['exe'],reader['path']),'Actual native owned child differs');result['reader_program_completed']=True
        need(read(out/'completion.json')['passed'],'Actual reader core did not pass');result['native_completed']=True;done,meta,proof=review(a.profile,out,rows,source,consumed);files=[stat(out/f)for f in('completion.json','bedkeep_metadata.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv')];frozen(consumed);result.update(passed=True,native_completion=stat(done),metadata=stat(meta),files=files,proof=proof,consumed=consumed,consumed_stats_unchanged=True,reader_build_reused=True,typed22_schema_changed=False)
    except Exception as e:
        if(L/(tag+'.call.json')).exists():result['actual_call']=stat(L/(tag+'.call.json'));result['reader_invocations']=int(read(result['actual_call']['path']).get('child')is not None)
        elif result.get('reader_launch_attempts'):result.update(reader_invocations=None,reader_launch_not_handle_proven=True)
        result.update(first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,completed_reader_never_relaunched=True);raise
    finally:m.save(check,result)
if __name__=='__main__':main()
