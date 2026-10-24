"""database.py - SQLite storage, login check, and config loader."""
import hashlib, hmac, os, sqlite3
from datetime import datetime
import config

"""
database.py


INDEX  (function - line number)
  connect()                - 62
  run()                    - 69
  query()                  - 80
  hash_password()          - 89
  _add_columns()           - 96
  _migrate()               - 104
  init_db()                - 114
  authenticate()           - 141
  can()                    - 152
  load_config()            - 158
  update_setting()         - 171
  update_company()         - 182
  lookup_sss()             - 191
  lookup_tax()             - 196
  save_employee()          - 208
  get_employee()           - 220
  list_employees()         - 226
  save_attendance()        - 233
  get_attendance()         - 252
  save_payslip()           - 260
  list_payslips()          - 267
  find_payslip()           - 274
  delete_payslip()         - 281
  approve_payslip()        - 286
"""

# table definitions, only created if they don't exist yet
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS company (id INTEGER PRIMARY KEY, name TEXT, address TEXT, tin TEXT, contact TEXT,
    hr_name TEXT, hr_title TEXT, manager_name TEXT, manager_title TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL);
CREATE TABLE IF NOT EXISTS sss_table (salary_min REAL, salary_max REAL, employee_share REAL);
CREATE TABLE IF NOT EXISTS tax_table (bracket_min REAL, bracket_max REAL, base_tax REAL, rate REAL);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, position TEXT, department TEXT,
    monthly_basic_salary REAL NOT NULL, sss_no TEXT, philhealth_no TEXT, pagibig_no TEXT,
    tin_no TEXT, status TEXT DEFAULT 'regular');
CREATE TABLE IF NOT EXISTS attendance (
    employee_id TEXT, period_start TEXT, period_end TEXT, days_worked REAL, absent_days REAL,
    late_minutes REAL, ot_hours REAL, night_diff_hours REAL, expected_days REAL,
    regular_holiday_days REAL DEFAULT 0, special_holiday_days REAL DEFAULT 0,
    PRIMARY KEY (employee_id, period_start, period_end));
CREATE TABLE IF NOT EXISTS payslips (
    payslip_id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, period_start TEXT,
    period_end TEXT, pay_date TEXT, kinsena TEXT, basic_pay REAL, ot_pay REAL,
    night_diff_pay REAL, holiday_pay REAL, bonus_13th REAL, gross_pay REAL,
    absent_deduction REAL, late_deduction REAL, sss REAL, philhealth REAL, pagibig REAL,
    tax REAL, total_deductions REAL, net_pay REAL, status TEXT DEFAULT 'pending',
    approved_by TEXT, created_at TEXT);
