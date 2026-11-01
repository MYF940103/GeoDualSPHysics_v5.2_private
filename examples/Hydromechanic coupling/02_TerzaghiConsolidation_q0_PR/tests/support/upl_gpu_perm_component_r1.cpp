// Private GPU smooth-k components. The copied constant suite remains unchanged and executes first.
// No coupled Run, public GPU option, wall or variable-coefficient stability admission.
#define main RetainedGpuK0TimeMain
#include "upl_gpu_k0_time_r1.cpp"
#undef main
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JArraysGpu.h"
#include <array>
#include <vector_functions.h>

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
  // Generic CalcRidp selects NORMAL IDs, so nonfluid ID99 must stay outside fluid range [100,104).
  const std::vector<unsigned> baseid={0,1,100,103,102,100,100,103,102,99,101,101,999,1000};
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

struct LawRef{
  Ref value;double ki=0,porosity=0,volume=0,rho=0,chainp=0,chaina=0,speed=0,speedbudget=0;
  tdouble3 gj=TDouble3(0);
};
struct PermTotals{
  unsigned patchcases=0,patchrows=0,periodiccases=0,periodicrows=0,directrate=0,hostrate=0;
  unsigned uniforms=0,guards=0,cachecases=0,requests=0,corners=0;
  double maxerror=0,maxratio=0,maxspeederror=0,maxspeedratio=0;
};
static double LawK(double k0,double j,double solid0,double ck){
  return k0==0||j==1.?k0:k0*exp((j-1.)/(solid0*ck));
}
static std::vector<LawRef> LawReference(unsigned np,unsigned npb,const StCteSph& csp,double solid0,double kw,double rhow,double k0,double vol0,double ck
  ,const std::vector<double2>& xy,const std::vector<double>& z,const std::vector<typecode>& code
  ,const std::vector<tmatrix3d>& c,const std::vector<float3>& ace,const std::vector<double>& js
  ,const std::vector<double>& theta,const std::vector<float>& pressure){
  std::vector<LawRef> result(np);const double gamma=rhow*9.80665,alpha=1./(solid0*ck);
  for(unsigned i=npb;i<np;i++)if(CODE_IsNormal(code[i])&&CODE_IsFluid(code[i])){
    auto& r=result[i];r.ki=LawK(k0,js[i],solid0,ck);r.porosity=1.-solid0/js[i];r.volume=vol0*js[i];r.rho=rhow+(2048.-rhow)/js[i];
    double lp=0,da=0,alp=0,ada=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),alx=TDouble3(0),agp=TDouble3(0),agj=TDouble3(0);
    if(k0>0)for(unsigned b=0;b<np;b++)if(CODE_IsFluid(code[b])){
      const tdouble3 d=TDouble3(xy[i].x-xy[b].x,0,z[i]-z[b]);const double rr=Dot(d,d);
      if(rr>double(csp.kernelsize2)||rr<ALMOSTZERO)continue;
      const tdouble3 g=d*double(fsph::GetKernel_Fac<KERNEL_Wendland>(csp,float(rr)));
      const auto gi=Product(c[i],g),gb=Product(c[b],g);const double v=vol0*js[b],dp=double(pressure[i])-pressure[b],dj=js[b]-js[i];
      const double w=v*Dot(d,gi+gb)/(rr+double(csp.eta2));lp+=w*dp;alp+=fabs(w*dp);lx=lx+d*w;gp=gp-gi*(v*dp);r.gj=r.gj+gi*(v*dj);
      alx.x+=fabs(d.x*w);alx.y+=fabs(d.y*w);alx.z+=fabs(d.z*w);
      agp.x+=fabs(gi.x*v*dp);agp.y+=fabs(gi.y*v*dp);agp.z+=fabs(gi.z*v*dp);
      agj.x+=fabs(gi.x*v*dj);agj.y+=fabs(gi.y*v*dj);agj.z+=fabs(gi.z*v*dj);
      const tdouble3 a=TDouble3(double(ace[b].x)-ace[i].x,double(ace[b].y)-ace[i].y,double(ace[b].z)-ace[i].z);
      da+=v*Dot(a,gi);ada+=v*(fabs(a.x*gi.x)+fabs(a.y*gi.y)+fabs(a.z*gi.z));
    }
    const double B=kw/r.porosity,scale=alpha*r.ki;
    const auto ai=TDouble3(ace[i].x,ace[i].y,ace[i].z);
    r.chainp=B/gamma*scale*Dot(r.gj,gp);r.chaina=B/gamma*scale*rhow*Dot(r.gj,ai);
    const double chain=scale*(Dot(r.gj,gp)+rhow*Dot(r.gj,ai));
    const double rawchain=fabs(scale)*(agj.x*(agp.x+rhow*fabs(ai.x))+agj.y*(agp.y+rhow*fabs(ai.y))+agj.z*(agp.z+rhow*fabs(ai.z)));
    const double raw=B*(fabs(theta[i])+r.ki/gamma*(alp+Dot(agp,alx)+rhow*ada)+rawchain/gamma);
    r.value={B*(-theta[i]+r.ki/gamma*(lp-Dot(gp,lx)+rhow*da)+chain/gamma),
      64.*FLT_EPSILON*raw+256.*DBL_EPSILON*(std::max)(1.,fabs(B*theta[i]))+1e-6,
      B*r.ki/gamma*(lp-Dot(gp,lx)),B*r.ki/gamma*rhow*da};
    r.speed=B/gamma*fabs(scale)*sqrt(Dot(r.gj,r.gj));
    r.speedbudget=64.*FLT_EPSILON*B/gamma*fabs(scale)*sqrt(Dot(agj,agj))
      +512.*DBL_EPSILON*(std::max)(1.,fabs(r.speed))+1e-12;
  }
  return result;
}
static void LawRow(std::ostream& out,const std::string& label,unsigned slot,unsigned id,double actual,const LawRef& r,PermTotals& total){
  const double error=fabs(actual-r.value.rate);
  Need(std::isfinite(actual)&&actual!=Sentinel&&std::isfinite(r.value.rate)&&std::isfinite(r.value.budget)&&r.value.budget>0&&error<=r.value.budget,"Variable-k complete rate exceeds propagated discrete-term budget");
  total.maxerror=(std::max)(total.maxerror,error);total.maxratio=(std::max)(total.maxratio,error/r.value.budget);
  out<<label<<','<<slot<<','<<id<<','<<actual<<','<<r.value.rate<<','<<error<<','<<r.value.budget<<','<<error/r.value.budget
    <<','<<r.ki<<','<<r.porosity<<','<<r.volume<<','<<r.rho<<','<<r.gj.x<<','<<r.gj.y<<','<<r.gj.z
    <<','<<r.value.pressure<<','<<r.value.acceleration<<','<<r.chainp<<','<<r.chaina<<','<<r.speed<<','<<r.speedbudget<<'\n';
}
static void CheckSpeed(double actual,const std::vector<LawRef>& refs,PermTotals& total,double& reference,double& budget){
  reference=0;budget=0;for(const auto& r:refs){reference=(std::max)(reference,r.speed);budget=(std::max)(budget,r.speedbudget);}
  const double error=fabs(actual-reference);Need(std::isfinite(actual)&&actual>=0&&budget>0&&error<=budget,"Actual native gradient-speed maximum exceeds original propagated float-kernel budget");
  total.maxspeederror=(std::max)(total.maxspeederror,error);total.maxspeedratio=(std::max)(total.maxspeedratio,error/budget);
}
static const char* LawHeader="field,slot,id,actual,reference,error,budget,error_over_budget,reference_k,reference_n,reference_V,reference_rho,reference_GJ_x,reference_GJ_y,reference_GJ_z,reference_pressure_source,reference_acceleration_source,reference_pressure_chain,reference_acceleration_chain,reference_speed,speed_budget\n";

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
  void LawState(unsigned field){
    for(unsigned i=0;i<cap;i++){
      ths[i]=0;ps[i]=128;as[i]=make_float3(0,0,0);
      if(i>=np)continue;const double x=xs[i].x,zr=zs[i];
      js[i]=field==0?1.:(field==1?1.01:1.+(x-.5)/32.+(zr-.5)/64.);
      if(field==0||field==1||field==5){ps[i]=float(128+32*x*x+16*zr*zr);as[i]=make_float3(float(x/8),0,float(zr/16));}
      if(field==2||field==4)ps[i]=float(128+125*x+500*zr);
      if(field==3)as[i]=make_float3(.125f,0,.5f);
      if(field==4)as[i]=make_float3(-.125f,0,-.5f);
      if(field==7)ths[i]=-1./32.;
    }
    Up(j.p,js);Up(theta.p,ths);Up(p.p,ps);Up(ace.p,as);
    cusph::ComputeFreeSurfaceTracking(KERNEL_Wendland,true,np,0,dvd,dcell.p,pos.p,vel.p,code.p,c.p,fstype.p,normal.p,posdiv.p,false,j.p);
    matrices=Down(c.p,cap);Need(matrices[9].a11==-123.25&&matrices[10].a11==-456.5,"Variable-k FS tail changed");
  }
  std::vector<LawRef> LawRefs(double k0,double ck)const{
    return LawReference(np,0,sph,.75,constants.porewaterbulkmodulus,1000,k0,.0625,ck,xs,zs,cs,matrices,as,js,ths,ps);
  }
  void LawFields(bool jitter,std::ostream& out,std::ostream& summary,std::ostream& scale,std::ostream& guards,PermTotals& total){
    const char* names[]={"J1_exact","uniform_J1p01","affineJ_pressure_chain","affineJ_acceleration_chain","affineJ_R0","nonlinear_complete","zero_driving_nonzero_speed","k0_exact"};
    constexpr double ck=.125;const double kbase=double(float(1e-4));
    Device<double> speed(2),values(3);
    for(unsigned f=0;f<8;f++){
      LawState(f);const double k0=f==7?0:kbase;const auto ref=LawRefs(k0,ck);
      Up(rate.p,std::vector<float>(cap,Sentinel));Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});Up(speed.p,std::vector<double>{0.,-901.25});
      cusph::ComputeDynamicPorePressureRate(np,0,dvd,dcell.p,xy.p,z.p,code.p,c.p,ace.p,j.p,theta.p,p.p,rate.p,.75,constants.porewaterbulkmodulus,1000,k0,1000*9.80665,.0625,invalid.p,true,ck,speed.p);total.directrate++;
      const auto got=Down(rate.p,cap);const auto actualSpeed=Down(speed.p,2);
      Need(Down(invalid.p,2)==std::vector<unsigned>({np,0x1234abcd})&&got[9]==Sentinel&&got[10]==Sentinel&&actualSpeed[1]==-901.25,"Law rate flag/tail contract failed");
      double sr=0,sb=0;CheckSpeed(actualSpeed[0],ref,total,sr,sb);double cp=0,ca=0,mb=0;
      const std::string label=std::string(jitter?"jitter_":"regular_")+names[f];
      for(unsigned i=0;i<np;i++){
        LawRow(out,label,i,i,got[i],ref[i],total);total.patchrows++;
        cp=(std::max)(cp,fabs(ref[i].chainp));ca=(std::max)(ca,fabs(ref[i].chaina));mb=(std::max)(mb,ref[i].value.budget);
        if(f==4)Need(fabs(ref[i].value.rate)<=ref[i].value.budget&&fabs(double(got[i]))<=ref[i].value.budget,"Variable-k affine R0 cancellation failed");
        if(f==6)Need(got[i]==0,"Zero driving must have exactly zero pressure rate despite nonzero speed");
      }
      if(f==2||f==5)Need(cp>10*mb,"Pressure coefficient-gradient chain is empty");
      if(f==3||f==5)Need(ca>10*mb,"Acceleration coefficient-gradient chain is empty");
      if(f==2||f==3||f==5||f==6)Need(actualSpeed[0]>10*sb,"Variable-k speed evidence is empty");
      if(f==0||f==7){
        Up(rate.p,std::vector<float>(cap,Sentinel));Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
        cusph::ComputeDynamicPorePressureRate(np,0,dvd,dcell.p,xy.p,z.p,code.p,c.p,ace.p,j.p,theta.p,p.p,rate.p,.75,constants.porewaterbulkmodulus,1000,k0,1000*9.80665,.0625,invalid.p);total.directrate++;
        Need(Same(got,Down(rate.p,cap))&&actualSpeed[0]==0,"J1/k0 law degeneracy is not bit-exact with constant path");
      }
      if(f==5){
        Up(rate.p,std::vector<float>(cap,Sentinel));Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
        cusph::ComputeDynamicPorePressureRate(np,0,dvd,dcell.p,xy.p,z.p,code.p,c.p,ace.p,j.p,theta.p,p.p,rate.p,.75,constants.porewaterbulkmodulus,1000,k0,1000*9.80665,.0625,invalid.p,true,ck,nullptr);total.directrate++;
        Need(Same(got,Down(rate.p,cap))&&Down(invalid.p,2)==std::vector<unsigned>({np,0x1234abcd}),"NULL speed output changed complete law rate or skipped validation");
      }
      if(f<2){
        Up(values.p,std::vector<double>{0,0,-902.25});Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});
        cusph::ComputePorosityWaveSpeed2(np,0,.75,2048,1000,(double(constants.modulus_K)+4.*double(constants.modulus_G)/3.),constants.porewaterbulkmodulus,code.p,j.p,values.p,invalid.p,kbase,1000*9.80665,values.p+1,true,ck);
        const auto v=Down(values.p,3);const double n=1.-.75/js[0],rho=1000.+1048./js[0],ki=LawK(kbase,js[0],.75,ck),d=constants.porewaterbulkmodulus/n*ki/(1000*9.80665);
        const double observedK=v[1]*(1000*9.80665)*n/constants.porewaterbulkmodulus;
        Need(Down(invalid.p,2)==std::vector<unsigned>({np,0x1234abcd})&&v[2]==-902.25&&NearScale(v[0],(double(constants.modulus_K)+4.*double(constants.modulus_G)/3.+constants.porewaterbulkmodulus/n)/rho)
          &&fabs(observedK-ki)<=5e-13*(std::max)(fabs(ki),DBL_MIN),"Actual current-k diffusion getter disagrees with analytic uniform closure");
        scale<<label<<','<<js[0]<<','<<ki<<','<<observedK<<','<<v[0]<<','<<v[1]<<','<<d<<'\n';total.uniforms++;
      }
      Need(Same(xs,Down(xy.p,cap))&&Same(zs,Down(z.p,cap))&&Same(js,Down(j.p,cap))&&Same(ps,Down(p.p,cap))&&Same(as,Down(ace.p,cap))&&Same(ths,Down(theta.p,cap))&&Same(matrices,Down(c.p,cap)),"Law kernel mutated frozen component inputs");
      summary<<label<<",9,"<<actualSpeed[0]<<','<<sr<<','<<sb<<','<<fabs(actualSpeed[0]-sr)<<','<<cp<<','<<ca<<'\n';total.patchcases++;
    }
    for(unsigned f=0;f<2;f++){
      const double J=f? .99:1.01;for(unsigned i=0;i<np;i++)js[i]=J;Up(j.p,js);Up(rate.p,std::vector<float>(cap,Sentinel));
      Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});Up(speed.p,std::vector<double>{0,-901.25});
      cusph::ComputeDynamicPorePressureRate(np,0,dvd,dcell.p,xy.p,z.p,code.p,c.p,ace.p,j.p,theta.p,p.p,rate.p,.75,constants.porewaterbulkmodulus,1000,kbase,1000*9.80665,.0625,invalid.p,true,1e-6,speed.p);total.directrate++;
      Need(Down(invalid.p,2)==std::vector<unsigned>({0,0x1234abcd}),"Legal-Ck conductivity overflow/positive-base underflow was not rejected");
      Up(invalid.p,std::vector<unsigned>{np,0x1234abcd});Up(values.p,std::vector<double>{0,0,-902.25});
      cusph::ComputePorosityWaveSpeed2(np,0,.75,2048,1000,(double(constants.modulus_K)+4.*double(constants.modulus_G)/3.),constants.porewaterbulkmodulus,code.p,j.p,values.p,invalid.p,kbase,1000*9.80665,values.p+1,true,1e-6);
      Need(Down(invalid.p,2)==std::vector<unsigned>({0,0x1234abcd})&&Down(values.p,3)[2]==-902.25,"Actual diffusion scale did not reject the same invalid conductivity");
      guards<<(jitter?"jitter_":"regular_")<<(f?"underflow":"overflow")<<",device_rate_and_scale,0,true,true\n";total.guards++;
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

  void LawHostGuards(std::ostream& guards,PermTotals& total){
    Restore();Stats();SoilCte.HydraulicConductivity=1e-4f;
    const double ck[]={0.,-1.,NAN,INFINITY,std::numeric_limits<double>::denorm_min(),.125};
    const char* names[]={"Ck_zero","Ck_negative","Ck_nan","Ck_infinite","alpha_overflow","requires_dynamic"};
    for(unsigned f=0;f<6;f++){
      DynamicPoreConductivity=true;DynamicPoreConductivityCk=ck[f];DynamicPorePressure=f!=5;
      const auto before=Capture();const auto th=Down(PoroThetag,Np);bool caught=false;
      try{InitPorosityObserverGpu();}catch(const std::exception& e){caught=std::string(e.what()).find("variable conductivity")!=std::string::npos;}
      Need(caught&&Equal(before,Capture())&&Same(th,Down(PoroThetag,Np))&&NoPre()&&TimeStep==0&&Nstep==0,"Real host conductivity Init guard did not reject before state advance");
      guards<<names[f]<<",host_Init,0,true,true\n";total.guards++;
    }
    DynamicPorePressure=true;DynamicPoreConductivity=false;DynamicPoreConductivityCk=NAN;Restore();Up(PoroThetag,std::vector<double>(Np,0));
    const auto before=Capture();InitPorosityObserverGpu();Need(Equal(before,Capture()),"OFF must ignore unused nonfinite Ck");
    guards<<"OFF_ignores_Ck_nan,host_Init,0,false,true\n";total.guards++;DynamicPoreConductivityCk=0.;
  }
  void LawCachePeriodic(std::ostream& cache,std::ostream& requests,PermTotals& total){
    Restore();Stats();ConstantDataUp();PreInteraction_Forces();
    auto stage=[&](bool law,float k0,bool uniform){
      DynamicPoreConductivity=law;DynamicPoreConductivityCk=1./16384.;SoilCte.HydraulicConductivity=k0;
      auto js=seed.j;std::vector<double> theta(Np,0);std::vector<float3> ace(Np,make_float3(0,0,0));std::vector<float> pressure(Np,128);
      for(unsigned i=0;i<Np;i++){const unsigned owner=Owner(seed.id[i]);js[i]=uniform?1.:1.+.001*cos(8.*acos(-1.)*seed.xy[owner].x/MapRealSize.x);}
      Up(PoroJg,js);Up(PoroThetag,theta);Up(Aceg,ace);Up(PorePressg,pressure);Up(PorePressRateg,std::vector<float>(Np,Sentinel));
      ComputeFreeSurfaceTracking();unsigned* map=PrepareDynamicPorePeriodicGpu();const auto c=Down(CorrMatg,Np);
      const auto ref=LawReference(Np,Npb,CSP,.75,SoilCte.PoreWaterBulkModulus,1000,k0,double(MassFluid)/RhopZero,DynamicPoreConductivityCk,seed.xy,seed.z,seed.code,c,ace,js,theta,pressure);
      ComputeDynamicPorePressureRateGpu(map);total.hostrate++;Need(Down(PorePressRateg,Np)==std::vector<float>(Np,0),"Zero driving produced nonzero pressure during speed-cache test");return ref;
    };
    try{
      const auto ref=stage(true,1e-4f,false);double sr=0,sb=0;CheckSpeed(DynamicConductivitySpeedMax,ref,total,sr,sb);
      Need(DynamicConductivitySpeedMax>10*sb,"Actual host zero-driving gradient-speed evidence is empty");
      const double active=DynamicConductivitySpeedMax;double wave=0,pore=0;GetDynamicStepScalesGpu(wave,pore);
      const auto js=Down(PoroJg,Np);double maxcu=0,maxd=0;
      for(unsigned i=Npb;i<Np;i++)if(CODE_IsNormal(seed.code[i])&&CODE_IsFluid(seed.code[i])){
        const double n=1.-.75/js[i],rho=1000.+1048./js[i],ki=LawK(double(SoilCte.HydraulicConductivity),js[i],.75,DynamicPoreConductivityCk);
        maxcu=(std::max)(maxcu,(M()+double(SoilCte.PoreWaterBulkModulus)/n)/rho);maxd=(std::max)(maxd,double(SoilCte.PoreWaterBulkModulus)/n*ki/(1000*9.80665));
      }
      const double wr=double(KernelH)/((std::max)(sqrt(maxcu),VelMax*10.)+double(KernelH)*ViscDtMax),pr=double(PoreDtSafety)*KernelH*KernelH/maxd;
      Need(NearScale(wave,wr)&&NearScale(pore,pr),"Host current-law wave/pore scales differ from independent per-node ki");
      const double old=(std::min)(CFLnumber*wave,pore),bound=(std::min)(old,double(PoreDtSafety)*KernelH/active);
      Need(bound>0&&bound<=.5*old,"Gradient necessary bound must be genuinely active before request tests");
      cache<<"periodic,active,"<<active<<','<<sr<<','<<sb<<','<<wave<<','<<pore<<','<<old<<','<<bound<<",true\n";total.cachecases++;
      const char* names[]={"variable_safe","fixed_safe","fixed_bound","locked_midway","requested_midway","DtMin_midway","DtMin_above_fixed","locked_bound"};
      for(unsigned f=0;f<8;f++){
        Stats();Need(Bits(DynamicConductivitySpeedMax,active),"Active cache must remain the actual rate result");SymplecticDtPre=.25*bound;double expected=bound;bool reject=false;
        if(f==1){FixedDt=new JDsFixedDt(.5*bound);DtMin=.125*bound;expected=.5*bound;}
        if(f==2)FixedDt=new JDsFixedDt(bound);
        if(f==3){SymplecticDtPre=.5*(bound+old);reject=true;}
        if(f==4){FixedDt=new JDsFixedDt(.5*(bound+old));reject=true;}
        if(f==5){DtMin=.5*(bound+old);reject=true;}
        if(f==6){FixedDt=new JDsFixedDt(.5*bound);DtMin=.75*bound;reject=true;}
        if(f==7)SymplecticDtPre=bound;
        const auto before=Capture();const auto th=Down(PoroThetag,Np);const auto rr=Down(PorePressRateg,Np);const auto cc=Down(CorrMatg,Np);const auto aa=Down(Aceg,Np);
        const double current=SymplecticDtPre,fixed=FixedDt?FixedDt->GetFixedValue():0.;double selected=0;bool caught=false;
        try{selected=DtVariable(false);}catch(const std::exception& e){caught=std::string(e.what()).find("GPU porosity")!=std::string::npos;}
        Need(caught==reject&&Equal(before,Capture())&&Same(th,Down(PoroThetag,Np))&&Same(rr,Down(PorePressRateg,Np))&&Same(cc,Down(CorrMatg,Np))&&Same(aa,Down(Aceg,Np))
          &&Bits(DynamicConductivitySpeedMax,active)&&NoPre()&&DtModif==0&&TimeStep==0&&Nstep==0,"Actual gradient-bound request rejected wrong case or advanced state");
        if(!caught)Need(Bits(selected,expected),"Safe gradient-bound request was clipped/uplifted");
        const double err=FixedDt?FixedDt->GetDtError(false):0.;if(FixedDt)Need(Bits(err,fixed-bound),"FixedDt did not receive full gradient-aware bound");
        requests<<names[f]<<','<<old<<','<<bound<<','<<current<<','<<fixed<<','<<DtMin<<','<<caught<<','<<reject<<','<<selected<<','<<err<<",true\n";total.requests++;
      }
      for(unsigned f=0;f<4;f++){
        Stats();DynamicConductivitySpeedMax=DBL_MAX;stage(f!=0,f==1?0.f:1e-4f,f==2);
        const double got=DynamicConductivitySpeedMax;
        if(f<3)Need(got==0.,"OFF/k0/uniform-J actual rate did not clear stale speed");
        else Need(Bits(got,active),"Restored law field did not recompute identical actual speed");
        cache<<"periodic,"<<(f==0?"OFF_reset":f==1?"k0_reset":f==2?"uniform_reset":"active_recomputed")<<','<<got<<",0,0,0,0,0,0,true\n";total.cachecases++;
      }
    }catch(...){PosInteraction_Forces();Restore();throw;}
    PosInteraction_Forces();Restore();Stats();DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;DynamicConductivitySpeedMax=0.;
  }
  void LawPeriodic(const fs::path& out,PermTotals& total){
    std::ofstream rows(out/"law_periodic_rates.csv"),summary(out/"law_periodic_summary.csv");rows<<std::setprecision(17)<<LawHeader;
    summary<<std::setprecision(17)<<"field,slots,ghosts,corners,actual_speed,reference_speed,speed_budget,owner_copy_exact\n";
    for(unsigned f=0;f<2;f++){
      Restore();Stats();DynamicPoreConductivity=true;DynamicPoreConductivityCk=.125;SoilCte.HydraulicConductivity=f?1e-4f:0;ConstantDataUp();
      PreInteraction_Forces();auto js=seed.j;std::vector<float3> a(Np);std::vector<double> th(Np);std::vector<float> pressure(Np);
      unsigned ghosts=0,corners=0;
      for(unsigned i=0;i<Np;i++){
        const unsigned owner=Owner(seed.id[i]);const double x=seed.xy[owner].x,z=seed.z[owner];
        js[i]=1.+.003*cos(2*acos(-1.)*x/MapRealSize.x)+.001*sin(2*acos(-1.)*z/MapRealSize.z);
        pressure[i]=f?float(128+64*cos(2*acos(-1.)*x/MapRealSize.x)+32*sin(2*acos(-1.)*z/MapRealSize.z)):128.f;
        a[i]=make_float3(float(x/8),0,float(z/16));th[i]=f?double(int(seed.id[i]%3)-1)/1024.:-1./32.;
        if(CODE_IsPeriodic(seed.code[i])){a[i]=make_float3(NAN,NAN,NAN);th[i]=NAN;ghosts++;
          if(fabs(seed.xy[i].x-seed.xy[owner].x)>1e-12&&fabs(seed.z[i]-seed.z[owner])>1e-12)corners++;}
      }
      Up(PoroJg,js);ComputeFreeSurfaceTracking();auto c=Down(CorrMatg,Np);
      for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(seed.code[i]))c[i]=TMatrix3d(NAN);Up(CorrMatg,c);
      unsigned* map=PrepareDynamicPorePeriodicGpu();c=Down(CorrMatg,Np);auto expectedA=a;auto expectedTheta=th;
      for(unsigned i=0;i<Np;i++)if(CODE_IsPeriodic(seed.code[i])){const unsigned o=Owner(seed.id[i]);expectedA[i]=a[o];expectedTheta[i]=th[o];Need(Bits(c[i],c[o]),"Law C owner repair failed");}
      Up(Aceg,a);Up(PoroThetag,th);Up(PorePressg,pressure);Up(PorePressRateg,std::vector<float>(Np,Sentinel));
      const auto before=Capture();const auto ref=LawReference(Np,Npb,CSP,.75,SoilCte.PoreWaterBulkModulus,1000,SoilCte.HydraulicConductivity,double(MassFluid)/RhopZero,.125,seed.xy,seed.z,seed.code,c,expectedA,js,expectedTheta,pressure);
      ComputeDynamicPorePressureRateGpu(map);total.hostrate++;const auto got=Down(PorePressRateg,Np);const auto gotA=Down(Aceg,Np);const auto gotT=Down(PoroThetag,Np);
      double sr=0,sb=0;CheckSpeed(DynamicConductivitySpeedMax,ref,total,sr,sb);
      Need(f?DynamicConductivitySpeedMax>10*sb:DynamicConductivitySpeedMax==0,"Law periodic max is empty or k0 did not stay zero");
      for(unsigned i=0;i<Np;i++){
        const unsigned o=CODE_IsPeriodic(seed.code[i])?Owner(seed.id[i]):i;LawRow(rows,f?"positive_law":"k0_law",i,seed.id[i],got[i],ref[o],total);total.periodicrows++;
        if(CODE_IsPeriodic(seed.code[i]))Need(Bits(got[i],got[o])&&Bits(gotA[i],gotA[o])&&Bits(gotT[i],gotT[o]),"Law Ace/theta/rate owner copy differs");
      }
      Need(ghosts>0&&corners>0&&Equal(before,Capture()),"Law periodic case is vacuous or changed covered physical input");
      total.corners+=corners;summary<<f<<','<<Np<<','<<ghosts<<','<<corners<<','<<DynamicConductivitySpeedMax<<','<<sr<<','<<sb<<",true\n";total.periodiccases++;PosInteraction_Forces();
    }
    Restore();Stats();DynamicPoreConductivity=false;DynamicPoreConductivityCk=0;DynamicConductivitySpeedMax=0;
    rows.flush();summary.flush();Need(bool(rows)&&bool(summary),"Law periodic output failed");
  }
  void VariableSuite(const fs::path& out){
    PermTotals total;std::ofstream rows(out/"law_rates.csv"),summary(out/"law_summary.csv"),scale(out/"law_scales.csv"),guards(out/"law_guards.csv"),cache(out/"law_cache.csv"),requests(out/"law_requests.csv");
    for(auto* stream:{&rows,&summary,&scale,&guards,&cache,&requests})*stream<<std::setprecision(17);
    rows<<LawHeader;summary<<"field,rows,actual_speed,reference_speed,speed_budget,speed_error,reference_pressure_chain,reference_acceleration_chain\n";
    scale<<"field,J,reference_k,inferred_k_from_actual_Dmax,actual_maxcu2,actual_Dmax,reference_Dmax\n";
    guards<<"case,API,actual_invalid,rejected,covered_state_unchanged\n";
    cache<<"geometry,case,actual_speed,reference_speed,speed_budget,wave,pore,old_bound,new_bound,passed\n";
    requests<<"case,old_bound,new_bound,current,fixed,DtMin,rejected,expected_reject,selected,signed_fixed_error,physical_unchanged\n";
    LawHostGuards(guards,total);
    {Patch patch(false);patch.LawFields(false,rows,summary,scale,guards,total);}
    {Patch patch(true);patch.LawFields(true,rows,summary,scale,guards,total);}
    LawCachePeriodic(cache,requests,total);
    LawPeriodic(out,total);
    for(auto* stream:{&rows,&summary,&scale,&guards,&cache,&requests}){stream->flush();Need(bool(*stream),"Variable component output incomplete");}
    Need(total.patchcases==16&&total.patchrows==144&&total.periodiccases==2&&total.periodicrows==1920&&total.directrate==26&&total.hostrate==7
      &&total.uniforms==4&&total.guards==11&&total.cachecases==5&&total.requests==8&&total.corners>0,"Variable component declared coverage incomplete");
    std::ofstream done(out/"perm_completion.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"stage\":\"upl_gpu_perm_component_r1\",\"original_constant_suite_retained\":true,\"original_completion_stage\":\"upl_gpu_darcy_component_r3\""
      <<",\"law_patch_cases\":"<<total.patchcases<<",\"law_patch_rows\":"<<total.patchrows<<",\"law_periodic_cases\":"<<total.periodiccases<<",\"law_periodic_rows\":"<<total.periodicrows
      <<",\"direct_rate_kernel_calls\":"<<total.directrate<<",\"actual_host_rate_calls\":"<<total.hostrate<<",\"uniform_scale_cases\":"<<total.uniforms<<",\"guard_cases\":"<<total.guards
      <<",\"cache_cases\":"<<total.cachecases<<",\"actual_gradient_DtVariable_cases\":"<<total.requests<<",\"corner_witnesses\":"<<total.corners
      <<",\"max_rate_reference_error_pa_s\":"<<total.maxerror<<",\"max_rate_error_over_budget\":"<<total.maxratio<<",\"max_speed_reference_error_m_s\":"<<total.maxspeederror<<",\"max_speed_error_over_budget\":"<<total.maxspeedratio
      <<",\"ki_GJ_chain_are_independent_reference_not_native_output\":true,\"actual_rate_speed_scales_measured\":true,\"native_periodic_host_component_not_Run\":true"
      <<",\"actual_ComputeStep_Sym_called\":false,\"completed_physical_steps\":0,\"public_GPU_dynamic_accepted\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Variable completion output failed");
  }
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Initialize(cfg,log);const fs::path out(cfg->DirOut);Totals total;PrefixOwners(out,total);Periodic(out,total);Time(out,total);
    std::ofstream rates(out/"patch_rates.csv"),summary(out/"patch_summary.csv");rates<<std::setprecision(17);summary<<std::setprecision(17);
    rates<<"field,slot,id,actual,reference,error,budget,error_over_budget,pressure_source,acceleration_source\n";summary<<"geometry,field,rows,max_pressure_source,max_acceleration_source\n";
    {Patch patch(false);patch.Fields(false,rates,summary,total);}{Patch patch(true);patch.Fields(true,rates,summary,total);}
    rates.flush();summary.flush();Need(bool(rates)&&bool(summary),"Patch diagnostics incomplete");
    int device=0;Cu(cudaGetDevice(&device));cudaDeviceProp props{};Cu(cudaGetDeviceProperties(&props,device));
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gpu_darcy_component_r3\",\"prefix_stage_cases\":"<<total.prefix<<",\"owner_negative_cases\":"<<total.ownernegative
      <<",\"finite_patch_cases\":"<<total.patchcases<<",\"finite_patch_rate_rows\":"<<total.patchrows<<",\"actual_host_periodic_cases\":"<<total.periodiccases<<",\"actual_host_periodic_rate_rows\":"<<total.periodicrows<<",\"corner_clone_witnesses\":"<<total.corners
      <<",\"class_scale_cases\":"<<total.scales<<",\"positive_k_domain_rejections\":"<<total.domain<<",\"actual_DtVariable_cases\":"<<total.requests<<",\"max_rate_reference_error_pa_s\":"<<total.maxerror<<",\"max_error_over_budget\":"<<total.ratio
      <<",\"actual_private_rate_kernel\":true,\"actual_host_owner_and_rate_helpers\":true,\"independent_all_particle_reference\":true,\"kernel_float_factor_budget_predeclared\":true,\"full_rate_overwrite\":true,\"actual_LoadConfig_ConfigDomain_InitRunGpu\":true,\"actual_ComputeStep_Sym_called\":false,\"completed_physical_steps\":0,\"public_GPU_dynamic_mode\":false,\"variable_k_tested\":false,\"physical_acceptance\":false,\"device_name\":\""<<props.name<<"\"}\n";
    done.flush();Need(bool(done),"Completion output failed");
    VariableSuite(out);
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
