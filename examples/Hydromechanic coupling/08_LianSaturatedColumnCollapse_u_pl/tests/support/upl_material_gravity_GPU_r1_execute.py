"""One reviewed GPU128 target under memcheck, then one existing native reader."""
import csv,ctypes,json,os,re,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';O=T/'outputs';TAG='upl_material_gravity_GPU_r1';NTAG=TAG+'_native_r1'
STEM='CaseLianSaturatedColumnCollapse_material_gravity_r1';OUT=O/TAG;RUN=O/(TAG+'_runtime');SEED=O/'upl_material_gravity_r1_seed';NATIVE=O/NTAG;CHECK=L/(TAG+'.check.json');NCHECK=L/(NTAG+'.check.json');before={};calls=[]
def need(v,s):
 if not v:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(p,e=None):
 a=stat(p);before.setdefault(a['path'],a)
 if e:need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed SMT changed: '+str(p))
 return a
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE;K.CloseHandle.argtypes=[w.HANDLE]
def identity(h,pid):
 ft=[w.FILETIME() for _ in range(4)];need(K.GetProcessTimes(h,*[ctypes.byref(x) for x in ft]),'Native process times unavailable')
 n=w.DWORD(32768);im=ctypes.create_unicode_buffer(n.value);need(K.QueryFullProcessImageNameW(h,0,im,ctypes.byref(n)),'Native process image unavailable')
 try:argv=psutil.Process(pid).cmdline()
 except psutil.NoSuchProcess:argv=None
 return dict(pid=pid,created_epoch=((ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime)/1e7-11644473600,exe=im.value,argv=argv)
def invoke(label,argv,target=None):
 log=L/(label+'.console.log');receipt=L/(label+'.call.json');need(not log.exists() and not receipt.exists(),'Fresh actual call required')
 record=dict(stage=label,program=argv[0],arguments=argv[1:],cwd=str(S),owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),SHA_scans=0);th=None
 try:
  with log.open('xb') as f:
   p=subprocess.Popen(argv,cwd=S,stdout=f,stderr=subprocess.STDOUT);record['child']=identity(int(p._handle),p.pid);save(L/(label+'.start.json'),record);print(label,'tool',p.pid,flush=True)
   if target:
    while p.poll() is None:
     if th is None:
      try:children=psutil.Process(p.pid).children(recursive=True)
      except psutil.NoSuchProcess:children=[]
      for q in children:
       try:
        if q.name().lower()!=target.name.lower():continue
        h=K.OpenProcess(0x1000|0x100000,False,q.pid)
        if not h:continue
        item=identity(h,q.pid)
        if not Path(item['exe']).samefile(target):K.CloseHandle(h);continue
        th=h;record['solver']=item;print('solver',q.pid,flush=True);break
       except psutil.NoSuchProcess:continue
     time.sleep(.005)
   rc=p.wait();code=w.DWORD();need(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Actual tool exit unavailable');record.update(actual_Popen_wait_exit=rc,actual_tool_Win32_exit=code.value,console_log=str(log))
   if th:
    code=w.DWORD();need(K.GetExitCodeProcess(th,ctypes.byref(code)),'Actual solver exit unavailable');record['actual_solver_Win32_exit']=code.value
   save(receipt,record);calls.append(str(receipt))
  need(record['actual_Popen_wait_exit']==0 and record['actual_tool_Win32_exit']==0,'Actual call failed: '+label)
  if target:need(th is not None and record['actual_solver_Win32_exit']==0,'Owned solver normal exit missing')
  return record,receipt
 finally:
  if th:K.CloseHandle(th)
try:
 need(not any(p.exists() for p in (OUT,RUN,NATIVE,CHECK,NCHECK)),'Fresh GPU/native paths required')
 active=[p.info for p in psutil.process_iter(['pid','name']) if 'dualsphysics' in (p.info['name'] or '').lower()];need(not active,'An actual solver is already active')
 cpu=read(L/'upl_material_gravity_CPU_r1_native_r1.check.json');need(cpu['passed'] is True and cpu['original_native_guards_passed'] is True and cpu['consumed_stats_unchanged'] is True,'Prior CPU native gates required');bind(L/'upl_material_gravity_CPU_r1_native_r1.check.json')
 for key in ('source_run_check','source_run_call','source_build','reader_call','native_completion'):bind(cpu[key]['path'],cpu[key])
 need(read(cpu['source_run_check']['path'])['passed'] is True and read(cpu['source_run_call']['path'])['actual_solver_Win32_exit']==0 and read(cpu['reader_call']['path'])['actual_Popen_wait_exit']==0,'CPU owned run/reader actual exits required')
 cd=cpu['actual_completion'];need(cd['total_native_IDs']==7060 and cd['typed_arrays']==22 and cd['samples']==5 and cd['soil_ledger_rows']==25000 and cd['fixed_marker_rows']==10300 and cd['soil_cache_float_bits_checks']==25000 and cd['soil_noninitial_kappa_monotonic_checks']==20000 and cd['noninitial_signed_intervals']==4 and cd['actual_end_s']==.00048828125 and cd['saved_FS23_soil_checks_by_part']==[100]*5 and cd['max_ledger_relative_error']==0,'Original CPU native coverage differs')
 bp=L/'upl_material_gravity_Debug_r1.build.json';b=read(bp);need(b['passed'] is True and b['actual_Win32_exit']==0 and b['actual_Link_full111_inputs_verified'] is True,'Reviewed GPU111 link closure required');bind(bp);bind(b['program']['path'],b['program'])
 sp=Path(b['source']);src=read(sp);bind(sp);bind(src['archive']['path'],src['archive'])
 for name in ('JSph.cpp','JSphCpu.cpp','JSphGpu.cpp'):bind(S/'source'/name,next(x for x in src['files'] if Path(x['path']).name==name))
 prep=read(cpu['source_run_check']['path']);need(prep['seed_copy_owned_by_actual_CPU_BAT'] is True,'Actual CPU-prepared same-input seed required')
 for e in prep['actual_seed_files']:bind(e['path'],e)
 bind(T/'notes/upl_material_gravity_r1.json')
 for p in (Path(__file__),T/'support'/('x'+STEM+'_win64_GPU.bat'),T/'configs'/(STEM+'_Def.xml'),T/'configs'/(STEM+'.xml')):bind(p)
 rbp=L/'upl_material_gravity_native_r1.build.json';rb=read(rbp);need(rb['passed'] is True,'Closed existing reader required');bind(rbp);reader=Path(rb['program']['path']);bind(reader,rb['program']);bind(rb['source']['path'],rb['source'])
 RUN.mkdir();OUT.mkdir();exe=RUN/Path(b['program']['path']).name
 copies=[(Path(b['program']['path']),exe)]+[(R/'bin/windows'/n,RUN/n) for n in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')]
 for p,q in copies:
  bind(p);shutil.copy2(p,q);bind(q);need(p.stat().st_size==q.stat().st_size and p.stat().st_mtime_ns==q.stat().st_mtime_ns,'Runtime copy SMT differs')
 SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe');bind(SAN)
 argv=[str(exe),'-gpu:0','-stable','-mdbc_freeslip',str(SEED/STEM),str(OUT),'-dirdataout','data','-svres','-nsteps:128'];(OUT/'run_command.txt').write_text(subprocess.list2cmdline(argv)+'\n',encoding='utf-8')
 save(L/(TAG+'.inputs.json'),dict(stage=TAG,source_build=stat(bp),runtime=[stat(q) for p,q in copies],seed=[stat(SEED/(STEM+x)) for x in ('.xml','.bi4')],exact_target_argv=argv,BAT_executed=False,SHA_scans=0))
 sanlog=L/(TAG+'.sanitizer.log');call,cp=invoke(TAG,[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*argv],exe)
 text=sanlog.read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Original memcheck zero errors/leaks required')
 (OUT/'solver_exit_code.txt').write_text(str(call['actual_solver_Win32_exit'])+'\n',encoding='ascii')
 with (OUT/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
 need(len(rows)==1,'One completed Run.csv row required');summary=rows[0];raw=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')
 for key,value in dict(Steps=128,Np=7060,Nbound=2060,Nfixed=2060,PartFiles=5,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items():need(int(summary[key])==value,'Original run count/exclusion differs: '+key)
 need('Finished execution (code=0).' in raw and 'DTs adjusted to DtMin............: 0' in raw,'Normal completion or original DtMin guard failed')
 saves=[int(m[1]) for m in re.finditer(r'^Part_\d+\s+[0-9.eE+-]+\s+(\d+)\s+\d+\s+.*$',raw,re.M)];need(saves==[32,64,96,128],'Original32-update saves differ')
 need(all(stat(p)==e for p,e in before.items()),'Consumed input/program/source changed')
 save(CHECK,dict(stage=TAG,passed=True,source_build=stat(bp),actual_call=stat(cp),summary=summary,saved_completed_steps=saves,memcheck_zero_errors_leaks=True,input_stats=list(before.values()),consumed_stats_unchanged=True,native_pending=True,SHA_scans=0,physical_acceptance=False))
 for p in sorted((OUT/'data').iterdir()):
  if p.is_file():bind(p)
 ncall,ncp=invoke(NTAG,[str(reader),'--read','GPU',str(OUT/'data'),str(NATIVE)])
 done=read(NATIVE/'completion.json');need(done['passed'] is True and done['stage']=='upl_material_gravity_native_r1' and done['input_run_tag']==TAG,'Original native completion identity differs')
 for key,value in dict(samples=5,completed_steps=128,total_native_IDs=7060,typed_arrays=22,soil_ledger_rows=25000,soil_cache_float_bits_checks=25000,fixed_marker_rows=10300,soil_noninitial_kappa_monotonic_checks=20000,noninitial_signed_intervals=4).items():need(done[key]==value,'Original native coverage differs: '+key)
 need(done['actual_end_s']==.00048828125 and done['max_ledger_relative_error']==0 and done['saved_FS23_soil_checks_by_part']==[100]*5 and done['saved_FS23_soil_pressure_nonpositive'] is True and done['no_exclusions'] is True,'Original clock/history/ledger guards differ')
 need(all(stat(p)==e for p,e in before.items()),'Consumed data/input/program/source changed')
 save(NCHECK,dict(stage=NTAG,passed=True,source_run_check=stat(CHECK),source_run_call=stat(cp),source_build=stat(rbp),reader_call=stat(ncp),native_completion=stat(NATIVE/'completion.json'),original_native_guards_passed=True,consumed_stats_unchanged=True,actual_completion=done,files=[stat(p) for p in sorted(NATIVE.iterdir()) if p.is_file()],SHA_scans=0,physical_acceptance=False))
 print(json.dumps(dict(passed=True,native=done)),flush=True)
except BaseException as e:
 failure=NCHECK if CHECK.exists() else CHECK
 if not failure.exists():save(failure,dict(stage=NTAG if failure==NCHECK else TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,consumed_stats=list(before.values()),SHA_scans=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
