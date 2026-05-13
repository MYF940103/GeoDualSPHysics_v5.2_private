#include "mcc_model.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace mcc {

double Params::bulk() const {
  return young/(3.0*(1.0-2.0*poisson));
}

double Params::shear() const {
  return young/(2.0*(1.0+poisson));
}

void Params::validate() const {
  if(!(m>0.0)) throw std::runtime_error("MCC M must be positive.");
  if(!(lambda>kappa && kappa>0.0)) throw std::runtime_error("MCC lambda must be greater than kappa > 0.");
  if(!(e0>-1.0)) throw std::runtime_error("Initial void ratio must be greater than -1.");
  if(!(pc0>0.0)) throw std::runtime_error("Initial preconsolidation pressure must be positive.");
  if(!(young>0.0 && poisson>-1.0 && poisson<0.5)) throw std::runtime_error("Elastic E/nu values are invalid.");
  if(!(return_tolerance>0.0 && return_max_iter>0)) throw std::runtime_error("Return mapping tolerance/iteration settings are invalid.");
}

Matrix eye(double scale) {
  return Matrix{{{{scale,0.0,0.0}},{{0.0,scale,0.0}},{{0.0,0.0,scale}}}};
}

Matrix zeros() {
  return eye(0.0);
}

Matrix principal_diag(double x,double y,double z) {
  return Matrix{{{{x,0.0,0.0}},{{0.0,y,0.0}},{{0.0,0.0,z}}}};
}

Matrix add(const Matrix &a,const Matrix &b) {
  Matrix out=zeros();
  for(int i=0;i<3;i++) for(int j=0;j<3;j++) out[i][j]=a[i][j]+b[i][j];
  return out;
}

Matrix sub(const Matrix &a,const Matrix &b) {
  Matrix out=zeros();
  for(int i=0;i<3;i++) for(int j=0;j<3;j++) out[i][j]=a[i][j]-b[i][j];
  return out;
}

Matrix scale(const Matrix &a,double s) {
  Matrix out=zeros();
  for(int i=0;i<3;i++) for(int j=0;j<3;j++) out[i][j]=a[i][j]*s;
  return out;
}

double trace(const Matrix &a) {
  return a[0][0]+a[1][1]+a[2][2];
}

Matrix deviator(const Matrix &a) {
  return sub(a,eye(trace(a)/3.0));
}

double tensor_dot(const Matrix &a,const Matrix &b) {
  double total=0.0;
  for(int i=0;i<3;i++) for(int j=0;j<3;j++) total+=a[i][j]*b[i][j];
  return total;
}

Invariants invariants(const Matrix &stress) {
  Invariants inv;
  inv.p=trace(stress)/3.0;
  const Matrix s=deviator(stress);
  inv.j2=0.5*tensor_dot(s,s);
  inv.q=std::sqrt(std::max(0.0,3.0*inv.j2));
  return inv;
}

Matrix to_sigmac_negative_compression(const Matrix &stress_cp) {
  return scale(stress_cp,-1.0);
}

Matrix from_sigmac_negative_compression(const Matrix &sigmac) {
  return scale(sigmac,-1.0);
}

double yield_function(double p,double q,double pc,const Params &params) {
  return q*q+params.m*params.m*p*(p-pc);
}

Matrix elastic_predictor(const Matrix &stress,const Matrix &strain_inc,const Params &params) {
  const double eps_v=trace(strain_inc);
  const Matrix dev_eps=deviator(strain_inc);
  const Matrix dstress=add(eye(params.bulk()*eps_v),scale(dev_eps,2.0*params.shear()));
  return add(stress,dstress);
}

static double norm4(const std::array<double,4> &v) {
  double total=0.0;
  for(const double x:v) total+=x*x;
  return std::sqrt(total);
}

