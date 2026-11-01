// Actual private CPU P3 helper, static manufactured cell tables; not a physical run.
#define main RetainedP2FeedbackMain
#include "upl_p2_feedback_harness_r1.cpp"
#undef main
#include <limits>
static tdouble3 Product(const tmatrix3d& c,const tdouble3& g){
  return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);
}
static double Dot(const tdouble3& a,const tdouble3& b){return a.x*b.x+a.y*b.y+a.z*b.z;}
class Actual:public Feedback{
  unsigned Dim,Native;bool Periodic,Jitter;
  std::vector<unsigned> Cells;
  static constexpr float Sentinel=1234567.0f;
  struct Particle{tdouble3 x;unsigned id,key;bool ghost;};
  std::vector<Particle> Particles;
  unsigned Owner(unsigned id)const{
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])&&Idpc[p]==id)return p;
    throw std::runtime_error("Native owner missing in fixture");
  }
  std::vector<double> Reference(const std::vector<tfloat3>& ace,const std::vector<double>& theta)const{
    std::vector<double> result(Np,0);const double kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,k=SoilCte.HydraulicConductivity;
    const double v0=double(MassFluid)/RhopZero,gn=sqrt(Dot(ToTDouble3(Gravity),ToTDouble3(Gravity))),gamma=rho*(gn>0?gn:9.80665);
    // Independent all-particle search: no production nsearch or cell ranges.
    for(unsigned i=0;i<Np;i++)if(CODE_IsNormal(Codec[i])){
      double lp=0,da=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0);
      if(k>0)for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])){
        tdouble3 d=Posc[i]-Posc[j];if(Dim==2)d.y=0;const double rr=Dot(d,d);
        if(rr>KernelSize2||rr<ALMOSTZERO)continue;
        const tdouble3 g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr)));
        const tdouble3 gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);
        const double v=v0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=v*Dot(d,gi+gj)/(rr+double(Eta2));
        lp+=w*dp;lx=lx+d*w;gp=gp-gi*(v*dp);da+=v*Dot(ToTDouble3(ace[j])-ToTDouble3(ace[i]),gi);
      }
      const double n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i];
      result[i]=kw/n*(-theta[i]+k/gamma*(lp-Dot(gp,lx)+rho*da));
    }
    for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(Codec[i]))result[i]=result[Owner(Idpc[i])];
    return result;
  }
