"""main.py - Payslip System. Run:  python main.py
Logins: hr / hr123 (HR)   manager / manager123 (MANAGER)"""

"""
main.py


INDEX  (function - line number)
  num()                    - 69
  parse_date()             - 86
  NoPayslip                - 95
  card()                   - 100
  field()                  - 107
  PayslipTab               - 125
      __init__()           - 132
      destroy()            - 220
      refresh()            - 227
      _picked()            - 239
      _fill_info()         - 245
      period()             - 256
      _period_changed()    - 269
      _expected_changed()  - 289
      _schedule()          - 297
      _update_absent()     - 304
      preview()            - 312
      _collect()           - 331
      generate()           - 355
      save_pdf()           - 383
      reset()              - 391
  EmployeeTab              - 403
      __init__()           - 409
      refresh()            - 440
      load()               - 447
      new()                - 455
      save()               - 460
  PayslipListTab           - 479
      __init__()           - 480
      refresh()            - 498
      _selected()          - 508
      view()               - 516
      approve()            - 530
  SettingsTab              - 539
      __init__()           - 556
      refresh()            - 576
      save()               - 590
      save_company()       - 599
  App                      - 609
      __init__()           - 616
      show()               - 668
"""
import calendar
import ctypes
import os
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk, messagebox

import database as db
import payroll
import theme
from login import ask_login
from output import PayslipPreview, PayslipView, build_model, export_pdf_dialog, fdate

# month names for the dropdown
MONTHS = list(calendar.month_name)[1:]
# the two cut-off choices
CUTOFFS = ["1st cutoff (1 - 15)", "2nd cutoff (16 - end)"]

# App icon: put orbit.ico in the same folder as main.py
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orbit.ico")


def num(var, label, strict=True):
    """Read a non-negative number. While typing (strict=False) a blank box counts as 0."""
    s = var.get().strip()
    if not s:
        if strict:
            raise ValueError(f"{label} cannot be blank.")
        return 0.0
    try:
        n = float(s)
    except ValueError:
        raise ValueError(f"{label} must be a number.")
    if n < 0:
        raise ValueError(f"{label} cannot be negative.")
    return n


# accepts a few date formats
def parse_date(text):
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError("Pay date must look like  Oct 15, 2026.")


class NoPayslip(ValueError):
    """Raised when there is nothing to show yet (no employee / no salary)."""


# makes a white box with a title
def card(parent, title):
    c = theme.Card(parent, title)
    c.pack(fill="x", pady=(0, 12), padx=(0, 8))
    c.body.columnconfigure((0, 1), weight=1, uniform="c")
    return c.body


def field(parent, row, col, label, kind, var, span=1, **kw):
    """Small grey caption above an input. kind: entry | ro | spin | combo."""
    cell = ttk.Frame(parent, style="Card.TFrame")
    cell.grid(row=row, column=col, columnspan=span, sticky="ew", padx=4, pady=3)
    ttk.Label(cell, text=label, style="Field.TLabel").pack(anchor="w")
    if kind == "ro":
        w = ttk.Entry(cell, textvariable=var, state="readonly", takefocus=False)
    elif kind == "spin":
        w = ttk.Spinbox(cell, textvariable=var, from_=0, to=kw.get("to", 9999), increment=kw.get("inc", 1))
    elif kind == "combo":
        w = ttk.Combobox(cell, textvariable=var, values=kw.get("values", []), state=kw.get("state", "readonly"))
    else:
        w = ttk.Entry(cell, textvariable=var)
    w.pack(fill="x")
    return w


