// G2 zero-step preparation. Actual CPU/GPU neighbor wrappers, no copied force kernel.
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
static void Synthetic(GpuLoad& fixture){
  const unsigned n=10,size=13;const float sentinel=12345.f;
  Device<double> z(size);Device<typecode> code(size);Device<float> raw(size);Device<float3> ace(size),load(size);
  const unsigned auxsize=cusph::HydroMechTopBandAuxSize(n);Device<float> aux(auxsize+4);
  const std::vector<double> hz={100,10,9,8,7,200,300,400,500,600,700,800,900};
  const std::vector<typecode> hc={CODE_TYPE_FIXED,CODE_TYPE_FLUID,CODE_TYPE_FLUID,CODE_TYPE_FLUID,CODE_TYPE_FLUID
    ,CODE_SetPeriodic(CODE_TYPE_FLUID),CODE_TYPE_FLOATING,CODE_SetOutPos(CODE_TYPE_FLUID),CODE_TYPE_FIXED,CODE_SetOutIgnore(CODE_TYPE_FLUID)
    ,CODE_TYPE_FLUID,CODE_TYPE_FLUID,CODE_TYPE_FLUID};
  z.Put(hz);code.Put(hc);
  for(double fraction:{0.,.5,1.,1.5,0.}){
    const float f=float((std::min)(1.,fraction));std::vector<float> hr(size,sentinel);
    std::vector<float3> ha(size,make_float3(1.25f,-2.5f,7.5f)),hl(size,make_float3(13,17,19));
    for(unsigned p=1;p<=4;p++){hr[p]=(p==1?-2.f:p==2?-3.f:-100.f)*f;hl[p]=make_float3(0,0,p==1?-500.f*f:0);ha[p].z+=hl[p].z;}
    raw.Put(hr);ace.Put(ha);load.Put(hl);aux.Put(std::vector<float>(auxsize+4,sentinel));
    const auto totals=cusph::ComputeHydroMechTopBandTotals(n,1,2,2,z.p,code.p,load.p,raw.p,aux.p);Sync();
    Need(totals.x==10&&totals.y==-1000.*f&&totals.z==-10.*f,"Synthetic totals: selection, strict support cutoff or reduction is wrong");
    fixture.SyntheticNormalize(n,1,z.p,code.p,raw.p,ace.p,load.p);
    const auto aa=ace.Get(),ll=load.Get();const auto scratch=aux.Get();
    for(unsigned p=0;p<size;p++){
      if(p>=1&&p<=4){
        const float expected=(p==1?-200.f:p==2?-300.f:0.f)*f;
        Need(ll[p].x==0&&ll[p].y==0&&ll[p].z==expected&&aa[p].x==ha[p].x&&aa[p].y==ha[p].y&&aa[p].z==7.5f+expected,"Synthetic new-old/background acceleration replacement failed");
      }else Need(Same(aa[p],ha[p])&&Same(ll[p],hl[p]),"Ignored type or memory tail was changed");
    }
    for(unsigned p=auxsize;p<scratch.size();p++)Need(scratch[p]==sentinel,"Reduction aux tail overwritten");
    Need(raw.Get()==hr&&z.Get()==hz&&code.Get()==hc,"Normalization changed raw/geometry/types");
  }
  for(float bad:{0.f,1.f,std::numeric_limits<float>::quiet_NaN()}){
    std::vector<float> hr(size,0);hr[1]=bad;std::vector<float3> hl(size,make_float3(0,0,0));hl[1].z=-500;
    raw.Put(hr);load.Put(hl);const auto before=ace.Get();bool rejected=false;
    try{fixture.SyntheticNormalize(n,1,z.p,code.p,raw.p,ace.p,load.p);}catch(const std::exception& e){Need(std::string(e.what()).find("negative raw vertical load")!=std::string::npos,"Unexpected synthetic rejection");rejected=true;}
    Need(rejected,"Nonnegative/nonfinite raw support was silently accepted");const auto after=ace.Get();for(unsigned p=0;p<size;p++)Need(Same(before[p],after[p]),"Rejected normalization changed acceleration");
  }
}
static void MultiBlock(){
  // Closed-form fields: every real particle is in-band, mass=2, raw=-1/2;
  // one native particle carries the old load -n. Thus totals=(1,-2n,-n),
  // scale=2 and every new load=-1. No cloned neighbor/reduction algorithm.
  for(unsigned n:{257u,65537u}){
    const unsigned size=n+3,asize=cusph::HydroMechTopBandAuxSize(n);const float tail=12345;
    Device<double> z(size);Device<typecode> code(size);Device<float> raw(size),aux(asize+4);Device<float3> ace(size),load(size);
    std::vector<double> hz(size,1);std::vector<typecode> hc(size,CODE_TYPE_FLUID);std::vector<float> hr(size,-.5f);
    std::vector<float3> hl(size,make_float3(0,0,0)),ha(size,make_float3(1.25f,-2.5f,7.5f));hl[0].z=-float(n);ha[0].z+=hl[0].z;
    for(unsigned i=n;i<size;i++){hz[i]=999;hr[i]=tail;hl[i]=make_float3(tail,tail,tail);ha[i]=hl[i];}
    z.Put(hz);code.Put(hc);raw.Put(hr);load.Put(hl);ace.Put(ha);tdouble3 first{};
    for(unsigned repeat=0;repeat<3;repeat++){
      aux.Put(std::vector<float>(asize+4,tail));const auto totals=cusph::ComputeHydroMechTopBandTotals(n,0,2,2,z.p,code.p,load.p,raw.p,aux.p);Sync();
      Need(totals.x==1&&totals.y==-2.*n&&totals.z==-double(n),"Multi-block closed-form totals failed at n="+std::to_string(n));
      if(repeat)Need(Same(totals,first),"Reduction repeat was not bit-identical");else first=totals;
      const auto scratch=aux.Get();for(unsigned i=asize;i<scratch.size();i++)Need(scratch[i]==tail,"Multi-block aux tail overwritten");
    }
    cusph::ApplyHydroMechTopBandLoad(n,0,1,2,2,z.p,code.p,raw.p,ace.p,load.p);Sync();const auto aa=ace.Get(),ll=load.Get();
    for(unsigned i=0;i<n;i++)Need(ll[i].x==0&&ll[i].y==0&&ll[i].z==-1&&aa[i].x==1.25f&&aa[i].y==-2.5f&&aa[i].z==6.5f,"Multi-block background/replacement failed");
    for(unsigned i=n;i<size;i++)Need(Same(aa[i],ha[i])&&Same(ll[i],hl[i]),"Multi-block apply tail overwritten");
    Need(z.Get()==hz&&code.Get()==hc&&raw.Get()==hr,"Multi-block modified inputs");
  }
}
static double RelativeFloatDifference(float actual,float reference){
  Need(std::isfinite(actual)&&std::isfinite(reference),"Nonfinite CPU/GPU comparison");
  return std::abs(double(actual)-reference)/(std::max)(1.,std::abs(double(reference)));
}
static void Configure(JSphCfgRun& cfg,char* executable,const std::string& stem,const fs::path& out,bool cpu){
  std::vector<std::string> strings={executable,cpu?"-cpu":"-gpu:0","-stable","-ompthreads:1","-mdbc","-sv:none",stem,out.string()};
  std::vector<char*> args;for(auto& s:strings)args.push_back(s.data());cfg.LoadArgv(int(args.size()),args.data());
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
}
int main(int argc,char** argv){
  fs::path out;
  try{
    Need(argc==3,"Usage: hg_gpu_load_test EXISTING_CASE_STEM NEW_OUTPUT_DIRECTORY");out=fs::absolute(argv[2]);Need(!fs::exists(out),"Refusing existing output");fs::create_directories(out);
    AppInfo.ConfigRunPaths(argv[0]);const std::vector<double> fractions={0,.5,1,1.5,0};std::vector<Phase> cpu,offcpu,gpu,offgpu;Frame cpuinitial,gpuinitial;
    {JSphCfgRun cfg;Configure(cfg,argv[0],argv[1],out/"cpu",true);CpuLoad f;f.Execute(&cfg,AppInfo.LogPtr(),"native",0,1,-1);cpuinitial=f.NativeState();
      for(double q:fractions){offcpu.push_back(f.Probe(q,false));cpu.push_back(f.Probe(q,true));VerifyNormalization(cpu.back(),q);}}
    {JSphCfgRun cfg;Configure(cfg,argv[0],argv[1],out/"gpu",false);GpuLoad f;f.Init(&cfg,AppInfo.LogPtr());gpuinitial=f.NativeState();Synthetic(f);MultiBlock();
      for(double q:fractions){offgpu.push_back(f.Probe(q,false));gpu.push_back(f.Probe(q,true));VerifyNormalization(gpu.back(),q);}}
    // Declared before execution: CPU/GPU local float neighbor arithmetic may
    // differ. This preliminary 64-eps gate is NOT a bitwise or physical claim.
    Need(cpuinitial.size()==1040&&gpuinitial.size()==1040,"Initial native ID extent");
    for(const auto& entry:cpuinitial){const auto& c=entry.second;const auto& g=gpuinitial.at(entry.first);
      Need(c.code==g.code&&Same(c.pos,g.pos),"Initial CPU/GPU native ID/geometry mismatch");
      if(CODE_IsFluid(c.code))Need(Unchanged(c,g),"Initial CPU/GPU fluid physical state mismatch at ID="+std::to_string(entry.first));
    }
    const double tolerance=64.*std::numeric_limits<float>::epsilon();double maxraw=0,maxload=0,maxace=0;std::string worst;double worsterror=0;
    const auto error=[&](float actual,float reference,const char* field,unsigned id,double q){const double e=RelativeFloatDifference(actual,reference);if(e>worsterror){worsterror=e;std::ostringstream s;s<<std::setprecision(17)<<"q="<<q<<" id="<<id<<" field="<<field<<" GPU="<<actual<<" CPU="<<reference<<" scaled_error="<<e;worst=s.str();}return e;};
    std::ofstream csv(out/"load_compare.csv");csv<<std::setprecision(17)<<"fraction,id,cpu_raw,gpu_raw,cpu_load_z,gpu_load_z,cpu_ax,gpu_ax,cpu_az,gpu_az\n";
    for(unsigned phase=0;phase<fractions.size();phase++)for(const auto& entry:cpu[phase].after){
      const unsigned id=entry.first;const auto& c=entry.second;const auto& g=gpu[phase].after.at(id);
      Need(c.code==g.code&&Same(c.pos,g.pos),"CPU/GPU native geometry mismatch");
      if(CODE_IsFluid(c.code))Need(Same(c.velocity,g.velocity)&&Same(c.stress,g.stress)&&Same(c.pore,g.pore),"CPU/GPU native-fluid physical state changed");
      const auto& cb=cpu[phase].before.at(id);const auto& gb=gpu[phase].before.at(id);
      const auto& co=offcpu[phase].after.at(id);const auto& go=offgpu[phase].after.at(id);
      Need(Unchanged(cb,co)&&Same(cb.ace,co.ace)&&Unchanged(gb,go)&&Same(gb.ace,go.ace),"Mode5 raw collection changed pre-normalization off-path physics or rates");
      maxraw=(std::max)(maxraw,error(g.raw,c.raw,"raw",id,fractions[phase]));maxload=(std::max)(maxload,error(g.load.z,c.load.z,"load.z",id,fractions[phase]));
      for(double d:{error(g.ace.x,c.ace.x,"ace.x",id,fractions[phase]),error(g.ace.y,c.ace.y,"ace.y",id,fractions[phase]),error(g.ace.z,c.ace.z,"ace.z",id,fractions[phase])})maxace=(std::max)(maxace,d);
      csv<<fractions[phase]<<','<<id<<','<<c.raw<<','<<g.raw<<','<<c.load.z<<','<<g.load.z<<','<<c.ace.x<<','<<g.ace.x<<','<<c.ace.z<<','<<g.ace.z<<'\n';
    }
    csv.flush();Need(bool(csv),"Comparison CSV write failed");Need(maxraw<=tolerance&&maxload<=tolerance&&maxace<=tolerance,"CPU/GPU preliminary 64-float-eps comparison failed: "+worst);
    std::ofstream record(out/"complete.json");record<<std::setprecision(17)<<"{\"passed\":true,\"integrated_steps\":0,\"synthetic_passed\":true,\"same_backend_off_path_exact\":true,\"phase_count\":5,\"normal_particles\":1040,\"force_limit_N_m\":0.001,\"relative_float_limit\":"<<tolerance
      <<",\"raw_scaled_max_error\":"<<maxraw<<",\"load_scaled_max_error\":"<<maxload<<",\"ace_scaled_max_error\":"<<maxace<<",\"phases\":[";
    for(unsigned i=0;i<fractions.size();i++){if(i)record<<',';record<<"{\"fraction\":"<<fractions[i]<<",\"cpu_target\":"<<cpu[i].target<<",\"gpu_target\":"<<gpu[i].target<<",\"cpu_applied\":"<<cpu[i].applied<<",\"gpu_applied\":"<<gpu[i].applied<<'}';}
    record<<"],\"multi_block_sizes\":[257,65537],\"reduction_repeats\":3,\"limitations\":[\"External raw scratch: production mode5 input/pool lifecycle not yet accepted\",\"Initial geometry only, no time integration or HG/SPR\",\"CPU/GPU comparison is tolerance based, not 0 ULP\"],\"physical_accuracy_accepted\":false}\n";record.flush();Need(bool(record),"Completion write failed");
    std::cout<<"PASS G2 zero-step load operators only\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Production exception; retain logs\n";return 2;}
}
