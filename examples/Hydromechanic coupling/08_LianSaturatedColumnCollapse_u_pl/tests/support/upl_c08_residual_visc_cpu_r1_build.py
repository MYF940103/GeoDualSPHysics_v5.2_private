"""Two CL calls and one link: private CPU residual-viscosity numerical-damping candidate."""
import argparse,ctypes,os,shutil,subprocess,zipfile
from pathlib import Path
import upl_c08_pair_force_cpu_r1_build as old
T,L,S=old.T,old.L,old.S;CPU,GPU=old.CPU,old.GPU;TAG='upl_c08_residual_visc_cpu_r1';CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md');CAP=T/'outputs'/(TAG+'_source');HELPER=T/'outputs'/(TAG+'_helper');PROGRAM=HELPER/'component.exe'
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke
MACRO='C08_RESIDUAL_VISCOSITY_CANDIDATE'
DECLARE=b'#ifdef C08_RESIDUAL_VISCOSITY_CANDIDATE\r\nextern void C08ResidualViscosityApply(JSphCpuSingle*);\r\n#endif\r\n\r\n'
APPLY=b'#ifdef C08_RESIDUAL_VISCOSITY_CANDIDATE\r\n  C08ResidualViscosityApply(this);\r\n#endif\r\n'
MEMBER='src/source/JSphCpuSingle.cpp'

def windows_args(line):
 shell=ctypes.WinDLL('shell32',use_last_error=True);shell.CommandLineToArgvW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(ctypes.c_wchar_p);count=ctypes.c_int();p=shell.CommandLineToArgvW('cl.exe '+line,ctypes.byref(count));need(bool(p),'Cannot parse actual Windows project CL command')
 try:return [p[i] for i in range(1,count.value)]
 finally:free=ctypes.WinDLL('kernel32').LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(ctypes.cast(p,ctypes.c_void_p))

