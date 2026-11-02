// Frozen case02 projected force/rate Jacobian. No Run, ComputeStep or constitutive update.
#define main RetainedCase02OperatorNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JDsFixedDt.h"
#include "JLog2.h"

namespace case02op {
constexpr unsigned Soil=1000,Fixed=40,Total=1040,Layers=100,Channels=5;
static const char* Names[Channels]={"az","Rsigma_zz","pdot","theta","pdot_noAce"};
static const char* Inputs[3]={"vz","sigma_zz","p"};
struct Response {
  std::array<std::array<double,Layers>,Channels> mean{},spread{};
  std::array<double,Channels> peak{};
};
struct Column {unsigned family,layer;double amplitude;};
class Operator:public JSphCpuSingle {
  std::array<tdouble3,Total> X0{};
  std::array<int,Total> Layer{};
  std::array<tmatrix3d,Soil> FrozenC{};
  std::array<unsigned,Soil> FrozenFS{};
  unsigned Calls=0,NoAceCalls=0,GhostChecks=0,Rows=0;
  double MaxSpreadRatio=0,MaxOddRatio=0,MaxScaleRatio=0;
  double Locked=0,OriginalLast=0,OriginalError=0,LambdaOverM=0;
  bool HaveFrozenC=false;
  std::ofstream Responses,Checks;
  std::vector<unsigned> Owners()const {
    std::vector<unsigned> map(Total,~0u);unsigned fixed=0,soil=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Need(Idpc[p]<Total&&map[Idpc[p]]==~0u,"Duplicate/invalid normal case02 owner");map[Idpc[p]]=p;
      if(Idpc[p]<Fixed){Need(CODE_IsFixed(Codec[p]),"Fixed ID not fixed");fixed++;}
      else{Need(CODE_IsFluid(Codec[p]),"Soil ID not fluid");soil++;}
    }
    Need(fixed==Fixed&&soil==Soil&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Incomplete/excluded case02 owners");
    for(unsigned p:map)Need(p!=~0u,"Missing case02 owner");
    return map;
  }
  void Clock()const {
    Need(!TimeStep&&!Nstep&&SymplecticDtPre==Locked&&LastDt==OriginalLast&&FixedDt->GetDtError(false)==OriginalError
      &&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Frozen component advanced clock/history");
  }
  std::vector<byte> SoilInput()const {
    std::vector<byte> bytes;auto add=[&](const auto& value){const byte* p=reinterpret_cast<const byte*>(&value);bytes.insert(bytes.end(),p,p+sizeof(value));};
    const auto map=Owners();
    for(unsigned id=0;id<Total;id++){const unsigned p=map[id];Need(!std::memcmp(Posc+p,&X0[id],sizeof(tdouble3)),"Initial geometry moved");
      add(Idpc[p]);add(Codec[p]);add(Dcellc[p]);add(Posc[p]);
      if(id>=Fixed){add(Velrhopc[p]);add(Sigmac[p]);add(PoroJc[p]);add(PorePressc[p]);add(PorePress0c[p]);add(Kplasticc[p]);}
      else Need(Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0,"Physical fixed wall moved");
    }return bytes;
  }
  void Reset(int family,int layer,double amplitude) {
    Need(!Acec&&!Arc&&!Rsigmac&&!HydroMechTopLoadRawc&&!BoundDerivativeVelc,"Prior force scratch still live");Clock();
    const auto map=Owners();
    // Only normal soil basis values are manufactured. Real periodic cloning and wall MLS supply every copy/sample.
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=map[id];const double value=(Layer[id]==layer?amplitude:0.);
      Velrhopc[p]=TFloat4(0,0,float(family==0?value:0.),RhopZero);
      const double stress=(family==1?value:0.);Sigmac[p]=TSymMatrix3d(LambdaOverM*stress,0,0,LambdaOverM*stress,0,stress);
      PorePressc[p]=float(family==2?value:0.);PorePress0c[p]=0;Kplasticc[p]=0;PoroJc[p]=1.;PoroThetac[p]=0.;PorePressRatec[p]=0;HydroMechLoadAcec[p]=TFloat3(0);
    }
    RunCellDivide(true); // Standard retire/regenerate/sort; no stale periodic basis data.
    std::fill(PorePressRatec,PorePressRatec+Np,0.f); // Defined derivative output, not a wall pressure/state replacement.
    Clock();const auto fresh=Owners();
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){Need(Idpc[p]<Total,"Invalid periodic input ID");const unsigned q=fresh[Idpc[p]];
      Need(CODE_IsFluid(Codec[p])&&!std::memcmp(Velrhopc+p,Velrhopc+q,sizeof(tfloat4))
        &&!std::memcmp(Sigmac+p,Sigmac+q,sizeof(tsymatrix3d))&&PorePressc[p]==PorePressc[q]&&PoroJc[p]==PoroJc[q],"Actual periodic input clone differs");
    }
  }
  static double Budget(double magnitude){return 64.*FLT_EPSILON*(std::max)(1.,magnitude)+256.*DBL_EPSILON*(std::max)(1.,magnitude);}
  Response Force(int family,int layer,double amplitude,bool zero) {
    Reset(family,layer,amplitude);const auto before=SoilInput();const unsigned count=Np;
    Interaction_Forces(INTERSTEP_SymPredictor);Calls++;
    Need(Np==count&&SoilInput()==before,"Actual force changed normal soil inputs/geometry");Clock();
    const auto map=Owners();
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=map[id];
      if(HaveFrozenC)Need(!std::memcmp(CorrMatc+p,&FrozenC[id-Fixed],sizeof(tmatrix3d))&&FSTypec[p]==FrozenFS[id-Fixed],"Initial geometry/J did not freeze C/classification");
      else{FrozenC[id-Fixed]=CorrMatc[p];FrozenFS[id-Fixed]=FSTypec[p];}
      Need(PoroJc[p]==1.&&PorePress0c[p]==0&&Kplasticc[p]==0&&HydroMechLoadAcec[p].x==0&&HydroMechLoadAcec[p].y==0&&HydroMechLoadAcec[p].z==0,"Nonzero t0 external source / changed elastic inputs");
      if(zero)Need(Acec[p].x==0&&Acec[p].y==0&&Acec[p].z==0&&Rsigmac[p].xx==0&&Rsigmac[p].xy==0&&Rsigmac[p].xz==0&&Rsigmac[p].yy==0&&Rsigmac[p].yz==0&&Rsigmac[p].zz==0&&PorePressRatec[p]==0&&PoroThetac[p]==0,"Zero-state true force/rate is nonzero");
    }HaveFrozenC=true;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){Need(Idpc[p]<Total,"Invalid periodic response ID");const unsigned q=map[Idpc[p]];
      Need(!std::memcmp(PoroJc+p,PoroJc+q,sizeof(double))&&!std::memcmp(CorrMatc+p,CorrMatc+q,sizeof(tmatrix3d))
        &&!std::memcmp(Acec+p,Acec+q,sizeof(tfloat3))&&!std::memcmp(PoroThetac+p,PoroThetac+q,sizeof(double))
        &&!std::memcmp(PorePressRatec+p,PorePressRatec+q,sizeof(float)),"Actual completed periodic owner extension differs");GhostChecks++;
    }
    double wave,pore;GetDynamicStepScalesCpu(wave,pore); // Retains production saturation and positive-k RH guards.
    Need(std::isfinite(wave)&&wave>0&&std::isfinite(pore)&&pore>0&&DynamicConductivitySpeedMax==0,"Frozen constant-k scales/cache invalid");
    const std::vector<tfloat3> ace(Acec,Acec+Np);const std::vector<float> rate(PorePressRatec,PorePressRatec+Np);
    const double cache=DynamicConductivitySpeedMax;
    std::fill(Acec,Acec+Np,TFloat3(0));ComputeDynamicPorePressureRateCpu();NoAceCalls++;
    const std::vector<float> noace(PorePressRatec,PorePressRatec+Np);
    memcpy(Acec,ace.data(),Np*sizeof(tfloat3));memcpy(PorePressRatec,rate.data(),Np*sizeof(float));DynamicConductivitySpeedMax=cache;
    Need(!std::memcmp(Acec,ace.data(),Np*sizeof(tfloat3))&&!std::memcmp(PorePressRatec,rate.data(),Np*sizeof(float))&&SoilInput()==before,"NoAce diagnostic failed to restore scratch/inputs");
    Response result;std::array<unsigned,Layers> hits{};
    std::array<std::array<double,Layers>,Channels> lo,hi;for(auto& a:lo)a.fill(DBL_MAX);for(auto& a:hi)a.fill(-DBL_MAX);
    for(unsigned id=Fixed;id<Total;id++){const unsigned p=map[id],z=unsigned(Layer[id]);hits[z]++;
      const double v[Channels]={double(Acec[p].z),double(Rsigmac[p].zz),double(PorePressRatec[p]),PoroThetac[p],double(noace[p])};
      for(unsigned c=0;c<Channels;c++){Need(std::isfinite(v[c]),"Nonfinite true operator response");result.mean[c][z]+=v[c];lo[c][z]=(std::min)(lo[c][z],v[c]);hi[c][z]=(std::max)(hi[c][z],v[c]);result.peak[c]=(std::max)(result.peak[c],std::fabs(v[c]));}
    }
    for(unsigned z=0;z<Layers;z++){Need(hits[z]==10,"Not ten normal columns per material layer");
      for(unsigned c=0;c<Channels;c++){result.mean[c][z]/=10.;result.spread[c][z]=hi[c][z]-lo[c][z];
        const double ratio=result.spread[c][z]/Budget(result.peak[c]);MaxSpreadRatio=(std::max)(MaxSpreadRatio,ratio);Need(ratio<=1.,"Layer-column spread exceeds declared arithmetic projection budget (not a physical-instability proof)");}
      const double compression=-double(SoilCte.PoreWaterBulkModulus)/double(SoilCte.Porosity)*result.mean[3][z];
      Responses<<Calls<<','<<(family<0?"zero":Inputs[family])<<','<<layer<<','<<amplitude<<','<<z;
      for(unsigned c=0;c<Channels;c++)Responses<<','<<result.mean[c][z]<<','<<result.spread[c][z]<<','<<result.peak[c]<<','<<Budget(result.peak[c]);
      Responses<<','<<compression<<','<<result.mean[4][z]-compression<<','<<result.mean[2][z]-result.mean[4][z]<<','<<wave<<','<<pore<<'\n';Rows++;
    }
    PosInteraction_Forces();Need(!Acec&&!Arc&&!Rsigmac&&!BoundDerivativeVelc&&!HydroMechTopLoadRawc,"Force scratch not released");Clock();return result;
  }
  void Pair(const Column& b,const Response& plus,const Response& minus,std::vector<double>& matrix,std::vector<double>& theta,unsigned column) {
    double oddmax=0;
    for(unsigned c=0;c<Channels;c++)for(unsigned z=0;z<Layers;z++){
      const double error=std::fabs(plus.mean[c][z]+minus.mean[c][z]),budget=Budget((std::max)(plus.peak[c],minus.peak[c]));
      oddmax=(std::max)(oddmax,error/budget);
      if(c<3)matrix[(c*Layers+z)*300+column]=(plus.mean[c][z]-minus.mean[c][z])/(2*b.amplitude);
      if(c==3)theta[z*300+column]=(plus.mean[c][z]-minus.mean[c][z])/(2*b.amplitude);
    }
    MaxOddRatio=(std::max)(MaxOddRatio,oddmax);Checks<<column<<','<<Inputs[b.family]<<','<<b.layer<<','<<b.amplitude<<','<<oddmax;
    Need(oddmax<=1.,"Central oddness exceeds declared arithmetic probe budget (not a trajectory failure)");
  }
