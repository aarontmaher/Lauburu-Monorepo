import os
import json
import csv
import requests
from datetime import datetime, timedelta

# Shopify GraphQL API configuration
SHOPIFY_STORE_URL = os.environ.get("SHOPIFY_STORE_URL", "your-store.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-01"

GRAPHQL_URL = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/graphql.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
}

ORDERS_QUERY = """
query getOrders($cursor: String) {
  orders(first: 250, after: $cursor, sortKey: CREATED_AT, reverse: false) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        createdAt
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        lineItems(first: 10) {
          edges {
            node {
              quantity
              variant {
                id
                sku
              }
            }
          }
        }
      }
    }
  }
}
"""

def fetch_all_orders():
    orders = []
    has_next = True
    cursor = None

    print(f"Fetching orders from {SHOPIFY_STORE_URL}...")
    
    while has_next:
        variables = {"cursor": cursor} if cursor else {}
        response = requests.post(GRAPHQL_URL, json={"query": ORDERS_QUERY, "variables": variables}, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code} - {response.text}")
            break
            
        data = response.json().get("data", {}).get("orders", {})
        if not data:
            break
            
        edges = data.get("edges", [])
        for edge in edges:
            orders.append(edge["node"])
            
        page_info = data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    print(f"Total orders fetched: {len(orders)}")
    return orders

def process_time_series_data(orders, output_file="shopify_time_series.csv"):
    """
    Processes raw orders into a daily aggregated time-series format suitable for TSFMs.
    Format: date, total_revenue, total_units_sold
    """
    daily_data = {}
    
    for order in orders:
        # Parse date and truncate to day
        created_at_raw = order.get("createdAt", "")
        if not created_at_raw:
            continue
            
        dt = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d')
        
        # Parse revenue
        revenue_str = order.get("totalPriceSet", {}).get("shopMoney", {}).get("amount", "0")
        try:
            revenue = float(revenue_str)
        except ValueError:
            revenue = 0.0
            
        # Parse units
        units = 0
        line_items = order.get("lineItems", {}).get("edges", [])
        for item in line_items:
            units += item.get("node", {}).get("quantity", 0)
            
        if date_str not in daily_data:
            daily_data[date_str] = {"revenue": 0.0, "units": 0}
            
        daily_data[date_str]["revenue"] += revenue
        daily_data[date_str]["units"] += units
        
    # Sort chronologically
    sorted_dates = sorted(daily_data.keys())
    
    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["date", "revenue", "units"])
        for d in sorted_dates:
            writer.writerow([d, round(daily_data[d]["revenue"], 2), daily_data[d]["units"]])
            
    print(f"Time series data exported to {output_file}")

if __name__ == "__main__":
    if not SHOPIFY_ACCESS_TOKEN:
        print("Warning: SHOPIFY_ACCESS_TOKEN is not set. The script will fail unless mocked.")
    
    # Example flow
    # orders = fetch_all_orders()
    # process_time_series_data(orders, output_file="shopify_ts_data.csv")
    print("Script ready. Run with valid credentials to extract Time Series Foundation Model dataset.")
