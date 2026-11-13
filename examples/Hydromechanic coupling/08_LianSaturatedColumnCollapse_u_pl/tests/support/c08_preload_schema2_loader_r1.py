"""Explicit build OR run of synthetic loader tests; never invokes a solver or real PRE."""
import argparse, csv, os, subprocess
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as e

T=Path(__file__).resolve().parents[1];L=T/'logs';S=T.parents[3]/'src'
TAG='c08_preload_schema2_loader_r1';BUILD=T/'outputs'/(TAG+'_build');OUT=T/'outputs'/(TAG+'_synthetic')
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke
BUILD_CHECK=L/(TAG+'.build.json');CHECK=L/(TAG+'.check.json')
LEAVES=('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')

def build():
    need(not BUILD.exists() and not BUILD_CHECK.exists(),'Existing or partial synthetic test build protected')
    before=[];calls=[]
    try:
        source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');loader=S/'source/JGravityPreloadState.h'
        bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp)
        need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Sealed Release utility build required')
        objects=[q for q in b['project_objects'] if Path(q['path']).stem in LEAVES];need(len(objects)==6 and {Path(q['path']).stem for q in objects}==set(LEAVES),'Exactly six sealed utility objects required')
        cap=read(bind(b['source_capture'])['path']);archive=Path(bind(cap['archive'])['path'])
        text=loader.read_text(encoding='utf-8-sig');need('unsigned Schema=0' in text and 'const std::string& contract2=std::string()' in text and 'Same-material plastic PRE requires unified material law2.' in text,'Final schema2 loader API required; do not use old frozen header')
        before=[stat(q) for q in (Path(__file__),source,note,loader,Path(e.__file__),bp)]+[bind(b['source_capture']),stat(archive),*[bind(q) for q in objects]]
        BUILD.mkdir();headers=BUILD/'headers';headers.mkdir()
        with ZipFile(archive) as z:
            for item in z.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
                    dest=headers/Path(item.filename).name;need(not dest.exists(),'Duplicate utility header leaf');dest.write_bytes(z.read(item))
            for leaf in ('JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h'):
                current=S/'source'/leaf;need(current.read_bytes()==z.read('src/source/'+leaf),'Utility ABI header changed: '+leaf);before.append(stat(current))
        (headers/'JGravityPreloadState.h').write_bytes(loader.read_bytes());before.append(stat(headers/'JGravityPreloadState.h'))
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'MSVC environment setup failed');env=dict(os.environ);env.update(q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Use the sealed MSVC14.36 toolchain')
        cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=BUILD/'test.obj';exe=BUILD/'C08PreloadSchema2Loader_win64.exe'
        ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(headers),'/Fo'+str(obj),str(source)]
        la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]]
        calls.append(invoke(TAG+'.compile',ca,BUILD,env));calls.append(invoke(TAG+'.link',la,BUILD,env));need(all(stat(q['path'])==q for q in before),'Consumed source/objects changed')
        save(BUILD_CHECK,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),loader=stat(loader),compiled_loader=stat(headers/'JGravityPreloadState.h'),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),objects=objects,actual_link_objects=7,JSph_objects_linked=False,calls=calls,consumed=before,consumed_stats_unchanged=True,synthetic_only=True,solver_invocations=0))
    except Exception as error:
        if not BUILD_CHECK.exists():save(BUILD_CHECK,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,synthetic_only=True,solver_invocations=0))
        raise

def run():
    need(not OUT.exists() and not CHECK.exists() and not (L/(TAG+'.test.call.json')).exists(),'Existing or partial synthetic test result protected')
    b=read(BUILD_CHECK);need(b['passed'] and b['synthetic_only'] and not b['JSph_objects_linked'],'Passed synthetic-only helper build required')
    before=[stat(Path(__file__)),stat(BUILD_CHECK),bind(b['program']),bind(b['source']),bind(b['compiled_loader'])];call=None
    try:
        call=invoke(TAG+'.test',[b['program']['path'],str(OUT)],T/'outputs');completion=OUT/'completion.json';done=read(completion)
        need(done['passed'] and done['tests']==done['passed_tests']==24 and done['accepted_cases']==5 and done['rejected_cases']==19 and done['synthetic_only'] and not done['physical_acceptance'] and done['solver_calls']==done['physical_updates']==0,'All24 synthetic loader cases must pass')
        with (OUT/'tests.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        need(len(rows)==24 and len({q['case'] for q in rows})==24 and all(q['passed']=='1' for q in rows),'Unique24 test CSV results required')
        need(all(q['carry_bits_checked']=='1' for q in rows if q['expected_accept']=='1') and all(q['accepted']=='0' and q['error'] for q in rows if q['expected_accept']=='0'),'Accepted carry bits and actual rejection reasons required')
        need(all(stat(q['path'])==q for q in before),'Consumed test input/program changed')
        save(CHECK,dict(stage=TAG+'.review',passed=True,actual_call=call,source_build=stat(BUILD_CHECK),completion=stat(completion),tests_csv=stat(OUT/'tests.csv'),synthetic_fixture_root=str(OUT),tests=24,accepted_cases=5,rejected_cases=19,synthetic_only=True,physical_acceptance=False,solver_invocations=0,consumed=before,consumed_stats_unchanged=True))
    except Exception as error:
        if not CHECK.exists():save(CHECK,dict(stage=TAG+'.review',passed=False,first_failure=str(error),actual_call=call,consumed=before,synthetic_only=True,physical_acceptance=False))
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','run'));p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root must review and separately authorize this action');{'build':build,'run':run}[a.action]()