public:
  Operator(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,bool smoke) {
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();RunCellDivide(true);
    Need(HydroMech&&PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&!DynamicPoreConductivity&&!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0,"Only private complete constant-k case02 model");
    Need(Simulate2D&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&!CaseNmoving&&!CaseNfloat&&!PartBegin&&TStep==STEP_Symplectic&&TKernel==KERNEL_Wendland&&PeriX&&!PeriY&&!PeriZ&&PeriXinc.y==0&&PeriXinc.z==0&&std::fabs(std::fabs(PeriXinc.x)-.1)<=64.*DBL_EPSILON*.1&&Gravity==TFloat3(0)&&CSP.gravity==Gravity&&OmpThreads==1,"Only actual g0 X-periodic fixed-bottom case02 geometry");
    Need(TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&HydroMechInitMode==HMINIT_None&&HydroMechTopLoadMode==HMLOAD_TopKernelBand&&HydroMechTopLoadQ0==10000.f&&HydroMechTopLoadRampTime==.01&&HydroMechDrainage&&HydroMechDrainageStartTime==.01&&HydroMechDrainageFixedGrid&&!IsHydroMechDrainageActive(),"Expected future load/drain declarations with both inactive at t0");
    Need(!HourglassCpu&&!SoilHourglassXi&&!SoilBoundaryDerivativeSPR&&!SoilDamping&&!Visco&&TVisco==VISCO_Artificial&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!Shifting&&!NoPenetration&&!ArtificialStress&&TDensity==DDT_None&&!StrainSoftening&&!UseDEM&&!Symmetry&&!PoreShepardRegularization&&PoreCompressionGradCorr&&!PoreCompressionSourceMode&&SoilStressRateGradCorr,"Unsupported extra physics/derivative path");
    Need(JSph::Dp==.01&&KernelH==float(.018)&&RhopZero==2100.f&&MassFluid==float(.21)&&MassBound==MassFluid&&SoilCte.Porosity==float(.3)&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==2e8f&&SoilCte.HydraulicConductivity==float(.0001)&&SoilCte.ModulusK==1666666.75f&&SoilCte.ModulusG==769230.8125f&&PoreDtSafety==1,"Initial material differs from case02 candidate");
    Need(!TimeStep&&!Nstep&&!PosPrec&&!PoroJPrec&&FixedDt,"Initialization advanced state");Locked=SymplecticDtPre;OriginalLast=LastDt;OriginalError=FixedDt->GetDtError(false);
    const double bulk=SoilCte.ModulusK,shear=SoilCte.ModulusG;LambdaOverM=(bulk-2*shear/3)/(bulk+4*shear/3);
    const auto map=Owners();std::array<unsigned,Layers> count{};Layer.fill(-1);
    for(unsigned id=0;id<Total;id++){const unsigned p=map[id];X0[id]=Posc[p];
      Need(Posc[p].y==0&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==2100.f&&PorePressc[p]==0&&PorePress0c[p]==0&&PoroJc[p]==1.&&PoroThetac[p]==0&&Sigmac[p].xx==0&&Sigmac[p].xy==0&&Sigmac[p].xz==0&&Sigmac[p].yy==0&&Sigmac[p].yz==0&&Sigmac[p].zz==0&&(id<Fixed||Kplasticc[p]==0),"Input is not original J1/rest state");
      if(id>=Fixed){const int z=int(std::llround(Posc[p].z/.01-.5));Need(z>=0&&z<100&&std::fabs(Posc[p].z-(z+.5)*.01)<=1e-12,"Initial layer position differs");Layer[id]=z;count[z]++;}
      else Need(BoundNormalc[p].x==0&&BoundNormalc[p].y==0&&BoundNormalc[p].z>0,"Actual upward bottom normal required");
    }for(unsigned n:count)Need(n==10,"Initial layer population differs");
    Responses.open(fs::path(cfg->DirOut)/"responses.csv");Checks.open(fs::path(cfg->DirOut)/"linearity.csv");Responses<<std::setprecision(17);Checks<<std::setprecision(17);
    Responses<<"call,input_family,input_layer,input_amplitude,output_layer";for(const char* name:Names)Responses<<','<<name<<"_mean,"<<name<<"_column_spread,"<<name<<"_global_peak,"<<name<<"_arithmetic_budget";Responses<<",compression_from_theta,pressure_noAce_component,acceleration_component,wave_scale_s,pore_scale_s\n";
    Checks<<"column,input_family,input_layer,amplitude,max_odd_error_over_arithmetic_budget,max_half_amplitude_derivative_error_over_budget\n";
    Force(-1,-1,0,true);
    std::vector<Column> columns;if(smoke)columns={{0,99,double(float(.001))},{1,99,1.},{2,99,1.},{2,0,1.}};else for(unsigned c=0;c<3;c++)for(unsigned z=0;z<Layers;z++)columns.push_back({c,z,(c==0?double(float(.001)):1.)});
    std::vector<double> matrix(300*300,0),theta(100*300,0);
    for(unsigned col=0;col<columns.size();col++){const auto b=columns[col];const auto plus=Force(int(b.family),int(b.layer),b.amplitude,false),minus=Force(int(b.family),int(b.layer),-b.amplitude,false);
      Pair(b,plus,minus,matrix,theta,col);double scaleRatio=0;
      if(smoke){const auto hp=Force(int(b.family),int(b.layer),b.amplitude*.5,false),hm=Force(int(b.family),int(b.layer),-b.amplitude*.5,false);
        for(unsigned c=0;c<Channels;c++)for(unsigned z=0;z<Layers;z++){const double full=(plus.mean[c][z]-minus.mean[c][z])/(2*b.amplitude),half=(hp.mean[c][z]-hm.mean[c][z])/b.amplitude;
          scaleRatio=(std::max)(scaleRatio,std::fabs(full-half)/Budget((std::max)(std::fabs(full),std::fabs(half))));}
        Need(scaleRatio<=1.,"Amplitude linearity exceeds declared arithmetic probe budget (not a physical-instability proof)");
      }MaxScaleRatio=(std::max)(MaxScaleRatio,scaleRatio);Checks<<','<<scaleRatio<<'\n';
    }
    if(!smoke){std::ofstream jac(fs::path(cfg->DirOut)/"jacobian.csv"),th(fs::path(cfg->DirOut)/"theta_jacobian.csv"),shape(fs::path(cfg->DirOut)/"basis.csv");jac<<std::setprecision(17);th<<std::setprecision(17);
      jac<<"row,output_family,output_layer";th<<"output_layer";for(unsigned col=0;col<300;col++){jac<<",c"<<col;th<<",c"<<col;}jac<<'\n';th<<'\n';shape<<"column,input_family,input_layer,amplitude\n";
      for(unsigned col=0;col<300;col++)shape<<col<<','<<Inputs[columns[col].family]<<','<<columns[col].layer<<','<<columns[col].amplitude<<'\n';
      for(unsigned row=0;row<300;row++){jac<<row<<','<<Names[row/100]<<','<<row%100;for(unsigned col=0;col<300;col++)jac<<','<<matrix[row*300+col];jac<<'\n';}
      for(unsigned row=0;row<100;row++){th<<row;for(unsigned col=0;col<300;col++)th<<','<<theta[row*300+col];th<<'\n';}
      jac.flush();th.flush();shape.flush();Need(bool(jac)&&bool(th)&&bool(shape),"Matrix CSV write failed");
    }
    Reset(-1,-1,0);Clock();Responses.flush();Checks.flush();Need(bool(Responses)&&bool(Checks),"Response CSV write failed");
    Need(Calls==(smoke?17u:601u)&&NoAceCalls==Calls&&Rows==100*Calls&&GhostChecks>0,"Declared force/response coverage differs");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_case02_operator_r1\",\"passed\":true,\"mode\":\""<<(smoke?"smoke":"matrix")<<"\",\"native_count\":1000,\"fixed_count\":40,\"layers\":100,\"columns_per_layer\":10,\"basis_columns\":"<<columns.size()<<",\"actual_force_calls\":"<<Calls<<",\"explicit_noAce_rate_calls\":"<<NoAceCalls<<",\"response_rows\":"<<Rows<<",\"matrix_rows\":"<<(smoke?0:300)<<",\"matrix_columns\":"<<(smoke?0:300)<<",\"periodic_owner_checks\":"<<GhostChecks<<",\"max_column_spread_over_arithmetic_budget\":"<<MaxSpreadRatio<<",\"max_oddness_over_arithmetic_budget\":"<<MaxOddRatio<<",\"max_half_amplitude_linearity_over_arithmetic_budget\":"<<MaxScaleRatio<<",\"zero_source_strict_zero\":true,\"soil_inputs_force_unchanged\":true,\"frozen_C_and_classification_exact\":true,\"NoAce_scratch_restored_byte_exact\":true,\"wall_state_and_periodic_copies_from_production\":true,\"normal_soil_basis_only\":true,\"manufactured_not_evolved_trajectory\":true,\"actual_time_s\":0,\"completed_physical_steps\":0,\"Run_ComputeStep_SaveData_called\":false,\"nonzero_load_or_drain_event_tested\":false,\"integrator_stability_proven\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Need(argc==6&&(std::string(argv[1])=="--smoke"||std::string(argv[1])=="--matrix")&&std::string(argv[2])=="--input"&&std::string(argv[4])=="--out","Use --smoke|--matrix --input EXISTING_XML --out NEW_DIR");
  const fs::path xml=argv[3],out=argv[5];auto prefix=xml;prefix.replace_extension();Need(fs::is_regular_file(xml)&&fs::is_regular_file(prefix.string()+".bi4")&&!fs::exists(out),"Existing unchanged case02 input and fresh output required");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<std::string> args={argv[0],"-cpu","-ompthreads:1","-stable","-mdbc_freeslip",prefix.string(),out.string(),"-dirdataout","data","-svres"};std::vector<char*> pointers;for(auto& a:args)pointers.push_back(a.data());JSphCfgRun cfg;cfg.LoadArgv(int(pointers.size()),pointers.data());
  Need(cfg.Cpu&&cfg.OmpThreads==1&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"No restart/integration/clock override admitted");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");case02op::Operator fixture;fixture.Execute(&cfg,AppInfo.LogPtr(),std::string(argv[1])=="--smoke");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Frozen case02 operator rejected; preserve partial component outputs\n";return 2;}}

