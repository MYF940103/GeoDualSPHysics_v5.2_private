"""Build only the isolated failed-source forensic reader; never decode or solve."""
import argparse,os,subprocess,difflib
from pathlib import Path
import c08_h18_plastic_native_r1_build as prior

e=prior.e
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_loss_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke

def derive_source(raw):
    changes=[
      ('int wmain(int argc,wchar_t** argv){unsigned activePart=~0u,activeId=~0u;try{',
       'static std::vector<tdouble3> LossX0;\nstatic std::vector<float> LossP0,LossPreviousK;\nstatic double LossScalar=0.;\nstatic unsigned LossCompleted=0;\nint wmain(int argc,wchar_t** argv){unsigned activePart=~0u,activeId=~0u;try{'),
      ('Need(full?samples==H18Rows.size():(samples>=1&&samples<=H18Rows.size()),"Actual source count differs from its original complete plan");',
       'Need(!full&&samples==534&&H18Rows.size()==1001,"Only the observed failed534-frame source is admitted");samples=533; // Explicit strict prefix; Part533 is independently read by the forensic branch.\n'),
      ('Need(!full||(samples==1001&&previous==Event),"Full source event/count incomplete");',
       'Need(!full&&samples==533&&previous==1064001,"Strict complete prefix range differs");LossX0=x0;LossP0=p0;LossPreviousK=previousK;LossScalar=scalar;LossCompleted=previous;'),
      (r'\"stage\":\"c08_h18_plastic_native_r1.source\"',
       r'\"stage\":\"c08_h18_loss_native_r1.strict_prefix\",\"actual_run_saved_frames\":534,\"strict_prefix_final_part\":532,\"forced_final_part_separately_exported\":533,\"whole_run_native_passed\":false')]
    return prior.patch(raw,changes),changes

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root must completely review before one explicit utility build')
    check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing or partial forensic build protected');calls=[];before=[]
    try:
        bp=L/'c08_h18_plastic_native_r1.build.json';b=read(bp);need(b['passed'] and b['PRE_schema']==2 and b['consumed_stats_unchanged'] and not b['JSph_objects_linked'],'Passed original plastic utility build required')
        original=Path(bind(b['program'])['path']).parent
        generated={Path(q['path']).name:bind(q) for q in b['generated']}
        leaves=('h18_source_core_r1.cpp','h18_headers_r1.h','public22_core_r1.h','h18_profiles_r1.h','h18_plastic_entry_r1.cpp')
        need(all(k in generated for k in leaves),'Original sealed generated core set differs')
        source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md')
        objects=[bind(q) for q in b['objects']];need(len(objects)==6 and {Path(q['path']).stem for q in objects}=={'JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'},'Exactly six old utility objects required')
        before=[stat(q) for q in (Path(__file__),Path(prior.__file__),Path(prior.base.__file__),Path(prior.base.base.__file__),source,note,bp)]+[generated[k] for k in leaves]+objects+[bind(b['source_archive']),bind(b['physical_source_archive'])]
        headers=original/'headers';before += [stat(q) for q in headers.iterdir() if q.is_file()]
        raw=Path(generated['h18_source_core_r1.cpp']['path']).read_text(encoding='utf-8');derived,changes=derive_source(raw)
        entry=Path(generated['h18_plastic_entry_r1.cpp']['path']).read_text(encoding='utf-8');marker='// Includes below contain unchanged numeric loops in distinct namespaces; all headers were lifted above.';need(entry.count(marker)==1,'Original entry/preamble anchor differs');shared=entry[:entry.index(marker)]
        OUT.mkdir()
        for leaf in ('h18_headers_r1.h','public22_core_r1.h','h18_profiles_r1.h'):(OUT/leaf).write_bytes(Path(generated[leaf]['path']).read_bytes())
        (OUT/'loss_shared_r1.h').write_text(shared,encoding='utf-8',newline='\n');(OUT/'loss_source_r1.cpp').write_text(derived,encoding='utf-8',newline='\n')
        diff=OUT/'strict_prefix_core.diff';diff.write_text(''.join(difflib.unified_diff(raw.splitlines(keepends=True),derived.splitlines(keepends=True),fromfile='passed/plastic_source',tofile='forensic/strict_prefix',n=4)),encoding='utf-8')
        proof=OUT/'core_derivation.json';save(proof,dict(stage=TAG+'.derive',original_core=generated['h18_source_core_r1.cpp'],original_entry=generated['h18_plastic_entry_r1.cpp'],declared_replacements=changes,reverse_declared_replacements_exact=True,physical_numeric_guards_changed=False,source_plan_rows=1001,strict_complete_prefix_parts=[0,532],observed_saved_parts=[0,533],forced_final_separate=True,source_not_qualified=True,old_files_changed=False))
        before += [stat(q) for q in OUT.iterdir() if q.is_file()]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
        cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18LossNative_win64.exe'
        ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
        la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]]
        calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(q['path'])==q for q in before),'Frozen source/header/object changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),note=stat(note),original_native_build=stat(bp),source_archive=b['source_archive'],physical_source_archive=b['physical_source_archive'],objects=objects,actual_link_objects=7,JSph_objects_linked=False,core_derivation=stat(proof),core_diff=stat(diff),calls=calls,consumed=before,consumed_stats_unchanged=True,forensic_reader_only=True,decoder_invocations=0,solver_invocations=0,SHA_scans=0))
    except Exception as error:
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
        raise

if __name__=='__main__':main()
