"""One authorized default-compatibility sequence; no retry, hashing or physical acceptance."""
import csv, ctypes, datetime, json, os, re, shutil, subprocess, time
from ctypes import wintypes
from pathlib import Path
import psutil
import numpy as np
import xml.etree.ElementTree as ET

R=Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b'); T=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
L=T/'logs'; S='upl_material_default_r1'; STEM='CaseLianSaturatedColumnCollapse_material_default_r1'
HELP=T/'outputs/upl_material_default_native_r1'; READER=HELP/'upl_material_default_native_r1.exe'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def need(x,s):
    if not x: raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve(); q=p.stat(); return dict(path=str(p),bytes=q.st_size,mtime_ns=q.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f: json.dump(d,f,indent=2,ensure_ascii=False,allow_nan=False); f.write('\n')
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def identity(pid):
    p=psutil.Process(pid)
    with p.oneshot(): return dict(pid=p.pid,created_epoch=p.create_time(),parent_pid=p.ppid(),exe=p.exe(),arguments=p.cmdline(),working_directory=p.cwd())
def unchanged(rows):
    return all((a:=stat(d['path']))['bytes']==d['bytes'] and a['mtime_ns']==d['mtime_ns'] for d in rows)
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; K.OpenProcess.restype=wintypes.HANDLE
K.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]; K.GetExitCodeProcess.restype=wintypes.BOOL
K.CloseHandle.argtypes=[wintypes.HANDLE]
OWNER=identity(os.getpid()); protected=[]; phase='preflight'; results={}
def call(tag,argv,cwd,env=None,solver=None):
    log=L/(tag+'.log'); started=now(); child=None; handle=None
    need(not any((L/(tag+s)).exists() for s in ['.log','.call.json','.start.json','.solver.start.json']),'Fresh call paths required: '+tag)
    with log.open('xb') as f:
        p=subprocess.Popen([str(x) for x in argv],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        actual=identity(p.pid); save(L/(tag+'.start.json'),dict(stage=tag+'.start',owner=OWNER,child=actual,started_utc=started,SHA_scans=0))
        print('START',tag,p.pid,flush=True)
        if solver:
            while p.poll() is None:
                if child is None:
                    try:
                        for q in psutil.Process(p.pid).children(recursive=True):
                            try:
                                if Path(q.exe())==solver:
                                    handle=K.OpenProcess(0x1000|0x00100000,False,q.pid); need(bool(handle),'Cannot retain solver exit handle')
                                    child=identity(q.pid); save(L/(tag+'.solver.start.json'),dict(stage=tag+'.solver.start',solver=child,program=stat(solver),retained_actual_exit_handle=True)); print('SOLVER',tag,q.pid,flush=True); break
                            except psutil.NoSuchProcess: pass
                    except psutil.NoSuchProcess: pass
                time.sleep(.002)
        exitcode=p.wait(); code=wintypes.DWORD(259)
        queried=bool(handle and K.GetExitCodeProcess(handle,ctypes.byref(code))); targetexit=code.value if queried else None
        if handle: K.CloseHandle(handle)
    record=dict(stage=tag+'.call',owner=OWNER,child=actual,solver=child,program=str(argv[0]),arguments=[str(x) for x in argv[1:]],working_directory=str(cwd),actual_Popen_wait_exit=exitcode,actual_solver_Win32_exit=targetexit,retained_solver_exit_queried=queried,started_utc=started,ended_utc=now(),log=stat(log),SHA_scans=0,physical_acceptance=False)
    save(L/(tag+'.call.json'),record); print('EXIT',tag,exitcode,targetexit,flush=True)
    need(exitcode==0 and (solver is None or targetexit==0),'Actual owned process failed: '+tag)
    if solver: need(child and child['parent_pid']==actual['pid'],'Solver parent differs')
    return record

def build_reader():
    global phase
    phase='reader_build'; need(not HELP.exists(),'Fresh helper directory required'); HELP.mkdir()
    oldc=read(L/'upl_c08_free_seepage_start_native_r1.compile.call.json'); oldl=read(L/'upl_c08_free_seepage_start_native_r1.link.call.json')
    oldroot=str(T/'outputs/upl_c08_free_seepage_start_native_r1')
    ca=[x.replace(oldroot,str(HELP)).replace('upl_c08_free_seepage_start_native_r1.cpp','upl_material_default_native_r1.cpp') for x in oldc['arguments']]
    objs=[d['path'] for d in builds['CPU']['project_objects'] if Path(d['path']).name.lower()!='main.obj']; need(len(objs)==85,'Current CPU non-main count differs')
    la=[]
    for x in oldl['arguments']:
        if x.lower().endswith('.obj'):
            if Path(x).name.lower()=='helper.obj': la.extend([str(HELP/'helper.obj')]+objs)
        else: la.append(x.replace(oldroot,str(HELP)).replace('upl_c08_free_seepage_start_native_r1.exe',READER.name))
    cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe'; dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat')
    setup=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True)
    need(setup.returncode==0,'Known VS environment setup failed'); env=os.environ.copy()
    for line in setup.stdout.decode('mbcs').splitlines():
        if '=' in line and not line.startswith('='): k,v=line.split('=',1); env[k]=v
    call('upl_material_default_native_r1.compile',[oldc['program']]+ca,HELP,env)
    call('upl_material_default_native_r1.link',[oldl['program']]+la,HELP,env)
    runtime=[]
    for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']:
        src=R/'bin/windows'/n; shutil.copy2(src,HELP/n); need((HELP/n).stat().st_size==src.stat().st_size,'Runtime copy size differs'); runtime.append(stat(HELP/n))
    need(unchanged(protected),'Protected current program/input SMT changed during reader build')
    save(L/'upl_material_default_native_r1.build.json',dict(stage='upl_material_default_native_r1.build',passed=True,source=stat(T/'support/upl_material_default_native_r1.cpp'),source_build=stat(L/'upl_material_DebugCPU_r1.build.json'),program=stat(READER),non_main_objects=85,project_objects=builds['CPU']['project_objects'],compile_call=stat(L/'upl_material_default_native_r1.compile.call.json'),link_call=stat(L/'upl_material_default_native_r1.link.call.json'),runtime=runtime,consumed_stats_unchanged=True,SHA_scans=0,physical_acceptance=False))

