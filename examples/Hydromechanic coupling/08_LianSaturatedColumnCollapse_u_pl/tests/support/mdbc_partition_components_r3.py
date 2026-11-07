"""Explicit single component build or single zero-step case; no solver/matrix/retry."""
import argparse,ctypes,datetime,json,os,re,shutil,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';P=T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests';L=T/'logs';TAG='mdbc_partition_components_r3'
SPECS={'CPU_planes':(False,P/'support/spr_planes_test.cpp'),'GPU_planes':(True,P/'support/spr_gpu_planes_test.cpp'),'CPU_wall':(False,T/'support/upl_noslip_cpu_component_r1.cpp'),'GPU_wall':(True,T/'support/upl_noslip_gpu_component_r1.cpp')}
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE];K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];K.QueryFullProcessImageNameW.restype=w.BOOL
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];K.GetProcessTimes.restype=w.BOOL
def need(b,s):
 if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,j):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2);f.write('\n')
def bind(e):
 a=stat(e['path']);need(a==e,'Consumed stat changed: '+e['path']);return a
def ident(h,pid):
 ft=[w.FILETIME() for _ in range(4)];n=w.DWORD(32768);exe=ctypes.create_unicode_buffer(n.value)
 need(K.GetProcessTimes(h,*[ctypes.byref(x) for x in ft]) and K.QueryFullProcessImageNameW(h,0,exe,ctypes.byref(n)),'Owned handle identity unavailable')
 try:q=psutil.Process(pid);args=q.cmdline();parent=q.ppid()
 except psutil.NoSuchProcess:args=None;parent=None
 return dict(pid=pid,creation_filetime_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime,exe=exe.value,argv=args,parent_pid=parent)
def invoke(tag,argv,cwd,env=None,target=None):
 log=L/(tag+'.log');call=L/(tag+'.call.json');need(not log.exists() and not call.exists(),'Existing invocation protected')
 rec=dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),program=argv[0],arguments=argv[1:],cwd=str(cwd),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());h=None;targetid=None;failure=None
 with log.open('xb') as f:
  p=subprocess.Popen(argv,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  child=ident(int(p._handle),p.pid);print(tag,'PID',p.pid,flush=True)
  try:
   if target:
    while p.poll() is None and h is None:
     for q in psutil.Process(p.pid).children(recursive=True):
      try:
       if Path(q.exe()).samefile(target):
        h=K.OpenProcess(0x100000|0x1000,False,q.pid);need(h,'Target handle unavailable');targetid=ident(h,q.pid);break
      except (psutil.NoSuchProcess,psutil.AccessDenied):pass
     if h is None:time.sleep(.01)
  except Exception as e:failure=str(e)
  rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)));tc=w.DWORD();tg=bool(h and K.GetExitCodeProcess(h,ctypes.byref(tc)))
 if h:K.CloseHandle(h)
 rec.update(child=child,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,actual_target=targetid,actual_target_Win32_exit=tc.value if tg else None,ownership_failure=failure,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),log=stat(log));save(call,rec)
 need(got and rc==code.value==0 and failure is None and (not target or tg and tc.value==0),'Invocation failed or owner proof incomplete; preserve first result, no retry')
 return stat(call)
