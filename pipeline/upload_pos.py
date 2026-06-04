#!/usr/bin/env python3
"""
Upload POS transactions from CSV to the Intelligence API.
"""
import os
import sys
import csv
import json
import argparse
import requests
from datetime import datetime, timezone

def upload_pos_data(csv_path: str, api_url: str, api_key: str):
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)

    transactions = []
    
    print(f"Reading {csv_path}...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Expected headers: store_id, transaction_id, timestamp, basket_value_inr
        for row in reader:
            # Handle potential BOM or whitespace in keys
            row = {k.strip(): v.strip() for k, v in row.items()}
            
            # Use fallback keys if exact headers aren't perfect
            store_id = row.get("store_id")
            transaction_id = row.get("transaction_id")
            timestamp = row.get("timestamp")
            basket_value = row.get("basket_value_inr")
            
            if not all([store_id, transaction_id, timestamp, basket_value]):
                continue
                
            try:
                # Validate date format (ensure it is ISO or parseable)
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts_iso = dt.isoformat()
            except Exception:
                ts_iso = timestamp # let pydantic try
                
            transactions.append({
                "transaction_id": transaction_id,
                "store_id": store_id,
                "timestamp": ts_iso,
                "basket_value_inr": float(basket_value)
            })

    if not transactions:
        print("No valid transactions found in CSV.")
        sys.exit(1)

    print(f"Parsed {len(transactions)} transactions. Uploading to {api_url}/pos/ingest")
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    # Batch into chunks of 500
    chunk_size = 500
    total_accepted = 0
    total_rejected = 0
    
    for i in range(0, len(transactions), chunk_size):
        chunk = transactions[i:i+chunk_size]
        payload = {"transactions": chunk}
        
        try:
            resp = requests.post(f"{api_url}/pos/ingest", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                total_accepted += data.get("accepted", 0)
                total_rejected += data.get("rejected", 0)
                errors = data.get("errors", [])
                if errors:
                    print(f"Batch {i//chunk_size + 1} completed with errors: {errors[:2]}...")
            else:
                print(f"Batch {i//chunk_size + 1} failed with status {resp.status_code}: {resp.text}")
                total_rejected += len(chunk)
        except Exception as e:
            print(f"Request failed: {e}")
            total_rejected += len(chunk)
            
    print(f"\nUpload complete.")
    print(f"Accepted: {total_accepted}")
    print(f"Rejected: {total_rejected}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload POS transactions to API")
    parser.add_argument("--csv", type=str, required=True, help="Path to pos_transactions.csv")
    parser.add_argument("--url", type=str, default=os.getenv("API_URL", "http://localhost:8000"), help="API base URL")
    parser.add_argument("--key", type=str, default=os.getenv("API_KEY", "test_key_1"), help="API Key")
    
    args = parser.parse_args()
    upload_pos_data(args.csv, args.url, args.key)
