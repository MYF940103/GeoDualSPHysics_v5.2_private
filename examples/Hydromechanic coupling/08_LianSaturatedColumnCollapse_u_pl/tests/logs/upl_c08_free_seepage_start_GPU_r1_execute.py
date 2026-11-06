import csv,ctypes,datetime,json,os,re,subprocess,time
from ctypes import wintypes
from pathlib import Path
import psutil
import xml.etree.ElementTree as ET
R=Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b');T=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests';L=T/'logs';TAG='upl_c08_free_seepage_start_GPU_r1';OUT=T/'outputs'/TAG;SEED=T/'outputs/upl_c08_free_seepage_start_r1_seed';RUN=T/'outputs'/(TAG+'_runtime');EXE=RUN/'DualSPHysics5.2_win64_debug.exe';BAT=T/'support/xCaseLianSaturatedColumnCollapse_free_seepage_start_r1_win64_GPU.bat'
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
    changed=[]
    for d in rows:
        try:a=stat(d['path']);ok=Path(a['path']).samefile(d['path'])and a['bytes']==d['bytes']and a['mtime_ns']==d['mtime_ns']
        except OSError:a=None;ok=False
        if not ok:changed.append(dict(expected=d,observed=a))
    return changed
OWNER=identity(os.getpid());protected=[];cmd_exit=None;target_exit=None;target=None;command=None;stage='preflight'
try:
    need(not any(p.exists()for p in [OUT,RUN]),'Fresh GPU runtime/output required');need(all((SEED/n).is_file()for n in ['CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml','CaseLianSaturatedColumnCollapse_free_seepage_start_r1.bi4','CaseLianSaturatedColumnCollapse_free_seepage_start_r1_Normals.nbi4']),'Reviewed CPU-prepared shared seed is missing')
    floor=next(v.get('value')for v in ET.parse(T/'configs/CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml').getroot().iter('parameter')if v.get('key')=='DtMin');need(float(floor)==1e-8,'Explicit reviewed DtMin differs')
    hp=ET.parse(T/'configs/CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml').getroot().find('execution/special/hydromechanics')
    need(hp is not None and all(hp.find(k).get('value')==value for k,value in [('HydroMechDynamicSeepage','1'),('HydroMechFreeSeepage','1'),('HydroMechDrainage','0'),('HydroMechConductivityModel','0'),('HydroMechConductivityCk','0')]),'Reviewed free-seepage input keys differ')
    fixedgrid=hp.find('HydroMechDrainageFixedGrid');need(fixedgrid is None or fixedgrid.get('value')=='0','Fixed-grid drainage must remain OFF')
    component_paths=[L/'upl_free_seepage_CPU_old_headers_r2.check.json',L/'upl_free_seepage_GPU_r1.check.json']
    for cp in component_paths:
        cd=read(cp);need(cd['passed'] and cd['consumed_stats_unchanged'] and all((cd.get('comparisons') or cd.get('old_new_byte_comparisons')).values()),'Required component/OFF gate not passed')
    cpu_native_path=L/'upl_c08_free_seepage_start_CPU_r1_native_r1.check.json';cpu_native=read(cpu_native_path);need(cpu_native['passed'] and cpu_native['original_native_guards_passed'] and cpu_native['consumed_stats_unchanged'] and cpu_native['samples']==5 and cpu_native['completed_steps']==128,'Actual CPU native gate not passed')
    component_paths.extend([cpu_native_path,Path(cpu_native['native_completion']['path']),Path(cpu_native['source_run_check']['path']),Path(cpu_native['source_run_call']['path'])])
    for suffix in ['start.json','solver.start.json','call.json','check.json','console.log','inputs.json']:need(not(L/(TAG+'.'+suffix)).exists(),'Fresh record collision '+suffix)
    active=[p.info for p in psutil.process_iter(['pid','name','exe'])if'dualsphysics'in(p.info['name']or'').casefold()];need(not active,'Duplicate active solver '+str(active))
    buildpath=L/'upl_free_seepage_Debug_r1.build.json';b=read(buildpath);source=read(b['source']);need(b['passed']and b['actual_typed_exit_code']==0 and b['objects']==111 and b['non_main_objects']==110,'Official free-seepage GPU build not sealed passed')
    expected=[{k:d[k]for k in ['path','bytes','mtime_ns']}for d in source['files']+[b['program']]];need(not changes(expected),'Sealed program/direct-source SMT changed')
    files=[Path(d['path'])for d in expected]+component_paths+[Path(b['source']),buildpath,BAT,T/'configs/CaseLianSaturatedColumnCollapse_free_seepage_start_r1_Def.xml',T/'configs/CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml',T/'notes/upl_c08_free_seepage_start_r1.json',Path(__file__)]
    old=T/'outputs/upl_c08_observer_r1_seed';files.extend([old/'CaseLianSaturatedColumnCollapse_geometry_r1.bi4',old/'CaseLianSaturatedColumnCollapse_geometry_r1_Normals.nbi4'])
    runtime=[R/'bin/windows'/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']];files.extend(runtime)
    gbp=L/'upl_free_seepage_DebugCPU_r1.build.json';gb=read(gbp);need(gb['passed']and gb['actual_typed_exit_code']==0,'Completed CPU build must stay protected');files.extend([gbp,Path(gb['program']['path'])]);files.extend(Path(d['path'])for d in b['project_objects']+gb['project_objects'])
    for case in [R/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR',R/'examples/Hydromechanic coupling/04_CryerProblem_PR']:files.extend(p for p in case.iterdir()if p.is_file()and p.suffix.lower()in['.xml','.bat'])
    C=R/'examples/Hydromechanic coupling/04_CryerProblem_PR';files.extend([C/'Cryer_upl_nu030_Windows_RTXA6000_r1.zip',C/'support/README_cryer_upl_nu030_r1.md'])
    for directory in [C/'support/bin_upl_r1',C/'support/upl_seed_nu030_r1']:files.extend(p for p in directory.iterdir()if p.is_file())
    files.extend(SEED/n for n in ['CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml','CaseLianSaturatedColumnCollapse_free_seepage_start_r1.bi4','CaseLianSaturatedColumnCollapse_free_seepage_start_r1_Normals.nbi4']);files.append(T/'outputs/upl_c08_free_seepage_start_CPU_r1/solver_exit_code.txt')
    protected=list({str(p.resolve()).casefold():stat(p)for p in files}.values());save(L/(TAG+'.inputs.json'),dict(stage=TAG+'.inputs',source_build=stat(buildpath),program_source=b['program'],BAT=stat(BAT),protected=protected,candidate_dt_s=2.**-18,planned_updates=128,planned_frames=5,free_seepage_input_verified=True,actual_CPU_native_gate=stat(cpu_native_path),component_checks=[stat(p)for p in component_paths],planned_saved_steps=[0,31,63,95,127],planned_completed_updates=[0,32,64,96,128],native_clocks_unobserved=True,SHA_scans=0,physical_acceptance=False))
    k32=ctypes.WinDLL('kernel32',use_last_error=True);k32.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k32.OpenProcess.restype=wintypes.HANDLE;k32.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];k32.GetExitCodeProcess.restype=wintypes.BOOL;k32.CloseHandle.argtypes=[wintypes.HANDLE];k32.CloseHandle.restype=wintypes.BOOL
    cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe';args=['/d','/c','call',str(BAT),'-batch'];started=now();handle=None;lp=L/(TAG+'.console.log');stage='actual_BAT'
    with lp.open('xb')as f:
        p=subprocess.Popen([str(cmd)]+args,cwd=R/'src',stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);command=identity(p.pid);save(L/(TAG+'.start.json'),dict(stage=TAG+'.start',owner=OWNER,command=command,source_inputs=stat(L/(TAG+'.inputs.json')),started_utc=started,SHA_scans=0));print('ACTUAL CMD',p.pid,flush=True)
        while p.poll()is None:
            if target is None:
                try:
                    for q in psutil.Process(p.pid).children(recursive=True):
                        try:
                            if Path(q.exe()).resolve()==EXE.resolve():
                                handle=k32.OpenProcess(0x1000|0x00100000,False,q.pid);target=identity(q.pid);save(L/(TAG+'.solver.start.json'),dict(stage=TAG+'.solver.start',solver=target,command=command,program=stat(EXE),retained_actual_exit_handle=bool(handle),observed_utc=now(),SHA_scans=0));print('ACTUAL SOLVER',target['pid'],flush=True);break
                        except psutil.NoSuchProcess:pass
                except psutil.NoSuchProcess:pass
            time.sleep(.002)
        cmd_exit=p.wait()
    code=wintypes.DWORD(259);queried=bool(handle and k32.GetExitCodeProcess(handle,ctypes.byref(code)));target_exit=code.value if queried else None
    if handle:k32.CloseHandle(handle)
    save(L/(TAG+'.call.json'),dict(stage=TAG+'.run_call',owner=OWNER,command=command,solver=target,program=str(cmd),arguments=args,actual_cmd_Popen_wait_exit=cmd_exit,actual_solver_Win32_exit=target_exit,solver_exit_queried_from_retained_handle=queried,started_utc=started,ended_utc=now(),console_log=stat(lp),BAT_invocations=1,solver_invocations_observed=int(target is not None),SHA_scans=0,physical_acceptance=False));print('SEALED ACTUAL EXITS cmd',cmd_exit,'solver',target_exit,flush=True)
    stage='Run_level_closure';changed=changes(protected);need(not changed,'Protected source/program/runtime/formal/Cryer SMT changed')
    need(cmd_exit==0 and target_exit==0 and target and target['parent_pid']==command['pid'],'Actual BAT/solver failure; preserve first reason and do not rerun')
    need('-gpu:0' in target['arguments'] and not any(a.startswith('-ompthreads:')for a in target['arguments']),'Actual GPU argv differs from reviewed BAT')
    need((OUT/'solver_exit_code.txt').read_text(encoding='utf-8-sig').strip()=='0','BAT immediate actual exit record mismatch')
    with(OUT/'Run.csv').open(newline='',encoding='utf-8-sig')as f:rows=list(csv.DictReader(f,delimiter=';'))
    need(len(rows)==1,'Run.csv missing/ambiguous');summary=rows[0];raw=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')
    need(int(summary['Steps'])==128 and int(summary['Np'])==7060 and int(summary['Nbound'])==2060 and int(summary['Nfixed'])==2060 and int(summary['PartFiles'])==5,'Actual steps/native/save counts differ')
    need(int(summary['PartsOut'])==int(summary['PartsOutRhop'])==int(summary['PartsOutVel'])==0 and'Finished execution (code=0).'in raw and'DTs adjusted to DtMin............: 0'in raw,'Normal exit/original exclusion/step guard failed')
    need('HydroMechFreeSeepage=True' in raw and 'FreeSeepagePolicy: candidate raw hydraulic surface rate' in raw,'Actual program free-seepage mode not logged')
    copied_hydro=ET.parse(SEED/'CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml').getroot().find('execution/special/hydromechanics');need(copied_hydro.find('HydroMechFreeSeepage').get('value')=='1','Actual copied input lost the free-seepage policy')
    need('GNOG('not in summary['Configuration']and'SoilDamping('not in summary['Configuration']and'SoilHourglass: forcecalls='not in raw,'Disabled HG/damping was unexpectedly active')
    part=[]
    for line in raw.splitlines():
        m=re.match(r'^Part_(\d+)\s+([0-9.eE+-]+)\s+(\d+)\s+(\d+)\s+',line)
        if m:part.append(dict(part=int(m[1]),printed_time_s=m[2],completed_steps=int(m[3]),interval_steps=int(m[4]),raw_line=line))
    need([v['part']for v in part]==[1,2,3,4]and[v['completed_steps']for v in part]==[32,64,96,128],'Actual unchanged planned save schedule failed')
    native=[stat(p)for p in(OUT/'data').glob('Part_[0-9][0-9][0-9][0-9].bi4')];need(len(native)==5 and{Path(v['path']).name for v in native}=={'Part_'+str(i).zfill(4)+'.bi4'for i in range(5)},'Actual five-file native membership failed')
    copies=[stat(p)for d in [SEED,RUN]for p in d.iterdir()if p.is_file()];need(not changes(protected),'Final protected SMT changed')
    save(L/(TAG+'.check.json'),dict(stage=TAG,passed=True,source_inputs=stat(L/(TAG+'.inputs.json')),actual_call=stat(L/(TAG+'.call.json')),actual_cmd_exit=cmd_exit,actual_solver_exit=target_exit,summary=summary,actual_part0_lines=[v for v in raw.splitlines()if v.startswith('Part_0000')],actual_saved_run_lines=part,actual_Run_last_lines=raw.splitlines()[-10:],simulation_end_section=raw[raw.index('[Simulation finished'):raw.index('[GPU Timers]')].splitlines(),native_files=native,shared_CPU_prepared_seed_and_copied_GPU_runtime=copies,shared_seed_copied_by_GPU_action=False,ordinary_Debug_GPU_BAT_executed=True,compute_sanitizer_invoked=False,HG_and_damping_disabled_as_configured=True,actual_program_free_seepage_logged=True,copied_input_free_seepage_verified=True,native_free_seepage_metadata_not_yet_decoded=True,completed_internal_dynamic_J_elastic_natural_bound_checkpoints_by_normal_exit=True,native_kappa_bits_not_independently_decoded=True,all22_native_fields_and_clocks_review_pending=True,root_physical_review_pending=True,protected_SMT_unchanged=True,solver_invocations=1,BAT_invocations=1,reader_or_CPU_or_half_or_reference_invoked=False,SHA_scans=0,physical_acceptance=False));print('GPU STARTUP128 RUN LEVEL CLOSED; NATIVE REVIEW PENDING',flush=True)
except BaseException as e:
    raw=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')if(OUT/'Run.out').exists()else'';console=(L/(TAG+'.console.log')).read_text(encoding='utf-8',errors='replace')if(L/(TAG+'.console.log')).exists()else'';lines=[v for v in raw.splitlines()if v.startswith('Part_')];reason=re.findall(r'Text: (.+)',raw or console)
    fp=L/(TAG+'.check.json')
    if not fp.exists():save(fp,dict(stage=TAG,passed=False,failed_stage=stage,reason=str(e),first_actual_exception=reason[0]if reason else None,actual_cmd_exit=cmd_exit,actual_solver_exit=target_exit,owner=OWNER,command=command,solver=target,last_actual_saved_Run_line=lines[-1]if lines else None,Run_last_lines=raw.splitlines()[-35:],console_last_lines=console.splitlines()[-12:],changed_protected=changes(protected),solver_retry_performed=False,SHA_scans=0,physical_acceptance=False))
    print('PRESERVED FAILURE',stage,str(e),flush=True);raise