static std::array<double,4> residual4(const std::array<double,4> &x,double p_tr,double q_tr,double pc_old,double e_old,const Params &params) {
  const double p=x[0], q=x[1], pc=x[2], dl=x[3];
  const double a=params.m*params.m;
  const double h=(1.0+e_old)/(params.lambda-params.kappa);
  const double df_dp=a*(2.0*p-pc);
  const double df_dq=2.0*q;
  const double depv=dl*df_dp;
  const double expo=std::max(-60.0,std::min(60.0,h*depv));
  const double pc_hard=pc_old*std::exp(expo);
  return std::array<double,4>{{
    p-p_tr+params.bulk()*dl*df_dp,
    q-q_tr+3.0*params.shear()*dl*df_dq,
    pc-pc_hard,
    yield_function(p,q,pc,params)
  }};
}

static std::array<std::array<double,4>,4> numeric_jacobian(const std::array<double,4> &x,double p_tr,double q_tr,double pc_old,double e_old,const Params &params) {
  const auto base=residual4(x,p_tr,q_tr,pc_old,e_old,params);
  std::array<std::array<double,4>,4> jac{};
  for(int c=0;c<4;c++) {
    const double step=1.0e-6*std::max(1.0,std::abs(x[c]));
    auto xp=x;
    xp[c]+=step;
    const auto rp=residual4(xp,p_tr,q_tr,pc_old,e_old,params);
    for(int r=0;r<4;r++) jac[r][c]=(rp[r]-base[r])/step;
  }
  return jac;
}

static std::array<double,4> solve_linear4(std::array<std::array<double,4>,4> a,std::array<double,4> b) {
  std::array<std::array<double,5>,4> mat{};
  for(int i=0;i<4;i++) {
    for(int j=0;j<4;j++) mat[i][j]=a[i][j];
    mat[i][4]=b[i];
  }
  for(int col=0;col<4;col++) {
    int pivot=col;
    for(int r=col+1;r<4;r++) {
      if(std::abs(mat[r][col])>std::abs(mat[pivot][col])) pivot=r;
    }
    if(std::abs(mat[pivot][col])<1.0e-18) throw std::runtime_error("Singular Newton Jacobian.");
    if(pivot!=col) std::swap(mat[pivot],mat[col]);
    const double piv=mat[col][col];
    for(int j=col;j<5;j++) mat[col][j]/=piv;
    for(int r=0;r<4;r++) {
      if(r==col) continue;
      const double fac=mat[r][col];
      if(fac==0.0) continue;
      for(int j=col;j<5;j++) mat[r][j]-=fac*mat[col][j];
    }
  }
  return std::array<double,4>{{mat[0][4],mat[1][4],mat[2][4],mat[3][4]}};
}

static std::array<double,4> initial_plastic_guess(double p_tr,double q_tr,double pc_old,const Params &params) {
  const double f_tr=yield_function(p_tr,q_tr,pc_old,params);
  const double denom=std::max(params.bulk()*params.m*params.m+6.0*params.shear(),1.0);
  double dl=std::max(0.0,f_tr/(denom*std::max(std::abs(p_tr)+std::abs(q_tr)+std::abs(pc_old),1.0)));
  dl=std::min(dl,1.0e-2);
  const double q=std::max(0.0,q_tr/(1.0+6.0*params.shear()*dl));
  const double p=std::max(params.tension_cutoff,std::min(std::max(p_tr,params.tension_cutoff),pc_old*0.999));
  const double pc=std::max(pc_old,p+params.tension_cutoff);
  return std::array<double,4>{{p,q,pc,std::max(dl,1.0e-12)}};
}

State make_initial_state(double p0,const Params &params,double q0) {
  State state;
  state.stress=(q0==0.0? eye(p0): principal_diag(p0+2.0*q0/3.0,p0-q0/3.0,p0-q0/3.0));
  state.pc=params.pc0;
  state.e=params.e0;
  return state;
}

