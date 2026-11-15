"""Prepare/build only the closed cached-HG scheduling optimization; never runs a program."""
import argparse,datetime,difflib,os,re,shutil,subprocess,zipfile
from pathlib import Path,PurePosixPath
import upl_c08_shepard_release_r1_build as recipe
T,L,S=recipe.T,recipe.L,recipe.S
need,read,stat,bind,save,invoke=recipe.need,recipe.read,recipe.stat,recipe.bind,recipe.save,recipe.invoke
TAG='c08_h18_hg_opt_r1';BUILD_TAG=TAG;CAP=T/'outputs'/(TAG+'_source');NOTE=T/'notes'/(TAG+'.md')
AUTHOR={'CUDA':T/'support'/(TAG+'.cu'),'header':T/'support'/(TAG+'.hpp')}
HOST=r'''
#include "c08_h18_hg_opt_r1.hpp"
#include "JDsFixedDt.h"
#include <cstdlib>
#include <memory>
#include <stdexcept>
namespace {
  struct C08OptRunScope{
    std::unique_ptr<c08cached::State> state;
    C08OptRunScope(){
      const char* e=std::getenv(c08cached::Environment());if(!e)return;
      if(std::string(e)!="1")throw std::runtime_error("Private cached HG requires absent env or exact C08_HG_OPT_H18=1.");
      state.reset(new c08cached::State);c08cached::SetCurrent(state.get());
    }
    ~C08OptRunScope(){if(state)c08cached::SetCurrent(NULL);}
  };
}
'''
HOOK=r'''
  if(c08cached::Current()){
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
    const c08cached::Config hc={double(MassFluid)/double(RhopZero),double(RhopZero),double(SoilCte.PoreWaterRho),
      1.-double(SoilCte.Porosity),KernelH,CSP.kwend.bwen,SoilCte.ModulusG};
    const c08cached::Material hm={SoilCte,DPCtes,StrainSoftening,bool(PartBegin && StrainSoftening),RequireElasticGravityPreload()};
    const c08cached::Stage hs={Np,Npb,unsigned(Nstep),TimeStep,SymplecticDtPre,corrector,DivData,Dcellg,Idpg,Codeg,
      Posxyg,Poszg,Velrhopg,PoroJg,(corrector? SigmaPreg: Sigmag),Rsigmag,Kplasticg,Aceg};
    c08cached::Current()->StageForce(hc,hm,hs);
  }
'''

def replace_once(text,old,new,proof,label):
    need(text.count(old)==1,'Unique reversible source anchor differs: '+label)
    proof.append(dict(label=label,old=old,new=new,count=1));return text.replace(old,new,1)

def function(text,anchor):
    need(text.count(anchor)==1,'Unique complete function anchor required')
    start=text.index(anchor);at=text.index('{',start);depth=0;mode='code';q='';i=at
    while i<len(text):
        c=text[i];n=text[i+1]if i+1<len(text)else''
        if mode=='line':
            if c=='\n':mode='code'
        elif mode=='block':
            if c=='*'and n=='/':mode='code';i+=1
        elif mode=='quote':
            if c=='\\':i+=1
            elif c==q:mode='code'
        elif c=='/'and n=='/':mode='line';i+=1
        elif c=='/'and n=='*':mode='block';i+=1
        elif c in ('"',"'"):mode='quote';q=c
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if not depth:return text[start:i+1]
        i+=1
    raise RuntimeError('Unclosed original source function')

def reverse(changed,proof,original):
    for q in reversed(proof):
        need(changed.count(q['new'])==1,'Ambiguous reverse source anchor: '+q['label']);changed=changed.replace(q['new'],q['old'],1)
    need(changed.encode()==original.encode(),'Source reverse did not restore every original byte')

