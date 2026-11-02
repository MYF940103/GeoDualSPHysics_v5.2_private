// Conditional manufactured CPU operator checks; no public gravity admission or trajectory.
#define main RetainedGravityFeedbackMain
#include "upl_p2_feedback_harness_r1.cpp"
#undef main
#include <limits>

static double GDot(const tdouble3& a,const tdouble3& b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double GNorm(const tdouble3& a){return sqrt(GDot(a,a));}
static tdouble3 GProduct(const tmatrix3d& c,const tdouble3& a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
static double GMatrixNorm(const tmatrix3d& c){return (std::max)({fabs(c.a11)+fabs(c.a12)+fabs(c.a13),fabs(c.a21)+fabs(c.a22)+fabs(c.a23),fabs(c.a31)+fabs(c.a32)+fabs(c.a33)});}

class GravityActual:public Feedback{
  unsigned Dimension;bool Jitter,StandardGamma;
  std::vector<unsigned> Cells;
  struct Point{tdouble3 x;unsigned id,key;};
  struct Reference{
    double n,k,lp=0,da=0,wabs=0,lpabs=0,daabs=0,sg=0,gabs=0,jabs=0,condition=1,rate=0,rawrate=0;
    tdouble3 gp=TDouble3(0),lx=TDouble3(0),gj=TDouble3(0),q=TDouble3(0);
  };
  double Gamma()const{return double(SoilCte.PoreWaterRho)*(StandardGamma? 9.80665:GNorm(ToTDouble3(Gravity)));}
  Reference Assemble(unsigned i)const{
    Reference r{};const double rhow=SoilCte.PoreWaterRho,v0=double(MassFluid)/RhopZero;
    r.n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i];
    r.k=double(SoilCte.HydraulicConductivity)*(DynamicPoreConductivity? exp((PoroJc[i]-1.)/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk)):1.);
    const auto ci=CorrMatc[i];tmatrix3d moment=TMatrix3d(0);
    // Independent O(N^2) search, not production cell ranges or its rate routine.
    for(unsigned j=0;j<Np;j++){
      tdouble3 d=Posc[i]-Posc[j];if(Dimension==2)d.y=0;const double rr=GDot(d,d);
      if(rr>KernelSize2||rr<ALMOSTZERO)continue;
      const tdouble3 g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr)));
      const auto gi=GProduct(ci,g),gj=GProduct(CorrMatc[j],g);const double v=v0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j];
      const double w=v*GDot(d,gi+gj)/(rr+double(Eta2));
      r.lp+=w*dp;r.lx=r.lx+d*w;r.gp=r.gp-gi*(v*dp);r.gj=r.gj+gi*(v*(PoroJc[j]-PoroJc[i]));
      const auto da=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);r.da+=v*GDot(da,gi);
      r.wabs+=fabs(w);r.lpabs+=fabs(w*dp);r.daabs+=v*(fabs(da.x*gi.x)+fabs(da.y*gi.y)+fabs(da.z*gi.z));
      r.sg+=v*GNorm(gi);r.gabs+=v*fabs(dp)*GNorm(gi);r.jabs+=v*fabs(PoroJc[j]-PoroJc[i])*GNorm(gi);
      moment.a11-=v*d.x*g.x;moment.a12-=v*d.x*g.y;moment.a13-=v*d.x*g.z;
      moment.a21-=v*d.y*g.x;moment.a22-=v*d.y*g.y;moment.a23-=v*d.y*g.z;
      moment.a31-=v*d.z*g.x;moment.a32-=v*d.z*g.y;moment.a33-=v*d.z*g.z;
    }
    r.condition=(std::max)(1.,GMatrixNorm(ci)*GMatrixNorm(moment));
    const auto drive=r.gp+ToTDouble3(Acec[i])*rhow;
    const double alpha=DynamicPoreConductivity? 1./((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk):0.;
    const double chain=r.k*alpha*GDot(r.gj,drive),kw=SoilCte.PoreWaterBulkModulus;
    r.rate=kw/r.n*(-PoroThetac[i]+(r.k*(r.lp-GDot(r.gp,r.lx)+rhow*r.da)+chain)/Gamma());
    r.rawrate=kw/r.n*(fabs(PoroThetac[i])+(r.k*(r.lpabs+fabs(r.gp.x*r.lx.x)+fabs(r.gp.y*r.lx.y)+fabs(r.gp.z*r.lx.z)+rhow*r.daabs)+fabs(chain))/Gamma());
    r.q=drive*(-r.k/Gamma());return r;
  }
  void Reset(bool law){
    DynamicPoreConductivity=law;DynamicPoreConductivityCk=1./8.;InitPorosityObserverCpu();
    const double xmin=(std::min_element)(Posc,Posc+Np,[](const tdouble3& a,const tdouble3& b){return a.x<b.x;})->x;
    const double xmax=(std::max_element)(Posc,Posc+Np,[](const tdouble3& a,const tdouble3& b){return a.x<b.x;})->x;
    for(unsigned p=0;p<Np;p++){
      PoroJc[p]=law? 1.+.005*(Posc[p].x-xmin)/(xmax-xmin):1.;PoroThetac[p]=0;
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
      PorePressc[p]=PorePress0c[p]=0;PorePressRatec[p]=1234567.f;
    }
  }
