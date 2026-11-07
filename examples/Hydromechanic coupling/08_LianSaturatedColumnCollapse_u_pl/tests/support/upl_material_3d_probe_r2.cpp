// Material points only: new candidate vs independent equations and current DP_PS.
#include "upl_material_3d_candidate_r1.h"
#include "FunSoilMaterial.h"
#include "JAppInfo.h"
#include <algorithm>
#include <cfloat>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
JAppInfo AppInfo("UplMaterial3DProbe","r1","material points only");
void UpdateDPvars(float&,float&,float&,float,float,float,float,float,float,float,float,TpDPCtes);
void Updatedfdk(double&,float,float,float,float,float,float,float,float,double,TpDPCtes);
namespace c=fsoil3d_candidate_r1;namespace fs=std::filesystem;
constexpr double Pi=3.14159265358979323846,Eps=DBL_EPSILON;
struct Inv{double I,q;};struct Ref{double a,ac,b;};
static void Need(bool yes,const char* message){if(!yes)throw std::runtime_error(message);}
template<class T> static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static bool Same(const c::State& a,const c::State& b){
  return Bits(a.stress.xx,b.stress.xx)&&Bits(a.stress.yy,b.stress.yy)&&Bits(a.stress.zz,b.stress.zz)
    &&Bits(a.stress.xy,b.stress.xy)&&Bits(a.stress.yz,b.stress.yz)&&Bits(a.stress.xz,b.stress.xz)&&Bits(a.kappa,b.kappa);
}
static Inv ReferenceInvariant(const c::Stress& s){return {s.xx+s.yy+s.zz,std::sqrt(((s.xx-s.yy)*(s.xx-s.yy)
  +(s.yy-s.zz)*(s.yy-s.zz)+(s.zz-s.xx)*(s.zz-s.xx))/6.+s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)};}
