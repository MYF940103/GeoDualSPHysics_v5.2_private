#include "mcc_model.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

using mcc::Matrix;
using mcc::Params;
using mcc::StepRow;

void write_rows(const fs::path &path,const std::vector<StepRow> &rows) {
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "step,path,eps_xx,eps_yy,eps_zz,eps_xy,eps_yz,eps_xz,eps_v,"
      << "stress_xx,stress_yy,stress_zz,stress_xy,stress_yz,stress_xz,"
      << "sigmac_xx,sigmac_yy,sigmac_zz,p,q,pc,e,eps_p_v,eps_p_eq,"
      << "plastic_multiplier,yield_f,yield_f_normalized,return_status,yield_flag,"
      << "iterations,residual,pore_pressure_proxy\n";
  for(const auto &r:rows) {
    out << r.step << ',' << r.path << ','
        << r.eps_xx << ',' << r.eps_yy << ',' << r.eps_zz << ','
        << r.eps_xy << ',' << r.eps_yz << ',' << r.eps_xz << ',' << r.eps_v << ','
        << r.stress_xx << ',' << r.stress_yy << ',' << r.stress_zz << ','
        << r.stress_xy << ',' << r.stress_yz << ',' << r.stress_xz << ','
        << r.sigmac_xx << ',' << r.sigmac_yy << ',' << r.sigmac_zz << ','
        << r.p << ',' << r.q << ',' << r.pc << ',' << r.e << ','
        << r.eps_p_v << ',' << r.eps_p_eq << ',' << r.plastic_multiplier << ','
        << r.yield_f << ',' << r.yield_f_normalized << ',' << r.return_status << ','
        << r.yield_flag << ',' << r.iterations << ',' << r.residual << ','
        << r.pore_pressure_proxy << '\n';
  }
}

void write_sign(const fs::path &path,const Params &params) {
  const Matrix sigmac=mcc::principal_diag(-50.0,-50.0,-50.0);
  const Matrix internal=mcc::from_sigmac_negative_compression(sigmac);
  const auto inv=mcc::invariants(internal);
  const Matrix back=mcc::to_sigmac_negative_compression(internal);
  const int passed=(inv.p>0.0 && std::abs(inv.q)<1.0e-12 && back[0][0]<0.0? 1: 0);
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "test,sigmac_xx_input,sigmac_yy_input,sigmac_zz_input,p_internal,q_internal,"
      << "sigmac_xx_roundtrip,sigmac_yy_roundtrip,sigmac_zz_roundtrip,passed,M,lambda,kappa,e0,pc0\n";
  out << "hydrostatic_compression,"
      << sigmac[0][0] << ',' << sigmac[1][1] << ',' << sigmac[2][2] << ','
      << inv.p << ',' << inv.q << ','
      << back[0][0] << ',' << back[1][1] << ',' << back[2][2] << ','
      << passed << ',' << params.m << ',' << params.lambda << ',' << params.kappa << ','
      << params.e0 << ',' << params.pc0 << '\n';
}

struct ConsistencyRow {
  std::string path;
  int steps=0;
  int plastic_steps=0;
  double max_abs_yield_f_plastic=0.0;
  double max_normalized_yield_f_plastic=0.0;
  double max_abs_return_residual_plastic=0.0;
  int max_iterations=0;
  const StepRow *final=nullptr;
  double tolerance=0.0;
};

ConsistencyRow consistency(const std::string &name,const std::vector<StepRow> &rows,const Params &params) {
  ConsistencyRow c;
  c.path=name;
  c.steps=static_cast<int>(rows.size())-1;
  c.tolerance=params.return_tolerance;
  c.final=&rows.back();
  for(const auto &r:rows) {
    if(r.yield_flag==1) {
      c.plastic_steps++;
      c.max_abs_yield_f_plastic=std::max(c.max_abs_yield_f_plastic,std::abs(r.yield_f));
      c.max_normalized_yield_f_plastic=std::max(c.max_normalized_yield_f_plastic,r.yield_f_normalized);
      c.max_abs_return_residual_plastic=std::max(c.max_abs_return_residual_plastic,std::abs(r.residual));
      c.max_iterations=std::max(c.max_iterations,r.iterations);
    }
  }
  return c;
}

