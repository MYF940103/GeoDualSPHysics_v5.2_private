// Bounded 2-D private P2 feedback components; actual GPU FS/force/p/J kernels.
// No JSph instance, physical outer loop, public option, Darcy or boundary admission.
#include "JSphGpu_ker.h"
#include "FunSphKernel.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("GpuFeedbackComponents","r1","02-11-2026");
namespace fs=std::filesystem;
static void Need(bool v,const char* text){if(!v)throw std::runtime_error(text);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
constexpr unsigned Cap=9;
template<class T,unsigned N=Cap>struct Device{
  T* p=nullptr;Device(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(T)*N));clear();}~Device(){if(p)cudaFree(p);}
  Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void clear(){Cu(cudaMemset(p,0,sizeof(T)*N));}
  void put(const std::array<T,N>& a){Cu(cudaMemcpy(p,a.data(),sizeof(T)*N,cudaMemcpyHostToDevice));}
  std::array<T,N> get()const{std::array<T,N>a;Cu(cudaMemcpy(a.data(),p,sizeof(T)*N,cudaMemcpyDeviceToHost));return a;}
};
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Close(double a,double b){return std::isfinite(a)&&std::isfinite(b)&&fabs(a-b)<=5e-13*(std::max)(1.,fabs(b));}
struct Ledger{double n,V,rho;};
struct Rates{
  std::array<double,Cap> theta;std::array<float,Cap> p,ar;
  std::array<float3,Cap> ace;std::array<tsymatrix3f,Cap> stress;std::array<tmatrix3d,Cap> C;
};
struct Frame{double t;std::array<double,Cap> j;std::array<float,Cap> p;};
struct Series{std::vector<Frame> frames;double pressure=0,jlog=0,nullp=0;};
class Patch{
  unsigned count;
  Device<int2,4> cells;Device<unsigned> dcell,id,fstype,invalid;Device<typecode> code;
  Device<double2> xy;Device<double> z,J,Jold,theta;
  Device<float4> pos,vel;Device<tmatrix3d> correction;Device<tsymatrix3d> sigma;
  Device<tsymatrix3f> stress;Device<float3> ace,fsnormal;Device<float> p,pold,pdot,ar,visc,posdiv,plastic;
  StDivDataGpu dvd;StCteInteraction c={};
  std::array<float4,Cap> positions={},velocities={};std::array<tsymatrix3d,Cap> sigmas={};
  std::array<float,Cap> pressures={};std::array<double,Cap> js={};
  std::array<double2,Cap> reference={};
  unsigned forcecalls=0,fscalls=0;
  static double Theta(unsigned kind){return kind==0?-1./32.:(kind==1?1./32.:0.);}
public:
  explicit Patch(unsigned n):count(n){
    Need(n==2||n==9,"Only pair/FS9 patches admitted");
    cells.put({make_int2(0,0),make_int2(0,0),make_int2(0,int(n)),make_int2(0,0)});
    std::array<unsigned,Cap> ids={};std::array<typecode,Cap> codes={};
    for(unsigned i=0;i<count;i++){ids[i]=i;codes[i]=CODE_TYPE_FLUID;js[i]=1.;}
    if(n==2){reference[0]=make_double2(-.0625,-.046875);reference[1]=make_double2(.0625,.046875);}
    else for(unsigned iz=0;iz<3;iz++)for(unsigned ix=0;ix<3;ix++)reference[3*iz+ix]=make_double2((int(ix)-1)*.25,(int(iz)-1)*.25);
    id.put(ids);code.put(codes);J.put(js);
    const unsigned cellcode=DCEL_GetCode(1,1,1);
    dvd=MakeDivDataGpu(1,TUint3(1,1,1),TUint3(0),cells.p,2.f,cellcode,TDouble3(0),.5f,2.f);
    c.simulate2d=true;c.nbound=0;c.kernelh=.5f;c.kernelsize=1;c.kernelsize2=1;c.poscellsize=2;c.scell=2;c.dp=.25f;
    c.rhopzero=2100;c.ovrhopzero=1.f/c.rhopzero;c.massb=c.massf=131.25f;c.cteb=0;c.gamma=7;c.cs0=40;c.eta2=.0025f;
    c.axis=MGDIV_Z;c.cellcode=cellcode;c.tboundary=BC_DBC;c.modulus_K=1666666.75f;c.modulus_G=769230.8125f;
    c.hydromech=1;c.porewaterbulkmodulus=2e8f;c.porewaterrho=1000;c.porosity=.3f;c.porekwn=c.porewaterbulkmodulus/c.porosity;
    c.porecompgradcorr=1;c.soilstressrategradcorr=1;c.porecompsourcemode=0;
    const auto kw=fsph::GetKernelWendland_Ctes(true,.5);c.awen=kw.awen;c.bwen=kw.bwen;
    cusph::CteInteractionUp(&c);Cu(cudaGetLastError());Kinematics(1,0.);
  }
  Ledger State(double j)const{
    const double n=1.-(1.-double(c.porosity))/j,V=double(c.massf)/double(c.rhopzero)*j,rho=double(c.porewaterrho)+(double(c.rhopzero)-double(c.porewaterrho))/j;
    Need(std::isfinite(j)&&j>1.-double(c.porosity)&&std::isfinite(n)&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0,"Invalid independent ledger");
    return{n,V,rho};
  }
  void Kinematics(unsigned kind,double time){
    const double trace=Theta(kind),stretch=exp(trace*time/2.);std::array<double2,Cap> xs={};std::array<double,Cap> zs={};
    for(unsigned i=0;i<count;i++){
      const auto r=reference[i];double x=r.x,zr=r.y;
      if(kind<2){x*=stretch;zr*=stretch;}else if(kind==2)x+=(1./32.)*time*r.y;
      positions[i]=make_float4(float(.5+x),0.f,float(.5+zr),0.f);
      // Use actual stored float geometry, not independently rounded ideal geometry.
      const float dx=positions[i].x-.5f,dz=positions[i].z-.5f;
      float vx=0,vz=0;if(kind<2){vx=float(trace*.5)*dx;vz=float(trace*.5)*dz;}
      else if(kind==2)vx=(1.f/32.f)*dz;else{vx=-(1.f/32.f)*dz;vz=(1.f/32.f)*dx;}
      velocities[i]=make_float4(vx,0.f,vz,c.rhopzero);xs[i]=make_double2(positions[i].x,0.);zs[i]=positions[i].z;
    }
    pos.put(positions);xy.put(xs);z.put(zs);vel.put(velocities);
  }
  void Poison(bool on){for(unsigned i=0;i<count;i++)velocities[i].w=on?float(1000+37*i):c.rhopzero;vel.put(velocities);}
  Rates Evaluate(bool actualC){
    if(actualC){
      cusph::ComputeFreeSurfaceTracking(KERNEL_Wendland,true,count,0,dvd,dcell.p,pos.p,vel.p,code.p,correction.p,fstype.p,fsnormal.p,posdiv.p,false,J.p);fscalls++;
    }else correction.clear();
    pdot.clear();theta.clear();ar.clear();ace.clear();visc.clear();stress.clear();
    const StInterParmsg a=StrInterParmsg(true,false,KERNEL_Wendland,FTMODE_None,false,DDT_None,SHIFT_None,MDBC2_None,
      0,0,128,128,count,0,0,0,0,dvd,dcell.p,xy.p,z.p,pos.p,vel.p,id.p,code.p,nullptr,nullptr,nullptr,
      correction.p,nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,visc.p,ar.p,ace.p,nullptr,nullptr,sigma.p,stress.p,nullptr,
      p.p,pdot.p,fstype.p,fsnormal.p,false,nullptr,nullptr,nullptr,nullptr,nullptr,nullptr,theta.p,J.p);
    cusph::Interaction_Forces(a);forcecalls++;Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
    Rates r={theta.get(),pdot.get(),ar.get(),ace.get(),stress.get(),correction.get()};
    for(unsigned i=0;i<count;i++){
      const auto s=r.stress[i];const auto a=r.ace[i];
      Need(std::isfinite(r.theta[i])&&std::isfinite(r.p[i])&&std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z)&&std::isfinite(s.xx)&&std::isfinite(s.yy)&&std::isfinite(s.zz)&&std::isfinite(s.xy)&&std::isfinite(s.yz)&&std::isfinite(s.xz),"Nonfinite actual feedback output");
    }
    Need(Bits(velocities,vel.get())&&Bits(sigmas,sigma.get())&&Bits(pressures,p.get()),"Force component changed physical input arrays");return r;
  }
  static void PoisonExact(const Rates& a,const Rates& b,unsigned n){
    for(unsigned i=0;i<n;i++)Need(Bits(a.theta[i],b.theta[i])&&Bits(a.p[i],b.p[i])&&Bits(a.ace[i],b.ace[i])&&Bits(a.stress[i],b.stress[i])&&Bits(a.C[i],b.C[i]),"Positive old density changed new operators");
    // ar is the legacy density diagnostic, deliberately not claimed independent.
  }
  void Pair(std::ostream& out){
    Need(count==2,"Expected pair");
    for(unsigned i=0;i<2;i++){velocities[i].x=velocities[i].z=0;}
    sigmas[0].xx=12345;sigmas[0].xy=0;sigmas[0].xz=432;sigmas[0].yy=23456;sigmas[0].yz=0;sigmas[0].zz=34567;
    sigmas[1].xx=2468;sigmas[1].xy=0;sigmas[1].xz=234;sigmas[1].yy=3579;sigmas[1].yz=0;sigmas[1].zz=4680;sigma.put(sigmas);
    pressures[0]=2000;pressures[1]=7000;p.put(pressures);
    for(unsigned arrangement=0;arrangement<2;arrangement++){
      js[0]=arrangement?1.2:.9;js[1]=arrangement?.9:1.2;J.put(js);Poison(false);const auto normal=Evaluate(false);Poison(true);const auto bad=Evaluate(false);PoisonExact(normal,bad,2);
      const auto a=State(js[0]),b=State(js[1]);const float dx=positions[0].x-positions[1].x,dz=positions[0].z-positions[1].z;
      const float rr2=dx*dx+dz*dz,fac=fsph::GetKernelWendland_Fac(fsph::GetKernelWendland_Ctes(true,.5),c.kernelh,rr2);
      const float gx=fac*dx,gz=fac*dz;
      const double xx=double(float(sigmas[0].xx))+float(sigmas[1].xx)-double(pressures[0])-pressures[1];
      const double zz=double(float(sigmas[0].zz))+float(sigmas[1].zz)-double(pressures[0])-pressures[1],xz=double(float(sigmas[0].xz))+float(sigmas[1].xz);
      const double fx=xx*gx+xz*gz,fz=xz*gx+zz*gz;Need(fabs(fx)>1e-6&&fabs(fz)>1e-6&&a.V!=b.V&&a.rho!=b.rho,"Pair momentum reference is vacuous");
      const double expected[2][3]={{b.V/a.rho*fx,0,b.V/a.rho*fz},{-a.V/b.rho*fx,0,-a.V/b.rho*fz}};
      double netx=0,nety=0,netz=0,scale=0;
      for(unsigned i=0;i<2;i++){
        const auto st=i?b:a;const auto v=normal.ace[i];const double actual[3]={v.x,v.y,v.z};
        for(unsigned k=0;k<3;k++)Need(fabs(actual[k]-expected[i][k])<=64*FLT_EPSILON*(std::max)(1e-6,fabs(expected[i][k]))+1e-9,"Actual unequal-J momentum reference failed");
        netx+=st.rho*st.V*v.x;nety+=st.rho*st.V*v.y;netz+=st.rho*st.V*v.z;scale+=st.rho*st.V*(fabs(v.x)+fabs(v.y)+fabs(v.z));
        out<<arrangement<<','<<i<<','<<js[i]<<','<<st.n<<','<<st.V<<','<<st.rho<<','<<v.x<<','<<expected[i][0]<<','<<v.y<<','<<expected[i][1]<<','<<v.z<<','<<expected[i][2]<<",1\n";
      }
      Need(fabs(netx)+fabs(nety)+fabs(netz)<=64*FLT_EPSILON*scale+1e-9,"Unequal-J pair internal force failed balance");
    }
  }
  void Affine(std::ostream& out){
    Need(count==9,"Expected FS9");
    for(unsigned field=0;field<3;field++){
      Kinematics(field==1?0:1,0.);const double trace=field==1?-1./32.:1./32.,shear=field==2?1./64.:0.;
      if(shear)for(unsigned i=0;i<count;i++){velocities[i].x+=float(shear)*(positions[i].z-.5f);velocities[i].z+=float(shear)*(positions[i].x-.5f);}
      for(unsigned i=0;i<count;i++){
        js[i]=.95+.025*(i%5);pressures[i]=128.f+float(i);
        sigmas[i].xx=1234;sigmas[i].xy=0;sigmas[i].xz=222;sigmas[i].yy=2345;sigmas[i].yz=0;sigmas[i].zz=3456;
      }
      J.put(js);p.put(pressures);sigma.put(sigmas);Poison(false);const auto normal=Evaluate(true);Poison(true);const auto bad=Evaluate(true);PoisonExact(normal,bad,count);
      double minB=DBL_MAX,maxB=0;
      for(unsigned i=0;i<count;i++){
        const auto st=State(js[i]);const double volume0=double(c.massf)/double(c.rhopzero),n0=double(c.porosity),rhos=(double(c.rhopzero)-n0*c.porewaterrho)/(1.-n0);
        Need(Close((1.-st.n)*st.V*rhos,(1.-n0)*volume0*rhos),"Reference solid-volume ledger failed");
        double mxx=0,mxz=0,mzz=0;
        for(unsigned j=0;j<count;j++)if(j!=i){
          const float dx=positions[i].x-positions[j].x,dz=positions[i].z-positions[j].z,rr2=dx*dx+dz*dz;
          const float fac=fsph::GetKernelWendland_Fac(fsph::GetKernelWendland_Ctes(true,.5),c.kernelh,rr2);const double V=State(js[j]).V;
          mxx-=V*double(dx)*double(fac)*double(dx);mxz-=V*double(dx)*double(fac)*double(dz);mzz-=V*double(dz)*double(fac)*double(dz);
        }
        const double det=mxx*mzz-mxz*mxz;Need(det>0&&std::isfinite(det),"Independent VJ moment not full rank");
        const double refC[3]={mzz/det,-mxz/det,mxx/det},actualC[3]={normal.C[i].a11,normal.C[i].a13,normal.C[i].a33};
        for(unsigned k=0;k<3;k++)Need(fabs(actualC[k]-refC[k])<=64*FLT_EPSILON*(std::max)(1.,fabs(refC[k])),"Actual FS correction does not use neighbour V0J");
        Need(fabs(normal.theta[i]-trace)<=64*FLT_EPSILON*fabs(trace),"Actual VJ affine divergence failed");
        const double B=double(c.porewaterbulkmodulus)/st.n,wanted=-B*trace;minB=(std::min)(minB,B);maxB=(std::max)(maxB,B);
        Need(fabs(double(normal.p[i])-wanted)<=64*FLT_EPSILON*fabs(wanted),"Storage did not use receiver-local double Kw/n");
        const double G=c.modulus_G,lambda=double(c.modulus_K)-2.*G/3.,sref[6]={(G+lambda)*trace,0,2.*G*shear,lambda*trace,0,(G+lambda)*trace};
        const auto s=normal.stress[i];const double sa[6]={s.xx,s.xy,s.xz,s.yy,s.yz,s.zz};
        for(unsigned k=0;k<6;k++)Need(fabs(sa[k]-sref[k])<=64*FLT_EPSILON*(std::max)(fabs(sref[k]),fabs(G*trace))+1e-6,"Actual VJ affine six-component stress-rate failed");
        if(shear)Need(s.xz>0&&fabs(s.xz)>.5*fabs(sref[2]),"Mixed XZ shear stress branch is empty");
        out<<field<<','<<i<<','<<js[i]<<','<<st.n<<','<<st.V<<','<<st.rho<<','<<normal.theta[i]<<','<<trace<<','<<normal.p[i]<<','<<wanted;
        for(unsigned k=0;k<6;k++)out<<','<<sa[k]<<','<<sref[k];
        out<<','<<actualC[0]<<','<<refC[0]<<','<<actualC[1]<<','<<refC[1]<<','<<actualC[2]<<','<<refC[2]<<",1\n";
      }
      Need(maxB>minB*1.1,"Receiver-storage heterogeneity check is empty");
    }
  }
  void Advance(bool corrector,double dt){
    if(!corrector){Cu(cudaMemcpy(Jold.p,J.p,sizeof(double)*count,cudaMemcpyDeviceToDevice));Cu(cudaMemcpy(pold.p,p.p,sizeof(float)*count,cudaMemcpyDeviceToDevice));}
    cusph::UpdatePorePressureSymplectic(count,0,dt,code.p,pold.p,pdot.p,p.p);
    std::array<unsigned,Cap> flag{};flag.fill(count);invalid.put(flag);
    cusph::UpdatePorosityObserver(count,0,corrector,dt,1.-double(c.porosity),code.p,plastic.p,Jold.p,theta.p,J.p,invalid.p);
    Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());Need(invalid.get()[0]==count,"Actual pressure/J component kernel rejected state");
    // Keep host input mirrors current solely for the Evaluate input-unchanged check.
    js=J.get();pressures=p.get();
  }
  Series Integrate(unsigned kind,unsigned steps,std::ostream& out){
    Need(count==9,"Expected FS9 integration");js.fill(1.);J.put(js);pressures.fill(0);p.put(pressures);sigmas={};sigma.put(sigmas);plastic.clear();
    const double end=1./1024.,dt=end/steps,trace=Theta(kind),n0=c.porosity,Kw=c.porewaterbulkmodulus;Series result;
    auto save=[&](double time){
      const auto j=J.get();const auto pressure=p.get();const auto th=theta.get();result.frames.push_back({time,j,pressure});
      for(unsigned i=0;i<count;i++){
        const auto st=State(j[i]);const double ref=-Kw*log((j[i]-1.+n0)/n0),pe=fabs(double(pressure[i])-ref),je=fabs(log(j[i])-trace*time);
        Need(pe<=1.&&je<=64*FLT_EPSILON*fabs(trace*time)+512*DBL_EPSILON,"Actual p/J kernels failed logarithmic storage/deformation reference");
        Need(Close((1.-st.n)*j[i],1.-n0),"Integrated single-J solid-volume ledger failed");
        if(kind>=2)Need(fabs(double(pressure[i]))<=.02&&fabs(j[i]-1.)<=5e-13,"Uniform-J trace-free null integration failed");
        result.pressure=(std::max)(result.pressure,pe);result.jlog=(std::max)(result.jlog,je);if(kind>=2)result.nullp=(std::max)(result.nullp,fabs(double(pressure[i])));
        out<<kind<<','<<steps<<','<<time<<','<<i<<','<<j[i]<<','<<st.n<<','<<st.V<<','<<st.rho<<','<<pressure[i]<<','<<ref<<','<<th[i]<<'\n';
      }
    };
    theta.clear();save(0.);
    for(unsigned step=0;step<steps;step++){
      Kinematics(kind,step*dt);Evaluate(true);Advance(false,dt*.5);
      Kinematics(kind,(step+.5)*dt);Evaluate(true);Advance(true,dt);save((step+1)*dt);
    }
    return result;
  }
  unsigned ForceCalls()const{return forcecalls;}unsigned FsCalls()const{return fscalls;}
};
int main(int argc,char** argv){
  try{
    fs::path out;int device=0;bool integrate=false;
    for(int i=1;i<argc;i++){const std::string key=argv[i];if(key=="--integrate")integrate=true;else{Need(i+1<argc,"Missing option value");if(key=="--out")out=argv[++i];else if(key=="--device")device=std::stoi(argv[++i]);else Need(false,"Unknown option");}}
    Need(!out.empty()&&!fs::exists(out),"Require fresh output directory");Cu(cudaSetDevice(device));fs::create_directories(out);
    std::ofstream pair(out/"momentum.csv"),affine(out/"affine.csv");pair<<std::setprecision(17);affine<<std::setprecision(17);
    pair<<"arrangement,id,J,n_reference,V_reference,rho_reference,ax,ax_reference,ay,ay_reference,az,az_reference,positive_oldrho_exact\n";
    affine<<"field,id,J,n_reference,V_reference,rho_reference,theta,theta_reference,pdot,pdot_reference,sxx,sxx_reference,sxy,sxy_reference,sxz,sxz_reference,syy,syy_reference,syz,syz_reference,szz,szz_reference,Cxx,Cxx_reference,Cxz,Cxz_reference,Czz,Czz_reference,positive_oldrho_exact\n";
    unsigned calls=0,fsCalls=0;{Patch a(2);a.Pair(pair);calls+=a.ForceCalls();}{Patch a(9);a.Affine(affine);calls+=a.ForceCalls();fsCalls+=a.FsCalls();}
    Need(calls==10&&fsCalls==6,"Static actual kernel call coverage changed");
    double maxPressure=0,maxHalf=0,maxJ=0,maxNull=0;unsigned halfPairs=0;
    if(integrate){
      std::ofstream history(out/"history.csv"),halves(out/"halves.csv");history<<std::setprecision(17);halves<<std::setprecision(17);
      history<<"field,steps,time_s,id,J,n_reference,V_reference,rho_reference,p,p_log_reference_actual_J,theta_last_stage\n";halves<<"field,time_s,pressure_absmax_pa,J_absmax\n";
      for(unsigned kind=0;kind<4;kind++){
        Series c,h;{Patch a(9);c=a.Integrate(kind,64,history);calls+=a.ForceCalls();fsCalls+=a.FsCalls();}{Patch a(9);h=a.Integrate(kind,128,history);calls+=a.ForceCalls();fsCalls+=a.FsCalls();}
        Need(c.frames.size()==65&&h.frames.size()==129,"Independent integration coverage missing");
        for(unsigned i=0;i<65;i++){
          const auto& a=c.frames[i];const auto& b=h.frames[2*i];Need(a.t==b.t,"Actual dyadic saved component clocks differ");double pe=0,je=0;
          for(unsigned k=0;k<9;k++){pe=(std::max)(pe,fabs(double(a.p[k])-b.p[k]));je=(std::max)(je,fabs(a.j[k]-b.j[k]));}
          Need(pe<=.5&&je<=5e-11,"Independent p/J component half-step gate failed");maxHalf=(std::max)(maxHalf,pe);halfPairs++;halves<<kind<<','<<a.t<<','<<pe<<','<<je<<'\n';
        }
        maxPressure=(std::max)({maxPressure,c.pressure,h.pressure});maxJ=(std::max)({maxJ,c.jlog,h.jlog});maxNull=(std::max)({maxNull,c.nullp,h.nullp});
      }
      history.flush();halves.flush();Need(bool(history)&&bool(halves)&&halfPairs==260,"Integrated component outputs incomplete");
    }
    pair.flush();affine.flush();Need(bool(pair)&&bool(affine),"Static component outputs incomplete");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"dimension\":2,\"pair_arrangements\":2,\"pair_rows\":4,\"nonuniform_affine_fields\":3,\"affine_rows\":27,\"static_force_calls\":10,\"static_actual_FS_calls\":6,\"positive_oldrho_poison_node_pairs\":31,\"six_stress_components_per_affine_node\":true,\"mixed_XZ_shear_nonempty\":true,\"optional_integration_executed\":"<<(integrate?"true":"false")
      <<",\"actual_force_calls\":"<<calls<<",\"actual_FS_calls\":"<<fsCalls<<",\"independent_half_pairs\":"<<halfPairs<<",\"max_pressure_log_reference_error_pa\":"<<maxPressure<<",\"max_half_pressure_difference_pa\":"<<maxHalf<<",\"max_J_log_error\":"<<maxJ<<",\"max_null_pressure_pa\":"<<maxNull
      <<",\"actual_pressure_J_update_kernels\":"<<(integrate?"true":"false")<<",\"nonuniform_tracefree_null_claimed\":false,\"CPU_CSV_used_as_truth\":false,\"actual_JSph_host_guard_tested\":false,\"physical_outer_loop_used\":false,\"prescribed_kinematics\":true,\"dynamic_Darcy_tested\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Completion write failed");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(const char* e){std::cerr<<e<<'\n';return 1;}
  catch(...){std::cerr<<"GPU feedback component failed; preserve evidence\n";return 2;}
}
