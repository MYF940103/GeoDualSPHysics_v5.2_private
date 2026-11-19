"""Synthetic CUDA interface fixture for pressure history and bounds at the first open step."""
import argparse
import ctypes as ct
import json
from pathlib import Path
import numpy as np


def main(library):
    receipt=library.parent/"abi_probe.json"
    if receipt.exists():raise FileExistsError(receipt)
    dll=ct.CDLL(str(library.resolve()))
    ptr=ct.c_void_p;integer=ct.c_int;real=ct.c_double
    types=dict(init=[integer,real,real,real,real],setCsr=[integer,integer,ptr,ptr,ptr],
        setGeometry=[ptr]*6,start=[],advance=[integer],readState=[ptr]*5,readPrevious=[ptr],
        restore=[integer]+[ptr]*6,currentStep=[],release=[])
    for name,args in types.items():
        getattr(dll,name).argtypes=args;getattr(dll,name).restype=integer
    dll.errorText.argtypes=[];dll.errorText.restype=ct.c_char_p
    def call(fn,*args):
        rc=getattr(dll,fn)(*[a.ctypes.data if isinstance(a,np.ndarray) else a for a in args])
        if rc:raise RuntimeError(dll.errorText().decode())
    n=37173;dt=2.**-19
    def read():
        z=[np.empty(n),np.empty(n),np.empty((n,3)),np.empty((n,3)),np.empty((n,6)),np.empty(n)]
        call("readState",z[0],*z[2:]);call("readPrevious",z[1]);return z
    call("init",n,dt,1.,1.,0.)
    try:
        row=np.arange(n+1,dtype=np.int32);col=row[:-1].copy()
        zero=np.zeros((n,3));one=np.ones(n);fs=np.zeros(n,dtype="u1");fs[1]=1
        for key in range(5):
            # Interior slot 0 reads exterior slot 1 pressure as its only artificial force.
            tmp=col.copy();values=np.zeros_like(zero) if key<2 else np.ones(n)
            if key==1:tmp[0]=1;values[0,0]=1.
            if key==4:values.fill(0.)
            call("setCsr",key,n,row,tmp,values)
        call("setGeometry",zero,one,zero,one,zero,fs);call("start")
        assert dll.currentStep()==0
        p=np.full(n,5.);p[1]=1000.
        prev=p.copy();prev[1]=888.
        saved=[p,prev,zero.copy(),zero.copy(),np.zeros((n,6)),one.copy()]
        call("restore",4096,*saved)
        assert dll.currentStep()==4096
        restored=read()
        for a,b in zip(saved,restored):assert a.tobytes()==b.tobytes()
        call("advance",1);post=read()
        assert dll.currentStep()==4097 and post[0][1]==post[1][1]==0.
        assert np.all(post[2]==0.) and np.all(post[3]==0.),"Pre-open p entered an open-stage force"
        call("advance",1);second=read();call("restore",4097,*post);call("advance",1)
        for a,b in zip(second,read()):assert a.tobytes()==b.tobytes()
        # Before opening the same surface pressure really drives slot 0; its
        # intentionally out-of-range displacement must report the actual rejected update.
        saved[0][1]=saved[1][1]=1e15
        call("restore",4095,*saved)
        assert dll.advance(1)==1
        fault=dll.errorText().decode()
        assert "update 4096, phase 2" in fault and "native ID 8" in fault and dll.currentStep()==-1,fault
        call("restore",4097,*post);assert dll.currentStep()==4097
        receipt.write_text(json.dumps(dict(initial_restore="all six arrays bit-identical",
            first_open_step=4097,surface_current_and_history_zero=True,spurious_preopen_force=False,
            replay_step=4098,restored_next_update_all_six_identical=True,rejected=fault,
            synthetic=True,physical_case=False),indent=2),encoding="utf8")
        print(receipt)
    finally:call("release")


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("library",type=Path)
    main(ap.parse_args().library)
