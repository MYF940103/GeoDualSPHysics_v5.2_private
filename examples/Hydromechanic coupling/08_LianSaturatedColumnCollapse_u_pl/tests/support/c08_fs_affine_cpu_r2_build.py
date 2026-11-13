"""Link the successful r1 CPU compilation's actual default object; no recompile or execution."""
import os,shutil,subprocess
from pathlib import Path
import c08_fs_affine_cpu_r1_build as previous

T,L,S=previous.T,previous.L,previous.S
old=previous.matrix
TAG='c08_fs_affine_cpu_r2'
OUT=T/'outputs'/(TAG+'_build')

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    old.need(a.execution_authorized and not OUT.exists() and not (L/(TAG+'.build.json')).exists(),'Fresh reviewed link only')
    failed=old.read(L/'c08_fs_affine_cpu_r1.build.json');compile=old.read(L/'c08_fs_affine_cpu_r1.compile.call.json');link=old.read(L/'c08_fs_affine_cpu_r1.link.call.json')
    old.need(not failed['passed'] and compile['actual_Popen_wait_exit']==compile['actual_Win32_exit']==0 and compile['ownership_failure'] is None,'Successful actual r1 compilation required')
    old.need(link['actual_Popen_wait_exit']==link['actual_Win32_exit']==1104 and link['ownership_failure'] is None,'Preserved missing-output-object link failure required')
    source=T/'support/c08_fs_affine_cpu_r1.cpp';obj=T/'outputs/c08_fs_affine_cpu_r1_build/c08_fs_affine_cpu_r1.obj'
    old.need(str(source) in compile['arguments'] and '/MTd' in compile['arguments'] and '/Od' in compile['arguments'],'Actual unchanged Debug fixture compilation required')
    before=[old.bind(q) for q in failed['consumed']]+[old.stat(q) for q in (obj,Path(__file__),T/'notes/c08_fs_affine_cpu_r2_build.md',L/'c08_fs_affine_cpu_r1.build.json',L/'c08_fs_affine_cpu_r1.compile.call.json',L/'c08_fs_affine_cpu_r1.link.call.json')]
    args=link['arguments'];missing=T/'outputs/c08_fs_affine_cpu_r1_build/fixture.obj';exe=OUT/'C08FsAffineCpuR1_win64.exe'
    old.need(not missing.exists() and sum(Path(q)==missing for q in args)==1 and obj.is_file(),'Actual default object and missing ignored-Fo output required')
    args=[str(obj) if Path(q)==missing else q.replace(str(missing.parent),str(OUT)) for q in args]
    args=[('/OUT:'+str(exe)) if q.lower().startswith('/out:') else q for q in args]
    objects=[Path(q) for q in args if q.lower().endswith('.obj')]
    old.need(len(objects)==87 and sum(q==obj for q in objects)==1 and all(q.exists() for q in objects),'86 public objects and one actual fixture object required')
    baseline=old.read(previous.BASE)
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    old.need(setup.returncode==0,'MSVC setup failed')
    env={k.upper():v for k,v in os.environ.items()};env.update(q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('='));env={k.upper():v for k,v in env.items()}
    old.need(env['VCTOOLSVERSION']=='14.36.32532','Same MSVC required')
    library_tlog=next(Path(q['path']) for q in failed['consumed'] if Path(q['path']).name=='link.read.1.tlog')
    libraries=[Path(q.strip('"')) for q in library_tlog.read_text(encoding='utf-16').splitlines() if not q.startswith('^') and q.lower().endswith('.lib')]
    env['LIB']=';'.join(dict.fromkeys(str(q.parent) for q in libraries));old.verify(before);OUT.mkdir()
    call=old.invoke(TAG+'.link',[link['program'],*args],Path(link['cwd']),env)
    runtime=[]
    for entry in baseline['runtime']:
        old.bind(entry);dest=OUT/Path(entry['path']).name;shutil.copy2(entry['path'],dest);old.need(dest.read_bytes()==Path(entry['path']).read_bytes(),'Runtime copy differs');runtime.append(old.stat(dest))
    old.verify(before)
    old.save(L/(TAG+'.build.json'),dict(stage=TAG+'.build',passed=True,program=old.stat(exe),source=old.stat(source),source_build=old.stat(previous.BASE),source_capture=baseline['source_capture'],source_archive=baseline['source_archive'],adopted_compile=old.stat(L/'c08_fs_affine_cpu_r1.compile.call.json'),actual_fixture_object=old.stat(obj),actual_link_objects=87,retained_public_objects=86,calls=[call],runtime=runtime,consumed=before,consumed_stats_unchanged=True,compile_invocations=0,fixture_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))

if __name__=='__main__':main()
