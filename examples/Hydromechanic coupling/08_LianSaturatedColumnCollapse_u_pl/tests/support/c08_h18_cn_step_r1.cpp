// Author-only: one finite-Kw diagonal-CN pressure intervention in the original CPU step.
#include "../outputs/c08_h18_cn_step_r1_build/shared_step.inc"
#include <chrono>

struct QuadDonor{tdouble3 r,gi;double v,rr,p;std::array<double,3> w;};
struct CnRow{double S=0,M=0,s=0,pn=0,ph=0,rate=0,delta=0,next=0,den=0,budget=0;unsigned negative=0,fixed=0;};
struct UnchangedExceptPressure{
  unsigned id,fs;typecode code;tdouble3 pos; tfloat4 velocity;tsymatrix3d sigma;float kappa,p0,posdiv;double j,theta;tfloat3 normal,load;
};
static unsigned RowCoupledManufacture(std::ofstream& file){
  // Independent normalized two-node constant-matrix test, never a native midpoint field.
  const double M[2]={2.,3.},S[2]={6.,3.},A[2]={6.,3.},p[2]={2.,-1.};double R[2],LR[2];unsigned rows=0;
  for(unsigned i=0;i<2;i++)R[i]=(-S[i]*p[i]+A[i]*p[1-i])/M[i];
  for(unsigned i=0;i<2;i++)LR[i]=(-S[i]*R[i]+A[i]*R[1-i])/M[i];
  file<<"node,h_normalized_s,M,S,A_neighbor,p_n,explicit_R_n,explicit_p_h,neighbor_p_h,diagonal_CN_p_new,rational_delta,second_Taylor_delta,measured_third_defect,exact_rational_third_defect,arithmetic_closure,arithmetic_budget\n";
  for(double h:{.01,.001,.0001})for(unsigned i=0;i<2;i++){
    const unsigned j=1-i;const double ph=p[i]+.5*h*R[i],phj=p[j]+.5*h*R[j],s=S[i]/M[i],den=1.+.5*h*s;
    const double next=((M[i]/h-.5*S[i])*p[i]+A[i]*phj)/(M[i]/h+.5*S[i]);
    const double delta=(h*R[i]+.5*h*h*(A[i]/M[i])*R[j])/den,taylor=h*R[i]+.5*h*h*LR[i],defect=delta-taylor,exact=-.25*h*h*h*s*LR[i]/den;
    const double budget=RoundoffGamma(256)*(fabs(delta)+fabs(taylor)+fabs(exact))+256*std::numeric_limits<double>::denorm_min();
    const double additionBudget=RoundoffGamma(256)*(fabs(p[i])+fabs(next)+fabs(delta))+256*std::numeric_limits<double>::denorm_min();
    Need(Finite(defect)&&fabs(defect-exact)<=budget&&fabs((next-p[i])-delta)<=additionBudget,"Manufactured explicit-predictor diagonal-CN Taylor identity failed");
    file<<i<<','<<h<<','<<M[i]<<','<<S[i]<<','<<A[i]<<','<<p[i]<<','<<R[i]<<','<<ph<<','<<phj<<','<<next<<','<<delta<<','<<taylor<<','<<defect<<','<<exact<<','<<defect-exact<<','<<budget<<'\n';rows++;
  }return rows;
}

