// Private C08 H1.8 energy-normalized plastic HG API; no public class/CTE/native layout changes.
#ifndef C08_H18_HG_GPU_R1_HPP
#define C08_H18_HG_GPU_R1_HPP
#include "DualSphDef.h"
#include "JCellDivDataGpu.h"
#include <cuda_runtime_api.h>
#include <string>
namespace c08hg {
constexpr unsigned Nodes=5000,FirstId=2060,Neighbors=128;
constexpr double Xi=.1,StepDt=.000005;
inline const char* Environment(){return "C08_HG_H18";}
// All constants are explicit POD copies, never references to another TU's __constant__ symbols.
struct Config{double vol0,rho0,rhow,solid0;float h,bwen,G;};
struct Material{StSoilCte soil;TpDPCtes fit;bool soft,trigger,require_elastic;};
struct Stage{
  unsigned np,npb,nstep;double time,dt;bool corrector;
  StDivDataGpu cells;const unsigned *cell,*id;const typecode* code;
  const double2* xy;const double* z;const float4* velocity;const double* J;
  const tsymatrix3d* sigma_base;const tsymatrix3f* sigma_rate;const float* kappa;
  float3* ace;
};
struct Summary{
  unsigned error,invalid_id,invalid_slot,np,rows,max_degree,known_constant_rows;
  unsigned elastic,smooth,apex,tension,material_checked;
  unsigned kept,born,dead;unsigned long long pre_calls,cor_calls,commits;
  double source_time,dt,condition,lambda,dt_over_limit,min_r,max_local_angle;
  double gamma_min,gamma_max,material_root_ratio;
  double Eold,Ekept,Edead,Enew,row_work,node_work,loading_loss,rotation_change,ledger;
  double adjoint_defect,adjoint_budget,net_x,net_z,torque,net_budget,torque_budget,ledger_budget;
  double max_force,max_delta_ace,max_commit_error,commit_budget;
};
// Run owns this object and destroys it before JSphGpu's cudaDeviceReset, also on exception.
// Default construction allocates nothing; only the explicitly ON first StageForce allocates.
class State{
  void* impl_;
public:
  State();~State() noexcept;
  State(const State&)=delete;State& operator=(const State&)=delete;
  void StageForce(const Config&,const Material&,const Stage&);
  // Called immediately AFTER the unchanged real predictor/corrector method returns.
  // Expected six stress components and predictor-old/full-returned kappa are keyed by native ID.
  void CheckMaterial(unsigned np,unsigned npb,const unsigned* id,const typecode* code,
    const tsymatrix3d* sigma,const float* kappa,bool corrector);
  // Only after the real full update, completed cell divide and actual scalar +=dt.
  void Accept(unsigned np,unsigned npb,const unsigned* id,const typecode* code,
    unsigned completed,double saved_time,double dt);
  void Save(const std::string& dir,unsigned completed,double saved_time);
  const Summary& Latest()const;
};
}
#endif
