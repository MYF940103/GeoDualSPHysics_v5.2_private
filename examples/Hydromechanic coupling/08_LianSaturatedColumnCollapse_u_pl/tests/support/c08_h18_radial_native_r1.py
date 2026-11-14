"""One separately admitted radial native read; no solver/build/VTK or chained job."""
import argparse
import json
import os
import struct
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
import c08_h18_storage_review_r2 as typedcore

T,L=m.T,m.L
SCRIPT=Path(__file__).resolve();TAG='c08_h18_radial_native_r1';NOTE=T/'notes'/(TAG+'.md')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
READER_BUILD=L/'c08_h18_rv_native_r1.build.json'
PRE=T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
JOBS={'off1':('c08_h18_rv_radial_off1_GPU_r1',1,2000001,'Release'),
      'debug2':('c08_h18_rv_radial_debug2_GPU_r1',2,2000002,'Debug'),
      'window':('c08_h18_rv_radial_window_GPU_r1',91,2180000,'Release')}
RVFILES=('C08H18RadialResidualPolicy.json','C08H18RadialResidual.csv','C08H18RadialManufactured.csv','C08H18RadialLimiterFixtures.csv')
need,read,stat,bind,entry,owned,same=typedcore.need,typedcore.read,typedcore.stat,typedcore.bind,typedcore.entry,typedcore.owned,typedcore.same

def bits(value):return struct.pack('<d',float(value))
def numeric_f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def frozen(receipt):
    for q in receipt:bind(q)

