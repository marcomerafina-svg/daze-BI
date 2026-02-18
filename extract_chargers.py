#!/usr/bin/env python3
"""
Extract chargers (EVSEs) data from the SQL dump, map product codes to
Gruppo Prodotto via the price list CSV, and produce dashboard JSON files.

Reads:
  - dazeapi-schema_dump.sql  (evses, network_evses, networks tables)
  - price_lists.csv           (Codes -> Gruppo Prodotto mapping)

Writes:
  - dashboard/data/chargers_by_city.json
  - dashboard/data/chargers_summary.json
"""

import csv
import json
import os
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SQL_DUMP = "/home/user/daze-BI/dazeapi-schema_dump.sql"
CSV_FILE = "/home/user/daze-BI/price_lists.csv"
OUTPUT_DIR = "/home/user/daze-BI/dashboard/data"

# Line numbers (1-indexed) for COPY blocks
EVSES_START = 7574          # COPY dazeapi.evses (id, serial_number) FROM stdin;
EVSES_END = 24105

NETWORK_EVSES_START = 24122  # COPY dazeapi.network_evses (network_id, evse_id) FROM stdin;
NETWORK_EVSES_END = 39338

NETWORKS_START = 39346       # COPY dazeapi.networks (...) FROM stdin;
NETWORKS_END = 63158

