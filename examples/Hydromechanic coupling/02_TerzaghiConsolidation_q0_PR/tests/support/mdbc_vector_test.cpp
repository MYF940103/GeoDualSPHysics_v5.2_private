// Fixed-plane manufactured fields: real production initialization, mDBC and ct.
// No copied neighbour/MLS algorithm and no time integration or physical acceptance.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
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

JAppInfo AppInfo("MdbcVectorCheck","v1","17-10-2026");
namespace fs=std::filesystem;
using Vec=std::array<double,3>;
using Mat=std::array<Vec,3>;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class T> static bool Same(const std::vector<T>& saved,const T* now){return !std::memcmp(saved.data(),now,saved.size()*sizeof(T));}
static Vec V(tdouble3 v){return{{v.x,v.y,v.z}};}
static Vec V(tfloat3 v){return{{v.x,v.y,v.z}};}
static tfloat3 F(Vec v){return TFloat3(float(v[0]),float(v[1]),float(v[2]));}
static double Dot(Vec a,Vec b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static Vec Mul(Mat a,Vec x){return{{Dot(a[0],x),Dot(a[1],x),Dot(a[2],x)}};}
static Mat Transpose(Mat a){Mat b{};for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)b[i][j]=a[j][i];return b;}
static std::array<double,6> Stress(tsymatrix3f s){return{{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz}};}

