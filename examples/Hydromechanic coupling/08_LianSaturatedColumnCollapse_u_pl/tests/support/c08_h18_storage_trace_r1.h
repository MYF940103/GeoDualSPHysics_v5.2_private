#ifndef C08_STORAGE_TRACE_R1_H
#define C08_STORAGE_TRACE_R1_H
#include "DualSphDef.h"
// Private, independent CUDA observer ABI. No member of JSph or a physical array is added.
struct C08StorageRow{
  unsigned native_id,inits,rhs_h,updates,cap_calls,cap_changes,release_cap_calls,release_cap_changes,errors,last_step;
  double initial_S,last_S,last_time,sum_dt;
  double weighted_pressure_delta,compression,Darcy_remainder,source_split_roundoff,pressure_commit_roundoff,weight_change,cap_change;
  double abs_increments,local_budget_sum,rate_quantization_bound;
};
namespace cusph{
  bool C08StorageInit(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* j,const float* p,double v0,double solid0,double kw,unsigned step,double time);
  bool C08StorageRhs(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* jn,const double* jh,const float* pn,const double* theta,const float* rate,double v0,double solid0,double kw,unsigned step,double time,double dt);
  bool C08StorageUpdate(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const float* pn,const double* jnew,const float* praw,double v0,double solid0,double kw,unsigned step,double time,double dt);
  bool C08StorageCapBefore(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* j,const float* p,unsigned step,double time,bool release_phase);
  bool C08StorageCapAfter(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,const double* j,const float* p,const unsigned* fs,double v0,double solid0,double kw);
  bool C08StorageRead(C08StorageRow* rows,unsigned* observer_errors);
}
#endif