static double Coh(const c::Material& m,double k){return m.cohesion_residual+(double(m.cohesion_peak)-m.cohesion_residual)*std::exp(-double(m.cohesion_decay)*k);}
static Ref Reference(const c::Material& m,double k,TpDPCtes fit){
  const double p=m.phi,psi=double(m.psi0)*std::exp(-double(m.psi_decay)*k);
  if(fit==DP_PS){const double t=std::tan(p),u=std::tan(psi);return {t/std::sqrt(9.+12.*t*t),3./std::sqrt(9.+12.*t*t),u/std::sqrt(9.+12.*u*u)};}
  const double sign=fit==DP_C?-1.:1.;return {2.*std::sin(p)/(std::sqrt(3.)*(3.+sign*std::sin(p))),
    6.*std::cos(p)/(std::sqrt(3.)*(3.+sign*std::sin(p))),2.*std::sin(psi)/(std::sqrt(3.)*(3.+sign*std::sin(psi)))};
}
static double Yield(const c::Stress& s,const c::Material& m,double k,TpDPCtes fit){const auto v=ReferenceInvariant(s);const auto a=Reference(m,k,fit);return v.q+a.a*v.I-a.ac*Coh(m,k);}
static c::Stress Scale(c::Stress s,double f){return {f*s.xx,f*s.yy,f*s.zz,f*s.xy,f*s.yz,f*s.xz};}
static c::Stress Rotate(const c::Stress& s){
  const double Q[3][3]={{-2./3.,2./15.,11./15.},{2./3.,-1./3.,2./3.},{1./3.,14./15.,2./15.}};
  const double A[3][3]={{s.xx,s.xy,s.xz},{s.xy,s.yy,s.yz},{s.xz,s.yz,s.zz}};double B[3][3]={};
  for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)for(int l=0;l<3;l++)B[i][j]+=Q[i][k]*A[k][l]*Q[j][l];
  return {B[0][0],B[1][1],B[2][2],B[0][1],B[1][2],B[0][2]};
}
static double StressGap(const c::Stress& a,const c::Stress& b){return (std::max)({std::fabs(a.xx-b.xx),std::fabs(a.yy-b.yy),std::fabs(a.zz-b.zz),std::fabs(a.xy-b.xy),std::fabs(a.yz-b.yz),std::fabs(a.xz-b.xz)});}
static void ExactPS(const c::State& p,const c::Material& m,const c::Result& r){
  const fsoil::State x={{p.stress.xx,p.stress.yy,p.stress.zz,p.stress.xy,p.stress.yz,p.stress.xz},p.kappa};
  const fsoil::Material a={m.bulk,m.shear,m.phi,m.cohesion_peak,m.cohesion_residual,m.cohesion_decay,m.psi0,m.psi_decay};
  const auto old=fsoil::Return(x,a);const c::State state={{old.state.stress.xx,old.state.stress.yy,old.state.stress.zz,old.state.stress.xy,old.state.stress.yz,old.state.stress.xz},old.state.kappa};
  Need(Same(state,r.state)&&unsigned(old.status)==unsigned(r.status)&&old.iterations==r.iterations
    &&Bits(old.kappa_continuous,r.kappa_continuous)&&Bits(old.lambda,r.lambda)&&Bits(old.trial_yield,r.trial_yield)
    &&Bits(old.root_residual,r.root_residual)&&Bits(old.root_budget,r.root_budget)&&Bits(old.minus_dF_dlambda,r.minus_dF_dlambda),"DP_PS candidate differs from actual current shared core");
}
// Central differences use independent equations, with predeclared analytic third-
// derivative bounds (Dpsi>=2) plus 16eps propagated evaluation/subtraction error.
static void Derivatives(const c::State& p,const c::Material& m,const c::Result& r,TpDPCtes fit,double& rf,double& rb,double& rl){
  const double k=r.kappa_continuous,h=1e-5,n=m.cohesion_decay,sf=m.psi_decay;
  const auto a=Reference(m,k,fit);const auto v=ReferenceInvariant(p.stress);const auto coeff=c::At(m,k,fit);
  const double amp=std::fabs(double(m.cohesion_peak)-m.cohesion_residual)*std::exp(-n*(k-h));
  const double fd=(Yield(r.state.stress,m,k+h,fit)-Yield(r.state.stress,m,k-h,fit))/(2.*h);
  const auto vr=ReferenceInvariant(r.state.stress);
  const double fb=a.ac*n*n*n*amp*h*h/6.+16.*Eps*(1.+vr.q+std::fabs(a.a*vr.I)+a.ac*(m.cohesion_residual+amp))/h;
  const double psi=std::fabs(double(m.psi0))*std::exp(-sf*(k-h));
  const double beta3=sf*sf*sf*(4.764*psi*psi*psi+5.199*psi*psi+.867*psi);
  const double bd=(Reference(m,k+h,fit).b-Reference(m,k-h,fit).b)/(2.*h),bb=beta3*h*h/6.+16.*Eps/h;
  const double hk=1./std::sqrt(3.),limit=v.q/m.shear,d=(std::min)(1e-7,.25*(std::min)(r.lambda,limit-r.lambda));
  Need(d>0&&k>h,"Derivative witness is outside the declared smooth radial domain");
  const auto F=[&](double l){const double kk=p.kappa+hk*l;const auto z=Reference(m,kk,fit);return v.q-double(m.shear)*l+z.a*(v.I-9.*m.bulk*z.b*l)-z.ac*Coh(m,kk);};
  const double ld=(F(r.lambda+d)-F(r.lambda-d))/(2.*d),psi2=std::fabs(double(m.psi0))*std::exp(-sf*(k-hk*d));
  const double b2=sf*sf*(1.733*psi2*psi2+.867*psi2),b3=sf*sf*sf*(4.764*psi2*psi2*psi2+5.199*psi2*psi2+.867*psi2);
  const double cmax=std::fabs(double(m.cohesion_peak)-m.cohesion_residual)*std::exp(-n*(k-hk*d));
  const double third=9.*m.bulk*std::fabs(a.a)*(3.*b2*hk*hk+(r.lambda+d)*b3*hk*hk*hk)+a.ac*n*n*n*cmax*hk*hk*hk;
  const double scale=1.+v.q+m.shear*(r.lambda+d)+std::fabs(a.a)*(std::fabs(v.I)+9.*m.bulk/std::sqrt(3.)*(r.lambda+d))+a.ac*(m.cohesion_residual+cmax);
  const double lb=third*d*d/6.+16.*Eps*scale/d;
  const c::Invariants original=c::Invariant(p.stress);const auto e=c::Evaluate(m,original,p.kappa,hk,r.lambda,fit);
  rf=std::fabs(fd-coeff.fk)/fb;rb=std::fabs(bd-coeff.bk)/bb;rl=std::fabs(ld-e.df)/lb;
  Need(rf<=1.&&rb<=1.&&rl<=1.,"Independent coefficient/return finite-difference budget failed");
}
static void Put(std::ostream& out,const c::Stress& s){out<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz;}
int main(int argc,char** argv){unsigned row=0,counts[5]={},exact=0,rotations=0,derivatives=0;double maxyield=0,maxsaved=0,maxfd=0;
  try{
    Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_RESULT_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path())&&fs::create_directory(out),"Fresh output required");
    std::ofstream csv(out/"points.csv");csv<<std::setprecision(17)<<"id,fit,path,psi0_deg,old_kappa,status,input_xx,input_yy,input_zz,input_xy,input_yz,input_xz,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz,saved_kappa,continuous_kappa,lambda,continuous_yield_Pa,saved_yield_Pa,root_budget_Pa,dev_error,trace_error,q_error_Pa,I_error_Pa,tensor_budget_Pa,rotation_checked,rotation_error_Pa,fd_checked,fd_fk_ratio,fd_beta_ratio,fd_Fprime_ratio,legacy_observed,legacy_alpha_delta,legacy_kc_delta_Pa,legacy_beta_delta,legacy_fk_delta_Pa\n";
    const auto point=[&](TpDPCtes fit,const char* path,double degrees,const c::State& p,const c::Material& m,c::Status expected,bool rotate){
      const c::State before=p;const auto r=c::Return(p,m,fit);Need(Same(before,p)&&r.status==expected,"Unexpected status or changed material input");
      if(fit==DP_PS){ExactPS(p,m,r);exact++;}counts[unsigned(r.status)]++;
      double y=0,saved=0,dev=0,trace=0,qe=0,ie=0,tb=0,re=0,rf=0,rb=0,rl=0,la=0,lk=0,lp=0,lf=0;bool fd=false,legacy=false;
      if(!c::CommitAllowed(r.status))Need(Same(p,r.state),"Failure committed state");
      else{
        Need(Bits(r.state.kappa,float(r.kappa_continuous))&&r.state.kappa>=p.kappa,"Float history storage failed");const auto tr=ReferenceInvariant(p.stress);const auto nr=ReferenceInvariant(r.state.stress);const auto a=Reference(m,r.kappa_continuous,fit);
        y=Yield(r.state.stress,m,r.kappa_continuous,fit);saved=Yield(r.state.stress,m,r.state.kappa,fit);tb=8192.*Eps*(std::max)({1.,std::fabs(tr.I),tr.q,std::fabs(nr.I),nr.q});
        if(r.status==c::Status::Elastic)Need(Same(p,r.state)&&y<=1e-5,"Elastic state contract failed");
        else{
          const auto& s=p.stress;const auto& t=r.state.stress;const double dx=s.xx-t.xx,dy=s.yy-t.yy,dz=s.zz-t.zz,mean=(dx+dy+dz)/3.;
          const double dpdev=std::sqrt((2./3.)*((dx-mean)*(dx-mean)+(dy-mean)*(dy-mean)+(dz-mean)*(dz-mean)+2.*((s.xy-t.xy)*(s.xy-t.xy)+(s.yz-t.yz)*(s.yz-t.yz)+(s.xz-t.xz)*(s.xz-t.xz)))/(4.*m.shear*m.shear));
          dev=std::fabs(dpdev-r.lambda/std::sqrt(3.));trace=std::fabs(mean/m.bulk-3.*a.b*r.lambda);qe=std::fabs(nr.q-(tr.q-m.shear*r.lambda));ie=std::fabs(nr.I-(tr.I-9.*m.bulk*a.b*r.lambda));
          Need(r.root_budget>0&&std::fabs(y)<=4.*r.root_budget&&dev<=8192.*Eps&&trace<=8192.*Eps&&qe<=tb&&ie<=tb&&r.minus_dF_dlambda>0,"Original radial consistency/compliance budget failed");
          Need(std::fabs(r.kappa_continuous-(double(p.kappa)+r.lambda/std::sqrt(3.)))<=8192.*Eps,"History increment contract failed");
          maxyield=(std::max)(maxyield,std::fabs(y));maxsaved=(std::max)(maxsaved,std::fabs(saved));
          if(m.cohesion_peak==m.cohesion_residual&&m.psi_decay==0.f){const auto z=Reference(m,p.kappa,fit);const double closed=(tr.q+z.a*tr.I-z.ac*m.cohesion_peak)/(m.shear+9.*m.bulk*z.a*z.b);Need(std::fabs(r.lambda-closed)<=4096.*Eps,"Constant-strength multiplier failed");}
          if(rotate){const auto rotated=c::Return({Rotate(p.stress),p.kappa},m,fit);Need(rotated.status==r.status,"Rotation changed radial status");re=StressGap(rotated.state.stress,Rotate(r.state.stress));Need(re<=tb&&std::fabs(rotated.lambda-r.lambda)<=4096.*Eps,"3D rotation covariance failed");rotations++;}
          if(fit!=DP_PS){Derivatives(p,m,r,fit,rf,rb,rl);fd=true;derivatives++;maxfd=(std::max)({maxfd,rf,rb,rl});}
        }
        if(fit!=DP_PS&&degrees==0.&&p.kappa==.5f&&std::string(path)=="cohesion_and_dilation_decay"){
          float olda=0,oldkc=0,oldb=0;double oldfk=0;const float psi=float(double(m.psi0)*std::exp(-double(m.psi_decay)*p.kappa));
          UpdateDPvars(olda,oldkc,oldb,m.phi,m.phi,0.f,m.cohesion_peak,m.cohesion_residual,m.cohesion_decay,psi,p.kappa,fit);
          Updatedfdk(oldfk,m.phi,m.phi,0.f,m.cohesion_peak,m.cohesion_residual,m.cohesion_decay,psi,p.kappa,tr.I,fit);const auto ca=c::At(m,p.kappa,fit);legacy=true;la=olda-ca.a;lk=oldkc-ca.kc;lp=oldb-ca.b;lf=oldfk-ca.fk;
        }
      }
      csv<<row++<<','<<unsigned(fit)<<','<<path<<','<<degrees<<','<<p.kappa<<','<<unsigned(r.status);Put(csv,p.stress);Put(csv,r.state.stress);
      csv<<','<<r.state.kappa<<','<<r.kappa_continuous<<','<<r.lambda<<','<<y<<','<<saved<<','<<r.root_budget<<','<<dev<<','<<trace<<','<<qe<<','<<ie<<','<<tb<<','<<rotate<<','<<re<<','<<fd<<','<<rf<<','<<rb<<','<<rl<<','<<legacy<<','<<la<<','<<lk<<','<<lp<<','<<lf<<'\n';return r;
    };
    const float E=20000000.f,nu=.33f,K=E/(3.f*(1.f-2.f*nu)),G=E/(2.f*(1.f+nu));const c::Stress trial={-90000.,-120000.,-90000.,90000.,-70000.,80000.};
    for(const auto fit:{DP_PS,DP_C,DP_MC})for(double degrees:{0.,2.5,-5.})for(int path=0;path<2;path++){
      c::Material m={K,G,float(25.*Pi/180.),5000.f,1000.f,5.f,float(degrees*Pi/180.),path==1?.2f:0.f};if(path==0){m.cohesion_residual=m.cohesion_peak;m.cohesion_decay=0.f;}
      const auto r=point(fit,path==0?"constant":"cohesion_and_dilation_decay",degrees,{trial,.5f},m,c::Status::Radial,path==0);
      if(path==1)point(fit,"unload",degrees,{Scale(r.state.stress,.9),r.state.kappa},m,c::Status::Elastic,false);
    }
    const c::Material good={K,G,float(25.*Pi/180.),5000.f,1000.f,5.f,0.f,.2f};
    for(const auto fit:{DP_PS,DP_C,DP_MC}){
      point(fit,"initial_history_radial",0.,{trial,0.f},good,c::Status::Radial,false);
      point(fit,"elastic",0.,{Scale(trial,.001),.5f},good,c::Status::Elastic,false);
      point(fit,"apex",0.,{{1e6,1e6,1e6,0,0,0},0.f},good,c::Status::ApexNeeded,false);
      auto invalid=good;invalid.shear=0;point(fit,"invalid_shear",0.,{trial,0.f},invalid,c::Status::Invalid,false);
    }
    auto nan=trial;nan.xy=std::numeric_limits<double>::quiet_NaN();point(DP_PS,"invalid_nan",0.,{nan,0.f},good,c::Status::Invalid,false);
    point(TpDPCtes(0),"invalid_fit",0.,{trial,0.f},good,c::Status::Invalid,false);
    Need(row==41&&counts[0]==5&&counts[1]==12&&counts[2]==21&&counts[3]==3&&counts[4]==0&&exact==14&&rotations==9&&derivatives==14,"Declared bounded coverage differs");csv.flush();Need(bool(csv),"CSV write failed");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_3d_probe_r2\",\"passed\":true,\"rows\":"<<row<<",\"DP_PS_exact_rows\":"<<exact<<",\"rotation_checks\":"<<rotations<<",\"independent_derivative_sets\":"<<derivatives<<",\"continuous_yield_max_Pa\":"<<maxyield<<",\"saved_float_yield_max_Pa\":"<<maxsaved<<",\"finite_difference_max_ratio\":"<<maxfd<<",\"legacy_coefficients_are_observations_not_double_truth\":true,\"NonConverged_naturally_covered\":false,\"spatial_solver\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
  }catch(const std::exception& e){std::cerr<<"row="<<row<<" : "<<e.what()<<'\n';return 1;}
}
