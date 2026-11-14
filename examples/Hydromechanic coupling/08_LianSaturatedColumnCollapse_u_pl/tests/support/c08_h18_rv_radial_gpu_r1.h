// Private radial residual candidate API; no public class/CTE/native22 changes.
#ifndef C08_H18_RV_RADIAL_GPU_R1_H
#define C08_H18_RV_RADIAL_GPU_R1_H
#include "DualSphDef.h"
#include "JCellDivDataGpu.h"
#include <cuda_runtime_api.h>
#define C08_RVR_METRICS(X) \
  X(edges,"edges") \
  X(active_edges,"active_edges") \
  X(closing_positive_residual_edges,"closing_positive_residual_edges") \
  X(max_degree,"max_degree") \
  X(max_condition,"max_condition") \
  X(normalization_max_ratio,"normalization_max_ratio") \
  X(LS_backward_max_ratio,"LS_backward_max_ratio") \
  X(net_gamma,"net_gamma") \
  X(power_gamma,"power_gamma") \
  X(torque_gamma,"torque_gamma") \
  X(degree_upper,"degree_upper_s_1") \
  X(lambda_upper,"lambda_upper_s_1") \
  X(dt_lambda_half,"dt_lambda_half") \
  X(dissipation_D,"dissipation_D_W_m") \
  X(node_power,"node_power_W_m") \
  X(power_error,"power_error_W_m") \
  X(power_budget,"power_budget_W_m") \
  X(net_norm,"net_norm_N_m") \
  X(net_budget,"net_budget_N_m") \
  X(pair_torque,"pair_torque_N") \
  X(central_budget,"central_budget_N") \
  X(node_torque,"node_torque_N") \
  X(torque_reduce_error,"torque_reduce_error_N") \
  X(torque_reduce_budget,"torque_reduce_budget_N") \
  X(torque_budget,"torque_budget_N") \
  X(max_q,"max_q_m_s") \
  X(max_force,"max_force_N_m") \
  X(max_added_accel,"max_added_accel_m_s2") \
  X(frozen_Euler_deltaE,"frozen_Euler_deltaE_J_m") \
  X(frozen_Euler_budget,"frozen_Euler_budget_J_m") \
  X(max_float_commit_error,"max_float_commit_error_N_m") \
  X(float_commit_budget_ratio,"float_commit_budget_ratio") \
  X(committed_power,"committed_power_W_m") \
  X(committed_power_budget,"committed_power_budget_W_m") \
  X(committed_net_norm,"committed_net_norm_N_m") \
  X(committed_net_budget,"committed_net_budget_N_m") \
  X(committed_torque,"committed_torque_N") \
  X(committed_torque_budget,"committed_torque_budget_N") \
  X(committed_Euler_deltaE,"committed_Euler_deltaE_J_m") \
  X(committed_Euler_budget,"committed_Euler_budget_J_m") \
  X(exchange_error,"exchange_error_N_m") \
  X(exchange_budget,"exchange_budget_N_m") \
  X(affine_q_budget,"affine_q_budget_m_s") \
  X(affine_force_budget,"affine_force_budget_N_m") \
  X(affine_LS_forward_budget,"affine_LS_forward_budget_s_1")
namespace c08h18radial {
constexpr double Alpha=.1;
#define C08_RVR_ENUM(name,label) name,
enum Metric {C08_RVR_METRICS(C08_RVR_ENUM) MetricCount};
#undef C08_RVR_ENUM
constexpr unsigned RunningCount=14,MainColumns=87,ManufacturedColumns=57;
struct Result {
 unsigned error_bits,invalid_sorted,invalid_native_id,validated_soil;
 unsigned directed_edges,reverse_memberships,mode;
 double value[MetricCount];
 bool committed,certificates_passed,manufactured_passed;
};
struct FixtureResult {double s[8],q[8],a[8],expected[8],power[8];unsigned errors;};
inline const char* MetricHeader(){return ""
#define C08_RVR_LABEL(name,label) "," label
 C08_RVR_METRICS(C08_RVR_LABEL)
#undef C08_RVR_LABEL
 ;}
inline const char* CommonHeader(){return "record,phase,active,alpha,step_start_global,completed_global,step_start_time_s,force_stage_time_s,save_time_s,operator_dt_s,phase_calls,phase_commits,pre_calls,cor_calls,pre_commits,cor_commits,last_lambda_max_s_1,running_lambda_max_s_1,last_dt_lambda_half,running_dt_lambda_half,validated_soil_nodes,committed,error_bits,invalid_sorted_index,invalid_native_id,cuda_status";}
inline const char* RunningHeader(){return ",running_normalization_ratio,running_LS_backward_ratio,running_exchange_ratio,running_power_ratio,running_net_ratio,running_central_torque_ratio,running_torque_reduce_ratio,running_torque_ratio,running_Euler_ratio,running_float_commit_ratio,running_committed_power_ratio,running_committed_net_ratio,running_committed_torque_ratio,running_committed_Euler_ratio";}
// mode0: actual float velocities; modes1..5: double scratch affine fields on the
// identical current graph. They cannot commit and do not advance any state.
cudaError_t Add(unsigned np,unsigned npb,const StDivDataGpu& dvd,const unsigned* dcell,const unsigned* idp,
 const double2* posxy,const double* posz,const float4* velocity,const typecode* code,const double* J,
 double solid0,double rho0,double rhow,double vol0,float h,float bwen,float G,double dt,
 unsigned mode,bool commit,float3* ace,Result& result);
// The same device Limiter used by Add is exercised by eight scalar sign/cap fixtures.
cudaError_t Fixtures(FixtureResult& result);
}
#endif
