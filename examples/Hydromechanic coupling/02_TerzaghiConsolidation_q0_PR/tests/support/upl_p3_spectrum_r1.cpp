// Actual-header frozen symbols only: no JSph object or project solver.
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <vector>
#include <fstream>
#include <iomanip>
#include <cmath>
#include <cfloat>
#include <filesystem>
#include <iostream>
#include <stdexcept>
static void Need(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
struct Symbol{double kr=0,ks=0,ksig=0,ell=0,mxx=0,cxx=0,lx=0,g0=0,scale=0;unsigned count=0;};
int main(int argc,char** argv){try{
  Need(argc==11,"Use STATES NEW_CSV H K G KW N0 RHO0 MASS0 RHOW");
  const double h=double(float(std::stod(argv[3]))),K=std::stod(argv[4]),G=std::stod(argv[5]),kw=std::stod(argv[6]),n0=std::stod(argv[7]),rho0=std::stod(argv[8]),V0=std::stod(argv[9])/rho0,rhow=std::stod(argv[10]);
  const float hf=float(h),support=float(2*h),support2=support*support,eta2=float((h*.1)*(h*.1));
  const auto kernel=fsph::GetKernelWendland_Ctes(true,h);const double Lx=.125,Lz=.0625;
  Need(!std::filesystem::exists(argv[2]),"Retained symbols protected");
  std::ifstream bin(argv[1],std::ios::binary);unsigned header[3];double time;
  bin.read(reinterpret_cast<char*>(header),sizeof(header));bin.read(reinterpret_cast<char*>(&time),8);
  Need(bin&&header[0]==128&&header[1]==26&&header[2]==257&&time==0,"Wrong retained initial-state header");
  std::vector<std::array<double,26>> nodes(128);for(auto& row:nodes)bin.read(reinterpret_cast<char*>(row.data()),26*8);
  Need(bool(bin)&&2*h<Lz*.5,"Initial positions/support invalid");
  auto Delta=[&](unsigned i,unsigned j){double x=nodes[i][0]-nodes[j][0],z=nodes[i][2]-nodes[j][2];x-=Lx*std::round(x/Lx);z-=Lz*std::round(z/Lz);return std::array<double,2>{x,z};};
  std::ofstream csv(argv[2]);csv<<std::setprecision(17)<<"J,m,k_cont,h,Eta2,V,Vstress_float,n,rho,K,G,Kw,rhow,Mxx,Cxx,Kr,Ks,Ksig,Ka,ell,receiver_max_variation,constant_grad_x,Lx_x,neighbors\n";
  for(double J:{1.,1.01})for(unsigned mode=1;mode<=7;mode++){
    const double V=V0*J,Vs=double(float(V)),n=1-(1-n0)/J,rho=rhow+(rho0-rhow)/J,k=2*acos(-1.)*mode/Lx;std::vector<Symbol> syms;
    for(unsigned i=0;i<128;i++){
      Symbol s;double mxz=0,mzz=0,rawx=0,rawz=0,stressx=0,stressz=0,sgx=0,sgz=0;
      for(unsigned j=0;j<128;j++)if(i!=j){
        const auto d=Delta(i,j);const double rr=d[0]*d[0]+d[1]*d[1];if(rr>support2||rr<ALMOSTZERO)continue;
        const double fac=fsph::GetKernelWendland_Fac(kernel,hf,float(rr)),gx=fac*d[0],gz=fac*d[1];
        const float dx=float(d[0]),dz=float(d[1]),ff=fsph::GetKernelWendland_Fac(kernel,hf,dx*dx+dz*dz);const double gfx=double(ff*dx),gfz=double(ff*dz),sn=sin(k*d[0]);
        s.mxx-=V*d[0]*gx;mxz-=V*d[0]*gz;mzz-=V*d[1]*gz;
        s.kr-=V*sn*gfx;rawx-=V*sn*gx;rawz-=V*sn*gz;stressx-=Vs*sn*gfx;stressz-=Vs*sn*gfz;
        sgx+=V*gx;sgz+=V*gz;s.scale+=fabs(V*gx)+fabs(V*gz);s.count++;
      }
      const double det=s.mxx*mzz-mxz*mxz;Need(det>0&&s.count==36,"Initial inverse moment/support invalid");
      const double cxx=mzz/det,cxz=-mxz/det,czz=s.mxx/det;s.cxx=cxx;s.ks=cxx*rawx+cxz*rawz;s.ksig=cxx*stressx+cxz*stressz;s.g0=cxx*sgx+cxz*sgz;
      double lxscale=0;
      for(unsigned j=0;j<128;j++)if(i!=j){
        const auto d=Delta(i,j);const double rr=d[0]*d[0]+d[1]*d[1];if(rr>support2||rr<ALMOSTZERO)continue;
        const double fac=fsph::GetKernelWendland_Fac(kernel,hf,float(rr)),gx=fac*d[0],gz=fac*d[1],cx=cxx*gx+cxz*gz,cz=cxz*gx+czz*gz;
        const double w=2*V*(d[0]*cx+d[1]*cz)/(rr+eta2);s.ell-=w*(1-cos(k*d[0]));s.lx+=w*d[0];lxscale+=fabs(w*d[0]);
      }
      Need(fabs(s.g0)<=32768*DBL_EPSILON*(std::max)(1.,s.scale)&&fabs(s.lx)<=32768*DBL_EPSILON*(std::max)(1.,lxscale),"Constant-gradient/Lx roundoff guard failed");syms.push_back(s);
    }
    const auto a=syms.front();double variation=0;for(const auto& b:syms)for(double error:{fabs(a.kr-b.kr),fabs(a.ks-b.ks),fabs(a.ksig-b.ksig),fabs(a.ell-b.ell)})variation=(std::max)(variation,error);
    Need(variation<=32768*DBL_EPSILON*(std::max)(1.,fabs(a.ell))&&a.kr>0&&a.ks>0&&a.ksig>0&&a.ell>0,"Nonuniform/invalid initial Fourier symbols");
    csv<<J<<','<<mode<<','<<k<<','<<h<<','<<eta2<<','<<V<<','<<Vs<<','<<n<<','<<rho<<','<<K<<','<<G<<','<<kw<<','<<rhow<<','<<a.mxx<<','<<a.cxx<<','<<a.kr<<','<<a.ks<<','<<a.ksig<<','<<a.ks<<','<<a.ell<<','<<variation<<','<<a.g0<<','<<a.lx<<','<<a.count<<'\n';
  }
  csv.flush();Need(csv.good(),"Symbols output failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