"""


# opens the database file
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# for insert / update / delete, saves right away
def run(sql, args=()):
    """Run one write statement and commit. Returns lastrowid."""
    conn = connect()
    try:
        with conn:
            return conn.execute(sql, args).lastrowid
    finally:
        conn.close()


# for select, returns a list of dicts
def query(sql, args=()):
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


# hashes the password with a salt so it isn't stored as plain text
def hash_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000)
    return h.hex(), salt


# adds columns that are missing in an older database
def _add_columns(conn, table, columns):
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


# updates an older database to the new layout
def _migrate(conn):
    """Bring a database created by an older version up to date (safe to run every start)."""
    _add_columns(conn, "company", {c: "TEXT" for c in ("hr_name", "hr_title", "manager_name", "manager_title")})
    _add_columns(conn, "attendance", {"expected_days": "REAL", "regular_holiday_days": "REAL DEFAULT 0",
                                      "special_holiday_days": "REAL DEFAULT 0"})
    for col in ("hr_name", "hr_title", "manager_name", "manager_title"):
        conn.execute(f"UPDATE company SET {col}=? WHERE {col} IS NULL OR {col}=''", (config.COMPANY[col],))


# creates the tables and adds the default data on the first run
def init_db():
    """Create tables and seed defaults on first run."""
    conn = connect()
    try:
        with conn:
            conn.executescript(SCHEMA)
            _migrate(conn)
            if not conn.execute("SELECT 1 FROM users").fetchone():
                for user, pw, role in config.USERS:
                    h, salt = hash_password(pw)
                    conn.execute("INSERT INTO users VALUES (?,?,?,?)", (user, h, salt, role))
                cols = list(config.COMPANY)
                conn.execute(f"INSERT INTO company (id,{','.join(cols)}) VALUES (1,{','.join('?' * len(cols))})",
                             [config.COMPANY[c] for c in cols])
                conn.executemany("INSERT INTO settings VALUES (?,?)", config.SETTINGS.items())
                conn.executemany("INSERT INTO sss_table VALUES (?,?,?)", config.SSS_TABLE)
                conn.executemany("INSERT INTO tax_table VALUES (?,?,?,?)", config.TAX_TABLE)
            if not conn.execute("SELECT 1 FROM employees").fetchone():
                for e in config.DUMMY_EMPLOYEES:
                    conn.execute(f"INSERT INTO employees ({','.join(EMP_FIELDS)}) VALUES ({','.join('?' * 10)})",
                                 [e[f] for f in EMP_FIELDS])
    finally:
        conn.close()


# ---------------------------------------------------------------- login
# checks the username and password, returns the user or None
def authenticate(username, password):
    """Return {'username', 'role'} if valid, else None."""
    rows = query("SELECT * FROM users WHERE username=?", (username.strip().lower(),))
    if rows:
        h, _ = hash_password(password, rows[0]["salt"])
        if hmac.compare_digest(h, rows[0]["password_hash"]):
            return {"username": rows[0]["username"], "role": rows[0]["role"]}
    return None


# true if the role is allowed to do the action
def can(role, action):
    return action in config.PERMISSIONS.get(role, ())


# --------------------------------------------------------------- config
# loads rates, tax/SSS tables and company info into one dict
def load_config():
    """One dict with every setting plus SSS_TABLE, TAX_TABLE, COMPANY_INFO."""
    cfg = {r["key"]: r["value"] for r in query("SELECT * FROM settings")}
    inf = float("inf")
    cfg["SSS_TABLE"] = [(r["salary_min"], r["salary_max"] if r["salary_max"] is not None else inf,
                         r["employee_share"]) for r in query("SELECT * FROM sss_table ORDER BY salary_min")]
    cfg["TAX_TABLE"] = [(r["bracket_min"], r["bracket_max"] if r["bracket_max"] is not None else inf,
                         r["base_tax"], r["rate"]) for r in query("SELECT * FROM tax_table ORDER BY bracket_min")]
    cfg["COMPANY_INFO"] = query("SELECT * FROM company")[0]
    return cfg


# saves one changed rate
def update_setting(key, value):
    if key not in config.SETTINGS or float(value) < 0:
        raise ValueError("Invalid setting.")
    run("UPDATE settings SET value=? WHERE key=?", (float(value), key))


# company columns that can be edited
COMPANY_FIELDS = ["name", "address", "tin", "contact", "hr_name", "hr_title", "manager_name", "manager_title"]


# saves company, HR and manager info (names can't be blank)
def update_company(info):
    for f in ("name", "hr_name", "manager_name"):
        if not str(info.get(f, "")).strip():
            raise ValueError(f"{f.replace('_', ' ').title()} cannot be blank.")
    run(f"UPDATE company SET {','.join(f + '=?' for f in COMPANY_FIELDS)} WHERE id=1",
        [str(info.get(f, "")).strip() for f in COMPANY_FIELDS])


# finds the SSS share for the salary bracket
def lookup_sss(salary, sss_table):
    return next((s for lo, hi, s in sss_table if lo <= salary < hi), sss_table[-1][2])


# yearly tax = bracket base tax + rate on the amount over the bracket
def lookup_tax(annual_taxable, tax_table):
    return next((base + (annual_taxable - lo) * rate
                 for lo, hi, base, rate in tax_table if lo <= annual_taxable < hi), 0.0)


# ------------------------------------------------------------ employees
# employee columns in the order they are saved
EMP_FIELDS = ["employee_id", "full_name", "position", "department", "monthly_basic_salary",
              "sss_no", "philhealth_no", "pagibig_no", "tin_no", "status"]


# required fields and salary are checked before saving
def save_employee(emp):
    """Add a new employee, or update if the ID already exists."""
    for f in ("employee_id", "full_name", "position", "department"):
        if not str(emp.get(f, "")).strip():
            raise ValueError(f"{f} cannot be blank.")
    if float(emp.get("monthly_basic_salary", 0)) <= 0:
        raise ValueError("Salary must be greater than zero.")
    values = [emp.get(f, "regular" if f == "status" else "") for f in EMP_FIELDS]
    run(f"INSERT OR REPLACE INTO employees ({','.join(EMP_FIELDS)}) VALUES ({','.join('?' * 10)})", values)


# gets one employee by ID
def get_employee(employee_id):
    rows = query("SELECT * FROM employees WHERE employee_id=?", (employee_id,))
    return rows[0] if rows else None


# gets all employees, filtered by name or ID when searching
def list_employees(search=""):
    like = f"%{search}%"
    return query("SELECT * FROM employees WHERE full_name LIKE ? OR employee_id LIKE ? ORDER BY full_name", (like, like))


# ----------------------------------------------------------- attendance
# saves attendance for one cut-off, checks for negatives and valid dates
def save_attendance(employee_id, start, end, days_worked=0, absent_days=0, late_minutes=0,
                    ot_hours=0, night_diff_hours=0, expected_days=0,
                    regular_holiday_days=0, special_holiday_days=0):
    """Dates are 'YYYY-MM-DD'. Holiday values are the number of holidays actually worked."""
    nums = [days_worked, absent_days, late_minutes, ot_hours, night_diff_hours,
            expected_days, regular_holiday_days, special_holiday_days]
    if any(float(n) < 0 for n in nums):
        raise ValueError("Values cannot be negative.")
    datetime.strptime(start, "%Y-%m-%d"); datetime.strptime(end, "%Y-%m-%d")
    if end < start:
        raise ValueError("Period end is before period start.")
    if not get_employee(employee_id):
        raise ValueError("Employee not found.")
    run("INSERT OR REPLACE INTO attendance (employee_id, period_start, period_end, days_worked, absent_days,"
        " late_minutes, ot_hours, night_diff_hours, expected_days, regular_holiday_days, special_holiday_days)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)", (employee_id, start, end, *map(float, nums)))


# gets the saved attendance of an employee for a cut-off
def get_attendance(employee_id, start, end):
    rows = query("SELECT * FROM attendance WHERE employee_id=? AND period_start=? AND period_end=?",
                 (employee_id, start, end))
    return rows[0] if rows else None


# ------------------------------------------------------------- payslips
# saves a generated payslip (status starts as pending)
def save_payslip(data):
    """data = dict whose keys match the payslips columns. Returns payslip_id."""
    data = {**data, "created_at": datetime.now().isoformat(timespec="seconds")}
    return run(f"INSERT INTO payslips ({','.join(data)}) VALUES ({','.join('?' * len(data))})", list(data.values()))


# gets saved payslips, newest first
def list_payslips(employee_id=None):
    if employee_id:
        return query("SELECT * FROM payslips WHERE employee_id=? ORDER BY created_at DESC", (employee_id,))
    return query("SELECT * FROM payslips ORDER BY created_at DESC")


# checks if a payslip already exists for that employee and cut-off
def find_payslip(employee_id, start, end):
    rows = query("SELECT * FROM payslips WHERE employee_id=? AND period_start=? AND period_end=?",
                 (employee_id, start, end))
    return rows[0] if rows else None


# removes a payslip
def delete_payslip(payslip_id):
    run("DELETE FROM payslips WHERE payslip_id=?", (payslip_id,))


# marks the payslip as approved by the manager
def approve_payslip(payslip_id, manager):
    run("UPDATE payslips SET status='approved', approved_by=? WHERE payslip_id=?", (manager, payslip_id))


# run this file alone to just create the database
if __name__ == "__main__":
    init_db()
    print("Database ready:", config.DB_PATH)
