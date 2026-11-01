// Entry-point batching only: every typed-array/poro read is the immutable retained function.
#define main RetainedObserverNativeMain
#include "upl_gpu_observer_native_r1.cpp"
#undef main

int main(int argc,char** argv){
  if(argc<2||std::string(argv[1])!="--batch-compare")return RetainedObserverNativeMain(argc,argv);
  try{
    Check(argc==7,"Use --batch-compare OLD_DATA NEW_DATA SAMPLES OBSERVER NEW_DIRECTORY");
    const unsigned samples=Uint(argv[4]);Check(samples==3||samples==17||samples==257,"Only declared legacy windows admitted");
    const std::string flag=argv[5];Check(flag=="0"||flag=="1","Observer must be0or1");const bool observer=flag=="1";
    const fs::path output=argv[6];Fresh(output);fs::create_directory(output);
    for(unsigned part=0;part<samples;part++){
      const std::string text=std::to_string(part),tag=std::string(4-text.size(),'0')+text;
      Compare(argv[2],argv[3],part,512,output/("typed_"+tag+".json"));
      if(observer){
        ReadPoro(argv[2],part,512,0,.25,output/("poro_old_"+tag+".csv"),output/("poro_old_"+tag+".json"));
        ReadPoro(argv[3],part,512,0,.25,output/("poro_new_"+tag+".csv"),output/("poro_new_"+tag+".json"));
      }
    }
    std::ofstream done(output/"batch_complete.json");done
      <<"{\"passed\":true,\"samples\":"<<samples<<",\"native_count\":512,\"observer\":"<<(observer?"true":"false")
      <<",\"retained_Compare_calls\":"<<samples<<",\"retained_ReadPoro_calls\":"<<(observer?2*samples:0)
      <<",\"retained_functions_unchanged\":true,\"physical_program_executed\":false,\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Batch completion write failed");return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(const std::string& e){std::cerr<<e<<'\n';return 1;}
  catch(const char* e){std::cerr<<e<<'\n';return 1;}
  catch(...){std::cerr<<"Legacy offline batch failed; retain all evidence\n";return 2;}
}
