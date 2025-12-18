import streamlit as st
import os
import requests
import base64
from datetime import datetime, timedelta
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from cryptography.fernet import Fernet
from close_platform.db_config import get_connection

CLIENT_ID = os.getenv("QBO_CLIENT_ID")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET")
_raw_redirect = os.getenv("QBO_REDIRECT_URI", "")
REDIRECT_URI = _raw_redirect.rstrip("/") if _raw_redirect else ""
ENV = os.getenv("QBO_ENVIRONMENT", "production")

def _get_encryption_key():
    key = os.getenv("QBO_ENCRYPTION_KEY")
    if not key:
        raise ValueError("QBO_ENCRYPTION_KEY not configured. Add a Fernet key to secrets before connecting to QuickBooks.")
    if isinstance(key, str):
        key = key.encode()
    return key

def _has_encryption_key() -> bool:
    return bool(os.getenv("QBO_ENCRYPTION_KEY"))

def _encrypt_token(token: str) -> str:
    if not token:
        return ""
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(token.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def _decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        decoded = base64.urlsafe_b64decode(encrypted_token.encode())
        decrypted = f.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        print(f"Token decryption failed: {e}")
        return ""

def get_auth_client():
    if not CLIENT_ID or not CLIENT_SECRET:
        return None
    return AuthClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        environment=ENV,
    )

def get_auth_url():
    client = get_auth_client()
    if not client:
        return None
    return client.get_authorization_url([Scopes.ACCOUNTING])

def handle_callback(auth_code, realm_id):
    client = get_auth_client()
    if not client:
        raise Exception("QBO credentials not configured")
    client.get_bearer_token(auth_code, realm_id=realm_id)

    encrypted_access = _encrypt_token(client.access_token)
    encrypted_refresh = _encrypt_token(client.refresh_token)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM close_qbo_tokens")
    cursor.execute("""
        INSERT INTO close_qbo_tokens (realm_id, access_token, refresh_token, updated_at)
        VALUES (%s, %s, %s, %s)
    """, (realm_id, encrypted_access, encrypted_refresh, datetime.now()))
    conn.commit()
    conn.close()

def save_manual_tokens(realm_id, access_token, refresh_token):
    """Save manually obtained tokens from OAuth Playground."""
    encrypted_access = _encrypt_token(access_token.strip())
    encrypted_refresh = _encrypt_token(refresh_token.strip())

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM close_qbo_tokens")
    cursor.execute("""
        INSERT INTO close_qbo_tokens (realm_id, access_token, refresh_token, updated_at)
        VALUES (%s, %s, %s, %s)
    """, (realm_id.strip(), encrypted_access, encrypted_refresh, datetime.now()))
    conn.commit()
    conn.close()

def get_active_client():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT realm_id, access_token, refresh_token FROM close_qbo_tokens LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    client = get_auth_client()
    if not client:
        return None
    
    decrypted_access = _decrypt_token(row['access_token'])
    decrypted_refresh = _decrypt_token(row['refresh_token'])
    
    if not decrypted_access or not decrypted_refresh:
        print("Token decryption failed - tokens may be corrupted or key changed")
        return None
    
    client.access_token = decrypted_access
    client.refresh_token = decrypted_refresh
    client.realm_id = row['realm_id']

    try:
        client.refresh()
        encrypted_access = _encrypt_token(client.access_token)
        encrypted_refresh = _encrypt_token(client.refresh_token)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE close_qbo_tokens SET access_token=%s, refresh_token=%s, updated_at=%s",
                       (encrypted_access, encrypted_refresh, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Token Refresh Failed: {e}")
        return None

    return client

def call_qbo_api(url, headers, params):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        st.error(f"QBO API Error ({response.status_code}): {response.text}")
        return None
    return response.json()

def parse_report_to_dict(json_data):
    data_map = {}
    rows = json_data.get("Rows", {}).get("Row", [])

    for row in rows:
        if "ColData" in row and "type" not in row:
            acct_str = row["ColData"][0]["value"]
            acct_parts = acct_str.split(" ", 1)

            if len(acct_parts) > 1 and acct_parts[0].isdigit():
                acct_num = acct_parts[0]
                acct_name = acct_parts[1]

                debit = float(row["ColData"][1]["value"].replace(",", "") or 0)
                credit = float(row["ColData"][2]["value"].replace(",", "") or 0)
                net_bal = debit - credit

                data_map[acct_num] = {
                    'name': acct_name,
                    'balance': net_bal
                }
    return data_map

def fetch_trial_balance(date_str):
    client = get_active_client()
    if not client:
        return None

    base_url = "https://sandbox-quickbooks.api.intuit.com" if ENV == 'sandbox' else "https://quickbooks.api.intuit.com"
    url = f"{base_url}/v3/company/{client.realm_id}/reports/TrialBalance"
    headers = {"Authorization": f"Bearer {client.access_token}", "Accept": "application/json"}

    dt_curr = datetime.strptime(date_str, "%Y-%m-%d")
    fy_start_str = dt_curr.replace(month=1, day=1).strftime("%Y-%m-%d")

    params_curr = {
        "start_date": fy_start_str,
        "end_date": date_str,
        "minorversion": 65
    }
    data_curr_json = call_qbo_api(url, headers, params_curr)
    if not data_curr_json:
        return None

    map_curr = parse_report_to_dict(data_curr_json)

    dt_prior = dt_curr.replace(day=1) - timedelta(days=1)
    prior_date_str = dt_prior.strftime("%Y-%m-%d")

    map_prior = {}

    if dt_curr.month > 1:
        params_prior = {
            "start_date": fy_start_str,
            "end_date": prior_date_str,
            "minorversion": 65
        }
        data_prior_json = call_qbo_api(url, headers, params_prior)
        if data_prior_json:
            map_prior = parse_report_to_dict(data_prior_json)

    final_map = {}

    for acct_num, details in map_curr.items():
        curr_bal = details['balance']
        prior_bal = 0.0

        is_pnl = False
        try:
            if int(acct_num) >= 40000:
                is_pnl = True
        except:
            pass

        if is_pnl and dt_curr.month > 1:
            if acct_num in map_prior:
                prior_bal = map_prior[acct_num]['balance']
            monthly_activity = curr_bal - prior_bal
            final_map[acct_num] = {
                'name': details['name'],
                'balance': monthly_activity
            }
        else:
            final_map[acct_num] = {
                'name': details['name'],
                'balance': curr_bal
            }

    return final_map