# =============================================================== PAYSLIP TAB
class PayslipTab(ttk.Frame):
    # fields shown in the employee box (display only)
    INFO = [("full_name", "Full name"), ("employee_id", "Employee ID"), ("department", "Department"),
            ("position", "Position"), ("salary", "Monthly salary (PHP)"), ("status", "Status"),
            ("sss_no", "SSS No."), ("philhealth_no", "PhilHealth No."),
            ("pagibig_no", "Pag-IBIG MID No."), ("tin_no", "TIN")]

    def __init__(self, parent, app):
        super().__init__(parent)
        # employees list, rates and the delayed refresh job
        self.app, self.emps, self.cfg, self._job = app, {}, None, None
        self._loading, self._prev_expected = False, ""
        # variables tied to the form inputs
        today = date.today()
        self.emp = tk.StringVar()
        self.info = {k: tk.StringVar() for k, _ in self.INFO}
        self.year = tk.StringVar(value=str(today.year))
        self.month = tk.StringVar(value=MONTHS[today.month - 1])
        self.cutoff = tk.StringVar(value=CUTOFFS[0] if today.day <= 15 else CUTOFFS[1])
        self.pay = tk.StringVar()
        self.duration = tk.StringVar()
        self.expected, self.worked, self.absent = tk.StringVar(), tk.StringVar(), tk.StringVar(value="0")
        self.v = {k: tk.StringVar(value="0") for k in
                  ("late_minutes", "ot_hours", "night_diff_hours", "regular_holiday_days", "special_holiday_days")}
        self.bonus = tk.BooleanVar()

        # layout: form on the left, payslip on the right
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ------------------------------------------------ left: inputs
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        sf = theme.ScrollFrame(left)
        sf.canvas.configure(width=470)
        sf.pack(fill="both", expand=True)
        body = sf.inner

        # employee box
        emp = card(body, "Employee Information")
        self.emp_cb = field(emp, 0, 0, "Quick pick", "combo", self.emp, span=2)
        self.emp_cb.bind("<<ComboboxSelected>>", self._picked)
        for i, (k, t) in enumerate(self.INFO):
            field(emp, 1 + i // 2, i % 2, t, "ro", self.info[k])

        # pay period box
        per = card(body, "Cut-off / Pay Period")
        field(per, 0, 0, "Month", "combo", self.month, values=MONTHS)
        field(per, 0, 1, "Year", "spin", self.year, to=2100)
        for v in (self.month, self.year, self.cutoff):
            v.trace_add("write", lambda *_: self._period_changed())
        field(per, 1, 0, "Cut-off (kinsenas)", "combo", self.cutoff, values=CUTOFFS)
        self.pay_cb = field(per, 1, 1, "Pay date", "combo", self.pay, state="normal", values=[])
        ttk.Label(per, textvariable=self.duration, style="Info.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 0))

        # attendance and adjustments box
        att = card(body, "Attendance & Pay Adjustments")
        field(att, 0, 0, "Expected work days", "spin", self.expected, to=31)
        field(att, 0, 1, "Days worked (8 hrs)", "spin", self.worked, to=31)
        field(att, 1, 0, "Absent days (auto)", "ro", self.absent)
        field(att, 1, 1, "Late (minutes)", "spin", self.v["late_minutes"], to=9999, inc=5)
        field(att, 2, 0, "Overtime hours", "spin", self.v["ot_hours"], to=999, inc=0.5)
        field(att, 2, 1, "Night diff hours (10PM onwards)", "spin", self.v["night_diff_hours"], to=999, inc=0.5)
        field(att, 3, 0, "Regular holiday worked (double)", "spin", self.v["regular_holiday_days"], to=31)
        field(att, 3, 1, "Special holiday worked (+30%)", "spin", self.v["special_holiday_days"], to=31)
        ttk.Checkbutton(att, text="Include 13th month / bonus  (1 month - absent)", variable=self.bonus,
                        style="TCheckbutton").grid(row=4, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0))
        ttk.Button(att, text="Reset attendance", style="Link.TButton", command=self.reset).grid(
            row=5, column=1, sticky="e", pady=(4, 0))

        # update the payslip when any value changes
        for v in (self.expected, self.worked, self.pay, *self.v.values()):
            v.trace_add("write", lambda *_: self._schedule())
        self.bonus.trace_add("write", lambda *_: self._schedule())
        self.expected.trace_add("write", self._expected_changed)

        # buttons + messages stay visible under the scrolling form
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(4, 0), padx=(0, 8))
        bar.columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(bar, text="Generate Payslip", style="Primary.TButton", command=self.generate).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(bar, text="Save as PDF", command=self.save_pdf).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.msg = ttk.Label(bar, text="", style="Error.TLabel", wraplength=440)
        self.msg.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.saved = ttk.Label(bar, text="", style="Ok.TLabel", wraplength=440)
        self.saved.grid(row=2, column=0, columnspan=2, sticky="w")

        # ------------------------------------------------ right: live payslip
        self.view = PayslipView(self)
        self.view.grid(row=0, column=1, sticky="nsew")
        self._period_changed()

    # stop the pending refresh before closing
    def destroy(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()

    # ---- loading
    def refresh(self):
        """Called whenever this tab is shown: pick up employee / settings changes made elsewhere."""
        self.cfg = db.load_config()
        self.emps = {f"{e['employee_id']} - {e['full_name']}": e for e in db.list_employees()}
        self.emp_cb["values"] = list(self.emps)
        if self.emp.get() not in self.emps:
            ready = [k for k, e in self.emps.items() if e["monthly_basic_salary"] > 0]
            self.emp.set(ready[0] if ready else next(iter(self.emps), ""))
        self._fill_info()
        self.preview()

    # runs when an employee is chosen
    def _picked(self, _=None):
        self.saved.config(text="")
        self._fill_info()
        self.preview()

    # shows the chosen employee's details
    def _fill_info(self):
        e = self.emps.get(self.emp.get())
        for k, _ in self.INFO:
            if k == "salary":
                val = f"{e['monthly_basic_salary']:,.2f}" if e else ""
            else:
                val = (e.get(k) or "") if e else ""
            self.info[k].set(val)

    # ---- period
    # returns start date, end date and name of the selected cut-off
    def period(self):
        try:
            y, m = int(self.year.get()), MONTHS.index(self.month.get()) + 1
            if not 2000 <= y <= 2100:
                raise ValueError
            last = calendar.monthrange(y, m)[1]
        except ValueError:
            raise ValueError("Enter a valid month and year (2000-2100).")
        if self.cutoff.get() == CUTOFFS[0]:
            return date(y, m, 1), date(y, m, 15), "1st Kinsena"
        return date(y, m, 16), date(y, m, last), "2nd Kinsena"

    # updates duration, pay date and default work days when the period changes
    def _period_changed(self):
        try:
            s, e, _ = self.period()
        except ValueError as ex:
            self.duration.set(str(ex))
            return
        days = (e - s).days + 1
        self.duration.set(f"Cut-off duration: {days} days   ({fdate(s.isoformat())} - {fdate(e.isoformat())})")
        self.pay_cb["values"] = [fdate((e + timedelta(k)).isoformat()) for k in range(6)]
        self.pay.set(fdate(e.isoformat()))
        n = str(payroll.weekdays_between(s, e))
        self._loading = True
        self.expected.set(n)
        self.worked.set(n)
        self._loading = False
        self._prev_expected = n
        self.saved.config(text="")
        self._schedule()

    # keeps days worked equal to expected days unless the user changed it
    def _expected_changed(self, *_):
        new = self.expected.get()
        if not self._loading and self.worked.get() == self._prev_expected:
            self.worked.set(new)             # keep "worked = expected" until the user types a lower number
        self._prev_expected = new

    # ---- live preview
    # waits a moment before redrawing so typing doesn't lag
    def _schedule(self):
        self.saved.config(text="")
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(60, self.preview)

    # absent days = expected days - days worked
    def _update_absent(self):
        try:
            a = max(0.0, num(self.expected, "", False) - num(self.worked, "", False))
            self.absent.set(f"{a:g}")
        except ValueError:
            self.absent.set("?")

    # redraws the payslip on screen
    def preview(self):
        self._job = None
        if self.cfg is None:
            return
        self._update_absent()
        try:
            model = self._collect(False)[-1]
        except NoPayslip as ex:
            self.msg.config(text=str(ex))
            self.view.show_message(str(ex))
            return
        except ValueError as ex:                 # typing mistake: keep the last good payslip on screen
            self.msg.config(text=str(ex))
            return
        self.msg.config(text="")
        self.view.show(model)

    # ---- gather + compute
    # reads and checks all inputs, then computes the payslip
    def _collect(self, strict):
        emp = self.emps.get(self.emp.get())
        if not emp:
            raise NoPayslip("Pick an employee to see the payslip.")
        if emp["monthly_basic_salary"] <= 0:
            raise NoPayslip(f"{emp['full_name']} has no monthly salary yet.\nSet it in the Employees tab.")
        expected = num(self.expected, "Expected work days", strict)
        worked = num(self.worked, "Days worked", strict)
        if expected <= 0:
            raise ValueError("Expected work days must be more than 0.")
        if worked > expected:
            raise ValueError("Days worked cannot be more than the expected work days.")
        att = dict(expected_days=expected, days_worked=worked, absent_days=expected - worked,
                   **{k: num(var, k.replace("_", " ").capitalize(), strict) for k, var in self.v.items()})
        if att["regular_holiday_days"] + att["special_holiday_days"] > worked:
            raise ValueError("Holiday days worked cannot be more than days worked.")
        s, e, kin = self.period()
        pay = parse_date(self.pay.get())
        period = dict(start=s.isoformat(), end=e.isoformat(), pay_date=pay.isoformat(), kinsena=kin)
        r = payroll.compute_payslip(emp, att, self.cfg, self.bonus.get())
        return emp, period, att, r, build_model(emp, self.cfg["COMPANY_INFO"], period, att, r, self.cfg)

    # ---- buttons
    # saves the payslip (HR only), asks first if one already exists
    def generate(self):
        if not db.can(self.app.user["role"], "generate_payslip"):
            return messagebox.showerror("Access", "Your role cannot generate payslips.")
        try:
            emp, period, att, r, _ = self._collect(True)
        except ValueError as ex:
            return messagebox.showerror("Cannot generate", str(ex))
        old = db.find_payslip(emp["employee_id"], period["start"], period["end"])
        if old:
            if old["status"] == "approved":
                return messagebox.showerror("Already approved",
                                            "This employee already has an APPROVED payslip for this cut-off.")
            if not messagebox.askyesno("Replace payslip?", "A pending payslip already exists for this "
                                       "employee and cut-off.\nReplace it with the new numbers?"):
                return
            db.delete_payslip(old["payslip_id"])
        try:
            db.save_attendance(emp["employee_id"], period["start"], period["end"], att["days_worked"],
                               att["absent_days"], att["late_minutes"], att["ot_hours"], att["night_diff_hours"],
                               att["expected_days"], att["regular_holiday_days"], att["special_holiday_days"])
            pid = db.save_payslip(dict(employee_id=emp["employee_id"], period_start=period["start"],
                                       period_end=period["end"], pay_date=period["pay_date"],
                                       kinsena=period["kinsena"], **payroll.result_to_row(r)))
        except ValueError as ex:
            return messagebox.showerror("Cannot generate", str(ex))
        self.saved.config(text=f"Payslip #{pid} generated and saved - waiting for manager approval.")

    # exports the current payslip as a PDF
    def save_pdf(self):
        try:
            emp, period, _, _, model = self._collect(True)
        except ValueError as ex:
            return messagebox.showerror("Cannot save PDF", str(ex))
        export_pdf_dialog(model, f"payslip_{emp['employee_id']}_{period['start']}.pdf", self)

    # sets all the adjustments back to 0
    def reset(self):
        self._loading = True
        for var in self.v.values():
            var.set("0")
        self.worked.set(self.expected.get())
        self._loading = False
        self.bonus.set(False)
        self._schedule()


# ============================================================== EMPLOYEES TAB
# employees tab: add and edit employee records
class EmployeeTab(ttk.Frame):
    LABELS = [("employee_id", "Employee ID"), ("full_name", "Full Name"), ("position", "Position"),
              ("department", "Department"), ("monthly_basic_salary", "Monthly Basic Salary"),
              ("sss_no", "SSS No."), ("philhealth_no", "PhilHealth No."), ("pagibig_no", "Pag-IBIG MID No."),
              ("tin_no", "TIN No."), ("status", "Status")]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.f = {k: tk.StringVar() for k, _ in self.LABELS}
        self.f["status"].set("regular")
        fc = theme.Card(self, "Employee record", "All fields are required.")
        fc.pack(side="left", fill="y")
        form = fc.body
        form.columnconfigure((0, 1), weight=1, uniform="e")
        for i, (k, t) in enumerate(self.LABELS):
            kind = "combo" if k == "status" else "entry"
            field(form, i // 2, i % 2, t, kind, self.f[k], values=["regular", "probationary"]).configure(width=22)
        b = ttk.Frame(form, style="Card.TFrame")
        b.grid(row=len(self.LABELS) // 2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        b.columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(b, text="Save", style="Primary.TButton", command=self.save).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(b, text="New", command=self.new).grid(row=0, column=1, sticky="ew", padx=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self.search = tk.StringVar()
        ttk.Label(right, text="Search by name or ID. Select a row to edit it.", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        s = ttk.Entry(right, textvariable=self.search)
        s.pack(fill="x", pady=(0, 10))
        s.bind("<KeyRelease>", lambda _: self.refresh())
        box, self.tree = theme.make_tree(right, ("id", "name", "dept", "salary"),
                                         ("ID", "Name", "Department", "Monthly salary"), (80, 220, 150, 120), right=("salary",))
        box.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.load)

    # reloads the employee list (also used for search)
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(db.list_employees(self.search.get())):
            self.tree.insert("", "end", iid=e["employee_id"], tags=("odd",) if i % 2 else (), values=(
                e["employee_id"], e["full_name"], e["department"], f"{e['monthly_basic_salary']:,.2f}"))

    # fills the form with the selected employee
    def load(self, _=None):
        sel = self.tree.selection()
        if sel:
            e = db.get_employee(sel[0])
            for k in self.f:
                self.f[k].set(e[k] if e[k] is not None else "")

    # clears the form
    def new(self):
        for k, v in self.f.items():
            v.set("regular" if k == "status" else "")

    # checks the fields then saves the employee
    def save(self):
        emp = {k: v.get().strip() for k, v in self.f.items()}
        try:
            for k, t in self.LABELS:
                if not emp[k]:
                    raise ValueError(f"{t} cannot be blank.")
            try:
                emp["monthly_basic_salary"] = float(emp["monthly_basic_salary"].replace(",", ""))
            except ValueError:
                raise ValueError("Monthly Basic Salary must be a number.")
            db.save_employee(emp)
        except ValueError as ex:
            return messagebox.showerror("Employee", str(ex))
        self.refresh()
        messagebox.showinfo("Employee", "Saved.")


# ============================================================== PAYSLIPS TAB
# saved payslips tab: view, approve and export
class PayslipListTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        # columns of the table
        cols = ("id", "employee", "period", "pay_date", "gross", "net", "status")
        heads = ("ID", "Employee", "Period", "Pay date", "Gross pay", "Net pay", "Status")
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="View / PDF", style="Primary.TButton", command=self.view).pack(side="left")
        if db.can(app.user["role"], "approve_payslip"):
            ttk.Button(bar, text="Approve", command=self.approve).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Label(bar, text="Double-click a row to open it.", style="Sub.TLabel").pack(side="right")
        box, self.tree = theme.make_tree(self, cols, heads, (50, 200, 210, 110, 110, 110, 90), right=("gross", "net"))
        box.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _: self.view())

    # reloads the list of saved payslips
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, p in enumerate(db.list_payslips()):
            e = db.get_employee(p["employee_id"])
            self.tree.insert("", "end", iid=p["payslip_id"], tags=(p["status"],) if p["status"] in ("approved", "pending") else (("odd",) if i % 2 else ()), values=(
                p["payslip_id"], e["full_name"] if e else p["employee_id"],
                f"{fdate(p['period_start'])} - {fdate(p['period_end'])}", fdate(p["pay_date"]),
                f"{p['gross_pay']:,.2f}", f"{p['net_pay']:,.2f}", str(p["status"]).capitalize()))

    # returns the selected payslip, or asks the user to pick one
    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Payslips", "Select a payslip first.")
            return None
        return next(p for p in db.list_payslips() if str(p["payslip_id"]) == sel[0])

    # opens the selected payslip in a preview window
    def view(self):
        p = self._selected()
        if not p:
            return
        emp, cfg = db.get_employee(p["employee_id"]), db.load_config()
        if not emp:
            return messagebox.showerror("Payslips", "This employee no longer exists.")
        att = db.get_attendance(p["employee_id"], p["period_start"], p["period_end"]) or {}
        period = dict(start=p["period_start"], end=p["period_end"], pay_date=p["pay_date"], kinsena=p["kinsena"])
        model = build_model(emp, cfg["COMPANY_INFO"], period, att, payroll.row_to_result(p), cfg,
                            status=p["status"], approved_by=p["approved_by"])
        PayslipPreview(self, model, f"payslip_{p['employee_id']}_{p['period_start']}.pdf")

    # manager approves the payslip
    def approve(self):
        p = self._selected()
        if p and p["status"] != "approved":
            db.approve_payslip(p["payslip_id"], self.app.user["username"])
            self.refresh()


# =============================================================== SETTINGS TAB
# settings tab: company info and rates
class SettingsTab(ttk.Frame):
    # (column, label) for the company info fields
    COMPANY_LABELS = [("name", "Company name"), ("address", "Address"), ("tin", "Company TIN"),
                      ("contact", "Contact no."), ("hr_name", "HR officer (prepared by)"),
                      ("hr_title", "HR title"), ("manager_name", "Manager (approved by)"),
                      ("manager_title", "Manager title")]
    # readable names for each rate
    RATE_LABELS = {
        "WORKING_DAYS_PER_MONTH": "Working days per month (daily rate = salary / this)",
        "HOURS_PER_DAY": "Hours per day", "OT_RATE": "Overtime rate (1.25 = +25%)",
        "NIGHT_DIFF_RATE": "Night differential (0.10 = +10%)",
        "REGULAR_HOLIDAY_RATE": "Regular holiday worked (2 = double)",
        "SPECIAL_HOLIDAY_RATE": "Special holiday worked (1.3 = +30%)", "CUTOFFS_PER_MONTH": "Cut-offs per month",
        "PHILHEALTH_RATE": "PhilHealth rate (total premium)", "PHILHEALTH_MIN": "PhilHealth salary floor",
        "PHILHEALTH_MAX": "PhilHealth salary ceiling", "PAGIBIG_RATE": "Pag-IBIG rate",
        "PAGIBIG_CAP": "Pag-IBIG max per month", "BONUS_TAX_EXEMPT": "13th month tax-exempt up to"}

    def __init__(self, parent, app):
        super().__init__(parent)
        self.vars, self.cvars = {}, {k: tk.StringVar() for k, _ in self.COMPANY_LABELS}
        lc = theme.Card(self, "Company, HR & Manager", "Printed on every payslip.")
        lc.pack(side="left", fill="y", anchor="n")
        left = lc.body
        left.columnconfigure(0, weight=1)
        for i, (k, t) in enumerate(self.COMPANY_LABELS):
            field(left, i, 0, t, "entry", self.cvars[k]).configure(width=38)
        ttk.Button(left, text="Save company info", style="Primary.TButton", command=self.save_company).grid(
            row=len(self.COMPANY_LABELS), column=0, sticky="ew", padx=4, pady=(10, 0))

        rc = theme.Card(self, "Rates", "Government rates change. Edit them here, then save.")
        rc.pack(side="left", fill="y", anchor="n", padx=(16, 0))
        right = rc.body
        self.box = ttk.Frame(right, style="Card.TFrame")
        self.box.pack(anchor="w")
        ttk.Button(right, text="Save rates", style="Primary.TButton", command=self.save).pack(anchor="w", pady=(10, 0))

    # loads the company info and rates into the boxes
    def refresh(self):
        info = db.load_config()["COMPANY_INFO"]
        for k, _ in self.COMPANY_LABELS:
            self.cvars[k].set(info.get(k) or "")
        for w in self.box.winfo_children():
            w.destroy()
        self.vars = {}
        for i, r in enumerate(db.query("SELECT * FROM settings ORDER BY rowid")):
            self.vars[r["key"]] = tk.StringVar(value=f"{r['value']:g}")
            ttk.Label(self.box, text=self.RATE_LABELS.get(r["key"], r["key"]), style="Card.TLabel").grid(
                row=i, column=0, sticky="w", padx=(0, 14), pady=3)
            ttk.Entry(self.box, textvariable=self.vars[r["key"]], width=12).grid(row=i, column=1, pady=3)

    # saves the edited rates
    def save(self):
        try:
            for k, v in self.vars.items():
                db.update_setting(k, v.get())
        except ValueError:
            return messagebox.showerror("Settings", "All values must be non-negative numbers.")
        messagebox.showinfo("Settings", "Saved.")

    # saves the company info
    def save_company(self):
        try:
            db.update_company({k: v.get() for k, v in self.cvars.items()})
        except ValueError as ex:
            return messagebox.showerror("Company", str(ex))
        messagebox.showinfo("Company", "Saved.")


# ==================================================================== APP
# main window after login
class App(tk.Tk):
    # title and subtitle of each tab
    PAGES = {"Payslip": ("Payslip", "Pick an employee and a cut-off. The payslip updates as you type."),
             "Employees": ("Employees", "Add people and keep their contribution numbers up to date."),
             "Saved Payslips": ("Saved payslips", "Review generated payslips, approve them and export PDFs."),
             "Settings": ("Settings", "Company details and the rates used in every computation.")}

    def __init__(self, user):
        super().__init__()
        theme.apply_theme(self)
        try:
            self.iconbitmap(ICON_PATH)          # window + taskbar icon (orbit.ico)
        except tk.TclError:
            pass                                # icon missing: keep the default one
        self.user = user
        self.title(f"Payslip System - {user['username']} ({user['role']})")
        self.geometry(f"1280x{min(900, self.winfo_screenheight() - 80)}")
        self.minsize(1100, 680)
        F = theme.FONT

        # top bar with the tab buttons
        top = tk.Frame(self, bg=theme.SIDEBAR)
        top.pack(side="top", fill="x")
        tk.Label(top, text="Payslip System", bg=theme.SIDEBAR, fg="white", font=(F, 13, "bold")).pack(
            side="left", padx=(24, 28), pady=10)
        side = top
        main = ttk.Frame(self)
        main.pack(side="top", fill="both", expand=True)
        # page title area
        head = ttk.Frame(main, padding=(28, 20, 28, 8))
        head.pack(fill="x")
        self.h_title = ttk.Label(head, style="Title.TLabel")
        self.h_title.pack(anchor="w")
        self.h_sub = ttk.Label(head, style="Sub.TLabel")
        self.h_sub.pack(anchor="w", pady=(2, 0))
        self.stage = ttk.Frame(main, padding=(28, 6, 28, 20))
        self.stage.pack(fill="both", expand=True)

        # only create the tabs that the user's role is allowed to use
        self.tabs, self.nav, self.current = {}, {}, None
        role = user["role"]
        for perm, cls, name in (("generate_payslip", PayslipTab, "Payslip"),
                                ("manage_employees", EmployeeTab, "Employees"),
                                ("view_payslips", PayslipListTab, "Saved Payslips"),
                                ("edit_settings", SettingsTab, "Settings")):
            if db.can(role, perm):
                self.tabs[name] = cls(self.stage, self)
                item = theme.NavItem(side, name, lambda n=name: self.show(n))
                item.pack(side="left")
                self.nav[name] = item

        # shows who is logged in
        who = tk.Label(top, text=f"{user['username']}  \u00b7  {'HR' if role == 'HR' else role.title()}",
                       bg=theme.SIDEBAR, fg=theme.SIDEBAR_TXT, font=(F, 9))
        who.pack(side="right", padx=24)
        if self.tabs:
            self.show(next(iter(self.tabs)))

    # switches to another tab
    def show(self, name):
        if self.current:
            self.tabs[self.current].pack_forget()
            self.nav[self.current].set_active(False)
        self.current = name
        self.nav[name].set_active(True)
        title, sub = self.PAGES[name]
        self.h_title.config(text=title)
        self.h_sub.config(text=sub)
        tab = self.tabs[name]
        tab.pack(fill="both", expand=True)
        if hasattr(tab, "refresh"):
            tab.refresh()


if __name__ == "__main__":
    # Makes Windows show orbit.ico in the taskbar instead of the Python icon
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("orbit.payslip.system")
    except Exception:
        pass
    # start: set up the database, log in, then open the app
    db.init_db()
    user = ask_login()
    if user:
        App(user).mainloop()
