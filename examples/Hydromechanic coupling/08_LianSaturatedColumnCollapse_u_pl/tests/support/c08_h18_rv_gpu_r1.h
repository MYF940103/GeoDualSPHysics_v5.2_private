// Private H1.8 residual-viscosity API only: no public class/CTE/BI4 interface.
#ifndef C08_H18_RV_GPU_R1_H
#define C08_H18_RV_GPU_R1_H
#include "DualSphDef.h"
#include "JCellDivDataGpu.h"
#include <cuda_runtime_api.h>
namespace c08h18rv {
constexpr double Alpha=.1;
struct Result {
  unsigned error_bits,invalid_sorted,invalid_native_id,validated_soil;
  unsigned directed_edges,reverse_memberships,max_degree,mode;
  double lambda_max,isolated_bound,gamma64,max_condition;
  double work,form,work_defect_prediction,work_certificate_error,work_certificate_budget,work_budget;
  double net_force_norm,net_force_budget,torque,torque_defect_prediction,torque_certificate_error,torque_certificate_budget,torque_budget;
  double committed_work,committed_work_budget,committed_net_force_norm,committed_net_force_budget,committed_torque,committed_torque_budget;
  double max_normal_budget_ratio,max_commit_budget_ratio,max_residual,residual_budget,max_force,force_budget;
  bool committed,certificates_passed,manufactured_passed;
};
inline const char* TelemetryHeader(){return
  "record,phase,active,alpha,step_start_global,completed_global,step_start_time_s,force_stage_time_s,save_time_s,operator_dt_s,phase_calls,phase_commits,pre_calls,cor_calls,pre_commits,cor_commits,last_lambda_max_s_1,running_lambda_max_s_1,last_dt_lambda_half,running_dt_lambda_half,validated_soil_nodes,committed,error_bits,invalid_sorted_index,invalid_native_id,cuda_status,"
  "directed_edges,reverse_memberships,max_degree,gamma64,max_condition,max_normal_budget_ratio,max_commit_budget_ratio,work_W_per_m,form_W_per_m,work_defect_prediction_W_per_m,work_certificate_error_W_per_m,work_certificate_budget_W_per_m,work_budget_W_per_m,net_force_norm_N_per_m,net_force_budget_N_per_m,torque_N,torque_defect_prediction_N,torque_certificate_error_N,torque_certificate_budget_N,torque_budget_N,committed_work_W_per_m,committed_work_budget_W_per_m,committed_net_force_norm_N_per_m,committed_net_force_budget_N_per_m,committed_torque_N,committed_torque_budget_N,"
  "running_normal_ratio,running_float_commit_ratio,running_work_certificate_ratio,running_work_budget_ratio,running_net_force_ratio,running_torque_certificate_ratio,running_torque_budget_ratio,running_committed_work_ratio,running_committed_net_force_ratio,running_committed_torque_ratio,max_residual_m_s,residual_budget_m_s,max_force_N_per_m,force_budget_N_per_m";}
inline const char* ManufacturedHeader(){return
  "mode,name,step_start_global,source_time_s,operator_dt_s,directed_edges,reverse_memberships,max_degree,gamma64,max_condition,max_normal_budget_ratio,max_commit_budget_ratio,"
  "work_W_per_m,form_W_per_m,work_defect_prediction_W_per_m,work_certificate_error_W_per_m,work_certificate_budget_W_per_m,work_budget_W_per_m,net_force_norm_N_per_m,net_force_budget_N_per_m,torque_N,torque_defect_prediction_N,torque_certificate_error_N,torque_certificate_budget_N,torque_budget_N,committed_work_W_per_m,committed_work_budget_W_per_m,committed_net_force_norm_N_per_m,committed_net_force_budget_N_per_m,committed_torque_N,committed_torque_budget_N,"
  "max_residual_m_s,residual_budget_m_s,max_force_N_per_m,force_budget_N_per_m,committed,certificates_passed,manufactured_passed,error_bits,cuda_status";}
// mode0 uses actual float velocity. Modes1/2/3 use scratch-only double synthetic
// translation/full-affine/rotation on the same current graph; they cannot commit.
cudaError_t Add(unsigned np,unsigned npb,const StDivDataGpu& dvd,const unsigned* dcell,const unsigned* idp,
  const double2* posxy,const double* posz,const float4* velocity,const typecode* code,const double* J,
  double solid0,double rho0,double rhow,double vol0,float h,float bwen,float G,double dt,
  unsigned mode,bool commit,float3* ace,Result& result);
}
#endif
