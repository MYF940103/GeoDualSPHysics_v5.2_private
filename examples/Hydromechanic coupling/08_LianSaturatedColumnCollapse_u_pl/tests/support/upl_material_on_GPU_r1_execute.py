import csv,ctypes,datetime,json,os,re,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';O=T/'outputs';TAG='upl_material_on_GPU_r1'
STEM='CaseLianSaturatedColumnCollapse_material_on_r1';OUT=O/TAG;RUN=O/(TAG+'_runtime');SEED=O/'upl_material_on_r1_seed'
NATIVE=O/(TAG+'_native_r1');HELPER=O/'upl_material_on_native_r1';CHECK=L/(TAG+'.check.json');before={};calls=[]
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
 need(not any(p.exists() for p in (OUT,RUN,SEED,NATIVE,HELPER,CHECK)),'Fresh ON paths/receipt required')
 for name in ('upl_material_default_r1.check.json','upl_material_default_GPU_r1.check.json'):
  p=L/name;j=read(p);need(j['passed'] is True and j['consumed_stats_unchanged'] is True,'Default closure is not passed/unchanged');bind(p)
 prior=read(L/'upl_material_default_GPU_r1.check.json');need(all(q['bit_identical'] for q in prior['comparisons'].values()),'Default retained22/clock/IDs compatibility failed')
 active=[q.info for q in psutil.process_iter(['pid','name']) if 'dualsphysics' in (q.info['name'] or '').lower()];need(not active,'An actual solver remains active: '+str(active))
 builds={}
 for backend,label,count in (('CPU','DebugCPU',85),('GPU','Debug',110)):
  p=L/('upl_material_'+label+'_r1.build.json');b=read(p);need(b['passed'] is True and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'] is True and b['non_main_objects']==count,'Sealed current engine build differs');bind(p);bind(b['program']['path'],b['program']);builds[backend]=b
 cfg=T/'configs'/(STEM+'.xml');definition=T/'configs'/(STEM+'_Def.xml');source=T/'support/upl_material_on_native_r1.cpp'
 for p in (Path(__file__),cfg,definition,source,T/'notes/upl_material_on_GPU_r1.json',T/'notes/upl_material_on_native_r1.json',T/'support'/('x'+STEM+'_win64_GPU.bat')):bind(p)
 import xml.etree.ElementTree as ET
 tree=ET.parse(cfg).getroot();soil=tree.find('execution/special/soils');need(soil.find('MaterialReturn').get('value')=='1' and soil.find('DilationDecay').get('value')=='0','Only explicit mode1/decay0 admitted')
 for key in ('MaterialReturn','DilationDecay'):soil.remove(soil.find(key))
 control=ET.parse(T/'configs/CaseLianSaturatedColumnCollapse_free_seepage_start_r1.xml').getroot();need(ET.tostring(tree)==ET.tostring(control),'ON companion differs beyond two explicit soil keys')
 # The BAT is not executed: perform its preparation only, then run its exact target once under memcheck.
 need((O/'upl_material_default_GPU_r1/solver_exit_code.txt').read_text().strip()=='0','Retained default GPU immediate exit is not0')
 oldseed=O/'upl_c08_observer_r1_seed';oldname='CaseLianSaturatedColumnCollapse_geometry_r1'
 pairs=[(cfg,SEED/(STEM+'.xml')),(oldseed/(oldname+'.bi4'),SEED/(STEM+'.bi4')),(oldseed/(oldname+'_Normals.nbi4'),SEED/(STEM+'_Normals.nbi4'))]
 exe=RUN/Path(builds['GPU']['program']['path']).name;pairs.append((Path(builds['GPU']['program']['path']),exe))
 for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):pairs.append((R/'bin/windows'/name,RUN/name))
 for p,q in pairs:bind(p)
 for p in (SEED,RUN,OUT):p.mkdir()
 for p,q in pairs:
  shutil.copy2(p,q);a=stat(p);b=stat(q);need((a['bytes'],a['mtime_ns'])==(b['bytes'],b['mtime_ns']),'Fresh preparation copy SMT differs')
 CUDA=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');SAN=CUDA/'compute-sanitizer/compute-sanitizer.exe';bind(SAN)
 argv=[str(exe),'-gpu:0','-stable','-mdbc_freeslip',str(SEED/STEM),str(OUT),'-dirdataout','data','-svres','-nsteps:128']
 (OUT/'run_command.txt').write_text(subprocess.list2cmdline(argv)+'\n',encoding='utf-8')
 save(L/(TAG+'.inputs.json'),dict(stage=TAG,source_builds={k:stat(L/('upl_material_'+('DebugCPU' if k=='CPU' else 'Debug')+'_r1.build.json')) for k in builds},prepared=[stat(q) for p,q in pairs],exact_target_argv=argv,BAT_executed=False,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),SHA_scans=0,physical_acceptance=False))
 sanitizer=L/(TAG+'.sanitizer.log');need(not sanitizer.exists(),'Existing sanitizer output protected')
 invoke('memcheck',[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanitizer),*argv],dict(os.environ),exe)
 mem=sanitizer.read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in mem and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in mem,'Memcheck summaries missing/nonzero')
 owned=read(L/(TAG+'.memcheck.call.json'));(OUT/'solver_exit_code.txt').write_text(str(owned['actual_target_Win32_exit'])+'\n',encoding='ascii')
 with (OUT/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
 need(len(rows)==1,'One completed Run.csv row required');summary=rows[0];raw=(OUT/'Run.out').read_text(encoding='utf-8',errors='replace')
 for key,value in dict(Steps=128,Np=7060,Nbound=2060,Nfixed=2060,PartFiles=5,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items():need(int(summary[key])==value,'Native run count/exclusion differs: '+key)
 need('Finished execution (code=0).' in raw and 'DTs adjusted to DtMin............: 0' in raw,'Normal completion or original time-step guard failed')
 need('MaterialReturn: 1=ConsistentDev' in raw and 'DilationDecay: 0' in raw and 'HydroMechFreeSeepage=True' in raw,'Explicit material/free configuration not observed in actual Run.out')
 need('SoilHourglass: forcecalls=' not in raw and 'GNOG(' not in summary['Configuration'] and 'SoilDamping(' not in summary['Configuration'],'Unchanged HG/damping configuration differs')
 saves=[int(m[1]) for m in re.finditer(r'^Part_\d+\s+[0-9.eE+-]+\s+(\d+)\s+\d+\s+.*$',raw,re.M)];need(saves==[32,64,96,128],'Actual32-update saves differ')
 save(L/(TAG+'.run.check.json'),dict(stage=TAG,passed=True,actual_call=stat(L/(TAG+'.memcheck.call.json')),summary=summary,saves=saves,memcheck_zero_errors_leaks=True,native_pending=True,SHA_scans=0,physical_acceptance=False))
 # Only after the one sealed physical target: compile/link the fresh reader once using the current85 CPU objects.
 objects=[e for e in builds['CPU']['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==85,'Current CPU85 closure differs')
 for e in objects:bind(e['path'],e)
 oldc=read(L/'upl_c08_free_seepage_start_native_r1.compile.call.json');oldl=read(L/'upl_c08_free_seepage_start_native_r1.link.call.json');oldroot=str(O/'upl_c08_free_seepage_start_native_r1');reader=HELPER/'upl_material_on_native_r1.exe'
 ca=[x.replace(oldroot,str(HELPER)).replace('upl_c08_free_seepage_start_native_r1.cpp',source.name) for x in oldc['arguments']];la=[]
 for x in oldl['arguments']:
  if x.lower().endswith('.obj'):
   if Path(x).name.lower()=='helper.obj':la.extend([str(HELPER/'helper.obj')]+[e['path'] for e in objects])
  else:la.append(x.replace(oldroot,str(HELPER)).replace('upl_c08_free_seepage_start_native_r1.exe',reader.name))
 envcall='call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set';setup=subprocess.run('cmd.exe /d /s /c "'+envcall+'"',stdout=subprocess.PIPE,stderr=subprocess.PIPE);need(setup.returncode==0,'MSVC14.36 environment failed')
 env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Wrong actual MSVC environment')
 HELPER.mkdir();invoke('reader.compile',[oldc['program'],*ca],env);invoke('reader.link',[oldl['program'],*la],env)
 for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):shutil.copy2(R/'bin/windows'/name,HELPER/name)
 save(L/'upl_material_on_native_r1.build.json',dict(stage='upl_material_on_native_r1',passed=True,program=stat(reader),source=stat(source),source_build=stat(L/'upl_material_DebugCPU_r1.build.json'),objects=objects,SHA_scans=0,physical_acceptance=False))
 invoke('native',[str(reader),'--read','GPU',str(OUT/'data'),str(NATIVE)],env)
 done=read(NATIVE/'completion.json');need(done['passed'] is True and done['stage']=='upl_material_on_native_r1' and done['input_run_tag']==TAG,'Fresh native profile completion differs')
 for key,value in dict(samples=5,completed_steps=128,total_native_IDs=7060,typed_arrays=22,soil_cache_float_bits_checks=25000,noninitial_signed_intervals=4).items():need(done[key]==value,'Original native coverage differs: '+key)
 comparisons={};oldnative=O/'upl_material_default_GPU_r1_native_r1'
 for name in ('typed22.bin','clocks.csv','typed22_layout.csv','native_ids.csv'):
  a=(NATIVE/name).read_bytes();b=(oldnative/name).read_bytes();need(len(a)==len(b),'Descriptive same-backend export size differs: '+name)
  pairsdiff=[(x,y) for x,y in zip(a,b) if x!=y];comparisons[name]=dict(bit_identical=a==b,different_bytes=len(pairsdiff),different_bits=sum((x^y).bit_count() for x,y in pairsdiff),comparison_is_descriptive=True)
 changed=[p for p,e in before.items() if not Path(p).is_file() or stat(p)!=e];need(not changed,'Consumed source/program/input SMT changed')
 save(CHECK,dict(stage=TAG,passed=True,actual_call=stat(L/(TAG+'.memcheck.call.json')),reader_call=stat(L/(TAG+'.native.call.json')),native_completion=done,same_backend_default_descriptive=comparisons,summary=summary,consumed_stats_unchanged=True,consumed_stats=list(before.values()),solver_invocations=1,reader_invocations=1,SHA_scans=0,physical_acceptance=False))
 print(json.dumps(dict(passed=True,same_backend_default_descriptive=comparisons,native=done)),flush=True)
except BaseException as e:
 if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,consumed_stats=list(before.values()),SHA_scans=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
