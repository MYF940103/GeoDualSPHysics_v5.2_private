"""Author-only isolated legacy-NoPen diagnostic overlays and authoritative VS builds; no solver."""
import argparse,copy,ctypes,difflib,json,os,re,shutil,subprocess,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
import mdbc_partition_components_r3 as old
T=Path(__file__).resolve().parents[1];C=T.parent;R=T.parents[3];S=R/'src';L=T/'logs';TAG='upl_c08_nopen';CAP=T/'outputs/upl_c08_nopen_source_r1';BASE=T/'outputs/upl_c08_artstress_source_r1'
FILES=('JSph.cpp','JSphCpu.cpp','JSphGpu.cpp');NS='http://schemas.microsoft.com/developer/msbuild/2003';ET.register_namespace('',NS)
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def once(s,a,b):
    need(s.count(a)==1,'Unique frozen source patch not found: '+a[:100]);return s.replace(a,b,1)

def overlay(leaf,raw):
    # Change qualifications/contract metadata only, never a force/integration/ledger expression.
    nl='\r\n' if b'\r\n' in raw else '\n';s=raw.decode('utf8').replace('\r\n','\n')
    if leaf=='JSph.cpp':
        s=once(s,'std::string JSph::GetGravityPreloadContract()const{','std::string JSph::GetGravityPreloadContract()const{\n  const bool nopenprobe=(NoPenetration && TMdbc2==MDBC2_NoPen && IsGravityPreloadHandoff());')
        s=once(s,"<<HydroMechInitZ<<' '<<unsigned(TBoundary)<<' '<<unsigned(SlipMode)<<' '<<unsigned(TMdbc2)<<' '\n    <<NoPenetration<<' '<<Stable", "<<HydroMechInitZ<<' '<<unsigned(TBoundary)<<' '<<unsigned(SlipMode)<<' '<<unsigned(nopenprobe? MDBC2_Std: TMdbc2)<<' '\n    <<(nopenprobe? false: NoPenetration)<<' '<<Stable")
        s=once(s,'&& TBoundary==BC_MDBC && UseNormals && TMdbc2!=MDBC2_NoPen && !NoPenetration','&& TBoundary==BC_MDBC && UseNormals && ((!NoPenetration && TMdbc2!=MDBC2_NoPen)\n      || (IsGravityPreloadHandoff() && NoPenetration && TMdbc2==MDBC2_NoPen && !ArtificialStress))')
        line='      if(IsGravityPreloadHandoff())bdpart->SetvText("GravityPreloadStateFile",GravityPreloadStateFile);'
        s=once(s,line,line+'\n      if(NoPenetration && IsGravityPreloadHandoff()){\n        bdpart->SetvText("DynamicNoPenetrationPolicy","LegacyProjectionDiagnostic");\n        bdpart->SetvBool("DynamicNoPenetrationReactionClosed",false);\n      }')
        line='    (state.MaterialLawVersion==2? "unified2": "legacy MR1 ElasticV1"));'
        s=once(s,line,line+'\n  if(NoPenetration && IsGravityPreloadHandoff())Log->Print("NoPenLegacyProjectionDiagnostic: PRE contract uses source Std/false only for admission; active legacy NoPen projection has no closed reaction/J/Darcy coupling; diagnostic only.");')
    else:
        condition='gravitycontainer' if leaf=='JSphCpu.cpp' else 'container'
        s=once(s,'|| InOut || Shifting || NoPenetration || Symmetry || (StrainSoftening','|| InOut || Shifting || (NoPenetration && !('+condition+' && IsGravityPreloadHandoff())) || Symmetry || (StrainSoftening')
    return s.replace('\n',nl).encode('utf8')

