// Output-only observer for the private C08 +2.5 degree, positive-pressure-clamp TPI receiver.
#pragma once
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <vector>

namespace c08round {
const unsigned openStep=2000200, firstSoil=2060, nSoil=5000;
const unsigned targets[]={6868,6918,6919,6920,7010};
inline bool sample(unsigned step){
  if(step<=openStep)return false;
  const unsigned k=step-openStep;
  return k<=8 || k==70 || k==139 || k==140 || k==141 || k%2000==0;
}
inline bool full(unsigned step){
  return step==openStep+60000 || step==openStep+176000 || step==openStep+240000;
}
template <class T> std::vector<T> copy(const T* device,unsigned n){
  std::vector<T> values(n);
  if(n && (!device || cudaMemcpy(values.data(),device,n*sizeof(T),cudaMemcpyDeviceToHost)!=cudaSuccess))
    throw std::runtime_error("C08 round observer device read failed.");
  return values;
}
template <class T> void field(std::ofstream& out,const char* name,const char* type,unsigned components,
                             const std::vector<T>& values){
  out <<name<<' '<<type<<' '<<values.size()<<' '<<components<<'\n';
  out.write(reinterpret_cast<const char*>(values.data()),values.size()*sizeof(T));
}
struct Probe {
  unsigned index,id,fs;
  double x,z,J,theta,ax,az,pn,prev,iterate,next,rate,residual;
};
struct Observer {
  bool active;
  unsigned step,round;
  double time,dt;
  std::vector<Probe> probes;
  Observer():active(false),step(0),round(0),time(0),dt(0){}

  void before(const std::string& dir,unsigned st,unsigned r,double t,double delta,unsigned np,unsigned npb,
    const unsigned* ids,const double2* xy,const double* z,const typecode* code,const unsigned* fs,
    const tmatrix3d* C,const double* J,const float* pressure,const float3* ace,const float3* normal,
    const byte* mode,const double* theta,const float* rate,const float* source,const float* previous,
    const float* next,double solid0,double kw,double rhow,double k0,double ck,double vol0,double h,
    double eta2,double kernelSize2)
  {
    step=st;round=r;time=t;dt=delta;active=sample(st);
    if(!active)return;
    const bool snapshot=full(step);
    if(np!=6805 || npb!=1805 || np-npb!=nSoil || !r || r>3)
      throw std::runtime_error("C08 round observer registry changed.");
    const double gamma=rhow*9.80665; // Match ComputeDynamicPorePressureRateGpu().
    const auto owner=copy(ids,np);
    const auto posxy=copy(xy,np);
    const auto posz=copy(z,np);
    const auto tags=copy(fs,np);
    const auto js=copy(J,np);
    const auto p=copy(pressure,np);
    const auto a=copy(ace,np);
    const auto th=copy(theta+npb,nSoil);
    const auto rr=copy(rate+npb,nSoil);
    const auto pn=copy(source+firstSoil,nSoil), pm=copy(previous+firstSoil,nSoil), q=copy(next+firstSoil,nSoil);
    probes.clear();
    for(const unsigned id:targets){
      const auto found=std::find(owner.begin()+npb,owner.end(),id);
      if(found==owner.end())throw std::runtime_error("C08 probe owner absent.");
      const unsigned i=unsigned(found-owner.begin()),j=id-firstSoil;
      const double n=1.-solid0/js[i];
      probes.push_back({i,id,tags[i],posxy[i].x,posz[i],js[i],th[i-npb],a[i].x,a[i].z,
                        pn[j],pm[j],p[i],q[j],rr[i-npb],double(rr[i-npb])*n*gamma/kw});
    }
    if(!snapshot)return;
    static_assert(sizeof(double2)==16 && sizeof(float3)==12 && sizeof(tmatrix3d)==72 &&
                  (sizeof(typecode)==2 || sizeof(typecode)==4),"Unexpected device array layout.");
    const std::string path=dir+"C08TpiRow_"+std::to_string(step)+"_r"+std::to_string(round)+".bin";
    if(fun::FileExists(path))throw std::runtime_error("C08 round snapshot already exists.");
    std::ofstream out(path,std::ios::binary);out.imbue(std::locale::classic());out<<std::setprecision(17);
    out<<"{\"schema\":\"C08TpiRow1\",\"step\":"<<step<<",\"round\":"<<round<<",\"time_start_s\":"<<time
       <<",\"dt_s\":"<<dt<<",\"np\":"<<np<<",\"npb\":"<<npb<<",\"first_soil_id\":"<<firstSoil
       <<",\"solid0\":"<<solid0<<",\"kw\":"<<kw<<",\"rhow\":"<<rhow<<",\"gamma\":"<<gamma
       <<",\"k0\":"<<k0<<",\"Ck\":"<<ck<<",\"vol0\":"<<vol0<<",\"h\":"<<h
       <<",\"eta2\":"<<eta2<<",\"kernel_size2\":"<<kernelSize2<<"}\n";
    field(out,"id","u4",1,owner);
    field(out,"posxy","f8",2,posxy);field(out,"posz","f8",1,posz);
    field(out,"code",sizeof(typecode)==2?"u2":"u4",1,copy(code,np));field(out,"fs","u4",1,tags);
    field(out,"C","f8",9,copy(C,np));field(out,"J","f8",1,js);field(out,"p","f4",1,p);
    field(out,"ace","f4",3,a);field(out,"normal","f4",3,copy(normal,np));
    field(out,"mode","u1",1,copy(mode,npb));
    field(out,"theta","f8",1,th);field(out,"rate","f4",1,rr);
    field(out,"source","f4",1,pn);field(out,"previous","f4",1,pm);field(out,"next","f4",1,q);
    out<<"END\n";out.close();
    if(!out)throw std::runtime_error("Could not write C08 round snapshot.");
  }

  void after(const std::string& dir,unsigned np,const unsigned* ids,const unsigned* fs,const float* pressure){
    if(!active)return;
    const auto owner=copy(ids,np),tags=copy(fs,np);
    const auto p=copy(pressure,np);
    const std::string path=dir+"C08TpiRoundProbe.csv";
    if(!file.is_open()){
      if(fun::FileExists(path))throw std::runtime_error("C08 round probe already exists.");
      file.open(path);file.imbue(std::locale::classic());file<<std::setprecision(17);
      file<<"step,round,time_start_s,dt_s,id,fs_before,fs_after,x_m,z_m,J,theta_s_inv,acc_x,acc_z,"
            "p_n_Pa,p_prev_Pa,iterate_Pa,next_Pa,post_Pa,rate_Pa_s,residual_from_rate,beta_active\n";
    }
    for(const Probe& s:probes){
      if(owner[s.index]!=s.id)throw std::runtime_error("Order changed during C08 round.");
      file<<step<<','<<round<<','<<time<<','<<dt<<','<<s.id<<','<<s.fs<<','<<tags[s.index]
          <<','<<s.x<<','<<s.z<<','<<s.J<<','<<s.theta<<','<<s.ax<<','<<s.az
          <<','<<s.pn<<','<<s.prev<<','<<s.iterate<<','<<s.next<<','<<p[s.index]
          <<','<<s.rate<<','<<s.residual<<','<<unsigned(s.pn<0.)<<'\n';
    }
    file.flush();
    if(!file)throw std::runtime_error("Could not write C08 round probes.");
    active=false;
  }
  std::ofstream file;
};
}
