"""main.py - Payslip System. Run:  python main.py
Logins: hr / hr123 (HR)   manager / manager123 (MANAGER)"""
import calendar
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk, messagebox

import database as db
import payroll
import theme
from login import ask_login
from output import PayslipPreview, PayslipView, build_model, export_pdf_dialog, fdate

MONTHS = list(calendar.month_name)[1:]
CUTOFFS = ["1st cutoff (1 - 15)", "2nd cutoff (16 - end)"]


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


def parse_date(text):
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError("Pay date must look like  Oct 15, 2026.")


class NoPayslip(ValueError):
    """Raised when there is nothing to show yet (no employee / no salary)."""


def card(parent, title):
    lf = ttk.LabelFrame(parent, text=title, padding=(8, 4, 8, 10))
    lf.pack(fill="x", pady=(0, 10), padx=(0, 6))
    lf.columnconfigure((0, 1), weight=1, uniform="c")
    return lf


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
    INFO = [("full_name", "Full name"), ("employee_id", "Employee ID"), ("department", "Department"),
            ("position", "Position"), ("salary", "Monthly salary (PHP)"), ("status", "Status"),
            ("sss_no", "SSS No."), ("philhealth_no", "PhilHealth No."),
            ("pagibig_no", "Pag-IBIG MID No."), ("tin_no", "TIN")]

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app, self.emps, self.cfg, self._job = app, {}, None, None
        self._loading, self._prev_expected = False, ""
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

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ------------------------------------------------ left: inputs
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        sf = theme.ScrollFrame(left)
        sf.canvas.configure(width=470)
        sf.pack(fill="both", expand=True)
        body = sf.inner

        emp = card(body, "Employee Information")
        self.emp_cb = field(emp, 0, 0, "Quick pick", "combo", self.emp, span=2)
        self.emp_cb.bind("<<ComboboxSelected>>", self._picked)
        for i, (k, t) in enumerate(self.INFO):
            field(emp, 1 + i // 2, i % 2, t, "ro", self.info[k])

        per = card(body, "Cut-off / Pay Period")
        field(per, 0, 0, "Month", "combo", self.month, values=MONTHS)
        field(per, 0, 1, "Year", "spin", self.year, to=2100)
        for v in (self.month, self.year, self.cutoff):
            v.trace_add("write", lambda *_: self._period_changed())
        field(per, 1, 0, "Cut-off (kinsenas)", "combo", self.cutoff, values=CUTOFFS)
        self.pay_cb = field(per, 1, 1, "Pay date", "combo", self.pay, state="normal", values=[])
        ttk.Label(per, textvariable=self.duration, style="Info.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 0))

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

        for v in (self.expected, self.worked, self.pay, *self.v.values()):
            v.trace_add("write", lambda *_: self._schedule())
        self.bonus.trace_add("write", lambda *_: self._schedule())
        self.expected.trace_add("write", self._expected_changed)

        # buttons + messages stay visible under the scrolling form
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(6, 0), padx=(0, 6))
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

    def _picked(self, _=None):
        self.saved.config(text="")
        self._fill_info()
        self.preview()

    def _fill_info(self):
        e = self.emps.get(self.emp.get())
        for k, _ in self.INFO:
            if k == "salary":
                val = f"{e['monthly_basic_salary']:,.2f}" if e else ""
            else:
                val = (e.get(k) or "") if e else ""
            self.info[k].set(val)

    # ---- period
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

    def _expected_changed(self, *_):
        new = self.expected.get()
        if not self._loading and self.worked.get() == self._prev_expected:
            self.worked.set(new)             # keep "worked = expected" until the user types a lower number
        self._prev_expected = new

    # ---- live preview
    def _schedule(self):
        self.saved.config(text="")
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(60, self.preview)

    def _update_absent(self):
        try:
            a = max(0.0, num(self.expected, "", False) - num(self.worked, "", False))
            self.absent.set(f"{a:g}")
        except ValueError:
            self.absent.set("?")

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

    def save_pdf(self):
        try:
            emp, period, _, _, model = self._collect(True)
        except ValueError as ex:
            return messagebox.showerror("Cannot save PDF", str(ex))
        export_pdf_dialog(model, f"payslip_{emp['employee_id']}_{period['start']}.pdf", self)

    def reset(self):
        self._loading = True
        for var in self.v.values():
            var.set("0")
        self.worked.set(self.expected.get())
        self._loading = False
        self.bonus.set(False)
        self._schedule()


# ============================================================== EMPLOYEES TAB
class EmployeeTab(ttk.Frame):
    LABELS = [("employee_id", "Employee ID"), ("full_name", "Full Name"), ("position", "Position"),
              ("department", "Department"), ("monthly_basic_salary", "Monthly Basic Salary"),
              ("sss_no", "SSS No."), ("philhealth_no", "PhilHealth No."), ("pagibig_no", "Pag-IBIG MID No."),
              ("tin_no", "TIN No."), ("status", "Status")]

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.f = {k: tk.StringVar() for k, _ in self.LABELS}
        self.f["status"].set("regular")
        form = ttk.LabelFrame(self, text="Employee record (all fields required)", padding=(8, 4, 8, 10))
        form.pack(side="left", fill="y")
        form.columnconfigure(0, weight=1)
        for i, (k, t) in enumerate(self.LABELS):
            kind = "combo" if k == "status" else "entry"
            field(form, i, 0, t, kind, self.f[k], values=["regular", "probationary"])
        b = ttk.Frame(form, style="Card.TFrame")
        b.grid(row=len(self.LABELS), column=0, pady=(10, 0), sticky="ew")
        b.columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(b, text="Save", style="Primary.TButton", command=self.save).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(b, text="New", command=self.new).grid(row=0, column=1, sticky="ew", padx=4)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        ttk.Label(right, text="Search by name or ID", foreground=theme.MUTED).pack(anchor="w")
        self.search = tk.StringVar()
        s = ttk.Entry(right, textvariable=self.search)
        s.pack(fill="x", pady=(2, 6))
        s.bind("<KeyRelease>", lambda _: self.refresh())
        self.tree = ttk.Treeview(right, columns=("id", "name", "dept", "salary"), show="headings")
        for c, t, w in (("id", "ID", 80), ("name", "Name", 220), ("dept", "Department", 150), ("salary", "Monthly salary", 110)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="e" if c == "salary" else "w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.load)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for e in db.list_employees(self.search.get()):
            self.tree.insert("", "end", iid=e["employee_id"], values=(
                e["employee_id"], e["full_name"], e["department"], f"{e['monthly_basic_salary']:,.2f}"))

    def load(self, _=None):
        sel = self.tree.selection()
        if sel:
            e = db.get_employee(sel[0])
            for k in self.f:
                self.f[k].set(e[k] if e[k] is not None else "")

    def new(self):
        for k, v in self.f.items():
            v.set("regular" if k == "status" else "")

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
class PayslipListTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        cols = ("id", "employee", "period", "pay_date", "gross", "net", "status")
        heads = ("ID", "Employee", "Period", "Pay date", "Gross pay", "Net pay", "Status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c, t, w in zip(cols, heads, (50, 200, 210, 110, 110, 110, 90)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="e" if c in ("gross", "net") else "w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _: self.view())
        bar = ttk.Frame(self)
        bar.pack(pady=8)
        ttk.Button(bar, text="View / PDF", style="Primary.TButton", command=self.view).pack(side="left", padx=4)
        if db.can(app.user["role"], "approve_payslip"):
            ttk.Button(bar, text="Approve", command=self.approve).pack(side="left", padx=4)
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left", padx=4)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for p in db.list_payslips():
            e = db.get_employee(p["employee_id"])
            self.tree.insert("", "end", iid=p["payslip_id"], values=(
                p["payslip_id"], e["full_name"] if e else p["employee_id"],
                f"{fdate(p['period_start'])} - {fdate(p['period_end'])}", fdate(p["pay_date"]),
                f"{p['gross_pay']:,.2f}", f"{p['net_pay']:,.2f}", p["status"]))

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Payslips", "Select a payslip first.")
            return None
        return next(p for p in db.list_payslips() if str(p["payslip_id"]) == sel[0])

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

    def approve(self):
        p = self._selected()
        if p and p["status"] != "approved":
            db.approve_payslip(p["payslip_id"], self.app.user["username"])
            self.refresh()


# =============================================================== SETTINGS TAB
class SettingsTab(ttk.Frame):
    COMPANY_LABELS = [("name", "Company name"), ("address", "Address"), ("tin", "Company TIN"),
                      ("contact", "Contact no."), ("hr_name", "HR officer (prepared by)"),
                      ("hr_title", "HR title"), ("manager_name", "Manager (approved by)"),
                      ("manager_title", "Manager title")]
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
        super().__init__(parent, padding=10)
        self.vars, self.cvars = {}, {k: tk.StringVar() for k, _ in self.COMPANY_LABELS}
        left = ttk.LabelFrame(self, text="Company, HR & Manager (printed on payslips)", padding=(8, 4, 8, 10))
        left.pack(side="left", fill="y", anchor="n")
        left.columnconfigure(0, weight=1)
        for i, (k, t) in enumerate(self.COMPANY_LABELS):
            field(left, i, 0, t, "entry", self.cvars[k]).configure(width=38)
        ttk.Button(left, text="Save company info", style="Primary.TButton", command=self.save_company).grid(
            row=len(self.COMPANY_LABELS), column=0, sticky="ew", padx=4, pady=(10, 0))

        right = ttk.LabelFrame(self, text="Rates (government rates change - edit, then save)", padding=(8, 4, 8, 10))
        right.pack(side="left", fill="y", anchor="n", padx=(12, 0))
        self.box = ttk.Frame(right, style="Card.TFrame")
        self.box.pack(anchor="w")
        ttk.Button(right, text="Save rates", style="Primary.TButton", command=self.save).pack(anchor="w", pady=(10, 0))

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

    def save(self):
        try:
            for k, v in self.vars.items():
                db.update_setting(k, v.get())
        except ValueError:
            return messagebox.showerror("Settings", "All values must be non-negative numbers.")
        messagebox.showinfo("Settings", "Saved.")

    def save_company(self):
        try:
            db.update_company({k: v.get() for k, v in self.cvars.items()})
        except ValueError as ex:
            return messagebox.showerror("Company", str(ex))
        messagebox.showinfo("Company", "Saved.")


# ==================================================================== APP
class App(tk.Tk):
    def __init__(self, user):
        super().__init__()
        theme.apply_theme(self)
        self.user = user
        self.title(f"Payslip System - {user['username']} ({user['role']})")
        self.geometry(f"1280x{min(900, self.winfo_screenheight() - 80)}")
        self.minsize(1100, 680)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        role = user["role"]
        for perm, cls, title in (("generate_payslip", PayslipTab, "Payslip"),
                                 ("manage_employees", EmployeeTab, "Employees"),
                                 ("view_payslips", PayslipListTab, "Saved Payslips"),
                                 ("edit_settings", SettingsTab, "Settings")):
            if db.can(role, perm):
                self.nb.add(cls(self.nb, self), text=f"  {title}  ")
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        self._tab_changed()

    def _tab_changed(self, _=None):
        tab = self.nametowidget(self.nb.select())
        if hasattr(tab, "refresh"):
            tab.refresh()


if __name__ == "__main__":
    db.init_db()
    user = ask_login()
    if user:
        App(user).mainloop()
