"""One root-admitted, fresh full111 C04 GPU Release build; never run a program.

The source is a new reconstructed/private candidate. No old C02/C04 object is
copied or linked, and no historical full-source-at-compile capture is claimed.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
import upl_tpi_cryer_cpu_build_r1 as b  # Pure ownership/stat/tool-call helpers only.

T, L, R = b.T, b.L, b.R
STAGE = 'upl_tpi_cryer_gpu_release_build_r1'
TAG = 'upl_tpi_cryer_gpu_Release_r1'
PREP = L / 'upl_tpi_cryer_gpu_r2.prepare.json'
OLD_BUILD = L / 'upl_cryer_freebody_r1_Release.build.json'
OLD_CALL = L / 'upl_cryer_freebody_r1_Release.call.json'
OLD_LOG = L / 'upl_cryer_freebody_r1_Release.log'
DEBUG_BUILD = L / 'upl_cryer_freebody_r1_Debug.build.json'
DEBUG_CALL = L / 'upl_cryer_freebody_r1_Debug.call.json'
OUT = T / 'outputs' / TAG
CHECK = L / (TAG + '.build.json')
CUDA = Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7')
NVCC = CUDA / 'bin/nvcc.exe'
VCROOT = Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532')
CL, LINK = VCROOT / 'bin/HostX64/x64/cl.exe', VCROOT / 'bin/HostX64/x64/link.exe'
CUSTOM = Path('D:/Program Files/VS2022/MSBuild/Microsoft/VC/v170/BuildCustomizations')
NS = b.NS
HELPERS = {'upl_tpi_cryer_gpu_r1.h', 'upl_tpi_cryer_gpu_r1.cuh'}


class Admission:
    def __init__(self, path):
        self.entry, self.data = b.stat(path), b.read(path)
        b.need(self.data.get('stage') == STAGE + '.build_admission' and self.data.get('passed') is True
               and self.data.get('build_only') is True and self.data.get('configuration') == 'Release',
               'Independent full111 Release-only root admission required')
        self.frozen = {b.key(e['path']): e for e in self.data['inputs']}; self.consumed = {}
        b.need(len(self.frozen) == len(self.data['inputs']), 'Duplicate root input binding')

    def pin(self, path):
        k = b.key(path); b.need(k in self.frozen, 'Consumed input absent from admission: ' + str(path))
        self.consumed[k] = b.same(self.frozen[k]); return self.consumed[k]

    def finish(self):
        for entry in self.consumed.values():
            b.same(entry)
        b.same(self.entry); return list(self.consumed.values())


def spelling(text):
    return text.replace('/', '\\').casefold()


def peel_source(raw, source):
    """Recover the genuine source suffix before parsing a possibly bare space."""
    raw = raw.rstrip(); quoted = raw.endswith('"'); n = len(source) + (2 if quoted else 0)
    b.need(len(raw) > n and raw[-n-1].isspace(), 'Missing real source suffix/boundary')
    tail = raw[-n:]; actual = tail[1:-1] if quoted else tail
    b.need((not quoted or tail.startswith('"')) and spelling(actual) == spelling(source),
           'Full command suffix does not match its actual source')
    return raw[:-n].rstrip()


def cl_commands(path):
    lines = path.read_text(encoding='utf-16').splitlines(); result = {}
    b.need(len(lines) % 2 == 0, 'CL command-pair schema differs')
    for i in range(0, len(lines), 2):
        b.need(lines[i].startswith('^') and '|' not in lines[i], 'One true CL source header required')
        source = lines[i][1:]; name = Path(source).name.casefold()
        b.need(name not in result, 'Duplicate CL source header')
        result[name] = dict(source=source, flags=b.windows_argv(peel_source(lines[i+1], source)))
    return result


def normalize_cl(flags):
    result, deps = [], []; i = 0
    while i < len(flags):
        x = flags[i]; low = x.casefold()
        if low == '/sourcedependencies':
            b.need(i+1 < len(flags), 'Missing CL sourceDependencies argument'); deps.append(flags[i+1]); i += 2; continue
        if low.startswith('/sourcedependencies:'):
            deps.append(x.split(':',1)[1])
        elif low.startswith(('/fo','/fd')):
            pass
        elif low.startswith('/i'):
            result.append('/I' + b.key(x[2:]))
        else:
            result.append(x.upper())
        i += 1
    return result, deps


def nvcc_commands(path):
    """Read the actual MSBuild CUDA command echo, not old XML custom strings."""
    result = {}
    for line in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        m = re.search(r'>"([^"\r\n]*nvcc\.exe)"\s+(.+)$', line, re.IGNORECASE)
        if not m:
            continue
        tail = re.search(r'"([^"\r\n]+\.(?:cu|h))"\s*$', m.group(2), re.IGNORECASE)
        b.need(bool(tail), 'Actual NVCC command lacks one complete quoted source suffix')
        source = tail.group(1); name = Path(source).name.casefold()
        b.need(name not in result and b.key(m.group(1)) == b.key(NVCC), 'Duplicate NVCC source or different actual tool')
        flags = b.windows_argv(peel_source(m.group(2), source))
        b.need(flags.count('-o') == 1 and flags.index('-o')+1 < len(flags), 'Actual NVCC output argument differs')
        result[name] = dict(source=source, flags=flags, object=Path(flags[flags.index('-o')+1]).name)
    b.need(len(result) == 14, 'Exactly fourteen actual NVCC compile echoes required')
    return result


def normalize_nvcc(flags):
    result, outputs, keep = [], [], []; i = 0
    while i < len(flags):
        x = flags[i]; low = x.casefold()
        if low in ('-o','--keep-dir'):
            b.need(i+1 < len(flags), 'Missing NVCC metadata argument')
            (outputs if low == '-o' else keep).append(flags[i+1]); i += 2; continue
        if low == '-xcompiler':
            b.need(i+1 < len(flags), 'Missing genuine NVCC host flags')
            nested = b.windows_argv(flags[i+1])
            result.extend(('-XCOMPILER', tuple(z.upper() for z in nested if not z.casefold().startswith('/fd'))))
            i += 2; continue
        if low == '-ccbin':
            b.need(i+1 < len(flags), 'Missing NVCC ccbin'); result.extend(('-CCBIN', b.key(flags[i+1]))); i += 2; continue
        if low.startswith('-i'):
            result.append('-I' + b.key(x[2:]))
        else:
            result.append(x.upper())
        i += 1
    b.need(len(outputs) == len(keep) == 1, 'Expected one original NVCC output/keep-dir argument')
    return result, outputs[0], keep[0]


def blocks(path):
    result, current = {}, None
    for line in path.read_text(encoding='utf-16').splitlines():
        if line.startswith('^'):
            b.need('|' not in line and line[1:] not in result, 'One dependency source per block required')
            current = line[1:]; result[current] = []
        elif line:
            b.need(current is not None, 'Dependency precedes source header'); result[current].append(Path(line).resolve())
    return result


def link_recipe(path):
    lines=path.read_text(encoding='utf-16').splitlines()
    headers=[x for x in lines if x.startswith('^')]
    b.need(len(headers)==1, 'Exactly one actual link command header required')
    args=b.windows_argv(' '.join(x for x in lines if not x.startswith('^')))
    normalized=[];objects=[]
    for x in args:
        low=x.casefold()
        if not x.startswith('/') and low.endswith('.obj'):
            objects.append(Path(x).name.casefold());normalized.append('OBJ:'+Path(x).name.casefold())
        elif low.startswith(('/out:','/pdb:','/implib:','/ltcgout:','/ilk:','/libpath:')):
            continue
        else:
            normalized.append(x.upper())
    return headers[0],objects,normalized


def project_items(project, tag):
    result = []
    for item in ET.parse(project).getroot().findall('.//m:' + tag + '[@Include]', NS):
        excluded = any("Release|x64" in e.get('Condition','') and e.text == 'true' for e in item.findall('m:ExcludedFromBuild',NS))
        if not excluded:
            result.append(item.get('Include'))
    return result


def context(ad):
    for p in (Path(__file__), T/'notes/upl_tpi_cryer_gpu_release_build_r1.md', Path(b.__file__), sys.executable,
              PREP, OLD_BUILD, OLD_CALL, OLD_LOG, DEBUG_BUILD, DEBUG_CALL,
              b.MSBUILD, b.VCVARS, NVCC, CL, LINK):
        ad.pin(p)
    import psutil
    ad.pin(psutil.__file__)
    for name in ('CUDA 11.7.props','CUDA 11.7.targets','CUDA 11.7.xml','Nvda.Build.CudaTasks.v11.7.dll'):
        ad.pin(CUSTOM/name)
    prep, old, call, dbg, dbgcall = map(b.read,(PREP,OLD_BUILD,OLD_CALL,DEBUG_BUILD,DEBUG_CALL))
    b.need(prep['passed'] and old['passed'] and old['configuration']=='Release' and old['objects']==111
           and call['exit_code']==0 and dbg['passed'] and dbg['configuration']=='Debug'
           and dbg['objects']==111 and dbgcall['exit_code']==0, 'New source and original actual full111 GPU recipes required')
    root = Path(prep['source_root']).resolve(); source, vs = root/'source', root/'VS'
    for e in prep['files']:
        ad.pin(e['path']); b.same(e)
    ad.pin(prep['source_diff']['path']); b.same(prep['source_diff']); diff=b.read(prep['source_diff']['path'])
    b.need(diff['passed'] and set(diff['only_changed_TUs'])=={'JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.cu'}
           and diff['class_or_header_ABI_changed'] is False and diff['HG_adapters_called'] is False
           and set(diff['new_private_helpers'])==HELPERS, 'Only the reviewed C04 three-TU/HG0 private overlay is permitted')
    b.need(len(list(source.iterdir()))==267 and all((source/x).is_file() for x in HELPERS), 'New full267 source/helper membership differs')
    solution, project = vs/'DualSPHysics5Re.sln', vs/'DualSPHysics5Re.vcxproj'
    ad.pin(solution); ad.pin(project)
    cl, cu = project_items(project,'ClCompile'), project_items(project,'CudaCompile')
    cl_names = [Path(x.replace('\\','/')).name for x in cl]; cu_names=[Path(x.replace('\\','/')).name for x in cu]
    b.need(len(cl_names)==len(set(cl_names))==97 and len(cu_names)==len(set(cu_names))==14, 'Actual authoritative Release97CL/14CUDA project scope differs')
    oldint=Path(next(x.split('=',1)[1] for x in call['arguments'] if x.startswith('/p:IntDir=')))
    oldt=oldint/'DualSPHysics.tlog'; paths={n:oldt/n for n in ('CL.command.1.tlog','CL.read.1.tlog','CudaCompile.read.1u.tlog','CudaCompile.write.1u.tlog','link.command.1.tlog','link.read.1.tlog')}
    for p in paths.values():
        ad.pin(p)
    oldcl, oldcu = cl_commands(paths['CL.command.1.tlog']), nvcc_commands(OLD_LOG)
    b.need(set(oldcl)=={x.casefold() for x in cl_names} and set(oldcu)=={x.casefold() for x in cu_names}, 'Original actual command/project TU membership differs')
    expected_objects=[Path(x).stem+'.obj' for x in cl_names]+[oldcu[x.casefold()]['object'] for x in cu_names]
    b.need(len(expected_objects)==len(set(expected_objects))==111
           and {'FunctionsGeo3d_iker.h.obj','FunctionsMath_iker.h.obj'}<=set(expected_objects), 'Original111 object names including .h.obj differ')
    # Bind mapped/new repository files, never mutable historical canonical sources.
    for name in ('CL.read.1.tlog','CudaCompile.read.1u.tlog'):
        for head, inc in blocks(paths[name]).items():
            for p in [Path(head).resolve(),*inc]:
                if p.is_relative_to(R/'src/source'):
                    ad.pin(source/p.name)
                elif b.key(p)==b.key(R/'src/VS/DualSPHysics5Re.vcxproj'):
                    ad.pin(project)
                else:
                    b.need(not p.is_relative_to(R), 'Unexpected historical repository dependency'); ad.pin(p)
    libs={Path(x).resolve() for x in paths['link.read.1.tlog'].read_text(encoding='utf-16').splitlines() if not x.startswith('^') and x.lower().endswith('.lib')}
    b.need(len(libs)==26, 'Actual original GPU Release26-library closure differs')
    third={p for p in libs if b.key(p.parent)==b.key(R/'src/lib/vs2022')}
    b.need(len(third)==5 and {p.name.casefold() for p in third}=={'dsphchrono.lib','libjvtklib_x64_v143_release.lib','libjnumexlib_x64_v143_release.lib','libjwavegen_x64_v143_release.lib','libdsphmoordyn_x64_v143_release.lib'}, 'Original five Release project libraries differ')
    b.need(sum(p.is_relative_to(CUDA/'lib/x64') for p in libs)==3
           and all('10.0.22000.0' in str(p) for p in libs if 'windows kits' in str(p).lower()), 'Original CUDA11.7/SDK10.0.22000 library selection differs')
    for p in libs:
        ad.pin(p)
    for e in old['runtime']:
        ad.pin(e['path']); b.same(e)
    intdir=Path(os.environ['LOCALAPPDATA'])/'Temp'/TAG/'int'
    b.need(' ' not in str(intdir) and not intdir.parent.exists() and not OUT.exists() and not CHECK.exists(), 'Existing build/partial or invalid IntDir is protected')
    return dict(source_root=root,source=source,vs=vs,solution=solution,project=project,cl=cl,cu=cu,
                cl_names=cl_names,cu_names=cu_names,oldcl=oldcl,oldcu=oldcu,oldpaths=paths,
                objects=expected_objects,libs=libs,third=third,runtime=old['runtime'],intdir=intdir,outdir=OUT/'out')


def targets(path, ctx, libdirs, evaluated):
    uri=NS['m']; ET.register_namespace('',uri); root=ET.Element('{'+uri+'}Project')
    prop=ET.SubElement(root,'PropertyGroup')
    for name in ('PreBuildEventUseInBuild','PreLinkEventUseInBuild','PostBuildEventUseInBuild'):
        ET.SubElement(prop,name).text='false'
    items=ET.SubElement(root,'ItemGroup')
    for rel in ctx['cl']:
        e=ET.SubElement(items,'ClCompile',Update=rel); leaf=Path(rel.replace('\\','/')).stem
        ET.SubElement(e,'AdditionalOptions').text='/sourceDependencies "'+str(ctx['intdir']/(leaf+'.dependencies.json'))+'" %(AdditionalOptions)'
    defs=ET.SubElement(root,'ItemDefinitionGroup'); cl=ET.SubElement(defs,'ClCompile')
    ET.SubElement(cl,'ProgramDataBaseFileName').text=str(ctx['intdir']/'vc143.pdb')
    link=ET.SubElement(defs,'Link')
    for name,value in [('AdditionalLibraryDirectories',';'.join(map(str,libdirs))+';%(AdditionalLibraryDirectories)'),
                       ('ProgramDatabaseFile',str(ctx['outdir']/'candidate.pdb')),('ImportLibrary',str(ctx['outdir']/'candidate.lib')),
                       ('LinkTimeCodeGenerationObjectFile',str(ctx['intdir']/'candidate.iobj')),
                       ('AdditionalOptions','/ILK:"'+str(ctx['intdir']/'candidate.ilk')+'" %(AdditionalOptions)')]:
        ET.SubElement(link,name).text=value
    target=ET.SubElement(root,'Target',Name='C04PrivateGpuCompileList',BeforeTargets='ClCompile;CudaCompile')
    ET.SubElement(target,'WriteLinesToFile',File=str(evaluated),Overwrite='true',Encoding='UTF-8',
                  Lines="@(ClCompile->'CL|%(FullPath)|%(ExcludedFromBuild)');@(CudaCompile->'CUDA|%(FullPath)|%(ExcludedFromBuild)')")
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def build(ad, ctx, result):
    OUT.mkdir();ctx['outdir'].mkdir();ctx['intdir'].mkdir(parents=True)
    libdir=OUT/'lib/vs2022';libdir.mkdir(parents=True);copies=[]
    for p in sorted(ctx['third'],key=b.key):
        dest=libdir/p.name
        with dest.open('xb') as f:f.write(p.read_bytes())
        b.need(dest.read_bytes()==p.read_bytes(),'Private project library copy differs')
        copies.append(dict(source=b.stat(p),destination=b.stat(dest)))
    batch=OUT/'load_environment.cmd'
    with batch.open('xb') as f:
        f.write(('@echo off\r\ncall "'+str(b.VCVARS)+'" x64 10.0.22000.0 -vcvars_ver=14.36 >nul\r\nif errorlevel 1 exit /b %errorlevel%\r\nset\r\n').encode('mbcs'))
    ad.finish();call,raw=b.invoke(TAG+'.environment',[os.environ.get('COMSPEC','C:/Windows/System32/cmd.exe'),'/d','/s','/c',batch.name],OUT,os.environ.copy(),True)
    result['calls'].append(call);env={k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in (x.split('=',1) for x in raw.decode('mbcs').splitlines() if '=' in x and not x.startswith('=')))
    for name in ('CL','_CL_','LINK','_LINK_','UPL_TPI_CPU_R1','UPL_TPI_GPU_R1'):env.pop(name,None)
    b.need(env.get('VCTOOLSVERSION')=='14.36.32532' and env.get('WINDOWSSDKVERSION','').rstrip('\\/')=='10.0.22000.0', 'Actual selected original GPU toolchain differs')
    # Use the original forward-slash CUDA spelling; no global environment edit.
    cuda_text=CUDA.as_posix();env['CUDA_PATH_V11_7']=cuda_text;env['CUDA_PATH']=cuda_text
    extra=OUT/'private_gpu.targets';evaluated=OUT/'evaluated_compile_sources.txt'
    libdirs=[libdir,*sorted({p.parent for p in ctx['libs'] if p not in ctx['third']},key=b.key)]
    targets(extra,ctx,libdirs,evaluated);binlog=L/(TAG+'.binlog');b.need(not binlog.exists(),'Existing binlog protected')
    args=[str(b.MSBUILD),str(ctx['solution']),'/m:1','/nr:false','/t:Rebuild','/v:minimal',
          '/p:Configuration=Release','/p:Platform=x64','/p:PlatformToolset=v143','/p:VCToolsVersion=14.36.32532',
          '/p:WindowsTargetPlatformVersion=10.0.22000.0','/p:BuildProjectReferences=false','/p:PostBuildEventUseInBuild=false',
          '/p:OutDir='+str(ctx['outdir'])+'/', '/p:IntDir='+str(ctx['intdir'])+'/',
          '/p:ForceImportAfterCppTargets='+str(extra),'/bl:'+str(binlog)]
    ad.finish();call,_=b.invoke(TAG+'.msbuild',args,ctx['vs'],env);result['calls'].append(call)
    actual={'CL':[],'CUDA':[]}
    for line in evaluated.read_text(encoding='utf-8-sig').splitlines():
        kind,p,excluded=line.split('|');b.need(kind in actual,'Unknown evaluated compile kind')
        if excluded.lower()!='true':actual[kind].append(Path(p).resolve())
    for kind,names in [('CL',ctx['cl_names']),('CUDA',ctx['cu_names'])]:
        b.need(len(actual[kind])==len(names) and {b.key(p) for p in actual[kind]}=={b.key(ctx['source']/x) for x in names}, 'Actual evaluated source scope differs: '+kind)
    objects=[b.stat(ctx['intdir']/x) for x in ctx['objects']]
    b.need({b.key(p) for p in ctx['intdir'].glob('*.obj')}=={b.key(e['path']) for e in objects},'Fresh object closure is not precisely111')
    logs={}
    for name in ctx['oldpaths']:
        found=list(ctx['intdir'].rglob(name));b.need(len(found)==1,'Actual tlog missing/ambiguous: '+name);logs[name]=found[0]
    current=cl_commands(logs['CL.command.1.tlog']);b.need(set(current)==set(ctx['oldcl']),'Actual CL97 closure differs')
    includes=set();deps=[]
    for leaf in ctx['cl_names']:
        key=leaf.casefold();old,olddep=normalize_cl(ctx['oldcl'][key]['flags']);new,newdep=normalize_cl(current[key]['flags'])
        dep=ctx['intdir']/(Path(leaf).stem+'.dependencies.json')
        b.need(b.key(current[key]['source'])==b.key(ctx['source']/leaf) and old==new and not olddep
               and len(newdep)==1 and b.key(newdep[0])==b.key(dep),'Original CL numerical flags/source/dependency changed: '+leaf)
        doc=b.read(dep)['Data'];b.need(b.key(doc['Source'])==b.key(ctx['source']/leaf),'Actual per-TU dependency source differs')
        includes.update(Path(x).resolve() for x in doc['Includes']);deps.append(b.stat(dep))
    nvcc=nvcc_commands(L/(TAG+'.msbuild.log'));b.need(set(nvcc)==set(ctx['oldcu']),'Actual14 NVCC closure differs')
    for leaf in ctx['cu_names']:
        key=leaf.casefold();old,_,_=normalize_nvcc(ctx['oldcu'][key]['flags']);new,obj,keep=normalize_nvcc(nvcc[key]['flags'])
        b.need(old==new and b.key(nvcc[key]['source'])==b.key(ctx['source']/leaf)
               and b.key(obj)==b.key(ctx['intdir']/ctx['oldcu'][key]['object']) and b.key(keep)==b.key(ctx['intdir']),
               'Original CUDA numerical/host flags, source or private object/keep path differs: '+leaf)
    cuda_blocks=blocks(logs['CudaCompile.read.1u.tlog'])
    b.need({Path(x).name.casefold() for x in cuda_blocks}==set(nvcc),'Actual14 CUDA dependency source blocks differ')
    for head,paths in cuda_blocks.items():
        b.need(b.key(head)==b.key(ctx['source']/Path(head).name),'CUDA dependency root is not private source')
        includes.update(paths)
    for p in includes:
        allowed={b.key(ctx['project']),b.key(extra)}
        b.need(not p.is_relative_to(R/'src/source') and (not p.is_relative_to(R) or p.is_relative_to(ctx['source']) or b.key(p) in allowed),
               'Compiler/CUDA dependency read live or unrelated repository source')
    b.need(all(ctx['source']/x in includes for x in HELPERS),'Actual compilers did not consume both private helpers')
    actual_libs={Path(x).resolve() for x in logs['link.read.1.tlog'].read_text(encoding='utf-16').splitlines() if not x.startswith('^') and x.lower().endswith('.lib')}
    expected={b.key(libdir/p.name if p in ctx['third'] else p) for p in ctx['libs']}
    b.need({b.key(p) for p in actual_libs}==expected,'Actual Release GPU link libraries differ from original private5/system21')
    # Link's genuine ^ header enumerates all objects; require precisely our fresh111.
    header,link_objects,link_flags=link_recipe(logs['link.command.1.tlog'])
    _,old_link_objects,old_link_flags=link_recipe(ctx['oldpaths']['link.command.1.tlog'])
    b.need({b.key(x) for x in header[1:].split('|')}=={b.key(e['path']) for e in objects}
           and len(link_objects)==111 and link_objects==old_link_objects and link_flags==old_link_flags,
           'Actual linker object closure/order or original non-path linker flags differ')
    runtimes=[]
    for e in ctx['runtime']:
        dest=ctx['outdir']/Path(e['path']).name;b.need(not dest.exists(),'Existing runtime destination protected')
        with dest.open('xb') as f:f.write(Path(e['path']).read_bytes())
        b.need(dest.read_bytes()==Path(e['path']).read_bytes(),'New runtime copy differs');runtimes.append(dict(source=e,destination=b.stat(dest)))
    program=ctx['outdir']/'DualSPHysics5.2_GEO_win64.exe'
    result.update(program=b.stat(program),runtime=runtimes,objects=objects,object_count=111,
                  CL_compile_count=97,CUDA_compile_count=14,old_objects_reused=0,
                  actual_CL_dependencies=deps,actual_dependency_stats=[b.stat(p) for p in sorted(includes,key=b.key)],
                  actual_tlogs={n:b.stat(p) for n,p in logs.items()},actual_NVCC_source_commands=nvcc,
                  actual_link_library_stats=[b.stat(p) for p in sorted(actual_libs,key=b.key)],
                  selected_toolchain={k:env.get(k) for k in ('VCTOOLSVERSION','WINDOWSSDKDIR','WINDOWSSDKVERSION','CUDA_PATH_V11_7')},
                  environment_batch=b.stat(batch),private_targets=b.stat(extra),evaluated_sources=b.stat(evaluated),binlog=b.stat(binlog),
                  project_library_copies=copies,numerical_CL_and_NVCC_flags_match_original=True,
                  internal_CL_NVCC_link_handles_claimed=False,
                  compiler_exit_scope='Actual owned MSBuild dual exits plus97 CL sourceDependencies/14 NVCC echoes+read tlog/link closure; no invented internal tool exits')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true')
    ap.add_argument('--admission',required=True,type=Path);args=ap.parse_args()
    b.need(args.execution_authorized,'Independent root full111 Release build-only authorization required')
    result=dict(stage=STAGE,configuration='Release',passed=False,calls=[],solver_invocations=0,program_help_invocations=0,
                native_invocations=0,VTK_invocations=0,SHA_scans=0,old_objects_reused=0,
                public_source_or_canonical_program_changed=False,historical_full_source_capture_claimed=False,
                physical_acceptance=False,following_action_launched=False)
    try:
        ad=Admission(args.admission);ctx=context(ad);result.update(root_admission=ad.entry,prepared=ad.pin(PREP),
            source_root=str(ctx['source_root']),private_IntDir=str(ctx['intdir']),private_output_root=str(OUT))
        build(ad,ctx,result);result.update(consumed=ad.finish(),consumed_stats_unchanged=True,passed=True)
    except Exception as exc:
        result.update(passed=False,failure=str(exc),partials_preserved=True)
    result['ended_utc']=b.now()
    result['actual_tool_call_receipts']=[b.stat(p) for p in (L/(TAG+'.environment.call.json'),L/(TAG+'.msbuild.call.json')) if p.exists()]
    if not CHECK.exists():b.write_new(CHECK,result)
    print(json.dumps(dict(passed=result['passed'],receipt=str(CHECK),failure=result.get('failure')),ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
