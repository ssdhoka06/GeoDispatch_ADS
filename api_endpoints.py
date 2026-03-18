from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# Request / Response models

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


# Endpoint implementations 
def register_p4_routes(app: FastAPI, gd, state_manager):
    """
    Call this from the main api.py to mount P4's routes.
    `gd` is the geodispatch bridge module.
    `state_manager` is P4's state_manager module.
    """

    @app.post("/optimise")
    def optimise(body: OptimiseRequest):
        """
        Run Lloyd's relaxation algorithm.
        Returns per-iteration facility movements and a final recommendation.
        """
        try:
            steps = gd.run_lloyds(body.iterations, body.convergence_threshold)
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
        Syncs with C engine via the state_manager → bridge pipeline.
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