def props(project_xml):
    project=ET.fromstring(project_xml);root=ET.Element('{'+NS+'}Project');group=ET.SubElement(root,'{'+NS+'}ItemGroup')
    for leaf in FILES:
        items=[x for x in project.findall('.//{'+NS+'}ClCompile') if Path(x.get('Include','').replace('\\','/')).name==leaf];need(len(items)==1,'Expected one authoritative ClCompile item: '+leaf);item=items[0];stem=Path(leaf).stem;private='_C08NoPen'+stem
        ET.SubElement(group,'{'+NS+'}'+private,{'Include':'@(ClCompile)','Condition':"'%(ClCompile.Filename)%(ClCompile.Extension)'=='"+leaf+"'"})
        ET.SubElement(group,'{'+NS+'}ClCompile',{'Remove':'@('+private+')'})
        new=ET.SubElement(group,'{'+NS+'}ClCompile',{'Include':'@('+private+"->'"+(CAP/leaf).as_posix()+"')"})
        # Preserve each explicit per-file item metadata (GPU CPU-config exclusion included).
        for child in item:new.append(copy.deepcopy(child))
        inc=ET.SubElement(new,'{'+NS+'}AdditionalIncludeDirectories');inc.text=(S/'source').as_posix()+';%(AdditionalIncludeDirectories)'
    target=ET.SubElement(root,'{'+NS+'}Target',{'Name':'C08NoPenValidateClCompileItems','BeforeTargets':'ClCompile'})
    original=';'.join('@(_C08NoPen'+Path(leaf).stem+')' for leaf in FILES);g=ET.SubElement(target,'{'+NS+'}ItemGroup');ET.SubElement(g,'{'+NS+'}_C08NoPenOriginal',{'Include':original});ET.SubElement(g,'{'+NS+'}_C08NoPenActual',{'Include':'@(ClCompile)','Condition':"'%(ClCompile.Filename)%(ClCompile.Extension)'=='JSph.cpp' Or '%(ClCompile.Filename)%(ClCompile.Extension)'=='JSphCpu.cpp' Or '%(ClCompile.Filename)%(ClCompile.Extension)'=='JSphGpu.cpp'"})
    ET.SubElement(target,'{'+NS+'}Error',{'Condition':"'@(_C08NoPenOriginal->Count())'!='3' Or '@(_C08NoPenActual->Count())'!='3'",'Text':'C08 NoPen overlay must replace exactly three ClCompile items.'})
    fields=['Filename','Extension','FullPath','ExcludedFromBuild','PrecompiledHeader','CompileAs','Optimization','RuntimeLibrary','WarningLevel','ObjectFileName','DebugInformationFormat','AdditionalOptions','PreprocessorDefinitions','BasicRuntimeChecks','SDLCheck','ExceptionHandling','EnableEnhancedInstructionSet','MultiProcessorCompilation','SupportJustMyCode','WholeProgramOptimization','FloatingPointModel','AdditionalIncludeDirectories']
    ET.SubElement(target,'{'+NS+'}WriteLinesToFile',{'File':'$(C08NoPenItemsReport)','Lines':'kind|'+'|'.join(fields),'Overwrite':'true','Encoding':'UTF-8'})
    for kind,item in [('original','_C08NoPenOriginal'),('overlay','_C08NoPenActual')]:
        text=kind+'|'+'|'.join('%('+x+')' for x in fields);ET.SubElement(target,'{'+NS+'}WriteLinesToFile',{'File':'$(C08NoPenItemsReport)','Lines':'@('+item+"->'"+text+"')",'Overwrite':'false','Encoding':'UTF-8'})
    ET.indent(root,space='  ');return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def prepare():
    check=L/(TAG+'_source_r1.prepare.json');need(not CAP.exists() and not check.exists(),'Existing/partial overlay source protected');b=read(L/'upl_c08_artstress_Release_r1.build.json');need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Closed frozen AS Release baseline required');base=read(bind(b['source_capture'])['path']);archive=Path(bind(b['source_archive'])['path']);need(archive.samefile(BASE/'source.zip'),'Unexpected AS source archive')
    original=[bind(e) for e in base['files']];CAP.mkdir();shutil.copy2(archive,CAP/'baselineAS_source.zip');shutil.copy2(BASE/'source.json',CAP/'baselineAS_source.json');need(stat(archive)['bytes']==stat(CAP/'baselineAS_source.zip')['bytes'],'Baseline whole archive copy differs');diff=[]
    with zipfile.ZipFile(archive) as z:
        for leaf in FILES:
            raw=z.read('src/source/'+leaf);candidate=overlay(leaf,raw);(CAP/leaf).write_bytes(candidate);diff += list(difflib.unified_diff(raw.decode('utf8').splitlines(keepends=True),candidate.decode('utf8').splitlines(keepends=True),fromfile='baselineAS/src/source/'+leaf,tofile='NoPenDiagnostic/'+leaf))
        cpu=z.read('src/VS/DualSPHysics5ReCpu.vcxproj');gpu=z.read('src/VS/DualSPHysics5Re.vcxproj');pc=props(cpu);pg=props(gpu);need(pc==pg,'The three original item metadata differ across CPU/GPU projects; inspect before overlay use');(CAP/'overlay.props').write_bytes(pc)
    (CAP/'three_files.diff').write_text(''.join(diff),encoding='utf8',newline='');files=[stat(p) for p in sorted(CAP.iterdir()) if p.is_file()]
    need(all(stat(e['path'])==e for e in original),'Original source changed during overlay preparation')
    save(check,dict(stage=TAG+'_source_r1',passed=True,source_baseline=stat(BASE/'source.json'),source_archive=stat(archive),files=files,original_worktree=original,original_worktree_stats_unchanged=all(stat(e['path'])==e for e in original),only_CPP_overlays=list(FILES),numerical_equations_changed=False,NoPen_reaction_J_Darcy_closure=False,scope='LegacyProjectionDiagnostic; AS0; qualified existing elastic PRE handoff only',programs_or_builds_started=0,SHA_scans=0));print('OVERLAY_SOURCE_PREPARED',check,flush=True)

