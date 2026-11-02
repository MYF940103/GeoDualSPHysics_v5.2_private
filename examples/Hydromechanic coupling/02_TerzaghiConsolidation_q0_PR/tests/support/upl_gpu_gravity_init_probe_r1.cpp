// Actual fresh GPU Init guard probes only: no Run, force, ComputeStep, PART read or restart.
#define main RetainedGravityInitObserverMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main
#include "JCellDivGpuSingle.h"
#include "JDsTimersGpu.h"
#include "JException.h"
#include "JXml.h"
#include <cuda_runtime_api.h>
#include <vector_functions.h>
#include <cfloat>
#include <limits>
namespace gravityinit {
static const char* WallGeneral="GPU dynamic wall requires equal-dp fixed mDBC FreeSlip planes, finite tangential gravity and its own derivative closure.";
static const char* WallTangent="GPU dynamic wall requires gravity exactly tangent to every wall mirror vector.";
static const char* ObserverGravity="GPU porosity observer requires fresh bounded 2-D elastic Symplectic corrected-pair fixtures without load, drainage, shifting or damping; finite in-plane gravity requires the complete dynamic-rate model.";
static void Cu(cudaError_t e){Check(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){Check(p!=nullptr,"Required actual device array missing");std::vector<T> a(n);if(n)Cu(cudaMemcpy(a.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return a;}
template<class T>static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&(a.empty()||std::memcmp(a.data(),b.data(),a.size()*sizeof(T))==0);}
template<class T>static bool Bits(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
static std::string Q(const std::string& s){std::string out="\"";for(char c:s){if(c=='\"')out+="\"\"";else if(c=='\n')out+="\\n";else if(c=='\r')out+="\\r";else out+=c;}return out+"\"";}
static bool WallCase(const std::string& s){return s.rfind("wall_",0)==0;}
static void Case(const std::string& s){Check(s=="wall_zero"||s=="wall_tangent"||s=="wall_normal"||s=="wall_gy"||s=="wall_nan"||s=="wall_tiny"||s=="observer_zero"||s=="observer_gravity","Use one of the six wall or two observer cases");}
static void Runtime(const fs::path& path,bool wall){JXml x;x.LoadFile(path.string());const auto* h=x.GetNodeError("case.execution.special.hydromechanics");for(const char* k:{"HydroMechDynamicSeepage","HydroMechConductivityModel","HydroMechConductivityCk"})Check(x.ReadElementDouble(h,k,"value")==0,"Private seed must keep all public options OFF");const auto g=wall?TDouble3(0,0,-8):TDouble3(-8,0,0);Check(x.GetAttributeDouble3(x.GetFirstElement(x.GetNodeError("case.execution.constants"),"gravity"))==g&&x.GetAttributeDouble3(x.GetFirstElement(x.GetNodeError("case.casedef.constantsdef"),"gravity"))==g,"Use the actual retained wall/periodic gravity seed");}
struct DeviceView{
  std::vector<typecode> code;std::vector<unsigned> id;std::vector<double2> xy;std::vector<double> z,j,theta;std::vector<float4> vel;std::vector<float3> normal;std::vector<byte> slip;
};
class Probe:public JSphGpuSingle{
  DeviceView Device(bool wall)const{DeviceView a;a.code=Down(Codeg,Np);a.id=Down(Idpg,Np);a.xy=Down(Posxyg,Np);a.z=Down(Poszg,Np);a.vel=Down(Velrhopg,Np);a.j=Down(PoroJg,Np);a.theta=Down(PoroThetag,Np);if(wall){a.normal=Down(BoundNormalg,Np);if(BoundSlipModeg)a.slip=Down(BoundSlipModeg,Np);}return a;}
  static void Unchanged(const DeviceView& a,const DeviceView& b){Check(Same(a.code,b.code)&&Same(a.id,b.id)&&Same(a.xy,b.xy)&&Same(a.z,b.z)&&Same(a.vel,b.vel)&&Same(a.j,b.j)&&Same(a.theta,b.theta)&&Same(a.normal,b.normal)&&Same(a.slip,b.slip),"Init probe changed actual device input/J/theta state");}
  // All guard-read host members are replaced together; original addresses are never dereferenced here.
  struct HostView{
    Probe& f;unsigned* oldid;typecode* oldcode;tdouble3* oldpos;tfloat4* oldvel;double *oldj,*oldtheta;tfloat3 oldg,oldcsp;bool oldobserver,oldfeedback,olddynamic,oldwall,oldlaw;double oldck;bool active=true;
    std::vector<unsigned> id;std::vector<typecode> code;std::vector<tdouble3> pos;std::vector<tfloat4> vel;std::vector<double> j,theta;std::vector<tfloat3> normal;std::vector<byte> slip;
    HostView(Probe& p,const DeviceView& a):f(p),oldid(p.Idp),oldcode(p.Code),oldpos(p.AuxPos),oldvel(p.Velrhop),oldj(p.PoroJ),oldtheta(p.PoroTheta),oldg(p.Gravity),oldcsp(p.CSP.gravity),oldobserver(p.PorosityObserver),oldfeedback(p.PorosityFeedback),olddynamic(p.DynamicPorePressure),oldwall(p.DynamicPoreWall),oldlaw(p.DynamicPoreConductivity),oldck(p.DynamicPoreConductivityCk),id(a.id),code(a.code),pos(a.id.size()),vel(a.id.size()),j(a.j),theta(a.theta),normal(a.normal.size()),slip(a.slip){
      static_assert(sizeof(tfloat4)==sizeof(float4),"Host/device velocity layouts differ");for(unsigned i=0;i<id.size();i++){pos[i]=TDouble3(a.xy[i].x,a.xy[i].y,a.z[i]);vel[i]=TFloat4(a.vel[i].x,a.vel[i].y,a.vel[i].z,a.vel[i].w);}for(unsigned i=0;i<normal.size();i++)normal[i]=TFloat3(a.normal[i].x,a.normal[i].y,a.normal[i].z);
      f.Idp=id.data();f.Code=code.data();f.AuxPos=pos.data();f.Velrhop=vel.data();f.PoroJ=j.data();f.PoroTheta=theta.data();
    }
    void Gravity(tfloat3 g){f.Gravity=g;f.CSP.gravity=g;}
    void ObserverOnly(){f.PorosityObserver=true;f.PorosityFeedback=f.DynamicPorePressure=f.DynamicPoreWall=f.DynamicPoreConductivity=false;f.DynamicPoreConductivityCk=0.;}
    void Restore(){if(!active)return;f.Idp=oldid;f.Code=oldcode;f.AuxPos=oldpos;f.Velrhop=oldvel;f.PoroJ=oldj;f.PoroTheta=oldtheta;f.Gravity=oldg;f.CSP.gravity=oldcsp;f.PorosityObserver=oldobserver;f.PorosityFeedback=oldfeedback;f.DynamicPorePressure=olddynamic;f.DynamicPoreWall=oldwall;f.DynamicPoreConductivity=oldlaw;f.DynamicPoreConductivityCk=oldck;active=false;}
    void Restored()const{Check(!active&&f.Idp==oldid&&f.Code==oldcode&&f.AuxPos==oldpos&&f.Velrhop==oldvel&&f.PoroJ==oldj&&f.PoroTheta==oldtheta&&Bits(f.Gravity,oldg)&&Bits(f.CSP.gravity,oldcsp)&&f.PorosityObserver==oldobserver&&f.PorosityFeedback==oldfeedback&&f.DynamicPorePressure==olddynamic&&f.DynamicPoreWall==oldwall&&f.DynamicPoreConductivity==oldlaw&&Bits(f.DynamicPoreConductivityCk,oldck),"Original host pointers/gravity/private flags not restored");}
    ~HostView(){Restore();}
    HostView(const HostView&)=delete;HostView& operator=(const HostView&)=delete;
  };
  void Clock()const{Check(TimeStep==0&&Nstep==0&&!PoroJPreg&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg,"Init-only probe advanced time/step or created PRE histories");}
  void ObserverConditions()const{Check(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!DynamicPoreConductivity&&HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&!CaseNpb&&!CaseNmoving&&!InOut&&!Shifting&&!NoPenetration&&!Symmetry&&!StrainSoftening&&!UseDEM&&!Damping&&!RelaxZones&&!AccInput&&!SoilDamping&&SoilHourglassXi==0&&!HydroMechDrainage&&HydroMechInitMode==HMINIT_None&&HydroMechTopLoadMode==HMLOAD_None&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0&&!PeriY&&SoilCte.Porosity>0&&SoilCte.Porosity<1&&PoroJ&&PoroTheta&&PoroJg&&PoroThetag,"Observer-only non-gravity prerequisites not independently established");}
public:
  explicit Probe(bool wall){PorosityObserver=PorosityFeedback=DynamicPorePressure=true;DynamicPoreWall=wall;DynamicPoreConductivity=false;DynamicPoreConductivityCk=0.;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::string& selected){
    const bool wall=WallCase(selected);Runtime(cfg->CaseName+".xml",wall);AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();Clock();
    Check(PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall==wall&&!DynamicPoreConductivity&&!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0&&HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&Gravity==(wall?TFloat3(0,0,-8):TFloat3(-8,0,0))&&CSP.gravity==Gravity&&CaseNp==(wall?1280u:512u)&&CaseNpb==(wall?256u:0u)&&CaseNfluid==(wall?1024u:512u)&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOut(),"Actual fresh baseline initialization/scope differs");
    if(wall)Check(TBoundary==BC_MDBC&&UseNormals&&BoundNormalg&&PeriZ&&!PeriX&&!PeriY,"Actual opposing x-wall/tangential periodic seed required");else Check(PeriX&&PeriZ&&!PeriY&&!Npb,"Actual no-wall periodic seed required");
    const DeviceView baseline=Device(wall);unsigned normal=0,fixed=0;std::vector<unsigned> owner(CaseNp,unsigned(-1));for(unsigned p=0;p<Np;p++){Check(baseline.id[p]<CaseNp&&(CODE_IsNormal(baseline.code[p])||CODE_IsPeriodic(baseline.code[p])),"Unexpected actual native/image ID");if(CODE_IsNormal(baseline.code[p])){Check(owner[baseline.id[p]]==unsigned(-1),"Duplicate actual normal ID");owner[baseline.id[p]]=p;normal++;if(CODE_IsFixed(baseline.code[p]))fixed++;}Check(std::isfinite(baseline.j[p])&&baseline.j[p]==1&&baseline.theta[p]==0,"Fresh actual observer state must be J1/theta0");}Check(normal==CaseNp&&fixed==CaseNpb,"Actual seed normal/fixed ownership differs");
    const fs::path out(cfg->DirOut);Fresh(out/"probes.csv");Fresh(out/"host_view.csv");Fresh(out/"completion.json");std::ofstream probes(out/"probes.csv"),host(out/"host_view.csv");probes<<std::setprecision(17);host<<std::setprecision(17);
    probes<<"label,api,gx,gy,gz,expected_reject,observed_reject,exact_method_and_message,expected_message,observed_exception\n";host<<"slot,id,code,x,y,z,vx,vy,vz,legacy_rho,J,theta,boundary_prefix,raw_normal_x,raw_normal_y,raw_normal_z,actual_effective_slip\n";for(unsigned p=0;p<Np;p++){const bool bound=wall&&p<Npb;const auto n=bound?baseline.normal[p]:make_float3(0,0,0);const int slip=bound?int(baseline.slip.empty()?SlipMode:TpSlipMode(baseline.slip[p])):-1;host<<p<<','<<baseline.id[p]<<','<<baseline.code[p]<<','<<baseline.xy[p].x<<','<<baseline.xy[p].y<<','<<baseline.z[p]<<','<<baseline.vel[p].x<<','<<baseline.vel[p].y<<','<<baseline.vel[p].z<<','<<baseline.vel[p].w<<','<<baseline.j[p]<<','<<baseline.theta[p]<<','<<(bound?1:0)<<','<<n.x<<','<<n.y<<','<<n.z<<','<<slip<<'\n';}
    unsigned calls=0,rejections=0,passes=0;double tinyOffaxis=0,tinyDot=0;unsigned tinySlot=unsigned(-1),tinyID=unsigned(-1);
    {
      HostView view(*this,baseline);
      auto probe=[&](const char* label,bool wallapi,const char* expected){const char* method=wallapi?"InitDynamicPoreWallGpu":"InitPorosityObserverGpu";bool rejected=false,matched=false;std::string text;try{if(wallapi)InitDynamicPoreWallGpu(view.normal.data(),view.slip.empty()?nullptr:view.slip.data());else InitPorosityObserverGpu();}catch(const JException& e){rejected=true;text=e.ToStr();matched=expected[0]&&text.find(expected)!=std::string::npos&&text.find(std::string("::")+method+")")!=std::string::npos;}calls++;probes<<label<<','<<method<<','<<Gravity.x<<','<<Gravity.y<<','<<Gravity.z<<','<<(expected[0]?1:0)<<','<<(rejected?1:0)<<','<<(matched?1:0)<<','<<Q(expected)<<','<<Q(text)<<'\n';probes.flush();Check(bool(probes),"Probe CSV write failed");Check(expected[0]?(rejected&&matched):!rejected,"Expected actual Init method/message was not observed");if(rejected)rejections++;else passes++;Clock();};
      view.Gravity(TFloat3(0,0,0));
      if(wall){
        probe("actual_normal_slip_g0_baseline",true,"");
        if(selected=="wall_tangent"){view.Gravity(TFloat3(0,0,-8));probe("strict_tangential",true,"");}
        else if(selected=="wall_normal"){view.Gravity(TFloat3(-8,0,0));probe("normal_gravity",true,WallTangent);}
        else if(selected=="wall_gy"){view.Gravity(TFloat3(0,1,-8));probe("nonzero_2D_gy",true,WallGeneral);}
        else if(selected=="wall_nan"){view.Gravity(TFloat3(0,0,std::numeric_limits<float>::quiet_NaN()));probe("nonfinite_gravity",true,WallGeneral);}
        else if(selected=="wall_tiny"){
          for(unsigned p=0;p<Npb;p++)if(CODE_IsNormal(view.code[p])&&CODE_IsFixed(view.code[p])&&view.normal[p].x!=0){tinySlot=p;tinyID=view.id[p];break;}Check(tinySlot!=unsigned(-1),"No actual normal fixed x-wall vector available");const auto raw=view.normal[tinySlot];Check(raw.y==0&&raw.z==0,"Original actual selected vector is not strict x-axis");view.normal[tinySlot].z=std::ldexp(raw.x,-22);const auto changed=view.normal[tinySlot];const double len=std::sqrt(double(changed.x)*changed.x+double(changed.z)*changed.z);tinyOffaxis=fabs(double(changed.z))/len;tinyDot=-8.*double(changed.z);Check(tinyOffaxis>0&&tinyOffaxis<=8.*FLT_EPSILON&&tinyDot!=0,"Tiny-vector negative is not inside old angle bound with nonzero raw dot");probe("tiny_vector_g0_geometry_control",true,"");view.Gravity(TFloat3(0,0,-8));probe("tiny_vector_exact_raw_dot",true,WallTangent);
        }
      }else{
        view.ObserverOnly();ObserverConditions();probe("pure_observer_g0",false,"");if(selected=="observer_gravity"){view.Gravity(TFloat3(-8,0,0));ObserverConditions();probe("pure_observer_nonzero_gravity",false,ObserverGravity);}
      }
      view.Restore();view.Restored();
    }
    Unchanged(baseline,Device(wall));Clock();const bool negative=selected=="wall_normal"||selected=="wall_gy"||selected=="wall_nan"||selected=="wall_tiny"||selected=="observer_gravity";Check(rejections==(negative?1u:0u)&&passes>0,"Incomplete selected positive/negative Init proof");for(auto* stream:{&probes,&host}){stream->flush();Check(bool(*stream),"Init probe CSV write failed");}
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gpu_gravity_init_probe_r1\",\"case\":\""<<selected<<"\",\"kind\":\""<<(wall?"wall":"observer")<<"\",\"fresh_objects\":1,\"actual_full_initializations\":1,\"actual_Init_guard_recheck_calls\":"<<calls<<",\"positive_rechecks\":"<<passes<<",\"expected_exact_method_message_rejections\":"<<rejections<<",\"native_count\":"<<CaseNp<<",\"fixed_count\":"<<CaseNpb<<",\"actual_slots\":"<<Np<<",\"boundary_slots\":"<<Npb<<",\"per_particle_slip_downloaded\":"<<(baseline.slip.empty()?"false":"true")<<",\"global_slip_fallback_is_actual\":"<<(wall&&baseline.slip.empty()?"true":"false")<<",\"all_guard_host_pointers_alive_and_restored\":true,\"Gravity_and_CSP_gravity_restored\":true,\"private_flags_restored\":true,\"device_input_J_theta_bits_unchanged\":true,\"tiny_offaxis_normalized_component\":"<<tinyOffaxis<<",\"tiny_raw_normal_dot_gravity\":"<<tinyDot<<",\"tiny_actual_fixed_slot\":"<<(tinySlot==unsigned(-1)?-1:int(tinySlot))<<",\"tiny_actual_fixed_ID\":"<<(tinyID==unsigned(-1)?-1:int(tinyID))<<",\"observer_only_compound_non_gravity_conditions_checked\":"<<(!wall?"true":"false")<<",\"Init_rechecks_may_reset_J_not_trajectory_controls\":true,\"Run_or_ComputeStep_called\":false,\"actual_force_calls\":0,\"physical_steps_advanced\":0,\"actual_time_s\":0,\"Nstep\":0,\"PART_read_or_restart\":false,\"public_gravity_accepted\":false,\"wall_trajectory_accepted\":false,\"physical_acceptance\":false,\"source_SHA_checked_by_component\":false}\n";done.flush();Check(bool(done),"Init probe completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Check(argc>=7&&std::string(argv[1])=="--probe"&&std::string(argv[3])=="--","Use --probe CASE -- ordinary GPU seed arguments");const std::string selected=argv[2];gravityinit::Case(selected);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Check(!cfg.Cpu&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut)&&!cfg.PartBegin&&!cfg.NstepsBreak&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"Fresh one-case Init probe only; retained outputs/restarts protected");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");gravityinit::Probe probe(gravityinit::WallCase(selected));probe.Execute(&cfg,AppInfo.LogPtr(),selected);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU Init probe rejected; retain original output\n";return 2;}}
