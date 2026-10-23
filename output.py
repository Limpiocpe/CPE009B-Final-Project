"""output.py - payslip model, on-screen payslip (live preview), preview window and PDF export.

build_model() turns the computed numbers into one plain dict. BOTH the screen view and the PDF are
drawn from that dict, so what you see on screen is exactly what gets printed."""
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk, messagebox, filedialog

import payroll
import theme

# colors used on the payslip
PAPER, HDR, GRAY, LIGHT = "white", "#6B8CB9", "#D9DCE1", "#EAEEF4"


# formats a number like 1,234.50
def peso(x):
    return f"{x:,.2f}"


# turns 2026-10-15 into Oct 15, 2026
def fdate(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%b %d, %Y")


def _n(x, unit):
    """'1 day', '2 days', '1.5 hrs' ..."""
    return f"{x:g} {unit}" if x == 1 else f"{x:g} {unit}s"


# turns 0.25 into 25
def _pct(x):
    return f"{x * 100:g}"


# ====================================================================== MODEL
"""Transforms raw computation outputs into a unified data contract. Because both on-screen rendering and PDF export consume this same dictionary,there is zero discrepancy between what is viewed and what is printed."""
def build_model(emp, company, period, att, r, cfg, status="draft", approved_by=None):
    """emp/company/period/att/r as used by payroll.compute_payslip -> dict ready to draw."""
    # work out the rates and dates first
    monthly = emp["monthly_basic_salary"]
    daily, hourly, minute = payroll.compute_rates(monthly, cfg)
    sd, ed = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
    cal_days = (ed - sd).days + 1
    expected = att.get("expected_days") or payroll.weekdays_between(sd, ed)
    absent, late = att.get("absent_days", 0), att.get("late_minutes", 0)
    worked = att.get("days_worked", expected - absent)
    ot_h, nd_h = att.get("ot_hours", 0), att.get("night_diff_hours", 0)
    reg_d, spe_d = att.get("regular_holiday_days", 0) or 0, att.get("special_holiday_days", 0) or 0

    hol_reg = r.get("holiday_regular")      # saved payslips only store the holiday total, so rebuild the split
    if hol_reg is None:
        hol_reg = payroll.r2(daily * (cfg["REGULAR_HOLIDAY_RATE"] - 1) * reg_d)
    hol_spe = r.get("holiday_special")
    if hol_spe is None:
        hol_spe = payroll.r2(daily * (cfg["SPECIAL_HOLIDAY_RATE"] - 1) * spe_d)
    # rows for the earnings table: (label, hours/days, rate, amount)
    earnings = [
        ("Basic Pay (semi-monthly)", _n(expected, "day"), peso(daily), r["basic_pay"]),
        (f"Overtime (+{_pct(cfg['OT_RATE'] - 1)}%)", _n(ot_h, "hr"), peso(hourly * cfg["OT_RATE"]), r["ot_pay"]),
        (f"Night Differential (+{_pct(cfg['NIGHT_DIFF_RATE'])}%)", _n(nd_h, "hr"),
         peso(hourly * cfg["NIGHT_DIFF_RATE"]), r["night_diff_pay"]),
        ("Regular Holiday Pay (double)", _n(reg_d, "day"),
         peso(daily * (cfg["REGULAR_HOLIDAY_RATE"] - 1)), hol_reg),
        (f"Special Holiday Pay (+{_pct(cfg['SPECIAL_HOLIDAY_RATE'] - 1)}%)", _n(spe_d, "day"),
         peso(daily * (cfg["SPECIAL_HOLIDAY_RATE"] - 1)), hol_spe),
        ("13th Month / Bonus", "1 month - absent" if r["bonus"] else "", "", r["bonus"]),
    ]
    # rows for the deductions table: (label, details, amount)
    deductions = [
        (f"Absent ({absent:g} days)", f"{absent:g} x {peso(daily)}", r["absent_ded"]),
        (f"Tardiness ({late:g} min)", f"{late:g} x {peso(minute)} per min", r["late_ded"]),
        ("SSS Contribution", f"SSS No. {emp['sss_no'] or '-'}", r["sss"]),
        ("PhilHealth", f"PhilHealth No. {emp['philhealth_no'] or '-'}", r["philhealth"]),
        ("Pag-IBIG", f"MID No. {emp['pagibig_no'] or '-'}", r["pagibig"]),
        ("Withholding Tax", f"TIN {emp['tin_no'] or '-'}", r["tax"]),
    ]
    # everything the payslip needs, in one dict
    return dict(
        company=dict(name=company["name"], address=company["address"], tin=company["tin"],
                     contact=company.get("contact") or ""),
        hr=f"{company['hr_name']} ({company['hr_title']})", hr_name=company["hr_name"], hr_title=company["hr_title"],
        mgr_name=company["manager_name"], mgr_title=company["manager_title"],
        emp=dict(name=emp["full_name"], id=emp["employee_id"], position=emp["position"],
                 department=emp["department"], sss=emp["sss_no"], philhealth=emp["philhealth_no"],
                 pagibig=emp["pagibig_no"], tin=emp["tin_no"]),
        pay_date=fdate(period["pay_date"]), pay_type="Semi-monthly",
        cutoff=period.get("kinsena", "").replace("Kinsena", "Cutoff"),
        monthly=peso(monthly), daily=peso(daily),
        period_line=f"Period: {fdate(period['start'])} - {fdate(period['end'])}   |   Cut-off duration: {cal_days} days",
        attend_line=f"Days worked: {worked:g} / {expected:g}   |   Absent: {absent:g}   |   Late: {late:g} min",
        earnings=earnings, gross=r["gross"], deductions=deductions, total_ded=r["total_ded"], net=r["net"],
        note="Holiday pay shows only the extra premium - the day's regular pay is already inside Basic Pay.",
        status=status, approved_by=approved_by)


# ================================================================ SCREEN VIEW
"""Live Preview GUI Canvas (PayslipView)"""
class PayslipView(ttk.Frame):
    """Scrollable white 'paper' that redraws from a model dict. Cheap enough to redraw on every keystroke."""

    def __init__(self, parent):
        super().__init__(parent)
        self.sf = theme.ScrollFrame(self, bg=theme.CANVAS)
        self.sf.pack(fill="both", expand=True)
        self.paper = tk.Frame(self.sf.inner, bg=PAPER, padx=24, pady=14, highlightthickness=1,
                              highlightbackground=theme.LINE)
        self.paper.pack(fill="x", padx=14, pady=10)

    # removes everything drawn on the paper
    def _clear(self):
        for w in self.paper.winfo_children():
            w.destroy()

    # shows a plain message instead of a payslip
    def show_message(self, text):
        self._clear()
        tk.Label(self.paper, text=text, bg=PAPER, fg=theme.MUTED, font=(theme.FONT, 11), pady=120).pack()

    # redraws the payslip from the model
    def show(self, m):
        keep = self.sf.canvas.yview()[0]          # stay where the user scrolled to while typing
        self._clear()
        self._draw(m)
        self.update_idletasks()
        self.sf.canvas.yview_moveto(keep)

    # draws the payslip piece by piece
    def _draw(self, m):
        P, F = self.paper, theme.FONT

        # small helper to make a label
        def lab(parent, text, size=9, bold=False, fg=theme.TEXT, bg=PAPER, anchor="w", italic=False, **kw):
            style = ("bold" if bold else "normal") + (" italic" if italic else "")
            return tk.Label(parent, text=text, bg=bg, fg=fg, anchor=anchor, justify="left",
                            font=(F, size, style.strip()), **kw)

        # ---- company + title
        head = tk.Frame(P, bg=PAPER)
        head.pack(fill="x")
        left = tk.Frame(head, bg=PAPER)
        left.pack(side="left")
        lab(left, m["company"]["name"], 17, True, theme.BLUE).pack(anchor="w")
        lab(left, m["company"]["address"], 8).pack(anchor="w")
        lab(left, f"TIN: {m['company']['tin']}" + (f"   |   {m['company']['contact']}" if m["company"]["contact"] else ""), 8).pack(anchor="w")
        lab(head, "PAYSLIP", 20, True, theme.BLUE).pack(side="right", anchor="n")

        # ---- employee box (left) + pay indicators (right)
        row = tk.Frame(P, bg=PAPER)
        row.pack(fill="x", pady=(12, 4))
        row.columnconfigure((0, 1), weight=1, uniform="a")
        e, box = m["emp"], tk.Frame(row, bg=PAPER)
        box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        lab(box, "  EMPLOYEE INFORMATION", 8, True, "white", HDR).pack(fill="x", ipady=2)
        lab(box, e["name"], 10, True).pack(anchor="w", padx=4, pady=(6, 0))
        lab(box, f"{e['position']} - {e['department']}", 8).pack(anchor="w", padx=4)
        for t, v in (("SSS No.", e["sss"]), ("PhilHealth No.", e["philhealth"]),
                     ("Pag-IBIG MID", e["pagibig"]), ("TIN", e["tin"])):
            lab(box, f"{t}: {v or '-'}", 8).pack(anchor="w", padx=4, pady=(3, 0))

        meta = tk.Frame(row, bg=PAPER)
        meta.grid(row=0, column=1, sticky="nsew")
        meta.columnconfigure((0, 1, 2), weight=1, uniform="m")
        grid = [("PAY DATE", "PAY TYPE", "PERIOD"), (m["pay_date"], m["pay_type"], m["cutoff"]),
                ("EMPLOYEE ID", "MONTHLY SALARY", "DAILY RATE"), (e["id"], m["monthly"], m["daily"])]
        for r_, vals in enumerate(grid):
            for c_, v in enumerate(vals):
                hdr = r_ % 2 == 0
                lab(meta, v, 8 if hdr else 9, True, "white" if hdr else theme.TEXT,
                    HDR if hdr else LIGHT, anchor="center").grid(row=r_, column=c_, sticky="nsew", padx=1, pady=1, ipady=3)

        lab(P, m["period_line"], 8, True).pack(anchor="w", pady=(6, 0))
        lab(P, m["attend_line"], 8).pack(anchor="w")

        # ---- tables
        # helper that draws a table with a header, rows and a total line
        def table(headers, rows, weights, aligns, foot):
            t = tk.Frame(P, bg=PAPER)
            t.pack(fill="x", pady=(6, 0))
            for c, w in enumerate(weights):
                t.columnconfigure(c, weight=w, uniform="t")

            def put(r_, vals, bold=False, bg=PAPER, size=9, fg=theme.TEXT):
                for c, v in enumerate(vals):
                    anchor = aligns[c]
                    lab(t, v, size, bold, fg, bg, anchor=anchor).grid(row=r_, column=c, sticky="ew", ipady=1, ipadx=4)

            put(0, headers, True, GRAY, 8)
            for i, vals in enumerate(rows, start=1):
                put(i, vals)
            n = len(rows) + 1
            tk.Frame(t, bg="#8A93A3", height=1).grid(row=n, column=0, columnspan=len(weights), sticky="ew", pady=(3, 0))
            put(n + 1, foot, True, PAPER, 10)
            return t

        table(["EARNINGS", "HOURS / DAYS", "RATE", "AMOUNT"],
              [(a, b, c, peso(d)) for a, b, c, d in m["earnings"]], (5, 2, 2, 2), ("w", "center", "e", "e"),
              ("", "", "GROSS PAY", f"PHP {peso(m['gross'])}"))
        lab(P, m["note"], 7, False, theme.MUTED, italic=True).pack(anchor="w", pady=(2, 0))
        tk.Frame(P, bg=PAPER, height=8).pack()
        table(["DEDUCTIONS", "DETAILS", "AMOUNT"],
              [(a, b, peso(c)) for a, b, c in m["deductions"]], (5, 4, 2), ("w", "w", "e"),
              ("", "TOTAL DEDUCTIONS", f"PHP {peso(m['total_ded'])}"))

        # ---- net pay
        """Renders the highlighted Net Pay summary bar at the bottom of the slip"""
        net = tk.Frame(P, bg=GRAY)
        net.pack(fill="x", pady=(12, 0))
        lab(net, "NET PAY", 10, True, bg=GRAY).pack(side="left", padx=12, pady=7)
        lab(net, f"PHP {peso(m['net'])}", 13, True, bg=GRAY).pack(side="right", padx=12)

        # ---- signatures
        sig = tk.Frame(P, bg=PAPER)
        sig.pack(fill="x", pady=(34, 0))
        sig.columnconfigure((0, 1, 2), weight=1, uniform="s")
        people = [(m["hr_name"], f"Prepared by ({m['hr_title']})"),
                  (m["mgr_name"], f"Approved by ({m['mgr_title']})"),
                  (e["name"], "Received by")]
        for c, (name, role) in enumerate(people):
            cell = tk.Frame(sig, bg=PAPER)
            cell.grid(row=0, column=c, padx=16, sticky="ew")
            tk.Frame(cell, bg=theme.TEXT, height=1).pack(fill="x")
            lab(cell, name, 8, anchor="center").pack(fill="x", pady=(2, 0))
            lab(cell, role, 8, italic=True, anchor="center").pack(fill="x")
        if m["status"] == "approved":
            lab(P, f"Approved in system by: {m['approved_by']}", 8, True, theme.GREEN, anchor="center").pack(fill="x", pady=(10, 0))
        lab(P, f"If you have any questions about this payslip, please contact: {m['hr']}", 8, True,
            anchor="center").pack(fill="x", pady=(14, 0))


# ===================================================================== PDF
def export_pdf(m, path):
    """Draw the model on an A4 page (needs: pip install reportlab)."""
    # reportlab is only needed when saving a PDF
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    blue, hdr = colors.HexColor(theme.BLUE), colors.HexColor(HDR)
    gray, light = colors.HexColor(GRAY), colors.HexColor(LIGHT)

    # helper for text styles
    def ps(size=8.5, bold=False, color=colors.black, **kw):
        kw.setdefault("leading", size * 1.3)
        return ParagraphStyle("s", fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size,
                              textColor=color, **kw)

    # usable page width
    W = 180 * mm
    story = []

    # company name and PAYSLIP title
    head = Table([[[Paragraph(m["company"]["name"], ps(18, True, blue, leading=22)),
                    Paragraph(m["company"]["address"], ps(8)),
                    Paragraph(f"TIN: {m['company']['tin']}" + (f" | {m['company']['contact']}" if m["company"]["contact"] else ""), ps(8))],
                   Paragraph("PAYSLIP", ps(22, True, blue, alignment=TA_RIGHT, leading=26))]],
                 colWidths=[W * 0.68, W * 0.32])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [head, Spacer(1, 7 * mm)]

    # employee info box and the pay details grid
    e = m["emp"]
    box = Table([[Paragraph("EMPLOYEE INFORMATION", ps(7.5, True, colors.white))],
                 [Paragraph(e["name"], ps(10, True))],
                 [Paragraph(f"{e['position']} - {e['department']}", ps(8))],
                 [Paragraph(f"SSS No.: {e['sss'] or '-'}", ps(8))],
                 [Paragraph(f"PhilHealth No.: {e['philhealth'] or '-'}", ps(8))],
                 [Paragraph(f"Pag-IBIG MID: {e['pagibig'] or '-'}", ps(8))],
                 [Paragraph(f"TIN: {e['tin'] or '-'}", ps(8))]], colWidths=[86 * mm])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), hdr), ("TOPPADDING", (0, 1), (-1, -1), 1.5),
                             ("BOTTOMPADDING", (0, 1), (-1, -1), 1.5)]))
    hs, vs = ps(7, True, colors.white, alignment=TA_CENTER), ps(8.5, True, alignment=TA_CENTER)
    meta = Table([[Paragraph(t, hs) for t in ("PAY DATE", "PAY TYPE", "PERIOD")],
                  [Paragraph(t, vs) for t in (m["pay_date"], m["pay_type"], m["cutoff"])],
                  [Paragraph(t, hs) for t in ("EMPLOYEE ID", "MONTHLY SALARY", "DAILY RATE")],
                  [Paragraph(t, vs) for t in (e["id"], m["monthly"], m["daily"])]], colWidths=[30 * mm] * 3)
    meta.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), hdr), ("BACKGROUND", (0, 2), (-1, 2), hdr),
                              ("BACKGROUND", (0, 1), (-1, 1), light), ("BACKGROUND", (0, 3), (-1, 3), light),
                              ("GRID", (0, 0), (-1, -1), 1.2, colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    outer = Table([[box, meta]], colWidths=[W - 90 * mm, 90 * mm])
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [outer, Spacer(1, 4 * mm), Paragraph(m["period_line"], ps(8, True)),
              Paragraph(m["attend_line"], ps(8)), Spacer(1, 2 * mm)]

    # helper that builds a table with a header and a total row
    def grid(rows, widths, head_row, total_row, aligns):
        t = Table([head_row] + rows + [total_row], colWidths=widths)
        n = len(rows) + 1
        style = [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                 ("BACKGROUND", (0, 0), (-1, 0), gray), ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                 ("LINEABOVE", (0, n), (-1, n), 0.8, colors.HexColor("#8A93A3")),
                 ("FONTNAME", (0, n), (-1, n), "Helvetica-Bold"), ("FONTSIZE", (0, n), (-1, n), 9.5),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                 ("LINEBELOW", (0, 1), (-1, n - 1), 0.25, colors.HexColor("#E3E6EC"))]
        style += [("ALIGN", (c, 0), (c, -1), a) for c, a in enumerate(aligns)]
        t.setStyle(TableStyle(style))
        return t

    story.append(grid([[a, b, c, peso(d)] for a, b, c, d in m["earnings"]], [78 * mm, 34 * mm, 34 * mm, 34 * mm],
                      ["EARNINGS", "HOURS / DAYS", "RATE", "AMOUNT"],
                      ["", "", "GROSS PAY", f"PHP {peso(m['gross'])}"], ("LEFT", "CENTER", "RIGHT", "RIGHT")))
    story += [Spacer(1, 1.5 * mm), Paragraph(m["note"], ps(7, False, colors.HexColor(theme.MUTED))), Spacer(1, 5 * mm)]
    """Converts deduction tuples from build_model() directly into a ReportLab Table"""
    story.append(grid([[a, b, peso(c)] for a, b, c in m["deductions"]], [78 * mm, 68 * mm, 34 * mm],
                      ["DEDUCTIONS", "DETAILS", "AMOUNT"],
                      ["", "TOTAL DEDUCTIONS", f"PHP {peso(m['total_ded'])}"], ("LEFT", "LEFT", "RIGHT")))
    story.append(Spacer(1, 6 * mm))

    # net pay bar
    net = Table([[Paragraph("NET PAY", ps(11, True)), Paragraph(f"PHP {peso(m['net'])}", ps(14, True, alignment=TA_RIGHT, leading=18))]],
                colWidths=[W / 2, W / 2])
    net.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), gray), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    story += [net, Spacer(1, 22 * mm)]

    # signature lines
    c = ps(8, False, alignment=TA_CENTER)
    ci = ParagraphStyle("i", parent=c, fontName="Helvetica-Oblique")
    """Generates formal document footer with signature baselines for HR, Manager, and Employee"""
    sig = Table([[Paragraph(m["hr_name"], c), "", Paragraph(m["mgr_name"], c), "", Paragraph(e["name"], c)],
                 [Paragraph(f"Prepared by ({m['hr_title']})", ci), "",
                  Paragraph(f"Approved by ({m['mgr_title']})", ci), "", Paragraph("Received by", ci)]],
                colWidths=[52 * mm, 12 * mm, 52 * mm, 12 * mm, 52 * mm])
    sig.setStyle(TableStyle([("LINEABOVE", (0, 0), (0, 0), 0.8, colors.black), ("LINEABOVE", (2, 0), (2, 0), 0.8, colors.black),
                             ("LINEABOVE", (4, 0), (4, 0), 0.8, colors.black), ("TOPPADDING", (0, 0), (-1, -1), 1),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story.append(sig)
    if m["status"] == "approved":
        story += [Spacer(1, 3 * mm), Paragraph(f"Approved in system by: {m['approved_by']}",
                                               ps(8, True, colors.HexColor(theme.GREEN), alignment=TA_CENTER))]
    story += [Spacer(1, 8 * mm),
              Paragraph(f"If you have any questions about this payslip, please contact: {m['hr']}", ps(8, True, alignment=TA_CENTER))]

    # builds the PDF file
    SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                      bottomMargin=15 * mm, title=f"Payslip - {e['name']}").build(story)


# asks where to save, then makes the PDF
def export_pdf_dialog(model, default_name="payslip.pdf", parent=None):
    path = filedialog.asksaveasfilename(parent=parent, defaultextension=".pdf", initialfile=default_name,
                                        filetypes=[("PDF", "*.pdf")])
    if not path:
        return
    try:
        export_pdf(model, path)
        messagebox.showinfo("Save as PDF", f"Saved:\n{path}", parent=parent)
    except ImportError:
        messagebox.showerror("Save as PDF", "reportlab is not installed.\nRun:  pip install reportlab", parent=parent)
    except OSError as ex:
        messagebox.showerror("Save as PDF", f"Could not write the file:\n{ex}", parent=parent)


class PayslipPreview(tk.Toplevel):
    """Pop-up used by the Saved Payslips tab."""

    def __init__(self, parent, model, file_name="payslip.pdf"):
        super().__init__(parent)
        self.title("Payslip Preview")
        self.geometry("720x820")
        self.configure(bg=theme.BG)
        view = PayslipView(self)
        view.pack(fill="both", expand=True)
        view.show(model)
        bar = ttk.Frame(self, padding=(14, 10))
        bar.pack(fill="x")
        ttk.Button(bar, text="Save as PDF", style="Primary.TButton",
                   command=lambda: export_pdf_dialog(model, file_name, self)).pack(side="left")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
