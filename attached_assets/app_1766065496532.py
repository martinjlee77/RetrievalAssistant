import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import qbo_connector # Import our new file
from datetime import date, timedelta
import calendar
import numpy as np

# --- CONFIGURATION ---
APP_TITLE = "Lynx Close Platform"
DB_NAME = "close_data.db"

st.set_page_config(page_title=APP_TITLE, layout="wide")

# --- DATABASE FUNCTIONS ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def get_all_months():
    """Fetch all close periods created so far."""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM monthly_close ORDER BY month_id DESC", conn)
    conn.close()
    return df

def create_new_month_close(month_str):
    """
    Creates a new close period. 
    Logic: Clones the Task List from the most recent prior month (Smart Rollover).
    If no prior month exists, falls back to the Master Template.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Create Month Entry
        cursor.execute("INSERT INTO monthly_close (month_id, status) VALUES (?, 'Open')", (month_str,))

        # 2. Smart Task Rollover Logic
        # Find the most recent month created before this one
        cursor.execute("SELECT month_id FROM monthly_close WHERE month_id < ? ORDER BY month_id DESC LIMIT 1", (month_str,))
        last_month_row = cursor.fetchone()

        if last_month_row:
            last_month_id = last_month_row[0]
            st.toast(f"Found history. Cloning tasks from {last_month_id}...", icon="📋")

            # Copy tasks from the previous month
            # We copy everything BUT reset status to 'Pending'
            cursor.execute("""
                INSERT INTO monthly_tasks (month_id, task_name, phase, day_due, owner, instructions_link, status)
                SELECT ?, task_name, phase, day_due, owner, instructions_link, 'Pending'
                FROM monthly_tasks
                WHERE month_id = ?
            """, (month_str, last_month_id))

        else:
            st.toast("First run detected. Using Master Template.", icon="🆕")
            # Fallback to Template
            cursor.execute("""
                INSERT INTO monthly_tasks (month_id, task_name, phase, day_due, owner, status)
                SELECT ?, task_name, phase, day_due, default_owner, 'Pending'
                FROM checklist_template
            """, (month_str,))

        # 3. Initialize GL Balances
        # We assume the 'accounts' table is the source of truth (it contains auto-discovered accounts)
        cursor.execute("""
            INSERT INTO monthly_balances (month_id, account_number, status)
            SELECT ?, account_number, 'Open'
            FROM accounts
        """, (month_str,))

        conn.commit()
        st.toast(f"Successfully initialized {month_str}", icon="✅")

    except sqlite3.IntegrityError:
        st.error(f"Close for {month_str} already exists.")
    finally:
        conn.close()

def update_task_status(task_id, new_status):
    """Update the status of a specific task in the DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE monthly_tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()

def update_account_entry(entry_id, field, value):
    """Generic updater for monthly_balances table (expected_balance, status, variance_note)."""
    conn = get_connection()
    cursor = conn.cursor()
    query = f"UPDATE monthly_balances SET {field} = ? WHERE id = ?"
    cursor.execute(query, (value, entry_id))
    conn.commit()
    conn.close()

