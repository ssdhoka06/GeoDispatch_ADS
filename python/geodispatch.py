import ctypes
import ctypes.util
import json
import math
import sys
from pathlib import Path

HERE      = Path(__file__).resolve().parent
REPO      = HERE.parent
DATA_FILE = REPO / "data" / "pune_facilities.json"

# Find and load the compiled shared library
for ext in ("so", "dll", "dylib"):
    lib_path = HERE / f"geodispatch.{ext}"
    if lib_path.exists():
        break
else:
    raise FileNotFoundError("geodispatch shared library not found. Run: make")

lib = ctypes.CDLL(str(lib_path))

# Need C's free() to release arrays malloc'd inside kd_knn
if sys.platform == "win32":
    libc = ctypes.CDLL("msvcrt")
else:
    libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc.free.argtypes = [ctypes.c_void_p]
libc.free.restype  = None

# Mirrors point_t in kd.h
class PointT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("id", ctypes.c_int)]

lib.kd_build.argtypes     = [ctypes.POINTER(PointT), ctypes.c_int]
lib.kd_build.restype      = ctypes.c_void_p
lib.kd_free.argtypes      = [ctypes.c_void_p]
lib.kd_free.restype       = None
lib.kd_nearest.argtypes   = [ctypes.c_void_p, PointT]
lib.kd_nearest.restype    = PointT
lib.kd_knn.argtypes       = [ctypes.c_void_p, PointT, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
lib.kd_knn.restype        = ctypes.POINTER(PointT)
lib.kd_delete.argtypes    = [ctypes.c_void_p, ctypes.c_int]
lib.kd_delete.restype     = None
lib.kd_insert.argtypes    = [ctypes.POINTER(ctypes.c_void_p), PointT]
lib.kd_insert.restype     = None
lib.kd_rebalance.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
lib.kd_rebalance.restype  = None
lib.kd_dead_ratio.argtypes = [ctypes.c_void_p]
lib.kd_dead_ratio.restype  = ctypes.c_double

# Equirectangular projection — same constants as data_loader.py
LAT0     = 18.5204
LON0     = 73.8567
R        = 6_371_000.0
COS_LAT0 = math.cos(math.radians(LAT0))

def _to_xy(lat, lon):
    return math.radians(lon - LON0) * COS_LAT0 * R, math.radians(lat - LAT0) * R

# Tree root and facility metadata loaded at import time
_root = ctypes.c_void_p(None)
_meta = {}  # id -> {name, type, lat, lon}

def _load():
    global _root
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"{DATA_FILE} not found. Run: python python/data_loader.py")

    facilities = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    n = len(facilities)
    arr = (PointT * n)()

    for i, f in enumerate(facilities):
        arr[i] = PointT(f["x"], f["y"], f["id"])
        _meta[f["id"]] = {"name": f.get("name", ""), "type": f.get("type", ""),
                          "lat": f["lat"], "lon": f["lon"]}

    _root = ctypes.c_void_p(lib.kd_build(arr, ctypes.c_int(n)))
    print(f"[geodispatch] {n} facilities loaded.", file=sys.stderr)

_load()

def _enrich(pt):
    info = _meta.get(pt.id, {})
    return {"id": pt.id, "lat": info.get("lat"), "lon": info.get("lon"),
            "name": info.get("name", ""), "type": info.get("type", "")}

def kd_nearest(lat, lon):
    x, y = _to_xy(lat, lon)
    return _enrich(lib.kd_nearest(_root, PointT(x, y, -1)))

def kd_knn(lat, lon, k):
    x, y  = _to_xy(lat, lon)
    count = ctypes.c_int(0)
    ptr   = lib.kd_knn(_root, PointT(x, y, -1), ctypes.c_int(k), ctypes.byref(count))
    if not ptr:
        return []
    results = [_enrich(ptr[i]) for i in range(count.value)]
    libc.free(ptr)
    return results

def kd_delete(point_id):
    lib.kd_delete(_root, ctypes.c_int(point_id))

def kd_insert(facility):
    if "x" in facility and "y" in facility:
        x, y = float(facility["x"]), float(facility["y"])
    else:
        x, y = _to_xy(float(facility["lat"]), float(facility["lon"]))
    lib.kd_insert(ctypes.byref(_root), PointT(x, y, int(facility["id"])))
    _meta[facility["id"]] = {"name": facility.get("name", ""), "type": facility.get("type", ""),
                              "lat": facility.get("lat"), "lon": facility.get("lon")}

def kd_rebalance():
    lib.kd_rebalance(ctypes.byref(_root))

def kd_dead_ratio():
    return float(lib.kd_dead_ratio(_root))