def run_backend(backend):
    global phase
    tag='upl_material_default_'+backend+'_r1'; out=T/'outputs'/tag; runtime=T/'outputs'/(tag+'_runtime'); native=T/'outputs'/(tag+'_native_r1')
    phase=tag; need(not any(p.exists() for p in [out,runtime,native]),'Fresh backend paths required')
    active=[p.info for p in psutil.process_iter(['pid','name']) if 'dualsphysics' in (p.info['name'] or '').lower()]; need(not active,'Duplicate active solver '+str(active))
    if backend=='CPU': need(not (T/'outputs/upl_material_default_r1_seed').exists(),'Fresh CPU seed required')
    bat=T/'support'/('x'+STEM+'_win64_'+backend+'.bat'); exe=runtime/Path(builds[backend]['program']['path']).name
    command=[Path(os.environ['SystemRoot'])/'System32/cmd.exe','/d','/c','call',bat,'-batch']
    owned=call(tag,command,R/'src',solver=exe)
    need((out/'solver_exit_code.txt').read_text().strip()=='0','Immediate BAT exit differs')
    with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter=';'))
    need(len(rows)==1,'Run.csv count differs'); summary=rows[0]; raw=(out/'Run.out').read_text(encoding='utf-8',errors='replace')
    for k,v in [('Steps',128),('Np',7060),('Nbound',2060),('Nfixed',2060),('PartFiles',5),('PartsOut',0),('PartsOutRhop',0),('PartsOutVel',0)]: need(int(summary[k])==v,'Run count differs: '+k)
    need('Finished execution (code=0).' in raw and 'DTs adjusted to DtMin............: 0' in raw,'Normal finish/necessary-step guard failed')
    need('HydroMechFreeSeepage=True' in raw and 'SoilHourglass: forcecalls=' not in raw and 'GNOG(' not in summary['Configuration'] and 'SoilDamping(' not in summary['Configuration'],'Unchanged free/HG/damping flags differ')
    saves=[dict(part=int(m[1]),time_printed=m[2],completed=int(m[3]),interval=int(m[4]),raw=m[0]) for m in re.finditer(r'^Part_(\d+)\s+([0-9.eE+-]+)\s+(\d+)\s+(\d+)\s+.*$',raw,re.M)]
    need([x['completed'] for x in saves]==[32,64,96,128] and [x['part'] for x in saves]==[1,2,3,4],'Actual32-update cadence differs')
    need({p.name for p in (out/'data').glob('Part_[0-9][0-9][0-9][0-9].bi4')}=={'Part_'+str(i).zfill(4)+'.bi4' for i in range(5)},'Actual native membership differs')
    need(unchanged(protected),'Protected input/current program SMT changed')
    save(L/(tag+'.run.check.json'),dict(stage=tag+'.run',passed=True,actual_call=stat(L/(tag+'.call.json')),summary=summary,actual_saved_Run_lines=saves,last_Run_lines=raw.splitlines()[-12:],protected_SMT_unchanged=True,native_pending=True,SHA_scans=0,physical_acceptance=False))
    phase=tag+'.native'; call(tag+'.native',[READER,'--read',backend,out/'data',native],HELP)
    c=read(native/'completion.json'); need(c['passed'] and c['stage']=='upl_material_default_native_r1' and c['input_run_tag']==tag and c['samples']==5 and c['total_native_IDs']==7060 and c['typed_arrays']==22 and c['soil_cache_float_bits_checks']==25000 and c['noninitial_signed_intervals']==4,'Native original completion guards differ')
    control=T/'outputs'/('upl_c08_free_seepage_start_'+backend+'_r1_native_r1'); comparisons={}
    for name in ['typed22.bin','clocks.csv','typed22_layout.csv','native_ids.csv']:
        a=(native/name).read_bytes(); b=(control/name).read_bytes(); need(len(a)==len(b),'Control export size differs: '+name)
        aa=np.frombuffer(a,dtype=np.uint8); bb=np.frombuffer(b,dtype=np.uint8); delta=aa!=bb
        comparisons[name]=dict(new=stat(native/name),retained=stat(control/name),different_bytes=int(np.count_nonzero(delta)),different_bits=sum(int(x).bit_count() for x in np.bitwise_xor(aa[delta],bb[delta])),bit_identical=a==b)
    with (native/'clocks.csv').open(newline='') as f: clocks=list(csv.DictReader(f))
    expected=[0,32,64,96,128]; need([int(x['completed_step']) for x in clocks]==expected and [float(x['time_s']) for x in clocks]==[x*2.**-18 for x in expected],'Decoded actual clock table differs')
    need(unchanged(protected),'Final protected SMT changed')
    result=dict(stage=tag+'.default_compatibility',passed=all(x['bit_identical'] for x in comparisons.values()),source_build=stat(L/('upl_material_DebugCPU_r1.build.json' if backend=='CPU' else 'upl_material_Debug_r1.build.json')),actual_call=stat(L/(tag+'.call.json')),reader_call=stat(L/(tag+'.native.call.json')),native_completion=stat(native/'completion.json'),original_native_guards_passed=True,comparisons=comparisons,actual_clocks=clocks,all_original_IDs=7060,all_arrays=22,all_ID_frame_records=35300,bit_difference_IDs=[] if all(x['bit_identical'] for x in comparisons.values()) else None,mode1_physical_job_invoked=False,consumed_stats_unchanged=True,SHA_scans=0,physical_acceptance=False)
    save(L/(tag+'.check.json'),result); need(result['passed'],'Default native comparison differs; preserve exports, no rerun'); print('DEFAULT BYTE COMPATIBILITY PASSED',backend,flush=True); return result

