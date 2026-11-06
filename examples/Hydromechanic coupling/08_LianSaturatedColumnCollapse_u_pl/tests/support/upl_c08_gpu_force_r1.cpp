// Actual case08 GPU one-main-ct affine compression; private zero-step diagnostic.
#include "JSphGpuSingle.h"
#include "JSphGpu_ker.h"
#include "JSphCfgRun.h"
#include "JCellDivGpuSingle.h"
#include "JDsTimersGpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("UplC08GpuForce","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
static constexpr unsigned Fixed=2060,Soil=5000,Total=Fixed+Soil;
static constexpr double Height=2.,RateC=-1./8192.;
template<class T>static std::vector<T> Down(const T* p,unsigned n){Need(p!=nullptr,"Missing actual device array");std::vector<T>a(n);Cu(cudaMemcpy(a.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return a;}
template<class T>static void Up(T* p,const std::vector<T>& a){Need(p!=nullptr,"Missing actual upload target");Cu(cudaMemcpy(p,a.data(),a.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||!memcmp(a.data(),b.data(),a.size()*sizeof(T)));}
template<class T>static bool EqualAt(const std::vector<T>& a,const std::vector<T>& b,unsigned q){return q<a.size()&&q<b.size()&&!memcmp(a.data()+q,b.data()+q,sizeof(T));}
struct State{
  std::vector<unsigned> id,cell,fs;std::vector<typecode> code;std::vector<double2> xy;std::vector<double> z,j,theta;
  std::vector<float4> poscell,vel;std::vector<float> p,p0,rate,plastic,posdiv;std::vector<float3> bn,tangent,fn,load,ace;std::vector<byte> mode,slip;
  std::vector<tsymatrix3d> sigma;std::vector<tmatrix3d> c;
};

struct BorrowDerivative{
  float3*& pointer;float3* original;float3* owned=nullptr;
  BorrowDerivative(float3*& p,unsigned n):pointer(p),original(p){Need(!p,"Derivative pointer was already owned");Cu(cudaMalloc(reinterpret_cast<void**>(&owned),n*sizeof(float3)));pointer=owned;}
  void Release(){pointer=original;float3* p=owned;owned=nullptr;Cu(cudaFree(p));}
  ~BorrowDerivative(){pointer=original;if(owned)cudaFree(owned);}
};
struct RestoreFlags{bool &feedback,&dynamic,&wall,&stress;bool f,d,w,s;~RestoreFlags(){feedback=f;dynamic=d;wall=w;stress=s;}};
static const char* CrossNames[14]={"theta","sxx","syy","szz","sxy","syz","sxz","Ace_x","Ace_y","Ace_z","legacy_Arc","rate_Pa_s","local_compression_Pa_s","spatial_acceleration_remainder_Pa_s"};
struct CpuRow{bool kin=false,rate=false;double x=0,z=0,vz=0;std::array<double,14> v{};};
static std::vector<std::string> Split(std::string line){if(!line.empty()&&line.back()=='\r')line.pop_back();std::stringstream s(line);std::vector<std::string> row;std::string v;while(std::getline(s,v,','))row.push_back(v);return row;}
static std::vector<CpuRow> CpuReference(const fs::path& dir){
  std::vector<CpuRow> out(Total);
  for(unsigned table=0;table<2;table++){
    std::ifstream f(dir/(table?"rates.csv":"kinematics.csv"));Need(bool(f),"Closed CPU force CSV missing");std::string line;Need(bool(std::getline(f,line)),"CPU force header missing");const auto h=Split(line);
    const auto index=[&](const char* key){const auto i=std::find(h.begin(),h.end(),key);Need(i!=h.end(),"CPU force field missing");return size_t(i-h.begin());};
    const size_t idc=index("native_id"),xc=(table?0:index("x")),zc=(table?0:index("z")),vc=(table?0:index("stored_vz"));std::array<size_t,14> cols{};for(unsigned k=(table?11:0);k<(table?14:11);k++)cols[k]=index(CrossNames[k]);unsigned rows=0;
    while(std::getline(f,line)){const auto r=Split(line);Need(r.size()==h.size(),"Truncated CPU force row");const unsigned id=unsigned(std::stoul(r[idc]));Need(id>=Fixed&&id<Total,"Unknown CPU soil ID");auto& a=out[id];Need(!(table?a.rate:a.kin),"Duplicate CPU force ID");if(table)a.rate=true;else{a.kin=true;a.x=std::stod(r[xc]);a.z=std::stod(r[zc]);a.vz=std::stod(r[vc]);}for(unsigned k=(table?11:0);k<(table?14:11);k++){a.v[k]=std::stod(r[cols[k]]);Need(std::isfinite(a.v[k]),"Closed CPU descriptor is nonfinite");}rows++;}Need(f.eof()&&rows==Soil,"Closed CPU force count changed");
  }
  for(unsigned id=Fixed;id<Total;id++)Need(out[id].kin&&out[id].rate,"CPU force ID missing from one table");return out;
}
class Probe:public JSphGpuSingle{
  State Capture(bool live)const{State a;a.id=Down(Idpg,Np);a.cell=Down(Dcellg,Np);a.code=Down(Codeg,Np);a.xy=Down(Posxyg,Np);a.z=Down(Poszg,Np);a.poscell=Down(PosCellg,Np);a.vel=Down(Velrhopg,Np);a.j=Down(PoroJg,Np);a.theta=Down(PoroThetag,Np);a.p=Down(PorePressg,Np);a.p0=Down(PorePress0g,Np);a.rate=Down(PorePressRateg,Np);a.plastic=Down(Kplasticg,Np);a.sigma=Down(Sigmag,Np);a.c=Down(CorrMatg,Np);a.fs=Down(FSTypeg,Np);a.fn=Down(FSNormalg,Np);a.posdiv=Down(PosDivg,Np);a.bn=Down(BoundNormalg,Np);a.tangent=Down(TangenVelg,Np);a.mode=Down(BoundModeg,Np);a.slip=Down(BoundSlipModeg,Np);a.load=Down(HydroMechLoadAceg,Np);if(live)a.ace=Down(Aceg,Np);return a;}
  void RestorePersistent(const State& a){Up(Idpg,a.id);Up(Dcellg,a.cell);Up(Codeg,a.code);Up(Posxyg,a.xy);Up(Poszg,a.z);Up(PosCellg,a.poscell);Up(Velrhopg,a.vel);Up(PoroJg,a.j);Up(PoroThetag,a.theta);Up(PorePressg,a.p);Up(PorePress0g,a.p0);Up(PorePressRateg,a.rate);Up(Kplasticg,a.plastic);Up(Sigmag,a.sigma);Up(CorrMatg,a.c);Up(FSTypeg,a.fs);Up(FSNormalg,a.fn);Up(PosDivg,a.posdiv);Up(BoundNormalg,a.bn);Up(TangenVelg,a.tangent);Up(BoundModeg,a.mode);Up(BoundSlipModeg,a.slip);Up(HydroMechLoadAceg,a.load);}
  static bool GeometrySame(const State& a,const State& b){return Same(a.id,b.id)&&Same(a.cell,b.cell)&&Same(a.code,b.code)&&Same(a.xy,b.xy)&&Same(a.z,b.z)&&Same(a.poscell,b.poscell)&&Same(a.bn,b.bn)&&Same(a.slip,b.slip);}
  static bool PersistentSame(const State& a,const State& b){return GeometrySame(a,b)&&Same(a.vel,b.vel)&&Same(a.j,b.j)&&Same(a.theta,b.theta)&&Same(a.p,b.p)&&Same(a.p0,b.p0)&&Same(a.rate,b.rate)&&Same(a.plastic,b.plastic)&&Same(a.sigma,b.sigma)&&Same(a.c,b.c)&&Same(a.fs,b.fs)&&Same(a.fn,b.fn)&&Same(a.posdiv,b.posdiv)&&Same(a.tangent,b.tangent)&&Same(a.mode,b.mode)&&Same(a.load,b.load);}
  std::vector<unsigned> Map(const State& a)const{Need(Np==Total&&Npb==Fixed,"Wrong actual7060 GPU counts");std::vector<unsigned> m(Total,UINT_MAX);unsigned ns=0,nb=0;for(unsigned q=0;q<Np;q++){Need(a.id[q]<Total&&m[a.id[q]]==UINT_MAX,"Unknown/duplicate GPU native ID");m[a.id[q]]=q;if(CODE_IsFluid(a.code[q])){Need(CODE_IsNormal(a.code[q])&&a.id[q]>=Fixed,"GPU soil code changed");ns++;}else{Need(CODE_IsFixed(a.code[q])&&a.id[q]<Fixed,"Unexpected GPU fixed type");nb++;}}Need(ns==Soil&&nb==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"GPU native/exclusion mismatch");return m;}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg,"GPU component advanced time/predictor");}

public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,const fs::path& cpuDir){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Observer-only constructor required");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();Cu(cudaDeviceSynchronize());
    Need(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!HydroMechDynamicSeepage&&HydroMech&&Simulate2D&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&!PeriActive&&!Symmetry&&BoundSlipModeg&&BoundModeg&&TangenVelg&&PoroJg&&PoroThetag,"Wrong genuine GPU observer initialization");
    Need(Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&Gravity==TFloat3(0,0,-9.81f)&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==2e-4f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f,"Retained material/geometry changed");
    Need(TimeMax==0&&NpbOk==465&&!SoilStressRateGradCorr&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0&&TVisco==VISCO_Artificial&&Visco==.1f&&!WithFloating&&!UseDEM&&!AccInput&&!ArtificialStress&&TDensity==DDT_None&&!Shifting&&!Damping&&!SoilDamping&&!SoilHourglassXi&&!HourglassGpu&&!SoilBoundaryDerivativeSPR&&!NoPenetration&&TMdbc2!=MDBC2_NoPen&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity&&!StrainSoftening&&!Aceg&&!BoundDerivativeVelg,"One-main-ct GPU scope changed");
    const State original=Capture(false);const auto map=Map(original);const auto cpu=CpuReference(cpuDir);NoStep();const unsigned initialNpbOk=NpbOk;const auto oldInter=InterStep;const double oldSpeed=DynamicConductivitySpeedMax,oldVelMax=VelMax;const float oldVisc=ViscDtMax;std::array<unsigned char,sizeof(SoilCte)> material;memcpy(material.data(),&SoilCte,sizeof(SoilCte));
    State input=original;double maxStoredV=0;
    for(unsigned q=0;q<Np;q++){const float vz=(CODE_IsFluid(input.code[q])?float(RateC*input.z[q]):0.f);input.vel[q]=make_float4(0,0,vz,RhopZero);maxStoredV=(std::max)(maxStoredV,fabs(double(vz)));input.sigma[q]=tsymatrix3d{};input.plastic[q]=0;input.j[q]=1;input.theta[q]=0;input.p0[q]=input.rate[q]=0;input.p[q]=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(input.z[q]-Height));}RestorePersistent(input);
    // EXACT CPU r1 budgets, declared before the actual main interaction; float material stays float.
    const double derivativeBudget=128.*double(FLT_EPSILON)*(std::max)(fabs(RateC),maxStoredV/double(KernelH))+4096.*double(DBL_EPSILON)*(std::max)(1.,fabs(RateC));
    const double bulk=double(SoilCte.ModulusK),shear=double(SoilCte.ModulusG),lambda=bulk-2.*shear/3.,modulus=(std::max)(bulk+4.*shear/3.,2.*shear);const std::array<double,6> reference={lambda*RateC,lambda*RateC,(lambda+2.*shear)*RateC,0,0,0};std::array<double,6> budget{},maxSigmaError{};for(unsigned c=0;c<6;c++)budget[c]=(c<3?derivativeBudget*modulus+64.*double(FLT_EPSILON)*(std::max)(1.,fabs(reference[c])):derivativeBudget*2.*shear);
    std::ofstream ledger(fs::path(cfg->DirOut)/"ids.csv"),kin(fs::path(cfg->DirOut)/"kinematics.csv"),walls(fs::path(cfg->DirOut)/"walls.csv"),rates(fs::path(cfg->DirOut)/"rates.csv"),cross(fs::path(cfg->DirOut)/"cpu_descriptor.csv");for(auto* f:{&ledger,&kin,&walls,&rates,&cross})*f<<std::setprecision(17);
    ledger<<"native_id,sorted_slot,is_fluid,x,y,z,code\n";for(unsigned id=0;id<Total;id++){const auto q=map[id];ledger<<id<<','<<q<<','<<CODE_IsFluid(original.code[q])<<','<<original.xy[q].x<<','<<original.xy[q].y<<','<<original.z[q]<<','<<unsigned(original.code[q])<<'\n';}
    kin<<"native_id,sorted_slot,x,z,stored_vz,theta,theta_ref,theta_error,theta_budget,sxx,sxx_ref,sxx_error,sxx_budget,syy,syy_ref,syy_error,syy_budget,szz,szz_ref,szz_error,szz_budget,sxy,sxy_ref,sxy_error,sxy_budget,syz,syz_ref,syz_error,syz_budget,sxz,sxz_ref,sxz_error,sxz_budget,Ace_x,Ace_y,Ace_z,legacy_Arc\n";
    walls<<"native_id,sorted_slot,slipmode,B_x,B_z,normal_x,normal_z,physical_vx,physical_vy,physical_vz,legacy_rho,derivative_vx,derivative_vy,derivative_vz,derivative_vz_affine,derivative_vz_error,tangent_vx,tangent_vy,tangent_vz,tangent_vz_affine,tangent_vz_error,J,p_Pa,Ace_x,Ace_y,Ace_z,true_ax,true_ay,true_az\n";
    rates<<"native_id,theta,J,n,rate_Pa_s,local_compression_Pa_s,spatial_acceleration_remainder_Pa_s,Ace_x,Ace_y,Ace_z,true_ax,true_ay,true_az\n";cross<<"native_id,field,CPU_value,GPU_value,absolute_difference,comparison_is_descriptive\n";
    unsigned calls=0,nativeRows=0,wallRows=0,offRows=0;double maxThetaError=0,maxImageError=0,maxTangentError=0,maxAce=0,maxRate=0,rateSquare=0;std::array<double,14> crossMax{},crossSquare{};
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Need(Aceg&&Arg&&Rsigmag&&ViscDtg&&!BoundDerivativeVelg&&!Deltag&&!ShiftPosfsg&&!SpsGradvelg&&!NoPenShiftg,"Ordinary GPU observer scratch changed");
    try{
      {
        BorrowDerivative borrow(BoundDerivativeVelg,Np);const float nan=std::numeric_limits<float>::quiet_NaN();Up(BoundDerivativeVelg,std::vector<float3>(Np,make_float3(nan,nan,nan)));
        RestoreFlags restore{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,SoilStressRateGradCorr,PorosityFeedback,DynamicPorePressure,DynamicPoreWall,SoilStressRateGradCorr};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=SoilStressRateGradCorr=true;ConstantDataUp();
        ComputeFreeSurfaceTracking();Cu(cudaDeviceSynchronize());State a=Capture(true);const auto derivative=Down(BoundDerivativeVelg,Np);Need(GeometrySame(a,original)&&NpbOk==initialNpbOk,"GPU field refresh changed geometry");
        for(unsigned id=0;id<Fixed;id++){const unsigned q=map[id];if(q>=NpbOk){Need(a.mode[q]==original.mode[q],"Ignored wall mode changed");continue;}const auto dv=derivative[q];if(a.mode[q]==BMODE_MDBC2OFF){offRows++;Need(std::isnan(dv.x)&&std::isnan(dv.y)&&std::isnan(dv.z),"OFF derivative was populated");continue;}const auto v=a.vel[q];const auto t=a.tangent[q];Need(a.mode[q]==BMODE_MDBC2&&v.x==0&&v.y==0&&v.z==0&&v.w==RhopZero&&std::isfinite(dv.x)&&std::isfinite(dv.y)&&std::isfinite(dv.z)&&std::isfinite(t.x)&&std::isfinite(t.y)&&std::isfinite(t.z),"GPU physical wall/image invalid");wallRows++;}Need(wallRows==410&&offRows==55,"Closed GPU support classification changed");
        const auto beforeP=a.p;ApplyFreeSurfacePorePressure();ApplyHydroMechTopLoadAcceleration();Cu(cudaDeviceSynchronize());const State before=Capture(true);Need(Same(beforeP,before.p),"Unexpected no-drain projection");
        for(unsigned id=Fixed;id<Total;id++){const unsigned q=map[id];Need(EqualAt(before.vel,input.vel,q)&&EqualAt(before.sigma,input.sigma,q)&&EqualAt(before.j,input.j,q)&&EqualAt(before.p,input.p,q)&&EqualAt(before.p0,input.p0,q)&&EqualAt(before.plastic,input.plastic,q),"GPU closure changed native manufactured state");}
        // Literal production argument order, including the current-J and derivative pointers.
        const StInterParmsg parms=StrInterParmsg(Simulate2D,Symmetry,TKernel,FtMode,TVisco==VISCO_LaminarSPS,TDensity,ShiftingMode,TMdbc2,Visco*ViscoBoundFactor,Visco,BlockSizes.forcesbound,BlockSizes.forcesfluid,Np,Npb,NpbOk,0,Nstep,DivData,Dcellg,Posxyg,Poszg,PosCellg,Velrhopg,Idpg,Codeg,FtoMasspg,SpsTaug,NULL,CorrMatg,BoundModeg,BoundSlipModeg,TangenVelg,MotionVelg,BoundNormalg,NoPenShiftg,ViscDtg,Arg,Aceg,Deltag,SpsGradvelg,Sigmag,Rsigmag,ArtificialStressg,PorePressg,(DynamicPorePressure?NULL:PorePressRateg),FSTypeg,FSNormalg,IsHydroMechDrainageActive(),HydroMechLoadAceg,HydroMechTopLoadRawg,ShiftPosfsg,NULL,NULL,BoundDerivativeVelg,PoroThetag,PorosityFeedback?PoroJg:NULL);
        cusph::Interaction_Forces(parms);calls++;if(Simulate2D)cusph::Resety(Np-Npb,Npb,Aceg);Cu(cudaDeviceSynchronize());a=Capture(true);const auto sr=Down(Rsigmag,Np);const auto ar=Down(Arg,Np);const auto vd=Down(ViscDtg,Np);ViscDtMax=0;for(float value:vd){Need(std::isfinite(value)&&value>=0,"GPU viscosity scale invalid");ViscDtMax=(std::max)(ViscDtMax,value);}
        Need(GeometrySame(a,original)&&Same(a.vel,before.vel)&&Same(a.sigma,before.sigma)&&Same(a.p,before.p)&&Same(a.p0,before.p0)&&Same(a.rate,before.rate)&&Same(a.j,before.j)&&Same(a.c,before.c)&&Same(a.plastic,before.plastic),"GPU main ct changed persistent physical inputs");
        for(unsigned id=Fixed;id<Total;id++){
          const unsigned q=map[id];const auto s=sr[q];const auto ac=a.ace[q];const std::array<double,6> actual={s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};const double error=fabs(a.theta[q]-RateC);bool good=std::isfinite(a.theta[q])&&error<=derivativeBudget&&std::isfinite(ac.x)&&std::isfinite(ac.y)&&std::isfinite(ac.z)&&std::isfinite(ar[q]);
          kin<<id<<','<<q<<','<<a.xy[q].x<<','<<a.z[q]<<','<<a.vel[q].z<<','<<a.theta[q]<<','<<RateC<<','<<error<<','<<derivativeBudget;for(unsigned k=0;k<6;k++){const double e=fabs(actual[k]-reference[k]);kin<<','<<actual[k]<<','<<reference[k]<<','<<e<<','<<budget[k];good=good&&std::isfinite(actual[k])&&e<=budget[k];maxSigmaError[k]=(std::max)(maxSigmaError[k],e);}kin<<','<<ac.x<<','<<ac.y<<','<<ac.z<<','<<ar[q]<<'\n';if(!good)kin.flush();Need(good,"GPU affine derivative/stress-rate original CPU budget failed; preserve CSV");maxThetaError=(std::max)(maxThetaError,error);nativeRows++;
        }
        const State finished=a;ComputeDynamicPorePressureRateGpu(nullptr);Cu(cudaDeviceSynchronize());a=Capture(true);Need(GeometrySame(a,original)&&Same(a.vel,finished.vel)&&Same(a.sigma,finished.sigma)&&Same(a.p,finished.p)&&Same(a.p0,finished.p0)&&Same(a.j,finished.j)&&Same(a.c,finished.c)&&Same(a.theta,finished.theta)&&Same(a.mode,finished.mode)&&Same(a.tangent,finished.tangent)&&Same(a.fs,finished.fs)&&Same(a.fn,finished.fn)&&Same(a.posdiv,finished.posdiv)&&Same(a.plastic,finished.plastic)&&Same(a.load,finished.load),"GPU full rate changed frozen inputs");
        for(unsigned id=Fixed;id<Total;id++){
          const unsigned q=map[id];Need(EqualAt(a.ace,finished.ace,q),"GPU wall Ace/rate changed finished native acceleration");const auto ac=a.ace[q];const auto s=sr[q];const double n=1.-(1.-double(SoilCte.Porosity))/a.j[q],compression=-double(SoilCte.PoreWaterBulkModulus)/n*a.theta[q],r=a.rate[q];Need(std::isfinite(r),"Complete GPU rate nonfinite");rates<<id<<','<<a.theta[q]<<','<<a.j[q]<<','<<n<<','<<r<<','<<compression<<','<<r-compression<<','<<ac.x<<','<<ac.y<<','<<ac.z<<','<<double(ac.x)+Gravity.x<<','<<double(ac.y)+Gravity.y<<','<<double(ac.z)+Gravity.z<<'\n';maxRate=(std::max)(maxRate,fabs(r));rateSquare+=r*r;maxAce=(std::max)({maxAce,fabs(double(ac.x)),fabs(double(ac.y)),fabs(double(ac.z))});
          const auto& ref=cpu[id];Need(ref.x==a.xy[q].x&&ref.z==a.z[q]&&ref.vz==a.vel[q].z,"CPU/GPU manufactured ID-position-velocity differs");const std::array<double,14> values={a.theta[q],s.xx,s.yy,s.zz,s.xy,s.yz,s.xz,ac.x,ac.y,ac.z,ar[q],r,compression,r-compression};for(unsigned k=0;k<14;k++){const double delta=fabs(values[k]-ref.v[k]);crossMax[k]=(std::max)(crossMax[k],delta);crossSquare[k]+=delta*delta;cross<<id<<','<<CrossNames[k]<<','<<ref.v[k]<<','<<values[k]<<','<<delta<<",1\n";}
        }
        for(unsigned id=0;id<Fixed;id++){const unsigned q=map[id];if(q>=NpbOk||a.mode[q]!=BMODE_MDBC2)continue;const auto b=a.xy[q];const auto bn=a.bn[q];const auto dv=derivative[q];const auto tv=a.tangent[q];const auto ac=a.ace[q];const auto physical=a.vel[q];const auto mode=TpSlipMode(a.slip[q]);Need(mode==(id<255||id>=1800?SLIP_FreeSlip:SLIP_NoSlip),"Original per-MK GPU slip changed");const double image=RateC*a.z[q],tangent=(mode==SLIP_NoSlip?0.:image),ei=fabs(double(dv.z)-image),et=fabs(double(tv.z)-tangent);maxImageError=(std::max)(maxImageError,ei);maxTangentError=(std::max)(maxTangentError,et);walls<<id<<','<<q<<','<<unsigned(mode)<<','<<b.x<<','<<a.z[q]<<','<<bn.x<<','<<bn.z<<','<<physical.x<<','<<physical.y<<','<<physical.z<<','<<physical.w<<','<<dv.x<<','<<dv.y<<','<<dv.z<<','<<image<<','<<ei<<','<<tv.x<<','<<tv.y<<','<<tv.z<<','<<tangent<<','<<et<<','<<a.j[q]<<','<<a.p[q]<<','<<ac.x<<','<<ac.y<<','<<ac.z<<','<<double(ac.x)+Gravity.x<<','<<double(ac.y)+Gravity.y<<','<<double(ac.z)+Gravity.z<<'\n';}
        NoStep();borrow.Release(); // NULL is restored BEFORE cudaFree and ArraysGpu Pos cleanup.
      }
      ConstantDataUp(); // RAII restored private G1/feedback flags; restore actual CTE as well.
    }catch(...){ConstantDataUp();PosInteraction_Forces();RestorePersistent(original);InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVelMax;ViscDtMax=oldVisc;throw;}
    PosInteraction_Forces();RestorePersistent(original);Cu(cudaDeviceSynchronize());InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVelMax;ViscDtMax=oldVisc;
    Need(PersistentSame(Capture(false),original)&&NpbOk==initialNpbOk&&!BoundDerivativeVelg&&!Aceg&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!SoilStressRateGradCorr&&!memcmp(material.data(),&SoilCte,sizeof(SoilCte)),"GPU original arrays/flags/material/scratch not restored");Map(Capture(false));NoStep();Need(calls==1&&nativeRows==Soil&&wallRows==410&&offRows==55,"GPU actual main-ct coverage incomplete");for(auto* f:{&ledger,&kin,&walls,&rates,&cross}){f->flush();Need(bool(*f),"GPU force CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_gpu_force_r1\",\"passed\":true,\"native_ids\":7060,\"soil\":5000,\"active_walls\":410,\"OFF_in_prefix\":55,\"actual_main_ct_calls\":"<<calls<<",\"native_theta_checks\":5000,\"native_sigma_rate_checks\":30000,\"c_per_s\":"<<RateC<<",\"derivative_budget_per_s\":"<<derivativeBudget<<",\"max_theta_error_per_s\":"<<maxThetaError<<",\"sigma_reference_Pa_s\":[";for(unsigned k=0;k<6;k++)done<<(k?",":"")<<reference[k];done<<"],\"sigma_budget_Pa_s\":[";for(unsigned k=0;k<6;k++)done<<(k?",":"")<<budget[k];done<<"],\"max_sigma_error_Pa_s\":[";for(unsigned k=0;k<6;k++)done<<(k?",":"")<<maxSigmaError[k];done<<"],\"CPU_descriptor_max_abs\":[";for(unsigned k=0;k<14;k++)done<<(k?",":"")<<crossMax[k];done<<"],\"CPU_descriptor_RMS\":[";for(unsigned k=0;k<14;k++)done<<(k?",":"")<<sqrt(crossSquare[k]/Soil);done<<"],\"max_wall_image_error_m_s\":"<<maxImageError<<",\"max_wall_tangent_error_m_s\":"<<maxTangentError<<",\"max_native_Ace_component_m_s2\":"<<maxAce<<",\"complete_rate_absmax_Pa_s\":"<<maxRate<<",\"complete_rate_RMS_Pa_s\":"<<sqrt(rateSquare/Soil)<<",\"actual_finished_Ace_not_prescribed\":true,\"G1_uploaded_then_original_CTE_restored\":true,\"borrowed_derivative_NULL_before_free_Pos\":true,\"production_allocator_proved\":false,\"CPU_comparison_descriptive\":true,\"half_or_cross_5Pa_claimed\":false,\"isolated_AV_dissipation_claimed\":false,\"physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"GPU force completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=8&&std::string(argv[1])=="--force"&&std::string(argv[2])=="--cpu-dir","Use --force --cpu-dir ABS_CLOSED_CPU_FORCE_DIR -gpu:0 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_RESULT");const fs::path cpuDir=argv[3];AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(!cfg.Cpu&&cfg.GpuId==0&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh actualGPU0 stable zero-step output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),cpuDir);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU actual main-ct diagnostic failed; preserve output\n";return 2;}}