public:
  Actual(unsigned dim,bool jitter,bool periodic):Feedback(dim,dim==2?9:27),Dim(dim),Native(dim==2?9:27),Periodic(periodic),Jitter(jitter){
    DynamicPorePressure=true;SoilCte.HydraulicConductivity=1e-5f;
    if(periodic){PeriActive=1;PeriX=true;PeriY=PeriZ=false;PeriXinc=TDouble3(.75,0,0);ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);}
    KernelH=.25f;KernelSize=.5f;KernelSize2=.25f;Eta2=.000625f;
    CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;CSP.kwend=fsph::GetKernelWendland_Ctes(Simulate2D,KernelH);
    InitPorosityObserverCpu();unsigned id=0;
    for(int y=(dim==3?-1:0);y<=(dim==3?1:0);y++)for(int z=-1;z<=1;z++)for(int x=-1;x<=1;x++){
      tdouble3 p=TDouble3(1.+x*Dp,dim==3?1.+y*Dp:0.,1.+z*Dp);
      if(jitter){const unsigned axis=id%dim;const double offset=(id%2?1.:-1.)*Dp/8.;if(axis==0)p.x+=offset;else if(axis==1&&dim==3)p.y+=offset;else p.z+=offset;}
      Particles.push_back({p,id++,0,false});
    }
    if(periodic){auto a=Particles.front(),b=Particles.back();a.x.x+=.75;b.x.x-=.75;a.ghost=b.ghost=true;Particles.push_back(a);Particles.push_back(b);}
    Np=unsigned(Particles.size());CaseNp=CaseNfluid=Native;NpfPer=periodic?2:0;NpbPer=0;
    Require(Np<=CpuParticlesSize,"Fixture exceeds allocated arrays");
    const tuint3 nc=TUint3(4,dim==3?3:1,3);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(27,2,2);
    for(auto& p:Particles){const unsigned cx=unsigned(p.x.x/KernelSize),cy=dim==3?unsigned(p.x.y/KernelSize):0,cz=unsigned(p.x.z/KernelSize);Require(cx<nc.x&&cy<nc.y&&cz<nc.z,"Cell fixture outside table");p.key=cx+nc.x*(cy+nc.y*cz);}
    std::stable_sort(Particles.begin(),Particles.end(),[](const Particle& a,const Particle& b){return a.key<b.key;});
    Cells.assign(2*(ncell+1),0);unsigned cursor=0;
    for(unsigned c=0;c<=ncell;c++){while(cursor<Np&&Particles[cursor].key<c)cursor++;Cells[ncell+1+c]=cursor;}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));
    for(unsigned p=0;p<Np;p++){
      const auto& a=Particles[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=a.ghost?CODE_SetPeriodic(CODE_TYPE_FLUID):CODE_TYPE_FLUID;
      const unsigned cx=a.key%nc.x,cy=(a.key/nc.x)%nc.y,cz=a.key/(nc.x*nc.y);Dcellc[p]=DCEL_Cell(code,cx,cy,cz);
      Require(DCEL_Cellx(code,Dcellc[p])==cx&&DCEL_Celly(code,Dcellc[p])==cy&&DCEL_Cellz(code,Dcellc[p])==cz,"Static packed cell round-trip failed");
      PoroJc[p]=.9375+.03125*(a.id%5);PoroThetac[p]=0;Velrhopc[p]=TFloat4(0,0,0,RhopZero);
      Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PorePressc[p]=PorePress0c[p]=0;PorePressRatec[p]=Sentinel;
      CorrMatc[p]=TMatrix3d();FSNormalc[p]=TFloat3(0);FSTypec[p]=FST_Inner;PosDivc[p]=0;HydroMechLoadAcec[p]=TFloat3(0);
    }
  }
  unsigned CtSuppression(std::ostream& out,bool kpositive){
    Require(!Periodic,"ct suppression uses nonperiodic patches");SoilCte.HydraulicConductivity=kpositive?1e-5f:0;
    for(unsigned p=0;p<Np;p++){Velrhopc[p].x=float(-Posc[p].x/32.);Velrhopc[p].z=float(-Posc[p].z/32.);if(Dim==3)Velrhopc[p].y=float(-Posc[p].y/32.);PorePressc[p]=float(1024+125*Posc[p].x+500*Posc[p].z);}
    PreInteraction_Forces();ComputeFreeSurfaceTracking();std::fill(PorePressRatec,PorePressRatec+Np,Sentinel);
    const auto parameters=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec,FSTypec,FSNormalc,nullptr,CorrMatc,Arc,Acec,nullptr,SHIFT_None,nullptr,nullptr,nullptr,Sigmac,Rsigmac,nullptr);
    StInterResultc result{};Interaction_Forces_ct(parameters,result);double maxTheta=0;
    for(unsigned p=0;p<Np;p++){Require(PorePressRatec[p]==Sentinel,"Old ct pressure source was not suppressed");maxTheta=(std::max)(maxTheta,fabs(PoroThetac[p]));}
    Require(maxTheta>.01,"ct observer theta test is vacuous");out<<Dim<<','<<Jitter<<','<<kpositive<<','<<Np<<','<<maxTheta<<",true\n";PosInteraction_Forces();return Np;
  }
  unsigned Check(unsigned field,std::ostream& rows,std::ostream& summary){
    const char* names[]={"k0_compression","k0_dilation","affine_equilibrium","constant_flux","quadratic_affine_acceleration","affine_acceleration_divergence","quadratic_zero_flux"};
    Require(field<7,"Unknown field");SoilCte.HydraulicConductivity=field<2?0:1e-5f;
    for(unsigned p=0;p<Np;p++)Velrhopc[p]=TFloat4(0,0,0,RhopZero);
    PreInteraction_Forces();
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))CorrMatc[p]=TMatrix3d(std::numeric_limits<double>::quiet_NaN());
    ComputeFreeSurfaceTracking();unsigned ghosts=0,ghostPairs=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){const unsigned owner=Owner(Idpc[p]);Require(!memcmp(CorrMatc+p,CorrMatc+owner,sizeof(tmatrix3d)),"Tracking did not repair ghost C by native ID");ghosts++;}
    const tdouble3 gradient=TDouble3(125,Dim==3?250:0,500);
    for(unsigned p=0;p<Np;p++){
      const tdouble3 x=Posc[p];double pressure=1024;tdouble3 ace=TDouble3(0);
      if(field==0||field==1||field==2){pressure+=Dot(gradient,x);ace=gradient*(-1./SoilCte.PoreWaterRho);}
      if(field==3)ace=TDouble3(.125,Dim==3?-.25:0,.5);
      if(field==4||field==6){pressure+=32*x.x*x.x+16*x.z*x.z+(Dim==3?8*x.y*x.y:0);ace=field==6?TDouble3(-64*x.x/1000.,Dim==3?-16*x.y/1000.:0,-32*x.z/1000.):TDouble3(x.x/8.,Dim==3?x.y/16.:0,-x.z/32.);}
      if(field==5)ace=TDouble3(x.x/8.+x.z/32.,Dim==3?x.y/16.+x.x/64.:0,x.z/4.-x.x/32.);
      PorePressc[p]=float(pressure);Acec[p]=ToTFloat3(ace);PoroThetac[p]=field==0?-1./32.:(field==1?1./32.:0.);PorePressRatec[p]=Sentinel;
    }
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))PorePressc[p]=PorePressc[Owner(Idpc[p])];
    std::vector<tfloat3> expectedAce(Acec,Acec+Np);std::vector<double> expectedTheta(PoroThetac,PoroThetac+Np);
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      const unsigned owner=Owner(Idpc[p]);expectedAce[p]=expectedAce[owner];expectedTheta[p]=expectedTheta[owner];
      Acec[p]=TFloat3(std::numeric_limits<float>::quiet_NaN());PoroThetac[p]=std::numeric_limits<double>::quiet_NaN();
      for(unsigned i=0;i<Np;i++)if(CODE_IsNormal(Codec[i])){tdouble3 d=Posc[i]-Posc[p];if(Dim==2)d.y=0;if(Dot(d,d)>ALMOSTZERO&&Dot(d,d)<KernelSize2)ghostPairs++;}
    }
    if(Periodic)Require(ghosts==2&&ghostPairs>0,"Periodic repair test is empty");
    const auto reference=Reference(expectedAce,expectedTheta);ComputeDynamicPorePressureRateCpu();double maxError=0,maxRate=0,maxNull=0;unsigned checked=0;
    for(unsigned p=0;p<Np;p++){
      Require(std::isfinite(PorePressRatec[p])&&PorePressRatec[p]!=Sentinel,"Actual helper did not overwrite a finite full rate");
      const double error=fabs(double(PorePressRatec[p])-reference[p]),limit=32*FLT_EPSILON*(std::max)(1.,fabs(reference[p]))+1e-6;
      Require(error<=limit,"Actual cell-list rate differs from independent all-particle reference");
      maxError=(std::max)(maxError,error);maxRate=(std::max)(maxRate,fabs(double(PorePressRatec[p])));
      if(field<2)Require(PorePressRatec[p]==float(reference[p]),"k0 compression overwrite is not exact float reference");
      if(!Periodic&&(field==2||field==3)){maxNull=(std::max)(maxNull,fabs(double(PorePressRatec[p])));Require(fabs(double(PorePressRatec[p]))<=.001,"Affine equilibrium/constant flux exceeds declared roundoff floor");}
      if(CODE_IsPeriodic(Codec[p])){const unsigned owner=Owner(Idpc[p]);Require(!memcmp(Acec+p,Acec+owner,sizeof(tfloat3))&&!memcmp(PoroThetac+p,PoroThetac+owner,sizeof(double))&&!memcmp(PorePressRatec+p,PorePressRatec+owner,sizeof(float)),"Ghost Ace/theta/rate ownership repair is not exact");}
      rows<<Dim<<','<<Jitter<<','<<Periodic<<','<<names[field]<<','<<p<<','<<Idpc[p]<<','<<CODE_IsPeriodic(Codec[p])<<','<<PoroJc[p]<<','<<PoroThetac[p]<<','<<PorePressc[p]<<','<<PorePressRatec[p]<<','<<reference[p]<<','<<error<<','<<limit<<'\n';checked++;
    }
    summary<<Dim<<','<<Jitter<<','<<Periodic<<','<<names[field]<<','<<checked<<','<<ghosts<<','<<ghostPairs<<','<<maxError<<','<<maxRate<<','<<maxNull<<'\n';PosInteraction_Forces();return checked;
  }
};
class ActualR2:public Actual{
  unsigned Dimension;bool IsJitter,IsPeriodic;
public:
  ActualR2(unsigned dimension,bool jitter,bool periodic):Actual(dimension,jitter,periodic),Dimension(dimension),IsJitter(jitter),IsPeriodic(periodic){}
  void PeriodicCProof(unsigned field,std::ostream& out){
    Require(IsPeriodic,"C ownership proof requires actual images");
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))CorrMatc[p]=TMatrix3d(std::numeric_limits<double>::quiet_NaN());
    unsigned poisoned=0;for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){Require(std::isnan(CorrMatc[p].a11),"C poison absent");poisoned++;}
    ComputeFreeSurfaceTracking();unsigned repaired=0;double minimumOwnerNorm=DBL_MAX;
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      unsigned owner=UINT_MAX;for(unsigned i=0;i<Np;i++)if(CODE_IsNormal(Codec[i])&&Idpc[i]==Idpc[p])owner=i;
      Require(owner!=UINT_MAX,"C proof owner missing");const auto& c=CorrMatc[owner];
      const double norm=fabs(c.a11)+fabs(c.a12)+fabs(c.a13)+fabs(c.a21)+fabs(c.a22)+fabs(c.a23)+fabs(c.a31)+fabs(c.a32)+fabs(c.a33);
      Require(std::isfinite(norm)&&norm>1e-12,"Owner C is zero/nonfinite: ownership proof vacuous");
      Require(!memcmp(CorrMatc+p,CorrMatc+owner,sizeof(tmatrix3d)),"C proof ownership mismatch");minimumOwnerNorm=(std::min)(minimumOwnerNorm,norm);repaired++;
    }
    Require(poisoned==2&&repaired==2,"C proof image count missing");
    out<<Dimension<<','<<IsJitter<<','<<field<<','<<poisoned<<','<<repaired<<','<<minimumOwnerNorm<<'\n';
  }
  void CtValues(bool positiveK,std::ostream& out)const{
    for(unsigned p=0;p<Np;p++)out<<Dimension<<','<<IsJitter<<','<<positiveK<<','<<Idpc[p]<<','<<PorePressRatec[p]<<'\n';
  }
};
static int RetainedP3ActualMain(int argc,char** argv){
  if(argc==3&&std::string(argv[1])=="--feedback-control"){char* args[]={argv[0],const_cast<char*>("--out"),argv[2]};return RetainedP2FeedbackMain(3,args);}
  try{
    Require(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path folder(argv[2]);Require(!fs::exists(folder),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,folder.string(),"data");AppInfo.LogInit((folder/"Run.out").string());
    std::ofstream rows(folder/"rates.csv"),summary(folder/"summary.csv"),ct(folder/"ct_suppression.csv"),cproof(folder/"periodic_c.csv"),ctvalues(folder/"ct_values.csv");
    for(auto* f:{&rows,&summary,&ct,&cproof,&ctvalues})*f<<std::setprecision(17);
    rows<<"dimension,jitter,periodic,field,index,native_id,is_ghost,J,theta,p_pa,actual_rate_pa_s,reference_rate_pa_s,absolute_error,limit\n";
    summary<<"dimension,jitter,periodic,field,checked,ghosts,ghost_neighbor_pairs,max_reference_error,max_absolute_rate,max_null_rate\n";
    ct<<"dimension,jitter,positive_k,checked,max_absolute_theta,sentinel_unchanged\n";cproof<<"dimension,jitter,field,poisoned,repaired,minimum_owner_C_L1\n";ctvalues<<"dimension,jitter,positive_k,native_id,actual_rate_sentinel\n";
    unsigned checks=0,ctchecks=0,cases=0,cProofs=0;
    for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){
      {ActualR2 a(dim,jitter,false);for(bool k:{false,true}){ctchecks+=a.CtSuppression(ct,k);a.CtValues(k,ctvalues);}for(unsigned f=0;f<7;f++){checks+=a.Check(f,rows,summary);cases++;}}
      {ActualR2 a(dim,jitter,true);for(unsigned f:{0u,2u,4u}){a.PeriodicCProof(f,cproof);cProofs++;checks+=a.Check(f,rows,summary);cases++;}}
    }
    for(auto* f:{&rows,&summary,&ct,&cproof,&ctvalues}){f->flush();Require(bool(*f),"Diagnostic output failed");}
    std::ofstream done(folder/"complete.json");done<<"{\"passed\":true,\"cases\":"<<cases<<",\"rate_checks\":"<<checks<<",\"ct_sentinel_checks\":"<<ctchecks<<",\"periodic_C_proofs\":"<<cProofs<<",\"actual_private_helper\":true,\"independent_all_particle_reference\":true,\"static_multicell_fixture\":true,\"periodic_owner_repair_nonempty\":true,\"actual_RunPeriodic_tested\":false,\"physical_trajectory\":false,\"integration_half_test\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Completion write failed");std::cout<<"Actual private P3 component passed; no physical trajectory acceptance.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Actual P3 r2 fixture failed; preserve output and Run.out\n";return 2;}
}


