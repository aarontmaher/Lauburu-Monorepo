import ctypes
import os

lib_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_c_bridge.so"
c_lib = None
if os.path.exists(lib_path):
    c_lib = ctypes.CDLL(lib_path)
    c_lib.predict_micro_mlp.argtypes = [ctypes.POINTER(ctypes.c_float)]
    c_lib.predict_micro_mlp.restype = ctypes.c_float

def predict(input_array):
    if c_lib is None:
        return 0.0
    if len(input_array) != 32:
        input_array = (input_array + [0.0]*32)[:32]
    FloatArray = ctypes.c_float * 32
    c_array = FloatArray(*input_array)
    return c_lib.predict_micro_mlp(c_array)
