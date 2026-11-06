"""One direct sanitized GPU128 target. The reproduction BAT is never executed here."""
import csv
import ctypes
from ctypes import wintypes
import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import psutil

T=Path(__file__).resolve().parents[1]
R=T.parents[3]
L=T/'logs';TAG='upl_c08_elastic_start_GPU_r2'
OUT=T/'outputs'/TAG;RUN=T/'outputs'/(TAG+'_runtime')
SEED=T/'outputs/upl_c08_elastic_start_r2_seed/CaseLianSaturatedColumnCollapse_elastic_start_r2'
SAN=Path(r'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.3/compute-sanitizer/compute-sanitizer.exe')
EXE=RUN/'DualSPHysics5.2_win64_debug.exe'
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

def main():
    owner=identity(psutil.Process().pid);protected=[];copies=[];tool=None;target=None;tool_exit=None;target_exit=None;stage='preflight'
    try:
        need(not OUT.exists()and not RUN.exists(),'Fresh GPU output/runtime required')
        for suffix in ['inputs.json','start.json','solver.start.json','call.json','check.json','console.log']:need(not(L/(TAG+'.'+suffix)).exists(),'Fresh record collision '+suffix)
        active=[p.info for p in psutil.process_iter(['pid','name','exe'])if'dualsphysics'in(p.info['name']or'').casefold()];need(not active,'Another actual solver is active: '+str(active))
        nativepath=L/'upl_c08_elastic_start_CPU_r2_native_r1.check.json';native=read(nativepath)
        need(native['stage']=='upl_c08_elastic_start_CPU_r2_native_r1'and native['passed']and native['original_native_guards_passed']and native['consumed_stats_unchanged']and native['samples']==5 and native['completed_steps']==128 and native['last_saved_step']==127 and native['total_native_IDs']==7060 and native['typed_arrays']==22 and native['no_exclusions'],'Actual CPU-r2 native prerequisite has not passed')
        cpupath=L/'upl_c08_elastic_start_CPU_r2.check.json';cpu=read(cpupath);need(cpu['passed']and cpu['actual_solver_exit']==0 and not changes([native['source_run_check'],native['source_run_call']]),'Closed CPU run/native bindings changed')
        seeds=[SEED.with_suffix('.xml'),SEED.with_suffix('.bi4'),SEED.parent/(SEED.name+'_Normals.nbi4')]
        seedentries=[d for d in cpu['copied_seed_and_runtime']if Path(d['path']).parent==SEED.parent];need(len(seedentries)==3 and not changes(seedentries),'Shared immutable CPU seed differs')
        buildpath=L/'upl_container_Debug_r1.build.json';b=read(buildpath);need(b['passed']and b['actual_typed_exit_code']==0 and b['objects']==111 and not changes([b['program']]),'Authoritative GPU container build/program differs')
        source=read(b['source']);need(not changes(source['applied_source']),'Applied container source SMT changed')
        runtime=[R/'bin/windows'/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']]
        files=[Path(__file__),SAN,nativepath,cpupath,Path(native['source_run_call']['path']),buildpath,Path(b['source']),Path(b['program']['path'])]+seeds+runtime+[Path(d['path'])for d in source['applied_source']]
        protected=list({str(p.resolve()).casefold():stat(p)for p in files}.values())
        save(L/(TAG+'.inputs.json'),dict(stage=TAG+'.inputs',source_CPU_native_check=stat(nativepath),source_GPU_build=stat(buildpath),source_GPU_program=b['program'],protected=protected,BAT_executed=False,shared_seed_copied=False,SHA_scans=0,physical_acceptance=False))
        RUN.mkdir()
        for p in [Path(b['program']['path'])]+runtime:
            dest=RUN/p.name;shutil.copy2(p,dest);need(dest.stat().st_size==p.stat().st_size and dest.stat().st_mtime_ns==p.stat().st_mtime_ns,'Runtime copy2 SMT mismatch');copies.append(stat(dest))
        need(not changes(protected),'Consumed SMT changed before target')
        # Same target values and case-root working directory as the reviewed GPU-r2 BAT.
        args=['--tool','memcheck','--leak-check','full','--error-exitcode','99',str(EXE),'-gpu:0','-stable','-mdbc_freeslip',str(SEED),str(OUT),'-dirdataout','data','-svres','-nsteps:128']
        k32=ctypes.WinDLL('kernel32',use_last_error=True);k32.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k32.OpenProcess.restype=wintypes.HANDLE;k32.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];k32.GetExitCodeProcess.restype=wintypes.BOOL;k32.CloseHandle.argtypes=[wintypes.HANDLE];k32.CloseHandle.restype=wintypes.BOOL
        stage='single_memcheck';started=now();handle=None;lp=L/(TAG+'.console.log')
        with lp.open('xb')as f:
            p=subprocess.Popen([str(SAN)]+args,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);tool=identity(p.pid)
            save(L/(TAG+'.start.json'),dict(stage=TAG+'.start',owner=owner,tool=tool,arguments=args,program=stat(EXE),started_utc=started,BAT_executed=False,SHA_scans=0));print('ACTUAL MEMCHECK',p.pid,flush=True)
            while p.poll()is None:
                if target is None:
                    try:
                        for child in psutil.Process(p.pid).children(recursive=True):
                            try:
                                if Path(child.exe()).resolve()==EXE.resolve():
                                    handle=k32.OpenProcess(0x1000|0x00100000,False,child.pid);target=identity(child.pid);save(L/(TAG+'.solver.start.json'),dict(stage=TAG+'.solver.start',solver=target,tool=tool,retained_actual_exit_handle=bool(handle),observed_utc=now(),BAT_executed=False,SHA_scans=0));print('ACTUAL GPU SOLVER',target['pid'],flush=True);break
                            except psutil.NoSuchProcess:pass
                    except psutil.NoSuchProcess:pass
                time.sleep(.002)
            tool_exit=p.wait()
        code=wintypes.DWORD(259);queried=bool(handle and k32.GetExitCodeProcess(handle,ctypes.byref(code)));target_exit=code.value if queried else None
        if handle:k32.CloseHandle(handle)
        save(L/(TAG+'.call.json'),dict(stage=TAG+'.run_call',owner=owner,tool=tool,solver=target,program=str(SAN),arguments=args,working_directory=str(T.parent),actual_tool_Popen_wait_exit=tool_exit,actual_solver_Win32_exit=target_exit,solver_exit_queried_from_retained_handle=queried,started_utc=started,ended_utc=now(),console_log=stat(lp),BAT_executed=False,target_invocations=1,unsanitized_target_invocations=0,SHA_scans=0,physical_acceptance=False));print('SEALED ACTUAL EXITS tool',tool_exit,'solver',target_exit,flush=True)
        stage='Run_level_closure';need(not changes(protected)and not changes(copies),'Protected/copied SMT changed')
        need(tool_exit==0 and target_exit==0 and target and target['parent_pid']==tool['pid'],'Actual memcheck/solver failure; do not rerun')
        console=lp.read_text(encoding='utf-8',errors='replace');need('ERROR SUMMARY: 0 errors'in console and'LEAK SUMMARY: 0 bytes leaked in 0 allocations'in console,'Memcheck error/leak summary failed')
        raw=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')
        with(OUT/'Run.csv').open(newline='',encoding='utf-8-sig')as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'Run.csv missing/ambiguous');s=rows[0]
        need(int(s['Steps'])==128 and int(s['Np'])==7060 and int(s['Nbound'])==2060 and int(s['Nfixed'])==2060 and int(s['PartFiles'])==5 and int(s['MemGpu'])>0,'Actual GPU step/native/save/memory summary differs')
        need(int(s['PartsOut'])==int(s['PartsOutRhop'])==int(s['PartsOutVel'])==0 and'Finished execution (code=0).'in raw and'DTs adjusted to DtMin............: 0'in raw,'Original normal-exit/exclusion/step guard failed')
        need('GNOG('not in s['Configuration']and'SoilDamping('not in s['Configuration']and'SoilHourglass: forcecalls='not in raw,'HG/damping unexpectedly active')
        part=[]
        for line in raw.splitlines():
            m=re.match(r'^Part_(\d+)\s+([0-9.eE+-]+)\s+(\d+)\s+(\d+)\s+',line)
            if m:part.append(dict(part=int(m[1]),printed_time_s=m[2],completed_steps=int(m[3]),interval_steps=int(m[4]),raw_line=line))
        need([r['part']for r in part]==[1,2,3,4]and[r['completed_steps']for r in part]==[32,64,96,128],'Actual five-frame schedule differs')
        data=[stat(p)for p in(OUT/'data').glob('Part_[0-9][0-9][0-9][0-9].bi4')];need(len(data)==5 and{Path(d['path']).name for d in data}=={'Part_'+str(i).zfill(4)+'.bi4'for i in range(5)},'Native file membership differs')
        need(not(OUT/'solver_exit_code.txt').exists()and not(OUT/'run_command.txt').exists(),'Unexpected BAT-only receipt artifacts')
        save(L/(TAG+'.check.json'),dict(stage=TAG,passed=True,source_inputs=stat(L/(TAG+'.inputs.json')),actual_call=stat(L/(TAG+'.call.json')),actual_tool_exit=tool_exit,actual_solver_exit=target_exit,zero_memcheck_errors=True,zero_memcheck_leaks=True,summary=s,actual_saved_run_lines=part,Run_last_lines=raw.splitlines()[-12:],native_files=data,runtime_copies=copies,protected_SMT_unchanged=True,source_CPU_native=stat(nativepath),BAT_executed=False,target_invocations=1,unsanitized_target_invocations=0,shared_seed_copied=False,noDrain_is_not_sealed_or_zero_normal_flux=True,FS_p0_not_forced=True,completed_internal_dynamic_J_elastic_natural_checks_by_normal_exit=True,all22_native_fields_clocks_and_physical_review_pending=True,reader_invoked=False,SHA_scans=0,physical_acceptance=False));print('GPU RUN LEVEL CLOSED; NATIVE/PHYSICAL REVIEW PENDING',flush=True)
    except BaseException as e:
        raw=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')if(OUT/'Run.out').exists()else'';lines=[v for v in raw.splitlines()if v.startswith('Part_')];reason=re.findall(r'Text: (.+)',raw);fp=L/(TAG+'.check.json')
        if not fp.exists():save(fp,dict(stage=TAG,passed=False,failed_stage=stage,reason=str(e),first_actual_exception=reason[0]if reason else None,owner=owner,tool=tool,solver=target,actual_tool_exit=tool_exit,actual_solver_exit=target_exit,last_actual_saved_Run_line=lines[-1]if lines else None,Run_last_lines=raw.splitlines()[-35:],changed_protected=changes(protected),changed_copies=changes(copies),BAT_executed=False,target_retry_performed=False,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()
