// One original CPU force on frozen Part300; algebraic pressure rows never feed back.
#define main c08_storage_rhs_unused_main
#include "../outputs/c08_h18_pressure_row_r1_build/shared.inc"
#undef main
#include <chrono>

static const char* RowBasis[7]={"1","x","z","half_x2","xz","half_z2","half_x2_minus_z2"};
static const char* RowRegions[4]={"all","interior_no_fixed","wall_adjacent","FS"};
static double RowPolynomial(unsigned b,tdouble3 r){switch(b){case 0:return 1.;case 1:return r.x;case 2:return r.z;case 3:return .5*r.x*r.x;case 4:return r.x*r.z;case 5:return .5*r.z*r.z;default:return .5*(r.x*r.x-r.z*r.z);}}
struct QuadDonor{tdouble3 r,gi;double v,rr,p;std::array<double,3> w;};
struct RowStats{unsigned count=0;double sum=0,sq=0,max=0;void Add(double value,double target){const double e=value-target;Need(Finite(value)&&Finite(e),"Nonfinite manufactured row");count++;sum+=value;sq+=e*e;max=(std::max)(max,fabs(e));}};
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

class PressureRowProbe:public Probe{
  // This complete stencil method is byte-identical to the retained quadratic fixture.
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
public:
  void ExecuteRow(const JSphCfgRun* cfg,JLog2* log,const Snapshot& a){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2 PRE/bedroles handoff differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.5f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Wendland N255 material/AS/AV/dt differs");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();Restore(a);Need(a.part==300&&a.completed==2600000,"Only original full3 Part300 admitted");Unchanged(a);
    std::ofstream rows(pf::path(cfg->DirOut)/"rows.csv"),manufactured(pf::path(cfg->DirOut)/"manufactured.csv"),shadows(pf::path(cfg->DirOut)/"shadows.csv"),summary(pf::path(cfg->DirOut)/"summary.csv"),coupled(pf::path(cfg->DirOut)/"coupled_CN.csv");
    for(auto f:{&rows,&manufactured,&shadows,&summary,&coupled}){Need(bool(*f),"Fresh row output unavailable");*f<<std::setprecision(17);}
    rows<<"part,time_s,tau_s,completed_step,native_id,region,FS,neighbors,fixed_neighbors,almostzero_excluded,x_m,z_m,p_Pa,J,n,V_m2,k_m_s,dkdJ,gamma_Pa_m,M_per_m,S_per_m_s,fluid_S_per_m_s,fixed_S_per_m_s,N_Pa_m_s,fixed_N_Pa_m_s,B_Pa_m_s,LP_pressure_Pa_m_s,Taylor_pressure_Pa_m_s,chain_pressure_Pa_m_s,row_pressure_Pa_m_s,N_minus_Sp_Pa_m_s,row_identity_error_Pa_m_s,row_identity_budget_Pa_m_s,actual_float_rate_Pa_s,literal_rate_Pa_s,row_rate_Pa_s,old_rate_budget_Pa_s,row_rate_error_Pa_s,A_min,A_max,negative_A,negative_fixed_A,A_absolute_sum,hS_over_M,soil_only_constant_shift1Pa_rate_Pa_s\n";
    manufactured<<"part,time_s,tau_s,completed_step,native_id,region,basis,full6805_analytic_donors,analytic_target_Pa_m_s,LP_Pa_m_s,Taylor_Pa_m_s,chain_Pa_m_s,row_pressure_Pa_m_s,direct_pressure_Pa_m_s,arithmetic_error,arithmetic_budget,full_N_minus_Sp,Eq22_gpx,Eq22_gpz,analytic_gpx,analytic_gpz\n";
    shadows<<"part,time_s,tau_s,completed_step,native_id,h_s,p_base_Pa,M_per_m,S_per_m_s,explicit_delta_Pa,BE_denominator,BE_defined,BE_positive_denominator,BE_delta_Pa,BE_new_Pa,BE_algebraic_error,BE_algebraic_budget,lagged_N_midpoint_denominator,lagged_N_midpoint_defined,lagged_N_midpoint_positive_denominator,lagged_N_midpoint_delta_Pa,lagged_N_midpoint_new_Pa,lagged_N_midpoint_algebraic_error,lagged_N_midpoint_algebraic_budget,rescaling_max_error_Pa,rescaling_budget_Pa\n";
    summary<<"region,basis,IDs,mean_response_Pa_m_s,RMS_error_Pa_m_s,max_abs_error_Pa_m_s\n";
    std::array<std::array<RowStats,7>,4> statistics;std::array<unsigned,4> receivers{};unsigned calls=0,rowCount=0,fieldCount=0,shadowCount=0,summaryCount=0,nonpositiveS=0,negativeRows=0,undefinedBE=0,undefinedMid=0;double maxOldRatio=0,maxIdentityRatio=0;
    const double kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,gamma=rho*9.80665,dt=.000005;bool scratch=true;double forceSeconds=0,rowSeconds=0;
    try{
      const auto forceStart=std::chrono::steady_clock::now();Interaction_Forces(INTERSTEP_SymCorrector);calls++;forceSeconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-forceStart).count();
      Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc&&CorrMatc,"Original full-force scratch missing");Unchanged(a);Map();const auto rowStart=std::chrono::steady_clock::now();
      for(unsigned i=Npb;i<Np;i++){
        unsigned fixed,almost;const auto donors=Stencil(i,fixed,almost);const auto all=Assemble(i);const auto& z=all[0];const bool sf=IsFreeSurfaceParticle(i,Codec,FSTypec);const unsigned region=sf?3u:fixed?2u:1u;receivers[0]++;receivers[region]++;
        Need(donors.size()==z.count&&fixed==all[2].count,"Exact original stencil coverage differs");double n,V,rhot;GetPorosityFeedbackStateCpu(i,n,V,rhot);const double k=GetDynamicConductivityCpu(i),dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk),M=gamma*n/kw,p=PorePressc[i],theta=PoroThetac[i];const auto ai=ToTDouble3(Acec[i]);
        Need(Finite(M)&&M>0&&Finite(k)&&k>0&&Finite(dk),"Original finite capacity/conductivity invalid");
        // Literal original raw-FS expression; its final float commit must remain exact.
        const double lap=(sf?z.lp+rho*(ai.x*z.lx.x+ai.y*z.lx.y+ai.z*z.lx.z+z.da):z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da);
        const double chain=dk*(z.gradj.x*(z.gp.x+rho*ai.x)+z.gradj.y*(z.gp.y+rho*ai.y)+z.gradj.z*(z.gp.z+rho*ai.z));const double literal=kw/n*(-theta+k/gamma*lap+chain/gamma);const float actual=PorePressRatec[i];
        const double fbudget=FLT_EPSILON*fabs(literal)+double(std::numeric_limits<float>::denorm_min());Need(Finite(literal)&&Finite(actual)&&Bits(actual,float(literal))&&fabs(double(actual)-literal)<=fbudget,Detail("Original literal/final-float mismatch",a.part,Idpc[i],actual,literal,fbudget));
        const tdouble3 u=z.lx*(sf?0.:-k)+z.gradj*dk;std::vector<double> A;A.reserve(donors.size());double S=0,N=0,fluidS=0,wallS=0,wallN=0,rowPressure=0,sumAbsA=0,sumAbsN=0,minA=DBL_MAX,maxA=-DBL_MAX;unsigned negative=0,negativeFixed=0,at=0;
        for(const auto& d:donors){const double aj=k*d.w[0]+d.v*Dot(d.gi,u);Need(Finite(aj),"Nonfinite complete pressure row coefficient");A.push_back(aj);S+=aj;N+=aj*d.p;rowPressure+=aj*(d.p-p);sumAbsA+=fabs(aj);sumAbsN+=fabs(aj*d.p);minA=(std::min)(minA,aj);maxA=(std::max)(maxA,aj);negative+=aj<0;if(at++>=donors.size()-fixed){wallS+=aj;wallN+=aj*d.p;negativeFixed+=aj<0;}else fluidS+=aj;}
        Need(Finite(S)&&Finite(N)&&Finite(rowPressure)&&Finite(sumAbsA)&&Finite(sumAbsN),"Nonfinite assembled pressure row");
        // Acceleration and theta are frozen; all pressure Taylor/chain coefficients are in A.
        const double B=-gamma*theta+k*rho*(z.da+(sf?Dot(ai,z.lx):0.))+dk*rho*Dot(z.gradj,ai);
        const double rowRate=(B+rowPressure)/M,oldBudget=RateBudget(z,sf,kw,n,k,dk,gamma,rho,ai,theta,literal),rateError=fabs(rowRate-double(actual));
        Need(Finite(rowRate)&&Finite(oldBudget)&&rateError<=oldBudget,Detail("Complete frozen pressure row differs from original rate",a.part,Idpc[i],rowRate,actual,oldBudget));maxOldRatio=(std::max)(maxOldRatio,oldBudget?rateError/oldBudget:0.);
        const double expandedPressure=k*z.lp+(sf?0.:-k*Dot(z.gp,z.lx))+dk*Dot(z.gradj,z.gp);
        Need(fabs((B+expandedPressure)/M-double(actual))<=oldBudget,"Original seven-term expansion changed");
        const double identity=N-S*p,error=fabs(identity-rowPressure),identityMagnitude=sumAbsN+sumAbsA*fabs(p)+fabs(rowPressure);const double identityBudget=2*RoundoffGamma(64*unsigned(donors.size()+1))*identityMagnitude+128*std::numeric_limits<double>::denorm_min();
        Need(Finite(error)&&Finite(identityBudget)&&error<=identityBudget,"N-S*p arithmetic row identity failed");maxIdentityRatio=(std::max)(maxIdentityRatio,identityBudget?error/identityBudget:0.);nonpositiveS+=S<=0;negativeRows+=negative>0;
        rows<<a.part<<','<<TimeStep<<','<<TimeStep-GravityPreloadActualTime<<','<<unsigned(Nstep)<<','<<Idpc[i]<<','<<RowRegions[region]<<','<<FSTypec[i]<<','<<donors.size()<<','<<fixed<<','<<almost<<','<<Posc[i].x<<','<<Posc[i].z<<','<<p<<','<<PoroJc[i]<<','<<n<<','<<V<<','<<k<<','<<dk<<','<<gamma<<','<<M<<','<<S<<','<<fluidS<<','<<wallS<<','<<N<<','<<wallN<<','<<B<<','<<k*z.lp<<','<<(sf?0.:-k*Dot(z.gp,z.lx))<<','<<dk*Dot(z.gradj,z.gp)<<','<<rowPressure<<','<<identity<<','<<error<<','<<identityBudget<<','<<actual<<','<<literal<<','<<rowRate<<','<<oldBudget<<','<<rateError<<','<<minA<<','<<maxA<<','<<negative<<','<<negativeFixed<<','<<sumAbsA<<','<<dt*S/M<<','<<-wallS/M<<'\n';rowCount++;
        for(unsigned b=0;b<7;b++){
          const double qi=RowPolynomial(b,TDouble3(0));double pr=0,lp=0,Nf=0,absLP=0,absPr=0;tdouble3 gp=TDouble3(0),gpabs=TDouble3(0);unsigned j=0;
          for(const auto& d:donors){const double qj=RowPolynomial(b,d.r),delta=qj-qi,term=A[j++]*delta;pr+=term;absPr+=fabs(term);Nf+=A[j-1]*qj;lp+=d.w[0]*delta;absLP+=fabs(d.w[0]*delta);const auto g=d.gi*(d.v*delta);gp=gp+g;gpabs=gpabs+Abs(g);}
          const double taylor=sf?0.:-k*Dot(gp,z.lx),kp=dk*Dot(z.gradj,gp),direct=k*lp+taylor+kp;const double mag=k*(absLP+(sf?0.:Dot(gpabs,z.lxabs)))+dk*Dot(z.jabs,gpabs)+absPr;
          const double budget=2*RoundoffGamma(64*unsigned(donors.size()+1))*mag+128*std::numeric_limits<double>::denorm_min();Need(Finite(pr)&&Finite(direct)&&Finite(budget)&&budget>=0&&fabs(pr-direct)<=budget,"Manufactured complete row/direct identity failed");
          if(b==0)Need(Bits(pr,0.)&&Bits(direct,0.),"Full6805 analytic constant pressure operator not zero");
          const tdouble3 grad=TDouble3(b==1?1.:0.,0,b==2?1.:0.);const double lapExact=b==3||b==5?1.:0.;const double target=k*lapExact+dk*Dot(z.gradj,grad);
          manufactured<<a.part<<','<<TimeStep<<','<<TimeStep-GravityPreloadActualTime<<','<<unsigned(Nstep)<<','<<Idpc[i]<<','<<RowRegions[region]<<','<<RowBasis[b]<<",1,"<<target<<','<<k*lp<<','<<taylor<<','<<kp<<','<<pr<<','<<direct<<','<<fabs(pr-direct)<<','<<budget<<','<<Nf-S*qi<<','<<gp.x<<','<<gp.z<<','<<grad.x<<','<<grad.z<<'\n';fieldCount++;
          for(unsigned g:{0u,region})statistics[g][b].Add(pr,target);
        }
        for(double h:{dt,dt/10.,dt/100.}){
          const double explicitDelta=h*rowRate,lambda=h*S/M,denBE=1.+lambda,denMid=1.+.5*lambda;const bool be=Finite(denBE)&&denBE!=0.,mid=Finite(denMid)&&denMid!=0.;undefinedBE+=!be;undefinedMid+=!mid;
          const double deltaBE=be?explicitDelta/denBE:0.,deltaMid=mid?explicitDelta/denMid:0.;double rescaleError=0;const double scaleBudget=RoundoffGamma(128)*(fabs(p)+fabs(explicitDelta)+fabs(deltaBE)+fabs(deltaMid))+128*std::numeric_limits<double>::denorm_min();
          for(double scale:{1./gamma,V}){
            const double scaledRate=(scale*B+scale*rowPressure)/(scale*M),scaledLambda=h*(scale*S)/(scale*M);const double bden=1.+scaledLambda,mden=1.+.5*scaledLambda;
            Need(!be||(Finite(bden)&&bden!=0.),"BE algebraic row scaling changed domain");Need(!mid||(Finite(mden)&&mden!=0.),"Midpoint algebraic row scaling changed domain");
            if(be)rescaleError=(std::max)(rescaleError,fabs((p+h*scaledRate/bden)-(p+deltaBE)));if(mid)rescaleError=(std::max)(rescaleError,fabs((p+h*scaledRate/mden)-(p+deltaMid)));
          }Need(Finite(rescaleError)&&rescaleError<=scaleBudget,"Pure row-unit rescaling changed the algebraic shadow");
          const double errorBE=be?fabs((deltaBE-explicitDelta)+lambda*deltaBE):0.,errorMid=mid?fabs((deltaMid-explicitDelta)+.5*lambda*deltaMid):0.;
          const double budgetBE=RoundoffGamma(64)*(fabs(deltaBE)+fabs(explicitDelta)+fabs(lambda*deltaBE))+64*std::numeric_limits<double>::denorm_min(),budgetMid=RoundoffGamma(64)*(fabs(deltaMid)+fabs(explicitDelta)+fabs(.5*lambda*deltaMid))+64*std::numeric_limits<double>::denorm_min();
          Need(!be||(Finite(deltaBE)&&errorBE<=budgetBE),"BE shadow arithmetic identity failed");Need(!mid||(Finite(deltaMid)&&errorMid<=budgetMid),"Midpoint shadow arithmetic identity failed");
          shadows<<a.part<<','<<TimeStep<<','<<TimeStep-GravityPreloadActualTime<<','<<unsigned(Nstep)<<','<<Idpc[i]<<','<<h<<','<<p<<','<<M<<','<<S<<','<<explicitDelta<<','<<denBE<<','<<be<<','<<(denBE>0)<<',';if(be)shadows<<deltaBE<<','<<p+deltaBE<<','<<errorBE<<','<<budgetBE;else shadows<<",,,";shadows<<','<<denMid<<','<<mid<<','<<(denMid>0)<<',';if(mid)shadows<<deltaMid<<','<<p+deltaMid<<','<<errorMid<<','<<budgetMid;else shadows<<",,,";shadows<<','<<rescaleError<<','<<scaleBudget<<'\n';shadowCount++;
        }
      }
      rowSeconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-rowStart).count();Unchanged(a);Map();PosInteraction_Forces();scratch=false;Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Original force scratch cleanup differs");Unchanged(a);Map();
    }catch(...){if(scratch)PosInteraction_Forces();throw;}
    for(unsigned g=0;g<4;g++)for(unsigned b=0;b<7;b++){const auto& s=statistics[g][b];Need(s.count==receivers[g],"Manufactured receiver coverage differs");summary<<RowRegions[g]<<','<<RowBasis[b]<<','<<s.count<<',';if(s.count)summary<<s.sum/s.count<<','<<sqrt(s.sq/s.count)<<','<<s.max;else summary<<",,";summary<<'\n';summaryCount++;}
    const unsigned coupledRows=RowCoupledManufacture(coupled);
    Need(calls==1&&rowCount==5000&&fieldCount==35000&&shadowCount==15000&&summaryCount==28&&coupledRows==6&&receivers[0]==5000&&receivers[1]+receivers[2]+receivers[3]==5000,"Exact pressure-row coverage differs");for(auto f:{&rows,&manufactured,&shadows,&summary,&coupled}){f->flush();Need(bool(*f),"Complete row CSV write failed");}Unchanged(a);
    std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_pressure_row_r1\",\"passed\":true,\"source_part\":300,\"source_completed_step\":"<<a.completed<<",\"source_time_s\":"<<a.time<<",\"actual_time_s\":"<<TimeStep<<",\"actual_completed_step\":"<<unsigned(Nstep)<<",\"actual_force_calls\":1,\"actual_Darcy_calls\":1,\"physical_steps\":0,\"material_return_calls\":0,\"extra_Darcy_calls\":0,\"row_records\":"<<rowCount<<",\"manufactured_records\":"<<fieldCount<<",\"shadow_records\":"<<shadowCount<<",\"summary_records\":"<<summaryCount<<",\"coupled_CN_manufactured_rows\":"<<coupledRows<<",\"native_row_is_not_midpoint_field\":true,\"literal_final_float_bits_matched\":5000,\"max_original_rate_budget_ratio\":"<<maxOldRatio<<",\"max_row_identity_budget_ratio\":"<<maxIdentityRatio<<",\"nonpositive_S_rows\":"<<nonpositiveS<<",\"rows_with_negative_A\":"<<negativeRows<<",\"undefined_BE_shadows\":"<<undefinedBE<<",\"undefined_midpoint_shadows\":"<<undefinedMid<<",\"force_seconds\":"<<forceSeconds<<",\"row_and_output_seconds\":"<<rowSeconds<<",\"all5000_primary_bits_unchanged\":true,\"all6805_normal_IDs_and_roles_unchanged\":true,\"analytic_fixed_donors_in_manufactured_fields\":true,\"wall_values_lagged_in_native_pressure_block\":true,\"acceleration_frozen_not_coupled_Jacobian\":true,\"TPI_or_beta_implemented\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_FULL301_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_SEED FRESH_OUT");
  const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_n255_full3_r1/c08_h18_n255_full3_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_n255_full3_r1/native_r1"),"Only sealed original full301 native admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);
  for(const char* leaf:{"c08_h18_n255_full3_r1.run.json","c08_h18_n255_full3_r1.call.json","c08_h18_n255_full3_native_r1.check.json","c08_h18_n255_full3_review_r1.check.json","c08_h18_late_rhs_r1.check.json","c08_h18_pressure_row_r1.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);protectedFiles.emplace_back(pf::absolute(argv[0]));for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const Snapshot state(native,2);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_pressure_row_r1")&&!pf::exists(cfg.DirOut),"Original seed and fresh pressure-row output required");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");PressureRowProbe probe;probe.ExecuteRow(&cfg,AppInfo.LogPtr(),state);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Frozen pressure-row diagnostic failed; preserve outputs\n";return 2;}}
