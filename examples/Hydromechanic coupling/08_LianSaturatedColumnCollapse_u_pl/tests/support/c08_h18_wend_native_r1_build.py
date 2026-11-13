"""Build only the explicit Wendland H1.8 same-material native adapter."""
import argparse,difflib,os,subprocess
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as e

T=Path(__file__).resolve().parents[1];L=T/'logs'
TAG='c08_h18_wend_native_r1';OUT=T/'outputs'/(TAG+'_build')
BASE=L/'c08_h18_plastic_native_r1.build.json'
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke


def patch(raw,changes):
    out=raw
    for before,after in changes:
        need(out.count(before)==1,'Unique Wendland derivation anchor differs: '+before[:100])
        out=out.replace(before,after,1)
    inverse=out
    for before,after in reversed(changes):
        need(inverse.count(after)==1,'Reverse Wendland derivation anchor differs')
        inverse=inverse.replace(after,before,1)
    need(inverse==raw,'New core differs beyond the declared kernel identity/profile edits')
    return out


CONTRACT=r'''static void H18CheckWendlandContract(const std::string& contract){
 std::istringstream input(contract);std::string prefix2,prefix1;std::array<std::string,8> values;std::string kernel;
 H18Need(bool(input>>prefix2>>prefix1),"Native material contract prefix is incomplete");
 for(auto& value:values)H18Need(bool(input>>value),"Native contract has fewer than eight geometry/reference fields");
 H18Need(bool(input>>kernel)&&prefix2=="gravity-preload-2"&&prefix1=="gravity-preload-1","Native schema2/contract1 prefix differs");
 // Read the actual serialized field order, not a substring search for a digit2.
 const unsigned count=H18Unsigned(values[0]),fixed=H18Unsigned(values[1]),soil=H18Unsigned(values[2]);
 const double dp=H18Double(values[3]),h=H18Double(values[4]),massf=H18Double(values[5]),massb=H18Double(values[6]),rho=H18Double(values[7]);
 H18Need(count==7060&&fixed==2060&&soil==5000&&dp==.04&&h==double(.072f)&&massf==double(float(3.316))&&massb==massf&&rho==2072.5&&H18Unsigned(kernel)==2,"Native certificate geometry/reference/unsigned TKernel is not the declared Wendland scope");
 // The remaining material/history contract is deliberately NOT reconstructed here.
}
'''


def derive_source(raw):
    tail=next(q for q in raw.splitlines() if q.startswith('  else for(const char* key:{"GravityPreloadHandoffSchema"'))
    changes=[
        ('const std::set<std::string> keys={"group","ModulusE","PRvs","DPCtes"','const std::set<std::string> keys={"Kernel","group","ModulusE","PRvs","DPCtes"'),
        ('Need(std::stoul(p.at("DPCtes"))','Need(H18Unsigned(p.at("Kernel"))==2,"Actual source XML/CSV Kernel must be2/Wendland");Need(std::stoul(p.at("DPCtes"))'),
        (tail,tail+'\n  if(event)H18CheckWendlandContract(p->GetvText("GravityPreloadHandoffContract"));'),
        ('c08_h18_plastic_native_r1.source','c08_h18_wend_native_r1.source'),
        (r'\"source_material_CSV_keys\":14',r'\"source_material_CSV_keys\":15'),
        (r'\"geometry_profile\":\"bedroles\"',r'\"declared_Kernel_XML_CSV\":2,\"kernel_name_declared\":\"Wendland\",\"source_event_contract_kernel_checked\":"<<(full?"true":"false")<<",\"non_event_kernel_identity_proven_by_reader\":false,\"actual_XML_Runout_kernel_binding_required\":true,\"geometry_profile\":\"bedroles\"')]
    return patch(raw,changes),changes


def derive_receiver(raw):
    anchor='const std::string contract=meta->GetvText("GravityPreloadHandoffContract");'
    changes=[
        (anchor,anchor+'H18CheckWendlandContract(contract);'),
        ('c08_h18_plastic_native_r1.receiver','c08_h18_wend_native_r1.receiver'),
        (r'\"source_handoff_schema\":2',r'\"declared_Kernel_XML_CSV\":2,\"kernel_name_declared\":\"Wendland\",\"source_PRE_contract_kernel_checked\":true,\"receiver_kernel_independently_proven_by_arrays\":false,\"actual_XML_Runout_kernel_binding_required\":true,\"source_handoff_schema\":2')]
    return patch(raw,changes),changes


