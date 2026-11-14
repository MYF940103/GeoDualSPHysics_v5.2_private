// Three fresh actual-CPU force/RHS evaluations on sealed completed states; no time update.
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
JAppInfo AppInfo("C08H18StorageRhs","r1","14-11-2026");
namespace pf=std::filesystem;
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=91;
static constexpr unsigned Parts[3]={30,60,90},Steps[3]={2060001,2120001,2180000};
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
static double Gamma(unsigned n){const double u=.5*DBL_EPSILON,t=n*u;Need(t<1,"Invalid arithmetic operation count");return t/(1-t);}
struct Stamp{pf::path p;std::uintmax_t bytes;pf::file_time_type time;explicit Stamp(pf::path q):p(q),bytes(pf::file_size(q)),time(pf::last_write_time(q)){}void Check()const{Need(pf::file_size(p)==bytes&&pf::last_write_time(p)==time,"Protected file changed: "+p.string());}};
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}
struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fs,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,normal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pf::path& folder,unsigned which):part(Parts[which]),completed(Steps[which]),byid(Original,UINT_MAX){
    std::ifstream clocks(folder/"clocks.csv");std::string line;Need(bool(std::getline(clocks,line)),"Missing native clocks");unsigned rows=0;bool found=false;
    while(std::getline(clocks,line)){std::stringstream ss(line);std::vector<std::string> c;std::string x;while(std::getline(ss,x,','))c.push_back(x);Need(c.size()==11,"Native clock layout differs");if(std::stoul(c[0])==part){Need(!found&&std::stoul(c[4])==completed,"Completed-step clock differs");time=std::stod(c[2]);found=true;}rows++;}Need(found&&rows==Samples,"Native full91 clock coverage differs");
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pf::file_size(folder/"typed22.bin")==12+Samples*stride,"Original full91/6805/22 extent differs");f.seekg(std::streamoff(12+part*stride));double nativeTime;f.read(reinterpret_cast<char*>(&nativeTime),8);Need(bool(f)&&Bits(time,nativeTime),"Actual native/CSV clock differs");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);normal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fs=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];Need(a<Original&&byid[a]==UINT_MAX&&(a<Fixed||a>=2060),"Unexpected/duplicate/retired bedroles native ID");byid[a]=q;if(a<Fixed)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid native soil ledger");if(fs[q]==2||fs[q]==3)Need(p[q]<=0,"Saved FS2/3 pressure is positive");}}Need(fixed==Fixed&&soil==Soil,"Native bedroles ownership differs");
  }
};
struct Sums{double lp=0,da=0,lpabs=0,daabs=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gradj=TDouble3(0),lxabs=TDouble3(0),gpabs=TDouble3(0),jabs=TDouble3(0);unsigned count=0;
  void Add(tdouble3 d,tdouble3 gi,double v,double w,double dp,tdouble3 daij,double dj){lp+=w*dp;lx=lx+d*w;gp=gp-gi*(v*dp);gradj=gradj+gi*(v*dj);da+=v*Dot(daij,gi);lpabs+=fabs(w*dp);daabs+=v*Dot(Abs(daij),Abs(gi));lxabs=lxabs+Abs(d*w);gpabs=gpabs+Abs(gi*(v*dp));jabs=jabs+Abs(gi*(v*dj));count++;}
};
struct Global{unsigned count=0,changed=0;double volume=0,weight=0,storage=0,actualQ=0,actualAbs=0,coefficientQ=0,error=0,budget=0;std::array<double,7> q{},absq{};};
class Probe:public JSphCpuSingle{
  std::vector<typecode> code;std::vector<tfloat3> wallnormal;std::vector<byte> slip;
  std::vector<unsigned> Map()const{Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Completed released allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate ID");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil role differs");soil++;}else{Need(id<Fixed&&q<Npb&&CODE_IsFixed(Codec[q]),"Fixed bedroles role differs");fixed++;}}Need(soil==Soil&&fixed==Fixed,"Released ID counts differ");return b;}
  void Roles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],code[id]),"ID-owned code changed");if(q<Npb)Need(Bits(BoundNormalc[q],wallnormal[id])&&Bits(BoundSlipModec[q],slip[id]),"ID-owned wall normal/slip changed");}}
  void Copy(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Restore ID differs");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fs[s];FSNormalc[q]=a.normal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Native J/n/V/rho/k/cache ledger differs");}}
  void Unchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto sigma=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],sigma)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force changed soil primary state");}Roles();Ledger(a);Need(Bits(TimeStep,a.time)&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step clock/state advanced");}
  void Restore(const Snapshot& a){Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch owned");Map();Copy(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Cell rebuild excluded a particle");Map();Copy(a);Roles();Ledger(a);TimeStep=a.time;Nstep=a.completed;Unchanged(a);}
  std::array<Sums,3> Assemble(unsigned i)const{
    std::array<Sums,3> r;const double v0=double(MassFluid)/double(RhopZero);const tmatrix3d ci=CorrMatc[i];
    for(unsigned group=0;group<2;group++){const bool boundary=group==1;const StNgSearch ngs=nsearch::Init(Dcellc[i],boundary,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned j=range.x;j<range.y;j++)if(CODE_IsFluid(Codec[j])||(boundary&&CODE_IsFixed(Codec[j]))){
          const tdouble3 d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=d.x*d.x+d.y*d.y+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;Need(!boundary||BoundModec[j]!=BMODE_MDBC2OFF,"Actual Darcy contains disabled wall donor");
          const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const tdouble3 g=d*fac,gi=Product(ci,g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j],dp=double(PorePressc[i])-double(PorePressc[j]);
          const double w=v*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr+double(Eta2));const tdouble3 da=TDouble3(double(Acec[j].x)-Acec[i].x,double(Acec[j].y)-Acec[i].y,double(Acec[j].z)-Acec[i].z);
          r[0].Add(d,gi,v,w,dp,da,PoroJc[j]-PoroJc[i]);r[group+1].Add(d,gi,v,w,dp,da,PoroJc[j]-PoroJc[i]);
        }
      }
    }return r;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::array<Snapshot,3>& states){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2 PRE/bedroles handoff differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.5f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Wendland N255 material/AS/AV/dt differs");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();const double release=GravityPreloadActualTime,kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,gamma=rho*9.80665;
    std::ofstream soil(pf::path(cfg->DirOut)/"soil_rhs.csv"),terms(pf::path(cfg->DirOut)/"terms.csv"),summary(pf::path(cfg->DirOut)/"summary.csv"),walls(pf::path(cfg->DirOut)/"walls.csv");for(auto f:{&soil,&terms,&summary,&walls})*f<<std::setprecision(17);
    soil<<"part,time_s,tau_s,completed_step,native_id,x_m,y_m,z_m,p_Pa,P0_Pa,J,n,V_m2,k_m_s,storage_weight,saved_theta_s_1,fresh_theta_s_1,saved_FS,fresh_FS,FSnx,FSny,FSnz,Acex,Acey,Acez,Cxx,Cxy,Cxz,Cyx,Cyy,Cyz,Czx,Czy,Czz,Rsigma_xx,Rsigma_yy,Rsigma_zz,Rsigma_xy,Rsigma_yz,Rsigma_xz,actual_rate_Pa_s,literal_reference_Pa_s,final_float_error_Pa_s,final_float_budget_Pa_s,expanded_rate_Pa_s,expanded_error_Pa_s,expanded_budget_Pa_s,coefficient_Q_m2_s\n";
    terms<<"part,time_s,tau_s,completed_step,native_id,fresh_FS,donor_group,neighbors,LP,Lxx,Lxy,Lxz,gpx,gpy,gpz,Da,gradJx,gradJy,gradJz";for(const char* n:Terms)terms<<','<<n<<"_Pa_s,"<<n<<"_Q_m2_s";terms<<'\n';
    walls<<"part,time_s,completed_step,native_id,x_m,y_m,z_m,J,p_Pa,P0_Pa,physical_vx,physical_vy,physical_vz,derivative_vx,derivative_vy,derivative_vz,Acex,Acey,Acez,Cxx,Cxy,Cxz,Cyx,Cyy,Cyz,Czx,Czy,Czz,mode,active,normalx,normaly,normalz,slip\n";
    summary<<"part,time_s,tau_s,completed_step,donor_group,receiver_group,receivers,saved_FS_changes,sumV_m2,sum_weight,sum_storage_proxy_m2,actual_Q_all_only_m2_s,coefficient_Q_all_only_m2_s,expanded_Q_m2_s,conditional_storage_derivative_all_only_m2_s,sum_weighted_abs_rate_error_m2_s,sum_weighted_rate_budget_m2_s,global_reconciliation_error_all_only_m2_s,global_reconciliation_budget_all_only_m2_s";for(const char* n:Terms)summary<<','<<n<<"_Q_m2_s,"<<n<<"_absQ_m2_s";summary<<'\n';
    unsigned calls=0,soilRows=0,termRows=0,summaryRows=0,wallRows=0;double maxFloatRatio=0,maxExpandedRatio=0;
    for(const auto& a:states){Restore(a);bool cleanup=true;try{
      Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc&&CorrMatc,"Complete actual force scratch missing");Unchanged(a);std::array<std::array<Global,3>,3> sums;
      for(unsigned q=0;q<Npb;q++){const bool active=BoundModec[q]!=BMODE_MDBC2OFF;const auto normal=BoundNormalc[q];const auto v=Velrhopc[q];const auto ace=Acec[q];walls<<a.part<<','<<TimeStep<<','<<unsigned(Nstep)<<','<<Idpc[q]<<','<<Posc[q].x<<','<<Posc[q].y<<','<<Posc[q].z<<','<<PoroJc[q]<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<v.x<<','<<v.y<<','<<v.z;
        if(active){const auto dv=BoundDerivativeVelc[q];walls<<','<<dv.x<<','<<dv.y<<','<<dv.z;}else walls<<",,,";walls<<','<<ace.x<<','<<ace.y<<','<<ace.z;
        if(active){const auto C=CorrMatc[q];walls<<','<<C.a11<<','<<C.a12<<','<<C.a13<<','<<C.a21<<','<<C.a22<<','<<C.a23<<','<<C.a31<<','<<C.a32<<','<<C.a33;}else walls<<",,,,,,,,,";
        walls<<','<<unsigned(BoundModec[q])<<','<<active<<','<<normal.x<<','<<normal.y<<','<<normal.z<<','<<unsigned(BoundSlipModec[q])<<'\n';wallRows++;}
      for(unsigned i=Npb;i<Np;i++){const unsigned id=Idpc[i],s=a.byid[id];const auto r=Assemble(i);const Sums& z=r[0];const auto ai=ToTDouble3(Acec[i]);const bool sf=IsFreeSurfaceParticle(i,Codec,FSTypec);double n,V,rhot;GetPorosityFeedbackStateCpu(i,n,V,rhot);const double k=GetDynamicConductivityCpu(i),B=kw/n,dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk),weight=n*V/kw;
        // Literal original raw-FS source operation order, including its final float commit.
        const double lap=(sf?z.lp+rho*(ai.x*z.lx.x+ai.y*z.lx.y+ai.z*z.lx.z+z.da):z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da);
        const double chain=dk*(z.gradj.x*(z.gp.x+rho*ai.x)+z.gradj.y*(z.gp.y+rho*ai.y)+z.gradj.z*(z.gp.z+rho*ai.z));const double literal=kw/n*(-PoroThetac[i]+k/gamma*lap+chain/gamma);const float commit=float(literal),actual=PorePressRatec[i];
        const double ferr=fabs(double(actual)-literal),fbudget=FLT_EPSILON*fabs(literal)+double(std::numeric_limits<float>::denorm_min());Need(Finite(actual)&&Finite(literal)&&Bits(actual,commit)&&ferr<=fbudget,Detail("Original literal/final-float reconciliation failed",a.part,id,actual,literal,fbudget));maxFloatRatio=(std::max)(maxFloatRatio,fbudget?ferr/fbudget:0.);
        std::array<std::array<double,7>,3> pieces{};for(unsigned g=0;g<3;g++){const auto& t=r[g];auto& q=pieces[g];q[0]=g?0:-B*PoroThetac[i];q[1]=B*k/gamma*t.lp;q[2]=sf?0:-B*k/gamma*Dot(z.gp,t.lx);q[3]=B*k/gamma*rho*t.da;q[4]=sf?B*k/gamma*rho*Dot(ai,t.lx):0;q[5]=B/gamma*dk*Dot(t.gradj,z.gp);q[6]=B/gamma*dk*rho*Dot(t.gradj,ai);}
        double expanded=0,partition=0;for(unsigned t=0;t<7;t++){expanded+=pieces[0][t];partition+=pieces[1][t]+pieces[2][t];}partition+=pieces[0][0];
        const double magnitude=B*fabs(PoroThetac[i])+B/gamma*(k*(z.lpabs+(sf?0:Dot(z.gpabs,z.lxabs))+rho*(z.daabs+(sf?Dot(Abs(ai),z.lxabs):0)))+dk*Dot(z.jabs,z.gpabs+Abs(ai)*rho));const double dbudget=2*Gamma(64*(z.count+1))*magnitude,ebudget=fbudget+dbudget,eerror=fabs(expanded-double(actual));
        Need(Finite(magnitude)&&Finite(ebudget)&&eerror<=ebudget,Detail("Expanded arithmetic reconciliation failed",a.part,id,actual,expanded,ebudget));Need(fabs(partition-expanded)<=dbudget,Detail("Donor-group arithmetic reconciliation failed",a.part,id,expanded,partition,dbudget));maxExpandedRatio=(std::max)(maxExpandedRatio,ebudget?eerror/ebudget:0.);const double coeff=PorePressc[i]*V*PoroThetac[i]/kw;const auto C=CorrMatc[i];const auto R=Rsigmac[i];const auto normal=FSNormalc[i];Need(Finite(ai)&&Finite(normal),"Nonfinite fresh CPU acceleration/FS normal");for(double v:{C.a11,C.a12,C.a13,C.a21,C.a22,C.a23,C.a31,C.a32,C.a33,double(R.xx),double(R.yy),double(R.zz),double(R.xy),double(R.yz),double(R.xz),PoroThetac[i],weight,coeff})Need(Finite(v),"Nonfinite fresh CPU derivative/storage field");
        soil<<a.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<id<<','<<Posc[i].x<<','<<Posc[i].y<<','<<Posc[i].z<<','<<PorePressc[i]<<','<<PorePress0c[i]<<','<<PoroJc[i]<<','<<n<<','<<V<<','<<k<<','<<weight<<','<<a.theta[s]<<','<<PoroThetac[i]<<','<<a.fs[s]<<','<<FSTypec[i]<<','<<normal.x<<','<<normal.y<<','<<normal.z<<','<<ai.x<<','<<ai.y<<','<<ai.z<<','<<C.a11<<','<<C.a12<<','<<C.a13<<','<<C.a21<<','<<C.a22<<','<<C.a23<<','<<C.a31<<','<<C.a32<<','<<C.a33<<','<<R.xx<<','<<R.yy<<','<<R.zz<<','<<R.xy<<','<<R.yz<<','<<R.xz<<','<<actual<<','<<literal<<','<<ferr<<','<<fbudget<<','<<expanded<<','<<eerror<<','<<ebudget<<','<<coeff<<'\n';soilRows++;
        for(unsigned g=0;g<3;g++){const auto& t=r[g];terms<<a.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<id<<','<<FSTypec[i]<<','<<Groups[g]<<','<<t.count<<','<<t.lp<<','<<t.lx.x<<','<<t.lx.y<<','<<t.lx.z<<','<<t.gp.x<<','<<t.gp.y<<','<<t.gp.z<<','<<t.da<<','<<t.gradj.x<<','<<t.gradj.y<<','<<t.gradj.z;for(double q:pieces[g])terms<<','<<q<<','<<weight*q;terms<<'\n';termRows++;
          for(unsigned region:{0u,sf?2u:1u}){auto& h=sums[g][region];h.count++;h.changed+=FSTypec[i]!=a.fs[s];h.volume+=V;h.weight+=weight;h.storage+=weight*PorePressc[i];if(!g){h.actualQ+=weight*actual;h.actualAbs+=fabs(weight*actual);h.coefficientQ+=coeff;h.error+=weight*eerror;h.budget+=weight*ebudget;}for(unsigned t=0;t<7;t++){h.q[t]+=weight*pieces[g][t];h.absq[t]+=fabs(weight*pieces[g][t]);}}
        }
      }
      for(unsigned g=0;g<3;g++)for(unsigned region=0;region<3;region++){const auto& h=sums[g][region];double q=0,aq=0;for(unsigned t=0;t<7;t++){q+=h.q[t];aq+=h.absq[t];}const double ge=g?0:fabs(h.actualQ-q),gb=g?0:h.budget+Gamma(8*(h.count+1))*(h.actualAbs+aq);Need(g||ge<=gb,"Global source-rate reconciliation failed");summary<<a.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<Groups[g]<<','<<(region==0?"all":region==1?"interior":"FS")<<','<<h.count<<','<<h.changed<<','<<h.volume<<','<<h.weight<<','<<h.storage<<','<<h.actualQ<<','<<h.coefficientQ<<','<<q<<','<<(g?0:h.actualQ+h.coefficientQ)<<','<<h.error<<','<<h.budget<<','<<ge<<','<<gb;for(unsigned t=0;t<7;t++)summary<<','<<h.q[t]<<','<<h.absq[t];summary<<'\n';summaryRows++;}
      Unchanged(a);PosInteraction_Forces();cleanup=false;Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Force scratch cleanup differs");Unchanged(a);Copy(a);Unchanged(a);for(auto f:{&soil,&terms,&summary,&walls}){f->flush();Need(bool(*f),"Complete RHS CSV write failed");}
    }catch(...){if(cleanup)PosInteraction_Forces();throw;}}
    Need(calls==3&&soilRows==15000&&termRows==45000&&summaryRows==27&&wallRows==5415,"Exact three-state coverage differs");std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_storage_rhs_r1\",\"passed\":true,\"source_parts\":[30,60,90],\"source_samples\":91,\"source_release_time_s\":"<<release<<",\"actual_force_calls\":3,\"actual_Darcy_calls\":3,\"soil_rows\":"<<soilRows<<",\"term_rows\":"<<termRows<<",\"summary_rows\":"<<summaryRows<<",\"wall_rows\":"<<wallRows<<",\"literal_final_float_bits_matched\":15000,\"max_final_float_budget_ratio\":"<<maxFloatRatio<<",\"max_expanded_budget_ratio\":"<<maxExpandedRatio<<",\"all5000_primary_bits_unchanged_per_call\":true,\"fresh_actual_CPU_corrector_mode_on_completed_states\":true,\"saved_GPU_force_stage_reconstructed\":false,\"wall_partition_is_additive_not_counterfactual\":true,\"coefficient_change_included\":true,\"original_Single_no_hook\":true,\"physical_steps\":0,\"material_return_calls\":0,\"filter_calls\":0,\"extra_Darcy_calls\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_N255_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_N255_SEED FRESH_OUT");const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as05_n255_r1/c08_h18_as05_n255_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_as05_n255_r1/native_r1"),"Only the sealed original N255 native is admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);for(const char* leaf:{"c08_h18_as05_n255_r1.run.json","c08_h18_as05_n255_r1.call.json","c08_h18_n255_native_run_r1.check.json","c08_h18_n255_review_r1.check.json","c08_h18_storage_rhs_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const std::array<Snapshot,3> states={Snapshot(native,0),Snapshot(native,1),Snapshot(native,2)};AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_storage_rhs_r1")&&!pf::exists(cfg.DirOut),"Original N255 seed and fresh exact CPU diagnostic output required");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),states);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Fresh zero-step storage diagnostic failed; preserve outputs\n";return 2;}}
