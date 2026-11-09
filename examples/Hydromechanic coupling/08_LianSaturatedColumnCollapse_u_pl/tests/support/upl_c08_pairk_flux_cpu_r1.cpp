// Three actual CPU frozen-state force evaluations; pair-k rate shadows never feed back.
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
JAppInfo AppInfo("C08PairKFluxCpu","r1","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=90;
static constexpr unsigned Parts[3]={13,14,29},Focus[4]={7011,7012,6230,6231},Bed[5]={1800,1852,1904,1956,2008};
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
    Need((selected==Parts[0]||selected==Parts[1]||selected==Parts[2]),"Only actual total-AS/n3 causal90 saved parts13/14/29 are admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
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
  bool HaloFree(unsigned i)const{
    const double limit=4.*double(KernelSize2);for(unsigned j=0;j<Np;j++)if(j<Npb||IsFreeSurfaceParticle(j,Codec,FSTypec)){const auto d=Posc[i]-Posc[j];if(d.x*d.x+d.z*d.z<=limit)return false;}return true;
  }
  std::vector<unsigned> Select()const{
    const auto byid=Map();std::vector<std::pair<double,unsigned>> score;for(unsigned id=2060;id<Original;id++){double best=DBL_MAX;for(unsigned f:Focus){const auto d=Posc[byid[id]]-Posc[byid[f]];best=(std::min)(best,d.x*d.x+d.z*d.z);}score.emplace_back(best,id);}std::sort(score.begin(),score.end());std::vector<unsigned> ids(std::begin(Focus),std::end(Focus));unsigned inside=0;
    for(const auto& q:score)if(std::find(ids.begin(),ids.end(),q.second)==ids.end()&&HaloFree(byid[q.second])){ids.push_back(q.second);if(++inside==8)break;}
    for(const auto& q:score)if(ids.size()<32&&std::find(ids.begin(),ids.end(),q.second)==ids.end())ids.push_back(q.second);
    Need(ids.size()==32&&inside>0,"Explicit focus/boundary/halo-free output coverage differs");std::vector<unsigned> slots;for(unsigned id:ids)slots.push_back(byid[id]);return slots;
  }
  struct Fields{unsigned kind;bool quantized,constantK;std::vector<double> p;std::vector<tdouble3> a;double pQuantMax=0,aQuantMax=0;Fields(unsigned n,unsigned k,bool q):kind(k),quantized(q),constantK(k==1),p(n),a(n){};};
  Fields Make(unsigned kind,bool quantized)const{
    Fields f(Np,kind,quantized);const double water=SoilCte.PoreWaterRho;
    for(unsigned q=0;q<Np;q++){
      double p=PorePressc[q];tdouble3 a=ToTDouble3(Acec[q]);if(kind==2){p=-1024.;a=TDouble3(0);}
      else if(kind>=3){const auto x=Posc[q];double potential=x.x/32.+x.z/16.;a=TDouble3(1./32.,0,1./16.);if(kind==4){potential+=(x.x*x.x+x.z*x.z)/64.+x.x*x.z/128.;a=a+TDouble3(x.x/32.+x.z/128.,0,x.x/128.+x.z/32.);}p=-1024.-water*potential;}
      const double pp=quantized?double(float(p)):p;const auto aa=quantized?ToTDouble3(ToTFloat3(a)):a;f.p[q]=pp;f.a[q]=aa;f.pQuantMax=(std::max)(f.pQuantMax,fabs(pp-p));const auto da=aa-a;f.aQuantMax=(std::max)(f.aQuantMax,sqrt(Dot(da,da)));
    }return f;
  }
  struct Terms{
    unsigned count=0,boundary=0;bool fs=false,normalAvailable=false;double ki=0,compression=0,lp=0,defect=0,divace=0,chain=0,current=0,budget=0,pairRaw=0,pairDefect=0,pair=0,algebraBudget=0,maxHydraulicPairResidual=0,normalF=0;tdouble3 gp=TDouble3(0),gJ=TDouble3(0),lx=TDouble3(0),F=TDouble3(0);
  };
  Terms Sum(unsigned i,const Fields& f,bool validateActual=false)const{
    const double water=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus,gamma=water*9.80665,v0=double(MassFluid)/RhopZero;double n,v,rho;GetPorosityFeedbackStateCpu(i,n,v,rho);Terms q;q.ki=f.constantK?double(SoilCte.HydraulicConductivity):GetDynamicConductivityCpu(i);const double kp=f.constantK?0.:q.ki/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk),B=kw/n;
    double lp=0,da=0,absLp=0,absDa=0,rawPair=0,absolutePair=0;const auto ai=f.a[i];
    // All actual normal fluid and fixed support, including real reconstructed wall C/J/Ace. No receiver-neighborhood truncation.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||(j<Npb&&CODE_IsFixed(Codec[j]))){
      const auto d=Posc[i]-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;if(j<Npb){Need(BoundModec[j]!=BMODE_MDBC2OFF,"Inactive fixed sample in actual Darcy support");q.boundary++;}
      const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr))),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double vol=v0*PoroJc[j],dp=f.p[i]-f.p[j],w=vol*Dot(d,gi+gj)/(rr+double(Eta2)),kj=f.constantK?double(SoilCte.HydraulicConductivity):GetDynamicConductivityCpu(j),kbar=.5*(q.ki+kj);const auto delta=f.a[j]-ai;Need(Finite(q.ki)&&q.ki>0&&Finite(kj)&&kj>0&&Finite(kbar),"Pair conductivity outside original positive finite domain");
      lp+=w*dp;q.lx=q.lx+d*w;q.gp=q.gp-gi*(vol*dp);q.gJ=q.gJ+gi*(vol*(PoroJc[j]-PoroJc[i]));da+=vol*Dot(delta,gi);absLp+=fabs(w*dp);absDa+=vol*(fabs(delta.x*gi.x)+fabs(delta.z*gi.z));
      const double b=dp+water*Dot(ai,d);rawPair+=kbar*w*b;q.maxHydraulicPairResidual=(std::max)(q.maxHydraulicPairResidual,fabs(b));absolutePair+=fabs(kbar*w)*(fabs(f.p[i])+fabs(f.p[j])+water*(fabs(ai.x*d.x)+fabs(ai.z*d.z)));q.count++;
    }
    q.fs=HydroMechFreeSeepage&&IsFreeSurfaceParticle(i,Codec,FSTypec);q.F=q.gp+ai*water;const double defect=q.fs?water*Dot(ai,q.lx):-Dot(q.gp,q.lx),chain=kp*Dot(q.gJ,q.F);
    q.compression=kindTheta(f.kind,i)*-B;q.lp=B*q.ki/gamma*lp;q.defect=B*q.ki/gamma*defect;q.divace=B*q.ki/gamma*water*da;q.chain=B/gamma*chain;q.current=q.compression+q.lp+q.defect+q.divace+q.chain;
    q.pairRaw=B/gamma*rawPair;q.pairDefect=q.fs?0.:-B*q.ki/gamma*Dot(q.F,q.lx);q.pair=q.compression+q.pairRaw+q.pairDefect+q.divace;
    const double absolute=fabs(q.compression)+B/gamma*(q.ki*(absLp+(q.fs?water*(fabs(ai.x*q.lx.x)+fabs(ai.z*q.lx.z)):fabs(q.gp.x*q.lx.x)+fabs(q.gp.z*q.lx.z))+water*absDa)+kp*(fabs(q.gJ.x)*(fabs(q.gp.x)+water*fabs(ai.x))+fabs(q.gJ.z)*(fabs(q.gp.z)+water*fabs(ai.z))));const double neps=(64.*q.count+256.)*DBL_EPSILON;Need(neps<1.,"Arithmetic gamma domain differs");const double roundoff=neps/(1.-neps);
    q.budget=(32.*FLT_EPSILON+roundoff)*(std::max)(1.,absolute);q.algebraBudget=roundoff*(std::max)(1.,absolute+fabs(q.compression)+B/gamma*(absolutePair+q.ki*(fabs(q.F.x*q.lx.x)+fabs(q.F.z*q.lx.z)+water*absDa)));
    const auto normal=ToTDouble3(FSNormalc[i]);const double norm2=Dot(normal,normal);q.normalAvailable=q.fs&&norm2>0;if(q.normalAvailable)q.normalF=Dot(q.F,normal)/sqrt(norm2);
    Need(q.count>0&&Finite(q.current)&&Finite(q.pair)&&Finite(q.budget)&&Finite(q.algebraBudget)&&Finite(q.normalF),"Nonfinite/empty shadow response");if(validateActual)Need(fabs(double(PorePressRatec[i])-q.current)<=q.budget,"Actual Darcy/current five-term original budget failed");return q;
  }
  double kindTheta(unsigned kind,unsigned i)const{return kind<=1?PoroThetac[i]:0.;}
  template<class U>struct Held{U* p;std::vector<U> v;Held(U* x,unsigned n):p(x),v(n){std::memcpy(v.data(),x,n*sizeof(U));}bool Equal()const{return !std::memcmp(p,v.data(),v.size()*sizeof(U));}};
 public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::array<Snapshot,3>& frames){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 receiver initialization differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released force-only controls differ");
    Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Frozen released force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==3.f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f),"Original total-AS3/AV/material/kernel differs");
    Need(FixedDt&&FixedDt->GetFixedValue()==.0000025&&SymplecticDtPre==.0000025,"Original fixed/current necessary-step context differs");
    releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();const double releaseTime=GravityPreloadActualTime;

    const float originalEta=Eta2;Need(originalEta>0&&Bits(originalEta,float((double(KernelH)*.1)*(double(KernelH)*.1))),"Original force/AV/Darcy Eta differs");
    std::ofstream receivers(pathfs::path(cfg->DirOut)/"receivers.csv"),manufactured(pathfs::path(cfg->DirOut)/"manufactured.csv"),callsCsv(pathfs::path(cfg->DirOut)/"calls.csv");for(auto* f:{&receivers,&manufactured,&callsCsv})*f<<std::setprecision(17);
    receivers<<"call,part,time_s,tau_s,completed_step,native_id,x_m,z_m,saved_FS,actual_FS,halo_free_FS_fixed_2R,boundary_neighbors,neighbors,p_Pa,J,kappa,k_m_s,theta_s_1,Ace_x,Ace_z,Cxx,Cxz,Czx,Czz,gp_x,gp_z,gradJ_x,gradJ_z,Lx_x,Lx_z,F_x,F_z,FS_normal_available,F_dot_FSnormal,actual_rate_Pa_s,current_compression_Pa_s,current_LP_Pa_s,current_defect_Pa_s,current_divAce_Pa_s,current_chain_Pa_s,current_rate_Pa_s,current_budget_Pa_s,pair_raw_hydraulic_Pa_s,pair_defect_Pa_s,pair_divAce_Pa_s,pair_rate_Pa_s,pair_minus_current_Pa_s\n";
    manufactured<<"call,part,time_s,native_id,field,storage,constant_k,actual_FS,halo_free_FS_fixed_2R,boundary_neighbors,neighbors,continuous_zero_reference,theta_s_1,p_Pa,A_x,A_z,max_p_float_quantization_Pa,max_A_float_quantization_m_s2,ki,gp_x,gp_z,F_x,F_z,F_norm,FS_normal_available,F_dot_FSnormal,max_pair_hydraulic_residual_Pa,current_rate_Pa_s,pair_rate_Pa_s,pair_minus_current_Pa_s,current_arithmetic_budget_Pa_s,constk_algebra_budget_Pa_s,actual_wall_closure_replay\n";
    callsCsv<<"call,part,time_s,tau_s,completed_step,soil,selected,halo_free_selected,fixed_support_selected,FS23,saved_FS_changes,max_actual_rate_abs_Pa_s,max_current_shadow_budget_fraction,constant_null_checks,constant_k_reduction_checks,max_constant_k_budget_fraction,actual_DtVariable_s,SymplecticDtPre_s,original_Eta2,primary_bits_unchanged,all6805_scratch_bits_held\n";
    unsigned calls=0,receiverRows=0,manufacturedRows=0,nullChecks=0,constantChecks=0;double maxRatio=0,maxConstantRatio=0;
    for(const auto& frame:frames){
      Restore(frame);SoilUnchanged(frame);bool cleanup=true;try{
        Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc,"Actual complete force scratch missing");SoilUnchanged(frame);Need(Bits(Eta2,originalEta),"Eta changed");const double actualDt=DtVariable(false);Need(actualDt==.0000025,"Original actual necessary-step guard differs");
        Held<tmatrix3d> hc(CorrMatc,Np);Held<tfloat3> ha(Acec,Np),hn(FSNormalc,Np);Held<unsigned> hf(FSTypec,Np);Held<double> ht(PoroThetac,Np);Held<float> hr(PorePressRatec,Np);const auto selected=Select();const auto actual=Make(0,false);unsigned fs23=0,changed=0,inside=0,boundary=0;double maxActual=0,ratio=0,constantRatio=0;
        for(unsigned q=Npb;q<Np;q++){Need(Finite(Acec[q])&&Finite(PoroThetac[q])&&Finite(PorePressRatec[q]),"Actual5000 force/pressure-rate nonfinite");fs23+=IsFreeSurfaceParticle(q,Codec,FSTypec);changed+=FSTypec[q]!=frame.fstype[frame.byid[Idpc[q]]];maxActual=(std::max)(maxActual,fabs(double(PorePressRatec[q])));}
        for(unsigned q:selected){const auto z=Sum(q,actual,true);const unsigned id=Idpc[q];const auto x=Posc[q],a=ToTDouble3(Acec[q]);const auto c=CorrMatc[q];const auto sr=Rsigmac[q];Need(Finite(sr.xx)&&Finite(sr.yy)&&Finite(sr.zz)&&Finite(sr.xy)&&Finite(sr.yz)&&Finite(sr.xz),"Actual selected stress rate nonfinite");const bool interior=HaloFree(q);inside+=interior;boundary+=z.boundary>0;ratio=(std::max)(ratio,fabs(double(PorePressRatec[q])-z.current)/z.budget);
          receivers<<calls<<','<<frame.part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<unsigned(Nstep)<<','<<id<<','<<x.x<<','<<x.z<<','<<frame.fstype[frame.byid[id]]<<','<<FSTypec[q]<<','<<interior<<','<<z.boundary<<','<<z.count<<','<<PorePressc[q]<<','<<PoroJc[q]<<','<<Kplasticc[q]<<','<<z.ki<<','<<PoroThetac[q]<<','<<a.x<<','<<a.z<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<','<<z.gp.x<<','<<z.gp.z<<','<<z.gJ.x<<','<<z.gJ.z<<','<<z.lx.x<<','<<z.lx.z<<','<<z.F.x<<','<<z.F.z<<','<<z.normalAvailable<<','<<z.normalF<<','<<PorePressRatec[q]<<','<<z.compression<<','<<z.lp<<','<<z.defect<<','<<z.divace<<','<<z.chain<<','<<z.current<<','<<z.budget<<','<<z.pairRaw<<','<<z.pairDefect<<','<<z.divace<<','<<z.pair<<','<<z.pair-z.current<<'\n';receiverRows++;
        }
        for(unsigned kind=1;kind<=4;kind++)for(unsigned quantized=0;quantized<(kind>=3?2u:1u);quantized++){
          const auto f=Make(kind,quantized!=0);const char* label=kind==1?"native_constant_k":kind==2?"constant_null":kind==3?"affine_hydraulic":"nonconstant_potential";
          for(unsigned q:selected){const auto z=Sum(q,f);if(kind==2){Need(z.current==0.&&z.pair==0.,"Constant pressure/A0/theta0 null differs");nullChecks++;}if(kind==1){const double rr=fabs(z.pair-z.current)/z.algebraBudget;Need(rr<=1.,"Constant-k algebraic reduction exceeds predeclared arithmetic budget");constantRatio=(std::max)(constantRatio,rr);constantChecks++;}
            manufactured<<calls<<','<<frame.part<<','<<TimeStep<<','<<Idpc[q]<<','<<label<<','<<(quantized?"float32":"float64")<<','<<f.constantK<<','<<FSTypec[q]<<','<<HaloFree(q)<<','<<z.boundary<<','<<z.count<<','<<(kind>=2)<<','<<kindTheta(kind,q)<<','<<f.p[q]<<','<<f.a[q].x<<','<<f.a[q].z<<','<<f.pQuantMax<<','<<f.aQuantMax<<','<<z.ki<<','<<z.gp.x<<','<<z.gp.z<<','<<z.F.x<<','<<z.F.z<<','<<sqrt(Dot(z.F,z.F))<<','<<z.normalAvailable<<','<<z.normalF<<','<<z.maxHydraulicPairResidual<<','<<z.current<<','<<z.pair<<','<<z.pair-z.current<<','<<z.budget<<','<<z.algebraBudget<<",0\n";manufacturedRows++;
          }
        }
        Need(hc.Equal()&&ha.Equal()&&hn.Equal()&&hf.Equal()&&ht.Equal()&&hr.Equal(),"Test-side shadows modified actual6805 C/Ace/FS/theta/rate bits");SoilUnchanged(frame);maxRatio=(std::max)(maxRatio,ratio);maxConstantRatio=(std::max)(maxConstantRatio,constantRatio);callsCsv<<calls<<','<<frame.part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<unsigned(Nstep)<<','<<Soil<<','<<selected.size()<<','<<inside<<','<<boundary<<','<<fs23<<','<<changed<<','<<maxActual<<','<<ratio<<",32,32,"<<constantRatio<<','<<actualDt<<','<<SymplecticDtPre<<','<<Eta2<<",1,1\n";
        PosInteraction_Forces();cleanup=false;SoilUnchanged(frame);Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc&&Bits(Eta2,originalEta)&&ArtificialStress&&ArtificialStressExp==3.f&&Visco==.1f,"Original flags/scratch not preserved");for(auto* f:{&receivers,&manufactured,&callsCsv}){f->flush();Need(bool(*f),"Component CSV flush failed");}
      }catch(...){if(cleanup)PosInteraction_Forces();throw;}
    }
    Need(calls==3&&receiverRows==96&&manufacturedRows==576&&nullChecks==constantChecks&&nullChecks==96,"Exact3-state shadow coverage differs");std::ofstream done(pathfs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_pairk_flux_cpu_r1\",\"passed\":true,\"source_parts\":[13,14,29],\"native_saved_samples\":90,\"explicit_focus_IDs\":[7011,7012,6230,6231],\"source_release_time_s\":"<<releaseTime<<",\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"actual_ct_calls\":3,\"actual_Darcy_calls\":3,\"actual_DtVariable_false_calls\":3,\"call_rows\":3,\"receiver_rows\":96,\"manufactured_rows\":576,\"constant_null_checks\":96,\"constant_k_algebra_checks\":96,\"max_current_shadow_budget_fraction\":"<<maxRatio<<",\"max_constant_k_budget_fraction\":"<<maxConstantRatio<<",\"physical_steps\":0,\"material_return_calls\":0,\"filter_calls\":0,\"Eta_changed\":false,\"AS_AV_changed\":false,\"all5000_soil_primary_bits_preserved_each_call\":true,\"all6805_C_Ace_FS_theta_rate_bits_held_by_shadows\":true,\"actual_full_wall_neighbor_force\":true,\"FS_changes_observed_not_suppressed\":true,\"candidate_written_back\":false,\"manufactured_ghosts_are_analytic_oracle\":true,\"manufactured_is_actual_wall_closure_replay\":false,\"uniform_A_interior_exact_null_promised\":false,\"nonconstant_potential_only_error_measured\":true,\"literal_Eq25_claimed\":false,\"conservation_or_dissipation_proven\":false,\"original_GPU_bit_replay\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_CAUSAL90_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 EXISTING_CAUSAL_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_causal_window_GPU_r1/native"),"Only actual passed total-AS/n3 causal90 is admitted");const std::array<Snapshot,3> frames={Snapshot(folder,Parts[0]),Snapshot(folder,Parts[1]),Snapshot(folder,Parts[2])};AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU component output required; certified PRE contract stays legal");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),frames);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Frozen pair-k shadow component failed; preserve first result\n";return 2;}}
