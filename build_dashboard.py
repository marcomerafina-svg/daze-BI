#!/usr/bin/env python3
"""Build a self-contained HTML dashboard with embedded data."""
import json
import os

DATA_DIR = "/home/user/daze-BI/dashboard/data"
TEMPLATE = "/home/user/daze-BI/dashboard/index.html"
OUTPUT = "/home/user/daze-BI/dashboard/daze-dashboard.html"

# Load data
with open(os.path.join(DATA_DIR, "networks_compact.json")) as f:
    compact = json.dumps(json.load(f), separators=(',', ':'))

with open(os.path.join(DATA_DIR, "summary.json")) as f:
    summary = json.dumps(json.load(f), separators=(',', ':'))

# Read template
with open(TEMPLATE) as f:
    html = f.read()

# Replace the fetch-based init with embedded data
old_init = """async function init() {
  try {
    const [geoRes, sumRes] = await Promise.all([
      fetch('data/networks_compact.json'),
      fetch('data/summary.json')
    ]);
    RAW_DATA = await geoRes.json();
    SUMMARY = await sumRes.json();
  } catch(e) {
    // Fallback: try loading full geocoded data
    try {
      const res = await fetch('data/networks_geocoded.json');
      const full = await res.json();
      RAW_DATA = full.map(c => [
        c.lat, c.lng, c.count, c.city, c.country,
        c.avg_power_kw || 0, c.photovoltaic_count || 0,
        c.three_phase_count || 0, c.first_created || '',
        c.network_types || {}
      ]);
      const sumRes2 = await fetch('data/summary.json');
      SUMMARY = await sumRes2.json();
    } catch(e2) {
      console.error('Failed to load data:', e2);
    }
  }

  initMap();
  renderKPIs();
  renderCountryList();
  renderFilters();
  renderMarkers();
  setupSearch();
  setupSidebar();

  setTimeout(() => document.getElementById('loading').classList.add('hidden'), 600);
}"""

new_init = f"""async function init() {{
  // Data embedded directly - no server needed
  RAW_DATA = {compact};
  SUMMARY = {summary};

  initMap();
  renderKPIs();
  renderCountryList();
  renderFilters();
  renderMarkers();
  setupSearch();
  setupSidebar();

  setTimeout(() => document.getElementById('loading').classList.add('hidden'), 600);
}}"""

html = html.replace(old_init, new_init)

with open(OUTPUT, "w") as f:
    f.write(html)

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"Dashboard generata: {OUTPUT}")
print(f"Dimensione: {size_kb:.0f} KB")
print(f"Apri direttamente nel browser con doppio click!")
