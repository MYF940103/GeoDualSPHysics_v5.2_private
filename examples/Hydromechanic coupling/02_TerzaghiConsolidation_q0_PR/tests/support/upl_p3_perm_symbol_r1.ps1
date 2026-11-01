# Read an existing PDB at the Windows Event1000 relative fault address; no solver.
$ErrorActionPreference='Stop'
$tests=Split-Path -Parent $PSScriptRoot
$folder=Join-Path $tests 'outputs\upl_p2_DebugCPU_p3_perm_r1'
$program=Join-Path $folder 'upl_p2_harness_r1.exe'
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class LocalFaultSymbol {
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 [DllImport("dbghelp.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern bool SymInitializeW(IntPtr p,string path,bool invade);
 [DllImport("dbghelp.dll")] static extern uint SymSetOptions(uint options);
 [DllImport("dbghelp.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern ulong SymLoadModuleExW(IntPtr p,IntPtr f,string image,string module,ulong address,uint size,IntPtr data,uint flags);
 [DllImport("dbghelp.dll",SetLastError=true)] static extern bool SymFromAddr(IntPtr p,ulong address,out ulong displacement,IntPtr symbol);
 [StructLayout(LayoutKind.Sequential)] struct Line {public uint Size;public IntPtr Key;public uint Number;public IntPtr File;public ulong Address;}
 [DllImport("dbghelp.dll",SetLastError=true)] static extern bool SymGetLineFromAddr64(IntPtr p,ulong address,out uint displacement,ref Line line);
 [DllImport("dbghelp.dll")] static extern bool SymCleanup(IntPtr p);
 public static string[] Read(string exe,string dir,ulong offset) {
  IntPtr p=GetCurrentProcess(); SymSetOptions(0x2|0x4|0x10|0x200);
  if(!SymInitializeW(p,dir,false))throw new Win32Exception();
  IntPtr info=IntPtr.Zero;
  try {
   ulong b=SymLoadModuleExW(p,IntPtr.Zero,exe,null,0x140000000,0,IntPtr.Zero,0);
   if(b==0)throw new Win32Exception();
   info=Marshal.AllocHGlobal(88+1024);
   for(int i=0;i<88+1024;i++)Marshal.WriteByte(info,i,0);
   Marshal.WriteInt32(info,88); Marshal.WriteInt32(info,80,1024);
   ulong delta; if(!SymFromAddr(p,b+offset,out delta,info))throw new Win32Exception();
   string name=Marshal.PtrToStringAnsi(IntPtr.Add(info,84));
   var line=new Line();line.Size=(uint)Marshal.SizeOf(typeof(Line));uint ld;
   bool ok=SymGetLineFromAddr64(p,b+offset,out ld,ref line);
   return new[]{name,delta.ToString(),ok?Marshal.PtrToStringAnsi(line.File):"<no source line>",ok?line.Number.ToString():"0"};
  } finally {if(info!=IntPtr.Zero)Marshal.FreeHGlobal(info);SymCleanup(p);}
 }
}
'@
$r=[LocalFaultSymbol]::Read($program,$folder,0xF139B)
[pscustomobject]@{program=$program;event_fault_offset='0xF139B';symbol=$r[0];symbol_displacement=$r[1];source=$r[2];line=$r[3];solver_started=$false}