void write_consistency(const fs::path &path,const std::vector<ConsistencyRow> &rows) {
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "path,steps,plastic_steps,max_abs_yield_f_plastic,max_normalized_yield_f_plastic,"
      << "max_abs_return_residual_plastic,max_iterations,final_p,final_q,final_pc,final_e,"
      << "final_eps_p_v,final_eps_p_eq,tolerance\n";
  for(const auto &r:rows) {
    const auto &f=*r.final;
    out << r.path << ',' << r.steps << ',' << r.plastic_steps << ','
        << r.max_abs_yield_f_plastic << ',' << r.max_normalized_yield_f_plastic << ','
        << r.max_abs_return_residual_plastic << ',' << r.max_iterations << ','
        << f.p << ',' << f.q << ',' << f.pc << ',' << f.e << ','
        << f.eps_p_v << ',' << f.eps_p_eq << ',' << r.tolerance << '\n';
  }
}

void write_iterations(const fs::path &path,const std::map<std::string,std::vector<StepRow>> &paths) {
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "path,step,yield_flag,return_status,iterations,residual,yield_f,yield_f_normalized,plastic_multiplier\n";
  for(const auto &kv:paths) {
    for(const auto &r:kv.second) {
      out << kv.first << ',' << r.step << ',' << r.yield_flag << ',' << r.return_status << ','
          << r.iterations << ',' << r.residual << ',' << r.yield_f << ','
          << r.yield_f_normalized << ',' << r.plastic_multiplier << '\n';
    }
  }
}

void write_summary(const fs::path &path,const std::map<std::string,std::vector<StepRow>> &paths,const Params &params) {
  std::ofstream out(path);
  out << std::setprecision(17);
  out << "case,steps,plastic_steps,failed_steps,final_p,final_q,final_pc,final_e,"
      << "final_eps_p_v,final_eps_p_eq,max_iterations,max_abs_yield_f,max_normalized_yield_f,"
      << "max_abs_residual,M,lambda,kappa,e0,pc0,E,nu\n";
  for(const auto &kv:paths) {
    int plastic=0, failed=0, maxiter=0;
    double maxf=0.0, maxfn=0.0, maxres=0.0;
    for(const auto &r:kv.second) {
      if(r.yield_flag==1) plastic++;
      if(r.return_status.find("failure")!=std::string::npos || r.return_status.find("tension")!=std::string::npos) failed++;
      maxiter=std::max(maxiter,r.iterations);
      maxf=std::max(maxf,std::abs(r.yield_f));
      maxfn=std::max(maxfn,r.yield_f_normalized);
      maxres=std::max(maxres,std::abs(r.residual));
    }
    const auto &f=kv.second.back();
    out << kv.first << ',' << (static_cast<int>(kv.second.size())-1) << ',' << plastic << ',' << failed << ','
        << f.p << ',' << f.q << ',' << f.pc << ',' << f.e << ',' << f.eps_p_v << ','
        << f.eps_p_eq << ',' << maxiter << ',' << maxf << ',' << maxfn << ',' << maxres << ','
        << params.m << ',' << params.lambda << ',' << params.kappa << ',' << params.e0 << ','
        << params.pc0 << ',' << params.young << ',' << params.poisson << '\n';
  }
}

} // namespace

int main(int argc,char **argv) {
  try {
    Params params;
    params.validate();
    fs::path outdir = (argc>1? fs::path(argv[1]): fs::path("output"));
    fs::create_directories(outdir);

    const auto iso=mcc::isotropic_path(params);
    const auto drained=mcc::drained_like_path(params);
    const auto undrained=mcc::undrained_like_path(params);
    const std::map<std::string,std::vector<StepRow>> paths{
      {"isotropic",iso},
      {"drained_like",drained},
      {"undrained_like",undrained}
    };

    write_sign(outdir/"m3a_cpp_sign_regression.csv",params);
    write_rows(outdir/"m3a_cpp_isotropic_path.csv",iso);
    write_rows(outdir/"m3a_cpp_drained_triaxial_path.csv",drained);
    write_rows(outdir/"m3a_cpp_undrained_path.csv",undrained);
    write_iterations(outdir/"m3a_cpp_return_iterations.csv",paths);

    const std::vector<ConsistencyRow> crows{
      consistency("isotropic",iso,params),
      consistency("drained_like",drained,params),
      consistency("undrained_like",undrained,params)
    };
    write_consistency(outdir/"m3a_cpp_yield_consistency.csv",crows);
    write_summary(outdir/"m3a_cpp_test_summary.csv",paths,params);

    std::cout << "M3a C++ MCC single-point tests complete\n";
    for(const auto &kv:paths) {
      const auto &f=kv.second.back();
      std::cout << kv.first << ": final_p=" << f.p << " final_q=" << f.q
                << " final_pc=" << f.pc << '\n';
    }
    return 0;
  }
  catch(const std::exception &e) {
    std::cerr << "M3a C++ MCC driver failed: " << e.what() << '\n';
    return 1;
  }
}
