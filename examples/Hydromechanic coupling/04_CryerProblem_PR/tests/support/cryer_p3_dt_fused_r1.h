#pragma once
#include <cfloat>
#include <cmath>
#ifdef __CUDACC__
#define CRYER_DT_HD __host__ __device__
#else
#define CRYER_DT_HD
#endif

namespace cryer_p3_dt {
struct Params { double solid0,rho0,rhow,modulus,kw,conductivity,gamma; };
struct Value {
  double legacy2,skeleton2,diffusion;
  bool legacy_valid,skeleton_valid;
};
CRYER_DT_HD inline bool Finite(double x){
#ifdef __CUDA_ARCH__
  return isfinite(x);
#else
  return std::isfinite(x);
#endif
}

// Constant-k Cryer only. Each result has the original pass's own zero/error semantics.
CRYER_DT_HD inline Value Evaluate(double J, const Params& p){
  Value out={0.,0.,0.,false,false};
  if(!Finite(J) || J<=p.solid0)return out;
  const double n=1.-p.solid0/J;
  const double rho=p.rhow+(p.rho0-p.rhow)/J;
  if(!Finite(n) || !(n>0. && n<1.) || !Finite(rho) || !(rho>0.))return out;

  // The two old wave passes use identical n and rho, but have separate validity rules.
  const double skeleton=(p.modulus+0./n)/rho;
  out.skeleton_valid=Finite(skeleton) && skeleton>0.;
  if(out.skeleton_valid)out.skeleton2=skeleton;
  const double bulk=p.kw/n;
  const double legacy=(p.modulus+bulk)/rho;
  if(!Finite(legacy) || !(legacy>0.) || !Finite(p.conductivity) || p.conductivity<0.
    || !Finite(p.gamma) || !(p.gamma>0.))return out;
  if(p.conductivity>0.){
    const double margin=rho*bulk/(p.modulus+bulk)-p.rhow;
    const double diffusion=bulk*p.conductivity/p.gamma;
    if(!(margin>64.*DBL_EPSILON*fmax(rho,p.rhow)) || !Finite(diffusion) || !(diffusion>0.))return out;
    out.diffusion=diffusion;
  }
  out.legacy2=legacy;out.legacy_valid=true;
  return out;
}

struct Summary {
  double legacy2,skeleton2,diffusion;
  unsigned invalid_legacy,invalid_skeleton;
};
inline unsigned FirstFailure(const Summary& r,unsigned np){
  if(r.invalid_legacy<np || !Finite(r.legacy2) || !(r.legacy2>0.)
    || !Finite(r.diffusion) || r.diffusion<0.)return 1;
  if(r.invalid_skeleton<np || !Finite(r.skeleton2) || !(r.skeleton2>0.))return 2;
  return 0;
}
}
#undef CRYER_DT_HD

