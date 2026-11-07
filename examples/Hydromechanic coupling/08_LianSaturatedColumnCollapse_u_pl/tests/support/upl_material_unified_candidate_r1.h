// Test-only two-entry DP return: evolving phi/cohesion/psi and explicit apex policy.
// Uncertified softening paths remain UnresolvedPath; this is not production admission.
#pragma once
#include "DualSphDef.h"
#include <cmath>
#include <cfloat>
#if defined(__CUDACC__)
#define FUNIFIED_HD __host__ __device__
#else
#define FUNIFIED_HD
#endif
namespace fsoil_unified_candidate_r1 {
struct Stress{double xx,yy,zz,xy,yz,xz;};
struct State{Stress stress;float kappa;};
struct Material{float ModulusK,ModulusG,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi0,sf;};
struct Coefficients{double DP_phi,DP_kc,DP_psi,dDP_phi_dk,dDP_kc_dk,dDP_psi_dk;};
enum class Status:unsigned{Invalid,Elastic,Smooth,Apex,TensionRepair,NoAdmissibleFlow,NonConverged,UnresolvedPath};
enum class Reason:unsigned{InvalidInput,WithinYield,CylinderFlow,SmoothFlow,SmoothEndpoint,
  PositiveDilationApex,JointExistingApexCap,UnreachableFlow,UnrepresentableState,
  UncertifiedRadialPath,RadialIterationLimit};
struct Result{
  State state;Status status;Reason reason;
  double trial_I,trial_q,returned_I,returned_q,trial_yield,kappa_continuous;
  // lambda_shear is the actual g_s multiplier; at an apex it is not sqrt(3)*delta_kappa.
  double lambda_shear,lambda_apex,lambda_tension;
  double root_residual,root_budget,minus_dF_dlambda,radial_slope_upper_bound;
  unsigned iterations;bool repair;
};
struct Invariants{double I,q;};
FUNIFIED_HD inline bool Finite(double x){
#if defined(__CUDA_ARCH__)
  return isfinite(x);
#else
  return std::isfinite(x);
#endif
}
FUNIFIED_HD inline bool Finite(const Stress& s){return Finite(s.xx)&&Finite(s.yy)&&Finite(s.zz)&&Finite(s.xy)&&Finite(s.yz)&&Finite(s.xz);}
FUNIFIED_HD inline bool Finite(const Coefficients& c){return Finite(c.DP_phi)&&Finite(c.DP_kc)&&Finite(c.DP_psi)&&Finite(c.dDP_phi_dk)&&Finite(c.dDP_kc_dk)&&Finite(c.dDP_psi_dk);}
FUNIFIED_HD inline bool CommitAllowed(Status s){return s==Status::Elastic||s==Status::Smooth||s==Status::Apex||s==Status::TensionRepair;}
FUNIFIED_HD inline double Max(double a,double b){return a>b?a:b;}
FUNIFIED_HD inline bool KnownFit(TpDPCtes fit){return fit==DP_PS||fit==DP_C||fit==DP_MC;}
FUNIFIED_HD inline Invariants GetInvariants(const Stress& s){
  // Equivalent to sqrt(s_dev:s_dev/2), with exact q=0 for identical diagonal inputs.
  const double a=s.xx-s.yy,b=s.yy-s.zz,c=s.zz-s.xx;
  return {s.xx+s.yy+s.zz,::sqrt((a*a+b*b+c*c)/6.+s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)};
}
// Angles and decay constants are float inputs in radians and inverse kappa.
// These coefficient expressions/operation groups retain the general-r1 candidate.
FUNIFIED_HD inline Coefficients UpdateDPvars(const Material& m,double kappa,TpDPCtes fit){
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
FUNIFIED_HD inline double Updatedfdk(const Coefficients& DP,double I){return I*DP.dDP_phi_dk-DP.dDP_kc_dk;}
struct Evaluation{double f,df,I,kappa;};
namespace detail{
struct BasicValues{
  Coefficients DP;
  FUNIFIED_HD Coefficients operator()(double)const{return DP;}
  FUNIFIED_HD bool IsConstant()const{return true;}
};
struct SoftValues{
  Material material;TpDPCtes fit;
  FUNIFIED_HD Coefficients operator()(double k)const{return UpdateDPvars(material,k,fit);}
  FUNIFIED_HD bool IsConstant()const{
    return (material.n_p==0.f||material.phi_p==material.phi_r)
      &&(material.n_c==0.f||material.coh_p==material.coh_r)&&(material.sf==0.f||material.psi0==0.f);
  }
  // Sufficient interval-wide certificate, not a material law or a proof that an
  // uncertified path has no physical root. Retain the stabilizing positive-beta
  // term instead of replacing it by its absolute value. No apex on failure.
  FUNIFIED_HD double SlopeUpper(const Invariants& tr,double K,double G,double limit,float old)const{
    const auto DP=operator()(old);const double h=1./::sqrt(3.);
    const auto endpoint=operator()(double(old)+h*limit);
    const double phirate=double(material.n_p)*(double(material.phi_p)-material.phi_r)*::exp(-double(material.n_p)*old);
    const double cohexcess=(double(material.coh_p)-material.coh_r)*::exp(-double(material.n_c)*old),cohmax=material.coh_r+cohexcess;
    const double psirate=double(material.sf)*::fabs(double(material.psi0))*::exp(-double(material.sf)*old);
    const double alphakmax=phirate,betakmax=psirate;
    const double kckmax=(fit==DP_PS?1.:2.)*double(material.n_c)*cohexcess+(fit==DP_PS?1.:4.)*cohmax*phirate;
    const double bmax=::fabs(DP.DP_psi),imax=::fabs(tr.I)+9.*K*bmax*limit;
    const double B_lower=material.psi0>=0.f?endpoint.DP_psi-limit*betakmax*h:DP.DP_psi;
    const double alpha_bound=B_lower>=0.?endpoint.DP_phi:DP.DP_phi;
    return -G-9.*K*alpha_bound*B_lower+(imax*alphakmax+kckmax)*h;
  }
};
// BasicValues has no evolving derivative; this overload is never the constant fast path.
FUNIFIED_HD inline double SlopeUpper(const BasicValues& v,const Invariants&,double K,double G,double,float){return -G-9.*K*v.DP.DP_phi*v.DP.DP_psi;}
FUNIFIED_HD inline double SlopeUpper(const SoftValues& v,const Invariants& tr,double K,double G,double limit,float old){return v.SlopeUpper(tr,K,G,limit,old);}
template<class Values> FUNIFIED_HD inline Evaluation EvaluateRadial(const Values& values,const Invariants& tr,double K,double G,float old,double lambda){
  const double h=1./::sqrt(3.),kappa=double(old)+h*lambda;const auto DP=values(kappa);
  const double I=tr.I-9.*K*DP.DP_psi*lambda;
  return {tr.q-G*lambda+DP.DP_phi*I-DP.DP_kc,
    -G-9.*K*DP.DP_phi*(DP.DP_psi+lambda*DP.dDP_psi_dk*h)+Updatedfdk(DP,I)*h,I,kappa};
}
FUNIFIED_HD inline Stress RadialStress(const Stress& trial,double trial_I,double new_I,double scale){
  const double oldmean=trial_I/3.,mean=new_I/3.;
  return {mean+scale*(trial.xx-oldmean),mean+scale*(trial.yy-oldmean),mean+scale*(trial.zz-oldmean),scale*trial.xy,scale*trial.yz,scale*trial.xz};
}
FUNIFIED_HD inline bool Commit(Result& r,const Stress& stress,double kappa,Status status,Reason reason,
  double lambda_shear,double lambda_apex,double lambda_tension){
  const float saved=float(kappa);const auto v=GetInvariants(stress);
  if(!Finite(stress)||!Finite(v.I)||!Finite(v.q)||!Finite(kappa)||!Finite(saved)||saved<r.state.kappa
    ||!Finite(lambda_shear)||!Finite(lambda_apex)||!Finite(lambda_tension)
    ||lambda_shear<0.||lambda_apex<0.||lambda_tension<0.)return false;
  r.state={stress,saved};r.status=status;r.reason=reason;r.kappa_continuous=kappa;
  r.returned_I=v.I;r.returned_q=v.q;r.lambda_shear=lambda_shear;r.lambda_apex=lambda_apex;
  r.lambda_tension=lambda_tension;r.repair=status==Status::TensionRepair;return true;
}
// At q=0 the accumulated deviatoric plastic increment is saturated. Coefficients
// are evaluated at kappa_tip, not at a guessed total apex multiplier or saved float.
template<class Values> FUNIFIED_HD inline Result ReturnApex(Result r,const Values& values,double K,double G){
  const double lambda0=r.trial_q/G,kappa_tip=double(r.state.kappa)+lambda0/::sqrt(3.);
  const auto DP=values(kappa_tip);
  r.status=Status::NoAdmissibleFlow;r.reason=Reason::UnreachableFlow;
  if(!Finite(lambda0)||!Finite(kappa_tip)||!Finite(DP)||DP.DP_phi<0.||DP.DP_kc<0.){
    r.status=Status::Invalid;r.reason=Reason::UnrepresentableState;return r;
  }
  if(DP.DP_phi==0.)return r; // A cylinder has no finite cone tip; never divide by alpha.
  const double I_tip=DP.DP_kc/DP.DP_phi,mean=I_tip/3.;
  if(!Finite(I_tip)||!Finite(mean)){r.reason=Reason::UnrepresentableState;return r;}
  const Stress tip={mean,mean,mean,0.,0.,0.};
  if(DP.DP_psi>0.){
    const double lambda=(r.trial_I-I_tip)/(9.*K*DP.DP_psi);
    if(Finite(lambda)&&lambda>=lambda0){
      if(Commit(r,tip,kappa_tip,Status::Apex,Reason::PositiveDilationApex,lambda,lambda,0.))return r;
      r.reason=Reason::UnrepresentableState;return r;
    }
  }
  // Additional existing tension-face policy f_t=I-I_tip, g_t=I. This is not
  // claimed to be the original single-potential apex solution or positive work.
  const double lambda_t=(r.trial_I-I_tip)/(9.*K)-DP.DP_psi*lambda0;
  if(Finite(lambda_t)&&lambda_t>=0.){
    if(Commit(r,tip,kappa_tip,Status::TensionRepair,Reason::JointExistingApexCap,lambda0,0.,lambda_t))return r;
    r.reason=Reason::UnrepresentableState;
  }
  return r;
}
template<class Values> FUNIFIED_HD inline Result ReturnFlow(const State& input,double K,double G,const Values& values){
  Result r{};r.state=input;r.status=Status::Invalid;r.reason=Reason::InvalidInput;r.kappa_continuous=input.kappa;
  if(!Finite(input.stress)||!Finite(input.kappa)||input.kappa<0.f||!Finite(K)||!Finite(G)||!(K>0.&&G>0.))return r;
  const auto tr=GetInvariants(input.stress);const auto DP=values(input.kappa);
  if(!Finite(tr.I)||!Finite(tr.q)||!Finite(DP)||DP.DP_phi<0.||DP.DP_kc<0.)return r;
  const double ft=tr.q+DP.DP_phi*tr.I-DP.DP_kc;if(!Finite(ft))return r;
  r.trial_I=r.returned_I=tr.I;r.trial_q=r.returned_q=tr.q;r.trial_yield=ft;
  if(ft<1e-5){r.status=Status::Elastic;r.reason=Reason::WithinYield;return r;}
  const double limit=tr.q/G;if(!Finite(limit)){r.reason=Reason::UnrepresentableState;return r;}
  if(!(tr.q>0.))return ReturnApex(r,values,K,G);
  if(values.IsConstant()){
    // Both entries share the exact same fixed-coefficient flow; no soft-only certificate.
    double lambda=0.,new_q=0.;Reason reason=Reason::SmoothFlow;
    bool smooth=false;
    const double D=G+9.*K*DP.DP_phi*DP.DP_psi;r.radial_slope_upper_bound=-D;
    if(DP.DP_phi==0.){lambda=(tr.q-DP.DP_kc)/G;new_q=DP.DP_kc;reason=Reason::CylinderFlow;smooth=true;}
    else if(Finite(D)&&D>0.){lambda=ft/D;new_q=lambda==limit?0.:tr.q-G*lambda;smooth=true;}
    if(smooth&&Finite(lambda)&&lambda>=0.&&lambda<=limit&&new_q>=0.){
      const double new_I=tr.I-9.*K*DP.DP_psi*lambda,kappa=double(input.kappa)+lambda/::sqrt(3.);
      const bool endpoint=new_q==0.&&DP.DP_phi>0.;
      r.root_residual=new_q+DP.DP_phi*new_I-DP.DP_kc;r.minus_dF_dlambda=D;
      if(Commit(r,RadialStress(input.stress,tr.I,new_I,new_q/tr.q),kappa,
        endpoint?Status::Apex:Status::Smooth,endpoint?Reason::SmoothEndpoint:reason,lambda,endpoint?lambda:0.,0.))return r;
      r.reason=Reason::UnrepresentableState;return r;
    }
    return ReturnApex(r,values,K,G); // D<=0 is not silently called invalid or a smooth root.
  }
  r.radial_slope_upper_bound=SlopeUpper(values,tr,K,G,limit,input.kappa);
  const double rounding=64.*DBL_EPSILON*(G+::fabs(r.radial_slope_upper_bound+G));
  if(!Finite(r.radial_slope_upper_bound)||!(r.radial_slope_upper_bound < -rounding)){
    r.status=Status::UnresolvedPath;r.reason=Reason::UncertifiedRadialPath;return r;
  }
  const auto start=EvaluateRadial(values,tr,K,G,input.kappa,0.);
  const auto endpoint=EvaluateRadial(values,tr,K,G,input.kappa,limit);
  if(!Finite(start.df)||!(start.df<0.)||!Finite(endpoint.f))return r;
  if(endpoint.f>0.)return ReturnApex(r,values,K,G); // Only after the interval-wide root exclusion.
  double lo=0.,hi=limit,lambda=ft/(-start.df);lambda=lambda<lo?lo:(lambda>hi?hi:lambda);
  r.root_budget=1e-10*Max(Max(1.,::fabs(tr.q)),Max(::fabs(DP.DP_phi*tr.I),::fabs(DP.DP_kc)));
  Evaluation e{};bool converged=false;
  for(unsigned n=0;n<80;n++){
    e=EvaluateRadial(values,tr,K,G,input.kappa,lambda);r.iterations=n+1;
    r.root_residual=e.f;r.minus_dF_dlambda=-e.df;
    if(!Finite(e.f)||!Finite(e.df)||!Finite(e.I)||!Finite(e.kappa)||!(e.df<0.)||e.kappa<input.kappa)return r;
    if(::fabs(e.f)<=r.root_budget){converged=true;break;}
    if(e.f>0.)lo=lambda;else hi=lambda;
    const double next=lambda-e.f/e.df;lambda=Finite(next)&&next>lo&&next<hi?next:.5*(lo+hi);
  }
  if(!converged){r.status=Status::NonConverged;r.reason=Reason::RadialIterationLimit;return r;}
  const double new_q=lambda==limit?0.:tr.q-G*lambda,scale=new_q/tr.q;
  if(!Finite(scale)||scale<0.||scale>1.)return r;
  const auto returnedDP=values(e.kappa);const bool at_tip=new_q==0.&&returnedDP.DP_phi>0.;
  if(!Commit(r,RadialStress(input.stress,tr.I,e.I,scale),e.kappa,at_tip?Status::Apex:Status::Smooth,
    at_tip?Reason::SmoothEndpoint:(returnedDP.DP_phi==0.?Reason::CylinderFlow:Reason::SmoothFlow),lambda,at_tip?lambda:0.,0.))
    r.reason=Reason::UnrepresentableState;
  return r;
}
} // namespace detail
FUNIFIED_HD inline Result ConsRelationEP(const State& input,float ModulusK,float ModulusG,double DP_phi,double DP_kc,double DP_psi){
  return detail::ReturnFlow(input,ModulusK,ModulusG,detail::BasicValues{{DP_phi,DP_kc,DP_psi,0.,0.,0.}});
}
FUNIFIED_HD inline Result ConsRelationEPsft(const State& input,const Material& m,TpDPCtes fit){
  if(!KnownFit(fit)||!Finite(m.phi_p)||!Finite(m.phi_r)||!Finite(m.n_p)||!Finite(m.coh_p)||!Finite(m.coh_r)||!Finite(m.n_c)||!Finite(m.psi0)||!Finite(m.sf)
    ||!(m.phi_r>=0.f&&m.phi_p>=m.phi_r&&double(m.phi_p)<1.57079632679489661923)
    ||m.n_p<0.f||m.coh_r<0.f||m.coh_p<m.coh_r||m.n_c<0.f||m.sf<0.f||!(::fabs(double(m.psi0))<1.57079632679489661923)){
    Result r{};r.state=input;r.status=Status::Invalid;r.reason=Reason::InvalidInput;r.kappa_continuous=input.kappa;return r;
  }
  return detail::ReturnFlow(input,m.ModulusK,m.ModulusG,detail::SoftValues{m,fit});
}
} // namespace fsoil_unified_candidate_r1
#undef FUNIFIED_HD