def check_report(path):
    text=path.read_text(encoding='utf-8-sig');rows=[x.split('|') for x in text.splitlines() if x];need(len(rows)==7,'Exactly header+three originals+three overlays required');head=rows[0];need(all(len(row)==len(head) for row in rows[1:]),'Evaluated metadata contains unexpected report separator/newline; inspect before build')
    orig={r[1]+r[2]:dict(zip(head,r)) for r in rows[1:] if r[0]=='original'};new={r[1]+r[2]:dict(zip(head,r)) for r in rows[1:] if r[0]=='overlay'};need(set(orig)==set(new)==set(FILES),'Evaluated item filenames differ')
    for leaf in FILES:
        a,b=orig[leaf],new[leaf];need(Path(b['FullPath']).samefile(CAP/leaf),'Original project source still selected for overlay')
        for k in head:
            if k not in ('kind','FullPath','AdditionalIncludeDirectories'):need(a[k]==b[k],'Per-file evaluated metadata changed: '+leaf+' '+k)
        prefix=(S/'source').as_posix()+';';need(b['AdditionalIncludeDirectories']==prefix+a['AdditionalIncludeDirectories'],'Only original source include path may be added')
    return dict(passed=True,three_items_replaced=True,all_other_evaluated_metadata_equal=True,source_include_only_added=True,report=stat(path))

