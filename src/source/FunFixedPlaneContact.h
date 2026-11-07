// Fixed lower-plane scalar contact: velocity projection, not a reaction/J/p closure.
#ifndef FUNFIXEDPLANECONTACT_H
#define FUNFIXEDPLANECONTACT_H

#ifdef __CUDACC__
#define FCONTACT_HD __host__ __device__
#else
#define FCONTACT_HD
#endif

namespace fcontact{
FCONTACT_HD inline bool ProjectLowerPlane(double pos,double plane,double &move,float &velocity){
  const double trial=pos+move;
  if(trial<=plane){
    move=plane-pos;
    if(velocity<0.f)velocity=0.f;
    return(true);
  }
  return(false);
}
}

#undef FCONTACT_HD
#endif
