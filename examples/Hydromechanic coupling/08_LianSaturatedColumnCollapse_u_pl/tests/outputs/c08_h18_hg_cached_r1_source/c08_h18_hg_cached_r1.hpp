// Private C08 single-producer energy-normalized HG/cache candidate; public ABI unchanged.
#ifndef C08_H18_HG_CACHED_R1_HPP
#define C08_H18_HG_CACHED_R1_HPP
#include "DualSphDef.h"
#include "JCellDivDataGpu.h"
#include "JSphGpuSimple_ker.h"
#include <cuda_runtime_api.h>
#include <string>
namespace c08cached {
constexpr unsigned Nodes=5000,FirstId=2060,Neighbors=128;
constexpr double Xi=.1,StepDt=.000005;
inline const char* Environment(){return "C08_HG_CACHED_H18";}
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
  unsigned material_produced,cache_consumed,cache_input_scalar_checks,cache_output_scalar_checks;
  unsigned kept,born,dead;unsigned long long pre_calls,cor_calls,commits;
  double source_time,dt,condition,lambda,dt_over_limit,min_r,max_local_angle;
  double gamma_min,gamma_max,material_root_ratio;
  double Eold,Ekept,Edead,Enew,row_work,node_work,loading_loss,rotation_change,ledger;
  double adjoint_defect,adjoint_budget,net_x,net_z,torque,net_budget,torque_budget,ledger_budget;
  double max_force,max_delta_ace,max_commit_error,commit_budget;
};
class State{
  void* impl_;
public:
  State();~State() noexcept;
  State(const State&)=delete;State& operator=(const State&)=delete;
  void StageForce(const Config&,const Material&,const Stage&);
  // Prefix is the actual current source step/clock/native ID array. Remaining
  // arguments preserve the original public Simpleker wrapper order and types.
  void ConsumePre(unsigned nstep,double time,const unsigned* id,
    bool floating,bool shift,bool inout,TpDPCtes dpctes,unsigned np,unsigned npb,
    const float4* velrhoppre,const float* ar,const float3* ace,const float4* shiftposfs,
    const tsymatrix3d* sigmapre,const float* kplasticpre,const tsymatrix3f* rsigma,
    const float3* indirvel,double dtm,float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity,
    typecode* code,double2* movxy,double* movz,float4* velrhop,
    tsymatrix3d* sigma,float* kplastic,float* kplasticdk,cudaStream_t stm,
    cusphs::StPorosityRhopState porostate,unsigned* materialerror,bool requireelastic);
  void ConsumeCor(unsigned nstep,double time,const unsigned* id,
    bool floating,bool shift,bool inout,TpDPCtes dpctes,TpMdbc2Mode mdbc2,unsigned np,unsigned npb,
    const float4* velrhoppre,const float* ar,const float3* ace,const float4* shiftposfs,
    const tsymatrix3d* sigmapre,const float* kplasticpre,const tsymatrix3f* rsigma,
    const float3* indirvel,const float4* nopenshift,double dtm,double dt,
    float rhopzero,float rhopoutmin,float rhopoutmax,tfloat3 gravity,
    typecode* code,double2* movxy,double* movz,float4* velrhop,
    tsymatrix3d* sigma,float* kplastic,float* kplasticdk,cudaStream_t stm,
    cusphs::StPorosityRhopState porostate,unsigned* materialerror,bool requireelastic);
  // Exact cache-writeback check only: this is not a second material-return solve.
  void CheckMaterial(unsigned np,unsigned npb,const unsigned* id,const typecode* code,
    const tsymatrix3d* sigma,const float* kappa,bool corrector);
  void Accept(unsigned np,unsigned npb,const unsigned* id,const typecode* code,
    unsigned completed,double saved_time,double dt);
  void Save(const std::string& dir,unsigned completed,double saved_time);
  const Summary& Latest()const;
};
// Nonowning pointer only. The Run-local owner clears it before destroying State.
State* Current() noexcept;
void SetCurrent(State*);
}
#endif

