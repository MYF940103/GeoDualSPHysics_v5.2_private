// Test-only Darcy denominator A/B, mechanically derived from SpatialWave r2.
// Actual ComputeStep_Sym and all original single-run guards are retained.
// UPL_DARCY_BARE only selects the independent initial Darcy symbol/reference label.
#ifndef UPL_DARCY_BARE
#error Define UPL_DARCY_BARE as 0 or 1 for this isolated helper.
#endif
static_assert(UPL_DARCY_BARE==0 || UPL_DARCY_BARE==1,"Invalid test-only denominator");
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("DarcyEtaWaveCpu","r1","07-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static constexpr unsigned Columns=26;
static constexpr double End=1./32768.,Lx=.125,Lz=.0625,Amplitude=1./512.;
using Row=std::array<double,Columns>;
struct Frame{double time=0;std::vector<Row> rows;};
static void WriteFrame(std::ofstream& file,const Frame& f){file.write(reinterpret_cast<const char*>(&f.time),8);for(const auto& r:f.rows)file.write(reinterpret_cast<const char*>(r.data()),Columns*8);Check(bool(file),"Frame write failed");}
static Frame ReadFrame(std::ifstream& file,unsigned native){Frame f;f.rows.resize(native);file.read(reinterpret_cast<char*>(&f.time),8);for(auto& r:f.rows)file.read(reinterpret_cast<char*>(r.data()),Columns*8);Check(bool(file),"Truncated frame");return f;}
class SpatialWave:public JSphCpuSingle{
  unsigned Nx,Native;
  std::vector<tdouble3> Initial;
  double InitialEnergy=0,MaxCfl=0,MaxDiffusion=0,MaxEnergy=0,MinBound=DBL_MAX,MinMargin=DBL_MAX;
  double MaxModeP=0,MaxModeV=0,MaxModeU=0,MaxContP=0,MaxContV=0,MaxContU=0;
  using Linear=std::array<double,4>;
  struct LinearOperator{double kr,ks,ksig,ka,ell;};
  LinearOperator Discrete{},Continuum{};
  Linear DiscreteRef{0,Amplitude,0,0},FineRef=DiscreteRef,ContinuumRef=DiscreteRef;
  double RefTime=0,Cu0=0;
  std::ofstream Policy;
  static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
  tdouble3 Delta(unsigned p,unsigned q)const{auto d=Posc[p]-Posc[q];d.y=0;d.x-=Lx*std::round(d.x/Lx);d.z-=Lz*std::round(d.z/Lz);return d;}
  std::vector<unsigned> Indices()const{
    std::vector<unsigned> ids(Native,~0u);unsigned count=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Check(CODE_IsFluid(Codec[p])&&Idpc[p]<Native&&ids[Idpc[p]]==~0u,"Native identity/duplicate changed");ids[Idpc[p]]=p;count++;
    }
    Check(count==Native&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native count/exclusion changed");return ids;
  }
  void InitReference(){
    const double k=2*acos(-1.)/Lx,V0=double(MassFluid)/RhopZero;
    double mxx=0,mxz=0,mzz=0,kr=0,kd=0,rawz=0,ell=0;unsigned neighbors=0;
    const auto ids=Indices();const unsigned p=ids[0];
    for(unsigned q:ids)if(q!=p){
      const auto d=Delta(p,q);const double r2=Dot(d,d);if(r2>double(KernelSize2)||r2<ALMOSTZERO)continue;
      const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(r2));const auto g=d*fac;
      mxx-=V0*d.x*g.x;mxz-=V0*d.x*g.z;mzz-=V0*d.z*g.z;
      kd-=V0*sin(k*d.x)*g.x;rawz-=V0*sin(k*d.x)*g.z;
      const float dx=float(d.x),dz=float(d.z),rf=dx*dx+dz*dz;
      const float ff=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,rf);
      kr-=V0*sin(k*d.x)*double(ff*dx);
      neighbors++;
    }
    const double det=mxx*mzz-mxz*mxz;Check(neighbors==36&&det>0,"Initial actual support/moment invalid");
    const double cxx=mzz/det,cxz=-mxz/det,czz=mxx/det;
    for(unsigned q:ids)if(q!=p){
      const auto d=Delta(p,q);const double r2=Dot(d,d);if(r2>double(KernelSize2)||r2<ALMOSTZERO)continue;
      const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(r2));const auto g=d*fac;
      const auto cg=TDouble3(cxx*g.x+cxz*g.z,0,cxz*g.x+czz*g.z);
      const double beta=Dot(d,cg)/(r2+(UPL_DARCY_BARE? 0.: double(Eta2)));
      ell-=2*V0*beta*(1-cos(k*d.x));
    }
    const double ks=cxx*kd+cxz*rawz;
    Discrete={kr,ks,cxx*kr,ks,ell};Continuum={k,k,k,k,k*k};
    Cu0=sqrt((double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3+double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity)/RhopZero);
  }
  Linear Derivative(const Linear& x,const LinearOperator& op)const{
    const double B=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity,M=double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3;
    const double D=B*double(SoilCte.HydraulicConductivity)/(double(SoilCte.PoreWaterRho)*9.80665);
    const double a=op.kr*(x[3]-x[2])/RhopZero;
    return {x[1],a,M*op.ksig*x[1],-B*op.ks*x[1]-D*op.ell*x[3]+D*SoilCte.PoreWaterRho*op.ka*a};
  }
  Linear Advance(Linear x,const LinearOperator& op,double interval,unsigned parts)const{
    const double h=interval/parts;
    for(unsigned it=0;it<parts;it++){
      const auto a=Derivative(x,op);auto y=x;for(unsigned j=0;j<4;j++)y[j]+=h*.5*a[j];const auto b=Derivative(y,op);
      y=x;for(unsigned j=0;j<4;j++)y[j]+=h*.5*b[j];const auto d=Derivative(y,op);
      y=x;for(unsigned j=0;j<4;j++)y[j]+=h*d[j];const auto e=Derivative(y,op);
      for(unsigned j=0;j<4;j++)x[j]+=h*(a[j]+2*b[j]+2*d[j]+e[j])/6;
    }return x;
  }
  double Energy()const{
    double energy=0;
    for(unsigned p:Indices()){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto s=Sigmac[p];const auto v=Velrhopc[p];
      const double tr=s.xx+s.yy+s.zz,mean=tr/3.;
      const double dev=(s.xx-mean)*(s.xx-mean)+(s.yy-mean)*(s.yy-mean)+(s.zz-mean)*(s.zz-mean)+2*(s.xy*s.xy+s.xz*s.xz+s.yz*s.yz);
      energy+=V*(.5*rho*(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z)+dev/(4*SoilCte.ModulusG)+tr*tr/(18*SoilCte.ModulusK)+n*double(PorePressc[p])*PorePressc[p]/(2*SoilCte.PoreWaterBulkModulus));
    }
    return energy;
  }

  void StateGuard(double dt,bool forceStatsAvailable=true){
    const auto ids=Indices();const double kw=SoilCte.PoreWaterBulkModulus,n0=SoilCte.Porosity,rhow=SoilCte.PoreWaterRho;
    const double M=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;double cu2max=0,dmax=0,marginmin=DBL_MAX;
    for(unsigned p:ids){
      const double j=PoroJc[p],n=1.-(1.-n0)/j,V=double(MassFluid)/RhopZero*j,rho=rhow+(double(RhopZero)-rhow)/j;
      Check(std::isfinite(j)&&j>1-n0&&fabs(j-1)<=1e-4&&n>0&&n<1&&V>0&&rho>0,"Invalid physical ledger");
      Check(fabs((1-n)*j-(1-n0))<=5e-13,"Solid volume identity failed");
      Check(Kplasticc[p]==0&&PorePress0c[p]==0&&Velrhopc[p].w>=RhopOutMin&&Velrhopc[p].w<=RhopOutMax,"Elastic/reference/passive-rho guard failed");
      const auto s=Sigmac[p];const auto v=Velrhopc[p];for(double z:{n,V,rho,s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(v.x),double(v.y),double(v.z),double(v.w),double(PorePressc[p]),double(PorePressRatec[p]),PoroThetac[p],Posc[p].x,Posc[p].y,Posc[p].z})Check(std::isfinite(z),"Nonfinite actual field");
      const double B=kw/n,cu2=(M+B)/rho,D=B*double(SoilCte.HydraulicConductivity)/(rhow*9.80665),margin=rho*B/(M+B)-rhow;
      Check(margin>64*DBL_EPSILON*(std::max)(rho,rhow),"Outside strict positive-k continuous decay domain");
      cu2max=(std::max)(cu2max,cu2);dmax=(std::max)(dmax,D);marginmin=(std::min)(marginmin,margin);
      const double cfl=sqrt(cu2)*dt/KernelH,diff=D*dt/(double(KernelH)*KernelH);
      MaxCfl=(std::max)(MaxCfl,cfl);MaxDiffusion=(std::max)(MaxDiffusion,diff);
      Check(cfl<=.01&&diff<=.01&&dt<=double(PoreDtSafety)*KernelH*KernelH/D,"Original coupled CFL/diffusion stage-window limits failed");
    }
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      Check(Idpc[p]<Native,"Periodic ID invalid");const unsigned q=ids[Idpc[p]];
      Check(PoroJc[p]==PoroJc[q]&&PoroThetac[p]==PoroThetac[q]&&PorePressc[p]==PorePressc[q]&&PorePress0c[p]==PorePress0c[q]&&PorePressRatec[p]==PorePressRatec[q],"Endpoint periodic scalar ownership failed");
      Check(!memcmp(Velrhopc+p,Velrhopc+q,sizeof(tfloat4))&&!memcmp(Sigmac+p,Sigmac+q,sizeof(tsymatrix3d)),"Endpoint periodic velocity/stress ownership failed");
    }
    const double energy=Energy()/InitialEnergy;MaxEnergy=(std::max)(MaxEnergy,energy);Check(std::isfinite(energy)&&energy<=1.1,"Energy exceeds original1.1 budget");
    // Force statistics do not exist before the first actual force call.
    if(forceStatsAvailable){
      double wave,pore;GetDynamicStepScalesCpu(wave,pore);
      const double wr=double(KernelH)/((std::max)(sqrt(cu2max),VelMax*10.)+double(KernelH)*ViscDtMax),pr=double(PoreDtSafety)*double(KernelH)*KernelH/dmax;
      Check(wave==wr&&pore==pr,"Read-only endpoint time-scale reference failed");
      const double force=AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,bound=(std::min)(double(CFLnumber)*(std::min)(force,wave),pore);
      Check(dt<=bound&&double(DtMin)<=bound,"Endpoint necessary step bound failed");MinBound=(std::min)(MinBound,bound);MinMargin=(std::min)(MinMargin,marginmin);
      const double legacy=double(CFLnumber)*(std::min)(force,double(KernelH)/((std::max)(Cs0,VelMax*10.)+double(KernelH)*ViscDtMax));Check(dt<=legacy,"Original drained natural-step screen failed");
      Policy<<Nstep<<','<<TimeStep<<','<<dt<<','<<wave<<','<<pore<<','<<bound<<','<<marginmin<<','<<energy<<','<<FixedDt->GetDtError(false)<<'\n';
    }
  }
  Frame Snapshot()const{
    Frame f;f.time=TimeStep;f.rows.resize(Native);const auto ids=Indices();
    for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p];const auto load=HydroMechLoadAcec[p];
      f.rows[id]={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(PorePressc[p]),double(PorePress0c[p]),PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Kplasticc[p]),double(FSTypec[p]),double(n.x),double(n.y),double(n.z),double(PosDivc[p]),double(load.x),double(load.y),double(load.z),double(v.w)};
      for(double q:f.rows[id])Check(std::isfinite(q),"Nonfinite serialized state");
    }return f;
  }
  void Modes(std::ofstream& out){
    const double interval=TimeStep-RefTime,k=2*acos(-1.)/Lx,B=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity,Pstar=B*Amplitude/Cu0,Ustar=Amplitude/(Cu0*k);
    if(interval){DiscreteRef=Advance(DiscreteRef,Discrete,interval,16);FineRef=Advance(FineRef,Discrete,interval,32);ContinuumRef=Advance(ContinuumRef,Continuum,interval,16);RefTime=TimeStep;}
    Check(fabs(DiscreteRef[3]-FineRef[3])<=1e-8,"Coupled RK4 reference self-check failed");
    double vs=0,pc=0,us=0,sc=0,ep=0,ev=0,eu=0,cp=0,cv=0,cu=0;
    const auto ids=Indices();for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const double phase=k*Initial[id].x,sn=sin(phase),cs=cos(phase),ux=Posc[p].x-Initial[id].x,uy=Posc[p].y-Initial[id].y,uz=Posc[p].z-Initial[id].z;
      vs+=2.*Velrhopc[p].x*sn/Native;pc+=2.*PorePressc[p]*cs/Native;us+=2.*ux*sn/Native;sc+=2.*Sigmac[p].xx*cs/Native;
      ep+=pow(PorePressc[p]-DiscreteRef[3]*cs,2);ev+=pow(Velrhopc[p].x-DiscreteRef[1]*sn,2)+pow(Velrhopc[p].y,2)+pow(Velrhopc[p].z,2);eu+=pow(ux-DiscreteRef[0]*sn,2)+uy*uy+uz*uz;
      cp+=pow(PorePressc[p]-ContinuumRef[3]*cs,2);cv+=pow(Velrhopc[p].x-ContinuumRef[1]*sn,2)+pow(Velrhopc[p].y,2)+pow(Velrhopc[p].z,2);cu+=pow(ux-ContinuumRef[0]*sn,2)+uy*uy+uz*uz;
    }
    ep=sqrt(ep/Native);ev=sqrt(ev/Native)/Amplitude;eu=sqrt(eu/Native)/Ustar;cp=sqrt(cp/Native)/Pstar;cv=sqrt(cv/Native)/Amplitude;cu=sqrt(cu/Native)/Ustar;
    MaxModeP=(std::max)(MaxModeP,ep);MaxModeV=(std::max)(MaxModeV,ev);MaxModeU=(std::max)(MaxModeU,eu);MaxContP=(std::max)(MaxContP,cp);MaxContV=(std::max)(MaxContV,cv);MaxContU=(std::max)(MaxContU,cu);
    Check(ep<=1&&ev<=1e-3&&eu<=1e-3,"Original frozen discrete reference limits failed");
    out<<Nstep<<','<<TimeStep<<','<<Cu0<<','<<vs<<','<<DiscreteRef[1]<<','<<ContinuumRef[1]<<','<<pc<<','<<DiscreteRef[3]<<','<<ContinuumRef[3]<<','<<us<<','<<DiscreteRef[0]<<','<<ContinuumRef[0]<<','<<sc<<','<<DiscreteRef[2]<<','<<ContinuumRef[2]<<','<<ep<<','<<ev<<','<<eu<<','<<cp<<','<<cv<<','<<cu<<','<<Energy()/InitialEnergy<<'\n';
  }