def build(key):
 gpu,source=SPECS[key];tag=TAG+'_'+key;out=T/'outputs'/tag;check=L/(tag+'.build.json');need(not out.exists() and not check.exists(),'Existing build protected');calls=[];before=[]
 try:
  if key=='CPU_planes':
   prior=L/'mdbc_partition_components_r1_CPU_planes.build.json';b=read(prior)
   need(b['passed'] and b['consumed_stats_unchanged'] and b['project_non_main_objects']==86 and b['actual_link_objects']==87,'Closed r1 CPU_planes helper required for adoption')
   before=[stat(prior),bind(b['program']),bind(b['source']),bind(b['source_build']),bind(b['source_capture']),*[bind(e) for e in b['runtime']],stat(__file__),stat(T/'notes'/(TAG+'.json'))]
   save(check,dict(stage=tag+'.build',passed=True,program=b['program'],source=b['source'],source_build=b['source_build'],source_capture=b['source_capture'],runtime=b['runtime'],adopted_build=stat(prior),project_non_main_objects=86,adopted_link_objects=87,calls=[],consumed=before,consumed_stats_unchanged=True,compile_link_invocations=0,component_invocations=0,SHA_scans=0));print('Adopted closed r1 CPU_planes helper; no recompile',flush=True);return
  bp=L/('mdbc_partition_Debug_r1.build.json' if gpu else 'mdbc_partition_DebugCPU_r1.build.json');b=read(bp);expected=113 if gpu else 87
  need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==expected,'Closed current authoritative Debug build required')
  before=[stat(bp),bind(b['source_capture']),stat(source),stat(__file__),stat(T/'notes'/(TAG+'.json'))]
  objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==expected-1,'Exactly one project main must be excluded');before += [bind(e) for e in objects]
  oldtag='upl_noslip_gpu_component_r1' if gpu else 'upl_noslip_cpu_component_r1';oldroot=T/'outputs'/oldtag;cp=L/(oldtag+'_compile.call.json');lp=L/(oldtag+'_link.call.json');c,l=read(cp),read(lp);before += [stat(cp),stat(lp)]
  need((c['actual_exit_code']==l['actual_exit_code']==0 and c['direct_Popen_wait'] is True and l['direct_Popen_wait'] is True) if gpu else (c['exit_code']==l['exit_code']==0 and c['owned_call_exited'] and l['owned_call_exited']),'Passed same-backend Debug compiler/link recipe required')
  oldsource=next(x for x in c['arguments'] if x.lower().endswith('.cpp'));exe=out/'component.exe'
  ca=[str(source) if x==oldsource else x.replace(str(oldroot),str(out)) for x in c['arguments']]
  if '/sourceDependencies' not in ca:ca += ['/sourceDependencies',str(out/'compile.dependencies.json')]
  la=[x.replace(str(oldroot),str(out)).replace(oldtag+'.exe','component.exe') for x in l['arguments'] if not x.lower().endswith('.obj')]+[str(out/'helper.obj'),*[e['path'] for e in objects]]
  need('/Od' in ca and '/MTd' in ca and '/fp:precise' in ca and ('/D_WITHGPU' in ca)==gpu and sum(x.lower().endswith('.obj') for x in la)==expected,'Debug flag/object closure differs')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
  out.mkdir();calls.append(invoke(tag+'.compile',[c['program'],*ca],S,env));calls.append(invoke(tag+'.link',[l['program'],*la],S,env));runtime=[]
  for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
   a=stat(oldroot/leaf);before.append(a);shutil.copy2(a['path'],out/leaf);d=stat(out/leaf);need((a['bytes'],a['mtime_ns'])==(d['bytes'],d['mtime_ns']),'Debug runtime copy differs');runtime.append(d)
  need(all(stat(e['path'])==e for e in before),'Consumed build inputs changed')
  save(check,dict(stage=tag+'.build',passed=True,program=stat(exe),source=stat(source),source_build=stat(bp),source_capture=b['source_capture'],project_non_main_objects=len(objects),actual_link_objects=expected,runtime=runtime,calls=calls,consumed=before,consumed_stats_unchanged=True,source_cloned=False,component_invocations=0,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=tag+'.build',passed=False,first_failure=str(e),calls=calls,consumed=before,SHA_scans=0))
  raise
def seed_refs(prefix):
 return [stat(str(prefix)+s) for s in ('.xml','.bi4')]+([stat(str(prefix)+'_Normals.nbi4')] if Path(str(prefix)+'_Normals.nbi4').exists() else [])
