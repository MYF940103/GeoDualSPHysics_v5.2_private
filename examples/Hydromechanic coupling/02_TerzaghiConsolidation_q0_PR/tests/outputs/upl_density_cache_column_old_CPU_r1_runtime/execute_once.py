import csv,datetime,json,os,re,shutil,subprocess
from pathlib import Path
import psutil
R=Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b');T=R/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests';A=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests';L=T/'logs';GROUP='upl_density_cache_column_CPU_r1'
OLD=Path(__file__).resolve().parent;SEED=T/'outputs/upl_gpu_stabilizers_short_r1_seed/upl_gpu_stabilizers_short_r1'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def need(b,s):
    if not b:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8',newline='\n')as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def identity(pid):
    p=psutil.Process(pid)
    with p.oneshot():return dict(pid=p.pid,created_epoch=p.create_time(),parent_pid=p.ppid(),exe=p.exe(),arguments=p.cmdline(),working_directory=p.cwd())
def changes(rows):
    result=[]
    for d in rows:
        try:a=stat(d['path']);ok=Path(a['path']).samefile(d['path'])and a['bytes']==d['bytes']and a['mtime_ns']==d['mtime_ns']
        except OSError:a=None;ok=False
        if not ok:result.append(dict(expected=d,observed=a))
    return result
def no_solver():
    hits=[]
    for p in psutil.process_iter(['pid','name','exe']):
        if 'dualsphysics'in(p.info['name']or'').casefold():hits.append(p.info)
    need(not hits,'An actual DualSPHysics process is already active: '+str(hits))
