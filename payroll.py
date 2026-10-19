"""payroll.py - all computation logic. Pure functions, no GUI."""
from datetime import timedelta

from database import lookup_sss, lookup_tax


def r2(x):
    """Round to centavos so the printed lines always add up to the printed totals."""
    return round(x + 1e-9, 2)


def weekdays_between(start, end):
    """Mon-Fri count between two dates (inclusive) = default expected work days of a cut-off."""
    n, d = 0, start
    while d <= end:
        n += d.weekday() < 5
        d += timedelta(days=1)
    return n


def compute_rates(monthly, cfg):
    daily = monthly / cfg["WORKING_DAYS_PER_MONTH"]
    hourly = daily / cfg["HOURS_PER_DAY"]
    return daily, hourly, hourly / 60


def compute_payslip(emp, att, cfg, include_13th=False):
    """emp = employee row.
    att = dict(absent_days, late_minutes, ot_hours, night_diff_hours,
               regular_holiday_days, special_holiday_days).
    Returns one result dict (every money value already rounded to 2 decimals)."""
    monthly = emp["monthly_basic_salary"]
    cutoffs = int(cfg["CUTOFFS_PER_MONTH"])
    daily, hourly, minute = compute_rates(monthly, cfg)

    # ---- earnings
    basic_pay = r2(monthly / cutoffs)                                   # fixed half-month (kinsenas)
    ot_pay = r2(hourly * cfg["OT_RATE"] * att["ot_hours"])
    night_diff_pay = r2(hourly * cfg["NIGHT_DIFF_RATE"] * att["night_diff_hours"])
    # holiday pay = the EXTRA over a normal day (the day's regular pay is already inside basic pay)
    holiday_regular = r2(daily * (cfg["REGULAR_HOLIDAY_RATE"] - 1) * att["regular_holiday_days"])
    holiday_special = r2(daily * (cfg["SPECIAL_HOLIDAY_RATE"] - 1) * att["special_holiday_days"])
    holiday_pay = r2(holiday_regular + holiday_special)
    # 13th month / bonus: one full month minus the days absent
    bonus = r2(max(0.0, monthly - daily * att["absent_days"])) if include_13th else 0.0
    gross = r2(basic_pay + ot_pay + night_diff_pay + holiday_pay + bonus)

    # ---- attendance deductions
    absent_ded = r2(daily * att["absent_days"])
    late_ded = r2(minute * att["late_minutes"])

    # ---- government contributions (monthly employee share / cutoffs)
    sss = r2(lookup_sss(monthly, cfg["SSS_TABLE"]) / cutoffs)
    ph_base = max(cfg["PHILHEALTH_MIN"], min(cfg["PHILHEALTH_MAX"], monthly))
    philhealth = r2(ph_base * cfg["PHILHEALTH_RATE"] / 2 / cutoffs)
    pagibig = r2(min(monthly * cfg["PAGIBIG_RATE"], cfg["PAGIBIG_CAP"]) / cutoffs)
    gov = sss + philhealth + pagibig

    # ---- withholding tax (annualized; 13th month exempt up to the cap)
    exempt = min(bonus, cfg["BONUS_TAX_EXEMPT"])
    taxable = max(0.0, gross - exempt - absent_ded - late_ded - gov)
    periods_per_year = cutoffs * 12
    tax = r2(lookup_tax(taxable * periods_per_year, cfg["TAX_TABLE"]) / periods_per_year)

    total_ded = r2(absent_ded + late_ded + sss + philhealth + pagibig + tax)
    return dict(basic_pay=basic_pay, ot_pay=ot_pay, night_diff_pay=night_diff_pay,
                holiday_pay=holiday_pay, holiday_regular=holiday_regular, holiday_special=holiday_special,
                bonus=bonus, gross=gross,
                absent_ded=absent_ded, late_ded=late_ded, sss=sss, philhealth=philhealth,
                pagibig=pagibig, tax=tax, taxable=r2(taxable), total_ded=total_ded,
                net=r2(gross - total_ded), daily_rate=daily, hourly_rate=hourly)


def result_to_row(r):
    """Result dict -> payslips table columns."""
    return dict(basic_pay=r["basic_pay"], ot_pay=r["ot_pay"], night_diff_pay=r["night_diff_pay"],
                holiday_pay=r["holiday_pay"], bonus_13th=r["bonus"], gross_pay=r["gross"],
                absent_deduction=r["absent_ded"], late_deduction=r["late_ded"], sss=r["sss"],
                philhealth=r["philhealth"], pagibig=r["pagibig"], tax=r["tax"],
                total_deductions=r["total_ded"], net_pay=r["net"])


def row_to_result(row):
    """payslips table row -> result dict (for re-printing saved payslips)."""
    return dict(basic_pay=row["basic_pay"], ot_pay=row["ot_pay"], night_diff_pay=row["night_diff_pay"],
                holiday_pay=row["holiday_pay"], bonus=row["bonus_13th"], gross=row["gross_pay"],
                absent_ded=row["absent_deduction"], late_ded=row["late_deduction"], sss=row["sss"],
                philhealth=row["philhealth"], pagibig=row["pagibig"], tax=row["tax"],
                total_ded=row["total_deductions"], net=row["net_pay"])
