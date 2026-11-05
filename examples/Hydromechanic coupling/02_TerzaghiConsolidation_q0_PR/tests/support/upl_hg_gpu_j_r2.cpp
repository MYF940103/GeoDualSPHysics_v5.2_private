// Real CPU versus real CUDA single-J HG, using the retained independent oracle.
// r1 remains unchanged, including its failed Debug record. Exact history update
// arithmetic is checked separately from independent dense near-zero cancellation.
// Compile this translation unit, not the included CPU fixture a second time.
// The unchanged hg_gpu_hourglass_test.cpp remains the separate NULL-J suite.
#define main UplRetainedCpuOracleMain
#include "upl_hg_cpu_oracle_r2.cpp"
#undef main
#include "JSphHourglassGpu.h"
#include <cuda_runtime.h>

namespace{
void CudaJ(cudaError_t error){if(error!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(error));}
void SyncJ(){CudaJ(cudaGetLastError());CudaJ(cudaDeviceSynchronize());}
template<class A> void BitsJ(const A& a,const A& b,const std::string& what){Require(std::memcmp(&a,&b,sizeof(A))==0,"HG bit mismatch: "+what);}
template<class A> struct DeviceJ{
  A* p=nullptr;unsigned count;
  explicit DeviceJ(unsigned n):count(n){CudaJ(cudaMalloc(reinterpret_cast<void**>(&p),sizeof(A)*n));}
  ~DeviceJ(){if(p)cudaFree(p);}
  DeviceJ(const DeviceJ&)=delete;DeviceJ& operator=(const DeviceJ&)=delete;
  void Put(const std::vector<A>& a){Require(a.size()<=count,"Device fixture capacity");CudaJ(cudaMemcpy(p,a.data(),sizeof(A)*a.size(),cudaMemcpyHostToDevice));}
  std::vector<A> Get(unsigned n)const{Require(n<=count,"Download fixture capacity");std::vector<A> a(n);CudaJ(cudaMemcpy(a.data(),p,sizeof(A)*n,cudaMemcpyDeviceToHost));return a;}
};
struct GpuJ{
  JSphHourglassGpu h;DeviceJ<unsigned> id;DeviceJ<typecode> code;DeviceJ<double2> xy;
  DeviceJ<double> z,ratej,forcej;DeviceJ<float4> vel;DeviceJ<float> plastic;DeviceJ<float3> ace;
  GpuJ(const State& s,bool cache):id(s.Size()+8),code(s.Size()+8),xy(s.Size()+8),z(s.Size()+8),ratej(s.Size()+8),forcej(s.Size()+8),vel(s.Size()+8),plastic(s.Size()+8),ace(s.Size()+8){
    h.Config(First,s.Count(),s.xi,s.mass,s.period,s.h,s.support,s.bwen,s.shear,s.rho0,s.rhow);h.SetRateCacheEnabled(cache);
  }
  void Put(const State& s){
    std::vector<double2> a;std::vector<double> b;std::vector<float4> v;std::vector<float3> q;
    for(unsigned p=0;p<s.Size();p++){a.push_back(make_double2(s.pos[p].x,s.pos[p].y));b.push_back(s.pos[p].z);v.push_back(make_float4(s.vel[p].x,s.vel[p].y,s.vel[p].z,s.vel[p].w));q.push_back(make_float3(s.ace[p].x,s.ace[p].y,s.ace[p].z));}
    id.Put(s.id);code.Put(s.code);xy.Put(a);z.Put(b);vel.Put(v);plastic.Put(s.plastic);ace.Put(q);
  }
  void Predictor(const State& s,bool missing=false){Put(s);ratej.Put(s.j);h.PredictorForce(s.Size(),Npb,id.p,code.p,xy.p,z.p,vel.p,plastic.p,ace.p,Dt,missing?nullptr:ratej.p);SyncJ();}
  void Corrector(const State& s,bool missing=false){Put(s);forcej.Put(s.j);h.CorrectorForce(s.Size(),Npb,id.p,code.p,ace.p,missing?nullptr:forcej.p);SyncJ();}
  void Endpoint(const State& s,bool missing=false){Put(s);ratej.Put(s.j);h.CorrectorUpdate(s.Size(),Npb,id.p,code.p,xy.p,z.p,vel.p,plastic.p,Dt,missing?nullptr:ratej.p);SyncJ();}
  void PoisonPredictorJ(){std::vector<double> bad(ratej.count,std::numeric_limits<double>::quiet_NaN());ratej.Put(bad);}
};
double MaxCpuActual=0,MaxGpuActual=0,MaxActualDifference=0,UlpLower=0,UlpUpper=0,UlpVolume=0;
unsigned HistoryRecurrenceBitChecks=0,ForceHistoryBitChecks=0;
std::map<std::string,Metric> AffineDenseDiagnostics;
std::map<std::string,unsigned> AffineDenseExceeds;
template<class H> std::vector<tdouble3> SnapshotHistoryJ(const H& h,unsigned count,bool rate=false){
  std::vector<tdouble3> result;for(unsigned i=0;i<count;i++)result.push_back(rate?h.GetRate(First+i):h.GetHistory(First+i));return result;
}
template<class H> void HistoryBitsJ(const std::string& stage,const std::vector<tdouble3>& before,const std::vector<tdouble3>& input,const H& h){
  Require(input.empty()||input.size()==before.size(),"History recurrence input size");
  for(unsigned i=0;i<before.size();i++){
    double x=before[i].x,z=before[i].z;
    if(!input.empty()){
      // Explicit binary64 writebacks prevent this test oracle contracting FMA.
      volatile double halfdt=.5*Dt;
      volatile double dx=halfdt*input[i].x,dz=halfdt*input[i].z;
      volatile double nextx=x+dx,nextz=z+dz;x=nextx;z=nextz;
    }
    const auto actual=h.GetHistory(First+i);BitsJ(actual.x,x,stage+".x");BitsJ(actual.z,z,stage+".z");
    if(input.empty())ForceHistoryBitChecks+=2;else HistoryRecurrenceBitChecks+=2;
  }
}
template<class H> void AffineDenseHistoryJ(const std::string& backend,const std::vector<tdouble3>& dense,const H& h){
  double error=0,scale=0;
  for(unsigned i=0;i<dense.size();i++){const auto actual=h.GetHistory(First+i);error=(std::max)(error,std::hypot(actual.x-dense[i].x,actual.z-dense[i].z));scale=(std::max)(scale,Norm(dense[i]));}
  const double limit=HistoryTolerance*(std::max)(1e-15,scale);
  Require(std::isfinite(error)&&std::isfinite(limit)&&limit>0,"Nonfinite affine dense diagnostic");
  auto& metric=AffineDenseDiagnostics[backend];metric.checks++;metric.error=(std::max)(metric.error,error);metric.ratio=(std::max)(metric.ratio,error/limit);
  if(error>limit)AffineDenseExceeds[backend]++;
}
void HistoryReferenceJ(bool affine,const JSphHourglassCpu& cpu,const GpuJ& on,const GpuJ& off,const std::vector<tdouble3>& dense){
  if(!affine){HistoryCheck(cpu,dense);return;}
  // The manufactured velocities/coordinates are exactly representable affine
  // fields and start with zero H. Their analytical history is zero. Dense()
  // remains untouched and independently checked at every rate stage.
  const std::vector<tdouble3> zero(dense.size(),TDouble3(0));HistoryCheck(cpu,zero);
  for(unsigned i=0;i<dense.size();i++){
    Near("J_GPU_affine_analytic_history",Norm(on.h.GetHistory(First+i)),HistoryTolerance*1e-15);
    Near("J_GPU_affine_analytic_history",Norm(off.h.GetHistory(First+i)),HistoryTolerance*1e-15);
  }
  // Preserve the former joint dense-history gate's result, including failures,
  // as an explicitly non-passing diagnostic rather than relaxing its budget.
  AffineDenseHistoryJ("CPU",dense,cpu);AffineDenseHistoryJ("GPU_cache_on",dense,on.h);AffineDenseHistoryJ("GPU_cache_off",dense,off.h);
}

void CompareJ(const State& before,const State& cpuState,const JSphHourglassCpu& cpu,const GpuJ& on,const GpuJ& off,bool force){
  double rateError=0,rateScale=0,historyError=0,historyScale=0;
  for(unsigned i=0;i<before.Count();i++){
    const auto cr=cpu.GetRate(First+i),ch=cpu.GetHistory(First+i),gr=on.h.GetRate(First+i),gh=on.h.GetHistory(First+i);
    const auto fr=off.h.GetRate(First+i),fh=off.h.GetHistory(First+i);
    BitsJ(gr.x,fr.x,"rate.x");BitsJ(gr.z,fr.z,"rate.z");BitsJ(gh.x,fh.x,"history.x");BitsJ(gh.z,fh.z,"history.z");
    rateError=(std::max)({rateError,std::abs(cr.x-gr.x),std::abs(cr.z-gr.z)});rateScale=(std::max)({rateScale,std::abs(cr.x),std::abs(cr.z)});
    historyError=(std::max)({historyError,std::abs(ch.x-gh.x),std::abs(ch.z-gh.z)});historyScale=(std::max)({historyScale,std::abs(ch.x),std::abs(ch.z)});
  }
  Near("J_cpu_gpu_rate",rateError,DoubleTolerance*(1+rateScale));Near("J_cpu_gpu_history",historyError,DoubleTolerance*(1+historyScale));
  const auto& c=cpu.GetRateInfo();const auto& g=on.h.GetRateInfo();const auto& f=off.h.GetRateInfo();
#define JRI(a) Scalar("J_rateinfo_" #a,g.a,c.a);BitsJ(g.a,f.a,"rateinfo." #a)
  JRI(netx);JRI(netz);JRI(condition);JRI(skew);JRI(form);JRI(lambda);JRI(tau);JRI(ratepower);JRI(workerror);JRI(rmax);JRI(sumrate);JRI(meandxx);JRI(rmsdxx);JRI(meandiv);JRI(rmsdiv);
#undef JRI
  Near("J_gpu_virtual_work",std::abs(g.ratepower+2*g.form),WorkTolerance*(1+std::abs(g.ratepower)+2*g.form));
  Require(cpu.GetPairCount()==on.h.GetPairCount()&&on.h.GetPairCount()==off.h.GetPairCount(),"J native pair count differs");
  const auto& cs=cpu.GetStats();const auto& gs=on.h.GetStats();const auto& fs=off.h.GetStats();
#define JCNT(a) Require(cs.a==gs.a&&gs.a==fs.a,"J phase/count " #a)
  JCNT(forcecalls);JCNT(predictorupdates);JCNT(correctorupdates);JCNT(ratecalls);JCNT(predictorrates);JCNT(endpointrates);JCNT(firstpairs);JCNT(minpairs);JCNT(maxpairs);
#undef JCNT
#define JST(a) Scalar("J_stats_" #a,gs.a,cs.a);BitsJ(gs.a,fs.a,"stats." #a)
  JST(maxnetforce);JST(maxnetrate);JST(maxrelativeforce);JST(maxrelativerate);JST(maxhistory);JST(maxcondition);JST(maxpoweridentityerror);JST(maxskew);JST(spinbound);JST(maxtauratio);JST(mintau);JST(maxlambda);
#undef JST
  Require(gs.ratecalculations+gs.ratecachehits==gs.ratecalls&&fs.ratecalculations==fs.ratecalls&&!fs.ratecachehits,"J logical/actual rate counts differ");
  BitsJ(gs.maxactualnetforce,fs.maxactualnetforce,"actual float net force");
  MaxCpuActual=(std::max)(MaxCpuActual,cs.maxactualnetforce);MaxGpuActual=(std::max)(MaxGpuActual,gs.maxactualnetforce);
  MaxActualDifference=(std::max)(MaxActualDifference,std::abs(cs.maxactualnetforce-gs.maxactualnetforce));
  if(!force)return;
  const auto a=on.ace.Get(before.Size()),b=off.ace.Get(before.Size());double netx=0,netz=0,sum=0,referenceX=0,referenceZ=0,referenceSum=0;
  for(unsigned p=0;p<before.Size();p++){
    BitsJ(a[p].x,b[p].x,"ace.x");BitsJ(a[p].y,b[p].y,"ace.y");BitsJ(a[p].z,b[p].z,"ace.z");
    if(!(p>=Npb&&CODE_IsNormal(before.code[p])&&CODE_IsFluid(before.code[p]))){
      BitsJ(a[p].x,before.ace[p].x,"ignored ace.x");BitsJ(a[p].y,before.ace[p].y,"ignored ace.y");BitsJ(a[p].z,before.ace[p].z,"ignored ace.z");continue;
    }
    const unsigned i=before.id[p]-First;const double mass=Inertia(before,i),factor=before.mass/mass;const auto history=on.h.GetHistory(First+i);
    const double expected[2]={factor*history.x,factor*history.z},actual[2]={double(a[p].x)-before.ace[p].x,double(a[p].z)-before.ace[p].z};
    for(unsigned k=0;k<2;k++)Near("J_current_inertia_float_acceleration",std::abs(actual[k]-expected[k]),FloatTolerance*(std::max)(1e-30,std::abs(expected[k])));
    BitsJ(a[p].y,before.ace[p].y,"transverse ace");
    Near("J_cpu_gpu_float_ace_x",std::abs(double(a[p].x)-cpuState.ace[p].x),FloatTolerance*(std::max)(1.,std::abs(double(cpuState.ace[p].x))));
    Near("J_cpu_gpu_float_ace_z",std::abs(double(a[p].z)-cpuState.ace[p].z),FloatTolerance*(std::max)(1.,std::abs(double(cpuState.ace[p].z))));
    netx+=mass*actual[0];netz+=mass*actual[1];sum+=mass*std::hypot(actual[0],actual[1]);
    referenceX+=before.mass*history.x;referenceZ+=before.mass*history.z;referenceSum+=before.mass*Norm(history);
  }
  Near("J_reference_history_net_force",std::hypot(referenceX,referenceZ),1e-10*(std::max)(1e-15,referenceSum));
  Near("J_current_mass_float_net_force",std::hypot(netx,netz),FloatTolerance*(std::max)(1e-30,sum));
}

void CaseJ(const std::string& name,const std::string& material,const std::string& velocity){
  State s;s.J(material);s.Velocity(velocity);JSphHourglassCpu cpu;Configure(cpu,s);GpuJ on(s,true),off(s,false);
  const bool affine=velocity=="translation"||velocity=="periodic_affine";
  std::vector<tdouble3> expected(s.Count(),TDouble3(0));
  if(name=="raw_J_one_ULP"){
    UlpLower=.8;bool found=false;
    for(unsigned k=0;k<2048;k++){UlpUpper=std::nextafter(UlpLower,1.);if(s.mass/s.rho0*UlpLower==s.mass/s.rho0*UlpUpper){found=true;break;}UlpLower=UlpUpper;}
    Require(found,"Retained one-ULP equal-volume witness unavailable");UlpVolume=s.mass/s.rho0*UlpLower;s.j[s.Slot(13)]=UlpLower;
  }
  for(unsigned step=0;step<4;step++){
    if(step==1&&name=="raw_J_one_ULP")s.j[s.Slot(13)]=UlpUpper;
    if(step==1&&name=="native_reorder_periodic_copies"){
      s.Reverse();for(unsigned p=Npb;p<s.Size();p++)if(CODE_IsPeriodic(s.code[p])){s.pos[p]=TDouble3(999);s.vel[p]=TFloat4(999);s.j[p]=-99;s.plastic[p]=1;}
      s.Append(First+13,CODE_SetPeriodic(CODE_TYPE_FLUID),TDouble3(-99),TFloat4(999),std::numeric_limits<double>::quiet_NaN());
    }
    std::vector<tdouble3> priorRate,priorHistory;
    if(step==1&&name=="passive_legacy_Rhop"){
      for(unsigned i=0;i<s.Count();i++){priorRate.push_back(on.h.GetRate(First+i));priorHistory.push_back(on.h.GetHistory(First+i));s.vel[s.Slot(i)].w=(i%4==0?0:i%4==1?-1:i%4==2?std::numeric_limits<float>::quiet_NaN():std::numeric_limits<float>::infinity());}
    }
    s.ResetAce();State c=s;const auto hits=on.h.GetStats().ratecachehits,calculations=on.h.GetStats().ratecalculations;
    const auto cpuBefore=SnapshotHistoryJ(cpu,s.Count()),onBefore=SnapshotHistoryJ(on.h,s.Count()),offBefore=SnapshotHistoryJ(off.h,s.Count());
    Predictor(cpu,c);on.Predictor(s);off.Predictor(s);CompareJ(s,c,cpu,on,off,true);
    HistoryBitsJ("CPU_predictor_force_unchanged",cpuBefore,{},cpu);HistoryBitsJ("GPU_on_predictor_force_unchanged",onBefore,{},on.h);HistoryBitsJ("GPU_off_predictor_force_unchanged",offBefore,{},off.h);
    const bool miss=step==0||(step==1&&name=="raw_J_one_ULP");
    Require(on.h.GetStats().ratecachehits==hits+unsigned(!miss)&&on.h.GetStats().ratecalculations==calculations+unsigned(miss),"Wrong raw-J/native-state GPU cache decision");
    for(unsigned i=0;i<priorRate.size();i++){
      const auto r=on.h.GetRate(First+i),h=on.h.GetHistory(First+i);
      BitsJ(r.x,priorRate[i].x,"passive Rhop rate.x");BitsJ(r.z,priorRate[i].z,"passive Rhop rate.z");BitsJ(h.x,priorHistory[i].x,"passive Rhop history.x");BitsJ(h.z,priorHistory[i].z,"passive Rhop history.z");
    }
    OracleCheck(s,cpu,affine);const auto first=Dense(s);
    const auto cpuInput=SnapshotHistoryJ(cpu,s.Count(),true),onInput=SnapshotHistoryJ(on.h,s.Count(),true),offInput=SnapshotHistoryJ(off.h,s.Count(),true);
    cpu.PredictorUpdate(Dt);on.h.PredictorUpdate(Dt);off.h.PredictorUpdate(Dt);SyncJ();
    HistoryBitsJ("CPU_predictor_update",cpuBefore,cpuInput,cpu);HistoryBitsJ("GPU_on_predictor_update",onBefore,onInput,on.h);HistoryBitsJ("GPU_off_predictor_update",offBefore,offInput,off.h);
    for(unsigned i=0;i<s.Count();i++){expected[i].x+=.5*Dt*first.rate[i].x;expected[i].z+=.5*Dt*first.rate[i].z;}
    HistoryReferenceJ(affine,cpu,on,off,expected);CompareJ(s,c,cpu,on,off,false);
    if(name=="fresh_corrector_J"){
      State half=s;for(unsigned i=0;i<half.Count();i++)half.j[half.Slot(i)]=.64+.065*(i%11);half.Reverse();
      // Poison only the old predictor buffers; both current half-stage arrays are separate and valid.
      std::fill(c.j.begin(),c.j.end(),std::numeric_limits<double>::quiet_NaN());on.PoisonPredictorJ();off.PoisonPredictorJ();s=half;
    }
    s.ResetAce();State halfCpu=s;const auto logical=cpu.GetStats().ratecalls;
    const auto cpuHalf=SnapshotHistoryJ(cpu,s.Count()),onHalf=SnapshotHistoryJ(on.h,s.Count()),offHalf=SnapshotHistoryJ(off.h,s.Count());
    Corrector(cpu,halfCpu);on.Corrector(s);off.Corrector(s);CompareJ(s,halfCpu,cpu,on,off,true);
    HistoryBitsJ("CPU_corrector_force_unchanged",cpuHalf,{},cpu);HistoryBitsJ("GPU_on_corrector_force_unchanged",onHalf,{},on.h);HistoryBitsJ("GPU_off_corrector_force_unchanged",offHalf,{},off.h);
    Require(cpu.GetStats().ratecalls==logical,"Corrector force recalculated its rate");HistoryReferenceJ(affine,cpu,on,off,expected);
    if(name=="fresh_corrector_J"){
      s.J("uniform");s.Velocity("random");for(unsigned i=0;i<s.Count();i++)s.pos[s.Slot(i)].z+=.0002*std::sin(.31*i);
    }
    const auto last=Dense(s);c=s;const auto calc=on.h.GetStats().ratecalculations;
    // CorrectorUpdate computes a fresh endpoint rate then consumes it once;
    // the verified production UpdateHistory does not modify that rate buffer.
    Endpoint(cpu,c);HistoryBitsJ("CPU_endpoint_update",cpuHalf,SnapshotHistoryJ(cpu,s.Count(),true),cpu);
    on.Endpoint(s);HistoryBitsJ("GPU_on_endpoint_update",onHalf,SnapshotHistoryJ(on.h,s.Count(),true),on.h);
    off.Endpoint(s);HistoryBitsJ("GPU_off_endpoint_update",offHalf,SnapshotHistoryJ(off.h,s.Count(),true),off.h);CompareJ(s,c,cpu,on,off,false);
    Require(on.h.GetStats().ratecalculations==calc+1,"Endpoint unexpectedly reused a cached rate");
    OracleCheck(s,cpu,affine);
    for(unsigned i=0;i<s.Count();i++){expected[i].x+=.5*Dt*last.rate[i].x;expected[i].z+=.5*Dt*last.rate[i].z;}
    HistoryReferenceJ(affine,cpu,on,off,expected);
  }
  Passed.push_back("GPU_J_"+name);std::cout<<"PASS GPU_J "<<name<<'\n';
}

void GuardsJ(){
  for(const std::string stage:{"predictor","corrector","endpoint"})for(const std::string bad:{"missing","zero","negative","nan","infinite","overflow_inertia"}){
    State s;s.J("nonuniform");JSphHourglassCpu cpu;Configure(cpu,s);GpuJ g(s,true);State c=s;
    // For predictor rejection populate an exact endpoint first, so invalid J cannot hide in a cache.
    Predictor(cpu,c);g.Predictor(s);cpu.PredictorUpdate(Dt);g.h.PredictorUpdate(Dt);
    if(stage!="corrector"){c=s;Corrector(cpu,c);g.Corrector(s);}
    if(stage=="predictor"){Endpoint(cpu,s);g.Endpoint(s);}
    if(bad!="missing")s.j[s.Slot(13)]=(bad=="zero"?0:bad=="negative"?-1:bad=="nan"?std::numeric_limits<double>::quiet_NaN():bad=="infinite"?std::numeric_limits<double>::infinity():DBL_MAX);
    const auto cp=[&]{
      const double* j=bad=="missing"?nullptr:s.j.data();
      if(stage=="predictor")cpu.PredictorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),s.ace.data(),Dt,j);
      else if(stage=="corrector")cpu.CorrectorForce(s.Size(),Npb,s.id.data(),s.code.data(),s.ace.data(),j);
      else cpu.CorrectorUpdate(s.Size(),Npb,s.id.data(),s.code.data(),s.pos.data(),s.vel.data(),s.plastic.data(),Dt,j);
    };
    const auto gp=[&]{if(stage=="predictor")g.Predictor(s,bad=="missing");else if(stage=="corrector")g.Corrector(s,bad=="missing");else g.Endpoint(s,bad=="missing");};
    Reject("CPU_J_"+stage+"_"+bad,cp);Reject("GPU_J_"+stage+"_"+bad,gp);SyncJ();
  }
}
}

