#!/usr/bin/env python3
"""Build a self-contained HTML dashboard with embedded data."""
import json
import os

DATA_DIR = "/home/user/daze-BI/dashboard/data"
TEMPLATE = "/home/user/daze-BI/dashboard/index.html"
OUTPUT = "/home/user/daze-BI/dashboard/daze-dashboard.html"

# Load all data
with open(os.path.join(DATA_DIR, "networks_compact.json")) as f:
    net_compact = json.dumps(json.load(f), separators=(',', ':'))

with open(os.path.join(DATA_DIR, "summary.json")) as f:
    net_summary = json.dumps(json.load(f), separators=(',', ':'))

with open(os.path.join(DATA_DIR, "chargers_compact.json")) as f:
    chg_compact = json.dumps(json.load(f), separators=(',', ':'))

with open(os.path.join(DATA_DIR, "chargers_summary.json")) as f:
    chg_summary = json.dumps(json.load(f), separators=(',', ':'))

# Read template
with open(TEMPLATE) as f:
    html = f.read()

# Replace the fetch-based init with embedded data
old_init = """async function init() {
  try {
    const [netRes, netSumRes, chgRes, chgSumRes] = await Promise.all([
      fetch('data/networks_compact.json'),
      fetch('data/summary.json'),
      fetch('data/chargers_compact.json'),
      fetch('data/chargers_summary.json')
    ]);
    NET_DATA = await netRes.json();
    NET_SUMMARY = await netSumRes.json();
    CHG_DATA = await chgRes.json();
    CHG_SUMMARY = await chgSumRes.json();
  } catch(e) {
    console.error('Failed to load data:', e);
    // Fallback for networks only
    try {
      const res = await fetch('data/networks_geocoded.json');
      const full = await res.json();
      NET_DATA = full.map(c => [
        c.lat, c.lng, c.count, c.city, c.country,
        c.avg_power_kw || 0, c.photovoltaic_count || 0,
        c.three_phase_count || 0, c.first_created || '',
        c.network_types || {}
      ]);
      const sumRes2 = await fetch('data/summary.json');
      NET_SUMMARY = await sumRes2.json();
    } catch(e2) {
      console.error('Failed to load fallback data:', e2);
    }
  }

  initMap();
  renderKPIs();
  renderCountryList();
  renderFilters();
  renderMarkers();
  setupSearch();
  setupSidebar();
  setupViewToggle();

  setTimeout(() => document.getElementById('loading').classList.add('hidden'), 600);
}"""

new_init = f"""async function init() {{
  // Data embedded directly - no server needed
  NET_DATA = {net_compact};
  NET_SUMMARY = {net_summary};
  CHG_DATA = {chg_compact};
  CHG_SUMMARY = {chg_summary};

  initMap();
  renderKPIs();
  renderCountryList();
  renderFilters();
  renderMarkers();
  setupSearch();
  setupSidebar();
  setupViewToggle();

  setTimeout(() => document.getElementById('loading').classList.add('hidden'), 600);
}}"""

html = html.replace(old_init, new_init)

with open(OUTPUT, "w") as f:
    f.write(html)

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"Dashboard generata: {OUTPUT}")
print(f"Dimensione: {size_kb:.0f} KB")
print(f"Apri direttamente nel browser con doppio click!")
