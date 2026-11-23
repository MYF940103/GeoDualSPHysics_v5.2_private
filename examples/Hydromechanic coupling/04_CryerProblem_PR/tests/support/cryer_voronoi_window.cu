// Pair the two-point pressure difference with the same face's mean acceleration.
// All time stepping, mechanics and sealed-volume projection come from the weak window.
#define CRYER_VORONOI_WINDOW
#include "cryer_weak_window.cu"

API int uploadVoronoiFlux(int nz,const int* rows,const int* cols,const V* values){BEGIN_API
  const int n=ctx.n;
  Csr &flux=weak.hydraulicAcceleration;
  if(!ctx.x||!weak.stiffness.row||weakStarted||failed||completed||flux.row
     ||nz<=0||!rows||!cols||!values||rows[0]!=0||rows[n]!=nz)
    throw std::runtime_error("Invalid or duplicate Voronoi face flux");
  for(int i=0;i<n;i++)if(rows[i]>=rows[i+1])throw std::runtime_error("Empty or decreasing Voronoi row");
  for(int k=0;k<nz;k++)
    if(cols[k]<0||cols[k]>=n||!std::isfinite(values[k].x)||!std::isfinite(values[k].y)||!std::isfinite(values[k].z))
      throw std::runtime_error("Invalid Voronoi vector coefficient");
  upload(flux.row,rows,n+1);upload(flux.col,cols,nz);upload(flux.vector,values,nz);
  END_API}
