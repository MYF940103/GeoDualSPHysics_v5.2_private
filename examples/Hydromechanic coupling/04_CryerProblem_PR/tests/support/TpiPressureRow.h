// Private benchmark implementation of the beta-zero TPI pressure arithmetic.
#pragma once
#include <cfloat>
#include <cmath>

#ifdef __CUDACC__
#define TPI_ROW_HD __host__ __device__ inline
#else
#define TPI_ROW_HD inline
#endif

namespace tpi_pressure {
enum class Predictor { Current, Linear };

TPI_ROW_HD bool Finite(double x) {
#ifdef __CUDA_ARCH__
  return isfinite(x);
#else
  return std::isfinite(x);
#endif
}

// Pressure in storage is binary32. All operands are promoted before subtraction.
TPI_ROW_HD bool Predict(Predictor scheme,float pn,float previous,double& predicted) {
  if(!Finite(pn)) return false;
  if(scheme==Predictor::Current) { predicted=double(pn); return true; }
  if(scheme!=Predictor::Linear || !Finite(previous)) return false;
#ifdef __CUDA_ARCH__
  const double p=__dadd_rn(double(pn),__dmul_rn(0.5,__dsub_rn(double(pn),double(previous))));
#else
  const double p=double(pn)+0.5*(double(pn)-double(previous));
#endif
  if(!Finite(p) || p>FLT_MAX || p < -FLT_MAX) return false;
  predicted=p;
  return true;
}

TPI_ROW_HD float WritePressure(double pressure) {
#ifdef __CUDA_ARCH__
  return __double2float_rn(pressure);
#else
  return static_cast<float>(pressure);
#endif
}

// One complete endpoint defect. The caller supplies the actual pressure in
// the neighbor stencil, and applies the actual boundary policy before reuse.
TPI_ROW_HD bool Endpoint(bool drained,float iterated,double diagonal,double residual,float& written) {
  if(drained) { written=0.f; return true; }
  if(!Finite(iterated) || !Finite(diagonal) || diagonal<=0. || !Finite(residual)) return false;
#ifdef __CUDA_ARCH__
  const double corrected=__dadd_rn(double(iterated),__ddiv_rn(residual,diagonal));
#else
  const double corrected=double(iterated)+residual/diagonal;
#endif
  if(!Finite(corrected) || corrected>FLT_MAX || corrected < -FLT_MAX) return false;
  written=WritePressure(corrected);
  return true;
}
}
#undef TPI_ROW_HD
