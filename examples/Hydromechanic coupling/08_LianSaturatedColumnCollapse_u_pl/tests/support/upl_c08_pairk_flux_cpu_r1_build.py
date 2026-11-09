"""One helper CL/link against the frozen runtime_r6 bedkeep CPU closure; never a solver build."""
import argparse,ctypes,datetime,os,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import mdbc_partition_components_r3 as old
T=Path(__file__).resolve().parents[1];S=T.parents[3]/'src';L=T/'logs';TAG='upl_c08_pairk_flux_cpu_r1'
CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md');HELPER=T/'outputs'/(TAG+'_helper');PROGRAM=HELPER/'component.exe'
CPU=L/'upl_c08_bedkeep_DebugCPU_r1.build.json';GPU=L/'upl_c08_bedkeep_Release_r1.build.json'
need,read,stat,bind,save=old.need,old.read,old.stat,old.bind,old.save

def invoke(tag,argv,cwd,env=None):
 log=L/(tag+'.log');call=L/(tag+'.call.json');need(not log.exists() and not call.exists(),'Existing actual call protected');failure=None;identity=None
 rec=dict(stage=tag,program=str(argv[0]),arguments=list(map(str,argv[1:])),cwd=str(cwd),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 with log.open('xb') as f:
  p=subprocess.Popen(list(map(str,argv)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);print(tag,'actual_PID',p.pid,flush=True)
  try:identity=old.ident(int(p._handle),p.pid)
  except Exception as e:failure=str(e)
  finally:rc=p.wait();code=old.w.DWORD();got=bool(old.K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
 rec.update(child=identity,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,typed_returncode_captured_before_postchecks=True,ownership_failure=failure,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),log=stat(log));save(call,rec)
 need(got and rc==code.value==0 and failure is None,'Actual invocation failed; preserve evidence, no retry');return stat(call)

def build():
 check=L/(TAG+'.build.json');need(not HELPER.exists() and not check.exists(),'Existing complete/partial helper build protected');before=[];calls=[]
 try:
  b,g=read(CPU),read(GPU);need(b['passed'] and g['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==g['actual_typed_exit_code']==g['actual_Win32_exit']==0 and b['source_stats_unchanged'] and g['source_stats_unchanged'] and b['source_capture']==g['source_capture'] and b['source_archive']==g['source_archive'] and len(b['project_objects'])==87,'Matching frozen bedkeep DebugCPU87/runtime_r6 source closure required')
  objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==86,'Exactly86 same-build non-main CPU objects required')
  cp=L/'upl_noslip_cpu_component_r1_compile.call.json';lp=L/'upl_noslip_cpu_component_r1_link.call.json';c,l=read(cp),read(lp);need(c['exit_code']==l['exit_code']==0 and c['owned_call_exited'] and l['owned_call_exited'],'Closed DebugCPU compiler/link flag recipe required')
  before=[stat(CPU),stat(GPU),bind(b['source_capture']),bind(b['source_archive']),*[bind(e) for e in objects],stat(cp),stat(lp),stat(CPP),stat(NOTE),stat(__file__),stat(old.__file__)]
  oldroot=T/'outputs/upl_noslip_cpu_component_r1';oldcpp=next(x for x in c['arguments'] if x.lower().endswith('.cpp'));frozen=HELPER/'frozen'
  ca=[str(CPP) if x==oldcpp else x.replace(str(oldroot),str(HELPER)) for x in c['arguments'] if not x.startswith('/I')];ca.insert(0,'/I'+str(frozen/'src/source'))
  la=[x.replace(str(oldroot),str(HELPER)).replace('upl_noslip_cpu_component_r1.exe','component.exe') for x in l['arguments'] if not x.lower().endswith('.obj')]+[str(HELPER/'helper.obj'),*[e['path'] for e in objects]]
  need(all(x in ca for x in ('/Od','/MTd','/fp:precise','/std:c++17','/openmp')) and '/D_WITHGPU' not in ca and sum(x.lower().endswith('.obj') for x in la)==87,'Actual CPU Debug flags/object closure differ')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC environment setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required');env.pop('CL',None);env.pop('_CL_',None)
  HELPER.mkdir();headers=[]
  with zipfile.ZipFile(b['source_archive']['path']) as z:
   for name in z.namelist():
    q=PurePosixPath(name);need(not q.is_absolute() and '..' not in q.parts,'Invalid archive member')
    if len(q.parts)>=3 and q.parts[:2]==('src','source') and q.suffix.lower() in ('.h','.hpp','.cuh'):
     dest=frozen/Path(*q.parts);dest.parent.mkdir(parents=True,exist_ok=True);data=z.read(name)
     with dest.open('xb') as f:f.write(data)
     need(dest.read_bytes()==data,'Frozen header extraction differs');headers.append(stat(dest))
  need(all((frozen/'src/source'/x).is_file() for x in ('JSph.h','JSphCpu.h','JSphCpuSingle.h','FunSoilMaterial.h','JGravityPreloadState.h')),'Frozen class/material/PRE headers absent')
  calls.append(invoke(TAG+'.compile',[c['program'],*ca],S,env));calls.append(invoke(TAG+'.link',[l['program'],*la],S,env));deps=read(HELPER/'compile.dependencies.json');includes=[Path(q).resolve() for q in deps['Data']['Includes']]
  need(all((frozen/'src/source'/q).resolve() in includes for q in ('JSph.h','JSphCpu.h','JSphCpuSingle.h')),'Compiler did not consume frozen class headers')
  runtime=[];origin=Path(b['program']['path']).parent
  for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
   e=stat(origin/leaf);before.append(e);shutil.copy2(e['path'],HELPER/leaf);dest=stat(HELPER/leaf);need((e['bytes'],e['mtime_ns'])==(dest['bytes'],dest['mtime_ns']),'Matching Debug runtime copy differs');runtime.append(dest)
  need(all(stat(e['path'])==e for e in before+headers),'Consumed build input changed')
  save(check,dict(stage=TAG+'.build',passed=True,program=stat(PROGRAM),source=stat(CPP),source_build=stat(CPU),runtime_r6_GPU_build=stat(GPU),source_capture=b['source_capture'],source_archive=b['source_archive'],project_non_main_objects=86,actual_link_objects=87,frozen_headers=headers,source_dependencies=stat(HELPER/'compile.dependencies.json'),runtime=runtime,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_builds=0,component_invocations=0,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=before,solver_builds=0,SHA_scans=0))
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root has read this helper build');build()
