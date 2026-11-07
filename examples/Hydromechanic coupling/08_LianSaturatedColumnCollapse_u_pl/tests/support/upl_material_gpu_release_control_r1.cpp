// Keep the frozen reader and its unused main byte-for-byte. Its internal main/undef
// macros make an outside #define main unsuitable. Select the normal MSVC wide CRT
// startup for this test-only wmain; every numeric check remains in the old Read.
#include "upl_material_release_native_r1.cpp"
int wmain(int argc,wchar_t** argv){try{
  Need(argc==5&&std::wstring(argv[1])==L"--data"&&std::wstring(argv[3])==L"--out","Use --data GPU_RELEASE_DATA --out FRESHOUT");
  c08releasegravity::Read("source","GPU_release",fs::path(argv[2]),"-",fs::path(argv[4]));return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){return 2;}}