class MdbcVectorCheck:public JSphCpuSingle{
  unsigned Dimension,Mode,ExpectedN,ExpectedWall,ExpectedRoi;
  Mat Rotation,Inverse;
  Vec Normal;
  std::ofstream Rows,Consumers,PoreRows;
  double MaxAux=0,MaxAuxRelative=0,MaxAuxVector=0,MaxPore=0;
  Vec MaxConsumer{},MaxAnalytic{};
  unsigned WallRoi=0,SoilRoi=0,RProofCount=0,ForcedInactiveCount=0;
  bool Active(unsigned p)const{return p<NpbOk&&(Mode==1||(BoundModec&&BoundModec[p]==BMODE_MDBC2));}
  bool WallROI(unsigned p)const{
    const auto q=Mul(Inverse,V(Posc[p]));return fabs(q[0])<=.035+1e-9&&(Dimension==2||fabs(q[1])<=.035+1e-9);
  }
  bool SoilROI(unsigned p)const{
    const auto q=Mul(Inverse,V(Posc[p]));
    return CODE_IsFluid(Codec[p])&&fabs(q[0])<=.015+1e-9&&(Dimension==2||fabs(q[1])<=.015+1e-9)&&q[2]>0&&q[2]<=.025+1e-9;
  }
  Mat LocalGradient()const{
    Mat a{};a[2][2]=.4;
    if(Mode==2){a[0][2]=.3;if(Dimension==3)a[1][2]=.2;}
    if(Mode==3){a[0][0]=.2;if(Dimension==3){a[0][1]=.1;a[1][0]=-.15;a[1][1]=.3;}}
    return a;
  }
  Vec Field(Vec position,bool affine)const{
    Vec local{};
    if(!affine)local=(Mode==1?Vec{{0,0,.75}}:Vec{{.5,(Dimension==3?.25:0),.75}});
    else{
      local=Mul(LocalGradient(),Mul(Inverse,position));
      if(Mode==3){local[0]+=.5;if(Dimension==3)local[1]+=.25;}
    }
    return Mul(Rotation,local);
  }
  Vec Oracle(unsigned p,bool affine)const{
    if(!Active(p))return{{Velrhopc[p].x,Velrhopc[p].y,Velrhopc[p].z}};
    const Vec vg=Field(V(Posc[p]+ToTDouble3(BoundNormalc[p])),affine);
    const double vn=Dot(vg,Normal);Vec result{};
    for(unsigned j=0;j<3;j++)result[j]=(Mode==1?-vn*Normal[j]:(Mode==2?-vg[j]:vg[j]-2*vn*Normal[j]));
    return result;
  }
  void SetField(bool affine){
    for(unsigned p=0;p<Np;p++){
      const Vec vel=(CODE_IsFluid(Codec[p])?Field(V(Posc[p]),affine):Vec{});
      Velrhopc[p]=TFloat4(float(vel[0]),float(vel[1]),float(vel[2]),RhopZero);
      PorePress0c[p]=32.f+float(Idpc[p]%8);PorePressc[p]=64.f+float(Idpc[p]%11);
      Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
    }
    InterStep=INTERSTEP_SymPredictor;
    MdbcBoundCorrection(); // Real BoundMode/TangenVel initialization, never a forced active flag.
    PreInteraction_Forces();ComputeFreeSurfaceTracking();
  }
  void CheckAux(const char* name,bool affine){
    const std::vector<tfloat4> vel(Velrhopc,Velrhopc+Np);
    const std::vector<tdouble3> pos(Posc,Posc+Np);
    const std::vector<float> pore(PorePressc,PorePressc+Np),pore0(PorePress0c,PorePress0c+Np);
    const std::vector<unsigned> ids(Idpc,Idpc+Np);
    ComputeBoundaryDerivativeVelocity();
    Check(BoundDerivativeVelc&&Same(vel,Velrhopc)&&Same(pos,Posc)&&Same(pore,PorePressc)&&Same(pore0,PorePress0c)&&Same(ids,Idpc),"Vector reconstruction altered physical fields or native IDs");
    unsigned roi=0;
    for(unsigned p=0;p<Npb;p++){
      const Vec actual=V(BoundDerivativeVelc[p]),target=Oracle(p,affine);
      const bool use=WallROI(p);if(use){roi++;Check(Active(p),"ROI wall is inactive after actual mDBC correction");}
      double squared=0;
      for(unsigned j=0;j<3;j++){
        const double error=fabs(actual[j]-target[j]);squared+=error*error;
        const double tolerance=32.*FLT_EPSILON*(std::max)(.125,fabs(target[j]));
        const double relative=(fabs(target[j])>1e-12?error/fabs(target[j]):0);
        Rows<<name<<','<<Idpc[p]<<','<<use<<','<<Active(p)<<','<<j<<','<<actual[j]<<','<<target[j]<<','<<error<<','<<relative<<','<<tolerance<<'\n';
        Check(std::isfinite(actual[j]),"Nonfinite derivative velocity at a wall");
        if(use){
          Rows.flush();Check(error<=tolerance,"ROI vector reflection mismatch; see vector_rows.csv");
          MaxAux=(std::max)(MaxAux,error);MaxAuxRelative=(std::max)(MaxAuxRelative,relative);
        }
      }
      if(use)MaxAuxVector=(std::max)(MaxAuxVector,sqrt(squared));
    }
    Check(roi==ExpectedRoi,"Manufactured wall ROI count changed");WallRoi=roi;
  }
  void CheckForcedInactive(){
    if(Mode==1)return; // Vel0 intentionally ignores BoundMode.
    unsigned chosen=Npb;for(unsigned p=0;p<Npb;p++)if(WallROI(p)&&Active(p)){chosen=p;break;}
    Check(chosen<Npb&&BoundModec,"No active ROI wall for inactive-branch fixture");
    const std::vector<tfloat4> vel(Velrhopc,Velrhopc+Np);
    const std::vector<tdouble3> pos(Posc,Posc+Np);
    const std::vector<float> pore(PorePressc,PorePressc+Np),pore0(PorePress0c,PorePress0c+Np);
    const std::vector<tfloat3> aux(BoundDerivativeVelc,BoundDerivativeVelc+Npb);
    const std::vector<byte> modes(BoundModec,BoundModec+Npb);
    // Branch test only, not evidence about natural MLS support or physical activation.
    BoundModec[chosen]=BMODE_MDBC2OFF;ComputeBoundaryDerivativeVelocity();
    const tfloat3 expected=TFloat3(vel[chosen].x,vel[chosen].y,vel[chosen].z);
    Check(!memcmp(&expected,BoundDerivativeVelc+chosen,sizeof(tfloat3))&&BoundModec[chosen]==BMODE_MDBC2OFF,"Forced inactive wall did not retain physical-velocity fallback");
    Check(Same(vel,Velrhopc)&&Same(pos,Posc)&&Same(pore,PorePressc)&&Same(pore0,PorePress0c),"Inactive-branch reconstruction changed physical fields");
    BoundModec[chosen]=modes[chosen];ComputeBoundaryDerivativeVelocity();
    Check(Same(modes,BoundModec)&&Same(aux,BoundDerivativeVelc),"Inactive-branch trial did not restore modes/auxiliary values");
    ForcedInactiveCount++;
  }
  void ClearRates(){
    memset(Arc,0,Np*sizeof(float));memset(PorePressRatec,0,Np*sizeof(float));
    memset(Rsigmac,0,Np*sizeof(tsymatrix3f));memset(Acec,0,Np*sizeof(tfloat3));
  }
  void ActualInteraction(){
    const stinterparmsc parms=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
      PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,
      SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
    StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(parms,result);
  }
  void CheckConsumers(){
    // Identical actual ct for MLS/analytic auxiliary values. Zero prestress and
    // constant zero pressure eliminate objective-stress and Darcy contributions.
    for(unsigned p=0;p<Np;p++){Sigmac[p]=tsymatrix3d{};PorePressc[p]=PorePress0c[p]=0;}
    ClearRates();ActualInteraction();
    const std::vector<float> rMls(Arc,Arc+Np),pMls(PorePressRatec,PorePressRatec+Np);
    const std::vector<tsymatrix3f> sMls(Rsigmac,Rsigmac+Np);
    const std::vector<tfloat4> physical(Velrhopc,Velrhopc+Np);
    const std::vector<tfloat3> auxiliary(BoundDerivativeVelc,BoundDerivativeVelc+Npb);
    for(unsigned p=0;p<Npb;p++)BoundDerivativeVelc[p]=F(Oracle(p,true));
    ClearRates();ActualInteraction();
    const std::vector<float> rOracle(Arc,Arc+Np);
    const Mat local=LocalGradient();Mat global{};
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)for(unsigned k=0;k<3;k++)for(unsigned l=0;l<3;l++)
      global[i][j]+=Rotation[i][k]*local[k][l]*Rotation[j][l];
    const double div=global[0][0]+global[1][1]+global[2][2];
    const double shear=SoilCte.ModulusG,lambda=double(SoilCte.ModulusK)-2*shear/3.;
    const std::array<double,6> exact{{2*shear*global[0][0]+lambda*div,2*shear*global[1][1]+lambda*div,
      2*shear*global[2][2]+lambda*div,shear*(global[0][1]+global[1][0]),shear*(global[1][2]+global[2][1]),shear*(global[0][2]+global[2][0])}};
    const double pExact=-double(SoilCte.PoreWaterBulkModulus)/double(SoilCte.Porosity)*div;
    unsigned roi=0;
    for(unsigned p=Npb;p<Np;p++)if(SoilROI(p)){
      roi++;const auto sm=Stress(sMls[p]),so=Stress(Rsigmac[p]);
      for(unsigned j=0;j<8;j++){
        const unsigned group=(j<6?0:(j==6?1:2));
        const double m=(j<6?sm[j]:(j==6?pMls[p]:rMls[p]));
        const double o=(j<6?so[j]:(j==6?PorePressRatec[p]:Arc[p]));
        const double e=(j<6?exact[j]:(j==6?pExact:-double(Velrhopc[p].w)*div));
        const double floor=(group==0?20.:(group==1?2000.:.02));
        const double diff=fabs(m-o),bias=fabs(m-e);
        Consumers<<Idpc[p]<<','<<j<<','<<m<<','<<o<<','<<e<<','<<diff<<','<<bias<<','<<floor+2e-5*fabs(o)<<'\n';
        Consumers.flush();Check(std::isfinite(m)&&std::isfinite(o),"Nonfinite production consumer output");
        Check(diff<=floor+2e-5*fabs(o),"MLS versus oracle production consumer comparison failed");
        if(group<2)Check(bias<=floor+2e-5*fabs(e),"Corrected S/P affine analytic comparison failed");
        MaxConsumer[group]=(std::max)(MaxConsumer[group],diff);MaxAnalytic[group]=(std::max)(MaxAnalytic[group],bias);
      }
    }
    Check(roi==(Dimension==2?12u:48u),"Near-wall soil ROI count changed");SoilRoi=roi;
    // R wiring proof uses the SAME production ct, not a second discrete formula.
    // Auxiliary xyz is temporarily copied into public wall xyz, then the aux
    // pointer is null. Only density rates are compared; S/P/viscosity are not.
    tfloat3* originalAux=BoundDerivativeVelc;
    for(unsigned p=0;p<Npb;p++){
      Velrhopc[p].x=originalAux[p].x;Velrhopc[p].y=originalAux[p].y;Velrhopc[p].z=originalAux[p].z;
    }
    BoundDerivativeVelc=NULL;
    try{ClearRates();ActualInteraction();}
    catch(...){std::copy(physical.begin(),physical.end(),Velrhopc);BoundDerivativeVelc=originalAux;throw;}
    std::copy(physical.begin(),physical.end(),Velrhopc);BoundDerivativeVelc=originalAux;
    Check(Same(physical,Velrhopc),"R wiring reference did not restore physical velocity");
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Check(!memcmp(&rOracle[p],Arc+p,sizeof(float)),"R auxiliary/public-wall reference is not 0 ULP");RProofCount++;
    }
    Check(RProofCount==ExpectedN,"R wiring proof missed native particles");
    std::copy(auxiliary.begin(),auxiliary.end(),BoundDerivativeVelc);
  }
  void CheckPoreScalar(){
    SetField(true);ComputeBoundaryDerivativeVelocity();
    for(unsigned p=0;p<Np;p++){
      PorePress0c[p]=32.f+float(Idpc[p]%8);
      PorePressc[p]=(CODE_IsFluid(Codec[p])?float(double(PorePress0c[p])+64+3*Posc[p].x-2*Posc[p].y+Posc[p].z):-321.f);
    }
    const std::vector<tfloat4> vel(Velrhopc,Velrhopc+Np);
    const std::vector<tfloat3> aux(BoundDerivativeVelc,BoundDerivativeVelc+Npb);
    const std::vector<float> pressure(PorePressc,PorePressc+Np),pore0(PorePress0c,PorePress0c+Np);
    InteractionPorePressureMdbcCorrection();
    Check(Same(vel,Velrhopc)&&Same(aux,BoundDerivativeVelc)&&Same(pore0,PorePress0c),"Scalar pore reconstruction altered velocity/auxiliary/reference pressure");
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p]))Check(!memcmp(&pressure[p],PorePressc+p,sizeof(float)),"Scalar reconstruction altered soil pressure");
    unsigned roi=0;
    for(unsigned p=0;p<Npb;p++)if(WallROI(p)){
      roi++;const auto g=Posc[p]+ToTDouble3(BoundNormalc[p]);
      const double exact=double(PorePress0c[p])+64+3*g.x-2*g.y+g.z,error=fabs(double(PorePressc[p])-exact);
      const double tolerance=32.*FLT_EPSILON*(std::max)(1.,fabs(exact));
      PoreRows<<Idpc[p]<<','<<PorePressc[p]<<','<<exact<<','<<error<<','<<tolerance<<'\n';PoreRows.flush();
      Check(std::isfinite(PorePressc[p])&&error<=tolerance,"Scalar pore affine reproduction failed");MaxPore=(std::max)(MaxPore,error);
    }
    Check(roi==ExpectedRoi,"Scalar pore ROI coverage changed");PosInteraction_Forces();
  }