class CnStepProbe:public StepProbe{
  // This complete stencil method is byte-identical to the passed pressure-row fixture.
  std::vector<QuadDonor> Stencil(unsigned i,unsigned& fixed,unsigned& almost)const{
    std::vector<QuadDonor> out;fixed=almost=0;const double v0=double(MassFluid)/double(RhopZero);const auto ci=CorrMatc[i];
    for(unsigned group=0;group<2;group++){const bool boundary=group==1;const StNgSearch ngs=nsearch::Init(Dcellc[i],boundary,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned j=range.x;j<range.y;j++)if(CODE_IsFluid(Codec[j])||(boundary&&CODE_IsFixed(Codec[j]))){
          const tdouble3 d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=d.x*d.x+d.y*d.y+d.z*d.z;
          Need(Finite(rr)&&rr>=0,"Invalid squared donor distance");if(rr>double(KernelSize2))continue;if(rr<ALMOSTZERO){almost++;continue;}Need(rr>0,"Bare denominator must be positive");
          Need(!boundary||BoundModec[j]!=BMODE_MDBC2OFF,"Actual stencil contains disabled fixed donor");
          const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const tdouble3 g=d*fac,gi=Product(ci,g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j];
          Need(Finite(v)&&v>0&&Finite(gi)&&Finite(gj),"Invalid actual force donor volume/C/kernel");
          // r=xj-xi; weights use delta=qj-qi, hence minus the native dp weight.
          QuadDonor a;a.r=d*(-1.);a.gi=gi;a.v=v;a.rr=rr;a.p=PorePressc[j];
          a.w={{-v*Dot(d,gi+gj)/(rr+double(Eta2)),-2.*v*Dot(d,gi)/(rr+double(Eta2)),-2.*v*Dot(d,gi)/rr}};out.push_back(a);fixed+=boundary;
        }
      }
    }Need(!out.empty(),"Empty actual force stencil");return out;
  }
  static double RateBudget(const Sums& z,bool sf,double kw,double n,double k,double dk,double gamma,double rho,tdouble3 ai,double theta,double literal){
    const double B=kw/n;
    const double magnitude=B*fabs(theta)+B/gamma*(k*(z.lpabs+(sf?0:Dot(z.gpabs,z.lxabs))+rho*(z.daabs+(sf?Dot(Abs(ai),z.lxabs):0)))+dk*Dot(z.jabs,z.gpabs+Abs(ai)*rho));
    const double fbudget=FLT_EPSILON*fabs(literal)+double(std::numeric_limits<float>::denorm_min());
    // Exactly the original late-RHS operation-count envelope, not a physical tolerance.
    return fbudget+2*RoundoffGamma(64*(z.count+1))*magnitude;
  }
  std::vector<CnRow> MidpointRows(const std::vector<StepState>& n,const std::vector<StepState>& h,std::ofstream& file,std::ofstream& constant){
    const auto ids=StageMap();const double kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,gamma=rho*9.80665;std::vector<CnRow> out(Original);unsigned count=0;
    file<<"native_id,source_time_s,source_completed_step,dt_s,x_h,z_h,FS_h,fixed_donors,neighbors,almostzero_excluded,J_h,n_h,k_h,M_h,S_h,s_h,hS_over_M,p_n,p_h,R_h,row_R_h,row_error,original_rate_budget,negative_A,denominator,positive_denominator,CN_delta_double,CN_new_double,CN_row_residual,CN_row_budget\n";
    constant<<"native_id,s_h,dt_s,constant_rate_Pa_s,p_n,p_h,CN_delta,expected_delta,error,arithmetic_budget\n";
    for(unsigned id=2060;id<Original;id++){
      const unsigned i=ids[id];unsigned fixed,almost;const auto donors=Stencil(i,fixed,almost);const auto all=Assemble(i);const auto& z=all[0];const bool sf=IsFreeSurfaceParticle(i,Codec,FSTypec);double porosity,V,rhot;GetPorosityFeedbackStateCpu(i,porosity,V,rhot);const double k=GetDynamicConductivityCpu(i),dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);const auto ai=ToTDouble3(Acec[i]);
      Need(donors.size()==z.count&&fixed==all[2].count&&Bits(PorePressPrec[i],n[id].p)&&Bits(PorePressc[i],h[id].p)&&Bits(PoroJc[i],h[id].j),"Actual midpoint pressure/J/base or stencil differs");
      auto& row=out[id];row.M=gamma*porosity/kw;row.pn=n[id].p;row.ph=h[id].p;row.rate=h[id].rate;row.fixed=fixed;
      const tdouble3 u=z.lx*(sf?0.:-k)+z.gradj*dk;double P=0;for(const auto& d:donors){const double A=k*d.w[0]+d.v*Dot(d.gi,u);Need(Finite(A),"Nonfinite midpoint row coefficient");row.S+=A;P+=A*(d.p-row.ph);row.negative+=A<0;}
      Need(Finite(row.M)&&row.M>0&&Finite(row.S)&&Finite(P),"Invalid actual midpoint finite capacity/row");row.s=row.S/row.M;row.den=1.+.5*dt*row.s;Need(Finite(row.s)&&Finite(row.den)&&row.den!=0.,"Undefined diagonal-CN denominator; preserve failure, never clip");
      const double B=-gamma*PoroThetac[i]+k*rho*(z.da+(sf?Dot(ai,z.lx):0.))+dk*rho*Dot(z.gradj,ai),rate=(B+P)/row.M;
      const double budget=RateBudget(z,sf,kw,porosity,k,dk,gamma,rho,ai,PoroThetac[i],h[id].literal),error=fabs(rate-row.rate);Need(Finite(rate)&&error<=budget,"Complete actual midpoint row differs from original rate");
      row.delta=dt*(row.rate+row.s*(row.ph-row.pn))/row.den;row.next=row.pn+row.delta;
      const double left=(row.M/dt+.5*row.S)*row.delta,right=row.M*row.rate+row.S*(row.ph-row.pn),residual=left-right;
      row.budget=RoundoffGamma(128)*(fabs(left)+fabs(right)+fabs(row.M*row.rate)+fabs(row.S*(row.ph-row.pn)))+128*std::numeric_limits<double>::denorm_min();Need(Finite(row.delta)&&Finite(row.next)&&Finite(residual)&&fabs(residual)<=row.budget,"Finite-Kw diagonal-CN row identity failed");
      file<<id<<','<<start<<','<<completed<<','<<dt<<','<<Posc[i].x<<','<<Posc[i].z<<','<<FSTypec[i]<<','<<fixed<<','<<donors.size()<<','<<almost<<','<<h[id].j<<','<<porosity<<','<<k<<','<<row.M<<','<<row.S<<','<<row.s<<','<<dt*row.s<<','<<row.pn<<','<<row.ph<<','<<row.rate<<','<<rate<<','<<error<<','<<budget<<','<<row.negative<<','<<row.den<<','<<(row.den>0)<<','<<row.delta<<','<<row.next<<','<<residual<<','<<row.budget<<'\n';
      for(double R:{-2.5,0.,2.5}){const double pn=100.,ph=pn+.5*dt*R,delta=dt*(R+row.s*(ph-pn))/row.den,target=dt*R;
        const double envelope=fabs(delta)+fabs(target)+dt*fabs(R)+dt*fabs(row.s)*(fabs(ph)+fabs(pn));const double cb=RoundoffGamma(192)*envelope+192*std::numeric_limits<double>::denorm_min();Need(Finite(delta)&&fabs(delta-target)<=cb,"Constant spatial pressure and constant source were spuriously attenuated");constant<<id<<','<<row.s<<','<<dt<<','<<R<<','<<pn<<','<<ph<<','<<delta<<','<<target<<','<<delta-target<<','<<cb<<'\n';}
      count++;
    }file.flush();constant.flush();Need(count==5000&&bool(file)&&bool(constant),"Midpoint rows/constant-source coverage or write failed");return out;
  }
  std::vector<UnchangedExceptPressure> KeepPrimary()const{
    std::vector<UnchangedExceptPressure> out;out.reserve(Np);for(unsigned i=0;i<Np;i++)out.push_back({Idpc[i],FSTypec[i],Codec[i],Posc[i],Velrhopc[i],Sigmac[i],Kplasticc[i],PorePress0c[i],PosDivc[i],PoroJc[i],PoroThetac[i],FSNormalc[i],HydroMechLoadAcec[i]});return out;
  }
  void CheckPrimary(const std::vector<UnchangedExceptPressure>& old)const{
    Need(old.size()==Np,"Pressure-only intervention changed count");for(unsigned i=0;i<Np;i++){const auto& a=old[i];Need(Idpc[i]==a.id&&FSTypec[i]==a.fs&&Bits(Codec[i],a.code)&&Bits(Posc[i],a.pos)&&Bits(Velrhopc[i],a.velocity)&&Bits(Sigmac[i],a.sigma)&&Bits(Kplasticc[i],a.kappa)&&Bits(PorePress0c[i],a.p0)&&Bits(PosDivc[i],a.posdiv)&&Bits(PoroJc[i],a.j)&&Bits(PoroThetac[i],a.theta)&&Bits(FSNormalc[i],a.normal)&&Bits(HydroMechLoadAcec[i],a.load),"Pressure intervention changed a checked nonpressure field");}Roles();Clock();
  }
  void CommitCn(const std::vector<CnRow>& rows,const std::vector<StepState>& off){
    const auto ids=StageMap();const auto primary=KeepPrimary();std::vector<float> fixed(Npb);for(unsigned i=0;i<Npb;i++)fixed[i]=PorePressc[i];
    for(unsigned id=2060;id<Original;id++){const unsigned i=ids[id];const auto& r=rows[id];Need(Bits(PorePressc[i],off[id].p)&&Bits(off[id].p,float(r.pn+dt*r.rate)),"Original corrector explicit pressure commit changed before intervention");const float next=float(r.next);Need(Finite(next)&&fabs(double(next)-r.next)<=FLT_EPSILON*fabs(r.next)+double(std::numeric_limits<float>::denorm_min()),"Candidate final float cast failed");PorePressc[i]=next;}
    for(unsigned i=0;i<Npb;i++)Need(Bits(PorePressc[i],fixed[i]),"Candidate changed fixed pressure before original boundary rebuild");CheckPrimary(primary);
  }
