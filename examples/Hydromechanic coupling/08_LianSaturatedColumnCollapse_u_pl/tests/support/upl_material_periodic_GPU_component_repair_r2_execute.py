import csv,ctypes,datetime,json,os,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';O=T/'outputs'
TAG='upl_material_periodic_GPU_component_repair_r2';ACTUAL='upl_material_periodic_GPU_component_r1';HELPER=O/TAG;RESULT=HELPER/'result';CHECK=L/(TAG+'.check.json');before={};calls=[]
def need(b,s):
 if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,j):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2);f.write('\n')
def stat(p):
 p=Path(p).resolve();v=p.stat();return dict(path=str(p),bytes=v.st_size,mtime_ns=v.st_mtime_ns)
def bind(p,e=None):
 a=stat(p);before.setdefault(a['path'],a)
 if e:need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed object/source SMT differs: '+str(p))
 return a
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE;k.CloseHandle.argtypes=[w.HANDLE]
def identity(h,pid):
 ft=[w.FILETIME() for _ in range(4)];need(k.GetProcessTimes(h,*[ctypes.byref(x) for x in ft]),'Native process times unavailable')
 size=w.DWORD(32768);image=ctypes.create_unicode_buffer(size.value);need(k.QueryFullProcessImageNameW(h,0,image,ctypes.byref(size)),'Native image unavailable')
 try:argv=psutil.Process(pid).cmdline()
 except psutil.NoSuchProcess:argv=None
 return dict(pid=pid,created_epoch=((ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime)/1e7-11644473600,exe=image.value,argv=argv)
def invoke(label,argv,env,target=None):
 log=L/(TAG+'.'+label+'.console.log');receipt=L/(TAG+'.'+label+'.call.json');need(not log.exists() and not receipt.exists(),'Call collision')
 record=dict(stage=TAG+'.'+label,program=argv[0],arguments=argv[1:],cwd=str(S),owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),started_utc=utc(),SHA_scans=0)
 th=None
 try:
  with log.open('xb') as f:
   p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT);record['child']=identity(int(p._handle),p.pid)
   if target:
    while p.poll() is None:
     if th is None:
      try:children=psutil.Process(p.pid).children(recursive=True)
      except psutil.NoSuchProcess:children=[]
      for child in children:
       try:
        if child.name().lower()!=target.name.lower():continue
        h=k.OpenProcess(0x1000|0x100000,False,child.pid)
        if not h:continue
        item=identity(h,child.pid)
        if not Path(item['exe']).samefile(target):k.CloseHandle(h);continue
        th=h;record['target']=item;break
       except psutil.NoSuchProcess:continue
     time.sleep(.005)
   rc=p.wait();code=w.DWORD();need(k.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Native tool exit unavailable')
   record.update(actual_Popen_wait_exit=rc,actual_tool_Win32_exit=code.value,ended_utc=utc(),console_log=str(log))
   if th:
    code=w.DWORD();need(k.GetExitCodeProcess(th,ctypes.byref(code)),'Native target exit unavailable');record['actual_target_Win32_exit']=code.value
   save(receipt,record);calls.append(str(receipt))
  need(Path(record['child']['exe']).samefile(argv[0]),'Actual tool identity differs')
  need(record['actual_Popen_wait_exit']==0 and record['actual_tool_Win32_exit']==0,'Actual '+label+' failed; retain '+str(log))
  if target:need(th is not None and record['actual_target_Win32_exit']==0,'Target handle/normal exit missing')
  return record
 finally:
  if th:k.CloseHandle(th)
try:
 need(not HELPER.exists() and not CHECK.exists(),'Fresh repair paths required')
 failed=L/(ACTUAL+'.check.json');first=read(failed);need(first['passed'] is False and 'Actual wrapper header not consumed' in first['first_failure'],'Only the recorded wrong-header audit failure may be repaired');bind(failed)
 for e in first['consumed_stats']:bind(e['path'],e)
 clpath=L/(ACTUAL+'.compile.call.json');cl=read(clpath);need(cl['child']['pid']==48204 and cl['actual_Popen_wait_exit']==0 and cl['actual_tool_Win32_exit']==0,'Actual successful CL48204 required');bind(clpath)
 dep=O/ACTUAL/'compile.dependencies.json';data=read(dep)['Data'];source=T/'support'/(ACTUAL+'.cpp');bind(dep);bind(source)
 need(Path(data['Source']).samefile(source) and Path(cl['arguments'][-1]).samefile(source),'Actual compiled component source differs')
 selected=[p for p in data['Includes'] if Path(p).samefile(S/'source/JSphGpu_ker.h')];need(len(selected)==1,'Actual correct periodic wrapper header identity missing');bind(selected[0])
 obj=O/ACTUAL/'helper.obj';adopted=bind(obj);stamp=obj.stat().st_mtime;lo=datetime.datetime.fromisoformat(cl['started_utc']).timestamp();hi=datetime.datetime.fromisoformat(cl['ended_utc']).timestamp();need(lo-1.<=stamp<=hi+1. and obj.stat().st_size>0,'Fresh original CL object timestamp/size is ambiguous')
 bp=L/'upl_plastic_periodic_Debug_r2.build.json';b=read(bp);need(b['passed'] is True and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'] is True,'Current r2 GPU closure not closed');bind(bp)
 objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(b['project_objects'])==111 and len(objects)==110,'111/110 actual current closure required')
 for e in objects:bind(e['path'],e)
 need(not any('upl_material_periodic_gpu_component' in (p.info['name'] or '').lower() for p in psutil.process_iter(['name'])),'A component target is already active')
 save(L/(TAG+'.adoption.json'),dict(stage=TAG,passed=True,first_check_preserved=stat(failed),actual_CL_receipt=stat(clpath),adopted_object_at_repair=adopted,actual_source_dependencies=stat(dep),correct_header_samefile=stat(selected[0]),wrong_header_predicate_only=True,recompile_performed=False,actual_component_stage_unchanged=ACTUAL,SHA_scans=0))
 recipe=read(L/'upl_noslip_gpu_component_r1_link.call.json');linkargs=[a for a in recipe['arguments'] if not a.lower().endswith('.obj') and not a.upper().startswith(('/OUT:','/PDB:'))];LINK=Path(recipe['program']);CUDA=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');SAN=CUDA/'compute-sanitizer/compute-sanitizer.exe'
 envcall='call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set';setup=subprocess.run('cmd.exe /d /s /c "'+envcall+'"',stdout=subprocess.PIPE,stderr=subprocess.PIPE);need(setup.returncode==0,'MSVC14.36 setup failed');env=dict(os.environ);env.update(a.split('=',1) for a in setup.stdout.decode('mbcs').splitlines() if '=' in a and not a.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Wrong MSVC environment')
 HELPER.mkdir();exe=HELPER/(ACTUAL+'.exe');invoke('link',[str(LINK),*linkargs,'/OUT:'+str(exe),str(obj),*[e['path'] for e in objects],'/PDB:'+str(HELPER/'link.pdb')],env)
 runtime=[]
 for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
  p=R/'bin/windows'/name;bind(p);shutil.copy2(p,HELPER/name);a=stat(p);c=stat(HELPER/name);need((a['bytes'],a['mtime_ns'])==(c['bytes'],c['mtime_ns']),'Runtime copy differs');runtime.append(c)
 save(L/(TAG+'.build.json'),dict(stage=TAG,passed=True,program=stat(exe),source_build=stat(bp),adopted_object=adopted,runtime=runtime,recompile_performed=False,SHA_scans=0))
 sanitizer=L/(TAG+'.sanitizer.log');need(not sanitizer.exists(),'Fresh sanitizer output required');invoke('memcheck',[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanitizer),str(exe),'--out',str(RESULT)],env,exe)
 mem=sanitizer.read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in mem and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in mem,'Actual memcheck is missing/nonzero')
 done=read(RESULT/'completion.json');need(done['passed'] is True and done['stage']==ACTUAL and done['conditions']==4 and done['actual_wrapper_calls']==12 and done['direct_or_chained_image_results']==20 and done['two_tail_points_per_call'] and done['legacy_NULL_vs_ON_defined_array_bytes_equal'],'Actual unchanged component completion differs')
 rows=list(csv.DictReader((RESULT/'copies.csv').open(newline='',encoding='utf-8')));need(len(rows)==24 and len({(r['predictor_arrays_present'],r['history_pointers_present'],r['slot']) for r in rows})==24,'Actual24 unique copy rows missing')
 need((RESULT/'legacy_NULL.bin').read_bytes()==(RESULT/'legacy_ON.bin').read_bytes(),'Legacy defined-field snapshots differ')
 need(all(stat(p)['bytes']==e['bytes'] and stat(p)['mtime_ns']==e['mtime_ns'] for p,e in before.items()),'Consumed source/object SMT changed')
 save(CHECK,dict(stage=TAG,passed=True,actual_component_stage=ACTUAL,completion=done,actual_calls=calls,actual_copy_rows=24,first_failed_check_preserved=True,original_CL_adopted_not_repeated=True,consumed_stats_unchanged=True,consumed_stats=list(before.values()),SHA_scans=0,spatial_solver_invocations=0,physical_acceptance=False));print(json.dumps(dict(passed=True,actual_component_stage=ACTUAL,completion=done)),flush=True)
except BaseException as e:
 if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,first_failed_check_preserved=True,SHA_scans=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
