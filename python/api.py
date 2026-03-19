from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import geodispatch as gd

app = FastAPI(title="GeoDispatch", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── P1 — Ragini ───────────────────────────────────────────────

class QueryRequest(BaseModel):
    lat: float
    lon: float

class KNNRequest(BaseModel):
    lat: float
    lon: float
    k: int = 3

class OptimiseRequest(BaseModel):
    iterations: int = Field(default=10, ge=1, le=200,
                            description="Number of Lloyd's iterations to run")
    convergence_threshold: float = Field(
        default=50.0, ge=0.1,
        description="Stop early if total movement < threshold (metres)")

class SetStateRequest(BaseModel):
    facility_id: int
    new_state: str = Field(
        ..., pattern="^(online|offline|overloaded)$",
        description="Target state: online | offline | overloaded")


@app.post("/query-nearest")
def query_nearest(body: QueryRequest):
    result = gd.kd_nearest(body.lat, body.lon)
    if result.get("id") == -1:
        return {"error": "No facilities available"}
    return {"facility": result}


@app.post("/query-knn")
def query_knn(body: KNNRequest):
    results = gd.kd_knn(body.lat, body.lon, body.k)
    return {"k": body.k, "facilities": results}


# Lazy import: state_manager can work without geodispatch.so loaded
import state_manager


@app.post("/optimise")
def optimise(body: OptimiseRequest):
    """
    Run Lloyd's relaxation algorithm.
    Returns per-iteration facility movements and a final recommendation.
    """
    try:
        steps = gd.run_lloyds(body.iterations, body.convergence_threshold)
    except AttributeError:
        raise HTTPException(
            status_code=501,
            detail="Lloyd's algorithm not yet available (waiting for P5's algo.c)")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Lloyd's optimisation failed: {e}")

    if not steps:
        return {"steps": [], "recommendation": None,
                "msg": "No movement — already converged."}

    return {
        "steps": steps,
        "recommendation": steps[-1].get("facility_movements", []),
    }


@app.post("/set-state")
def set_facility_state(body: SetStateRequest):
    """
    Transition a facility between online / offline / overloaded.
    Syncs with C engine via state_manager -> geodispatch bridge.
    """
    result = state_manager.set_state(body.facility_id, body.new_state)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["msg"])
    return result


@app.get("/facility-states")
def facility_states():
    """Return { facility_id: state } for all facilities."""
    return state_manager.get_all_states()


@app.get("/live-facilities")
def live_facilities():
    """Return list of facility IDs that are currently online."""
    return {"ids": state_manager.get_live_facilities()}


# ── P3 — Shakti ───────────────────────────────────────────────
import math

@app.get('/coverage-map')
def coverage_map():
    cells = gd.get_coverage_map() if hasattr(gd, 'get_coverage_map') else []

    features = []
    for cell in cells:
        polygon_coords = []
        for x, y in cell.get('polygon', []):
            lat = (y / 111320.0) + 18.5204
            lon = (x / (math.cos(18.5204 * math.pi / 180.0) * 111320.0)) + 73.8567
            polygon_coords.append([lon, lat])

        feature = {
            "type": "Feature",
            "properties": {
                "site_id": cell.get('site_id'),
                "area": cell.get('area', 0),
                "is_underserved": cell.get('is_underserved', 0),
                "facility_name": cell.get('facility_name', f"Facility {cell.get('site_id')}")
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords]
            }
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


