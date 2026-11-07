"""One standalone production adapter compile/link and one memcheck; author-only until root review."""
import argparse,json,os,subprocess,traceback
from pathlib import Path
import upl_material_unified_gpu_build_run_r1 as owner
T=Path(__file__).resolve().parents[1];R=T.parents[3];L=T/'logs';TAG='upl_material_adapters_r1'

def main():
    a=argparse.ArgumentParser();a.add_argument('--execution-authorized',action='store_true');args=a.parse_args();owner.need(args.execution_authorized,'Root-reviewed execution flag required')
    owner.TAG=TAG;owner.STAGE=T/'outputs'/TAG;owner.CHECK=L/(TAG+'.check.json');owner.CALLS=[]
    inputs=[];summary=dict(stage=TAG,passed=False,SHA_scans=0,engine_objects=0,spatial_solver_invocations=0,production_changed=False,physical_acceptance=False)
    try:
        owner.need(not owner.STAGE.exists() and not owner.CHECK.exists(),'Fresh adapter outputs required; no retries')
        receipts=[T/'logs/upl_material_release_DebugCPU_r3.build.json',T/'logs/upl_material_release_Debug_r3.build.json'];builds=[owner.read(p) for p in receipts]
        for b in builds:owner.need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Closed production r3 CPU/GPU builds required')
        owner.need(builds[0]['source_capture']==builds[1]['source_capture'],'CPU/GPU r3 source capture differs')
        capture=builds[0]['source_capture'];owner.need(owner.stat(capture['path'])==capture,'Build source receipt changed');source=owner.read(capture['path'])
        prod=[R/'src/source/FunSoilMaterial.h',R/'src/source/DualSphDef.h',R/'src/source/TypesDef.h']
        for p in prod:
            expected=next(e for e in source['files'] if Path(e['path']).resolve()==p.resolve());owner.need(owner.stat(p)==expected,'Current adapter header differs from completed r3 source')
        src=T/'support/upl_material_adapters_r1.cu';frozen=T/'support/upl_material_unified_candidate_r1.h';cpu_ref=T/'logs/upl_material_unified_r1.check.json';ref=owner.read(cpu_ref)
        owner.need(ref['passed'] and ref['completion']['point_count']==109,'Closed frozen U CPU reference required');expected=next(e for e in ref['consumed'] if Path(e['path']).resolve()==frozen.resolve());owner.need(owner.stat(frozen)==expected,'Frozen U candidate changed')
        inputs=[owner.stat(p) for p in [Path(__file__),Path(owner.__file__),src,frozen,cpu_ref,*prod,*receipts,Path(capture['path'])]]
        for b in builds:owner.need(owner.stat(b['program']['path'])==b['program'],'Production r3 build program binding changed')
        owner.STAGE.mkdir();temp=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_material_adapters_r1';owner.need(not temp.exists(),'Fresh compiler temp required');temp.mkdir()
        cuda=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');nvcc=cuda/'bin/nvcc.exe';san=cuda/'compute-sanitizer/compute-sanitizer.exe'
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',capture_output=True);owner.need(setup.returncode==0,'MSVC environment setup failed')
        env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));owner.need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required')
        compiler=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64';exe=owner.STAGE/'upl_material_adapters_r1.exe';result=owner.STAGE/'result'
        argv=[str(nvcc),'-gencode=arch=compute_86,code=[sm_86,compute_86]','--use-local-env','-ccbin',str(compiler),'-x','cu','-std=c++17','-G','-g','-use_fast_math','--machine','64','-cudart','static','-maxrregcount=0','-D_WITHGPU','-DWIN32','-D_CONSOLE','-D_MBCS','-I'+str(R/'src/source'),'-I'+str(T/'support'),'-Xcompiler','/EHsc,/W3,/Od,/MTd,/Zi,/RTC1,/wd4267,/Fd'+str(temp/'compile.pdb'),'-Xlinker','/DEBUG,/PDB:'+str(temp/'link.pdb'),'-o',str(exe),str(src)]
        owner.invoke('nvcc_compile_link',argv,env)
        owner.save(L/(TAG+'.build.json'),dict(passed=True,program=owner.stat(exe),compiler_argv=argv,consumed=inputs,production_build_prerequisites=[owner.stat(p) for p in receipts],calls=owner.CALLS.copy(),engine_objects=0,cudart='static',MSVC_CRT='MTd static',SHA_scans=0))
        sanlog=L/(TAG+'.memcheck.sanitizer.log');owner.need(not sanlog.exists(),'Sanitizer output already exists')
        owner.invoke('memcheck',[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),str(exe),'--out',str(result)],env,exe)
        text=sanlog.read_text();owner.need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Missing zero-error/leak sanitizer closure')
        done=owner.read(result/'completion.json');owner.need(done['passed'] and done['points']==28 and done['kernel_launches']==1 and done['failed_adapter_sentinel_checks_per_backend']==2 and done['input_defined_scalar_checks']==30 and done['output_tail_defined_member_checks']==2,'Adapter coverage incomplete')
        owner.need(all(owner.stat(e['path'])==e for e in inputs),'Consumed header/probe/receipt changed')
        summary.update(passed=True,completion=done,consumed=inputs,consumed_stats_unchanged=True,calls=owner.CALLS,memcheck_zero_errors_and_leaks=True,memcheck=owner.stat(sanlog),outputs=[owner.stat(p) for p in sorted(result.iterdir())])
    except Exception as e:summary.update(first_failure=str(e),traceback=traceback.format_exc(),calls=owner.CALLS,consumed=inputs)
    owner.save(owner.CHECK,summary);print(json.dumps(summary,indent=2));return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
