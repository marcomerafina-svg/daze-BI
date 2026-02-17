#!/usr/bin/env python3
"""
Extract networks data from the SQL dump and produce dashboard JSON files.

Reads dazeapi-schema_dump.sql, parses the COPY block for dazeapi.networks,
cleans/normalizes cities, filters junk and deleted rows, then writes:
  - dashboard/data/networks_by_city.json   (per-city aggregates)
  - dashboard/data/summary.json            (global summary)
"""

import json
import os
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SQL_DUMP = "/home/user/daze-BI/dazeapi-schema_dump.sql"
OUTPUT_DIR = "/home/user/daze-BI/dashboard/data"

# Line numbers (1-indexed) that bracket the data rows
DATA_START_LINE = 39346
DATA_END_LINE = 63158

COLUMNS = [
    "id", "name", "address", "city", "zip_code", "country",
    "network_type", "grid_is_three_phase", "supply_max_power",
    "chargers_max_power", "is_photovoltaic", "is_photovoltaic_three_phase",
    "is_accumulation", "accumulation_max_power", "arera", "is_deleted",
    "slave_number", "energy_cost_mul_by_thousand", "smart_tariff_enabled",
    "eco_mode_enabled", "network_recharge_modality", "timezone",
    "self_consumption_enabled_out_of_time_slot", "ems_configuration",
    "three_phase_auto_switch_enabled", "currency", "integration_partner_id",
    "created_on", "updated_on",
    "price_activation_mul_by_thousand", "price_energy_mul_by_thousand",
    "price_minute_charging_mul_by_thousand",
    "price_minute_post_charging_mul_by_thousand",
]

