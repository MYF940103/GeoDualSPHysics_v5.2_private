// Private, nonadvancing CPU interaction component; no public initialization or MLS test.
#include "JSphCpuSingle.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <omp.h>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("UplSprAvPairCpu","r1","03-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
// Declared before execution. No dimensional absolute tolerance or old Near floor.
static constexpr double Eps=std::numeric_limits<float>::epsilon();
static constexpr double ForceUlps=64.,BalanceUlps=128.,WorkUlps=256.;
static unsigned long long KernelCalls=0;
static double AbsMax(tdouble3 a){return (std::max)({fabs(a.x),fabs(a.y),fabs(a.z)});}
static bool Zero(tfloat3 a){return a==TFloat3(0);}
static tdouble3 Delta(tfloat3 a,tfloat3 b){return ToTDouble3(a)-ToTDouble3(b);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double Scaled(double error,double scale,double ulps){
  if(!std::isfinite(error)||!std::isfinite(scale)||scale<0)return std::numeric_limits<double>::infinity();
  const double budget=ulps*Eps*scale;
  return budget>0? fabs(error)/budget: (error==0?0:std::numeric_limits<double>::infinity());
}
struct Spec{
  bool wall=false,feedback=true,scratch=false;std::string motion;
  double j[2]={1,1};float legacy[2]={2,2},mass=1,alpha=.125f;
  float vx[2]={0,0},vz[2]={.125f,-.125f},tangentx=0,tangentz=0,auxx=.5f,auxz=.75f;
};
static bool Approach(const Spec& s){
  const double dx=s.wall?s.vx[1]-s.tangentx:s.vx[1]-s.vx[0];
  const double dz=s.wall?s.vz[1]-s.tangentz:s.vz[1]-s.vz[0];
  return .0625*dx+.125*dz<0; // Actual oblique separation dotted with configured physical dv_visc.
}
struct Sample{
  tfloat3 ace[2]={};tsymatrix3f stress[2]={};float ar[2]={},pore[2]={};
  double theta[2]={},rho[2]={},volume[2]={},mi[2]={};float viscdt=0;
  bool wall_receiver_untouched=true;
};
class Pair:public JSphCpuSingle{
  byte modes[2]={BMODE_MDBC2,BMODE_MDBC2};
  tfloat3 tangents[2]={},auxiliary[2]={},wallnormals[2]={TFloat3(0,0,1),TFloat3(0)};
  double jstate[2]={1,1},theta[2]={};
public:
  Pair(){
    OmpThreads=1;omp_set_num_threads(1);Np=2;Npb=NpbOk=0;
    Simulate2D=true;TKernel=KERNEL_Wendland;TVisco=VISCO_Artificial;TDensity=DDT_None;
    FtMode=FTMODE_None;UseDEM=false;Symmetry=false;ArtificialStress=false;Shifting=nullptr;
    TBoundary=BC_MDBC;TMdbc2=MDBC2_Std;SlipMode=SLIP_FreeSlip;
    HydroMech=true;HydroMechDynamicSeepage=false;HydroMechDrainage=false;HydroMechTopLoadMode=HMLOAD_None;
    SoilBoundaryDerivativeSPR=false;SoilHourglassXi=0;SoilDamping=false;
    SoilStressRateGradCorr=true;PoreCompressionGradCorr=true;PoreCompressionSourceMode=0;PoreDarcySymmetricCorr=false;
    PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=DynamicPoreConductivity=false;
    PoroJc=PoroThetac=PoroJPrec=nullptr;BoundDerivativeVelc=nullptr;
    SoilCte={};SoilCte.ModulusK=16;SoilCte.ModulusG=8;
    SoilCte.PoreWaterBulkModulus=128;SoilCte.Porosity=.5f;SoilCte.PoreWaterRho=1;
    Dp=.125;KernelH=.25f;KernelSize=.5f;KernelSize2=.25f;
    MassFluid=MassBound=1;RhopZero=2;Cs0=4;Eta2=(.1f*KernelH)*(.1f*KernelH);
    Gravity=TFloat3(0);Visco=.125f;ViscoBoundFactor=1;BoundModec=modes;TangenVelc=tangents;BoundNormalc=wallnormals;
  }
  ~Pair(){
    BoundModec=nullptr;TangenVelc=nullptr;BoundDerivativeVelc=nullptr;BoundNormalc=nullptr;
    PoroJc=PoroThetac=PoroJPrec=nullptr;DivData=DivDataCpuNull();
  }
  Sample run(const Spec& s){
    Check(s.j[0]>.5&&s.j[1]>.5&&s.mass>0&&s.legacy[0]>0&&s.legacy[1]>0,"Invalid component state");
    Np=2;Npb=s.wall?1:0;NpbOk=0;MassFluid=MassBound=s.mass;Visco=s.alpha;
    PorosityObserver=PorosityFeedback=s.feedback;DynamicPorePressure=DynamicPoreWall=DynamicPoreConductivity=false;
    SoilBoundaryDerivativeSPR=false;jstate[0]=s.j[0];jstate[1]=s.j[1];theta[0]=theta[1]=0;
    PoroJc=jstate;PoroThetac=s.feedback?theta:nullptr;PoroJPrec=nullptr;
    tangents[0]=TFloat3(s.tangentx,0,s.tangentz);tangents[1]=TFloat3(0);
    auxiliary[0]=TFloat3(s.auxx,0,s.auxz);auxiliary[1]=TFloat3(0);
    BoundDerivativeVelc=s.scratch?auxiliary:nullptr;
    CSP=CteSphNull();CSP.simulate2d=true;CSP.tkernel=TKernel;
    CSP.kwend=fsph::GetKernelWendland_Ctes(true,KernelH);CSP.kernelh=KernelH;
    CSP.massbound=MassBound;CSP.massfluid=MassFluid;CSP.rhopzero=RhopZero;
    const unsigned begin[4]={0,Npb,Npb,2},dcell[2]={0,0},id[2]={0,1};
    const unsigned fst[2]={unsigned(s.wall?FST_Boundary:FST_Inner),FST_Inner};
    const typecode code[2]={typecode(s.wall?CODE_TYPE_FIXED:CODE_TYPE_FLUID),CODE_TYPE_FLUID};
    const tdouble3 pos[2]={TDouble3(.25,.25,.25),TDouble3(.3125,.25,.375)};
    const tfloat4 velocity[2]={TFloat4(s.vx[0],0,s.vz[0],s.legacy[0]),TFloat4(s.vx[1],0,s.vz[1],s.legacy[1])};
    const float pressure[2]={0,0},pore[2]={0,0};float rate[2]={0,0},ar[2]={0,0};
    tfloat3 ace[2]={},normal[2]={};tsymatrix3d sigma[2]={};tsymatrix3f stress[2]={};
    tmatrix3d I={};I.a11=I.a22=I.a33=1;tmatrix3d corr[2]={I,I};
    DivData=MakeDivDataCpu(1,TUint3(1,1,1),TUint3(0),begin,.5f,DCEL_GetCode(1,1,1),TDouble3(0));
    const auto parms=StInterparmsc(2,Npb,NpbOk,DivData,dcell,pos,velocity,id,code,pressure,pore,rate,fst,normal,nullptr,corr,
      ar,ace,nullptr,SHIFT_None,nullptr,nullptr,nullptr,sigma,stress,nullptr);
    StInterResultc result={0};Interaction_Forces_ct(parms,result);KernelCalls++;
    Sample r;r.viscdt=result.viscdt;
    for(unsigned p=0;p<2;p++){
      r.ace[p]=ace[p];r.stress[p]=stress[p];r.ar[p]=ar[p];r.pore[p]=rate[p];r.theta[p]=theta[p];
      if(s.feedback){double n;GetPorosityFeedbackStateCpu(p,n,r.volume[p],r.rho[p]);r.mi[p]=r.volume[p]*r.rho[p];}
      else{r.rho[p]=s.legacy[p];r.mi[p]=s.mass;r.volume[p]=double(s.mass)/s.legacy[p];}
    }
    r.wall_receiver_untouched=!s.wall||(Zero(ace[0])&&ar[0]==0&&rate[0]==0&&theta[0]==0);
    PoroJc=PoroThetac=nullptr;BoundDerivativeVelc=nullptr;DivData=DivDataCpuNull();
    return r;
  }
};
struct Row{
  Spec spec;unsigned receiver=0;Sample on,off,legacy_on,legacy_off,rhop_on,rhop_off,scratch_on,scratch_off;
  tdouble3 force=TDouble3(0),reference=TDouble3(0),residual=TDouble3(0);
  double reference_mass=0,work=0,reference_work=0,force_scaled=0,rhop_scaled=0,scratch_scaled=0,balance_scaled=0,work_scaled=0;
  double derivative_change=0;bool exact_zero_controls=true,passed=true;
};
static double Compare(const Sample& a,const Sample& b,const Sample& c,const Sample& d,unsigned p,double mi){
  const double x[3]={a.ace[p].x,a.ace[p].y,a.ace[p].z},y[3]={b.ace[p].x,b.ace[p].y,b.ace[p].z};
  const double z[3]={c.ace[p].x,c.ace[p].y,c.ace[p].z},w[3]={d.ace[p].x,d.ace[p].y,d.ace[p].z};double scaled=0;
  for(unsigned k=0;k<3;k++)scaled=(std::max)(scaled,Scaled(mi*((x[k]-y[k])-(z[k]-w[k])),
    mi*(fabs(x[k])+fabs(y[k])+fabs(z[k])+fabs(w[k])),ForceUlps));
  return scaled;
}
static double DerivativeChange(const Sample& a,const Sample& b,unsigned p){
  const auto x=a.stress[p],y=b.stress[p];
  return (std::max)({fabs(double(x.xx)-y.xx),fabs(double(x.yy)-y.yy),fabs(double(x.zz)-y.zz),
    fabs(double(x.xy)-y.xy),fabs(double(x.yz)-y.yz),fabs(double(x.xz)-y.xz),fabs(double(a.ar[p])-b.ar[p]),
    fabs(double(a.pore[p])-b.pore[p]),fabs(a.theta[p]-b.theta[p])});
}
static void Evaluate(Pair& pair,const Spec& s,std::vector<Row>& rows){
  Spec zero=s;zero.alpha=0;const auto on=pair.run(s),off=pair.run(zero);
  Spec changed=s;changed.legacy[0]=.75f;changed.legacy[1]=7.f;const auto rhop_on=pair.run(changed);
  changed.alpha=0;const auto rhop_off=pair.run(changed);
  Sample scratch_on=on,scratch_off=off;
  if(s.wall){changed=s;changed.scratch=!s.scratch;scratch_on=pair.run(changed);changed.alpha=0;scratch_off=pair.run(changed);}
  std::vector<Row> current;
  for(unsigned p=s.wall?1:0;p<2;p++){
    Row r;r.spec=s;r.receiver=p;r.on=on;r.off=off;r.rhop_on=rhop_on;r.rhop_off=rhop_off;r.scratch_on=scratch_on;r.scratch_off=scratch_off;
    // Oracle is the actual old compiled interaction, once per receiver: its global mass is this neighbor current mi.
    Spec legacy=s;legacy.feedback=false;legacy.mass=float(on.mi[1-p]);
    legacy.legacy[0]=float(on.rho[0]);legacy.legacy[1]=float(on.rho[1]);r.reference_mass=legacy.mass;
    r.legacy_on=pair.run(legacy);legacy.alpha=0;r.legacy_off=pair.run(legacy);
    r.force=Delta(on.ace[p],off.ace[p])*on.mi[p];r.reference=Delta(r.legacy_on.ace[p],r.legacy_off.ace[p])*on.mi[p];
    r.force_scaled=Compare(on,off,r.legacy_on,r.legacy_off,p,on.mi[p]);
    r.rhop_scaled=Compare(on,off,rhop_on,rhop_off,p,on.mi[p]);
    r.scratch_scaled=Compare(on,off,scratch_on,scratch_off,p,on.mi[p]);
    r.derivative_change=s.wall?DerivativeChange(on,scratch_on,p):0;
    const bool approach=Approach(s);
    r.exact_zero_controls=Zero(off.ace[p])&&Zero(rhop_off.ace[p])&&Zero(scratch_off.ace[p])&&Zero(r.legacy_off.ace[p]);
    if(!approach)r.exact_zero_controls=r.exact_zero_controls&&Zero(on.ace[p])&&Zero(rhop_on.ace[p])&&Zero(scratch_on.ace[p])&&Zero(r.legacy_on.ace[p]);
    r.passed=r.exact_zero_controls&&on.wall_receiver_untouched&&off.wall_receiver_untouched&&
      rhop_on.wall_receiver_untouched&&rhop_off.wall_receiver_untouched&&scratch_on.wall_receiver_untouched&&scratch_off.wall_receiver_untouched&&
      r.legacy_on.wall_receiver_untouched&&r.legacy_off.wall_receiver_untouched&&r.force_scaled<=1&&r.rhop_scaled<=1&&r.scratch_scaled<=1&&
      (!s.wall||r.derivative_change>0)&&(!approach||AbsMax(r.force)>0);
    current.push_back(r);
  }
  tdouble3 total=TDouble3(0);double work=0,reference_work=0,work_scale=0,balance=0;
  for(const auto& r:current){
    const tdouble3 v=s.wall?TDouble3(s.vx[1]-s.tangentx,0,s.vz[1]-s.tangentz):TDouble3(s.vx[r.receiver],0,s.vz[r.receiver]);
    total=total+r.force;work+=Dot(r.force,v);reference_work+=Dot(r.reference,v);
    work_scale+=fabs(r.force.x*v.x)+fabs(r.force.z*v.z)+fabs(r.reference.x*v.x)+fabs(r.reference.z*v.z);
  }
  if(!s.wall){
    const double a[3]={current[0].force.x,current[0].force.y,current[0].force.z};
    const double b[3]={current[1].force.x,current[1].force.y,current[1].force.z};
    for(unsigned k=0;k<3;k++)balance=(std::max)(balance,Scaled(a[k]+b[k],fabs(a[k])+fabs(b[k]),BalanceUlps));
  }
  for(auto& r:current){
    r.residual=total;r.work=work;r.reference_work=reference_work;r.balance_scaled=balance;
    r.work_scaled=Scaled(work-reference_work,work_scale,WorkUlps);
    const bool approach=Approach(s);
    r.passed=r.passed&&balance<=1&&r.work_scaled<=1&&work<=WorkUlps*Eps*work_scale&&(!approach||work<0);
    rows.push_back(r);
  }
}
static void Write3(std::ostream& out,tdouble3 a){out<<','<<a.x<<','<<a.y<<','<<a.z;}
static void JsonNumber(std::ostream& out,double value){if(std::isfinite(value))out<<value;else out<<"null";}
int main(int argc,char** argv){
  try{
    if(argc==1||std::string(argv[1])=="--help"){
      std::cout<<"upl_spr_av_pair_cpu_r1 --out NEW_DIRECTORY\nPrivate actual CPU interaction; no advancement, Darcy, MLS or public initialization.\n";return 0;}
    Check(argc==3&&std::string(argv[1])=="--out","Expected --out NEW_DIRECTORY");
    const fs::path out=argv[2];Check(!fs::exists(out),"Refusing overwrite");fs::create_directories(out);
    Pair pair;std::vector<Row> rows;unsigned trials=0;
    const double states[3][2]={{1,1},{.75,1.25},{.625,1.5}};
    for(bool wall:{false,true})for(const auto& j:states)for(int motion:{-1,0,1})for(unsigned scratch=0;scratch<(wall?2u:1u);scratch++){
      Spec s;s.wall=wall;s.scratch=scratch!=0;s.j[0]=j[0];s.j[1]=j[1];
      s.motion=motion<0?"approach":(motion>0?"recession":"rest");
      s.vz[0]=wall?.375f:-.125f*motion;s.vz[1]=wall?.25f*motion:.125f*motion;
      Evaluate(pair,s,rows);trials++;
    }
    // Manual coherent tangential translation, not an MLS or wall-producer test.
    for(int sign:{-1,1})for(bool scratch:{false,true}){
      Spec s;s.wall=true;s.scratch=scratch;s.j[0]=.75;s.j[1]=1.25;s.motion=sign<0?"manual_tangent_minus":"manual_tangent_plus";
      s.vx[0]=s.vx[1]=s.tangentx=.125f*sign;s.vz[0]=s.vz[1]=0;
      Evaluate(pair,s,rows);trials++;
    }
    bool passed=true,exact=true;double max_force=0,max_rhop=0,max_scratch=0,max_balance=0,max_work=0;
    for(const auto& r:rows){
      passed=passed&&r.passed;exact=exact&&r.exact_zero_controls;
      max_force=(std::max)(max_force,r.force_scaled);max_rhop=(std::max)(max_rhop,r.rhop_scaled);max_scratch=(std::max)(max_scratch,r.scratch_scaled);
      max_balance=(std::max)(max_balance,r.balance_scaled);max_work=(std::max)(max_work,r.work_scaled);
    }
    std::ofstream csv(out/"pairs.csv");csv<<std::setprecision(17)
      <<"trial,wall,derivative_scratch_present,receiver,J0,J1,legacy_rho0,legacy_rho1,mutated_legacy_rho0,mutated_legacy_rho1,reference_M0,current_rho0,current_rho1,current_V0,current_V1,current_m0,current_m1,oracle_neighbor_mass,oracle_legacy_rho0,oracle_legacy_rho1,alpha,v0_x,v1_x,v0_z,v1_z,tangent_x,tangent_z,aux_x,aux_z,configured_dv_visc_x,configured_dv_visc_z,configured_dv_deriv_x,configured_dv_deriv_z"
      <<",actual_on_ax,actual_on_ay,actual_on_az,actual_off_ax,actual_off_ay,actual_off_az,oracle_on_ax,oracle_on_ay,oracle_on_az,oracle_off_ax,oracle_off_ay,oracle_off_az"
      <<",rhop_mutated_on_ax,rhop_mutated_on_ay,rhop_mutated_on_az,rhop_mutated_off_ax,rhop_mutated_off_ay,rhop_mutated_off_az,scratch_other_on_ax,scratch_other_on_ay,scratch_other_on_az,scratch_other_off_ax,scratch_other_off_ay,scratch_other_off_az"
      <<",current_mi_AV_force_x,current_mi_AV_force_y,current_mi_AV_force_z,oracle_force_x,oracle_force_y,oracle_force_z,fluid_pair_sum_or_wall_fluid_force_x,fluid_pair_sum_or_wall_fluid_force_y,fluid_pair_sum_or_wall_fluid_force_z"
      <<",ar,pore_rate,theta,rsigma_xx,rsigma_yy,rsigma_zz,rsigma_xy,rsigma_yz,rsigma_xz,scratch_other_ar,scratch_other_pore_rate,scratch_other_theta,scratch_other_rsigma_xx,scratch_other_rsigma_yy,scratch_other_rsigma_zz,scratch_other_rsigma_xy,scratch_other_rsigma_yz,scratch_other_rsigma_xz,viscdt,work,oracle_work,force_scaled_error,rhop_scaled_error,scratch_scaled_error,current_mi_pair_scaled_residual,work_scaled_error,scratch_derivative_change,exact_zero_controls,J1_legacy_case,max_scaled_force_error,max_scaled_rhop_error,max_scaled_scratch_error,max_scaled_current_mi_pair_residual,max_scaled_work_error,passed\n";
    for(const auto& r:rows){const auto& s=r.spec;const unsigned p=r.receiver;const auto z=r.on.stress[p],other=r.scratch_on.stress[p];
      csv<<s.motion<<','<<s.wall<<','<<s.scratch<<','<<p<<','<<s.j[0]<<','<<s.j[1]<<','<<s.legacy[0]<<','<<s.legacy[1]<<",0.75,7,"<<s.mass
        <<','<<r.on.rho[0]<<','<<r.on.rho[1]<<','<<r.on.volume[0]<<','<<r.on.volume[1]<<','<<r.on.mi[0]<<','<<r.on.mi[1]<<','<<r.reference_mass
        <<','<<r.legacy_on.rho[0]<<','<<r.legacy_on.rho[1]<<','<<s.alpha
        <<','<<s.vx[0]<<','<<s.vx[1]<<','<<s.vz[0]<<','<<s.vz[1]<<','<<s.tangentx<<','<<s.tangentz<<','<<s.auxx<<','<<s.auxz
        <<','<<(s.wall?s.vx[1]-s.tangentx:s.vx[p]-s.vx[1-p])<<','<<(s.wall?s.vz[1]-s.tangentz:s.vz[p]-s.vz[1-p])
        <<','<<(s.wall?(s.vx[1]-(s.scratch?s.auxx:s.vx[0])):s.vx[p]-s.vx[1-p])
        <<','<<(s.wall?(s.vz[1]-(s.scratch?s.auxz:s.vz[0])):s.vz[p]-s.vz[1-p]);
      Write3(csv,ToTDouble3(r.on.ace[p]));Write3(csv,ToTDouble3(r.off.ace[p]));
      Write3(csv,ToTDouble3(r.legacy_on.ace[p]));Write3(csv,ToTDouble3(r.legacy_off.ace[p]));
      Write3(csv,ToTDouble3(r.rhop_on.ace[p]));Write3(csv,ToTDouble3(r.rhop_off.ace[p]));
      Write3(csv,ToTDouble3(r.scratch_on.ace[p]));Write3(csv,ToTDouble3(r.scratch_off.ace[p]));
      Write3(csv,r.force);Write3(csv,r.reference);Write3(csv,r.residual);
      csv<<','<<r.on.ar[p]<<','<<r.on.pore[p]<<','<<r.on.theta[p]<<','<<z.xx<<','<<z.yy<<','<<z.zz<<','<<z.xy<<','<<z.yz<<','<<z.xz
        <<','<<r.scratch_on.ar[p]<<','<<r.scratch_on.pore[p]<<','<<r.scratch_on.theta[p]
        <<','<<other.xx<<','<<other.yy<<','<<other.zz<<','<<other.xy<<','<<other.yz<<','<<other.xz<<','<<r.on.viscdt<<','<<r.work<<','<<r.reference_work
        <<','<<r.force_scaled<<','<<r.rhop_scaled<<','<<r.scratch_scaled<<','<<r.balance_scaled<<','<<r.work_scaled<<','<<r.derivative_change
        <<','<<r.exact_zero_controls<<','<<(s.j[0]==1&&s.j[1]==1)
        <<','<<max_force<<','<<max_rhop<<','<<max_scratch<<','<<max_balance<<','<<max_work<<','<<r.passed<<'\n';
    }
    csv.flush();Check(bool(csv),"CSV write failed");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)
      <<"{\"stage\":\"upl_spr_av_pair_cpu_r1\",\"component_completed\":true,\"private_component\":true,\"passed\":"<<(passed?"true":"false")
      <<",\"actual_interaction_calls\":"<<KernelCalls<<",\"trials\":"<<trials<<",\"csv_rows\":"<<rows.size()
      <<",\"particles\":2,\"dimension\":2,\"initial_pressure_and_stress_zero\":true,\"time_integrated\":false,\"public_initialization_tested\":false"
      <<",\"darcy_tested\":false,\"mls_tested\":false,\"general_boundary_acceptance\":false,\"public_3d_acceptance\":false,\"physical_acceptance\":false"
      <<",\"epsilon_float\":"<<Eps<<",\"force_budget_eps\":"<<ForceUlps<<",\"balance_budget_eps\":"<<BalanceUlps<<",\"work_budget_eps\":"<<WorkUlps
      <<",\"exact_zero_controls\":"<<(exact?"true":"false")<<",\"max_scaled_force_error\":";JsonNumber(done,max_force);
    done<<",\"max_scaled_legacy_rhop_error\":";JsonNumber(done,max_rhop);done<<",\"max_scaled_derivative_scratch_AV_error\":";JsonNumber(done,max_scratch);
    done<<",\"max_scaled_current_mi_pair_residual\":";JsonNumber(done,max_balance);done<<",\"max_scaled_work_error\":";JsonNumber(done,max_work);done<<"}\n";
    done.flush();Check(bool(done),"Completion write failed");
    std::cout<<"Private actual CPU calls="<<KernelCalls<<" trials="<<trials<<" rows="<<rows.size()<<" passed="<<passed<<'\n';return passed?0:2;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Private CPU component failed; no acceptance\n";return 1;}
}
