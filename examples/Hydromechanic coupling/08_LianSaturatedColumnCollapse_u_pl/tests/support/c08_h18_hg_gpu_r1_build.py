"""Private C08 energy-memory HG prepare/build only. Never run a program or reader."""
import argparse,datetime,difflib,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_shepard_release_r1_build as recipe
T,L,S=recipe.T,recipe.L,recipe.S
need,read,stat,bind,save,invoke=recipe.need,recipe.read,recipe.stat,recipe.bind,recipe.save,recipe.invoke
TAG='c08_h18_hg_gpu_r1';BUILD_TAG=TAG;CAP=T/'outputs'/(TAG+'_source');NOTE=T/'notes'/(TAG+'.md')
AUTHOR={'CUDA':T/'support'/(TAG+'.cu'),'header':T/'support'/(TAG+'.hpp')}
HOST=r'''
#include "c08_h18_hg_gpu_r1.hpp"
#include "JDsFixedDt.h"
#include <cstdlib>
#include <memory>
#include <stdexcept>
namespace {
  // Nonowning only: the Run-local scope destroys all CUDA resources before base reset.
  c08hg::State* C08HgState=NULL;
  struct C08HgRunScope{
    std::unique_ptr<c08hg::State> state;
    C08HgRunScope(){
      const char* e=std::getenv(c08hg::Environment());
      if(!e)return;
      if(std::string(e)!="1")throw std::runtime_error("Private C08 HG requires absent env or exact C08_HG_H18=1.");
      if(C08HgState)throw std::runtime_error("Private C08 HG does not allow nested/concurrent owners.");
      state.reset(new c08hg::State);C08HgState=state.get();
    }
    ~C08HgRunScope(){C08HgState=NULL;}
  };
}
'''
HOOK=r'''
  if(C08HgState){
    if(!GravityPreloadReleased || !GravityPreload || !IsGravityPreloadHandoff() || GravityPreloadElasticSource
      || GravityPreloadKeepBedOverlap || !GravityPreloadBedIds.empty() || GravityPreloadActualStep!=2000000
      || GravityPreloadIdBegin!=1805 || GravityPreloadIdCount!=255 || Np!=6805 || Npb!=1805 || NpbOk>Npb
      || CaseNp!=7060 || CaseNpb!=2060 || CaseNfixed!=2060 || CaseNfluid!=5000 || PartBegin
      || CaseNmoving || CaseNfloat || InOut || Symmetry || PeriActive || Shifting || Damping || RelaxZones || UseDEM || AccInput
      || !UseDynamicPorePlaneContact() || !NoPenetration || TMdbc2!=MDBC2_NoPen || TBoundary!=BC_MDBC || !UseNormals
      || !HydroMech || !HydroMechDynamicSeepage || !PorosityFeedback || !DynamicPorePressure || !DynamicPoreWall
      || !DynamicPoreConductivity || HydroMechConductivityModel!=1 || DynamicPoreConductivityCk!=2.
      || !Simulate2D || TKernel!=KERNEL_Wendland || TStep!=STEP_Symplectic || Dp!=.04 || KernelH!=.072f
      || !FixedDt || !FixedDt->GetFile().empty() || FixedDt->GetFixedValue()!=.000005 || SymplecticDtPre!=.000005
      || (interstep!=INTERSTEP_SymPredictor && interstep!=INTERSTEP_SymCorrector)
      || !PoroJg || !Aceg || HourglassGpu || SoilHourglassXi || SoilDamping || PoreShepardRegularization || SoilBoundaryDerivativeSPR
      || !ArtificialStress || ArtificialStressCoef!=.3f || ArtificialStressExp!=2.55f || TVisco!=VISCO_Artificial || Visco!=.1f || ViscoTime
      || TDensity!=DDT_None || !SoilStressRateGradCorr || !HydroMechFreeSeepage || HydroMechDrainage
      || HydroMechTopLoadMode!=HMLOAD_None || RhopZero!=2072.5f || SoilCte.PoreWaterRho!=1000.f
      || SoilCte.PoreWaterBulkModulus!=1e9f || SoilCte.Porosity!=.35f || SoilCte.HydraulicConductivity!=.0002f
      || SoilCte.ModulusE!=20e6f || SoilCte.PRvs!=.33f || DPCtes!=DP_PS || !StrainSoftening
      || SoilCte.dlt!=0.f || SoilCte.psiDecay!=0.f || SoilCte.coh!=5000.f || SoilCte.coh_r!=1000.f || SoilCte.n_coh!=5.f
      || SoilCte.n_phi!=0.f || SoilCte.phi!=SoilCte.phi_r || Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=-9.81f)
      Run_Exceptioon("Private H1.8 energy-normalized plastic HG requires unchanged schema2 psi0 Wendland/AS.3n2.55/5us/bedroles released target.");
    const bool corrector=(interstep==INTERSTEP_SymCorrector);
    if((corrector && (!SigmaPreg || !VelrhopPreg || !PoroJPreg)) || (!corrector && (SigmaPreg || PoroJPreg)))
      Run_Exceptioon("Private HG predictor/corrector base pointers do not match genuine stage.");
    const c08hg::Config hc={double(MassFluid)/double(RhopZero),double(RhopZero),double(SoilCte.PoreWaterRho),
      1.-double(SoilCte.Porosity),KernelH,CSP.kwend.bwen,SoilCte.ModulusG};
    const c08hg::Material hm={SoilCte,DPCtes,StrainSoftening,bool(PartBegin && StrainSoftening),RequireElasticGravityPreload()};
    const c08hg::Stage hs={Np,Npb,unsigned(Nstep),TimeStep,SymplecticDtPre,corrector,DivData,Dcellg,Idpg,Codeg,
      Posxyg,Poszg,Velrhopg,PoroJg,(corrector? SigmaPreg: Sigmag),Rsigmag,Kplasticg,Aceg};
    C08HgState->StageForce(hc,hm,hs);
  }
'''

