// Private zero-step normal-gravity wall manufacture; no public guard is removed.
// Init uses the retained zero-g parallel FreeSlip seed, then assigns manufactured g.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
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
JAppInfo AppInfo("GravityWallCpuComponent","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static constexpr unsigned Native=1024,Fixed=256;
static constexpr double Dp0=1./512.,Width=1./16.,Lz=1./16.,Head=128.;
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double Norm(tdouble3 a){return sqrt(Dot(a,a));}
static tdouble3 Product(tmatrix3d c,tdouble3 a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
static double MatrixNorm(tmatrix3d a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});}
using Row=std::array<double,18>;
template<class T>struct Copy{
  T* p;std::vector<T> v;
  Copy(T* a,unsigned n):p(a){Need(a||!n,"Missing component array");if(n)v.assign(a,a+n);}
  void Restore()const{if(!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}
  bool Equal()const{return v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}
};
class Wall:public JSphCpuSingle{
  std::vector<unsigned> Soil,Bound;
  unsigned Cases=0,WallRows=0,FaceRows=0,RateRows=0;
  double MaxStateRatio=0,MaxFluxRatio=0,MaxRateRatio=0,MinMissingHeadRatio=DBL_MAX,MinWrongAceRatio=DBL_MAX;
  struct Moment{tmatrix3d inverse;double condition;};
  struct Face{double p;tdouble3 grad,a;double condition,limit,qn;};
  struct Rate{double value,limit,gpnormal;};
  std::vector<unsigned> Map()const{
    std::vector<unsigned> m(CaseNp,UINT_MAX);unsigned soil=0,bound=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Need(Idpc[p]<CaseNp&&m[Idpc[p]]==UINT_MAX,"Duplicate/unknown native ID");m[Idpc[p]]=p;
      if(CODE_IsFluid(Codec[p]))soil++;else{Need(CODE_IsFixed(Codec[p]),"Nonfixed boundary");bound++;}
    }
    Need(soil==Native&&bound==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native/exclusion mismatch");return m;
  }
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec,"Component advanced time or retained predictor J");}
  double Wab(double rr)const{return TKernel==KERNEL_Cubic? fsph::GetKernel_Wab<KERNEL_Cubic>(CSP,float(rr)):fsph::GetKernel_Wab<KERNEL_Wendland>(CSP,float(rr));}
  double Fac(double rr)const{return TKernel==KERNEL_Cubic? fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr)):fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));}
  bool Sample(unsigned p,bool walls)const{return CODE_IsFluid(Codec[p])||(walls&&p<Npb&&CODE_IsFixed(Codec[p])&&BoundModec[p]==BMODE_MDBC2);}
  Moment FitMoment(tdouble3 at,bool walls)const{
    tmatrix3d m=TMatrix3d(0);
    for(unsigned p=0;p<Np;p++)if(Sample(p,walls)){
      const auto d=Posc[p]-at;const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2))continue;
      const double w=double(MassFluid)/RhopZero*PoroJc[p]*Wab(rr),x=d.x/KernelH,z=d.z/KernelH;
      m.a11+=w;m.a12+=w*x;m.a13+=w*z;m.a21+=w*x;m.a22+=w*x*x;m.a23+=w*x*z;m.a31+=w*z;m.a32+=w*x*z;m.a33+=w*z*z;
    }
    const double det=fmath::Determinant3x3(m);Need(std::isfinite(det)&&det>0,"Independent physical-face/target support singular");
    const auto inv=fmath::InverseMatrix3x3(m,det);return {inv,(std::max)(1.,MatrixNorm(m)*MatrixNorm(inv))};
  }
  Face PhysicalFace(tdouble3 at,double inward,unsigned negative)const{
    const auto fit=FitMoment(at,true);tdouble3 bp=TDouble3(0),ba[3]={TDouble3(0),TDouble3(0),TDouble3(0)};
    for(unsigned p=0;p<Np;p++)if(Sample(p,true)){
      const auto d=Posc[p]-at;const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2))continue;
      const double w=double(MassFluid)/RhopZero*PoroJc[p]*Wab(rr);const auto basis=TDouble3(1,d.x/KernelH,d.z/KernelH);
      double pressure=PorePressc[p];auto a=ToTDouble3(Acec[p]);
      if(p<Npb&&CODE_IsFixed(Codec[p])){
        if(negative==1)pressure=float(Head+double(SoilCte.PoreWaterRho)*Dot(ToTDouble3(Gravity),Posc[p]+ToTDouble3(BoundNormalc[p]))); // Old even-p image, without the hydrostatic head shift.
        if(negative==2)a.x=-a.x; // Incorrect Q*Ace instead of Q*(Ace+g)-g at these x-normal walls.
      }
      bp=bp+basis*(w*pressure);ba[0]=ba[0]+basis*(w*a.x);ba[1]=ba[1]+basis*(w*a.y);ba[2]=ba[2]+basis*(w*a.z);
    }
    const auto pcoef=Product(fit.inverse,bp);const auto a0=Product(fit.inverse,ba[0]),a1=Product(fit.inverse,ba[1]),a2=Product(fit.inverse,ba[2]);
    const auto grad=TDouble3(pcoef.y/KernelH,0,pcoef.z/KernelH),a=TDouble3(a0.x,a1.x,a2.x);
    const double rhow=SoilCte.PoreWaterRho,k=SoilCte.HydraulicConductivity,gamma=rhow*9.80665;
    const double td=32768*DBL_EPSILON*fit.condition,tf=64*FLT_EPSILON*fit.condition;
    // Propagate the retained affine-wall td/tf budgets through one MLS derivative and Darcy's linear drive.
    const double limit=k/gamma*(tf*(rhow*Norm(ToTDouble3(Gravity))+rhow)+td*256./KernelH);
    return {pcoef.x,grad,a,fit.condition,limit,-k/gamma*(grad.x+rhow*a.x)*inward};
  }
  Rate CompleteReference(unsigned i)const{
    const double rhow=SoilCte.PoreWaterRho,v0=double(MassFluid)/RhopZero,kw=SoilCte.PoreWaterBulkModulus;
    double lp=0,da=0,lpabs=0,daabs=0;tdouble3 gp=TDouble3(0),lx=TDouble3(0);
    // Independent O(N^2) enumeration; no production cell-list helper or rate routine is called here.
    for(unsigned j=0;j<Np;j++)if(Sample(j,true)){
      const auto d=Posc[i]-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
      const auto g=d*Fac(rr),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j];
      const double w=v*Dot(d,gi+gj)/(rr+double(Eta2));lp+=w*dp;lx=lx+d*w;gp=gp-gi*(v*dp);
      const auto a=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);da+=v*Dot(a,gi);lpabs+=fabs(w*dp);daabs+=v*(fabs(a.x*gi.x)+fabs(a.y*gi.y)+fabs(a.z*gi.z));
    }
    const double n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i],scale=kw/n*double(SoilCte.HydraulicConductivity)/(rhow*9.80665);
    const double raw=scale*(lpabs+fabs(gp.x*lx.x)+fabs(gp.y*lx.y)+fabs(gp.z*lx.z)+rhow*daabs);
    const double limit=(32*FLT_EPSILON+4096*DBL_EPSILON)*(std::max)(1.,raw);
    return {kw/n*(-PoroThetac[i])+scale*(lp-Dot(gp,lx)+rhow*da),limit,gp.x};
  }
  std::vector<Row> Snapshot()const{
    const auto m=Map();std::vector<Row> r;for(unsigned id:Soil){const unsigned p=m[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];
      r.push_back({x.x,x.y,x.z,v.x,v.y,v.z,v.w,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p]});for(double a:r.back())Need(std::isfinite(a),"Nonfinite native physical field");}return r;
  }
  void Check(const fs::path& out,int sign,bool offgrid){
    const auto m=Map();const Copy<tfloat3> normals(BoundNormalc,Np);const Copy<tdouble3> positions(Posc,Np);const Copy<unsigned> ids(Idpc,Np);const Copy<typecode> codes(Codec,Np);
    if(offgrid)for(unsigned p=0;p<Npb;p++)BoundNormalc[p].x+=float((BoundNormalc[p].x>0?1.:-1.)*Dp0/8.);
    Gravity=TFloat3(float(sign),0,0);CSP.gravity=Gravity; // Private field assignment AFTER the real zero-g InitDynamicPoreWallCpu admission.
    for(unsigned p=0;p<Np;p++){
      const bool fluid=CODE_IsFluid(Codec[p]);const double pressure=Head+double(SoilCte.PoreWaterRho)*Dot(ToTDouble3(Gravity),Posc[p]);Need(fabs(pressure)<256,"Manufacture left retained 256-Pa affine pressure scale");
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);PoroJc[p]=1.;PoroThetac[p]=0;PorePressc[p]=fluid? float(pressure):12345.f;PorePress0c[p]=0;PorePressRatec[p]=1234567.f;
      Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;CorrMatc[p]=TMatrix3d(0);if(TangenVelc)TangenVelc[p]=TFloat3(0);
    }
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();for(unsigned p=0;p<Np;p++)Acec[p]=BoundDerivativeVelc[p]=TFloat3(0);
    const auto before=Snapshot();ComputeFreeSurfaceTracking(); // Actual wall state, actual fluid C/classification, then actual wall C.
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p]))Acec[p]=TFloat3(-Gravity.x,-Gravity.y,-Gravity.z);
    ComputeDynamicPoreWallAccelerationCpu();
    const std::string tag=std::string(sign<0?"gminus":"gplus")+(offgrid?"_offgrid":"_coincident");std::ofstream wall(out/(tag+"_wall.csv")),face(out/(tag+"_face.csv")),rate(out/(tag+"_rate.csv"));
    for(auto* f:{&wall,&face,&rate})*f<<std::setprecision(17);
    wall<<"native_id,wall_x,mirror_x,expected_p,actual_p,p_error,J_error,Ace_error,condition,double_base_tol,float_base_tol\n";
    face<<"side,z,physical_plane_x,p_fit,gradp_x,gradp_z,Ace_fit_x,Ace_fit_z,normal_flux,q_limit,missing_head_normal_flux,wrong_Ace_normal_flux,condition\n";
    rate<<"native_id,x,z,actual_rate,independent_complete_rate,roundoff_limit,independent_gradp_x\n";
    for(unsigned id:Bound){const unsigned p=m[id];const auto target=Posc[p]+ToTDouble3(BoundNormalc[p]);const auto fit=FitMoment(target,false);
      const double td=32768*DBL_EPSILON*fit.condition,tf=64*FLT_EPSILON*fit.condition,expected=float(Head+double(SoilCte.PoreWaterRho)*Dot(ToTDouble3(Gravity),Posc[p]));
      const double ep=fabs(PorePressc[p]-expected),ej=fabs(PoroJc[p]-1.),ea=Norm(ToTDouble3(Acec[p])+ToTDouble3(Gravity));
      Need(ep<=256*tf&&ej<=2*td&&ea<=tf,"Normal-gravity wall p/J/Ace exceeds retained affine budget");
      Need(Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==RhopZero&&Norm(ToTDouble3(BoundDerivativeVelc[p]))<=tf&&Norm(ToTDouble3(TangenVelc[p]))<=tf&&BoundModec[p]==BMODE_MDBC2,"Fixed/derivative/tangent wall state changed");
      MaxStateRatio=(std::max)({MaxStateRatio,ep/(256*tf),ej/(2*td),ea/tf});wall<<id<<','<<Posc[p].x<<','<<target.x<<','<<expected<<','<<PorePressc[p]<<','<<ep<<','<<ej<<','<<ea<<','<<fit.condition<<','<<td<<','<<tf<<'\n';WallRows++;
    }
    for(unsigned side=0;side<2;side++)for(unsigned iz=0;iz<32;iz++){
      const double inward=side? -1.:1.,plane=(side?Width:0.)+inward*(offgrid?Dp0/16.:0.);const auto at=TDouble3(plane,0,(iz+.5)*Dp0);
      const auto f=PhysicalFace(at,inward,0),missing=PhysicalFace(at,inward,1),wrong=PhysicalFace(at,inward,2);const double td=32768*DBL_EPSILON*f.condition,tf=64*FLT_EPSILON*f.condition;
      const auto truegrad=ToTDouble3(Gravity)*double(SoilCte.PoreWaterRho);const double expected=Head+Dot(truegrad,at);
      Need(fabs(f.p-expected)<=256*tf&&Norm(f.grad-truegrad)<=tf*Norm(truegrad)+td*256./KernelH&&Norm(f.a+ToTDouble3(Gravity))<=tf,"Independent true-plane affine fit exceeds retained propagated budget");
      Need(std::isfinite(f.qn)&&fabs(f.qn)<=f.limit,"True physical-face normal Darcy flux is not zero within retained propagated budget");
      const double mh=fabs(missing.qn)/f.limit,wa=fabs(wrong.qn)/f.limit;Need(mh>100&&wa>100,"Omitted-head/wrong-Ace negative control is vacuous");
      MaxFluxRatio=(std::max)(MaxFluxRatio,fabs(f.qn)/f.limit);MinMissingHeadRatio=(std::min)(MinMissingHeadRatio,mh);MinWrongAceRatio=(std::min)(MinWrongAceRatio,wa);
      face<<side<<','<<at.z<<','<<at.x<<','<<f.p<<','<<f.grad.x<<','<<f.grad.z<<','<<f.a.x<<','<<f.a.z<<','<<f.qn<<','<<f.limit<<','<<missing.qn<<','<<wrong.qn<<','<<f.condition<<'\n';FaceRows++;
    }
    std::vector<Rate> ref;for(unsigned id:Soil)ref.push_back(CompleteReference(m[id]));ComputeDynamicPorePressureRateCpu();
    for(unsigned row=0;row<Native;row++){const unsigned p=m[Soil[row]];const auto r=ref[row];const double error=fabs(double(PorePressRatec[p])-r.value);
      Need(std::isfinite(PorePressRatec[p])&&PorePressRatec[p]!=1234567.f&&error<=r.limit,"Complete Darcy rate differs from independent all-particle reference");
      MaxRateRatio=(std::max)(MaxRateRatio,error/r.limit);rate<<Soil[row]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<PorePressRatec[p]<<','<<r.value<<','<<r.limit<<','<<r.gpnormal<<'\n';RateRows++;
    }
    const auto after=Snapshot();Need(!memcmp(before.data(),after.data(),Native*sizeof(Row)),"Zero-step stages changed native physical18 fields");NoStep();PosInteraction_Forces();
    normals.Restore();Need(normals.Equal()&&positions.Equal()&&ids.Equal()&&codes.Equal(),"Geometry/IDs/normals changed");Gravity=CSP.gravity=TFloat3(0);
    for(auto* f:{&wall,&face,&rate}){f->flush();Need(bool(*f),"Diagnostic CSV write failed");}Cases++;
  }
