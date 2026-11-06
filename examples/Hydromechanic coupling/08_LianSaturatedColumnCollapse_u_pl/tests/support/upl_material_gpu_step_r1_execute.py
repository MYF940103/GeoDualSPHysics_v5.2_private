import csv,ctypes,datetime,json,os,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';O=T/'outputs';TAG='upl_material_gpu_step_r1'
HELPER=O/TAG;RESULT=HELPER/'result';CHECK=L/(TAG+'.check.json');BUILD=L/(TAG+'.build.json')
SOURCE=T/'support'/ (TAG+'.cpp');NOTE=T/'notes'/(TAG+'.json');PLAN=T/'notes'/(TAG+'_build_plan.md')
before={};calls=[];result={}
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
 need(not HELPER.exists() and not CHECK.exists() and not BUILD.exists(),'Fresh helper/receipts required')
 bp=L/'upl_material_Debug_r1.build.json';bc=L/'upl_material_Debug_r1.call.json';b=read(bp);c=read(bc)
 need(b['passed'] is True and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'] is True,'Authoritative new GPU build not closed/passed')
 need(c['exit_code']==0 and c['typed_returncode_captured_from_Popen_wait'] is True,'Actual GPU MSBuild exit is not typed0')
 bind(bp);bind(bc);objects=b['project_objects'];need(len(objects)==111,'Exactly111 actual project objects required')
 objdir=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_material_r1/Debug/int'
 need(all(Path(e['path']).resolve().parent==objdir.resolve() for e in objects),'Object from a different closure')
 need(sum(Path(e['path']).name.lower()=='main.obj' for e in objects)==1,'Exactlyone main object expected')
 objects=[e for e in objects if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==110,'110 nonmain objects required')
 for e in objects:bind(e['path'],e)
 source_record=read(b['source']);expected={str(Path(e['path']).resolve()):e for e in source_record['files']};bind(b['source'])
 for p in (SOURCE,NOTE,PLAN,T/'support/upl_material_shared_cases_r1.h',T/'support/upl_material_shared_candidate_r1.h',T/'outputs/upl_material_return_CPU_result_r1/points.csv',T/'outputs/upl_material_shared_CPU_r1/result/points.csv',T/'outputs/upl_material_shared_CPU_r1/result/completion.json'):bind(p)
 for name in ('DualSphDef.h','FunSoilMaterial.h','JSphGpu.h','JSphGpu.cpp','JSphGpuSimple_ker.h','JSphGpuSimple_ker.cu'):
  p=(S/'source'/name).resolve();bind(p,expected[str(p)])
 CL=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe');LINK=CL.with_name('link.exe');CUDA=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');SAN=CUDA/'compute-sanitizer/compute-sanitizer.exe'
 for p in (CL,LINK,SAN):bind(p)
 recipe=read(L/'upl_noslip_gpu_component_r1_link.call.json');linkargs=[a for a in recipe['arguments'] if not a.lower().endswith('.obj') and not a.upper().startswith(('/OUT:','/PDB:'))]
 for a in linkargs:
  if a.lower().endswith('.lib'):
   for folder in (S/'lib/vs2022',CUDA/'lib/x64'):
    if (folder/a).is_file():bind(folder/a);break
 envcall='call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set'
 setup=subprocess.run('cmd.exe /d /s /c "'+envcall+'"',stdout=subprocess.PIPE,stderr=subprocess.PIPE);need(setup.returncode==0,'MSVC environment setup failed')
 env=dict(os.environ);env.update(a.split('=',1) for a in setup.stdout.decode('mbcs').splitlines() if '=' in a and not a.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Wrong actual MSVC host environment');env['OMP_NUM_THREADS']='1'
 HELPER.mkdir();obj=HELPER/'helper.obj';exe=HELPER/(TAG+'.exe');deps=HELPER/'compile.dependencies.json'
 invoke('compile',[str(CL),'/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU','/I'+str(S/'source'),'/I'+str(CUDA/'include'),'/Fo'+str(obj),'/Fd'+str(HELPER/'compile.pdb'),'/sourceDependencies',str(deps),'/Od','/MTd','/Zi','/RTC1',str(SOURCE)],env)
 headers=[]
 for x in read(deps)['Data']['Includes']:
  p=Path(x).resolve();headers.append(bind(p,expected.get(str(p))))
 need(any(Path(x['path']).name=='JSphGpuSimple_ker.h' for x in headers),'Actual wrapper header not consumed')
 invoke('link',[str(LINK),*linkargs,'/OUT:'+str(exe),str(obj),*[e['path'] for e in objects],'/PDB:'+str(HELPER/'link.pdb')],env)
 runtime=[]
 for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
  p=R/'bin/windows'/name;e=bind(p);shutil.copy2(p,HELPER/name);a=stat(HELPER/name);need((e['bytes'],e['mtime_ns'])==(a['bytes'],a['mtime_ns']),'Runtime copy SMT differs');runtime.append(a)
 save(BUILD,dict(stage=TAG,passed=True,source_build=stat(bp),program=stat(exe),objects=objects,headers=headers,runtime=runtime,calls=calls.copy(),SHA_scans=0,physical_acceptance=False))
 sanitizer=L/(TAG+'.sanitizer.log');need(not sanitizer.exists(),'Sanitizer output already exists')
 invoke('memcheck',[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanitizer),str(exe),'--source',str(T/'outputs/upl_material_return_CPU_result_r1/points.csv'),'--cpu',str(T/'outputs/upl_material_shared_CPU_r1/result/points.csv'),'--out',str(RESULT)],env,exe)
 mem=sanitizer.read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in mem and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in mem,'Memcheck summaries are missing/nonzero')
 done=read(RESULT/'completion.json');need(done['passed'] is True and done['stage']==TAG,'Component completion failed')
 for key,value in dict(case_rows=71,actual_wrapper_calls=142,Pre_history_checks=54,Cor_history_checks=54,failure_native_unchanged_checks=34,tail_point_checks=284,protected_input_record_checks=2982).items():need(done[key]==value,'Completion count differs: '+key)
 rows=list(csv.DictReader((RESULT/'steps.csv').open(newline='',encoding='utf-8')));need(len(rows)==142 and len({(r['id'],r['stage']) for r in rows})==142,'Actual142 unique stage rows missing')
 metrics=dict(max_stress_CPU_difference_Pa=max(float(r['stress_CPU_difference_Pa']) for r in rows),max_original_budget_ratio=max(float(r['stress_CPU_difference_Pa'])/float(r['combined_original_tensor_budget_Pa']) for r in rows if float(r['combined_original_tensor_budget_Pa'])>0),failure_rows=sum(int(r['status_bits'])!=0 for r in rows))
 changed=[p for p,e in before.items() if not Path(p).is_file() or stat(p)!=e];need(not changed,'Consumed source/object/input SMT changed')
 save(CHECK,dict(stage=TAG,passed=True,completion=done,metrics=metrics,calls=calls,consumed_stats=list(before.values()),consumed_stats_unchanged=True,SHA_scans=0,solver_or_decoder_invocations=0,physical_acceptance=False))
 print(json.dumps(dict(passed=True,metrics=metrics,completion=done)),flush=True)
except BaseException as e:
 if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,consumed_stats=list(before.values()),SHA_scans=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
