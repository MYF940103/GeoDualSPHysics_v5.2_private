"""Build/run the reviewed shared scalar contact component once, without a solver."""
import argparse,os,subprocess
from pathlib import Path
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];S=T.parents[3]/'src';TAG='upl_c08_contact_component_r1'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Reviewed execution required')
    out=T/'outputs'/(TAG+'_build');result=T/'outputs'/TAG
    receipt=T/'logs'/(TAG+'.check.json')
    e.need(not out.exists() and not result.exists() and not receipt.exists(),'Existing component protected')
    inputs=[e.stat(p) for p in (Path(__file__),T/'support'/(TAG+'.cpp'),S/'source/FunFixedPlaneContact.h',T/'notes'/(TAG+'.md'))]
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    e.need(setup.returncode==0,'MSVC environment failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
    e.need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC required');out.mkdir();exe=out/'contact.exe'
    compilecall=e.invoke(TAG+'.build',['cl.exe','/nologo','/std:c++17','/EHsc','/W4','/Od','/MDd','/I'+str(S/'source'),str(T/'support'/(TAG+'.cpp')),'/Fo'+str(out/'contact.obj'),'/Fe'+str(exe)],S,env)
    runcall=e.invoke(TAG+'.host',[str(exe),'--out',str(result)],S,env)
    done=e.read(result/'completion.json');e.need(done['passed'] and done['host_points']==17 and done['half_stage_sign_flip_toys']==2,'Component coverage failed')
    e.need(all(e.stat(x['path'])==x for x in inputs),'Reviewed source changed')
    e.save(receipt,dict(stage=TAG,passed=True,compile_call=compilecall,run_call=runcall,consumed=inputs,program=e.stat(exe),completion=e.stat(result/'completion.json'),GPU_execution_proven=False,physical_acceptance=False,SHA_scans=0))
    print('COMPONENT_PASSED',receipt,flush=True)
if __name__=='__main__':main()