OWNER=identity(os.getpid());protected=[];copies=[];runs=[];stage='preparation'
try:
    no_solver();need(set(p.name for p in OLD.iterdir())=={'execute_once.py'},'Fresh old runtime required');need(not list(L.glob(GROUP+'.*')),'Fresh group log collision')
    source_paths=[R/'src/source'/n for n in ['JSphCpu.cpp','JSphGpu.cpp','JSphGpuSimple_ker.h','JSphGpuSimple_ker.cu','JSphGpu_ker.cu']]
    runtime=[R/'bin/windows'/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']]
    seed_paths=[SEED.with_suffix('.xml'),SEED.with_suffix('.bi4'),SEED.parent/(SEED.name+'_Normals.nbi4')]
    prep_path=L/'upl_gpu_stabilizers_short_r1.prepare.json';prep=read(prep_path);need(prep['passed']and Path(prep['input_prefix'])==SEED and prep['dt_s']==6.250143051147461e-6,'Retained admitted input differs')
    dt=prep['dt_s'];clock_path=Path(prep['clock_prefix']['path'])
    with clock_path.open(newline='',encoding='utf-8')as f:reader=csv.DictReader(f);clock_header=reader.fieldnames;plan=[r for r in reader if int(r['completed_steps'])<=128]
    actual_end=0.
    for i in range(128):actual_end+=dt
    need([int(r['completed_steps'])for r in plan]==[0,20,40,59,79,98,118],'Unexpected unchanged save-schedule prefix')
    plan.append(dict(part='7',completed_steps='128',saved_step='127',time_s=repr(actual_end),dt_s=repr(dt),post_open_by_completed_step='0',target_time_s='0.0008544921875',forced_final='1'))
    planned=L/(GROUP+'.planned_clock.csv')
    with planned.open('x',newline='',encoding='utf-8')as f:w=csv.DictWriter(f,fieldnames=clock_header);w.writeheader();w.writerows(plan)
    jobs=[];inputs=source_paths+runtime+seed_paths+[prep_path,clock_path,planned,Path(__file__),A/'logs/upl_density_cache_CPU_r3.check.json',A/'logs/upl_density_cache_GPU_compare_r3.check.json']
    for variant,bname in [('old','upl_wall_gpuport_DebugCPU_r1.build.json'),('new','upl_density_cache_DebugCPU_r1.build.json')]:
        tag='upl_density_cache_column_'+variant+'_CPU_r1';out=T/'outputs'/tag;directory=T/'outputs'/(tag+'_runtime');need(not out.exists(),'Fresh solver output required')
        if variant=='new':directory.mkdir()
        bp=A/'logs'/bname;b=read(bp);need(b['passed']and b.get('actual_typed_exit_code',b.get('exit_code'))==0 and not changes([b['program']]),'Actual sealed '+variant+' CPU program differs')
        source=Path(b['program']['path']);dest=directory/source.name
        for p in [source]+runtime:
            q=directory/p.name;need(not q.exists(),'Runtime copy collision');shutil.copy2(p,q);need(p.stat().st_size==q.stat().st_size and p.stat().st_mtime_ns==q.stat().st_mtime_ns,'Program/runtime copy2 SMT mismatch');copies.append(stat(q))
        args=['-cpu','-ompthreads:1','-stable','-mdbc_freeslip',str(SEED),str(out),'-dirdataout','data','-svres','-nsteps:128']
        jobs.append(dict(variant=variant,tag=tag,output_directory=str(out),program=stat(dest),source_program=b['program'],source_build=stat(bp),arguments=args,working_directory=str(R/'src')));inputs.extend([source,bp,Path(b['source'])])
    for case in [T.parent,R/'examples/Hydromechanic coupling/04_CryerProblem_PR']:
        inputs.extend(p for p in case.iterdir()if p.is_file()and p.suffix.lower()in['.xml','.bat'])
    C=R/'examples/Hydromechanic coupling/04_CryerProblem_PR';inputs.extend([C/'Cryer_upl_nu030_Windows_RTXA6000_r1.zip',C/'support/README_cryer_upl_nu030_r1.md'])
    for d in [C/'support/bin_upl_r1',C/'support/upl_seed_nu030_r1']:inputs.extend(p for p in d.iterdir()if p.is_file())
    protected=list({str(Path(p).resolve()).casefold():stat(p)for p in inputs}.values())
    manifest=L/(GROUP+'.inputs.json');save(manifest,dict(stage=GROUP+'.inputs',prepared=True,jobs=jobs,shared_seed=[stat(p)for p in seed_paths],source_current_five=[stat(p)for p in source_paths],runtime_copies=copies,protected=protected,steps_limit=128,dt_s=dt,planned_clock_CSV=stat(planned),plan_is_not_native_clock_observation=True,XML_dt_output_schedule_unchanged=True,SHA_scans=0,physical_acceptance=False))
    save(T/'notes'/(GROUP+'.json'),dict(stage=GROUP,scope='Root-authorized old/new CPU Debug one fresh128-update admitted constant-k column each. Same seed/XML/dt/save schedule; only step cap/output differ. Native/physical review is separate and pending.',source_input_manifest=str(manifest),new_cache_and_old_legacy_Rhop_Arc_semantics_differ=True,no_half_or_reference_chain=True,metadata_policy='size/mtime only; no SHA',reader_or_GPU_invoked=False,physical_acceptance=False))
    for job in jobs:
        stage=job['tag'];no_solver();need(not changes(protected)and not changes(copies),'Input/program/runtime/formal/Cryer SMT changed before solver')
        tag=job['tag'];lp=L/(tag+'.log');started=now()
        with lp.open('xb')as f:
            p=subprocess.Popen([job['program']['path']]+job['arguments'],cwd=job['working_directory'],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);child=identity(p.pid);need(child['parent_pid']==OWNER['pid'],'Actual solver parent mismatch');save(L/(tag+'.start.json'),dict(stage=tag+'.start',owner=OWNER,solver=child,job=job,source_input_manifest=stat(manifest),started_utc=started,SHA_scans=0));print(tag,'ACTUAL START',p.pid,flush=True);rc=p.wait()
        call=L/(tag+'.call.json');save(call,dict(stage=tag+'.run_call',job=job,owner=OWNER,solver=child,actual_exit_code=rc,direct_Popen_wait=True,started_utc=started,ended_utc=now(),log=stat(lp),SHA_scans=0));print(tag,'SEALED EXIT',rc,flush=True)
        need(rc==0,'Actual solver failed; no retry');out=Path(job['output_directory']);raw=(out/'Run.out').read_text(encoding='utf-8',errors='replace')
        with(out/'Run.csv').open(newline='',encoding='utf-8-sig')as f:summary=list(csv.DictReader(f,delimiter=';'))
        need(len(summary)==1,'Unexpected actual Run.csv rows');s=summary[0];need(int(s['Steps'])==128 and int(s['Np'])==1040 and int(s['Nbound'])==40 and int(s['Nfixed'])==40 and int(s['PartFiles'])==8 and int(s['PartsOut'])==int(s['PartsOutRhop'])==int(s['PartsOutVel'])==0,'Actual step/particle/save/exclusion summary failed')
        need('Finished execution (code=0).'in raw and 'DTs adjusted to DtMin............: 0'in raw and 'Excluded particles...............: 0'in raw,'Normal termination/original step/exclusion guard failed')
        hg=re.search(r'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)\s+SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)',raw);need(hg is not None and list(map(int,hg.groups()))==[256,128,128,256,129,127],'Original HG stage/cache counters failed')
        part=[]
        for line in raw.splitlines():
            m=re.match(r'^Part_(\d+)\s+([0-9.eE+-]+)\s+(\d+)\s+(\d+)\s+',line)
            if m:part.append(dict(part=int(m[1]),time_s_as_printed=m[2],completed_steps=int(m[3]),interval_steps=int(m[4]),raw_line=line))
        need([r['part']for r in part]==list(range(1,8))and[r['completed_steps']for r in part]==[20,40,59,79,98,118,128],'Actual unchanged save-clock step sequence failed')
        need(float(s['PhysicalTime'])==float(format(actual_end,'.6f'))and float(part[-1]['time_s_as_printed'])==float(format(actual_end,'.6f')),'Actual printed endpoint differs from128 scalar updates')
        files=[stat(q)for q in(out/'data').glob('Part_[0-9][0-9][0-9][0-9].bi4')];need(len(files)==8 and{Path(d['path']).name for d in files}=={'Part_'+str(i).zfill(4)+'.bi4'for i in range(8)},'Actual raw native file membership failed')
        need(not changes(protected)and not changes(copies),'Consumed/formal/Cryer SMT changed after solver')
        record=dict(stage=tag+'.run',passed=True,job=job,source_input_manifest=stat(manifest),source_start=stat(L/(tag+'.start.json')),source_call=stat(call),actual_exit_code=rc,Run_csv=s,HG_counters=list(map(int,hg.groups())),part0_actual_log=[x for x in raw.splitlines()if x.startswith('Part_0000')],actual_logged_part_records=part,clock_precision='Run.out/Run.csv printed6decimals; exact native clocks not decoded',planned_clock_CSV=stat(planned),planned_scalar_end_s=actual_end,files=files,metadata_files=[stat(q)for q in[out/'Run.out',out/'Run.csv',out/'data/PartInfo.ibi4']if q.exists()],run_out_last_lines=raw.splitlines()[-8:],simulation_end_section=raw[raw.index('[Simulation finished'):raw.index('[CPU Timers]')].splitlines(),no_exclusion_reported=True,existing_internal_finite_domain_step_load_guards_unchanged=True,all22_native_arrays_review_pending=True,exact_native_clock_and_signed_dt_review_pending=True,raw_payload_not_decoded=True,consumed_stats_unchanged=True,SHA_scans=0,physical_acceptance=False)
        rp=L/(tag+'.run.json');save(rp,record);runs.append(stat(rp))
    save(L/(GROUP+'.check.json'),dict(stage=GROUP,passed=True,runs=runs,source_input_manifest=stat(manifest),actual_solver_invocations=2,actual_owned_exit_codes=[0,0],actual_steps_each=128,actual_saves_each=8,XML_dt_save_plan_unchanged=True,consumed_source_program_runtime_formal_Cryer_stats_unchanged=not changes(protected)and not changes(copies),native_and_physical_review_pending=True,reader_invoked=False,SHA_scans=0,physical_acceptance=False));print('BOTH128UPDATE RUNS CLOSED; NATIVE/PYSICAL REVIEW PENDING',flush=True)
except BaseException as e:
    fp=L/(GROUP+'.failure.json')
    if not fp.exists():save(fp,dict(stage=GROUP+'.failure',failed_stage=stage,reason=str(e),completed_runs=runs,changed_protected=changes(protected),changed_copies=changes(copies),SHA_scans=0,no_solver_retry=True,physical_acceptance=False))
    print('PRESERVED FAILURE',stage,str(e),flush=True);raise
