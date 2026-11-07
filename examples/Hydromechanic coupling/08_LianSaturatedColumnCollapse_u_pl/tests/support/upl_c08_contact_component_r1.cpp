// Standalone host component of the shared CPU/CUDA scalar projection; no solver/AppInfo.
#include "FunFixedPlaneContact.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
static void Need(bool b,const char* text){if(!b)throw std::runtime_error(text);}
template<class T>static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
struct Case{const char* name;double pos,plane,move;float velocity;bool limited,roundoffWitness;};
int wmain(int argc,wchar_t** argv){try{
  Need(argc==3&&std::wstring(argv[1])==L"--out","Use --out FRESHOUT");const fs::path out=argv[2];Need(!fs::exists(out),"Existing component output protected");Need(fs::create_directory(out),"Cannot create fresh output");
  const double fp=double(float(.1f)),fn=double(std::nextafter(.1f,1.f));
  const std::vector<Case> cases={
    {"crossing_incoming",.125,0.,-.25,-2.f,true,false},
    {"crossing_outgoing",.125,0.,-.25,2.f,true,false},
    {"at_plane_incoming",0.,0.,0.,-2.f,true,false},
    {"at_plane_outgoing",0.,0.,0.,2.f,true,false},
    {"at_plane_negative_zero",0.,0.,-0.,-0.f,true,false},
    {"already_below_plane",-.125,0.,.0625,-1.f,true,false},
    {"noncrossing_incoming",.5,0.,-.125,-2.f,false,false},
    {"noncrossing_outgoing",.5,0.,.125,2.f,false,false},
    {"noncrossing_zero_move",.5,0.,-0.,-0.f,false,false},
    {"positive_binary_plane",.5,.25,-.5,-1.f,true,false},
    {"negative_binary_plane",0.,-.25,-.5,-1.f,true,false},
    {"float_endpoint_exact",fn,fp,fp-fn,-.5f,true,false},
    {"float_position_zero_plane",double(float(.02f)),0.,-2.*double(float(.02f)),-.5f,true,false},
    {"float_large_zero_plane",double(std::numeric_limits<float>::max()),0.,-double(std::numeric_limits<float>::max()),-std::numeric_limits<float>::max(),true,false},
    {"float_small_velocity",.125,0.,-.25,-std::numeric_limits<float>::min(),true,false},
    {"fractional_positive_cancellation",1.,.1,-2.,-1.f,true,true},
    {"fractional_negative_cancellation",1.,-.1,-2.,-1.f,true,true}
  };
  std::ofstream rows(out/"points.csv"),toy(out/"half_stage_toy.csv");rows<<std::setprecision(17);toy<<std::setprecision(17);
  rows<<"case,pos_m,plane_m,trial_move_m,trial_velocity_m_s,limited,new_move_m,new_velocity_m_s,endpoint_m,endpoint_minus_plane_m,endpoint_ge_plane,roundoff_witness,endpoint_budget_m,normal_energy_before,normal_energy_after,tangent_bits_unchanged,unconstrained_bits_unchanged\n";
  unsigned n=0,witnesses=0,strict=0,roundedBelow=0;double maxGap=0.,maxBudget=0.;
  for(const auto &c:cases){
    // Tangents are separate axes; the scalar call has no access to them.
    const double tangentMove[2]={.03125,-.0625};const float tangentVel[2]={1.25f,-2.5f};double moves[3]={tangentMove[0],c.move,tangentMove[1]};float velocities[3]={tangentVel[0],c.velocity,tangentVel[1]};
    const bool limited=fcontact::ProjectLowerPlane(c.pos,c.plane,moves[1],velocities[1]);const double endpoint=c.pos+moves[1],gap=c.plane-endpoint;const double before=.5*double(c.velocity)*double(c.velocity),after=.5*double(velocities[1])*double(velocities[1]);
    Need(limited==c.limited,"Contact branch classification differs");Need(after<=before,"Normal kinetic energy increased");const bool tangents=Bits(moves[0],tangentMove[0])&&Bits(moves[2],tangentMove[1])&&Bits(velocities[0],tangentVel[0])&&Bits(velocities[2],tangentVel[1]);Need(tangents,"Independent tangent axis changed");
    const bool unchanged=Bits(moves[1],c.move)&&Bits(velocities[1],c.velocity);if(!limited)Need(unchanged,"Unconstrained state was changed");if(limited&&c.velocity<0)Need(velocities[1]==0.f,"Incoming normal velocity not projected to zero");if(c.velocity>=0)Need(Bits(velocities[1],c.velocity),"Outgoing/zero normal velocity changed");
    // A single subtraction and endpoint addition each round. Only the declared fractional-plane
    // cancellation witnesses use this absolute IEEE budget; zero/binary/float endpoints stay strict.
    const double budget=c.roundoffWitness?2.*std::numeric_limits<double>::epsilon()*(std::abs(c.pos)+std::abs(c.plane)+std::abs(moves[1])):0.;
    if(c.roundoffWitness){Need(c.plane!=0.&&gap<=budget,"Fractional-plane error exceeds the stated arithmetic budget");witnesses++;maxGap=(std::max)(maxGap,gap);maxBudget=(std::max)(maxBudget,budget);roundedBelow+=endpoint<c.plane;}
    else{Need(endpoint>=c.plane,"Endpoint crossed the lower plane beyond strict geometry");strict++;}
    if(c.plane==0.)Need(endpoint>=0.,"Zero plane geometry must be strict");
    rows<<c.name<<','<<c.pos<<','<<c.plane<<','<<c.move<<','<<c.velocity<<','<<limited<<','<<moves[1]<<','<<velocities[1]<<','<<endpoint<<','<<endpoint-c.plane<<','<<(endpoint>=c.plane)<<','<<c.roundoffWitness<<','<<budget<<','<<before<<','<<after<<','<<tangents<<','<<unchanged<<'\n';n++;
  }
  // The actual flat-wall half-stage shift is -2*v_half. Applying it to v_n
  // can reverse either an outward current corrector velocity or an inward one.
  struct Toy{const char* name;float original,halfTrial,expectedFree,expectedLegacy;};
  const Toy toys[]={{"outgoing_flipped_inward",-1.f,-.25f,.5f,-.5f},{"incoming_flipped_outward",1.f,-.25f,-1.5f,1.5f}};
  toy<<"case,original_velocity,half_trial_velocity,corrector_trial_velocity,half_shift,legacy_corrector_velocity,legacy_move,uncorrected_move,projected_velocity,projected_move,projected_endpoint,dt,normal_energy_before,normal_energy_after,limited\n";
  for(const auto &t:toys){
    const float correctorTrial=2.f*t.halfTrial-t.original,halfShift=-2.f*t.halfTrial,legacyCorrector=t.original+halfShift;const double dt=.01,pos=.001,plane=0.;
    double move=(double(t.original)+correctorTrial)*(.5*dt);const double oldMove=double(legacyCorrector)*dt,trialMove=move;float velocity=correctorTrial;const bool limited=fcontact::ProjectLowerPlane(pos,plane,move,velocity);const double before=.5*double(correctorTrial)*correctorTrial,after=.5*double(velocity)*velocity;
    Need(correctorTrial==t.expectedFree&&legacyCorrector==t.expectedLegacy&&correctorTrial*legacyCorrector<0.f,"Factor2 manufactured half-stage reversal witness not reached");Need(limited&&move==plane-pos&&pos+move>=plane,"Current-velocity projection failed to limit the crossing displacement");Need(after<=before,"Toy normal energy increased");
    if(correctorTrial>0.f)Need(Bits(velocity,correctorTrial),"Outward current velocity was flipped or changed");else Need(velocity==0.f,"Inward current velocity was not projected to zero");
    toy<<t.name<<','<<t.original<<','<<t.halfTrial<<','<<correctorTrial<<','<<halfShift<<','<<legacyCorrector<<','<<oldMove<<','<<trialMove<<','<<velocity<<','<<move<<','<<pos+move<<','<<dt<<','<<before<<','<<after<<','<<limited<<'\n';
  }
  for(auto* f:{&rows,&toy}){f->flush();Need(bool(*f),"CSV write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_contact_component_r1\",\"passed\":true,\"host_points\":"<<n<<",\"strict_endpoint_points\":"<<strict<<",\"fractional_roundoff_witnesses\":"<<witnesses<<",\"actual_fractional_endpoints_below_plane\":"<<roundedBelow<<",\"max_fractional_endpoint_gap_m\":"<<maxGap<<",\"max_declared_endpoint_budget_m\":"<<maxBudget<<",\"fractional_endpoint_budget\":\"2*DBL_EPSILON*(abs(pos)+abs(plane)+abs(move))\",\"normal_kinetic_energy_nonincrease\":true,\"tangent_axes_bit_unchanged\":true,\"unconstrained_bits_unchanged\":true,\"half_stage_sign_flip_toys\":2,\"universal_exact_double_endpoint_claimed\":false,\"CPU_CUDA_shared_source\":true,\"GPU_execution_proven\":false,\"reaction_J_p_closure_claimed\":false,\"solver_invocations\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