State return_mapping(const Matrix &trial_stress,const State &old,const Params &params) {
  const Invariants trial_inv=invariants(trial_stress);
  const double p_tr=trial_inv.p;
  const double q_tr=trial_inv.q;
  if(p_tr<=params.tension_cutoff) {
    State failed=old;
    failed.stress=trial_stress;
    failed.return_status="tension_cutoff";
    failed.residual=p_tr-params.tension_cutoff;
    return failed;
  }
  const double f_tr=yield_function(p_tr,q_tr,old.pc,params);
  const double fscale=std::max(q_tr*q_tr+params.m*params.m*p_tr*std::max(old.pc,p_tr),1.0);
  if(f_tr<=params.return_tolerance*fscale) {
    State elastic=old;
    elastic.stress=trial_stress;
    elastic.yield_flag=0;
    elastic.return_status="elastic";
    elastic.iterations=0;
    elastic.residual=f_tr;
    elastic.plastic_multiplier=0.0;
    return elastic;
  }

  auto x=initial_plastic_guess(p_tr,q_tr,old.pc,params);
  auto res=residual4(x,p_tr,q_tr,old.pc,old.e,params);
  double best_norm=norm4(res);
  std::string status="max_iter";
  int iterations=0;
  for(int it=1;it<=params.return_max_iter;it++) {
    iterations=it;
    std::array<double,4> dx{};
    try {
      const auto jac=numeric_jacobian(x,p_tr,q_tr,old.pc,old.e,params);
      std::array<double,4> rhs{};
      for(int i=0;i<4;i++) rhs[i]=-res[i];
      dx=solve_linear4(jac,rhs);
    }
    catch(const std::exception&) {
      status="jacobian_failure";
      break;
    }
    bool accepted=false;
    for(int ls=0;ls<=params.max_line_search;ls++) {
      const double fac=std::pow(0.5,ls);
      std::array<double,4> cand{};
      for(int i=0;i<4;i++) cand[i]=x[i]+fac*dx[i];
      if(cand[0]<=params.tension_cutoff || cand[1]<0.0 || cand[2]<=params.tension_cutoff || cand[3]<0.0) continue;
      bool finite=true;
      for(const double v:cand) if(!std::isfinite(v)) finite=false;
      if(!finite) continue;
      const auto rc=residual4(cand,p_tr,q_tr,old.pc,old.e,params);
      const double nc=norm4(rc);
      if(std::isfinite(nc) && nc<=best_norm*(1.0-1.0e-4*fac)+1.0e-18) {
        x=cand;
        res=rc;
        best_norm=nc;
        accepted=true;
        break;
      }
    }
    if(!accepted) {
      status="line_search_failure";
      break;
    }
    const double norm_scale=std::max(std::abs(x[2])*params.m*params.m*std::max(std::abs(x[0]),1.0),1.0);
    if(best_norm<=params.return_tolerance*norm_scale) {
      status="plastic_converged";
      break;
    }
  }

  const double p=x[0], q=x[1], pc=x[2], dl=x[3];
  const Matrix dev_tr=deviator(trial_stress);
  Matrix dev_new=zeros();
  if(q_tr>1.0e-14) dev_new=scale(dev_tr,q/q_tr);
  const Matrix new_stress=add(eye(p),dev_new);
  const double a=params.m*params.m;
  const double depv=dl*a*(2.0*p-pc);
  const double depeq=std::abs(dl)*std::sqrt(std::pow(a*(2.0*p-pc),2.0)+std::pow(2.0*q,2.0));

  State next=old;
  next.stress=new_stress;
  next.pc=pc;
  next.eps_p_v+=depv;
  next.eps_p_eq+=depeq;
  next.plastic_multiplier=dl;
  next.yield_flag=1;
  next.return_status=status;
  next.iterations=iterations;
  next.residual=yield_function(p,q,pc,params);
  return next;
}

State update_state(const State &old,const Matrix &strain_inc,const Params &params) {
  params.validate();
  const Matrix trial=elastic_predictor(old.stress,strain_inc,params);
  State next=return_mapping(trial,old,params);
  const double eps_v=trace(strain_inc);
  next.e=std::max(-0.999,old.e-(1.0+old.e)*eps_v);
  return next;
}