public:
  MdbcVectorCheck(unsigned dim,unsigned mode,unsigned n,unsigned wall,unsigned roi,Mat rotation):
    Dimension(dim),Mode(mode),ExpectedN(n),ExpectedWall(wall),ExpectedRoi(roi),Rotation(rotation),Inverse(Transpose(rotation)),Normal{{rotation[0][2],rotation[1][2],rotation[2][2]}}{}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(HydroMech&&SoilBoundaryDerivativeSPR&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&!PartBegin&&TimeStep==0,"Unexpected production configuration");
    Check(Simulate2D==(Dimension==2)&&unsigned(SlipMode)==Mode&&!PeriActive&&Np==ExpectedN&&Npb==ExpectedWall,"Geometry/mode/native count disagrees with prepared manifest");
    Check(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!SoilDamping&&!Shifting&&TDensity==DDT_None&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None,"Fixture must isolate fixed-wall derivatives");
    std::set<unsigned> ids;for(unsigned p=0;p<Np;p++)Check(CODE_IsNormal(Codec[p])&&ids.insert(Idpc[p]).second,"Unexpected native IDs/duplicates");
    Check(ids.size()==ExpectedN&&*ids.begin()==0&&*ids.rbegin()==ExpectedN-1,"Native ID range changed");
    // Check actual rotated particles, not only descriptor/normal agreement.
    // GenCase rotateaxis sign errors must fail before any field experiment.
    std::set<std::array<int,3>> grid;
    for(unsigned p=0;p<Np;p++){
      const auto q=Mul(Inverse,V(Posc[p]));std::array<int,3> index{};
      for(unsigned j=0;j<3;j++){
        const double first=(j<2?-.075:(p<Npb?-.025:.005));
        const unsigned count=(j<2?16u:(p<Npb?3u:10u));
        if(j==1&&Dimension==2){Check(fabs(q[j])<=1e-7,"2-D particle left the local y=0 plane");index[j]=0;continue;}
        index[j]=int(std::lround((q[j]-first)/.01));
        Check(index[j]>=0&&unsigned(index[j])<count&&fabs(q[j]-(first+.01*index[j]))<=1e-7,"Actual native grid disagrees with manifest rotation");
      }
      if(p>=Npb)index[2]+=3;
      Check(grid.insert(index).second,"Duplicate local-grid native particle");
    }
    Check(grid.size()==ExpectedN,"Prepared local grid is incomplete");
    for(unsigned p=0;p<Npb;p++){
      const double r=Dot(V(Posc[p]),Normal);const Vec displacement=V(BoundNormalc[p]);
      Check(r<0&&CODE_IsFixed(Codec[p]),"Prepared wall is not on the negative side of the fixed plane");
      for(unsigned j=0;j<3;j++)Check(fabs(displacement[j]+2*r*Normal[j])<=64*FLT_EPSILON*.05,"Production plane normal/rotation disagrees with manifest");
    }
    const fs::path out(cfg->DirOut);Rows.open(out/"vector_rows.csv");Consumers.open(out/"consumer_rows.csv");PoreRows.open(out/"pore_rows.csv");
    Rows<<std::setprecision(17)<<"trial,id,roi,active,component,actual,expected,error,relative_nonzero_error,tolerance\n";
    Consumers<<std::setprecision(17)<<"id,component_0to5_sigma_6_pore_7_rho,mls,oracle,analytic,mls_oracle_error,analytic_error,comparison_tolerance\n";
    PoreRows<<std::setprecision(17)<<"id,actual,expected,error,tolerance\n";
    SetField(false);CheckAux("constant_projection_only",false);PosInteraction_Forces();
    SetField(true);CheckAux("bc_compatible_affine",true);CheckForcedInactive();CheckConsumers();PosInteraction_Forces();
    CheckPoreScalar();
    std::ofstream done(out/"vector_complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"dimension\":"<<Dimension<<",\"slip_mode\":"<<Mode<<",\"native_count\":"<<Np
      <<",\"wall_count\":"<<Npb<<",\"wall_roi_count\":"<<WallRoi<<",\"soil_roi_count\":"<<SoilRoi
      <<",\"max_velocity_abs_error\":"<<MaxAux<<",\"max_velocity_relative_nonzero_error\":"<<MaxAuxRelative<<",\"max_velocity_vector_error\":"<<MaxAuxVector
      <<",\"max_pore_scalar_error_Pa\":"<<MaxPore<<",\"consumer_mls_oracle_max\":["<<MaxConsumer[0]<<','<<MaxConsumer[1]<<','<<MaxConsumer[2]
      <<"],\"consumer_analytic_max\":["<<MaxAnalytic[0]<<','<<MaxAnalytic[1]<<','<<MaxAnalytic[2]<<"]"
      <<",\"r_wiring_0ulp_native_count\":"<<RProofCount<<",\"r_reference_physical_velocity_restored\":true"
      <<",\"actual_rotated_native_grid_verified\":true,\"local_grid_tolerance_m\":1e-7"
      <<",\"forced_inactive_branch_trials\":"<<ForcedInactiveCount<<",\"forced_inactive_is_not_physical_activation_test\":true,\"no_support_fallback_not_instrumented\":true"
      <<",\"vector_tolerance\":\"32*FLT_EPSILON*max(.125,abs(expected_component))\""
      <<",\"consumer_tolerance\":\"S:20 Pa/s, P:2000 Pa/s, R:.02 kg/m3/s plus 2e-5*abs(reference)\""
      <<",\"raw_density_analytic_error_is_not_an_acceptance_gate\":true,\"constant_projection_is_not_bc_compatible_flow\":true"
      <<",\"r_public_wall_reference_is_fixture_only\":true,\"copied_mls_or_neighbor_formula\":false,\"time_integrated\":false,\"physical_acceptance\":false}\n";
    done.flush();Rows.flush();Consumers.flush();PoreRows.flush();Check(bool(done)&&bool(Rows)&&bool(Consumers)&&bool(PoreRows),"Manufactured-field output write failed");
    std::cout<<"PASS vector dim="<<Dimension<<" slip="<<Mode<<" native="<<Np<<'\n';
  }
};

int main(int argc,char** argv){
  try{
    Check(argc>=18,"Usage: vector DIM SLIP NP NWALL NROI R00..R22 then ordinary solver arguments");
    const unsigned dim=std::stoul(argv[1]),mode=std::stoul(argv[2]),np=std::stoul(argv[3]),nw=std::stoul(argv[4]),roi=std::stoul(argv[5]);
    Check((dim==2||dim==3)&&mode>=1&&mode<=3,"Invalid manufactured-field dimension/slip");
    Mat rotation{};for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)rotation[i][j]=std::stod(argv[6+i*3+j]);
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)Check(fabs(Dot(rotation[i],rotation[j])-(i==j?1.:0.))<1e-12,"Manifest rotation is not orthogonal");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> arguments{argv[0]};for(int i=15;i<argc;i++)arguments.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(arguments.size()),arguments.data());cfg.Cpu=true;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Output exists; choose a new label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    MdbcVectorCheck fixture(dim,mode,np,nw,roi,rotation);fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}
