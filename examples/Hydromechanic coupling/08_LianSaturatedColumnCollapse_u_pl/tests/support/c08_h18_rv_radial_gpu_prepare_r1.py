"""Prepare only a reversible one-host overlay and standalone RV CUDA source."""
import argparse
import difflib
import json
import zipfile
from pathlib import Path

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_rv_radial_gpu_r1'
OUT=T/'outputs'/(TAG+'_source');NOTE=T/'notes'/(TAG+'.md')
AUTHOR={k:T/'support'/(TAG+suffix) for k,suffix in [('CUDA','.cu'),('header','.h')]}

def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def need(v,s):
    if not v:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def bind(e):need(stat(e['path'])==e,'Consumed stat changed: '+e['path']);return e
def save(p,j):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')

HOST=r'''
#include "JDsFixedDt.h"
#include "c08_h18_rv_radial_gpu_r1.h"
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <stdexcept>
namespace {
struct C08H18Phase {
 unsigned long long Calls=0,Commits=0;
 unsigned Step=~0u,CudaStatus=0;
 double Time=0,Dt=0,MaxLambda=0,MaxBound=0;
 double Running[c08h18radial::RunningCount]={};
 c08h18radial::Result Value={};
};
struct C08H18Counter {const void*Owner=nullptr;unsigned StartStep=0,LastSavedStep=0,ManufacturedCalls=0,FixtureRows=0;C08H18Phase Pre,Cor;};
static C08H18Counter C08H18Count;
static bool C08H18Requested(){static const bool v=[](){const char*p=std::getenv("C08_RV_RADIAL_H18");if(!p)return false;if(std::strcmp(p,"1"))throw std::runtime_error("C08_RV_RADIAL_H18 must be absent or exactly1");return true;}();return v;}
static double C08H18Ratio(double x,double b){return b>0?std::fabs(x)/b:(x==0?0:std::numeric_limits<double>::infinity());}
static void C08H18Raw(std::ostream&f,const c08h18radial::Result&r){f<<','<<r.directed_edges<<','<<r.reverse_memberships;for(double v:r.value)f<<','<<v;}
static void C08H18Update(C08H18Phase&p,const c08h18radial::Result&r){using namespace c08h18radial;p.Value=r;const auto*m=r.value;p.MaxLambda=(std::max)(p.MaxLambda,m[lambda_upper]);p.MaxBound=(std::max)(p.MaxBound,m[dt_lambda_half]);if(!r.certificates_passed)return;
 const double a[]={m[normalization_max_ratio],m[LS_backward_max_ratio],C08H18Ratio(m[exchange_error],m[exchange_budget]),C08H18Ratio(m[power_error],m[power_budget]),C08H18Ratio(m[net_norm],m[net_budget]),C08H18Ratio(m[pair_torque],m[central_budget]),C08H18Ratio(m[torque_reduce_error],m[torque_reduce_budget]),C08H18Ratio(m[node_torque],m[torque_budget]),C08H18Ratio((std::max)(m[frozen_Euler_deltaE],0.),m[frozen_Euler_budget]),m[float_commit_budget_ratio],C08H18Ratio((std::max)(m[committed_power],0.),m[committed_power_budget]),C08H18Ratio(m[committed_net_norm],m[committed_net_budget]),C08H18Ratio(m[committed_torque],m[committed_torque_budget]),C08H18Ratio((std::max)(m[committed_Euler_deltaE],0.),m[committed_Euler_budget])};
 static_assert(sizeof(a)/sizeof(a[0])==RunningCount,"Running certificate schema differs");for(unsigned i=0;i<RunningCount;i++){if(!std::isfinite(a[i]))throw std::runtime_error("Nonfinite radial running certificate ratio");p.Running[i]=(std::max)(p.Running[i],a[i]);}
}
static bool C08H18Init(const void*owner,const std::string&dir,unsigned step,float h,double dp){
 if(C08H18Count.Owner)return C08H18Count.Owner==owner;
 for(const char*leaf:{"C08H18RadialResidualPolicy.json","C08H18RadialResidual.csv","C08H18RadialManufactured.csv","C08H18RadialLimiterFixtures.csv"})if(std::ifstream((dir+leaf).c_str()).good())return false;
 std::ofstream p((dir+"C08H18RadialResidualPolicy.json").c_str());p<<std::setprecision(17)
 <<"{\"policy\":\"C08H18RadialResidualPolicy\",\"schema\":3,\"operator\":\"compression_only_radial_residual_limiter\",\"phase_policy\":\"ReleaseOnly\",\"active\":true,\"alpha\":"<<c08h18radial::Alpha
 <<",\"main_columns\":"<<c08h18radial::MainColumns<<",\"main_schema\":\"C08H18Radial87-r1\",\"manufactured_columns\":"<<c08h18radial::ManufacturedColumns
 <<",\"fixture_columns\":6,\"kernel\":\"Wendland\",\"kernel_h_sph_float\":"<<double(h)<<",\"dp_m\":"<<dp<<",\"requested_hdp\":1.8,\"operator_dt_s\":0.000005,\"source_schema\":2,\"keep_bed_overlap\":false,\"geometry_profile\":\"bedroles\",\"first_stage_global_step\":"<<step
 <<",\"retired_begin\":1805,\"retired_count\":255,\"force_clock\":\"original_TimeStep_both_stages\",\"reaction_closed\":false,\"BI4_metadata\":false,\"native_22_schema_changed\":false,\"manufactured_mode_count\":5,\"limiter_fixture_count\":8"
 <<",\"synthetic_velocity_coordinates\":\"global\",\"manufactured_first_force_scratch_only\":true,\"manufactured_commit_fields_hypothetical\":true,\"device_fixtures_use_actual_Limiter\":true,\"host_gate_before_Ace_commit\":true,\"canonical_native_id_order\":true,\"canonical_helper_noinline\":true,\"reverse_force_bit_reproduction\":true"
 <<",\"ephemeral_buffers_per_helper\":5,\"neighbor_kernels_per_helper\":2,\"summary_kernels_per_helper\":2,\"serial_O_N_summaries\":true,\"reverse_cell_membership_each_positive_neighbor\":true,\"directed_D_and_pair_torque_halved\":true,\"node_and_absolute_force_not_halved\":true"
 <<",\"old_vector_form_or_contraction_certificate_used\":false,\"per_stage_mechanical_certificates\":true,\"save_rows_are_not_all_stage_trace\":true,\"running_ratios_are_per_phase_maxima\":true,\"budget_formed_by_bound_source_not_rebuilt_offline_from_all_neighbors\":true,\"frozen_RV_Euler_only\":true"
 <<",\"LS_regularized\":false,\"wall_bonds\":false,\"full_coupled_stability_claimed\":false,\"physical_acceptance\":false}\n";p.flush();if(!p)return false;
 std::ofstream c((dir+"C08H18RadialResidual.csv").c_str());c<<c08h18radial::CommonHeader()<<",directed_edges,reverse_memberships"<<c08h18radial::MetricHeader()<<c08h18radial::RunningHeader()<<'\n';c.flush();if(!c)return false;
 std::ofstream m((dir+"C08H18RadialManufactured.csv").c_str());m<<"mode,name,step_start_global,source_time_s,operator_dt_s,directed_edges,reverse_memberships"<<c08h18radial::MetricHeader()<<",committed,certificates_passed,manufactured_passed,error_bits,cuda_status\n";m.flush();if(!m)return false;
 std::ofstream f((dir+"C08H18RadialLimiterFixtures.csv").c_str());f<<"fixture,s_m_s,q_m_s,a_m_s,expected_a_m_s,pair_power_unit_beta_alpha\n";f.flush();if(!f)return false;
 C08H18Count.Owner=owner;C08H18Count.StartStep=step;return true;
}
static bool C08H18Row(const std::string&dir,const char*record,const char*phase,const C08H18Phase&q,unsigned completed,double saved){using namespace c08h18radial;const auto&s=C08H18Count;const auto&r=q.Value;const auto*m=r.value;std::ofstream f((dir+"C08H18RadialResidual.csv").c_str(),std::ios::out|std::ios::app);
 f<<std::setprecision(17)<<record<<','<<phase<<",1,"<<Alpha<<','<<q.Step<<','<<completed<<','<<q.Time<<','<<q.Time<<','<<saved<<','<<q.Dt<<','<<q.Calls<<','<<q.Commits<<','<<s.Pre.Calls<<','<<s.Cor.Calls<<','<<s.Pre.Commits<<','<<s.Cor.Commits<<','<<m[lambda_upper]<<','<<q.MaxLambda<<','<<m[dt_lambda_half]<<','<<q.MaxBound<<','<<r.validated_soil<<','<<r.committed<<','<<r.error_bits<<','<<r.invalid_sorted<<','<<r.invalid_native_id<<','<<q.CudaStatus;
 C08H18Raw(f,r);for(double v:q.Running)f<<','<<v;f<<'\n';f.flush();return bool(f);
}
static bool C08H18Manufactured(const std::string&dir,unsigned mode,unsigned step,double time,double dt,const c08h18radial::Result&r,unsigned status){const char*names[]={"actual","translation","full_affine","isotropic_compression","pure_shear","rigid_rotation"};std::ofstream f((dir+"C08H18RadialManufactured.csv").c_str(),std::ios::out|std::ios::app);f<<std::setprecision(17)<<mode<<','<<names[mode]<<','<<step<<','<<time<<','<<dt;C08H18Raw(f,r);f<<','<<r.committed<<','<<r.certificates_passed<<','<<r.manufactured_passed<<','<<r.error_bits<<','<<status<<'\n';f.flush();return bool(f);}
static bool C08H18Fixtures(const std::string&dir,const c08h18radial::FixtureResult&r){std::ofstream f((dir+"C08H18RadialLimiterFixtures.csv").c_str(),std::ios::out|std::ios::app);f<<std::setprecision(17);for(unsigned k=0;k<8;k++)f<<k<<','<<r.s[k]<<','<<r.q[k]<<','<<r.a[k]<<','<<r.expected[k]<<','<<r.power[k]<<'\n';f.flush();return bool(f);}
static bool C08H18Save(const void*owner,const std::string&dir,unsigned completed,double time){const auto&s=C08H18Count;if(s.Owner!=owner||s.LastSavedStep==completed||s.ManufacturedCalls!=5||s.FixtureRows!=8||s.Pre.Calls!=s.Cor.Calls||s.Pre.Commits!=s.Pre.Calls||s.Cor.Commits!=s.Cor.Calls||s.Pre.Step+1!=completed||s.Cor.Step+1!=completed||s.Pre.Calls!=completed-s.StartStep)return false;if(!C08H18Row(dir,"save","Pre",s.Pre,completed,time)||!C08H18Row(dir,"save","Cor",s.Cor,completed,time))return false;C08H18Count.LastSavedStep=completed;return true;}
}
'''

