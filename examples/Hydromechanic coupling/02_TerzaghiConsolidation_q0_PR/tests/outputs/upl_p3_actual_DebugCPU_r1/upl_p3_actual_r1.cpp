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
    const tuint3 nc=TUint3(4,dim==3?3:1,3);const unsigned ncell=nc.x*nc.y*nc.z,code=DCEL_GetCode(2,2,2);
    for(auto& p:Particles){const unsigned cx=unsigned(p.x.x/KernelSize),cy=dim==3?unsigned(p.x.y/KernelSize):0,cz=unsigned(p.x.z/KernelSize);Require(cx<nc.x&&cy<nc.y&&cz<nc.z,"Cell fixture outside table");p.key=cx+nc.x*(cy+nc.y*cz);}
    std::stable_sort(Particles.begin(),Particles.end(),[](const Particle& a,const Particle& b){return a.key<b.key;});
    Cells.assign(2*(ncell+1),0);unsigned cursor=0;
    for(unsigned c=0;c<=ncell;c++){while(cursor<Np&&Particles[cursor].key<c)cursor++;Cells[ncell+1+c]=cursor;}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));
    for(unsigned p=0;p<Np;p++){
      const auto& a=Particles[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=a.ghost?CODE_SetPeriodic(CODE_TYPE_FLUID):CODE_TYPE_FLUID;
      const unsigned cx=a.key%nc.x,cy=(a.key/nc.x)%nc.y,cz=a.key/(nc.x*nc.y);Dcellc[p]=DCEL_Cell(code,cx,cy,cz);
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
int main(int argc,char** argv){
  if(argc==3&&std::string(argv[1])=="--feedback-control"){char* args[]={argv[0],const_cast<char*>("--out"),argv[2]};return RetainedP2FeedbackMain(3,args);}
  try{
    Require(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path folder(argv[2]);Require(!fs::exists(folder),"Retained output protected");
    AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,folder.string(),"data");AppInfo.LogInit((folder/"Run.out").string());
    std::ofstream rows(folder/"rates.csv"),summary(folder/"summary.csv"),ct(folder/"ct_suppression.csv");for(auto* f:{&rows,&summary,&ct})*f<<std::setprecision(17);
    rows<<"dimension,jitter,periodic,field,index,native_id,is_ghost,J,theta,p_pa,actual_rate_pa_s,reference_rate_pa_s,absolute_error,limit\n";
    summary<<"dimension,jitter,periodic,field,checked,ghosts,ghost_neighbor_pairs,max_reference_error,max_absolute_rate,max_null_rate\n";
    ct<<"dimension,jitter,positive_k,checked,max_absolute_theta,sentinel_unchanged\n";
    unsigned checks=0,ctchecks=0,cases=0;
    for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){
      {Actual a(dim,jitter,false);ctchecks+=a.CtSuppression(ct,false);ctchecks+=a.CtSuppression(ct,true);for(unsigned f=0;f<7;f++){checks+=a.Check(f,rows,summary);cases++;}}
      {Actual a(dim,jitter,true);for(unsigned f:{0u,2u,4u}){checks+=a.Check(f,rows,summary);cases++;}}
    }
    for(auto* f:{&rows,&summary,&ct}){f->flush();Require(bool(*f),"Diagnostic output failed");}
    std::ofstream done(folder/"complete.json");done<<"{\"passed\":true,\"cases\":"<<cases<<",\"rate_checks\":"<<checks<<",\"ct_sentinel_checks\":"<<ctchecks<<",\"actual_private_helper\":true,\"independent_all_particle_reference\":true,\"static_multicell_fixture\":true,\"periodic_owner_repair_nonempty\":true,\"actual_RunPeriodic_tested\":false,\"physical_trajectory\":false,\"integration_half_test\":false,\"physical_acceptance\":false}\n";done.flush();Require(bool(done),"Completion write failed");std::cout<<"Actual private P3 component passed; no physical trajectory acceptance.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Actual P3 fixture failed; preserve output and Run.out\n";return 2;}
}
