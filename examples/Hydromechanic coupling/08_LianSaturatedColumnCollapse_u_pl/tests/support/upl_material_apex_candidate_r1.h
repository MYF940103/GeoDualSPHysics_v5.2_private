// Test-only analytic fixed-strength DP return and explicit existing-apex tension policy.
// Not a production material, not a softening solver, and not a general PART restart.
#pragma once
#include <cmath>
#if defined(__CUDACC__)
#define FAPEX_HD __host__ __device__
#else
#define FAPEX_HD
#endif
namespace fsoil_apex_candidate_r1 {
struct Stress{double xx,yy,zz,xy,yz,xz;};
struct State{Stress stress;float kappa;};
struct Material{float ModulusK,ModulusG;double DP_phi,DP_kc,DP_psi;};
enum class Status:unsigned{Invalid,Elastic,Smooth,Apex,TensionRepair,NoAdmissibleFlow};
enum class Reason:unsigned{InvalidInput,WithinYield,CylinderFlow,SmoothFlow,SmoothEndpoint,
  PositiveDilationApex,JointExistingApexCap,UnreachableFlow,UnrepresentableState};
struct Result{
  State state;Status status;Reason reason;
  double trial_I,trial_q,returned_I,returned_q,trial_yield,kappa_continuous;
  // Actual multiplier of g_s. At a pure apex it need not equal sqrt(3)*delta_kappa.
  double lambda_shear,lambda_apex,lambda_tension;
  bool repair;
};
struct Invariants{double I,q;};
FAPEX_HD inline bool Finite(double x){
#if defined(__CUDA_ARCH__)
  return isfinite(x);
#else
  return std::isfinite(x);
#endif
}
FAPEX_HD inline bool Finite(const Stress& s){return Finite(s.xx)&&Finite(s.yy)&&Finite(s.zz)&&Finite(s.xy)&&Finite(s.yz)&&Finite(s.xz);}
FAPEX_HD inline bool CommitAllowed(Status s){return s==Status::Elastic||s==Status::Smooth||s==Status::Apex||s==Status::TensionRepair;}
FAPEX_HD inline Invariants GetInvariants(const Stress& s){
  // Pair differences are equivalent to s_dev:s_dev/2 and give q=0 for identical diagonals.
  const double a=s.xx-s.yy,b=s.yy-s.zz,c=s.zz-s.xx;
  return {s.xx+s.yy+s.zz,::sqrt((a*a+b*b+c*c)/6.+s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)};
}
FAPEX_HD inline Stress RadialStress(const Stress& trial,double trial_I,double new_I,double scale){
  const double oldmean=trial_I/3.,mean=new_I/3.;
  return {mean+scale*(trial.xx-oldmean),mean+scale*(trial.yy-oldmean),
    mean+scale*(trial.zz-oldmean),scale*trial.xy,scale*trial.yz,scale*trial.xz};
}
FAPEX_HD inline bool Commit(Result& r,const Stress& stress,double kappa,Status status,Reason reason,
  double lambda_shear,double lambda_apex,double lambda_tension){
  const float saved=float(kappa);const Invariants v=GetInvariants(stress);
  if(!Finite(stress)||!Finite(v.I)||!Finite(v.q)||!Finite(kappa)||!Finite(saved)||saved<r.state.kappa
    || !Finite(lambda_shear)||!Finite(lambda_apex)||!Finite(lambda_tension))return false;
  r.state={stress,saved};r.status=status;r.reason=reason;r.kappa_continuous=kappa;
  r.returned_I=v.I;r.returned_q=v.q;r.lambda_shear=lambda_shear;r.lambda_apex=lambda_apex;
  r.lambda_tension=lambda_tension;r.repair=status==Status::TensionRepair;return true;
}
FAPEX_HD inline Result Return(const State& input,const Material& m){
  Result r{};r.state=input;r.status=Status::Invalid;r.reason=Reason::InvalidInput;
  r.kappa_continuous=double(input.kappa);
  if(!Finite(input.stress)||!Finite(input.kappa)||input.kappa<0.f
    || !Finite(m.ModulusK)||!Finite(m.ModulusG)||!(m.ModulusK>0.f&&m.ModulusG>0.f)
    || !Finite(m.DP_phi)||!Finite(m.DP_kc)||!Finite(m.DP_psi)||m.DP_phi<0.||m.DP_kc<0.)return r;
  const double K=m.ModulusK,G=m.ModulusG,DP_phi=m.DP_phi,DP_kc=m.DP_kc,DP_psi=m.DP_psi;
  const Invariants tr=GetInvariants(input.stress);const double f=tr.q+DP_phi*tr.I-DP_kc;
  if(!Finite(tr.I)||!Finite(tr.q)||!Finite(f))return r;
  r.trial_I=r.returned_I=tr.I;r.trial_q=r.returned_q=tr.q;r.trial_yield=f;
  if(f<=0.){r.status=Status::Elastic;r.reason=Reason::WithinYield;return r;}
  r.status=Status::NoAdmissibleFlow;r.reason=Reason::UnreachableFlow;
  const double sqrt3=::sqrt(3.),lambda0=tr.q/G,kappa_tip=double(input.kappa)+lambda0/sqrt3;
  if(!Finite(lambda0)||!Finite(kappa_tip)){r.reason=Reason::UnrepresentableState;return r;}
  // A finite cone tip does not exist for phi=0. Keep the supplied potential beta unchanged.
  if(DP_phi==0.){
    if(tr.q>0.){
      const double lambda=(tr.q-DP_kc)/G,new_I=tr.I-9.*K*DP_psi*lambda;
      if(lambda>=0. && Commit(r,RadialStress(input.stress,tr.I,new_I,DP_kc/tr.q),
        double(input.kappa)+lambda/sqrt3,Status::Smooth,Reason::CylinderFlow,lambda,0.,0.))return r;
    }
    r.reason=Reason::UnrepresentableState;return r;
  }
  // Prefer the smallest admissible smooth solution before considering the singular point.
  const double D=G+9.*K*DP_phi*DP_psi;
  if(Finite(D)&&D>0. && tr.q>0.){
    const double lambda=f/D;
    const double new_q=(lambda==lambda0?0.:tr.q-G*lambda),new_I=tr.I-9.*K*DP_psi*lambda;
    if(Finite(lambda)&&lambda>=0.&&lambda<=lambda0&&new_q>=0.){
      const bool endpoint=new_q==0.;
      if(Commit(r,RadialStress(input.stress,tr.I,new_I,new_q/tr.q),
        double(input.kappa)+lambda/sqrt3,endpoint?Status::Apex:Status::Smooth,
        endpoint?Reason::SmoothEndpoint:Reason::SmoothFlow,lambda,endpoint?lambda:0.,0.))return r;
      r.reason=Reason::UnrepresentableState;return r;
    }
  }
  const double I_tip=DP_kc/DP_phi,mean=I_tip/3.;
  if(!Finite(I_tip)||!Finite(mean)){r.reason=Reason::UnrepresentableState;return r;}
  const Stress tip={mean,mean,mean,0.,0.,0.};
  // Genuine original-g apex: beta>0 and the subgradient bound lambda>=q_trial/G.
  if(DP_psi>0.){
    const double lambda=(tr.I-I_tip)/(9.*K*DP_psi);
    if(Finite(lambda)&&lambda>=lambda0){
      if(Commit(r,tip,kappa_tip,Status::Apex,Reason::PositiveDilationApex,lambda,lambda,0.))return r;
      r.reason=Reason::UnrepresentableState;return r;
    }
  }
  // Explicit compatibility policy: additional f_t=I-I_tip, g_t=I, no new strength.
  // The shear endpoint may activate the tension face even when I_trial<=I_tip.
  const double lambda_t=(tr.I-I_tip)/(9.*K)-DP_psi*lambda0;
  if(Finite(lambda_t)&&lambda_t>=0.){
    if(Commit(r,tip,kappa_tip,Status::TensionRepair,Reason::JointExistingApexCap,lambda0,0.,lambda_t))return r;
    r.reason=Reason::UnrepresentableState;
  }
  return r;
}
} // namespace fsoil_apex_candidate_r1
#undef FAPEX_HD