public:
  GravityActual(unsigned dim,bool jitter,bool standardGamma):Feedback(dim,dim==2?9:27),Dimension(dim),Jitter(jitter),StandardGamma(standardGamma){
    // Mechanical reuse of upl_p3_actual_r3.cpp:41-69, NONPERIODIC branch only.
    // Its nested main/undef precludes safely including that complete .cpp again.
    DynamicPorePressure=true;SoilCte.HydraulicConductivity=1e-5f;
    Gravity=dim==2? TFloat3(-4,0,-8):TFloat3(-4,2,-8);CSP.gravity=Gravity;
    KernelH=.25f;KernelSize=.5f;KernelSize2=.25f;Eta2=.000625f;
    CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;CSP.kwend=fsph::GetKernelWendland_Ctes(Simulate2D,KernelH);
    InitPorosityObserverCpu();std::vector<Point> particles;unsigned id=0;
    for(int y=(dim==3?-1:0);y<=(dim==3?1:0);y++)for(int z=-1;z<=1;z++)for(int x=-1;x<=1;x++){
      tdouble3 p=TDouble3(1.+x*Dp,dim==3?1.+y*Dp:0.,1.+z*Dp);
      if(jitter){const unsigned axis=id%dim;const double offset=(id%2?1.:-1.)*Dp/8.;if(axis==0)p.x+=offset;else if(axis==1&&dim==3)p.y+=offset;else p.z+=offset;}
      particles.push_back({p,id++,0});
    }
    Np=unsigned(particles.size());CaseNp=CaseNfluid=Np;NpfPer=NpbPer=0;Require(Np<=CpuParticlesSize,"Gravity patch exceeds arrays");
    const tuint3 nc=TUint3(4,dim==3?3:1,3);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(27,2,2);
    for(auto& p:particles){const unsigned cx=unsigned(p.x.x/KernelSize),cy=dim==3?unsigned(p.x.y/KernelSize):0,cz=unsigned(p.x.z/KernelSize);Require(cx<nc.x&&cy<nc.y&&cz<nc.z,"Gravity cell outside table");p.key=cx+nc.x*(cy+nc.y*cz);}
    std::stable_sort(particles.begin(),particles.end(),[](const Point& a,const Point& b){return a.key<b.key;});
    Cells.assign(2*(ncell+1),0);unsigned cursor=0;for(unsigned c=0;c<=ncell;c++){while(cursor<Np&&particles[cursor].key<c)cursor++;Cells[ncell+1+c]=cursor;}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));
    for(unsigned p=0;p<Np;p++){
      const auto& a=particles[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=CODE_TYPE_FLUID;
      const unsigned cx=a.key%nc.x,cy=(a.key/nc.x)%nc.y,cz=a.key/(nc.x*nc.y);Dcellc[p]=DCEL_Cell(code,cx,cy,cz);
      Require(DCEL_Cellx(code,Dcellc[p])==cx&&DCEL_Celly(code,Dcellc[p])==cy&&DCEL_Cellz(code,Dcellc[p])==cz,"Packed cell round-trip failed");
      PoroJc[p]=1;PoroThetac[p]=0;Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
      PorePressc[p]=PorePress0c[p]=0;PorePressRatec[p]=1234567.f;CorrMatc[p]=TMatrix3d();FSNormalc[p]=TFloat3(0);FSTypec[p]=FST_Inner;PosDivc[p]=0;HydroMechLoadAcec[p]=TFloat3(0);
    }
  }
  unsigned ForceFreefall(std::ostream& out){
    Reset(false);PreInteraction_Forces();ComputeFreeSurfaceTracking();
    std::fill(PorePressRatec,PorePressRatec+Np,1234567.f);
    const auto parameters=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec,FSTypec,FSNormalc,nullptr,CorrMatc,Arc,Acec,nullptr,SHIFT_None,nullptr,nullptr,nullptr,Sigmac,Rsigmac,nullptr);
    StInterResultc result{};Interaction_Forces_ct(parameters,result);
    for(unsigned p=0;p<Np;p++)Require(Acec[p].x==0&&Acec[p].y==0&&Acec[p].z==0&&PoroThetac[p]==0&&PorePressRatec[p]==1234567.f,"Zero total-stress force or old-rate suppression failed");
    ComputeDynamicPorePressureRateCpu();
    for(unsigned p=0;p<Np;p++){
      const auto physical=ToTDouble3(Acec[p])+ToTDouble3(Gravity);
      Require(physical==ToTDouble3(Gravity)&&PorePressRatec[p]==0,"Freefall physical acceleration or complete rate failed");
      out<<Dimension<<','<<Jitter<<','<<Idpc[p]<<','<<Acec[p].x<<','<<Acec[p].y<<','<<Acec[p].z<<','<<physical.x<<','<<physical.y<<','<<physical.z<<','<<PorePressRatec[p]<<"\n";
    }
    PosInteraction_Forces();return Np;
  }
  unsigned Check(unsigned field,bool law,std::ostream& rows,std::ostream& summary){
    const char* names[]={"hydrostatic","freefall","tangential_acceleration","affine_acceleration_divergence","wrong_missing_g","wrong_doubled_g"};
    Require(field<6,"Unknown gravity field");Reset(law);PreInteraction_Forces();ComputeFreeSurfaceTracking();
    const auto gravity=ToTDouble3(Gravity);const double rhow=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus;
    tdouble3 gradient=gravity*rhow;if(field==1||field==3)gradient=TDouble3(0);
    const auto tangential=TDouble3(.25,0,-.125);if(field==2)gradient=(gravity-tangential)*rhow;
    const double divA=field==3? .125+(Dimension==3?.0625:0)-.03125:0.;
    double xmin=DBL_MAX,xmax=-DBL_MAX,pmax=1,amax=1;std::vector<tdouble3> actualTrue(Np),intendedTrue(Np);
    for(unsigned p=0;p<Np;p++){xmin=(std::min)(xmin,Posc[p].x);xmax=(std::max)(xmax,Posc[p].x);}
    const auto jgradient=law? TDouble3(.005/(xmax-xmin),0,0):TDouble3(0);
    for(unsigned p=0;p<Np;p++){
      tdouble3 physical=TDouble3(0);if(field==1)physical=gravity;if(field==2)physical=tangential;
      if(field==3)physical=TDouble3(.125*(Posc[p].x-1.),Dimension==3?.0625*(Posc[p].y-1.):0.,-.03125*(Posc[p].z-1.));
      intendedTrue[p]=physical-gravity;actualTrue[p]=intendedTrue[p];
      if(field==4)actualTrue[p]=actualTrue[p]+gravity;if(field==5)actualTrue[p]=actualTrue[p]-gravity;
      const double pressure=65536.+GDot(gradient,Posc[p]);PorePressc[p]=float(pressure);Acec[p]=ToTFloat3(actualTrue[p]);
      pmax=(std::max)(pmax,fabs(pressure));amax=(std::max)(amax,GNorm(actualTrue[p]));PorePressRatec[p]=1234567.f;
    }
    std::vector<Reference> reference;for(unsigned p=0;p<Np;p++)reference.push_back(Assemble(p));
    const double ep=(field==1||field==3? 0:2.*FLT_EPSILON*pmax),ea=4.*FLT_EPSILON*amax;
    ComputeDynamicPorePressureRateCpu();double maxDiscreteRatio=0,maxAnalyticRatio=0,maxQRatio=0,maxNegativeQ=0,maxNegativeRate=0,maxGamma=0;
    for(unsigned p=0;p<Np;p++){
      const auto& r=reference[p];const double alpha=law? 1./((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk):0.;
      const auto drive=gradient+actualTrue[p]*rhow,intendedDrive=gradient+intendedTrue[p]*rhow;
      const double analytic=kw/r.n*r.k/Gamma()*(rhow*divA+alpha*GDot(jgradient,drive));
      const double intended=kw/r.n*r.k/Gamma()*(rhow*divA+alpha*GDot(jgradient,intendedDrive));
      const double bg=2.*ep*r.sg+(64.*FLT_EPSILON+32768.*DBL_EPSILON)*r.condition*GNorm(gradient)+4096.*DBL_EPSILON*(std::max)(1.,r.gabs);
      const double bj=(64.*FLT_EPSILON+32768.*DBL_EPSILON)*r.condition*GNorm(jgradient)+4096.*DBL_EPSILON*(std::max)(1.,r.jabs);
      const double bl=2.*ep*r.wabs+bg*GNorm(r.lx)+4096.*DBL_EPSILON*(std::max)(1.,r.lpabs+GNorm(gradient)*GNorm(r.lx));
      const double bd=2.*ea*r.sg+4096.*DBL_EPSILON*(std::max)(1.,r.daabs);
      const double chainBound=r.k*alpha*(GNorm(jgradient)*(bg+rhow*ea)+bj*(GNorm(drive)+bg+rhow*ea));
      const double propagated=kw/r.n/Gamma()*(r.k*(bl+rhow*bd)+chainBound);
      const double analyticLimit=propagated+2.*FLT_EPSILON*(std::max)(1.,fabs(analytic)+propagated);
      const double discreteLimit=32.*FLT_EPSILON*(std::max)(1.,r.rawrate)+4096.*DBL_EPSILON*(std::max)(1.,r.rawrate);
      const double qLimit=r.k/Gamma()*(bg+rhow*ea)+4096.*DBL_EPSILON*(std::max)(1.,GNorm(r.q));
      const auto qTrue=drive*(-r.k/Gamma()),qIntended=intendedDrive*(-r.k/Gamma());
      const double actual=PorePressRatec[p],discreteError=fabs(actual-r.rate),analyticError=fabs(actual-analytic),qError=GNorm(r.q-qTrue);
      Require(std::isfinite(actual)&&actual!=1234567.f&&discreteError<=discreteLimit,"Current complete rate differs from independent raw-term reference");
      Require(std::isfinite(qError)&&qError<=qLimit&&analyticError<=analyticLimit,"Gravity analytic flux/rate exceeds prior propagated bound");
      const double actualK=GetDynamicConductivityCpu(p);Require(std::isfinite(actualK)&&fabs(actualK-r.k)<=5e-13*fabs(r.k),"Same-stage conductivity reference failed");
      Require(PoroJc[p]>=1&&PoroJc[p]<=1.005&&r.n>0&&r.n<1,"Gravity manufactured state left declared domain");
      maxDiscreteRatio=(std::max)(maxDiscreteRatio,discreteError/discreteLimit);maxAnalyticRatio=(std::max)(maxAnalyticRatio,analyticError/analyticLimit);maxQRatio=(std::max)(maxQRatio,qError/qLimit);
      const double negativeQ=GNorm(r.q-qIntended)/qLimit,negativeRate=fabs(actual-intended)/analyticLimit;
      if(field>=4){maxNegativeQ=(std::max)(maxNegativeQ,negativeQ);maxNegativeRate=(std::max)(maxNegativeRate,negativeRate);}
      const double alternateGamma=rhow*(StandardGamma? GNorm(gravity):9.80665);
      const double wrongGammaAnalytic=analytic*Gamma()/alternateGamma,gammaRatio=fabs(analytic-wrongGammaAnalytic)/analyticLimit;
      if(field==3)maxGamma=(std::max)(maxGamma,gammaRatio);
      rows<<Dimension<<','<<Jitter<<','<<law<<','<<names[field]<<','<<Idpc[p]<<','<<PoroJc[p]<<','<<r.n<<','<<r.k<<','<<Gamma()<<','<<PorePressc[p]<<','<<Acec[p].x<<','<<Acec[p].y<<','<<Acec[p].z<<','<<actual<<','<<r.rate<<','<<discreteLimit<<','<<analytic<<','<<analyticLimit<<','<<intended<<','<<r.q.x<<','<<r.q.y<<','<<r.q.z<<','<<qTrue.x<<','<<qTrue.y<<','<<qTrue.z<<','<<qLimit<<','<<negativeQ<<','<<negativeRate<<','<<gammaRatio<<'\n';
    }
    if(field>=4){Require(maxNegativeQ>100.,"Missing/doubled-g input perturbation is not detectable in q");if(law)Require(maxNegativeRate>10.,"Smooth-k gravity source negative diagnostic is empty");}
    if(field==3)Require(maxGamma>10.,"Affine acceleration does not distinguish norm(g) from standard gamma");
    summary<<Dimension<<','<<Jitter<<','<<law<<','<<names[field]<<','<<Np<<','<<maxDiscreteRatio<<','<<maxAnalyticRatio<<','<<maxQRatio<<','<<maxNegativeQ<<','<<maxNegativeRate<<','<<maxGamma<<'\n';
    PosInteraction_Forces();return Np;
  }
};