# Cities to discard (after lowering + stripping)
JUNK_CITIES = {"", "a", "1", "test"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pg_val(raw: str):
    """Return None for Postgres NULL marker, else the stripped string."""
    return None if raw == "\\N" else raw.strip()


def pg_bool(raw: str) -> bool:
    """Interpret Postgres boolean literal."""
    return raw.strip().lower() in ("t", "true")


def normalize_city(city: str) -> str:
    """Title-case, strip, and collapse known variants."""
    city = city.strip().title()
    return city


def is_junk_city(city: str) -> bool:
    """Return True if the city should be filtered out."""
    low = city.lower().strip()
    if low in JUNK_CITIES:
        return True
    # single-character cities
    if len(low) <= 1:
        return True
    return False


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse a Postgres timestamp string to datetime."""
    if ts_str is None:
        return None
    try:
        # Format: 2025-10-15 21:33:30.941115+00
        return datetime.fromisoformat(ts_str.replace("+00", "+00:00"))
    except Exception:
        try:
            return datetime.fromisoformat(ts_str)
        except Exception:
            return None


def power_bucket(watts: float) -> str:
    """Map watts into human-readable buckets."""
    if watts <= 3000:
        return "0-3000"
    elif watts <= 6000:
        return "3001-6000"
    elif watts <= 10000:
        return "6001-10000"
    elif watts <= 20000:
        return "10001-20000"
    else:
        return "20001+"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Read and parse the data rows
    # ------------------------------------------------------------------
    rows = []
    with open(SQL_DUMP, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if line_no < DATA_START_LINE:
                continue
            if line_no > DATA_END_LINE:
                break
            line = line.rstrip("\n")
            if line == "\\.":
                break
            fields = line.split("\t")
            if len(fields) != len(COLUMNS):
                # Skip malformed lines
                continue
            row = dict(zip(COLUMNS, fields))
            rows.append(row)

    print(f"Parsed {len(rows)} raw rows from SQL dump.")

    # ------------------------------------------------------------------
    # 2. Filter deleted networks
    # ------------------------------------------------------------------
    rows = [r for r in rows if not pg_bool(r["is_deleted"])]
    print(f"After removing deleted: {len(rows)} rows.")

    # ------------------------------------------------------------------
    # 3. Normalize cities and filter junk
    # ------------------------------------------------------------------
    for r in rows:
        r["city"] = normalize_city(pg_val(r["city"]) or "")
        r["country"] = (pg_val(r["country"]) or "").strip()

    rows = [r for r in rows if not is_junk_city(r["city"])]
    print(f"After removing junk cities: {len(rows)} rows.")

    # ------------------------------------------------------------------
    # 4. Group by (city, country) and aggregate
    # ------------------------------------------------------------------
    groups = defaultdict(lambda: {
        "count": 0,
        "zip_codes": [],
        "supply_powers": [],
        "pv_count": 0,
        "three_phase_count": 0,
        "network_types": defaultdict(int),
        "earliest_created": None,
    })

    # Also accumulate global stats
    total_networks = 0
    country_counts = defaultdict(int)
    global_network_types = defaultdict(int)
    global_pv = 0
    global_three_phase = 0
    monthly_counts = defaultdict(int)
    power_dist = defaultdict(int)

    for r in rows:
        city = r["city"]
        country = r["country"]
        key = (city, country)
        g = groups[key]

        g["count"] += 1

        zip_code = pg_val(r["zip_code"])
        if zip_code:
            g["zip_codes"].append(zip_code)

        try:
            sp = float(pg_val(r["supply_max_power"]) or 0)
        except (ValueError, TypeError):
            sp = 0.0
        g["supply_powers"].append(sp)

        if pg_bool(r["is_photovoltaic"]):
            g["pv_count"] += 1

        if pg_bool(r["grid_is_three_phase"]):
            g["three_phase_count"] += 1

        nt = pg_val(r["network_type"]) or "unknown"
        g["network_types"][nt] += 1

        created = parse_timestamp(pg_val(r["created_on"]))
        if created is not None:
            if g["earliest_created"] is None or created < g["earliest_created"]:
                g["earliest_created"] = created

        # Global stats
        total_networks += 1
        country_counts[country] += 1
        global_network_types[nt] += 1
        if pg_bool(r["is_photovoltaic"]):
            global_pv += 1
        if pg_bool(r["grid_is_three_phase"]):
            global_three_phase += 1
        if created is not None:
            month_key = created.strftime("%Y-%m")
            monthly_counts[month_key] += 1
        power_dist[power_bucket(sp)] += 1

    # ------------------------------------------------------------------
    # 5. Build networks_by_city list
    # ------------------------------------------------------------------
    by_city = []
    for (city, country), g in sorted(groups.items(), key=lambda x: -x[1]["count"]):
        avg_power = (
            round(sum(g["supply_powers"]) / len(g["supply_powers"]), 1)
            if g["supply_powers"]
            else 0.0
        )
        # Convert avg from watts to kW
        avg_power_kw = round(avg_power / 1000, 1)

        sample_zip = g["zip_codes"][0] if g["zip_codes"] else ""
        first_created = (
            g["earliest_created"].strftime("%Y-%m-%d")
            if g["earliest_created"]
            else None
        )

        by_city.append({
            "city": city,
            "country": country,
            "zip_code": sample_zip,
            "count": g["count"],
            "avg_power_kw": avg_power_kw,
            "photovoltaic_count": g["pv_count"],
            "three_phase_count": g["three_phase_count"],
            "network_types": dict(g["network_types"]),
            "first_created": first_created,
        })

    out_path = os.path.join(OUTPUT_DIR, "networks_by_city.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(by_city, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(by_city)} city records to {out_path}")

    # ------------------------------------------------------------------
    # 6. Build summary
    # ------------------------------------------------------------------
    monthly_growth = sorted(
        [{"month": m, "count": c} for m, c in monthly_counts.items()],
        key=lambda x: x["month"],
    )

    # Order power_distribution buckets logically
    bucket_order = ["0-3000", "3001-6000", "6001-10000", "10001-20000", "20001+"]
    ordered_power_dist = {b: power_dist.get(b, 0) for b in bucket_order}

    summary = {
        "total_networks": total_networks,
        "total_cities": len(by_city),
        "countries": dict(sorted(country_counts.items(), key=lambda x: -x[1])),
        "network_types": dict(sorted(global_network_types.items())),
        "photovoltaic_total": global_pv,
        "three_phase_total": global_three_phase,
        "monthly_growth": monthly_growth,
        "power_distribution": ordered_power_dist,
    }

    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
