// Constant-k private GPU P3 components; actual APIs, no coupled Run/step admission.
#define main RetainedGpuK0TimeMain
#include "upl_gpu_k0_time_r1.cpp"
#undef main
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JArraysGpu.h"
#include <array>

namespace gd {
constexpr float Sentinel=1234567.f;
static bool NearScale(double actual,double reference){return std::isfinite(actual)&&std::isfinite(reference)&&fabs(actual-reference)<=64.*DBL_EPSILON*(std::max)(DBL_MIN,fabs(reference));}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(const tmatrix3d& a,tdouble3 b){
  return TDouble3(a.a11*b.x+a.a12*b.y+a.a13*b.z,a.a21*b.x+a.a22*b.y+a.a23*b.z,a.a31*b.x+a.a32*b.y+a.a33*b.z);
}
struct Ref {double rate=0,budget=0,pressure=0,acceleration=0;};
static std::vector<Ref> Reference(unsigned np,unsigned npb,const StCteSph& csp,double solid0,double kw,double rhow,double k,double vol0
  ,const std::vector<double2>& xy,const std::vector<double>& z,const std::vector<typecode>& code
  ,const std::vector<tmatrix3d>& c,const std::vector<float3>& ace,const std::vector<double>& j
  ,const std::vector<double>& theta,const std::vector<float>& p){
  std::vector<Ref> out(np);
  for(unsigned i=npb;i<np;i++)if(CODE_IsNormal(code[i])&&CODE_IsFluid(code[i])){
    double lp=0,da=0,alp=0,ada=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),alx=TDouble3(0),agp=TDouble3(0);
    if(k>0)for(unsigned b=0;b<np;b++)if(CODE_IsFluid(code[b])){
      const tdouble3 d=TDouble3(xy[i].x-xy[b].x,0,z[i]-z[b]);const double rr=Dot(d,d);
      if(rr>double(csp.kernelsize2)||rr<ALMOSTZERO)continue;
      const tdouble3 g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(csp,float(rr)));
      const auto gi=Product(c[i],g),gj=Product(c[b],g);const double v=vol0*j[b],dp=double(p[i])-p[b];
      const double w=v*Dot(d,gi+gj)/(rr+double(csp.eta2));
      lp+=w*dp;alp+=fabs(w*dp);lx=lx+d*w;gp=gp-gi*(v*dp);
      alx.x+=fabs(d.x*w);alx.y+=fabs(d.y*w);alx.z+=fabs(d.z*w);
      agp.x+=fabs(gi.x*v*dp);agp.y+=fabs(gi.y*v*dp);agp.z+=fabs(gi.z*v*dp);
      const tdouble3 a=TDouble3(double(ace[b].x)-ace[i].x,double(ace[b].y)-ace[i].y,double(ace[b].z)-ace[i].z);
      da+=v*Dot(a,gi);ada+=v*(fabs(a.x*gi.x)+fabs(a.y*gi.y)+fabs(a.z*gi.z));
    }
    const double B=kw/(1.-solid0/j[i]),gamma=rhow*9.80665;
    const double scale=B*(fabs(theta[i])+k/gamma*(alp+Dot(agp,alx)+rhow*ada));
    out[i]={B*(-theta[i]+k/gamma*(lp-Dot(gp,lx)+rhow*da)),
      64.*FLT_EPSILON*scale+256.*DBL_EPSILON*(std::max)(1.,fabs(B*theta[i]))+1e-6,
      B*k/gamma*(lp-Dot(gp,lx)),B*k/gamma*rhow*da};
  }
  return out;
}
struct Totals{unsigned prefix=0,ownernegative=0,patchcases=0,patchrows=0,periodiccases=0,periodicrows=0,corners=0,scales=0,domain=0,requests=0;double ratio=0,maxerror=0;};
static void CheckRate(std::ostream& out,const std::string& label,unsigned slot,unsigned id,double actual,const Ref& ref,Totals& total){
  const double error=fabs(actual-ref.rate);Need(std::isfinite(actual)&&std::isfinite(ref.rate)&&std::isfinite(ref.budget)&&ref.budget>0&&actual!=Sentinel&&error<=ref.budget,"Actual complete rate exceeds predeclared propagated discrete-term budget");
  total.maxerror=(std::max)(total.maxerror,error);total.ratio=(std::max)(total.ratio,error/ref.budget);
  out<<label<<','<<slot<<','<<id<<','<<actual<<','<<ref.rate<<','<<error<<','<<ref.budget<<','<<error/ref.budget<<','<<ref.pressure<<','<<ref.acceleration<<'\n';
}
static void PrefixOwners(const fs::path& out,Totals& total){
  constexpr unsigned np=12,npb=2,cap=14,idini=100,idfin=104;
  Device<unsigned> ids(cap),map(5),invalid(2);Device<typecode> codes(cap);
  Device<tmatrix3d> cg(cap);Device<float3> ag(cap);Device<double> tg(cap);Device<float> rg(cap);
  std::ofstream rows(out/"prefix.csv"),negative(out/"owner_negatives.csv");
  rows<<"permutation,stage,prefix,native_owners,periodic_images,all_active_and_tail_bits_exact\n";
  negative<<"case,actual_invalid,expected_invalid,negative_nonempty,host_pool_released\n";
  const std::vector<unsigned> baseid={0,1,100,103,102,100,100,103,102,102,101,101,999,1000};
  std::vector<typecode> basecode(cap,CODE_TYPE_FLUID);basecode[0]=basecode[1]=basecode[12]=basecode[13]=CODE_TYPE_FIXED;
  for(unsigned p:{2u,4u,7u,11u})basecode[p]=CODE_SetPeriodic(CODE_TYPE_FLUID);
  basecode[5]=CODE_SetOutIgnore(CODE_TYPE_FLUID);basecode[9]=CODE_TYPE_FLOATING;
  std::vector<unsigned> baseMap;
  for(unsigned permutation=0;permutation<2;permutation++){
    auto id=baseid;auto code=basecode;if(permutation){std::reverse(id.begin()+npb,id.begin()+np);std::reverse(code.begin()+npb,code.begin()+np);}
    std::vector<tmatrix3d> c(cap);std::vector<float3> a(cap);std::vector<double> theta(cap);std::vector<float> rate(cap);
    std::vector<unsigned> owner(4,UINT_MAX);unsigned ghosts=0;
    for(unsigned p=0;p<cap;p++){
      c[p]=TMatrix3d();c[p].a11=.5+double(id[p])/16.;c[p].a22=1.;c[p].a33=2.+double(id[p])/32.;
      a[p]=make_float3(float(id[p])/32.f,-.25f,float(id[p])/64.f);theta[p]=double(id[p])/128.;rate[p]=float(id[p])+.25f;
      if(p>=npb&&p<np&&CODE_IsNormal(code[p])&&CODE_IsFluid(code[p]))owner[id[p]-idini]=p;
      if(p<np&&CODE_IsPeriodic(code[p])){c[p]=TMatrix3d(std::numeric_limits<double>::quiet_NaN());a[p]=make_float3(NAN,NAN,NAN);theta[p]=NAN;rate[p]=NAN;ghosts++;}
    }
    Need(ghosts==4&&owner[0]!=npb&&owner[3]!=npb+3,"Synthetic nonzero-prefix ownership is vacuous");
    Up(ids.p,id);Up(codes.p,code);Up(cg.p,c);Up(ag.p,a);Up(tg.p,theta);Up(rg.p,rate);
    Up(map.p,std::vector<unsigned>(5,0x1234abcd));cusph::CalcRidp(true,np-npb,npb,idini,idfin,codes.p,ids.p,map.p);
    auto rid=Down(map.p,5);Need(std::equal(owner.begin(),owner.end(),rid.begin())&&rid[4]==0x1234abcd,"Actual CalcRidp prefix/ID permutation/tail failed");
    if(!permutation)baseMap=rid;
    for(unsigned stage=0;stage<3;stage++){
      Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
      cusph::ExtendDynamicPorePeriodic(np,npb,idini,idfin,codes.p,ids.p,map.p,stage==0?cg.p:nullptr,stage==1?ag.p:nullptr,stage==1?tg.p:nullptr,stage==2?rg.p:nullptr,invalid.p);
      for(unsigned p=npb;p<np;p++)if(CODE_IsPeriodic(code[p])){const unsigned b=owner[id[p]-idini];if(stage==0)c[p]=c[b];if(stage==1){a[p]=a[b];theta[p]=theta[b];}if(stage==2)rate[p]=rate[b];}
      Need(Down(invalid.p,2)==std::vector<unsigned>({np,0x1234abcd})&&Same(c,Down(cg.p,cap))&&Same(a,Down(ag.p,cap))&&Same(theta,Down(tg.p,cap))&&Same(rate,Down(rg.p,cap)),"Requested owner extension changed prefix/tail/unrequested fields or failed exact copy");
      rows<<permutation<<','<<stage<<','<<npb<<",4,4,true\n";total.prefix++;
    }
  }
  Up(ids.p,baseid);Up(codes.p,basecode);
  for(unsigned trial=0;trial<3;trial++){
    auto rid=baseMap;rid[0]=trial==0?UINT_MAX:(trial==1?10u:2u);Up(map.p,rid);Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
    cusph::ExtendDynamicPorePeriodic(np,npb,idini,idfin,codes.p,ids.p,map.p,cg.p,nullptr,nullptr,nullptr,invalid.p);
    const auto bad=Down(invalid.p,2);Need(bad[0]==2&&bad[1]==0x1234abcd,"Missing/wrong-ID/periodic owner was not rejected before dereference");
    negative<<(trial==0?"missing":trial==1?"wrong_id":"ghost_owner")<<','<<bad[0]<<",2,true,false\n";total.ownernegative++;
  }
  rows.flush();negative.flush();Need(bool(rows)&&bool(negative),"Prefix/owner diagnostic output failed");
}
class Patch{
  static constexpr unsigned np=9,cap=11;
  Device<int2> cells{4};Device<unsigned> dcell{cap},ids{cap},fstype{cap},invalid{2};Device<typecode> code{cap};
  Device<double2> xy{cap};Device<double> z{cap},j{cap},theta{cap};Device<float4> pos{cap},vel{cap};
  Device<tmatrix3d> c{cap};Device<float3> ace{cap},normal{cap};Device<float> p{cap},rate{cap},posdiv{cap};
  std::vector<double2> xs;std::vector<double> zs,js,ths;std::vector<float> ps;std::vector<float3> as;
  std::vector<typecode> cs;std::vector<tmatrix3d> matrices;
  StDivDataGpu dvd;StCteInteraction constants{};StCteSph sph=CteSphNull();
public:
  explicit Patch(bool jitter):xs(cap),zs(cap),js(cap,1.),ths(cap),ps(cap),as(cap),cs(cap,CODE_TYPE_FIXED){
    std::vector<tmatrix3d> initialC(cap,TMatrix3d());initialC[9]=TMatrix3d(-123.25);initialC[10]=TMatrix3d(-456.5);Up(c.p,initialC);
    constants.simulate2d=1;constants.kernelh=.5f;constants.kernelsize=1;constants.kernelsize2=1;constants.poscellsize=2;constants.scell=2;constants.dp=.25f;
    constants.rhopzero=2048;constants.massf=constants.massb=128;constants.cteb=0;constants.gamma=7;constants.cs0=40;constants.eta2=.0025f;
    constants.axis=MGDIV_Z;constants.cellcode=DCEL_GetCode(1,1,1);constants.tboundary=BC_DBC;
    constants.modulus_K=89478488.f;constants.modulus_G=134217728.f;constants.hydromech=1;
    constants.porewaterbulkmodulus=67108864.f;constants.porewaterrho=1000;constants.porosity=.25f;constants.porekwn=constants.porewaterbulkmodulus/constants.porosity;
    constants.porecompgradcorr=constants.soilstressrategradcorr=1;constants.porecompsourcemode=0;
    sph.kernelh=constants.kernelh;sph.kernelsize=constants.kernelsize;sph.kernelsize2=constants.kernelsize2;sph.eta2=constants.eta2;sph.kwend=fsph::GetKernelWendland_Ctes(true,.5);
    constants.awen=sph.kwend.awen;constants.bwen=sph.kwend.bwen;cusph::CteInteractionUp(&constants);
    Up(cells.p,std::vector<int2>{make_int2(0,0),make_int2(0,0),make_int2(0,np),make_int2(0,0)});
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,2,constants.cellcode,TDouble3(0),1,2);
    std::vector<float4> positions(cap),velocities(cap);std::vector<unsigned> ds(cap,0),id(cap);
    for(unsigned i=0;i<cap;i++){id[i]=i;if(i<np){double x=.5+(int(i%3)-1)*.25,zr=.5+(int(i/3)-1)*.25;if(jitter){if(i%2)x+=(i%3?1.:-1.)/32.;else zr+=(i%3?1.:-1.)/32.;}
      xs[i]=make_double2(x,0);zs[i]=zr;positions[i]=make_float4(float(x),0,float(zr),0);velocities[i]=make_float4(0,0,0,2048);cs[i]=CODE_TYPE_FLUID;js[i]=.98+.0075*(i%5);}}
    Up(xy.p,xs);Up(z.p,zs);Up(pos.p,positions);Up(vel.p,velocities);Up(dcell.p,ds);Up(ids.p,id);Up(code.p,cs);Up(j.p,js);
    cusph::ComputeFreeSurfaceTracking(KERNEL_Wendland,true,np,0,dvd,dcell.p,pos.p,vel.p,code.p,c.p,fstype.p,normal.p,posdiv.p,false,j.p);matrices=Down(c.p,cap);
    Need(Bits(matrices[9],initialC[9])&&Bits(matrices[10],initialC[10]),"Actual FS changed known C tail canaries");
    for(unsigned i=0;i<np;i++)Need(std::isfinite(matrices[i].a11)&&fabs(matrices[i].a11)+fabs(matrices[i].a33)>1e-10,"Actual finite-patch C is empty");
  }
  void Fields(bool jitter,std::ostream& out,std::ostream& summary,Totals& total){
    const char* names[]={"k0_compression","k0_dilation","constant","affine_balance","constant_flux","quadratic_affine_acceleration"};
    for(unsigned f=0;f<6;f++){
      const double k=f<2?0:double(float(1e-4));const double kw=constants.porewaterbulkmodulus;
      for(unsigned i=0;i<cap;i++){ths[i]=0;ps[i]=128;as[i]=make_float3(0,0,0);if(i>=np)continue;
        const double x=xs[i].x,zr=zs[i];if(f<2)ths[i]=f?1./32.:-1./32.;
        if(f==3){ps[i]=float(128+125*x+500*zr);as[i]=make_float3(-.125f,0,-.5f);}
        if(f==4)as[i]=make_float3(.125f,0,.5f);
        if(f==5){ps[i]=float(128+32*x*x+16*zr*zr);as[i]=make_float3(float(x/8),0,float(zr/16));}}
      Up(theta.p,ths);Up(p.p,ps);Up(ace.p,as);Up(rate.p,std::vector<float>(cap,Sentinel));Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
      const auto ref=Reference(np,0,sph,.75,kw,1000,k,.0625,xs,zs,cs,matrices,as,js,ths,ps);
      cusph::ComputeDynamicPorePressureRate(np,0,dvd,dcell.p,xy.p,z.p,code.p,c.p,ace.p,j.p,theta.p,p.p,rate.p,.75,kw,1000,k,1000*9.80665,.0625,invalid.p);
      const auto got=Down(rate.p,cap);const auto bad=Down(invalid.p,2);Need(bad==std::vector<unsigned>({np,0x1234abcd})&&got[9]==Sentinel&&got[10]==Sentinel,"Actual rate domain/tail contract failed");
      double pe=0,ae=0;for(unsigned i=0;i<np;i++){
        CheckRate(out,std::string(jitter?"jitter_":"regular_")+names[f],i,i,got[i],ref[i],total);total.patchrows++;
        if(f<2)Need(got[i]==float(ref[i].rate),"k0 complete rate differs from exact float formula");
        if(f==3)Need(fabs(ref[i].rate)<=ref[i].budget&&fabs(double(got[i]))<=ref[i].budget,"Affine complete-rate cancellation exceeds original propagated roundoff budget");
        if(f==2||f==4)Need(got[i]==0,"Constant p/constant Ace discrete rate must vanish");
        pe=(std::max)(pe,fabs(ref[i].pressure));ae=(std::max)(ae,fabs(ref[i].acceleration));
      }
      if(f==5)Need(pe>10*ref[0].budget&&ae>10*ref[0].budget,"Separate pressure/Ace source evidence is empty");
      Need(Same(xs,Down(xy.p,cap))&&Same(zs,Down(z.p,cap))&&Same(js,Down(j.p,cap))&&Same(ps,Down(p.p,cap))&&Same(as,Down(ace.p,cap))&&Same(ths,Down(theta.p,cap))&&Same(matrices,Down(c.p,cap)),"Rate kernel changed frozen input state");
      summary<<(jitter?"jitter":"regular")<<','<<names[f]<<",9,"<<pe<<','<<ae<<'\n';total.patchcases++;
    }
  }
};
class Fixture:public JSphGpuSingle{
  struct Physical{
    std::vector<unsigned> id;std::vector<typecode> code;std::vector<double2> xy;std::vector<double> z,j;std::vector<float4> v;
    std::vector<float> p,p0,plastic;std::vector<tsymatrix3d> sigma;
  } seed;
  Physical Capture()const{return{Down(Idpg,Np),Down(Codeg,Np),Down(Posxyg,Np),Down(Poszg,Np),Down(PoroJg,Np),Down(Velrhopg,Np),Down(PorePressg,Np),Down(PorePress0g,Np),Down(Kplasticg,Np),Down(Sigmag,Np)};}
  static bool Equal(const Physical& a,const Physical& b){return Same(a.id,b.id)&&Same(a.code,b.code)&&Same(a.xy,b.xy)&&Same(a.z,b.z)&&Same(a.j,b.j)&&Same(a.v,b.v)&&Same(a.p,b.p)&&Same(a.p0,b.p0)&&Same(a.plastic,b.plastic)&&Same(a.sigma,b.sigma);}
  void Restore(){Up(Idpg,seed.id);Up(Codeg,seed.code);Up(Posxyg,seed.xy);Up(Poszg,seed.z);Up(PoroJg,seed.j);Up(Velrhopg,seed.v);Up(PorePressg,seed.p);Up(PorePress0g,seed.p0);Up(Kplasticg,seed.plastic);Up(Sigmag,seed.sigma);}
  bool NoPre()const{return !PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg;}
  unsigned Owner(unsigned id)const{for(unsigned p=0;p<Np;p++)if(seed.id[p]==id&&CODE_IsNormal(seed.code[p])&&CODE_IsFluid(seed.code[p]))return p;throw std::runtime_error("No independent native owner");}
  void Stats(){AceMax=0.;VelMax=.125;ViscDtMax=.5f;CFLnumber=.2;DtMin=0.;DtModif=0;SymplecticDtPre=1e-12;TimeStep=0;Nstep=0;delete FixedDt;FixedDt=nullptr;}
  double M()const{return double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;}
  std::array<double,2> ScalesRef()const{
    const auto js=Down(PoroJg,Np);const auto code=Down(Codeg,Np);double maxcu=0,maxd=0;const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,k=SoilCte.HydraulicConductivity,n0=SoilCte.Porosity,rhos=(RhopZero-n0*rhow)/(1-n0);
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(code[p])&&CODE_IsFluid(code[p])){const double n=1-(1-n0)/js[p],rho=(1-n)*rhos+n*rhow;maxcu=(std::max)(maxcu,(M()+kw/n)/rho);maxd=(std::max)(maxd,kw/n*k/(rhow*9.80665));}
    return{double(KernelH)/((std::max)(sqrt(maxcu),10*VelMax)+double(KernelH)*ViscDtMax),maxd>0?double(PoreDtSafety)*KernelH*KernelH/maxd:DBL_MAX};
  }