def case(key,label):
 gpu,_=SPECS[key]
 if key.endswith('planes'):
  need(label in {g+'_s'+str(s) for g in ('corner2','edge3') for s in (1,2,3)},'Only explicit corner2/edge3 and three slips are admitted')
  geometry,slip=label.rsplit('_s',1)
  if gpu:
   rp=P/'logs/spr_gpu_planes_dbg_r1.check.json';r=read(rp);need(r['passed'],'Old Debug GPU control failed');v=next(x for x in r['runs'] if x['geometry']==geometry and x['slip']==int(slip));a=v['command'][1:];control=Path(a[3]);prefix=Path(a[2]);args=a.copy();args[3]='OUTPUT'
  else:
   rp=P/'logs/spr_planes_r2_dbg.check.json';r=read(rp);need(r['passed'],'Old Debug CPU control failed');name='spr_planes_r2_dbg_'+label;v=next(x for x in r['runs'] if x['name']==name);control=P/'outputs'/name;prefix=P/'outputs'/(name+'_input')/name;args=['-cpu','-ompthreads:1',str(prefix),'OUTPUT','-dirdataout','data','-sv:none']
  need(v['exit_code']==0,'Old component exit failed');completion='planes_complete.json';refs=[stat(rp)]+seed_refs(prefix)
 elif not gpu:
  need(label in ('Wendland','Cubic'),'Explicit CPU kernel required');old='upl_noslip_CPU_'+label+'_r1';rp=L/(old+'.check.json');need(read(rp)['passed'],'Old CPU wall control failed');cl=L/(old+'.call.json');a=read(cl);need(a['exit_code']==0 and a['owned_call_exited'],'Old wall call failed');args=a['arguments'].copy();control=Path(args[-1]);prefix=Path(args[-2]);args[-1]='OUTPUT';completion='completion.json';refs=[stat(rp),stat(cl)]+seed_refs(prefix)
 else:
  need(label=='all','GPU wall contains its fixed12 conditions, select all');rp=L/'upl_noslip_gpu_component_r1.check.json';need(read(rp)['passed'] and read(rp)['zero_errors_and_leaks'],'Old GPU wall control failed');control=T/'outputs/upl_noslip_gpu_component_r1/result';args=['--out','OUTPUT'];completion='completion.json';refs=[stat(rp)]
 need(control.is_dir() and read(control/completion)['passed'],'Closed old completion required')
 return args,control,completion,refs
def run(key,label,memcheck):
 gpu,_=SPECS[key];need(not memcheck or gpu,'Memcheck is GPU-only');tag=TAG+'_'+key+'_'+label;out=T/'outputs'/tag;check=L/(tag+'.check.json');need(not out.exists() and not check.exists(),'Existing case/partial result protected');before=[];call=None
 try:
  bp=L/(TAG+'_'+key+'.build.json');b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'],'Current component build required');before=[stat(bp),bind(b['program']),bind(b['source_build']),bind(b['source_capture']),*[bind(e) for e in b['runtime']],stat(__file__)];exe=Path(b['program']['path'])
  args,control,completion,refs=case(key,label);before += refs+[stat(p) for p in sorted(control.glob('*.csv'))]+[stat(control/completion)];need(any(control.glob('*.csv')),'No retained raw CSV controls');argv=[str(exe),*[str(out) if a=='OUTPUT' else a for a in args]];sanlog=L/(tag+'.memcheck.log')
  if memcheck:before.append(stat(SAN));need(not sanlog.exists(),'Existing memcheck protected');argv=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*argv]
  call=invoke(tag+'.run',argv,exe.parent,target=exe if memcheck else None);d=read(out/completion);need(d['passed'],'Original component numerical guards failed');same=[]
  need({p.name for p in out.glob('*.csv')}=={p.name for p in control.glob('*.csv')},'Raw CSV names/count differ')
  for p in sorted(control.glob('*.csv')):need(p.read_bytes()==(out/p.name).read_bytes(),'Raw CSV differs: '+p.name);same.append(dict(old=stat(p),new=stat(out/p.name),byte_exact=True))
  if memcheck:
   text=sanlog.read_text(encoding='utf-8');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',text);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',text);need(errors and leaks and all(int(x.replace(',',''))==0 for x in errors) and all(int(x.replace(',',''))==int(y.replace(',',''))==0 for x,y in leaks),'Memcheck errors/leaks missing or nonzero')
  need(all(stat(e['path'])==e for e in before),'Consumed case inputs/control changed')
  save(check,dict(stage=tag,passed=True,component_build=stat(bp),actual_call=call,native_completion=stat(out/completion),original_completion=d,same_backend_Debug_CSV=same,memcheck_zero_errors_and_leaks=True if memcheck else None,consumed=before,consumed_stats_unchanged=True,physical_steps=0,solver_invocations=0,physical_acceptance=False,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=tag,passed=False,first_failure=str(e),actual_call=call,consumed=before,solver_invocations=0,SHA_scans=0))
  raise
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','run'));p.add_argument('component',choices=tuple(SPECS));p.add_argument('--case');p.add_argument('--memcheck',action='store_true');p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until the reviewed execution is authorized')
 if a.action=='build':need(a.case is None and not a.memcheck,'Build never runs a component');build(a.component)
 else:need(a.case is not None,'One explicit case is required; no implicit matrix');run(a.component,a.case,a.memcheck)
if __name__=='__main__':main()
