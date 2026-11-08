"""One private original-total-AS GPU CUDA TU/link per explicit configuration; no program run."""
import argparse,copy,difflib,os,re,shutil,subprocess,xml.etree.ElementTree as ET,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_asn4_zero_cpu_r2_build as base
from upl_c08_as_effective_gpu_r2_build import windows_args
T,L,S=base.T,base.L,base.S;TAG='upl_c08_darcy_eta0_gpu_r2';NOTE=T/'notes'/(TAG+'.md');CAP=T/'outputs'/(TAG+'_source');RUNTIME=T.parent/'support/runtime_r6';REFERENCE=T.parent/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml';CPU=L/'upl_c08_darcy_eta0_component_r1.check.json'
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
MEMBER='src/source/JSphGpu_ker.cu';ANCHOR=b'const double w=vol2*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr2+double(CTE.eta2));';REPLACEMENT=ANCHOR.replace(b'/(rr2+double(CTE.eta2));',b'/rr2;')

def baseline(conf):
 path=L/('upl_c08_bedkeep_'+conf+'_r1.build.json');b=read(path);need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==113,'Closed original macro-off bedkeep113 configuration required');return path,b
def cpu_gate():
 r=read(CPU);need(r['passed'] and r['actual_ct_calls']==2 and r['actual_Darcy_calls']==6 and r['actual_physical_updates']==0 and r['only_Darcy_Eta_temporarily_changed'] and r['upstream_all_native_fields_and_wall_roles_bits_unchanged_between_rates'] and r['restored_original_rate_all5000_bits_exact'] and r['consumed_stats_unchanged'],'Actual passed strong-state2ct/6Darcy CPU component required before GPU compilation');call=read(bind(r['actual_call'])['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual prerequisite CPU component typed exits differ');return [stat(CPU),bind(r['actual_call']),bind(r['component_completion']),bind(r['component_build']),bind(r['source_native'])]
def capture_source():
 # Called only by an explicitly authorized build, after the real CPU gate.
 db,d=baseline('Debug');rb,r=baseline('Release');need(d['source_capture']==r['source_capture'] and d['source_archive']==r['source_archive'],'Debug/Release original source archives differ');archive=Path(bind(r['source_archive'])['path']);p={q.get('key'):q.get('value') for q in ET.parse(REFERENCE).getroot().findall('execution/parameters/parameter')};need(all(float(p[k])==v for k,v in dict(ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=3,Kernel=1,DtFixed=.0000025).items()),'Original rootr6 input must remain total-AS/n3 reference')
 if CAP.exists():
  sc=read(CAP/'source.json');need(sc['baseline_capture']==r['source_capture'] and sc['baseline_archive']==r['source_archive'] and sc['reference_input']==stat(REFERENCE) and sc['Darcy_denominator']=='bare_r2' and sc['reverse_reconstruction_original_bytes_exact'] and sc['all_other_archive_members_byte_exact'],'Existing candidate capture differs');[bind(sc[k]) for k in ('private_gpu_source','archive','diff')];return sc
 with zipfile.ZipFile(archive) as z:
  original=z.read(MEMBER);need(original.count(ANCHOR)==1 and original.count(REPLACEMENT)==0,'Exactly one original complete Darcy w anchor required');modified=original.replace(ANCHOR,REPLACEMENT,1);need(modified.replace(REPLACEMENT,ANCHOR,1)==original,'One-line inverse reconstruction differs');single=z.read('src/source/JSphGpuSingle.cpp');need(b'SoilDamping=false;PoreShepardRegularization=false;ConstantDataUp();' in single,'Original release must disable both damping and Shepard')
  CAP.mkdir();cu=CAP/'JSphGpu_ker.cu';patch=CAP/'darcy_eta0.patch';outzip=CAP/'source.zip';cu.write_bytes(modified);patch.write_text(''.join(difflib.unified_diff(original.decode('utf-8-sig').splitlines(True),modified.decode('utf-8-sig').splitlines(True),fromfile=MEMBER,tofile=MEMBER)),encoding='utf-8')
  with zipfile.ZipFile(outzip,'x') as out:
   for info in z.infolist():
    q=PurePosixPath(info.filename);need(not q.is_absolute() and '..' not in q.parts,'Invalid source archive member');out.writestr(copy.copy(info),modified if info.filename==MEMBER else z.read(info))
  with zipfile.ZipFile(outzip) as out:need(z.namelist()==out.namelist() and all(out.read(name)==(modified if name==MEMBER else z.read(name)) for name in z.namelist()),'Candidate archive member closure differs')
 sc=dict(stage=TAG+'.source',prepared_only=True,private_gpu_source=stat(cu),archive=stat(outzip),diff=stat(patch),baseline_capture=r['source_capture'],baseline_archive=r['source_archive'],baseline_Debug_build=stat(db),baseline_Release_build=stat(rb),changed_archive_members=[MEMBER],exact_anchor_replacements=1,reverse_reconstruction_original_bytes_exact=True,all_other_archive_members_byte_exact=True,Darcy_denominator='bare_r2',LP_Lx_same_weight=True,Darcy_symC_unchanged=True,force_AV_Eta2_unchanged=True,var_k_chain_gp_divAce_unchanged=True,AS_stress_space='original_total',AS_parameters_set_by_input_not_build=True,reference_input=stat(REFERENCE),reference_AS_epsilon=.2,reference_AS_exponent=3,release_Shepard_OFF=True,release_damping_OFF=True,trace_macros_enabled=False,public_interfaces_changed=False,production_source_changed=False,complete_Lian_Eq23_Eq25_or_TPI_claimed=False,physical_jobs_authored=False,solver_invocations=0,native_decodes=0,SHA_scans=0);save(CAP/'source.json',sc);return sc

def build(conf):
 label='upl_c08_darcy_eta0_gpu_'+conf+'_r2';out=T/'outputs'/(label+'_build');check=L/(label+'.build.json');need(not out.exists() and not any((L/(label+q)).exists() for q in ('.build.json','.compile.call.json','.compile.log','.link.call.json','.link.log')),'Existing complete/partial candidate build protected');before=[];calls=[]
 try:
  before=cpu_gate();sc=capture_source();bp,b=baseline(conf);cu=Path(bind(sc['private_gpu_source'])['path']);archive=Path(bind(sc['archive'])['path']);need(sc['AS_stress_space']=='original_total' and sc['release_Shepard_OFF'] and sc['force_AV_Eta2_unchanged'] and not sc['trace_macros_enabled'],'Only original-total-AS Darcy denominator intervention allowed');program=out/Path(b['program']['path']).name
  objects=b['project_objects'];original=next(e for e in objects if Path(e['path']).name.lower()=='jsphgpu_ker.cu.obj');retained=[e for e in objects if e!=original];need(len(retained)==112 and sum(Path(e['path']).name.lower()=='main.obj' for e in retained)==1,'Exactly112 original objects including main required');actual=read(bind(b['actual_call'])['path']);log=Path(bind(actual['log'])['path']);intdir=Path(original['path']).parent;tlog=intdir/'DualSPHysics.tlog/link.command.1.tlog'
  raw=log.read_bytes().splitlines();lines=[v.split(b'>',1)[1].strip().decode('ascii') for v in raw if b'nvcc.exe' in v.lower() and b'jsphgpu_ker.cu' in v.lower()];need(len(lines)==1,'Exactly one actual ASCII project NVCC command required');ca=windows_args(lines[0]);nvcc=Path(ca.pop(0));inc=[a[2:] for a in ca if a.startswith('-I')];need(len(inc)==1 and Path(inc[0]).resolve()==(nvcc.parent.parent/'include').resolve() and '-I' not in ca and not any(a.startswith('--include-path') for a in ca),'Original explicit CUDA-only include closure differs');lines=tlog.read_text(encoding='utf-16').splitlines();need(sum(v.startswith('^') for v in lines)==1,'Exactly one original link-command block required');la=windows_args(' '.join(v for v in lines if v and not v.startswith('^')))
  runtime=[stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file() and (p.suffix.lower()=='.dll' or p.name=='DsphConfig.xml')];need(len(runtime)==7,'Exactly seven isolated runtime dependencies required');protected=[stat(S.parent/'bin/windows'/leaf) for leaf in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if (S.parent/'bin/windows'/leaf).exists()]+[stat(p) for p in RUNTIME.iterdir() if p.is_file()]
  before += [stat(p) for p in (Path(__file__),NOTE,Path(base.__file__),Path(base.old.__file__),T/'support/upl_c08_as_effective_gpu_r2_build.py',CAP/'source.json',REFERENCE,bp,log,tlog)]+[bind(sc[k]) for k in ('private_gpu_source','archive','diff')]+[bind(b[k]) for k in ('program','source_capture','source_archive','actual_call')]+[bind(e) for e in objects]+runtime+protected
  out.mkdir();frozen=out/'frozen/src/source';sources=[]
  with zipfile.ZipFile(archive) as z:
   need(z.read(MEMBER)==cu.read_bytes(),'Private CU differs from candidate ZIP')
   for info in z.infolist():
    p=PurePosixPath(info.filename);need(not p.is_absolute() and '..' not in p.parts,'Invalid frozen archive member')
    if not info.is_dir() and len(p.parts)>=3 and p.parts[:2]==('src','source'):
     need(p.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'Do not copy old binary/object artifacts');dest=out/'frozen'/Path(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);data=z.read(info)
     with dest.open('xb') as f:f.write(data)
     need(dest.read_bytes()==data,'Frozen compiler include closure differs');sources.append(stat(dest))
  need(all((frozen/q).is_file() for q in ('JSphGpu_ker.h','JSphGpu_mdbc_ker.cuh','JSphGpu_InOut_iker.cu','DualSphDef.h','FunSphKernel_iker.h')),'Complete frozen CUDA include closure missing');before+=sources
  pdb=0
  for i,arg in enumerate(ca):
   if i and ca[i-1]=='-Xcompiler':ca[i],count=re.subn(r'(?i)(?<!\S)/Fd[^\s]+','/Fdphysical.pdb',arg);pdb+=count
  need(pdb==1,'One original host PDB flag required');oldstyles=(str(intdir),str(intdir).replace('\\','/'))
  def rehome(value):
   for prefix in oldstyles:value=re.sub(re.escape(prefix),lambda _:str(out).replace('\\','/'),value,flags=re.I)
   return value
  ca=[str(cu) if Path(arg).name.lower()=='jsphgpu_ker.cu' else rehome(arg) for arg in ca];obj=out/'JSphGpu_ker.cu.obj';need(ca.count('-o')==ca.count('--keep-dir')==1,'Original output/scratch flags differ');ca[ca.index('-o')+1]=str(obj);ca[ca.index('--keep-dir')+1]=str(out);ca.insert(0,'-I'+str(frozen));hostflags='/Od' if conf=='Debug' else '/O2';crt='/MTd' if conf=='Debug' else '/MT'
  need(sum(Path(arg).name.lower()=='jsphgpu_ker.cu' for arg in ca)==1 and all(v in ca for v in ('--compile','--machine','64','-cudart','static','-use_fast_math','-D_WITHGPU')) and any('compute_86' in v and 'sm_86' in v for v in ca) and any(hostflags in v and crt in v for v in ca) and not any('C08_STAGE_TRACE' in v or 'C08_CAUSAL_TRACE' in v or v in ('--device-link','-dc') or 'rdc=true' in v for v in ca),'Original configuration/macro-off/sm86/non-RDC flags required')
  targets={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':out/(program.stem+'.iobj'),'/ilk:':out/(program.stem+'.ilk')};seen=set();linked=[]
  for arg in la:
   if arg.lower().endswith('.obj') and Path(arg).resolve()==Path(original['path']).resolve():arg=str(obj)
   for key,target in targets.items():
    if arg.lower().startswith(key):arg=key+str(target);seen.add(key);break
   linked.append(arg)
  linkobjs=[Path(arg).resolve() for arg in linked if arg.lower().endswith('.obj')];need('/out:' in seen and '/pdb:' in seen and len(linkobjs)==113 and set(linkobjs)=={Path(e['path']).resolve() for e in retained}|{obj.resolve()},'Actual link inputs must be112 retained plus exactly one candidate CUDA object')
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(v.split('=',1) for v in setup.stdout.decode('mbcs').splitlines() if '=' in v and not v.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC14.36 required')
  for key in list(env):
   if key.upper() in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
  need(ca.count('-ccbin')==1,'One original MSVC host directory required');link=Path(ca[ca.index('-ccbin')+1])/'link.exe';need('CUDA/v11.7' in str(nvcc).replace('\\','/') and '/14.36.32532/' in str(link).replace('\\','/'),'Original CUDA11.7/MSVC14.36 tools required');before += [stat(nvcc),stat(link)]
  libdirs=[S/'VS']+[Path(a.split(':',1)[1]) if Path(a.split(':',1)[1]).is_absolute() else S/'VS'/a.split(':',1)[1] for a in linked if a.lower().startswith('/libpath:')]+[Path(p) for p in env.get('LIB','').split(';') if p]
  for arg in linked:
   if arg.lower().endswith('.lib') and not arg.startswith('/'):
    candidates=[Path(arg)] if Path(arg).is_absolute() else [p/arg for p in libdirs];library=next((p for p in candidates if p.is_file()),None);need(library is not None,'Original explicit link library missing: '+arg);before.append(stat(library))
  need(all(stat(e['path'])==e for e in before),'Frozen source/object/runtime changed before compile');calls.append(invoke(label+'.compile',[str(nvcc),*ca],out,env));calls.append(invoke(label+'.link',[str(link),*linked],S/'VS',env));copied=[]
  for entry in runtime:
   dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing new runtime file protected');shutil.copy2(entry['path'],dest);e=stat(dest);need((e['bytes'],e['mtime_ns'])==(entry['bytes'],entry['mtime_ns']) and dest.read_bytes()==Path(entry['path']).read_bytes(),'Matched private runtime copy differs');copied.append(e)
  need(all(stat(e['path'])==e for e in before),'Original inputs/objects/runtime changed');save(check,dict(stage=label+'.build',passed=True,configuration=conf,program=stat(program),private_gpu_source=stat(cu),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),CPU_component=stat(CPU),baseline_source_build=stat(bp),baseline_source_capture=b['source_capture'],baseline_source_archive=b['source_archive'],original_physical_object=original,replacement_physical_object=stat(obj),physical_objects_recompiled=1,retained_physical_objects=112,actual_link_objects=113,actual_link_inputs=[str(p) for p in linkobjs],actual_NVCC_calls=1,compile_invocations=1,link_invocations=1,Darcy_denominator='bare_r2',AS_stress_space='original_total',reference_AS_epsilon=.2,reference_AS_exponent=3,AS_parameters_set_by_input_not_build=True,release_Shepard_OFF=True,trace_macros_enabled=False,force_AV_Eta2_unchanged=True,public_interfaces_changed=False,production_source_changed=False,complete_Lian_Eq23_Eq25_or_TPI_claimed=False,compiler_recipe='closed matching authoritative MSBuild NVCC log and link.command.1.tlog; output paths rehomed only',compiler_recipe_log=stat(log),link_recipe_tlog=stat(tlog),frozen_sources=sources,runtime=copied,calls=calls,consumed=before,consumed_stats_unchanged=True,full_project_builds=0,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0));print('DARCY_ETA0_PRIVATE_GPU_BUILD_PASSED',conf,program,flush=True)
 except Exception as error:
  if not check.exists():save(check,dict(stage=label+'.build',passed=False,configuration=conf,Darcy_denominator='bare_r2',first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',choices=('Debug','Release'),required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root full-read and actual CPU component pass');build(a.configuration)