public:
  void Initialize(const JSphCfgRun* cfg,JLog2* log){
    PorosityObserver=PorosityFeedback=DynamicPorePressure=true;AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
    SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunGpu();FreePartsInit();
    Need(CaseNfluid==512&&Np==960&&Npb==0&&!CaseNfloat&&PeriX&&PeriZ&&!PeriY&&!HydroMechDynamicSeepage&&NoPre()&&TimeStep==0&&Nstep==0,"Only fresh retained private rectangular periodic512 fixture admitted");
    Need(RhopZero==2048.f&&MassFluid==.03125f&&KernelH==float(.00703125)&&SoilCte.Porosity==.25f
      &&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==67108864.f
      &&SoilCte.ModulusK==89478488.f&&SoilCte.ModulusG==134217728.f
      &&MapRealSize.x==.125&&MapRealSize.z==.0625,"Frozen manufactured CPU material/geometry changed");
    seed=Capture();unsigned count=0;for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(seed.code[p]))count++;Need(count==512,"Native owner count changed");
  }
  void Periodic(const fs::path& out,Totals& total){
    std::ofstream rows(out/"periodic_rates.csv"),summary(out/"periodic_summary.csv");
    rows<<std::setprecision(17)<<"field,slot,id,actual,reference,error,budget,error_over_budget,pressure_source,acceleration_source\n";
    summary<<std::setprecision(17)<<"field,slots,ghosts,corners,min_owner_C_norm,pre_rate_sentinel_preserved\n";
    for(unsigned f=0;f<2;f++){
      Restore();SoilCte.HydraulicConductivity=f?1e-4f:0;ConstantDataUp();Up(PorePressRateg,std::vector<float>(Np,Sentinel));PreInteraction_Forces();
      Need(Down(PorePressRateg,Np)==std::vector<float>(Np,Sentinel),"Dynamic Pre unexpectedly cleared old rate sentinel");ComputeFreeSurfaceTracking();
      auto c=Down(CorrMatg,Np);auto js=seed.j;std::vector<float3> a(Np);std::vector<double> th(Np);std::vector<float> p(Np);
      unsigned ghosts=0,corners=0;double minC=DBL_MAX;
      for(unsigned i=0;i<Np;i++){
        const unsigned owner=Owner(seed.id[i]);const double x=seed.xy[owner].x,z=seed.z[owner];
        js[i]=1.+.002*(seed.id[i]%4);p[i]=f?float(128+32*cos(2*acos(-1.)*x/MapRealSize.x)):128.f;
        a[i]=make_float3(float(x/8.),0,float(z/16.));th[i]=-1./32.;
        // Nonzero positive-k compression is bounded and keyed by the native material ID.
        if(f)th[i]=double(int(seed.id[i]%3)-1)/1024.;
        if(CODE_IsPeriodic(seed.code[i])){
          c[i]=TMatrix3d(NAN);a[i]=make_float3(NAN,NAN,NAN);th[i]=NAN;ghosts++;
          if(fabs(seed.xy[i].x-seed.xy[owner].x)>1e-12&&fabs(seed.z[i]-seed.z[owner])>1e-12)corners++;
        }
      }
      Up(PoroJg,js); // C must use the same J as the rate.
      ComputeFreeSurfaceTracking();c=Down(CorrMatg,Np);
      for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(seed.code[i]))c[i]=TMatrix3d(NAN);Up(CorrMatg,c);
      unsigned* map=PrepareDynamicPorePeriodicGpu();Need(map!=nullptr,"Periodic map absent");c=Down(CorrMatg,Np);
      for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(seed.code[i])){
        const unsigned o=Owner(seed.id[i]);const double norm=fabs(c[o].a11)+fabs(c[o].a33);Need(norm>1e-12&&std::isfinite(norm)&&Bits(c[i],c[o]),"Actual host C owner repair is empty or inexact");minC=(std::min)(minC,norm);
      }
      auto expectedA=a;auto expectedTheta=th;
      for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(seed.code[i])){const unsigned o=Owner(seed.id[i]);expectedA[i]=a[o];expectedTheta[i]=th[o];}
      Up(Aceg,a);Up(PoroThetag,th);Up(PorePressg,p);Up(PorePressRateg,std::vector<float>(Np,Sentinel));
      const auto before=Capture();const auto ref=Reference(Np,Npb,CSP,1.-double(SoilCte.Porosity),SoilCte.PoreWaterBulkModulus,SoilCte.PoreWaterRho,SoilCte.HydraulicConductivity,double(MassFluid)/RhopZero,seed.xy,seed.z,seed.code,c,expectedA,js,expectedTheta,p);
      ComputeDynamicPorePressureRateGpu(map);map=nullptr;const auto got=Down(PorePressRateg,Np);const auto gotA=Down(Aceg,Np);const auto gotT=Down(PoroThetag,Np);
      for(unsigned i=0;i<Np;i++){
        const unsigned o=CODE_IsPeriodic(seed.code[i])?Owner(seed.id[i]):i;
        CheckRate(rows,f?"positive_k":"k0",i,seed.id[i],got[i],ref[o],total);total.periodicrows++;
        if(CODE_IsPeriodic(seed.code[i]))Need(Bits(got[i],got[o])&&Bits(gotA[i],gotA[o])&&Bits(gotT[i],gotT[o]),"Actual host Ace/theta/rate owner copy is not bit exact");
      }
      Need(ghosts>0&&corners>0&&Equal(before,Capture()),"Periodic owner test is empty or physical inputs changed");
      total.corners+=corners;summary<<f<<','<<Np<<','<<ghosts<<','<<corners<<','<<minC<<",true\n";PosInteraction_Forces();total.periodiccases++;
    }
    Restore();auto badCode=seed.code;unsigned ghost=0;while(ghost<Np&&!CODE_IsPeriodic(seed.code[ghost]))ghost++;Need(ghost<Np,"Missing-owner negative empty");badCode[Owner(seed.id[ghost])]=CODE_SetOutIgnore(CODE_TYPE_FLUID);Up(Codeg,badCode);
    const unsigned used=ArraysGpu->GetArrayCountUsed(JArraysGpu::SIZE_4B);bool caught=false;
    try{unsigned* map=PrepareDynamicPorePeriodicGpu();if(map)ArraysGpu->Free(map);}catch(const std::exception& e){caught=std::string(e.what()).find("no valid normal-fluid native owner")!=std::string::npos;}
    Need(caught&&used==ArraysGpu->GetArrayCountUsed(JArraysGpu::SIZE_4B),"Actual host missing-owner error did not release map/flag");Restore();
    std::ofstream negative(out/"host_owner_negative.csv");negative<<"case,rejected,map_flag_pool_released\nmissing_native,true,true\n";total.ownernegative++;
    rows.flush();summary.flush();negative.flush();Need(bool(rows)&&bool(summary)&&bool(negative),"Periodic diagnostic output failed");
  }
  void Time(const fs::path& out,Totals& total){
    std::ofstream scales(out/"scales.csv"),requests(out/"requests.csv");scales<<std::setprecision(17);requests<<std::setprecision(17);
    scales<<"case,J,k,wave,pore,wave_independent,pore_independent,rejected\n";
    const double jvals[]={1.,1.02,1.,1.01,1.02};const float kvals[]={0,0,1e-4f,1e-4f,1e-4f};
    for(unsigned f=0;f<5;f++){
      Restore();Stats();SoilCte.HydraulicConductivity=kvals[f];Up(PoroJg,std::vector<double>(Np,jvals[f]));double w=0,p=0;bool caught=false;
      try{GetDynamicStepScalesGpu(w,p);}catch(const std::exception& e){caught=std::string(e.what()).find("strict positive-k continuous decay domain")!=std::string::npos;}
      if(f==4){Need(caught,"Positive-k J1.02 must fail strict decay domain");total.domain++;scales<<f<<','<<jvals[f]<<','<<kvals[f]<<",0,0,0,0,true\n";continue;}
      const auto ref=ScalesRef();Need(!caught&&NearScale(w,ref[0])&&((p==DBL_MAX&&ref[1]==DBL_MAX)||NearScale(p,ref[1])),"Actual current-J wave/diffusion differs from independent closure");if(!kvals[f])Need(p==DBL_MAX&&Bits(w,GetPorosityStepWaveGpu()),"k0 acoustic compatibility changed");
      scales<<f<<','<<jvals[f]<<','<<kvals[f]<<','<<w<<','<<p<<','<<ref[0]<<','<<ref[1]<<",false\n";total.scales++;
    }
    requests<<"case,bound,independent_bound,current,fixed,DtMin,rejected,expected_reject,selected,signed_fixed_error,physical_unchanged\n";
    const char* names[]={"variable","safe_fixed","fixed_bound","current_bound","current_nextafter","fixed_nextafter","DtMin_nextafter","DtMin_above_fixed","force_dominated","velocity_dominated","current_zero","current_nan"};
    for(unsigned f=0;f<12;f++){
      Restore();Stats();SoilCte.HydraulicConductivity=1e-4f;if(f==8)AceMax=1e12;if(f==9)VelMax=1024.;
      double w=0,p=0;GetDynamicStepScalesGpu(w,p);const double b=(std::min)(CFLnumber*(std::min)(AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,w),p);const auto ref=ScalesRef();const double rb=(std::min)(CFLnumber*(std::min)(AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX,ref[0]),ref[1]);Need(NearScale(b,rb),"Combined dynamic bound differs");
      if(!f)Need(p<CFLnumber*w,"Positive-k diffusion-bound test is vacuous");SymplecticDtPre=b*.25;double expected=b;bool reject=false;
      if(f==1){FixedDt=new JDsFixedDt(b*.75);DtMin=b*.5;expected=b*.75;}if(f==2)FixedDt=new JDsFixedDt(b);if(f==3)SymplecticDtPre=b;
      if(f==4){SymplecticDtPre=std::nextafter(b,DBL_MAX);reject=true;}if(f==5){FixedDt=new JDsFixedDt(std::nextafter(b,DBL_MAX));reject=true;}
      if(f==6){DtMin=std::nextafter(b,DBL_MAX);reject=true;}if(f==7){FixedDt=new JDsFixedDt(b*.5);DtMin=b*.75;reject=true;}
      if(f==10){SymplecticDtPre=0;reject=true;}if(f==11){SymplecticDtPre=NAN;reject=true;}
      const double current=SymplecticDtPre,fixed=FixedDt?FixedDt->GetFixedValue():0;const auto before=Capture();double selected=0;bool caught=false;
      try{selected=DtVariable(false);}catch(const std::exception& e){caught=std::string(e.what()).find("GPU porosity")!=std::string::npos;}
      Need(caught==reject&&Equal(before,Capture())&&NoPre()&&DtModif==0,"Actual dynamic current/request guard or immutability failed");
      if(!caught)Need(Bits(selected,expected),"Safe dynamic step was clipped or uplifted");const double err=FixedDt?FixedDt->GetDtError(false):0;if(FixedDt)Need(Bits(err,fixed-b),"FixedDt did not receive complete dynamic bound");
      requests<<names[f]<<','<<b<<','<<rb<<','<<current<<','<<fixed<<','<<DtMin<<','<<caught<<','<<reject<<','<<selected<<','<<err<<",true\n";total.requests++;
    }
    Restore();Stats();Need(NoPre()&&TimeStep==0&&Nstep==0,"Time component advanced state");
    scales.flush();requests.flush();Need(bool(scales)&&bool(requests),"Scale/request diagnostic output failed");
  }
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Initialize(cfg,log);const fs::path out(cfg->DirOut);Totals total;PrefixOwners(out,total);Periodic(out,total);Time(out,total);
    std::ofstream rates(out/"patch_rates.csv"),summary(out/"patch_summary.csv");rates<<std::setprecision(17);summary<<std::setprecision(17);
    rates<<"field,slot,id,actual,reference,error,budget,error_over_budget,pressure_source,acceleration_source\n";summary<<"geometry,field,rows,max_pressure_source,max_acceleration_source\n";
    {Patch patch(false);patch.Fields(false,rates,summary,total);}{Patch patch(true);patch.Fields(true,rates,summary,total);}
    rates.flush();summary.flush();Need(bool(rates)&&bool(summary),"Patch diagnostics incomplete");
    int device=0;Cu(cudaGetDevice(&device));cudaDeviceProp props{};Cu(cudaGetDeviceProperties(&props,device));
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gpu_darcy_component_r1\",\"prefix_stage_cases\":"<<total.prefix<<",\"owner_negative_cases\":"<<total.ownernegative
      <<",\"finite_patch_cases\":"<<total.patchcases<<",\"finite_patch_rate_rows\":"<<total.patchrows<<",\"actual_host_periodic_cases\":"<<total.periodiccases<<",\"actual_host_periodic_rate_rows\":"<<total.periodicrows<<",\"corner_clone_witnesses\":"<<total.corners
      <<",\"class_scale_cases\":"<<total.scales<<",\"positive_k_domain_rejections\":"<<total.domain<<",\"actual_DtVariable_cases\":"<<total.requests<<",\"max_rate_reference_error_pa_s\":"<<total.maxerror<<",\"max_error_over_budget\":"<<total.ratio
      <<",\"actual_private_rate_kernel\":true,\"actual_host_owner_and_rate_helpers\":true,\"independent_all_particle_reference\":true,\"kernel_float_factor_budget_predeclared\":true,\"full_rate_overwrite\":true,\"actual_LoadConfig_ConfigDomain_InitRunGpu\":true,\"actual_ComputeStep_Sym_called\":false,\"completed_physical_steps\":0,\"public_GPU_dynamic_mode\":false,\"variable_k_tested\":false,\"physical_acceptance\":false,\"device_name\":\""<<props.name<<"\"}\n";
    done.flush();Need(bool(done),"Completion output failed");
  }
};
}
int main(int argc,char** argv){
  try{
    Need(argc>=6&&std::string(argv[1])=="--darcy","Use --darcy followed by ordinary -gpu arguments and a fresh output");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(!cfg.Cpu&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut),"Only fresh GPU component arguments admitted");
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    gd::Fixture fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU Darcy component rejected; retain all evidence\n";return 2;}
}