def integrators(original):
    nl='\r\n'if'\r\n'in original else'\n'
    pieces=[];allproof=[]
    helper=function(original,'template<bool corrector> static __device__ __forceinline__ bool KerPorosityRhopCache')
    hp=[];h=replace_once(helper,'KerPorosityRhopCache','CachedPorosityRhopCache',hp,'helper private name')
    h=replace_once(h,'float &cache)','float &cache,const StSoilCte& cached_soil)',hp,'explicit soil helper argument')
    h=replace_once(h,'SOILSCTE.PoreWaterRho','cached_soil.PoreWaterRho',hp,'same water density member')
    h=replace_once(h,'SOILSCTE.Porosity','cached_soil.Porosity',hp,'same porosity member');reverse(h,hp,helper);pieces.append(h);allproof.append(dict(role='porosity',original=helper,changes=hp))
    for phase in ('Pre','Cor'):
        part=function(original,'template<bool floating,bool shift,bool inout,TpDPCtes dpctes> __global__ void KerComputeStepSymplectic'+phase)
        proof=[];p=replace_once(part,'KerComputeStepSymplectic'+phase,'CachedSymplectic'+phase,proof,'private '+phase+' kernel name')
        p=replace_once(p,'bool requireelastic)','bool requireelastic,CacheView cache,unsigned source_step,double source_time,const unsigned* native_id,StSoilCte cached_soil)',proof,'cache identity and explicit soil kernel inputs')
        width='dtm'if phase=='Pre'else'dt';flag='false'if phase=='Pre'else'true'
        old='KerPorosityRhopCache<'+flag+'>(porostate,p,'+width+',rhopzero,rhopoutmin,rhopoutmax,rvelrhopnew.w)'
        new='CachedPorosityRhopCache<'+flag+'>(porostate,p,'+width+',rhopzero,rhopoutmin,rhopoutmax,rvelrhopnew.w,cached_soil)'
        p=replace_once(p,old,new,proof,'same '+phase+' mixture-density cache formula')
        start=p.index('double2 sigma_e_xx_xy=make_double2(0,0);');start=p.rfind(nl,0,start)+len(nl)
        if phase=='Pre':
            end=p.index('kplasticnew=kplasticold;//Update in the corrector step');end=p.rfind(nl,0,end)+len(nl)
        else:
            end=p.index('//-Restore data of inout particles.');end=p.rfind(nl,0,end)+len(nl)
        block=p[start:end]
        need(block.count('fsoil::ReturnMaterial(')==1 and block.count('fsoil::CommitAllowed(')==1,'Exactly one original return/commit block required')
        call=('        float kplasticold=kplasticpre[p];'+nl+
              '        if(!ReadCachedMaterial(cache,p,native_id[p],source_step,source_time,'+width+','+flag+','+nl+
              '          sigmapre_xx_xy,sigmapre_xz_yy,sigmapre_yz_zz,rsigma_xx_xy,rsigma_xz_yy,rsigma_yz_zz,kplasticold,'+nl+
              '          sigmanew_xx_xy,sigmanew_xz_yy,sigmanew_yz_zz,kplasticnew,materialerror,requireelastic))return;'+nl)
        p=replace_once(p,block,call,proof,'one producer cache replaces '+phase+' material solve only')
        reverse(p,proof,part)
        need('fsoil::ReturnMaterial('not in p and' fsoil::EvaluateMaterial('not in p and'SOILSCTE'not in p,'Consumer must not return material again or access external constants')
        if phase=='Pre':need('kplasticnew=kplasticold;//Update in the corrector step'in p,'Original predictor old-kappa policy missing')
        else:need('if(kplasticdk)kplasticdk[p]+=fmaxf(kplasticnew-kplasticpre[p],0.f);'in p,'Original full kappa increment expression changed')
        pieces.append(p);allproof.append(dict(role=phase,original=part,changes=proof))
    return 'using cusphs::StPorosityRhopState;'+nl+nl+(nl+nl).join(pieces)+nl,allproof


