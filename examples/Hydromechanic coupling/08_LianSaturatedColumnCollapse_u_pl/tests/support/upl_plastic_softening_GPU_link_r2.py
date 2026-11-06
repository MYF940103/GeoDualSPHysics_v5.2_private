"""One link-only repair: retain failed r1 and supply actual host Link items."""
import ctypes,datetime,json,os,shutil,subprocess,time,traceback
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];S=T.parents[3]/'src';L=T/'logs';TAG='upl_plastic_softening_Debug_r2_link'
OUT=T/'outputs'/TAG;INT=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_plastic_softening_link_r2/Debug/int';BUILD=L/(TAG+'.build.json');CALL=L/(TAG+'.call.json')
def need(v,s):
 if not v:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def same(e):
 p=Path(e['path']);return p.is_file() and (p.stat().st_size,p.stat().st_mtime_ns)==(e['bytes'],e['mtime_ns'])
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
record={};rc=None
try:
 need(not any(p.exists() for p in (OUT,INT.parent,BUILD,CALL)),'Fresh repair paths required')
 failed=read(L/'upl_plastic_softening_Debug_r1.build.json');oldcall=read(L/'upl_plastic_softening_Debug_r1.call.json');source=L/'upl_plastic_softening_Debug_r1.source.json';src=read(source)
 need(failed['passed'] is False and oldcall['actual_Win32_exit']==1,'Retained first failed build required')
 before=src['files'];need(all(same(e) for e in before),'Reviewed source/header/project changed')
 oldint=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_plastic_softening_r1/Debug/int';objects=[stat(p) for p in sorted(oldint.glob('*.obj'))]
 need(len(objects)==111 and sum(not Path(e['path']).name.lower().endswith(('.cu.obj','.h.obj')) for e in objects)==97,'Adopted111-object closure differs')
 need((oldint/'main.obj').stat().st_size>0 and (oldint/'FunctionsCuda.obj').stat().st_size>0,'Required actual host objects absent')
 baseline=read(L/'upl_plastic_periodic_Debug_r2.build.json');protected=objects+baseline['project_objects']+[baseline['program']]
 OUT.mkdir();INT.mkdir(parents=True)
 for e in objects:shutil.copy2(e['path'],INT/Path(e['path']).name)
 envcall='call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set';setup=subprocess.run('cmd.exe /d /s /c "'+envcall+'"',stdout=subprocess.PIPE,stderr=subprocess.PIPE);need(setup.returncode==0,'MSVC environment setup failed')
 env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Compiler version differs')
 diag=L/(TAG+'.diagnostic.log');console=L/(TAG+'.log');targets='PrepareForBuild;AddCudaCompileMetadata;ComputeCudaCompileOutput;ComputeCLGeneratedLinkInputs;_Link'
 args=[str(S/'VS/DualSPHysics5Re.vcxproj'),'/m:1','/nr:false','/t:'+targets,'/v:minimal','/p:Configuration=Debug','/p:Platform=x64','/p:PlatformToolset=v143','/p:VCToolsVersion=14.36.32532','/p:BuildProjectReferences=false','/p:PostBuildEventUseInBuild=false','/p:OutDir='+OUT.as_posix()+'/','/p:IntDir='+INT.as_posix()+'/', '/bl:'+str(L/(TAG+'.binlog')),'/flp:LogFile='+str(diag)+';Verbosity=diagnostic']
 owner=psutil.Process();record=dict(stage=TAG,program=oldcall['program'],arguments=args,owner=dict(pid=owner.pid,created_epoch=owner.create_time()),source=str(source),adopted_failed_build=str(L/'upl_plastic_softening_Debug_r1.build.json'),adopted_objects=objects,SHA_scans=0)
 with console.open('xb') as f:
  p=subprocess.Popen([record['program'],*args],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS);q=psutil.Process(p.pid);record['child']=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),arguments=q.cmdline());save(L/(TAG+'.start.json'),record);print('MSBUILD_LINK',p.pid,flush=True)
  rc=p.wait();code=w.DWORD();need(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Native exit unavailable')
 record.update(exit_code=rc,actual_Win32_exit=code.value,actual_typed_exit_code=rc);save(CALL,record)
 need(rc==0 and code.value==0,'Actual link-only repair failed; retain first repair evidence')
 text=diag.read_text(encoding='utf-8-sig',errors='replace');need('Task "CL"' not in text and 'Task "CudaCompile"' not in text and 'nvcc.exe ' not in text,'Unexpected compilation during link-only repair')
 final=[stat(p) for p in sorted(INT.glob('*.obj'))];need(len(final)==111,'Final111 objects absent')
 linklogs=list(INT.rglob('link.read.1.tlog'))+list(INT.rglob('link.command.1.tlog'));inputs='\n'.join(p.read_text(encoding='utf-16',errors='replace') for p in linklogs).replace('\\','/').lower()
 need(linklogs and all(Path(e['path']).as_posix().lower() in inputs for e in final),'Actual Link inputs omit project objects')
 need(all(same(e) for e in before+protected),'Source or retained failed/baseline objects changed')
 exe=OUT/Path(baseline['program']['path']).name;need(exe.is_file(),'Linked program absent')
 save(BUILD,dict(stage=TAG,passed=True,classification='Authoritative link-only repair:97 adopted current host+14 cached CUDA objects',actual_typed_exit_code=rc,actual_Win32_exit=code.value,source=str(source),source_stats_unchanged=True,program=stat(exe),project_objects=final,non_main_objects=110,actual_Link_full111_inputs_verified=True,actual_CL_task_calls=0,actual_NVCC_calls=0,retained_failed_and_baseline_unchanged=True,actual_call=stat(CALL),diagnostic_log=stat(diag),SHA_scans=0,physical_acceptance=False));print('LINK_REPAIR_PASSED',str(exe),flush=True)
except BaseException as e:
 if record and not CALL.exists():record.update(exit_code=rc,first_failure=str(e));save(CALL,record)
 if not BUILD.exists():save(BUILD,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),actual_typed_exit_code=rc,SHA_scans=0,physical_acceptance=False))
 print(traceback.format_exc(),flush=True);raise
