"""
Fetches hospitals and fire stations in Pune from OpenStreetMap (Overpass API),
converts lat/lon to metric x/y, and writes data/pune_facilities.json.

Run once before starting the server:
    python python/data_loader.py
"""

import json
import math
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

OVERPASS_URL  = "https://overpass-api.de/api/interpreter"
BBOX          = (18.40, 73.70, 18.65, 74.05)   # south, west, north, east — covers Pune
AMENITY_TYPES = ["hospital", "fire_station"]

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
OUT_FILE  = DATA_DIR / "pune_facilities.json"

# Pune city centre — projection origin (equirectangular)
LAT0 = 18.5204
LON0 = 73.8567
R    = 6_371_000.0

def latlon_to_xy(lat, lon):
    x = math.radians(lon - LON0) * math.cos(math.radians(LAT0)) * R
    y = math.radians(lat - LAT0) * R
    return x, y

def build_query(bbox, amenity_types):
    s, w, n, e = bbox
    clauses = "\n  ".join(f'node["amenity"="{t}"]({s},{w},{n},{e});' for t in amenity_types)
    return f"[out:json][timeout:60];\n(\n  {clauses}\n);\nout body;"

def fetch_overpass(query, retries=3):
    req = urllib.request.Request(
        OVERPASS_URL,
        data=("data=" + urllib.request.quote(query, safe="")).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "GeoDispatch-ADS/1.0"},
        method="POST",
    )
    backoff = 5.0
    for attempt in range(1, retries + 1):
        try:
            print(f"Querying Overpass API (attempt {attempt}/{retries})...")
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read())
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"Error: {e}", file=sys.stderr)
            if attempt < retries:
                print(f"Retrying in {backoff:.0f}s...", file=sys.stderr)
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

def parse_facilities(osm_json):
    records = []
    for elem in osm_json.get("elements", []):
        if elem.get("type") != "node":
            continue
        tags    = elem.get("tags", {})
        amenity = tags.get("amenity", "")
        if amenity not in AMENITY_TYPES:
            continue
        lat, lon = elem["lat"], elem["lon"]
        x, y = latlon_to_xy(lat, lon)
        records.append({
            "_sort_key": (amenity, elem["id"]),
            "lat": lat, "lon": lon,
            "x": round(x, 4), "y": round(y, 4),
            "name": tags.get("name", ""),
            "type": amenity,
        })

    records.sort(key=lambda r: r["_sort_key"])

    return [{"id": i, "x": r["x"], "y": r["y"], "lat": r["lat"],
             "lon": r["lon"], "name": r["name"], "type": r["type"]}
            for i, r in enumerate(records)]

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    osm_data   = fetch_overpass(build_query(BBOX, AMENITY_TYPES))
    facilities = parse_facilities(osm_data)

    if not facilities:
        print("No facilities found. Check bbox or Overpass availability.", file=sys.stderr)
        sys.exit(1)

    counts = {}
    for f in facilities:
        counts[f["type"]] = counts.get(f["type"], 0) + 1

    print(f"Found {len(facilities)} facilities: {counts}")

    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(facilities, fh, indent=2, ensure_ascii=False)

    print(f"Written to {OUT_FILE}")

if __name__ == "__main__":
    main()