def optimization_derivation():
    """Read-only proof of scheduling-only changes against the actual cached source."""
    base=T/'outputs/c08_h18_hg_cached_r1_source/source.json';sc=read(base);before=[stat(base)]
    need(sc['passed'] and sc['exact_reverse_original_hosts_bytes'] and sc['exact_reverse_original_integrators_bytes']
         and sc['physical_objects_retained']==111 and sc['private_objects_required']==3
         and sc['actual_link_objects_required']==114,'Passed frozen cached source package required')
    for conf in ('Debug','Release'):
        p=L/('c08_h18_hg_cached_'+conf+'_r1.build.json');b=read(p)
        need(b['passed'] and b['consumed_stats_unchanged'] and b['source_capture']==stat(base)
             and b['retained_original_objects']==111 and b['private_objects']==3 and b['actual_link_objects']==114,
             'Actual cached build closure required')
        before += [stat(p),bind(b['program']),bind(b['source_capture'])]
    runpath=L/'c08_h18_hg_cached_window_GPU_r1.run.json';q=read(runpath)
    need(q['passed'] and q['solver_completed'] and q['consumed_stats_unchanged']
         and q['actual_steps']==2180000 and q['saved_frames']==91 and q['source_capture']==stat(base)
         and q['actual_exit']==q['actual_Win32_exit']==q['actual_tool_exit']==q['actual_tool_Win32_exit']==0,
         'Genuine retained cached window required, not physical acceptance')
    phasepath=L/'c08_h18_hg_cached_phase_review_r1.check.json';phase=read(phasepath)
    need(phase['passed'] and phase['analysis_complete'] and phase['consumed_stats_unchanged']
         and phase['source_run']==stat(runpath) and phase['reviewed_rows']==182
         and phase['Eold_bit_equal_pairs']==91 and phase['final_commits']==180000,
         'Retained saved-phase implementation review required')
    before += [stat(runpath),bind(q['actual_call']),stat(phasepath)]
    before += [bind(sc['private_sources'][k])for k in ('CUDA','header')]
    before += [stat(T/'support/c08_h18_hg_cached_r1_build.py')]
    oldcu=Path(sc['private_sources']['CUDA']['path']).read_bytes().decode()
    oldh=Path(sc['private_sources']['header']['path']).read_bytes().decode()
    changes=[]
    def edit(src,old,new,label,kernel=None,count=1):
        part=function(src,'__global__ void '+kernel+'(')if kernel else src
        need(part.count(old)==count,'Exact optimizer anchor count differs: '+label)
        changed=part.replace(old,new)
        changes.append(dict(label=label,kernel=kernel,old=old,new=new,count=count))
        return src.replace(part,changed,1)if kernel else changed
    cu=edit(oldcu,'c08_h18_hg_cached_r1','c08_h18_hg_opt_r1','CUDA family include labels',count=oldcu.count('c08_h18_hg_cached_r1'))
    cu=edit(cu,'C08CachedPlasticHG','C08OptPlasticHG','exclusive sidecar/debug basenames',count=cu.count('C08CachedPlasticHG'))
    cu=edit(cu,'PrivateC08SingleProducerCachedPlasticHG','PrivateC08SingleProducerOptPlasticHG','exclusive policy identity')
    kernels=('CheckConsumedKernel','NeighborKernel','FitKernel','RowKernel','AdjointFitKernel','AdjointRowKernel','ForceKernel','AceUnchangedKernel','CheckCommitKernel')
    for name in kernels:
        pointer='cache.failure'if name=='CheckConsumedKernel'else'fail'
        old='  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||atomicAdd(&'+pointer+'->bits,0u))return;'
        new=('  __shared__ unsigned c08_opt_block_error;\n'
             '  if(threadIdx.x==0)c08_opt_block_error=atomicAdd(&'+pointer+'->bits,0u);\n'
             '  __syncthreads();\n'
             '  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=Nodes||c08_opt_block_error)return;')
        cu=edit(cu,old,new,'one shared error snapshot before every return',kernel=name)
    old=('  AceUnchangedKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,s.ace,p.failure);Cuda(cudaGetLastError(),"precommit Ace check launch");p.ErrorNow();\n'
         '  CommitAceKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,s.ace);Cuda(cudaGetLastError(),"single Ace commit launch");')
    new='  CommitAceKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,s.ace);Cuda(cudaGetLastError(),"single Ace commit launch");'
    cu=edit(cu,old,new,'remove old late Ace observation; preserve single commit')
    old='  LocalSummaryKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,p.graph,p.memory,p.failure,p.partial_summary);Cuda(cudaGetLastError(),"bounded receiver summary launch");'
    new=('  AceUnchangedKernel<<<(Nodes+Block-1)/Block,Block>>>(p.node,s.ace,p.failure);Cuda(cudaGetLastError(),"precommit Ace check launch");\n'+old)
    cu=edit(cu,old,new,'Ace observation before readonly summaries')
    old='  Cuda(cudaMemcpy(&p.latest,p.device_summary,sizeof(Summary),cudaMemcpyDeviceToHost),"small summary download");p.ErrorNow();'
    new='  Cuda(cudaMemcpy(&p.latest,p.device_summary,sizeof(Summary),cudaMemcpyDeviceToHost),"small summary download");if(p.latest.error)p.ErrorNow();'
    cu=edit(cu,old,new,'reuse summary error normal path; full first cause still fetched on failure')
    rewound=cu
    for change in reversed(changes):
        part=function(rewound,'__global__ void '+change['kernel']+'(')if change['kernel']else rewound
        need(part.count(change['new'])==change['count'],'Optimizer reverse anchor differs')
        restored=part.replace(change['new'],change['old'])
        rewound=rewound.replace(part,restored,1)if change['kernel']else restored
    need(rewound.encode()==oldcu.encode(),'Optimizer reverse does not recover complete cached CUDA bytes')
    h=oldh.replace('C08_H18_HG_CACHED_R1_HPP','C08_H18_HG_OPT_R1_HPP').replace('C08_HG_CACHED_H18','C08_HG_OPT_H18')
    need(h.replace('C08_H18_HG_OPT_R1_HPP','C08_H18_HG_CACHED_R1_HPP').replace('C08_HG_OPT_H18','C08_HG_CACHED_H18').encode()==oldh.encode(),
         'Header reverse differs')
    need(cu.encode()==AUTHOR['CUDA'].read_bytes() and h.encode()==AUTHOR['header'].read_bytes(),
         'Author CUDA/header contain changes outside the closed scheduling derivation')
    need(function(cu,'__global__ void NodeKernel(')==function(oldcu,'__global__ void NodeKernel('),
         'Node material producer must remain every source byte unchanged')
    need(cu.count('__global__ void ')==oldcu.count('__global__ void ') and cu.count('<<<')==oldcu.count('<<<'),
         'Optimizer must add no kernel or launch')
    return before,dict(base_cached_source_capture=stat(base),base_cached_CUDA=sc['private_sources']['CUDA'],
        base_cached_header=sc['private_sources']['header'],changes=changes,header_label_changes_only=True,
        complete_cached_CUDA_reverse_equal=True,NodeKernel_source_bytes_exact=True,
        nonNode_block_poll_kernels=list(kernels),block_poll_before_out_of_range_return=True,
        Ace_check_precedes_readonly_summary=True,normal_summary_uses_error_field=True,
        full_ErrorNow_on_failure=True,same_stage_launch_count=True,same_numeric_formulas=True,
        same_topology_and_native_ID_order=True,source_proof_not_machine_code_equivalence=True)


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
    rawrun=L/'c08_h18_hg_matprobe_GPU_r1.run.json';q=read(rawrun)
    need(q['diagnostic_capture_ready'] and not q['solver_completed'] and not q['physical_acceptance'] and q['actual_exit']==q['actual_Popen_exit']==1 and q['ownership_failure'] is None and q['consumed_stats_unchanged'] and q['no_queue_or_followon'],'Actual preserved failed raw capture required, never a completed physical window')
    raw=read(bind(q['raw'])['path']);vals={v['name']:v for v in raw['values']}
    need(raw['schema']==1 and raw['native_id']==7011 and raw['source_step']==2000731 and raw['failure_bits']==2048 and raw['strict_rejection_retained'] and not raw['actual_material_status_observed'] and not raw['actual_returned_kappa_observed'] and len(vals)==len(raw['values'])==37 and vals['actual_Pre_kappa_array_old']['ieee_hex']==vals['shadow_old_kappa']['ieee_hex'],'Same raw observed failure/old-kappa and honest unobserved fields required')
    call=read(bind(q['actual_call'])['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==1 and call['ownership_failure'] is None,'Genuine failed process handles/exits required')
    before += [stat(rawrun)]+[bind(q[k])for k in ('raw','first_error','actual_call','original_start','preparation','source_build')]
    before += optimization_derivation()[0]
    return before


def prepare():
    check=L/(TAG+'.prepare.json');need(not CAP.exists() and not check.exists(),'Existing complete/partial cached preparation protected')
    before=prerequisites()+[stat(Path(__file__)),stat(NOTE)]+[stat(p)for p in AUTHOR.values()]
    _,optimization=optimization_derivation()
    db,debug,_=baseline('Debug');rb,release,_=baseline('Release')
    need(debug['source_archive']==release['source_archive'] and debug['source_capture']==release['source_capture'],'Same unchanged original schema2 source required')
    before += [stat(db),stat(rb)]+[bind(debug[k])for k in ('source_archive','source_capture','actual_call','program')]+[bind(release[k])for k in ('actual_call','program')]
    archive=bind(debug['source_archive'])
    with zipfile.ZipFile(archive['path'])as z:
        single=z.read('src/source/JSphGpuSingle.cpp').decode();gpu=z.read('src/source/JSphGpu.cpp').decode();simple=z.read('src/source/JSphGpuSimple_ker.cu').decode()
        need(re.search(r'#define\s+SPHBSIZE\s+256(?:\s|$)',z.read('src/source/FunctionsBasic_iker.h').decode())is not None,'Original consumer blocksize256 definition required')
    nl='\r\n'if'\r\n'in single else'\n'
    def text(s):return s.replace('\r\n','\n').replace('\n',nl)
    sp=[];new=replace_once(single,'#include "JSphGpuSingle.h"'+nl,'#include "JSphGpuSingle.h"'+nl+text(HOST),sp,'Run-owned private API')
    edits=[('Run owner','  AppName=appname; Log=log; CfgRun=cfg;','  AppName=appname; Log=log; CfgRun=cfg;'+text('\n  C08OptRunScope c08_cached_run_scope;')),
      ('one producer before sole original Darcy','  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);',text(HOOK)+'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);'),
      ('selected predictor dt','  const double ddt_p=DtVariable(false);','  const double ddt_p=DtVariable(false);'+text('\n  if(c08cached::Current() && ddt_p!=c08cached::StepDt)Run_Exceptioon("Cached HG predictor selected dt differs from 5us.");')),
      ('selected corrector dt','  const double ddt_c=DtVariable(true);','  const double ddt_c=DtVariable(true);'+text('\n  if(c08cached::Current() && ddt_c!=c08cached::StepDt)Run_Exceptioon("Cached HG corrector selected dt differs from 5us.");')),
      ('predictor cache writeback','  ComputeSymplecticPre(dt);','  ComputeSymplecticPre(dt);'+text('\n  if(c08cached::Current())c08cached::Current()->CheckMaterial(Np,Npb,Idpg,Codeg,Sigmag,Kplasticg,false);')),
      ('corrector cache writeback','  ComputeSymplecticCorr(dt);','  ComputeSymplecticCorr(dt);'+text('\n  if(c08cached::Current())c08cached::Current()->CheckMaterial(Np,Npb,Idpg,Codeg,Sigmag,Kplasticg,true);')),
      ('accept after full divide and scalar clock','    TimeStep+=stepdt;'+nl+'    LastDt=stepdt;','    TimeStep+=stepdt;'+nl+'    LastDt=stepdt;'+text('\n    if(c08cached::Current())c08cached::Current()->Accept(Np,Npb,Idpg,Codeg,unsigned(Nstep+1),TimeStep,stepdt);')),
      ('sidecar after native save','  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);','  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);'+text('\n  if(c08cached::Current())c08cached::Current()->Save(DirOut,unsigned(Nstep+1),TimeStep);'))]
    for label,old,newtext in edits:new=replace_once(new,old,newtext,sp,label)
    reverse(new,sp,single)
    gp=[];newgpu=replace_once(gpu,'#include "JSphGpu.h"'+nl,'#include "JSphGpu.h"'+nl+'#include "c08_h18_hg_opt_r1.hpp"'+nl,gp,'private nonowning current API')
    for phase in ('Pre','Cor'):
        prefix='  cusphs::ComputeStepSymplectic'+phase+'(';need(newgpu.count(prefix)==1,'One original integration call required')
        start=newgpu.index(prefix);end=newgpu.index(';',start)+1;oldcall=newgpu[start:end]
        args=oldcall[len(prefix):-2]
        on='  if(c08cached::Current())c08cached::Current()->Consume'+phase+'(unsigned(Nstep),TimeStep,Idpg,'+args+');'+nl+'  else'+nl+oldcall
        newgpu=replace_once(newgpu,oldcall,on,gp,'ON cached '+phase+' consumer; OFF exact original CUDA call')
    reverse(newgpu,gp,gpu)
    inc,ip=integrators(simple);need(all(stat(v['path'])==v for v in before),'Inputs changed before cached preparation')
    CAP.mkdir();sources={}
    for key,leaf,data in [('host','JSphGpuSingle.cpp',new.encode()),('gpu_host','JSphGpu.cpp',newgpu.encode()),('integrators',TAG+'_integrators.inc',inc.encode())]+[(k,p.name,p.read_bytes())for k,p in AUTHOR.items()]:
        dest=CAP/leaf
        with dest.open('xb')as f:f.write(data)
        sources[key]=stat(dest)
    diff=CAP/'source.diff';diff.write_text(''.join(difflib.unified_diff(single.splitlines(True),new.splitlines(True),fromfile='schema2/Single',tofile='opt/Single'))+''.join(difflib.unified_diff(gpu.splitlines(True),newgpu.splitlines(True),fromfile='schema2/Gpu',tofile='opt/Gpu')),encoding='utf8')
    proof=CAP/'source_proof.json';save(proof,dict(host_changes=sp,Gpu_host_changes=gp,integrator_changes=ip,exact_reverse_all_original_bytes=True,original_Simpleker_and_physical_CUDA_unchanged=True,original_consumer_SPHBSIZE=256,optimization=optimization))
    need(all(stat(v['path'])==v for v in before),'Inputs changed during cached preparation')
    capture=CAP/'source.json';save(capture,dict(stage=TAG+'.source',passed=True,prepared_only=True,operator='EnergyNormalizedAdjointLoadingOnlyCachedMaterial',policy_schema=2,default_OFF_env_absent=True,explicit_ON_env='C08_HG_OPT_H18=1',xi=.1,source_archive=archive,baseline_source_capture=debug['source_capture'],private_sources=sources,source_diff=stat(diff),source_proof=stat(proof),exact_reverse_original_hosts_bytes=True,exact_reverse_original_integrators_bytes=True,original_CUDA_members_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,physical_objects_retained=111,private_objects_required=3,actual_link_objects_required=114,neighbor_capacity=128,ON_material_producer_calls_per_stage=1,OFF_calls_original_compiled_integrators=True,optimization_scope='block_error_snapshot_and_summary_reuse',NodeKernel_source_bytes_exact=True,base_cached_source_capture=optimization['base_cached_source_capture'],physical_acceptance=False))
    save(check,dict(stage=TAG+'.prepare',passed=True,source_capture=stat(capture),source_archive=archive,private_sources=sources,consumed=before,consumed_stats_unchanged=True,prepared_only=True,build_invocations=0,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
    print('C08_H18_HG_OPT_SOURCE_PREPARED',capture,flush=True)

def baseline(conf):
    p=L/('c08_preload_schema2_'+conf+'_r1.build.json');b=read(p)
    need(b['passed'] and b['configuration']==conf and b['consumed_stats_unchanged'],'Successful unchanged schema2 baseline required')
    a=read(bind(b['actual_call'])['path'])
    need(a['actual_Popen_wait_exit']==a['actual_Win32_exit']==0 and a['ownership_failure'] is None,'Actual original MSBuild handles/exit required')
    need(any('/p:Configuration='+conf==v for v in a['arguments']) and any('/p:VCToolsVersion=14.36.32532'==v for v in a['arguments']),'Original authoritative solution/config/toolset required')
    return p,b,a

def build(conf):
    label='c08_h18_hg_opt_'+conf+'_r1';out=T/'outputs'/label;intdir=Path(os.environ['TEMP'])/BUILD_TAG/conf
    check=L/(label+'.build.json');calls=[];before=[]
    need(' ' not in str(intdir.resolve()) and not out.exists() and not intdir.exists() and all(not(L/(label+s)).exists() for s in ('.build.json','.host_compile.call.json','.host_compile.log','.gpu_host_compile.call.json','.gpu_host_compile.log','.cuda_compile.call.json','.cuda_compile.log','.link.call.json','.link.log')),'Fresh isolated outputs/receipts/no-space IntDir required')
    try:
        bp,b,a=baseline(conf);db,d,_=baseline('Debug');rb,r,_=baseline('Release');sc=read(CAP/'source.json')
        need(sc['passed'] and sc['prepared_only'] and sc['exact_reverse_original_hosts_bytes'] and sc['exact_reverse_original_integrators_bytes'] and sc['original_CUDA_members_unchanged'] and not sc['public_source_changed'] and not sc['class_or_CTE_layout_changed'],'Reviewed reversible private preparation required')
        need(sc['optimization_scope']=='block_error_snapshot_and_summary_reuse' and sc['NodeKernel_source_bytes_exact'],'Exact scheduling-only source proof required')
        need(sc['default_OFF_env_absent'] and sc['explicit_ON_env']=='C08_HG_OPT_H18=1' and sc['xi']==.1 and sc['policy_schema']==2 and sc['operator']=='EnergyNormalizedAdjointLoadingOnlyCachedMaterial' and sc['physical_objects_retained']==111 and sc['private_objects_required']==3 and sc['actual_link_objects_required']==114,'Exact private HG scope/object count required')
        need(d['source_archive']==r['source_archive']==sc['source_archive'] and d['source_capture']==r['source_capture']==sc['baseline_source_capture'],'Same original schema2 archive/capture required')
        prep=L/(TAG+'.prepare.json');pr=read(prep);need(pr['passed'] and pr['consumed_stats_unchanged'] and pr['source_capture']==stat(CAP/'source.json'),'Successful actual source preparation required')
        sources={k:Path(bind(sc['private_sources'][k])['path']) for k in ('host','gpu_host','CUDA','header','integrators')};archive=Path(bind(sc['source_archive'])['path'])
        oldint=Path(b['intermediate']);ctlog=oldint/'DualSPHysics.tlog/CL.command.1.tlog';ltlog=ctlog.with_name('link.command.1.tlog')
        lines=ctlog.read_text(encoding='utf-16').splitlines();at=[i for i,x in enumerate(lines) if x.startswith('^') and Path(x[1:]).name.lower()=='jsphgpusingle.cpp']
        need(len(at)==1,'One authoritative original Single CL block required');clargs=recipe.windows_args(lines[at[0]+1]);original_single_args=list(clargs)
        gat=[i for i,x in enumerate(lines)if x.startswith('^')and Path(x[1:]).name.lower()=='jsphgpu.cpp'];need(len(gat)==1,'One authoritative original GPU host CL block required');gpuargs=recipe.windows_args(lines[gat[0]+1]);original_gpu_args=list(gpuargs)
        ll=ltlog.read_text(encoding='utf-16').splitlines();need(sum(x.startswith('^') for x in ll)==1,'One original link block required');linkargs=recipe.windows_args(' '.join(x for x in ll if x and not x.startswith('^')))
        # This is an honest NEW inventory, not a historical object seal from the old receipt.
        objects=[stat(p) for p in sorted(oldint.rglob('*.obj'))];linked_original=[Path(x).resolve() for x in linkargs if x.lower().endswith('.obj')]
        start=datetime.datetime.fromisoformat(a['started_utc']).timestamp();end=datetime.datetime.fromisoformat(a['ended_utc']).timestamp()
        need(len(objects)==113 and len(linked_original)==113 and len(set(linked_original))==113 and set(linked_original)=={Path(v['path']).resolve() for v in objects},'Fresh113-object inventory must match actual link membership exactly')
        need(all(start<=v['mtime_ns']/1e9<=end for v in objects),'Original object mtime outside genuine original MSBuild call')
        removed=[v for v in objects if Path(v['path']).name.lower()in ('jsphgpusingle.obj','jsphgpu.obj')];retained=[v for v in objects if v not in removed];removed_map={Path(v['path']).resolve():Path(v['path']).name.lower()for v in removed}
        need(len(removed)==2 and len(retained)==111 and all(sum(Path(v['path']).name.lower()==n for v in retained)==1 for n in ('main.obj','jsphgpu_ker.cu.obj','jsphgpusimple_ker.cu.obj')),'Retain111 including original main, interaction and original compiled material/integration CUDA')
        log=Path(bind(a['log'])['path']);nv=[x.split(b'>',1)[-1].strip().decode('ascii') for x in log.read_bytes().splitlines() if b'nvcc.exe' in x.lower() and b'jsphgpu_ker.cu' in x.lower()]
        need(len(nv)==1,'One actual NVCC command required');cuargs=recipe.windows_args(nv[0]);nvcc=Path(cuargs.pop(0));incs=[x[2:] for x in cuargs if x.startswith('-I')]
        need(len(incs)==1 and Path(incs[0]).resolve()==(nvcc.parent.parent/'include').resolve() and '-I' not in cuargs and not any(x.startswith('--include-path') for x in cuargs),'Original CUDA include recipe changed')
        runtime=[bind(v['destination']) for v in b['runtime']];need(len(runtime)==9 and len({Path(v['path']).name.lower() for v in runtime})==9,'Actual original nine-file runtime required')
        pre=T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
        protected=[stat(pre)]+[stat(q) for name in ('runtime_r5','runtime_r6') for q in (T.parent/'support'/name).iterdir() if q.is_file()]
        protected += [stat(S.parent/'bin/windows'/n) for n in ('DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_win64_debug.exe','DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2_GEO_win64.exe') if(S.parent/'bin/windows'/n).exists()]
        before=prerequisites()+[stat(q) for q in (Path(__file__),NOTE,Path(recipe.__file__),Path(recipe.e.__file__),bp,db,rb,ctlog,ltlog,log,CAP/'source.json',prep)]+[bind(sc['source_diff']),bind(sc['source_proof'])]+[stat(q)for q in sources.values()]+[bind(b[k])for k in ('actual_call','source_capture','source_archive')]+[bind(d['program']),bind(r['program'])]+objects+runtime+protected
        out.mkdir();intdir.mkdir(parents=True);frozen=out/'frozen/src/source';frozen_entries=[]
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                q=PurePosixPath(info.filename);need(not q.is_absolute() and '..' not in q.parts,'Unsafe source archive path')
                if not info.is_dir() and len(q.parts)>=3 and q.parts[:2]==('src','source'):
                    need(q.suffix.lower() not in ('.obj','.o','.pdb','.exe','.dll','.lib'),'Binary in source archive')
                    dest=out/'frozen'/Path(*q.parts);dest.parent.mkdir(parents=True,exist_ok=True)
                    data=sources['host'].read_bytes()if q.as_posix()=='src/source/JSphGpuSingle.cpp'else sources['gpu_host'].read_bytes()if q.as_posix()=='src/source/JSphGpu.cpp'else z.read(info)
                    with dest.open('xb')as f:f.write(data)
                    frozen_entries.append(stat(dest))
            need((frozen/'JSphGpu_ker.cu').read_bytes()==z.read('src/source/JSphGpu_ker.cu'),'Original physical CUDA source must remain unmodified')
        for k in ('CUDA','header','integrators'):
            dest=frozen/sources[k].name
            with dest.open('xb')as f:f.write(sources[k].read_bytes())
            frozen_entries.append(stat(dest))
        need(all((frozen/n).is_file() for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h','FunctionsBasic_iker.h','FunSphKernel_iker.h','JCellSearch_iker.h')),'Complete actual private header closure required');before+=frozen_entries
        hostobj=intdir/'JSphGpuSingle.obj';gpuobj=intdir/'JSphGpu.obj';cudaobj=intdir/'c08_h18_hg_opt_r1.cu.obj';program=out/Path(b['program']['path']).name
        need(sum(x.lower().startswith('/fo') for x in clargs)==sum(x.lower().startswith('/fd') for x in clargs)==sum(x.lower().endswith('jsphgpusingle.cpp') for x in clargs)==1 and not any(x.lower().startswith(('/yu','/yc','/gl')) for x in clargs),'Original single-source non-PCH/non-GL host recipe required')
        clargs=['/I'+str(frozen),*['/Fo'+str(hostobj) if x.lower().startswith('/fo') else '/Fd'+str(intdir/'host.pdb') if x.lower().startswith('/fd') else str(frozen/'JSphGpuSingle.cpp') if x.lower().endswith('jsphgpusingle.cpp') else x for x in clargs],'/sourceDependencies',str(intdir/'host.dependencies.json')]
        need(sum(x.lower().startswith('/fo')for x in gpuargs)==sum(x.lower().startswith('/fd')for x in gpuargs)==sum(x.lower().endswith('jsphgpu.cpp')for x in gpuargs)==1 and not any(x.lower().startswith(('/yu','/yc','/gl'))for x in gpuargs),'Original single-source GPU host recipe required')
        gpuargs=['/I'+str(frozen),*['/Fo'+str(gpuobj)if x.lower().startswith('/fo')else '/Fd'+str(intdir/'gpu_host.pdb')if x.lower().startswith('/fd')else str(frozen/'JSphGpu.cpp')if x.lower().endswith('jsphgpu.cpp')else x for x in gpuargs],'/sourceDependencies',str(intdir/'gpu_host.dependencies.json')]
        nfd=0
        for i,x in enumerate(cuargs):
            if i and cuargs[i-1]=='-Xcompiler':cuargs[i],n=re.subn(r'(?i)(?<!\S)/Fd[^\s]+',lambda m:'/Fd'+str(intdir/'cuda.pdb'),x);nfd+=n
        need(nfd==1 and cuargs.count('-o')==cuargs.count('--keep-dir')==1 and sum(Path(x).name.lower()=='jsphgpu_ker.cu' for x in cuargs)==1,'One actual NVCC source/object/PDB/keep directory required')
        cuargs=[str(frozen/sources['CUDA'].name) if Path(x).name.lower()=='jsphgpu_ker.cu' else x for x in cuargs];cuargs[cuargs.index('-o')+1]=str(cudaobj);cuargs[cuargs.index('--keep-dir')+1]=str(intdir);cuargs=['-I'+str(frozen),*cuargs]
        need(not any('C08_HG_DEBUG_SNAPSHOT' in x for x in cuargs),'Unexpected inherited snapshot macro')
        if conf=='Debug':cuargs.append('-DC08_HG_DEBUG_SNAPSHOT')
        opt='/Od' if conf=='Debug' else '/O2';crt='/MTd' if conf=='Debug' else '/MT'
        need(all(x in clargs and x in gpuargs for x in (opt,crt,'/fp:precise','/openmp')) and all(x in cuargs for x in ('--compile','-use_fast_math','-D_WITHGPU')) and any('compute_86' in x and 'sm_86' in x for x in cuargs) and any(opt in x and crt in x for x in cuargs) and not any('C08_STAGE_TRACE' in x or 'C08_CAUSAL_TRACE' in x or 'rdc=true' in x or x in ('--device-link','-dc') for x in (*clargs,*cuargs)),'Original config/CRT/sm86/non-RDC flags required with no observer macros')
        targets={'/out:':program,'/pdb:':out/(program.stem+'.pdb'),'/implib:':out/(program.stem+'.lib'),'/ltcgout:':intdir/(program.stem+'.iobj'),'/ilk:':out/(program.stem+'.ilk'),'/map:':out/(program.stem+'.map'),'/manifestfile:':intdir/'program.manifest','/pgd:':intdir/'program.pgd','/tlbout:':intdir/'program.tlb','/winmdfile:':intdir/'program.winmd'};seen={};linked=[]
        for arg in linkargs:
            if arg.lower().endswith('.obj')and Path(arg).resolve()in removed_map:arg=str(hostobj if removed_map[Path(arg).resolve()]=='jsphgpusingle.obj'else gpuobj)
            for key,target in targets.items():
                if arg.lower().startswith(key):need(key not in seen,'Duplicate link output switch');seen[key]=str(target);arg=key+str(target);break
            linked.append(arg)
        linked.append(str(cudaobj));actual=[Path(x).resolve()for x in linked if x.lower().endswith('.obj')]
        need(all(k in seen for k in ('/out:','/pdb:','/implib:','/ltcgout:')) and len(actual)==len(set(actual))==114 and set(actual)=={Path(v['path']).resolve()for v in retained}|{hostobj.resolve(),gpuobj.resolve(),cudaobj.resolve()},'Exactly111 retained+three private objects and fully rehomed link outputs required')
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
        def tool(suffix,argv,cwd,environment):
            name=label+suffix
            try:invoke(name,argv,cwd,environment)
            finally:
                q=L/(name+'.call.json')
                if q.exists():calls.append(stat(q))
        tool('.host_compile',[str(cl),*clargs],intdir,env);tool('.gpu_host_compile',[str(cl),*gpuargs],intdir,env);tool('.cuda_compile',[str(nvcc),*cuargs],intdir,cudaenv);tool('.link',[str(link),*linked],S/'VS',env)
        deps=read(intdir/'host.dependencies.json');includes={Path(x).resolve()for x in deps['Data']['Includes']};need(all((frozen/n).resolve()in includes for n in ('JSphGpuSingle.h','JSphGpu.h','JSph.h','JSphGpu_ker.h',sources['header'].name)),'Host used another class/header ABI')
        gdeps=read(intdir/'gpu_host.dependencies.json');gincludes={Path(x).resolve()for x in gdeps['Data']['Includes']};need(all((frozen/n).resolve()in gincludes for n in ('JSphGpu.h','JSph.h','JSphGpuSimple_ker.h',sources['header'].name)),'GPU host used another class/header ABI')
        copied=[]
        for entry in runtime:
            dest=out/Path(entry['path']).name;need(not dest.exists(),'Existing private runtime protected');shutil.copy2(entry['path'],dest);v=stat(dest);need((v['bytes'],v['mtime_ns'])==(entry['bytes'],entry['mtime_ns'])and dest.read_bytes()==Path(entry['path']).read_bytes(),'Private runtime copy differs');copied.append(v)
        need(all(stat(v['path'])==v for v in before),'Original object/source/program/PRE/runtime changed during build')
        warning_lines=[line for q in calls for line in Path(read(q['path'])['log']['path']).read_bytes().decode('mbcs').splitlines()if re.search(r'\bwarning\b',line,re.I)]
        save(check,dict(stage=label+'.build',passed=True,configuration=conf,program=stat(program),source_capture=stat(CAP/'source.json'),source_archive=stat(archive),baseline_source_capture=b['source_capture'],private_sources={k:stat(v)for k,v in sources.items()},baseline_source_build=stat(bp),original_actual_build_call=b['actual_call'],original_build_started_utc=a['started_utc'],original_build_ended_utc=a['ended_utc'],original_objects_historical_seal_claimed=False,fresh_original_objects=objects,original113_mtimes_within_actual_build=True,original_link_membership_exact=True,retained_original_objects=111,private_objects=3,actual_link_objects=114,retained_object_stats=retained,new_private_objects=[stat(hostobj),stat(gpuobj),stat(cudaobj)],actual_link_inputs=[str(q)for q in actual],original_host_recipe=stat(ctlog),original_single_command=original_single_args,original_GPU_host_command=original_gpu_args,original_CUDA_recipe_log=stat(log),original_link_recipe=stat(ltlog),link_output_flags=seen,private_header_dependencies=stat(intdir/'host.dependencies.json'),private_GPU_header_dependencies=stat(intdir/'gpu_host.dependencies.json'),frozen_sources=frozen_entries,IntDir=str(intdir),OutDir=str(out),runtime=copied,calls=calls,warning_lines=warning_lines,new_warning_free_claimed=False,consumed=before,consumed_stats_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,original_physical_CUDA_objects_retained=True,ON_runtime_env='C08_HG_OPT_H18=1',OFF_env_absent_no_HG_allocation_launch_sidecar=True,operator='EnergyNormalizedAdjointLoadingOnlyCachedMaterial',xi=.1,neighbor_capacity=128,policy_schema=2,single_material_producer=True,OFF_calls_original_compiled_integrators=True,optimization_scope='block_error_snapshot_and_summary_reuse',NodeKernel_source_bytes_exact=True,base_cached_source_capture=sc['base_cached_source_capture'],new_binary_equivalence_not_yet_proven=True,cache_consumer_writeback_is_independent_material_solve=False,new_GPU_material_bit_equivalence_qualified=False,coupled_energy_qualified=False,Debug_first_n_snapshot_macro_enabled=(conf=='Debug'),private_observer_only_flag=('-DC08_HG_DEBUG_SNAPSHOT'if conf=='Debug'else None),compile_invocations=3,link_invocations=1,full_project_builds=0,solver_invocations=0,help_invocations=0,memcheck_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        print('C08_H18_HG_OPT_PRIVATE_BUILD_PASSED',conf,program,flush=True)
    except Exception as error:
        if not check.exists():save(check,dict(stage=label+'.build',passed=False,configuration=conf,first_failure=str(error),calls=calls,consumed=before,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--configuration',choices=('Debug','Release'));p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized and (a.prepare != bool(a.configuration)),'Independent root admission and exactly one prepare/configuration operation required')
    if a.prepare:prepare()
    else:build(a.configuration)
