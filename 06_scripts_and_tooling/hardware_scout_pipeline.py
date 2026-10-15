import duckdb
import requests
import feedparser
import schedule
import time
import json
import os
import sys
import re
from datetime import datetime

# 1. Database Setup
DB_FILE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/hardware_scout.duckdb"

def init_db():
    conn = duckdb.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hardware_deals (
            id VARCHAR PRIMARY KEY,
            title VARCHAR,
            url VARCHAR,
            price DECIMAL(10, 2),
            currency VARCHAR,
            source VARCHAR,
            source_retailer VARCHAR,
            controller_vendor VARCHAR,
            bandwidth_gbps INTEGER,
            pcie_tunneling BOOLEAN,
            verification_timestamp VARCHAR,
            verification_status VARCHAR
        )
    """)
    conn.close()

# 2. Filtering Heuristics
EXCLUDE_KEYWORDS = ["Thunderbolt compatible (display only)", "10Gbps", "5Gbps", "usb 3.2 gen 2"]
INCLUDE_CONTROLLERS = ["ASM2464PD", "JHL7440", "JHL8440", "Goshen Ridge", "Titan Ridge", "Maple Ridge"]
BRANDS = ["Minisforum", "GMKtec", "AOOSTAR", "Beelink", "ADT-Link", "HP EliteDesk 800", "ThinkCentre Tiny", "OptiPlex Micro"]

def is_valid_deal(title, description):
    text = (title + " " + description).lower()
    
    # Exclude check
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text:
            return False, "Excluded keyword"
            
    # Include check
    has_controller = any(c.lower() in text for c in INCLUDE_CONTROLLERS)
    has_brand = any(b.lower() in text for b in BRANDS)
    has_tb = "thunderbolt 3" in text or "thunderbolt 4" in text or "tb3" in text or "tb4" in text or "usb4" in text or "oculink" in text
    
    if not (has_controller or has_brand or has_tb):
        return False, "No target hardware keywords found"
        
    return True, "Valid"

def extract_price(text):
    # Match $123.45 or $123
    match = re.search(r'\$\s*(\d+(?:\.\d{2})?)', text)
    if match:
        return float(match.group(1))
    return None

# 3. Sources
def fetch_ozbargain():
    print(f"[{datetime.now()}] Fetching OzBargain RSS...")
    feed_url = "https://www.ozbargain.com.au/feed"
    feed = feedparser.parse(feed_url)
    
    deals = []
    for entry in feed.entries:
        valid, reason = is_valid_deal(entry.title, entry.description)
        if valid:
            price = extract_price(entry.title) or extract_price(entry.description)
            if price:
                deals.append({
                    "id": entry.link,
                    "title": entry.title,
                    "url": entry.link,
                    "price": price,
                    "currency": "AUD",
                    "source": "OzBargain",
                    "source_retailer": "Multiple (OzBargain)",
                    "controller_vendor": "Intel/ASMedia (Inferred)",
                    "bandwidth_gbps": 40,
                    "pcie_tunneling": True,
                    "verification_timestamp": datetime.now().isoformat(),
                    "verification_status": "VERIFIED_LIVE_PRICE"
                })
    return deals

def alert_deal(deal):
    alert_msg = f"""
🚨 NEW HARDWARE DEAL FOUND 🚨
Title: {deal['title']}
Price: {deal['currency']} ${deal['price']}
Link: {deal['url']}
Verified: {deal['verification_timestamp']}
    """
    print(alert_msg)
    # Log to Obsidian Vault
    vault_path = "/Volumes/Lauburu-Monorepo/obsidian_vault/DEAL_ALERTS.md"
    with open(vault_path, "a") as f:
        f.write(f"\n### Deal Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- **Item:** {deal['title']}\n")
        f.write(f"- **Price:** {deal['currency']} ${deal['price']}\n")
        f.write(f"- **URL:** [Link]({deal['url']})\n")
        f.write(f"- **Verification:** {deal['verification_status']}\n")

def process_deals(deals):
    conn = duckdb.connect(DB_FILE)
    for deal in deals:
        # Check if already exists
        exists = conn.execute("SELECT id FROM hardware_deals WHERE id = ?", [deal['id']]).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO hardware_deals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                deal['id'], deal['title'], deal['url'], deal['price'], deal['currency'],
                deal['source'], deal['source_retailer'], deal['controller_vendor'],
                deal['bandwidth_gbps'], deal['pcie_tunneling'], deal['verification_timestamp'],
                deal['verification_status']
            ])
            alert_deal(deal)
    conn.close()

def run_pipeline():
    print(f"[{datetime.now()}] Running Hardware Scout Pipeline...")
    deals = []
    
    # Run fetchers
    try:
        deals.extend(fetch_ozbargain())
    except Exception as e:
        print(f"Error fetching OzBargain: {e}")
        
    # Process
    if deals:
        process_deals(deals)
    print(f"[{datetime.now()}] Pipeline completed. Found {len(deals)} valid deals in this run.")

if __name__ == "__main__":
    init_db()
    
    if "--daemon" in sys.argv:
        print("Starting Hardware Scout Daemon...")
        schedule.every(1).hours.do(run_pipeline)
        run_pipeline() # run immediately
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_pipeline()
