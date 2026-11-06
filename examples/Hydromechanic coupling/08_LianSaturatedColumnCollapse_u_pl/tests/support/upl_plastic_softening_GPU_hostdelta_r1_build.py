"""One authoritative Debug host-delta build with immutable, unchanged cached CUDA objects."""
import ctypes,datetime,filecmp,json,os,shutil,subprocess,time,traceback,zipfile
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';TAG='upl_plastic_softening_Debug_r1'
OUT=T/'outputs'/TAG;INT=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_plastic_softening_r1/Debug/int';BUILD=L/(TAG+'.build.json');CALL=L/(TAG+'.call.json');SRC=L/(TAG+'.source.json')
def need(b,s):
 if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,j):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2);f.write('\n')
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def same(e):
 p=Path(e['path']);return p.is_file() and (p.stat().st_size,p.stat().st_mtime_ns)==(e['bytes'],e['mtime_ns'])
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
before=[];protected=[];copies=[];nvcc={};rc=None;record={}
try:
 need(not any(p.exists() for p in (OUT,INT.parent,BUILD,CALL,SRC)),'Fresh GPU HostDelta paths required')
 bp=L/'upl_plastic_periodic_Debug_r2.build.json';b=read(bp);oldsource=read(b['source']);oldcall=read(L/'upl_plastic_periodic_Debug_r2.call.json')
 need(b['passed'] is True and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'] is True and oldcall['exit_code']==0,'Closed prior r2 GPU build required')
 need(oldsource['compiler']=='MSVC14.36.32532' and oldsource['cuda']=='11.7 sm86','Prior tool/math configuration differs')
 expected_changes={str((S/'source'/x).resolve()) for x in ('JSph.cpp','JSphCpu.cpp','JSphGpu.cpp')}
 compiler_records=[e for e in oldsource['files'] if Path(e['path']).is_relative_to(S/'source') or (Path(e['path']).is_relative_to(S/'VS') and Path(e['path']).suffix.lower() in ('.sln','.vcxproj','.props','.targets'))]
 changed={e['path'] for e in compiler_records if not same(e)};need(changed==expected_changes,'Compiler source/header/project changes differ from the exact3 reviewed cpp bodies')
 before=[stat(e['path']) for e in compiler_records];oldobjects=b['project_objects'];need(len(oldobjects)==111 and all(same(e) for e in oldobjects),'Prior111 objects not unchanged')
 cuda=[e for e in oldobjects if Path(e['path']).name.lower().endswith(('.cu.obj','.h.obj'))];need(len(cuda)==14,'Actual recorded14 CUDA objects required')
 protected=oldobjects+[b['program']]+[stat(p) for p in (R/'bin/windows').iterdir() if p.is_file() and p.suffix.lower() in ('.exe','.pdb','.dll','.xml')]
 proj=S/'VS/DualSPHysics5Re.vcxproj';need(proj.is_file(),'Authoritative GPU project missing');OUT.mkdir();INT.mkdir(parents=True)
 for e in cuda:
  origin=Path(e['path']);target=INT/origin.name;shutil.copy2(origin,target);need(filecmp.cmp(origin,target,shallow=False),'Cached CUDA object bytes differ after copy');copies.append({'origin':e,'copy':stat(target),'byte_compare_equal':True})
 # A fresh current source/header/project snapshot, not an old archive scan or a false fresh CUDA compile.
 archive=OUT/'source.zip'
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for e in before:z.write(e['path'],Path(e['path']).relative_to(R).as_posix())
  z.write(__file__,Path(__file__).relative_to(R).as_posix())
 save(SRC,dict(stage=TAG+'.source',configuration='Debug|x64',compiler='MSVC14.36.32532',cuda='11.7 sm86 cached objects',compiler_source_changes=sorted(changed),files=before,archive=stat(archive),cached_CUDA_origins=copies,authoritative_project=stat(proj),ABI_qualification='No header/device/project change; actual r2 CUDA object bytes reused.3 host method-body changes do not alter class or StSoilCte layout/wrapper ABI.',SHA_scans=0))
 envcall='call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set';setup=subprocess.run('cmd.exe /d /s /c "'+envcall+'"',stdout=subprocess.PIPE,stderr=subprocess.PIPE);need(setup.returncode==0,'MSVC setup failed')
 env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Actual MSVC14.36 required')
 msbuild=Path(oldcall['program']);diag=L/(TAG+'.diagnostic.log');binlog=L/(TAG+'.binlog');console=L/(TAG+'.log');need(not any(p.exists() for p in (diag,binlog,console)),'Fresh logs required')
 targets='PrepareForBuild;ClCompile;AddCudaCompileMetadata;ComputeCudaCompileOutput;Link'
 args=[str(proj),'/m:1','/nr:false','/t:'+targets,'/v:minimal','/p:Configuration=Debug','/p:Platform=x64','/p:PlatformToolset=v143','/p:VCToolsVersion=14.36.32532','/p:BuildProjectReferences=false','/p:PostBuildEventUseInBuild=false','/p:OutDir='+OUT.as_posix()+'/','/p:IntDir='+INT.as_posix()+'/', '/bl:'+str(binlog),'/flp:LogFile='+str(diag)+';Verbosity=diagnostic']
 owner=psutil.Process();record=dict(stage=TAG,classification='authoritative MSBuild HostDelta Debug with cached unchanged CUDA',owner=dict(pid=owner.pid,created_epoch=owner.create_time()),program=str(msbuild),arguments=args,working_directory=str(S),started_utc=utc(),SHA_scans=0)
 with console.open('xb') as f:
  p=subprocess.Popen([str(msbuild),*args],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS);q=psutil.Process(p.pid);record['child']=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),arguments=q.cmdline());save(L/(TAG+'.start.json'),record);print('MSBUILD',p.pid,'owner',owner.pid,flush=True)
  while p.poll() is None:
   try:
    for child in psutil.Process(p.pid).children(recursive=True):
     try:
      if child.name().lower()=='nvcc.exe':nvcc[(child.pid,child.create_time())]=dict(pid=child.pid,created_epoch=child.create_time(),exe=child.exe(),argv=child.cmdline())
     except psutil.NoSuchProcess:pass
   except psutil.NoSuchProcess:pass
   time.sleep(.04)
  rc=p.wait();code=w.DWORD();need(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Actual MSBuild Win32 exit unavailable')
 record.update(exit_code=rc,actual_Win32_exit=code.value,actual_typed_exit_code=rc,ended_utc=utc(),observed_nvcc_processes=list(nvcc.values()));save(CALL,record)
 objects=[stat(p) for p in sorted(INT.glob('*.obj'))];need(rc==0 and code.value==0,'Actual authoritative HostDelta build failed; retain first logs')
 need(len(objects)==111 and {Path(e['path']).name for e in objects}=={Path(e['path']).name for e in oldobjects},'Final full111 project object closure differs')
 freshhost=[e for e in objects if not Path(e['path']).name.lower().endswith(('.cu.obj','.h.obj'))];need(len(freshhost)==97,'Actual97 freshly rebuilt host objects required')
 reused=sum(same(e['copy']) and filecmp.cmp(e['origin']['path'],e['copy']['path'],shallow=False) for e in copies)
 text=diag.read_text(encoding='utf-8-sig',errors='replace');cuda_tasks=text.count('Task "CudaCompile"');cuda_targets=text.count('Target "CudaBuild:')
 need(all(same(e) for e in before),'Current compiler source/header/project changed during build');need(all(same(e) for e in protected),'Retained r2/canonical object/program changed')
 exe=OUT/Path(b['program']['path']).name;need(exe.is_file() and exe.stat().st_size>0,'Actual new linked GPU program missing')
 # The diagnostic Link task must list all111 actual objects, not just the new host subset.
 link_logs=list(INT.glob('**/link.read.1.tlog'))+list(INT.glob('**/link.command.1.tlog'));link_inputs='\n'.join(p.read_text(encoding='utf-16',errors='replace') for p in link_logs).replace('\\','/').lower()
 need(link_logs and all(Path(e['path']).as_posix().lower() in link_inputs for e in objects),'Actual fresh Link tracking does not expose the full111 object inputs')
 classification='HostDelta Debug:14 cached CUDA +97 fresh host' if reused==14 and not nvcc and cuda_tasks==0 and cuda_targets==0 else 'Unexpected fresh CUDA activity; review cache classification, no blind rerun'
 save(BUILD,dict(stage=TAG,passed=True,classification=classification,actual_typed_exit_code=rc,actual_Win32_exit=code.value,source=str(SRC),source_stats_unchanged=True,source_capture=stat(SRC),program=stat(exe),project_objects=objects,non_main_objects=110,cached_CUDA_objects=copies,reused_CUDA_count=reused,fresh_host_count=97,observed_nvcc_process_calls=len(nvcc),diagnostic_CudaCompile_task_calls=cuda_tasks,diagnostic_CudaBuild_target_calls=cuda_targets,actual_Link_full111_inputs_verified=True,protected_r2_and_canonical_unchanged=True,diagnostic_log=stat(diag),actual_call=stat(CALL),SHA_scans=0,physical_acceptance=False));print('GPU_HOSTDELTA_BUILD_PASSED',classification,str(exe),flush=True)
except BaseException as e:
 if record and not CALL.exists():record.update(exit_code=rc,ended_utc=utc(),first_failure=str(e));save(CALL,record)
 if not BUILD.exists():save(BUILD,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),actual_typed_exit_code=rc,observed_nvcc_processes=list(nvcc.values()),cached_CUDA_origins=copies,SHA_scans=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
