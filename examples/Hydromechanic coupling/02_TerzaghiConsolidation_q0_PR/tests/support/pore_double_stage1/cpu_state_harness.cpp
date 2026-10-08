// Stage 1 acceptance linked against authoritative, freshly built CPU objects.
// Calls real pressure integration/output/periodic methods, not copied algorithms.
#include "JSphCpu.h"
#include "JSphCpuSingle.h"
#include "JAppInfo.h"
#include "JPartDataBi4.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <omp.h>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

JAppInfo AppInfo("PoreDoubleStage1Acceptance","v1","09-09-2026");
static void Require(bool ok,const std::string& message){if(!ok)throw std::runtime_error(message);}
template<class T> static bool Same(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static std::string Quote(const std::string& s){
  std::string out="\"";
  for(unsigned char c:s){
    if(c=='"'||c=='\\'){out+='\\';out+=char(c);}
    else if(c=='\n')out+="\\n";
    else if(c>=32)out+=char(c);
  }
  return out+'"';
}
struct State{double value,old;int phase;};
class PressureFixture:public JSphCpu{
  double a[1],b[1],c[1];float rate[1];
  typecode code[1];unsigned fstype[1];tdouble3 pos[1];
public:
  PressureFixture(double initial,float source,bool verlet=false):JSphCpu(false){
    static_assert(std::is_same<decltype(PorePressc),double*>::value,"State must be double");
    static_assert(std::is_same<decltype(PorePressRatec),float*>::value,"Stage 1 rate must remain float");
    Np=CaseNp=CaseNfluid=1;Npb=NpbOk=CaseNbound=CaseNpb=0;
    TStep=verlet?STEP_Verlet:STEP_Symplectic;OmpThreads=1;
    HydroMech=true;HydroMechDrainage=false;
    HydroMechTopLoadMode=HMLOAD_None;HydroMechDrainageStartTime=0;
    TimeStep=0;VerletSteps=40;VerletStep=0;
    a[0]=b[0]=c[0]=initial;rate[0]=source;
    code[0]=CODE_TYPE_FLUID;fstype[0]=FST_Inner;pos[0]=TDouble3(0);
    PorePressc=a;PorePressPrec=b;PorePressM1c=c;
    PorePressRatec=rate;Codec=code;FSTypec=fstype;Posc=pos;
  }
  ~PressureFixture(){
    PorePressc=PorePressPrec=PorePressM1c=NULL;
    PorePressRatec=NULL;Codec=NULL;FSTypec=NULL;Posc=NULL;
  }
  double Value()const{return PorePressc[0];}
  State Save()const{return {Value(),PorePressM1c[0],VerletStep};}
  void Restore(const State& s){PorePressc[0]=s.value;PorePressM1c[0]=s.old;VerletStep=s.phase;}
  void SeedVerletHistory(double dt){PorePressM1c[0]=Value()-dt*double(rate[0]);}
  void Predictor(double dt){PorePressPrec[0]=Value();ComputeSymplecticPrePorePressure(dt);}
  void Corrector(double dt){ComputeSymplecticCorrPorePressure(dt);}
  void Verlet(double dt){
    VerletStep++;ComputeVerletPorePressure(VerletStep<VerletSteps?dt+dt:dt);
    if(VerletStep>=VerletSteps)VerletStep=0;
    std::swap(PorePressc,PorePressM1c);ApplyFreeSurfacePorePressure();
  }
  void Step(double dt,bool verlet){if(verlet)Verlet(dt);else{Predictor(dt);Corrector(dt);}}
  void SetBoundary(){Npb=NpbOk=1;code[0]=CODE_TYPE_FIXED;}
  void SetNonFluid(){code[0]=CODE_TYPE_FIXED;}
  void SetDrained(){HydroMechDrainage=true;fstype[0]=FST_FreeSurface;}
};
struct Result{
  std::string scheme;double initial,dt,analytic,value,legacy,tolerance,pre_error=0,full_error=0;
  float rate;unsigned steps,mismatches=0;bool pass;
};
static Result Evaluate(double initial,float rate,double dt,unsigned steps,bool verlet){
  PressureFixture run(initial,rate,verlet),resume(initial,rate,verlet);
  if(verlet)run.SeedVerletHistory(dt);
  Result r;r.scheme=verlet?"Verlet_valid_history":"Symplectic";
  r.initial=initial;r.rate=rate;r.dt=dt;r.steps=steps;
  const double increment=dt*double(rate);
  float legacy=float(initial),legacyold=float(initial-increment);unsigned phase=0;
  for(unsigned step=1;step<=steps;step++){
    if(verlet){
      run.Verlet(dt);phase++;
      const float next=float(double(phase<40?legacyold:legacy)+(phase<40?2.*dt:dt)*double(rate));
      legacyold=legacy;legacy=next;if(phase>=40)phase=0;
    }
    else{
      run.Predictor(dt);
      r.pre_error=(std::max)(r.pre_error,std::abs(run.Value()-(initial+(step-.5)*increment)));
      run.Corrector(dt);legacy=float(double(legacy)+increment);
    }
    r.full_error=(std::max)(r.full_error,std::abs(run.Value()-(initial+step*increment)));
    if(step==steps/2)resume.Restore(run.Save());
    else if(step>steps/2){resume.Step(dt,verlet);if(!Same(resume.Value(),run.Value()))r.mismatches++;}
  }
  r.value=run.Value();r.analytic=initial+steps*increment;r.legacy=legacy;
  const double scale=(std::max)(1.,(std::max)(std::abs(initial),std::abs(r.analytic)));
  r.tolerance=(std::max)(1e-10,16.*steps*std::numeric_limits<double>::epsilon()*scale);
  r.pass=std::isfinite(r.value)&&r.mismatches==0&&r.pre_error<=r.tolerance&&r.full_error<=r.tolerance;
  return r;
}
class PeriodicFixture:public JSphCpuSingle{
public:
  void CheckCopies(bool verlet){
    DomPosMin=TDouble3(0);Scell=1.;DomCellCode=(8u<<10)|(4u<<15);
    unsigned id[4]={7,9,0,0},dcell[4]={};const unsigned list[2]={0,0x80000001u};
    typecode code[4]={CODE_TYPE_FLUID,CODE_TYPE_FLUID,0,0};
    tdouble3 pos[4]={TDouble3(2),TDouble3(4),TDouble3(0),TDouble3(0)},pospre[4]={};
    tfloat4 vel[4]={},velold[4]={};tsymatrix3f sigma[4]={},sigmaold[4]={};
    double pressure[4]={20000.0003,10000.0001,0,0},old[4]={19999.0002,9999.0002,0,0};
    double reference[4]={1.000000001,2.000000002,0,0};float rate[4]={3,4,0,0};
    if(verlet)PeriodicDuplicateVerlet(2,2,TUint3(15),TDouble3(1,0,0),list,id,code,dcell,pos,vel,NULL,
      velold,sigma,sigmaold,pressure,reference,rate,old);
    else PeriodicDuplicateSymplectic(2,2,TUint3(15),TDouble3(1,0,0),list,id,code,dcell,pos,vel,NULL,
      pospre,velold,sigma,sigmaold,pressure,reference,rate,old);
    for(unsigned p=0;p<2;p++){
      Require(id[p+2]==id[p]&&!CODE_IsNormal(code[p+2]),"Periodic ID/code mismatch");
      Require(Same(pressure[p+2],pressure[p])&&Same(old[p+2],old[p]),"Periodic current/history double mismatch");
      Require(Same(reference[p+2],reference[p])&&Same(rate[p+2],rate[p]),"Periodic reference/rate mismatch");
    }
    Require(pos[2].x==3.&&pos[3].x==3.,"Forward/inverse periodic position mismatch");
  }
};
class OutputFixture:public JSphCpu{
  unsigned id[4]={9,9,5,1};typecode code[4];tdouble3 pos[4];tfloat4 vel[4];
  double pressure[4]={20000.0003,20000.0003,10000.0001,15000.0002},reference[4]={1.000000001,1.000000001,2.000000002,3.000000003};
public:
  OutputFixture():JSphCpu(false){
    Np=4;HydroMech=true;
    for(unsigned p=0;p<4;p++){code[p]=CODE_TYPE_FLUID;pos[p]=TDouble3(id[p]);vel[p]=TFloat4(0,0,0,2100);}
    code[1]=CODE_SetPeriodic(code[1]);code[3]=CODE_SetOutIgnore(code[3]);
    Idpc=id;Codec=code;Posc=pos;Velrhopc=vel;PorePressc=pressure;PorePress0c=reference;
  }
  ~OutputFixture(){Idpc=NULL;Codec=NULL;Posc=NULL;Velrhopc=NULL;PorePressc=PorePress0c=NULL;}
  void CheckCompaction(){
    unsigned outid[4];tdouble3 outpos[4];tfloat3 outvel[4];typecode outcode[4];float outrhop[4];
    double outpressure[4],outreference[4];
    const unsigned count=GetParticlesData(4,0,true,outid,outpos,outvel,outrhop,NULL,NULL,NULL,outcode,
      NULL,NULL,NULL,outpressure,outreference,NULL);
    Require(count==2&&outid[0]==9&&outid[1]==5,"Normal-only compaction ID/count mismatch");
    Require(Same(outpressure[1],pressure[2])&&Same(outreference[1],reference[2]),"Output lost double precision or mapping");
  }
};
struct Check{std::string name,detail;bool pass;};
static void Test(std::vector<Check>& checks,const std::string& name,const std::function<void()>& action){
  try{action();checks.push_back({name,"",true});}
  catch(const std::exception& e){checks.push_back({name,e.what(),false});}
  catch(...){checks.push_back({name,"Unknown exception",false});}
}
static int CompareParts(int argc,char** argv){
  Require(argc==8&&std::string(argv[6])=="--json","Usage: --compare-parts BEFORE_DIR PART AFTER_DIR PART --json NEW.json");
  Require(!std::filesystem::exists(argv[7]),"Refusing to overwrite result");
  JPartDataBi4 before,after;
  before.LoadFilePart(argv[2],unsigned(std::stoul(argv[3])));
  after.LoadFilePart(argv[4],unsigned(std::stoul(argv[5])));
  Require(before.GetNpiece()==1&&after.GetNpiece()==1,"This solver fixture expects one PART piece");
  const unsigned n=before.Get_Npok();Require(after.Get_Npok()==n,"Different particle counts");
  std::vector<unsigned> bid(n),aid(n),bindex(n),aindex(n);before.Get_Idp(n,bid.data());after.Get_Idp(n,aid.data());
  for(unsigned p=0;p<n;p++){Require(bid[p]<n&&aid[p]<n,"Expected complete contiguous IDs");bindex[bid[p]]=p;aindex[aid[p]]=p;}
  std::ofstream out(argv[7]);Require(bool(out),"Cannot create checkpoint result");
  out<<std::setprecision(17)<<"{\"scope\":\"Actual saved double PART -> solver restart -> initial saved PART, aligned by particle ID. Not full restart trajectory equivalence.\",\"count\":"<<n<<",\"before_time\":"<<before.Get_TimeStep()<<",\"after_time\":"<<after.Get_TimeStep()<<",\"fields\":[";
  unsigned failures=0,field=0;
  for(const char* name:{"PorePress","PorePress0"}){
    std::vector<double> b(n),a(n);
    before.GetArray(name,JBinaryDataDef::DatDouble)->GetDataCopy(n,b.data());
    after.GetArray(name,JBinaryDataDef::DatDouble)->GetDataCopy(n,a.data());
    unsigned different=0;double maxdelta=0;
    for(unsigned id=0;id<n;id++){const double bv=b[bindex[id]],av=a[aindex[id]];if(!Same(bv,av))different++;maxdelta=(std::max)(maxdelta,std::abs(av-bv));}
    if(different)failures++;if(field++)out<<',';
    out<<"{\"name\":\""<<name<<"\",\"storage\":\"double\",\"bit_mismatches\":"<<different<<",\"max_abs_difference\":"<<maxdelta<<'}';
  }
  out<<"],\"passed\":"<<(failures?"false":"true")<<"}\n";out.flush();Require(bool(out),"Checkpoint JSON write failed");
  return failures?1:0;
}
static int ExportState(int argc,char** argv){
  Require(argc==6&&std::string(argv[4])=="--csv","Usage: --export-state DIR PART --csv NEW.csv");
  Require(!std::filesystem::exists(argv[5]),"Refusing to overwrite export");
  JPartDataBi4 part;part.LoadFilePart(argv[2],unsigned(std::stoul(argv[3])));
  Require(part.GetNpiece()==1,"Single-piece fixture expected");const unsigned n=part.Get_Npok();
  std::vector<unsigned> id(n);part.Get_Idp(n,id.data());
  std::vector<double> pressure(n),reference(n),stored(n),low(n,0.);
  unsigned field=0;
  for(const char* name:{"PorePress","PorePress0"}){
    auto array=part.GetArray(name);Require((array->DataInPointer()?array->GetCount():array->GetFileDataCount())==n,"Pore array count mismatch");auto& target=field++?reference:pressure;
    if(array->GetType()==JBinaryDataDef::DatDouble)array->GetDataCopy(n,target.data());
    else{Require(array->GetType()==JBinaryDataDef::DatFloat,"Unsupported pore type");std::vector<float> temporary(n);array->GetDataCopy(n,temporary.data());for(unsigned i=0;i<n;i++)target[i]=double(temporary[i]);}
  }
  stored=pressure;
  if(part.ArrayExists("PorePressRes")){
    std::vector<float> temporary(n);part.GetArray("PorePressRes",JBinaryDataDef::DatFloat)->GetDataCopy(n,temporary.data());
    for(unsigned i=0;i<n;i++){low[i]=double(temporary[i]);pressure[i]+=low[i];}
  }
  std::ofstream out(argv[5]);Require(bool(out),"Cannot create native export");out<<std::setprecision(17)<<"id,pressure_pa,reference_pa,stored_pressure_pa,residual_pa,time_s\n";
  for(unsigned i=0;i<n;i++){Require(std::isfinite(pressure[i])&&std::isfinite(reference[i]),"Nonfinite pressure");out<<id[i]<<','<<pressure[i]<<','<<reference[i]<<','<<stored[i]<<','<<low[i]<<','<<part.Get_TimeStep()<<'\n';}
  out.flush();Require(bool(out),"CSV write failed");return 0;
}
int main(int argc,char** argv){
  try{
    if(argc>1&&std::string(argv[1])=="--compare-parts")return CompareParts(argc,argv);
    if(argc>1&&std::string(argv[1])=="--export-state")return ExportState(argc,argv);
    Require(argc==3&&std::string(argv[1])=="--json","Usage: cpu_state_harness --json NEW.json");
    Require(!std::filesystem::exists(argv[2]),"Refusing to overwrite JSON");omp_set_num_threads(1);
    std::vector<Result> results;std::vector<Check> checks;
    const double dt[]={625e-9,250e-9,125e-9,62.5e-9};const unsigned steps[]={800,2000,4000,8000};
    for(bool verlet:{false,true}){
      for(double p:{0.,10000.,20000.})for(float rate:{0.f,1.f,-1.f,1e3f,-1e3f,1e4f,-1e4f,1e7f,-1e7f})
        for(unsigned d=0;d<4;d++)results.push_back(Evaluate(p,rate,dt[d],steps[d],verlet));
      results.push_back(Evaluate(20000.0003,0.f,62.5e-9,8000,verlet));
      const std::string scheme=verlet?"Verlet":"Symplectic";
      Test(checks,scheme+"_periodic_double_copy",[&](){PeriodicFixture f;f.CheckCopies(verlet);});
      Test(checks,scheme+"_boundary_double_copy",[&](){PressureFixture f(20000.0003,1e7f,verlet);f.SetBoundary();f.Step(62.5e-9,verlet);Require(Same(f.Value(),20000.0003),"Boundary changed");});
      Test(checks,scheme+"_nonfluid_copy",[&](){PressureFixture f(20000.0003,1e7f,verlet);f.SetNonFluid();f.Step(62.5e-9,verlet);Require(Same(f.Value(),20000.0003),"Nonfluid changed");});
      Test(checks,scheme+"_drained_zero",[&](){PressureFixture f(20000.0003,1.f,verlet);f.SetDrained();f.Step(62.5e-9,verlet);Require(Same(f.Value(),0.),"Drain did not prescribe zero");});
    }
    Test(checks,"normal_output_double_compaction",[&](){OutputFixture f;f.CheckCompaction();});
    unsigned failures=0;for(const auto& r:results)if(!r.pass)failures++;
    for(const auto& c:checks){if(!c.pass)failures++;std::cout<<(c.pass?"PASS ":"FAIL ")<<c.name<<' '<<c.detail<<'\n';}
    std::ofstream out(argv[2]);Require(bool(out),"Cannot create JSON");out<<std::setprecision(17);
    out<<"{\"completed\":true,\"passed\":"<<(failures?"false":"true")<<",\"failure_count\":"<<failures
      <<",\"integration_case_count\":"<<results.size()<<",\"scope\":\"Actual CPU pressure methods, frozen float rate, double state. Memory-resume and mapping only; BI4 loader tested separately. Not full coupled temporal convergence.\",\"cases\":[";
    for(size_t i=0;i<results.size();i++){
      const auto& r=results[i];if(i)out<<',';
      out<<"{\"scheme\":"<<Quote(r.scheme)<<",\"initial_pa\":"<<r.initial<<",\"rate_pa_s\":"<<r.rate<<",\"dt_s\":"<<r.dt<<",\"steps\":"<<r.steps
        <<",\"analytic_pa\":"<<r.analytic<<",\"value_pa\":"<<r.value<<",\"error_pa\":"<<r.value-r.analytic
        <<",\"legacy_float_pa\":"<<r.legacy<<",\"legacy_float_error_pa\":"<<r.legacy-r.analytic<<",\"max_predictor_error_pa\":"<<r.pre_error
        <<",\"max_full_error_pa\":"<<r.full_error<<",\"tolerance_pa\":"<<r.tolerance<<",\"resume_bit_mismatches\":"<<r.mismatches<<",\"pass\":"<<(r.pass?"true":"false")<<'}';
    }
    out<<"],\"checks\":[";
    for(size_t i=0;i<checks.size();i++){const auto& c=checks[i];if(i)out<<',';out<<"{\"name\":"<<Quote(c.name)<<",\"pass\":"<<(c.pass?"true":"false")<<",\"detail\":"<<Quote(c.detail)<<'}';}
    out<<"]}\n";out.flush();Require(bool(out),"JSON write failed");
    std::cout<<"COMPLETE cases="<<results.size()<<" checks="<<checks.size()<<" failures="<<failures<<'\n';return failures?1:0;
  }
  catch(const std::exception& e){std::cerr<<"HARNESS ERROR: "<<e.what()<<'\n';return 2;}
}
