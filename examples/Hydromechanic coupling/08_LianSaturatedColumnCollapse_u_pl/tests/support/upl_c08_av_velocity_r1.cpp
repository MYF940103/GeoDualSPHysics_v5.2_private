// CPU force-stage evaluations of two sealed Shepard/n3 saved states; no time integration.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
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
JAppInfo AppInfo("C08AVVelocity","r1","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=72;
static constexpr unsigned Parts[2]={49,71},Focus[8]={7013,7015,6963,7014,7017,5944,6814,5208},Bed[5]={1800,1852,1904,1956,2008};
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
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pathfs::file_size(folder/"typed22.bin")==12+Samples*stride,"Actual72/6805/22 native extent differs");
    Need(selected==Parts[0]||selected==Parts[1],"Only actual Shepard saved parts49/71 are admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);fsnormal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fstype=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];const bool bed=std::find(std::begin(Bed),std::end(Bed),a)!=std::end(Bed);Need(a<Original&&byid[a]==UINT_MAX&&(a<1800||bed||a>=2060),"Unexpected/duplicate/retired native ID");byid[a]=q;if(a<2060)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid soil native ledger domain");if(fstype[q]==2||fstype[q]==3)Need(p[q]<=0,"Closed saved FS2/3 has positive pressure");}}
    Need(fixed==Fixed&&soil==Soil,"Actual fixed/soil ownership differs");for(unsigned a:Focus)Need(byid[a]!=UINT_MAX,"Explicit focus missing");
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
  std::vector<unsigned> Select(const Snapshot& a)const{
    const auto b=Map();std::vector<std::pair<double,unsigned>> score;const double radius2=4.*double(KernelSize2);
    for(unsigned id=2060;id<Original;id++){const auto x=a.pos[a.byid[id]];double d2=DBL_MAX;for(unsigned f:Focus){const auto d=x-a.pos[a.byid[f]];d2=(std::min)(d2,d.x*d.x+d.z*d.z);}if(d2<=radius2)score.emplace_back(d2,id);}
    std::sort(score.begin(),score.end());std::vector<unsigned> out;for(const auto& x:score){if(out.size()==81)break;out.push_back(b[x.second]);}Need(!out.empty()&&out.size()<=81,"Receiver output selection differs");for(unsigned f:Focus)Need(std::find(out.begin(),out.end(),b[f])!=out.end(),"An explicit focus was truncated");return out;
  }
  struct Terms{unsigned neighbors;double compression,lp,defect,divace,chain,rate,budget,fsace,chainace,chaingp;};
  Terms Sum(unsigned i)const{
    const double water=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus,gamma=water*9.80665,v0=double(MassFluid)/RhopZero,ki=GetDynamicConductivityCpu(i),kp=ki/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);double n,v,rho;GetPorosityFeedbackStateCpu(i,n,v,rho);
    double lp=0,da=0,absLp=0,absDa=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gJ=TDouble3(0);unsigned count=0;
    // All actual particles, independent of production cell order; never omit fixed support.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||(j<Npb&&CODE_IsFixed(Codec[j]))){const auto d=Posc[i]-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;if(j<Npb)Need(BoundModec[j]!=BMODE_MDBC2OFF,"Inactive fixed sample in actual Darcy support");const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr))),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double vol=v0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=vol*Dot(d,gi+gj)/(rr+double(Eta2));const auto delta=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol*dp);gJ=gJ+gi*(vol*(PoroJc[j]-PoroJc[i]));da+=vol*Dot(delta,gi);absLp+=fabs(w*dp);absDa+=vol*(fabs(delta.x*gi.x)+fabs(delta.z*gi.z));count++;}
    const bool fs=HydroMechFreeSeepage&&IsFreeSurfaceParticle(i,Codec,FSTypec);const auto a=ToTDouble3(Acec[i]);const double defect=fs?water*Dot(a,lx):-Dot(gp,lx),chain=kp*Dot(gJ,gp+a*water),B=kw/n;
    Terms q{count,-B*PoroThetac[i],B*ki/gamma*lp,B*ki/gamma*defect,B*ki/gamma*water*da,B/gamma*chain,0,0};q.rate=q.compression+q.lp+q.defect+q.divace+q.chain;
    const double absolute=fabs(q.compression)+B/gamma*(ki*(absLp+(fs?water*(fabs(a.x*lx.x)+fabs(a.z*lx.z)):fabs(gp.x*lx.x)+fabs(gp.z*lx.z))+water*absDa)+kp*(fabs(gJ.x)*(fabs(gp.x)+water*fabs(a.x))+fabs(gJ.z)*(fabs(gp.z)+water*fabs(a.z))));const double neps=(64.*count+256.)*DBL_EPSILON;
    q.budget=(32.*FLT_EPSILON+neps/(1.-neps))*(std::max)(1.,absolute);Need(Finite(q.rate)&&Finite(q.budget)&&fabs(double(PorePressRatec[i])-q.rate)<=q.budget,"Actual Darcy rate/test-side five-term sum budget failed");q.fsace=(fs?q.defect:0.);q.chainace=B/gamma*kp*water*Dot(gJ,a);q.chaingp=B/gamma*kp*Dot(gJ,gp);return q;
  }
  struct Response{
    std::vector<tdouble3> velocity,acc;std::vector<double> theta;std::vector<float> rate;std::vector<unsigned> fs;std::vector<tmatrix3d> c;std::vector<tsymatrix3f> art;std::vector<Terms> terms;std::vector<std::vector<unsigned>> av;
    Response():velocity(Original),acc(Original),theta(Original),rate(Original),fs(Original),c(Original),art(Original),terms(Original),av(Original){}
  };
  std::vector<unsigned> AvShadow(unsigned i)const{
    std::vector<unsigned> active;
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||(j<Npb&&CODE_IsFixed(Codec[j]))){
      const float dx=float(Posc[i].x-Posc[j].x),dy=float(Posc[i].y-Posc[j].y),dz=float(Posc[i].z-Posc[j].z),rr=dx*dx+dy*dy+dz*dz;if(rr>KernelSize2||rr<ALMOSTZERO)continue;
      const bool wall=j<Npb;const TpSlipMode slip=(wall&&BoundSlipModec?TpSlipMode(BoundSlipModec[j]):SlipMode);const bool mdbc=wall&&TBoundary==BC_MDBC&&slip>=SLIP_NoSlip;if(mdbc&&BoundModec&&BoundModec[j]==BMODE_MDBC2OFF)continue;
      tfloat3 other=TFloat3(Velrhopc[j].x,Velrhopc[j].y,Velrhopc[j].z);if(mdbc&&TangenVelc)other=TangenVelc[j];const float vx=Velrhopc[i].x-other.x,vy=Velrhopc[i].y-other.y,vz=Velrhopc[i].z-other.z;const float dot=dx*vx+dy*vy+dz*vz;if(dot<0)active.push_back(Idpc[j]);
    }std::sort(active.begin(),active.end());return active;
  }
  static unsigned Difference(const std::vector<unsigned>& a,const std::vector<unsigned>& b){unsigned n=0;for(unsigned id:a)n+=!std::binary_search(b.begin(),b.end(),id);return n;}
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& first,const Snapshot& second){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 receiver initialization differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released force-only controls differ; no filter may run");
    Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Frozen released force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==3.f&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&TVisco==VISCO_Artificial&&Visco==.1f&&Gravity==TFloat3(0,0,-9.81f),"Frozen original-total AS3/kernel/AV differs");
    releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();const double sourceTime=GravityPreloadActualTime;
    std::ofstream rates(pathfs::path(cfg->DirOut)/"rates.csv"),callsCsv(pathfs::path(cfg->DirOut)/"calls.csv"),directions(pathfs::path(cfg->DirOut)/"directions.csv"),responseCsv(pathfs::path(cfg->DirOut)/"response.csv");for(auto* f:{&rates,&callsCsv,&directions,&responseCsv})*f<<std::setprecision(17);
    rates<<"call,part,time_s,tau_s,eta,sign,native_id,x,z,base_vx,base_vz,input_vx,input_vz,actual_delta_vx,actual_delta_vz,p_Pa,J,kappa,saved_FS,actual_FS,theta,Ace_x,Ace_z,actual_rate_Pa_s,compression_Pa_s,LP_Pa_s,defect_Pa_s,divAce_Pa_s,chain_Pa_s,FS_Ace_Pa_s,chain_Ace_Pa_s,chain_gp_Pa_s,shadow_sum_Pa_s,shadow_budget_Pa_s,AV_active_pairs_shadow,AV_became_approaching_shadow,AV_ceased_approaching_shadow\n";
    callsCsv<<"call,part,time_s,tau_s,completed_step,eta,sign,soil,selected,velocity_bits_changed,max_actual_delta_v_m_s,saved_FS_changed,baseline_FS_changed,baseline_C_bits_changed,baseline_AS_bits_changed,AV_active_pairs_selected_shadow,AV_switches_selected_shadow,max_actual_rate_abs_Pa_s,max_shadow_budget_fraction,primary_bits_match_incoming\n";
    directions<<"part,time_s,tau_s,eta,selected,direction_velocity_M_norm,acceleration_derivative_M_norm,pressure_rate_derivative_W_norm,compression_derivative_W_norm,noncompression_velocity_response_W_norm,acceleration_gain_s_1,pressure_rate_gain_s_1,dt_times_pressure_rate_gain,kinetic_direction_power_W,pressure_storage_rate_direction_W,compression_storage_rate_direction_W,noncompression_storage_rate_direction_W,direction_minus_base_velocity_M_norm,rate_one_sided_asymmetry_W_norm,baseline_FS_changed,baseline_C_bits_changed,baseline_AS_bits_changed,max_abs_rate_derivative_Pa_s,rate_derivative_max_native_id\n";
    responseCsv<<"part,time_s,tau_s,eta,native_id,actual_direction_vx,actual_direction_vz,Ace_derivative_x,Ace_derivative_z,theta_derivative_s_1,actual_rate_derivative_Pa_s,compression_derivative_Pa_s,LP_derivative_Pa_s,defect_derivative_Pa_s,divAce_derivative_Pa_s,chain_derivative_Pa_s,FS_Ace_derivative_Pa_s,chain_Ace_derivative_Pa_s,chain_gp_derivative_Pa_s,five_term_derivative_Pa_s,propagated_arithmetic_budget_Pa_s,plus_AV_became,plus_AV_ceased,minus_AV_became,minus_AV_ceased\n";
    unsigned calls=0,rateRows=0,responseRows=0,selectedTotal=0,coefficientChanges=0;double maxRatio=0;
    for(const Snapshot* base:{&first,&second}){
      Restore(*base);SoilUnchanged(*base);const auto initial=Select(*base);std::vector<unsigned> selected;for(unsigned q:initial)selected.push_back(Idpc[q]);selectedTotal+=unsigned(selected.size());std::vector<Response> measured;measured.reserve(5);
      for(unsigned evaluation=0;evaluation<5;evaluation++){
        const double eta=evaluation==0?0.:(evaluation<=2?.001:.0005);const int sign=evaluation==0?0:(evaluation%2?1:-1);Snapshot incoming=*base;unsigned vChanged=0;double maxDv=0;
        for(unsigned s=0;s<Total;s++)if(incoming.id[s]>=2060){const auto old=base->vel[s];incoming.vel[s]=TFloat3(float((1.+sign*eta)*double(old.x)),float((1.+sign*eta)*double(old.y)),float((1.+sign*eta)*double(old.z)));vChanged+=!Bits(incoming.vel[s],old);const auto delta=ToTDouble3(incoming.vel[s])-ToTDouble3(old);maxDv=(std::max)(maxDv,sqrt(Dot(delta,delta)));}
        Need(evaluation?vChanged>0:vChanged==0,"Actual float velocity direction vanished or baseline changed");Restore(incoming);SoilUnchanged(incoming);const auto byid=Map();const double clock=TimeStep;const int step=Nstep;Response out;bool cleanup=true;
        try{Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc,"Actual force-stage scratch absent");SoilUnchanged(incoming);unsigned fsSaved=0,fsBase=0,cBase=0,asBase=0,avPairs=0,avSwitch=0;double rateMax=0,ratio=0;
          for(unsigned q=Npb;q<Np;q++){const unsigned id=Idpc[q];Need(Finite(Acec[q])&&Finite(PoroThetac[q])&&Finite(PorePressRatec[q]),"Actual full5000 force/rate nonfinite");const auto sr=Rsigmac[q];Need(Finite(sr.xx)&&Finite(sr.yy)&&Finite(sr.zz)&&Finite(sr.xy)&&Finite(sr.yz)&&Finite(sr.xz),"Actual stress rate nonfinite");out.velocity[id]=TDouble3(Velrhopc[q].x,Velrhopc[q].y,Velrhopc[q].z);out.acc[id]=ToTDouble3(Acec[q]);out.theta[id]=PoroThetac[q];out.rate[id]=PorePressRatec[q];out.fs[id]=FSTypec[q];out.c[id]=CorrMatc[q];out.art[id]=ArtificialStressc[q];fsSaved+=FSTypec[q]!=base->fstype[base->byid[id]];if(evaluation){const auto& b=measured[0];fsBase+=out.fs[id]!=b.fs[id];cBase+=!Bits(out.c[id],b.c[id]);asBase+=!Bits(out.art[id],b.art[id]);}rateMax=(std::max)(rateMax,fabs(double(out.rate[id])));}
          for(unsigned id:selected){const unsigned q=byid[id],saved=base->byid[id];const auto t=Sum(q);out.terms[id]=t;out.av[id]=AvShadow(q);const unsigned became=evaluation?Difference(out.av[id],measured[0].av[id]):0,ceased=evaluation?Difference(measured[0].av[id],out.av[id]):0;avPairs+=unsigned(out.av[id].size());avSwitch+=became+ceased;ratio=(std::max)(ratio,fabs(double(out.rate[id])-t.rate)/t.budget);const auto x=Posc[q],vel=out.velocity[id];rates<<calls<<','<<base->part<<','<<clock<<','<<clock-sourceTime<<','<<eta<<','<<sign<<','<<id<<','<<x.x<<','<<x.z<<','<<base->vel[saved].x<<','<<base->vel[saved].z<<','<<vel.x<<','<<vel.z<<','<<vel.x-base->vel[saved].x<<','<<vel.z-base->vel[saved].z<<','<<PorePressc[q]<<','<<PoroJc[q]<<','<<Kplasticc[q]<<','<<base->fstype[saved]<<','<<out.fs[id]<<','<<out.theta[id]<<','<<out.acc[id].x<<','<<out.acc[id].z<<','<<out.rate[id]<<','<<t.compression<<','<<t.lp<<','<<t.defect<<','<<t.divace<<','<<t.chain<<','<<t.fsace<<','<<t.chainace<<','<<t.chaingp<<','<<t.rate<<','<<t.budget<<','<<out.av[id].size()<<','<<became<<','<<ceased<<'\n';rateRows++;}
          coefficientChanges+=fsBase+cBase+asBase;callsCsv<<calls<<','<<base->part<<','<<clock<<','<<clock-sourceTime<<','<<step<<','<<eta<<','<<sign<<','<<Soil<<','<<selected.size()<<','<<vChanged<<','<<maxDv<<','<<fsSaved<<','<<fsBase<<','<<cBase<<','<<asBase<<','<<avPairs<<','<<avSwitch<<','<<rateMax<<','<<ratio<<",1\n";maxRatio=(std::max)(maxRatio,ratio);Need(TimeStep==clock&&Nstep==step,"Force evaluation advanced time");PosInteraction_Forces();cleanup=false;
        }catch(...){if(cleanup)PosInteraction_Forces();throw;}Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Force scratch not released");SoilUnchanged(incoming);measured.push_back(std::move(out));
      }
      for(unsigned group=0;group<2;group++){
        const double eta=group==0?.001:.0005,den=2.*eta;const auto& b=measured[0];const auto& plus=measured[1+group*2];const auto& minus=measured[2+group*2];double nv=0,na=0,nr=0,nc=0,nq=0,nd=0,asym=0,pkin=0,prate=0,pcomp=0,pav=0,maxRate=0;unsigned maxId=0,fsChanges=0,cChanges=0,asChanges=0;
        for(unsigned id=2060;id<Original;id++){const unsigned s=base->byid[id];const double mass=base->volume[s]*base->rho[s],W=base->volume[s]*base->n[s]/double(SoilCte.PoreWaterBulkModulus),B=double(SoilCte.PoreWaterBulkModulus)/base->n[s];const auto u=(plus.velocity[id]-minus.velocity[id])/den,acc=(plus.acc[id]-minus.acc[id])/den,d=u-ToTDouble3(base->vel[s]);const double theta=(plus.theta[id]-minus.theta[id])/den,rate=(double(plus.rate[id])-minus.rate[id])/den,compression=-B*theta,av=rate-compression,oneSide=(double(plus.rate[id])+minus.rate[id]-2.*double(b.rate[id]))/eta;
          nv+=mass*Dot(u,u);na+=mass*Dot(acc,acc);nr+=W*rate*rate;nc+=W*compression*compression;nq+=W*av*av;nd+=mass*Dot(d,d);asym+=W*oneSide*oneSide;pkin+=mass*Dot(u,acc);prate+=W*double(base->p[s])*rate;pcomp+=W*double(base->p[s])*compression;pav+=W*double(base->p[s])*av;if(fabs(rate)>maxRate){maxRate=fabs(rate);maxId=id;}fsChanges+=(plus.fs[id]!=b.fs[id])+(minus.fs[id]!=b.fs[id]);cChanges+=!Bits(plus.c[id],b.c[id]);cChanges+=!Bits(minus.c[id],b.c[id]);asChanges+=!Bits(plus.art[id],b.art[id]);asChanges+=!Bits(minus.art[id],b.art[id]);}
        Need(nv>0&&Finite(nv)&&Finite(na)&&Finite(nr)&&Finite(nc)&&Finite(nq)&&Finite(pkin)&&Finite(prate)&&Finite(pcomp)&&Finite(pav),"Invalid full5000 weighted direction");directions<<base->part<<','<<base->time<<','<<base->time-sourceTime<<','<<eta<<','<<selected.size()<<','<<sqrt(nv)<<','<<sqrt(na)<<','<<sqrt(nr)<<','<<sqrt(nc)<<','<<sqrt(nq)<<','<<sqrt(na/nv)<<','<<sqrt(nr/nv)<<','<<.0000025*sqrt(nr/nv)<<','<<pkin<<','<<prate<<','<<pcomp<<','<<pav<<','<<sqrt(nd)<<','<<sqrt(asym)<<','<<fsChanges<<','<<cChanges<<','<<asChanges<<','<<maxRate<<','<<maxId<<'\n';
        for(unsigned id:selected){const auto& p=plus.terms[id];const auto& m=minus.terms[id];const auto u=(plus.velocity[id]-minus.velocity[id])/den,acc=(plus.acc[id]-minus.acc[id])/den;const double actual=(double(plus.rate[id])-minus.rate[id])/den,shadow=(p.rate-m.rate)/den,budget=(p.budget+m.budget)/den+16.*DBL_EPSILON*(std::max)(1.,fabs(actual)+fabs(shadow));Need(fabs(actual-shadow)<=budget,"Differenced actual rate/five-term propagated arithmetic budget failed");responseCsv<<base->part<<','<<base->time<<','<<base->time-sourceTime<<','<<eta<<','<<id<<','<<u.x<<','<<u.z<<','<<acc.x<<','<<acc.z<<','<<(plus.theta[id]-minus.theta[id])/den<<','<<actual<<','<<(p.compression-m.compression)/den<<','<<(p.lp-m.lp)/den<<','<<(p.defect-m.defect)/den<<','<<(p.divace-m.divace)/den<<','<<(p.chain-m.chain)/den<<','<<(p.fsace-m.fsace)/den<<','<<(p.chainace-m.chainace)/den<<','<<(p.chaingp-m.chaingp)/den<<','<<shadow<<','<<budget<<','<<Difference(plus.av[id],b.av[id])<<','<<Difference(b.av[id],plus.av[id])<<','<<Difference(minus.av[id],b.av[id])<<','<<Difference(b.av[id],minus.av[id])<<'\n';responseRows++;}
      }
    }
    Need(calls==10&&rateRows==5*selectedTotal&&responseRows==2*selectedTotal,"Exact10-call/two-state coverage differs");for(auto* f:{&rates,&callsCsv,&directions,&responseCsv}){f->flush();Need(bool(*f),"CSV write failed");}
    std::ofstream done(pathfs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_av_velocity_r1\",\"passed\":true,\"source_parts\":[49,71],\"native_saved_samples\":72,\"AS_exponent\":3,\"AV_coefficient\":"<<double(Visco)<<",\"eta\":[0.001,0.0005],\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"actual_ct_calls\":10,\"actual_Darcy_calls\":10,\"call_rows\":10,\"rate_rows\":"<<rateRows<<",\"response_rows\":"<<responseRows<<",\"direction_rows\":4,\"selected_total\":"<<selectedTotal<<",\"physical_steps\":0,\"material_return_calls\":0,\"primary_bits_match_each_explicit_incoming_state\":true,\"only_velocity_perturbed\":true,\"actual_float_velocity_directions_exported\":true,\"original_AV_parameter_unchanged\":true,\"soil_FS_C_AS_held\":"<<(coefficientChanges==0?"true":"false")<<",\"coefficient_change_observations\":"<<coefficientChanges<<",\"max_rate_shadow_budget_fraction\":"<<maxRatio<<",\"five_term_sum_is_test_side_shadow\":true,\"AV_branch_counts_are_test_side_shadow\":true,\"global_gains_use_all5000\":true,\"powers_are_conditional_not_total_energy_proof\":true,\"private_GPU_filter_wrapper_not_called\":true,\"source_metadata_rewritten\":false,\"original_GPU_or_unsaved_stage_replay\":false,\"full_two_stage_Jacobian\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_SHEPARD_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 EXISTING_SHEPARD_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_shepard_partial_r1"),"Only closed72-frame Shepard partial is admitted");Snapshot first(folder,Parts[0]),second(folder,Parts[1]);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU component output required; real PRE loader flags remain legal");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),first,second);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Frozen AV velocity component failed; preserve first result\n";return 2;}}