def build(action,conf):
    gpu=conf=='Release';tag=TAG+'_'+conf+'_r1';receipt=L/(tag+('.evaluate.json' if action=='evaluate' else '.build.json'));need(not receipt.exists(),'Existing build/evaluation protected');prep=L/(TAG+'_source_r1.prepare.json');c=read(prep);need(c['passed'] and c['original_worktree_stats_unchanged'],'Prepared overlay source required');consumed=[stat(prep),*[bind(e) for e in c['files']],*[bind(e) for e in c['original_worktree']],stat(Path(__file__)),stat(T/'notes/upl_c08_nopen_build_r1.md')]
    out=T/'outputs'/tag;inter=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_c08_nopen_r1'/conf/'int';need(' ' not in str(inter),'No-space CUDA IntDir required');template=L/('upl_c08_artstress_'+conf+'_r1.call.json');call=read(template);args=call['arguments'].copy();report=L/(tag+('.evaluate.items.txt' if action=='evaluate' else '.build.items.txt'));need(not report.exists(),'Existing evaluated items report protected');logtag=tag+'.'+action
    args=[('/t:C08NoPenValidateClCompileItems' if action=='evaluate' else '/t:Build') if x.startswith('/t:') else '/p:OutDir='+out.as_posix()+'/' if x.startswith('/p:OutDir=') else '/p:IntDir='+inter.as_posix()+'/' if x.startswith('/p:IntDir=') else '/bl:'+str(L/(logtag+'.binlog')) if x.startswith('/bl:') else x for x in args]
    # A solution metaproject does not expose arbitrary C++ targets: evaluate its actual authoritative project directly.
    if action=='evaluate':args[0]=str(S/'VS'/('DualSPHysics5Re.vcxproj' if gpu else 'DualSPHysics5ReCpu.vcxproj'))
    # Builds still use the original solution; only this evaluated item overlay is imported.
    args += ['/p:ForceImportBeforeCppTargets='+(CAP/'overlay.props').as_posix(),'/p:C08NoPenItemsReport='+str(report)]
    need('/p:PostBuildEventUseInBuild=false' in args and '/p:VCToolsVersion=14.36.32532' in args,'Original isolated VS toolchain flags differ');consumed.append(stat(template));protected=[]
    for root in [R/'bin/windows',C/'support/runtime_r2',C/'support/runtime_r3']:
        protected += [stat(p) for p in root.iterdir() if p.is_file() and p.suffix.lower() in ('.exe','.dll','.pdb','.xml')]
    for name in ('DebugCPU','Debug','Release'):
        b=read(L/('upl_c08_artstress_'+name+'_r1.build.json'));need(b['passed'],'Original AS build not closed');protected += [bind(b['program']),*[bind(e) for e in b['project_objects']]]
    if action=='build':
        ev=read(L/(tag+'.evaluate.json'));need(ev['passed'] and ev['items']['passed'],'Explicit same-config evaluated-items pass required before compiling');consumed.append(stat(L/(tag+'.evaluate.json')));need(not out.exists() and not inter.parent.exists(),'Existing/partial isolated objects/output protected');out.mkdir();inter.mkdir(parents=True)
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','MSVC14.36 required');actual=None;result=dict(stage=logtag,passed=False,programs_or_solvers_started=0,SHA_scans=0,physical_acceptance=False)
    try:
        actual=invoke(logtag,[call['program'],*args],S,env);items=check_report(report);need(all(stat(e['path'])==e for e in consumed+protected),'Frozen source, canonicals or old object stats changed');result.update(passed=True,actual_call=actual,items=items,consumed=consumed,protected=protected,source_stats_unchanged=True,canonical_runtime_old_objects_stats_unchanged=True)
        if action=='build':
            exe=out/('DualSPHysics5.2_GEO_win64.exe' if gpu else 'DualSPHysics5.2CPU_win64_debug.exe');objects=[stat(p) for p in sorted(inter.glob('*.obj'))];need(exe.is_file() and len(objects)==(113 if gpu else 87),'Original authoritative object/program closure differs');result.update(program=stat(exe),project_objects=objects,source_capture=stat(prep),source_archive=stat(CAP/'baselineAS_source.zip'),overlay_sources=[stat(CAP/p) for p in FILES],actual_typed_exit_code=0,actual_Win32_exit=0)
    except Exception as e:
        cp=L/(logtag+'.call.json')
        if cp.exists():
            actual=stat(cp);record=read(cp);result.update(actual_typed_exit_code=record['actual_Popen_wait_exit'],actual_Win32_exit=record['actual_Win32_exit'])
        result.update(passed=False,first_failure=str(e),actual_call=actual,consumed=consumed,protected=protected)
    save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('prepare','evaluate','build'));ap.add_argument('--configuration',choices=('DebugCPU','Release'));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full review and explicit author-tool invocation required')
    if a.action=='prepare':need(a.configuration is None,'Preparation is shared, not per configuration');prepare();return 0
    need(a.configuration is not None,'One explicit authoritative configuration required');return build(a.action,a.configuration)
if __name__=='__main__':raise SystemExit(main())
