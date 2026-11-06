// Real CPU Pre/Cor material adapter, two pool-owned slots; no InitRun, force or scene.
#include "JSphCpuSingle.h"
#include "JArraysCpu.h"
#include "JDsTimersCpu.h"
#include "JDsDcellDef.h"
#include "JException.h"
#include "JAppInfo.h"
#include "FunSoilMaterial.h"
#include "upl_material_shared_cases_r1.h"
#include <iostream>
#include <omp.h>
JAppInfo AppInfo("UplMaterialCpuStage","r1","06-11-2026");
namespace fs=std::filesystem;
namespace mc=upl_material_cases_r1;
using upl_material_candidate_r1::Stress;
using upl_material_candidate_r1::State;
struct Measure {double inferred_kappa=0,inferred_lambda=0,yield_continuous=0,yield_written=0,dev_error=0,stress_gap=0,tensor_budget=0;};
static Stress ReadStress(const tsymatrix3d& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static tsymatrix3d NativeStress(const Stress& s){tsymatrix3d r{};r.xx=s.xx;r.yy=s.yy;r.zz=s.zz;r.xy=s.xy;r.yz=s.yz;r.xz=s.xz;return r;}
class Probe:public JSphCpuSingle{
  static constexpr double Dt=.125; // Arithmetic-stage interval, not a stable physical timestep.
  struct Snapshot{tdouble3 p;tfloat4 v;State s;typecode code;unsigned cell;};
  Snapshot Snap(unsigned q)const{return {Posc[q],Velrhopc[q],{ReadStress(Sigmac[q]),Kplasticc[q]},Codec[q],Dcellc[q]};}
  bool Same(unsigned q,const Snapshot& a)const{
    const auto b=Snap(q);return mc::Bits(a.p.x,b.p.x)&&mc::Bits(a.p.y,b.p.y)&&mc::Bits(a.p.z,b.p.z)
      &&mc::Bits(a.v.x,b.v.x)&&mc::Bits(a.v.y,b.v.y)&&mc::Bits(a.v.z,b.v.z)&&mc::Bits(a.v.w,b.v.w)
      &&mc::SameState(a.s,b.s)&&a.code==b.code&&a.cell==b.cell;
  }
  void CheckScope()const{
    mc::Need(TimeStep==0&&Nstep==0&&!HydroMech&&!PorosityObserver&&!PorosityFeedback&&!PoroJc&&!PorePressc&&Np==2&&Npb==1,"Stage-only scope changed");
    mc::Need(Idpc[0]==0&&Idpc[1]==1&&CODE_IsNormal(Codec[1])&&CODE_IsFluid(Codec[1]),"Native fixture identity changed");
  }
  void Row(std::ostream& o,const char* test,const char* phase,const char* status,const mc::Case& c,const Measure& m={})const{
    const unsigned q=1;const auto s=ReadStress(Sigmac[q]);
    o<<test<<','<<phase<<','<<status<<','<<c.point.id<<','<<Kplasticc[q]<<','<<c.point.state.kappa<<','<<c.saved_reference.kappa
      <<','<<Posc[q].x<<','<<Posc[q].y<<','<<Posc[q].z<<','<<Velrhopc[q].x<<','<<Velrhopc[q].z<<','<<Velrhopc[q].w<<','<<unsigned(Codec[q])
      <<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<m.inferred_kappa<<','<<m.inferred_lambda<<','<<m.yield_continuous<<','<<m.yield_written
      <<','<<m.dev_error<<','<<m.stress_gap<<','<<m.tensor_budget<<','<<TimeStep<<','<<Nstep<<','<<ArraysCpu->GetArrayCountUsed(JArraysCpu::SIZE_24B)<<'\n';
    o.flush();mc::Need(bool(o),"Stage row write failed");
  }
  Measure CheckRadial(const mc::Case& c,bool predictor)const{
    const auto& a=c.point.state.stress;const auto b=ReadStress(Sigmac[1]);const auto& m=c.point.material;
    const auto tr=mc::InvariantIndependent(a),v=mc::InvariantIndependent(b);
    const double x=a.xx-b.xx,y=a.yy-b.yy,z=a.zz-b.zz,xy=a.xy-b.xy,yz=a.yz-b.yz,xz=a.xz-b.xz,mean=(x+y+z)/3.,G=m.shear,K=m.bulk;
    const double dev=std::sqrt((2./3.)*((x-mean)*(x-mean)+(y-mean)*(y-mean)+(z-mean)*(z-mean)+2.*(xy*xy+yz*yz+xz*xz))/(4.*G*G));
    Measure r;r.inferred_kappa=double(c.point.state.kappa)+dev;r.inferred_lambda=std::sqrt(3.)*dev;
    r.yield_continuous=mc::YieldIndependent(b,m,r.inferred_kappa);r.yield_written=mc::YieldIndependent(b,m,Kplasticc[1]);
    r.dev_error=std::fabs(dev-(c.continuous_reference-double(c.point.state.kappa)));r.stress_gap=mc::StressGap(b,c.saved_reference.stress);
    r.tensor_budget=8192.*DBL_EPSILON*(std::max)({1.,std::fabs(tr.I),tr.q,std::fabs(v.I),v.q});
    const double t=std::tan(double(m.phi)),den=std::sqrt(9.+12.*t*t),alpha=t/den;
    const double coh=double(m.cohesion_residual)+(double(m.cohesion_peak)-m.cohesion_residual)*std::exp(-double(m.cohesion_decay)*c.point.state.kappa);
    const double rootbudget=1e-10*(std::max)({1.,tr.q,std::fabs(alpha*tr.I),3.*coh/den});
    const double psi=double(m.psi0)*std::exp(-double(m.psi_decay)*r.inferred_kappa),tp=std::tan(psi),beta=tp/std::sqrt(9.+12.*tp*tp);
    mc::Need(r.stress_gap<=r.tensor_budget&&r.dev_error<=8192.*DBL_EPSILON*(std::max)(1.,dev)
      &&std::fabs(r.yield_continuous)<=4.*rootbudget,"Actual stage tensor/compliance/yield budget failed");
    mc::Need(std::fabs(v.q-(tr.q-G*r.inferred_lambda))<=r.tensor_budget
      &&std::fabs(v.I-(tr.I-9.*K*beta*r.inferred_lambda))<=r.tensor_budget
      &&std::fabs(r.inferred_lambda-c.lambda_reference)<=4096.*DBL_EPSILON*(std::max)(1.,std::fabs(c.lambda_reference)),"Actual stage q/I/lambda differs from retained radial reference");
    mc::Need(predictor?mc::Bits(Kplasticc[1],c.point.state.kappa):(mc::Bits(Kplasticc[1],c.saved_reference.kappa)&&mc::Bits(Kplasticc[1],float(r.inferred_kappa))),"Pre old-kappa/Cor commit rule failed");
    return r;
  }
public:
  Probe(const upl_material_candidate_r1::Material& m,const State& state){
    OmpThreads=1;omp_set_num_threads(1);Timersc->Config(false);Np=2;Npb=NpbOk=1;
    Simulate2D=true;TStep=STEP_Symplectic;DPCtes=DP_PS;PartBegin=0;
    HydroMech=false;PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=false;
    WithFloating=false;InOut=NULL;Shifting=NULL;NoPenetration=false;PeriActive=0;Symmetry=false;TMdbc2=MDBC2_Std;
    Gravity=TFloat3(0);RhopZero=2072.5f;RhopOutMin=700;RhopOutMax=3000;MovLimit=1;Scell=1;
    MapRealPosMin=TDouble3(-4);MapRealSize=TDouble3(8);DomCellCode=DCEL_GetCode(4,4,4);TimeStep=0;Nstep=0;
    SoilCte={};SoilCte.MaterialReturn=1;SoilCte.psiDecay=m.psi_decay;SoilCte.ModulusK=m.bulk;SoilCte.ModulusG=m.shear;
    SoilCte.phi=SoilCte.phi_r=m.phi;SoilCte.coh=m.cohesion_peak;SoilCte.coh_r=m.cohesion_residual;
    SoilCte.n_phi=0;SoilCte.n_coh=m.cohesion_decay;SoilCte.dlt=m.psi0;SoilCte.SoilTriggerFos=1;StrainSoftening=m.cohesion_decay>0;
    ArraysCpu->SetArraySize(2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_24B,4); // pos,pospre,mov,rsigma
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_16B,2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_48B,2);
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_12B,1);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_4B,4); // id,cell,kappa,ar
#ifdef CODE_SIZE4
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);
#else
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_2B,1);
#endif
    Posc=ArraysCpu->ReserveDouble3();Velrhopc=ArraysCpu->ReserveFloat4();Sigmac=ArraysCpu->ReserveSymatrix3d();
    Rsigmac=ArraysCpu->ReserveSymatrix3f();Kplasticc=ArraysCpu->ReserveFloat();Arc=ArraysCpu->ReserveFloat();Acec=ArraysCpu->ReserveFloat3();
    Idpc=ArraysCpu->ReserveUint();Dcellc=ArraysCpu->ReserveUint();Codec=ArraysCpu->ReserveTypeCode();
    for(unsigned q=0;q<2;q++){
      Idpc[q]=q;Codec[q]=(q?CODE_TYPE_FLUID:CODE_TYPE_FIXED);Dcellc[q]=0;Posc[q]=TDouble3(q?.25:-.25,0,.25);
      Velrhopc[q]=TFloat4(q?1.f/1024:0,0,q?-1.f/2048:0,RhopZero);Sigmac[q]=(q?NativeStress(state.stress):tsymatrix3d{});
      Kplasticc[q]=(q?state.kappa:0);Arc[q]=0;Acec[q]=TFloat3(0);Rsigmac[q]=tsymatrix3f{};
    }CheckScope();
  }
  void Success(const mc::Case& c,std::ostream& csv){
    const auto begin=Snap(1);ComputeSymplecticPre(Dt);CheckScope();
    mc::Need(mc::Bits(Posc[1].x,begin.p.x+double(begin.v.x)*Dt*.5)&&mc::Bits(Posc[1].z,begin.p.z+double(begin.v.z)*Dt*.5),"Actual predictor displacement differs");
    Row(csv,"radial","Pre","completed",c,CheckRadial(c,true));
    ComputeSymplecticCorr(Dt);CheckScope();
    mc::Need(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec,"Successful Pre buffers not released");
    mc::Need(mc::Bits(Posc[1].x,begin.p.x+double(begin.v.x)*Dt)&&mc::Bits(Posc[1].z,begin.p.z+double(begin.v.z)*Dt),"Actual corrector displacement differs");
    Row(csv,"radial","Cor","completed",c,CheckRadial(c,false));
  }
  void Failure(const mc::Case& apex,std::ostream& csv,std::ostream& rejected){
    ComputeSymplecticPre(Dt);CheckScope();const Snapshot before[]={Snap(0),Snap(1)};
    mc::Need(mc::Bits(Kplasticc[1],apex.point.state.kappa),"Valid elastic Pre changed old kappa");Row(csv,"apex_setup","Pre","elastic_completed",apex);
    SigmaPrec[1]=NativeStress(apex.point.state.stress); // Explicit manufactured full-stage trial, not a physical trajectory.
    const unsigned used=ArraysCpu->GetArrayCountUsed(JArraysCpu::SIZE_24B);std::string error;
    try{ComputeSymplecticCorr(Dt);}catch(const JException& e){error=e.ToStr();}catch(const std::exception& e){error=e.what();}
    rejected<<error<<'\n';rejected.flush();mc::Need(bool(rejected),"Rejection log write failed");
    const unsigned mask=1u<<unsigned(fsoil::Status::ApexNeeded);
    mc::Need(error.find("corrector")!=std::string::npos&&error.find("status mask="+std::to_string(mask))!=std::string::npos,"Actual corrector material rejection not observed");
    mc::Need(Same(0,before[0])&&Same(1,before[1])&&ArraysCpu->GetArrayCountUsed(JArraysCpu::SIZE_24B)==used,"Failed stage changed native fields/positions or leaked mov scratch");
    mc::Need(!mc::Bits(Posc[1].x,PosPrec[1].x+double(VelrhopPrec[1].x)*Dt),"Failure position witness is vacuous");CheckScope();
    Row(csv,"apex","Cor","expected_ApexNeeded",apex);
  }
};
int main(int argc,char** argv){try{
  mc::Need(argc==5&&std::string(argv[1])=="--source"&&std::string(argv[3])=="--out","Use --source ORIGINAL_POINTS.csv --out FRESH_DIR");
  const fs::path tests=fs::path(__FILE__).parent_path().parent_path(),source=argv[2],out=argv[4];
  mc::Need(tests.is_absolute()&&fs::equivalent(source,tests/"outputs/upl_material_return_CPU_result_r1/points.csv")&&!fs::exists(out),"Require original closed source and fresh output");
  const auto cases=mc::Load(source);const mc::Case *radial=nullptr,*apex=nullptr;
  for(const auto& c:cases)if(c.reference&&c.branch=="consistent_dev_decay_psi"&&c.point.material.psi0>0&&c.point.state.kappa==.5f){
    if(c.path=="preset_kappa_nonzero_shear")radial=&c;if(c.path=="hydrostatic_apex_diagnostic")apex=&c;
  }mc::Need(radial&&apex&&fs::create_directory(out),"Required retained material points absent");
  std::ofstream csv(out/"stages.csv"),rejected(out/"rejection.txt");csv<<std::setprecision(17);
  csv<<"test,phase,result,source_case_id,kappa_written,kappa_old,kappa_reference_full,x,y,z,vx,vz,native_rho,CODE,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,inferred_continuous_kappa,inferred_lambda,yield_continuous_Pa,yield_written_kappa_Pa,dev_error,reference_stress_gap_Pa,tensor_budget_Pa,TimeStep,Nstep,pool24_used\n";
  {Probe p(radial->point.material,radial->point.state);p.Success(*radial,csv);}
  const State elastic{{-20000,-20000,-20000,0,0,0},apex->point.state.kappa};
  {Probe p(apex->point.material,elastic);p.Failure(*apex,csv,rejected);}
  csv.flush();mc::Need(bool(csv),"Stage CSV final write failed");std::ofstream done(out/"completion.json");
  done<<"{\"stage\":\"upl_material_cpu_stage_r1\",\"passed\":true,\"slots\":2,\"actual_Pre_calls\":2,\"actual_Cor_calls\":2,\"radial_stage_checks\":2,\"corrector_ApexNeeded_rejections\":1,\"predictor_failure_exercised\":false,\"Pre_old_kappa_bits_preserved\":true,\"Cor_kappa_committed\":true,\"failed_Cor_native_fields_unchanged\":true,\"failed_mov_scratch_released\":true,\"no_POD_padding_compared\":true,\"global_TimeStep_Nstep_unadvanced\":true,\"spatial_force_called\":false,\"scene_or_InitRun_called\":false,\"public_softening_admission_proved\":false,\"physical_acceptance\":false}\n";
  done.flush();mc::Need(bool(done),"Completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