// New private smooth-k component; the retained implementation above is kept for OFF exact control.
class PermeabilityActual:public ActualR2{
  inline static unsigned RateCalls=0;
  unsigned Dim;bool Jittered,PeriodicCloud;
  static constexpr float RateSentinel=1234567.f;
  struct Expected{double rate=0,k=0,n=0,chain=0,base=0,analytic=0;tdouble3 gj=TDouble3(0),gp=TDouble3(0),drive=TDouble3(0);};
  unsigned OwnerOf(unsigned id)const{
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])&&Idpc[p]==id)return p;
    throw std::runtime_error("k(J) native owner missing");
  }
  double Alpha()const{return 1./((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);}
  void RunActualRate(){RateCalls++;ComputeDynamicPorePressureRateCpu();}
  double Law(unsigned p)const{
    const double k0=SoilCte.HydraulicConductivity;
    return k0==0?0:k0*exp(Alpha()*(PoroJc[p]-1.));
  }
  std::vector<Expected> Reference(const std::vector<tfloat3>& ace,const std::vector<double>& theta)const{
    std::vector<Expected> r(Np);const double kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,V0=double(MassFluid)/RhopZero;
    const double gn=sqrt(Dot(ToTDouble3(Gravity),ToTDouble3(Gravity))),gamma=rho*(gn>0?gn:9.80665),k0=SoilCte.HydraulicConductivity;
    for(unsigned i=0;i<Np;i++)if(CODE_IsNormal(Codec[i])){
      auto& a=r[i];a.k=Law(i);a.n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i];double lp=0,da=0;tdouble3 lx=TDouble3(0);
      if(k0>0)for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])){
        tdouble3 d=Posc[i]-Posc[j];if(Dim==2)d.y=0;const double rr=Dot(d,d);
        if(rr>KernelSize2||rr<ALMOSTZERO)continue;
        const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr)));
        const auto gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);
        const double Vj=V0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=Vj*Dot(d,gi+gj)/(rr+double(Eta2));
        lp+=w*dp;lx=lx+d*w;a.gp=a.gp-gi*(Vj*dp);
        a.gj=a.gj+gi*(Vj*(PoroJc[j]-PoroJc[i]));
        da+=Vj*Dot(ToTDouble3(ace[j])-ToTDouble3(ace[i]),gi);
      }
      a.drive=a.gp+ToTDouble3(ace[i])*rho;a.base=lp-Dot(a.gp,lx)+rho*da;
      a.chain=k0>0?Alpha()*a.k*Dot(a.gj,a.drive):0;
      a.rate=kw/a.n*(-theta[i]+a.k/gamma*a.base+a.chain/gamma);
    }
    for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(Codec[i]))r[i]=r[OwnerOf(Idpc[i])];
    return r;
  }
  void Assign(unsigned field,unsigned sub){
    const tdouble3 b=TDouble3(1./32.,Dim==3?1./128.:0,1./64.);
    const tdouble3 pg=TDouble3(125,Dim==3?250:0,500);
    SoilCte.HydraulicConductivity=field==5?0:1e-5f;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      const auto x=Posc[p];PoroJc[p]=field==0?1.:(field==1?1.+(sub?1.:-1.)/64.:1.+Dot(b,x-TDouble3(1,Dim==3?1:0,1)));
      double pressure=1024;tdouble3 a=TDouble3(0);
      if(field==0){pressure+=32*x.x*x.x+16*x.z*x.z+(Dim==3?8*x.y*x.y:0);a=TDouble3(x.x/8.,Dim==3?x.y/16.:0,-x.z/32.);}
      if(field==1){pressure+=32*x.x*x.x+16*x.z*x.z+(Dim==3?8*x.y*x.y:0);a=TDouble3(x.x/8.,Dim==3?x.y/16.:0,-x.z/32.);}
      if(field==2||field==4||field==5)pressure+=Dot(pg,x);
      if(field==3)a=TDouble3(.125,Dim==3?.25:0,.5)*(sub?-1.:1.);
      if(field==4)a=pg*(-1./SoilCte.PoreWaterRho);
      if(field==5)a=TDouble3(.125,Dim==3?.25:0,.5);
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);PorePressc[p]=float(pressure);PorePress0c[p]=0;
      PoroThetac[p]=field==5?(sub?1./32.:-1./32.):0;Acec[p]=ToTFloat3(a);
    }
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      const unsigned q=OwnerOf(Idpc[p]);PoroJc[p]=PoroJc[q];PoroThetac[p]=PoroThetac[q];
      PorePressc[p]=PorePressc[q];PorePress0c[p]=0;Acec[p]=Acec[q];Velrhopc[p]=Velrhopc[q];
    }
  }
