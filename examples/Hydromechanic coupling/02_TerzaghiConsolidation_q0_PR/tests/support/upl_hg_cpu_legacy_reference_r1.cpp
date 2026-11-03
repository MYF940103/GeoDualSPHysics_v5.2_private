// Compile the untouched frozen reference as a separate translation unit.
// The current and reference classes both use the actual linked JObject.
#include "JSphHourglassCpu.h"
#undef _JSphHourglassCpu_
#define JSphHourglassCpu JSphHourglassCpuReference
#include "../outputs/hg_release_base/source/JSphHourglassCpu.cpp"
#undef JSphHourglassCpu
