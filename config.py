"""config.py - default seed data. Seeded into the SQLite DB on first run;
after that, edit rates and company/HR/manager names in the app's Settings tab (stored in the DB)."""
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payslip.db")

USERS = [("hr", "hr123", "HR"), ("manager", "manager123", "MANAGER")]   # dummy logins

PERMISSIONS = {
    "HR": ("manage_employees", "encode_attendance", "generate_payslip", "view_payslips", "edit_settings"),
    "MANAGER": ("view_payslips", "approve_payslip"),
}

# Company + the dummy HR officer / manager whose names are printed on every payslip
COMPANY = dict(
    name="Sample Trading Corporation",
    address="123 Sample St., Quezon City, Metro Manila",
    tin="000-111-222-000",
    contact="(02) 8000-0000",
    hr_name="Maria Santos", hr_title="HR Officer",
    manager_name="Roberto Reyes", manager_title="General Manager",
)

SETTINGS = {
    "WORKING_DAYS_PER_MONTH": 22,    # daily rate = monthly salary / this
    "HOURS_PER_DAY": 8,
    "OT_RATE": 1.25,                 # overtime = 125% of hourly rate
    "NIGHT_DIFF_RATE": 0.10,         # night differential = +10% of hourly rate (10PM-6AM)
    "REGULAR_HOLIDAY_RATE": 2.00,    # regular holiday worked = double (200%) of daily rate
    "SPECIAL_HOLIDAY_RATE": 1.30,    # special non-working holiday worked = 130%
    "CUTOFFS_PER_MONTH": 2,          # kinsenas
    "PHILHEALTH_RATE": 0.05,         # total premium, employee pays half
    "PHILHEALTH_MIN": 10000,
    "PHILHEALTH_MAX": 100000,
    "PAGIBIG_RATE": 0.02,
    "PAGIBIG_CAP": 200,              # max employee share per month
    "BONUS_TAX_EXEMPT": 90000,       # 13th month + other benefits exempt up to this
}

# SSS: employee share 5% of Monthly Salary Credit (MSC 5,000-35,000, steps of 500)
SSS_TABLE = [(0 if m == 5000 else m - 250, None if m == 35000 else m + 250, m * 0.05)
             for m in range(5000, 35001, 500)]

# Annual withholding tax brackets (TRAIN, 2023 onward): (min, max, base_tax, rate)
TAX_TABLE = [(0, 250000, 0, 0.0), (250000, 400000, 0, 0.15), (400000, 800000, 22500, 0.20),
             (800000, 2000000, 102500, 0.25), (2000000, 8000000, 402500, 0.30),
             (8000000, None, 2202500, 0.35)]

DUMMY_EMPLOYEES = [
    dict(employee_id="EMP-001", full_name="Katindig, Jiro Luis A.", position="Software Developer",
         department="IT Department", monthly_basic_salary=30000, sss_no="34-1234567-8",
         philhealth_no="12-345678901-2", pagibig_no="1234-5678-9012", tin_no="123-456-789-000", status="regular"),
    dict(employee_id="EMP-002", full_name="Clint Hoven Estorco", position="Employee",
         department="Unassigned", monthly_basic_salary=0, sss_no="",
         philhealth_no="", pagibig_no="", tin_no="", status="regular"),
    dict(employee_id="EMP-003", full_name="Ramelissa Melith Limpio", position="Employee",
         department="Unassigned", monthly_basic_salary=0, sss_no="",
         philhealth_no="", pagibig_no="", tin_no="", status="regular"),
    dict(employee_id="EMP-004", full_name="Eunice Moradillo", position="Employee",
         department="Unassigned", monthly_basic_salary=0, sss_no="",
         philhealth_no="", pagibig_no="", tin_no="", status="regular"),
    dict(employee_id="EMP-005", full_name="Jaime Demain", position="Employee",
         department="Unassigned", monthly_basic_salary=0, sss_no="",
         philhealth_no="", pagibig_no="", tin_no="", status="regular"),
]
