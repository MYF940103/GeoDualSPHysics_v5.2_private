// Frozen instantaneous J-versus-neighbour-weighted Eq24 comparison; never integrates.
#define main RetainedPorosityOperatorNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JLog2.h"
#include "FunSphKernel.h"
namespace porosityop {
constexpr unsigned Count=512;
constexpr double Dp=1./256.,V0=Dp*Dp,EpsilonJ=1./1024.;
struct Saved {
  unsigned id,cell,fs;typecode code;tdouble3 pos;tfloat4 vel;tsymatrix3d sigma;
  float plastic,p,p0,rate,posdiv;double j,theta;tmatrix3d c;tfloat3 normal,load;
};
struct Reference {unsigned neighbours=0;double theta=0,lian=0,delta=0,raw=0,rawL=0,rawD=0;};
class Operator:public JSphCpuSingle {
  std::vector<unsigned> Owners()const {
    std::vector<unsigned> owner(Count,~0u);unsigned native=0,ghost=0,corner=0;
    for(unsigned p=0;p<Np;p++) {
      Need(CODE_IsFluid(Codec[p])&&Idpc[p]<Count,"Unexpected frozen particle type/ID");
      if(CODE_IsNormal(Codec[p])){Need(owner[Idpc[p]]==~0u,"Duplicate normal owner");owner[Idpc[p]]=p;native++;}
      else {Need(CODE_IsPeriodic(Codec[p]),"Excluded/unknown frozen particle code");ghost++;}
    }
    Need(native==Count&&ghost&&!Npb&&!NpbOk&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Incomplete native/periodic scope");
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){const auto d=Posc[p]-Posc[owner[Idpc[p]]];corner+=unsigned(d.x!=0&&d.z!=0);}
    Need(corner>0,"No actual XZ corner image");return owner;
  }
  std::vector<Saved> Capture()const {
    std::vector<Saved> a(Count);const auto owner=Owners();
    for(unsigned id=0;id<Count;id++){const unsigned p=owner[id];a[id]={Idpc[p],Dcellc[p],FSTypec[p],Codec[p],Posc[p],Velrhopc[p],Sigmac[p],Kplasticc[p],PorePressc[p],PorePress0c[p],PorePressRatec[p],PosDivc[p],PoroJc[p],PoroThetac[p],CorrMatc[p],FSNormalc[p],HydroMechLoadAcec[p]};}return a;
  }
  static std::vector<byte> Bytes(const std::vector<Saved>& a,bool diagnostics) {
    std::vector<byte> b;auto add=[&](const auto& x){const auto p=reinterpret_cast<const byte*>(&x);b.insert(b.end(),p,p+sizeof(x));};
    for(const auto& s:a){add(s.id);add(s.cell);add(s.code);add(s.pos);add(s.vel);add(s.sigma);add(s.plastic);add(s.p);add(s.p0);add(s.j);add(s.load);if(diagnostics){add(s.fs);add(s.rate);add(s.posdiv);add(s.theta);add(s.c);add(s.normal);}}return b;
  }
  void Restore(const std::vector<Saved>& a) {
    const auto owner=Owners();for(unsigned id=0;id<Count;id++){const unsigned p=owner[id];const auto& s=a[id];Idpc[p]=s.id;Dcellc[p]=s.cell;Codec[p]=s.code;Posc[p]=s.pos;Velrhopc[p]=s.vel;Sigmac[p]=s.sigma;Kplasticc[p]=s.plastic;PorePressc[p]=s.p;PorePress0c[p]=s.p0;PorePressRatec[p]=s.rate;PoroJc[p]=s.j;PoroThetac[p]=s.theta;CorrMatc[p]=s.c;FSTypec[p]=s.fs;FSNormalc[p]=s.normal;PosDivc[p]=s.posdiv;HydroMechLoadAcec[p]=s.load;}
    Need(Bytes(Capture(),true)==Bytes(a,true),"Covered normal state not byte-exact after restore");
  }
  unsigned CheckCopies(bool rate)const {
    const auto owner=Owners();unsigned count=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){const unsigned q=owner[Idpc[p]];
      Need(!std::memcmp(PoroJc+p,PoroJc+q,sizeof(double))&&!std::memcmp(Velrhopc+p,Velrhopc+q,sizeof(tfloat4)),"Actual periodic J/velocity copy differs");
      Need(PorePressc[p]==0&&PorePress0c[p]==0,"Nonzero ghost pore-pressure field");
      if(rate)Need(!std::memcmp(CorrMatc+p,CorrMatc+q,sizeof(tmatrix3d))&&!std::memcmp(PoroThetac+p,PoroThetac+q,sizeof(double))&&!std::memcmp(PorePressRatec+p,PorePressRatec+q,sizeof(float)),"Completed periodic C/theta/rate copy differs");count++;
    }return count;
  }
  Reference Evaluate(unsigned i)const {
    Reference r;const auto c=CorrMatc[i];const auto vi=Velrhopc[i];const double ni=1.-(1.-N0)/PoroJc[i];
    // Independent all-slot search, but preserve BOTH production support tests and rounded operands.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])&&Velrhopc[j].w>0){
      const float dx=float(Posc[i].x-Posc[j].x),dy=float(Posc[i].y-Posc[j].y),dz=float(Posc[i].z-Posc[j].z),rr=dx*dx+dy*dy+dz*dz;
      if(rr>KernelSize2||rr<ALMOSTZERO)continue;
      const double x=double(dx),y=0,z=double(dz),prr=x*x+y*y+z*z;if(prr>double(KernelSize2)||prr<ALMOSTZERO)continue;
      const double fac=double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(prr))),gx=fac*x,gy=0,gz=fac*z;
      const double cx=c.a11*gx+c.a12*gy+c.a13*gz,cy=c.a21*gx+c.a22*gy+c.a23*gz,cz=c.a31*gx+c.a32*gy+c.a33*gz;
      const float dvx=vi.x-Velrhopc[j].x,dvy=vi.y-Velrhopc[j].y,dvz=vi.z-Velrhopc[j].z;
      const double ux=-double(dvx),uy=0,uz=-double(dvz),volume=V0*PoroJc[j],nj=1.-(1.-N0)/PoroJc[j];
      const double b=ux*cx+uy*cy+uz*cz,term=volume*b;
      const double raw=volume*(std::fabs(ux*cx)+std::fabs(uy*cy)+std::fabs(uz*cz));
      // The same rounded volume*b is shared; Eq24 factors are not separately re-associated.
      r.theta+=term;r.lian+=(1.-nj)*term;r.delta+=(ni-nj)*term;r.raw+=raw;r.rawL+=std::fabs(1.-nj)*raw;r.rawD+=std::fabs(ni-nj)*raw;r.neighbours++;
    }return r;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log) {
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMech&&PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&!DynamicPoreConductivity&&!DynamicPoreWall,"Accepted constant-k CPU input required");
    Need(Simulate2D&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&CaseNp==Count&&!CaseNpb&&!CaseNfloat&&!CaseNmoving&&PeriX&&PeriZ&&!PeriY&&Gravity==TFloat3(0)&&CSP.gravity==Gravity&&OmpThreads==1,"Only g0/no-wall512 XZ-periodic CPU scope");
    Need(JSph::Dp==porosityop::Dp&&double(KernelH)==double(float(1.8*porosityop::Dp))&&double(MassFluid)/RhopZero==V0&&double(RhopZero)==Rho0&&double(SoilCte.Porosity)==N0&&double(SoilCte.PoreWaterRho)==Rhow&&double(SoilCte.PoreWaterBulkModulus)==Kw&&double(SoilCte.ModulusK)==Bulk&&double(SoilCte.ModulusG)==Shear&&double(SoilCte.HydraulicConductivity)==K0,"Seed material/geometry differs");
    Need(PoreCompressionGradCorr&&!PoreCompressionSourceMode&&!HourglassCpu&&!SoilDamping&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!Shifting&&!NoPenetration&&!SoilBoundaryDerivativeSPR&&!Visco&&!ArtificialStress&&!PoreShepardRegularization&&!HydroMechDrainage&&!HydroMechInitMode&&!HydroMechTopLoadMode,"Unsupported extra physics/compression path");
    Need(!TimeStep&&!Nstep&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec&&FixedDt,"Initialization advanced state/history");
    RunCellDivide(true);const auto baseline=Capture();const auto basebytes=Bytes(baseline,true);const auto initialstage=InterStep;const double locked=SymplecticDtPre,lastdt=LastDt,dtError=FixedDt->GetDtError(false);const double kappa=2*std::acos(-1.)/Lx;
    std::ofstream csv(fs::path(cfg->DirOut)/"operators.csv"),summary(fs::path(cfg->DirOut)/"summary.csv");csv<<std::setprecision(17);summary<<std::setprecision(17);
    csv<<"case,id,x,z,J,n,V,neighbours,C11,C12,C13,C21,C22,C23,C31,C32,C33,theta_actual,theta_reference,theta_budget,ndot_J_actual,ndot_Lian,delta_reference,identity_error,identity_budget,raw_theta,raw_Lian,raw_delta,pressure_rate,expected_pressure_rate,wrong_weight_pressure_rate\n";
    summary<<"case,native_count,periodic_copy_slots,theta_RMS,n_span,ndot_difference_RMS,combined_budget_RMS,witness_delta,max_theta_error_ratio,max_identity_error_ratio\n";
    std::vector<tmatrix3d> nonuniformC(Count);unsigned rows=0,copychecks=0;double maxThetaRatio=0,maxIdentityRatio=0,signalRatio=0;
    for(unsigned trial=0;trial<3;trial++) {
      const auto owner=Owners();for(unsigned id=0;id<Count;id++){const unsigned p=owner[id];const double phi=4*kappa*(Posc[p].x-porosityop::Dp/2);
        PoroJc[p]=(trial?1.+EpsilonJ*std::cos(phi):1.);Velrhopc[p]=(trial==1?TFloat4(float(A),0,float(-A/2),float(Rho0)):TFloat4(float(A*std::sin(phi)),0,0,float(Rho0)));
        PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=Kplasticc[p]=0;PoroThetac[p]=0;Sigmac[p]={0,0,0,0,0,0};HydroMechLoadAcec[p]=TFloat3(0);LoadDcellParticles(1,Codec+p,Posc+p,Dcellc+p);
      }
      RunCellDivide(true);copychecks+=CheckCopies(false);const auto before=Capture();const auto physical=Bytes(before,false);const unsigned np=Np;
      Interaction_Forces(INTERSTEP_SymPredictor);Need(Np==np&&Bytes(Capture(),false)==physical&&!TimeStep&&!Nstep&&SymplecticDtPre==locked&&LastDt==lastdt&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Frozen force changed physical state/clock/history");copychecks+=CheckCopies(true);
      const auto map=Owners();double st=0,sd=0,sbudget=0,nlo=1,nhi=0,witness=0,mt=0,mi=0;
      for(unsigned id=0;id<Count;id++){const unsigned p=map[id];double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);
        Need(std::isfinite(n)&&std::isfinite(V)&&std::isfinite(rho)&&PoroJc[p]>1.-N0&&n>0&&n<1&&V>0&&rho>0&&std::isfinite(PoroThetac[p])&&Norm2(Acec[p])==0&&PorePressc[p]==0&&PorePress0c[p]==0&&Kplasticc[p]==0&&Norm2(HydroMechLoadAcec[p])==0,"Frozen field/domain/nonzero forcing guard failed");
        const double M=Bulk+4*Shear/3,B=Kw/n;Need(rho*B>Rhow*(M+B),"Frozen positive-k continuous domain failed");
        const Reference r=Evaluate(p);Need(r.neighbours>0,"Empty compression support");const double m=64.*(r.neighbours+1),gam=m*DBL_EPSILON/(1.-m*DBL_EPSILON);
        const double tb=(std::max)(DBL_MIN,gam*r.raw),jb=(std::max)(DBL_MIN,gam*(r.rawL+std::fabs(1.-n)*r.raw+r.rawD)+std::fabs(1.-n)*tb);
        const double nj=(1.-n)*PoroThetac[p],te=std::fabs(PoroThetac[p]-r.theta),ie=std::fabs((r.lian-nj)-r.delta);Need(te<=tb&&ie<=jb,"Prior common-rounded-term arithmetic budget failed");
        const float expected=float(Kw/n*(-PoroThetac[p])),wrong=float(Kw/n*(-nj));Need(std::isfinite(PorePressRatec[p])&&PorePressRatec[p]==expected,"Actual pressure compression did not use unweighted theta");
        if(trial==1)Need(PoroThetac[p]==0&&r.theta==0&&r.lian==0&&r.delta==0&&PorePressRatec[p]==0,"Nonuniform translation failed zero derivative");if(trial==0)Need(std::fabs(r.lian-nj)<=jb,"Uniform-n instantaneous rates differ");
        if(trial==1)nonuniformC[id]=CorrMatc[p];if(trial==2)Need(!std::memcmp(&nonuniformC[id],CorrMatc+p,sizeof(tmatrix3d)),"Same nonuniform J/positions changed actual C");
        st+=PoroThetac[p]*PoroThetac[p];sd+=(r.lian-nj)*(r.lian-nj);sbudget+=jb*jb;nlo=(std::min)(nlo,n);nhi=(std::max)(nhi,n);mt=(std::max)(mt,te/tb);mi=(std::max)(mi,ie/jb);if(Posc[p].x==porosityop::Dp/2)witness=(std::max)(witness,std::fabs(r.delta));
        const auto c=CorrMatc[p];csv<<trial<<','<<id<<','<<Posc[p].x<<','<<Posc[p].z<<','<<PoroJc[p]<<','<<n<<','<<V<<','<<r.neighbours<<','<<c.a11<<','<<c.a12<<','<<c.a13<<','<<c.a21<<','<<c.a22<<','<<c.a23<<','<<c.a31<<','<<c.a32<<','<<c.a33<<','<<PoroThetac[p]<<','<<r.theta<<','<<tb<<','<<nj<<','<<r.lian<<','<<r.delta<<','<<ie<<','<<jb<<','<<r.raw<<','<<r.rawL<<','<<r.rawD<<','<<PorePressRatec[p]<<','<<expected<<','<<wrong<<'\n';rows++;
      }
      const double trms=std::sqrt(st/Count),drms=std::sqrt(sd/Count),brms=std::sqrt(sbudget/Count);if(trial==0)Need(trms>0,"Periodic dilation theta is empty");if(trial)Need(nhi>nlo,"Nonuniform-n witness empty");if(trial==2){Need(drms>100*brms&&witness>0,"Mode4 Eq24-versus-J difference unresolved");signalRatio=drms/brms;}
      summary<<trial<<','<<Count<<','<<np-Count<<','<<trms<<','<<nhi-nlo<<','<<drms<<','<<brms<<','<<witness<<','<<mt<<','<<mi<<'\n';maxThetaRatio=(std::max)(maxThetaRatio,mt);maxIdentityRatio=(std::max)(maxIdentityRatio,mi);
      PosInteraction_Forces();InterStep=initialstage;Restore(baseline);Need(Bytes(Capture(),true)==basebytes&&FixedDt->GetDtError(false)==dtError&&!Acec&&!Arc&&!BoundDerivativeVelc&&!PosPrec&&!PoroJPrec,"Scratch release / baseline normal restoration failed");
    }
    Need(rows==1536&&copychecks>0&&!TimeStep&&!Nstep&&DynamicConductivitySpeedMax==0,"Coverage/clock/constant-law cache guard failed");csv.flush();summary.flush();Need(bool(csv)&&bool(summary),"Frozen operator CSV write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_porosity_operator_r1\",\"passed\":true,\"cases\":3,\"native_count\":512,\"rows\":"<<rows<<",\"actual_force_calls\":3,\"periodic_copy_checks\":"<<copychecks<<",\"max_theta_error_over_prior_budget\":"<<maxThetaRatio<<",\"max_identity_error_over_prior_budget\":"<<maxIdentityRatio<<",\"nonuniform_difference_RMS_over_prior_budget\":"<<signalRatio<<",\"same_nonuniform_C_bitexact\":true,\"normal_state_restored_byte_exact\":true,\"constant_k_law_OFF\":true,\"Run_or_ComputeStep_or_SaveData_called\":false,\"physical_steps\":0,\"physical_acceptance\":false,\"input_hashes_owned_by_wrapper\":true}\n";done.flush();Need(bool(done),"Operator completion write failed");
  }
};
}
int main(int argc,char** argv){try {
  Need(argc==5&&std::string(argv[1])=="--input"&&std::string(argv[3])=="--out","Use --input SEALED_CONSTANT_CPU_XML --out NEW_DIR");const fs::path xml=argv[2],out=argv[4];auto prefix=xml;prefix.replace_extension();Need(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&!fs::exists(out),"Existing unchanged seed and fresh output required");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],"-cpu","-ompthreads:1","-stable",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> pointers;for(auto& a:args)pointers.push_back(a.data());JSphCfgRun cfg;cfg.LoadArgv(int(pointers.size()),pointers.data());Need(cfg.Cpu&&cfg.OmpThreads==1&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No restart/clock override admitted");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");porosityop::Operator fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Frozen porosity operator rejected; preserve evidence\n";return 2;}}
