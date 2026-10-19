// Real GPU initialization, mDBC, vector MLS and S/P/R consumers; no integration.
#include "JSphGpuSingle.h"
#include "JSphGpu_ker.h"
#include "JSphCfgRun.h"
#include "JDsTimersGpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("MdbcGpuVectorCheck","v1","18-10-2026");
using Vec=std::array<double,3>;
using Mat=std::array<Vec,3>;
static void Check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static void Cu(cudaError_t e){Check(e==cudaSuccess,cudaGetErrorString(e));}
template<class T> static std::vector<T> Down(const T* p,unsigned n){std::vector<T> v(n);Cu(cudaMemcpy(v.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return v;}
template<class T> static void Up(T* p,const std::vector<T>& v){Cu(cudaMemcpy(p,v.data(),v.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T> static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&!memcmp(a.data(),b.data(),a.size()*sizeof(T));}
static double Dot(Vec a,Vec b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static Vec Mul(Mat a,Vec x){return {{Dot(a[0],x),Dot(a[1],x),Dot(a[2],x)}};}
static Mat Transpose(Mat a){Mat b{};for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)b[i][j]=a[j][i];return b;}
static float3 F(Vec a){return make_float3(float(a[0]),float(a[1]),float(a[2]));}

class MdbcGpuVectorCheck:public JSphGpuSingle{
  unsigned Dim,Mode,ExpectedN,ExpectedWall,ExpectedRoi;
  Mat Rotation,Inverse;Vec Normal;
  std::vector<Vec> Position;
  std::vector<unsigned> Id;
  std::vector<typecode> Codes;
  std::vector<float3> Normals;
  std::vector<byte> Modes;
  std::ofstream Rows,Consumers;
  double MaxAux=0;std::array<double,3> MaxConsumer{},MaxAnalytic{};
  unsigned WallRoi=0,SoilRoi=0,RProof=0;
  bool Active(unsigned p)const{return p<NpbOk&&(Mode==1||(Modes.size()&&Modes[p]==BMODE_MDBC2));}
  bool WallROI(unsigned p)const{const auto q=Mul(Inverse,Position[p]);return fabs(q[0])<=.035+1e-9&&(Dim==2||fabs(q[1])<=.035+1e-9);}
  bool SoilROI(unsigned p)const{const auto q=Mul(Inverse,Position[p]);return CODE_IsFluid(Codes[p])&&fabs(q[0])<=.015+1e-9&&(Dim==2||fabs(q[1])<=.015+1e-9)&&q[2]>0&&q[2]<=.025+1e-9;}
  Mat LocalGradient()const{
    Mat a{};a[2][2]=.4;
    if(Mode==2){a[0][2]=.3;if(Dim==3)a[1][2]=.2;}
    if(Mode==3){a[0][0]=.2;if(Dim==3){a[0][1]=.1;a[1][0]=-.15;a[1][1]=.3;}}
    return a;
  }
  Vec Field(Vec position,bool affine)const{
    Vec local{};
    if(!affine)local=(Mode==1?Vec{{0,0,.75}}:Vec{{.5,(Dim==3?.25:0),.75}});
    else{local=Mul(LocalGradient(),Mul(Inverse,position));if(Mode==3){local[0]+=.5;if(Dim==3)local[1]+=.25;}}
    return Mul(Rotation,local);
  }
  Vec Oracle(unsigned p,bool affine,const std::vector<float4>& physical)const{
    const auto w=physical[p];if(!Active(p))return {{w.x,w.y,w.z}};
    Vec gp=Position[p];gp[0]+=Normals[p].x;gp[1]+=Normals[p].y;gp[2]+=Normals[p].z;
    const Vec v=Field(gp,affine);const double vn=Dot(v,Normal);Vec out{};
    for(unsigned j=0;j<3;j++)out[j]=(Mode==1?-vn*Normal[j]:(Mode==2?-v[j]:v[j]-2*vn*Normal[j]));
    return out;
  }
  void SetField(bool affine){
    std::vector<float4> v(Np);std::vector<float> pressure(Np),p0(Np);
    for(unsigned p=0;p<Np;p++){
      const auto q=(CODE_IsFluid(Codes[p])?Field(Position[p],affine):Vec{});
      v[p]=make_float4(float(q[0]),float(q[1]),float(q[2]),RhopZero);
      p0[p]=32.f+float(Id[p]%8);pressure[p]=64.f+float(Id[p]%11);
    }
    Up(Velrhopg,v);Up(PorePressg,pressure);Up(PorePress0g,p0);
    Cu(cudaMemset(Sigmag,0,Np*sizeof(tsymatrix3d)));Cu(cudaMemset(Kplasticg,0,Np*sizeof(float)));
    InterStep=INTERSTEP_SymPredictor;MdbcBoundCorrection();PreInteraction_Forces();ComputeFreeSurfaceTracking();
    if(BoundModeg)Modes=Down(BoundModeg,Np);
  }
  void CheckAux(bool affine){
    const auto physical=Down(Velrhopg,Np);const auto pressure=Down(PorePressg,Np),p0=Down(PorePress0g,Np);
    ComputeBoundaryDerivativeVelocity();const auto aux=Down(BoundDerivativeVelg,Npb);
    Check(Same(physical,Down(Velrhopg,Np))&&Same(pressure,Down(PorePressg,Np))&&Same(p0,Down(PorePress0g,Np)),"GPU MLS changed physical fields");
    unsigned count=0;
    for(unsigned p=0;p<Npb;p++){
      const auto target=Oracle(p,affine,physical);const Vec actual{{aux[p].x,aux[p].y,aux[p].z}};
      if(WallROI(p)){count++;Check(Active(p),"Actual mDBC left ROI wall inactive");}
      for(unsigned j=0;j<3;j++){
        const double error=fabs(actual[j]-target[j]),tol=32.*FLT_EPSILON*(std::max)(.125,fabs(target[j]));
        Rows<<(affine?"affine":"constant")<<','<<Id[p]<<','<<WallROI(p)<<','<<j<<','<<actual[j]<<','<<target[j]<<','<<error<<','<<tol<<'\n';
        Check(std::isfinite(actual[j]),"Nonfinite GPU auxiliary velocity");
        if(WallROI(p)){Rows.flush();Check(error<=tol,"GPU vector MLS exceeds CPU manufactured-field tolerance");MaxAux=(std::max)(MaxAux,error);}
      }
    }
    Check(count==ExpectedRoi,"Wall ROI population changed");WallRoi=count;
    // Explicit inactive and no-supported-fluid fallbacks, then exact restoration.
    if(affine){
      if(Mode>=2){
        auto modes=Modes;unsigned p=0;while(p<Npb&&!WallROI(p))p++;Check(p<Npb,"No inactive test point");
        modes[p]=BMODE_MDBC2OFF;Up(BoundModeg,modes);ComputeBoundaryDerivativeVelocity();const auto inactive=Down(BoundDerivativeVelg,Npb);
        const float3 expected=make_float3(physical[p].x,physical[p].y,physical[p].z);
        Check(!memcmp(&inactive[p],&expected,sizeof(float3)),"Inactive wall fallback changed");Up(BoundModeg,Modes);
      }
      auto unsupported=physical;for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codes[p]))unsupported[p].w=0;
      Up(Velrhopg,unsupported);ComputeBoundaryDerivativeVelocity();const auto fallback=Down(BoundDerivativeVelg,Npb);
      for(unsigned p=0;p<Npb;p++){
        auto expected=make_float3(physical[p].x,physical[p].y,physical[p].z);
        if(Mode==1&&Normals[p].x==0&&Normals[p].y==0)expected.z=-expected.z;
        Check(!memcmp(&fallback[p],&expected,sizeof(float3)),"Unsupported wall fallback changed");
      }
      Up(Velrhopg,physical);ComputeBoundaryDerivativeVelocity();Check(Same(aux,Down(BoundDerivativeVelg,Npb)),"Fallback test did not restore exact auxiliary state");
    }
  }
  void ClearRates(){
    Cu(cudaMemset(Arg,0,Np*sizeof(float)));Cu(cudaMemset(PorePressRateg,0,Np*sizeof(float)));
    Cu(cudaMemset(Rsigmag,0,Np*sizeof(tsymatrix3f)));Cu(cudaMemset(Aceg,0,Np*sizeof(float3)));Cu(cudaMemset(ViscDtg,0,Np*sizeof(float)));
  }
  void ActualInteraction(){
    const StInterParmsg p=StrInterParmsg(Simulate2D,false,TKernel,FtMode,false,TDensity,ShiftingMode,TMdbc2,
      Visco*ViscoBoundFactor,Visco,BlockSizes.forcesbound,BlockSizes.forcesfluid,Np,Npb,NpbOk,0,Nstep,DivData,Dcellg,
      Posxyg,Poszg,PosCellg,Velrhopg,Idpg,Codeg,FtoMasspg,SpsTaug,NULL,CorrMatg,BoundModeg,BoundSlipModeg,TangenVelg,
      MotionVelg,BoundNormalg,NoPenShiftg,ViscDtg,Arg,Aceg,Deltag,SpsGradvelg,Sigmag,Rsigmag,ArtificialStressg,
      PorePressg,PorePressRateg,FSTypeg,FSNormalg,false,HydroMechLoadAceg,HydroMechTopLoadRawg,ShiftPosfsg,NULL,NULL,BoundDerivativeVelg);
    cusph::Interaction_Forces(p);Cu(cudaDeviceSynchronize());
  }
  void CheckConsumers(){
    Cu(cudaMemset(PorePressg,0,Np*sizeof(float)));Cu(cudaMemset(PorePress0g,0,Np*sizeof(float)));
    ClearRates();ActualInteraction();const auto rm=Down(Arg,Np),pm=Down(PorePressRateg,Np);const auto sm=Down(Rsigmag,Np);
    const auto physical=Down(Velrhopg,Np);const auto aux=Down(BoundDerivativeVelg,Npb);
    std::vector<float3> oracle(Npb);for(unsigned p=0;p<Npb;p++)oracle[p]=F(Oracle(p,true,physical));Up(BoundDerivativeVelg,oracle);
    ClearRates();ActualInteraction();const auto ro=Down(Arg,Np),po=Down(PorePressRateg,Np);const auto so=Down(Rsigmag,Np);
    const Mat local=LocalGradient();Mat global{};
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)for(unsigned k=0;k<3;k++)for(unsigned l=0;l<3;l++)global[i][j]+=Rotation[i][k]*local[k][l]*Rotation[j][l];
    const double div=global[0][0]+global[1][1]+global[2][2],g=SoilCte.ModulusG,lambda=double(SoilCte.ModulusK)-2*g/3.;
    const std::array<double,6> exact{{2*g*global[0][0]+lambda*div,2*g*global[1][1]+lambda*div,2*g*global[2][2]+lambda*div,
      g*(global[0][1]+global[1][0]),g*(global[1][2]+global[2][1]),g*(global[0][2]+global[2][0])}};
    const double pexact=-double(SoilCte.PoreWaterBulkModulus)/double(SoilCte.Porosity)*div;
    for(unsigned p=0;p<Np;p++){
      // Check density wiring for all native particles, including walls.
      Check(std::isfinite(rm[p])&&fabs(double(rm[p])-ro[p])<=.02+2e-5*fabs(double(ro[p])),"All-native density MLS/oracle mismatch");
      if(!SoilROI(p))continue;SoilRoi++;
      const std::array<double,6> a{{sm[p].xx,sm[p].yy,sm[p].zz,sm[p].xy,sm[p].yz,sm[p].xz}},b{{so[p].xx,so[p].yy,so[p].zz,so[p].xy,so[p].yz,so[p].xz}};
      for(unsigned j=0;j<8;j++){
        const unsigned group=(j<6?0:(j==6?1:2));const double m=(j<6?a[j]:(j==6?pm[p]:rm[p])),o=(j<6?b[j]:(j==6?po[p]:ro[p]));
        const double e=(j<6?exact[j]:(j==6?pexact:-double(physical[p].w)*div)),floor=(group==0?20.:(group==1?2000.:.02));
        const double diff=fabs(m-o),bias=fabs(m-e);
        Consumers<<Id[p]<<','<<j<<','<<m<<','<<o<<','<<e<<','<<diff<<','<<bias<<'\n';Consumers.flush();
        Check(std::isfinite(m)&&diff<=floor+2e-5*fabs(o),"GPU actual S/P/R consumer MLS/oracle mismatch");
        if(group<2)Check(bias<=floor+2e-5*fabs(e),"GPU corrected affine S/P analytic mismatch");
        MaxConsumer[group]=(std::max)(MaxConsumer[group],diff);MaxAnalytic[group]=(std::max)(MaxAnalytic[group],bias);
      }
    }
    Check(SoilRoi==(Dim==2?12u:48u),"Soil ROI population changed");
    // Soil R: replace physical wall xyz by the oracle, then remove auxiliary pointer.
    auto publicwall=physical;for(unsigned p=0;p<Npb;p++){publicwall[p].x=oracle[p].x;publicwall[p].y=oracle[p].y;publicwall[p].z=oracle[p].z;}
    Up(Velrhopg,publicwall);auto saved=BoundDerivativeVelg;BoundDerivativeVelg=NULL;
    ClearRates();ActualInteraction();const auto reference=Down(Arg,Np);BoundDerivativeVelg=saved;Up(Velrhopg,physical);
    for(unsigned p=Npb;p<Np;p++){Check(!memcmp(&ro[p],&reference[p],sizeof(float)),"Soil R public-wall wiring is not 0 ULP");RProof++;}
    Up(BoundDerivativeVelg,aux);Check(Same(physical,Down(Velrhopg,Np)),"Physical velocity restoration failed");
  }
public:
  MdbcGpuVectorCheck(unsigned d,unsigned m,unsigned n,unsigned w,unsigned roi,Mat rot):Dim(d),Mode(m),ExpectedN(n),ExpectedWall(w),ExpectedRoi(roi),Rotation(rot),Inverse(Transpose(rot)),Normal{{rot[0][2],rot[1][2],rot[2][2]}}{}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();
    Check(HydroMech&&SoilBoundaryDerivativeSPR&&!HourglassGpu&&!SoilDamping&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None,"Fixture isolation failed");
    Check(Np==ExpectedN&&Npb==ExpectedWall&&Simulate2D==(Dim==2)&&unsigned(SlipMode)==Mode&&!PeriActive,"Prepared geometry/mode mismatch");
    Id=Down(Idpg,Np);Codes=Down(Codeg,Np);Normals=Down(BoundNormalg,Np);const auto xy=Down(Posxyg,Np);const auto z=Down(Poszg,Np);
    Position.resize(Np);std::set<unsigned> ids;
    for(unsigned p=0;p<Np;p++){Check(CODE_IsNormal(Codes[p])&&ids.insert(Id[p]).second,"Invalid native IDs");Position[p]={{xy[p].x,xy[p].y,z[p]}};}
    Check(*ids.begin()==0&&*ids.rbegin()==Np-1,"Native range mismatch");
    for(unsigned p=0;p<Npb;p++){
      const double r=Dot(Position[p],Normal);Check(r<0&&CODE_IsFixed(Codes[p]),"Wall orientation mismatch");
      const Vec bn{{Normals[p].x,Normals[p].y,Normals[p].z}};
      for(unsigned j=0;j<3;j++)Check(fabs(bn[j]+2*r*Normal[j])<=64*FLT_EPSILON*.05,"Actual normal disagrees with manifest rotation");
    }
    const std::filesystem::path out(cfg->DirOut);Rows.open(out/"vector_rows.csv");Consumers.open(out/"consumer_rows.csv");
    Rows<<std::setprecision(17)<<"trial,id,roi,component,actual,expected,error,tolerance\n";
    Consumers<<std::setprecision(17)<<"id,component,mls,oracle,analytic,difference,bias\n";
    SetField(false);CheckAux(false);PosInteraction_Forces();SetField(true);CheckAux(true);CheckConsumers();PosInteraction_Forces();
    std::ofstream done(out/"vector_complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"dimension\":"<<Dim<<",\"slip_mode\":"<<Mode
      <<",\"native_count\":"<<Np<<",\"wall_count\":"<<Npb<<",\"wall_roi_count\":"<<WallRoi<<",\"soil_roi_count\":"<<SoilRoi
      <<",\"max_aux_error\":"<<MaxAux<<",\"consumer_mls_oracle_max\":["<<MaxConsumer[0]<<','<<MaxConsumer[1]<<','<<MaxConsumer[2]
      <<"],\"consumer_analytic_max\":["<<MaxAnalytic[0]<<','<<MaxAnalytic[1]<<','<<MaxAnalytic[2]<<"],\"soil_r_0ulp_count\":"<<RProof
      <<",\"all_native_density_mls_oracle_checked\":true,\"inactive_and_no_support_fallbacks_checked\":true,\"physical_acceptance\":false,\"time_integrated\":false}\n";
    done.flush();Rows.flush();Consumers.flush();Check(bool(done)&&bool(Rows)&&bool(Consumers),"Fixture output failed");
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>=18,"Usage: DIM SLIP NP NWALL NROI R00..R22 then solver arguments");
    const unsigned d=std::stoul(argv[1]),m=std::stoul(argv[2]),n=std::stoul(argv[3]),w=std::stoul(argv[4]),roi=std::stoul(argv[5]);
    Mat rotation{};for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)rotation[i][j]=std::stod(argv[6+3*i+j]);
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=15;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());cfg.Cpu=false;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!std::filesystem::exists(cfg.DirOut),"Fixture output exists");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    MdbcGpuVectorCheck fixture(d,m,n,w,roi,rotation);fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
