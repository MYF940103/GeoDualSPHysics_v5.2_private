// Compile the untouched frozen reference separately, like the candidate class.
// This avoids giving only the reference cross-function inlining in the fixture.
#include "JSphHourglassCpu.h"
#undef _JSphHourglassCpu_
#define JSphHourglassCpu JSphHourglassCpuReference
#include "../outputs/hg_release_base/source/JSphHourglassCpu.cpp"
#undef JSphHourglassCpu