public:
  Wall(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&(TKernel==KERNEL_Cubic||TKernel==KERNEL_Wendland)&&TStep==STEP_Symplectic&&CaseNpb==Fixed&&CaseNfluid==Native&&CaseNp==Native+Fixed&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&MdbcCorrector&&!PeriX&&!PeriY&&PeriZ,"Wrong retained private wall fixture/options");
    Need(!Gravity.x&&!Gravity.y&&!Gravity.z&&!CSP.gravity.x&&!CSP.gravity.y&&!CSP.gravity.z&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity,"XML initialization must retain zero-g/no-load/no-drain/constant-k scope");
    Need(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR,"Auxiliary path outside component scope");
    Need(Dp==Dp0&&MapRealPosMin.x==-4*Dp0&&MapRealPosMax.x==Width+4*Dp0&&MapRealPosMin.z==0&&MapRealSize.z==Lz&&FixedDt&&TangenVelc&&BoundModec,"Changed retained map/spacing/mDBC arrays");
    Need(SoilCte.PoreWaterRho==1000.f&&SoilCte.Porosity==.25f&&SoilCte.HydraulicConductivity==float(.0001)&&RhopZero==2048&&double(MassFluid)/RhopZero==Dp0*Dp0&&KernelH==float(1.8*Dp0),"Changed retained hydraulic material/h-over-dp");
    NoStep();const auto m=Map();unsigned left=0,right=0;std::ofstream idcsv(fs::path(cfg->DirOut)/"native_ids.csv");idcsv<<std::setprecision(17)<<"native_id,fluid,x0,y0,z0,physical_plane_x\n";
    for(unsigned id=0;id<CaseNp;id++){const unsigned p=m[id];const auto x=Posc[p];const bool fluid=CODE_IsFluid(Codec[p]);double plane=0;
      if(fluid)Soil.push_back(id);else{Bound.push_back(id);const auto n=BoundNormalc[p];plane=x.x+.5*n.x;Need(n.y==0&&n.z==0&&((n.x>0&&plane==0)||(n.x<0&&plane==Width)),"Fixed plane/normal mismatch");n.x>0?left++:right++;}
      idcsv<<id<<','<<fluid<<','<<x.x<<','<<x.y<<','<<x.z<<','<<plane<<'\n';}
    Need(left==128&&right==128,"Missing retained parallel face");InitDynamicPoreWallCpu(); // Real public restrictions still see exactly zero gravity.
    for(int sign:{-1,1})for(bool offgrid:{false,true})Check(cfg->DirOut,sign,offgrid);
    Need(Cases==4&&WallRows==1024&&FaceRows==256&&RateRows==4096,"Declared component coverage differs");NoStep();idcsv.flush();Need(bool(idcsv),"Native ID write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_gravity_wall_cpu_r1\",\"passed\":true,\"private_manufactured\":true,\"kernel\":\""<<(TKernel==KERNEL_Cubic?"Cubic":"Wendland")<<"\",\"h_over_dp\":1.8,\"cases\":"<<Cases<<",\"wall_rows\":"<<WallRows<<",\"true_plane_rows\":"<<FaceRows<<",\"complete_rate_rows\":"<<RateRows<<",\"max_state_over_retained_budget\":"<<MaxStateRatio<<",\"max_true_plane_flux_over_propagated_budget\":"<<MaxFluxRatio<<",\"max_complete_rate_over_old_roundoff_budget\":"<<MaxRateRatio<<",\"min_missing_head_flux_over_budget\":"<<MinMissingHeadRatio<<",\"min_wrong_Ace_flux_over_budget\":"<<MinWrongAceRatio<<",\"native_soil\":1024,\"native_fixed\":256,\"native_physical18_unchanged\":true,\"geometry_ID_normal_bytes_restored\":true,\"actual_CPU_initialization\":true,\"actual_free_surface_and_wall_stages\":true,\"actual_complete_Darcy_rate\":true,\"public_guard_changed\":false,\"actual_Run_or_ComputeStep_called\":false,\"completed_physical_steps\":0,\"actual_time_s\":0,\"mechanical_equilibrium_accepted\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--wall","Use --wall -cpu -ompthreads:1 -stable -mdbc_freeslip ZERO_G_SEED FRESH");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Only fresh CPU zero-step component admitted");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Wall wall;wall.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Gravity wall component failed; preserve evidence\n";return 2;}}
