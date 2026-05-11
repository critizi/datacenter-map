"""Fetch satellite imagery from NASA GIBS (Global Imagery Browse Services).

Fetches a Sentinel-2 HLS tile (30 m/px) at zoom-12 for each datacenter,
falling back to MODIS Terra True Color (250 m/px) at zoom-9 if the
high-res tile has no data.  Saves PNG/JPEG to data/images/{id}.png and
updates primary_image_local_path in the database.

GIBS does not require an API key — it is a free NASA public service.
The NASA_API_KEY environment variable is accepted for consistency but
unused by GIBS itself.

Usage:
    python -m pipeline.fetch_images                  # all datacenters
    python -m pipeline.fetch_images --force          # re-fetch existing
    python -m pipeline.fetch_images --id aws-us-east-1   # single DC
"""
from __future__ import annotations

import argparse
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from pipeline.schema import connect

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "data" / "images"

_GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

# Sentinel-2 HLS 30 m, max zoom 12 (~7.6 km per tile at equator)
_HLS_LAYER = "HLS_S30_Nadir_BRDF_Adjusted_Reflectance"
_HLS_TMS = "GoogleMapsCompatible_Level12"
_HLS_ZOOM = 12
_HLS_EXT = "png"

# MODIS Terra True Color 250 m, max zoom 9 (~56 km per tile at equator)
_MODIS_LAYER = "MODIS_Terra_CorrectedReflectance_TrueColor"
_MODIS_TMS = "GoogleMapsCompatible_Level9"
_MODIS_ZOOM = 9
_MODIS_EXT = "jpg"

# Dates tried in order — June often has cloud cover; August/September is clearer
_IMAGERY_DATES = ["2024-08-01", "2024-09-15", "2024-06-15", "2023-08-01"]

# A tile with fewer than this many bytes is likely blank / no-data
_MIN_BYTES = 7_000

_DELAY = 0.4  # seconds between requests


def _deg2tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def _tile_url(layer: str, tms: str, zoom: int, ext: str, lat: float, lon: float, date: str) -> str:
    x, y = _deg2tile(lat, lon, zoom)
    return f"{_GIBS}/{layer}/default/{date}/{tms}/{zoom}/{y}/{x}.{ext}"


def _get(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "datacenter-map/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return None  # zoom out of range for this layer
        print(f"HTTP {e.code}", end=" ")
        return None
    except Exception as e:
        print(str(e)[:50], end=" ")
        return None


def fetch_tile(lat: float, lon: float) -> tuple[bytes, str] | None:
    """Return (image_bytes, extension) using best available source."""
    for date in _IMAGERY_DATES:
        # Try high-res Sentinel-2 HLS first
        url = _tile_url(_HLS_LAYER, _HLS_TMS, _HLS_ZOOM, _HLS_EXT, lat, lon, date)
        data = _get(url)
        if data and len(data) >= _MIN_BYTES:
            return data, _HLS_EXT

        # Fall back to MODIS (daily global coverage, lower res)
        url = _tile_url(_MODIS_LAYER, _MODIS_TMS, _MODIS_ZOOM, _MODIS_EXT, lat, lon, date)
        data = _get(url)
        if data and len(data) >= _MIN_BYTES:
            return data, _MODIS_EXT

    return None


def run(force: bool = False, dc_id: str | None = None) -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()

    if dc_id:
        rows = conn.execute(
            "SELECT id, name, latitude, longitude, primary_image_local_path FROM datacenters WHERE id=?",
            (dc_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, latitude, longitude, primary_image_local_path FROM datacenters"
        ).fetchall()

    to_fetch = [
        r for r in rows
        if force
        or (
            not r["primary_image_local_path"]
            and not (IMAGES_DIR / f"{r['id']}.png").exists()
            and not (IMAGES_DIR / f"{r['id']}.jpg").exists()
        )
    ]
    skipped = len(rows) - len(to_fetch)
    print(f"NASA GIBS imagery: {len(to_fetch)} to fetch, {skipped} skipped.\n")

    ok = failed = 0
    for row in to_fetch:
        rid = row["id"]
        lat, lon = row["latitude"], row["longitude"]
        print(f"  {rid}  ({lat:.3f}, {lon:.3f})  ... ", end="", flush=True)

        result = fetch_tile(lat, lon)
        if result:
            data, ext = result
            path = IMAGES_DIR / f"{rid}.{ext}"
            path.write_bytes(data)
            local_path = f"images/{rid}.{ext}"
            conn.execute(
                "UPDATE datacenters SET primary_image_local_path=? WHERE id=?",
                (local_path, rid),
            )
            conn.commit()
            ok += 1
            src = "HLS" if ext == "png" else "MODIS"
            print(f"OK  {src}  ({len(data) // 1024} KB)")
        else:
            failed += 1
            print("FAILED")

        time.sleep(_DELAY)

    print(f"\n{ok} fetched  |  {failed} failed")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-fetch existing images")
    parser.add_argument("--id", dest="dc_id", default=None, help="Fetch only this datacenter ID")
    # NASA_API_KEY accepted but unused — GIBS is keyless
    parser.add_argument("--api-key", default=os.environ.get("NASA_API_KEY", ""), help="(unused for GIBS)")
    args = parser.parse_args()

    run(force=args.force, dc_id=args.dc_id)
