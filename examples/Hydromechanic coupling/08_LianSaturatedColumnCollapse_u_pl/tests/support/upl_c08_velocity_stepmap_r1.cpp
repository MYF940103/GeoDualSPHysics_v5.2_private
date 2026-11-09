// Five independent one-update CPU velocity maps of the sealed total-AS/n3 causal90 state.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include <memory>
#include "JCellDivCpuSingle.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "FunSphKernel.h"
#include "FunSoilMaterial.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>
JAppInfo AppInfo("C08VelocityStepMap","r1","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=90;
static constexpr unsigned SelectedPart=71,Bed[5]={1800,1852,1904,1956,2008};
static void Need(bool x,const char* s){if(!x)throw std::runtime_error(s);}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}
struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fstype,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,fsnormal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pathfs::path& folder,unsigned selected):part(selected),completed(4000000+4000*(selected+1)),byid(Original,UINT_MAX){
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pathfs::file_size(folder/"typed22.bin")==12+Samples*stride,"Actual90/6805/22 native extent differs");
    Need(selected==SelectedPart,"Only actual total-AS/n3 causal90 saved part71 is admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);fsnormal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fstype=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];const bool bed=std::find(std::begin(Bed),std::end(Bed),a)!=std::end(Bed);Need(a<Original&&byid[a]==UINT_MAX&&(a<1800||bed||a>=2060),"Unexpected/duplicate/retired native ID");byid[a]=q;if(a<2060)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid soil native ledger domain");if(fstype[q]==2||fstype[q]==3)Need(p[q]<=0,"Closed saved FS2/3 has positive pressure");}}
    Need(fixed==Fixed&&soil==Soil,"Actual fixed/soil ownership differs");
  }
};
class Probe:public JSphCpuSingle{
  std::vector<typecode> releasedCode;std::vector<tfloat3> releasedNormal;std::vector<byte> releasedSlip;
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Full released-state allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate native identity");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil ownership differs");soil++;}else{Need(q<Npb&&CODE_IsFixed(Codec[q])&&(id<1800||IsGravityPreloadBedId(id)),"Fixed ownership differs");fixed++;}}
    Need(soil==Soil&&fixed==Fixed,"Released counts differ");return b;
  }
  void StaticRoles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],releasedCode[id]),"ID-owned code changed");if(q<Npb){Need(Bits(BoundNormalc[q],releasedNormal[id])&&Bits(BoundSlipModec[q],releasedSlip[id]),"ID-owned wall normal/slip changed");if(IsGravityPreloadBedId(id))Need(BoundNormalc[q]==TFloat3(0,0,float(Dp))&&BoundSlipModec[q]==byte(SLIP_NoSlip),"Kept bed override differs");}}}
  void CopySaved(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Snapshot/current ID mismatch");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fstype[s];FSNormalc[q]=a.fsnormal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Original soil J/n/V/rho/k/cache ledger differs");}}
  void Restore(const Snapshot& a){
    Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch still owned");Map();CopySaved(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);
    const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;
    try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;
    Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Snapshot cell rebuild excluded a particle");Map();CopySaved(a);StaticRoles();Ledger(a);TimeStep=a.time;Nstep=a.completed;
  }
  void SoilUnchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto stress=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],stress)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force evaluation changed a soil primary state");}StaticRoles();Ledger(a);Need(TimeStep==a.time&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step evaluation advanced the state");}
  struct FixedScope{
    JDsFixedDt*& slot;JDsFixedDt* original;std::unique_ptr<JDsFixedDt> local;
    FixedScope(JDsFixedDt*& p,double h):slot(p),original(p),local(new JDsFixedDt(h)){slot=local.get();}
    ~FixedScope(){slot=original;}
  };
  struct Delta{double p=0;tdouble3 v=TDouble3(0),sk=TDouble3(0),si=TDouble3(0);};
  struct Quadratic{double p=0,v=0,s=0;double Total()const{return p+v+s;}};
  static Delta Sub(const Delta& a,const Delta& b){Delta d;d.p=a.p-b.p;d.v=a.v-b.v;d.sk=a.sk-b.sk;d.si=a.si-b.si;return d;}
  static Delta Scale(const Delta& a,double c){Delta d;d.p=a.p*c;d.v=a.v*c;d.sk=a.sk*c;d.si=a.si*c;return d;}
  std::vector<Delta> Difference(const Snapshot& a,const Snapshot& base)const{
    std::vector<Delta> out(Total);for(unsigned s=0;s<Total;s++)if(a.id[s]>=2060){out[s].p=double(a.p[s])-base.p[s];out[s].v=ToTDouble3(a.vel[s])-ToTDouble3(base.vel[s]);out[s].sk=a.sk[s]-base.sk[s];out[s].si=a.si[s]-base.si[s];}return out;
  }
  Quadratic Norm(const Snapshot& reference,const std::vector<Delta>& d)const{
    Quadratic out;const double K=SoilCte.ModulusK,G=SoilCte.ModulusG,Kw=SoilCte.PoreWaterBulkModulus;Need(K>0&&G>0&&Kw>0,"Positive original elastic/storage metrics required");
    for(unsigned s=0;s<Total;s++)if(reference.id[s]>=2060){const auto& a=d[s];const double V=reference.volume[s],mass=V*reference.rho[s],W=V*reference.n[s]/Kw,I=a.sk.x+a.sk.y+a.sk.z,m=I/3.;const auto dev=a.sk-TDouble3(m,m,m);const double ss=Dot(dev,dev)+2.*Dot(a.si,a.si);out.p+=W*a.p*a.p;out.v+=mass*Dot(a.v,a.v);out.s+=V*(I*I/(9.*K)+ss/(2.*G));}
    Need(Finite(out.p)&&Finite(out.v)&&Finite(out.s),"Nonfinite perturbation quadratic");return out;
  }
  Snapshot Capture(const Snapshot& incoming){
    Map();StaticRoles();Snapshot a=incoming;a.time=TimeStep;a.completed=unsigned(Nstep);
    for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(Bits(PorePress0c[q],incoming.p0[s]),"One-step map changed material P0");
      if(q<Npb){Need(Bits(Posc[q],incoming.pos[s])&&Velrhopc[q].x==0&&Velrhopc[q].y==0&&Velrhopc[q].z==0&&Kplasticc[q]==0,"One-step map changed a retained fixed marker");continue;}
      const auto v=Velrhopc[q];const auto stress=Sigmac[q];Need(Finite(Posc[q])&&Finite(TFloat3(v.x,v.y,v.z))&&Finite(v.w)&&Finite(PorePressc[q])&&Finite(PoroThetac[q])&&Finite(Kplasticc[q])&&Kplasticc[q]>=incoming.kap[s]&&FSTypec[q]<=4,"Nonfinite/decreasing material state after one step");
      Need(Finite(stress.xx)&&Finite(stress.yy)&&Finite(stress.zz)&&Finite(stress.xy)&&Finite(stress.yz)&&Finite(stress.xz),"Nonfinite effective stress after one step");
      Need(Posc[q].x>=-1e-6*Dp&&Posc[q].z>=-1e-6*Dp&&Posc[q].y==0,"Original fixed-plane geometry guard failed");if(FSTypec[q]==2||FSTypec[q]==3)Need(PorePressc[q]<=0,"Completed true free-seepage pressure is positive");
      double n,V,rho;GetPorosityFeedbackStateCpu(q,n,V,rho);const double k=GetDynamicConductivityCpu(q);Need(PoroJc[q]>1.-double(SoilCte.Porosity)&&n>0&&n<1&&V>0&&rho>0&&k>0&&Finite(k)&&Bits(v.w,float(rho)),"Original J/storage/inertia/conductivity cache guard failed");
      a.pos[s]=Posc[q];a.vel[s]=TFloat3(v.x,v.y,v.z);a.rhop[s]=v.w;a.sk[s]=TDouble3(stress.xx,stress.yy,stress.zz);a.si[s]=TDouble3(stress.xy,stress.yz,stress.xz);a.kap[s]=Kplasticc[q];a.p[s]=PorePressc[q];a.excess[s]=float(PorePressc[q]-PorePress0c[q]);a.j[s]=PoroJc[q];a.n[s]=n;a.volume[s]=V;a.rho[s]=rho;a.k[s]=k;a.theta[s]=PoroThetac[q];a.fstype[s]=FSTypec[q];a.fsnormal[s]=FSNormalc[q];a.posdiv[s]=PosDivc[q];
    }return a;
  }

  struct PreYield{unsigned rows=0,at_or_above=0,max_id=UINT_MAX;double fmax=-DBL_MAX;fsoil::Material material{};TpDPCtes fit=DP_PS;bool trigger=false;};
  static const char* FitName(TpDPCtes fit){return fit==DP_PS?"DP_PS":fit==DP_C?"DP_C":"DP_MC";}
  PreYield ObservePreYield(const pathfs::path& out)const{
    Need(Np==Original&&Npb==2060&&unsigned(Nstep)==4000000&&Finite(TimeStep)&&Bits(TimeStep,TimeStepIni)&&Bits(TimeStep,TimeStepM1)&&TimeStep>=GravityPreloadTime&&!GravityPreloadReleased,"Only the actual imported pre-release state is observed");
    const auto& c=SoilCte;const bool trigger=PartBegin && StrainSoftening;
    const float cohesion=(trigger&&(c.n_phi>0.f||c.n_coh>0.f)?c.coh/c.SoilTriggerFos:c.coh);
    const float residual=(c.n_coh>0.f?c.coh_r:cohesion);
    const fsoil::Material material={c.ModulusK,c.ModulusG,c.phi,c.phi_r,c.n_phi,cohesion,residual,c.n_coh,c.dlt,c.psiDecay};
    Need(fsoil::KnownFit(DPCtes),"Actual production DP fit is unknown");PreYield result;result.material=material;result.fit=DPCtes;result.trigger=trigger;std::vector<bool> seen(Original,false);std::ofstream csv(out/"pre_yield.csv");csv<<std::setprecision(17);
    csv<<"native_id,source_time_s,source_completed_step,sigma_xx_Pa,sigma_yy_Pa,sigma_zz_Pa,sigma_xy_Pa,sigma_yz_Pa,sigma_xz_Pa,DP_fit,DP_fit_value,ModulusK_Pa,ModulusG_Pa,phi_p_rad,phi_r_rad,n_phi,coh_p_Pa,coh_r_Pa,n_coh,psi0_rad,psi_decay,DP_phi,DP_kc_Pa,DP_psi,I_Pa,q_Pa,f_Pa,kappa,PorePress_Pa,PorePress0_Pa,J\n";
    for(unsigned q=Npb;q<Np;q++){
      const unsigned id=Idpc[q];Need(id>=2060&&id<Original&&!seen[id]&&CODE_IsNormal(Codec[q])&&CODE_IsFluid(Codec[q]),"Imported soil identity/coverage differs");seen[id]=true;const auto& s=Sigmac[q];const fsoil::Stress stress={s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};const auto DP=fsoil::UpdateDPvars(material,Kplasticc[q],DPCtes);const auto inv=fsoil::GetInvariants(stress);const double f=inv.q+DP.DP_phi*inv.I-DP.DP_kc;
      Need(fsoil::Finite(stress)&&fsoil::Finite(DP)&&Finite(inv.I)&&Finite(inv.q)&&Finite(f)&&Finite(Kplasticc[q])&&Finite(PorePressc[q])&&Finite(PorePress0c[q])&&Finite(PoroJc[q]),"Nonfinite imported PRE yield observation");
      if(f>result.fmax||(f==result.fmax&&id<result.max_id)){result.fmax=f;result.max_id=id;}result.at_or_above+=f>=1e-5;result.rows++;
      csv<<id<<','<<TimeStep<<','<<unsigned(Nstep)<<','<<stress.xx<<','<<stress.yy<<','<<stress.zz<<','<<stress.xy<<','<<stress.yz<<','<<stress.xz<<','<<FitName(DPCtes)<<','<<unsigned(DPCtes)<<','<<double(material.ModulusK)<<','<<double(material.ModulusG)<<','<<double(material.phi_p)<<','<<double(material.phi_r)<<','<<double(material.n_p)<<','<<double(material.coh_p)<<','<<double(material.coh_r)<<','<<double(material.n_c)<<','<<double(material.psi0)<<','<<double(material.sf)<<','<<DP.DP_phi<<','<<DP.DP_kc<<','<<DP.DP_psi<<','<<inv.I<<','<<inv.q<<','<<f<<','<<double(Kplasticc[q])<<','<<double(PorePressc[q])<<','<<double(PorePress0c[q])<<','<<PoroJc[q]<<'\n';
    }
    csv.flush();Need(bool(csv)&&result.rows==Soil,"Imported PRE observation CSV/coverage differs");return result;
  }

