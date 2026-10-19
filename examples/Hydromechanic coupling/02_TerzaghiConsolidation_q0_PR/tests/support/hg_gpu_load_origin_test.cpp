// G2 causal origin diagnostic, copied orchestration from frozen hg_gpu_load_test.cpp.
// Actual CPU/GPU mode2 versus mode5, no copied force kernel and no new acceptance limit.
// Initialize retained case02 mode1; external raw scratch avoids the still-closed
// production mode5 input/pool gate. This is not integration or pool acceptance.
#define main mechanics_load_unused_main
#include "mechanics_harness.cpp"
#undef main
#include "JSphGpuSingle.h"
#include "JSphGpu_ker.h"
#include "JDsTimersGpu.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <cstring>
#include <limits>
#include <sstream>

static void Need(bool ok,const std::string& message){if(!ok)throw std::runtime_error(message);}
static void Cu(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
static void Sync(){Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());}
template<class T> static bool Same(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
template<class T> static std::vector<T> Download(const T* p,unsigned n){std::vector<T> v(n);Cu(cudaMemcpy(v.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return v;}
template<class T> struct Device{
  T* p=nullptr;unsigned n;explicit Device(unsigned count):n(count){Cu(cudaMalloc(reinterpret_cast<void**>(&p),n*sizeof(T)));}
  ~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void Put(const std::vector<T>& v){Need(v.size()==n,"Upload extent");Cu(cudaMemcpy(p,v.data(),n*sizeof(T),cudaMemcpyHostToDevice));}
  std::vector<T> Get()const{return Download(p,n);}
};
struct RawScope{
  float*& raw;TpHydroMechLoadMode& mode;
  ~RawScope(){raw=nullptr;mode=HMLOAD_TopVertical;}
};
struct Sample{
  typecode code;tdouble3 pos;tfloat4 velocity;tsymatrix3d stress;
  float pore,pore0,plastic,ar,prate,raw;tfloat3 ace,load;tsymatrix3f rate;
};
using Frame=std::map<unsigned,Sample>;
struct Phase{Frame before,after;double target=0,applied=0;};
static bool Unchanged(const Sample& a,const Sample& b){
  return a.code==b.code&&Same(a.pos,b.pos)&&Same(a.velocity,b.velocity)&&Same(a.stress,b.stress)
    &&Same(a.pore,b.pore)&&Same(a.pore0,b.pore0)&&Same(a.plastic,b.plastic)
    &&Same(a.ar,b.ar)&&Same(a.prate,b.prate)&&Same(a.rate,b.rate);
}
static void VerifyNormalization(const Phase& r,double fraction){
  Need(r.before.size()==1040&&r.after.size()==1040,"Expected 1040 unique normal IDs");
  Need(std::abs(r.target+1000.*(std::min)(1.,fraction))<.001&&std::abs(r.applied-r.target)<.001,"Total force target/replacement failed (.001 N/m)");
  for(const auto& entry:r.before){
    const auto& a=entry.second;const auto& b=r.after.at(entry.first);
    Need(Unchanged(a,b),"Normalization changed physical state or pressure/density/stress rates");
    if(CODE_IsFluid(a.code)){
      const float expected=a.ace.z+(b.load.z-a.load.z);
      Need(Same(b.ace.x,a.ace.x)&&Same(b.ace.y,a.ace.y)&&Same(b.ace.z,expected),"Normalization did not replace old acceleration in the tested float order");
    }
  }
}
class CpuLoad:public MechanicsCheck{
  Frame Capture(bool physicalonly=false){
    Frame f;for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Sample s{};s.code=Codec[p];s.pos=Posc[p];s.velocity=Velrhopc[p];s.stress=Sigmac[p];s.pore=PorePressc[p];s.pore0=PorePress0c[p];s.plastic=Kplasticc[p];
      if(!physicalonly){s.ar=Arc[p];s.prate=PorePressRatec[p];s.raw=HydroMechTopLoadRawc?HydroMechTopLoadRawc[p]:0.f;s.ace=Acec[p];s.load=HydroMechLoadAcec[p];s.rate=Rsigmac[p];}
      Need(f.emplace(Idpc[p],s).second,"Duplicate CPU native ID");
    }return f;
  }
public:
  Frame NativeState(){return Capture(true);}
  Phase Probe(double fraction,bool band){
    Need(!SoilBoundaryDerivativeSPR&&!SoilHourglassXi&&!ArtificialStress&&!Shifting&&TDensity==DDT_None,"Probe scope requires HG/SPR/shifting/DDT/artificial stress off");
    TimeStep=HydroMechTopLoadRampTime*fraction;HydroMechTopLoadMode=HMLOAD_TopVertical;
    MdbcBoundCorrection();InterStep=INTERSTEP_SymPredictor;
    std::vector<float> raw(Np+3,12345.f);if(band)HydroMechTopLoadRawc=raw.data();
    RawScope detach{HydroMechTopLoadRawc,HydroMechTopLoadMode};
    PreInteraction_Forces();
    if(band){for(unsigned p=0;p<Np;p++)Need(raw[p]==0,"CPU phase raw scratch not cleared");HydroMechTopLoadMode=HMLOAD_TopKernelBand;}
    ComputeFreeSurfaceTracking();ApplyHydroMechTopLoadAcceleration();ApplyFreeSurfacePorePressure();
    const stinterparmsc parms=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec
      ,FSTypec,FSNormalc,nullptr,CorrMatc,Arc,Acec,nullptr,ShiftingMode,nullptr,nullptr,nullptr,Sigmac,Rsigmac,nullptr);
    StInterResultc result{0};Interaction_Forces_ct(parms,result);
    if(SoilDamping)AddSoilDampingCpu(Np,Npb,Codec,Velrhopc,Acec);
    for(unsigned p=Npb;p<Np;p++)Acec[p].y=0;
    Phase r;r.before=Capture();if(band)NormalizeHydroMechTopBandLoad();r.after=Capture();
    for(const auto& entry:r.before)if(CODE_IsFluid(entry.second.code)){r.target+=double(MassFluid)*entry.second.load.z;r.applied+=double(MassFluid)*r.after.at(entry.first).load.z;}
    if(band)for(unsigned p=Np;p<raw.size();p++)Need(raw[p]==12345.f,"CPU raw tail overwritten");
    HydroMechTopLoadRawc=nullptr;HydroMechTopLoadMode=HMLOAD_TopVertical;PosInteraction_Forces();TimeStep=0;
    return r;
  }
};
class GpuLoad:public JSphGpuSingle{
  Frame Capture(bool physicalonly=false){
    const auto id=Download(Idpg,Np);const auto code=Download(Codeg,Np);const auto xy=Download(Posxyg,Np);const auto z=Download(Poszg,Np);
    const auto v=Download(Velrhopg,Np);const auto s=Download(Sigmag,Np);const auto p=Download(PorePressg,Np);const auto p0=Download(PorePress0g,Np);
    const auto k=Download(Kplasticg,Np);const auto ar=physicalonly?std::vector<float>(Np):Download(Arg,Np);const auto pr=physicalonly?std::vector<float>(Np):Download(PorePressRateg,Np);
    const auto rate=physicalonly?std::vector<tsymatrix3f>(Np):Download(Rsigmag,Np);
    const auto ace=physicalonly?std::vector<float3>(Np):Download(Aceg,Np),load=physicalonly?std::vector<float3>(Np):Download(HydroMechLoadAceg,Np);
    const auto raw=HydroMechTopLoadRawg?Download(HydroMechTopLoadRawg,Np):std::vector<float>(Np,0);
    Frame f;for(unsigned i=0;i<Np;i++)if(CODE_IsNormal(code[i])){
      Sample item{code[i],TDouble3(xy[i].x,xy[i].y,z[i]),TFloat4(v[i].x,v[i].y,v[i].z,v[i].w),s[i],p[i],p0[i],k[i],ar[i],pr[i],raw[i]
        ,TFloat3(ace[i].x,ace[i].y,ace[i].z),TFloat3(load[i].x,load[i].y,load[i].z),rate[i]};
      Need(f.emplace(id[i],item).second,"Duplicate GPU native ID");
    }return f;
  }
public:
  Frame NativeState(){return Capture(true);}
  void Init(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);
    Timersg->Config(cfg->SvTimers);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunGpu();
    Need(!PartBegin&&HydroMech&&Simulate2D&&HydroMechInitMode==HMINIT_None&&HydroMechTopLoadMode==HMLOAD_TopVertical,"GPU probe requires fresh retained mode1 case02");
    Need(!SoilHourglassXi&&!SoilBoundaryDerivativeSPR&&!SoilStressRateGradCorr&&!ArtificialStress&&!Shifting&&TDensity==DDT_None
      &&!UseDEM&&!NoPenetration&&TMdbc2!=MDBC2_NoPen&&!PoreShepardRegularization&&!CaseNfloat&&!CaseNmoving&&TVisco==VISCO_Artificial,"Unsupported GPU probe feature");
    RunGaugeSystem(TimeStep,true);FreePartsInit();UpdateMaxValues();Timersg->ResetTimes();Timersg->TmStop(TMG_Init,false);
  }
  Phase Probe(double fraction,bool band){
    TimeStep=HydroMechTopLoadRampTime*fraction;HydroMechTopLoadMode=HMLOAD_TopVertical;
    MdbcBoundCorrection();InterStep=INTERSTEP_SymPredictor;
    Device<float> raw(Np+3);raw.Put(std::vector<float>(Np+3,12345.f));if(band)HydroMechTopLoadRawg=raw.p;
    RawScope detach{HydroMechTopLoadRawg,HydroMechTopLoadMode};
    PreInteraction_Forces();
    if(band){const auto zero=raw.Get();for(unsigned p=0;p<Np;p++)Need(zero[p]==0,"GPU phase raw scratch not cleared");HydroMechTopLoadMode=HMLOAD_TopKernelBand;}
    ConstantDataUp();ComputeFreeSurfaceTracking();ApplyFreeSurfacePorePressure();ApplyHydroMechTopLoadAcceleration();
    const StInterParmsg parms=StrInterParmsg(Simulate2D,Symmetry,TKernel,FtMode,false,TDensity,ShiftingMode,TMdbc2
      ,Visco*ViscoBoundFactor,Visco,BlockSizes.forcesbound,BlockSizes.forcesfluid,Np,Npb,NpbOk,0,Nstep,DivData,Dcellg
      ,Posxyg,Poszg,PosCellg,Velrhopg,Idpg,Codeg,FtoMasspg,SpsTaug,nullptr,CorrMatg,BoundModeg,BoundSlipModeg,TangenVelg,MotionVelg,BoundNormalg,nullptr
      ,ViscDtg,Arg,Aceg,nullptr,nullptr,Sigmag,Rsigmag,nullptr,PorePressg,PorePressRateg,FSTypeg,FSNormalg,IsHydroMechDrainageActive()
      ,HydroMechLoadAceg,HydroMechTopLoadRawg,nullptr,nullptr,nullptr);
    cusph::Interaction_Forces(parms);if(SoilDamping)cusph::AddSoilDamping(Np,Npb,Codeg,Velrhopg,Aceg);
    cusph::Resety(Np-Npb,Npb,Aceg);Sync();
    Phase r;r.before=Capture();if(band)NormalizeHydroMechTopBandLoad();Sync();r.after=Capture();
    for(const auto& entry:r.before)if(CODE_IsFluid(entry.second.code)){r.target+=double(MassFluid)*entry.second.load.z;r.applied+=double(MassFluid)*r.after.at(entry.first).load.z;}
    if(band){const auto tail=raw.Get();for(unsigned p=Np;p<tail.size();p++)Need(tail[p]==12345.f,"GPU raw tail overwritten");}
    HydroMechTopLoadRawg=nullptr;HydroMechTopLoadMode=HMLOAD_TopVertical;PosInteraction_Forces();TimeStep=0;
    return r;
  }
  // Use the actual host normalization (including its rejection) with a tiny
  // independent array. Restore ownership before any device buffer is destroyed.
  void SyntheticNormalize(unsigned n,unsigned nb,double* z,typecode* code,float* raw,float3* ace,float3* load){
    const auto oldnp=Np,oldnb=Npb;const auto oldmass=MassFluid,oldh=KernelSize;const auto oldmode=HydroMechTopLoadMode;
    auto* oldz=Poszg;auto* oldcode=Codeg;auto* oldraw=HydroMechTopLoadRawg;auto* oldace=Aceg;auto* oldload=HydroMechLoadAceg;
    auto restore=[&](){Np=oldnp;Npb=oldnb;MassFluid=oldmass;KernelSize=oldh;HydroMechTopLoadMode=oldmode;Poszg=oldz;Codeg=oldcode;HydroMechTopLoadRawg=oldraw;Aceg=oldace;HydroMechLoadAceg=oldload;};
    Np=n;Npb=nb;MassFluid=2;KernelSize=2;HydroMechTopLoadMode=HMLOAD_TopKernelBand;Poszg=z;Codeg=code;HydroMechTopLoadRawg=raw;Aceg=ace;HydroMechLoadAceg=load;
    try{NormalizeHydroMechTopBandLoad();Sync();}catch(...){restore();throw;}restore();
  }
};