public:
  explicit SpatialWave(unsigned nx):Nx(nx),Native(nx*nx/2){Check(nx==32,"Only the retained32x16 grid is admitted");Initial.resize(Native);PorosityObserver=true;PorosityFeedback=true;DynamicPorePressure=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,unsigned steps,bool smoke){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!CaseNpb&&CaseNfluid==Native&&PeriX&&PeriZ&&!PeriY,"Wrong new periodic geometry");
    Check(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput,"Auxiliary path not admitted");
    Check(MapRealSize.x==Lx&&MapRealSize.z==Lz&&Dp==Lx/Nx&&TimeStep==0&&FixedDt,"Wrong domain/spacing/clock");
    Check(SoilCte.ModulusK==89478488.f&&SoilCte.ModulusG==134217728.f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.PoreWaterBulkModulus==67108864.f&&SoilCte.Porosity==.25f&&RhopZero==2048&&MassFluid/RhopZero==Dp*Dp&&KernelH==float(1.8*Dp),"Changed physical material/volume/smoothing ratio");
    const unsigned base=256*(Nx/16);const double dt=smoke?End/base:End/steps;
    Check(!smoke&&Nx==32&&steps==512&&SymplecticDtPre==dt,"Only the declared512-step coarse window is admitted; no half or smoke chain");
    const unsigned samples=smoke?3:257,stride=smoke?1:steps/256;const double stop=steps*dt;
    auto ids=Indices();std::vector<bool> lattice(Native,false);
    for(unsigned id=0;id<Native;id++){
      const auto x=Posc[ids[id]];const double ix=x.x/Dp-.5,iz=x.z/Dp-.5;
      Check(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<Nx&&iz>=0&&iz<Nx/2&&x.y==0,"Non-cell-centred initial lattice");
      const unsigned key=unsigned(ix)+Nx*unsigned(iz);Check(!lattice[key],"Duplicate initial material coordinate");lattice[key]=true;Initial[id]=x;
    }
    for(unsigned p=0;p<Np;p++){Velrhopc[p].x=float(Amplitude*sin(2*acos(-1.)*Initial[Idpc[p]].x/Lx));Velrhopc[p].y=Velrhopc[p].z=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PorePressc[p]=PorePress0c[p]=0;PoroJc[p]=1;PoroThetac[p]=0;}
    InitReference();InitialEnergy=Energy();Check(InitialEnergy>0,"Initial energy is zero");
    Policy.open(fs::path(cfg->DirOut)/"endpoint_policy.csv");Policy<<std::setprecision(17)<<"step,time_s,used_dt_s,wave_scale_s,pore_safety_scale_s,complete_bound_s,min_RH_margin,energy_ratio,cumulative_fixed_error_s\n";
    std::ofstream binary(fs::path(cfg->DirOut)/"physical.bin",std::ios::binary),mode(fs::path(cfg->DirOut)/"modes.csv");const unsigned header[3]={Native,Columns,samples};binary.write(reinterpret_cast<const char*>(header),sizeof(header));
    mode<<std::setprecision(17)<<"step,time_s,cu_actual,v_sine,v_discrete,v_continuum,p_cosine,p_discrete,p_continuum,u_sine,u_discrete,u_continuum,sigma_cosine,sigma_discrete,sigma_continuum,p_discrete_RMS_Pa,v_discrete_RMS_over_A,u_discrete_RMS_over_Ustar,p_continuum_RMS_over_Pstar,v_continuum_RMS_over_A,u_continuum_RMS_over_Ustar,energy_ratio\n";
    StateGuard(dt,false);WriteFrame(binary,Snapshot());Modes(mode);unsigned saved=1;
    for(unsigned it=0;it<steps;it++){
      InterStep=INTERSTEP_SymPredictor;const double used=ComputeStep_Sym();Check(used==dt,"Actual locked step changed");
      RunCellDivide(true);TimeStep+=used;LastDt=used;UpdateMaxValues();Nstep++;StateGuard(dt);
      if((it+1)%stride==0){WriteFrame(binary,Snapshot());Modes(mode);saved++;}
    }
    Check(TimeStep==stop&&Nstep==steps&&saved==samples&&!PoroJPrec,"Incomplete actual trajectory");binary.flush();mode.flush();Policy.flush();Check(bool(binary)&&bool(mode)&&bool(Policy),"Output write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"darcy_bare\":"<<(UPL_DARCY_BARE?"true":"false")<<",\"global_eta2\":"<<Eta2<<",\"darcy_eta2\":"<<(UPL_DARCY_BARE?0.:double(Eta2))<<",\"actual_ComputeStep_Sym\":true,\"Nx\":"<<Nx<<",\"native_ids\":"<<Native<<",\"samples\":"<<samples<<",\"steps\":"<<steps<<",\"actual_end_s\":"<<TimeStep<<",\"smoke\":"<<(smoke?"true":"false")<<",\"cu\":"<<Cu0<<",\"Pstar\":"<<double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity*Amplitude/Cu0<<",\"Ustar\":"<<Amplitude/(Cu0*2*acos(-1.)/Lx)<<",\"max_energy_ratio\":"<<MaxEnergy<<",\"max_coupled_CFL\":"<<MaxCfl<<",\"max_Ddt_h2\":"<<MaxDiffusion<<",\"min_endpoint_bound_s\":"<<MinBound<<",\"min_RH_margin\":"<<MinMargin<<",\"max_discrete_pressure_RMS_Pa\":"<<MaxModeP<<",\"max_discrete_v_RMS_normalized\":"<<MaxModeV<<",\"max_discrete_u_RMS_normalized\":"<<MaxModeU<<",\"max_continuum_p_RMS_normalized\":"<<MaxContP<<",\"max_continuum_v_RMS_normalized\":"<<MaxContV<<",\"max_continuum_u_RMS_normalized\":"<<MaxContU<<",\"discrete_Kr\":"<<Discrete.kr<<",\"discrete_Ks\":"<<Discrete.ks<<",\"discrete_Ksig\":"<<Discrete.ksig<<",\"discrete_ell\":"<<Discrete.ell<<",\"physical_acceptance\":false}\n";done.flush();Check(bool(done),"Completion write failed");
  }
};
// Actual compiled kernel factors at the existing positive-distance support guard.
// No Fac call is made for a pair the production rr2<ALMOSTZERO guard excludes.
static void Limits(const fs::path& target){
  Check(!fs::exists(target),"Retained limits output protected");fs::create_directory(target);
  const float h=float(1.8*(.125/32));StCteSph csp{};csp.kernelh=h;
  csp.kcubic=fsph::GetKernelCubic_Ctes(true,h);csp.kwend=fsph::GetKernelWendland_Ctes(true,h);
  const double guard=ALMOSTZERO,hh=double(h)*h;
  const std::array<double,8> rr={0.,std::nextafter(guard,0.),guard,std::nextafter(guard,DBL_MAX),hh*1e-12,hh*.01,hh,4*hh};
  std::ofstream rows(target/"kernel_limits.csv");rows<<std::setprecision(17)<<"kernel,rr2,production_pair_admitted,fac,radial_dot_gradient_over_rr2\n";
  unsigned accepted=0,skipped=0;
  for(unsigned kernel=0;kernel<2;kernel++)for(double r2:rr){
    if(r2<guard){rows<<(kernel?"Wendland":"Cubic")<<','<<r2<<",false,,\n";skipped++;continue;}
    const double fac=kernel?fsph::GetKernel_Fac<KERNEL_Wendland>(csp,float(r2)):fsph::GetKernel_Fac<KERNEL_Cubic>(csp,float(r2));
    const double d=std::sqrt(r2),g=d*fac,weight=d*g/r2;
    Check(std::isfinite(fac)&&std::isfinite(weight),"Actual positive-distance kernel/zero-Eta weight is not finite");
    rows<<(kernel?"Wendland":"Cubic")<<','<<r2<<",true,"<<fac<<','<<weight<<'\n';accepted++;
  }
  rows.flush();Check(bool(rows),"Limits CSV write failed");
  std::ofstream done(target/"completion.json");done<<"{\"passed\":true,\"actual_kernel_calls\":"<<accepted<<",\"guard_excluded_pairs\":"<<skipped<<",\"zero_distance_kernel_called\":false,\"solver_started\":false,\"physical_acceptance\":false}\n";
  done.flush();Check(bool(done),"Limits completion write failed");
}
int main(int argc,char** argv){try{
  if(argc==3&&std::string(argv[1])=="--limits"){Limits(argv[2]);return 0;}
  Check(argc>8&&std::string(argv[1])=="--job","Use --job 32 512 0 solverargs or --limits FRESH_OUTPUT");const unsigned nx=unsigned(std::stoul(argv[2])),steps=unsigned(std::stoul(argv[3]));const bool smoke=std::string(argv[4])=="1";Check(smoke||std::string(argv[4])=="0","Bad smoke flag");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> arguments{argv[0]};for(int i=5;i<argc;i++)arguments.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(arguments.size()),arguments.data());cfg.Cpu=true;Check(!fs::exists(cfg.DirOut),"Retained output protected");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");SpatialWave wave(nx);wave.Execute(&cfg,AppInfo.LogPtr(),steps,smoke);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Spatial wave rejected; preserve output\n";return 2;}}



