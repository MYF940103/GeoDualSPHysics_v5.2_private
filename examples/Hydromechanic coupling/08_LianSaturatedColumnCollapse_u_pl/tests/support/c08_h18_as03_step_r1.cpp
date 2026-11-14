// One original CPU step from one separately selected saved late state; no production TU hooks.
#define main c08_storage_rhs_unused_main
#include "../outputs/c08_h18_as03_step_r1_build/shared.inc"
#include "FunSoilMaterial.h"
#undef main

struct StepState{
  double j=0,theta=0,literal=0,hydraulic=0;float p=0,rate=0;unsigned fs=0;
  tdouble3 pos=TDouble3(0);tfloat3 vel=TFloat3(0),ace=TFloat3(0);
  tsymatrix3d sigma={0,0,0,0,0,0};tsymatrix3f rsigma={0,0,0,0,0,0};float kappa=0;
};
struct StepSum{
  unsigned count=0,capped=0;double dj=0,dp=0,hydraulic=0,cap=0,fp=0,defect=0,closure=0,budget=0,absclosure=0,absTerms=0,logdefect=0,maxlog=0;
};
class StepProbe:public Probe{
  double start=0,dt=0;unsigned completed=0,stageRows=0,materialRows=0,traceRows=0,sourcePart=0;
  void Clock()const{Need(Bits(TimeStep,start)&&unsigned(Nstep)==completed,"Original stage clock advanced early");}
  std::vector<unsigned> StageMap()const{
    Need(Np==Total&&Npb==Fixed,"One-step particle counts changed");std::vector<unsigned> b(Original,UINT_MAX);unsigned count=0;
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"One-step ID changed/excluded");b[id]=q;Need(id<Fixed?(q<Npb&&CODE_IsFixed(Codec[q])):(id>=2060&&q>=Npb&&CODE_IsFluid(Codec[q])),"One-step ownership changed");count+=id>=2060;}
    Need(count==Soil,"One-step soil coverage changed");Roles();return b;
  }
  std::vector<StepState> Capture(const char* name,double offset,bool force,std::ofstream& file,const std::vector<StepState>* base){
    Clock();const auto ids=StageMap();const bool pre=PosPrec!=NULL;
    Need(pre?VelrhopPrec&&SigmaPrec&&PorePressPrec&&PoroJPrec:!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Partial predictor ownership");
    if(force)Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc&&CorrMatc,"Original full-force scratch missing");
    const double kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,gamma=rho*9.80665;
    std::vector<StepState> out(Original);
    for(unsigned id=2060;id<Original;id++){const unsigned i=ids[id];Need(i!=UINT_MAX,"Missing tracked soil ID");auto& x=out[id];x.j=PoroJc[i];x.p=PorePressc[i];x.theta=PoroThetac[i];x.fs=FSTypec[i];x.pos=Posc[i];x.vel=TFloat3(Velrhopc[i].x,Velrhopc[i].y,Velrhopc[i].z);x.sigma=Sigmac[i];x.kappa=Kplasticc[i];
      Need(Finite(x.j)&&Finite(x.p)&&Finite(x.theta)&&Finite(x.pos)&&Finite(x.vel),"Nonfinite one-step primary state");
      if(pre){Need(base&&Bits(PorePressPrec[i],(*base)[id].p)&&Bits(PoroJPrec[i],(*base)[id].j),"Sorted predictor scalar base differs from p_n/J_n");Need(Bits(SigmaPrec[i],(*base)[id].sigma)&&Bits(Kplasticc[i],(*base)[id].kappa),"Sorted predictor sigma/kappa base differs from n state");}
      if(force){const auto all=Assemble(i);const auto& z=all[0];x.ace=Acec[i];x.rsigma=Rsigmac[i];const auto ai=ToTDouble3(x.ace);const bool sf=IsFreeSurfaceParticle(i,Codec,FSTypec);double n,v,rhot;GetPorosityFeedbackStateCpu(i,n,v,rhot);const double k=GetDynamicConductivityCpu(i),dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);
        const double lap=(sf?z.lp+rho*(ai.x*z.lx.x+ai.y*z.lx.y+ai.z*z.lx.z+z.da):z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da);
        const double chain=dk*(z.gradj.x*(z.gp.x+rho*ai.x)+z.gradj.y*(z.gp.y+rho*ai.y)+z.gradj.z*(z.gp.z+rho*ai.z));
        x.hydraulic=k/gamma*lap+chain/gamma;x.literal=kw/n*(-PoroThetac[i]+k/gamma*lap+chain/gamma);x.rate=PorePressRatec[i];
        const double castBudget=FLT_EPSILON*fabs(x.literal)+double(std::numeric_limits<float>::denorm_min());
        Need(Finite(x.ace)&&Finite(x.hydraulic)&&Finite(x.literal)&&Finite(x.rate)&&Bits(x.rate,float(x.literal))&&fabs(double(x.rate)-x.literal)<=castBudget,Detail("Original force literal/cast mismatch",sourcePart,id,x.rate,x.literal,castBudget));
      }
      file<<name<<','<<start<<','<<offset<<','<<completed<<','<<id<<','<<x.pos.x<<','<<x.pos.y<<','<<x.pos.z<<','<<x.vel.x<<','<<x.vel.y<<','<<x.vel.z<<','<<x.j<<','<<x.p<<','<<PorePress0c[i]<<','<<x.fs<<','<<x.theta<<','<<pre;
      if(pre)file<<','<<PoroJPrec[i]<<','<<PorePressPrec[i];else file<<",,";
      if(force)file<<','<<x.rate<<','<<x.literal<<','<<x.hydraulic<<','<<x.ace.x<<','<<x.ace.y<<','<<x.ace.z;else file<<",,,,,,";
      file<<','<<x.sigma.xx<<','<<x.sigma.yy<<','<<x.sigma.zz<<','<<x.sigma.xy<<','<<x.sigma.yz<<','<<x.sigma.xz<<','<<x.kappa;
      if(force)file<<','<<x.rsigma.xx<<','<<x.rsigma.yy<<','<<x.rsigma.zz<<','<<x.rsigma.xy<<','<<x.rsigma.yz<<','<<x.rsigma.xz;else file<<",,,,,,";
      file<<'\n';stageRows++;
    }file.flush();Need(bool(file),"Stage CSV write failed");return out;
  }
  static double Trace(const tsymatrix3d& s){return (s.xx+s.yy)+s.zz;}
  static double RateTrace(const tsymatrix3f& s){return (double(s.xx)+double(s.yy))+double(s.zz);}
  std::vector<fsoil::Result> MaterialShadow(const char* stage,double width,const std::vector<StepState>& n,
      const std::vector<StepState>& force,const std::vector<StepState>& committed,bool predictor,std::ofstream& file){
    std::vector<fsoil::Result> out(Original);const bool trigger=PartBegin&&StrainSoftening;
    for(unsigned id=2060;id<Original;id++){
      const auto& b=n[id];const auto& f=force[id];const auto& actual=committed[id];tsymatrix3d trial={0,0,0,0,0,0};
      trial.xx=b.sigma.xx+f.rsigma.xx*width;trial.yy=b.sigma.yy+f.rsigma.yy*width;trial.zz=b.sigma.zz+f.rsigma.zz*width;
      trial.xy=b.sigma.xy+f.rsigma.xy*width;trial.yz=b.sigma.yz+f.rsigma.yz*width;trial.xz=b.sigma.xz+f.rsigma.xz*width;
      const fsoil::State input={{trial.xx,trial.yy,trial.zz,trial.xy,trial.yz,trial.xz},b.kappa};
      const auto r=fsoil::EvaluateMaterial(input,SoilCte,DPCtes,StrainSoftening,trigger);Need(fsoil::CommitAllowed(r.status),"Shadow material return rejected");
      const tsymatrix3d expected={r.state.stress.xx,r.state.stress.xy,r.state.stress.xz,r.state.stress.yy,r.state.stress.yz,r.state.stress.zz};
      Need(Bits(actual.sigma,expected),Detail("Actual material sigma differs from same-input original shadow",sourcePart,id,Trace(actual.sigma),Trace(expected),0));
      const float expected_kappa=(predictor?b.kappa:r.state.kappa);Need(Bits(actual.kappa,expected_kappa),"Actual material kappa differs from original predictor/corrector policy");
      out[id]=r;file<<stage<<','<<id<<','<<start<<','<<width<<','<<completed<<','<<unsigned(r.status)<<','<<unsigned(r.reason)<<','<<trigger<<','<<b.kappa<<','<<r.kappa_continuous<<','<<r.state.kappa<<','<<actual.kappa<<','<<Trace(b.sigma)<<','<<Trace(trial)<<','<<Trace(actual.sigma)<<','<<r.trial_q<<','<<r.returned_q<<','<<r.lambda_shear<<','<<r.lambda_apex<<','<<r.lambda_tension<<','<<RateTrace(f.rsigma)<<','<<f.theta<<','<<SoilCte.ModulusK<<','<<SoilCte.ModulusG<<','<<Trace(actual.sigma)-Trace(trial)<<'\n';materialRows++;
    }file.flush();Need(bool(file),"Shadow material rows incomplete");return out;
  }
  void SameJP(const std::vector<StepState>& a,const std::vector<StepState>& b,const char* label)const{for(unsigned id=2060;id<Original;id++)Need(Bits(a[id].j,b[id].j)&&Bits(a[id].p,b[id].p),std::string(label)+" ID="+std::to_string(id));}
