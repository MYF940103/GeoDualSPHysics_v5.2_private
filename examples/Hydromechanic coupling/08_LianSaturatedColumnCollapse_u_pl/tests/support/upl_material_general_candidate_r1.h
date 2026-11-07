// Test-only general DP coefficients and two-entry radial return candidate.
// No production admission. Non-radial/apex policy remains a separate physical decision.
#pragma once
#include "DualSphDef.h"
#include <cmath>
#include <cfloat>
#if defined(__CUDACC__)
#define FGENERAL_HD __host__ __device__
#else
#define FGENERAL_HD
#endif
namespace fsoil_general_candidate_r1 {
struct Stress{double xx,yy,zz,xy,yz,xz;};
struct State{Stress stress;float kappa;};
struct Material{
  float ModulusK,ModulusG,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi0,sf;
};
struct Coefficients{
  double DP_phi,DP_kc,DP_psi,dDP_phi_dk,dDP_kc_dk,dDP_psi_dk;
};
enum class Status:unsigned{Invalid,Elastic,Radial,ApexNeeded,NonConverged,UnresolvedPath};
struct Result{
  State state;Status status;
  double kappa_continuous,lambda,trial_yield,root_residual,root_budget,minus_dF_dlambda;
  double radial_slope_upper_bound;
  unsigned iterations;
};
FGENERAL_HD inline bool Finite(double x){
#if defined(__CUDA_ARCH__)
  return isfinite(x);
#else
  return std::isfinite(x);
#endif
}
FGENERAL_HD inline bool Finite(const Stress& s){return Finite(s.xx)&&Finite(s.yy)&&Finite(s.zz)&&Finite(s.xy)&&Finite(s.yz)&&Finite(s.xz);}
FGENERAL_HD inline bool Finite(const Coefficients& c){return Finite(c.DP_phi)&&Finite(c.DP_kc)&&Finite(c.DP_psi)&&Finite(c.dDP_phi_dk)&&Finite(c.dDP_kc_dk)&&Finite(c.dDP_psi_dk);}
FGENERAL_HD inline bool CommitAllowed(Status s){return s==Status::Elastic||s==Status::Radial;}
FGENERAL_HD inline double Max(double a,double b){return a>b?a:b;}
FGENERAL_HD inline bool KnownFit(TpDPCtes fit){return fit==DP_PS||fit==DP_C||fit==DP_MC;}
struct Invariants{double I,q;};
FGENERAL_HD inline Invariants GetInvariants(const Stress& s){
  const double I=s.xx+s.yy+s.zz,mean=I/3.;
  return {I,::sqrt(.5*((s.xx-mean)*(s.xx-mean)+(s.yy-mean)*(s.yy-mean)+(s.zz-mean)*(s.zz-mean)+2.*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)))};
}
// Material and fit are validated at the entry. This function depends only on
// kappa; an apex caller can evaluate it at kappa_tip without using radial lambda.
FGENERAL_HD inline Coefficients UpdateDPvars(const Material& m,double kappa,TpDPCtes fit){
  const double phi=m.phi_r+(double(m.phi_p)-m.phi_r)*::exp(-double(m.n_p)*kappa);
  const double coh=m.coh_r+(double(m.coh_p)-m.coh_r)*::exp(-double(m.n_c)*kappa);
  const double psi=double(m.psi0)*::exp(-double(m.sf)*kappa);
  const double dphidk=-double(m.n_p)*(phi-m.phi_r),dcohdk=-double(m.n_c)*(coh-m.coh_r),dpsidk=-double(m.sf)*psi;
  double DP_phi,DP_kc,DP_psi,dalphadphi,dkcdphi,dkcdcoh,dbetadpsi;
  if(fit==DP_PS){
    const double tphi=::tan(phi),sec2=1.+tphi*tphi,den=9.+12.*tphi*tphi,powden=::pow(den,1.5);
    const double tpsi=::tan(psi),denpsi=9.+12.*tpsi*tpsi;
    DP_phi=tphi/::sqrt(den);DP_kc=3.*coh/::sqrt(den);DP_psi=tpsi/::sqrt(denpsi);
    dalphadphi=9.*sec2/powden;dkcdphi=-36.*coh*tphi*sec2/powden;dkcdcoh=3./::sqrt(den);
    dbetadpsi=9.*(1.+tpsi*tpsi)/::pow(denpsi,1.5);
  }
  else{
    const double side=(fit==DP_MC?1.:-1.),root3=::sqrt(3.),sphi=::sin(phi),cphi=::cos(phi),den=3.+side*sphi,denpsi=3.+side*::sin(psi);
    DP_phi=2.*sphi/(root3*den);DP_kc=6.*coh*cphi/(root3*den);DP_psi=2.*::sin(psi)/(root3*denpsi);
    dalphadphi=6.*cphi/(root3*den*den);dkcdphi=6.*coh*(-3.*sphi-side)/(root3*den*den);dkcdcoh=6.*cphi/(root3*den);
    dbetadpsi=6.*::cos(psi)/(root3*denpsi*denpsi);
  }
  return {DP_phi,DP_kc,DP_psi,dalphadphi*dphidk,dkcdphi*dphidk+dkcdcoh*dcohdk,dbetadpsi*dpsidk};
}
FGENERAL_HD inline double Updatedfdk(const Coefficients& DP,double I){return I*DP.dDP_phi_dk-DP.dDP_kc_dk;}
struct Evaluation{double f,df,I,kappa;};
namespace detail{
struct BasicValues{
  Coefficients DP;
  FGENERAL_HD Coefficients operator()(double)const{return DP;}
  FGENERAL_HD double SlopeUpper(const Invariants&,double K,double G,double,float)const{return -G-9.*K*DP.DP_phi*DP.DP_psi;}
};
struct SoftValues{
  Material material;TpDPCtes fit;
  FGENERAL_HD Coefficients operator()(double k)const{return UpdateDPvars(material,k,fit);}
  // Sufficient interval-wide monotonicity certificate, not a new material law.
  // Deliberately conservative. Uncertified paths are not labelled as an apex.
  FGENERAL_HD double SlopeUpper(const Invariants& tr,double K,double G,double limit,float old)const{
    const auto DP=operator()(old);const double h=1./::sqrt(3.);
    const double phirate=double(material.n_p)*(double(material.phi_p)-material.phi_r)*::exp(-double(material.n_p)*old);
    const double cohexcess=(double(material.coh_p)-material.coh_r)*::exp(-double(material.n_c)*old),cohmax=material.coh_r+cohexcess;
    const double psirate=double(material.sf)*::fabs(double(material.psi0))*::exp(-double(material.sf)*old);
    const double alphakmax=phirate,betakmax=psirate; // Angle-slope bounds: PS<=1/3, 3-D<=.867, both <1.
    const double kckmax=(fit==DP_PS?1.:2.)*double(material.n_c)*cohexcess+(fit==DP_PS?1.:4.)*cohmax*phirate;
    const double bmax=::fabs(DP.DP_psi),imax=::fabs(tr.I)+9.*K*bmax*limit;
    return -G+9.*K*DP.DP_phi*(bmax+limit*betakmax*h)+(imax*alphakmax+kckmax)*h;
  }
};
template<class Values> FGENERAL_HD inline Evaluation EvaluateRadial(const Values& values,const Invariants& tr,double K,double G,float old,double lambda){
  const double h=1./::sqrt(3.),kappa=double(old)+h*lambda;const auto DP=values(kappa);
  const double I=tr.I-9.*K*DP.DP_psi*lambda;
  return {tr.q-G*lambda+DP.DP_phi*I-DP.DP_kc,
    -G-9.*K*DP.DP_phi*(DP.DP_psi+lambda*DP.dDP_psi_dk*h)+Updatedfdk(DP,I)*h,I,kappa};
}
template<class Values> FGENERAL_HD inline Result ReturnRadial(const State& input,double K,double G,const Values& values){
  Result r{};r.state=input;r.status=Status::Invalid;r.kappa_continuous=input.kappa;
  if(!Finite(input.stress)||!Finite(input.kappa)||input.kappa<0.f||!Finite(K)||!Finite(G)||!(K>0.&&G>0.))return r;
  const auto tr=GetInvariants(input.stress);const auto DP=values(input.kappa);
  if(!Finite(tr.I)||!Finite(tr.q)||!Finite(DP)||DP.DP_phi<0.||DP.DP_kc<0.)return r;
  const double ft=tr.q+DP.DP_phi*tr.I-DP.DP_kc;r.trial_yield=ft;
  if(!Finite(ft))return r;
  if(ft<1e-5){r.status=Status::Elastic;return r;}
  if(!(tr.q>0.)){r.status=Status::ApexNeeded;return r;}
  const double limit=tr.q/G;r.radial_slope_upper_bound=values.SlopeUpper(tr,K,G,limit,input.kappa);
  const double rounding=64.*DBL_EPSILON*(G+::fabs(r.radial_slope_upper_bound+G));
  if(!Finite(r.radial_slope_upper_bound)||!(r.radial_slope_upper_bound < -rounding)){r.status=Status::UnresolvedPath;return r;}
  const auto start=EvaluateRadial(values,tr,K,G,input.kappa,0.),endpoint=EvaluateRadial(values,tr,K,G,input.kappa,limit);
  if(!Finite(start.df)||!(start.df<0.)||!Finite(endpoint.f))return r;
  if(endpoint.f>0.){r.status=Status::ApexNeeded;return r;} // No radial root only after the interval proof.
  double lo=0.,hi=limit,lambda=ft/(-start.df);lambda=lambda<lo?lo:(lambda>hi?hi:lambda);
  r.root_budget=1e-10*Max(Max(1.,::fabs(tr.q)),Max(::fabs(DP.DP_phi*tr.I),::fabs(DP.DP_kc)));
  Evaluation e{};bool converged=false;
  for(unsigned n=0;n<80;n++){
    e=EvaluateRadial(values,tr,K,G,input.kappa,lambda);r.iterations=n+1;r.lambda=lambda;
    r.root_residual=e.f;r.kappa_continuous=e.kappa;r.minus_dF_dlambda=-e.df;
    if(!Finite(e.f)||!Finite(e.df)||!Finite(e.I)||!Finite(e.kappa)||!(e.df<0.)||e.kappa<input.kappa)return r;
    if(::fabs(e.f)<=r.root_budget){converged=true;break;}
    if(e.f>0.)lo=lambda;else hi=lambda;
    const double next=lambda-e.f/e.df;lambda=Finite(next)&&next>lo&&next<hi?next:.5*(lo+hi);
  }
  if(!converged){r.status=Status::NonConverged;return r;}
  const double scale=(tr.q-G*r.lambda)/tr.q,mean=e.I/3.,oldmean=tr.I/3.;
  if(!Finite(scale)||scale<0.||scale>1.)return r;
  const Stress corrected={mean+scale*(input.stress.xx-oldmean),mean+scale*(input.stress.yy-oldmean),mean+scale*(input.stress.zz-oldmean),scale*input.stress.xy,scale*input.stress.yz,scale*input.stress.xz};
  const float saved=float(e.kappa);if(!Finite(corrected)||!Finite(saved)||saved<input.kappa)return r;
  r.state={corrected,saved};r.status=Status::Radial;return r;
}
} // namespace detail
// Basic fixed-coefficient elastoplastic entry. Coefficients are double temporary
// values; underlying angle/cohesion/moduli and saved history remain float.
FGENERAL_HD inline Result ConsRelationEP(const State& input,float ModulusK,float ModulusG,double DP_phi,double DP_kc,double DP_psi){
  return detail::ReturnRadial(input,ModulusK,ModulusG,detail::BasicValues{{DP_phi,DP_kc,DP_psi,0.,0.,0.}});
}
// General same-kappa evolution entry. No XML algorithm selector is introduced.
FGENERAL_HD inline Result ConsRelationEPsft(const State& input,const Material& m,TpDPCtes fit){
  if(!KnownFit(fit)||!Finite(m.phi_p)||!Finite(m.phi_r)||!Finite(m.n_p)||!Finite(m.coh_p)||!Finite(m.coh_r)||!Finite(m.n_c)||!Finite(m.psi0)||!Finite(m.sf)
    ||!(m.phi_r>0.f&&m.phi_p>=m.phi_r&&double(m.phi_p)<1.57079632679489661923)
    ||m.n_p<0.f||m.coh_r<0.f||m.coh_p<m.coh_r||m.n_c<0.f||m.sf<0.f||!(::fabs(double(m.psi0))<1.57079632679489661923)){
    Result r{};r.state=input;r.status=Status::Invalid;r.kappa_continuous=input.kappa;return r;
  }
  return detail::ReturnRadial(input,m.ModulusK,m.ModulusG,detail::SoftValues{m,fit});
}
} // namespace fsoil_general_candidate_r1
#undef FGENERAL_HD
