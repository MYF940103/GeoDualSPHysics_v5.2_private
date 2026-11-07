// Failed-source saved-state inspector. Never labels last saved time as failure time.
#include "JPartDataBi4.h"
#include "JBinaryData.h"
#include "JAppInfo.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("PreloadRejectSavedState","r1","07-11-2026");
namespace fs=std::filesystem;
static void Need(bool yes,const char* text){if(!yes)throw std::runtime_error(text);}
int main(int argc,char** argv){try{
  Need(argc==4&&std::string(argv[1])=="--inspect","Use --inspect REJECTED_DATA FRESHOUT");
  const fs::path dir=argv[2],out=argv[3],tests=fs::path(__FILE__).parent_path().parent_path();
  Need(tests.is_absolute()&&fs::is_directory(dir)&&fs::equivalent(dir,tests/"outputs/upl_preload_handoff_reject_CPU_r1/data"),"Only the retained failed-source DATA is admitted");
  Need(!fs::exists(out),"Retained inspector output protected");std::vector<fs::path> paths;
  for(const auto& item:fs::directory_iterator(dir))if(item.is_regular_file()&&item.path().extension()==".bi4"&&item.path().filename().string().find("Part_")==0)paths.push_back(item.path());
  std::sort(paths.begin(),paths.end());Need(paths.size()==1&&paths[0].filename()=="Part_0000.bi4","Unexpected saved rejected-source PART membership");
  JPartDataBi4 file;file.LoadFilePart(dir.string(),0,0,1);constexpr unsigned N=7060;
  Need(file.GetNpiece()==1&&file.GetPiece()==0&&file.Get_Npok()==N&&file.Get_Nout()==0&&file.Get_CaseNp()==N&&file.Get_CaseNfixed()==2060&&file.Get_CaseNfluid()==5000,"Native initial registry/piece/exclusion mismatch");
  Need(file.Get_Step()==0&&file.Get_TimeStep()==0.,"Only original saved Step0/Time0 is admitted; never infer the failure time");
  using D=JBinaryDataDef::TpData;const D U=JBinaryDataDef::DatUint,F=JBinaryDataDef::DatFloat,D8=JBinaryDataDef::DatDouble,F3=JBinaryDataDef::DatFloat3,D3=JBinaryDataDef::DatDouble3;
  const char* names[]={"Idp","Posd","Vel","Rhop","Sigma_kk","Sigma_ij","SigmaState_kk","SigmaState_ij","Kplastic","FSType","FSNormal","HydroMechLoadAce","PorePress","PorePress0","ExcessPorePress","PoroVolumeRatio","PoroPorosity","PoroThetaLastStage","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"};
  const D types[]={U,D3,F3,F,F3,F3,D3,D3,F,U,F3,F3,F,F,F,D8,D8,D8,D8,D8,D8,F};
  Need(file.ArraysCount()==22&&!file.ArrayExists("Pos"),"Expected22 typed original double-position arrays");
  for(unsigned i=0;i<22;i++){const auto* a=file.GetArray(names[i],types[i]);Need((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==N,"Typed native array count mismatch");}
  const auto* meta=file.GetPart();const char* cert[]={"GravityPreloadHandoffSchema","GravityPreloadElasticSource","GravityPreloadHandoffContract","GravityPreloadSourceCohesion"};
  for(const char* key:cert)Need(!meta->ExistsValue(key),"Rejected source wrote a handoff certification key");
  std::vector<unsigned> ids(N);std::vector<float> kappa(N);std::vector<tdouble3> pos(N);Need(file.Get_Idp(N,ids.data())==N&&file.Get_Posd(N,pos.data())==N&&file.GetArray("Kplastic",F)->GetDataCopy(N,kappa.data())==N,"Incomplete original IDs/positions/kappa");
  std::vector<bool> seen(N,false);for(unsigned q=0;q<N;q++){Need(ids[q]<N&&!seen[ids[q]],"Missing or duplicate original ID");seen[ids[q]]=true;Need(kappa[q]==0.f&&std::isfinite(pos[q].x)&&std::isfinite(pos[q].y)&&std::isfinite(pos[q].z)&&pos[q].y==0.,"Saved initial kappa or finite 2D position mismatch");}
  Need(fs::create_directory(out),"Fresh inspector output could not be created");std::ofstream done(out/"completion.json");
  done<<"{\"stage\":\"upl_preload_handoff_reject_native_r1\",\"passed\":true,\"inspected_native_frames\":1,\"last_saved_part\":0,\"last_saved_step\":0,\"last_saved_time_s\":0,\"last_saved_kappa_max\":0,\"original_IDs\":7060,\"typed_arrays\":22,\"typed_array_count_checks\":22,\"original_ID_and_kappa_checks\":7060,\"all_four_handoff_certification_keys_absent\":true,\"failure_time_known\":false,\"failure_time_s\":null,\"last_saved_state_is_not_the_failure_state\":true,\"solver_exit_or_predictor_mask_verified_by_reader\":false,\"all22_array_values_fully_decoded\":false,\"native_files_modified\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Inspector completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Rejected-source saved-state inspector failed\n";return 2;}}
