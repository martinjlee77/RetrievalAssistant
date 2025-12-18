import sqlite3
import os

DB_NAME = "close_data.db"

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        print(f"Connected to {DB_NAME}")
        return conn
    except sqlite3.Error as e:
        print(e)
    return None

def create_tables(conn):
    cursor = conn.cursor()

    # 1. Master Table: Chart of Accounts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_number TEXT PRIMARY KEY,
        account_name TEXT NOT NULL,
        category TEXT, -- 'BS' or 'PL'
        permanent_link TEXT -- Link to the SharePoint Folder
    );
    """)

    # 2. Master Table: Checklist Template
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checklist_template (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT,
        task_name TEXT,
        day_due INTEGER,
        default_owner TEXT
    );
    """)

    # 3. Monthly Close Metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_close (
        month_id TEXT PRIMARY KEY,
        status TEXT,
        is_locked BOOLEAN DEFAULT 0,
        variance_threshold_pct REAL DEFAULT 10.0,
        variance_threshold_amt REAL DEFAULT 5000.0
    );
    """)

    # 4. Monthly Account Balances
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_id TEXT,
        account_number TEXT,
        qbo_balance REAL DEFAULT 0.0,
        expected_balance REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Open',
        variance_note TEXT,
        FOREIGN KEY (month_id) REFERENCES monthly_close (month_id),
        FOREIGN KEY (account_number) REFERENCES accounts (account_number)
    );
    """)

    # 5. Monthly Checklist Status
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month_id TEXT,
        task_name TEXT,
        phase TEXT,
        day_due INTEGER,
        owner TEXT,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (month_id) REFERENCES monthly_close (month_id)
    );
    """)

    conn.commit()
    print("Tables created successfully.")

def seed_data(conn):
    cursor = conn.cursor()

    # --- A. FULL CHART OF ACCOUNTS ---
    # Scraped from your TB. 
    # Logic: < 40000 is Balance Sheet (BS), >= 40000 is Profit Loss (PL)

    accounts_list = [
        ('10000', 'Silicon Valley Bank Checking (0703)'),
        ('10050', 'Silicon Valley Bank Sweep'),
        ('10100', 'Silicon Valley Bank Money Market (7792)'),
        ('10200', 'Silicon Valley Bank Checking (0602)'),
        ('10300', 'Mercury Checking (0358)'),
        ('10400', 'Mercury Savings (8069)'),
        ('10500', 'Pinnacle Checking (5706)'),
        ('10502', 'Pinnacle Sweep'),
        ('10600', 'JPMorgan Chase Checking'),
        ('10650', 'JPMorgan Chase Sweep'),
        ('10670', 'JP Money Market'),
        ('10680', 'JPMorgan Investments'),
        ('10700', 'Avidia Banks'),
        ('10701', 'Avidia Banks:Avidia FBO Card Settlement (6089)'),
        ('10705', 'Avidia Banks:Avidia Operating Account (4519)'),
        ('10706', 'Avidia Banks:Avidia Reserve Account (0354)'),
        ('10707', 'Avidia Banks:Avidia Revenue Account (0774)'),
        ('10708', 'Avidia Banks:Avidia OTC Settelment Account (5158)'),
        ('10900', 'Bill.com Money Out Clearing'),
        ('11000', 'Accounts Receivable (A/R)'),
        ('12000', 'Payroll Clearing'),
        ('12100', 'Prepaid Expenses'),
        ('12200', 'Prepaid Expenses - Card & Catalog Related'),
        ('12300', 'R&D Tax Credit Receivable'),
        ('12400', 'Accrued Revenue'),
        ('12500', 'Undeposited Funds'),
        ('12600', 'Accrued R&D Tax Credit Receiveable'),
        ('12700', 'OTC Bank Clearing'),
        ('12800', 'Revenue Cash Clearing'),
        ('12900', 'Card Settlement Clearing'),
        ('13200', 'Furniture & Fixtures'),
        ('13400', 'Capitalized Software'),
        ('13800', 'Accumulated Amortization'),
        ('13900', 'Accumulated Depreciation'),
        ('14000', 'Deposits'),
        ('20000', 'Accounts Payable (A/P)'),
        ('21100', 'Silicon Valley Bank (3537)'),
        ('21200', 'American Express'),
        ('22000', 'Accrued Expenses'),
        ('22500', 'Customer Reserve Deposit'),
        ('23000', 'Payroll Liabilities'),
        ('23100', 'Payroll Liabilities:401K Payable'),
        ('23300', 'Payroll Liabilities:Accrued Payroll'),
        ('23400', 'Payroll Liabilities:Accrued Bonus'),
        ('23500', 'Payroll Liabilities:Accrued Payroll Taxes'),
        ('24000', 'Deferred Revenue'),
        ('25000', 'Shareholder Loan'),
        ('26000', 'Interchange Payable'),
        ('26100', 'Massachusetts Department of Revenue Payable'),
        ('26200', 'Utah State Tax Commission Payable'),
        ('26300', 'Texas State Comptroller Payable'),
        ('26301', 'California Department of Tax and Fee Administration Payable'),
        ('26302', 'District of Columbia Office of Tax and Revenue Payable'),
        ('26303', 'New York Department of Taxation and Finance Payable'),
        ('26304', 'Nebraska Department of Revenue Payable'),
        ('26305', 'Florida Department of Revenue Payable'),
        ('26500', 'Convertible Notes Interest Accrual'),
        ('27000', 'Convertible Notes'),
        ('30000', 'Opening Balance Equity'),
        ('30100', 'Additional Paid in Capital'),
        ('30350', 'Series Seed Preferred'),
        ('30360', 'Series Seed 2 Preferred'),
        ('30371', 'Preferred Stock - Series A:Series A Preferred Stock - (par value)'),
        ('30372', 'Preferred Stock - Series A:Series A Preferred Stock APIC'),
        ('30373', 'Preferred Stock - Series A:Equity Issuance Costs'),
        ('30380', 'Series A-1 Preferred Stock'),
        ('30600', 'Retained Earnings'),
        ('40000', 'Revenue'),
        ('41000', 'Revenue:Implementation Fee'),
        ('42000', 'Revenue:Subscription Fees'),
        ('43000', 'Revenue:Administration Fee'),
        ('44000', 'Revenue:Interest Revenue'),
        ('45000', 'Revenue:Interchange Revenue'),
        ('45500', 'Revenue:Interchange Revenue:Interchange Share Expense'),
        ('46000', 'Revenue:Card Fees'),
        ('47000', 'Revenue:Transaction Fees'),
        ('48000', 'Revenue:Card Network Incentive Revenue'),
        ('49000', 'Revenue:Ecommerce revenue'),
        ('49500', 'Revenue:Other Revenue'),
        ('54000', 'Cost of Sales:Platform Partners'),
        ('59000', 'Cost of Sales:Card & Catalog Related Expenses'),
        ('60000', 'Advertising & Marketing'),
        ('60005', 'Advertising & Marketing:Events'),
        ('60007', 'Advertising & Marketing:Other Marketing'),
        ('61000', 'Contract Labor'),
        ('62050', 'General Business Expenses:Bank Fees'),
        ('62100', 'General Business Expenses:Business Licenses'),
        ('62150', 'General Business Expenses:Charitable Contributions'),
        ('62200', 'General Business Expenses:Company Events'),
        ('62300', 'General Business Expenses:Insurance'),
        ('62310', 'General Business Expenses:Insurance:Business Insurance'),
        ('62400', 'General Business Expenses:Meals & Entertainment'),
        ('62410', 'General Business Expenses:Meals & Entertainment:Entertainment'),
        ('62420', 'General Business Expenses:Meals & Entertainment:Meals'),
        ('62500', 'General Business Expenses:Memberships & Subscriptions'),
        ('62600', 'General Business Expenses:Rent'),
        ('62700', 'General Business Expenses:Software & Apps'),
        ('62750', 'General Business Expenses:Utilities'),
        ('63000', 'Office Expenses'),
        ('63100', 'Office Expenses:Equipment Lease & Rental'),
        ('63200', 'Office Expenses:Office Furniture & Equipment (under $2,500)'),
        ('63300', 'Office Expenses:Office Supplies'),
        ('63500', 'Office Expenses:Shipping & Postage'),
        ('64200', 'Payroll Expenses:401K Management Fees'),
        ('64300', 'Payroll Expenses:Health Insurance'),
        ('64400', 'Payroll Expenses:Payroll Fees'),
        ('64500', 'Payroll Expenses:Payroll Tax Expense'),
        ('64600', 'Payroll Expenses:Salaries & Wages'),
        ('64700', 'Payroll Expenses:Bonus Expense'),
        ('64800', 'Payroll Expenses:401k Employer Match'),
        ('65100', 'Professional Fees:Accounting Fees'),
        ('65200', 'Professional Fees:Consulting Fees'),
        ('65300', 'Professional Fees:Legal Fees'),
        ('66000', 'Taxes'),
        ('67000', 'Travel'),
        ('68000', 'Product Testing'),
        ('69100', 'Travel:Airfare'),
        ('69200', 'Travel:Lodging'),
        ('69300', 'Travel:Parking & Tolls'),
        ('69400', 'Travel:Transportation'),
        ('70000', 'Interest Income'),
        ('71000', 'Other Miscellaneous Income'),
        ('71600', 'Other Miscellaneous Income:R&D Tax Credits'),
        ('80000', 'Amortization Expense'),
        ('81000', 'Depreciation Expense'),
        ('84000', 'Interest Expense'),
        ('85000', 'Other Miscellaneous Expense')
    ]

    # Convert to tuple format for DB insertion: (id, name, type, link)
    accounts_data = []
    for acc in accounts_list:
        acct_num = acc[0]
        acct_name = acc[1]
        # Determine BS vs PL
        if int(acct_num) < 40000:
            cat = 'BS'
        else:
            cat = 'PL'
        accounts_data.append((acct_num, acct_name, cat, ''))

    cursor.executemany("""
        INSERT OR IGNORE INTO accounts (account_number, account_name, category, permanent_link)
        VALUES (?, ?, ?, ?)
    """, accounts_data)

    # --- B. CHECKLIST TEMPLATE ---
    checklist_data = [
        # Phase 1: Data Gathering & Cash
        ('Phase 1', 'Download Interchange/Processor Reports', 1, 'VP'),
        ('Phase 1', 'Download Card/Catalog Vendor Reports', 1, 'VP'),
        ('Phase 1', 'Download Payroll Reports', 1, 'VP'),
        ('Phase 1', 'Sync Bill.com / Ramp / Amex to QBO', 1, 'VP'),
        ('Phase 1', 'Reconcile Operating Cash (SVB/Merc/Chase)', 2, 'VP'),
        ('Phase 1', 'Reconcile FBO & Clearing Accounts', 3, 'VP'),
        ('Phase 1', 'Confirm AR Invoicing (Impl/Sub)', 3, 'VP'),

        # Phase 2: Balance Sheet
        ('Phase 2', 'Update Prepaids Schedule (General)', 5, 'VP'),
        ('Phase 2', 'Reconcile Card & Catalog Prepaids (High Risk)', 5, 'VP'),
        ('Phase 2', 'Update Fixed Assets & Amortization', 6, 'VP'),
        ('Phase 2', 'Review AP Aging', 6, 'VP'),
        ('Phase 2', 'Reconcile Credit Cards', 6, 'VP'),
        ('Phase 2', 'Book Accruals (Legal/AWS/Est)', 6, 'VP'),
        ('Phase 2', 'Payroll Rec & True-up', 7, 'VP'),
        ('Phase 2', 'Tax Payables (State/Interchange)', 7, 'VP'),

        # Phase 3: Revenue & Equity
        ('Phase 3', 'Process Interchange Rev & Share', 8, 'VP'),
        ('Phase 3', 'Process Transaction/Card Fees', 8, 'VP'),
        ('Phase 3', 'Update Deferred Revenue Waterfall', 9, 'VP'),
        ('Phase 3', 'Book Interest & Equity Activity', 9, 'VP'),

        # Phase 4: Review
        ('Phase 4', 'Run P&L Flux Analysis', 10, 'VP'),
        ('Phase 4', 'Check Gross Margins', 10, 'VP'),
        ('Phase 4', 'Lock Books in QBO', 10, 'VP'),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO checklist_template (phase, task_name, day_due, default_owner)
        VALUES (?, ?, ?, ?)
    """, checklist_data)

    conn.commit()
    print(f"Seeded {len(accounts_data)} accounts and {len(checklist_data)} tasks.")

def main():
    if os.path.exists(DB_NAME):
        print(f"Warning: {DB_NAME} already exists.")

    conn = create_connection()
    if conn:
        create_tables(conn)
        seed_data(conn)
        conn.close()

if __name__ == '__main__':
    main()