def derive_entry(raw):
    anchor='// Includes below contain unchanged numeric loops in distinct namespaces; all headers were lifted above.'
    changes=[
        ('const std::set<std::string> keys={"group","ModulusE","PRvs","ArtificialStressCoef"','const std::set<std::string> keys={"Kernel","group","ModulusE","PRvs","ArtificialStressCoef"'),
        ('H18Group=group;H18E=','H18Need(H18Unsigned(p.at("Kernel"))==2,"Actual receiver XML/CSV Kernel must be2/Wendland");H18Group=group;H18E='),
        (anchor,CONTRACT+anchor),
        ('c08_h18_plastic_native_r1.metadata','c08_h18_wend_native_r1.metadata'),
        (r'\"expected_source_material_CSV_keys\":14',r'\"expected_source_material_CSV_keys\":15'),
        (r'\"receiver_material_CSV_keys\":16',r'\"receiver_material_CSV_keys\":17'),
        (r'\"geometry_profile\":\"bedroles\"',r'\"declared_Kernel_XML_CSV\":2,\"kernel_name_declared\":\"Wendland\",\"source_PRE_contract_kernel_checked\":true,\"receiver_kernel_independently_proven_by_arrays\":false,\"actual_XML_Runout_kernel_binding_required\":true,\"geometry_profile\":\"bedroles\"')]
    return patch(raw,changes),changes


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');a=parser.parse_args()
    need(a.execution_authorized,'Root full-read before the one explicit utility build')
    check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial utility build protected')
    before=[];calls=[]
    try:
        baseline=read(BASE)
        need(baseline['passed'] and baseline['consumed_stats_unchanged'] and baseline['actual_link_objects']==7 and not baseline['JSph_objects_linked'],'Passed plastic utility baseline required')
        objects=[bind(q) for q in baseline['objects']]
        need(len(objects)==6 and {Path(q['path']).stem for q in objects}=={'JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'},'Exactly six unchanged BI4 utility objects required')
        originals={Path(q['path']).name:bind(q) for q in baseline['generated']}
        leaves={'h18_plastic_entry_r1.cpp','h18_headers_r1.h','public22_core_r1.h','h18_source_core_r1.cpp','h18_receiver_core_r1.cpp','h18_profiles_r1.h'}
        need(set(originals)==leaves,'Actual passed generated-core closure differs')
        archive=Path(bind(baseline['source_archive'])['path']);physical_archive=Path(bind(baseline['physical_source_archive'])['path'])
        source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md')
        before=[stat(q) for q in (Path(__file__),Path(e.__file__),source,note,BASE)]+[bind(baseline[k]) for k in ('program','source','source_build','source_capture','physical_source_build')]+[stat(archive),stat(physical_archive),*objects,*originals.values()]
        OUT.mkdir();headers=OUT/'headers';headers.mkdir()
        with ZipFile(archive) as z:
            for item in z.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
                    dest=headers/Path(item.filename).name;need(not dest.exists(),'Duplicate archived header leaf');dest.write_bytes(z.read(item))
        with ZipFile(physical_archive) as z:
            for leaf in ('JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h'):need((headers/leaf).read_bytes()==z.read('src/source/'+leaf),'Original utility/physical ABI header differs: '+leaf)
            for leaf in ('JGravityPreloadState.h','FunSoilMaterial.h'):(headers/leaf).write_bytes(z.read('src/source/'+leaf))
        raw={name:Path(q['path']).read_text(encoding='utf-8-sig') for name,q in originals.items()}
        entry,ec=derive_entry(raw['h18_plastic_entry_r1.cpp']);source_core,sc=derive_source(raw['h18_source_core_r1.cpp']);receiver_core,rc=derive_receiver(raw['h18_receiver_core_r1.cpp'])
        need('#include <sstream>' not in raw['h18_headers_r1.h'],'Expected explicit new contract-token stream include')
        generated={OUT/'h18_wend_entry_r1.cpp':entry,OUT/'h18_headers_r1.h':raw['h18_headers_r1.h']+'#include <sstream>\n',OUT/'public22_core_r1.h':raw['public22_core_r1.h'],OUT/'h18_source_core_r1.cpp':source_core,OUT/'h18_receiver_core_r1.cpp':receiver_core,OUT/'h18_profiles_r1.h':raw['h18_profiles_r1.h']}
        for dest,text in generated.items():dest.write_text(text,encoding='utf-8',newline='\n')
        diffs=[]
        for name,old,new in [('entry',raw['h18_plastic_entry_r1.cpp'],entry),('source',raw['h18_source_core_r1.cpp'],source_core),('receiver',raw['h18_receiver_core_r1.cpp'],receiver_core)]:
            dest=OUT/(name+'_core.diff');dest.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='passed_plastic/'+name,tofile='explicit_wendland/'+name,n=3)),encoding='utf-8');diffs.append(stat(dest))
        derivation=OUT/'core_derivation.json'
        save(derivation,dict(stage=TAG+'.derivation',passed_baseline=stat(BASE),baseline_generated=list(originals.values()),generated=[stat(q) for q in generated],diffs=diffs,source_declared_replacements=sc,receiver_declared_replacements=rc,entry_declared_replacements=ec,reverse_declared_replacements_exact=True,unchanged_pure22_body=True,unchanged_scalar_profile_body=True,source_material_CSV_keys=15,receiver_material_CSV_keys=17,declared_Kernel_XML_CSV=2,full_event_and_PRE_contract_token_Kernel_required=2,full_material_contract_independently_reconstructed=False,non_event_XML_Runout_kernel_binding_required=True,physical_equations_changed=False,original_numerical_tolerances_changed=False,old_files_changed=False))
        before += [stat(q) for q in generated]+diffs+[stat(derivation),stat(headers/'JGravityPreloadState.h'),stat(headers/'FunSoilMaterial.h')]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching six-object MSVC14.36 required')
        cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18WendNative_win64.exe'
        ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
        la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]]
        calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(q['path'])==q for q in before),'Closed baseline/program/object/source changed')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),baseline_build=stat(BASE),baseline_generated=list(originals.values()),source_archive=stat(archive),physical_source_archive=stat(physical_archive),source_capture=baseline['source_capture'],generated=[stat(q) for q in generated],core_derivation=stat(derivation),objects=objects,actual_link_objects=7,JSph_objects_linked=False,declared_Kernel_XML_CSV=2,source_material_CSV_keys=15,receiver_material_CSV_keys=17,non_event_XML_Runout_kernel_binding_required=True,full_material_contract_independently_reconstructed=False,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0))
    except Exception as error:
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
        raise


if __name__=='__main__':main()
