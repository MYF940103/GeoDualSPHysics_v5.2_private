"""Two independent root-admitted GPU implementation smokes; no reader, queue or next job."""
import argparse,csv,math,os,re,shutil,struct,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
T,C,L=m.T,m.C,m.L;SCRIPT=Path(__file__).resolve();NOTE=T/'notes/c08_h18_lstar_gpu_smoke_r1.md'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';CONTROL='c08_h18_as03_n255_r1';DT=5e-6;PRESTEP=2000000
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
JOBS={'off1':dict(tag='c08_h18_lstar_gpu_off1_r1',configuration='Release',mode='off',steps=(2000001,),updates=1,frames=1),'debug2':dict(tag='c08_h18_lstar_gpu_debug2_r1',configuration='Debug',mode='on',steps=(2000001,2000002),updates=2,frames=2)}
def paths(job):return {k:L/(job['tag']+s)for k,s in dict(prep='.prepare.json',prepare_admission='.root_prepare_admission.json',run_admission='.root_run_admission.json',start='.start.json',call='.call.json',log='.log',run='.run.json',status='.status.json').items()}
def f32(x):return struct.unpack('<f',struct.pack('<f',float(x)))[0]
def admission(path,profile,phase,build):
    q=m.read(path);m.need(q['authorized']and q['allowed_job']==JOBS[profile]['tag']and q['profile']==profile and q['phase']==phase and q['execution_script']==m.stat(SCRIPT)and q['note']==m.stat(NOTE)and q['source_build']==m.stat(build)and q['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD and not q['automatic_native']and not q['automatic_next_job']and not q.get('terminal_queue',False)and not q.get('watcher',False),'Separate exact current-root admission required');return q
def copy(source,dest):
    m.need(not dest.exists(),'Protect copied input');shutil.copy2(source,dest);m.need(dest.read_bytes()==Path(source).read_bytes(),'Byte-identical original input copy required');return m.stat(dest)
def plan(job,t0):
    clock=float(t0);old=PRESTEP;out=[];source=[]
    for i,step in enumerate(job['steps']):
        for _ in range(old,step):before=clock;clock+=DT
        out.append(dict(part=i,completed_step=step,saved_step=step-1,time_s=clock,dt_s=DT));source.append(before);old=step
    m.need(old-PRESTEP==job['updates']and len(out)==job['frames'],'Closed scalar update plan differs');return out,source,clock

def prepare(profile):
    job=JOBS[profile];p=paths(job);out=T/'outputs'/job['tag'];stepfile=T/'configs'/(job['tag']+'.steps.csv');bp=L/('c08_h18_lstar_gpu_'+job['configuration']+'_'+job['mode']+'_r1.build.json');before=[]
    m.need(not out.exists()and not stepfile.exists()and not p['prep'].exists()and all(not p[k].exists()for k in('run','call','log','start','status')),'Protect existing attempt/partial; no reuse')
    try:
        admission(p['prepare_admission'],profile,'prepare',bp);cr=L/(CONTROL+'.run.json');cn=L/'c08_h18_as03_n255_native_r1.check.json';original=m.read(cr);native=m.read(cn);b=m.read(bp)
        m.need(original['passed']and original['solver_completed']and original['consumed_stats_unchanged']and original['actual_steps']==2180000 and original['saved_frames']==91 and original['actual_exit']==original['actual_Win32_exit']==original['actual_tool_exit']==0 and original['AS_coefficient']==.3 and original['AS_exponent']==2.55 and original['hdp']==1.8 and original['fixed_dt_s']==DT and not original['keep_bed_overlap']and native['passed']and native['reader_invocations']==1 and native['consumed_stats_unchanged'],'Original admitted AS03 generated seed/native required')
        m.need(b['passed']and b['consumed_stats_unchanged']and b['configuration']==job['configuration']and b['mode']==job['mode']and b['receiver_C_bare_enabled']==(job['mode']=='on')and b['retained_original_objects']==112 and b['private_objects']==1 and b['actual_link_objects']==113 and b['host_compiles']==0 and b['CUDA_compiles']==1 and b['exact_reversible_private_weight_block']and b['original_sm86_fast_math_retained']and not b['CUDA_arithmetic_flags_changed']and b['source_archive']==original['source_archive']and b['baseline_source_capture']==original['source_capture'],'Exact independently passed private113-object Lstar build required')
        cap=m.read(m.bind(b['source_capture'])['path']);m.need(cap['passed']and cap['prepared_only']and cap['configuration']==job['configuration']and cap['mode']==job['mode']and cap['compile_macro']=='C08_H18_LSTAR_ON='+str(int(job['mode']=='on'))and cap['changed_source_blocks']==1 and cap['exact_reverse_original_kernel_bytes']and cap['all_other_members_byte_equal']and not cap['class_or_CTE_layout_changed'],'Actual private kernel/macro source proof required')
        before=[m.stat(q)for q in(SCRIPT,NOTE,p['prepare_admission'],cr,cn,bp)]+[m.bind(original[k])for k in('source_pre_file','source_run','source_native','source_archive','input_xml','native_profile','planned_steps','actual_call')]+[m.bind(native[k])for k in('actual_call','native_completion','metadata','reader_build')]+[m.bind(b[k])for k in('program','source_capture','source_archive','baseline_source_capture','private_physical_source')]+[m.bind(q)for q in b['runtime']]
        source=m.read(original['source_native']['path']);m.need(source['passed']and source['certified_PRE']and source['expected_handoff_schema']==2 and source['same_material_plastic_PRE']and source['completed_steps']==PRESTEP and source['samples']==1001 and source['soil_IDs']==5000 and source['fixed_IDs']==2060 and source['declared_Kernel_XML_CSV']==2 and math.isfinite(float(source['actual_end_s'])),'Original certified Wendland schema2 PRE contract required; not equilibrium proof')
        x=ET.parse(original['input_xml']['path']).getroot();pars={q.get('key'):q.get('value')for q in x.findall('execution/parameters/parameter')};m.need(all(float(pars[k])==v for k,v in dict(Kernel=2,DtFixed=DT,TimeMax=10.9,TimeOut=.01).items())and all(f32(pars[k])==f32(v)for k,v in dict(Visco=.1,ArtificialStressCoef=.3,ArtificialStressExp=2.55).items()),'Unchanged original XML physics/cadence required');profile_rows=m.table(original['native_profile']['path']);m.need(len(profile_rows)==17 and all(list(q)==['key','value']for q in profile_rows)and len({q['key']for q in profile_rows})==17,'Original17-key profile required')
        seed=Path(original['input_xml']['path']).with_suffix('');m.need(len(original['seed'])==3,'Original triple required');entries=[]
        for suffix in('.xml','.bi4','_Normals.nbi4'):
            q=Path(str(seed)+suffix);e=next(z for z in original['seed']if Path(z['path']).resolve()==q.resolve());entries.append(m.bind(e));before.append(e)
        rows,sources,end=plan(job,source['actual_end_s']);old=m.table(original['planned_steps']['path']);m.need(len(old)==91 and int(old[0]['completed_step'])==2000001 and float(old[0]['time_s'])==rows[0]['time_s'],'Genuine retained first saved scalar clock required')
        oldcap=L/'c08_h18_rv_radial_off1_GPU_r1.run.json';proof=m.read(oldcap);m.need(proof['passed']and proof['solver_completed']and proof['actual_steps']==2000001 and proof['saved_frames']==1 and proof['solver_argv'][-1]=='-nsteps:2000001','Actual previously passed absolute-step cap semantics required');before.append(m.stat(oldcap));m.verify(before);out.mkdir();seeds=[copy(e['path'],out/Path(e['path']).name)for e in entries];prof=copy(original['native_profile']['path'],out/'native_profile.csv')
        with stepfile.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        argv=[str(b['program']['path']),'-gpu:0','-stable','-mdbc_freeslip:1',str(out/seed.name),str(out),'-dirdataout','data','-svres','-nsteps:'+str(job['steps'][-1])];m.verify(before)
        m.save(p['prep'],dict(stage=job['tag']+'.prepare',passed=True,prepared_only=True,profile=profile,configuration=job['configuration'],mode=job['mode'],program=b['program'],source_build=m.stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],baseline_source_capture=b['baseline_source_capture'],private_physical_source=b['private_physical_source'],runtime=b['runtime'],source_pre_file=original['source_pre_file'],source_run=original['source_run'],source_native=original['source_native'],control_run=m.stat(cr),control_native=m.stat(cn),input_xml=seeds[0],seed=seeds,native_profile=prof,planned_steps=m.stat(stepfile),planned_rows=rows,save_source_clocks_s=sources,actual_source_time_s=source['actual_end_s'],planned_actual_end_s=end,global_nsteps_limit=job['steps'][-1],new_updates=job['updates'],expected_saved_frames=job['frames'],fixed_dt_s=DT,argv=argv,cwd=str(C),output=str(out),execution_script=m.stat(SCRIPT),note=m.stat(NOTE),root_prepare_admission=m.stat(p['prepare_admission']),consumed=before,consumed_stats_unchanged=True,seed_copied_byte_identical=True,generated_basename_preserved=seed.name,XML_TimeMax_unchanged=10.9,XML_TimeOut_unchanged=.01,GenCase_invocations=0,solver_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False,physical_acceptance=False))
    except Exception as e:
        if not p['prep'].exists():m.save(p['prep'],dict(stage=job['tag']+'.prepare',passed=False,first_failure=str(e),consumed=before,partial_outputs_preserved=True,solver_invocations=0,automatic_retry=False))
        raise

def summary(path):
    lines=path.read_text(encoding='utf-8-sig').splitlines();m.need(len(lines)==2 and lines[0].startswith('#RunName;'),'One actual Run.csv row required');keys,values=lines[0][1:].split(';'),lines[1].split(';');i=keys.index('Configuration');m.need(len(set(keys))==len(keys)and len(values)==len(keys)+1,'Original embedded AS semicolon only');values=values[:i]+[values[i]+';'+values[i+1]]+values[i+2:];q=dict(zip(keys,values));asv=re.findall(r'(?:^| - )AS_Bui2008\(([^;]+);([^\)]+)\)(?= - |$)',q['Configuration']);m.need(len(asv)==1 and q['Configuration'].count(';')==1 and all(f32(a)==f32(b)for a,b in zip(asv[0],(.3,2.55)))and'Wendland'in q['Configuration'],'Actual AS03/n255/Wendland configuration required');return q

def survivors(call,program):
    result=[]
    for key in('child','actual_target'):
        expected=call.get(key)if call else None
        if not expected:continue
        try:
            p=psutil.Process(expected['pid']);result.append(dict(role=key,expected=expected,current=dict(pid=p.pid,created_epoch=p.create_time(),exe=p.exe(),argv=p.cmdline(),parent_pid=p.ppid()),ownership_reaffirmed=False))
        except psutil.NoSuchProcess:result.append(dict(role=key,expected=expected,current=None))
        except psutil.AccessDenied:result.append(dict(role=key,expected=expected,access_denied=True))
    return result

def run(profile):
    job=JOBS[profile];p=paths(job);out=T/'outputs'/job['tag'];bp=L/('c08_h18_lstar_gpu_'+job['configuration']+'_'+job['mode']+'_r1.build.json');m.need(all(not p[k].exists()for k in('run','start','call','log','status')),'Protect existing/partial owned attempt');before=[];prep=None;call=None
    result=dict(stage=job['tag'],passed=False,solver_completed=False,profile=profile,configuration=job['configuration'],mode=job['mode'],solver_invocations=0,solver_launch_attempts=0,native_review_pending=True,physical_acceptance=False,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False,terminal_queue=False,watcher=False,unsaved_state_reconstructed=False)
    try:
        prep=m.read(p['prep']);ad=admission(p['run_admission'],profile,'run',bp);m.need(prep['passed']and prep['prepared_only']and prep['consumed_stats_unchanged']and prep['profile']==profile and prep['mode']==job['mode']and prep['execution_script']==m.stat(SCRIPT)and prep['note']==m.stat(NOTE)and ad['preparation']==m.stat(p['prep']),'Exact independent prepared smoke admission required')
        before=[m.stat(q)for q in(SCRIPT,NOTE,p['prep'],p['run_admission'])]+[m.bind(prep[k])for k in('program','source_build','source_capture','source_archive','baseline_source_capture','private_physical_source','source_pre_file','source_run','source_native','control_run','control_native','input_xml','native_profile','planned_steps')]+[m.bind(q)for q in prep['seed']+prep['runtime']];program=Path(prep['program']['path']);argv=list(prep['argv']);m.need(out.is_dir()and not(out/'data').exists()and not(out/'Run.out').exists()and argv[0]==str(program)and argv[-1]=='-nsteps:'+str(PRESTEP+job['updates'])and prep['global_nsteps_limit']==PRESTEP+job['updates'],'Fresh original-input bounded output required')
        for proc in psutil.process_iter(['pid','exe']):
            try:m.need(not proc.info['exe']or Path(proc.info['exe']).resolve()!=program.resolve(),'Exact private program already active; no duplicate')
            except(psutil.NoSuchProcess,psutil.AccessDenied):pass
        tool=[str(x)for x in argv]
        if profile=='debug2':before.append(m.stat(SAN));tool=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','99',*tool]
        ownerproc=psutil.Process();owner=dict(pid=ownerproc.pid,created_epoch=ownerproc.create_time(),exe=ownerproc.exe(),argv=ownerproc.cmdline(),parent_pid=ownerproc.ppid());env=dict(os.environ);m.verify(before);m.save(p['start'],dict(stage=job['tag']+'.start',owner=owner,preparation=m.stat(p['prep']),root_admission=m.stat(p['run_admission']),program=prep['program'],source_build=prep['source_build'],source_capture=prep['source_capture'],source_archive=prep['source_archive'],source_pre_file=prep['source_pre_file'],input_xml=prep['input_xml'],planned_steps=prep['planned_steps'],argv=tool,solver_argv=argv,cwd=prep['cwd'],consumed=before,automatic_next_job=False,physical_acceptance=False))
        result.update({k:prep[k]for k in('program','source_build','source_capture','source_archive','baseline_source_capture','private_physical_source','runtime','source_pre_file','source_run','source_native','control_run','control_native','input_xml','seed','planned_steps','native_profile','actual_source_time_s','planned_actual_end_s','global_nsteps_limit','new_updates','expected_saved_frames')});result.update(owner=owner,preparation=m.stat(p['prep']),root_admission=m.stat(p['run_admission']),argv=tool,solver_argv=argv,output=str(out),fixed_dt_s=DT,solver_launch_attempts=1)
        result['actual_call']=m.invoke(job['tag'],tool,Path(prep['cwd']),env=env,target=program if profile=='debug2'else None)
    except Exception as e:result['first_failure']=str(e)
    if p['call'].exists():
        result['actual_call']=m.stat(p['call']);call=m.read(p['call']);target=call.get('actual_target')if profile=='debug2'else call.get('child');result.update(actual_tool_exit=call.get('actual_Popen_wait_exit'),actual_tool_Win32_exit=call.get('actual_Win32_exit'),actual_Win32_exit=call.get('actual_target_Win32_exit')if profile=='debug2'else call.get('actual_Win32_exit'),actual_exit=call.get('actual_target_Win32_exit')if profile=='debug2'else call.get('actual_Win32_exit'),ownership_failure=call.get('ownership_failure'),solver_invocations=1 if target else None)
        result['solver_identity']=target;result['solver_program_identity_matches']=bool(target and Path(target['exe']).resolve()==Path(prep['program']['path']).resolve());result['actual_solver_argv_observed']=bool(target and target.get('argv')is not None and len(target['argv'])==len(prep['argv'])and Path(target['argv'][0]).resolve()==Path(prep['argv'][0]).resolve()and target['argv'][1:]==prep['argv'][1:])
    try:
        m.need(call is not None and result.get('solver_program_identity_matches')and result['actual_exit']==result['actual_Win32_exit']==0,'Actual native solver handle normal exit required');text=(out/'Run.out').read_text(encoding='utf-8-sig');m.need('Finished execution (code=0).'in text and '[Simulation INTERRUPTED'not in text and 'certified same-material plastic schema/contract2'in text,'Actual normal schema2 completion required')
        # Seal solver completion before later argv/summary/memcheck review; never rerun after this point.
        result.update(solver_completed=True,Run_out=m.stat(out/'Run.out'));q=summary(out/'Run.csv');frames=sorted((out/'data').glob('Part_*.bi4'));m.need(int(q['Steps'])==prep['global_nsteps_limit']and int(q['PartFiles'])==job['frames']and int(q['PartsOut'])==0 and[q.name for q in frames]==['Part_%04d.bi4'%i for i in range(job['frames'])],'Actual global-step/frame/no-loss coverage differs');result.update(summary=q,actual_steps=int(q['Steps']),saved_frames=len(frames),Run_csv=m.stat(out/'Run.csv'),PARTs=[m.stat(q)for q in frames],particle_data_files=[m.stat(q)for q in sorted((out/'data').iterdir())if q.is_file()])
        m.need(result['actual_solver_argv_observed']and result['actual_tool_exit']==result['actual_tool_Win32_exit']==0 and result['ownership_failure']is None and'first_failure'not in result and result['solver_identity']['creation_filetime_100ns']>0 and result['solver_identity']['parent_pid']is not None,'Actual tool/solver creation/argv/ownership must pass')
        if profile=='debug2':
            log=Path(call['log']['path']).read_text(encoding='mbcs',errors='replace');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',log);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',log);m.need(errors and leaks and all(int(x.replace(',',''))==0 for x in errors)and all(int(x.replace(',',''))==int(y.replace(',',''))==0 for x,y in leaks),'Actual memcheck zero errors/leaks absent');result.update(memcheck_actual_call=result['actual_call'],memcheck_zero_errors_and_leaks=True)
        m.verify(before);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as e:result.setdefault('first_failure',str(e))
    if(out/'Run.out').exists():
        text=(out/'Run.out').read_text(encoding='utf-8-sig',errors='replace');hit=re.search(r'^Text: (.*)$',text,re.M);result.update(Run_out=m.stat(out/'Run.out'),first_engine_exception_text=hit[1]if hit else None,observed_saved_files=len(list((out/'data').glob('Part_*.bi4'))))
    if call and Path(call['log']['path']).is_file():
        raw=Path(call['log']['path']).read_text(encoding='mbcs',errors='replace');lines=[s for s in raw.splitlines()if re.match(r'^Part_\d+\s',s)];result.update(console_log=m.bind(call['log']),last_original_console_PART_line=lines[-1]if lines else None)
    try:unchanged=all(m.stat(q['path'])==q for q in before)
    except Exception as e:unchanged=False;result['terminal_stat_error']=str(e)
    if not unchanged:result['passed']=False
    result.update(consumed=before,consumed_stats_unchanged=unchanged)
    if result['solver_launch_attempts']and call is None:result.update(solver_invocations=None,solver_launch_outcome_not_handle_proven=True)
    if not result['passed']:result['surviving_process_observations']=survivors(call,Path(prep['program']['path'])if prep else None)
    m.save(p['run'],result);m.save(p['status'],dict(stage=job['tag'],status='completed_pending_unique_native_review'if result['passed']else'completed_solver_review_failed'if result['solver_completed']else'failed_preserved_no_retry',run=m.stat(p['run']),automatic_native=False,automatic_next_job=False,terminal_queue=False,physical_acceptance=False));return 0 if result['passed']else 1
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('prepare','run'));p.add_argument('--profile',choices=tuple(JOBS),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();m.need(a.execution_authorized,'Separate root prepare/run authorization required')
    if a.phase=='prepare':prepare(a.profile)
    else:raise SystemExit(run(a.profile))
