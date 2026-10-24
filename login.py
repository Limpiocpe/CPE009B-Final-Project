"""login.py - login screen. ask_login() returns {'username','role'} or None."""
import tkinter as tk
from tkinter import ttk
import database as db
import theme

"""
login.py


INDEX  (function - line number)
  ask_login()              - 14
"""

# shows the login window, returns the user if correct, otherwise None
def ask_login():
    result = {}
    root = tk.Tk()
    root.title("Payslip System - Sign in")
    root.resizable(False, False)
    theme.apply_theme(root)
    w, h = 780, 460
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    F = theme.FONT

    # left panel with the title
    side = tk.Frame(root, bg=theme.SIDEBAR, width=300)
    side.pack(side="left", fill="y")
    side.pack_propagate(False)
    tk.Label(side, text="Payslip", bg=theme.SIDEBAR, fg="white", font=(F, 26, "bold")).pack(anchor="w", padx=32, pady=(64, 0))
    tk.Label(side, text="System", bg=theme.SIDEBAR, fg=theme.BLUE, font=(F, 26, "bold")).pack(anchor="w", padx=32)
    tk.Label(side, text="Semi-monthly payroll with SSS, PhilHealth,\nPag-IBIG and withholding tax built in.",
             bg=theme.SIDEBAR, fg=theme.SIDEBAR_TXT, font=(F, 10), justify="left").pack(anchor="w", padx=32, pady=(14, 0))

    # right side: username and password
    form = ttk.Frame(root, padding=(48, 0))
    form.pack(side="left", fill="both", expand=True)
    form.columnconfigure(0, weight=1)
    ttk.Label(form, text="Sign in", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(70, 0))
    ttk.Label(form, text="Use your HR or Manager account.", style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 22))

    u, p = tk.StringVar(), tk.StringVar()
    ttk.Label(form, text="Username").grid(row=2, column=0, sticky="w")
    ue = ttk.Entry(form, textvariable=u, style="Big.TEntry")
    ue.grid(row=3, column=0, sticky="ew", pady=(3, 12))
    ttk.Label(form, text="Password").grid(row=4, column=0, sticky="w")
    ttk.Entry(form, textvariable=p, show="\u2022", style="Big.TEntry").grid(row=5, column=0, sticky="ew", pady=(3, 6))
    err = ttk.Label(form, text="", style="Error.TLabel")
    err.grid(row=6, column=0, sticky="w")

    # runs when Sign in is clicked or Enter is pressed
    def attempt(_=None):
        user = db.authenticate(u.get(), p.get())
        if user:
            result.update(user)
            root.destroy()
        else:
            err.config(text="Wrong username or password. Check both and try again.")

    ttk.Button(form, text="Sign in", style="Primary.TButton", command=attempt).grid(row=7, column=0, sticky="ew", pady=(10, 0))
    root.bind("<Return>", attempt)
    ue.focus()
    # wait here until the window closes
    root.mainloop()
    return result or None