public:
  void ExecuteStep(const JSphCfgRun* cfg,JLog2* log,const Snapshot& a){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2 PRE/bedroles handoff differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original force scope differs");
    Need(!CaseNmoving&&!CaseNfloat&&!RelaxZones&&!InOut&&!ViscoTime&&!DDTRamp.x,"An omitted original step/outer-loop facility is active");
    Need(ArtificialStress&&ArtificialStressCoef==.3f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Original material/AS/AV/dt differs");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();Restore(a);start=a.time;completed=a.completed;sourcePart=a.part;dt=SymplecticDtPre;Need((a.part==38&&completed==2076001)||(a.part==76&&completed==2152001),"Only two selected completed onset states admitted");
    std::ofstream stages(pf::path(cfg->DirOut)/"stages.csv"),balance(pf::path(cfg->DirOut)/"balance.csv"),summary(pf::path(cfg->DirOut)/"summary.csv");for(auto f:{&stages,&balance,&summary}){Need(bool(*f),"Fresh CSV open failed");*f<<std::setprecision(17);}
    stages<<"stage,solver_time_s,stage_offset_s,solver_completed_step,native_id,x,y,z,vx,vy,vz,J,p_Pa,P0_Pa,FS,theta_s_1,PRE_owned,J_saved_base,p_saved_base,actual_rate_Pa_s,literal_rate_Pa_s,D_s_1,Acex,Acey,Acez,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kappa,Rsigma_xx,Rsigma_yy,Rsigma_zz,Rsigma_xy,Rsigma_yz,Rsigma_xz\n";
    const auto n=Capture("restored_n",0,false,stages,NULL);bool scratch=false;std::vector<StepState> fn,h,hdiv,fh,raw,next;double ddtp=0,ddtc=0;
    try{
      // Original ComputeStep_Sym call order; only read-only captures are inserted.
      DemDtForce=dt*0.5f;scratch=true;Interaction_Forces(INTERSTEP_SymPredictor);ddtp=DtVariable(false);fn=Capture("force_n",0,true,stages,NULL);Unchanged(a);SameJP(n,fn,"Predictor force changed J/p");
      ComputeSymplecticPre(dt);h=Capture("half_before_divide",dt*.5,false,stages,&n);PosInteraction_Forces();scratch=false;
      DemDtForce=dt;RunCellDivide(true);hdiv=Capture("half_after_divide",dt*.5,false,stages,&n);SameJP(h,hdiv,"Half divide changed J/p");
      scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);ddtc=DtVariable(true);fh=Capture("force_h",dt*.5,true,stages,&n);SameJP(hdiv,fh,"Corrector force changed J/p");
      ComputeSymplecticCorr(dt);raw=Capture("raw_full",dt,false,stages,NULL);PosInteraction_Forces();scratch=false;
      SymplecticDtPre=(std::min)(ddtp,ddtc);RunCellDivide(true);next=Capture("completed_cap",dt,false,stages,NULL);Map();Clock();
    }catch(...){if(scratch)PosInteraction_Forces();throw;}
    Need(Bits(ddtp,dt)&&Bits(ddtc,dt)&&Bits(SymplecticDtPre,dt),"Original fixed timestep changed");
    balance<<"native_id,force_h_group,FS_n,FS_force_n,FS_half_divide,FS_h,FS_completed,J_n,J_h,J_star,J_next,p_n,p_h,p_star,p_next,theta_n,theta_h,R_n,R_h,R_h_literal,D_h,delta_J,delta_p,delta_cap,c,hydraulic,cap,rate_cast_Pa_s,p_add_Pa,p_cast_Pa,p_update_residual_Pa,J_update_residual,source_order_residual,fp_predicted,balance_defect,closure_error,closure_budget,E_Pa,pre_contact_dx,pre_contact_dz,pre_contact_dvx,pre_contact_dvz,corr_contact_dx,corr_contact_dz,corr_contact_dvx,corr_contact_dvz\n";
    const double s=1.-double(SoilCte.Porosity),kw=SoilCte.PoreWaterBulkModulus,v0=double(MassFluid)/double(RhopZero);std::array<StepSum,3> sums;unsigned rows=0;
    for(unsigned id=2060;id<Original;id++){const auto& b=n[id];const auto& f=fn[id];const auto& m=fh[id];const auto& r=raw[id];const auto& q=next[id];
      double jp=b.j;jp+=dt*.5*b.j*f.theta;const float pp=float(double(b.p)+dt*.5*double(f.rate));double jc=b.j;jc+=dt*m.j*m.theta;const double pmul=dt*double(m.rate),padd=double(b.p)+pmul;const float pc=float(padd);
      Need(Bits(h[id].j,jp)&&Bits(h[id].p,pp)&&Bits(r.j,jc)&&Bits(r.p,pc)&&Bits(q.j,r.j),Detail("Original predictor/corrector J/p bits differ",sourcePart,id,r.p,pc,0));
      const float capExpected=((q.fs==2||q.fs==3)&&r.p>0?0.f:r.p);Need(Bits(q.p,capExpected),Detail("Completed positive-only FS cap differs",sourcePart,id,q.p,capExpected,0));
      const double dj=r.j-b.j,dp=double(q.p)-double(b.p),dcap=double(q.p)-double(r.p),c=(m.j-s)/kw,hyd=dt*m.j*m.hydraulic,cap=c*dcap;
      const double erate=double(m.rate)-m.literal,epadd=(padd-double(b.p))-pmul,epcast=double(r.p)-padd,ep=(double(r.p)-double(b.p))-pmul,ej=dj-dt*m.j*m.theta,esource=c*m.literal+m.j*m.theta-m.j*m.hydraulic;
      const double fp=ej+c*ep+dt*c*erate+dt*esource,defect=dj+c*dp-hyd-cap,closure=defect-fp;
      // Fixed arithmetic-only envelope, declared before execution; no physical tolerance.
      const double envelope=fabs(r.j)+fabs(b.j)+fabs(dj)+fabs(c*dp)+fabs(hyd)+fabs(cap)+fabs(ej)+fabs(c*ep)+fabs(dt*c*erate)+fabs(dt*esource)+fabs(dt*m.j*m.theta)+fabs(dt*c*m.literal)+fabs(dt*m.j*m.hydraulic);
      const double budget=RoundoffGamma(128)*envelope+128*std::numeric_limits<double>::denorm_min();
      Need(Finite(closure)&&Finite(budget)&&fabs(closure)<=budget,Detail("Discrete balance arithmetic closure failed",sourcePart,id,closure,0,budget));
      const double e=kw*(log1p((r.j-b.j)/(b.j-s))-(r.j-b.j)/(m.j-s));Need(Finite(e),"Nonfinite logarithmic compression quadrature defect");
      const float pvx=float(double(b.vel.x)+(double(f.ace.x)+Gravity.x)*dt*.5),pvz=float(double(b.vel.z)+(double(f.ace.z)+Gravity.z)*dt*.5),cvx=float(double(b.vel.x)+(double(m.ace.x)+Gravity.x)*dt),cvz=float(double(b.vel.z)+(double(m.ace.z)+Gravity.z)*dt);
      const double pdx=h[id].pos.x-(b.pos.x+double(b.vel.x)*dt*.5),pdz=h[id].pos.z-(b.pos.z+double(b.vel.z)*dt*.5),cdx=r.pos.x-(b.pos.x+(double(b.vel.x)+double(cvx))*dt*.5),cdz=r.pos.z-(b.pos.z+(double(b.vel.z)+double(cvz))*dt*.5);
      const bool sf=m.fs==2||m.fs==3;balance<<id<<','<<(sf?"FS":"interior")<<','<<b.fs<<','<<f.fs<<','<<hdiv[id].fs<<','<<m.fs<<','<<q.fs<<','<<b.j<<','<<m.j<<','<<r.j<<','<<q.j<<','<<b.p<<','<<m.p<<','<<r.p<<','<<q.p<<','<<f.theta<<','<<m.theta<<','<<f.rate<<','<<m.rate<<','<<m.literal<<','<<m.hydraulic<<','<<dj<<','<<dp<<','<<dcap<<','<<c<<','<<hyd<<','<<cap<<','<<erate<<','<<epadd<<','<<epcast<<','<<ep<<','<<ej<<','<<esource<<','<<fp<<','<<defect<<','<<closure<<','<<budget<<','<<e<<','<<pdx<<','<<pdz<<','<<double(h[id].vel.x)-pvx<<','<<double(h[id].vel.z)-pvz<<','<<cdx<<','<<cdz<<','<<double(r.vel.x)-cvx<<','<<double(r.vel.z)-cvz<<'\n';rows++;
      for(unsigned group:{0u,sf?2u:1u}){auto& z=sums[group];z.count++;z.capped+=dcap!=0;z.dj+=v0*dj;z.dp+=v0*c*dp;z.hydraulic+=v0*hyd;z.cap+=v0*cap;z.fp+=v0*fp;z.defect+=v0*defect;z.closure+=v0*closure;z.absclosure+=fabs(v0*closure);z.absTerms+=v0*(fabs(dj)+fabs(c*dp)+fabs(hyd)+fabs(cap)+fabs(fp));z.budget+=v0*budget;z.logdefect+=v0*e;z.maxlog=(std::max)(z.maxlog,fabs(e));}
    }
    summary<<"force_h_receiver_group,IDs,capped_IDs,sumV0_deltaJ,sumV0_c_deltaP,sumV0_hydraulic,sumV0_cap,sumV0_fp,sumV0_balance_defect,sumV0_closure,sumV0_abs_closure,sumV0_local_budget,aggregate_closure,aggregate_budget,sumV0_E_Pa_m2,max_abs_E_Pa\n";
    for(unsigned g=0;g<3;g++){const auto& z=sums[g];const double closure=z.dj+z.dp-z.hydraulic-z.cap-z.fp,budget=z.budget+RoundoffGamma(16*(z.count+1))*(z.absTerms+z.absclosure);Need(fabs(closure)<=budget,"Aggregate arithmetic closure failed");summary<<(g==0?"all":g==1?"interior":"FS")<<','<<z.count<<','<<z.capped<<','<<z.dj<<','<<z.dp<<','<<z.hydraulic<<','<<z.cap<<','<<z.fp<<','<<z.defect<<','<<z.closure<<','<<z.absclosure<<','<<z.budget<<','<<closure<<','<<budget<<','<<z.logdefect<<','<<z.maxlog<<'\n';}
    Need(rows==Soil&&stageRows==7*Soil&&sums[0].count==Soil&&sums[1].count+sums[2].count==Soil,"Exact one-step coverage differs");for(auto f:{&stages,&balance,&summary}){f->flush();Need(bool(*f),"Complete CSV write failed");}
    // Pure same-input material shadows run only after all original step calls; they never feed back.
    std::ofstream material(pf::path(cfg->DirOut)/"material_shadow.csv"),trace(pf::path(cfg->DirOut)/"trace_balance.csv");
    for(auto f:{&material,&trace}){Need(bool(*f),"Fresh trace/material output unavailable");*f<<std::setprecision(17);}
    material<<"stage,native_id,source_time_s,stage_width_s,source_completed_step,shadow_status,shadow_reason,trigger,kappa_n,kappa_continuous,shadow_kappa,actual_saved_kappa,I_n,I_trial,I_committed,q_trial,q_committed,lambda_shear,lambda_apex,lambda_tension,Rsigma_trace_Pa_s,theta_s_1,K_Pa,G_Pa,return_deltaI_Pa\n";
    const auto mh=MaterialShadow("half",dt*.5,n,fn,h,true,material);
    const auto mc=MaterialShadow("full",dt,n,fh,raw,false,material);
    trace<<"native_id,source_time_s,source_completed_step,dt_s,J_n,J_h,J_raw,I_n,I_trial_full,I_raw,Rsigma_trace_h_Pa_s,theta_h_s_1,delta_logJ,deltaI_over_3K,logJ_minus_elastic_trace,kinematic_log_quadrature,rate_trace_minus_3Ktheta_equivalent,trial_addition_roundoff_equivalent,return_trace_equivalent,closure,closure_budget,shadow_half_status,shadow_full_status,lambda_tension_full,kappa_n,kappa_next\n";
    double maxtrace=0;const double threeK=3.*double(SoilCte.ModulusK);
    for(unsigned id=2060;id<Original;id++){
      const auto& b=n[id];const auto& r=raw[id];const auto& f=fh[id];const auto& c=mc[id];
      const double in=Trace(b.sigma),it=c.trial_I,ir=Trace(r.sigma),rt=RateTrace(f.rsigma);
      const double dl=log1p((r.j-b.j)/b.j),elastic=(ir-in)/threeK,inferred=dl-elastic;
      const double quadrature=dl-dt*f.theta,rateMismatch=dt*(rt/threeK-f.theta),addition=((it-in)-dt*rt)/threeK,returned=(it-ir)/threeK;
      const double residual=inferred-(quadrature-rateMismatch-addition+returned);
      const double envelope=fabs(dl)+fabs(elastic)+fabs(inferred)+fabs(quadrature)+fabs(rateMismatch)+fabs(addition)+fabs(returned)+(fabs(in)+fabs(it)+fabs(ir)+fabs(dt*rt))/threeK+fabs(dt*f.theta);
      const double budget=RoundoffGamma(128)*envelope+128*std::numeric_limits<double>::denorm_min();
      Need(Finite(residual)&&Finite(budget)&&fabs(residual)<=budget,"Trace decomposition arithmetic closure failed");maxtrace=(std::max)(maxtrace,fabs(residual));
      trace<<id<<','<<start<<','<<completed<<','<<dt<<','<<b.j<<','<<h[id].j<<','<<r.j<<','<<in<<','<<it<<','<<ir<<','<<rt<<','<<f.theta<<','<<dl<<','<<elastic<<','<<inferred<<','<<quadrature<<','<<rateMismatch<<','<<addition<<','<<returned<<','<<residual<<','<<budget<<','<<unsigned(mh[id].status)<<','<<unsigned(c.status)<<','<<c.lambda_tension<<','<<b.kappa<<','<<r.kappa<<'\n';traceRows++;
    }material.flush();trace.flush();Need(bool(material)&&bool(trace)&&materialRows==2*Soil&&traceRows==Soil,"Complete trace/material write or coverage failed");
    // Outer Run owns these updates after the completed divide, never either substage.
    TimeStep+=dt;LastDt=dt;Nstep++;Need(Bits(TimeStep,start+dt)&&unsigned(Nstep)==completed+1,"One outer clock update differs");
    std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_as03_step_r1\",\"passed\":true,\"source_part\":"<<a.part<<",\"source_completed_step\":"<<completed<<",\"completed_step\":"<<unsigned(Nstep)<<",\"source_time_s\":"<<start<<",\"source_tau_s\":"<<start-GravityPreloadActualTime<<",\"completed_time_s\":"<<TimeStep<<",\"dt_s\":"<<dt<<",\"actual_force_calls\":2,\"actual_Darcy_calls\":2,\"physical_steps\":1,\"stage_rows\":"<<stageRows<<",\"balance_rows\":"<<rows<<",\"summary_rows\":3,\"original_step_calls\":true,\"material_shadow_rows\":10000,\"trace_balance_rows\":5000,\"all6_material_sigma_and_policy_kappa_bits_matched\":true,\"shadow_status_not_instrumented_original_status\":true,\"extra_material_evaluations_no_feedback\":10000,\"sorted_predictor_scalar_bases_bit_equal\":true,\"positive_only_completed_cap_verified\":true,\"contact_reaction_closed\":false,\"contact_primary_changes_observed_only\":true,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=11&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native"&&std::string(argv[4])=="--part","Use --check --native CLOSED_FULL301_NATIVE --part PART -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_N255_SEED FRESH_OUT");
  const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_as03n255_full3_r1/native_r1"),"Only sealed original N255 native admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);
  for(const char* leaf:{"c08_h18_as03n255_full3_r1.run.json","c08_h18_as03n255_full3_r1.call.json","c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json","c08_h18_as03_rhs_r1.check.json","c08_h18_as03_step_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);
  protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const unsigned requested=unsigned(std::stoul(argv[5]));Need((requested==38||requested==76)&&std::to_string(requested)==argv[5],"Only exact parts38/76 admitted");const unsigned selected=(requested==38?0:1);const Snapshot state(native,selected);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=6;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs"/("c08_h18_as03_step_r1_p"+std::to_string(requested)))&&!pf::exists(cfg.DirOut),"Original seed and fresh fixed one-step output required");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");StepProbe probe;probe.ExecuteStep(&cfg,AppInfo.LogPtr(),state);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Original one-step diagnostic failed; preserve outputs\n";return 2;}}
