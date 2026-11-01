// Private GPU opposing-wall components, not a physical trajectory or Run admission.
#define main RetainedGpuK0TimeMain
#include "upl_gpu_k0_time_r1.cpp"
#undef main
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include "JArraysGpu.h"
#include <array>
#include <vector_functions.h>

namespace gw {
constexpr unsigned Fluid=1024,Fixed=256,Total=Fluid+Fixed;
constexpr double Dp=1./512.,Width=1./16.,Lz=1./16.,FullLx=1./8.,Amplitude=1./512.,Ck=1./8192.;
constexpr float Sentinel=1234567.f;
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double Norm(tdouble3 a){return sqrt(Dot(a,a));}
static tdouble3 Product(const tmatrix3d& m,tdouble3 v){return TDouble3(m.a11*v.x+m.a12*v.y+m.a13*v.z,m.a21*v.x+m.a22*v.y+m.a23*v.z,m.a31*v.x+m.a32*v.y+m.a33*v.z);}
static tdouble3 Vec(float3 v){return TDouble3(v.x,v.y,v.z);}
template<class T>static std::vector<T> Optional(const T* p,unsigned n){return p?Down(p,n):std::vector<T>();}
template<class T>static void Restore(T* p,const std::vector<T>& v){if(!v.empty())Up(p,v);}
static double WrapZ(double z){while(z<0)z+=Lz;while(z>=Lz)z-=Lz;return z;}
static double Inf(const tmatrix3d& a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});}
struct View{
  std::vector<unsigned> id,cell,fs;std::vector<typecode> code;
  std::vector<double2> xy;std::vector<double> z,j,theta;std::vector<float4> vel;
  std::vector<float> p,p0,rate,plastic,posdiv;std::vector<tsymatrix3d> sigma;
  std::vector<tmatrix3d> c;std::vector<float3> ace,derivative,tangent,normal,fsnormal,load;std::vector<byte> mode;
};
struct Fit{double condition,bare,nearest,distance;};
struct Ref{double value,budget,pressure,acceleration,chain;unsigned wall,wallperiodic;};
struct Counts{
  unsigned affine=0,affinerows=0,quadratic=0,ratecases=0,raterows=0,counterfactual=0,ownernegative=0,audits=0,rollbacks=0;
  unsigned periodicfluid=0,periodicwall=0,ownerperm=0;
  double maxrateerror=0,maxrateratio=0,maxforce=0,maxqn=0,maxvn=0,maxbadzero=0,maxbadcopy=0;
};
class WallFixture:public JSphGpuSingle{
  View seed;Counts counts;
  View Read()const{
    View v;v.id=Down(Idpg,Np);v.cell=Down(Dcellg,Np);v.code=Down(Codeg,Np);v.xy=Down(Posxyg,Np);v.z=Down(Poszg,Np);
    v.j=Down(PoroJg,Np);v.theta=Down(PoroThetag,Np);v.vel=Down(Velrhopg,Np);v.p=Down(PorePressg,Np);v.p0=Down(PorePress0g,Np);v.rate=Down(PorePressRateg,Np);
    v.plastic=Down(Kplasticg,Np);v.sigma=Down(Sigmag,Np);v.c=Down(CorrMatg,Np);v.fs=Down(FSTypeg,Np);v.posdiv=Down(PosDivg,Np);
    v.normal=Down(BoundNormalg,Np);v.mode=Down(BoundModeg,Np);v.tangent=Down(TangenVelg,Np);v.fsnormal=Down(FSNormalg,Np);v.load=Down(HydroMechLoadAceg,Np);
    v.ace=Optional(Aceg,Np);v.derivative=Optional(BoundDerivativeVelg,Np);return v;
  }
  void Put(const View& v,bool scratch=false){
    Up(PoroJg,v.j);Up(PoroThetag,v.theta);Up(Velrhopg,v.vel);Up(PorePressg,v.p);Up(PorePress0g,v.p0);Up(PorePressRateg,v.rate);
    Up(Kplasticg,v.plastic);Up(Sigmag,v.sigma);Up(CorrMatg,v.c);Up(FSTypeg,v.fs);Up(PosDivg,v.posdiv);
    Up(BoundNormalg,v.normal);Up(BoundModeg,v.mode);Up(TangenVelg,v.tangent);Up(FSNormalg,v.fsnormal);Up(HydroMechLoadAceg,v.load);
    if(scratch){Restore(Aceg,v.ace);Restore(BoundDerivativeVelg,v.derivative);}
  }
  std::vector<unsigned> Map(const View& v)const{
    std::vector<unsigned> m(Total,UINT_MAX);unsigned fluid=0,wall=0,pf=0,pw=0;
    for(unsigned p=0;p<Np;p++){
      Need(v.id[p]<Total&&(CODE_IsNormal(v.code[p])||CODE_IsPeriodic(v.code[p])),"Unknown/excluded wall component identity");
      const bool f=CODE_IsFluid(v.code[p]);Need(f==(v.id[p]>=Fixed),"Native ID fluid/fixed partition changed");
      Need(f||CODE_IsFixed(v.code[p]),"Nonfixed boundary outside scope");
      if(CODE_IsNormal(v.code[p])){Need(m[v.id[p]]==UINT_MAX,"Duplicate normal owner");m[v.id[p]]=p;f?fluid++:wall++;}
      else f?pf++:pw++;
    }
    Need(fluid==Fluid&&wall==Fixed&&pf>0&&pw>0&&Npb>=Fixed&&NpbOk>=Fixed&&Npb>0,"True fixed prefix/periodic ownership is empty");
    Need(CellDivSingle->GetNpfOut()==0&&CellDivSingle->GetNpbOut()==0,"Actual cell division excluded particles");return m;
  }
  using Row=std::array<double,26>;
  std::vector<Row> NativeRows(const View& v)const{
    const auto m=Map(v);std::vector<Row> out;out.reserve(Fluid);
    for(unsigned id=Fixed;id<Total;id++){
      const unsigned p=m[id];const auto x=v.xy[p];const auto s=v.sigma[p];const auto n=v.fsnormal[p];const auto l=v.load[p];const auto u=v.vel[p];
      out.push_back({x.x,x.y,v.z[p],u.x,u.y,u.z,v.p[p],v.p0[p],v.j[p],v.theta[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,v.plastic[p],double(v.fs[p]),n.x,n.y,n.z,v.posdiv[p],l.x,l.y,l.z,u.w});
    }return out;
  }
  bool Immutable(const View& v)const{return Same(v.id,Down(Idpg,Np))&&Same(v.cell,Down(Dcellg,Np))&&Same(v.code,Down(Codeg,Np))&&Same(v.xy,Down(Posxyg,Np))&&Same(v.z,Down(Poszg,Np));}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPreg&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg,"Component advanced time or left predictor state");}
  double Volume(double j)const{return double(MassFluid)/double(RhopZero)*j;}
  double Rho(double j)const{return double(SoilCte.PoreWaterRho)+(double(RhopZero)-double(SoilCte.PoreWaterRho))/j;}
  double Law(double j,bool on)const{return !on||j==1.?double(SoilCte.HydraulicConductivity):double(SoilCte.HydraulicConductivity)*exp((j-1.)/((1.-double(SoilCte.Porosity))*Ck));}
  Fit FitPressure(const View& v,tdouble3 target)const{
    target.z=WrapZ(target.z);tmatrix3d raw=TMatrix3d(0),scaled=TMatrix3d(0);tdouble3 rhs=TDouble3(0);double nearest=0,distance=DBL_MAX;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(v.code[p])){
      const auto d=TDouble3(target.x-v.xy[p].x,0,target.z-v.z[p]);const float rr=float(Dot(d,d));if(rr>KernelSize2)continue;
      float fac=0;const double wab=rr==0?double(fsph::GetKernel_Wab<KERNEL_Wendland>(CSP,rr)):double(fsph::GetKernel_WabFac<KERNEL_Wendland>(CSP,rr,fac));
      const double vol=Volume(v.j[p]),w=vol*wab,fx=vol*double(fac)*d.x,fz=vol*double(fac)*d.z;
      raw.a11+=w;raw.a12+=d.x*w;raw.a13+=d.z*w;raw.a21+=fx;raw.a22+=d.x*fx;raw.a23+=d.z*fx;raw.a31+=fz;raw.a32+=d.x*fz;raw.a33+=d.z*fz;
      rhs=rhs+TDouble3(w,fx,fz)*double(v.p[p]);const double x=-d.x/KernelH,z=-d.z/KernelH;
      scaled.a11+=w;scaled.a12+=w*x;scaled.a13+=w*z;scaled.a21+=w*x;scaled.a22+=w*x*x;scaled.a23+=w*x*z;scaled.a31+=w*z;scaled.a32+=w*x*z;scaled.a33+=w*z*z;
      if(Dot(d,d)<distance){distance=Dot(d,d);nearest=v.p[p];}
    }
    const double det=fmath::Determinant3x3(raw),sd=fmath::Determinant3x3(scaled);Need(fabs(det)>=1e-3&&sd>0&&distance<DBL_MAX,"Independent wall fit unsupported");
    const auto inv=fmath::InverseMatrix3x3(raw,det),si=fmath::InverseMatrix3x3(scaled,sd);
    return {(std::max)(1.,Inf(scaled)*Inf(si)),inv.a11*rhs.x+inv.a12*rhs.y+inv.a13*rhs.z,nearest,sqrt(distance)};
  }
  void Initialize(const JSphCfgRun* cfg,JLog2* log){
    PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunGpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TStep==STEP_Symplectic&&CaseNfluid==Fluid&&CaseNpb==Fixed&&CaseNp==Total&&!CaseNfloat&&!CaseNmoving,"Only real1024soil+256fixed initialization admitted");
    Need(TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&!PeriX&&!PeriY&&PeriZ&&PeriZinc.x==0&&PeriZinc.y==0,"Only opposite FreeSlip walls/tangent Z periodicity admitted");
    Need(Dp==gw::Dp&&KernelH==float(1.8*gw::Dp)&&SoilCte.ModulusK==89478488.f&&SoilCte.ModulusG==134217728.f&&SoilCte.PoreWaterBulkModulus==67108864.f&&SoilCte.Porosity==.25f&&RhopZero==2048&&SoilCte.PoreWaterRho==1000.f&&SoilCte.HydraulicConductivity==float(.0001),"Frozen wall material changed");
    Need(Volume(1)==gw::Dp*gw::Dp&&Gravity.x==0&&Gravity.y==0&&Gravity.z==0&&BoundNormalg&&BoundModeg&&TangenVelg,"Wall volume/geometry arrays unavailable");
    seed=Read();const auto m=Map(seed);unsigned left=0,right=0;
    for(unsigned id=0;id<Total;id++){const unsigned p=m[id];Need(seed.xy[p].y==0&&seed.j[p]==1.&&seed.theta[p]==0.,"Fresh J/theta/2D identity changed");
      if(id<Fixed){const double plane=seed.xy[p].x+.5*seed.normal[p].x;Need(seed.normal[p].y==0&&seed.normal[p].z==0&&((seed.normal[p].x>0&&plane==0)||(seed.normal[p].x<0&&plane==Width)),"Wrong true wall plane");seed.normal[p].x>0?left++:right++;}
      else Need(seed.xy[p].x>0&&seed.xy[p].x<Width&&seed.z[p]>0&&seed.z[p]<Lz,"Native soil outside declared slab");
    }Need(left==128&&right==128,"Missing opposing fixed face");
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(seed.code[p]))CODE_IsFluid(seed.code[p])?counts.periodicfluid++:counts.periodicwall++;
    NoStep();
  }

  void Affine(const fs::path& out,bool offgrid){
    Put(seed);InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Cu(cudaMemset(Aceg,0,sizeof(float3)*Np));Cu(cudaMemset(BoundDerivativeVelg,0,sizeof(float3)*Np));auto v=Read();const auto original=v;
    if(offgrid)for(unsigned p=0;p<Npb;p++)v.normal[p].x+=float((v.normal[p].x>0?1.:-1.)*gw::Dp/8.);
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(v.code[p])){
      const double x=v.xy[p].x;v.vel[p]=make_float4(float(.125+.5*x),0,float(-.25+.125*x),RhopZero);v.j[p]=1.+x/1024.;v.theta[p]=0;
      v.p[p]=float(128.+256*x);v.p0[p]=0;v.sigma[p]={16.+x,0,8.+32*x,32.+2*x,0,64.+4*x};v.plastic[p]=0;
      v.ace[p]=make_float3(float(.25+.5*x),0,float(-.125+.25*x));v.c[p]={1.+x,0,.125+.5*x,0,0,0,.125+.5*x,0,2.+x};
    }
    Put(v,true);const auto before=NativeRows(v);ComputeDynamicPoreWallStateGpu();ComputeDynamicPoreWallMatrixGpu();ComputeDynamicPoreWallAccelerationGpu();Cu(cudaDeviceSynchronize());
    const auto got=Read();Need(Same(before,NativeRows(got))&&Immutable(v),"Explicit wall helpers changed native fields or geometry");const auto m=Map(got);
    std::ofstream csv(out/(offgrid?"offgrid_affine.csv":"affine.csv"));csv<<std::setprecision(17)<<"id,target_x,J_error,p_error,v_error,sigma_error,C_error,ace_error,condition,double_base_tol,float_base_tol,nearest_distance_m,wrong_copy_C_error,wrong_copy_Ace_error\n";
    unsigned nonempty=0,offset=0;for(unsigned id=0;id<Fixed;id++){
      const unsigned p=m[id];const double x=got.xy[p].x+got.normal[p].x;const auto fit=FitPressure(v,TDouble3(x,0,got.z[p]));
      const float3 vm=make_float3(float(-(.125+.5*x)),0,float(-.25+.125*x)),am=make_float3(float(-(.25+.5*x)),0,float(-.125+.25*x));
      const tsymatrix3d sr={16.+x,0,-(8.+32*x),32.+2*x,0,64.+4*x};
      const tmatrix3d cr={1.+x,0,-(.125+.5*x),0,0,0,-(.125+.5*x),0,2.+x};const auto s=got.sigma[p];const auto c=got.c[p];
      const double ej=fabs(got.j[p]-(1.+x/1024.)),ep=fabs(got.p[p]-float(128.+256*x)),ev=Norm(Vec(got.derivative[p])-Vec(vm)),ea=Norm(Vec(got.ace[p])-Vec(am));
      const double es=(std::max)({fabs(s.xx-sr.xx),fabs(s.xy-sr.xy),fabs(s.xz-sr.xz),fabs(s.yy-sr.yy),fabs(s.yz-sr.yz),fabs(s.zz-sr.zz)});
      const double ec=(std::max)({fabs(c.a11-cr.a11),fabs(c.a12-cr.a12),fabs(c.a13-cr.a13),fabs(c.a21-cr.a21),fabs(c.a22-cr.a22),fabs(c.a23-cr.a23),fabs(c.a31-cr.a31),fabs(c.a32-cr.a32),fabs(c.a33-cr.a33)});
      const double td=32768.*DBL_EPSILON*fit.condition,tf=64.*FLT_EPSILON*fit.condition;
      Need(ej<=2*td&&ep<=256*tf&&ev<=tf&&ea<=tf&&es<=128*td&&ec<=4*td,"Original affine wall component budget failed");
      Need(got.vel[p].x==0&&got.vel[p].y==0&&got.vel[p].z==0&&got.vel[p].w==RhopZero&&got.mode[p]==BMODE_MDBC2,"Physical fixed velocity/mDBC mode changed");
      Need(got.tangent[p].x==0&&fabs(got.tangent[p].z-vm.z)<=tf,"Separate tangent wall velocity incorrect");
      const double wrongc=fabs((.125+.5*x)-cr.a13),wronga=fabs(float(.25+.5*x)-am.x);
      Need(wrongc>4*td&&wronga>tf,"C/Ace reflection negative witnesses empty");nonempty++;
      if(offgrid){Need(fit.distance==gw::Dp/8.,"Dp/8 noncoincident target was not exercised");offset++;}
      else Need(fit.distance==0.,"Declared same-node target lacks a coincident native fluid sample");
      csv<<id<<','<<x<<','<<ej<<','<<ep<<','<<ev<<','<<es<<','<<ec<<','<<ea<<','<<fit.condition<<','<<td<<','<<tf<<','<<fit.distance<<','<<wrongc<<','<<wronga<<'\n';counts.affinerows++;
    }
    Need(nonempty==Fixed&&(!offgrid||offset==Fixed),"Affine reflection/anchor witnesses empty");
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(got.code[p])&&CODE_IsFixed(got.code[p])){
      const unsigned q=m[got.id[p]];Need(Bits(got.j[p],got.j[q])&&Bits(got.p[p],got.p[q])&&Bits(got.sigma[p],got.sigma[q])&&Bits(got.c[p],got.c[q])&&Bits(got.ace[p],got.ace[q])&&Bits(got.derivative[p],got.derivative[q]),"Tangent wall clone reconstruction differs from its native owner");
    }
    // A separate pressure-only nonlinear coincident witness discriminates anchoring from bare MLS.
    if(!offgrid){
      for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(v.code[p]))v.p[p]=float(128.+32768.*v.xy[p].x*v.xy[p].x);
      Put(v,true);const auto native=NativeRows(v);ComputeDynamicPoreWallStateGpu();const auto nonlinear=Read();
      Need(Same(native,NativeRows(nonlinear))&&Immutable(v),"Nonlinear State component changed native state/geometry");
      std::ofstream qcsv(out/"coincident_pressure_anchor.csv");qcsv<<std::setprecision(17)<<"id,target_x,nearest_distance_m,actual_pressure,nearest_native_float,bits_exact,bare_intercept_counterfactual,bare_error,original_float_pressure_budget,bare_error_over_budget,bare_float_write,bare_float_bits_differ\n";
      unsigned barewrong=0,barefloatwrong=0;for(unsigned id=0;id<Fixed;id++){
        const unsigned p=m[id];const double x=nonlinear.xy[p].x+nonlinear.normal[p].x;const auto fit=FitPressure(v,TDouble3(x,0,nonlinear.z[p]));const float nearest=float(fit.nearest);
        Need(fit.distance==0.&&Bits(nonlinear.p[p],nearest),"Coincident pressure did not preserve the actual nearest float bits");
        const double error=fabs(fit.bare-fit.nearest),budget=64.*FLT_EPSILON*fit.condition*256.;if(error>0)barewrong++;
        const float barefloat=float(fit.bare);const bool floatdifferent=!Bits(barefloat,nearest);barefloatwrong+=unsigned(floatdifferent);
        qcsv<<id<<','<<x<<','<<fit.distance<<','<<nonlinear.p[p]<<','<<nearest<<",true,"<<fit.bare<<','<<error<<','<<budget<<','<<error/budget<<','<<barefloat<<','<<floatdifferent<<'\n';counts.quadratic++;
      }Need(barewrong>0&&barefloatwrong>0,"Bare-intercept nonlinear float-write counterfactual is empty");qcsv.flush();Need(bool(qcsv),"Coincident anchor CSV write failed");
    }
    Put(original,true);Need(Same(original.normal,Down(BoundNormalg,Np))&&Immutable(original),"All-slot normal/geometry restoration failed");
    NoStep();PosInteraction_Forces();Put(seed);csv.flush();Need(bool(csv),"Affine CSV write failed");counts.affine++;
  }
  std::vector<Ref> Reference(const View& v,bool law)const{
    std::vector<Ref> r(Np);const double kw=SoilCte.PoreWaterBulkModulus,rhow=SoilCte.PoreWaterRho,gamma=rhow*9.80665,alpha=1./((1.-double(SoilCte.Porosity))*Ck);
    for(unsigned i=Npb;i<Np;i++)if(CODE_IsNormal(v.code[i])&&CODE_IsFluid(v.code[i])){
      double lp=0,da=0,alp=0,ada=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gj=TDouble3(0),alx=TDouble3(0),agp=TDouble3(0),agj=TDouble3(0);unsigned wall=0,wp=0;
      for(unsigned b=0;b<Np;b++)if(CODE_IsFluid(v.code[b])||(CODE_IsFixed(v.code[b])&&v.mode[b]!=BMODE_MDBC2OFF)){
        const auto d=TDouble3(v.xy[i].x-v.xy[b].x,0,v.z[i]-v.z[b]);const double rr=Dot(d,d);if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;
        const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr))),gi=Product(v.c[i],g),gb=Product(v.c[b],g);
        const double vol=Volume(v.j[b]),dp=double(v.p[i])-v.p[b],w=vol*Dot(d,gi+gb)/(rr+double(CSP.eta2));
        lp+=w*dp;alp+=fabs(w*dp);lx=lx+d*w;gp=gp-gi*(vol*dp);gj=gj+gi*(vol*(v.j[b]-v.j[i]));
        alx.x+=fabs(d.x*w);alx.z+=fabs(d.z*w);agp.x+=fabs(gi.x*vol*dp);agp.z+=fabs(gi.z*vol*dp);agj.x+=fabs(gi.x*vol*(v.j[b]-v.j[i]));agj.z+=fabs(gi.z*vol*(v.j[b]-v.j[i]));
        const auto a=Vec(v.ace[b])-Vec(v.ace[i]);da+=vol*Dot(a,gi);ada+=vol*(fabs(a.x*gi.x)+fabs(a.z*gi.z));
        if(CODE_IsFixed(v.code[b])){wall++;if(CODE_IsPeriodic(v.code[b]))wp++;}
      }
      const double n=1.-(1.-double(SoilCte.Porosity))/v.j[i],B=kw/n,ki=Law(v.j[i],law),scale=law?alpha*ki:0.;
      const double chain=scale*Dot(gj,gp+Vec(v.ace[i])*rhow),raw=B*(fabs(v.theta[i])+ki/gamma*(alp+Dot(agp,alx)+rhow*ada)+fabs(scale)/gamma*Dot(agj,TDouble3(agp.x+rhow*fabs(v.ace[i].x),0,agp.z+rhow*fabs(v.ace[i].z))));
      r[i]={B*(-v.theta[i]+ki/gamma*(lp-Dot(gp,lx)+rhow*da)+chain/gamma),64.*FLT_EPSILON*raw+256.*DBL_EPSILON*(std::max)(1.,fabs(B*v.theta[i]))+1e-6,B*ki/gamma*(lp-Dot(gp,lx)),B*ki/gamma*rhow*da,B/gamma*chain,wall,wp};
    }return r;
  }
  void CheckRates(std::ostream& csv,const char* name,const View& v,bool law){
    const auto ref=Reference(v,law);unsigned rows=0,wallrows=0,clonewallrows=0;
    for(unsigned i=0;i<Np;i++){
      if(i<Npb)Need(v.rate[i]==Sentinel,"Complete rate overwrote its real fixed prefix");
      if(CODE_IsNormal(v.code[i])&&CODE_IsFluid(v.code[i])){
        const auto r=ref[i];const double error=fabs(double(v.rate[i])-r.value);Need(std::isfinite(v.rate[i])&&v.rate[i]!=Sentinel&&error<=r.budget,"Actual wall-neighbor rate exceeded original propagated budget");
        counts.maxrateerror=(std::max)(counts.maxrateerror,error);counts.maxrateratio=(std::max)(counts.maxrateratio,error/r.budget);
        csv<<name<<','<<i<<','<<v.id[i]<<','<<v.rate[i]<<','<<r.value<<','<<error<<','<<r.budget<<','<<error/r.budget<<','<<r.pressure<<','<<r.acceleration<<','<<r.chain<<','<<r.wall<<','<<r.wallperiodic<<'\n';
        rows++;wallrows+=unsigned(r.wall>0);clonewallrows+=unsigned(r.wallperiodic>0);counts.raterows++;
      }
    }Need(rows==Fluid&&wallrows>0&&clonewallrows>0,"True fixed/periodic-wall neighbor rate reference is empty");counts.ratecases++;
  }

  void RateComponents(const fs::path& out){
    Put(seed);InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Cu(cudaMemset(Aceg,0,sizeof(float3)*Np));Cu(cudaMemset(BoundDerivativeVelg,0,sizeof(float3)*Np));
    std::ofstream csv(out/"rates.csv"),owners(out/"owners.csv"),negative(out/"negative_rates.csv");
    csv<<std::setprecision(17)<<"case,slot,id,actual,reference,error,budget,error_over_budget,pressure_source,acceleration_source,chain_reference,wall_neighbors,periodic_wall_neighbors\n";
    owners<<"case,np,npb,npbok,normal_soil,normal_fixed,fluid_periodic,wall_periodic,permuted_owner_slots,all_C_Ace_theta_rate_owners_exact\n";
    negative<<std::setprecision(17)<<"case,native_changed,max_rate_change_Pa_s,max_change_over_combined_original_budget,max_bad_actual_reference_error_Pa_s\n";
    for(unsigned law=0;law<2;law++){
      Put(seed);auto v=Read();const double kx=2*acos(-1.)/FullLx,kz=2*acos(-1.)/Lz;
      for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(v.code[p])){
        const double x=v.xy[p].x,z=WrapZ(v.z[p]);v.j[p]=1.+x/1024.+sin(kz*z)/65536.;v.theta[p]=.03125+x/16.;
        v.p[p]=float(64*cos(kx*x)+16*cos(kz*z));v.vel[p]=make_float4(float(Amplitude*sin(kx*x)),0,0,RhopZero);
        v.sigma[p]={};v.ace[p]=make_float3(float(.25+.5*x+.125*sin(kz*z)),0,float(.125*cos(kz*z)+.25*x));
      }
      Put(v,true);DynamicPoreConductivity=(law!=0);DynamicPoreConductivityCk=law?Ck:0.;
      ComputeFreeSurfaceTracking();auto originalC=Read();const auto m=Map(originalC);
      // Poison only output C replicas; correct native matrices remain the conditional inputs.
      auto c=originalC.c;unsigned poisonedC=0;
      for(unsigned p=0;p<Np;p++)if(CODE_IsFixed(originalC.code[p])||CODE_IsPeriodic(originalC.code[p])){c[p]=TMatrix3d(std::numeric_limits<double>::quiet_NaN());poisonedC++;}
      Need(poisonedC>Fixed,"C poison/periodic witnesses empty");Up(CorrMatg,c);
      if(!law){
        auto ids=originalC.id;unsigned badslot=UINT_MAX;for(unsigned p=Npb;p<Np;p++)if(CODE_IsPeriodic(originalC.code[p])&&CODE_IsFluid(originalC.code[p])){badslot=p;break;}
        Need(badslot!=UINT_MAX,"Real nonzero-prefix owner negative is empty");ids[badslot]=CaseNp;Up(Idpg,ids);bool caught=false;
        try{unsigned* map=PrepareDynamicPorePeriodicGpu();if(map)ArraysGpu->Free(map);}
        catch(const std::exception& e){caught=std::string(e.what()).find("normal-fluid native owner")!=std::string::npos;}
        Up(Idpg,originalC.id);Need(caught&&Immutable(originalC),"Real missing owner was not rejected/restored");counts.ownernegative++;
      }
      unsigned* ridp=PrepareDynamicPorePeriodicGpu();Need(ridp!=nullptr,"Actual nonzero-prefix owner map absent");
      const auto map=Down(ridp,Fluid);unsigned permutation=0;for(unsigned id=Fixed;id<Total;id++){Need(map[id-Fixed]==m[id],"Actual fluid owner ID map differs");permutation+=unsigned(map[id-Fixed]!=Npb+id-Fixed);}counts.ownerperm=(std::max)(counts.ownerperm,permutation);
      ComputeDynamicPoreWallMatrixGpu();auto ready=Read();for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(ready.code[p])&&CODE_IsFluid(ready.code[p]))Need(Bits(ready.c[p],ready.c[m[ready.id[p]]]),"Fluid C owner repair failed");
      for(unsigned p=0;p<Np;p++)if(CODE_IsFixed(ready.code[p]))Need(Bits(ready.c[p],originalC.c[p]),"Wall C reconstruction did not repair poison");
      auto a=v.ace;auto theta=v.theta;unsigned forcepoison=0;
      for(unsigned p=0;p<Np;p++)if(CODE_IsFixed(ready.code[p])||CODE_IsPeriodic(ready.code[p])){a[p]=make_float3(NAN,NAN,NAN);forcepoison++;if(CODE_IsFluid(ready.code[p]))theta[p]=NAN;}
      Need(forcepoison>Fixed,"Finished acceleration poison empty");Up(Aceg,a);Up(PoroThetag,theta);Up(PorePressRateg,std::vector<float>(Np,Sentinel));
      ComputeDynamicPorePressureRateGpu(ridp);Cu(cudaDeviceSynchronize());const auto got=Read();CheckRates(csv,law?"smooth":"constant",got,law!=0);
      for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(got.code[p])){
        const unsigned q=m[got.id[p]];Need(Bits(got.c[p],got.c[q])&&Bits(got.ace[p],got.ace[q])&&Bits(got.theta[p],got.theta[q])&&Bits(got.rate[p],got.rate[q]),"Wall/fluid periodic output differs from normal owner");
      }
      owners<<(law?"smooth":"constant")<<','<<Np<<','<<Npb<<','<<NpbOk<<','<<Fluid<<','<<Fixed<<','<<counts.periodicfluid<<','<<counts.periodicwall<<','<<permutation<<",true\n";
      if(!law){
        const auto good=Reference(got,false);
        for(unsigned bad=0;bad<3;bad++){
          View wrong=got;for(unsigned p=0;p<Np;p++)if(CODE_IsFixed(wrong.code[p])){
            if(bad==0)wrong.c[p]=TMatrix3d(0);else if(bad==1)wrong.ace[p]=make_float3(0,0,0);else wrong.ace[p].x=-wrong.ace[p].x;
          }
          Up(CorrMatg,wrong.c);Up(Aceg,wrong.ace);Up(PorePressRateg,std::vector<float>(Np,Sentinel));Device<unsigned> invalid(1);Up(invalid.p,std::vector<unsigned>{Np});
          cusph::ComputeDynamicPorePressureRate(Np,Npb,DivData,Dcellg,Posxyg,Poszg,Codeg,CorrMatg,Aceg,PoroJg,PoroThetag,PorePressg,PorePressRateg,
            1.-double(SoilCte.Porosity),double(SoilCte.PoreWaterBulkModulus),double(SoilCte.PoreWaterRho),double(SoilCte.HydraulicConductivity),double(SoilCte.PoreWaterRho)*9.80665,double(MassFluid)/RhopZero,invalid.p,false,0.,nullptr,true,BoundModeg);
          Cu(cudaDeviceSynchronize());Need(Down(invalid.p,1)[0]==Np,"Deliberate wrong-wall coefficient produced an unrelated invalid-state failure");
          wrong.rate=Down(PorePressRateg,Np);const auto ref=Reference(wrong,false);unsigned changed=0;double effect=0,ratio=0,error=0;
          for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(wrong.code[p])&&CODE_IsFluid(wrong.code[p])){
            const double delta=fabs(double(wrong.rate[p])-got.rate[p]),residual=fabs(double(wrong.rate[p])-ref[p].value);Need(residual<=ref[p].budget,"Wrong-wall actual kernel/reference budget mismatch");
            effect=(std::max)(effect,delta);ratio=(std::max)(ratio,delta/(ref[p].budget+good[p].budget));error=(std::max)(error,residual);changed+=unsigned(delta>ref[p].budget+good[p].budget);
          }
          Need(changed>0&&ratio>1.,"Incorrect C/Ace full-rate counterfactual was empty");negative<<(bad==0?"zero_wall_C":bad==1?"zero_wall_Ace":"copy_instead_of_reflect_wall_Ace")<<','<<changed<<','<<effect<<','<<ratio<<','<<error<<'\n';counts.counterfactual++;
        }
        Put(got,true);
      }
      NoStep();Need(Immutable(seed),"Rate component moved/sorted actual particles");
    }
    DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;DynamicConductivitySpeedMax=0.;PosInteraction_Forces();Put(seed);counts.rollbacks++;
    csv.flush();owners.flush();negative.flush();Need(csv&&owners&&negative,"Rate/owner CSV output failed");
  }
  void FaceAndForce(const fs::path& out,const View& v){
    const auto m=Map(v);tdouble3 fluid=TDouble3(0),reaction=TDouble3(0);double pairabs=0;
    for(unsigned id=Fixed;id<Total;id++){
      const unsigned i=m[id];const double Vi=Volume(v.j[i]);fluid=fluid+Vec(v.ace[i])*(Rho(v.j[i])*Vi);
      for(unsigned j=0;j<Np;j++){
        const float dx=float(v.xy[i].x-v.xy[j].x),dz=float(v.z[i]-v.z[j]),rr=dx*dx+dz*dz;if(rr<ALMOSTZERO||rr>KernelSize2)continue;
        if(j<Npb)Need(v.mode[j]!=BMODE_MDBC2OFF,"Inactive actual wall contributed feedback volume");
        const float f=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,rr),gx=f*dx,gz=f*dz;
        const auto si=ToTSymMatrix3f(v.sigma[i]),sj=ToTSymMatrix3f(v.sigma[j]);const double pw=double(v.p[i])+v.p[j],Vj=Volume(v.j[j]);
        const auto force=TDouble3(Vi*Vj*((double(si.xx)+sj.xx-pw)*gx+(double(si.xz)+sj.xz)*gz),0,Vi*Vj*((double(si.zz)+sj.zz-pw)*gz+(double(si.xz)+sj.xz)*gx));
        pairabs+=Norm(force);if(j<Npb)reaction=reaction-force;
      }
    }
    const double residual=Norm(fluid+reaction),fb=128.*FLT_EPSILON*pairabs+4096.*DBL_EPSILON*(std::max)(1.,pairabs);
    Need(residual<=fb,"Actual fluid/wall reaction failed original float budget");counts.maxforce=residual/fb;
    const double cu=sqrt((double(SoilCte.ModulusK)+4.*SoilCte.ModulusG/3.+double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity)/RhopZero);
    const double pstar=double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity*Amplitude/cu;
    std::ofstream csv(out/"face_force.csv");csv<<std::setprecision(17)<<"plane_x,vn,vn_bound,qn,qn_bound,condition,neighbors,fluid_force_x,fluid_force_z,wall_reaction_x,wall_reaction_z,force_residual,force_bound,wrong_zero_wall_Ace_qn,wrong_copy_wall_Ace_qn,wrong_zero_over_bound,wrong_copy_over_bound\n";
    unsigned badzero=0,badcopy=0;for(unsigned side=0;side<2;side++){
      const auto face=TDouble3(side?Width:0,0,Lz*.5);tmatrix3d mom=TMatrix3d(0);tdouble3 rp=TDouble3(0),rv=TDouble3(0),ra=TDouble3(0);
      struct Sample{double w,bx,bz,p,v,a;bool wall;};std::vector<Sample> points;double pmax=1,vmax=Amplitude,amax=Amplitude*cu*2*acos(-1.)/FullLx;
      for(unsigned j=0;j<Np;j++){
        const auto d=TDouble3(v.xy[j].x-face.x,0,v.z[j]-face.z);const double rr=Dot(d,d);if(rr>double(KernelSize2))continue;
        const double wab=fsph::GetKernel_Wab<KERNEL_Wendland>(CSP,float(rr));if(wab<=0)continue;
        const double w=Volume(v.j[j])*wab,bx=d.x/KernelH,bz=d.z/KernelH,p=v.p[j],vel=j<Npb?v.derivative[j].x:v.vel[j].x,a=v.ace[j].x;
        points.push_back({w,bx,bz,p,vel,a,j<Npb});mom.a11+=w;mom.a12+=w*bx;mom.a13+=w*bz;mom.a21+=w*bx;mom.a22+=w*bx*bx;mom.a23+=w*bx*bz;mom.a31+=w*bz;mom.a32+=w*bx*bz;mom.a33+=w*bz*bz;
        rp=rp+TDouble3(1,bx,bz)*(w*p);rv=rv+TDouble3(1,bx,bz)*(w*vel);ra=ra+TDouble3(1,bx,bz)*(w*a);pmax=(std::max)(pmax,fabs(p));vmax=(std::max)(vmax,fabs(vel));amax=(std::max)(amax,fabs(a));
      }
      const double det=fmath::Determinant3x3(mom);Need(points.size()>6&&det>0,"Independent all-support physical-plane fit is singular");
      const auto inv=fmath::InverseMatrix3x3(mom,det);const double cond=(std::max)(1.,Inf(mom)*Inf(inv)),vp=inv.a11*rv.x+inv.a12*rv.y+inv.a13*rv.z,ap=inv.a11*ra.x+inv.a12*ra.y+inv.a13*ra.z,gp=(inv.a21*rp.x+inv.a22*rp.y+inv.a23*rp.z)/KernelH;
      double sb=0,sa=0,gscale=0,bad0=0,badCopy=0;for(const auto& s:points){
        const double beta=s.w*(inv.a11+inv.a12*s.bx+inv.a13*s.bz),alpha=s.w*(inv.a21+inv.a22*s.bx+inv.a23*s.bz)/KernelH;
        sb+=fabs(beta);sa+=fabs(alpha);gscale+=fabs(alpha*s.p);bad0+=beta*(s.wall?0:s.a);badCopy+=beta*(s.wall?-s.a:s.a);
      }
      const double sign=side?-1.:1.,kh=SoilCte.HydraulicConductivity,rhow=SoilCte.PoreWaterRho,gamma=rhow*9.80665,qn=-kh/gamma*(gp+rhow*ap)*sign,vn=vp*sign;
      const double qstar=kh/gamma*(2*acos(-1.)/FullLx*pstar+rhow*Amplitude*cu*2*acos(-1.)/FullLx);
      const double bv=4.*FLT_EPSILON*vmax*sb+4096.*DBL_EPSILON*cond*vmax+1e-4*Amplitude;
      const double bq=kh/gamma*(2.*FLT_EPSILON*pmax*sa+4.*rhow*FLT_EPSILON*amax*sb+4096.*DBL_EPSILON*cond*(gscale+rhow*amax))+1e-4*qstar;
      Need(bv<.01*Amplitude&&bq<.01*qstar&&fabs(vn)<=bv&&fabs(qn)<=bq,"Original independent physical-plane velocity/flux budget failed");
      const double q0=-kh/gamma*(gp+rhow*bad0)*sign,qcopy=-kh/gamma*(gp+rhow*badCopy)*sign;
      badzero+=unsigned(fabs(q0)>bq);badcopy+=unsigned(fabs(qcopy)>bq);
      counts.maxqn=(std::max)(counts.maxqn,fabs(qn)/bq);counts.maxvn=(std::max)(counts.maxvn,fabs(vn)/bv);counts.maxbadzero=(std::max)(counts.maxbadzero,fabs(q0)/bq);counts.maxbadcopy=(std::max)(counts.maxbadcopy,fabs(qcopy)/bq);
      csv<<face.x<<','<<vn<<','<<bv<<','<<qn<<','<<bq<<','<<cond<<','<<points.size()<<','<<fluid.x<<','<<fluid.z<<','<<reaction.x<<','<<reaction.z<<','<<residual<<','<<fb<<','<<q0<<','<<qcopy<<','<<fabs(q0)/bq<<','<<fabs(qcopy)/bq<<'\n';
    }Need(badzero>0&&badcopy>0,"Actual-force wrong-zero/copy acceleration face controls were empty");csv.flush();Need(bool(csv),"Face CSV write failed");
  }

  void ForceAudit(const fs::path& out){
    Put(seed);auto v=Read();const double k=2*acos(-1.)/FullLx;
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(v.code[p])){
      const double x=v.xy[p].x,cs=cos(k*x);v.j[p]=1.+cs/65536.;v.theta[p]=0.;v.p[p]=float(64.*cs);v.p0[p]=0.;
      v.vel[p]=make_float4(float(Amplitude*sin(k*x)),0,0,RhopZero);v.sigma[p]={16.*cs,0,0,0,0,0};v.plastic[p]=0.;
    }Put(v);const auto before=Read();const auto rows=NativeRows(before);const unsigned np=Np,npb=Npb;const auto inter=InterStep;
    const double time=TimeStep,locked=SymplecticDtPre,last=LastDt,error=FixedDt->GetDtError(false),cache=DynamicConductivitySpeedMax;const unsigned step=Nstep;
    // AceMax has never been reduced here: do not read/restore an undefined old statistic.
    Interaction_Forces(INTERSTEP_SymPredictor);Cu(cudaDeviceSynchronize());const auto actual=Read();NoStep();Need(Np==np&&Npb==npb&&Immutable(before),"Extra force changed actual cell identity/geometry");
    FaceAndForce(out,actual);
    std::ofstream rate(out/"force_rates.csv");rate<<std::setprecision(17)<<"slot,id,actual,reference,error,budget,error_over_budget,wall_neighbors\n";const auto ref=Reference(actual,false);unsigned n=0,wall=0;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(actual.code[p])&&CODE_IsFluid(actual.code[p])){
      const auto r=ref[p];const double e=fabs(double(actual.rate[p])-r.value);Need(e<=r.budget,"Actual full-force complete rate/reference budget failed");
      rate<<p<<','<<actual.id[p]<<','<<actual.rate[p]<<','<<r.value<<','<<e<<','<<r.budget<<','<<e/r.budget<<','<<r.wall<<'\n';n++;wall+=unsigned(r.wall>0);
    }Need(n==Fluid&&wall>0,"Full-force true wall-neighbor rate reference empty");
    Put(before);InterStep=inter;DynamicConductivitySpeedMax=cache;
    Need(TimeStep==time&&Nstep==step&&SymplecticDtPre==locked&&LastDt==last&&FixedDt->GetDtError(false)==error,"Extra force altered clock/fixed-step telemetry");
    PosInteraction_Forces();const auto after=Read();Need(Same(rows,NativeRows(after))&&Immutable(before)&&Same(before.normal,after.normal)&&Same(before.mode,after.mode)&&Same(before.c,after.c)&&Same(before.tangent,after.tangent)&&Same(before.fs,after.fs),"Covered native/boundary state rollback was not byte-exact");
    Need(std::isfinite(AceMax)&&AceMax>=0&&std::isfinite(VelMax)&&VelMax>=0&&std::isfinite(ViscDtMax)&&ViscDtMax>=0,"First real force statistics not genuinely initialized");
    NoStep();Put(seed);rate.flush();Need(bool(rate),"Force rate CSV write failed");counts.audits++;counts.rollbacks++;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Initialize(cfg,log);const fs::path out(cfg->DirOut);Affine(out,false);Affine(out,true);RateComponents(out);ForceAudit(out);
    const auto last=Read();Need(Immutable(seed)&&Same(seed.normal,last.normal)&&Same(NativeRows(seed),NativeRows(last)),"Component did not restore initial native state/normal bytes");
    NoStep();Need(counts.affine==2&&counts.affinerows==512&&counts.quadratic==256&&counts.ratecases==2&&counts.raterows==2048&&counts.counterfactual==3&&counts.ownernegative==1&&counts.audits==1&&counts.rollbacks==2,"Incomplete declared component counts");
    int device=0;Cu(cudaGetDevice(&device));cudaDeviceProp props{};Cu(cudaGetDeviceProperties(&props,device));
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gpu_wall_component_r1\",\"native_soil\":1024,\"native_fixed\":256,\"actual_np\":"<<Np<<",\"actual_nonzero_Npb\":"<<Npb<<",\"actual_NpbOk\":"<<NpbOk
      <<",\"fluid_periodic_slots\":"<<counts.periodicfluid<<",\"wall_periodic_slots\":"<<counts.periodicwall<<",\"permuted_owner_slots_observed\":"<<counts.ownerperm<<",\"affine_cases\":"<<counts.affine<<",\"affine_wall_rows\":"<<counts.affinerows<<",\"coincident_pressure_rows\":"<<counts.quadratic
      <<",\"complete_rate_cases\":"<<counts.ratecases<<",\"complete_rate_rows\":"<<counts.raterows<<",\"wrong_wall_rate_cases\":"<<counts.counterfactual<<",\"real_owner_negative_cases\":"<<counts.ownernegative<<",\"actual_force_component_audits\":"<<counts.audits<<",\"persistent_rollback_checks\":"<<counts.rollbacks
      <<",\"max_actual_rate_reference_error_Pa_s\":"<<counts.maxrateerror<<",\"max_rate_error_over_original_budget\":"<<counts.maxrateratio<<",\"force_reaction_over_original_budget\":"<<counts.maxforce<<",\"max_face_qn_over_original_budget\":"<<counts.maxqn<<",\"max_face_vn_over_original_budget\":"<<counts.maxvn
      <<",\"max_wrong_zero_face_qn_over_budget\":"<<counts.maxbadzero<<",\"max_wrong_copy_face_qn_over_budget\":"<<counts.maxbadcopy
      <<",\"actual_LoadConfig_ConfigDomain_InitRunGpu\":true,\"actual_private_wall_host_helpers\":true,\"actual_complete_rate_kernel\":true,\"actual_nonzero_fixed_prefix_and_wall_neighbors\":true,\"Dp_over_8_noncoincident_affine_witness\":true,\"coincident_nonlinear_pressure_anchor_bits_exact\":true"
      <<",\"all_real_positions_and_normal_bytes_restored\":true,\"covered_native26_and_persistent_boundary_rollback_exact\":true,\"first_force_statistics_computed_not_read_before_force\":true,\"extra_force_is_not_an_integrator_stage\":true,\"J_C_Ace_rate_references_use_actual_conditional_C\":true"
      <<",\"completed_physical_steps\":0,\"actual_ComputeStep_Sym_called\":false,\"actual_production_Run_called\":false,\"physical_trajectory_or_energy_acceptance\":false,\"native_BI4_serialization_tested\":false,\"full_force_stage_call_counts_directly_observed\":false,\"public_GPU_dynamic_mode\":false,\"physical_acceptance\":false,\"device_name\":\""<<props.name<<"\"}\n";
    done.flush();Need(bool(done),"Completion write failed");
  }
};
}
int main(int argc,char** argv){
  try{
    Need(argc>=6&&std::string(argv[1])=="--wall","Use --wall followed by ordinary -gpu arguments, sealed wall seed and fresh output");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
    Need(!cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Only fresh private GPU component arguments admitted");
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    gw::WallFixture fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU wall component rejected; preserve all evidence\n";return 2;}
}

