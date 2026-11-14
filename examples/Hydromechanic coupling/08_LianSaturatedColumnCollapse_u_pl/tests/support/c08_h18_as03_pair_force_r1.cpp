// Author-only four-state actual-CPU pair force/RHS audit; no time or material update.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JCellDivCpuSingle.h"
#include "JCellSearch_inline.h"
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
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("C08H18As03PairForce","r1","14-11-2026");
namespace pf=std::filesystem;
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=301;
static constexpr unsigned Parts[4]={38,76,92,300},Steps[4]={2076001,2152001,2184001,2600000};
static const char* Terms[7]={"compression","LP","Taylor_pressure","Da","FS_Ace_Lx","chain_pressure","chain_Ace"};
static const char* Groups[3]={"all","fluid_donors","fixed_donors"};
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Original typed22 ABI required");
static void Need(bool x,const std::string& s){if(!x)throw std::runtime_error(s);}
static std::string Detail(const char* label,unsigned part,unsigned id,double actual,double reference,double budget){std::ostringstream s;s<<std::setprecision(17)<<label<<" part="<<part<<" ID="<<id<<" actual="<<actual<<" reference="<<reference<<" budget="<<budget;return s.str();}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Abs(tdouble3 a){return TDouble3(fabs(a.x),fabs(a.y),fabs(a.z));}
static tdouble3 Product(tmatrix3d c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
static double RoundoffGamma(unsigned n){const double u=.5*DBL_EPSILON,t=n*u;Need(t<1,"Invalid arithmetic operation count");return t/(1-t);}
struct Stamp{pf::path p;std::uintmax_t bytes;pf::file_time_type time;explicit Stamp(pf::path q):p(q),bytes(pf::file_size(q)),time(pf::last_write_time(q)){}void Check()const{Need(pf::file_size(p)==bytes&&pf::last_write_time(p)==time,"Protected file changed: "+p.string());}};
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}
struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fs,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,normal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pf::path& folder,unsigned which):part(Parts[which]),completed(Steps[which]),byid(Original,UINT_MAX){
    std::ifstream clocks(folder/"clocks.csv");std::string line;Need(bool(std::getline(clocks,line)),"Missing native clocks");unsigned rows=0;bool found=false;
    while(std::getline(clocks,line)){std::stringstream ss(line);std::vector<std::string> c;std::string x;while(std::getline(ss,x,','))c.push_back(x);Need(c.size()==11,"Native clock layout differs");if(std::stoul(c[0])==part){Need(!found&&std::stoul(c[4])==completed,"Completed-step clock differs");time=std::stod(c[2]);found=true;}rows++;}Need(found&&rows==Samples,"Native full301 clock coverage differs");
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pf::file_size(folder/"typed22.bin")==12+Samples*stride,"Original full301/6805/22 extent differs");f.seekg(std::streamoff(12+part*stride));double nativeTime;f.read(reinterpret_cast<char*>(&nativeTime),8);Need(bool(f)&&Bits(time,nativeTime),"Actual native/CSV clock differs");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);normal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fs=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];Need(a<Original&&byid[a]==UINT_MAX&&(a<Fixed||a>=2060),"Unexpected/duplicate/retired bedroles native ID");byid[a]=q;if(a<Fixed)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid native soil ledger");if(fs[q]==2||fs[q]==3)Need(p[q]<=0,"Saved FS2/3 pressure is positive");}}Need(fixed==Fixed&&soil==Soil,"Native bedroles ownership differs");
  }
};
class Probe:public JSphCpuSingle{
  std::vector<typecode> code;std::vector<tfloat3> wallnormal;std::vector<byte> slip;
  std::vector<unsigned> Map()const{Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Completed released allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate ID");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil role differs");soil++;}else{Need(id<Fixed&&q<Npb&&CODE_IsFixed(Codec[q]),"Fixed bedroles role differs");fixed++;}}Need(soil==Soil&&fixed==Fixed,"Released ID counts differ");return b;}
  void Roles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],code[id]),"ID-owned code changed");if(q<Npb)Need(Bits(BoundNormalc[q],wallnormal[id])&&Bits(BoundSlipModec[q],slip[id]),"ID-owned wall normal/slip changed");}}
  void Copy(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Restore ID differs");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fs[s];FSNormalc[q]=a.normal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Native J/n/V/rho/k/cache ledger differs");}}
  void Unchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto sigma=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],sigma)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force changed soil primary state");}Roles();Ledger(a);Need(Bits(TimeStep,a.time)&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step clock/state advanced");}
  void Restore(const Snapshot& a){Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch owned");Map();Copy(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Cell rebuild excluded a particle");Map();Copy(a);Roles();Ledger(a);TimeStep=a.time;Nstep=a.completed;Unchanged(a);}
  struct SwitchScope{bool& as;float& av;const bool oldas;const float oldav;SwitchScope(bool& a,float& v,unsigned mode):as(a),av(v),oldas(a),oldav(v){as=mode!=1;av=mode==2?0.f:oldav;}~SwitchScope(){as=oldas;av=oldav;}};
  struct Response{std::vector<tdouble3> ace;std::vector<float> rate;std::vector<unsigned> fs;Response():ace(Original),rate(Original),fs(Original){}};
  struct Direct{tdouble3 raw,ci,cj,effective,pore,total,as,av,total_literal,as_literal,av_literal;float rr2=0,w=0,wdp=0,ratio=0,f=0,dot=0;double vi=0,vj=0,rhoi=0,rhoj=0;};
  static tdouble3 Cast(tdouble3 a){return TDouble3(float(a.x),float(a.y),float(a.z));}
  Direct PairLiteral(unsigned i,unsigned j)const{
    Need(i>=Npb&&j>=Npb&&CODE_IsFluid(Codec[i])&&CODE_IsFluid(Codec[j]),"Direct audit is soil-soil only");Direct d;double ni,nj;GetPorosityFeedbackStateCpu(i,ni,d.vi,d.rhoi);GetPorosityFeedbackStateCpu(j,nj,d.vj,d.rhoj);
    const float dx=float(Posc[i].x-Posc[j].x),dy=float(Posc[i].y-Posc[j].y),dz=float(Posc[i].z-Posc[j].z);d.rr2=dx*dx+dy*dy+dz*dz;
    Need(d.rr2<=KernelSize2&&d.rr2>=ALMOSTZERO,"Selected native pair outside actual force support");
    if(ArtificialStress)d.w=fsph::GetKernel_WabFac<KERNEL_Wendland>(CSP,d.rr2,d.f);else d.f=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,d.rr2);
    const float gx=d.f*dx,gy=d.f*dy,gz=d.f*dz;d.raw=TDouble3(gx,gy,gz);d.ci=Product(CorrMatc[i],d.raw);d.cj=Product(CorrMatc[j],d.raw);
    const tsymatrix3f a=ToTSymMatrix3f(Sigmac[i]),b=ToTSymMatrix3f(Sigmac[j]);const double c=d.vj/d.rhoi,pw=double(PorePressc[i])+double(PorePressc[j]);
    const double xx=double(a.xx)+b.xx-pw,yy=double(a.yy)+b.yy-pw,zz=double(a.zz)+b.zz-pw,xy=double(a.xy)+b.xy,xz=double(a.xz)+b.xz,yz=double(a.yz)+b.yz;
    d.total_literal=TDouble3(c*(xx*gx+xy*gy+xz*gz),c*(yy*gy+xy*gx+yz*gz),c*(zz*gz+yz*gy+xz*gx));d.total=Cast(d.total_literal);
    // The real force commits total stress once; these two double rows are bookkeeping shadows only.
    d.effective=TDouble3(c*((double(a.xx)+b.xx)*gx+xy*gy+xz*gz),c*((double(a.yy)+b.yy)*gy+xy*gx+yz*gz),c*((double(a.zz)+b.zz)*gz+yz*gy+xz*gx));d.pore=d.raw*(-c*pw);
    d.as_literal=d.as=d.av_literal=d.av=TDouble3(0);
    if(ArtificialStress&&ArtificialStressc){
      d.wdp=fsph::GetKernel_Wab<KERNEL_Wendland>(CSP,float(Dp*Dp));Need(d.wdp>0,"Actual W(dp) is invalid");const float inv=1.f/d.wdp;d.ratio=d.w*inv;
      const auto a=ArtificialStressc[i],b=ArtificialStressc[j];const double xx=double(a.xx)+b.xx,yy=double(a.yy)+b.yy,zz=double(a.zz)+b.zz,xy=double(a.xy)+b.xy,xz=double(a.xz)+b.xz,yz=double(a.yz)+b.yz;
      if(d.ratio>0.f&&(xx||yy||zz||xy||xz||yz)){
        const double m=d.vj/d.rhoi*double(powf(d.ratio,ArtificialStressExp)),axx=m*xx,ayy=m*yy,azz=m*zz,axy=m*xy,axz=m*xz,ayz=m*yz;
        d.as_literal=TDouble3(axx*gx+axy*gy+axz*gz,ayy*gy+axy*gx+ayz*gz,azz*gz+ayz*gy+axz*gx);d.as=Cast(d.as_literal);
      }
    }
    const float vx=Velrhopc[i].x-Velrhopc[j].x,vy=Velrhopc[i].y-Velrhopc[j].y,vz=Velrhopc[i].z-Velrhopc[j].z;d.dot=dx*vx+dy*vy+dz*vz;
    if(d.dot<0&&Visco!=0.f){
      const float dot_rr2=d.dot/(d.rr2+Eta2),amubar=KernelH*dot_rr2,cbar=float(Cs0);
      const double robar=(d.rhoi+d.rhoj)*.5,mass2=d.vj*d.rhoj,pi=(-double(Visco)*double(cbar)*double(amubar)/robar)*mass2;
      d.av_literal=TDouble3(-pi*double(gx),-pi*double(gy),-pi*double(gz));d.av=Cast(d.av_literal);
    }
    Need(Finite(d.total)&&Finite(d.as)&&Finite(d.av)&&Finite(d.raw)&&Finite(d.ci)&&Finite(d.cj),"Nonfinite direct literal result");return d;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::array<Snapshot,4>& states){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2/bed-last handoff required");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original current scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.3f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Exact original AS03/Wendland/5us context required");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();const double release=GravityPreloadActualTime;const unsigned pairs[2][2]={{6767,6865},{4953,4954}};const unsigned focusIDs[4]={6767,6865,4953,4954};const char* modes[3]={"baseline","AS_off","AV_off"};
    std::ofstream soil(pf::path(cfg->DirOut)/"soil_force.csv"),focus(pf::path(cfg->DirOut)/"focus.csv"),paircsv(pf::path(cfg->DirOut)/"pairs.csv"),direct(pf::path(cfg->DirOut)/"direct_pairs.csv"),callsCsv(pf::path(cfg->DirOut)/"calls.csv");for(auto f:{&soil,&focus,&paircsv,&direct,&callsCsv})*f<<std::setprecision(17);
    soil<<"part,time_s,tau_s,completed_step,mode,native_id,Acex,Acey,Acez,minus_baseline_Acex,minus_baseline_Acey,minus_baseline_Acez,pressure_rate_Pa_s,minus_baseline_rate_Pa_s,saved_FS,fresh_FS,theta_s_1\n";
    focus<<"part,time_s,tau_s,completed_step,mode,native_id,x_m,y_m,z_m,vx,vy,vz,p_Pa,P0_Pa,J,kappa,saved_FS,fresh_FS,Cxx,Cxy,Cxz,Cyx,Cyy,Cyz,Czx,Czy,Czz,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,AS_Rxx,AS_Ryy,AS_Rzz,AS_Rxy,AS_Ryz,AS_Rxz,theta_s_1,Rsigma_xx,Rsigma_yy,Rsigma_zz,Rsigma_xy,Rsigma_yz,Rsigma_xz,NoPenScratchx,NoPenScratchy,NoPenScratchz,NoPenScratchw\n";
    paircsv<<"part,time_s,tau_s,completed_step,mode,id_i,id_j,r_m,rdot_m_s,relative_all_neighbor_a_radial_m_s2,tangential_curvature_m_s2,rddot_m_s2,minus_baseline_relative_a_radial_m_s2,pressure_rate_i_Pa_s,pressure_rate_j_Pa_s\n";
    direct<<"part,time_s,tau_s,completed_step,mode,id_i,id_j,term,source_term_not_split_shadow,r_m,rdot_m_s,W_ratio,raw_gradx,raw_grady,raw_gradz,Ci_gradx,Ci_grady,Ci_gradz,Cj_gradx,Cj_grady,Cj_gradz,mass_i,mass_j,ai_x,ai_y,ai_z,aj_x,aj_y,aj_z,relative_a_radial_m_s2,Fi_radial_N_per_m,Fj_radial_along_ij_N_per_m,pair_power_W_per_m,force_balance_norm_N_per_m,cast_residual_i_norm_m_s2,cast_residual_j_norm_m_s2,total_minus_eff_pressure_shadow_i_norm_m_s2\n";
    callsCsv<<"part,time_s,tau_s,completed_step,mode,AS_enabled,AS_coefficient,AS_exponent,AV_coefficient,soil_rows,source_saved_FS_changes,baseline_FS_changes,primary_bits_unchanged\n";
    unsigned calls=0,soilRows=0,focusRows=0,pairRows=0,directRows=0;
    for(const auto& state:states){std::vector<Response> responses;responses.reserve(3);
      for(unsigned mode=0;mode<3;mode++){
        Restore(state);Unchanged(state);Response response;bool cleanup=true;unsigned fsChanges=0,baseFSChanges=0;
        {SwitchScope switches(ArtificialStress,Visco,mode);try{
          Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&CorrMatc&&(ArtificialStress?ArtificialStressc!=NULL:ArtificialStressc==NULL),"Actual force scratch incomplete");Unchanged(state);const auto byid=Map();
          for(unsigned q=Npb;q<Np;q++){
            const unsigned id=Idpc[q],s=state.byid[id];Need(Finite(Acec[q])&&Finite(PorePressRatec[q])&&Finite(PoroThetac[q]),"Nonfinite full-neighbor response");response.ace[id]=ToTDouble3(Acec[q]);response.rate[id]=PorePressRatec[q];response.fs[id]=FSTypec[q];const auto da=mode?response.ace[id]-responses[0].ace[id]:TDouble3(0);const double dp=mode?double(response.rate[id])-responses[0].rate[id]:0;fsChanges+=response.fs[id]!=state.fs[s];baseFSChanges+=mode&&response.fs[id]!=responses[0].fs[id];soil<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<id<<','<<Acec[q].x<<','<<Acec[q].y<<','<<Acec[q].z<<','<<da.x<<','<<da.y<<','<<da.z<<','<<response.rate[id]<<','<<dp<<','<<state.fs[s]<<','<<response.fs[id]<<','<<PoroThetac[q]<<'\n';soilRows++;
          }
          for(unsigned id:focusIDs){
            const unsigned q=byid[id],s=state.byid[id];const auto v=Velrhopc[q];const auto x=Posc[q];const auto c=CorrMatc[q];const auto stress=Sigmac[q];const auto r=Rsigmac[q];tsymatrix3f as={0,0,0,0,0,0};if(ArtificialStressc)as=ArtificialStressc[q];const tfloat4 nopen=NoPenShiftc?NoPenShiftc[q]:TFloat4(0);
            for(double value:{c.a11,c.a12,c.a13,c.a21,c.a22,c.a23,c.a31,c.a32,c.a33,double(r.xx),double(r.yy),double(r.zz),double(r.xy),double(r.yz),double(r.xz),double(as.xx),double(as.yy),double(as.zz),double(as.xy),double(as.yz),double(as.xz)})Need(Finite(value),"Nonfinite actual focus gradient/stress/AS scratch");
            focus<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<PoroJc[q]<<','<<Kplasticc[q]<<','<<state.fs[s]<<','<<FSTypec[q]<<','<<c.a11<<','<<c.a12<<','<<c.a13<<','<<c.a21<<','<<c.a22<<','<<c.a23<<','<<c.a31<<','<<c.a32<<','<<c.a33<<','<<stress.xx<<','<<stress.yy<<','<<stress.zz<<','<<stress.xy<<','<<stress.yz<<','<<stress.xz<<','<<as.xx<<','<<as.yy<<','<<as.zz<<','<<as.xy<<','<<as.yz<<','<<as.xz<<','<<PoroThetac[q]<<','<<r.xx<<','<<r.yy<<','<<r.zz<<','<<r.xy<<','<<r.yz<<','<<r.xz<<','<<nopen.x<<','<<nopen.y<<','<<nopen.z<<','<<nopen.w<<'\n';focusRows++;
          }
          for(const auto& pair:pairs){
            const unsigned i=byid[pair[0]],j=byid[pair[1]];const auto dx=Posc[i]-Posc[j];const double distance=sqrt(Dot(dx,dx));Need(distance>0&&Finite(distance),"Coincident pair");const auto normal=dx/distance,vi=TDouble3(Velrhopc[i].x,Velrhopc[i].y,Velrhopc[i].z),vj=TDouble3(Velrhopc[j].x,Velrhopc[j].y,Velrhopc[j].z),dv=vi-vj;const double rdot=Dot(dv,normal),curvature=(Dot(dv,dv)-rdot*rdot)/distance,an=Dot(response.ace[pair[0]]-response.ace[pair[1]],normal),baseline=mode?Dot(responses[0].ace[pair[0]]-responses[0].ace[pair[1]],normal):an;
            paircsv<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<pair[0]<<','<<pair[1]<<','<<distance<<','<<rdot<<','<<an<<','<<curvature<<','<<an+curvature<<','<<an-baseline<<','<<response.rate[pair[0]]<<','<<response.rate[pair[1]]<<'\n';pairRows++;
            const Direct a=PairLiteral(i,j),b=PairLiteral(j,i);const double mi=a.vi*a.rhoi,mj=a.vj*a.rhoj;const char* names[5]={"effective_shadow","pore_shadow","literal_total_stress_commit","literal_AS_commit","literal_AV_commit"};const tdouble3 aa[5]={a.effective,a.pore,a.total,a.as,a.av},bb[5]={b.effective,b.pore,b.total,b.as,b.av},al[5]={a.effective,a.pore,a.total_literal,a.as_literal,a.av_literal},bl[5]={b.effective,b.pore,b.total_literal,b.as_literal,b.av_literal};
            for(unsigned term=0;term<5;term++){
              const auto fi=aa[term]*mi,fj=bb[term]*mj,ei=aa[term]-al[term],ej=bb[term]-bl[term],split=a.total_literal-a.effective-a.pore;
              direct<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<pair[0]<<','<<pair[1]<<','<<names[term]<<','<<(term>=2)<<','<<distance<<','<<rdot<<','<<a.ratio<<','<<a.raw.x<<','<<a.raw.y<<','<<a.raw.z<<','<<a.ci.x<<','<<a.ci.y<<','<<a.ci.z<<','<<a.cj.x<<','<<a.cj.y<<','<<a.cj.z<<','<<mi<<','<<mj<<','<<aa[term].x<<','<<aa[term].y<<','<<aa[term].z<<','<<bb[term].x<<','<<bb[term].y<<','<<bb[term].z<<','<<Dot(aa[term]-bb[term],normal)<<','<<Dot(fi,normal)<<','<<Dot(fj,normal)<<','<<Dot(fi,vi)+Dot(fj,vj)<<','<<sqrt(Dot(fi+fj,fi+fj))<<','<<sqrt(Dot(ei,ei))<<','<<sqrt(Dot(ej,ej))<<','<<sqrt(Dot(split,split))<<'\n';directRows++;
            }
          }
          Unchanged(state);PosInteraction_Forces();cleanup=false;
        }catch(...){if(cleanup)PosInteraction_Forces();throw;}}
        Need(ArtificialStress&&Visco==.1f&&!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Flags/scratch not restored");Unchanged(state);responses.push_back(std::move(response));Copy(state);Unchanged(state);
        callsCsv<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<(mode!=1)<<','<<double(ArtificialStressCoef)<<','<<double(ArtificialStressExp)<<','<<(mode==2?0.:double(Visco))<<','<<Soil<<','<<fsChanges<<','<<baseFSChanges<<",1\n";for(auto f:{&soil,&focus,&paircsv,&direct,&callsCsv}){f->flush();Need(bool(*f),"Complete audit CSV write failed");}
      }
    }
    Need(calls==12&&soilRows==60000&&focusRows==48&&pairRows==24&&directRows==120,"Exact four-state three-mode two-pair coverage required");
    std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_as03_pair_force_r1\",\"passed\":true,\"source_parts\":[38,76,92,300],\"pair_IDs\":[[6767,6865],[4953,4954]],\"source_samples\":301,\"source_release_time_s\":"<<release<<",\"actual_force_calls\":12,\"actual_Darcy_calls\":12,\"soil_rows\":60000,\"focus_rows\":48,\"pair_rows\":24,\"direct_pair_rows\":120,\"all5000_soil_primary_bits_unchanged_per_call\":true,\"all_primary_restored_before_each_mode\":true,\"direct_pair_is_frozen_CPU_literal_not_GPU_callback\":true,\"effective_and_pressure_split_is_double_bookkeeping\":true,\"counterfactual_differences_are_not_strict_additive_parts\":true,\"ASoff_kernel_function_path_can_change_roundoff\":true,\"corrected_gradients_are_reported_not_used_in_momentum\":true,\"separate_plane_projection_or_reaction_executed\":false,\"original_Single_no_hook\":true,\"physical_steps\":0,\"material_return_calls\":0,\"filter_calls\":0,\"saved_GPU_substages_reconstructed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_AS03_FULL301 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_AS03_SEED FRESH_OUT");const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_as03n255_full3_r1/native_r1"),"Only the existing complete AS03 full301 native is admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);for(const char* leaf:{"c08_h18_as03n255_full3_r1.run.json","c08_h18_as03n255_full3_r1.call.json","c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json","c08_h18_as03_pair_force_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);protectedFiles.emplace_back(pf::absolute(argv[0]));
  for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const std::array<Snapshot,4> states={Snapshot(native,0),Snapshot(native,1),Snapshot(native,2),Snapshot(native,3)};AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_as03_pair_force_r1")&&!pf::exists(cfg.DirOut),"Exact AS03 seed and new zero-step output required");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),states);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Fresh zero-step pair audit failed; preserve outputs\n";return 2;}}