static bool PhysicalSame(const Sample& a,const Sample& b){
  return a.code==b.code&&Same(a.pos,b.pos)&&Same(a.velocity,b.velocity)&&Same(a.stress,b.stress)
    &&Same(a.pore,b.pore)&&Same(a.pore0,b.pore0)&&Same(a.plastic,b.plastic);
}
class OriginCpu:public CpuLoad{
public:
  double Mass()const{Need(MassBound==MassFluid,"Equal native masses required for all-particle force norm");return double(MassFluid);}
  double Support()const{return double(KernelSize);}
  Frame Flexible(double fraction){
    TimeStep=HydroMechTopLoadRampTime*fraction;HydroMechTopLoadMode=HMLOAD_FlexibleConfinement;
    MdbcBoundCorrection();InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();
    const Frame before=NativeState();ComputeFreeSurfaceTracking();ApplyFreeSurfacePorePressure();
    const stinterparmsc parms=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec
      ,FSTypec,FSNormalc,nullptr,CorrMatc,Arc,Acec,nullptr,ShiftingMode,nullptr,nullptr,nullptr,Sigmac,Rsigmac,nullptr);
    StInterResultc result{0};Interaction_Forces_ct(parms,result);
    if(SoilDamping)AddSoilDampingCpu(Np,Npb,Codec,Velrhopc,Acec);
    for(unsigned p=Npb;p<Np;p++)Acec[p].y=0;
    Frame frame=NativeState();
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Sample& s=frame.at(Idpc[p]);Need(PhysicalSame(s,before.at(Idpc[p])),"CPU mode2 changed physical state");
      s.ace=Acec[p];s.load=HydroMechLoadAcec[p];s.raw=s.load.z;s.ar=Arc[p];s.prate=PorePressRatec[p];s.rate=Rsigmac[p];
    }
    PosInteraction_Forces();HydroMechTopLoadMode=HMLOAD_TopVertical;TimeStep=0;return frame;
  }
};
class OriginGpu:public GpuLoad{
public:
  double Mass()const{Need(MassBound==MassFluid,"Equal native masses required for all-particle force norm");return double(MassFluid);}
  double Support()const{return double(KernelSize);}
  Frame Flexible(double fraction){
    TimeStep=HydroMechTopLoadRampTime*fraction;HydroMechTopLoadMode=HMLOAD_FlexibleConfinement;
    MdbcBoundCorrection();InterStep=INTERSTEP_SymPredictor;ConstantDataUp();PreInteraction_Forces();
    const Frame before=NativeState();ComputeFreeSurfaceTracking();ApplyFreeSurfacePorePressure();
    const StInterParmsg parms=StrInterParmsg(Simulate2D,Symmetry,TKernel,FtMode,false,TDensity,ShiftingMode,TMdbc2
      ,Visco*ViscoBoundFactor,Visco,BlockSizes.forcesbound,BlockSizes.forcesfluid,Np,Npb,NpbOk,0,Nstep,DivData,Dcellg
      ,Posxyg,Poszg,PosCellg,Velrhopg,Idpg,Codeg,FtoMasspg,SpsTaug,nullptr,CorrMatg,BoundModeg,BoundSlipModeg,TangenVelg,MotionVelg,BoundNormalg,nullptr
      ,ViscDtg,Arg,Aceg,nullptr,nullptr,Sigmag,Rsigmag,nullptr,PorePressg,PorePressRateg,FSTypeg,FSNormalg,IsHydroMechDrainageActive()
      ,HydroMechLoadAceg,HydroMechTopLoadRawg,nullptr,nullptr,nullptr);
    cusph::Interaction_Forces(parms);if(SoilDamping)cusph::AddSoilDamping(Np,Npb,Codeg,Velrhopg,Aceg);
    cusph::Resety(Np-Npb,Npb,Aceg);Sync();
    Frame frame=NativeState();const auto ids=Download(Idpg,Np);const auto code=Download(Codeg,Np);
    const auto ace=Download(Aceg,Np),load=Download(HydroMechLoadAceg,Np);const auto ar=Download(Arg,Np),pr=Download(PorePressRateg,Np);const auto rate=Download(Rsigmag,Np);
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(code[p])){
      Sample& s=frame.at(ids[p]);Need(PhysicalSame(s,before.at(ids[p])),"GPU mode2 changed physical state");
      s.ace=TFloat3(ace[p].x,ace[p].y,ace[p].z);s.load=TFloat3(load[p].x,load[p].y,load[p].z);s.raw=s.load.z;s.ar=ar[p];s.prate=pr[p];s.rate=rate[p];
    }
    PosInteraction_Forces();HydroMechTopLoadMode=HMLOAD_TopVertical;TimeStep=0;return frame;
  }
};
static void ConfigureOrigin(JSphCfgRun& cfg,char* executable,const std::string& stem,const fs::path& out,bool cpu){
  std::vector<std::string> strings={executable,cpu?"-cpu":"-gpu:0","-stable","-ompthreads:1","-mdbc","-sv:none",stem,out.string()};
  std::vector<char*> args;for(auto& s:strings)args.push_back(s.data());cfg.LoadArgv(int(args.size()),args.data());
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
}
int main(int argc,char** argv){
  try{
    Need(argc==3,"Usage: hg_gpu_load_origin_test EXISTING_CASE_STEM NEW_OUTPUT_DIRECTORY");
    const fs::path out=fs::absolute(argv[2]);Need(!fs::exists(out),"Refusing existing output");fs::create_directories(out);
    AppInfo.ConfigRunPaths(argv[0]);const std::vector<double> fractions={0,.5,1,1.5,0};
    std::vector<Frame> cpu2,gpu2;std::vector<Phase> cpu5,gpu5;Frame ci,gi;double mass=0,support=0;
    {JSphCfgRun cfg;ConfigureOrigin(cfg,argv[0],argv[1],out/"cpu",true);OriginCpu f;f.Execute(&cfg,AppInfo.LogPtr(),"native",0,1,-1);
      ci=f.NativeState();mass=f.Mass();support=f.Support();
      for(double q:fractions){cpu2.push_back(f.Flexible(q));cpu5.push_back(f.Probe(q,true));VerifyNormalization(cpu5.back(),q);}}
    {JSphCfgRun cfg;ConfigureOrigin(cfg,argv[0],argv[1],out/"gpu",false);OriginGpu f;f.Init(&cfg,AppInfo.LogPtr());
      gi=f.NativeState();Need(f.Mass()==mass&&f.Support()==support,"CPU/GPU constants differ");
      for(double q:fractions){gpu2.push_back(f.Flexible(q));gpu5.push_back(f.Probe(q,true));VerifyNormalization(gpu5.back(),q);}}
    Need(ci.size()==1040&&gi.size()==1040,"Native ID extent");double zmax=-DBL_MAX;
    for(const auto& e:ci){const auto& g=gi.at(e.first);Need(e.second.code==g.code&&Same(e.second.pos,g.pos),"Native ID/geometry mismatch");
      if(CODE_IsFluid(e.second.code)){Need(PhysicalSame(e.second,g),"Initial native-fluid state mismatch");zmax=(std::max)(zmax,e.second.pos.z);}}
    const double originalLimit=64.*std::numeric_limits<float>::epsilon();
    unsigned cpuMismatches=0,gpuMismatches=0,states=0,fluidstates=0;double maxScaled2=0,maxScaled5=0,maxAbsolute2=0,maxAbsolute5=0;
    // Predeclared for this new causal diagnostic: spatial L1 of actual vector
    // acceleration differences, all 1040 native particles, not a clipped field
    // or the signed total-force cancellation. Original 64eps remains recorded.
    const double spatialForceLimit=.001;bool spatialPassed=true;
    std::ofstream csv(out/"origin_compare.csv");csv<<std::setprecision(17)
      <<"phase,fraction,id,code,z,in_band,cpu_mode2_raw,gpu_mode2_raw,cpu_mode5_raw,gpu_mode5_raw,cpu_origin_exact,gpu_origin_exact,cpu_mode5_load,gpu_mode5_load,mode2_abs_cpu_gpu,mode5_abs_cpu_gpu,cpu_ax,gpu_ax,cpu_ay,gpu_ay,cpu_az,gpu_az\n";
    std::ofstream done(out/"complete.json");done<<std::setprecision(17)<<"{\"diagnostic_only\":true,\"integrated_steps\":0,\"original_64eps_limit\":"<<originalLimit<<",\"phases\":[";
    for(unsigned k=0;k<fractions.size();k++){
      double cpuL1=0,gpuL1=0,diffL1=0,cpuBand=0,gpuBand=0,cpuApplied=0,gpuApplied=0,spatialForce=0;
      for(const auto& e:cpu2[k]){
        const unsigned id=e.first;const auto& c=e.second;const auto& g=gpu2[k].at(id);const auto& c5=cpu5[k].before.at(id);const auto& g5=gpu5[k].before.at(id);
        Need(Unchanged(c,c5)&&Unchanged(g,g5),"Mode2/mode5 physical states or rates differ at ID="+std::to_string(id));
        Need(c.code==g.code&&Same(c.pos,g.pos),"CPU/GPU current native geometry mismatch");
        const auto ca=cpu5[k].after.at(id).ace,ga=gpu5[k].after.at(id).ace;
        const double dx=double(ga.x)-ca.x,dy=double(ga.y)-ca.y,dz=double(ga.z)-ca.z;
        Need(std::isfinite(dx)&&std::isfinite(dy)&&std::isfinite(dz),"Nonfinite spatial acceleration difference");
        spatialForce+=mass*std::sqrt(dx*dx+dy*dy+dz*dz);
        if(CODE_IsFluid(c.code)){Need(PhysicalSame(c,g),"CPU/GPU current native-fluid state mismatch");fluidstates++;}
        const bool ce=Same(c.raw,c5.raw),ge=Same(g.raw,g5.raw);cpuMismatches+=!ce;gpuMismatches+=!ge;states++;
        Need(std::isfinite(c.raw)&&std::isfinite(g.raw)&&std::isfinite(c5.raw)&&std::isfinite(g5.raw),"Nonfinite origin comparison");
        const double d2=std::abs(double(g.raw)-c.raw),d5=std::abs(double(g5.raw)-c5.raw);
        maxAbsolute2=(std::max)(maxAbsolute2,d2);maxAbsolute5=(std::max)(maxAbsolute5,d5);
        maxScaled2=(std::max)(maxScaled2,d2/(std::max)(1.,std::abs(double(c.raw))));
        maxScaled5=(std::max)(maxScaled5,d5/(std::max)(1.,std::abs(double(c5.raw))));
        cpuL1+=mass*std::abs(double(c.raw));gpuL1+=mass*std::abs(double(g.raw));diffL1+=mass*d2;
        const bool band=c.pos.z>zmax-support;if(band){cpuBand+=mass*c.raw;gpuBand+=mass*g.raw;}
        const float cl=cpu5[k].after.at(id).load.z,gl=gpu5[k].after.at(id).load.z;cpuApplied+=mass*cl;gpuApplied+=mass*gl;
        csv<<k<<','<<fractions[k]<<','<<id<<','<<unsigned(c.code)<<','<<c.pos.z<<','<<band<<','<<c.raw<<','<<g.raw<<','<<c5.raw<<','<<g5.raw<<','<<ce<<','<<ge<<','<<cl<<','<<gl<<','<<d2<<','<<d5
          <<','<<ca.x<<','<<ga.x<<','<<ca.y<<','<<ga.y<<','<<ca.z<<','<<ga.z<<'\n';
      }
      const bool phasePassed=spatialForce<spatialForceLimit;spatialPassed=spatialPassed&&phasePassed;
      if(k)done<<',';done<<"{\"fraction\":"<<fractions[k]<<",\"cpu_flex_l1_force_N_m\":"<<cpuL1<<",\"gpu_flex_l1_force_N_m\":"<<gpuL1
        <<",\"cpu_gpu_flex_l1_difference_N_m\":"<<diffL1<<",\"cpu_band_raw_force_N_m\":"<<cpuBand<<",\"gpu_band_raw_force_N_m\":"<<gpuBand
        <<",\"cpu_applied_force_N_m\":"<<cpuApplied<<",\"gpu_applied_force_N_m\":"<<gpuApplied
        <<",\"all_native_spatial_vector_L1_force_difference_N_m\":"<<spatialForce<<",\"spatial_force_passed\":"<<(phasePassed?"true":"false")<<'}';
    }
    const bool exact=!cpuMismatches&&!gpuMismatches;
    done<<"],\"native_comparisons\":"<<states<<",\"native_fluid_comparisons\":"<<fluidstates<<",\"cpu_mode2_mode5_mismatches\":"<<cpuMismatches<<",\"gpu_mode2_mode5_mismatches\":"<<gpuMismatches
      <<",\"same_backend_origin_exact\":"<<(exact?"true":"false")<<",\"mode2_cpu_gpu_max_absolute\":"<<maxAbsolute2<<",\"mode5_cpu_gpu_max_absolute\":"<<maxAbsolute5
      <<",\"mode2_cpu_gpu_max_scaled\":"<<maxScaled2<<",\"mode5_cpu_gpu_max_scaled\":"<<maxScaled5
      <<",\"mode2_original_64eps_passed\":"<<(maxScaled2<=originalLimit?"true":"false")<<",\"mode5_original_64eps_passed\":"<<(maxScaled5<=originalLimit?"true":"false")
      <<",\"spatial_force_limit_N_m\":"<<spatialForceLimit<<",\"spatial_native_particles\":1040,\"spatial_force_passed\":"<<(spatialPassed?"true":"false")
      <<",\"g2_accepted\":false,\"physical_accuracy_accepted\":false,\"limitations\":[\"Origin diagnostic on the current built neighbor kernel, not a frozen-G1 executable regression\",\"Original r1 rejection and 64eps limit remain unchanged; near-zero cancellation scale must be reviewed, not silently relaxed\",\"Spatial force gate adds an all-native absolute-force measure; it does not prove long-term errors physically irrelevant\",\"No mode5 pool/input or integration acceptance\"]}\n";
    csv.flush();done.flush();Need(bool(csv)&&bool(done),"Origin record write failed");
    Need(exact,"Same-backend mode2/mode5 origin differs; retain all diagnostics");
    Need(spatialPassed,"All-native spatial force allocation difference exceeds .001 N/m; retain diagnostics");
    std::cout<<"ORIGIN IDENTICAL; not G2 acceptance. CPU/GPU mode2 maximum scaled error="<<std::setprecision(17)<<maxScaled2<<'\n';return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Production exception; retain logs\n";return 2;}
}

