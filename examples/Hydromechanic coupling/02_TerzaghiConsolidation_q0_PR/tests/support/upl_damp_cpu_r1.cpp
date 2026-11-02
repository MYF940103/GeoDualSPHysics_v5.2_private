// Frozen-stage damping components only: no Run, ComputeStep, integration or saved-data decoder.
#ifdef UPL_DAMP_GPU
#define main RetainedDampingNeutralMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main
#include "JSphGpu_ker.h"
#include "JDsTimersGpu.h"
#include <cuda_runtime_api.h>
#include <vector_functions.h>
#else
#define main RetainedDampingNeutralMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JDsTimersCpu.h"
#endif
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JException.h"
#include "FunSphKernel.h"
#include <array>
#include <cfloat>
#include <climits>
#include <limits>
namespace damp {
constexpr unsigned Soil=1000,Fixed=40,Total=1040;
constexpr float Eta=.02f;
constexpr double At=.005;
constexpr double Event=5243./524288.;
#ifdef UPL_DAMP_GPU
using Base=JSphGpuSingle;using V3=float3;using V4=float4;
static const char* Backend="GPU";
static const char* CteUpdates="true";
static void Cu(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T>static std::vector<T> Read(const T* p,unsigned n){if(!p)throw std::runtime_error("Required GPU array missing");std::vector<T> v(n);if(n)Cu(cudaMemcpy(v.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return v;}
template<class T>static void Write(T* p,const std::vector<T>& v){if(!p)throw std::runtime_error("Required GPU upload missing");if(!v.empty())Cu(cudaMemcpy(p,v.data(),v.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T>struct Device{T* p=nullptr;explicit Device(unsigned n){Cu(cudaMalloc(reinterpret_cast<void**>(&p),n*sizeof(T)));}~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;};
#else
using Base=JSphCpuSingle;using V3=tfloat3;using V4=tfloat4;
static const char* Backend="CPU";
static const char* CteUpdates="false";
template<class T>static std::vector<T> Read(const T* p,unsigned n){if(!p)throw std::runtime_error("Required CPU array missing");return std::vector<T>(p,p+n);}
template<class T>static void Write(T* p,const std::vector<T>& v){if(!p)throw std::runtime_error("Required CPU upload missing");if(!v.empty())std::memcpy(p,v.data(),v.size()*sizeof(T));}
#endif
static void Want(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!std::memcmp(a.data(),b.data(),a.size()*sizeof(T)));}
static tdouble3 Vec(V3 a){return TDouble3(a.x,a.y,a.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Abs(tdouble3 a){return TDouble3(std::fabs(a.x),std::fabs(a.y),std::fabs(a.z));}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
static double ForceBudget(double raw,double target){return 64.*FLT_EPSILON*raw+256.*DBL_EPSILON*(std::max)(1.,std::fabs(target))+1e-6;}
struct Snapshot{
  struct Block{void* p;std::vector<byte> bytes;};std::vector<Block> blocks;double cache=0;
  template<class T>void Add(T* p,unsigned n){if(!p)return;Block b{p,std::vector<byte>(n*sizeof(T))};
#ifdef UPL_DAMP_GPU
    Cu(cudaMemcpy(b.bytes.data(),p,b.bytes.size(),cudaMemcpyDeviceToHost));
#else
    std::memcpy(b.bytes.data(),p,b.bytes.size());
#endif
    blocks.push_back(std::move(b));}
  void Restore()const{for(const auto& b:blocks){
#ifdef UPL_DAMP_GPU
    Cu(cudaMemcpy(b.p,b.bytes.data(),b.bytes.size(),cudaMemcpyHostToDevice));
#else
    std::memcpy(b.p,b.bytes.data(),b.bytes.size());
#endif
  }}
  bool Exact()const{for(const auto& b:blocks){std::vector<byte> v(b.bytes.size());
#ifdef UPL_DAMP_GPU
    Cu(cudaMemcpy(v.data(),b.p,v.size(),cudaMemcpyDeviceToHost));
#else
    std::memcpy(v.data(),b.p,v.size());
#endif
    if(v!=b.bytes)return false;}return true;}
};
struct State{std::vector<unsigned> id,cell,fs;std::vector<typecode> code;std::vector<tdouble3> x;std::vector<V4> vel;std::vector<V3> normal,ace,load;std::vector<tsymatrix3d> sigma;std::vector<tmatrix3d> c;std::vector<double> j,theta;std::vector<float> p,p0,rate,plastic,raw;};
struct Reference{double value,raw,budget,da,normalTarget;tdouble3 gp,gc,lx;};
struct Totals{unsigned forces=0,rates=0,rateRows=0,directRows=0,owners=0,restores=0,changed=0;double maxRate=0,maxDelta=0,maxLoad=0,power=0,cd=0,rhos=0;};
class Component:public Base{
  double Locked=0,Last=0,Error0=0;
  State Capture(bool live)const{State a;
#ifdef UPL_DAMP_GPU
    a.id=Read(Idpg,Np);a.cell=Read(Dcellg,Np);a.code=Read(Codeg,Np);const auto xy=Read(Posxyg,Np);const auto z=Read(Poszg,Np);for(unsigned q=0;q<Np;q++)a.x.push_back(TDouble3(xy[q].x,xy[q].y,z[q]));a.vel=Read(Velrhopg,Np);a.sigma=Read(Sigmag,Np);a.plastic=Read(Kplasticg,Np);a.p=Read(PorePressg,Np);a.p0=Read(PorePress0g,Np);a.rate=Read(PorePressRateg,Np);a.j=Read(PoroJg,Np);a.theta=Read(PoroThetag,Np);a.c=Read(CorrMatg,Np);a.fs=Read(FSTypeg,Np);a.normal=Read(FSNormalg,Np);a.load=Read(HydroMechLoadAceg,Np);if(live){a.ace=Read(Aceg,Np);a.raw=Read(HydroMechTopLoadRawg,Np);}
#else
    a.id=Read(Idpc,Np);a.cell=Read(Dcellc,Np);a.code=Read(Codec,Np);a.x=Read(Posc,Np);a.vel=Read(Velrhopc,Np);a.sigma=Read(Sigmac,Np);a.plastic=Read(Kplasticc,Np);a.p=Read(PorePressc,Np);a.p0=Read(PorePress0c,Np);a.rate=Read(PorePressRatec,Np);a.j=Read(PoroJc,Np);a.theta=Read(PoroThetac,Np);a.c=Read(CorrMatc,Np);a.fs=Read(FSTypec,Np);a.normal=Read(FSNormalc,Np);a.load=Read(HydroMechLoadAcec,Np);if(live){a.ace=Read(Acec,Np);a.raw=Read(HydroMechTopLoadRawc,Np);}
#endif
    return a;
  }
  std::vector<unsigned> Owners(const State& a)const{std::vector<unsigned> map(Total,UINT_MAX);unsigned soil=0,fixed=0;for(unsigned q=0;q<Np;q++){Want(a.id[q]<Total&&(CODE_IsNormal(a.code[q])||CODE_IsPeriodic(a.code[q])),"Unknown/excluded slot");if(CODE_IsNormal(a.code[q])){Want(map[a.id[q]]==UINT_MAX,"Duplicate native owner");map[a.id[q]]=q;if(a.id[q]<Fixed){Want(CODE_IsFixed(a.code[q]),"Wrong fixed type");fixed++;}else{Want(CODE_IsFluid(a.code[q]),"Wrong soil type");soil++;}}}Want(soil==Soil&&fixed==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Original1040 native scope required");return map;}
  std::vector<byte> Physical(const State& a)const{const auto map=Owners(a);std::vector<byte> b;auto put=[&](const auto& value){const auto p=reinterpret_cast<const byte*>(&value);b.insert(b.end(),p,p+sizeof(value));};for(unsigned id=Fixed;id<Total;id++){unsigned q=map[id];put(a.id[q]);put(a.cell[q]);put(a.code[q]);put(a.x[q]);put(a.vel[q]);put(a.sigma[q]);put(a.plastic[q]);put(a.p[q]);put(a.p0[q]);put(a.j[q]);}return b;}
  void Clock(double time=0)const{Want(TimeStep==time&&!Nstep&&SymplecticDtPre==Locked&&LastDt==Last&&FixedDt->GetDtError(false)==Error0,"Component advanced clock/step/error");
#ifdef UPL_DAMP_GPU
    Want(!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg,"GPU predictor history unexpectedly live");
#else
    Want(!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"CPU predictor history unexpectedly live");
#endif
  }
  Snapshot Save()const{Snapshot s;s.cache=DynamicConductivitySpeedMax;
#ifdef UPL_DAMP_GPU
    s.Add(Idpg,Np);s.Add(Codeg,Np);s.Add(Dcellg,Np);s.Add(Posxyg,Np);s.Add(Poszg,Np);s.Add(Velrhopg,Np);s.Add(Sigmag,Np);s.Add(Kplasticg,Np);s.Add(PorePressg,Np);s.Add(PorePress0g,Np);s.Add(PorePressRateg,Np);s.Add(PoroJg,Np);s.Add(PoroThetag,Np);s.Add(CorrMatg,Np);s.Add(FSTypeg,Np);s.Add(FSNormalg,Np);s.Add(HydroMechLoadAceg,Np);s.Add(TangenVelg,Np);s.Add(BoundModeg,Np);
#else
    s.Add(Idpc,Np);s.Add(Codec,Np);s.Add(Dcellc,Np);s.Add(Posc,Np);s.Add(Velrhopc,Np);s.Add(Sigmac,Np);s.Add(Kplasticc,Np);s.Add(PorePressc,Np);s.Add(PorePress0c,Np);s.Add(PorePressRatec,Np);s.Add(PoroJc,Np);s.Add(PoroThetac,Np);s.Add(CorrMatc,Np);s.Add(FSTypec,Np);s.Add(FSNormalc,Np);s.Add(HydroMechLoadAcec,Np);s.Add(TangenVelc,Np);s.Add(BoundModec,Np);
#endif
    return s;}
  void Set(bool on,float eta,bool dynamic=true){SoilDamping=on;SoilDampingCoef=eta;DynamicPorePressure=dynamic;
#ifdef UPL_DAMP_GPU
    ConstantDataUp();Cu(cudaDeviceSynchronize());
#endif
  }
  void Restore(const Snapshot& s,Totals& t){TimeStep=0;s.Restore();DynamicConductivitySpeedMax=s.cache;Set(true,Eta);Want(s.Exact(),"Covered persistent scratch did not restore");Clock();t.restores++;}
  void AddActual(){
#ifdef UPL_DAMP_GPU
    cusph::AddSoilDamping(Np,Npb,Codeg,Velrhopg,Aceg,(DynamicPorePressure?GetDynamicSoilDampingRate():0.f));Cu(cudaDeviceSynchronize());
#else
    AddSoilDampingCpu(Np,Npb,Codec,Velrhopc,Acec);
#endif
  }
  void Rate(){
#ifdef UPL_DAMP_GPU
    ComputeDynamicPorePressureRateGpu(PrepareDynamicPorePeriodicGpu());Cu(cudaDeviceSynchronize());
#else
    ComputeDynamicPorePressureRateCpu();
#endif
  }
  void FreeForce(){PosInteraction_Forces();
#ifdef UPL_DAMP_GPU
    Want(!Aceg&&!Arg&&!Rsigmag&&!BoundDerivativeVelg&&!HydroMechTopLoadRawg,"GPU force scratch survived release");
#else
    Want(!Acec&&!Arc&&!Rsigmac&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"CPU force scratch survived release");
#endif
  }
  Reference Ref(const State& a,unsigned i)const{double lp=0,alp=0,da=0,ada=0;tdouble3 gp=TDouble3(0),lx=TDouble3(0),agp=TDouble3(0),alx=TDouble3(0);const double v0=double(MassFluid)/RhopZero,rhow=SoilCte.PoreWaterRho,B=double(SoilCte.PoreWaterBulkModulus)/(1.-(1.-double(SoilCte.Porosity))/a.j[i]),k=SoilCte.HydraulicConductivity,gamma=rhow*9.80665;
    for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(a.code[q])||CODE_IsFixed(a.code[q])){const auto d=a.x[i]-a.x[q];double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=Product(a.c[i],g),gj=Product(a.c[q],g);const double v=v0*a.j[q],dp=double(a.p[i])-a.p[q],w=v*Dot(d,gi+gj)/(rr+double(Eta2));const auto delta=Vec(a.ace[q])-Vec(a.ace[i]);lp+=w*dp;alp+=std::fabs(w*dp);lx=lx+d*w;alx=alx+Abs(d*w);gp=gp-gi*(v*dp);agp=agp+Abs(gi*(v*dp));da+=v*Dot(delta,gi);ada+=v*Dot(Abs(delta),Abs(gi));}
    auto gc=gp,agc=agp;double normalTarget=0;if(a.fs[i]==FST_FreeSurface||a.fs[i]==FST_Isolated){const auto n=Vec(a.normal[i]);const double n2=Dot(n,n);Want(std::isfinite(n2)&&n2>0,"Invalid actual surface normal");const auto acc=Vec(a.ace[i]);double r=Dot(n,gp+acc*rhow)/n2,ar=Dot(Abs(n),agp+Abs(acc)*rhow)/n2;gc=gp-n*r;agc=agp+Abs(n)*ar;normalTarget=Dot(n,gc+acc*rhow)/std::sqrt(n2);Want(std::fabs(normalTarget)<=256.*DBL_EPSILON*(std::max)(1.,Dot(Abs(n),Abs(gc)+Abs(acc)*rhow)/std::sqrt(n2)),"Closed-face target identity failed");}
    const double value=B*(-a.theta[i]+k/gamma*(lp-Dot(gc,lx)+rhow*da)),raw=B*(std::fabs(a.theta[i])+k/gamma*(alp+Dot(agc,alx)+rhow*ada)),budget=64.*FLT_EPSILON*raw+256.*DBL_EPSILON*(std::max)(1.,std::fabs(B*a.theta[i]))+1e-6;Want(std::isfinite(value)&&std::isfinite(raw)&&raw>=0,"Conditional rate reference nonfinite");return{value,raw,budget,da,normalTarget,gp,gc,lx};}
  void CheckRate(const State& a,const char* label,Totals& t,std::ofstream& rows)const{const auto map=Owners(a);unsigned top=0;for(unsigned id=Fixed;id<Total;id++){const unsigned q=map[id];const auto r=Ref(a,q);const double error=std::fabs(double(a.rate[q])-r.value);rows<<label<<','<<id<<','<<a.x[q].z<<','<<a.fs[q]<<','<<a.rate[q]<<','<<r.value<<','<<r.raw<<','<<r.budget<<','<<error/r.budget<<','<<a.theta[q]<<','<<a.ace[q].x<<','<<a.ace[q].z<<','<<r.gp.x<<','<<r.gp.z<<','<<r.gc.x<<','<<r.gc.z<<','<<r.lx.x<<','<<r.lx.z<<','<<r.da<<','<<r.normalTarget<<'\n';t.rateRows++;Want(std::isfinite(a.rate[q])&&error<=r.budget,"Original full-rate raw-term budget failed");t.maxRate=(std::max)(t.maxRate,error/r.budget);top+=unsigned(a.fs[q]==FST_FreeSurface||a.fs[q]==FST_Isolated);}
    Want(top==10,"Actual closed-top mask missing");unsigned ghosts=0;for(unsigned q=Npb;q<Np;q++)if(CODE_IsPeriodic(a.code[q])&&CODE_IsFluid(a.code[q])){const unsigned p=map[a.id[q]];Want(!std::memcmp(&a.j[q],&a.j[p],sizeof(double))&&!std::memcmp(&a.c[q],&a.c[p],sizeof(tmatrix3d))&&!std::memcmp(&a.ace[q],&a.ace[p],sizeof(V3))&&!std::memcmp(&a.theta[q],&a.theta[p],sizeof(double))&&!std::memcmp(&a.rate[q],&a.rate[p],sizeof(float)),"Finished native owner was not copied to periodic slot");ghosts++;}Want(ghosts>0,"Empty actual X-periodic owner proof");t.owners+=ghosts;}
  void Direct(const State& natural,Totals& t,std::ofstream& rows,std::ofstream& summary){const unsigned n=Np+2,cap=n+1;auto code=natural.code;code.resize(cap,CODE_TYPE_FIXED);code[Np]=CODE_SetOutIgnore(CODE_TYPE_FLUID);code[Np+1]=CODE_ToFluidInout(CODE_TYPE_FLUID,0);code[n]=CODE_TYPE_FLUID;std::vector<V3> positive;unsigned eligible=0,periodic=0,excluded=0;
    for(unsigned trial=0;trial<5;trial++){Set(true,trial==3?0.f:Eta,trial!=4);const float cd=(DynamicPorePressure?GetDynamicSoilDampingRate():0.f);const double n0=SoilCte.Porosity,rhos=(double(RhopZero)-n0*SoilCte.PoreWaterRho)/(1.-n0);const float anchor=trial<3?float(double(Eta)*std::sqrt(double(SoilCte.ModulusE)/(rhos*double(KernelH)*double(KernelH)))):0.f;Want(!std::memcmp(&cd,&anchor,4),"Selected actual cd differs from independent intrinsic-density anchor");t.cd=trial<3?cd:t.cd;t.rhos=rhos;
      std::vector<V4> velocity(cap);std::vector<V3> before(cap),expect(cap);eligible=periodic=excluded=0;for(unsigned q=0;q<cap;q++){const bool active=q<n&&q>=Npb&&CODE_IsNormal(code[q])&&CODE_IsFluid(code[q])&&!CODE_IsFluidInout(code[q]);const double z=q<Np?natural.x[q].z:.25;velocity[q]={trial?float((z-.5)/256.):0.f,0.f,trial?float(z/512.):0.f,(trial==2||trial==4)?0.f:RhopZero};before[q]=active?V3{0,0,0}:V3{.125f,-.25f,.5f};expect[q]=before[q];if(active&&trial<3){expect[q].x-=cd*velocity[q].x;expect[q].y-=cd*velocity[q].y;expect[q].z-=cd*velocity[q].z;}eligible+=unsigned(active);periodic+=unsigned(q<n&&CODE_IsPeriodic(code[q])&&CODE_IsFluid(code[q]));excluded+=unsigned(q<n&&CODE_IsOutIgnore(code[q]));}
      auto got=before;
#ifdef UPL_DAMP_GPU
      Device<typecode> dc(cap);Device<V4> dv(cap);Device<V3> da(cap);Write(dc.p,code);Write(dv.p,velocity);Write(da.p,got);cusph::AddSoilDamping(n,Npb,dc.p,dv.p,da.p,cd);Cu(cudaDeviceSynchronize());got=Read(da.p,cap);
#else
      AddSoilDampingCpu(n,Npb,code.data(),velocity.data(),got.data());
#endif
      Want(Same(got,expect)&&eligible==Soil&&periodic>0&&excluded==1,"Actual damping eligibility/no-op/tail/rounding differs");if(trial==1)positive=got;if(trial==2)Want(Same(positive,got),"Dynamic damping changed under legacy-w poison");double power=0;for(unsigned q=0;q<cap;q++){const bool active=q<n&&q>=Npb&&CODE_IsNormal(code[q])&&CODE_IsFluid(code[q])&&!CODE_IsFluidInout(code[q]);if(q<Np&&active){const double mass=double(MassFluid)/RhopZero*(double(RhopZero)-SoilCte.PoreWaterRho+SoilCte.PoreWaterRho*natural.j[q]);power+=mass*(double(velocity[q].x)*(double(got[q].x)-before[q].x)+double(velocity[q].y)*(double(got[q].y)-before[q].y)+double(velocity[q].z)*(double(got[q].z)-before[q].z));}rows<<trial<<','<<q<<','<<unsigned(code[q])<<','<<active<<','<<velocity[q].x<<','<<velocity[q].y<<','<<velocity[q].z<<','<<velocity[q].w<<','<<before[q].x<<','<<before[q].y<<','<<before[q].z<<','<<got[q].x<<','<<got[q].y<<','<<got[q].z<<','<<expect[q].x<<','<<expect[q].y<<','<<expect[q].z<<','<<cd<<','<<rhos<<'\n';t.directRows++;}Want(std::isfinite(power)&&power<=0&&(trial!=1&&trial!=2||power<0),"Actual direct damping injected stage power");summary<<"direct,"<<trial<<','<<cd<<','<<eligible<<','<<power<<",0,0,0,0\n";}
    Want(positive.size()==cap,"Missing positive direct-damping state");Set(true,Eta);
  }
  void AffineVelocity(const State& initial){auto v=initial.vel;for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(initial.code[q])){v[q].x=float((initial.x[q].z-.5)/256.);v[q].y=0;v[q].z=float(initial.x[q].z/512.);}
#ifdef UPL_DAMP_GPU
    Write(Velrhopg,v);
#else
    Write(Velrhopc,v);
#endif
  }
  void LoadAndDelta(const State& b,const State& a,Totals& t,std::ofstream& summary)const{const auto map=Owners(a);double weightedLoad=0,absLoad=0,target=0,power=0,deltaResidual=0,deltaRaw=0,full=0,expectedFull=0,fullRaw=0;unsigned top=0;
    const double q=double(HydroMechTopLoadQ0)*At/HydroMechTopLoadRampTime,provisional=float(q/(double(RhopZero)*double(JSph::Dp))),v0=double(MassFluid)/RhopZero;const float cd=GetDynamicSoilDampingRate();
    for(unsigned id=Fixed;id<Total;id++){unsigned p=map[id];const double mass=v0*(double(RhopZero)-SoilCte.PoreWaterRho+SoilCte.PoreWaterRho*a.j[p]);Want(mass>0&&std::isfinite(mass)&&!std::memcmp(&a.load[p],&b.load[p],sizeof(V3))&&a.raw[p]==b.raw[p],"Damping changed normalized external load");const auto n=Vec(a.normal[p]);if((a.fs[p]==FST_FreeSurface||a.fs[p]==FST_Isolated)&&Dot(n,n)>1e-24&&n.z/std::sqrt(Dot(n,n))>.35){target-=double(MassFluid)*provisional;top++;}
      weightedLoad+=mass*a.load[p].z;absLoad+=std::fabs(mass*a.load[p].z);const auto old=Vec(b.ace[p]),now=Vec(a.ace[p]),v=TDouble3(a.vel[p].x,a.vel[p].y,a.vel[p].z);const auto wanted=old-v*double(cd),error=now-wanted;const double raw=mass*(std::fabs(old.x)+std::fabs(old.y)+std::fabs(old.z)+double(cd)*(std::fabs(v.x)+std::fabs(v.y)+std::fabs(v.z))),budget=ForceBudget(raw,mass*std::sqrt(Dot(wanted,wanted)));const double worst=mass*(std::max)({std::fabs(error.x),std::fabs(error.y),std::fabs(error.z)});Want(worst<=budget,"Finished-Ace damping increment exceeds original force budget");t.maxDelta=(std::max)(t.maxDelta,worst/budget);power+=mass*Dot(v,now-old);deltaResidual+=mass*error.z;deltaRaw+=raw;full+=mass*now.z;expectedFull+=mass*wanted.z;fullRaw+=mass*(std::fabs(now.z)+std::fabs(wanted.z));t.changed+=unsigned(std::memcmp(&a.ace[p],&b.ace[p],sizeof(V3))!=0);}
    const double budget=ForceBudget(absLoad,target),loadRatio=(std::max)(std::fabs(weightedLoad-target),std::fabs(weightedLoad+q*.1))/budget;Want(top==10&&target<0&&loadRatio<=1&&std::fabs(deltaResidual)<=ForceBudget(deltaRaw,0)&&std::fabs(full-expectedFull)<=ForceBudget(fullRaw,expectedFull)&&power<0&&t.changed>0,"Damping/load/power coupling failed");t.maxLoad=(std::max)(t.maxLoad,loadRatio);t.power=power;summary<<"finished,affine,"<<cd<<','<<Soil<<','<<power<<','<<weightedLoad<<','<<target<<','<<loadRatio<<','<<t.maxDelta<<'\n';
  }
public:
  void Init(const JSphCfgRun* cfg,JLog2* log){AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
#ifdef UPL_DAMP_GPU
    SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
#else
    Timersc->Config(false);
#endif
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();
#ifdef UPL_DAMP_GPU
    InitRunGpu();
#else
    InitRunCpu();
#endif
    FreePartsInit();RunCellDivide(true);Want(HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0&&PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&!DynamicPoreConductivity&&SoilDamping&&SoilDampingCoef==Eta,"Require new candidate public constant-k XML with damping1/.02 before Init");
    Want(Simulate2D&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.y==0&&PeriXinc.z==0&&std::fabs(std::fabs(PeriXinc.x)-.1)<=1e-14&&Gravity==TFloat3(0)&&CSP.gravity==Gravity&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip,"Original static column geometry only");
    Want(HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==Event&&HydroMechDrainage&&HydroMechDrainageStartTime==Event&&HydroMechDrainageFixedGrid&&HydroMechInitMode==HMINIT_None&&PoreDtSafety==1,"Prepared dyadic load/drain window required");
    Want(JSph::Dp==.01&&KernelH==float(.018)&&RhopZero==2100.f&&MassFluid==float(.21)&&MassBound==MassFluid&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusE==2e6f,"Original reference material required");
    Want(!SoilHourglassXi&&!Visco&&!Damping&&!RelaxZones&&!Shifting&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR&&!ArtificialStress&&!PoreShepardRegularization&&TDensity==DDT_None&&!StrainSoftening&&PoreCompressionGradCorr&&!PoreCompressionSourceMode&&SoilStressRateGradCorr&&FixedDt,"No other auxiliary physics admitted");Locked=SymplecticDtPre;Last=LastDt;Error0=FixedDt->GetDtError(false);Clock();const auto a=Capture(false);const auto map=Owners(a);for(unsigned id=Fixed;id<Total;id++){unsigned p=map[id];Want(a.j[p]==1&&a.theta[p]==0&&a.p[p]==0&&a.p0[p]==0&&a.plastic[p]==0&&a.vel[p].x==0&&a.vel[p].y==0&&a.vel[p].z==0&&a.vel[p].w==RhopZero,"Original strict-rest input differs");}
  }
  void Execute(Totals& t,std::ofstream& direct,std::ofstream& rates,std::ofstream& summary){Interaction_Forces(INTERSTEP_SymPredictor);t.forces++;const auto natural=Capture(true);CheckRate(natural,"rest",t,rates);for(unsigned p:Owners(natural))if(p!=UINT_MAX&&CODE_IsFluid(natural.code[p]))Want(natural.ace[p].x==0&&natural.ace[p].y==0&&natural.ace[p].z==0&&natural.theta[p]==0&&natural.rate[p]==0,"Actual natural rest not strict0");const auto initial=Save();FreeForce();Clock();Direct(natural,t,direct,summary);
    State baseline;try{
      Restore(initial,t);AffineVelocity(natural);Set(false,Eta);TimeStep=At;const auto before=Physical(Capture(false));Interaction_Forces(INTERSTEP_SymPredictor);t.forces++;baseline=Capture(true);Want(Physical(baseline)==before,"Baseline force changed covered native inputs");CheckRate(baseline,"affine_no_damping",t,rates);Clock(At);
      Set(true,Eta);AddActual();const auto preOwner=Capture(true);unsigned stale=0;for(unsigned p=0;p<Np;p++)if(!CODE_IsNormal(preOwner.code[p])||!CODE_IsFluid(preOwner.code[p])){Want(!std::memcmp(&preOwner.ace[p],&baseline.ace[p],sizeof(V3)),"Damping touched fixed/periodic slot before owner copy");stale+=unsigned(CODE_IsPeriodic(preOwner.code[p])&&CODE_IsFluid(preOwner.code[p]));}Want(stale>0,"No stale periodic slots to refresh");Rate();t.rates++;const auto staged=Capture(true);Want(Physical(staged)==before,"Damping/rate changed native physical inputs");CheckRate(staged,"affine_damp_then_owner_rate",t,rates);Clock(At);FreeForce();
      Restore(initial,t);AffineVelocity(natural);Set(true,Eta);TimeStep=At;const auto physical=Physical(Capture(false));Interaction_Forces(INTERSTEP_SymPredictor);t.forces++;const auto actual=Capture(true);Want(Physical(actual)==physical,"Actual damped force changed covered native inputs");CheckRate(actual,"affine_actual_finished",t,rates);LoadAndDelta(baseline,actual,t,summary);Clock(At);FreeForce();Restore(initial,t);Want(initial.Exact(),"Final named persistent state rollback differs");
    }catch(...){TimeStep=0;
#ifdef UPL_DAMP_GPU
      if(Aceg)FreeForce();
#else
      if(Acec)FreeForce();
#endif
      Restore(initial,t);throw;}
    Want(t.forces==3&&t.rates==1&&t.rateRows==4000&&t.directRows==5*(Np+3)&&t.owners>0&&t.changed>0,"Declared bounded component coverage differs");Clock();
  }
};
}
int main(int argc,char** argv){try{
  damp::Want(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input NEW_DAMPING_CANDIDATE_PUBLIC_XML --out FRESH_DIR");const fs::path xml=argv[2],out=argv[4];auto prefix=xml;prefix.replace_extension();damp::Want(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&fs::is_regular_file(prefix.string()+"_Normals.nbi4")&&!fs::exists(out),"Candidate XML/unchanged seed/Normals and fresh output required");AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],
#ifdef UPL_DAMP_GPU
    "-gpu:0",
#else
    "-cpu","-ompthreads:1",
#endif
    "-stable","-mdbc_freeslip",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> a;for(auto& s:args)a.push_back(s.data());JSphCfgRun cfg;cfg.LoadArgv(int(a.size()),a.data());damp::Want(cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No Run/restart/clock overrides");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");std::ofstream direct(out/"damping.csv"),rates(out/"rates.csv"),summary(out/"summary.csv");for(auto* s:{&direct,&rates,&summary})*s<<std::setprecision(17);
  direct<<"case,slot,code,normal_fluid_eligible,vx,vy,vz,legacy_w,before_ax,before_ay,before_az,actual_ax,actual_ay,actual_az,expected_ax,expected_ay,expected_az,selected_cd_s_inv,reference_intrinsic_rhos\n";rates<<"case,id,z,FSType,actual_rate,conditional_reference,raw_abs_rate,original_budget,error_ratio,theta,Ace_x,Ace_z,Gp_x,Gp_z,gpcorr_x,gpcorr_z,Lx_x,Lx_z,DA,constructed_normal_target\n";summary<<"kind,case,selected_cd_s_inv,native_rows,actual_damping_stage_power,weighted_load_N,retained_load_target_N,load_error_ratio,max_finished_increment_force_ratio\n";damp::Totals totals;{damp::Component fixture;fixture.Init(&cfg,AppInfo.LogPtr());fixture.Execute(totals,direct,rates,summary);}for(auto* s:{&direct,&rates,&summary}){s->flush();damp::Want(bool(*s),"Component CSV write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_damp_components_r1\",\"backend\":\""<<damp::Backend<<"\",\"passed\":true,\"native_count\":1000,\"fixed_count\":40,\"direct_damping_cases\":5,\"direct_rows\":"<<totals.directRows<<",\"actual_force_calls\":3,\"explicit_complete_rate_calls\":1,\"conditional_reference_rows\":4000,\"periodic_owner_checks\":"<<totals.owners<<",\"named_persistent_restores\":"<<totals.restores<<",\"changed_native_finished_Ace\":"<<totals.changed<<",\"actual_cd_s_inv\":"<<totals.cd<<",\"reference_intrinsic_solid_density\":"<<totals.rhos<<",\"actual_finished_damping_stage_power\":"<<totals.power<<",\"max_full_rate_over_original_budget\":"<<totals.maxRate<<",\"max_finished_increment_over_original_force_budget\":"<<totals.maxDelta<<",\"max_load_target_over_original_force_budget\":"<<totals.maxLoad<<",\"eta0_actual_wrapper_noop\":true,\"legacy_w_poison_dynamic_invariance\":true,\"GPU_CTE_updates_use_production_ConstantDataUp\":"<<damp::CteUpdates<<",\"reference_conditional_on_actual_C_and_wall_Ace\":true,\"closed_normal_target_is_constructed_not_measured_face_flux\":true,\"candidate_damping_enabled_before_Init\":true,\"manufactured_component_only\":true,\"Run_ComputeStep_or_SaveData_called\":false,\"physical_steps_advanced\":0,\"eta0_or_defaultOFF_native_trajectory_verified\":false,\"physical_acceptance\":false}\n";done.flush();damp::Want(bool(done),"Component completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Damping component rejected; retain partials\n";return 2;}}
