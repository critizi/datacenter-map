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

# (id, name, operator, lat, lon, status, capacity_mw, capacity_use, country, region, sources, image_url)
SEED = [
    # ---------- AWS ----------
    (
        "aws-us-east-1", "AWS us-east-1 (Northern Virginia)", "AWS",
        39.0438, -77.4874, "operational", 2600,
        "AWS cloud (EC2/S3/Lambda/Bedrock) — primary home of Anthropic Claude. "
        "Amazon committed $4B to Anthropic (2023) with potential for $4B more; Anthropic runs "
        "Claude training and inference on AWS Trainium/Inferentia chips, principally in us-east-1. "
        "Largest single AWS region by deployed capacity.",
        "USA", "Ashburn, VA",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-us-west-2", "AWS us-west-2 (Oregon)", "AWS",
        45.8399, -119.7006, "operational", 1500,
        "AWS cloud (us-west-2) — secondary Anthropic inference region; Amazon Bedrock AI services; "
        "major hyperscale campus powered largely by hydroelectric and wind energy.",
        "USA", "Boardman, OR",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-us-east-2", "AWS us-east-2 (Ohio)", "AWS",
        39.9612, -82.9988, "operational", 900,
        "AWS cloud (us-east-2); redundant US East region for AWS AI services and Amazon Bedrock.",
        "USA", "Columbus, OH",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-eu-west-1", "AWS eu-west-1 (Ireland)", "AWS",
        53.3498, -6.2603, "operational", 800,
        "AWS cloud EU flagship region; Amazon Bedrock and Claude API available for GDPR-scoped EU workloads.",
        "Ireland", "Dublin",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-eu-central-1", "AWS eu-central-1 (Frankfurt)", "AWS",
        50.1109, 8.6821, "operational", 700,
        "AWS cloud (Germany); GDPR/DSGVO compliance hub for European enterprise and AI workloads.",
        "Germany", "Frankfurt",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-ap-northeast-1", "AWS ap-northeast-1 (Tokyo)", "AWS",
        35.6762, 139.6503, "operational", 600,
        "AWS cloud (Japan); largest APAC AWS region; serves Japanese AI/ML workloads and Amazon Bedrock Japan.",
        "Japan", "Tokyo",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-ap-southeast-1", "AWS ap-southeast-1 (Singapore)", "AWS",
        1.3521, 103.8198, "operational", 500,
        "AWS cloud (Southeast Asia hub); Amazon Bedrock and AI services for ASEAN markets.",
        "Singapore", "Singapore",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),
    (
        "aws-sa-east-1", "AWS sa-east-1 (São Paulo)", "AWS",
        -23.5505, -46.6333, "operational", 350,
        "AWS cloud (South America); only AWS region in Latin America; serves Brazilian and LatAm AI/cloud workloads.",
        "Brazil", "São Paulo",
        ["https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"],
        None,
    ),

    # ---------- Azure ----------
    (
        "azure-east-us", "Azure East US (Virginia)", "Azure",
        37.3719, -79.8164, "operational", 2000,
        "Microsoft Azure cloud + OpenAI (GPT-4, GPT-o1, o3 training and inference). "
        "Azure is OpenAI's exclusive cloud provider — Microsoft has committed $13B+ to OpenAI since 2019. "
        "This region hosts the largest concentration of OpenAI compute globally, powering ChatGPT, "
        "the OpenAI API, and Microsoft Copilot.",
        "USA", "Boydton, VA",
        ["https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/"],
        None,
    ),
    (
        "azure-west-us-2", "Azure West US 2 (Quincy)", "Azure",
        47.2343, -119.8526, "operational", 1200,
        "Microsoft Azure cloud (West Coast); OpenAI inference for US West users; Microsoft Copilot AI services.",
        "USA", "Quincy, WA",
        ["https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/"],
        None,
    ),
    (
        "azure-north-europe", "Azure North Europe (Dublin)", "Azure",
        53.3498, -6.2603, "operational", 900,
        "Microsoft Azure EU cloud; OpenAI inference for EU users (GDPR-compliant); Microsoft Copilot EU.",
        "Ireland", "Dublin",
        ["https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/"],
        None,
    ),
    (
        "azure-west-europe", "Azure West Europe (Amsterdam)", "Azure",
        52.3676, 4.9041, "operational", 850,
        "Microsoft Azure cloud (Netherlands); major European AI inference hub; OpenAI EU workloads.",
        "Netherlands", "Amsterdam",
        ["https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/"],
        None,
    ),
    (
        "azure-southeast-asia", "Azure Southeast Asia (Singapore)", "Azure",
        1.3521, 103.8198, "operational", 500,
        "Microsoft Azure APAC flagship; Microsoft Copilot and OpenAI API for Southeast Asia.",
        "Singapore", "Singapore",
        ["https://azure.microsoft.com/en-us/explore/global-infrastructure/geographies/"],
        "https://www.gstatic.com/marketing-cms/assets/images/21/04/f43823104859a23d1b45f3a84d1b/singapore-hero-2.jpg",
    ),
    (
        "azure-mt-pleasant-wi", "Azure Fairwater (Mt. Pleasant, WI)", "Azure",
        42.7261, -87.9168, "operational", 700,
        "Fairwater — Microsoft's purpose-built AI superfactory, opened 2026. "
        "Houses hundreds of thousands of NVIDIA H100/H200 GPUs in a two-story liquid-cooled configuration. "
        "Dedicated to OpenAI's next-generation model training at scale; Microsoft calls it "
        "'the world's most powerful AI datacenter.' Part of $3.3B Wisconsin investment. "
        "Connected to a second identical campus in Atlanta as an AI superfactory cluster.",
        "USA", "Mt. Pleasant, WI",
        [
            "https://news.microsoft.com/source/2024/05/08/microsoft-announces-3-3-billion-investment-in-wisconsin-to-spur-artificial-intelligence-innovation-and-economic-growth/",
            "https://blogs.microsoft.com/blog/2025/09/18/inside-the-worlds-most-powerful-ai-datacenter/",
        ],
        "https://blogs.microsoft.com/wp-content/uploads/2025/09/OMB-Image-1-Datacenter.jpg",
    ),

    # ---------- Google Cloud ----------
    (
        "gcp-us-central1", "GCP us-central1 (Iowa)", "GCP",
        41.2619, -95.8608, "operational", 1000,
        "Google Cloud + Google DeepMind (Gemini model training and inference). "
        "Google's flagship North American AI infrastructure hub; Vertex AI platform; "
        "Google's TPU supercomputers for Gemini Ultra/Pro training are concentrated here.",
        "USA", "Council Bluffs, IA",
        ["https://cloud.google.com/about/locations", "https://datacenters.google/locations/iowa/"],
        "https://www.gstatic.com/marketing-cms/assets/images/36/a9/65a25c6f463fb493dbac5ba475bb/council-bluffs-hero.jpg",
    ),
    (
        "gcp-us-east1", "GCP us-east1 (South Carolina)", "GCP",
        33.8361, -81.1637, "operational", 850,
        "Google Cloud (US East); major AI inference region for Gemini and Vertex AI; "
        "Google's South Carolina campus runs on 100% renewable energy.",
        "USA", "Moncks Corner, SC",
        ["https://cloud.google.com/about/locations", "https://datacenters.google/locations/south-carolina/"],
        "https://www.gstatic.com/marketing-cms/assets/images/5b/62/f2ec72f24e5a9738a458f6b72c5c/dc-location-page-header-imagery-south-carolina.webp",
    ),
    (
        "gcp-europe-west1", "GCP europe-west1 (Belgium)", "GCP",
        50.4674, 3.8203, "operational", 600,
        "Google Cloud EU flagship (St. Ghislain, Belgium); Gemini inference for European users; "
        "Vertex AI EU; Google's first European data center, operational since 2010.",
        "Belgium", "Saint-Ghislain",
        ["https://cloud.google.com/about/locations", "https://datacenters.google/locations/belgium/"],
        "https://www.gstatic.com/marketing-cms/assets/images/02/71/924a39ac4e19badb460d745be842/st-ghislain-belgium-hero.jpg",
    ),
    (
        "gcp-asia-east1", "GCP asia-east1 (Taiwan)", "GCP",
        24.0518, 120.5161, "operational", 500,
        "Google Cloud (Taiwan); APAC AI inference hub for Gemini; Vertex AI for Greater China and NE Asia.",
        "Taiwan", "Changhua County",
        ["https://cloud.google.com/about/locations", "https://datacenters.google/locations/taiwan/"],
        "https://www.gstatic.com/marketing-cms/assets/images/62/9e/a83866944646bb64c130a1e483d2/changhua-county-taiwan-hero.jpg",
    ),
    (
        "gcp-asia-northeast1", "GCP asia-northeast1 (Tokyo)", "GCP",
        35.6762, 139.6503, "operational", 450,
        "Google Cloud (Japan); Gemini and AI services for Japan and Northeast Asia; "
        "Google's Inzai, Chiba campus.",
        "Japan", "Tokyo",
        ["https://cloud.google.com/about/locations"],
        None,
    ),

    # ---------- Meta ----------
    (
        "meta-prineville-or", "Meta Prineville", "Meta",
        44.2901, -120.8307, "operational", 400,
        "Meta internal only — Facebook, Instagram, WhatsApp global infrastructure. "
        "Meta's first purpose-built hyperscale greenfield campus (opened 2011); "
        "pioneered the Open Compute Project (open-source server design). "
        "No third-party cloud tenants; all capacity serves Meta's own platforms.",
        "USA", "Prineville, OR",
        ["https://datacenters.atmeta.com/"],
        "https://about.fb.com/wp-content/uploads/2015/05/prineville-data-center-exterior-4.jpg",
    ),
    (
        "meta-forest-city-nc", "Meta Forest City", "Meta",
        35.3343, -81.8662, "operational", 300,
        "Meta internal — Facebook/Instagram/WhatsApp US East serving. "
        "One of Meta's oldest hyperscale facilities; 100% renewable energy.",
        "USA", "Forest City, NC",
        ["https://datacenters.atmeta.com/"],
        None,
    ),
    (
        "meta-lulea-se", "Meta Luleå", "Meta",
        65.5848, 22.1567, "operational", 250,
        "Meta internal — European social media infrastructure (Facebook/Instagram/WhatsApp EU). "
        "Cooled using Arctic air year-round; one of the world's most energy-efficient hyperscale facilities "
        "(PUE ~1.01). 100% renewable hydroelectric power.",
        "Sweden", "Luleå",
        ["https://datacenters.atmeta.com/"],
        None,
    ),
    (
        "meta-clonee-ie", "Meta Clonee", "Meta",
        53.4106, -6.4197, "operational", 280,
        "Meta internal — European data hub; Facebook/Instagram EU serving under GDPR. "
        "Meta's largest European campus.",
        "Ireland", "Clonee",
        ["https://datacenters.atmeta.com/"],
        None,
    ),
    (
        "meta-richland-parish-la", "Meta Richland Parish", "Meta",
        32.4099, -91.7570, "under_construction", 2000,
        "Meta AI training ONLY — dedicated exclusively to training Llama 4, Llama 5, and future "
        "open-source LLMs. Meta's largest facility ever: $10B investment, 2GW capacity, 4 million sq ft. "
        "No commercial cloud tenants — 100% Meta AI workloads. "
        "This is the clearest pure-play AI training infrastructure bet in Meta's portfolio.",
        "USA", "Richland Parish, LA",
        [
            "https://datacenters.atmeta.com/richland-parish-data-center/",
            "https://www.datacenterdynamics.com/en/news/meta-announces-4-million-sq-ft-louisiana-data-center-campus/",
        ],
        "https://datacenters.atmeta.com/wp-content/uploads/2024/12/Richland-Parish-Data-Cener.jpg",
    ),

    # ---------- Oracle ----------
    (
        "oci-us-ashburn-1", "OCI us-ashburn-1", "Oracle",
        39.0438, -77.4874, "operational", 350,
        "Oracle Cloud Infrastructure + xAI (Grok). "
        "Oracle signed a landmark deal with Elon Musk's xAI in 2024 to provide up to 131,072 NVIDIA H100 GPUs "
        "for Grok model training and inference. Oracle is xAI's primary cloud infrastructure partner. "
        "Also hosts Oracle database cloud and enterprise SaaS workloads.",
        "USA", "Ashburn, VA",
        ["https://www.oracle.com/cloud/data-regions/"],
        None,
    ),
    (
        "oci-uk-london-1", "OCI uk-london-1", "Oracle",
        51.5074, -0.1278, "operational", 250,
        "Oracle Cloud UK region; enterprise cloud and database workloads; UK-regulated financial services customers.",
        "UK", "London",
        ["https://www.oracle.com/cloud/data-regions/"],
        None,
    ),

    # ---------- Apple ----------
    (
        "apple-maiden-nc", "Apple Maiden iCloud", "Apple",
        35.5817, -81.2095, "operational", 200,
        "Apple internal only — iCloud storage/sync, Siri NLP, App Store, Apple Maps. "
        "Apple does not sell cloud or AI capacity to third parties. "
        "100% renewable energy; adjacent 200MW solar installation. "
        "Apple's first purpose-built data center.",
        "USA", "Maiden, NC",
        ["https://www.apple.com/environment/"],
        None,
    ),
    (
        "apple-reno-nv", "Apple Reno", "Apple",
        39.5296, -119.8138, "operational", 150,
        "Apple internal — iCloud and Apple services for Western US; Apple's Nevada campus.",
        "USA", "Reno, NV",
        ["https://www.apple.com/environment/"],
        None,
    ),
    (
        "apple-waukee-ia", "Apple Waukee", "Apple",
        41.6125, -93.8819, "operational", 400,
        "Apple internal — iCloud/Siri/Apple AI services; $1.3B campus opened October 2024 "
        "(seven years after announcement). Apple's largest data center campus. "
        "100% renewable energy; Apple Intelligence AI workloads expected to grow here.",
        "USA", "Waukee, IA",
        ["https://www.apple.com/newsroom/2017/08/apples-next-us-data-center-will-be-built-in-iowa/"],
        None,
    ),

    # ---------- ByteDance / TikTok ----------
    (
        "bytedance-hamina-fi", "ByteDance Hamina", "ByteDance",
        60.5693, 27.1972, "under_construction", 600,
        "TikTok European user data storage — Project Clover (€12B total programme). "
        "Regulatory compliance facility: stores and processes European TikTok user data under GDPR, "
        "with independent cybersecurity oversight by NCC Group. "
        "Not an AI training facility; purpose is data sovereignty for EU regulators.",
        "Finland", "Hamina",
        [
            "https://newsroom.tiktok.com/en-eu/tiktok-sets-new-standards-for-security-and-sustainability-through-12-bn-project-clover-programme",
            "https://newsroom.tiktok.com/en-eu/cornerstonefinland",
        ],
        None,
    ),
    (
        "bytedance-johor-my", "ByteDance Johor", "ByteDance",
        1.4927, 103.7414, "planned", 500,
        "TikTok/ByteDance Southeast Asia infrastructure; serving APAC social media users and "
        "ByteDance AI content recommendation algorithms.",
        "Malaysia", "Johor",
        [],
        None,
    ),
]


def upsert(record):
    (rid, name, operator, lat, lon, status, capacity_mw, capacity_use,
     country, region, sources, image_url) = record
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
        "primary_image_url": image_url,
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
