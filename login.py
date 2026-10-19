"""login.py - login screen. ask_login() returns {'username','role'} or None."""
import tkinter as tk
from tkinter import ttk, messagebox
import database as db
import theme


def ask_login():
    result = {}
    root = tk.Tk()
    root.title("Payslip System - Login")
    root.resizable(False, False)
    root.minsize(400, 300)
    theme.apply_theme(root)
    f = ttk.Frame(root, padding=(36, 28))
    f.pack()
    ttk.Label(f, text="PAYSLIP SYSTEM", style="Title.TLabel", font=(theme.FONT, 16, "bold")).grid(
        row=0, column=0, columnspan=2, pady=(0, 2))
    ttk.Label(f, text="Sign in as HR or Manager", foreground=theme.MUTED).grid(
        row=1, column=0, columnspan=2, pady=(0, 16))
    u, p = tk.StringVar(), tk.StringVar()
    ttk.Label(f, text="Username").grid(row=2, column=0, sticky="w", pady=4)
    ue = ttk.Entry(f, textvariable=u, width=24)
    ue.grid(row=2, column=1, padx=(10, 0))
    ttk.Label(f, text="Password").grid(row=3, column=0, sticky="w", pady=4)
    ttk.Entry(f, textvariable=p, show="*", width=24).grid(row=3, column=1, padx=(10, 0))

    def attempt(_=None):
        user = db.authenticate(u.get(), p.get())
        if user:
            result.update(user)
            root.destroy()
        else:
            messagebox.showerror("Login", "Invalid username or password.")

    ttk.Button(f, text="Login", style="Primary.TButton", command=attempt).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(18, 0))
    root.bind("<Return>", attempt)
    ue.focus()
    root.mainloop()
    return result or None
