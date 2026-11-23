// C08 development candidate. S and R use the gamma-scaled Darcy row.
#pragma once
#include "TpiPressureRow.h"

namespace c08_m0 {
__host__ __device__ inline bool Correct(bool dirichlet, float pn, float previous,
    float iterate, double diagonal, double residual, double beta, double dt,
    float& pressure) {
  if(!tpi_pressure::Finite(beta) || beta<0. || !tpi_pressure::Finite(dt) || dt<=0.)
    return false;
  if(dirichlet) { pressure=0.f; return true; }
  if(!tpi_pressure::Finite(pn)) return false;
  if(beta==0. || pn>=0.f)
    return tpi_pressure::Endpoint(false,iterate,diagonal,residual,pressure);

  double alphaPressure;
  if(!tpi_pressure::Predict(tpi_pressure::Predictor::Linear,pn,previous,alphaPressure)
      || !tpi_pressure::Finite(diagonal) || diagonal<=0.) return false;
  const double capacity=beta/dt;
  return tpi_pressure::Endpoint(false,iterate,diagonal+capacity,
    residual+capacity*(alphaPressure-double(iterate)),pressure);
}
}