NETWORK_COLUMNS = [
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

JUNK_CITIES = {"", "a", "1", "test"}

# ---------------------------------------------------------------------------
# Build prefix -> Gruppo Prodotto mapping from CSV
# ---------------------------------------------------------------------------
def build_product_group_map():
    """Read the price list CSV and build a 4-char prefix -> Gruppo Prodotto map.

    Only includes charger products (Family == 'AC Chargers'), excluding
    accessories whose codes look like color variants (e.g. DT01WHI).
    """
    prefix_groups = {}

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["Codes"].strip()
            group = row["Gruppo Prodotto"].strip()
            family = row.get("Family", "").strip()

            if not code or len(code) < 4:
                continue
            # Skip accessories – they have short codes or color suffixes
            if group == "AC accessories" or group == "Cables":
                continue

            prefix = code[:4]
            if prefix not in prefix_groups:
                prefix_groups[prefix] = group

    # Manual mappings for older product generations not in the current CSV
    legacy_map = {
        "DB07": "Dazebox C",      # old gen Dazebox -> same family as DB08
        "DM04": "Dazebox",        # very old model
        "OS01": "Duo",            # older gen Duo
        "OT01": "Duo",            # older gen Duo
        "OT03": "Duo",            # gen 3 Duo
        "CH01": "Altro",          # unknown
        "US01": "Urban",          # older gen Urban
        "US03": "Urban",          # gen 3 Urban
        "UT01": "Urban",          # older gen Urban
        "UT03": "Urban",          # gen 3 Urban
        "YP02": "Altro",          # unknown
        "S010": "Altro",          # malformed serial
    }

    for prefix, group in legacy_map.items():
        if prefix not in prefix_groups:
            prefix_groups[prefix] = group

    return prefix_groups


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pg_val(raw):
    return None if raw == "\\N" else raw.strip()

def pg_bool(raw):
    return raw.strip().lower() in ("t", "true")

def normalize_city(city):
    return city.strip().title()

def is_junk_city(city):
    low = city.lower().strip()
    return low in JUNK_CITIES or len(low) <= 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Build product group mapping
    prefix_map = build_product_group_map()
    print(f"Product prefix map: {len(prefix_map)} entries")
    for p in sorted(prefix_map.keys()):
        print(f"  {p} -> {prefix_map[p]}")

    # 2. Parse EVSEs (chargers)
    evses = {}  # evse_id -> serial_number
    with open(SQL_DUMP, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if line_no <= EVSES_START:
                continue
            if line_no >= EVSES_END:
                break
            line = line.rstrip("\n")
            if line == "\\.":
                break
            parts = line.split("\t")
            if len(parts) == 2:
                evses[parts[0]] = parts[1]

    print(f"Parsed {len(evses)} EVSEs")

    # 3. Parse network_evses (junction table)
    evse_to_network = {}  # evse_id -> network_id
    with open(SQL_DUMP, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if line_no <= NETWORK_EVSES_START:
                continue
            if line_no >= NETWORK_EVSES_END:
                break
            line = line.rstrip("\n")
            if line == "\\.":
                break
            parts = line.split("\t")
            if len(parts) == 2:
                network_id, evse_id = parts
                evse_to_network[evse_id] = network_id

    print(f"Parsed {len(evse_to_network)} network-EVSE links")

    # 4. Parse networks (for city/country info)
    networks = {}  # network_id -> {city, country, zip_code, is_deleted}
    with open(SQL_DUMP, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if line_no < NETWORKS_START:
                continue
            if line_no > NETWORKS_END:
                break
            line = line.rstrip("\n")
            if line == "\\.":
                break
            fields = line.split("\t")
            if len(fields) != len(NETWORK_COLUMNS):
                continue
            row = dict(zip(NETWORK_COLUMNS, fields))

            if pg_bool(row["is_deleted"]):
                continue

            city = normalize_city(pg_val(row["city"]) or "")
            country = (pg_val(row["country"]) or "").strip()

            if is_junk_city(city):
                continue

            networks[row["id"]] = {
                "city": city,
                "country": country,
                "zip_code": pg_val(row["zip_code"]) or "",
            }

    print(f"Parsed {len(networks)} active networks")

    # 5. Map each charger to its Gruppo Prodotto and city
    #    Serial format: YYCCCCNNNNN where CCCC is the 4-char product prefix
    city_chargers = defaultdict(lambda: defaultdict(int))
    # Also track per (city, country) -> zip_code for geocoding
    city_meta = {}
    unmatched_prefixes = defaultdict(int)
    total_mapped = 0
    total_no_network = 0
    total_no_prefix = 0

    for evse_id, serial in evses.items():
        # Find the network for this EVSE
        network_id = evse_to_network.get(evse_id)
        if not network_id or network_id not in networks:
            total_no_network += 1
            continue

        net = networks[network_id]
        city = net["city"]
        country = net["country"]
        key = (city, country)

        # Extract product prefix (chars 3-6 of serial, 0-indexed: 2:6)
        if len(serial) >= 6:
            prefix = serial[2:6]
        else:
            prefix = serial
            total_no_prefix += 1
            continue

        group = prefix_map.get(prefix)
        if not group:
            unmatched_prefixes[prefix] += 1
            group = "Altro"

        city_chargers[key][group] += 1
        total_mapped += 1

        if key not in city_meta:
            city_meta[key] = net["zip_code"]

    print(f"\nMapping results:")
    print(f"  Chargers mapped to city+group: {total_mapped}")
    print(f"  No network found: {total_no_network}")
    print(f"  No valid prefix: {total_no_prefix}")
    if unmatched_prefixes:
        print(f"  Unmatched prefixes:")
        for p, c in sorted(unmatched_prefixes.items(), key=lambda x: -x[1]):
            print(f"    {p}: {c}")

    # 6. Build chargers_by_city list
    by_city = []
    for (city, country), groups in sorted(
        city_chargers.items(), key=lambda x: -sum(x[1].values())
    ):
        total = sum(groups.values())
        by_city.append({
            "city": city,
            "country": country,
            "zip_code": city_meta.get((city, country), ""),
            "total_chargers": total,
            "groups": dict(sorted(groups.items(), key=lambda x: -x[1])),
        })

    out_path = os.path.join(OUTPUT_DIR, "chargers_by_city.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(by_city, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(by_city)} city records to {out_path}")

    # 7. Build chargers_summary
    global_groups = defaultdict(int)
    country_counts = defaultdict(int)
    total_chargers = 0

    for (city, country), groups in city_chargers.items():
        for group, count in groups.items():
            global_groups[group] += count
            total_chargers += count
        country_counts[country] += sum(groups.values())

    summary = {
        "total_chargers": total_chargers,
        "total_cities": len(by_city),
        "groups": dict(sorted(global_groups.items(), key=lambda x: -x[1])),
        "countries": dict(sorted(country_counts.items(), key=lambda x: -x[1])),
    }

    summary_path = os.path.join(OUTPUT_DIR, "chargers_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