public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& saved){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 receiver initialization differs");const auto preYield=ObservePreYield(pathfs::path(cfg->DirOut));RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released operator scope differs; no Shepard wrapper is scheduled in these maps");
    Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original one-step fixture scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==3.f&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&TVisco==VISCO_Artificial&&Visco==.1f&&Gravity==TFloat3(0,0,-9.81f),"Original total-AS3/kernel/AV/material differs");
    Need(FixedDt&&FixedDt->GetFixedValue()==.0000025,"Original PRE admission must retain its actual fixed dt before clone-local replacement");
    releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();
    Need(saved.part==71&&saved.completed==4288000,"Only actual total-AS/n3 causal90 part71 is admitted");
    const double sourceTime=GravityPreloadActualTime;std::ofstream summary(pathfs::path(cfg->DirOut)/"maps.csv"),fields(pathfs::path(cfg->DirOut)/"differences.csv"),consistency(pathfs::path(cfg->DirOut)/"consistency.csv");for(auto* f:{&summary,&fields,&consistency})*f<<std::setprecision(17);
    summary<<"clone,h_s,velocity_eta,source_time_s,output_time_s,source_completed_step,clone_completed_step,actual_integrated_updates,p_min_Pa,p_max_Pa,max_speed_m_s,max_kappa,min_J,max_J,input_max_abs_delta_p_Pa,input_max_abs_delta_v_m_s,input_max_abs_float_scaling_error_m_s,input_scaling_error_Qv,input_Qp,input_Qv,input_Qsigma,output_Qp,output_Qv,output_Qsigma,total_quadratic_ratio,total_norm_gain,max_abs_delta_J,max_abs_delta_kappa,max_position_difference_m,max_abs_trace_defect_T_Pa,FS_changes,endpoint_plane_membership_changes,P0_bits_unchanged,original_output_guards_passed\n";
    fields<<"clone,h_s,velocity_eta,native_id,input_delta_vx_m_s,input_delta_vy_m_s,input_delta_vz_m_s,input_float_scaling_error_vx_m_s,input_float_scaling_error_vy_m_s,input_float_scaling_error_vz_m_s,delta_p_Pa,delta_vx_m_s,delta_vy_m_s,delta_vz_m_s,delta_sigma_xx_Pa,delta_sigma_yy_Pa,delta_sigma_zz_Pa,delta_sigma_xy_Pa,delta_sigma_yz_Pa,delta_sigma_xz_Pa,delta_J,delta_kappa,delta_x_m,delta_y_m,delta_z_m,baseline_FS,perturbed_FS,baseline_p_Pa,perturbed_p_Pa,baseline_theta_mid_s_1,perturbed_theta_mid_s_1,baseline_trace_defect_T_Pa,perturbed_trace_defect_T_Pa,delta_trace_defect_T_Pa\n";
    consistency<<"h_s,sign_asymmetry_eta001_Qp_per_eta2,sign_asymmetry_eta001_Qv_per_eta2,sign_asymmetry_eta001_Qsigma_per_eta2,sign_asymmetry_eta0005_Qp_per_eta2,sign_asymmetry_eta0005_Qv_per_eta2,sign_asymmetry_eta0005_Qsigma_per_eta2,amplitude_derivative_difference_Qp_per_eta2,amplitude_derivative_difference_Qv_per_eta2,amplitude_derivative_difference_Qsigma_per_eta2,reference_eta001_derivative_total_Q_per_eta2,amplitude_derivative_relative_norm_difference,input_sign_asymmetry_eta001_Qv_per_eta2,input_sign_asymmetry_eta0005_Qv_per_eta2,input_amplitude_derivative_difference_Qv_per_eta2\n";
    const double h=.0000025,etas[5]={0,.001,-.001,.0005,-.0005};unsigned clones=0,rows=0;JDsFixedDt* const originalFixed=FixedDt;
    std::vector<Snapshot> outputs;outputs.reserve(5);std::vector<std::vector<Delta>> diffs,inputs;diffs.reserve(5);inputs.reserve(5);
    for(unsigned c=0;c<5;c++){
      Snapshot incoming=saved;
      if(c)for(unsigned s=0;s<Total;s++)if(saved.id[s]>=2060){const auto v=saved.vel[s];incoming.vel[s]=TFloat3(float(double(v.x)*(1.+etas[c])),float(double(v.y)*(1.+etas[c])),float(double(v.z)*(1.+etas[c])));}
      inputs.push_back(Difference(incoming,saved));std::vector<Delta> scalingError(Total);double maxInputP=0,maxInputV=0,maxScaleError=0;
      for(unsigned s=0;s<Total;s++)if(saved.id[s]>=2060){const auto dv=inputs.back()[s].v;scalingError[s].v=dv-ToTDouble3(saved.vel[s])*etas[c];maxInputP=(std::max)(maxInputP,fabs(inputs.back()[s].p));maxInputV=(std::max)(maxInputV,sqrt(Dot(dv,dv)));maxScaleError=(std::max)(maxScaleError,sqrt(Dot(scalingError[s].v,scalingError[s].v)));}
      const auto inputQ=Norm(saved,inputs.back()),errorQ=Norm(saved,scalingError);Need(inputQ.p==0&&inputQ.s==0&&maxInputP==0&&(c?inputQ.v>0:inputQ.v==0),"Explicit velocity-only float perturbation differs");Restore(incoming);SoilUnchanged(incoming);
      Need(FixedDt==originalFixed,"Previous clone did not restore FixedDt ownership");double used=0;
      std::cout<<"VELOCITY_STEP_MAP_BEGIN clone="<<(clones+1)<<" source_time="<<std::setprecision(17)<<TimeStep<<" h="<<h<<" eta="<<etas[c]<<" actual_input_Qv="<<inputQ.v<<std::endl;
      {FixedScope scope(FixedDt,h);SymplecticDtPre=LastDt=h;Need(FixedDt->GetFixedValue()==h&&h>=double(DtMin),"Clone-local dt conflicts with original DtMin");used=ComputeStep_Sym();std::cout<<"VELOCITY_STEP_MAP_COMPUTE_RETURNED clone="<<(clones+1)<<" used_dt="<<std::setprecision(17)<<used<<" step_start="<<TimeStep<<std::endl;Need(Bits(used,h),"Actual original integrator used another dt");RunCellDivide(true);TimeStep+=used;LastDt=used;Nstep++;}
      Need(FixedDt==originalFixed&&Bits(TimeStep,saved.time+h)&&unsigned(Nstep)==saved.completed+1,"Actual one-step clock or FixedDt ownership differs");Snapshot output=Capture(incoming);outputs.push_back(std::move(output));diffs.push_back(Difference(outputs.back(),outputs[0]));const auto q=Norm(saved,diffs.back());
      double pl=DBL_MAX,ph=-DBL_MAX,speed=0,kap=0,jl=DBL_MAX,jh=-DBL_MAX,dj=0,dk=0,dx=0,maxT=0;unsigned fs=0,contact=0;const auto& a=outputs.back();const auto& base=outputs[0];
      for(unsigned s=0;s<Total;s++)if(saved.id[s]>=2060){pl=(std::min)(pl,double(a.p[s]));ph=(std::max)(ph,double(a.p[s]));speed=(std::max)(speed,sqrt(Dot(ToTDouble3(a.vel[s]),ToTDouble3(a.vel[s]))));kap=(std::max)(kap,double(a.kap[s]));jl=(std::min)(jl,a.j[s]);jh=(std::max)(jh,a.j[s]);dj=(std::max)(dj,fabs(a.j[s]-base.j[s]));dk=(std::max)(dk,fabs(double(a.kap[s])-base.kap[s]));const auto dp=a.pos[s]-base.pos[s];dx=(std::max)(dx,sqrt(Dot(dp,dp)));fs+=a.fstype[s]!=base.fstype[s];const double traceIn=saved.sk[s].x+saved.sk[s].y+saved.sk[s].z,T=(a.sk[s].x+a.sk[s].y+a.sk[s].z)-traceIn-3.*double(SoilCte.ModulusK)*h*a.theta[s],Tb=(base.sk[s].x+base.sk[s].y+base.sk[s].z)-traceIn-3.*double(SoilCte.ModulusK)*h*base.theta[s];maxT=(std::max)(maxT,fabs(T));const double tol=1e-6*Dp;contact+=(fabs(a.pos[s].x)<=tol)!=(fabs(base.pos[s].x)<=tol);contact+=(fabs(a.pos[s].z)<=tol)!=(fabs(base.pos[s].z)<=tol);
        if(c){const auto& d=diffs.back()[s];const auto iv=inputs.back()[s].v,e=scalingError[s].v;fields<<(clones+1)<<','<<h<<','<<etas[c]<<','<<a.id[s]<<','<<iv.x<<','<<iv.y<<','<<iv.z<<','<<e.x<<','<<e.y<<','<<e.z<<','<<d.p<<','<<d.v.x<<','<<d.v.y<<','<<d.v.z<<','<<d.sk.x<<','<<d.sk.y<<','<<d.sk.z<<','<<d.si.x<<','<<d.si.y<<','<<d.si.z<<','<<a.j[s]-base.j[s]<<','<<double(a.kap[s])-base.kap[s]<<','<<dp.x<<','<<dp.y<<','<<dp.z<<','<<base.fstype[s]<<','<<a.fstype[s]<<','<<base.p[s]<<','<<a.p[s]<<','<<base.theta[s]<<','<<a.theta[s]<<','<<Tb<<','<<T<<','<<T-Tb<<'\n';rows++;}}
      summary<<(clones+1)<<','<<h<<','<<etas[c]<<','<<saved.time<<','<<a.time<<','<<saved.completed<<','<<a.completed<<",1,"<<pl<<','<<ph<<','<<speed<<','<<kap<<','<<jl<<','<<jh<<','<<maxInputP<<','<<maxInputV<<','<<maxScaleError<<','<<errorQ.v<<','<<inputQ.p<<','<<inputQ.v<<','<<inputQ.s<<','<<q.p<<','<<q.v<<','<<q.s<<',';if(c)summary<<q.Total()/inputQ.Total();summary<<',';if(c)summary<<sqrt(q.Total()/inputQ.Total());summary<<','<<dj<<','<<dk<<','<<dx<<','<<maxT<<','<<fs<<','<<contact<<",1,1\n";clones++;summary.flush();fields.flush();Need(bool(summary)&&bool(fields),"Completed clone CSV write failed");
    }
    std::vector<Delta> asym001(Total),asym0005(Total),der001(Total),difference(Total),inputAsym001(Total),inputAsym0005(Total),inputDifference(Total);
    for(unsigned s=0;s<Total;s++)if(saved.id[s]>=2060){asym001[s]=Sub(Scale(diffs[1][s],1./etas[1]),Scale(diffs[2][s],1./etas[2]));asym0005[s]=Sub(Scale(diffs[3][s],1./etas[3]),Scale(diffs[4][s],1./etas[4]));der001[s]=Scale(Sub(diffs[1][s],diffs[2][s]),1./(etas[1]-etas[2]));const auto der0005=Scale(Sub(diffs[3][s],diffs[4][s]),1./(etas[3]-etas[4]));difference[s]=Sub(der001[s],der0005);inputAsym001[s]=Sub(Scale(inputs[1][s],1./etas[1]),Scale(inputs[2][s],1./etas[2]));inputAsym0005[s]=Sub(Scale(inputs[3][s],1./etas[3]),Scale(inputs[4][s],1./etas[4]));inputDifference[s]=Sub(Scale(Sub(inputs[1][s],inputs[2][s]),1./(etas[1]-etas[2])),Scale(Sub(inputs[3][s],inputs[4][s]),1./(etas[3]-etas[4])));}
    const auto a=Norm(saved,asym001),b=Norm(saved,asym0005),d=Norm(saved,difference),ref=Norm(saved,der001),ia=Norm(saved,inputAsym001),ib=Norm(saved,inputAsym0005),id=Norm(saved,inputDifference);consistency<<h<<','<<a.p<<','<<a.v<<','<<a.s<<','<<b.p<<','<<b.v<<','<<b.s<<','<<d.p<<','<<d.v<<','<<d.s<<','<<ref.Total()<<',';if(ref.Total()>0)consistency<<sqrt(d.Total()/ref.Total());consistency<<','<<ia.v<<','<<ib.v<<','<<id.v<<'\n';consistency.flush();Need(bool(consistency),"Consistency CSV write failed");
    Need(clones==5&&rows==20000&&FixedDt==originalFixed,"Exact independent clone coverage or final pointer differs");
    std::ofstream done(pathfs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_velocity_stepmap_r1\",\"passed\":true,\"source_profile\":\"total_AS_n3_Shepard_OFF_causal90\",\"source_part\":71,\"source_time_s\":"<<saved.time<<",\"source_release_time_s\":"<<sourceTime<<",\"source_completed_step\":4288000,\"dt_s\":0.0000025,\"velocity_etas\":[0,0.001,-0.001,0.0005,-0.0005],\"velocity_perturbation_scope\":\"all5000_soil_original_float_components\",\"initial_pressure_perturbation_Pa\":0,\"AS_stress_space\":\"original_total\",\"AS_coefficient\":0.2,\"AS_exponent\":3,\"ponding_policy\":\"CompletedOnly\",\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"clone_updates\":5,\"physical_trajectories\":5,\"actual_force_evaluations\":10,\"original_ComputeStep_Sym_calls\":5,\"map_rows\":5,\"difference_rows\":20000,\"consistency_rows\":1,\"independent_FixedDt_per_clone\":true,\"original_FixedDt_pointer_restored\":true,\"original_DtMin_and_necessary_guards_retained\":true,\"input_primary_bits_checked_against_explicit_perturbed_snapshot\":true,\"P0_unchanged\":true,\"initial_weights_frozen_for_all_norms\":true,\"quadratic_norm_has_no_half_factor\":true,\"input_norm_uses_actual_float_velocity_delta\":true,\"consistency_denominators_are_nominal_etas\":true,\"elastic_bulk_modulus_Pa\":"<<double(SoilCte.ModulusK)<<",\"elastic_shear_modulus_Pa\":"<<double(SoilCte.ModulusG)<<",\"contact_observation\":\"endpoint_plane_membership_only_not_hit_or_reaction_count\",\"exact_material_return_status_observed\":false,\"Shepard_wrapper_invocations\":0,\"formal_Run_invocations\":0,\"native_decodes\":0,\"reciprocity_claimed\":false,\"complete_energy_theorem\":false,\"stability_spectrum\":false,\"original_GPU_restart_or_replay\":false,\"physical_acceptance\":false,\"pre_yield_rows\":"<<preYield.rows<<",\"pre_yield_source_time_s\":"<<sourceTime<<",\"pre_yield_source_completed_step\":4000000,\"pre_yield_fmax_Pa\":"<<preYield.fmax<<",\"pre_yield_fmax_ID\":"<<preYield.max_id<<",\"pre_yield_count_f_ge_1e_5\":"<<preYield.at_or_above<<",\"pre_yield_evaluation_material_law_version\":2,\"pre_yield_observation_only\":true,\"pre_yield_return_or_update_calls\":0,\"pre_yield_material\":{\"DP_fit\":\""<<FitName(preYield.fit)<<"\",\"DP_fit_value\":"<<unsigned(preYield.fit)<<",\"ModulusK_Pa\":"<<double(preYield.material.ModulusK)<<",\"ModulusG_Pa\":"<<double(preYield.material.ModulusG)<<",\"phi_p_rad\":"<<double(preYield.material.phi_p)<<",\"phi_r_rad\":"<<double(preYield.material.phi_r)<<",\"n_phi\":"<<double(preYield.material.n_p)<<",\"coh_p_Pa\":"<<double(preYield.material.coh_p)<<",\"coh_r_Pa\":"<<double(preYield.material.coh_r)<<",\"n_coh\":"<<double(preYield.material.n_c)<<",\"psi0_rad\":"<<double(preYield.material.psi0)<<",\"psi_decay\":"<<double(preYield.material.sf)<<",\"restart_trigger\":"<<(preYield.trigger?"true":"false")<<",\"StrainSoftening\":"<<(StrainSoftening?"true":"false")<<",\"SoilTriggerFos\":"<<double(SoilCte.SoilTriggerFos)<<"}}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_CAUSAL90_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 EXISTING_CAUSAL_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_causal_window_GPU_r1/native"),"Only the passed total-AS/n3 causal90 native is admitted");Snapshot saved(folder,SelectedPart);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU component output required; real PRE loader flags remain legal");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),saved);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"One-step clone component failed; preserve first result\n";return 2;}}