def build():
 check=L/(TAG+'.build.json');need(not HELPER.exists() and not check.exists(),'Existing complete/partial residual-viscosity candidate build protected');before=[];calls=[]
 try:
  prior=L/'upl_c08_pair_force_cpu_r1.build.json';cpu=L/'upl_c08_bedkeep_DebugCPU_r1.build.json';driver=read(prior);base=read(cpu);capture=read(CAP/'source.json')
  need(driver['passed'] and driver['consumed_stats_unchanged'] and driver['project_non_main_objects']==86 and driver['actual_link_objects']==87 and base['passed'] and base['actual_typed_exit_code']==base['actual_Win32_exit']==0 and len(base['project_objects'])==87 and driver['source_capture']==base['source_capture'] and driver['source_archive']==base['source_archive'],'Closed same-capture DebugCPU/driver closure required')
  need(capture['author_only'] and capture['numerical_damping_candidate'] and capture['macro']==MACRO and capture['callback_blocks_added']==2 and capture['macro_enabled_can_modify_acceleration_and_darcy'] and not capture['original_physical_body_edited'] and not capture['class_layout_changed'] and capture['baseline_capture']==base['source_capture'] and capture['baseline_archive']==base['source_archive'] and capture['changed_archive_members']==[MEMBER] and capture['all_other_archive_member_bytes_exact'] and capture['reverse_reconstruction_original_bytes_exact'] and capture['macro_disabled_original_bytes_exact'],'Read-reviewed numerical-damping private source/capture differs')
  objects=[e for e in base['project_objects'] if Path(e['path']).name.lower()!='main.obj'];original=next(e for e in objects if Path(e['path']).name.lower()=='jsphcpusingle.obj');retained=[e for e in objects if e!=original];need(len(objects)==86 and len(retained)==85,'Exactly one physical object replacement required')
  oldroot=Path(driver['program']['path']).parent;cp=L/'upl_c08_pair_force_cpu_r1.compile.call.json';lp=L/'upl_c08_pair_force_cpu_r1.link.call.json';c,l=read(cp),read(lp);need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==l['actual_Popen_wait_exit']==l['actual_Win32_exit']==0 and c['ownership_failure'] is l['ownership_failure'] is None,'Closed matching helper compiler/link recipe required')
  headers=driver['frozen_headers'];frozen=oldroot/'frozen/src/source';tlogs=list(Path(original['path']).parent.glob('*.tlog/CL.command.1.tlog'));need(len(tlogs)==1,'One actual project CL tlog required');tlog=tlogs[0];lines=tlog.read_text(encoding='utf-16').splitlines();at=[i for i,v in enumerate(lines) if v.startswith('^') and Path(v[1:]).name.lower()=='jsphcpusingle.cpp'];need(len(at)==1,'One actual JSphCpuSingle project CL command required');physical=windows_args(lines[at[0]+1]);need(sum(x.lower().endswith('jsphcpusingle.cpp') for x in physical)==1 and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in physical),'Unexpected PCH/LTCG or source in project CL flags')
  before=[stat(prior),stat(cpu),bind(driver['runtime_r6_GPU_build']),stat(cp),stat(lp),stat(tlog),stat(CAP/'source.json'),bind(capture['private_cpu_source']),bind(capture['helper_source']),bind(capture['diff']),bind(capture['archive']),bind(base['source_capture']),bind(base['source_archive']),*[bind(e) for e in objects],*[bind(e) for e in headers],stat(CPP),stat(NOTE),stat(__file__),stat(old.__file__),stat(old.old.__file__)]
  with zipfile.ZipFile(base['source_archive']['path']) as original_archive,zipfile.ZipFile(capture['archive']['path']) as private_archive:
   need(original_archive.namelist()==private_archive.namelist(),'Private archive members differ');patched=private_archive.read(MEMBER);baseline=original_archive.read(MEMBER)
   need(patched==Path(capture['private_cpu_source']['path']).read_bytes() and patched.count(DECLARE)==patched.count(APPLY)==1 and patched.replace(DECLARE,b'',1).replace(APPLY,b'',1)==baseline,'Exactly two reversible candidate blocks required')
   need(DECLARE+b'using namespace std;' in patched and APPLY+b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateCpu();' in patched,'Candidate declaration/call placement differs')
   need(all(original_archive.read(n)==private_archive.read(n) for n in original_archive.namelist() if n!=MEMBER),'Other private archive member bytes differ')
  freshobj=HELPER/'JSphCpuSingle_residual_visc.obj';pa=[str(CAP/'JSphCpuSingle.cpp') if x.lower().endswith('jsphcpusingle.cpp') else '/Fo'+str(freshobj) if x.lower().startswith('/fo') else '/Fd'+str(HELPER/'physical.pdb') if x.lower().startswith('/fd') else x for x in physical];pa=['/D'+MACRO,'/I'+str(frozen),*pa];pa+=['/sourceDependencies',str(HELPER/'physical.dependencies.json')]
  ca=[str(CPP) if x.lower().endswith('.cpp') else x if x.startswith('/I') else x.replace(str(oldroot),str(HELPER)) for x in c['arguments']];la=[str(freshobj) if x==original['path'] else x.replace(str(oldroot),str(HELPER)) for x in l['arguments']]
  need(sum(x.lower().endswith('.obj') for x in la)==87 and la.count(str(freshobj))==1 and original['path'] not in la and all(e['path'] in la for e in retained) and str(HELPER/'helper.obj') in la,'Actual87-link inputs must be85 retained+one patched+one new helper')
  need(all(x in pa for x in ('/Od','/MTd','/fp:precise','/openmp','/RTC1','/Zi')) and all(x in ca for x in ('/Od','/MTd','/fp:precise','/std:c++17')) and '/D_WITHGPU' not in pa and '/D_WITHGPU' not in ca and len(driver['runtime'])==4,'Matching CPU physical/driver Debug flags and runtime4 required')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC environment setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required');env.pop('CL',None);env.pop('_CL_',None)
  HELPER.mkdir();calls.append(invoke(TAG+'.physical_compile',[c['program'],*pa],S,env));calls.append(invoke(TAG+'.helper_compile',[c['program'],*ca],S,env));calls.append(invoke(TAG+'.link',[l['program'],*la],S,env))
  dependencies=[]
  for leaf in ('physical.dependencies.json','compile.dependencies.json'):
   q=HELPER/leaf;deps=read(q);includes=[Path(p).resolve() for p in deps['Data']['Includes']];need(all((frozen/n).resolve() in includes for n in ('JSphCpuSingle.h','JSphCpu.h','JSph.h')),'Compiler used another class-header ABI');dependencies.append(stat(q))
  runtime=[]
  for e in driver['runtime']:before.append(bind(e));dest=HELPER/Path(e['path']).name;shutil.copy2(e['path'],dest);copy=stat(dest);need((copy['bytes'],copy['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Debug runtime copy differs');runtime.append(copy)
  need(all(stat(e['path'])==e for e in before),'Original object/source/header/runtime changed')
  save(check,dict(stage=TAG+'.build',passed=True,numerical_damping_candidate=True,candidate_macro=MACRO,program=stat(PROGRAM),source=stat(CPP),private_cpu_source=stat(CAP/'JSphCpuSingle.cpp'),private_source_capture=stat(CAP/'source.json'),private_source_archive=capture['archive'],source_capture=base['source_capture'],source_archive=base['source_archive'],runtime_r6_GPU_build=driver['runtime_r6_GPU_build'],source_build=stat(cpu),baseline_driver_build=stat(prior),project_non_main_objects=86,retained_physical_objects=85,physical_objects_recompiled=1,helper_objects_compiled=1,actual_link_objects=87,original_physical_object=original,replacement_physical_object=stat(freshobj),physical_project_tlog=stat(tlog),source_dependencies=dependencies,frozen_headers=headers,runtime=runtime,calls=calls,consumed=before,consumed_stats_unchanged=True,compile_invocations=2,link_invocations=1,solver_builds=0,component_invocations=0,production_source_changed=False,physical_acceptance=False,SHA_scans=0))
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=before,solver_builds=0,SHA_scans=0))
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reads the private candidate source/flags/link closure');build()
