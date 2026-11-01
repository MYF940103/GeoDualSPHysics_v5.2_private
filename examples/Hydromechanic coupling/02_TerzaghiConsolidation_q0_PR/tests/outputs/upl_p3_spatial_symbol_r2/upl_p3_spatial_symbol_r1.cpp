// Frozen actual-header moments/symbols only. No JSph object or project solver.
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
int main(int argc,char** argv){try{
  Need(argc==10,"Use INITIAL_STATES NEW_CSV K G KW N RHO RHOW");
  const double K=std::stod(argv[3]),G=std::stod(argv[4]),kw=std::stod(argv[5]),n=std::stod(argv[6]),rho=std::stod(argv[7]),rhow=std::stod(argv[8]);
  // argc also binds the original mass, which must describe the retained lattice.
  const double mass0=std::stod(argv[9]),Lx=.125,Lz=.0625,k=2*acos(-1.)/Lx;
  Need(mass0/rho==1./16384.,"Retained mass/volume changed");
  std::ifstream initial(argv[1],std::ios::binary);unsigned header[3];double time=1;
  initial.read(reinterpret_cast<char*>(header),sizeof(header));initial.read(reinterpret_cast<char*>(&time),8);
  Need(initial&&header[0]==128&&header[1]==26&&header[2]==257&&time==0,"Wrong retained native initial state");
  std::vector<std::array<double,2>> retained;std::array<bool,128> found{};
  for(unsigned i=0;i<128;i++){
    std::array<double,26> r;initial.read(reinterpret_cast<char*>(r.data()),26*8);Need(bool(initial),"Truncated retained initial state");
    const double ix=r[0]*128-.5,iz=r[2]*128-.5;
    Need(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<16&&iz>=0&&iz<8&&r[1]==0,"Retained seed is not the prescribed dyadic lattice");
    const unsigned key=unsigned(ix)+16*unsigned(iz);Need(!found[key],"Duplicate retained lattice coordinate");found[key]=true;retained.push_back({r[0],r[2]});
  }
  Need(!std::filesystem::exists(argv[2]),"Retained symbols protected");
  std::ofstream csv(argv[2]);csv<<std::setprecision(17)<<"nx,nz,native,dp,h,Eta2,V,Vstress_float,K,G,Kw,n,rho,rhow,k_cont,neighbors,Mxx,Mxz,Mzx,Mzz,Mraw_xx,Mraw_xz,Mraw_zx,Mraw_zz,Cxx,Cxz,Czx,Czz,corrected_moment_max_error,Lquad_xx,Lquad_xz,Lquad_zz,constant_grad_max,Lx_max,Kr,Ks,Ksig,Ka,ell\n";
  for(unsigned nx:{16u,32u,64u}){
    const unsigned nz=nx/2;const double dp=Lx/nx,V=dp*dp,Vs=double(float(V));
    const double h=double(float(1.8*dp));const float hf=float(h),support=float(2*h),support2=support*support,eta2=float((h*.1)*(h*.1));
    Need(support<Lz*.5,"Minimum-image support overlaps multiple images");const auto kernel=fsph::GetKernelWendland_Ctes(true,h);
    std::vector<std::array<double,2>> points;
    if(nx==16)points=retained;else for(unsigned z=0;z<nz;z++)for(unsigned x=0;x<nx;x++)points.push_back({(x+.5)*dp,(z+.5)*dp});
    const auto base=points.front();double mxx=0,mxz=0,mzx=0,mzz=0,mrxx=0,mrxz=0,mrzx=0,mrzz=0,rawx=0,rawz=0,kr=0,stressx=0,stressz=0,gx0=0,gz0=0,firstscale=0;unsigned count=0;
    struct Pair{double x,z,rr,gx,gz;};std::vector<Pair> pairs;
    for(const auto& point:points){
      double x=base[0]-point[0],z=base[1]-point[1];x-=Lx*std::round(x/Lx);z-=Lz*std::round(z/Lz);
      const double rr=x*x+z*z;if(rr>support2||rr<ALMOSTZERO)continue;
      const double fac=fsph::GetKernelWendland_Fac(kernel,hf,float(rr)),gx=fac*x,gz=fac*z,sn=sin(k*x);
      const float dx=float(x),dz=float(z),ff=fsph::GetKernelWendland_Fac(kernel,hf,dx*dx+dz*dz);const double gfx=double(ff*dx),gfz=double(ff*dz);
      mxx-=V*x*gx;mxz-=V*x*gz;mzx-=V*z*gx;mzz-=V*z*gz;
      mrxx-=V*x*gfx;mrxz-=V*x*gfz;mrzx-=V*z*gfx;mrzz-=V*z*gfz;
      kr-=V*sn*gfx;rawx-=V*sn*gx;rawz-=V*sn*gz;stressx-=Vs*sn*gfx;stressz-=Vs*sn*gfz;
      gx0+=V*gx;gz0+=V*gz;firstscale+=fabs(V*gx)+fabs(V*gz);count++;pairs.push_back({x,z,rr,gx,gz});
    }
    Need(count==36,"Fixed-ratio lattice did not retain36 neighbors");const double det=mxx*mzz-mxz*mzx;Need(det>0,"Singular moment matrix");
    const double cxx=mzz/det,cxz=-mxz/det,czx=-mzx/det,czz=mxx/det;
    const double affine=(std::max)({fabs(cxx*mxx+cxz*mzx-1),fabs(cxx*mxz+cxz*mzz),fabs(czx*mxx+czz*mzx),fabs(czx*mxz+czz*mzz-1)});
    double qxx=0,qxz=0,qzz=0,lx=0,lz=0,ell=0,lscale=0;
    for(const auto& p:pairs){
      const double cgx=cxx*p.gx+cxz*p.gz,cgz=czx*p.gx+czz*p.gz;
      const double beta=(p.x*cgx+p.z*cgz)/(p.rr+eta2),w=2*V*beta;
      qxx-=V*beta*p.x*p.x;qxz-=2*V*beta*p.x*p.z;qzz-=V*beta*p.z*p.z;
      lx+=w*p.x;lz+=w*p.z;lscale+=fabs(w*p.x)+fabs(w*p.z);ell-=w*(1-cos(k*p.x));
    }
    const double g0=(std::max)(fabs(cxx*gx0+cxz*gz0),fabs(czx*gx0+czz*gz0));
    Need(affine<=32768*DBL_EPSILON&&g0<=32768*DBL_EPSILON*(std::max)(1.,firstscale)&&(std::max)(fabs(lx),fabs(lz))<=32768*DBL_EPSILON*(std::max)(1.,lscale),"Affine or constant cancellation failed");
    const double ks=cxx*rawx+cxz*rawz,ksig=cxx*stressx+cxz*stressz;Need(kr>0&&ks>0&&ksig>0&&ell>0,"Invalid fundamental symbols");
    csv<<nx<<','<<nz<<','<<points.size()<<','<<dp<<','<<h<<','<<eta2<<','<<V<<','<<Vs<<','<<K<<','<<G<<','<<kw<<','<<n<<','<<rho<<','<<rhow<<','<<k<<','<<count<<','<<mxx<<','<<mxz<<','<<mzx<<','<<mzz<<','<<mrxx<<','<<mrxz<<','<<mrzx<<','<<mrzz<<','<<cxx<<','<<cxz<<','<<czx<<','<<czz<<','<<affine<<','<<qxx<<','<<qxz<<','<<qzz<<','<<g0<<','<<(std::max)(fabs(lx),fabs(lz))<<','<<kr<<','<<ks<<','<<ksig<<','<<ks<<','<<ell<<'\n';
  }
  csv.flush();Need(bool(csv),"Symbol output failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
