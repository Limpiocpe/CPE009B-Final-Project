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
