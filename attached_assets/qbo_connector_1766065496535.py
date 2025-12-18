import streamlit as st
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

load_dotenv()

# --- CONFIG ---
CLIENT_ID = os.getenv("QBO_CLIENT_ID")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("QBO_REDIRECT_URI")
ENV = os.getenv("QBO_ENVIRONMENT", "production") 

DB_NAME = "close_data.db"

if not CLIENT_ID or not CLIENT_SECRET:
    st.error("❌ Missing QBO Keys in .env file.")

def get_auth_client():
    return AuthClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        environment=ENV,
    )

def get_auth_url():
    client = get_auth_client()
    return client.get_authorization_url([Scopes.ACCOUNTING])

def handle_callback(auth_code, realm_id):
    client = get_auth_client()
    client.get_bearer_token(auth_code, realm_id=realm_id)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM qbo_tokens") 
    cursor.execute("""
        INSERT INTO qbo_tokens (realm_id, access_token, refresh_token)
        VALUES (?, ?, ?)
    """, (realm_id, client.access_token, client.refresh_token))
    conn.commit()
    conn.close()

def get_active_client():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT realm_id, access_token, refresh_token FROM qbo_tokens LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row: return None

    realm_id, access_token, refresh_token = row
    client = get_auth_client()
    client.access_token = access_token
    client.refresh_token = refresh_token
    client.realm_id = realm_id

    try:
        client.refresh()
        conn = sqlite3.connect(DB_NAME)
        conn.execute("UPDATE qbo_tokens SET access_token=?, refresh_token=?", 
                     (client.access_token, client.refresh_token))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Token Refresh Failed: {e}")
        return None

    return client

def call_qbo_api(url, headers, params):
    """Helper to make the request and return JSON."""
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        st.error(f"🛑 QBO API Error ({response.status_code}): {response.text}")
        return None
    return response.json()

def parse_report_to_dict(json_data):
    """Parses TB JSON into a simple dict: { 'AcctNum': {'name': 'X', 'balance': 100.0} }"""
    data_map = {}
    rows = json_data.get("Rows", {}).get("Row", [])

    for row in rows:
        if "ColData" in row and "type" not in row:
            acct_str = row["ColData"][0]["value"] 
            acct_parts = acct_str.split(" ", 1)

            if len(acct_parts) > 1 and acct_parts[0].isdigit():
                acct_num = acct_parts[0]
                acct_name = acct_parts[1]

                # QBO Returns Abs Value in Col 1 (Debit) and Col 2 (Credit)
                debit = float(row["ColData"][1]["value"].replace(",", "") or 0)
                credit = float(row["ColData"][2]["value"].replace(",", "") or 0)

                # Standard Accounting Net (Dr - Cr)
                net_bal = debit - credit

                data_map[acct_num] = {
                    'name': acct_name,
                    'balance': net_bal
                }
    return data_map

def fetch_trial_balance(date_str):
    """
    Fetches Monthly Activity by calculating the delta between 
    Current Month YTD and Prior Month YTD for P&L accounts.
    """
    client = get_active_client()
    if not client: return None

    base_url = "https://sandbox-quickbooks.api.intuit.com" if ENV == 'sandbox' else "https://quickbooks.api.intuit.com"
    url = f"{base_url}/v3/company/{client.realm_id}/reports/TrialBalance"
    headers = {"Authorization": f"Bearer {client.access_token}", "Accept": "application/json"}

    # Calculate Dates
    dt_curr = datetime.strptime(date_str, "%Y-%m-%d")

    # Fiscal Year Start (Jan 1 of the requested year)
    # This ensures we get true "YTD" balances for P&L logic
    fy_start_str = dt_curr.replace(month=1, day=1).strftime("%Y-%m-%d")

    # 1. Fetch CURRENT Month End (YTD: Jan 1 -> Nov 30)
    # ------------------------------------------------
    params_curr = {
        "start_date": fy_start_str,
        "end_date": date_str, 
        "minorversion": 65
    }
    print(f"DEBUG: Fetching Current YTD ({fy_start_str} to {date_str})")
    data_curr_json = call_qbo_api(url, headers, params_curr)
    if not data_curr_json: return None

    map_curr = parse_report_to_dict(data_curr_json)

    # 2. Fetch PRIOR Month End (YTD: Jan 1 -> Oct 31)
    # ------------------------------------------------
    # Go to first day of current month, then subtract 1 day
    dt_prior = dt_curr.replace(day=1) - timedelta(days=1)
    prior_date_str = dt_prior.strftime("%Y-%m-%d")

    map_prior = {}

    # Only fetch prior if we are NOT in January
    if dt_curr.month > 1:
        print(f"DEBUG: Fetching Prior YTD ({fy_start_str} to {prior_date_str})")
        params_prior = {
            "start_date": fy_start_str,
            "end_date": prior_date_str, 
            "minorversion": 65
        }
        data_prior_json = call_qbo_api(url, headers, params_prior)
        if data_prior_json:
            map_prior = parse_report_to_dict(data_prior_json)

    # 3. Calculate Delta (Monthly Activity)
    # ------------------------------------------------
    final_map = {}

    for acct_num, details in map_curr.items():
        curr_bal = details['balance']
        prior_bal = 0.0

        # Check if P&L (Account >= 40000)
        is_pnl = False
        try:
            if int(acct_num) >= 40000: is_pnl = True
        except: pass

        if is_pnl and dt_curr.month > 1:
            # Look up prior YTD balance
            if acct_num in map_prior:
                prior_bal = map_prior[acct_num]['balance']

            # Monthly Activity = (Nov YTD) - (Oct YTD)
            monthly_activity = curr_bal - prior_bal

            final_map[acct_num] = {
                'name': details['name'],
                'balance': monthly_activity
            }
        else:
            # Balance Sheet (Always use Ending Balance)
            # OR January P&L (YTD is correct)
            final_map[acct_num] = {
                'name': details['name'],
                'balance': curr_bal
            }

    return final_map