"""Build one isolated candidate with the authoritative VS solution; no solver invocation."""
import argparse, os, shutil, sys
from pathlib import Path
import mdbc_partition_components_r3 as e

T=Path(__file__).resolve().parents[1]; R=T.parents[3]; L=T/'logs'
SPECS={'ReleaseCPU':('DualSPHysics5ReCpu_vs2022.sln','DualSPHysics5.2CPU_win64.exe'),
       'Debug':('DualSPHysics5Re.sln','DualSPHysics5.2_win64_debug.exe'),
       'Release':('DualSPHysics5Re.sln','DualSPHysics5.2_GEO_win64.exe')}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('configuration',choices=SPECS)
    p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    e.need(a.execution_authorized,'Explicit build required')
    tag='c08_preload_schema2_'+a.configuration+'_r1';out=T/'outputs'/tag;check=L/(tag+'.build.json')
    intermediate=Path(os.environ['TEMP'])/'c08_schema2_build_r1'/a.configuration/'int'
    e.need(not out.exists() and not intermediate.exists() and not check.exists(),'Existing candidate protected')
    capture=T/'outputs/c08_preload_schema2_source_r1/full_source.json';s=e.read(capture)
    before=[e.stat(__file__),e.stat(capture),e.bind(s['archive'])]+[e.bind(q) for q in s['source_files']]
    runtime=T.parent/'support/runtime_r6';leaves=('GenCase_win64.exe','PartVTK_win64.exe','DsphConfig.xml',
        'ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')
    before += [e.stat(runtime/q) for q in leaves]
    out.mkdir();intermediate.mkdir(parents=True);call=None
    try:
        solution,leaf=SPECS[a.configuration]
        argv=['D:/Program Files/VS2022/MSBuild/Current/Bin/MSBuild.exe',str(R/'src/VS'/solution),
            '/m','/t:Build','/p:Configuration='+a.configuration,'/p:Platform=x64',
            '/p:VCToolsVersion=14.36.32532','/p:OutDir='+out.as_posix()+'/',
            '/p:IntDir='+intermediate.as_posix()+'/','/v:minimal']
        call=e.invoke(tag,argv,R/'src')
        copied=[]
        for name in leaves:
            shutil.copy2(runtime/name,out/name);src=e.stat(runtime/name);dest=e.stat(out/name)
            e.need((src['bytes'],src['mtime_ns'])==(dest['bytes'],dest['mtime_ns']),'Runtime copy differs')
            copied.append(dict(source=src,destination=dest))
        e.need(all(e.stat(q['path'])==q for q in before),'Frozen source/runtime changed during build')
        e.save(check,dict(stage=tag,passed=True,configuration=a.configuration,program=e.stat(out/leaf),
            actual_call=call,source_capture=e.stat(capture),source_archive=s['archive'],
            runtime=copied,intermediate=str(intermediate),consumed=before,consumed_stats_unchanged=True,
            solver_invocations=0,physical_acceptance=False,SHA_scans=0))
        print('ISOLATED_BUILD_PASS',a.configuration,flush=True)
    except Exception as error:
        e.save(check,dict(stage=tag,passed=False,first_failure=str(error),actual_call=call,
            source_capture=e.stat(capture),consumed=before,solver_invocations=0))
        raise

if __name__=='__main__':main()