def prerequisites():
    before=[]
    for name in ('c08_h18_hg_numeric_r1','c08_h18_plastic_hg_stage_r1'):
        p=L/(name+'.check.json');q=read(p);need(q['passed'] and not q['public_source_changed'] and not q['physical_acceptance'],'Passed closed CPU implementation evidence required')
        done=read(bind(q['completion'])['path']);call=read(bind(q['actual_call'])['path']);b=read(bind(q['build'])['path'])
        need(done['passed'] and b['passed'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual successful CPU build/call/completion required')
        if name.endswith('numeric_r1'):
            need(done['all_common_values_bit_equal'] and done['retained_actual_n0_force_scalar_bits']==20000 and done['local_unloading_value_and_branch_bits']==26 and done['quarter_turn_reference_checks']==4 and done['spin_sequences']==2 and done['spin_steps_per_sequence']==1024 and not done['coupled_large_rotation_qualified'],'Exact Audit/Fast/n0 and finite-spin implementation checks required')
        else:
            need(q['consumed_stats_unchanged'] and done['source_parts']==[38,76] and done['total_updates']==8 and done['material_sigma_kappa_scalar_bit_checks']==420000 and done['manual_OFF_CPU22_equivalent_field_checks']==220000,'Actual short-stage OFF/material proof required')
        before += [stat(p)]+[bind(q[k])for k in ('build','actual_call','completion')]
    return before

def prepare():
    check=L/(TAG+'.prepare.json');need(not CAP.exists() and not check.exists(),'Existing complete/partial private source preparation protected')
    before=prerequisites()+[stat(Path(__file__)),stat(NOTE)]+[stat(p)for p in AUTHOR.values()]
    db,debug,_=baseline('Debug');rb,release,_=baseline('Release')
    need(debug['source_archive']==release['source_archive'] and debug['source_capture']==release['source_capture'],'Same frozen schema2 Debug/Release original source required')
    before += [stat(db),stat(rb)]+[bind(debug[k])for k in ('source_archive','source_capture','actual_call','program')]+[bind(release[k])for k in ('actual_call','program')]
    archive=bind(debug['source_archive'])
    with zipfile.ZipFile(archive['path'])as z:original=z.read('src/source/JSphGpuSingle.cpp')
    nl=b'\r\n' if b'\r\n'in original else b'\n'
    def text(s):return s.replace('\r\n','\n').replace('\n',nl.decode()).encode('utf8')
    edits=[
      ('private API/nonowning Run scope',b'#include "JSphGpuSingle.h"'+nl,b'#include "JSphGpuSingle.h"'+nl+text(HOST)),
      ('Run resource lifetime',b'  AppName=appname; Log=log; CfgRun=cfg;',b'  AppName=appname; Log=log; CfgRun=cfg;'+text('\n  C08HgRunScope c08_hg_run_scope;')),
      ('same-stage force before sole original Darcy',b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);',text(HOOK)+b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);'),
      ('selected predictor fixed dt',b'  const double ddt_p=DtVariable(false);',b'  const double ddt_p=DtVariable(false);'+text('\n  if(C08HgState && ddt_p!=c08hg::StepDt)Run_Exceptioon("Private HG predictor actual selected dt differs from fixed 5us.");')),
      ('selected corrector fixed dt',b'  const double ddt_c=DtVariable(true);',b'  const double ddt_c=DtVariable(true);'+text('\n  if(C08HgState && ddt_c!=c08hg::StepDt)Run_Exceptioon("Private HG corrector actual selected dt differs from fixed 5us.");')),
      ('real predictor material check',b'  ComputeSymplecticPre(dt);',b'  ComputeSymplecticPre(dt);'+text('\n  if(C08HgState)C08HgState->CheckMaterial(Np,Npb,Idpg,Codeg,Sigmag,Kplasticg,false);')),
      ('real corrector material check',b'  ComputeSymplecticCorr(dt);',b'  ComputeSymplecticCorr(dt);'+text('\n  if(C08HgState)C08HgState->CheckMaterial(Np,Npb,Idpg,Codeg,Sigmag,Kplasticg,true);')),
      ('accepted full history after actual divide/scalar clock',b'    TimeStep+=stepdt;'+nl+b'    LastDt=stepdt;',b'    TimeStep+=stepdt;'+nl+b'    LastDt=stepdt;'+text('\n    if(C08HgState)C08HgState->Accept(Np,Npb,Idpg,Codeg,unsigned(Nstep+1),TimeStep,stepdt);')),
      ('sidecar only after actual native save',b'  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',b'  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);'+text('\n  if(C08HgState)C08HgState->Save(DirOut,unsigned(Nstep+1),TimeStep);'))]
    overlay=original;proof=[]
    for label,old,new in edits:
        need(overlay.count(old)==1,'Unique original anchor differs: '+label);overlay=overlay.replace(old,new,1)
        proof.append(dict(label=label,original_anchor=old.decode(),replacement=new.decode(),matches=1))
    inverse=overlay
    for label,old,new in reversed(edits):need(inverse.count(new)==1,'Reverse anchor differs: '+label);inverse=inverse.replace(new,old,1)
    need(inverse==original,'Unexpected edit outside exact host insertion anchors')
    need(all(stat(v['path'])==v for v in before),'Source/admission evidence changed before preparation')
    CAP.mkdir();sources={}
    for key,leaf,data in [('host','JSphGpuSingle.cpp',overlay)]+[(k,p.name,p.read_bytes())for k,p in AUTHOR.items()]:
        dest=CAP/leaf
        with dest.open('xb')as f:f.write(data)
        sources[key]=stat(dest)
    diff=CAP/'host.diff';diff.write_text(''.join(difflib.unified_diff(original.decode().splitlines(True),overlay.decode().splitlines(True),fromfile='schema2/JSphGpuSingle.cpp',tofile='private/JSphGpuSingle.cpp')),encoding='utf8')
    need(all(stat(v['path'])==v for v in before),'Source/admission evidence changed during preparation')
    capture=CAP/'source.json';save(capture,dict(stage=TAG+'.source',passed=True,prepared_only=True,operator='EnergyNormalizedAdjointLoadingOnly',policy_schema=1,default_OFF_env_absent=True,explicit_ON_env='C08_HG_H18=1',xi=.1,source_archive=archive,baseline_source_capture=debug['source_capture'],private_sources=sources,host_diff=stat(diff),exact_reverse_original_host_bytes=True,exact_insertions=proof,original_CUDA_members_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,physical_objects_retained=112,private_objects_required=2,actual_link_objects_required=114,neighbor_capacity=128,physical_acceptance=False))
    save(check,dict(stage=TAG+'.prepare',passed=True,source_capture=stat(capture),source_archive=archive,private_sources=sources,consumed=before,consumed_stats_unchanged=True,prepared_only=True,build_invocations=0,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
    print('C08_H18_HG_PRIVATE_SOURCE_PREPARED',capture,flush=True)

def baseline(conf):
    p=L/('c08_preload_schema2_'+conf+'_r1.build.json');b=read(p)
    need(b['passed'] and b['configuration']==conf and b['consumed_stats_unchanged'],'Successful unchanged schema2 baseline required')
    a=read(bind(b['actual_call'])['path'])
    need(a['actual_Popen_wait_exit']==a['actual_Win32_exit']==0 and a['ownership_failure'] is None,'Actual original MSBuild handles/exit required')
    need(any('/p:Configuration='+conf==v for v in a['arguments']) and any('/p:VCToolsVersion=14.36.32532'==v for v in a['arguments']),'Original authoritative solution/config/toolset required')
    return p,b,a

def build(conf):
    label='c08_h18_hg_gpu_'+conf+'_r1';out=T/'outputs'/label;intdir=Path(os.environ['TEMP'])/BUILD_TAG/conf
    check=L/(label+'.build.json');calls=[];before=[]
    need(' ' not in str(intdir.resolve()) and not out.exists() and not intdir.exists() and all(not(L/(label+s)).exists() for s in ('.build.json','.host_compile.call.json','.host_compile.log','.cuda_compile.call.json','.cuda_compile.log','.link.call.json','.link.log')),'Fresh isolated outputs/receipts/no-space IntDir required')
    try:
        bp,b,a=baseline(conf);db,d,_=baseline('Debug');rb,r,_=baseline('Release');sc=read(CAP/'source.json')
        need(sc['passed'] and sc['prepared_only'] and sc['exact_reverse_original_host_bytes'] and sc['original_CUDA_members_unchanged'] and not sc['public_source_changed'] and not sc['class_or_CTE_layout_changed'],'Reviewed reversible private preparation required')
        need(sc['default_OFF_env_absent'] and sc['explicit_ON_env']=='C08_HG_H18=1' and sc['xi']==.1 and sc['policy_schema']==1 and sc['operator']=='EnergyNormalizedAdjointLoadingOnly' and sc['physical_objects_retained']==112 and sc['private_objects_required']==2 and sc['actual_link_objects_required']==114,'Exact private HG scope/object count required')
        need(d['source_archive']==r['source_archive']==sc['source_archive'] and d['source_capture']==r['source_capture']==sc['baseline_source_capture'],'Same original schema2 archive/capture required')
        prep=L/(TAG+'.prepare.json');pr=read(prep);need(pr['passed'] and pr['consumed_stats_unchanged'] and pr['source_capture']==stat(CAP/'source.json'),'Successful actual source preparation required')
        sources={k:Path(bind(sc['private_sources'][k])['path']) for k in ('host','CUDA','header')};archive=Path(bind(sc['source_archive'])['path'])
        oldint=Path(b['intermediate']);ctlog=oldint/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog')
        lines=ctlog.read_text(encoding='utf-16').splitlines();at=[i for i,x in enumerate(lines) if x.startswith('^') and Path(x[1:]).name.lower()=='jsphgpusingle.cpp']
        need(len(at)==1,'One authoritative original host CL block required');clargs=recipe.windows_args(lines[at[0]+1])
        ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(x.startswith('^') for x in ll)==1,'One original link block required');linkargs=recipe.windows_args(' '.join(x for x in ll if x and not x.startswith('^')))
        # This is an honest NEW inventory, not a historical object seal from the old receipt.
        objects=[stat(p) for p in sorted(oldint.rglob('*.obj'))];linked_original=[Path(x).resolve() for x in linkargs if x.lower().endswith('.obj')]
        start=datetime.datetime.fromisoformat(a['started_utc']).timestamp();end=datetime.datetime.fromisoformat(a['ended_utc']).timestamp()
        need(len(objects)==113 and len(linked_original)==113 and len(set(linked_original))==113 and set(linked_original)=={Path(v['path']).resolve() for v in objects},'Fresh113-object inventory must match actual link membership exactly')
        need(all(start<=v['mtime_ns']/1e9<=end for v in objects),'Original object mtime outside genuine original MSBuild call')
        removed=[v for v in objects if Path(v['path']).name.lower()=='jsphgpusingle.obj'];retained=[v for v in objects if v not in removed]
        need(len(removed)==1 and len(retained)==112 and sum(Path(v['path']).name.lower()=='main.obj' for v in retained)==sum(Path(v['path']).name.lower()=='jsphgpu_ker.cu.obj' for v in retained)==1,'Retain112 including original main and physical CUDA object')
        log=Path(bind(a['log'])['path']);nv=[x.split(b'>',1)[-1].strip().decode('ascii') for x in log.read_bytes().splitlines() if b'nvcc.exe' in x.lower() and b'jsphgpu_ker.cu' in x.lower()]
        need(len(nv)==1,'One actual NVCC command required');cuargs=recipe.windows_args(nv[0]);nvcc=Path(cuargs.pop(0));incs=[x[2:] for x in cuargs if x.startswith('-I')]
        need(len(incs)==1 and Path(incs[0]).resolve()==(nvcc.parent.parent/'include').resolve() and '-I' not in cuargs and not any(x.startswith('--include-path') for x in cuargs),'Original CUDA include recipe changed')
        runtime=[bind(v['destination']) for v in b['runtime']];need(len(runtime)==9 and len({Path(v['path']).name.lower() for v in runtime})==9,'Actual original nine-file runtime required')
        pre=T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
        protected=[stat(pre)]+[stat(q) for name in ('runtime_r5','runtime_r6') for q in (T.parent/'support'/name).iterdir() if q.is_file()]
        protected += [stat(S.parent/'bin/windows'/n) for n in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if(S.parent/'bin/windows'/n).exists()]
        before=prerequisites()+[stat(q) for q in (Path(__file__),NOTE,Path(recipe.__file__),Path(recipe.e.__file__),bp,db,rb,ctlog,ltlog,log,CAP/'source.json',prep)]+[bind(sc['host_diff'])]+[stat(q)for q in sources.values()]+[bind(b[k])for k in ('actual_call','source_capture','source_archive')]+[bind(d['program']),bind(r['program'])]+objects+runtime+protected
        out.mkdir();intdir.mkdir(parents=True);frozen=out/'frozen/src/source';frozen_entries=[]
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                q=PurePosixPath(info.filename);need(not q.is_absolute() and '..' not in q.parts,'Unsafe source archive path')
                if not info.is_dir() and len(q.parts)>=3 and q.parts[:2]==('src','source'):
                    need(q.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'Binary in source archive')
                    dest=out/'frozen'/Path(*q.parts);dest.parent.mkdir(parents=True,exist_ok=True)
                    data=sources['host'].read_bytes() if q.as_posix()=='src/source/JSphGpuSingle.cpp' else z.read(info)
                    with dest.open('xb')as f:f.write(data)
                    frozen_entries.append(stat(dest))
            need((frozen/'JSphGpu_ker.cu').read_bytes()==z.read('src/source/JSphGpu_ker.cu'),'Original physical CUDA source must remain unmodified')
        for k in ('CUDA','header'):
            dest=frozen/sources[k].name
            with dest.open('xb')as f:f.write(sources[k].read_bytes())
            frozen_entries.append(stat(dest))
        need(all((frozen/n).is_file() for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h','FunctionsBasic_iker.h','FunSphKernel_iker.h','JCellSearch_iker.h')),'Complete actual private header closure required');before+=frozen_entries
        hostobj=intdir/'JSphGpuSingle.obj';cudaobj=intdir/'c08_h18_hg_gpu_r1.cu.obj';program=out/Path(b['program']['path']).name
        need(sum(x.lower().startswith('/fo') for x in clargs)==sum(x.lower().startswith('/fd') for x in clargs)==sum(x.lower().endswith('jsphgpusingle.cpp') for x in clargs)==1 and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in clargs),'Original single-source non-PCH/non-GL host recipe required')
        clargs=['/I'+str(frozen),*['/Fo'+str(hostobj) if x.lower().startswith('/fo') else '/Fd'+str(intdir/'host.pdb') if x.lower().startswith('/fd') else str(frozen/'JSphGpuSingle.cpp') if x.lower().endswith('jsphgpusingle.cpp') else x for x in clargs],'/sourceDependencies',str(intdir/'host.dependencies.json')]
        nfd=0
        for i,x in enumerate(cuargs):
            if i and cuargs[i-1]=='-Xcompiler':cuargs[i],n=re.subn(r'(?i)(?<!\S)/Fd[^\s]+',lambda m:'/Fd'+str(intdir/'cuda.pdb'),x);nfd+=n
        need(nfd==1 and cuargs.count('-o')==cuargs.count('--keep-dir')==1 and sum(Path(x).name.lower()=='jsphgpu_ker.cu' for x in cuargs)==1,'One actual NVCC source/object/PDB/keep directory required')
        cuargs=[str(frozen/sources['CUDA'].name) if Path(x).name.lower()=='jsphgpu_ker.cu' else x for x in cuargs];cuargs[cuargs.index('-o')+1]=str(cudaobj);cuargs[cuargs.index('--keep-dir')+1]=str(intdir);cuargs=['-I'+str(frozen),*cuargs]
        need(not any('C08_HG_DEBUG_SNAPSHOT' in x for x in cuargs),'Unexpected inherited snapshot macro')
        if conf=='Debug':cuargs.append('-DC08_HG_DEBUG_SNAPSHOT')
        opt='/Od' if conf=='Debug' else '/O2';crt='/MTd' if conf=='Debug' else '/MT'
        need(all(x in clargs for x in (opt,crt,'/fp:precise','/openmp')) and all(x in cuargs for x in ('--compile','-use_fast_math','-D_WITHGPU')) and any('compute_86' in x and 'sm_86' in x for x in cuargs) and any(opt in x and crt in x for x in cuargs) and not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x or 'rdc=true' in x or x in ('--device-link','-dc') for x in (*clargs,*cuargs)),'Original config/CRT/sm86/non-RDC flags required with no observer macros')
        targets={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':intdir/(program.stem+'.iobj'),'/ilk:':out/(program.stem+'.ilk'),'/map:':out/(program.stem+'.map'),'/manifestfile:':intdir/'program.manifest','/pgd:':intdir/'program.pgd','/tlbout:':intdir/'program.tlb','/winmdfile:':intdir/'program.winmd'};seen={};linked=[]
        for arg in linkargs:
            if arg.lower().endswith('.obj') and Path(arg).resolve()==Path(removed[0]['path']).resolve():arg=str(hostobj)
            for key,target in targets.items():
                if arg.lower().startswith(key):need(key not in seen,'Duplicate link output switch');seen[key]=str(target);arg=key+str(target);break
            linked.append(arg)
        linked.append(str(cudaobj));actual=[Path(x).resolve()for x in linked if x.lower().endswith('.obj')]
        need(all(k in seen for k in ('/out:','/pdb:','/implib:','/ltcgout:')) and len(actual)==len(set(actual))==114 and set(actual)=={Path(v['path']).resolve()for v in retained}|{hostobj.resolve(),cudaobj.resolve()},'Exactly112 retained+two private objects and fully rehomed link outputs required')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed')
        env={k.upper():v for k,v in os.environ.items()};env.update((k.upper(),v)for k,v in (x.split('=',1)for x in setup.stdout.decode('mbcs').splitlines()if '=' in x and not x.startswith('=')));need(env['VCTOOLSVERSION']=='14.36.32532','Actual original MSVC14.36 required')
        for key in list(env):
            if key.upper()in ('CL','_CL_','NVCC_PREPEND_FLAGS','NVCC_APPEND_FLAGS'):env.pop(key)
        cl=Path(env['VCTOOLSINSTALLDIR'])/'bin/Hostx64/x64/cl.exe';link=cl.with_name('link.exe')
        need('CUDA/v11.7' in str(nvcc).replace('\\','/') and cuargs.count('-ccbin')==1 and '14.36.32532' in cuargs[cuargs.index('-ccbin')+1] and Path(cuargs[cuargs.index('-ccbin')+1]).is_dir(),'Authoritative CUDA11.7/MSVC14.36 ccbin required');before += [stat(cl),stat(nvcc),stat(link)]
        libdirs=[S/'VS']+[Path(x.split(':',1)[1]) if Path(x.split(':',1)[1]).is_absolute()else S/'VS'/x.split(':',1)[1]for x in linked if x.lower().startswith('/libpath:')]+[Path(x)for x in env.get('LIB','').split(';')if x]
        for arg in linked:
            if arg.lower().endswith('.lib')and not arg.startswith('/'):
                candidates=[Path(arg)]if Path(arg).is_absolute()else[p/arg for p in libdirs];lib=next((q for q in candidates if q.is_file()),None);need(lib is not None,'Actual original library missing: '+arg);before.append(stat(lib))
        need(all(stat(v['path'])==v for v in before),'Frozen inputs changed before compilation')
        cudaenv=dict(env);cuda_path=env.get('Path',env.get('PATH',''))
        for key in list(cudaenv):
            if key.upper()=='PATH':cudaenv.pop(key)
        cudaenv['PATH']=str(Path(cuargs[cuargs.index('-ccbin')+1]))+os.pathsep+cuda_path
        calls.append(invoke(label+'.host_compile',[str(cl),*clargs],intdir,env));calls.append(invoke(label+'.cuda_compile',[str(nvcc),*cuargs],intdir,cudaenv));calls.append(invoke(label+'.link',[str(link),*linked],S/'VS',env))
        deps=read(intdir/'host.dependencies.json');includes={Path(x).resolve()for x in deps['Data']['Includes']};need(all((frozen/n).resolve()in includes for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h',sources['header'].name)),'Host used another class/header ABI')
        copied=[]
        for entry in runtime:
            dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing private runtime protected');shutil.copy2(entry['path'],dest);v=stat(dest);need((v['bytes'],v['mtime_ns'])==(entry['bytes'],entry['mtime_ns'])and dest.read_bytes()==Path(entry['path']).read_bytes(),'Private runtime copy differs');copied.append(v)
        need(all(stat(v['path'])==v for v in before),'Original object/source/program/PRE/runtime changed during build')
        warning_lines=[line for q in calls for line in Path(read(q['path'])['log']['path']).read_bytes().decode('mbcs').splitlines()if re.search(r'\bwarning\b',line,re.I)]
        save(check,dict(stage=label+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),baseline_source_capture=b['source_capture'],private_sources={k:stat(v)for k,v in sources.items()},baseline_source_build=stat(bp),original_actual_build_call=b['actual_call'],original_build_started_utc=a['started_utc'],original_build_ended_utc=a['ended_utc'],original_objects_historical_seal_claimed=False,fresh_original_objects=objects,original113_mtimes_within_actual_build=True,original_link_membership_exact=True,retained_original_objects=112,private_objects=2,actual_link_objects=114,retained_object_stats=retained,new_private_objects=[stat(hostobj),stat(cudaobj)],actual_link_inputs=[str(q)for q in actual],original_host_recipe=stat(ctlog),original_CUDA_recipe_log=stat(log),original_link_recipe=stat(ltlog),link_output_flags=seen,private_header_dependencies=stat(intdir/'host.dependencies.json'),frozen_sources=frozen_entries,IntDir=str(intdir),OutDir=str(out),runtime=copied,calls=calls,warning_lines=warning_lines,new_warning_free_claimed=False,consumed=before,consumed_stats_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,original_physical_CUDA_objects_retained=True,ON_runtime_env='C08_HG_H18=1',OFF_env_absent_no_HG_allocation_launch_sidecar=True,operator='EnergyNormalizedAdjointLoadingOnly',xi=.1,neighbor_capacity=128,policy_schema=1,new_GPU_material_bit_equivalence_qualified=False,coupled_energy_qualified=False,Debug_first_n_snapshot_macro_enabled=(conf=='Debug'),private_observer_only_flag=('-DC08_HG_DEBUG_SNAPSHOT'if conf=='Debug'else None),compile_invocations=2,link_invocations=1,full_project_builds=0,solver_invocations=0,help_invocations=0,memcheck_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        print('C08_H18_HG_PRIVATE_BUILD_PASSED',conf,program,flush=True)
    except Exception as error:
        if not check.exists():save(check,dict(stage=label+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--configuration',choices=('Debug','Release'));p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized and (a.prepare != bool(a.configuration)),'Independent root admission and exactly one prepare/configuration operation required')
    if a.prepare:prepare()
    else:build(a.configuration)
