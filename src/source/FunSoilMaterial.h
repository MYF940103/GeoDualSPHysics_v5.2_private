// Experimental fixed-phi DP_PS radial return. Legacy fast material remains the default.
// Coefficients/root/tensor use double; material parameters and persistent kappa remain float.
#pragma once
#include "DualSphDef.h"
#include <cmath>
#if defined(__CUDACC__)
#define FSOIL_HD __host__ __device__
#else
#define FSOIL_HD
#endif
namespace fsoil {
struct Stress { double xx,yy,zz,xy,yz,xz; };
struct State { Stress stress; float kappa; };
struct Material {
  // phi and psi0 are float radians; K/G/cohesion are Pa, decay factors are per kappa.
  float bulk,shear,phi; // phi is fixed throughout a return; no n_phi/MC/3D branch.
  float cohesion_peak,cohesion_residual,cohesion_decay,psi0,psi_decay;
};
enum class Status : unsigned { Invalid,Elastic,Radial,ApexNeeded,NonConverged };
struct Result {
  State state; Status status;
  double kappa_continuous,lambda,trial_yield,root_residual,root_budget,minus_dF_dlambda;
  unsigned iterations;
};
FSOIL_HD inline bool Finite(double x){
#if defined(__CUDA_ARCH__)
  return isfinite(x);
#else
  return std::isfinite(x);
#endif
}
FSOIL_HD inline bool Finite(const Stress& s){
  return Finite(s.xx)&&Finite(s.yy)&&Finite(s.zz)&&Finite(s.xy)&&Finite(s.yz)&&Finite(s.xz);
}
FSOIL_HD inline double Max(double a,double b){return a>b?a:b;}
FSOIL_HD inline bool CommitAllowed(Status s){return s==Status::Elastic||s==Status::Radial;}
struct Invariants { double I,q; };
FSOIL_HD inline Invariants Invariant(const Stress& s){
  const double I=s.xx+s.yy+s.zz,m=I/3.;
  return {I,::sqrt(.5*((s.xx-m)*(s.xx-m)+(s.yy-m)*(s.yy-m)+(s.zz-m)*(s.zz-m)+2.*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)))};
}
struct Coeff { double a,kc,b,fk,bk; };
FSOIL_HD inline Coeff At(const Material& m,double k){
  const double t=::tan(double(m.phi)),den=::sqrt(9.+12.*t*t);
  const double coh=double(m.cohesion_residual)+(double(m.cohesion_peak)-m.cohesion_residual)*::exp(-double(m.cohesion_decay)*k);
  const double psi=double(m.psi0)*::exp(-double(m.psi_decay)*k),tp=::tan(psi),dp=9.+12.*tp*tp;
  return {t/den,3.*coh/den,tp/::sqrt(dp),3.*double(m.cohesion_decay)*(coh-m.cohesion_residual)/den,
    (-double(m.psi_decay)*psi)*9.*(1.+tp*tp)/::pow(dp,1.5)};
}
struct Evaluation { double f,df,I,k; };
FSOIL_HD inline Evaluation Evaluate(const Material& m,const Invariants& tr,float old,double h,double l){
  const double k=double(old)+h*l;const Coeff c=At(m,k);
  const double I=tr.I-9.*double(m.bulk)*c.b*l;
  return {tr.q-double(m.shear)*l+c.a*I-c.kc,
    -double(m.shear)-9.*double(m.bulk)*c.a*(c.b+l*c.bk*h)+c.fk*h,I,k};
}
// Input is const; failures return its unchanged state. Only CommitAllowed authorizes a caller write.
FSOIL_HD inline Result Return(const State& input,const Material& m){
  Result r{};r.state=input;r.status=Status::Invalid;r.kappa_continuous=double(input.kappa);
  if(!Finite(input.stress)||!Finite(input.kappa)||input.kappa<0.f
    || !Finite(m.bulk)||!Finite(m.shear)||!Finite(m.phi)||!Finite(m.cohesion_peak)
    || !Finite(m.cohesion_residual)||!Finite(m.cohesion_decay)||!Finite(m.psi0)||!Finite(m.psi_decay)
    || !(m.bulk>0.f&&m.shear>0.f&&m.phi>0.f&&double(m.phi)<1.57079632679489661923)
    || m.cohesion_residual<0.f||m.cohesion_peak<m.cohesion_residual||m.cohesion_decay<0.f
    || m.psi_decay<0.f||!(::fabs(double(m.psi0))<1.57079632679489661923))return r;
  const Invariants tr=Invariant(input.stress);const Coeff co=At(m,double(input.kappa));
  const double ft=tr.q+co.a*tr.I-co.kc;r.trial_yield=ft;
  if(!(Finite(tr.I)&&Finite(tr.q)&&Finite(ft)&&Finite(co.a)&&Finite(co.kc)&&Finite(co.b)&&Finite(co.fk)&&Finite(co.bk)))return r;
  if(ft<1e-5){r.status=Status::Elastic;return r;} // Same tested elastic threshold.
  if(!(tr.q>0.)){r.status=Status::ApexNeeded;return r;}
  const double h=1./::sqrt(3.),A=double(m.shear)+9.*double(m.bulk)*co.a*co.b;
  const double stable=A-co.fk*h;r.minus_dF_dlambda=stable;
  if(!(Finite(stable)&&stable>0.))return r;
  const double limit=tr.q/double(m.shear);const Evaluation endpoint=Evaluate(m,tr,input.kappa,h,limit);
  if(!Finite(endpoint.f))return r;
  if(endpoint.f>0.){r.status=Status::ApexNeeded;return r;} // No crossing q=0/cap invention.
  double lo=0.,hi=limit,l=ft/stable;
  l=l<lo?lo:(l>hi?hi:l);
  r.root_budget=1e-10*Max(Max(1.,::fabs(tr.q)),Max(::fabs(co.a*tr.I),::fabs(co.kc)));
  Evaluation e{};bool converged=false;
  for(unsigned n=0;n<80;n++){
    e=Evaluate(m,tr,input.kappa,h,l);r.iterations=n+1;r.lambda=l;
    r.kappa_continuous=e.k;r.root_residual=e.f;r.minus_dF_dlambda=-e.df;
    if(!(Finite(e.f)&&Finite(e.df)&&Finite(e.I)&&Finite(e.k)&&e.k>=input.kappa&&e.df<0.))return r;
    if(::fabs(e.f)<=r.root_budget){converged=true;break;}
    if(e.f>0.)lo=l;else hi=l;
    const double next=l-e.f/e.df;l=(Finite(next)&&next>lo&&next<hi?next:.5*(lo+hi));
  }
  if(!converged){r.status=Status::NonConverged;return r;}
  const double scale=(tr.q-double(m.shear)*r.lambda)/tr.q;
  if(!(Finite(scale)&&scale>=0.&&scale<=1.))return r; // No numerical clipping.
  const double mean=e.I/3.,oldmean=tr.I/3.;
  const Stress corrected={mean+scale*(input.stress.xx-oldmean),mean+scale*(input.stress.yy-oldmean),
    mean+scale*(input.stress.zz-oldmean),scale*input.stress.xy,scale*input.stress.yz,scale*input.stress.xz};
  const float saved=float(e.k);
  if(!Finite(corrected)||!Finite(saved)||saved<input.kappa)return r;
  r.state={corrected,saved};r.status=Status::Radial;return r;
}
// Named adapters: native tensor layouts must never be reinterpreted as Stress.
FSOIL_HD inline Material Parameters(const StSoilCte& c){
  return {c.ModulusK,c.ModulusG,c.phi,c.coh,c.coh_r,c.n_coh,c.dlt,c.psiDecay};
}
inline Status ReturnPlaneStrain(const tsymatrix3d& trial,float old,const StSoilCte& c,
  tsymatrix3d& corrected,float& kappa){
  const State input={{trial.xx,trial.yy,trial.zz,trial.xy,trial.yz,trial.xz},old};
  const Result r=Return(input,Parameters(c));
  if(CommitAllowed(r.status)){
    corrected.xx=r.state.stress.xx;corrected.yy=r.state.stress.yy;corrected.zz=r.state.stress.zz;
    corrected.xy=r.state.stress.xy;corrected.yz=r.state.stress.yz;corrected.xz=r.state.stress.xz;
    kappa=r.state.kappa;
  }
  return r.status;
}
#if defined(__CUDACC__)
__device__ inline Status ReturnPlaneStrain(const double2& a,const double2& b,const double2& c,
  float old,const StSoilCte& parameters,double2& oa,double2& ob,double2& oc,float& kappa){
  const State input={{a.x,b.y,c.y,a.y,c.x,b.x},old};
  const Result r=Return(input,Parameters(parameters));
  if(CommitAllowed(r.status)){
    oa=make_double2(r.state.stress.xx,r.state.stress.xy);
    ob=make_double2(r.state.stress.xz,r.state.stress.yy);
    oc=make_double2(r.state.stress.yz,r.state.stress.zz);kappa=r.state.kappa;
  }
  return r.status;
}
#endif
} // namespace fsoil
#undef FSOIL_HD
