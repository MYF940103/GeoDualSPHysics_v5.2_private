// Checks the actual CPU and CUDA TPI rows against manufactured fields on a 3x3 soil patch.
#include "JSphCpuSingle.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#ifdef _WITHGPU
#include "JSphGpu_ker.h"
#include <cuda_runtime.h>
#endif
#include <array>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <omp.h>

JAppInfo AppInfo("TpiVariableKRows","1","");
namespace {
constexpr unsigned count=9,centre=4;
constexpr double vol=.0625,solid=.75,ck=2.,rhow=1000.,kw=67108864.,gammaw=rhow*9.80665;
constexpr float k0=.0001f;
template<class T> using Field=std::array<T,count>;
enum Scenario { UniformFixed,UniformLaw,UniformOffReference,Affine,Acceleration,Balanced };
struct Patch {
  Field<tdouble3> pos;
  Field<tfloat3> ace;
  Field<double> j,theta;
  Field<float> p;
  Field<unsigned> id{},cell{};
  Field<typecode> code;
  Field<tmatrix3d> corr;
  StCteSph sph=CteSphNull();
  bool variable;
  Scenario scenario;
  Patch(Scenario s): variable(s!=UniformFixed),scenario(s){
    sph.kernelh=.5f;sph.kernelsize=1.f;sph.kernelsize2=1.f;sph.eta2=.0025f;
    sph.kwend=fsph::GetKernelWendland_Ctes(true,sph.kernelh);
    for(unsigned i=0;i<count;i++){
      const double x=(int(i%3)-1)*.25,z=(int(i/3)-1)*.25;
      pos[i]=TDouble3(x,0,z);id[i]=i;code[i]=CODE_TYPE_FLUID;
      j[i]=s==UniformOffReference?1.125:(s>=Affine?1.125+x/8.+z/16.:1.);
      p[i]=float(s<Affine?128+32*x*x+16*z*z:(s==Acceleration?128:128+125*x+500*z));
      theta[i]=s<Affine?2.e-5:0.;
      ace[i]=(s==Acceleration?TFloat3(.125f,0,.5f):(s==Balanced?TFloat3(-.125f,0,-.5f):TFloat3(0)));
    }
    for(unsigned i=0;i<count;i++){
      double xx=0,xz=0,zz=0;
      for(unsigned q=0;q<count;q++)if(i!=q){
        const tdouble3 d=pos[i]-pos[q];
        const double w=-vol*j[q]*factor(d);
        xx+=w*d.x*d.x;xz+=w*d.x*d.z;zz+=w*d.z*d.z;
      }
      const double det=xx*zz-xz*xz;
      corr[i]=TMatrix3d();corr[i].a11=zz/det;corr[i].a13=corr[i].a31=-xz/det;corr[i].a33=xx/det;
    }
  }
  double factor(tdouble3 d)const{return fsph::GetKernel_Fac<KERNEL_Wendland>(sph,float(d.x*d.x+d.z*d.z));}
  double expected(unsigned i,double& omitted,double& wrongK)const{
    // Affine p/J have analytic corrected gradients everywhere. At the centre of
    // the symmetric constant-J quadratic stencil the pressure gradient is zero.
    double sumw=0,lap=0;
    for(unsigned q=0;q<count;q++)if(i!=q){
      const auto d=pos[i]-pos[q];const auto &a=corr[i],&b=corr[q];
      const double moment=(a.a11+b.a11)*d.x*d.x+2.*(a.a13+b.a13)*d.x*d.z+(a.a33+b.a33)*d.z*d.z;
      const double w=vol*j[q]*factor(d)*moment/(d.x*d.x+d.z*d.z+sph.eta2);
      sumw+=w;
      if(scenario<Affine)lap+=w*(p[i]-p[q]);  // affine Taylor defect vanishes identically
    }
    const double ki=variable?k0*exp((j[i]-1.)/(solid*ck)):k0;
    const double chain=(scenario==Affine || scenario==Acceleration?ki*(125./8.+500./16.)/(solid*ck):0.);
    const double principal=-ki*sumw,residual=-gammaw*theta[i]+ki*lap;
    omitted=p[i]+residual/principal;
    wrongK=p[i]+(-gammaw*theta[i]+k0*lap+chain)/(-k0*sumw);
    return p[i]+(residual+chain)/principal;
  }
};

class CpuPatch: public JSphCpuSingle{
public:
  Field<float> evaluate(Patch& f){
    unsigned ranges[]={0,0,0,count};
    DivData=MakeDivDataCpu(1,TUint3(1,1,1),TUint3(0),ranges,2,DCEL_GetCode(1,1,1),TDouble3(0));
    Np=count;Npb=0;PeriActive=0;Simulate2D=true;TKernel=KERNEL_Wendland;CSP=f.sph;
    HydroMech=true;HydroMechDrainage=false;HydroMechFreeSeepage=false;DynamicPoreFreeBody=false;
    DynamicPorePressure=TpiEndpoint=true;DynamicPoreWall=false;DynamicPoreConductivity=f.variable;
    DynamicPoreConductivityCk=ck;MassFluid=128;RhopZero=2048;Eta2=CSP.eta2;KernelSize2=CSP.kernelsize2;
    SoilCte.Porosity=float(1.-solid);SoilCte.PoreWaterRho=float(rhow);SoilCte.PoreWaterBulkModulus=float(kw);SoilCte.HydraulicConductivity=k0;
    Dcellc=f.cell.data();Idpc=f.id.data();Codec=f.code.data();Posc=f.pos.data();CorrMatc=f.corr.data();
    PoroJc=f.j.data();PoroThetac=f.theta.data();PorePressc=f.p.data();Acec=f.ace.data();
    Field<float> rates{},result{};PorePressRatec=rates.data();TpiNext.assign(count,-999.f);
    ComputeDynamicPorePressureRateCpu();
    std::copy(TpiNext.begin(),TpiNext.end(),result.begin());
    return result;
  }
};
#ifdef _WITHGPU
void check(cudaError_t e){if(e!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(e));}
template<class T> struct DeviceField{
  T *p=nullptr;
  DeviceField(const T* host,size_t n){check(cudaMalloc(&p,n*sizeof(T)));check(cudaMemcpy(p,host,n*sizeof(T),cudaMemcpyHostToDevice));}
  template<size_t N> explicit DeviceField(const std::array<T,N>& a):DeviceField(a.data(),N){}
  ~DeviceField(){cudaFree(p);}
};
Field<float> gpu(Patch& f){
  Field<double2> xy;Field<double> z;Field<float3> a;
  for(unsigned i=0;i<count;i++){
    xy[i]=make_double2(f.pos[i].x,0);z[i]=f.pos[i].z;a[i]=make_float3(f.ace[i].x,0,f.ace[i].z);
  }
  const unsigned gcode=DCEL_GetCode(1,1,1);
  const std::array<int2,4> ranges={make_int2(0,0),make_int2(0,0),make_int2(0,count),make_int2(0,0)};
  DeviceField<int2> cells(ranges);DeviceField<double2> gx(xy);DeviceField<double> gz(z),gj(f.j),gt(f.theta);
  DeviceField<unsigned> gc(f.cell),id(f.id),invalid(&count,1);DeviceField<typecode> code(f.code);
  DeviceField<float3> ga(a);DeviceField<tmatrix3d> corr(f.corr);DeviceField<float> p(f.p),rate(f.p),next(f.p);
  StCteInteraction c{};c.simulate2d=1;c.kernelh=f.sph.kernelh;c.kernelsize2=f.sph.kernelsize2;c.eta2=f.sph.eta2;
  c.awen=f.sph.kwend.awen;c.bwen=f.sph.kwend.bwen;c.cellcode=gcode;c.axis=MGDIV_Z;
  cusph::CteInteractionUp(&c);
  const auto dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,2,gcode,TDouble3(0),1,2);
  cusph::ComputeDynamicPorePressureRate(count,0,dvd,gc.p,gx.p,gz.p,code.p,corr.p,ga.p,gj.p,gt.p,p.p,rate.p,
    solid,kw,rhow,k0,gammaw,vol,invalid.p,f.variable,ck,nullptr,false,nullptr,nullptr,nullptr,false,false,HMLOAD_None,
    TDouble3(0),0,KERNEL_Wendland,false,{id.p,next.p,count});
  unsigned invalidId;Field<float> result;
  check(cudaMemcpy(&invalidId,invalid.p,sizeof(invalidId),cudaMemcpyDeviceToHost));
  if(invalidId!=count)throw std::runtime_error("GPU rejected a manufactured pressure row");
  check(cudaMemcpy(result.data(),next.p,sizeof(result),cudaMemcpyDeviceToHost));
  return result;
}
#endif
}
int main(){
  omp_set_num_threads(1);CpuPatch cpu;Field<float> fixedCpu{},fixedGpu{};
  const char* names[]={"quadratic_fixed","quadratic_uniform_J1","quadratic_uniform_J1125","affine_p_J","affine_J_acceleration","affine_J_balanced"};
  puts("field,id,reference_Pa,cpu_Pa,gpu_Pa,omit_chain_Pa,constant_k_row_Pa");
  for(int scenario=UniformFixed;scenario<=Balanced;scenario++){
    Patch f(static_cast<Scenario>(scenario));const auto c=cpu.evaluate(f);
    if(scenario==UniformFixed)fixedCpu=c;
    if(scenario==UniformLaw && c!=fixedCpu)return 3;
#ifdef _WITHGPU
    const auto g=gpu(f);
    if(scenario==UniformFixed)fixedGpu=g;
    if(scenario==UniformLaw && g!=fixedGpu)return 3;
#endif
    for(unsigned i=0;i<count;i++){
      if(scenario<Affine && i!=centre)continue;
      double omitted,wrongK;const double expected=f.expected(i,omitted,wrongK);
      printf("%s,%u,%.12g,%.12g,",names[scenario],i,expected,c[i]);
#ifdef _WITHGPU
      printf("%.12g",g[i]);
      if(!(fabs(g[i]-expected)<.0002))return 4;
#endif
      printf(",%.12g,%.12g\n",omitted,wrongK);
      if(!(fabs(c[i]-expected)<.0002))return 4;
      if((scenario==Affine || scenario==Acceleration) && fabs(expected-omitted)<.1)return 5;
      if(scenario==UniformOffReference && fabs(expected-wrongK)<.1)return 6;
    }
  }
}
