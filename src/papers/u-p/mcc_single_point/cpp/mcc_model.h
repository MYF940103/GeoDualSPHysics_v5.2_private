#pragma once

#include <array>
#include <string>
#include <vector>

namespace mcc {

using Matrix = std::array<std::array<double,3>,3>;

struct Params {
  double m = 1.2;
  double lambda = 0.20;
  double kappa = 0.04;
  double e0 = 0.80;
  double pc0 = 160.0;
  double young = 5000.0;
  double poisson = 0.30;
  double tension_cutoff = 1.0e-5;
  double return_tolerance = 1.0e-8;
  int return_max_iter = 45;
  int max_line_search = 12;

  double bulk() const;
  double shear() const;
  void validate() const;
};

struct State {
  Matrix stress{};
  double pc = 0.0;
  double e = 0.0;
  double eps_p_v = 0.0;
  double eps_p_eq = 0.0;
  double plastic_multiplier = 0.0;
  int yield_flag = 0;
  std::string return_status = "initial";
  int iterations = 0;
  double residual = 0.0;
};

struct Invariants {
  double p = 0.0;
  double q = 0.0;
  double j2 = 0.0;
};

struct StepRow {
  int step = 0;
  std::string path;
  double eps_xx = 0.0;
  double eps_yy = 0.0;
  double eps_zz = 0.0;
  double eps_xy = 0.0;
  double eps_yz = 0.0;
  double eps_xz = 0.0;
  double eps_v = 0.0;
  double stress_xx = 0.0;
  double stress_yy = 0.0;
  double stress_zz = 0.0;
  double stress_xy = 0.0;
  double stress_yz = 0.0;
  double stress_xz = 0.0;
  double sigmac_xx = 0.0;
  double sigmac_yy = 0.0;
  double sigmac_zz = 0.0;
  double p = 0.0;
  double q = 0.0;
  double pc = 0.0;
  double e = 0.0;
  double eps_p_v = 0.0;
  double eps_p_eq = 0.0;
  double plastic_multiplier = 0.0;
  double yield_f = 0.0;
  double yield_f_normalized = 0.0;
  std::string return_status;
  int yield_flag = 0;
  int iterations = 0;
  double residual = 0.0;
  double pore_pressure_proxy = 0.0;
};

Matrix eye(double scale=1.0);
Matrix zeros();
Matrix principal_diag(double x,double y,double z);
Matrix add(const Matrix &a,const Matrix &b);
Matrix sub(const Matrix &a,const Matrix &b);
Matrix scale(const Matrix &a,double s);
double trace(const Matrix &a);
Matrix deviator(const Matrix &a);
double tensor_dot(const Matrix &a,const Matrix &b);
Invariants invariants(const Matrix &stress);
Matrix to_sigmac_negative_compression(const Matrix &stress_cp);
Matrix from_sigmac_negative_compression(const Matrix &sigmac);
double yield_function(double p,double q,double pc,const Params &params);
Matrix elastic_predictor(const Matrix &stress,const Matrix &strain_inc,const Params &params);
State make_initial_state(double p0,const Params &params,double q0=0.0);
State return_mapping(const Matrix &trial_stress,const State &old,const Params &params);
State update_state(const State &old,const Matrix &strain_inc,const Params &params);
StepRow record_step(int step,const std::string &path,const Matrix &strain_inc,const State &state,const Params &params,double pore_pressure_proxy=0.0);

std::vector<StepRow> run_path(const std::string &path,const std::vector<Matrix> &increments,const Params &params,double p0=100.0);
std::vector<StepRow> isotropic_path(const Params &params);
std::vector<StepRow> drained_like_path(const Params &params);
std::vector<StepRow> undrained_like_path(const Params &params);

} // namespace mcc
