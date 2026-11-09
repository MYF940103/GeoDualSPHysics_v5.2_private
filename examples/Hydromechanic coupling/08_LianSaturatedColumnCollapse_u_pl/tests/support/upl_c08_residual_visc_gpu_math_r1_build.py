"""Author-only standalone Debug CUDA DLL build; no component/solver execution."""
import argparse,os,re,subprocess
from pathlib import Path
import mdbc_partition_components_r3 as b
from upl_c08_as_effective_gpu_r2_build import windows_args
T,L=b.T,b.L;TAG='upl_c08_residual_visc_gpu_math_r1';OUT=T/'outputs'/(TAG+'_build')
CU=T/'support'/(TAG+'.cu');DEF=T/'support'/(TAG+'.def');NOTE=T/'notes/upl_c08_residual_visc_gpu_math_harness_r1.md'
DLL=OUT/'C08ResidualViscGpuMath_r1.dll';CHECK=L/(TAG+'.build.json')
need,read,stat,bind,save,invoke=b.need,b.read,b.stat,b.bind,b.save,b.invoke

def build():
    need(not OUT.exists() and not CHECK.exists(),'Existing complete/partial build protected');before=[];calls=[]
    try:
        bp=L/'upl_c08_bedkeep_Debug_r1.build.json';old=read(bp)
        need(old['passed'] and old['configuration']=='Debug' and old['actual_typed_exit_code']==old['actual_Win32_exit']==0 and old['source_stats_unchanged'] and len(old['project_objects'])==113,'Closed authoritative bedkeep Debug GPU build required')
        actual=read(bind(old['actual_call'])['path']);log=Path(bind(actual['log'])['path']);obj=next(Path(e['path']) for e in old['project_objects'] if Path(e['path']).name.lower()=='jsphgpu_ker.cu.obj');tlog=obj.parent/'DualSPHysics.tlog/link.command.1.tlog'
        lines=[v.split(b'>',1)[1].strip().decode('ascii') for v in log.read_bytes().splitlines() if b'nvcc.exe' in v.lower() and b'jsphgpu_ker.cu' in v.lower()]
        need(len(lines)==1,'Exactly one closed NVCC recipe required');ca=windows_args(lines[0]);nvcc=Path(ca.pop(0));need('CUDA/v11.7' in str(nvcc).replace('\\','/'),'Closed CUDA11.7 compiler required')
        host=Path(ca[ca.index('-ccbin')+1]);link=host/'link.exe';need('/14.36.32532/' in str(host).replace('\\','/'),'MSVC14.36 host required')
        need(all(v in ca for v in ('-G','-g','--compile','-cudart','static','-use_fast_math','--machine','64')) and any('compute_86' in v and 'sm_86' in v for v in ca) and any('/Od' in v and '/MTd' in v for v in ca),'Actual Debug/sm86/static CRT/numeric flags differ')
        need(not any('C08_' in v or v in ('-dc','--device-link') or 'rdc=true' in v for v in ca),'Standalone TU must have no observer/candidate macros or RDC')
        recipe=ca.copy();need(sum(Path(v).name.lower()=='jsphgpu_ker.cu' for v in ca)==1 and ca.count('-o')==ca.count('--keep-dir')==1,'Closed NVCC source/output anchors differ')
        ca=[str(CU) if Path(v).name.lower()=='jsphgpu_ker.cu' else v for v in ca];ca[ca.index('-o')+1]=str(OUT/'math.obj');ca[ca.index('--keep-dir')+1]=str(OUT)
        changes=0
        for i,v in enumerate(ca):
            if i and ca[i-1]=='-Xcompiler':ca[i],count=re.subn(r'(?i)(?<!\S)/Fd[^\s]+','/Fdhost.pdb',v);changes+=count
        need(changes==1,'Exactly one host PDB output must be rehomed')
        need(not any(str(obj.parent).lower().replace('\\','/') in v.lower().replace('\\','/') for v in ca),'Original project intermediate directory remains in candidate outputs')
        raw=tlog.read_text(encoding='utf-16').splitlines();need(sum(v.startswith('^') for v in raw)==1,'Closed link tlog block differs');la=windows_args(' '.join(v for v in raw if v and not v.startswith('^')))
        windowslibs=[v for v in la if not v.startswith(('/','-')) and v.lower().endswith('.lib') and not Path(v).name.lower().startswith(('dsph','libj','libdsph','cudart','cudadevrt'))]
        need('KERNEL32.LIB' in [v.upper() for v in windowslibs],'Original system-library closure missing')
        cuda=nvcc.parent.parent;cuda_libs=[cuda/'lib/x64/cudart_static.lib',cuda/'lib/x64/cudadevrt.lib']
        # DLL-specific adaptation only: no solver objects/libraries, console entry
        # or project layout. Numeric compilation flags remain the closed recipe.
        linked=['/NOLOGO','/DLL','/MACHINE:X64','/DEBUG','/INCREMENTAL:NO','/DYNAMICBASE','/NXCOMPAT','/OUT:'+str(DLL),'/PDB:'+str(OUT/'math.pdb'),'/IMPLIB:'+str(OUT/'math.lib'),'/DEF:'+str(DEF),str(OUT/'math.obj'),*[str(p) for p in cuda_libs],*windowslibs]
        before=[stat(p) for p in (Path(__file__),Path(b.__file__),T/'support/upl_c08_as_effective_gpu_r2_build.py',CU,DEF,NOTE,bp,log,tlog,nvcc,link,*cuda_libs)]+[bind(old[k]) for k in ('actual_call','source_capture','source_archive')]
        OUT.mkdir();setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC environment setup failed');env=dict(os.environ);env.update(v.split('=',1) for v in setup.stdout.decode('mbcs').splitlines() if '=' in v and not v.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Actual MSVC14.36 environment differs')
        for key in list(env):
            if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
        calls.append(invoke(TAG+'.compile',[str(nvcc),*ca],OUT,env));calls.append(invoke(TAG+'.link',[str(link),*linked],OUT,env))
        need(all(stat(e['path'])==e for e in before),'Closed inputs changed during DLL build')
        save(CHECK,dict(stage=TAG+'.build',passed=True,configuration='Debug',program=stat(DLL),source=stat(CU),module_definition=stat(DEF),source_build=stat(bp),compiler_recipe_log=stat(log),link_recipe_tlog=stat(tlog),original_NVCC_arguments=recipe,actual_NVCC_arguments=ca,actual_link_arguments=linked,compiler=stat(nvcc),host_linker=stat(link),actual_NVCC_calls=1,link_invocations=1,actual_link_objects=1,physical_objects=0,solver_libraries=0,CUDA_runtime='static',MSVC_CRT='MTd',CUDA_debug_G=True,fast_math=True,standalone_DLL_adaptation=True,exported_entry='C08ResidualViscGpuMathR1',calls=calls,consumed=before,consumed_stats_unchanged=True,component_invocations=0,solver_invocations=0,native_decodes=0,production_changed=False,physical_acceptance=False,SHA_scans=0))
    except Exception as error:
        if not CHECK.exists():save(CHECK,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,SHA_scans=0))
        raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reviews DLL flags and authorizes one build');build()
