// Current-state CPU necessary scales only; no cell search, force or integration calls.
#define main RetainedGravityScalesFeedbackMain
#include "upl_p2_feedback_harness_r1.cpp"
#undef main
#include <limits>

class GravityScales:public Feedback {
public:
  GravityScales():Feedback(2,9){DynamicPorePressure=true;VelMax=ViscDtMax=AceMax=0;PoreDtSafety=.1f;}
  void Check(unsigned gid,bool positiveK,bool law,bool standard,std::ostream& states,std::ostream& ledger){
    const tfloat3 gravities[]={TFloat3(0),TFloat3(0,0,-8),TFloat3(0,0,-16),TFloat3(-4,0,-8),TFloat3(0,0,-9.80665f)};
    Require(gid<5&&Np==9&&Npb==0,"Undeclared scale fixture state");
    Gravity=gravities[gid];CSP.gravity=Gravity;SoilCte.HydraulicConductivity=positiveK?1e-5f:0.f;
    DynamicPoreConductivity=law;DynamicPoreConductivityCk=.125;VelMax=ViscDtMax=AceMax=0;PoreDtSafety=.1f;
    InitPorosityObserverCpu();for(unsigned p=0;p<Np;p++){PoroJc[p]=1.+.005*double(p)/double(Np-1);PoroThetac[p]=0;}
    const double eps=std::numeric_limits<double>::epsilon(),tol=128.*eps;
    const double n0=double(SoilCte.Porosity),solid0=1.-n0,rho0=double(RhopZero),rhow=double(SoilCte.PoreWaterRho);
    const double rhos=(rho0-n0*rhow)/solid0,v0=double(MassFluid)/rho0,kw=double(SoilCte.PoreWaterBulkModulus),k0=double(SoilCte.HydraulicConductivity);
    const double m=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;
    // hypot is independent of production's explicit squared-component norm.
    const double gnorm=std::hypot(double(Gravity.x),double(Gravity.z));
    const double gamma=rhow*(standard||gnorm==0?9.80665:gnorm),alternate=rhow*(standard&&gnorm>0?gnorm:9.80665);
    double cu2max=0,bkmax=0,minMargin=std::numeric_limits<double>::max(),maxLedger=0;
    for(unsigned p=0;p<Np;p++){
      Require(CODE_IsNormal(Codec[p])&&CODE_IsFluid(Codec[p]),"Scale helper would skip an intended native");
      const double j=PoroJc[p],n=1.-solid0/j,V=v0*j,rho=(1.-n)*rhos+n*rhow;
      const double ki=positiveK?(law?k0*std::exp((j-1.)/(solid0*.125)):k0):0.;
      double actualN,actualV,actualRho;GetPorosityFeedbackStateCpu(p,actualN,actualV,actualRho);const double actualK=GetDynamicConductivityCpu(p);
      const double got[]={actualN,actualV,actualRho,actualK},wanted[]={n,V,rho,ki};
      for(unsigned c=0;c<4;c++){
        Require(std::isfinite(got[c])&&std::isfinite(wanted[c]),"Nonfinite state ledger");
        if(wanted[c]==0)Require(got[c]==0,"Zero-k degeneration changed");
        else{const double relative=std::fabs(got[c]-wanted[c])/std::fabs(wanted[c]);Require(relative<=tol,"Independent constituent-state ledger budget failed");maxLedger=(std::max)(maxLedger,relative);}
      }
      Require(j>=1.&&j<=1.005&&n>0&&n<1&&rho>0&&V>0&&ki>=0,"Manufactured state domain failed");
      const double b=kw/n,cu2=(m+b)/rho,margin=rho*b/(m+b)-rhow;
      Require(std::isfinite(cu2)&&cu2>0,"Invalid independent acoustic scale");
      // Strict RH applies only to positive k; k0 is the separate degenerate case.
      if(positiveK)Require(margin>64.*eps*(std::max)(rho,rhow),"Fixture must be safely inside positive-k continuous domain");
      cu2max=(std::max)(cu2max,cu2);bkmax=(std::max)(bkmax,b*ki);minMargin=(std::min)(minMargin,margin);
      ledger<<gid<<','<<positiveK<<','<<law<<','<<Idpc[p]<<','<<j<<','<<actualN<<','<<n<<','<<actualV<<','<<V<<','<<actualRho<<','<<rho<<','<<actualK<<','<<ki<<','<<cu2<<','<<b*ki/gamma<<','<<margin<<'\n';
    }
    const double h=double(KernelH),safety=double(PoreDtSafety),wantedWave=h/std::sqrt(cu2max),dmax=bkmax/gamma;
    const double wantedPore=positiveK?safety*h*h/dmax:std::numeric_limits<double>::max();
    const double alternatePore=positiveK?safety*h*h/(bkmax/alternate):std::numeric_limits<double>::max();
    double wave=0,pore=0;GetDynamicStepScalesCpu(wave,pore);
    const double waveLimit=tol*std::fabs(wantedWave),waveError=std::fabs(wave-wantedWave);
    Require(std::isfinite(wave)&&wave>0&&waveError<=waveLimit,"Actual wave scale exceeds prior double relative budget");
    double poreLimit=0,poreError=0,separation=0,inferredGamma=0;
    if(positiveK){
      poreLimit=tol*std::fabs(wantedPore);poreError=std::fabs(pore-wantedPore);
      Require(std::isfinite(pore)&&pore>0&&poreError<=poreLimit,"Actual pore scale differs from selected independent gamma oracle");
      separation=std::fabs(wantedPore-alternatePore)/poreLimit;
      if(gnorm>0)Require(separation>10.,"Nonzero-gravity mobility policies are not distinguishable above prior budget");
      inferredGamma=pore*bkmax/(safety*h*h); // Diagnostic inversion, not direct production gamma telemetry.
    }else Require(pore==std::numeric_limits<double>::max(),"k0 pore scale must be exact DBL_MAX");
    states<<gid<<','<<Gravity.x<<','<<Gravity.y<<','<<Gravity.z<<','<<positiveK<<','<<law<<','<<(standard?"standard":"norm")<<','<<k0<<','<<gamma<<','<<alternate<<','<<cu2max<<','<<dmax<<','<<minMargin<<','<<wave<<','<<wantedWave<<','<<waveLimit<<','<<waveError/waveLimit<<','<<pore<<','<<wantedPore<<','<<poreLimit<<','<<(positiveK?poreError/poreLimit:0.)<<','<<alternatePore<<','<<separation<<','<<inferredGamma<<','<<maxLedger<<'\n';
  }
};