def update_permanent_link(account_number, link):
    """Updates the Master Account table with the SharePoint link."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE accounts SET permanent_link = ? WHERE account_number = ?", (link, account_number))
    conn.commit()
    conn.close()

def simulate_qbo_data(month_id):
    """TEMPORARY: Fills QBO column with random numbers so we can test the UI."""
    conn = get_connection()
    cursor = conn.cursor()
    # Update random balances for testing
    cursor.execute(f"""
        UPDATE monthly_balances 
        SET qbo_balance = ABS(RANDOM() % 100000) / 100.0
        WHERE month_id = '{month_id}'
    """)
    conn.commit()
    conn.close()
    st.toast("Simulated QBO Data Loaded", icon="🤖")
    st.rerun()

def get_last_sync_time(month_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_synced_at FROM monthly_close WHERE month_id = ?", (month_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# --- HELPER FUNCTIONS ---
def get_account_group(acct_num):
    """Categorize accounts based on specific Fintech COA ranges (Zero-padded for sorting)."""
    try:
        n = int(acct_num)

        # --- ASSETS ---
        if 10000 <= n <= 10999: return "01. Cash & Cash Equivalents"
        if 11000 <= n <= 11999: return "02. Accounts Receivable"
        if 12000 <= n <= 12999: return "03. Other Current Assets"
        if 13000 <= n <= 13999: return "04. Fixed Assets"
        if 14000 <= n <= 14999: return "03. Other Current Assets"

        # --- LIABILITIES ---
        if 20000 <= n <= 21999: return "05. Accounts Payable & Cards"
        if 22000 <= n <= 23999: return "06. Other Current Liabilities"
        if 26000 <= n <= 26999: return "06. Other Current Liabilities"
        if 24000 <= n <= 25999: return "07. Long-term Liabilities"
        if 27000 <= n <= 29999: return "07. Long-term Liabilities"

        # --- EQUITY ---
        if 30000 <= n <= 39999: return "08. Equity"

        # --- P&L ---
        if 40000 <= n <= 49999: return "09. Revenue"
        if 50000 <= n <= 59999: return "10. Cost of Sales"
        if 60000 <= n <= 69999: return "11. Operating Expenses"
        if 70000 <= n <= 89999: return "12. Other Income/Expense"

    except:
        pass
    return "13. Other / Unmapped"

def get_prior_month_id(curr_month_id):
    """Calculates the previous month string (YYYY-MM)."""
    try:
        curr_date = datetime.strptime(curr_month_id, "%Y-%m")
        # Subtract one month
        if curr_date.month == 1:
             prev_date = curr_date.replace(year=curr_date.year - 1, month=12)
        else:
             prev_date = curr_date.replace(month=curr_date.month - 1)
        return prev_date.strftime("%Y-%m")
    except:
        return None

def update_month_totals(month_id, debits, credits):
    """Save the manual QBO tie-out totals."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE monthly_close 
        SET qbo_total_debits = ?, qbo_total_credits = ? 
        WHERE month_id = ?
    """, (debits, credits, month_id))
    conn.commit()
    conn.close()


def get_month_totals(month_id):
    """Fetch the manual QBO totals."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT qbo_total_debits, qbo_total_credits FROM monthly_close WHERE month_id = ?", (month_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else (0.0, 0.0)

def get_business_day_delta(month_id):
    """Calculates current T-Day relative to the month end."""
    # 1. Calculate Month End Date
    y, m = map(int, month_id.split('-'))
    last_day = calendar.monthrange(y, m)[1]
    month_end_date = date(y, m, last_day)

    # 2. Today
    today = date.today()

    # 3. Calculate Business Days (numpy.busday_count excludes weekends)
    if today <= month_end_date:
        return 0 # Close hasn't started

    # busday_count returns the number of business days between dates
    t_days = np.busday_count(month_end_date, today)
    return int(t_days)

# --- UI COMPONENTS ---

def render_lobby():
    """The Home Screen: Grid of Cards."""
    st.title(f"📂 {APP_TITLE}")

    # 1. Action: Create New Close
    with st.expander("Start a New Month Close", expanded=False):
        c1, c2 = st.columns([1, 4])
        with c1:
            current_month = datetime.now().strftime("%Y-%m")
            new_month_input = st.text_input("Month (YYYY-MM)", value=current_month)
        with c2:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("Initialize Close"):
                create_new_month_close(new_month_input)
                st.rerun()

    # 2. Display Existing Closes
    df_months = get_all_months()

    if df_months.empty:
        st.info("No close periods found. Initialize one above!")
        return

    st.subheader("Active Closes")

    cols = st.columns(4)
    for index, row in df_months.iterrows():
        col = cols[index % 4]
        with col:
            status_color = "🟢" if row['status'] == 'Closed' else "🔵"
            lock_icon = "🔒 Closed" if row['is_locked'] else "🔓 Open"

            with st.container(border=True, horizontal_alignment="center"):
                st.markdown(f"### {row['month_id']}", text_alignment="center")
                st.markdown(f"**Close Status:** {status_color} {row['status']}", text_alignment="center")
                st.markdown(f"**QBO:** {lock_icon}", text_alignment="center")

                if st.button(f"Open {row['month_id']}", key=f"btn_{row['month_id']}"):
                    st.session_state['active_month'] = row['month_id']
                    st.rerun()

def render_checklist_tab(month_id, owner_filter):
    """Render the Interactive Checklist (Full Height Grid)."""
    conn = get_connection()

    # 1. Fetch Tasks
    query = "SELECT * FROM monthly_tasks WHERE month_id = ?"
    params = [month_id]

    if owner_filter != "All":
        query += " AND owner = ?"
        params.append(owner_filter)

    query += " ORDER BY day_due ASC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    # 2. Calculate Context & Progress
    current_t_day = get_business_day_delta(month_id)
    total_tasks = len(df)
    done_tasks = len(df[df['status'].isin(['Done', 'N/A'])])
    prog = done_tasks / total_tasks if total_tasks > 0 else 0

    # --- HEADER SECTION ---
    c1, c2, c3 = st.columns([2.5, 1, 1])

    with c1:
        st.markdown(f"### 📅 Today is T+{current_t_day}")
        st.caption("✅ Done &nbsp;|&nbsp; 🔴 Late &nbsp;|&nbsp; 🟡 Due Today &nbsp;|&nbsp; ⚪️ Upcoming")

    with c2:
        st.metric("Completion", f"{done_tasks}/{total_tasks}")

    with c3:
        # SAVE BUTTON AT THE TOP
        save_clicked = st.button("💾 Save Changes", type="primary", use_container_width=True)

    # Full Width Progress Bar
    st.progress(prog, text=f"Overall Completion: {int(prog*100)}%")

    # 3. Logic: Add 'Alert' Column
    def get_alert_icon(row):
        if row['status'] in ['Done', 'N/A']:
            return "✅"

        if row['day_due'] < current_t_day:
            return "🔴" # Late
        elif row['day_due'] == current_t_day:
            return "🟡" # Due Today
        else:
            return "⚪️" # Upcoming

    if not df.empty:
        df['Health'] = df.apply(get_alert_icon, axis=1)
    else:
        df['Health'] = []

    # 4. Configure the Grid
    st.divider()

    ROLES = ["VP Accounting", "Ops", "CFO", "Accounting Firm"]
    PHASES = ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]
    STATUS_OPTS = ["Pending", "In Progress", "Done", "N/A"]

    column_config = {
        "id": None,
        "month_id": None,
        "Health": st.column_config.TextColumn("Health", width="small", disabled=True),
        "task_name": st.column_config.TextColumn("Task Name", width="large", required=True),
        "phase": st.column_config.SelectboxColumn("Phase", options=PHASES, required=True),
        "day_due": st.column_config.NumberColumn("Due (T+)", min_value=1, max_value=20, format="%d"),
        "owner": st.column_config.SelectboxColumn("Owner", options=ROLES, required=True),
        "instructions_link": st.column_config.LinkColumn("SOP", display_text="Open Doc"),
        "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTS, required=True)
    }

    display_df = df[['id', 'Health', 'phase', 'task_name', 'day_due', 'owner', 'instructions_link', 'status', 'month_id']]

    # DYNAMIC HEIGHT CALCULATION
    # 35px per row + 35px for header. Max 1500px to prevent infinite scrolling on huge lists.
    dynamic_height = min((len(df) + 1) * 35, 1500)

    edited_df = st.data_editor(
        display_df,
        key="checklist_editor",
        hide_index=True,
        column_config=column_config,
        use_container_width=True,
        num_rows="dynamic",
        height=dynamic_height # <--- This applies the fix
    )

    # 5. Save Logic (Triggered by Top Button)
    if save_clicked:
        conn = get_connection()
        cursor = conn.cursor()

        # A. Detect Deletions
        original_ids = set(df['id'].dropna().astype(int))
        current_ids = set(edited_df['id'].dropna().astype(int))
        deleted_ids = original_ids - current_ids

        for del_id in deleted_ids:
            cursor.execute("DELETE FROM monthly_tasks WHERE id = ?", (del_id,))

        # B. Detect Updates & Inserts
        for index, row in edited_df.iterrows():
            if pd.notna(row['id']):
                cursor.execute("""
                    UPDATE monthly_tasks 
                    SET task_name=?, phase=?, day_due=?, owner=?, instructions_link=?, status=?
                    WHERE id=?
                """, (row['task_name'], row['phase'], row['day_due'], row['owner'], row['instructions_link'], row['status'], row['id']))
            else:
                cursor.execute("""
                    INSERT INTO monthly_tasks (month_id, task_name, phase, day_due, owner, instructions_link, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (month_id, row['task_name'], row['phase'], row['day_due'], row['owner'], row['instructions_link'], row['status']))

        conn.commit()
        conn.close()
        st.toast("Checklist Updated!", icon="✅")
        st.rerun()

def render_tb_tab(month_id):
    """Render the Trial Balance & Substantiation View (Clean Execution Mode)."""

    conn = get_connection()

    # 1. Fetch Data
    query = """
        SELECT 
            mb.id, 
            mb.account_number, 
            a.account_name, 
            a.permanent_link,
            mb.qbo_balance, 
            mb.expected_balance, 
            mb.status,
            mb.rec_note
        FROM monthly_balances mb
        JOIN accounts a ON mb.account_number = a.account_number
        WHERE mb.month_id = ?
        ORDER BY mb.account_number ASC
    """
    df_bal = pd.read_sql(query, conn, params=[month_id])
    conn.close()

    if df_bal.empty:
        st.error("No account data found for this month.")
        return

    # 2. Add Grouping
    df_bal['Group'] = df_bal['account_number'].apply(get_account_group)

    # 3. Progress Bar
    total_accts = len(df_bal)
    done_accts = len(df_bal[df_bal['status'].isin(['Supported', 'Reviewed'])])
    progress = done_accts / total_accts if total_accts > 0 else 0

    st.progress(progress, text=f"Reconciliation Progress: {int(progress*100)}% ({done_accts}/{total_accts})")
    st.divider()

    # 4. Render Compact Grids by Group
    groups = sorted(df_bal['Group'].unique())

    for group in groups:
        with st.expander(f"📂 {group}", expanded=False):

            group_rows = df_bal[df_bal['Group'] == group].copy()

            # Formatting for Display
            group_rows['Variance'] = group_rows['qbo_balance'] - group_rows['expected_balance']
            group_rows['qbo_balance_fmt'] = group_rows['qbo_balance'].apply(lambda x: "{:,.2f}".format(x))
            group_rows['Variance_fmt'] = group_rows['Variance'].apply(lambda x: "{:,.2f}".format(x))

            # Configure Columns
            column_config = {
                "id": None, 
                "Group": None,
                "qbo_balance": None, # Hide raw number
                "Variance": None,    # Hide raw number

                "account_number": "Acct #",
                "account_name": "Account Name",
                "permanent_link": st.column_config.LinkColumn("Workpaper Link", display_text="Open Folder"),
                "rec_note": st.column_config.TextColumn("Reconciliation Note", width="medium"),

                "qbo_balance_fmt": st.column_config.TextColumn("QBO Balance", disabled=True),
                "expected_balance": st.column_config.NumberColumn("Expected Balance", format="$%.2f"),
                "Variance_fmt": st.column_config.TextColumn("Diff", disabled=True),

                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Open", "Supported", "Reviewed"],
                    required=True
                )
            }

            display_cols = ['id', 'account_number', 'account_name', 'qbo_balance_fmt', 'expected_balance', 'Variance_fmt', 'status', 'permanent_link', 'rec_note']

            edited_df = st.data_editor(
                group_rows[display_cols],
                key=f"editor_{group}",
                hide_index=True,
                column_config=column_config,
                use_container_width=True,
                height=min((len(group_rows) + 1) * 35, 600)
            )

            # 5. Detect Changes & Auto-Save
            changes_detected = False
            for index, row in edited_df.iterrows():
                orig_row = df_bal[df_bal['id'] == row['id']].iloc[0]

                # A. Check Expected Balance
                if abs(row['expected_balance'] - orig_row['expected_balance']) > 0.001:
                    update_account_entry(row['id'], 'expected_balance', row['expected_balance'])
                    changes_detected = True

                # B. Check Note
                if row['rec_note'] != orig_row['rec_note']:
                    # Update the specific note field
                    conn = get_connection()
                    conn.execute("UPDATE monthly_balances SET rec_note = ? WHERE id = ?", (row['rec_note'], row['id']))
                    conn.commit()
                    conn.close()
                    changes_detected = True

                # C. Check Link
                if row['permanent_link'] != orig_row['permanent_link']:
                    update_permanent_link(row['account_number'], row['permanent_link'])
                    changes_detected = True

                # D. Check Status (With Validation Logic)
                if row['status'] != orig_row['status']:
                    # Calculate Variance using the NEW expected balance
                    new_variance = orig_row['qbo_balance'] - row['expected_balance']

                    # Audit Logic: Cannot be Supported/Reviewed if Variance exists
                    if row['status'] in ['Supported', 'Reviewed'] and abs(new_variance) > 0.01:
                        st.toast(f"❌ Account {row['account_number']}: Cannot mark complete. Variance is {new_variance:,.2f}", icon="🚫")

                        # FORCE RESET: Delete the editor state so it forgets the user's invalid selection
                        if f"editor_{group}" in st.session_state:
                            del st.session_state[f"editor_{group}"]

                        # Rerun immediately to reload the "Open" status from DB
                        st.rerun()
                    else:
                        update_account_entry(row['id'], 'status', row['status'])
                        changes_detected = True

            if changes_detected:
                st.rerun()

def render_flux_tab(month_id, threshold_amt, threshold_pct):
    """Render the Audit Center (Compact & Descriptive)."""

    conn = get_connection()
    prev_month_id = get_prior_month_id(month_id)

    # 1. Fetch Data
    query = """
        SELECT 
            curr.id,
            curr.account_number,
            a.account_name,
            curr.qbo_balance as curr_bal,
            prev.qbo_balance as prev_bal,
            curr.variance_note
        FROM monthly_balances curr
        LEFT JOIN monthly_balances prev 
            ON curr.account_number = prev.account_number 
            AND prev.month_id = ?
        JOIN accounts a ON curr.account_number = a.account_number
        WHERE curr.month_id = ?
        ORDER BY curr.account_number ASC
    """
    df = pd.read_sql(query, conn, params=[prev_month_id, month_id])

    # Sub-Ledger Query
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(qbo_balance) FROM monthly_balances WHERE month_id = ?", (month_id,))
    sub_ledger_total = cursor.fetchone()[0] or 0.0
    conn.close()

    if df.empty:
        st.info("No data found.")
        return

    # 2. Data Enrichment
    df['Group'] = df['account_number'].apply(get_account_group)
    df['prev_bal'] = df['prev_bal'].fillna(0.0)
    df['diff_amt'] = df['curr_bal'] - df['prev_bal']
    df['diff_pct'] = df.apply(
        lambda x: (x['diff_amt'] / x['prev_bal'] * 100) if x['prev_bal'] != 0 else 0.0, axis=1
    )

    # ==========================================
    # 3. AUDIT CALCULATIONS
    # ==========================================

    # Test 1: Population
    count_db = len(df)
    count_tab2 = len(df[df['Group'] != "13. Other / Unmapped"])
    count_tab3 = len(df)
    is_pop_match = (count_db == count_tab2 == count_tab3)

    # Test 2: BS Logic
    total_assets = df[df['Group'].str.startswith(('01', '02', '03', '04'))]['curr_bal'].sum()
    total_liabs  = df[df['Group'].str.startswith(('05', '06', '07'))]['curr_bal'].sum()
    total_equity = df[df['Group'].str.startswith(('08'))]['curr_bal'].sum()
    total_pnl    = df[df['Group'].str.startswith(('09', '10', '11', '12'))]['curr_bal'].sum()
    bs_check_val = total_assets + total_liabs + total_equity + total_pnl
    is_bs_balanced = abs(bs_check_val) < 0.01

    # Test 3: 3-Way Tie Out
    df_mapped = df[df['Group'] != "13. Other / Unmapped"]
    tab2_dr = df_mapped[df_mapped['curr_bal'] > 0]['curr_bal'].sum()
    tab2_cr = df_mapped[df_mapped['curr_bal'] < 0]['curr_bal'].sum()
    tab3_dr = df[df['curr_bal'] > 0]['curr_bal'].sum()
    tab3_cr = df[df['curr_bal'] < 0]['curr_bal'].sum()
    saved_debits, saved_credits = get_month_totals(month_id)

    internal_dr_match = abs(tab2_dr - tab3_dr) < 0.01
    internal_cr_match = abs(tab2_cr - tab3_cr) < 0.01
    external_dr_match = abs(tab3_dr - saved_debits) < 0.01
    external_cr_match = abs(tab3_cr - saved_credits) < 0.01
    is_tied_out = internal_dr_match and internal_cr_match and external_dr_match and external_cr_match

    # ==========================================
    # 4. RENDER AUDIT DASHBOARD (Compact)
    # ==========================================
    st.markdown("### 🛡 Audit Control Center")

    r1_c1, r1_c2 = st.columns(2)

    # CARD 1: Population Control (Compact)
    with r1_c1:
        with st.container(border=True):
            st.markdown("**1. Population Integrity Check**")
            st.caption("Verifies DB rows match visible accounts in Tab 2 & 3.")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("Raw DB")
                st.markdown(f"**{count_db}**")
            with c2:
                st.caption("Tab 2")
                st.markdown(f"**{count_tab2}**")
            with c3:
                st.caption("Tab 3")
                st.markdown(f"**{count_tab3}**")

            st.write("") # Spacer
            if is_pop_match:
                st.success("✅ Valid")
            else:
                st.error(f"🚨 Variance: {count_db - count_tab2}")

    # CARD 2: Accounting Equation (Compact)
    with r1_c2:
        with st.container(border=True):
            st.markdown("**2. Balance Sheet Logic Check**")
            st.caption("Assets = Liabilities + Equity")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("Assets")
                st.markdown(f"**{total_assets:,.0f}**")
            with c2:
                st.caption("L+E+NI")
                st.markdown(f"**{(total_liabs + total_equity + total_pnl):,.0f}**")
            with c3:
                st.caption("Net Check")
                st.markdown(f"**{bs_check_val:,.2f}**")

            st.write("") # Spacer
            if is_bs_balanced:
                st.success("✅ Balanced")
            else:
                st.error("🚨 Out of Balance")

    # CARD 3: 3-Way Tie Out (Full Width)
    with st.container(border=True):
        st.markdown("**3. External 3-Way Tie-Out**")
        st.caption("Sub-Ledger (Tab 2) vs. General Ledger (Tab 3) vs. QBO PDF.")

        # Grid: Label | Tab 2 | Tab 3 | Input
        c_lbl, c_t2, c_t3, c_qbo = st.columns([1, 1.5, 1.5, 2])

        # Header Row
        c_lbl.markdown("###### Label")
        c_t2.markdown("###### Tab 2")
        c_t3.markdown("###### Tab 3")
        c_qbo.markdown("###### QBO Input")

        # Debits Row
        c_lbl.markdown("Total Dr")
        c_t2.markdown(f"**{tab2_dr:,.2f}**")
        c_t3.markdown(f"**{tab3_dr:,.2f}**")
        val_dr = c_qbo.number_input("Dr", value=saved_debits, key="aud_dr", label_visibility="collapsed", format="%.2f")

        # Credits Row
        c_lbl.markdown("Total Cr")
        c_t2.markdown(f"**{tab2_cr:,.2f}**")
        c_t3.markdown(f"**{tab3_cr:,.2f}**")
        val_cr = c_qbo.number_input("Cr", value=saved_credits, key="aud_cr", label_visibility="collapsed", format="%.2f")

        # Save Logic
        if val_dr != saved_debits or val_cr != saved_credits:
            update_month_totals(month_id, val_dr, val_cr)
            st.rerun()

        # Final Status
        if is_tied_out:
            st.success("✅ 3-Way Match Confirmed")
        else:
            # Create columns to show specific errors
            c_err1, c_err2 = st.columns(2)

            # Check Internal (Tab 2 vs Tab 3)
            if not (internal_dr_match and internal_cr_match):
                c_err1.error(f"🚨 Internal Var: Dr {tab2_dr - tab3_dr:.2f} | Cr {tab2_cr - tab3_cr:.2f}")

            # Check External (System vs Manual Input)
            if not (external_dr_match and external_cr_match):
                # Calculate variances using the correct variables (tab3_dr/cr are the System Totals)
                v_dr = tab3_dr - saved_debits
                v_cr = tab3_cr - saved_credits
                c_err2.error(f"🚨 External Var: Dr {v_dr:.2f} | Cr {v_cr:.2f}")

    st.divider()

    # ==========================================
    # 5. FLUX ANALYSIS TABLE
    # ==========================================
    st.subheader("📊 Flux Analysis")

    # Auto N/A Logic
    updates_made = False
    for index, row in df.iterrows():
        is_material = (abs(row['diff_amt']) >= threshold_amt) and (abs(row['diff_pct']) >= threshold_pct)
        current_note = str(row['variance_note']) if row['variance_note'] else ""
        if not is_material and current_note == "":
            update_account_entry(row['id'], 'variance_note', "N/A")
            df.at[index, 'variance_note'] = "N/A"
            updates_made = True
    if updates_made:
        st.rerun()

    # Formatting
    display_df = df.copy()
    display_df['prev_bal'] = display_df['prev_bal'].apply(lambda x: "{:,.2f}".format(x))
    display_df['curr_bal'] = display_df['curr_bal'].apply(lambda x: "{:,.2f}".format(x))
    display_df['diff_amt'] = display_df['diff_amt'].apply(lambda x: "{:,.2f}".format(x))
    display_df['diff_pct'] = display_df['diff_pct'].apply(lambda x: "{:.1f}%".format(x))

    def get_status_icon(row):
        orig_row = df[df['id'] == row['id']].iloc[0]
        is_material = (abs(orig_row['diff_amt']) >= threshold_amt) and (abs(orig_row['diff_pct']) >= threshold_pct)
        note = str(orig_row['variance_note']) if orig_row['variance_note'] else ""
        if not is_material: return "⚪️" 
        elif is_material and (note == "" or note == "None"): return "🔴"
        else: return "✅" 

    display_df['Action'] = display_df.apply(get_status_icon, axis=1)

    column_config = {
        "id": None, 
        "Group": None,
        "account_number": "Acct #",
        "account_name": "Account Name",
        "prev_bal": st.column_config.TextColumn("Prior Month", disabled=True),
        "curr_bal": st.column_config.TextColumn("Current Month", disabled=True),
        "diff_amt": st.column_config.TextColumn("Var $", disabled=True),
        "diff_pct": st.column_config.TextColumn("Var %", disabled=True),
        "variance_note": st.column_config.TextColumn("Explanation", width="large"),
        "Action": st.column_config.TextColumn("St", width="small", disabled=True)
    }

    final_view = display_df[['id', 'account_number', 'account_name', 'prev_bal', 'curr_bal', 'diff_amt', 'diff_pct', 'Action', 'variance_note']]

    # DYNAMIC KEY FIX (Using f-string correctly)
    edited_df = st.data_editor(
        final_view,
        key=f"audit_flux_editor_{month_id}",
        hide_index=True,
        column_config=column_config,
        use_container_width=True,
        height=min((len(df) + 1) * 35, 1200)
    )

    changes_detected = False
    for index, row in edited_df.iterrows():
        original_note = str(df.at[index, 'variance_note'])
        new_note = str(row['variance_note'])
        if original_note != new_note:
            update_account_entry(row['id'], 'variance_note', new_note)
            changes_detected = True

    if changes_detected:
        st.toast("Saved!", icon="💾")
        st.rerun()

def render_workspace(month_id):
    """The Main Close Management Screen."""

    # --- SIDEBAR ---
    with st.sidebar:
        st.header(f"🗓 {month_id}")
        if st.button("← Back to Lobby"):
            del st.session_state['active_month']
            st.rerun()

        st.divider()
        st.subheader("Filters")
        owner_filter = st.selectbox("Task Owner", ["All", "VP", "Firm", "Payroll"])

        st.divider()
        st.subheader("Flux Thresholds")
        # Default to 5000 and 10%
        thresh_amt = st.number_input("Min Variance ($)", value=5000, step=1000)
        thresh_pct = st.number_input("Min Variance (%)", value=10, step=1)

        st.divider()
        st.subheader("Data Sync")

        # Check connection status
        try:
            client = qbo_connector.get_active_client()
        except Exception:
            client = None

        if client:
            st.success("✅ QBO Connected")

            # Show Last Sync Time
            last_sync = get_last_sync_time(month_id)
            if last_sync:
                st.caption(f"Last Sync: {last_sync}")
            else:
                st.caption("Last Sync: Never")

            if st.button("🔄 Sync Live Data"):
                with st.spinner("Fetching Trial Balance from QBO..."):
                    try:
                        # 1. Date Logic
                        y, m = map(int, month_id.split('-'))
                        last_day = calendar.monthrange(y, m)[1]
                        end_date_str = f"{month_id}-{last_day}"

                        # 2. Fetch
                        qbo_data = qbo_connector.fetch_trial_balance(end_date_str)

                        if qbo_data:
                            conn = get_connection()
                            cursor = conn.cursor()

                            # 3. Process Data (Same as before)
                            new_accounts_found = 0
                            updated_balances = 0

                            for acct_num, details in qbo_data.items():
                                name = details['name']
                                bal = details['balance']

                                # Auto-Discovery
                                cursor.execute("SELECT account_number FROM accounts WHERE account_number = ?", (acct_num,))
                                if not cursor.fetchone():
                                    cat = 'BS' if int(acct_num) < 40000 else 'PL'
                                    cursor.execute("INSERT INTO accounts (account_number, account_name, category, permanent_link) VALUES (?, ?, ?, '')", (acct_num, name, cat))
                                    new_accounts_found += 1

                                # Update Balance
                                cursor.execute("SELECT id FROM monthly_balances WHERE month_id = ? AND account_number = ?", (month_id, acct_num))
                                row = cursor.fetchone()

                                if row:
                                    cursor.execute("UPDATE monthly_balances SET qbo_balance = ? WHERE id = ?", (bal, row[0]))
                                else:
                                    cursor.execute("INSERT INTO monthly_balances (month_id, account_number, qbo_balance, status) VALUES (?, ?, ?, 'Open')", (month_id, acct_num, bal))
                                updated_balances += 1

                            # 4. UPDATE SYNC TIMESTAMP
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("UPDATE monthly_close SET last_synced_at = ? WHERE month_id = ?", (now_str, month_id))

                            conn.commit()
                            conn.close()

                            if new_accounts_found > 0: st.toast(f"Auto-discovered {new_accounts_found} new accounts!")
                            st.toast(f"Synced {updated_balances} balances.", icon="✅")
                            st.rerun()
                        else:
                            st.error("Failed to fetch data.")
                    except Exception as e:
                        st.error(f"Sync Error: {e}")
        else:
            st.warning("Not Connected")
            auth_url = qbo_connector.get_auth_url()
            st.link_button("🔗 Login to Intuit", auth_url)

    # --- MAIN TABS ---
    st.title(f"Close Workspace: {month_id}")

    tab1, tab2, tab3 = st.tabs(["📋 Process (Checklist)", "⚖️ Substantiation (TB)", "📊 Reporting (Flux)"])

    with tab1:
        render_checklist_tab(month_id, owner_filter)

    with tab2:
        render_tb_tab(month_id)

    with tab3:
        # Pass the threshold values from sidebar to the function
        render_flux_tab(month_id, thresh_amt, thresh_pct)



# --- MAIN ENTRY POINT ---
def main():
    # --- OAUTH HANDLER ---
    # Check if we just came back from QBO login
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        realm_id = query_params["realmId"]
        try:
            qbo_connector.handle_callback(auth_code, realm_id)
            st.toast("Successfully Connected to QuickBooks!", icon="🔗")
            # Clear params to clean URL
            st.query_params.clear()
        except Exception as e:
            st.error(f"Login Failed: {e}")

    if 'active_month' in st.session_state:
        render_workspace(st.session_state['active_month'])
    else:
        render_lobby()

if __name__ == '__main__':
    main()