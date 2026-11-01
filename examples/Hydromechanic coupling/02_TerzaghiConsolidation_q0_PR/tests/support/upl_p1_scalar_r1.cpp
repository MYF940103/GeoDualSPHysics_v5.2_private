// P1 standalone 2D scalar companion. Does not call a production force routine.
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Vec { double x=0,z=0; };
struct Mat { double xx=1,xz=0,zz=1; };
static Vec operator+(Vec a,Vec b){ return {a.x+b.x,a.z+b.z}; }
static Vec operator-(Vec a,Vec b){ return {a.x-b.x,a.z-b.z}; }
static Vec operator*(double b,Vec a){ return {b*a.x,b*a.z}; }
static double Dot(Vec a,Vec b){ return a.x*b.x+a.z*b.z; }
static Vec Apply(Mat c,Vec a){ return {c.xx*a.x+c.xz*a.z,c.xz*a.x+c.zz*a.z}; }
struct Node { unsigned id; int ix,iz; Vec p; Mat c; };
struct Edge { unsigned j; Vec d,g,b; double rr2; };
struct Grid {
  int n,ghost,side; double dp,h,volume; std::vector<Node> p;
  std::vector<std::vector<Edge>> edges;
};
static uint32_t Next(uint32_t& state){ state^=state<<13;state^=state>>17;state^=state<<5;return state; }
static double Jitter(uint32_t& state){ return (double(Next(state))/4294967295.-.5)*.3; }
static Grid MakeGrid(int n,int ghost,bool disorder){
  Grid a; a.n=n;a.ghost=ghost;a.side=n+2*ghost;a.dp=1./(n-1);a.h=1.8*a.dp;a.volume=a.dp*a.dp;
  uint32_t state=20261101;
  for(int iz=-ghost;iz<n+ghost;iz++)for(int ix=-ghost;ix<n+ghost;ix++){
    Vec p={ix*a.dp,iz*a.dp};
    if(disorder){ p.x+=Jitter(state)*a.dp;p.z+=Jitter(state)*a.dp; }
    a.p.push_back({unsigned(a.p.size()),ix,iz,p,{}});
  }
  a.edges.resize(a.p.size());
  const fsph::StKWendlandCte kw=fsph::GetKernelWendland_Ctes(true,a.h);
  const int reach=4; // 2h=3.6dp, plus maximum relative jitter .3dp.
  for(unsigned i=0;i<a.p.size();i++){
    const Node& pi=a.p[i];
    for(int dz=-reach;dz<=reach;dz++)for(int dx=-reach;dx<=reach;dx++){
      const int x=pi.ix+ghost+dx,z=pi.iz+ghost+dz;
      if(x<0||x>=a.side||z<0||z>=a.side)continue;
      const unsigned j=unsigned(z*a.side+x);if(i==j)continue;
      const Vec d=pi.p-a.p[j].p;const double rr2=Dot(d,d);
      if(rr2>4*a.h*a.h)continue;
      // Actual project API and its float arithmetic; local moments stay double.
      const double fac=fsph::GetKernelWendland_Fac(kw,float(a.h),float(rr2));
      a.edges[i].push_back({j,d,fac*d,{},rr2});
    }
    double mxx=0,mxz=0,mzz=0;
    for(const Edge& e:a.edges[i]){
      mxx-=a.volume*e.d.x*e.g.x;mxz-=a.volume*e.d.x*e.g.z;mzz-=a.volume*e.d.z*e.g.z;
    }
    const double det=mxx*mzz-mxz*mxz;
    if(!(det>1e-12))throw std::runtime_error("singular manufactured gradient moment");
    a.p[i].c={mzz/det,-mxz/det,mxx/det};
  }
  for(unsigned i=0;i<a.p.size();i++)for(Edge& e:a.edges[i])e.b=a.volume*Apply(a.p[i].c,e.g);
  return a;
}
static const char* Methods[]={"raw","receiverC","symC","raw_star","receiverC_star","symC_star"};
static const char* Fields[]={"constant","linear_x","linear_z","linear_mix","quadratic_x","quadratic_z","quadratic_xz","quadratic_mix","sine","hydrostatic_head"};
static double Field(int f,Vec p){
  switch(f){
    case 0:return 7.;case 1:return p.x;case 2:return p.z;case 3:return 1+3*p.x-2*p.z;
    case 4:return p.x*p.x;case 5:return p.z*p.z;case 6:return p.x*p.z;
    case 7:return p.x*p.x+.3*p.x*p.z+2*p.z*p.z;
    case 8:return std::sin(PI*p.x)*std::sin(PI*p.z);
    default:{const double pressure=10000.-9810.*p.z;return pressure+9810.*p.z;}
  }
}
static double ExactLap(int f,Vec p){ if(f==4||f==5)return 2.;if(f==7)return 6.;if(f==8)return -2*PI*PI*Field(f,p);return 0.; }
static Vec ExactGrad(int f){if(f==1)return {1,0};if(f==2)return {0,1};if(f==3)return {3,-2};return {};}
static double Weight(const Grid& a,unsigned i,const Edge& e,int base,double eta2){
  Vec g=e.g;
  if(base==1)g=Apply(a.p[i].c,g);
  if(base==2)g=.5*(Apply(a.p[i].c,g)+Apply(a.p[e.j].c,g));
  return 2*a.volume*Dot(e.d,g)/(e.rr2+eta2);
}
struct Value { double lap=0; Vec grad; Vec lx; };
static Value Evaluate(const Grid& a,unsigned i,const std::vector<double>& f,int method,double eta2){
  Value v;
  for(const Edge& e:a.edges[i]){
    const double df=f[e.j]-f[i];const double w=Weight(a,i,e,method%3,eta2);
    v.grad=v.grad+df*e.b;v.lap-=w*df;v.lx=v.lx+w*e.d;
  }
  if(method>=3)v.lap-=Dot(v.grad,v.lx);
  return v;
}
struct Error {
  double sum2=0,maxabs=0,gradmax=0,budget=0,exactbudget=0;unsigned count=0;
  void Add(double actual,double exact,Vec g,Vec eg,bool linear,double vol){
    const double e=actual-exact;sum2+=e*e;maxabs=std::max(maxabs,std::abs(e));
    if(linear)gradmax=std::max(gradmax,std::sqrt(Dot(g-eg,g-eg)));
    budget+=actual*vol;exactbudget+=exact*vol;count++;
  }
};
static bool IsCore(const Grid& a,const Node& p){return p.ix>=0&&p.iz>=0&&p.ix<a.n&&p.iz<a.n;}
static int Region(const Grid& a,const Node& p){return (p.ix>=4&&p.iz>=4&&p.ix<a.n-4&&p.iz<a.n-4)?0:1;}
static void PolynomialTests(const std::string& out,std::ofstream& errors,std::ofstream& gates){
  for(int n:{21,41,81})for(bool disorder:{false,true}){
    auto start=std::chrono::steady_clock::now();Grid a=MakeGrid(n,9,disorder);
    const std::string geom=(disorder?"disorder":"regular");
    std::ofstream nodes(out+"/nodes_"+geom+"_"+std::to_string(n)+".csv");nodes<<std::setprecision(17);
    nodes<<"id,ix,iz,x,z,volume,core,region,cxx,cxz,czz\n";
    for(const Node& p:a.p)nodes<<p.id<<','<<p.ix<<','<<p.iz<<','<<p.p.x<<','<<p.p.z<<','<<a.volume<<','<<IsCore(a,p)<<','<<(IsCore(a,p)?Region(a,p):-1)<<','<<p.c.xx<<','<<p.c.xz<<','<<p.c.zz<<'\n';
    std::ofstream native;
    if(n==21&&disorder){native.open(out+"/native_scalar_samples.csv");native<<std::setprecision(17)<<"id,eta,method,field,x,z,input,actual,exact,grad_x,grad_z,lx,lz\n";}
    double hydroPressureOnlyMax[2][6]={};
    for(int eta=0;eta<2;eta++)for(int method=0;method<6;method++){
      const double eta2=(eta?.01*a.h*a.h:0);
      for(int f=0;f<10;f++){
        std::vector<double> input;for(const Node& p:a.p)input.push_back(Field(f,p.p));
        std::array<Error,2> stat;
        for(unsigned i=0;i<a.p.size();i++)if(IsCore(a,a.p[i])){
          const Value v=Evaluate(a,i,input,method,eta2);const double exact=ExactLap(f,a.p[i].p);
          if(!std::isfinite(v.lap))throw std::runtime_error("nonfinite scalar field");
          stat[Region(a,a.p[i])].Add(v.lap,exact,v.grad,ExactGrad(f),f>=1&&f<=3,a.volume);
          if(native)native<<i<<','<<eta<<','<<Methods[method]<<','<<Fields[f]<<','<<a.p[i].p.x<<','<<a.p[i].p.z<<','<<input[i]<<','<<v.lap<<','<<exact<<','<<v.grad.x<<','<<v.grad.z<<','<<v.lx.x<<','<<v.lx.z<<'\n';
          if(f==0)gates<<"constant,"<<n<<','<<geom<<','<<eta<<','<<Methods[method]<<','<<std::abs(v.lap)<<",1e-10,"<<(std::abs(v.lap)<=1e-10)<<'\n';
          if(f>=1&&f<=3){
            const Vec d=v.grad-ExactGrad(f);const double ge=std::sqrt(Dot(d,d));
            gates<<"linear_gradient,"<<n<<','<<geom<<','<<eta<<','<<Methods[method]<<','<<ge<<",1e-10,"<<(ge<=1e-10)<<'\n';
            if(method>=3)gates<<"star_linear,"<<n<<','<<geom<<','<<eta<<','<<Methods[method]<<','<<std::abs(v.lap)<<",1e-8,"<<(std::abs(v.lap)<=1e-8)<<'\n';
          }
          if(f==9)gates<<"hydrostatic_head,"<<n<<','<<geom<<','<<eta<<','<<Methods[method]<<','<<std::abs(v.lap)<<",1e-6,"<<(std::abs(v.lap)<=1e-6)<<'\n';
        }
        for(int r=0;r<2;r++){
          const Error& e=stat[r];
          errors<<n<<','<<geom<<','<<eta<<','<<Methods[method]<<','<<Fields[f]<<','<<(r?"core_outer":"core_interior")<<','<<e.count<<','<<a.dp<<','<<a.h<<','<<std::sqrt(e.sum2/e.count)<<','<<e.maxabs<<','<<e.gradmax<<','<<e.budget<<','<<e.exactbudget<<'\n';
        }
      }
      // Literal pressure-only compensation with the uncompensated gravity coordinate
      // differs from applying the same corrected operator to the complete head.
      std::vector<double> pressure,z;
      for(const Node& p:a.p){pressure.push_back(10000.-9810*p.p.z);z.push_back(p.p.z);}
      for(unsigned i=0;i<a.p.size();i++)if(IsCore(a,a.p[i])){
        const double residual=Evaluate(a,i,pressure,method,eta2).lap+9810*Evaluate(a,i,z,method%3,eta2).lap;
        hydroPressureOnlyMax[eta][method]=std::max(hydroPressureOnlyMax[eta][method],std::abs(residual));
      }
    }
    std::ofstream timing(out+"/timing_"+geom+"_"+std::to_string(n)+".csv");
    timing<<std::setprecision(17)<<"nodes,edges,grid_diagnostics_elapsed_s,eta,method,pressure_only_hydro_residual_max\n";
    size_t ne=0;for(const auto& e:a.edges)ne+=e.size();
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    for(int eta=0;eta<2;eta++)for(int method=0;method<6;method++)timing<<a.p.size()<<','<<ne<<','<<seconds<<','<<eta<<','<<Methods[method]<<','<<hydroPressureOnlyMax[eta][method]<<'\n';
    // Separate descriptive operator microbenchmark: identical frozen input,
    // excluding setup and file writes. No inference about production overhead.
    std::vector<double> input;for(const Node& p:a.p)input.push_back(Field(8,p.p));
    std::ofstream micro(out+"/operator_timing_"+geom+"_"+std::to_string(n)+".csv");
    micro<<std::setprecision(17)<<"nodes,core_nodes,eta,method,repeats,evaluations,compute_s,checksum\n";
    const int repeats=25;
    for(int eta=0;eta<2;eta++)for(int method=0;method<6;method++){
      const double eta2=eta?.01*a.h*a.h:0;double checksum=0;
      auto begin=std::chrono::steady_clock::now();
      for(int r=0;r<repeats;r++)for(unsigned i=0;i<a.p.size();i++)if(IsCore(a,a.p[i]))checksum+=Evaluate(a,i,input,method,eta2).lap;
      const double compute=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
      micro<<a.p.size()<<','<<n*n<<','<<eta<<','<<Methods[method]<<','<<repeats<<','<<n*n*repeats<<','<<compute<<','<<checksum<<'\n';
    }
    std::cout<<"POLYNOMIAL "<<n<<' '<<geom<<" seconds="<<seconds<<'\n';
  }
}
static void MatrixTests(const std::string& out,std::ofstream& gates){
  for(bool disorder:{false,true}){
    Grid a=MakeGrid(9,0,disorder);const unsigned n=unsigned(a.p.size());
    std::ofstream nodes(out+"/matrix_nodes_"+(disorder?std::string("disorder"):std::string("regular"))+".csv");
    nodes<<std::setprecision(17)<<"id,x,z,volume\n";for(const Node& p:a.p)nodes<<p.id<<','<<p.p.x<<','<<p.p.z<<','<<a.volume<<'\n';
    for(int eta=0;eta<2;eta++)for(int method=0;method<6;method++){
      const double eta2=eta?.01*a.h*a.h:0;std::vector<double> m(n*n,0),test;
      for(const Node& p:a.p)test.push_back(std::sin(3*p.p.x)+.4*p.p.z*p.p.z);
      for(unsigned i=0;i<n;i++){
        Vec lx;for(const Edge& e:a.edges[i])lx=lx+Weight(a,i,e,method%3,eta2)*e.d;
        for(const Edge& e:a.edges[i]){
          const double w=Weight(a,i,e,method%3,eta2)+(method>=3?Dot(e.b,lx):0);
          m[i*n+i]+=w;m[i*n+e.j]-=w;
        }
        double row=0,absrow=0,action=0;
        for(unsigned j=0;j<n;j++){row+=m[i*n+j];absrow+=std::abs(m[i*n+j]);action+=m[i*n+j]*test[j];}
        const double rowerr=std::abs(row)/std::max(1.,absrow);
        const double actionerr=std::abs(action-Evaluate(a,i,test,method,eta2).lap)/std::max(1.,absrow);
        const std::string label=(disorder?"disorder":"regular");
        gates<<"matrix_row_sum,9,"<<label<<','<<eta<<','<<Methods[method]<<','<<rowerr<<",1e-12,"<<(rowerr<=1e-12)<<'\n';
        gates<<"matrix_action,9,"<<label<<','<<eta<<','<<Methods[method]<<','<<actionerr<<",1e-12,"<<(actionerr<=1e-12)<<'\n';
      }
      const std::string file=out+"/matrix_"+(disorder?"disorder":"regular")+"_eta"+std::to_string(eta)+"_"+Methods[method]+".csv";
      std::ofstream mat(file);mat<<std::setprecision(17);
      for(unsigned i=0;i<n;i++){for(unsigned j=0;j<n;j++){if(j)mat<<',';mat<<m[i*n+j];}mat<<'\n';}
    }
  }
}
int main(int argc,char** argv){
  if(argc!=2){std::cerr<<"usage: upl_p1_scalar_r1.exe NEW_OUTPUT_DIRECTORY\n";return 2;}
  try{
    std::ofstream errors(std::string(argv[1])+"/errors.csv"),gates(std::string(argv[1])+"/arithmetic.csv");
    if(!errors||!gates)throw std::runtime_error("output directory unavailable");
    errors<<std::setprecision(17)<<"n,geometry,eta,method,field,region,count,dp,h,rms_error,max_error,linear_grad_error_max,volume_budget,exact_volume_budget\n";
    gates<<std::setprecision(17)<<"gate,n,geometry,eta,method,error,threshold,pass\n";
    PolynomialTests(argv[1],errors,gates);MatrixTests(argv[1],gates);
    std::cout<<"COMPLETED companion diagnostics; no production/physical acceptance\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
