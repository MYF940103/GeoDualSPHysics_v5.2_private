// Poisson-ratio sweep host for the sealed native-mass weak CUDA component.
// Run from the original package directory. Its operators/anchors remain untouched.
// Only Lame parameters and the artificial-viscosity wave-speed factor change.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" {
const char* errorText();
int currentStep(), init(int,double,double,double,double), start(), startWeak(), releaseWeak();
int setCsr(int,int,const int*,const int*,const double*);
int setGeometry(const double*,const double*,const double*,const double*,const double*,const unsigned char*);
int uploadWeak(int,const int*,const int*,const double*,const double*,const double*);
int advanceWeak(int), readState(double*,double*,double*,double*,double*), readPrevious(double*);
}
namespace fs=std::filesystem;
constexpr int n=37173, drainStep=4096;
constexpr double dt=1.0/524288.0, young=2000000.0, density=2100.0;
using Frame=std::vector<double>;
void require(bool condition,const std::string& error){if(!condition)throw std::runtime_error(error);}
void checked(int result){if(result)throw std::runtime_error(errorText());}
template<class T> std::vector<T> readArray(std::istream& input,size_t length){
  std::vector<T> value(length);
  input.read(reinterpret_cast<char*>(value.data()),length*sizeof(T));
  require(bool(input),"Short binary input");return value;
}
struct Geometry {
  std::vector<double> x,radius;
  std::vector<unsigned char> surface,center;
};
Geometry setup(double nominalNu,std::ostream& material){
  std::ifstream input("inputs/operators.bin",std::ios::binary);
  const auto args=readArray<double>(input,4);
  const double baseNu=double(.3f), nu=double(float(nominalNu));
  const double baseMu=young/(2*(1+baseNu)), baseLambda=young*baseNu/((1+baseNu)*(1-2*baseNu));
  require(args[0]==dt&&args[1]==baseMu&&args[2]==baseLambda,"Expected sealed nu=0.30 operator header");
  const double mu=young/(2*(1+nu)), lambda=young*nu/((1+nu)*(1-2*nu));
  const double sound=std::sqrt((lambda+2*mu)/density);
  const double baseSound=std::sqrt((baseLambda+2*baseMu)/density), avScale=sound/baseSound;
  material<<std::setprecision(17)
          <<"nu_nominal,nu_effective,young_Pa,mu_Pa,lambda_Pa,sound_m_s,base_sound_m_s,av_scale,dt_s,damping_s_inv\n"
          <<nominalNu<<','<<nu<<','<<young<<','<<mu<<','<<lambda<<','<<sound<<','<<baseSound<<','<<avScale<<','<<dt<<','<<args[3]<<std::endl;
  require(bool(material),"Material record write failed");
  std::cout<<std::setprecision(17)<<"nu_nominal="<<nominalNu<<", nu_effective="<<nu
           <<", mu="<<mu<<", lambda="<<lambda<<", sound="<<sound<<", av_scale="<<avScale
           <<", dt="<<dt<<", damping="<<args[3]<<std::endl;
  checked(init(n,dt,mu,lambda,args[3]));
  for(int key:{0,1,2,4}){
    int nz=readArray<int>(input,1)[0];require(nz>0&&nz<20000000,"Invalid operator size");
    auto row=readArray<int>(input,n+1),col=readArray<int>(input,nz);
    auto value=readArray<double>(input,(key<2?3:1)*size_t(nz));
    if(key==4)for(double& v:value)v*=avScale;
    checked(setCsr(key,nz,row.data(),col.data(),value.data()));
    if(key==2)checked(setCsr(3,nz,row.data(),col.data(),value.data()));
  }
  Geometry g;
  g.x=readArray<double>(input,3*n);
  auto mass=readArray<double>(input,n),traction=readArray<double>(input,3*n);
  auto inverse=readArray<double>(input,n),normal=readArray<double>(input,3*n);
  g.surface=readArray<unsigned char>(input,n);g.radius.resize(n);g.center.resize(n);
  for(int i=0;i<n;i++){
    const double* x=g.x.data()+3*i;
    g.radius[i]=std::sqrt(x[0]*x[0]+x[1]*x[1]+x[2]*x[2]);
    require(g.radius[i]>0,"Unexpected material point at origin");
    g.center[i]=g.radius[i]<.003;
  }
  require(std::count(g.center.begin(),g.center.end(),1)==18&&
          std::count(g.surface.begin(),g.surface.end(),1)==5153,"Unexpected center/surface material counts");
  checked(setGeometry(g.x.data(),mass.data(),traction.data(),inverse.data(),normal.data(),g.surface.data()));
  checked(start());
  int nz=readArray<int>(input,1)[0];require(nz>0&&nz<20000000,"Invalid weak operator size");
  auto row=readArray<int>(input,n+1),col=readArray<int>(input,nz);
  auto value=readArray<double>(input,nz),volume=readArray<double>(input,n),diagonal=readArray<double>(input,n);
  // The weak absolute-row denominator depends on dt, damping, geometry and mass,
  // not Lame parameters: endpoint stress and AV are frozen during its three rounds.
  checked(uploadWeak(nz,row.data(),col.data(),value.data(),volume.data(),diagonal.data()));
  require(input.peek()==std::char_traits<char>::eof(),"Unexpected operator data");
  checked(startWeak());return g;
}
Frame state(){
  Frame f(15*n);auto a=f.data();
  checked(readState(a,a+2*n,a+5*n,a+8*n,a+14*n));checked(readPrevious(a+n));
  require(std::all_of(f.begin(),f.end(),[](double v){return std::isfinite(v);}),"Nonfinite material state");
  return f;
}
void advanceTo(int step){
  const int startStep=currentStep();require(startStep>=0&&startStep<=step,"Nonmonotonic clock");
  if(step>startStep)checked(advanceWeak(step-startStep));
  require(currentStep()==step,"Unexpected GPU clock");
}
std::string frameName(int step){return "state_"+std::to_string(step)+".bin";}
void saveFrame(const fs::path& path,const Frame& f){
  auto temporary=path;temporary+=".writing";require(!fs::exists(path)&&!fs::exists(temporary),"Frame already exists");
  std::ofstream out(temporary,std::ios::binary);out.write(reinterpret_cast<const char*>(f.data()),f.size()*sizeof(double));
  out.close();require(bool(out),"Failed writing frame");fs::rename(temporary,path);
}
struct Metrics {
  double center=0,surfaceInward=0,pmin=0,pmax=0,speed=0;
  double pressureRms=0,totalRms=0,displacementRms=0,surfaceRadialRms=0;
};
Metrics measure(const Geometry& g,const Frame& f){
  Metrics m;m.pmin=m.pmax=f[0];
  for(int i=0;i<n;i++){
    const double p=f[i];const double* u=f.data()+2*n+3*i;
    const double* v=f.data()+5*n+3*i;const double* s=f.data()+8*n+6*i;
    const double* x=g.x.data()+3*i;
    m.center+=g.center[i]?p:0;
    m.pmin=std::min(m.pmin,p);m.pmax=std::max(m.pmax,p);
    const double speed2=v[0]*v[0]+v[1]*v[1]+v[2]*v[2];
    m.speed=std::max(m.speed,std::sqrt(speed2));
    const double dp=p-10000,total=p-(s[0]+s[1]+s[2])/3-10000;
    m.pressureRms+=dp*dp;m.totalRms+=total*total;
    m.displacementRms+=1e6*(u[0]*u[0]+u[1]*u[1]+u[2]*u[2]);
    if(g.surface[i]){
      double radius2=0,radial=0;
      for(int k=0;k<3;k++){radius2+=(x[k]+u[k])*(x[k]+u[k]);radial+=u[k]*x[k];}
      m.surfaceInward+=1000*(g.radius[i]-std::sqrt(radius2));
      radial*=1000/g.radius[i];m.surfaceRadialRms+=radial*radial;
    }
  }
  m.center/=18;m.surfaceInward/=5153;
  m.pressureRms=std::sqrt(m.pressureRms/n);m.totalRms=std::sqrt(m.totalRms/n);
  m.displacementRms=std::sqrt(m.displacementRms/n);m.surfaceRadialRms=std::sqrt(m.surfaceRadialRms/5153);
  return m;
}
int main(int argc,char** argv){
  try{
    require(argc==5,"Usage (cwd=sealed package): weak_nu_full.exe NU STEPS_TXT PEAK_END_STEP NEW_OUTPUT");
    size_t used=0;const std::string nuText=argv[1];const double nu=std::stod(nuText,&used);
    require(used==nuText.size()&&std::isfinite(nu)&&
            (std::abs(nu-.1)<1e-12||std::abs(nu-.2)<1e-12||std::abs(nu-.3)<1e-12||std::abs(nu-.45)<1e-12),
            "Supported nominal Poisson ratios: 0.10, 0.20, 0.30, 0.45");
    const std::string peakText=argv[3];const int peakEnd=std::stoi(peakText,&used);
    require(used==peakText.size(),"Invalid peak end step");
    std::ifstream schedule(argv[2]);std::set<int> saves;int step;
    while(schedule>>step)require(step>=0&&saves.insert(step).second,"Negative/duplicate scheduled step");
    require(schedule.eof()&&!saves.empty()&&*saves.begin()==0&&saves.count(drainStep)&&
            peakEnd>=drainStep&&peakEnd<=*saves.rbegin(),"Invalid schedule or peak end step");
    const int end=*saves.rbegin();std::set<int> dense={drainStep,peakEnd};
    if(peakEnd>drainStep)dense.insert(drainStep+1);
    for(int i=drainStep;i<peakEnd;i+=32)dense.insert(i);
    const std::set<int> closed={3904,3968,4032,4096};
    std::set<int> events=saves;events.insert(dense.begin(),dense.end());events.insert(closed.begin(),closed.end());
    const fs::path output=argv[4];require(fs::create_directory(output),"Output directory already exists");
    const auto startTime=std::chrono::steady_clock::now();
    std::ofstream material(output/"material.csv");const Geometry geometry=setup(nu,material);
    std::ofstream clock(output/"actual_clock.csv"),history(output/"peak_history.csv"),gate(output/"closed_gate.csv");
    clock<<"step,time_s,elapsed_s\n"<<std::setprecision(17);
    history<<"step,time_s,center18_Pa,surface_inward_mm,p_min_Pa,p_max_Pa,max_speed_m_s\n"<<std::setprecision(17);
    gate<<"step,time_s,rms_p_to_10000_Pa,rms_total_to_10000_Pa,max_speed_m_s,rms_displacement_mm,rms_surface_displacement_mm,passed\n"<<std::setprecision(17);
    require(bool(clock)&&bool(history)&&bool(gate),"Unable to open run records");
    int closedCount=0;
    for(int next:events){
      advanceTo(next);const auto f=state();
      if(saves.count(next)){
        saveFrame(output/frameName(next),f);
        const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-startTime).count();
        clock<<next<<','<<next*dt<<','<<elapsed<<std::endl;
        require(bool(clock),"Clock write failed");
        std::cout<<"step "<<next<<", elapsed "<<elapsed<<" s"<<std::endl;
      }
      if(dense.count(next)||closed.count(next)){
        const auto m=measure(geometry,f);
        if(dense.count(next)){
          history<<next<<','<<next*dt<<','<<m.center<<','<<m.surfaceInward<<','<<m.pmin<<','<<m.pmax<<','<<m.speed<<std::endl;
          require(bool(history),"Peak history write failed");
        }
        if(closed.count(next)){
          const bool passed=m.pressureRms<=100&&m.totalRms<=100&&m.speed<=1e-5&&
                            m.displacementRms<=1e-5&&m.surfaceRadialRms<=1e-5;
          gate<<next<<','<<next*dt<<','<<m.pressureRms<<','<<m.totalRms<<','<<m.speed<<','
              <<m.displacementRms<<','<<m.surfaceRadialRms<<','<<int(passed)<<std::endl;
          require(bool(gate),"Closed gate write failed");
          require(passed,"Closed preload gate failed at step "+std::to_string(next));closedCount++;
        }
      }
      if(next==drainStep)require(closedCount==4,"Closed preload gate incomplete");
    }
    require(closedCount==4&&currentStep()==end,"Incomplete final clock/gate");
    checked(releaseWeak());std::ofstream done(output/"complete.txt");done<<"full"<<std::endl;
    require(bool(done),"Unable to seal run");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
