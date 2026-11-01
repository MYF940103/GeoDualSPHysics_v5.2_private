// Frozen mirror images only. No JSph object, production dynamic-rate call, or physical solver.
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>
using V=std::array<double,3>;
using M=std::array<V,3>;
static void Need(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
static V Add(V a,const V& b){for(unsigned i=0;i<3;i++)a[i]+=b[i];return a;}
static V Sub(V a,const V& b){for(unsigned i=0;i<3;i++)a[i]-=b[i];return a;}
static V Scale(V a,double s){for(double& x:a)x*=s;return a;}
static double Dot(const V& a,const V& b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static double Norm(const V& a){return sqrt(Dot(a,a));}
static V Unit(V a){return Scale(a,1/Norm(a));}
static V Cross(const V& a,const V& b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
static V F32(V a){for(double& x:a)x=double(float(x));return a;}
static V Reflect(const V& a,const V& n){return Sub(a,Scale(n,2*Dot(a,n)));}
static V Mul(const M& a,const V& b){return {Dot(a[0],b),Dot(a[1],b),Dot(a[2],b)};}
static M Mul(const M& a,const M& b){M c{};for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)for(unsigned k=0;k<3;k++)c[i][j]+=a[i][k]*b[k][j];return c;}
static double Inf(const M& a){double q=0;for(const V& r:a)q=(std::max)(q,fabs(r[0])+fabs(r[1])+fabs(r[2]));return q;}
static double Diff(const M& a,const M& b){double q=0;for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)q=(std::max)(q,fabs(a[i][j]-b[i][j]));return q;}
static M Identity(bool two){M a{};a[0][0]=a[2][2]=1;if(!two)a[1][1]=1;return a;}
static M Reflection(const V& n){M a=Identity(false);for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)a[i][j]-=2*n[i]*n[j];return a;}
static M Inverse(const M& a,bool two){
  if(two){const double d=a[0][0]*a[2][2]-a[0][2]*a[2][0];Need(d>0,"Singular 2D moment");M c{};c[0][0]=a[2][2]/d;c[0][2]=-a[0][2]/d;c[2][0]=-a[2][0]/d;c[2][2]=a[0][0]/d;return c;}
  const tmatrix3d m={a[0][0],a[0][1],a[0][2],a[1][0],a[1][1],a[1][2],a[2][0],a[2][1],a[2][2]};
  const double d=fmath::Determinant3x3(m);Need(d>0,"Singular 3D moment");const auto c=fmath::InverseMatrix3x3(m,d);
  return {{{c.a11,c.a12,c.a13},{c.a21,c.a22,c.a23},{c.a31,c.a32,c.a33}}};
}
static constexpr double Dp=1./64.,Rhow=1000.,Rho0=2048.,Kw=67108864.,N0=.25;
static constexpr double Eps=DBL_EPSILON,EpsF=FLT_EPSILON,RotationTol=64*EpsF+32768*Eps;
struct Node{V x{},ace{},wrong{};double j=1,v=0,ideal=0,p=0,cond=0;M moment{},c{};unsigned owner=0;bool ghost=false;};
struct Cloud{
  bool two;V normal,tangent,gravity;M q;unsigned native;std::vector<Node> points;std::vector<unsigned> probes;
  double h=double(float(1.8*Dp));float hf=float(h),support=float(2*h),support2=support*support,eta2=float((h*.1)*(h*.1));
  StKWendlandCte kernel;
  Cloud(bool d,unsigned rotation,unsigned disorder,unsigned jmode):two(d),kernel(fsph::GetKernelWendland_Ctes(d,h)){
    normal=(two?(rotation?V{.6,0,.8}:V{1,0,0}):(rotation?Unit(V{2,1,2}):V{1,0,0}));
    tangent=(two?V{-normal[2],0,normal[0]}:(rotation?Unit(Cross(normal,V{0,0,1})):V{0,1,0}));
    const V second=Cross(normal,tangent);gravity=(two?V{-4,0,-8}:V{-4,2,-8});q=Reflection(normal);
    Need(fabs(Dot(normal,gravity))>1&&fabs(Dot(normal,tangent))<32*Eps,"Degenerate normal/tangent gravity test");
    const double v0=(two?Dp*Dp:Dp*Dp*Dp);uint32_t seed=0x71c3a591u;
    const auto jitter=[&](){seed=1664525u*seed+1013904223u;return disorder?(.05*Dp*(2.*double(seed)/4294967295.-1.)):0.;};
    for(int s=0;s<6;s++)for(int u=-4;u<=4;u++)for(int v=(two?0:-4);v<=(two?0:4);v++){
      const double sn=(s+.5)*Dp+jitter(),tn=u*Dp+jitter(),bn=(two?0:v*Dp+jitter());Node a;
      a.x=Add(Add(Scale(normal,sn),Scale(tangent,tn)),Scale(second,bn));a.owner=unsigned(points.size());
      if(jmode==1)a.j=1.005;
      if(jmode==2)a.j=1.+.004*sin(2*acos(-1.)*sn/(6*Dp))*cos(acos(-1.)*tn/(4.5*Dp))*(two?1.:cos(acos(-1.)*bn/(4.5*Dp)));
      a.v=v0*a.j;const double n=1.-(1.-N0)/a.j,rho=Rhow+(Rho0-Rhow)/a.j;
      Need(n>0&&n<1&&rho>0&&fabs((1-n)*a.j-(1-N0))<=5e-13,"Invalid frozen saturated ledger");
      if(s<3&&u==0&&v==0)probes.push_back(a.owner);points.push_back(a);
    }
    native=unsigned(points.size());Need(probes.size()==3,"Wrong probe set");
    for(unsigned i=0;i<native;i++){Node a=points[i];a.x=Reflect(a.x,normal);a.ghost=true;points.push_back(a);}
    for(unsigned i=0;i<native;i++){points[i].moment=Moment(i);points[i].c=Inverse(points[i].moment,two);SetCondition(i,false);}
    for(unsigned i=native;i<points.size();i++){
      auto& a=points[i];a.moment=Moment(i);a.c=Mul(Mul(q,points[a.owner].c),q);SetCondition(i,true);
      const M direct=Inverse(a.moment,two);
      Need(Diff(a.c,direct)<=RotationTol*a.cond*(std::max)({1.,Inf(a.c),Inf(direct)}),"Mapped C differs from independently inverted ghost moment");
    }
  }
  bool Gradient(unsigned i,unsigned j,V& d,V& g,double& rr)const{
    d=Sub(points[i].x,points[j].x);rr=Dot(d,d);if(rr>double(support2)||rr<ALMOSTZERO)return false;
    const double fac=fsph::GetKernelWendland_Fac(kernel,hf,float(rr));g=Scale(d,fac);return true;
  }
  M Moment(unsigned i)const{
    // ComputeFS uses float rr2 for support; the later dynamic helper uses double rr2.
    M a{};for(unsigned j=0;j<points.size();j++){const V d=Sub(points[i].x,points[j].x);const float rr=float(Dot(d,d));if(rr>support2||rr<ALMOSTZERO)continue;
      const V g=Scale(d,double(fsph::GetKernelWendland_Fac(kernel,hf,rr)));
      for(unsigned r=0;r<3;r++)for(unsigned c=0;c<3;c++)a[r][c]-=d[r]*g[c]*points[j].v;
    }return a;
  }
  void SetCondition(unsigned i,bool ghost){auto& a=points[i];a.cond=(std::max)(1.,Inf(a.c)*Inf(a.moment));Need(std::isfinite(a.cond),"Nonfinite C condition scale");
    Need(Diff(Mul(a.c,a.moment),Identity(two))<=(ghost?RotationTol:32768*Eps)*a.cond,"C first-moment residual failed");
  }
  void Fields(const V& a0,const V& grad){
    for(unsigned i=0;i<native;i++){auto& a=points[i];a.ideal=4096+Dot(grad,a.x);a.p=double(float(a.ideal));a.ace=F32(Sub(a0,gravity));}
    for(unsigned i=native;i<points.size();i++){auto& a=points[i];const auto& owner=points[a.owner];a.ideal=4096+Dot(grad,a.x);
      a.p=double(float(owner.p+Rhow*Dot(gravity,Sub(a.x,owner.x))));
      a.ace=F32(Sub(Reflect(Add(owner.ace,gravity),normal),gravity));a.wrong=F32(Reflect(owner.ace,normal));
    }
  }
};
struct Eval{V gp{},gpd{},rawpd{},flux{};double ls=0,lsd=0,da=0,da0=0,daw=0,rate=0,rate0=0,ratew=0,bg=0,bgd=0,bl=0,bld=0,bda=0,bq=0,br=0,cwrong_ratio=0;};
static Eval Evaluate(const Cloud& cloud,unsigned i,const V& grad,const V& a0,double E,double EA,double k,double gamma){
  const auto& p=cloud.points[i];Eval out;V lx{};double lp=0,lpd=0,sg=0,ws=0,gs=0,lps=0,das=0;
  for(unsigned j=0;j<cloud.points.size();j++){
    V d,g;double rr;if(!cloud.Gradient(i,j,d,g,rr))continue;const auto& b=cloud.points[j];
    const V gi=Mul(p.c,g),gj=Mul(b.c,g);const double w=b.v*Dot(d,Add(gi,gj))/(rr+double(cloud.eta2));
    const double dp=p.p-b.p,dpd=p.ideal-b.ideal;lp+=w*dp;lpd+=w*dpd;lx=Add(lx,Scale(d,w));
    out.gp=Sub(out.gp,Scale(gi,b.v*dp));out.gpd=Sub(out.gpd,Scale(gi,b.v*dpd));out.rawpd=Sub(out.rawpd,Scale(g,b.v*dpd));
    out.da+=b.v*Dot(Sub(b.ace,p.ace),gi);
    const V a0i=(p.ghost?V{}:p.ace),a0j=(b.ghost?V{}:b.ace),awi=(p.ghost?p.wrong:p.ace),awj=(b.ghost?b.wrong:b.ace);
    out.da0+=b.v*Dot(Sub(a0j,a0i),gi);out.daw+=b.v*Dot(Sub(awj,awi),gi);
    sg+=b.v*Norm(gi);ws+=fabs(w);gs+=b.v*fabs(dpd)*Norm(gi);lps+=fabs(w*dpd);das+=b.v*Norm(gi)*(Norm(p.ace)+Norm(b.ace));
  }
  out.ls=lp-Dot(out.gp,lx);out.lsd=lpd-Dot(out.gpd,lx);
  out.bgd=RotationTol*p.cond*Norm(grad)+4096*Eps*(std::max)(1.,gs);out.bg=2*E*sg+out.bgd;
  out.bda=2*EA*sg+4096*Eps*(std::max)(1.,das);
  const double arithmetic=4096*Eps*(std::max)(1.,lps+Norm(grad)*Norm(lx));
  out.bl=2*E*ws+out.bg*Norm(lx)+arithmetic;out.bld=out.bgd*Norm(lx)+arithmetic;
  const double n=1.-(1.-N0)/p.j,gain=Kw/n*k/gamma;
  out.rate=double(float(gain*(out.ls+Rhow*out.da)));out.rate0=double(float(gain*(out.ls+Rhow*out.da0)));out.ratew=double(float(gain*(out.ls+Rhow*out.daw)));
  out.br=gain*(out.bl+Rhow*out.bda);out.br+=2*EpsF*(std::max)(1.,out.br);
  out.flux=Scale(Add(out.gp,Scale(p.ace,Rhow)),-k/gamma);out.bq=k/gamma*(out.bg+Rhow*EA);
  const V exact=Scale(Sub(grad,Scale(Sub(cloud.gravity,a0),Rhow)),-k/gamma);
  Need(Norm(Sub(out.gp,grad))<=out.bg&&Norm(Sub(out.gpd,grad))<=out.bgd,"Affine corrected gradient rounding bound failed");
  Need(fabs(out.ls)<=out.bl&&fabs(out.lsd)<=out.bld&&fabs(out.da)<=out.bda,"Lstar/divAce prior bound failed");
  Need(std::isfinite(out.rate)&&fabs(out.rate)<=out.br&&Norm(Sub(out.flux,exact))<=out.bq,"Complete-rate or actual flux bound failed");
  if(p.ghost)out.cwrong_ratio=Norm(Sub(Mul(cloud.points[p.owner].c,out.rawpd),grad))/out.bgd;
  return out;
}
int main(int argc,char** argv){try{
  Need(argc==2,"Use one fresh output directory");const std::filesystem::path dir=argv[1];
  const auto cases=dir/"cases.csv",probes=dir/"probes.csv",done=dir/"complete.json";
  Need(!std::filesystem::exists(cases)&&!std::filesystem::exists(probes)&&!std::filesystem::exists(done),"Retained artifacts protected");
  std::ofstream cs(cases),ps(probes);cs<<std::setprecision(17);ps<<std::setprecision(17);
  cs<<"case,dimension,rotation,disorder,Jmode,fluxcase,native,normal_gravity,pressure_rounding_E,acceleration_rounding_EA,max_gradient_error,max_gradient_bound,max_Lstar,max_Lstar_bound,max_divAce,max_divAce_bound,max_abs_rate,max_rate_bound,max_q_error,max_q_bound,max_face_qn,min_negative_zero_qn,min_negative_wrong_g_qn,max_C_reflection_change,max_wrong_C_gradient_bound_ratio\n";
  ps<<"case,probe,depth,native_qx,native_qy,native_qz,ghost_qx,ghost_qy,ghost_qz,face_qx,face_qy,face_qz,analytic_qx,analytic_qy,analytic_qz,native_qn,ghost_qn,face_qn,face_bound,negative_zero_native_qn,negative_zero_ghost_qn,negative_zero_face_qn,negative_wrong_g_native_qn,negative_wrong_g_ghost_qn,negative_wrong_g_face_qn,native_rate,ghost_rate,negative_zero_native_rate,negative_wrong_g_native_rate,native_rate_bound,ghost_rate_bound,wrong_C_gradient_bound_ratio\n";
  unsigned id=0,pairs=0,cwrong=0;double maxratio=0;
  for(unsigned dim:{2u,3u})for(unsigned rot:{0u,1u})for(unsigned dis:{0u,1u})for(unsigned jm:{0u,1u,2u}){
    Cloud cloud(dim==2,rot,dis,jm);
    for(unsigned flow:{0u,1u}){
      const V a0=Scale(cloud.tangent,flow?.25:0.),grad=Add(Scale(Sub(cloud.gravity,a0),Rhow),Scale(cloud.tangent,flow?1024.:0.));cloud.Fields(a0,grad);
      double pmax=1;for(const auto& p:cloud.points)pmax=(std::max)(pmax,fabs(p.ideal));const double E=2*EpsF*pmax,EA=4*EpsF*(std::max)({1.,Norm(cloud.gravity),Norm(Sub(a0,cloud.gravity))});
      const double k=double(float(.0001)),gamma=Rhow*Norm(cloud.gravity);const V exact=Scale(cloud.tangent,-k/gamma*(flow?1024.:0.));
      double eg=0,bg=0,ls=0,bl=0,da=0,bda=0,rate=0,br=0,eq=0,bq=0,fqn=0,neg0=DBL_MAX,negw=DBL_MAX,crefl=0,cratio=0;
      for(unsigned probe:cloud.probes){
        const unsigned ghost=probe+cloud.native;const auto ni=Evaluate(cloud,probe,grad,a0,E,EA,k,gamma),gi=Evaluate(cloud,ghost,grad,a0,E,EA,k,gamma);
        const V face=Scale(Add(ni.flux,gi.flux),.5);const double fb=.5*(ni.bq+gi.bq);
        const V ghost0=Scale(gi.gp,-k/gamma),ghostw=Scale(Add(gi.gp,Scale(cloud.points[ghost].wrong,Rhow)),-k/gamma);
        const double bad0=Dot(Scale(Add(ni.flux,ghost0),.5),cloud.normal),badw=Dot(Scale(Add(ni.flux,ghostw),.5),cloud.normal);
        Need(fabs(Dot(face,cloud.normal))<=fb&&Norm(Sub(face,exact))<=fb,"Declared face-average flux bound failed");
        Need(fabs(bad0)>fb&&fabs(badw)>fb,"Acceleration negative diagnostic not discriminated");
        if(flow)for(const auto& value:std::array<std::pair<V,double>,3>{{{ni.flux,ni.bq},{gi.flux,gi.bq},{face,fb}}})
          Need(value.second<.01*Norm(exact)&&fabs(Dot(value.first,cloud.tangent))>.5*Norm(exact),"Tangential flux check vacuous or suppressed");
        for(const auto& e:{ni,gi}){eg=(std::max)(eg,Norm(Sub(e.gp,grad)));bg=(std::max)(bg,e.bg);ls=(std::max)(ls,fabs(e.ls));bl=(std::max)(bl,e.bl);da=(std::max)(da,fabs(e.da));bda=(std::max)(bda,e.bda);rate=(std::max)(rate,fabs(e.rate));br=(std::max)(br,e.br);eq=(std::max)(eq,Norm(Sub(e.flux,exact)));bq=(std::max)(bq,e.bq);}
        fqn=(std::max)(fqn,fabs(Dot(face,cloud.normal)));neg0=(std::min)(neg0,fabs(bad0));negw=(std::min)(negw,fabs(badw));
        crefl=(std::max)(crefl,Diff(cloud.points[ghost].c,cloud.points[probe].c));cratio=(std::max)(cratio,gi.cwrong_ratio);if(gi.cwrong_ratio>1)cwrong++;
        ps<<id<<','<<probe<<','<<Dot(cloud.points[probe].x,cloud.normal);for(const V& v:{ni.flux,gi.flux,face,exact})for(double z:v)ps<<','<<z;
        ps<<','<<Dot(ni.flux,cloud.normal)<<','<<Dot(gi.flux,cloud.normal)<<','<<Dot(face,cloud.normal)<<','<<fb
          <<','<<Dot(ni.flux,cloud.normal)<<','<<Dot(ghost0,cloud.normal)<<','<<bad0<<','<<Dot(ni.flux,cloud.normal)<<','<<Dot(ghostw,cloud.normal)<<','<<badw
          <<','<<ni.rate<<','<<gi.rate<<','<<ni.rate0<<','<<ni.ratew<<','<<ni.br<<','<<gi.br<<','<<gi.cwrong_ratio<<'\n';pairs++;
      }
      maxratio=(std::max)(maxratio,cratio);cs<<id<<','<<dim<<','<<rot<<','<<dis<<','<<jm<<','<<flow<<','<<cloud.native<<','<<Dot(cloud.gravity,cloud.normal)<<','<<E<<','<<EA<<','<<eg<<','<<bg<<','<<ls<<','<<bl<<','<<da<<','<<bda<<','<<rate<<','<<br<<','<<eq<<','<<bq<<','<<fqn<<','<<neg0<<','<<negw<<','<<crefl<<','<<cratio<<'\n';id++;
    }
  }
  Need(id==48&&pairs==144&&cwrong>0,"Incomplete case set or matrix-negative discrimination absent");cs.flush();ps.flush();Need(bool(cs)&&bool(ps),"CSV write failed");
  std::ofstream json(done);json<<std::setprecision(17)<<"{\"passed\":true,\"cases\":"<<id<<",\"probe_pairs\":"<<pairs<<",\"native_and_ghost_evaluations\":"<<2*pairs<<",\"wrong_C_detected_probes\":"<<cwrong<<",\"max_wrong_C_gradient_bound_ratio\":"<<maxratio<<",\"operator_transcription_only\":true,\"production_dynamic_function_called\":false,\"project_solver_started\":false,\"actual_boundary_or_mdbc_acceptance\":false,\"physical_acceptance\":false}\n";json.flush();Need(bool(json),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
