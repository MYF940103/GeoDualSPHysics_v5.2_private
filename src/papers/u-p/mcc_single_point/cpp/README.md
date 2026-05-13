# M3a C++ MCC Helper

This directory contains the standalone C++ parity helper for the M2 Python
Modified Cam Clay material-point prototype.

It is not linked into GeoDualSPHysics and does not modify the production solver.

Build:

```bat
build_mcc_cpp.bat
```

Run:

```bat
build\mcc_single_point_driver.exe ..\output
```

The driver writes C++ CSV outputs named `m3a_cpp_*.csv`. The parent
`compare_mcc_python_cpp.py` script compares these files against the Python M2
outputs.