public:
  void ExecuteCnStep(const JSphCfgRun* cfg,JLog2* log,const Snapshot& a){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2 PRE/bedroles handoff differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original force scope differs");
    Need(!CaseNmoving&&!CaseNfloat&&!RelaxZones&&!InOut&&!ViscoTime&&!DDTRamp.x,"An omitted original step/outer-loop facility is active");
    Need(ArtificialStress&&ArtificialStressCoef==.5f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Original material/AS/AV/dt differs");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();Restore(a);start=a.time;completed=a.completed;sourcePart=a.part;dt=SymplecticDtPre;Need(a.part==300&&completed==2600000,"Only sealed full3 Part300 admitted");
    std::ofstream stages(pf::path(cfg->DirOut)/"stages.csv"),rows(pf::path(cfg->DirOut)/"midpoint_rows.csv"),pressure(pf::path(cfg->DirOut)/"pressure.csv"),balance(pf::path(cfg->DirOut)/"balance.csv"),constant(pf::path(cfg->DirOut)/"constant_source.csv"),coupled(pf::path(cfg->DirOut)/"coupled_CN.csv");for(auto f:{&stages,&rows,&pressure,&balance,&constant,&coupled}){Need(bool(*f),"Fresh CN output unavailable");*f<<std::setprecision(17);}
    stages<<"stage,solver_time_s,stage_offset_s,solver_completed_step,native_id,x,y,z,vx,vy,vz,J,p_Pa,P0_Pa,FS,theta_s_1,PRE_owned,J_saved_base,p_saved_base,actual_rate_Pa_s,literal_rate_Pa_s,D_s_1,Acex,Acey,Acez,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,kappa,Rsigma_xx,Rsigma_yy,Rsigma_zz,Rsigma_xy,Rsigma_yz,Rsigma_xz\n";
    const auto n=Capture("restored_n",0,false,stages,NULL);bool scratch=false;std::vector<StepState> fn,h,hdiv,fh,off,on,next;std::vector<CnRow> midpoint;double ddtp=0,ddtc=0;
    try{
      // Original CPU call order, with actual midpoint row capture and one explicit pressure intervention.
      DemDtForce=dt*0.5f;scratch=true;Interaction_Forces(INTERSTEP_SymPredictor);ddtp=DtVariable(false);fn=Capture("force_n",0,true,stages,NULL);Unchanged(a);SameJP(n,fn,"Predictor force changed J/p");
      ComputeSymplecticPre(dt);h=Capture("half_before_divide",dt*.5,false,stages,&n);PosInteraction_Forces();scratch=false;
      DemDtForce=dt;RunCellDivide(true);hdiv=Capture("half_after_divide",dt*.5,false,stages,&n);SameJP(h,hdiv,"Half divide changed J/p");
      scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);ddtc=DtVariable(true);fh=Capture("force_h",dt*.5,true,stages,&n);SameJP(hdiv,fh,"Corrector force changed J/p");
      midpoint=MidpointRows(n,fh,rows,constant);
      ComputeSymplecticCorr(dt);off=Capture("raw_original_commit",dt,false,stages,NULL);
      CommitCn(midpoint,off);on=Capture("raw_CN",dt,false,stages,NULL);PosInteraction_Forces();scratch=false;
      SymplecticDtPre=(std::min)(ddtp,ddtc);RunCellDivide(true);next=Capture("completed_cap",dt,false,stages,NULL);Map();Clock();
    }catch(...){if(scratch)PosInteraction_Forces();throw;}
    Need(Bits(ddtp,dt)&&Bits(ddtc,dt)&&Bits(SymplecticDtPre,dt),"Original necessary fixed-step policy changed");
    pressure<<"native_id,source_time_s,completed_step,dt_s,p_n,p_h,R_n,R_h,M_h,S_h,hS_over_M,CN_denominator,CN_positive_denominator,p_original_raw,p_CN_raw,p_CN_after_cap,original_cap_shadow,raw_change_Pa,completed_change_vs_original_cap_shadow_Pa,CN_float_cast_error_Pa,CN_float_cast_budget_Pa,FS_h,FS_completed,J_n,J_h,J_next,kappa_n,kappa_next,x_next,z_next\n";
    balance<<"native_id,deltaJ,c_h,deltaP_CN,hydraulic,completed_cap,original_fp,CN_intervention_storage,observed_defect,closure,arithmetic_budget\n";
    const double solid=1.-double(SoilCte.Porosity),kw=SoilCte.PoreWaterBulkModulus;unsigned negativeDen=0,changed=0,caps=0;double maxDelta=0,maxClosure=0;
    for(unsigned id=2060;id<Original;id++){
      const auto& b=n[id];const auto& f=fn[id];const auto& m=fh[id];const auto& o=off[id];const auto& r=on[id];const auto& q=next[id];const auto& row=midpoint[id];
      double jp=b.j;jp+=dt*.5*b.j*f.theta;double jc=b.j;jc+=dt*m.j*m.theta;const float pp=float(double(b.p)+dt*.5*double(f.rate)),pc=float(double(b.p)+dt*double(m.rate));
      Need(Bits(h[id].j,jp)&&Bits(h[id].p,pp)&&Bits(o.j,jc)&&Bits(o.p,pc)&&Bits(r.j,o.j)&&Bits(q.j,r.j)&&Bits(r.p,float(row.next)),"Original predictor/temporary explicit commit or candidate update changed");
      Need(Bits(r.pos,o.pos)&&Bits(r.vel,o.vel)&&Bits(r.sigma,o.sigma)&&Bits(r.kappa,o.kappa)&&Bits(r.theta,o.theta)&&r.fs==o.fs,"Pressure intervention changed captured nonpressure fields");
      const float capExpected=((q.fs==2||q.fs==3)&&r.p>0?0.f:r.p),offCap=((q.fs==2||q.fs==3)&&o.p>0?0.f:o.p);Need(Bits(q.p,capExpected),"Original completed-step positive-only cap differs");
      Need(Finite(q.j)&&q.j>solid&&Finite(q.p)&&Finite(q.kappa)&&q.kappa>=b.kappa&&Finite(q.pos)&&Finite(q.vel),"Candidate completed primary state violates original finite/ledger/history domain");
      const double castError=double(r.p)-row.next,castBudget=FLT_EPSILON*fabs(row.next)+double(std::numeric_limits<float>::denorm_min());Need(fabs(castError)<=castBudget,"Candidate final-float arithmetic budget failed");
      const double c=(m.j-solid)/kw,dj=r.j-b.j,dp=double(q.p)-b.p,dcap=double(q.p)-r.p,hyd=dt*m.j*m.hydraulic,cap=c*dcap,extra=c*(double(r.p)-o.p);
      const double erate=double(m.rate)-m.literal,ep=(double(o.p)-b.p)-dt*double(m.rate),ej=dj-dt*m.j*m.theta,esource=c*m.literal+m.j*m.theta-m.j*m.hydraulic;
      const double fp=ej+c*ep+dt*c*erate+dt*esource,defect=dj+c*dp-hyd-cap,closure=defect-fp-extra;
      const double envelope=fabs(r.j)+fabs(b.j)+fabs(dj)+fabs(c*dp)+fabs(hyd)+fabs(cap)+fabs(fp)+fabs(extra)+fabs(ej)+fabs(c*ep)+fabs(dt*c*erate)+fabs(dt*esource)+fabs(dt*m.j*m.theta)+fabs(dt*c*m.literal)+fabs(dt*m.j*m.hydraulic);
      const double budget=RoundoffGamma(128)*envelope+128*std::numeric_limits<double>::denorm_min();Need(Finite(closure)&&fabs(closure)<=budget,"Candidate pressure/J balance with declared time-intervention term failed");maxClosure=(std::max)(maxClosure,fabs(closure));negativeDen+=row.den<0;changed+=!Bits(r.p,o.p);caps+=!Bits(q.p,r.p);maxDelta=(std::max)(maxDelta,fabs(double(r.p)-o.p));
      pressure<<id<<','<<start<<','<<completed+1<<','<<dt<<','<<b.p<<','<<m.p<<','<<f.rate<<','<<m.rate<<','<<row.M<<','<<row.S<<','<<dt*row.s<<','<<row.den<<','<<(row.den>0)<<','<<o.p<<','<<r.p<<','<<q.p<<','<<offCap<<','<<double(r.p)-o.p<<','<<double(q.p)-offCap<<','<<castError<<','<<castBudget<<','<<m.fs<<','<<q.fs<<','<<b.j<<','<<m.j<<','<<q.j<<','<<b.kappa<<','<<q.kappa<<','<<q.pos.x<<','<<q.pos.z<<'\n';
      balance<<id<<','<<dj<<','<<c<<','<<dp<<','<<hyd<<','<<cap<<','<<fp<<','<<extra<<','<<defect<<','<<closure<<','<<budget<<'\n';
    }
    const unsigned toy=RowCoupledManufacture(coupled);Need(stageRows==8*Soil&&toy==6,"Exact stage/toy coverage differs");
    const auto ids=StageMap();for(unsigned i=0;i<Np;i++){const unsigned s=a.byid[Idpc[i]];Need(s!=UINT_MAX&&Bits(PorePress0c[i],a.p0[s]),"Completed all-ID P0 inheritance changed");}for(unsigned id=2060;id<Original;id++){const unsigned i=ids[id];double porosity,V,rho;GetPorosityFeedbackStateCpu(i,porosity,V,rho);const double k=GetDynamicConductivityCpu(i);Need(Finite(porosity)&&porosity>0&&porosity<1&&Finite(V)&&V>0&&Finite(rho)&&rho>0&&Bits(float(rho),Velrhopc[i].w)&&Finite(k)&&k>0,"Completed ledger/cache check failed");}
    std::ofstream material(pf::path(cfg->DirOut)/"material_shadow.csv");Need(bool(material),"Fresh material output unavailable");material<<std::setprecision(17)<<"stage,native_id,source_time_s,stage_width_s,source_completed_step,shadow_status,shadow_reason,trigger,kappa_n,kappa_continuous,shadow_kappa,actual_saved_kappa,I_n,I_trial,I_committed,q_trial,q_committed,lambda_shear,lambda_apex,lambda_tension,Rsigma_trace_Pa_s,theta_s_1,K_Pa,G_Pa,return_deltaI_Pa\n";
    MaterialShadow("half",dt*.5,n,fn,h,true,material);MaterialShadow("full",dt,n,fh,on,false,material);Need(materialRows==10000,"Original same-input material shadow coverage differs");
    for(auto f:{&stages,&rows,&pressure,&balance,&constant,&coupled,&material}){f->flush();Need(bool(*f),"Complete candidate CSV write failed");}
    TimeStep+=dt;LastDt=dt;Nstep++;Need(Bits(TimeStep,start+dt)&&unsigned(Nstep)==completed+1,"One genuine outer clock update differs");
    std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_cn_step_r1\",\"passed\":true,\"source_part\":300,\"source_completed_step\":"<<completed<<",\"source_time_s\":"<<start<<",\"completed_step\":"<<unsigned(Nstep)<<",\"completed_time_s\":"<<TimeStep<<",\"dt_s\":"<<dt<<",\"actual_force_calls\":2,\"actual_Darcy_calls\":2,\"physical_steps\":1,\"extra_OFF_trajectories\":0,\"pressure_CN_interventions\":1,\"midpoint_row_records\":5000,\"pressure_records\":5000,\"balance_records\":5000,\"stage_rows\":"<<stageRows<<",\"constant_source_manufactured_rows\":15000,\"coupled_CN_manufactured_rows\":"<<toy<<",\"material_shadow_rows\":"<<materialRows<<",\"negative_finite_denominators\":"<<negativeDen<<",\"changed_raw_pressure_IDs\":"<<changed<<",\"completed_cap_IDs\":"<<caps<<",\"max_abs_raw_pressure_change_Pa\":"<<maxDelta<<",\"max_balance_closure\":"<<maxClosure<<",\"true_midpoint_capacity_stored_before_J_update\":true,\"only_checked_pressure_field_changed_at_intervention\":true,\"all22_field_equivalence_claimed\":false,\"positive_only_completed_cap_verified\":true,\"contact_reaction_closed\":false,\"global_implicit_or_TPI\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Candidate completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_FULL301_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_SEED FRESH_OUT");
  const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_n255_full3_r1/c08_h18_n255_full3_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_n255_full3_r1/native_r1"),"Only sealed original full301 native admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);
  for(const char* leaf:{"c08_h18_n255_full3_r1.run.json","c08_h18_n255_full3_r1.call.json","c08_h18_n255_full3_native_r1.check.json","c08_h18_n255_full3_review_r1.check.json","c08_h18_late_step_r1_p300.check.json","c08_h18_pressure_row_r1.check.json","c08_h18_cn_step_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const Snapshot state(native,2);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_cn_step_r1")&&!pf::exists(cfg.DirOut),"Original seed and fresh single-CN-step output required");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");CnStepProbe probe;probe.ExecuteCnStep(&cfg,AppInfo.LogPtr(),state);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Single finite-Kw CN diagnostic failed; preserve outputs\n";return 2;}}