try:
    need(not (L/(S+'.check.json')).exists(),'Fresh terminal check required')
    builds={}
    for backend,label in [('CPU','DebugCPU'),('GPU','Debug')]:
        bp=L/('upl_material_'+label+'_r1.build.json'); b=read(bp)
        need(b['passed'] and b['actual_typed_exit_code']==0 and b['non_main_objects']==(85 if backend=='CPU' else 110),'Current engine build not passed')
        need(unchanged([b['program']]),'Current sealed program SMT differs'); builds[backend]=b
    for n in ['upl_material_cpu_stage_CPU_r1.check.json','upl_material_gpu_step_r2.check.json']:
        need(read(L/n)['passed'],'Actual material stage prerequisite failed'); protected.append(stat(L/n))
    cfg=T/'configs'/(STEM+'.xml'); tree=ET.parse(cfg).getroot(); soils=tree.find('execution/special/soils')
    need(soils is not None and soils.find('MaterialReturn') is None and soils.find('DilationDecay') is None,'Default0 input must omit both new material keys')
    files=[Path(__file__),cfg,T/'configs'/(STEM+'_Def.xml'),T/'support/upl_material_default_native_r1.cpp',T/'notes/upl_material_default_r1.json',R/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp']
    files += [T/'support'/('x'+STEM+'_win64_'+b+'.bat') for b in ['CPU','GPU']]
    files += [Path(b['program']['path']) for b in builds.values()]+[L/'upl_material_DebugCPU_r1.build.json',L/'upl_material_Debug_r1.build.json']
    files += [T/'outputs/upl_c08_observer_r1_seed'/n for n in ['CaseLianSaturatedColumnCollapse_geometry_r1.bi4','CaseLianSaturatedColumnCollapse_geometry_r1_Normals.nbi4']]
    files += [R/'bin/windows'/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']]
    protected += [stat(p) for p in files]; save(L/(S+'.inputs.json'),dict(stage=S+'.inputs',owner=OWNER,protected=protected,default_keys_absent=True,authorized_sequence=['reader_compile_link_once','CPU_BAT128_native_compare_once','GPU_BAT128_native_compare_once_only_after_CPU_pass'],SHA_scans=0,physical_acceptance=False))
    build_reader(); results['CPU']=run_backend('CPU'); results['GPU']=run_backend('GPU')
    save(L/(S+'.check.json'),dict(stage=S,passed=True,backends=results,consumed_stats_unchanged=unchanged(protected),solver_invocations=2,reader_invocations=2,SHA_scans=0,physical_acceptance=False)); print('ALL DEFAULT COMPATIBILITY CLOSED',flush=True)
except BaseException as e:
    p=L/(S+'.check.json')
    if not p.exists(): save(p,dict(stage=S,passed=False,failed_phase=phase,reason=str(e),completed_backends=list(results),retry_performed=False,SHA_scans=0,physical_acceptance=False))
    print('PRESERVED FIRST FAILURE',phase,str(e),flush=True); raise
