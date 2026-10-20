import ctypes
import math
import pathlib
import sys

def sma(values, window, native=False):
    if type(window) is not int or window <= 0 or any(not math.isfinite(v) for v in values):
        raise ValueError('invalid SMA input')
    if native:
        ext = '.dylib' if sys.platform == 'darwin' else '.so'
        lib = ctypes.CDLL(str(pathlib.Path(__file__).resolve().parents[1]/'build'/('libindicators'+ext)))
        array = ctypes.c_double * len(values)
        out = array()
        lib.sma.argtypes = [ctypes.POINTER(ctypes.c_double),ctypes.c_size_t,ctypes.c_size_t,ctypes.POINTER(ctypes.c_double)]
        lib.sma.restype = ctypes.c_int
        if lib.sma(array(*values),len(values),window,out): raise ValueError('C++ SMA failed')
        return list(out)
    return [math.nan if i+1 < window else sum(values[i-window+1:i+1])/window for i in range(len(values))]

def signals(bars, fast, slow, native=False):
    if not 0 < fast < slow: raise ValueError('require 0 < fast < slow')
    values = [b.close for b in bars]
    f,s = sma(values,fast,native),sma(values,slow,native)
    return [False if math.isnan(s[i]) else f[i] > s[i] for i in range(len(bars))]
