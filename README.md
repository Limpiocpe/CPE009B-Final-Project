<p align="center">
  <img src="banner.svg" alt="Payslip System" width="100%">
</p><img width="1000" height="220" alt="banner" src="https://github.com/user-attachments/assets/39ba0967-b569-45ca-89a0-cdfaad1aece4" /><svg xmlns="http://www.w3.org/2000/svg" width="1000" height="220" viewBox="0 0 1000 220">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1D4ED8"/><stop offset="1" stop-color="#0F172A"/></linearGradient></defs>
  <rect width="1000" height="220" rx="14" fill="url(#g)"/>
  <text x="500" y="100" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="52" font-weight="700" fill="#ffffff">Payslip System</text>
  <text x="500" y="145" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="22" fill="#BFD4FF">CPE009B (OOP2) Final Project · Group 5</text>
</svg>


# CPE009B-Final-Project

## 📖 About

The Orbit company handled payslips manually, which was slow and prone to computation errors. This project automates the process with a Python program that computes employee salaries and generates payslips.

HR enters the employee's details, days worked, overtime, holiday work, night shifts and tardiness for a cutoff period. The system then calculates gross pay, subtracts the deductions (SSS, Pag-IBIG, PhilHealth, tax, tardiness) and shows the net pay on a printable payslip, making payroll faster and more accurate.

## ✨ Features

- **Role-based login** — HR and Manager accounts see only the tabs they are allowed to use.
- **Employee management** — add and edit employees and their SSS, PhilHealth, Pag-IBIG and TIN numbers.
- **Attendance encoding** — days worked, absences, late minutes, overtime, night differential and holiday work per cut-off.
- **Automatic computation** — earnings, deductions, government contributions, withholding tax and net pay.
- **Live payslip preview** — the payslip updates as you type, before anything is saved.
- **PDF export** — save any payslip as an A4 PDF.
- **Approval workflow** — saved payslips start as drafts and are approved by a manager.
- **Editable settings** — company details, pay rates and contribution tables are edited in the app, with no code changes.
- **Optional 13th-month pay** — include it when generating a payslip.

- ## 👥 User Roles

| Role | Can do |
|---|---|
| **HR** | Manage employees, encode attendance, generate payslips, view saved payslips, edit settings |
| **Manager** | View saved payslips and approve them |

## 🧮 How Pay Is Computed

All formulas live in [`payroll.py`](payroll.py). Rates are configurable in the **Settings** tab.

| Item | Computation |
|---|---|
| Basic pay | Monthly salary ÷ cut-offs per month (2) |
| Daily / hourly / minute rate | Monthly ÷ 22 working days, ÷ 8 hours, ÷ 60 minutes |
| Overtime | Hourly rate × 1.25 × OT hours |
| Night differential | Hourly rate × 10% × night hours |
| Holiday pay | Extra pay over a normal day: regular holiday 200%, special holiday 130% |
| 13th-month (optional) | One month's salary minus days absent |
| **Gross pay** | Basic + overtime + night differential + holiday + 13th-month |
| Absence / late deduction | Daily rate × days absent · Minute rate × minutes late |
| SSS | Employee share from the bracket table (5% of monthly salary credit) ÷ cut-offs |
| PhilHealth | 5% premium on salary (₱10,000–₱100,000), employee pays half ÷ cut-offs |
| Pag-IBIG | 2% of salary, capped at ₱200/month ÷ cut-offs |
| Withholding tax | Taxable pay annualized, run through the TRAIN brackets, then divided back per cut-off |
| **Net pay** | Gross pay − total deductions |
