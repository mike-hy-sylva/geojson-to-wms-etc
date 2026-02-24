"""
generate_stress_test.py
-----------------------
Generates an H3 hexagon stress-test GeoJSON by filling the CIPA bounding box
at resolution 6 (~100k–150k cells).

Resolution reference for this bounding box [-16.45, 10.35, -0.32, 39.31]:
  Res 5  → ~20,000 cells   (fast, light load)
  Res 6  → ~140,000 cells  ← default: meaningful stress test
  Res 7  → ~1,000,000 cells (likely exceeds browser memory limits)

Usage:
    pip install -r requirements.txt
    python generate_stress_test.py            # generates res 6
    python generate_stress_test.py --res 5   # override resolution
"""

import json
import time
import os
import argparse

import h3

# Bounding box of the CIPA source dataset (lon_min, lat_min, lon_max, lat_max)
BOUNDS = {
    "lon_min": -16.45,
    "lat_min": 10.35,
    "lon_max": -0.32,
    "lat_max": 39.31,
}

# GeoJSON polygon describing the bounding box (used by h3.polyfill_geojson)
BBOX_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [BOUNDS["lon_min"], BOUNDS["lat_min"]],
        [BOUNDS["lon_max"], BOUNDS["lat_min"]],
        [BOUNDS["lon_max"], BOUNDS["lat_max"]],
        [BOUNDS["lon_min"], BOUNDS["lat_max"]],
        [BOUNDS["lon_min"], BOUNDS["lat_min"]],  # close the ring
    ]],
}

# Expected approximate polygon counts per resolution (for reference)
EXPECTED_COUNTS = {
    3: 400,
    4: 2_800,
    5: 20_000,
    6: 140_000,
    7: 1_000_000,
}

OUTPUT_FILENAME = "h3_stress_test.geojson"


def generate_h3_geojson(resolution: int = 6) -> tuple:
    """
    Fill the CIPA bounding box with H3 cells at the given resolution.

    Returns:
        (FeatureCollection dict, polygon_count int, generation_ms float)
    """
    print(f"Generating H3 resolution {resolution} cells...")
    expected = EXPECTED_COUNTS.get(resolution, "?")
    print(f"  Expected ~{expected:,} cells")

    t0 = time.perf_counter()

    # h3 v4: geo_to_cells replaces polyfill_geojson
    cells = h3.geo_to_cells(BBOX_GEOJSON, resolution)

    features = []
    for cell in cells:
        # h3 v4: cell_to_boundary returns [(lat, lng), ...] — swap for GeoJSON [lng, lat]
        boundary = h3.cell_to_boundary(cell)
        coords = [[lng, lat] for lat, lng in boundary]
        # Close the polygon ring
        coords = coords + [coords[0]]
        features.append({
            "type": "Feature",
            "properties": {
                "h3_index": cell,
                "resolution": resolution,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
        })

    elapsed_ms = (time.perf_counter() - t0) * 1000

    feature_collection = {
        "type": "FeatureCollection",
        "name": f"H3 Stress Test (Resolution {resolution})",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    return feature_collection, len(features), round(elapsed_ms, 1)


def save_geojson(fc: dict, path: str) -> float:
    """
    Write a FeatureCollection to disk.

    Returns:
        File size in MB.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, separators=(",", ":"))  # compact JSON (no whitespace)
    size_bytes = os.path.getsize(path)
    return round(size_bytes / (1024 * 1024), 1)


def main():
    parser = argparse.ArgumentParser(description="Generate H3 stress-test GeoJSON")
    parser.add_argument(
        "--res",
        type=int,
        default=6,
        choices=[3, 4, 5, 6, 7],
        help="H3 resolution (default: 6 → ~140k cells)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=OUTPUT_FILENAME,
        help=f"Output file path (default: {OUTPUT_FILENAME})",
    )
    args = parser.parse_args()

    if args.res == 7:
        print("WARNING: Resolution 7 generates ~1M polygons.")
        print("         This will produce a ~300MB file and likely crash browser tabs.")
        print("         Continuing anyway — this is the 'limits' demonstration.")
        print()

    fc, count, gen_ms = generate_h3_geojson(resolution=args.res)

    print(f"\nSaving to {args.output}...")
    size_mb = save_geojson(fc, args.output)

    print()
    print("=" * 55)
    print(f"  H3 Resolution {args.res}: {count:,} polygons")
    print(f"  Generation time : {gen_ms:,.0f} ms")
    print(f"  File size       : {size_mb:.1f} MB  ->  {args.output}")
    print("=" * 55)

    if args.res <= 5:
        print()
        print("TIP: Run with --res 6 for a meaningful browser stress test (~140k cells)")
    elif args.res == 6:
        print()
        print("TIP: Run with --res 7 to hit the hard limit (~1M cells, likely crashes browser)")


if __name__ == "__main__":
    main()
