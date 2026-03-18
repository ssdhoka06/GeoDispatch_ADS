"""
Maintains a live record of facility states (online / offline / overloaded).
Calls into P5's geodispatch.py bridge to sync state changes with the
C engine (KD-tree delete/insert, Voronoi incremental update).

Dependencies:
    geodispatch.py (P5) — gd.kd_delete(), gd.kd_insert(),
                          gd.voronoi_incremental_update(),
                          gd.voronoi_insert_site()

"""

from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("geodispatch.state_manager")

# Facility states 
class FacilityState(str, Enum):
    ONLINE     = "online"
    OFFLINE    = "offline"
    OVERLOADED = "overloaded"

# Valid transitions
_TRANSITIONS = {
    FacilityState.ONLINE:     {FacilityState.OFFLINE, FacilityState.OVERLOADED},
    FacilityState.OFFLINE:    {FacilityState.ONLINE},
    FacilityState.OVERLOADED: {FacilityState.ONLINE, FacilityState.OFFLINE},
}

# Bridge accessor (lazy so module loads without geodispatch.so) ──
_gd = None

def _get_bridge():
    """Lazy-load the geodispatch ctypes bridge (P5's module)."""
    global _gd
    if _gd is None:
        try:
            import geodispatch as gd_module
            _gd = gd_module
        except ImportError:
            logger.warning(
                "geodispatch bridge not available — "
                "state changes will be recorded but NOT synced to C engine"
            )
    return _gd


# In-memory state store 
# { facility_id (int) : FacilityState }
_facility_states: Dict[int, FacilityState] = {}

# { facility_id : { "x": float, "y": float, "name": str, "type": str } }
_facility_meta: Dict[int, dict] = {}

# Monotonically increasing ID counter for new facilities
_next_id: int = 0


def init_from_facilities(facilities: List[dict]) -> None:
    """
    Initialise the state store from the loaded facility list.
    Called once at startup after pune_facilities.json is read.

    Each facility dict: { "id": int, "x": float, "y": float,
                          "name": str, "type": str }
    """
    global _next_id
    _facility_states.clear()
    _facility_meta.clear()

    for f in facilities:
        fid = f["id"]
        _facility_states[fid] = FacilityState.ONLINE
        _facility_meta[fid] = {
            "x":    f["x"],
            "y":    f["y"],
            "name": f.get("name", ""),
            "type": f.get("type", ""),
        }
    _next_id = max(_facility_states.keys(), default=-1) + 1
    logger.info("State manager initialised with %d facilities", len(_facility_states))


def set_state(facility_id: int, new_state: str) -> dict:
    """
    Transition a facility to a new state.

    Returns a status dict: { "ok": bool, "prev": str, "new": str, "msg": str }
    """
    new_state = FacilityState(new_state)

    if facility_id not in _facility_states:
        return {"ok": False, "prev": None, "new": None,
                "msg": f"Unknown facility {facility_id}"}

    prev = _facility_states[facility_id]

    if new_state == prev:
        return {"ok": True, "prev": prev.value, "new": new_state.value,
                "msg": "No change"}

    if new_state not in _TRANSITIONS.get(prev, set()):
        return {"ok": False, "prev": prev.value, "new": new_state.value,
                "msg": f"Invalid transition {prev.value} → {new_state.value}"}

    # Sync with C engine via bridge
    gd = _get_bridge()

    if new_state in (FacilityState.OFFLINE, FacilityState.OVERLOADED) \
       and prev == FacilityState.ONLINE:
        # Facility going down — remove from spatial index
        if gd:
            try:
                gd.kd_delete(facility_id)
                gd.voronoi_incremental_update(facility_id)
            except Exception as e:
                logger.error("Bridge sync failed on delete: %s", e)

    elif new_state == FacilityState.ONLINE \
         and prev in (FacilityState.OFFLINE, FacilityState.OVERLOADED):
        # Facility coming back up — re-insert into spatial index
        meta = _facility_meta.get(facility_id, {})
        if gd and meta:
            try:
                gd.kd_insert(meta["x"], meta["y"], facility_id)
                gd.voronoi_insert_site(meta["x"], meta["y"])
            except Exception as e:
                logger.error("Bridge sync failed on insert: %s", e)

    _facility_states[facility_id] = new_state
    logger.info("Facility %d: %s → %s", facility_id, prev.value, new_state.value)

    return {"ok": True, "prev": prev.value, "new": new_state.value,
            "msg": "Transition complete"}


def get_state(facility_id: int) -> Optional[str]:
    """Return current state string or None if unknown."""
    s = _facility_states.get(facility_id)
    return s.value if s else None


def get_live_facilities() -> List[int]:
    """Return IDs of all facilities currently ONLINE."""
    return [fid for fid, st in _facility_states.items()
            if st == FacilityState.ONLINE]


def get_all_states() -> Dict[int, str]:
    """Return { id: state_str } for every facility."""
    return {fid: st.value for fid, st in _facility_states.items()}


def register_new_facility(x: float, y: float,
                          name: str, ftype: str) -> int:
    """
    Register a brand-new facility (from the /add-facility endpoint).
    Returns the assigned integer ID.
    """
    global _next_id
    fid = _next_id
    _next_id += 1

    _facility_states[fid] = FacilityState.ONLINE
    _facility_meta[fid] = {"x": x, "y": y, "name": name, "type": ftype}
    logger.info("Registered new facility %d (%s) at (%.2f, %.2f)",
                fid, name, x, y)
    return fid


def remove_facility(facility_id: int) -> bool:
    """
    Mark a facility as OFFLINE (used by /remove-facility endpoint).
    Returns True if the facility existed.
    """
    if facility_id not in _facility_states:
        return False
    set_state(facility_id, FacilityState.OFFLINE.value)
    return True