int main(int argc,char** argv){try{
  Require(argc==5&&std::string(argv[1])=="--out"&&std::string(argv[3])=="--gamma-policy","Use --out NEW_DIRECTORY --gamma-policy norm|standard");
  const std::string policy=argv[4];Require(policy=="norm"||policy=="standard","Unknown gamma oracle policy");
  const fs::path out(argv[2]);Require(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output with existing parent required");
  AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
  std::ofstream states(out/"scales.csv"),ledger(out/"ledger.csv");states<<std::setprecision(17);ledger<<std::setprecision(17);
  states<<"gravity_id,gx,gy,gz,positive_k,smooth_law,gamma_policy,k0,gamma_oracle,gamma_alternate,max_cu2_reference,max_D_reference,min_continuous_margin,wave_actual,wave_reference,wave_limit,wave_error_over_limit,pore_actual,pore_reference,pore_limit,pore_error_over_limit,pore_alternate,alternate_pore_separation_over_limit,gamma_inferred_from_actual_pore,max_state_ledger_relative_error\n";
  ledger<<"gravity_id,positive_k,smooth_law,native_id,J,n_actual,n_reference,V_actual,V_reference,rho_actual,rho_constituent_reference,k_actual,k_reference,cu2_reference,D_reference,continuous_margin\n";
  GravityScales fixture;unsigned cases=0;for(unsigned gid=0;gid<5;gid++)for(bool positiveK:{false,true})for(bool law:{false,true}){fixture.Check(gid,positiveK,law,policy=="standard",states,ledger);cases++;}
  states.flush();ledger.flush();Require(cases==20&&states&&ledger,"Scale output/declared coverage failed");
  std::ofstream done(out/"completion.json");done<<"{\"passed\":true,\"stage\":\"upl_gravity_scales_r1\",\"gamma_policy\":\""<<policy<<"\",\"gamma_policy_changes_oracle_only\":true,\"cases\":20,\"native_count\":9,\"ledger_rows\":180,\"actual_step_scale_calls\":20,\"actual_state_ledger_calls\":180,\"gravity_states\":5,\"positive_k_cases\":10,\"zero_k_cases\":10,\"nonzero_gravity_policy_discrimination_cases\":8,\"prior_double_relative_budget_eps\":128,\"k0_DBL_MAX_exact\":true,\"strict_domain_checked_only_for_positive_k\":true,\"reference_density_from_constituents\":true,\"cell_or_neighbor_or_force_called\":false,\"actual_Run_or_ComputeStep_called\":false,\"completed_physical_steps\":0,\"production_modified\":false,\"public_gravity_accepted\":false,\"sufficient_stability_proved\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Scale completion write failed");
  std::cout<<"Current-state gravity scale component passed; no force, integration or physical acceptance.\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Scale component rejected; preserve partial output\n";return 2;}}
