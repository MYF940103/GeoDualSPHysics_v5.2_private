// Actual CPU material stages and two-level Verlet pairing; no force, scene or InitRun.
#include "JSphCpuSingle.h"
#include "JArraysCpu.h"
#include "JDsTimersCpu.h"
#include "JDsDcellDef.h"
#include "JException.h"
#include "JAppInfo.h"
#include "FunSoilMaterial.h"
#include "upl_material_unified_candidate_r1.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <omp.h>
JAppInfo AppInfo("UplMaterialStageCpu","r1","07-11-2026");
namespace fs=std::filesystem;namespace U=fsoil_unified_candidate_r1;
static unsigned Rows=0,PreCalls=0,CorCalls=0,VerletCalls=0;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static U::Stress Named(const tsymatrix3d& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static tsymatrix3d Native(const U::Stress& s){return TSymMatrix3d(s.xx,s.xy,s.xz,s.yy,s.yz,s.zz);}
static std::array<double,6> Six(const U::Stress& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static bool Same(const U::Stress& a,const U::Stress& b){const auto x=Six(a),y=Six(b);for(unsigned i=0;i<6;i++)if(!Bits(x[i],y[i]))return false;return true;}
static double Gap(const U::Stress& a,const U::Stress& b){const auto x=Six(a),y=Six(b);double e=0;for(unsigned i=0;i<6;i++)e=(std::max)(e,std::abs(x[i]-y[i]));return e;}
struct Inv{double I,q;};
static Inv Invariant(const U::Stress& s){const double I=s.xx+s.yy+s.zz,m=I/3.;return {I,std::sqrt(.5*((s.xx-m)*(s.xx-m)+(s.yy-m)*(s.yy-m)+(s.zz-m)*(s.zz-m)+2.*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)))};}
struct DP{double alpha,kc,beta;};
static DP Coeff(const U::Material& m,double k,TpDPCtes fit){
  const double p=m.phi_r+(double(m.phi_p)-m.phi_r)*std::exp(-double(m.n_p)*k),c=m.coh_r+(double(m.coh_p)-m.coh_r)*std::exp(-double(m.n_c)*k),b=double(m.psi0)*std::exp(-double(m.sf)*k);
  if(fit==DP_PS){const double t=std::tan(p),u=std::tan(b);return {t/std::sqrt(9.+12.*t*t),3.*c/std::sqrt(9.+12.*t*t),u/std::sqrt(9.+12.*u*u)};}
  const double sign=fit==DP_MC?1.:-1.,r=std::sqrt(3.);return {2.*std::sin(p)/(r*(3.+sign*std::sin(p))),6.*c*std::cos(p)/(r*(3.+sign*std::sin(p))),2.*std::sin(b)/(r*(3.+sign*std::sin(b)))};
}
static U::Stress Make(double I,double q){return {I/3.+q,I/3.-q,I/3.,0,0,0};}
static U::Stress Rotate(const U::Stress& s){
  const double r[3][3]={{1./9,8./9,4./9},{8./9,1./9,-4./9},{-4./9,4./9,-7./9}},a[3][3]={{s.xx,s.xy,s.xz},{s.xy,s.yy,s.yz},{s.xz,s.yz,s.zz}};double b[3][3]{};
  for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)for(unsigned k=0;k<3;k++)for(unsigned l=0;l<3;l++)b[i][j]+=r[i][k]*a[k][l]*r[j][l];return {b[0][0],b[1][1],b[2][2],b[0][1],b[1][2],b[0][2]};
}
static float Rad(double d){return float(d*3.1415926535897932384626433832795/180.);}
static U::Material Law(float psi,bool soft){const float E=20e6f,n=.33f;return {float(double(E)/(3.*(1.-2.*double(n)))),float(double(E)/(2.*(1.+double(n)))),Rad(25),Rad(soft?20:25),soft?5.f:0.f,5000,soft?1000.f:5000.f,soft?5.f:0.f,Rad(psi),soft?.2f:0.f};}
struct Case{std::string name;U::Material reference;StSoilCte soil;TpDPCtes fit;U::Stress fulltrial;float old=.02f;bool soft=false,trigger=false,fluid=false;};
static StSoilCte Soil(const U::Material& m){StSoilCte s{};s.ModulusE=20e6f;s.ModulusK=m.ModulusK;s.ModulusG=m.ModulusG;s.phi=m.phi_p;s.phi_r=m.phi_r;s.n_phi=m.n_p;s.coh=m.coh_p;s.coh_r=m.coh_r;s.n_coh=m.n_c;s.dlt=m.psi0;s.psiDecay=m.sf;s.SoilTriggerFos=1;return s;}
static Case Smooth(std::string name,U::Material m,TpDPCtes fit){
  Case c{};c.name=name;c.reference=m;c.soil=Soil(m);c.fit=fit;c.soft=m.n_p>0||m.n_c>0;
  const double lambda=.001,k=double(c.old)+lambda/std::sqrt(3.);const auto d=Coeff(m,k,fit);const double I=-60000.,q=d.kc-d.alpha*I;c.fulltrial=Rotate(Make(I+9.*double(m.ModulusK)*d.beta*lambda,q+double(m.ModulusG)*lambda));return c;
}
static std::vector<Case> Cases(){std::vector<Case> v;
  for(auto fit:{DP_PS,DP_C,DP_MC})for(bool soft:{false,true})v.push_back(Smooth(std::string(soft?"soft_":"basic_")+std::to_string(unsigned(fit)),Law(fit==DP_PS?0.f:fit==DP_C?2.5f:-5.f,soft),fit));
  {auto m=Law(2.5f,true);m.phi_p=m.phi_r=0;m.n_p=0;v.push_back(Smooth("phi0_soft",m,DP_PS));}
  {auto m=Law(2.5f,false);m.sf=.2f;auto c=Smooth("sf_only_no_FOS",m,DP_PS);c.trigger=true;c.soil.SoilTriggerFos=2;c.soil.coh_r=4500;v.push_back(c);}
  {auto m=Law(2.5f,true);m.coh_p=m.coh_r=2500;m.n_c=0;m.sf=0;auto c=Smooth("phi_only_FOS_unused_cr",m,DP_C);c.trigger=true;c.soil.coh=5000;c.soil.coh_r=4500;c.soil.SoilTriggerFos=2;v.push_back(c);}
  {auto m=Law(2.5f,true);Case c{};c.name="positive_apex_dev_saturated";c.reference=m;c.soil=Soil(m);c.fit=DP_PS;c.soft=true;const auto d=Coeff(m,c.old,c.fit);c.fulltrial=Make(d.kc/d.alpha+9.*double(m.ModulusK)*d.beta*.01,0);v.push_back(c);}
  {Case c{};c.name="no_soil_zero_moduli";c.fit=DP_PS;c.fluid=true;c.old=0;v.push_back(c);}Need(v.size()==11,"Success point count changed");return v;
}
class Probe:public JSphCpuSingle{
  static constexpr double Dt=.125; // Manufactured stage arithmetic, not a stable physical timestep.
  struct Saved{tdouble3 p;tfloat4 v;U::Stress s;float k;typecode code;unsigned cell;};
  Saved Snap(unsigned q)const{return {Posc[q],Velrhopc[q],Named(Sigmac[q]),Kplasticc[q],Codec[q],Dcellc[q]};}
  bool SameSlot(unsigned q,const Saved& a)const{const auto b=Snap(q);return Bits(a.p.x,b.p.x)&&Bits(a.p.y,b.p.y)&&Bits(a.p.z,b.p.z)&&Bits(a.v.x,b.v.x)&&Bits(a.v.y,b.v.y)&&Bits(a.v.z,b.v.z)&&Bits(a.v.w,b.v.w)&&Same(a.s,b.s)&&Bits(a.k,b.k)&&a.code==b.code&&a.cell==b.cell;}
  void Scope()const{Need(TimeStep==0&&Nstep==0&&Np==2&&Npb==1&&!HydroMech&&!PorosityObserver&&!PorosityFeedback&&!PorePressc&&!PoroJc,"Actual component scope changed");}
  U::Stress Trial(const tsymatrix3d& base,double dt)const{auto t=base;t.xx+=Rsigmac[1].xx*dt;t.yy+=Rsigmac[1].yy*dt;t.zz+=Rsigmac[1].zz*dt;t.xy+=Rsigmac[1].xy*dt;t.yz+=Rsigmac[1].yz*dt;t.xz+=Rsigmac[1].xz*dt;return Named(t);}
  U::Result Reference(const Case& c,const U::Stress& trial,float old)const{if(c.fluid){U::Result r{};r.state={trial,old};r.status=U::Status::Elastic;r.kappa_continuous=old;return r;}return U::ConsRelationEPsft({trial,old},c.reference,c.fit);}
  void Row(std::ostream& o,const Case& c,const char* stage,const U::Stress& trial,float old,const U::Result& ref,bool pre)const{
    const auto actual=Named(Sigmac[1]);const auto t=Invariant(trial),n=Invariant(actual);double se=Gap(actual,ref.state.stress),dev=0,ve=0,yc=0,ys=0;
    const double sb=8192.*DBL_EPSILON*(std::max)({1.,std::fabs(t.I),t.q,std::fabs(n.I),n.q}),eb=8192.*DBL_EPSILON;
    Need(U::CommitAllowed(ref.status)&&se<=sb,"Actual stage/referenceU stress mismatch");
    Need(Bits(Kplasticc[1],pre?old:ref.state.kappa),"Actual Pre restore/Cor or Verlet commit differs");
    if(!c.fluid){const double dx=trial.xx-actual.xx,dy=trial.yy-actual.yy,dz=trial.zz-actual.zz,m=(dx+dy+dz)/3.,xy=trial.xy-actual.xy,yz=trial.yz-actual.yz,xz=trial.xz-actual.xz,G=c.reference.ModulusG,K=c.reference.ModulusK;
      dev=std::sqrt((2./3.)*((dx-m)*(dx-m)+(dy-m)*(dy-m)+(dz-m)*(dz-m)+2.*(xy*xy+yz*yz+xz*xz)))/(2.*G);const auto d=Coeff(c.reference,ref.kappa_continuous,c.fit);
      ve=std::fabs((t.I-n.I)/(3.*K)-3.*(d.beta*ref.lambda_shear+ref.lambda_tension));yc=n.q+d.alpha*n.I-d.kc;const auto ds=Coeff(c.reference,Kplasticc[1],c.fit);ys=n.q+ds.alpha*n.I-ds.kc;
      Need(std::fabs(dev-(ref.kappa_continuous-double(old)))<=eb*(std::max)(1.,dev)&&ve<=eb*(std::max)(1.,std::fabs((t.I-n.I)/(3.*K))),"Independent plastic compliance failed");
      const auto d0=Coeff(c.reference,old,c.fit);const double rb=1e-10*(std::max)({1.,t.q,std::fabs(d0.alpha*t.I),std::fabs(d0.kc)});Need(ref.status==U::Status::Elastic||std::fabs(yc)<=4.*rb,"Continuous-history yield budget failed");
    }else Need(Same(actual,trial)&&Bits(Kplasticc[1],old),"Zero-material stage changed state");
    o<<c.name<<','<<stage<<','<<unsigned(c.fit)<<','<<unsigned(ref.status)<<','<<old<<','<<Kplasticc[1]<<','<<ref.kappa_continuous<<','<<ref.lambda_shear<<','<<ref.lambda_tension<<','<<dev<<','<<ve<<','<<yc<<','<<ys<<','<<se<<','<<sb;for(auto x:Six(actual))o<<','<<x;o<<','<<TimeStep<<','<<Nstep<<'\n';o.flush();Need(bool(o),"Stage CSV write failed");Rows++;Scope();
  }
public:
  Probe(const Case& c,bool verlet=false){
    OmpThreads=1;omp_set_num_threads(1);Timersc->Config(false);Np=2;Npb=NpbOk=1;Simulate2D=c.fit==DP_PS;TStep=verlet?STEP_Verlet:STEP_Symplectic;DPCtes=c.fit;PartBegin=c.trigger?1:0;StrainSoftening=c.soft;SoilCte=c.soil;
    HydroMech=PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=false;WithFloating=false;InOut=NULL;Shifting=NULL;NoPenetration=false;PeriActive=0;Symmetry=false;TMdbc2=MDBC2_Std;
    Gravity=TFloat3(0);RhopZero=2072.5f;RhopOutMin=700;RhopOutMax=3000;MovLimit=1;Scell=1;MapRealPosMin=TDouble3(-4);MapRealSize=TDouble3(8);DomCellCode=DCEL_GetCode(4,4,4);TimeStep=0;Nstep=0;
    ArraysCpu->SetArraySize(2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_24B,4);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_16B,2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_48B,2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_12B,1);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_4B,verlet?5:4);