StepRow record_step(int step,const std::string &path,const Matrix &strain_inc,const State &state,const Params &params,double pore_pressure_proxy) {
  const Invariants inv=invariants(state.stress);
  const Matrix sigmac=to_sigmac_negative_compression(state.stress);
  const double yf=yield_function(inv.p,inv.q,state.pc,params);
  const double yscale=std::max(inv.q*inv.q+params.m*params.m*inv.p*std::max(state.pc,inv.p),1.0);
  StepRow row;
  row.step=step;
  row.path=path;
  row.eps_xx=strain_inc[0][0];
  row.eps_yy=strain_inc[1][1];
  row.eps_zz=strain_inc[2][2];
  row.eps_xy=strain_inc[0][1];
  row.eps_yz=strain_inc[1][2];
  row.eps_xz=strain_inc[0][2];
  row.eps_v=trace(strain_inc);
  row.stress_xx=state.stress[0][0];
  row.stress_yy=state.stress[1][1];
  row.stress_zz=state.stress[2][2];
  row.stress_xy=state.stress[0][1];
  row.stress_yz=state.stress[1][2];
  row.stress_xz=state.stress[2][0];
  row.sigmac_xx=sigmac[0][0];
  row.sigmac_yy=sigmac[1][1];
  row.sigmac_zz=sigmac[2][2];
  row.p=inv.p;
  row.q=inv.q;
  row.pc=state.pc;
  row.e=state.e;
  row.eps_p_v=state.eps_p_v;
  row.eps_p_eq=state.eps_p_eq;
  row.plastic_multiplier=state.plastic_multiplier;
  row.yield_f=yf;
  row.yield_f_normalized=std::abs(yf)/yscale;
  row.return_status=state.return_status;
  row.yield_flag=state.yield_flag;
  row.iterations=state.iterations;
  row.residual=state.residual;
  row.pore_pressure_proxy=pore_pressure_proxy;
  return row;
}

std::vector<StepRow> run_path(const std::string &path,const std::vector<Matrix> &increments,const Params &params,double p0) {
  State state=make_initial_state(p0,params);
  std::vector<StepRow> rows;
  rows.push_back(record_step(0,path,principal_diag(0.0,0.0,0.0),state,params,0.0));
  const double p_initial=invariants(state.stress).p;
  for(size_t i=0;i<increments.size();i++) {
    state=update_state(state,increments[i],params);
    const double pnow=invariants(state.stress).p;
    const double pore_proxy=(path.rfind("undrained",0)==0? p_initial-pnow: 0.0);
    rows.push_back(record_step(static_cast<int>(i)+1,path,increments[i],state,params,pore_proxy));
  }
  return rows;
}

std::vector<StepRow> isotropic_path(const Params &params) {
  std::vector<Matrix> inc;
  for(int i=0;i<90;i++) inc.push_back(principal_diag(1.5e-4,1.5e-4,1.5e-4));
  for(int i=0;i<45;i++) inc.push_back(principal_diag(-1.0e-4,-1.0e-4,-1.0e-4));
  for(int i=0;i<45;i++) inc.push_back(principal_diag(1.0e-4,1.0e-4,1.0e-4));
  return run_path("isotropic_compression_swelling",inc,params);
}

std::vector<StepRow> drained_like_path(const Params &params) {
  std::vector<Matrix> inc;
  for(int i=0;i<140;i++) inc.push_back(principal_diag(3.0e-4,0.0,0.0));
  return run_path("drained_like_triaxial_strain_control",inc,params);
}

std::vector<StepRow> undrained_like_path(const Params &params) {
  std::vector<Matrix> inc;
  for(int i=0;i<140;i++) inc.push_back(principal_diag(3.0e-4,-1.5e-4,-1.5e-4));
  return run_path("undrained_like_zero_volumetric_strain",inc,params);
}

} // namespace mcc