def admission(path,profile,runpath):
    a=read(path);job=JOBS[profile][0]
    need(a['authorized'] is True and a['phase']=='native' and a['profile']==profile and a['allowed_job']==job
         and a['execution_script']==stat(SCRIPT) and a['note']==stat(NOTE) and a['source_run']==stat(runpath)
         and a['reader_build']==stat(READER_BUILD) and a['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD
         and a['automatic_solver'] is False and a['automatic_next_job'] is False,'Exact independent current-root native admission required')
    return a

def inputs(profile,runpath,consumed):
    job,count,end,configuration=JOBS[profile];run=read(runpath);startpath=L/(job+'.start.json');start=read(startpath)
    need(run['stage']==job and run['profile']==profile and run['passed'] is True and run['solver_completed'] is True
         and run['consumed_stats_unchanged'] is True and run['actual_steps']==end and run['saved_frames']==count
         and run['actual_exit']==run['actual_Win32_exit']==run['actual_tool_exit']==0
         and run['ownership_failure'] is None and run['unsaved_state_reconstructed'] is False,
         'A successful actual radial owned run is required before any native invocation')
    need(run['RV_requested'] is (profile!='off1') and run['environment_override']=={'C08_RV_RADIAL_H18':'1' if profile!='off1' else None}
         and run['RV_operator']=='compression_only_radial_residual_limiter' and run['policy_schema']==3,'Actual radial environment/operator differs')
    callentry=entry(run,'actual_call');call=read(callentry['path']);owned(call)
    need(call['owner']['pid']==run['owner']['pid'] and call['owner']['created_epoch']==run['owner']['created_epoch']
         and call['child']['parent_pid']==run['owner']['pid'] and call['child']['argv']==run['argv']
         and start['owner']==run['owner'] and start['argv']==run['argv'] and start['solver_argv']==run['solver_argv']
         and start['environment_override']==run['environment_override'],'Original actual owner/child/start/argv differs')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','planned_steps'):
        need(start[key]==run[key],'Original run/start binding differs: '+key)
    radbuild=entry(run,'source_build');b=read(radbuild['path'])
    need(b['passed'] and b['consumed_stats_unchanged'] and b['configuration']==configuration and b['actual_link_objects']==114
         and b['retained_original_objects']==112 and b['private_objects']==2 and b['policy_schema']==3,'Actual frozen radial source build differs')
    for key in ('program','source_capture','source_archive'):need(entry(b,key)==entry(run,key),'Actual run/build binding differs: '+key)
    need(b['private_sources']==run['private_sources'] and set(b['private_sources'])=={'host','CUDA','header'},'Private source binding differs')
    consumed.extend(bind(q) for q in b['private_sources'].values())
    reader=read(READER_BUILD)
    need(reader['passed'] and reader['consumed_stats_unchanged'] and reader['stage']=='c08_h18_rv_native_r1.build'
         and reader['actual_link_objects']==7 and reader['JSph_objects_linked'] is False,'Reuse only the passed seven-object original reader')
    program=entry(reader,'program');pre=entry(run,'source_pre_file');plan=entry(run,'planned_steps');material=entry(run,'native_profile')
    need(same(pre['path'],PRE) and Path(material['path']).name=='native_profile.csv','Original PRE and actual17-key native profile required')
    rows=typedcore.table(plan['path']);keys=['part','completed_step','saved_step','time_s','dt_s']
    need(len(rows)==count and list(rows[0])==keys,'Actual five-column launch plan differs')
    steps=[2000001] if profile=='off1' else ([2000001,2000002] if profile=='debug2' else [2000001+2000*i for i in range(90)]+[2180000])
    need([int(q['completed_step'])for q in rows]==steps,'Closed native profile saved-step sequence differs')
    source=entry(run,'source_native');sd=read(source['path'])
    need(sd['passed'] and sd['certified_PRE'] and sd['samples']==1001 and sd['completed_steps']==2000000,'Full retained PRE qualification required')
    out=T/'outputs'/job;need(same(run['output'],out) and same(Path(entry(run,'Run_out')['path']).parent,out),'Actual run output root differs')
    if profile=='off1':need(run['RV_files_absent'] is True and all(not(out/f).exists()for f in RVFILES),'Default-OFF must have no radial sidecars')
    else:
        for key,leaf in zip(('rv_policy','rv_sidecar','rv_manufactured','rv_fixtures'),RVFILES):
            e=entry(run,key);need(same(e['path'],out/leaf),'Actual radial sidecar path differs');consumed.append(e)
    if profile=='debug2':
        need(run['memcheck_zero_errors_and_leaks'] is True and entry(run,'memcheck_actual_call')==callentry
             and call['actual_target'] and call['actual_target_Win32_exit']==0 and same(call['actual_target']['exe'],entry(run,'program')['path'])
             and call['actual_target']['argv']==run['solver_argv'],'Actual Debug memcheck/solver target evidence required')
    consumed.extend([stat(runpath),stat(startpath),callentry,radbuild,stat(READER_BUILD),program,pre,plan,material,source])
    consumed.extend(entry(run,k)for k in ('program','source_capture','source_archive','input_xml','Run_out','Run_csv'))
    raw=[out/'data'/('Part_%04d.bi4'%i)for i in range(count)]
    consumed.extend(stat(q)for q in raw)
    return run,reader,program,out,pre,plan,material,rows,sd

def off_byteproof(bundle,consumed):
    receipt=L/'c08_h18_as03_n255_native_r1.check.json';q=read(receipt)
    need(q['passed'] and q['consumed_stats_unchanged'] and q['reader_invocations']==1,'Passed retained original AS03 native control required')
    doneentry=entry(q,'native_completion');done=read(doneentry['path']);root=Path(doneentry['path']).parent
    need(done['passed'] and done['samples']==91 and done['completed_steps']==2180000,'Genuine original91-frame reference required')
    ref=typedcore.typed(root,6805,91,consumed)
    need(bundle['count']==1 and bundle['dtype']==ref['dtype'],'True one-record/layout comparison required')
    need((bundle['root']/'typed22_layout.csv').read_bytes()==(root/'typed22_layout.csv').read_bytes(),'Literal original typed22 layout differs')
    with(bundle['root']/'typed22.bin').open('rb')as a,(root/'typed22.bin').open('rb')as b:
        need(struct.unpack('<III',a.read(12))==(6805,22,1) and struct.unpack('<III',b.read(12))==(6805,22,91),'Preserve genuine1/91 headers')
        need(a.read(bundle['dtype'].itemsize)==b.read(bundle['dtype'].itemsize) and not a.read(1),'All22 arrays/actual time bytes differ in original first record')
    with(bundle['root']/'clocks.csv').open('rb')as a,(root/'clocks.csv').open('rb')as b:
        need(a.readline()==b.readline() and a.readline()==b.readline() and not a.readline(),'First genuine signed-clock header/row differs')
    consumed.extend([stat(receipt),doneentry])
    return dict(compared_records=1,new_header_samples=1,reference_header_samples=91,all22_and_actual_time_bytes_equal=True,
                literal_layout_bytes_equal=True,literal_signed_clock_bytes_equal=True,headers_rewritten=False,interpolation=False)

def native_review(profile,out,rows,source,consumed):
    count,end=JOBS[profile][1:3];donepath=out/'completion.json';metapath=out/'bedkeep_metadata.json';done,meta=read(donepath),read(metapath)
    need(done['passed'] and done['stage']=='c08_h18_wend_native_r1.receiver' and done['samples']==count and done['completed_steps']==end
         and done['typed_arrays']==22 and done['typed_bytes_per_particle']==212,'Original native22 completion profile differs')
    expected={'actual_native_IDs_per_frame':6805,'actual_fixed_IDs':1805,'soil_IDs':5000,'ledger_checks':count*5000,
              'fixed_marker_checks':count*1805,'P0_bits_checks':count*6805,'rho_cache_bits_checks':count*5000,
              'kappa_nondecreasing_from_PRE_checks':count*5000,'nonempty_signed_intervals':count}
    for key,v in expected.items():need(done[key]==v,'Original all-state native coverage differs: '+key)
    need(done['max_scalar_clock_error_s']<=1e-14 and done['max_ledger_relative_error']<=5e-13 and done['max_signed_dterror_s']<=1e-14
         and done['FS23_pressure_checks']>0 and done['negative_x_ID_observations']==done['negative_z_ID_observations']==0
         and done['NoPenOn_argument'] is True and done['native_rewritten'] is False,'Original native numerical/FS/geometry guards failed')
    need(meta['passed'] and meta['stage']=='c08_h18_rv_native_r1.metadata' and meta['profile']==profile and meta['backend_argument']=='GPU'
         and meta['samples']==count and meta['receiver_material_CSV_keys']==17 and meta['AS_coefficient_float_reference']==numeric_f32(.3)
         and meta['AS_exponent_float_reference']==numeric_f32(2.55) and meta['original_AV_private_keys_absent_headers']==count
         and meta['residual_viscosity_proven_by_reader'] is False and meta['debug_profile_is_Release_bit_truth'] is False,
         'Original RV-independent metadata/material/backend profile differs')
    bundle=typedcore.typed(out,6805,count,consumed);scalar=float(source['actual_end_s']);previous=2000000
    for part,(clock,plan)in enumerate(zip(bundle['clocks'],rows)):
        step=int(plan['completed_step'])
        for _ in range(previous,step):scalar+=5e-6
        need(int(clock['part'])==int(plan['part'])==part and int(clock['completed_step'])==step and int(clock['saved_step'])==int(plan['saved_step'])==step-1
             and bits(float(clock['time_s']))==bits(scalar) and bits(bundle['frames'][part]['time'])==bits(scalar)
             and bits(float(clock['dt_s']))==bits(float(plan['dt_s']))==bits(5e-6) and float(clock['signed_dterror_s'])<=1e-14
             and clock['dterror_interval_empty']=='0' and int(clock['native_IDs'])==6805,'Original actual scalar clock/Step/signed interval differs')
        need((bundle['frames'][part]['Idp'][:,0]==bundle['expected']).all(),'Complete native material IDs differ')
        previous=step
    consumed.extend([stat(donepath),stat(metapath)])
    proof=off_byteproof(bundle,consumed)if profile=='off1'else dict(Debug_is_Release_bit_truth=False,RV_certificates_proven_by_reader=False)
    return donepath,metapath,proof

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=tuple(JOBS),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized,'Separate root native admission required; author-only otherwise')
    job,count,end,configuration=JOBS[a.profile];runpath=L/(job+'.run.json');calltag=job+'.native_r1';check=L/(calltag+'.check.json');adpath=L/(calltag+'.admission.json');out=T/'outputs'/job/'native_r1'
    if check.exists():
        old=read(check);need(old['passed'] and old['source_run']==stat(runpath) and old['reader_invocations']==1,'Existing failed/changed native receipt preserved; no retry')
        frozen(old['consumed']);frozen(old['files']);print('Existing passed native receipt verified; no decoder launched',flush=True);return
    need(not out.exists() and not any((L/(calltag+s)).exists()for s in ('.start.json','.call.json','.log')),'Existing reader/partial native artifacts protected; diagnose offline, never overwrite')
    consumed=[];result=dict(stage=calltag,profile=a.profile,passed=False,native_completed=False,reader_program_completed=False,reader_launch_attempts=0,reader_invocations=0,solver_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_next_job=False)
    try:
        admission(adpath,a.profile,runpath);consumed=[stat(SCRIPT),stat(NOTE),stat(adpath),stat(Path(m.__file__)),stat(Path(typedcore.__file__)),stat(Path(typedcore.core.__file__))]
        run,reader,program,runout,pre,plan,material,rows,source=inputs(a.profile,runpath,consumed)
        for proc in psutil.process_iter(['pid','exe','cmdline']):
            try:
                exe=proc.info.get('exe');argv=proc.info.get('cmdline')or[]
                need(not(exe and same(exe,program['path']))and not any(same(v,out)for v in argv if isinstance(v,str)and str(out).lower()in v.lower()),'An existing exact reader/output owner is active; no duplicate decode')
            except(psutil.NoSuchProcess,psutil.AccessDenied):continue
        argv=[str(program['path']),'--receiver',str(a.profile),'psi0',str(runout/'data'),str(pre['path']),str(plan['path']),str(material['path']),str(out)]
        owner=psutil.Process();identity=dict(pid=owner.pid,created_epoch=owner.create_time(),exe=owner.exe(),argv=owner.cmdline(),parent_pid=owner.ppid())
        frozen(consumed);m.save(L/(calltag+'.start.json'),dict(stage=calltag+'.start',owner=identity,source_run=stat(runpath),root_admission=stat(adpath),reader_build=stat(READER_BUILD),argv=argv,output=str(out),consumed=consumed,physical_acceptance=False,automatic_next_job=False))
        result.update(source_run=stat(runpath),reader_build=stat(READER_BUILD),root_admission=stat(adpath),reader_launch_attempts=1,owner=identity,argv=argv)
        result['actual_call']=m.invoke(calltag,argv,T.parent)
        call=read(result['actual_call']['path']);result['reader_invocations']=int(call.get('child')is not None);owned(call)
        consumed.extend([stat(L/(calltag+'.start.json')),result['actual_call'],bind(call['log'])])
        need(call['owner']['pid']==identity['pid'] and call['owner']['created_epoch']==identity['created_epoch'] and call['child']['parent_pid']==identity['pid']
             and call['child']['argv']==argv and same(call['child']['exe'],program['path']),'Actual native child handle/owner/argv differs')
        result['reader_program_completed']=True
        observed=read(out/'completion.json');need(observed['passed'] is True,'Completed reader lacks successful native core completion')
        result['native_completed']=True
        done,meta,proof=native_review(a.profile,out,rows,source,consumed)
        files=[stat(out/f)for f in ('completion.json','bedkeep_metadata.json','typed22.bin','typed22_layout.csv','clocks.csv')]
        frozen(consumed);result.update(passed=True,native_completion=stat(done),metadata=stat(meta),files=files,proof=proof,consumed=consumed,consumed_stats_unchanged=True,typed22_schema_changed=False,reader_build_reused=True)
    except Exception as e:
        if(L/(calltag+'.call.json')).exists():
            result['actual_call']=stat(L/(calltag+'.call.json'));failedcall=read(result['actual_call']['path']);result['reader_invocations']=int(failedcall.get('child')is not None)
        elif result.get('reader_launch_attempts'):result.update(reader_invocations=None,reader_launch_not_handle_proven=True)
        result.update(first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,completed_reader_never_relaunched=True)
        raise
    finally:m.save(check,result)

if __name__=='__main__':main()