#ifdef CODE_SIZE4
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);
#else
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_2B,1);
#endif
    Posc=ArraysCpu->ReserveDouble3();Velrhopc=ArraysCpu->ReserveFloat4();Sigmac=ArraysCpu->ReserveSymatrix3d();Rsigmac=ArraysCpu->ReserveSymatrix3f();Kplasticc=ArraysCpu->ReserveFloat();Arc=ArraysCpu->ReserveFloat();Acec=ArraysCpu->ReserveFloat3();Idpc=ArraysCpu->ReserveUint();Dcellc=ArraysCpu->ReserveUint();Codec=ArraysCpu->ReserveTypeCode();
    if(verlet){VelrhopM1c=ArraysCpu->ReserveFloat4();SigmaM1c=ArraysCpu->ReserveSymatrix3d();KplasticM1c=ArraysCpu->ReserveFloat();}
    for(unsigned q=0;q<2;q++){Idpc[q]=q;Codec[q]=q?CODE_TYPE_FLUID:CODE_TYPE_FIXED;Dcellc[q]=0;Posc[q]=TDouble3(q?.25:-.25,0,.25);Velrhopc[q]=TFloat4(q?1.f/1024:0,0,q?-1.f/2048:0,RhopZero);Sigmac[q]=q?Native(c.fulltrial):tsymatrix3d{};Kplasticc[q]=q?c.old:0;Arc[q]=0;Acec[q]=TFloat3(0);Rsigmac[q]=tsymatrix3f{};
      if(q&&!c.fluid){Rsigmac[q].xx=8192;Rsigmac[q].yy=-8192;Sigmac[q].xx-=Rsigmac[q].xx*Dt;Sigmac[q].yy-=Rsigmac[q].yy*Dt;}
      if(verlet){VelrhopM1c[q]=Velrhopc[q];SigmaM1c[q]=Sigmac[q];KplasticM1c[q]=Kplasticc[q];}}
    Scope();
  }
  void Success(const Case& c,std::ostream& out){const auto base=Sigmac[1];const auto wall=Snap(0);const auto pretrial=Trial(base,Dt*.5),fulltrial=Trial(base,Dt);const auto a=Reference(c,pretrial,c.old),b=Reference(c,fulltrial,c.old);
    PreCalls++;ComputeSymplecticPre(Dt);Need(SameSlot(0,wall),"Pre changed defined fixed slot");Row(out,c,"Pre",pretrial,c.old,a,true);
    CorCalls++;ComputeSymplecticCorr(Dt);Need(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&SameSlot(0,wall),"Cor scratch or fixed slot changed");Row(out,c,"Cor",fulltrial,c.old,b,false);
  }
  void Reject(const Case& c,std::ostream& out,std::ostream& errors){
    const auto trial=Trial(Sigmac[1],Dt*.5);const auto ref=Reference(c,trial,c.old);PreCalls++;ComputeSymplecticPre(Dt);Row(out,c,"Reject_setup_Pre",trial,c.old,ref,true);const Saved before[]={Snap(0),Snap(1)};SoilCte.n_phi=SoilCte.n_coh=1e6f;SoilCte.phi_r=Rad(20);SoilCte.coh_r=1000;StrainSoftening=true;SigmaPrec[1]=Native(Make(-60000,100000));
    const auto used=ArraysCpu->GetArrayCountUsed(JArraysCpu::SIZE_24B);std::string error;CorCalls++;try{ComputeSymplecticCorr(Dt);}catch(const JException& e){error=e.ToStr();}catch(const std::exception& e){error=e.what();}
    errors<<error<<'\n';errors.flush();Need(bool(errors)&&error.find("corrector")!=std::string::npos&&error.find("status mask="+std::to_string(1u<<unsigned(fsoil::Status::UnresolvedPath)))!=std::string::npos,"Expected actual UnresolvedPath was not rejected");
    Need(SameSlot(0,before[0])&&SameSlot(1,before[1])&&used==ArraysCpu->GetArrayCountUsed(JArraysCpu::SIZE_24B),"Rejected Cor changed completed native state or leaked mov scratch");out<<"uncertified,Cor_rejected,"<<unsigned(DPCtes)<<','<<unsigned(fsoil::Status::UnresolvedPath)<<','<<c.old<<','<<Kplasticc[1];for(unsigned q=6;q<15;q++)out<<',';for(auto x:Six(Named(Sigmac[1])))out<<','<<x;out<<','<<TimeStep<<','<<Nstep<<'\n';out.flush();Need(bool(out),"Rejection row write failed");Rows++;Scope();
  }
  void VerletPair(const Case& c,bool reset,std::ostream& out){
    const auto base=Sigmac[1];if(reset){SigmaM1c[1]=Native(Make(-40000,3000));KplasticM1c[1]=.75f;}else{SigmaM1c[1]=base;KplasticM1c[1]=c.old;Sigmac[1]=Native(Make(-40000,3000));Kplasticc[1]=.75f;}
    const auto current=Sigmac[1];const float currentk=Kplasticc[1];const auto oldptr=Kplasticc,m1ptr=KplasticM1c;const auto trial=Trial(reset?Sigmac[1]:SigmaM1c[1],reset?Dt:Dt+Dt);const float old=reset?Kplasticc[1]:KplasticM1c[1];const auto ref=Reference(c,trial,old);VerletSteps=40;VerletStep=reset?39:0;
    VerletCalls++;ComputeVerlet(Dt);Need(Kplasticc==m1ptr&&KplasticM1c==oldptr&&Bits(KplasticM1c[1],currentk)&&Same(Named(SigmaM1c[1]),Named(current))&&VerletStep==(reset?0:1),"Verlet paired output/swap/reset differs");Row(out,c,reset?"Verlet_reset_dt":"Verlet_2dt",trial,old,ref,false);
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path())&&fs::create_directory(out),"Fresh result required");std::ofstream csv(out/"stages.csv"),errors(out/"rejection.txt");csv<<std::setprecision(17)<<"case,stage,fit,reference_status,kappa_base,kappa_written,kappa_continuous,lambda_shear,lambda_tension,dev_compliance,volume_error,yield_continuous_Pa,yield_written_Pa,referenceU_stress_gap_Pa,tensor_budget_Pa,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,TimeStep,Nstep\n";
  const auto cases=Cases();for(const auto& c:cases){Probe p(c);p.Success(c,csv);}
  Case reject=Smooth("uncertified",Law(0,true),DP_PS);reject.old=0;reject.fulltrial=Make(-20000,0);{Probe p(reject);p.Reject(reject,csv,errors);}
  for(bool reset:{false,true}){Probe p(cases[0],true);p.VerletPair(cases[0],reset,csv);}csv.flush();Need(bool(csv)&&Rows==26&&PreCalls==12&&CorCalls==12&&VerletCalls==2,"Actual stage call/row coverage differs");
  std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_material_stage_cpu_r1\",\"passed\":true,\"manufactured_points\":14,\"rows\":"<<Rows<<",\"actual_Pre_calls\":"<<PreCalls<<",\"actual_Cor_calls\":"<<CorCalls<<",\"actual_Verlet_calls\":"<<VerletCalls<<",\"three_fits\":true,\"phi_zero\":true,\"Pre_old_kappa_bits\":true,\"Cor_reference_and_compliance\":true,\"Verlet_only_pairing_not_general_irreversibility\":true,\"original_startup_strategy_unchanged\":true,\"InitRun_or_force_called\":false,\"spatial_3D_admission\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
