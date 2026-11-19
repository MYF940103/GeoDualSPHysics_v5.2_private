// Prescribed surface pressures and benchmark strip geometry.
#ifndef FUNEXTERNALLOAD_H
#define FUNEXTERNALLOAD_H

#include "DualSphDef.h"
#include <algorithm>
#include <cmath>

#ifdef __CUDACC__
#define FLOAD_HD __host__ __device__
#else
#define FLOAD_HD
#endif

namespace externalload{

inline double RampedPressure(double q0,double ramptime,double time){
  using std::max;
  return(ramptime>0 && time<ramptime? q0*max(0.0,time)/ramptime: q0);
}

FLOAD_HD inline bool InStripFootprint(unsigned loadmode,double x){
  if(loadmode==HMLOAD_TopStripVertical)return(x>=-3.0 && x<=3.0);
  //-Mirror the Lian half-domain strip across the free-slip wall at x=0.
  if(loadmode==HMLOAD_LianFlexibleStrip)return(fabs(x)<=1.25);
  return(false);
}

//-Includes top-strip corners which the free-surface tracker may classify as interior.
FLOAD_HD inline bool IsStripSurface(unsigned loadmode,double x,double z,double dp){
  return(InStripFootprint(loadmode,x) && z>=10.0-0.5*dp && z<=10.0+0.5*dp);
}

}

#undef FLOAD_HD
#endif
