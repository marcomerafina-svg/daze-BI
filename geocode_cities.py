#!/usr/bin/env python3
"""Geocode cities from networks data and generate dashboard-ready JSON."""
import json
import hashlib
import os
import time
import requests

DATA_DIR = "/home/user/daze-BI/dashboard/data"
CACHE_FILE = os.path.join(DATA_DIR, "geocode_cache.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "networks_geocoded.json")

# Italian province centroids by ZIP prefix (first 2 digits)
IT_PROVINCES = {
    "00": (41.90, 12.50), "01": (42.42, 12.11), "02": (42.40, 12.86),
    "03": (41.63, 13.35), "04": (41.47, 13.07), "05": (42.72, 12.11),
    "06": (43.11, 12.39), "07": (40.73, 8.56), "08": (40.32, 9.33),
    "09": (39.22, 9.12), "10": (45.07, 7.69), "11": (45.74, 7.32),
    "12": (44.39, 7.55), "13": (45.57, 8.05), "14": (44.90, 8.21),
    "15": (44.91, 8.61), "16": (44.41, 8.93), "17": (44.31, 8.48),
    "18": (43.82, 7.78), "19": (44.11, 9.82), "20": (45.46, 9.19),
    "21": (45.82, 8.83), "22": (45.81, 9.08), "23": (46.17, 9.88),
    "24": (45.69, 9.67), "25": (45.54, 10.21), "26": (45.13, 9.69),
    "27": (45.18, 9.16), "28": (45.44, 8.62), "29": (45.05, 9.69),
    "30": (45.44, 12.32), "31": (45.67, 12.24), "32": (46.41, 12.13),
    "33": (46.07, 13.23), "34": (45.65, 13.77), "35": (45.41, 11.88),
    "36": (45.55, 11.55), "37": (45.44, 10.99), "38": (46.07, 11.12),
    "39": (46.50, 11.35), "40": (44.49, 11.34), "41": (44.65, 10.92),
    "42": (44.70, 10.63), "43": (44.80, 10.33), "44": (44.84, 11.62),
    "45": (44.96, 12.07), "46": (45.16, 10.79), "47": (44.22, 12.40),
    "48": (44.42, 12.20), "49": (44.06, 12.57), "50": (43.77, 11.25),
    "51": (43.93, 10.91), "52": (43.46, 11.88), "53": (43.32, 11.33),
    "54": (44.03, 10.00), "55": (43.84, 10.50), "56": (43.72, 10.40),
    "57": (42.76, 10.31), "58": (42.76, 11.11), "59": (43.88, 11.10),
    "60": (43.62, 13.52), "61": (43.85, 12.90), "62": (43.30, 13.45),
    "63": (42.85, 13.57), "64": (42.66, 13.70), "65": (42.46, 14.21),
    "66": (42.35, 14.17), "67": (42.35, 13.40), "68": (42.19, 13.52),
    "69": (42.50, 14.14), "70": (41.13, 16.87), "71": (41.46, 15.55),
    "72": (40.63, 17.94), "73": (40.35, 18.17), "74": (40.48, 17.23),
    "75": (40.66, 16.60), "76": (41.23, 16.28), "80": (40.85, 14.27),
    "81": (41.07, 14.33), "82": (41.13, 14.78), "83": (40.91, 14.79),
    "84": (40.68, 14.77), "85": (40.64, 15.81), "86": (41.56, 14.67),
    "87": (39.30, 16.25), "88": (38.91, 16.59), "89": (38.11, 15.64),
    "90": (38.12, 13.36), "91": (37.97, 12.76), "92": (37.31, 13.58),
    "93": (37.49, 14.07), "94": (37.57, 14.27), "95": (37.50, 15.09),
    "96": (37.07, 15.29), "97": (36.93, 14.73), "98": (38.19, 15.55),
}

# Spanish province centroids by ZIP prefix
ES_PROVINCES = {
    "01": (42.85, -2.67), "02": (38.99, -1.86), "03": (38.35, -0.48),
    "04": (36.83, -2.46), "05": (40.66, -4.68), "06": (38.88, -6.97),
    "07": (39.57, 2.65), "08": (41.39, 2.17), "09": (42.34, -3.70),
    "10": (39.47, -6.37), "11": (36.53, -6.28), "12": (39.99, -0.03),
    "13": (38.99, -3.93), "14": (37.88, -4.77), "15": (43.37, -8.40),
    "16": (40.07, -2.13), "17": (41.97, 2.82), "18": (37.18, -3.60),
    "19": (40.63, -3.17), "20": (43.32, -1.98), "21": (37.26, -6.95),
    "22": (42.14, -0.41), "23": (37.77, -3.79), "24": (42.60, -5.57),
    "25": (41.62, 0.62), "26": (42.47, -2.44), "27": (43.01, -7.56),
    "28": (40.42, -3.70), "29": (36.72, -4.42), "30": (37.99, -1.13),
    "31": (42.82, -1.64), "32": (42.34, -7.86), "33": (43.36, -5.85),
    "34": (42.01, -4.53), "35": (28.10, -15.42), "36": (42.43, -8.64),
    "37": (40.97, -5.66), "38": (28.47, -16.25), "39": (43.46, -3.80),
    "40": (40.95, -4.12), "41": (37.39, -5.99), "42": (41.76, -2.47),
    "43": (41.12, 1.25), "44": (40.34, -1.11), "45": (39.86, -4.03),
    "46": (39.47, -0.38), "47": (41.65, -4.72), "48": (43.26, -2.92),
    "49": (41.50, -5.75), "50": (41.65, -0.88), "51": (35.89, -5.32),
    "52": (35.29, -2.94),
}

# French department centroids by ZIP prefix
FR_DEPARTMENTS = {
    "01": (46.21, 5.23), "02": (49.56, 3.62), "03": (46.34, 3.18),
    "04": (44.09, 6.24), "05": (44.66, 6.26), "06": (43.70, 7.27),
    "07": (44.74, 4.60), "08": (49.77, 4.63), "09": (42.93, 1.51),
    "10": (48.30, 4.08), "11": (43.21, 2.35), "12": (44.35, 2.58),
    "13": (43.30, 5.37), "14": (49.18, -0.37), "15": (45.03, 2.67),
    "16": (45.65, 0.16), "17": (45.75, -0.80), "18": (47.08, 2.40),
    "19": (45.27, 1.77), "20": (42.04, 9.01), "21": (47.32, 4.77),
    "22": (48.51, -2.76), "23": (46.08, 2.03), "24": (45.19, 0.72),
    "25": (47.24, 6.02), "26": (44.56, 5.05), "27": (49.09, 1.15),
    "28": (48.45, 1.49), "29": (48.39, -4.49), "30": (44.13, 4.08),
    "31": (43.60, 1.44), "32": (43.65, 0.59), "33": (44.84, -0.58),
    "34": (43.61, 3.88), "35": (48.11, -1.68), "36": (46.81, 1.69),
    "37": (47.39, 0.69), "38": (45.19, 5.72), "39": (46.67, 5.55),
    "40": (43.89, -0.50), "41": (47.59, 1.33), "42": (45.44, 4.39),
    "43": (45.04, 3.88), "44": (47.22, -1.55), "45": (47.90, 2.17),
    "46": (44.45, 1.44), "47": (44.23, 0.62), "48": (44.52, 3.50),
    "49": (47.47, -0.56), "50": (48.89, -1.25), "51": (49.04, 3.95),
    "52": (48.11, 5.14), "53": (48.07, -0.77), "54": (48.69, 6.18),
    "55": (49.16, 5.38), "56": (47.66, -2.76), "57": (49.12, 6.18),
    "58": (47.10, 3.50), "59": (50.63, 3.06), "60": (49.42, 2.42),
    "61": (48.43, 0.09), "62": (50.43, 2.83), "63": (45.78, 3.08),
    "64": (43.30, -0.37), "65": (43.23, 0.15), "66": (42.70, 2.90),
    "67": (48.58, 7.75), "68": (47.75, 7.34), "69": (45.76, 4.84),
    "70": (47.62, 6.16), "71": (46.80, 4.45), "72": (47.80, 0.20),
    "73": (45.56, 6.39), "74": (46.07, 6.41), "75": (48.86, 2.35),
    "76": (49.44, 1.10), "77": (48.54, 2.66), "78": (48.80, 2.13),
    "79": (46.32, -0.46), "80": (49.89, 2.30), "81": (43.90, 2.15),
    "82": (44.02, 1.36), "83": (43.46, 6.22), "84": (43.95, 5.05),
    "85": (46.67, -1.43), "86": (46.58, 0.34), "87": (45.85, 1.25),
    "88": (48.17, 6.45), "89": (47.80, 3.57), "90": (47.64, 6.86),
    "91": (48.63, 2.44), "92": (48.83, 2.25), "93": (48.91, 2.48),
    "94": (48.79, 2.47), "95": (49.08, 2.17), "97": (14.64, -61.02),
}

# Portuguese district centroids
PT_DISTRICTS = {
    "10": (38.72, -9.14), "11": (38.72, -9.14), "12": (38.72, -9.14),
    "13": (38.72, -9.14), "14": (38.72, -9.14), "15": (38.72, -9.14),
    "19": (38.72, -9.14),
    "20": (38.57, -7.91), "21": (38.57, -7.91),
    "23": (39.29, -8.07), "24": (39.46, -8.20), "25": (39.75, -8.81),
    "26": (39.60, -8.41),
    "30": (40.21, -8.43), "31": (40.21, -8.43), "32": (40.63, -8.65),
    "33": (40.66, -7.91), "34": (40.66, -7.91),
    "38": (41.15, -8.61), "39": (41.15, -8.61), "40": (41.15, -8.61),
    "41": (41.15, -8.61), "42": (41.15, -8.61), "43": (41.15, -8.61),
    "44": (41.15, -8.61), "45": (41.15, -8.61),
    "47": (41.55, -8.42), "48": (41.70, -8.83), "49": (41.70, -8.83),
    "50": (41.30, -7.74), "51": (41.81, -6.76),
    "60": (40.53, -7.27), "62": (40.53, -7.27), "63": (40.08, -7.50),
    "80": (37.02, -7.93), "90": (38.57, -8.91),
}

# Country centroids fallback
COUNTRY_CENTROIDS = {
    "Italy": (42.50, 12.50), "Spain": (40.00, -3.70),
    "France": (46.60, 2.30), "Portugal": (39.40, -8.22),
    "Switzerland": (46.80, 8.23), "Greece": (39.07, 21.82),
    "Poland": (51.92, 19.15), "Slovenia": (46.15, 14.99),
    "Hungary": (47.16, 19.50), "Czechia": (49.82, 15.47),
    "Belgium": (50.85, 4.35), "Germany": (51.17, 10.45),
    "Morocco": (31.79, -7.09), "Afghanistan": (33.94, 67.71),
    "Tunisia": (33.89, 9.54), "Costa Rica": (9.93, -84.09),
    "Austria": (47.52, 14.55), "Sweden": (60.13, 18.64),
    "San Marino": (43.94, 12.46), "Bulgaria": (42.73, 25.49),
    "Slovakia": (48.67, 19.70), "Romania": (45.94, 24.97),
    "Finland": (61.92, 25.75), "Denmark": (56.26, 9.50),
    "Moldova": (47.41, 28.37), "Lithuania": (55.17, 23.88),
    "Cyprus": (35.13, 33.43), "Croatia": (45.10, 15.20),
    "Ivory Coast": (7.54, -5.55), "Netherlands": (52.13, 5.29),
    "United Arab Emirates": (23.42, 53.85), "Anguilla": (18.22, -63.07),
    "Guadeloupe": (16.27, -61.55), "United Kingdom": (55.38, -3.44),
    "Venezuela": (6.42, -66.59), "Luxembourg": (49.82, 6.13),
    "Ukraine": (48.38, 31.17), "Martinique": (14.64, -61.02),
    "Ecuador": (-1.83, -78.18), "Turkey": (38.96, 35.24),
    "Albania": (41.15, 20.17), "Serbia": (44.02, 21.01),
    "Monaco": (43.74, 7.42), "Angola": (-11.20, 17.87),
    "American Samoa": (-14.27, -170.70),
}

# Nominatim geocoding cache
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def nominatim_geocode(city, country):
    """Geocode using Nominatim API (1 req/sec rate limit)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "city": city,
        "country": country,
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": "DazeBI-Dashboard/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        print(f"  Nominatim error for {city}, {country}: {e}")
    return None

def city_jitter(city_name, base_lat, base_lng):
    """Deterministic small offset based on city name hash."""
    h = int(hashlib.md5(city_name.encode()).hexdigest()[:8], 16)
    dlat = ((h % 1000) - 500) / 5000.0  # ±0.1 degrees
    dlng = (((h >> 12) % 1000) - 500) / 5000.0
    return base_lat + dlat, base_lng + dlng

def geocode_city(city, country, zip_code, cache):
    """Try to geocode a city using multiple strategies."""
    cache_key = f"{city}|{country}"

    # 1. Check cache
    if cache_key in cache:
        return cache[cache_key]

    # 2. Zip-code based geocoding for Italy, Spain, France, Portugal
    zip_prefix = zip_code[:2] if zip_code and len(zip_code) >= 2 else None

    if country == "Italy" and zip_prefix and zip_prefix in IT_PROVINCES:
        lat, lng = IT_PROVINCES[zip_prefix]
        result = list(city_jitter(city, lat, lng))
        cache[cache_key] = result
        return result

    if country == "Spain" and zip_prefix and zip_prefix in ES_PROVINCES:
        lat, lng = ES_PROVINCES[zip_prefix]
        result = list(city_jitter(city, lat, lng))
        cache[cache_key] = result
        return result

    if country == "France" and zip_prefix and zip_prefix in FR_DEPARTMENTS:
        lat, lng = FR_DEPARTMENTS[zip_prefix]
        result = list(city_jitter(city, lat, lng))
        cache[cache_key] = result
        return result

    if country == "Portugal" and zip_prefix and zip_prefix in PT_DISTRICTS:
        lat, lng = PT_DISTRICTS[zip_prefix]
        result = list(city_jitter(city, lat, lng))
        cache[cache_key] = result
        return result

    # 3. Country centroid with jitter
    if country in COUNTRY_CENTROIDS:
        lat, lng = COUNTRY_CENTROIDS[country]
        result = list(city_jitter(city, lat, lng))
        cache[cache_key] = result
        return result

    return None

def main():
    # Load input data
    with open(os.path.join(DATA_DIR, "networks_by_city.json"), "r") as f:
        cities = json.load(f)

    cache = load_cache()
    total = len(cities)
    geocoded = []
    nominatim_count = 0
    nominatim_limit = 150  # Limit API calls

    print(f"Processing {total} cities...")

    # First pass: geocode top cities via Nominatim for best accuracy
    top_cities = sorted(cities, key=lambda c: c["count"], reverse=True)[:nominatim_limit]
    for i, city_data in enumerate(top_cities):
        cache_key = f"{city_data['city']}|{city_data['country']}"
        if cache_key not in cache:
            print(f"  [{i+1}/{nominatim_limit}] Nominatim: {city_data['city']}, {city_data['country']}...")
            coords = nominatim_geocode(city_data["city"], city_data["country"])
            if coords:
                cache[cache_key] = list(coords)
                nominatim_count += 1
            time.sleep(1.1)  # Rate limit

    save_cache(cache)
    print(f"  Nominatim geocoded {nominatim_count} new cities")

    # Second pass: geocode all cities (cache + zip-based + centroid fallback)
    skipped = 0
    for city_data in cities:
        coords = geocode_city(
            city_data["city"], city_data["country"],
            city_data["zip_code"], cache
        )
        if coords:
            geocoded.append({
                **city_data,
                "lat": round(coords[0], 4),
                "lng": round(coords[1], 4),
            })
        else:
            skipped += 1

    save_cache(cache)

    print(f"Geocoded: {len(geocoded)}, Skipped: {skipped}")

    # Sort by count descending
    geocoded.sort(key=lambda c: c["count"], reverse=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(geocoded, f, indent=2)

    print(f"Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