int main(int argc,char** argv){
  try{
    Require((argc==3||argc==5)&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY [--gamma-policy norm|standard]");
    const bool standardGamma=argc==5&&std::string(argv[4])=="standard";
    if(argc==5)Require(std::string(argv[3])=="--gamma-policy"&&(standardGamma||std::string(argv[4])=="norm"),"Unknown gamma oracle policy");
    const fs::path out(argv[2]);Require(!fs::exists(out),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
    std::ofstream rows(out/"rates_flux.csv"),summary(out/"summary.csv"),force(out/"force_freefall.csv");for(auto* f:{&rows,&summary,&force})*f<<std::setprecision(17);
    rows<<"dimension,jitter,smooth_law,field,native_id,J,n,k,gamma,p_pa,Ace_x,Ace_y,Ace_z,actual_rate,discrete_reference,discrete_limit,analytic_actual_input_rate,analytic_limit,intended_unperturbed_rate,q_x,q_y,q_z,analytic_q_x,analytic_q_y,analytic_q_z,q_limit,negative_q_over_bound,negative_rate_over_bound,fallback_gamma_separation_over_bound\n";
    summary<<"dimension,jitter,smooth_law,field,rows,max_discrete_ratio,max_analytic_ratio,max_q_ratio,max_negative_q_ratio,max_negative_rate_ratio,max_gamma_separation_ratio\n";
    force<<"dimension,jitter,native_id,Ace_x,Ace_y,Ace_z,physical_as_x,physical_as_y,physical_as_z,complete_rate\n";
    unsigned cases=0,checks=0,forceCases=0,forceRows=0;
    for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){GravityActual a(dim,jitter,standardGamma);forceRows+=a.ForceFreefall(force);forceCases++;for(bool law:{false,true})for(unsigned field=0;field<6;field++){checks+=a.Check(field,law,rows,summary);cases++;}}
    for(auto* f:{&rows,&summary,&force}){f->flush();Require(bool(*f),"Diagnostic write failed");}
    Require(cases==48&&checks==864&&forceCases==4&&forceRows==72,"Declared gravity coverage differs");
    std::ofstream done(out/"completion.json");done<<"{\"passed\":true,\"stage\":\"upl_gravity_cpu_r1\",\"gamma_policy\":\""<<(standardGamma? "standard":"norm")<<"\",\"gamma_policy_changes_oracle_only\":true,\"field_cases\":"<<cases<<",\"rate_flux_rows\":"<<checks<<",\"actual_complete_rate_calls\":52,\"actual_force_ct_calls\":"<<forceCases<<",\"force_freefall_rows\":"<<forceRows<<",\"nonzero_Gravity_and_CSP_gravity\":true,\"prior_propagated_bounds\":true,\"independent_all_particle_reference\":true,\"public_guard_changed\":false,\"wall_tested\":false,\"actual_Run_or_ComputeStep_called\":false,\"completed_physical_steps\":0,\"default_OFF_regression_executed\":false,\"final_material_mobility_policy_accepted\":false,\"mechanical_hydrostatic_well_balance_accepted\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Completion write failed");
    std::cout<<"Conditional CPU gravity operator checks passed; no public/wall/trajectory acceptance.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Gravity fixture failed; preserve output\n";return 2;}
}