HOOK=r'''
  if(C08H18Requested()){
    if(!GravityPreloadReleased || !GravityPreload || !IsGravityPreloadHandoff() || GravityPreloadElasticSource
      || GravityPreloadKeepBedOverlap || !GravityPreloadBedIds.empty() || GravityPreloadActualStep!=2000000
      || GravityPreloadIdBegin!=1805 || GravityPreloadIdCount!=255 || Np!=6805 || Npb!=1805 || NpbOk>Npb
      || CaseNp!=7060 || CaseNpb!=2060 || CaseNfixed!=2060 || CaseNfluid!=5000 || PartBegin
      || CaseNmoving || CaseNfloat || InOut || Symmetry || PeriActive || Shifting || Damping || RelaxZones || UseDEM || AccInput
      || !UseDynamicPorePlaneContact() || !NoPenetration || TMdbc2!=MDBC2_NoPen || TBoundary!=BC_MDBC || !UseNormals
      || !HydroMech || !HydroMechDynamicSeepage || !PorosityFeedback || !DynamicPorePressure || !DynamicPoreWall
      || !DynamicPoreConductivity || HydroMechConductivityModel!=1 || DynamicPoreConductivityCk!=2.
      || !Simulate2D || TKernel!=KERNEL_Wendland || TStep!=STEP_Symplectic || Dp!=.04 || KernelH!=.072f
      || !FixedDt || FixedDt->GetFixedValue()!=.000005 || SymplecticDtPre!=.000005
      || (interstep!=INTERSTEP_SymPredictor && interstep!=INTERSTEP_SymCorrector)
      || !PoroJg || !Aceg || HourglassGpu || SoilHourglassXi || SoilDamping || PoreShepardRegularization || SoilBoundaryDerivativeSPR
      || !ArtificialStress || ArtificialStressCoef!=.3f || ArtificialStressExp!=2.55f || TVisco!=VISCO_Artificial || Visco!=.1f || ViscoTime
      || TDensity!=DDT_None || !SoilStressRateGradCorr || !HydroMechFreeSeepage || HydroMechDrainage
      || HydroMechTopLoadMode!=HMLOAD_None || RhopZero!=2072.5f || SoilCte.PoreWaterRho!=1000.f
      || SoilCte.PoreWaterBulkModulus!=1e9f || SoilCte.Porosity!=.35f || SoilCte.HydraulicConductivity!=.0002f
      || SoilCte.ModulusE!=20e6f || SoilCte.PRvs!=.33f || DPCtes!=DP_PS || !StrainSoftening
      || SoilCte.dlt!=0.f || SoilCte.psiDecay!=0.f || SoilCte.coh!=5000.f || SoilCte.coh_r!=1000.f || SoilCte.n_coh!=5.f
      || SoilCte.n_phi!=0.f || SoilCte.phi!=SoilCte.phi_r || Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=-9.81f)
      Run_Exceptioon("Private H1.8 radial RV requires unchanged schema2 psi0 Wendland/AS.3n2.55/5us/bedroles released target.");
    if(!C08H18Init(this,DirOut,Nstep,KernelH,Dp))Run_Exceptioon("Private H1.8 radial RV policy/counter output exists or initialization failed.");
    C08H18Counter& count=C08H18Count;const bool predictor=(interstep==INTERSTEP_SymPredictor);
    if((predictor && (count.Pre.Calls!=count.Cor.Calls || Nstep!=count.StartStep+count.Cor.Calls))
      ||(!predictor && (count.Pre.Calls!=count.Cor.Calls+1 || Nstep!=count.StartStep+count.Cor.Calls)))
      Run_Exceptioon("Private H1.8 radial RV actual Pre/Cor order changed.");
    const auto evaluate=[&](unsigned mode,bool commit,c08h18radial::Result& r){return c08h18radial::Add(Np,Npb,DivData,Dcellg,Idpg,
      Posxyg,Poszg,Velrhopg,Codeg,PoroJg,1.-double(SoilCte.Porosity),double(RhopZero),double(SoilCte.PoreWaterRho),
      double(MassFluid)/double(RhopZero),KernelH,CSP.kwend.bwen,SoilCte.ModulusG,SymplecticDtPre,mode,commit,Aceg,r);};
    if(!count.ManufacturedCalls){
      c08h18radial::FixtureResult fixture={};const cudaError_t fixtureStatus=c08h18radial::Fixtures(fixture);
      if(!C08H18Fixtures(DirOut,fixture))Run_Exceptioon("Failed preserving real GPU limiter fixtures.");
      if(fixtureStatus!=cudaSuccess || fixture.errors)Run_Exceptioon("Private radial GPU limiter fixtures failed before actual Ace commit.");
      count.FixtureRows=8;
      if(!predictor || Nstep!=2000000)Run_Exceptioon("Manufactured graph must be the first genuine released force graph.");
      for(unsigned mode=1;mode<=5;mode++){
        c08h18radial::Result r={};const cudaError_t status=evaluate(mode,false,r);count.ManufacturedCalls++;
        if(!C08H18Manufactured(DirOut,mode,Nstep,TimeStep,SymplecticDtPre,r,unsigned(status)))Run_Exceptioon("Failed preserving real manufactured metrics.");
        if(status!=cudaSuccess || r.error_bits || r.committed || !r.certificates_passed || !r.manufactured_passed || r.validated_soil!=5000)
          Run_Exceptioon("Private H1.8 radial RV manufactured graph/affine-null/mechanical certificate failed; actual Ace not committed.");
      }
    }
    C08H18Phase& record=predictor?count.Pre:count.Cor;record.Calls++;record.Step=Nstep;record.Time=TimeStep;record.Dt=SymplecticDtPre;
    c08h18radial::Result r={};const cudaError_t status=evaluate(0,true,r);record.CudaStatus=unsigned(status);C08H18Update(record,r);if(r.committed)record.Commits++;
    if(status!=cudaSuccess || r.error_bits || !r.committed || !r.certificates_passed || r.validated_soil!=5000){
      if(!C08H18Row(DirOut,"failure",predictor?"Pre":"Cor",record,Nstep,TimeStep))Run_Exceptioon("Failed preserving real residual-viscosity failure metrics.");
      Log->Printf("Private H1.8 radial RV rejected: phase=%s Nstep=%u id=%u sorted=%u bits=%u CUDA=%u committed=%u dt=%.17g lambda=%.17g isolated=%.17g.",
        predictor?"Pre":"Cor",Nstep,r.invalid_native_id,r.invalid_sorted,r.error_bits,unsigned(status),unsigned(r.committed),SymplecticDtPre,r.value[c08h18radial::lambda_upper],r.value[c08h18radial::dt_lambda_half]);
      Run_Exceptioon("Private H1.8 radial RV rank/finite/mechanical/coupled-path diagnostic rejected; preserve partial evidence.");
    }
  }
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized,'Separate root source-preparation admission required')
    check=L/(TAG+'.prepare.json');need(not OUT.exists() and not check.exists(),'Existing complete/partial source preparation protected')
    paths=[L/('c08_preload_schema2_'+q+'_r1.build.json') for q in ('Debug','Release')];builds=[read(p) for p in paths]
    need(all(b['passed'] and b['consumed_stats_unchanged'] for b in builds) and builds[0]['source_archive']==builds[1]['source_archive']
         and builds[0]['source_capture']==builds[1]['source_capture'],'Same successful original Debug/Release schema2 archive required')
    rvpaths=[L/'c08_h18_rv_gpu_Debug_r2.build.json',L/'c08_h18_rv_gpu_Release_r3.build.json']
    rvproof=[read(q)for q in rvpaths]
    need(all(b['passed'] and b['consumed_stats_unchanged'] and b['source_archive']==builds[0]['source_archive']
             and b['retained_original_objects']==112 and b['private_objects']==2 and b['actual_link_objects']==114 for b in rvproof),
         'Passed original vector-RV implementation proof differs; its host/CUDA objects are not adopted')
    before=[stat(q)for q in [Path(__file__),NOTE,*AUTHOR.values(),*paths,*rvpaths]]
    for b in rvproof:before += [bind(b[k])for k in ('program','source_capture','source_archive')]
    for b in builds:before += [bind(b[k]) for k in ('program','source_capture','source_archive','actual_call')]
    archive=bind(builds[0]['source_archive'])
    with zipfile.ZipFile(archive['path'])as z:original=z.read('src/source/JSphGpuSingle.cpp')
    nl=b'\r\n' if b'\r\n' in original else b'\n'
    def text(s):return s.replace('\n',nl.decode()).encode('utf-8')
    anchors=[(b'#include "JSphGpuSingle.h"'+nl,b'#include "JSphGpuSingle.h"'+nl+text(HOST)),
      (b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);',text(HOOK)+b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);'),
      (b'  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',b'  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);'+text('\n  if(C08H18Requested() && GravityPreloadReleased && !C08H18Save(this,DirOut,Nstep+1,TimeStep))\n    Run_Exceptioon("Private H1.8 radial RV actual saved phase counters failed.");'))]
    overlay=original
    for old,new in anchors:need(overlay.count(old)==1,'Unique original host source anchor differs');overlay=overlay.replace(old,new,1)
    inverse=overlay
    for old,new in reversed(anchors):need(inverse.count(new)==1,'Ambiguous reverse overlay anchor');inverse=inverse.replace(new,old,1)
    need(inverse==original,'Unexpected original source body edit')
    for e in before:bind(e)
    OUT.mkdir();sources={}
    for key,leaf,content in [('host','JSphGpuSingle.cpp',overlay),*[(k,p.name,p.read_bytes())for k,p in AUTHOR.items()]]:
        q=OUT/leaf
        with q.open('xb')as f:f.write(content)
        sources[key]=stat(q)
    diff=OUT/'host.diff';diff.write_text(''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),overlay.decode('utf-8').splitlines(True),fromfile='schema2/JSphGpuSingle.cpp',tofile='private/JSphGpuSingle.cpp')),encoding='utf-8')
    capture=OUT/'source.json';save(capture,dict(stage=TAG+'.source',passed=True,prepared_only=True,private_sources=sources,
      source_archive=archive,baseline_source_capture=builds[0]['source_capture'],baseline_builds=[stat(p)for p in paths],prior_vector_RV_builds=[stat(p)for p in rvpaths],host_diff=stat(diff),
      exact_reverse_original_host_bytes=True,original_CUDA_members_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,
      default_OFF_env_absent=True,explicit_ON_env='C08_RV_RADIAL_H18=1',alpha=.1,main_columns=87,manufactured_columns=57,fixture_columns=6,policy_schema=3,
      operator='compression_only_radial_residual_limiter',manufactured_mode_count=5,limiter_fixture_count=8,
      physical_objects_retained=112,private_objects_required=2,actual_link_objects_required=114,budget_formed_by_bound_source=True,
      new_operator_not_vector_form=True,manufactured_float_commit_fields_hypothetical=True,
      default_OFF_old_original_body_exact=True,all_stage_trace_claimed=False,physical_acceptance=False,SHA_scans=0))
    for e in before:bind(e)
    save(check,dict(stage=TAG+'.prepare',passed=True,source_capture=stat(capture),source_archive=archive,private_sources=sources,
      host_diff=stat(diff),consumed=before,consumed_stats_unchanged=True,compiler_invocations=0,solver_invocations=0,reader_invocations=0,
      original_CUDA_objects_not_recompiled=True,public_source_changed=False,physical_acceptance=False,SHA_scans=0))

if __name__=='__main__':main()
