// Real case08 one-ct affine compression: private instantaneous field/force diagnostic.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
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
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("UplC08Force","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static constexpr unsigned Fixed=2060,Soil=5000,Total=Fixed+Soil;
static constexpr double Height=2.,RateC=-1./8192.;
template<class T>struct Copy{T* p;std::vector<T> v;Copy(T* a,unsigned n):p(a){if(p)v.assign(a,a+n);}void Restore()const{if(p&&!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}bool Equal()const{return !p||v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}~Copy(){Restore();}};
struct BorrowDerivative{
  tfloat3*& pointer;tfloat3* original;
  BorrowDerivative(tfloat3*& p,tfloat3* owned):pointer(p),original(p){Need(p==nullptr,"Derivative pointer was already owned");pointer=owned;}
  ~BorrowDerivative(){pointer=original;}
};
struct RestoreFlags{
  bool &feedback,&dynamic,&wall,&stress;bool f,d,w,s;
  ~RestoreFlags(){feedback=f;dynamic=d;wall=w;stress=s;}
};
class Probe:public JSphCpuSingle{
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed,"Wrong retained case08 counts");std::vector<unsigned> map(Total,UINT_MAX);unsigned soil=0,fixed=0;
    for(unsigned q=0;q<Np;q++){Need(Idpc[q]<Total&&map[Idpc[q]]==UINT_MAX,"Unknown/duplicate native ID");map[Idpc[q]]=q;
      if(CODE_IsFluid(Codec[q])){Need(CODE_IsNormal(Codec[q])&&Idpc[q]>=Fixed,"Unexpected native soil code");soil++;}else{Need(CODE_IsFixed(Codec[q])&&Idpc[q]<Fixed,"Unexpected fixed type");fixed++;}}
    Need(soil==Soil&&fixed==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native identity/exclusions changed");return map;
  }
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PosPrec,"Instantaneous component advanced a step");}
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Observer-only constructor required");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&!PeriActive&&!Symmetry&&BoundModec&&BoundSlipModec&&TangenVelc,"Wrong legitimate observer initialization");
    Need(Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==2e-4f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f),"Retained material/geometry changed");
    Need(TimeMax==0&&NpbOk==465&&!SoilStressRateGradCorr&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0&&TVisco==VISCO_Artificial&&Visco==.1f&&!WithFloating&&!UseDEM&&!AccInput&&!ArtificialStress&&TDensity==DDT_None&&!Shifting&&!Damping&&!SoilDamping&&!SoilHourglassXi&&!HourglassCpu&&!SoilBoundaryDerivativeSPR&&!NoPenetration&&TMdbc2!=MDBC2_NoPen&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity&&!StrainSoftening&&!Acec&&!BoundDerivativeVelc,"One-ct scope changed");
    const auto map=Map();NoStep();const unsigned initialNpbOk=NpbOk;const auto oldInter=InterStep;const double oldSpeed=DynamicConductivitySpeedMax,oldVelMax=VelMax;const float oldVisc=ViscDtMax;
    std::array<unsigned char,sizeof(SoilCte)> material;memcpy(material.data(),&SoilCte,sizeof(SoilCte));
    const Copy<unsigned> ids(Idpc,Np),cells(Dcellc,Np),fstype(FSTypec,Np);const Copy<typecode> codes(Codec,Np);const Copy<tdouble3> pos(Posc,Np);const Copy<tfloat3> normal(BoundNormalc,Np),tan(TangenVelc,Np),load(HydroMechLoadAcec,Np),fsnormal(FSNormalc,Np);
    const Copy<tfloat4> vel(Velrhopc,Np);const Copy<tsymatrix3d> sigma(Sigmac,Np);const Copy<byte> modes(BoundModec,Np),selectors(BoundSlipModec,Np);const Copy<tmatrix3d> corr(CorrMatc,Np);const Copy<double> j(PoroJc,Np),theta(PoroThetac,Np);const Copy<float> p(PorePressc,Np),p0(PorePress0c,Np),rate(PorePressRatec,Np),plastic(Kplasticc,Np),posdiv(PosDivc,Np);
    double maxStoredV=0;
    for(unsigned q=0;q<Np;q++){const float vz=(CODE_IsFluid(Codec[q])?float(RateC*Posc[q].z):0.f);Velrhopc[q]=TFloat4(0,0,vz,RhopZero);maxStoredV=(std::max)(maxStoredV,fabs(double(vz)));Sigmac[q]=tsymatrix3d{};Kplasticc[q]=0;PoroJc[q]=1;PoroThetac[q]=0;PorePress0c[q]=PorePressRatec[q]=0;PorePressc[q]=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(Posc[q].z-Height));}
    // Declared before the force observation. Material storage remains the actual parsed float.
    const double derivativeBudget=128.*double(FLT_EPSILON)*(std::max)(fabs(RateC),maxStoredV/double(KernelH))+4096.*double(DBL_EPSILON)*(std::max)(1.,fabs(RateC));
    const double bulk=double(SoilCte.ModulusK),shear=double(SoilCte.ModulusG),lambda=bulk-2.*shear/3.,modulus=(std::max)(bulk+4.*shear/3.,2.*shear);
    const std::array<double,6> reference={lambda*RateC,lambda*RateC,(lambda+2.*shear)*RateC,0,0,0};std::array<double,6> budget{},maxSigmaError{};
    for(unsigned c=0;c<6;c++)budget[c]=(c<3?derivativeBudget*modulus+64.*double(FLT_EPSILON)*(std::max)(1.,fabs(reference[c])):derivativeBudget*2.*shear);
    std::ofstream ledger(fs::path(cfg->DirOut)/"ids.csv"),kin(fs::path(cfg->DirOut)/"kinematics.csv"),walls(fs::path(cfg->DirOut)/"walls.csv"),rates(fs::path(cfg->DirOut)/"rates.csv");for(auto* f:{&ledger,&kin,&walls,&rates})*f<<std::setprecision(17);
    ledger<<"native_id,sorted_slot,is_fluid,x,y,z,code\n";for(unsigned id=0;id<Total;id++){const auto q=map[id];ledger<<id<<','<<q<<','<<CODE_IsFluid(Codec[q])<<','<<Posc[q].x<<','<<Posc[q].y<<','<<Posc[q].z<<','<<unsigned(Codec[q])<<'\n';}
    kin<<"native_id,sorted_slot,x,z,stored_vz,theta,theta_ref,theta_error,theta_budget,sxx,sxx_ref,sxx_error,sxx_budget,syy,syy_ref,syy_error,syy_budget,szz,szz_ref,szz_error,szz_budget,sxy,sxy_ref,sxy_error,sxy_budget,syz,syz_ref,syz_error,syz_budget,sxz,sxz_ref,sxz_error,sxz_budget,Ace_x,Ace_y,Ace_z,legacy_Arc\n";
    walls<<"native_id,sorted_slot,slipmode,B_x,B_z,normal_x,normal_z,physical_vx,physical_vy,physical_vz,legacy_rho,derivative_vx,derivative_vy,derivative_vz,derivative_vz_affine,derivative_vz_error,tangent_vx,tangent_vy,tangent_vz,tangent_vz_affine,tangent_vz_error,J,p_Pa,Ace_x,Ace_y,Ace_z,true_ax,true_ay,true_az\n";
    rates<<"native_id,theta,J,n,rate_Pa_s,local_compression_Pa_s,spatial_acceleration_remainder_Pa_s,Ace_x,Ace_y,Ace_z,true_ax,true_ay,true_az\n";
    unsigned forceCalls=0,nativeRows=0,wallRows=0,offRows=0;double maxThetaError=0,maxImageError=0,maxTangentError=0,maxAce=0,maxRate=0,rateSquare=0;
    try{
      InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Need(Arc&&Acec&&Rsigmac&&Pressc&&!BoundDerivativeVelc&&!Deltac&&!ShiftPosfsc&&!SpsGradvelc&&!NoPenShiftc,"Ordinary observer scratch budget changed");
      std::vector<tfloat3> borrowed(Np,TFloat3(std::numeric_limits<float>::quiet_NaN()));
      {
        BorrowDerivative borrow(BoundDerivativeVelc,borrowed.data()); // Restores NULL before either normal or catch Pos cleanup.
        RestoreFlags restore{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,SoilStressRateGradCorr,PorosityFeedback,DynamicPorePressure,DynamicPoreWall,SoilStressRateGradCorr};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=SoilStressRateGradCorr=true;
        ComputeFreeSurfaceTracking(); // One real state refresh fills borrowed images, then native FS/C and wall C.
        ApplyHydroMechTopLoadAcceleration();const Copy<float> beforeProjection(PorePressc,Np);ApplyFreeSurfacePorePressure();Need(beforeProjection.Equal(),"Unexpected pressure projection in no-drain input");
        for(unsigned id=0;id<Fixed;id++){const unsigned q=map[id];if(q>=NpbOk){Need(BoundModec[q]==modes.v[q],"Ignored wall mode changed");continue;}if(BoundModec[q]==BMODE_MDBC2OFF){offRows++;Need(std::isnan(borrowed[q].x)&&std::isnan(borrowed[q].y)&&std::isnan(borrowed[q].z),"OFF derivative slot unexpectedly populated");continue;}
          Need(BoundModec[q]==BMODE_MDBC2&&Velrhopc[q]==TFloat4(0,0,0,RhopZero),"Physical fixed velocity/rho changed");const auto dv=borrowed[q],tv=TangenVelc[q];Need(std::isfinite(dv.x)&&std::isfinite(dv.y)&&std::isfinite(dv.z)&&std::isfinite(tv.x)&&std::isfinite(tv.y)&&std::isfinite(tv.z),"Live wall image nonfinite");wallRows++;}
        Need(wallRows==410&&offRows==55&&NpbOk==initialNpbOk,"Closed current support classification changed");
        const Copy<tfloat4> forcevel(Velrhopc,Np);const Copy<tsymatrix3d> forcesigma(Sigmac,Np);const Copy<float> forcep(PorePressc,Np),forcep0(PorePress0c,Np),forcerate(PorePressRatec,Np);const Copy<double> forcej(PoroJc,Np);const Copy<tmatrix3d> forcec(CorrMatc,Np);
        const stinterparmsc parms=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
        StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(parms,result);forceCalls++;
        if(SoilDamping)AddSoilDampingCpu(Np,Npb,Codec,Velrhopc,Acec);
        if(Simulate2D)for(unsigned q=Npb;q<Np;q++)Acec[q].y=0;ViscDtMax=result.viscdt;
        Need(std::isfinite(result.viscdt)&&result.viscdt>=0&&forcevel.Equal()&&forcesigma.Equal()&&forcep.Equal()&&forcep0.Equal()&&forcerate.Equal()&&forcej.Equal()&&forcec.Equal(),"Actual ct changed physical inputs or returned invalid viscosity scale");
        for(unsigned id=Fixed;id<Total;id++){
          const unsigned q=map[id];const auto sr=Rsigmac[q];const auto a=Acec[q];const std::array<double,6> actual={sr.xx,sr.yy,sr.zz,sr.xy,sr.yz,sr.xz};const double et=fabs(PoroThetac[q]-RateC);bool good=std::isfinite(PoroThetac[q])&&et<=derivativeBudget&&std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z)&&std::isfinite(Arc[q]);
          kin<<id<<','<<q<<','<<Posc[q].x<<','<<Posc[q].z<<','<<Velrhopc[q].z<<','<<PoroThetac[q]<<','<<RateC<<','<<et<<','<<derivativeBudget;
          for(unsigned c=0;c<6;c++){const double error=fabs(actual[c]-reference[c]);kin<<','<<actual[c]<<','<<reference[c]<<','<<error<<','<<budget[c];good=good&&std::isfinite(actual[c])&&error<=budget[c];maxSigmaError[c]=(std::max)(maxSigmaError[c],error);}
          kin<<','<<a.x<<','<<a.y<<','<<a.z<<','<<Arc[q]<<'\n';if(!good)kin.flush();Need(good,"Actual affine theta/stress-rate budget or finite force failed; preserve kinematics.csv");maxThetaError=(std::max)(maxThetaError,et);nativeRows++;
        }
        const Copy<tfloat3> finishedAce(Acec,Np);const Copy<double> finishedTheta(PoroThetac,Np);
        ComputeDynamicPorePressureRateCpu(); // Genuine finished native acceleration; no Ace=-g substitution.
        Need(forcep.Equal()&&forcep0.Equal()&&forcej.Equal()&&forcec.Equal()&&forcevel.Equal()&&forcesigma.Equal()&&finishedTheta.Equal(),"Complete rate changed frozen state inputs");
        for(unsigned id=Fixed;id<Total;id++){const unsigned q=map[id];Need(!memcmp(Acec+q,finishedAce.v.data()+q,sizeof(tfloat3)),"Wall-Ace/rate changed finished native acceleration");const auto a=Acec[q];const double n=1.-(1.-double(SoilCte.Porosity))/PoroJc[q],compression=-double(SoilCte.PoreWaterBulkModulus)/n*PoroThetac[q],r=PorePressRatec[q];
          rates<<id<<','<<PoroThetac[q]<<','<<PoroJc[q]<<','<<n<<','<<r<<','<<compression<<','<<r-compression<<','<<a.x<<','<<a.y<<','<<a.z<<','<<double(a.x)+Gravity.x<<','<<double(a.y)+Gravity.y<<','<<double(a.z)+Gravity.z<<'\n';Need(std::isfinite(r),"Finished complete native rate nonfinite");maxRate=(std::max)(maxRate,fabs(r));rateSquare+=r*r;maxAce=(std::max)({maxAce,fabs(double(a.x)),fabs(double(a.y)),fabs(double(a.z))});}
        for(unsigned id=0;id<Fixed;id++){const unsigned q=map[id];if(q>=NpbOk||BoundModec[q]!=BMODE_MDBC2)continue;const auto b=Posc[q];const auto bn=BoundNormalc[q],dv=borrowed[q],tv=TangenVelc[q],a=Acec[q];const auto physical=Velrhopc[q];const auto mode=TpSlipMode(BoundSlipModec[q]);Need(mode==(id<255||id>=1800?SLIP_FreeSlip:SLIP_NoSlip),"Original per-MK slip changed");const double image=RateC*b.z,tangent=(mode==SLIP_NoSlip?0.:image),ei=fabs(double(dv.z)-image),et=fabs(double(tv.z)-tangent);maxImageError=(std::max)(maxImageError,ei);maxTangentError=(std::max)(maxTangentError,et);
          walls<<id<<','<<q<<','<<unsigned(mode)<<','<<b.x<<','<<b.z<<','<<bn.x<<','<<bn.z<<','<<physical.x<<','<<physical.y<<','<<physical.z<<','<<physical.w<<','<<dv.x<<','<<dv.y<<','<<dv.z<<','<<image<<','<<ei<<','<<tv.x<<','<<tv.y<<','<<tv.z<<','<<tangent<<','<<et<<','<<PoroJc[q]<<','<<PorePressc[q]<<','<<a.x<<','<<a.y<<','<<a.z<<','<<double(a.x)+Gravity.x<<','<<double(a.y)+Gravity.y<<','<<double(a.z)+Gravity.z<<'\n';}
        Need(ids.Equal()&&cells.Equal()&&codes.Equal()&&pos.Equal()&&normal.Equal()&&selectors.Equal(),"Force/rate changed original IDs/CODE/positions/cells");NoStep();
      }
      Need(!BoundDerivativeVelc&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!SoilStressRateGradCorr,"Borrowed pointer/private flags not restored before cleanup");
    }catch(...){PosInteraction_Forces();InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVelMax;ViscDtMax=oldVisc;throw;}
    PosInteraction_Forces();InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVelMax;ViscDtMax=oldVisc;
    vel.Restore();sigma.Restore();modes.Restore();tan.Restore();load.Restore();corr.Restore();j.Restore();theta.Restore();p.Restore();p0.Restore();rate.Restore();plastic.Restore();fstype.Restore();fsnormal.Restore();posdiv.Restore();
    Need(!BoundDerivativeVelc&&!Acec&&NpbOk==initialNpbOk&&ids.Equal()&&cells.Equal()&&codes.Equal()&&pos.Equal()&&normal.Equal()&&selectors.Equal()&&vel.Equal()&&sigma.Equal()&&modes.Equal()&&tan.Equal()&&load.Equal()&&corr.Equal()&&j.Equal()&&theta.Equal()&&p.Equal()&&p0.Equal()&&rate.Equal()&&plastic.Equal()&&fstype.Equal()&&fsnormal.Equal()&&posdiv.Equal()&&!memcmp(material.data(),&SoilCte,sizeof(SoilCte)),"Original arrays/material/control state not restored");Map();NoStep();
    Need(forceCalls==1&&nativeRows==5000&&wallRows==410&&offRows==55,"One-ct coverage incomplete");for(auto* f:{&ledger,&kin,&walls,&rates}){f->flush();Need(bool(*f),"Force diagnostic CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_force_r1\",\"passed\":true,\"native_ids\":7060,\"soil\":5000,\"active_walls\":410,\"OFF_in_prefix\":55,\"actual_ct_calls\":"<<forceCalls<<",\"native_theta_checks\":5000,\"native_sigma_rate_checks\":30000,\"c_per_s\":"<<RateC<<",\"max_stored_velocity_m_s\":"<<maxStoredV<<",\"derivative_budget_per_s\":"<<derivativeBudget<<",\"max_theta_error_per_s\":"<<maxThetaError<<",\"sigma_reference_Pa_s\":[";
    for(unsigned c=0;c<6;c++)done<<(c?",":"")<<reference[c];done<<"],\"sigma_budget_Pa_s\":[";for(unsigned c=0;c<6;c++)done<<(c?",":"")<<budget[c];done<<"],\"max_sigma_error_Pa_s\":[";for(unsigned c=0;c<6;c++)done<<(c?",":"")<<maxSigmaError[c];
    done<<"],\"max_wall_image_error_m_s\":"<<maxImageError<<",\"max_wall_tangent_error_m_s\":"<<maxTangentError<<",\"max_actual_native_Ace_component_m_s2\":"<<maxAce<<",\"complete_rate_absmax_Pa_s\":"<<maxRate<<",\"complete_rate_RMS_Pa_s\":"<<sqrt(rateSquare/Soil)<<",\"borrowed_derivative_restored_before_Pos_cleanup\":true,\"production_allocator_proved\":false,\"private_stress_gradient_correction_restored\":true,\"geometry_IDs_CODE_cells_arrays_material_restored\":true,\"actual_finished_Ace_not_prescribed\":true,\"isolated_AV_dissipation_claimed\":false,\"physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--force","Use --force -cpu -ompthreads:1 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_RESULT");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU one-ct output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Case08 one-ct diagnostic failed; preserve output\n";return 2;}}