int main(int argc,char** argv){
  if(argc!=3||std::string(argv[1])!="--json"||std::filesystem::exists(argv[2])){std::cerr<<"Use upl_hg_gpu_j_r2 --json NEW_CHECK_JSON\n";return 2;}
  bool passed=false;std::string reason,device;
  try{
    AppInfo.LogInit("");CudaJ(cudaSetDevice(0));cudaDeviceProp info;CudaJ(cudaGetDeviceProperties(&info,0));device=info.name;
    for(const std::string material:{"J1","uniform","nonuniform"})for(const std::string mode:{"translation","periodic_affine","checkerboard","random"})CaseJ(material+"_"+mode,material,mode);
    for(const std::string name:{"fresh_corrector_J","raw_J_one_ULP","native_reorder_periodic_copies","passive_legacy_Rhop"})CaseJ(name,"nonuniform","random");
    GuardsJ();SyncJ();passed=true;
  }catch(const std::exception& e){reason=e.what();std::cerr<<reason<<'\n';}catch(...){reason="Non-standard fixture exception";}
  std::ofstream out(argv[2]);out<<std::setprecision(17)<<"{\"stage\":\"upl_hg_gpu_j_r2\",\"passed\":"<<(passed?"true":"false")<<",\"reason\":"<<Json(reason)<<",\"device\":"<<Json(device)
    <<",\"physical_acceptance\":false,\"solver_run\":false,\"four_phase_cycles_per_valid_case\":4,\"double_relative_plus_absolute_tolerance\":"<<DoubleTolerance<<",\"float_epsilon_multiplier\":64,\"work_tolerance\":"<<WorkTolerance
    <<",\"gpu_cache_required_max_ulp\":0,\"legacy_NULL_J_suite_executed_here\":false,\"legacy_NULL_J_required_separate_fixture\":\"hg_gpu_hourglass_test.cpp\",\"raw_J_equal_volume_witness\":{\"lower\":"<<UlpLower<<",\"upper\":"<<UlpUpper<<",\"volume\":"<<UlpVolume<<"},\"passed_cases\":[";
  for(size_t i=0;i<Passed.size();i++)out<<(i?",":"")<<Json(Passed[i]);out<<"],\"metrics\":{";bool first=true;
  for(const auto& item:Metrics){out<<(first?"":",")<<Json(item.first)<<":{\"checks\":"<<item.second.checks<<",\"max_abs_error\":"<<item.second.error<<",\"max_error_over_limit\":"<<item.second.ratio<<'}';first=false;}
  out<<"},\"history_recurrence_bit_checks\":"<<HistoryRecurrenceBitChecks<<",\"force_no_history_write_bit_checks\":"<<ForceHistoryBitChecks
    <<",\"affine_dense_original_joint_gate_status\":\"diagnostic_only_not_claimed_passed_r1_failed\",\"affine_dense_original_budget_diagnostics\":{";
  bool firstDense=true;for(const auto& item:AffineDenseDiagnostics){out<<(firstDense?"":",")<<Json(item.first)<<":{\"checks\":"<<item.second.checks<<",\"max_abs_error\":"<<item.second.error<<",\"max_error_over_original_limit\":"<<item.second.ratio<<",\"checks_exceeding_original_limit\":"<<AffineDenseExceeds[item.first]<<'}';firstDense=false;}
  out<<"},\"actual_float_net_force_cross_backend\":{\"cpu_max\":"<<MaxCpuActual<<",\"gpu_max\":"<<MaxGpuActual<<",\"max_difference\":"<<MaxActualDifference<<",\"scope\":\"Descriptive CPU-GPU diagnostic; actual current-mi float balance and per-node 64eps gates remain mandatory\"},\"limitations\":[\"Real CPU/CUDA HG components only; no physical solver or half-step trajectory\",\"CPU/GPU double comparison is tolerance-based; cache-on/off and passive-Rhop identities are within the same GPU only\",\"No public coupled dynamic GPU, wall, Darcy, load, restart, long-time energy or full2Tv acceptance\",\"Retained legacy NULL-J GPU executable must be run separately against the same fresh authoritative objects\"]}\n";
  out.flush();if(!out){std::cerr<<"Cannot write check record\n";return 2;}return passed?0:1;
}