public:
  static unsigned ActualRateCalls(){return RateCalls;}
  PermeabilityActual(unsigned dim,bool jitter,bool periodic):ActualR2(dim,jitter,periodic),Dim(dim),Jittered(jitter),PeriodicCloud(periodic){
    DynamicPoreConductivity=true;DynamicPoreConductivityCk=1./8.;InitPorosityObserverCpu();
  }
  unsigned GuardCases(std::ostream& out){
    unsigned checks=0;
    auto rejectInit=[&](const char* label){
      bool caught=false;try{InitPorosityObserverCpu();}catch(const std::exception&){caught=true;}
      Require(caught,"Invalid k(J) admission was not rejected");out<<label<<",InitPorosityObserverCpu,rejected\n";checks++;
    };
    const double good=DynamicPoreConductivityCk;
    for(double bad:{0.,-1.,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),std::numeric_limits<double>::denorm_min()}){
      DynamicPoreConductivityCk=bad;rejectInit("invalid_Ck_or_unrepresentable_alpha");
    }
    DynamicPoreConductivityCk=good;DynamicPorePressure=false;rejectInit("dynamic_model_missing");DynamicPorePressure=true;
    DynamicPoreConductivity=false;DynamicPoreConductivityCk=std::numeric_limits<double>::quiet_NaN();InitPorosityObserverCpu();
    for(unsigned p=0;p<Np;p++)Require(GetDynamicConductivityCpu(p)==double(SoilCte.HydraulicConductivity),"OFF getter read new Ck");
    out<<"OFF_Ck_unused,GetDynamicConductivityCpu,exact_k0\n";checks++;
    DynamicPoreConductivity=true;DynamicPoreConductivityCk=good;InitPorosityObserverCpu();
    SoilCte.HydraulicConductivity=0;for(unsigned p=0;p<Np;p++){PoroJc[p]=1024;Require(GetDynamicConductivityCpu(p)==0,"k0 getter evaluated exponential");}
    out<<"k0_large_J,GetDynamicConductivityCpu,exact_zero_fastpath\n";checks++;
    SoilCte.HydraulicConductivity=1e-5f;InitPorosityObserverCpu();
    for(bool underflow:{false,true}){
      DynamicPoreConductivityCk=underflow?1e-8:good;InitPorosityObserverCpu();
      PreInteraction_Forces();for(unsigned p=0;p<Np;p++){PoroJc[p]=underflow?.75:1024.;PoroThetac[p]=0;PorePressc[p]=0;PorePressRatec[p]=RateSentinel;}
      bool caught=false;try{RunActualRate();}catch(const std::exception&){caught=true;}
      PosInteraction_Forces();Require(caught,"Unrepresentable positive k was silently admitted");
      out<<(underflow?"positive_k_underflow":"positive_k_overflow")<<",ComputeDynamicPorePressureRateCpu,rejected\n";checks++;
    }
    DynamicPoreConductivityCk=good;InitPorosityObserverCpu();return checks;
  }
  unsigned StepScales(std::ostream& out){
    Require(!PeriodicCloud,"Scale component uses native-only cloud");
    // These are declared manufactured component inputs, not observed solver force statistics.
    VelMax=0;ViscDtMax=0;PoreDtSafety=.1f;SoilCte.HydraulicConductivity=1e-5f;
    const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,k0=SoilCte.HydraulicConductivity;
    const double m=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.,gamma=rhow*9.80665;
    for(unsigned field=0;field<2;field++){
      double cu2=0,dmax=0,oldDmax=0,kmax=0;
      for(unsigned p=0;p<Np;p++){
        PoroJc[p]=field?1.+(Posc[p].x-1.)/32.+(Posc[p].z-1.)/64.:1.+1./64.;
        const double j=PoroJc[p],n=1.-(1.-double(SoilCte.Porosity))/j,rho=rhow+(double(RhopZero)-rhow)/j;
        const double k=k0*exp((j-1.)/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk)),b=kw/n;
        cu2=(std::max)(cu2,(m+b)/rho);dmax=(std::max)(dmax,b*k/gamma);oldDmax=(std::max)(oldDmax,b*k0/gamma);kmax=(std::max)(kmax,k);
      }
      double wave,pore;GetDynamicStepScalesCpu(wave,pore);
      const double wr=double(KernelH)/sqrt(cu2),pr=double(PoreDtSafety)*double(KernelH)*KernelH/dmax,old=double(PoreDtSafety)*double(KernelH)*KernelH/oldDmax;
      const double wt=64*DBL_EPSILON*(std::max)(fabs(wr),DBL_MIN),pt=64*DBL_EPSILON*(std::max)(fabs(pr),DBL_MIN);
      Require(std::isfinite(wave)&&std::isfinite(pore)&&fabs(wave-wr)<=wt&&fabs(pore-pr)<=pt,"Actual current-k time scales differ from independent local n/rho/k reference");
      Require(kmax>k0&&fabs(pore-old)/old>1e-3,"Current-k pore time-scale distinction is empty");
      out<<Dim<<','<<(field?"affine_J":"uniform_J")<<','<<k0<<','<<kmax<<','<<cu2<<','<<dmax<<','<<oldDmax<<','<<wave<<','<<wr<<','<<wt<<','<<pore<<','<<pr<<','<<pt<<','<<old<<",true\n";
    }return 2;
  }
  unsigned Evaluate(unsigned field,unsigned sub,std::ostream& rows,std::ostream& law,std::ostream& summary,std::ostream& periodic){
    const char* names[]={"J1_known_k","uniform_known_k","affineJ_affinep_source","affineJ_constantp_Ace_sign","affineJ_zero_drive","k0_theta_sign"};
    Require(field<6,"Unknown permeability field");PreInteraction_Forces();Assign(field,sub);
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p]))CorrMatc[p]=TMatrix3d(std::numeric_limits<double>::quiet_NaN());
    ComputeFreeSurfaceTracking();unsigned ghostCount=0,ghostPairs=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      const unsigned q=OwnerOf(Idpc[p]);const auto& c=CorrMatc[q];
      const double norm=fabs(c.a11)+fabs(c.a12)+fabs(c.a13)+fabs(c.a21)+fabs(c.a22)+fabs(c.a23)+fabs(c.a31)+fabs(c.a32)+fabs(c.a33);
      Require(norm>1e-12&&std::isfinite(norm)&&!memcmp(CorrMatc+p,CorrMatc+q,sizeof(tmatrix3d)),"Periodic k(J) C ownership proof empty");ghostCount++;
      for(unsigned i=0;i<Np;i++)if(CODE_IsNormal(Codec[i])){auto d=Posc[i]-Posc[p];if(Dim==2)d.y=0;if(Dot(d,d)>ALMOSTZERO&&Dot(d,d)<KernelSize2)ghostPairs++;}
    }
    std::vector<tfloat3> ace(Acec,Acec+Np);std::vector<double> theta(PoroThetac,PoroThetac+Np);
    const auto expected=Reference(ace,theta);
    for(unsigned p=0;p<Np;p++){PorePressRatec[p]=RateSentinel;if(CODE_IsPeriodic(Codec[p])){Acec[p]=TFloat3(std::numeric_limits<float>::quiet_NaN());PoroThetac[p]=std::numeric_limits<double>::quiet_NaN();}}
    RunActualRate();std::vector<float> actual(PorePressRatec,PorePressRatec+Np),off;double maxError=0,maxNull=0,minChainRatio=DBL_MAX,minK=DBL_MAX,maxK=0;
    if(!PeriodicCloud&&(field==0||field==2||field==3||field==5)){
      DynamicPoreConductivity=false;RunActualRate();off.assign(PorePressRatec,PorePressRatec+Np);DynamicPoreConductivity=true;
      std::copy(actual.begin(),actual.end(),PorePressRatec);
    }
    const double kw=SoilCte.PoreWaterBulkModulus,rho=SoilCte.PoreWaterRho,gamma=rho*9.80665;
    const tdouble3 b=TDouble3(1./32.,Dim==3?1./128.:0,1./64.);
    unsigned checked=0;
    for(unsigned p=0;p<Np;p++){
      const auto& e=expected[p];const double got=actual[p],error=fabs(got-e.rate),limit=32*FLT_EPSILON*(std::max)(1.,fabs(e.rate))+1e-6;
      Require(std::isfinite(got)&&actual[p]!=RateSentinel&&error<=limit,"Actual variable-k cell-list rate differs from independent reference");
      const double k=GetDynamicConductivityCpu(p),ktol=5e-13*(std::max)(fabs(e.k),DBL_MIN);
      Require(std::isfinite(k)&&k>=0&&fabs(k-e.k)<=ktol,"Actual local conductivity differs from exponential law");
      if(field==0)Require(k==double(SoilCte.HydraulicConductivity),"J1 conductivity did not return exact k0");
      if(!off.empty()&&(field==0||field==5))Require(!memcmp(&actual[p],&off[p],sizeof(float)),"J1/k0 ON/OFF same-state rate is not exact");
      double analytic=0,analyticError=0,chainRatio=0;
      if(!PeriodicCloud&&(field==2||field==3)){
        const tdouble3 pressureGradient=field==2?TDouble3(125,Dim==3?250:0,500):TDouble3(0);
        analytic=kw/e.n/gamma*Alpha()*e.k*Dot(b,pressureGradient+ToTDouble3(ace[p])*rho);analyticError=fabs(got-analytic);
        Require(analyticError<=32*FLT_EPSILON*(std::max)(1.,fabs(analytic))+1e-6,"Actual affine-J chain source differs from analytic field");
        chainRatio=fabs(got-off[p])/limit;Require(chainRatio>100,"Variable-k source effect is numerically empty");minChainRatio=(std::min)(minChainRatio,chainRatio);
      }
      if(!PeriodicCloud&&field==4){maxNull=(std::max)(maxNull,fabs(got));Require(fabs(got)<=.001,"Variable-J zero-drive balance exceeds original null bound");}
      if(field==5)Require(actual[p]==float(-kw/e.n*theta[p]),"k0 complete compression is not exact float reference");
      if(CODE_IsPeriodic(Codec[p])){const unsigned q=OwnerOf(Idpc[p]);Require(!memcmp(Acec+p,Acec+q,sizeof(tfloat3))&&!memcmp(PoroThetac+p,PoroThetac+q,sizeof(double))&&!memcmp(PorePressRatec+p,PorePressRatec+q,sizeof(float)),"Variable-k periodic Ace/theta/rate repair not exact");}
      rows<<Dim<<','<<Jittered<<','<<PeriodicCloud<<','<<names[field]<<','<<sub<<','<<p<<','<<Idpc[p]<<','<<CODE_IsPeriodic(Codec[p])<<','<<PoroJc[p]<<','<<theta[p]<<','<<PorePressc[p]<<','<<got<<','<<e.rate<<','<<error<<','<<limit<<','<<analytic<<','<<analyticError<<','<<e.chain<<','<<chainRatio<<'\n';
      law<<Dim<<','<<Jittered<<','<<PeriodicCloud<<','<<names[field]<<','<<sub<<','<<Idpc[p]<<','<<PoroJc[p]<<','<<DynamicPoreConductivityCk<<','<<Alpha()<<','<<k<<','<<e.k<<','<<fabs(k-e.k)<<','<<ktol<<','<<e.gj.x<<','<<e.gj.y<<','<<e.gj.z<<','<<e.drive.x<<','<<e.drive.y<<','<<e.drive.z<<'\n';
      maxError=(std::max)(maxError,error);minK=(std::min)(minK,k);maxK=(std::max)(maxK,k);checked++;
    }
    if(PeriodicCloud){Require(ghostCount==2&&ghostPairs>0,"Variable-k periodic case is empty");periodic<<Dim<<','<<Jittered<<','<<names[field]<<','<<ghostCount<<','<<ghostPairs<<",true,true\n";}
    if(!PeriodicCloud&&field==2){
      const std::vector<tmatrix3d> c(CorrMatc,CorrMatc+Np);
      for(unsigned p=0;p<Np;p++)Velrhopc[p].w=float(1000+37*Idpc[p]);ComputeFreeSurfaceTracking();RunActualRate();
      for(unsigned p=0;p<Np;p++)Require(!memcmp(CorrMatc+p,c.data()+p,sizeof(tmatrix3d))&&!memcmp(PorePressRatec+p,actual.data()+p,sizeof(float)),"Positive old-rho poison changed new J-derived conductivity operator");
    }
    summary<<Dim<<','<<Jittered<<','<<PeriodicCloud<<','<<names[field]<<','<<sub<<','<<checked<<','<<maxError<<','<<maxNull<<','<<minK<<','<<maxK<<','<<(minChainRatio==DBL_MAX?0:minChainRatio)<<'\n';PosInteraction_Forces();return checked;
  }
};
int main(int argc,char** argv){
  if(argc==3&&std::string(argv[1])=="--off-control"){char* args[]={argv[0],const_cast<char*>("--out"),argv[2]};return RetainedP3ActualMain(3,args);}
  try{
    Require(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY or --off-control NEW_DIRECTORY");const fs::path folder(argv[2]);Require(!fs::exists(folder),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,folder.string(),"data");AppInfo.LogInit((folder/"Run.out").string());
    std::ofstream rates(folder/"rates.csv"),law(folder/"permeability.csv"),summary(folder/"summary.csv"),guards(folder/"guards.csv"),periodic(folder/"periodic.csv"),scales(folder/"scales.csv");
    for(auto* f:{&rates,&law,&summary,&guards,&periodic,&scales})*f<<std::setprecision(17);
    rates<<"dimension,jitter,periodic,field,subcase,index,native_id,is_ghost,J,theta,p_pa,actual_rate_pa_s,reference_rate_pa_s,error,limit,affine_analytic_rate_pa_s,analytic_error,chain_unscaled,source_effect_over_original_roundoff\n";
    law<<"dimension,jitter,periodic,field,subcase,native_id,J,Ck,alpha,actual_k,reference_k,k_error,k_limit,reference_GJ_x,reference_GJ_y,reference_GJ_z,reference_drive_x,reference_drive_y,reference_drive_z\n";
    summary<<"dimension,jitter,periodic,field,subcase,checked,max_reference_error,max_null_rate,min_k,max_k,min_source_effect_over_roundoff\n";
    guards<<"case,actual_method,result\n";periodic<<"dimension,jitter,field,poisoned_images,ghost_neighbor_pairs,C_owner_exact,Ace_theta_rate_owner_exact\n";
    scales<<"dimension,field,k0,max_current_k,max_cu2,max_current_D,max_initial_k_D,actual_wave_s,reference_wave_s,wave_tolerance_s,actual_pore_s,reference_pore_s,pore_tolerance_s,old_initial_k_pore_s,force_statistics_manually_initialized\n";
    unsigned fieldCases=0,evaluations=0,checks=0,guardChecks=0,scaleChecks=0;
    {PermeabilityActual a(2,false,false);guardChecks=a.GuardCases(guards);scaleChecks=a.StepScales(scales);}
    for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){
      {PermeabilityActual a(dim,jitter,false);for(unsigned field=0;field<6;field++){fieldCases++;const unsigned parts=(field==1||field==3||field==5)?2:1;for(unsigned sub=0;sub<parts;sub++){checks+=a.Evaluate(field,sub,rates,law,summary,periodic);evaluations++;}}}
      {PermeabilityActual a(dim,jitter,true);fieldCases++;checks+=a.Evaluate(2,0,rates,law,summary,periodic);evaluations++;}
    }
    Require(fieldCases==28&&evaluations==40&&checks==728&&guardChecks==10&&scaleChecks==2&&PermeabilityActual::ActualRateCalls()==70,"Unexpected bounded component coverage");
    for(auto* f:{&rates,&law,&summary,&guards,&periodic,&scales}){f->flush();Require(bool(*f),"Permeability diagnostic output failed");}
    std::ofstream done(folder/"complete.json");done<<"{\"passed\":true,\"actual_private_helper\":true,\"field_cases\":"<<fieldCases<<",\"helper_evaluations\":"<<evaluations<<",\"rate_checks\":"<<checks<<",\"guard_checks\":"<<guardChecks<<",\"scale_checks\":"<<scaleChecks<<",\"total_actual_rate_helper_calls\":"<<PermeabilityActual::ActualRateCalls()<<",\"extra_same_state_OFF_calls\":24,\"extra_old_rho_poison_calls\":4,\"expected_rejected_rate_calls\":2,\"force_statistics_manually_initialized_for_component\":true,\"independent_all_particle_reference\":true,\"periodic_owner_repair_nonempty\":true,\"actual_RunPeriodic_tested\":false,\"physical_trajectory\":false,\"integration_half_test\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Permeability completion write failed");
    std::cout<<"Actual smooth-k component passed; no integrated or interface/general model acceptance.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Smooth-k component rejected; preserve outputs\n";return 2;}
}

