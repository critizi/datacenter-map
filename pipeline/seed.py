"""Seed the database with a curated set of well-known hyperscaler datacenters.

These are public knowledge anchors so the globe has visible points immediately,
before any scraping or LLM enrichment runs. Coordinates are approximate to the
known DC campus, not exact (operators rarely publish exact addresses).

Each record is upserted by id, so re-running is safe and won't duplicate.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pipeline.schema import connect, init_db

NOW = datetime.now(timezone.utc).isoformat()

# (id, name, operator, lat, lon, status, capacity_mw, capacity_use, country, region, sources)
SEED = [
    # ---------- AWS ----------
    ("aws-us-east-1", "AWS us-east-1 (Northern Virginia)", "AWS", 39.0438, -77.4874, "operational", 2600, "AWS us-east-1 region — broadest service availability", "USA", "Ashburn, VA", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-us-west-2", "AWS us-west-2 (Oregon)", "AWS", 45.8399, -119.7006, "operational", 1500, "AWS us-west-2 region", "USA", "Boardman, OR", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-us-east-2", "AWS us-east-2 (Ohio)", "AWS", 39.9612, -82.9988, "operational", 900, "AWS us-east-2 region", "USA", "Columbus, OH", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-eu-west-1", "AWS eu-west-1 (Ireland)", "AWS", 53.3498, -6.2603, "operational", 800, "AWS eu-west-1 region", "Ireland", "Dublin", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-eu-central-1", "AWS eu-central-1 (Frankfurt)", "AWS", 50.1109, 8.6821, "operational", 700, "AWS eu-central-1 region", "Germany", "Frankfurt", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-ap-northeast-1", "AWS ap-northeast-1 (Tokyo)", "AWS", 35.6762, 139.6503, "operational", 600, "AWS ap-northeast-1 region", "Japan", "Tokyo", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-ap-southeast-1", "AWS ap-southeast-1 (Singapore)", "AWS", 1.3521, 103.8198, "operational", 500, "AWS ap-southeast-1 region", "Singapore", "Singapore", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),
    ("aws-sa-east-1", "AWS sa-east-1 (São Paulo)", "AWS", -23.5505, -46.6333, "operational", 350, "AWS sa-east-1 region", "Brazil", "São Paulo", ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"]),

    # ---------- Azure ----------
    ("azure-east-us", "Azure East US (Virginia)", "Azure", 37.3719, -79.8164, "operational", 2000, "Azure East US region", "USA", "Boydton, VA", ["https://azure.microsoft.com/en-us/explore/global-infrastructure/"]),
    ("azure-west-us-2", "Azure West US 2 (Quincy)", "Azure", 47.2343, -119.8526, "operational", 1200, "Azure West US 2 region", "USA", "Quincy, WA", ["https://azure.microsoft.com/en-us/explore/global-infrastructure/"]),
    ("azure-north-europe", "Azure North Europe (Dublin)", "Azure", 53.3498, -6.2603, "operational", 900, "Azure North Europe region", "Ireland", "Dublin", ["https://azure.microsoft.com/en-us/explore/global-infrastructure/"]),
    ("azure-west-europe", "Azure West Europe (Amsterdam)", "Azure", 52.3676, 4.9041, "operational", 850, "Azure West Europe region", "Netherlands", "Amsterdam", ["https://azure.microsoft.com/en-us/explore/global-infrastructure/"]),
    ("azure-southeast-asia", "Azure Southeast Asia (Singapore)", "Azure", 1.3521, 103.8198, "operational", 500, "Azure Southeast Asia region", "Singapore", "Singapore", ["https://azure.microsoft.com/en-us/explore/global-infrastructure/"]),
    ("azure-mt-pleasant-wi", "Azure Mt. Pleasant (Wisconsin)", "Azure", 42.7261, -87.9168, "under_construction", 700, "Future Azure capacity expansion", "USA", "Mt. Pleasant, WI", ["https://news.microsoft.com/source/features/digital-transformation/microsoft-wisconsin-datacenter/"]),

    # ---------- Google Cloud ----------
    ("gcp-us-central1", "GCP us-central1 (Iowa)", "GCP", 41.2619, -95.8608, "operational", 1000, "GCP us-central1 region", "USA", "Council Bluffs, IA", ["https://cloud.google.com/about/locations"]),
    ("gcp-us-east1", "GCP us-east1 (South Carolina)", "GCP", 33.8361, -81.1637, "operational", 850, "GCP us-east1 region", "USA", "Moncks Corner, SC", ["https://cloud.google.com/about/locations"]),
    ("gcp-europe-west1", "GCP europe-west1 (Belgium)", "GCP", 50.4674, 3.8203, "operational", 600, "GCP europe-west1 region", "Belgium", "Saint-Ghislain", ["https://cloud.google.com/about/locations"]),
    ("gcp-asia-east1", "GCP asia-east1 (Taiwan)", "GCP", 24.0518, 120.5161, "operational", 500, "GCP asia-east1 region", "Taiwan", "Changhua County", ["https://cloud.google.com/about/locations"]),
    ("gcp-asia-northeast1", "GCP asia-northeast1 (Tokyo)", "GCP", 35.6762, 139.6503, "operational", 450, "GCP asia-northeast1 region", "Japan", "Tokyo", ["https://cloud.google.com/about/locations"]),

    # ---------- Meta ----------
    ("meta-prineville-or", "Meta Prineville", "Meta", 44.2901, -120.8307, "operational", 400, "Meta global infrastructure (Facebook, Instagram, WhatsApp)", "USA", "Prineville, OR", ["https://datacenters.atmeta.com/"]),
    ("meta-forest-city-nc", "Meta Forest City", "Meta", 35.3343, -81.8662, "operational", 300, "Meta global infrastructure", "USA", "Forest City, NC", ["https://datacenters.atmeta.com/"]),
    ("meta-lulea-se", "Meta Luleå", "Meta", 65.5848, 22.1567, "operational", 250, "Meta global infrastructure", "Sweden", "Luleå", ["https://datacenters.atmeta.com/"]),
    ("meta-clonee-ie", "Meta Clonee", "Meta", 53.4106, -6.4197, "operational", 280, "Meta global infrastructure", "Ireland", "Clonee", ["https://datacenters.atmeta.com/"]),
    ("meta-richland-parish-la", "Meta Richland Parish", "Meta", 32.4099, -91.7570, "under_construction", 2000, "Meta AI training capacity — Llama and successors", "USA", "Richland Parish, LA", ["https://about.fb.com/news/2024/12/new-data-center-richland-parish-louisiana/"]),

    # ---------- Oracle ----------
    ("oci-us-ashburn-1", "OCI us-ashburn-1", "Oracle", 39.0438, -77.4874, "operational", 350, "OCI us-ashburn-1 region", "USA", "Ashburn, VA", ["https://www.oracle.com/cloud/data-regions/"]),
    ("oci-uk-london-1", "OCI uk-london-1", "Oracle", 51.5074, -0.1278, "operational", 250, "OCI uk-london-1 region", "UK", "London", ["https://www.oracle.com/cloud/data-regions/"]),

    # ---------- Apple ----------
    ("apple-maiden-nc", "Apple Maiden iCloud", "Apple", 35.5817, -81.2095, "operational", 200, "iCloud, Siri, App Store backend", "USA", "Maiden, NC", ["https://www.apple.com/environment/"]),
    ("apple-reno-nv", "Apple Reno", "Apple", 39.5296, -119.8138, "operational", 150, "iCloud and services backend", "USA", "Reno, NV", ["https://www.apple.com/environment/"]),
    ("apple-waukee-ia", "Apple Waukee", "Apple", 41.6125, -93.8819, "under_construction", 400, "Apple services expansion", "USA", "Waukee, IA", ["https://www.apple.com/newsroom/2017/08/apple-to-build-data-center-in-iowa-investing-in-community/"]),

    # ---------- ByteDance / TikTok ----------
    ("bytedance-hamina-fi", "ByteDance Hamina", "ByteDance", 60.5693, 27.1972, "under_construction", 600, "TikTok European user data (Project Clover)", "Finland", "Hamina", ["https://newsroom.tiktok.com/en-eu/project-clover-update"]),
    ("bytedance-johor-my", "ByteDance Johor", "ByteDance", 1.4927, 103.7414, "planned", 500, "TikTok Southeast Asia capacity", "Malaysia", "Johor", []),
]


def upsert(record):
    (rid, name, operator, lat, lon, status, capacity_mw, capacity_use, country, region, sources) = record
    return {
        "id": rid,
        "name": name,
        "operator": operator,
        "latitude": lat,
        "longitude": lon,
        "status": status,
        "construction_start_date": None,
        "expected_completion_date": None,
        "actual_completion_date": None,
        "build_duration_months": None,
        "capacity_mw": capacity_mw,
        "capacity_use": capacity_use,
        "address": None,
        "country": country,
        "region": region,
        "primary_image_url": None,
        "primary_image_local_path": None,
        "source_urls": json.dumps(sources),
        "confidence": "high" if len(sources) >= 1 else "low",
        "last_updated": NOW,
    }


def seed_database() -> int:
    init_db()
    conn = connect()
    try:
        rows = [upsert(r) for r in SEED]
        cols = list(rows[0].keys())
        placeholders = ",".join(f":{c}" for c in cols)
        col_list = ",".join(cols)
        update_clause = ",".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = (
            f"INSERT INTO datacenters ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {update_clause}"
        )
        conn.executemany(sql, rows)
        conn.commit()
        return len(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    n = seed_database()
    print(f"Seeded {n} datacenters")
