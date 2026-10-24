"""
theme.py


INDEX  (function - line number)
  apply_theme()            - 32
  _on_wheel()              - 110
  Card                     - 121
      __init__()           - 124
  NavItem                  - 134
      __init__()           - 137
      _paint()             - 150
      set_active()         - 156
  make_tree()              - 161
  ScrollFrame              - 178
      __init__()           - 181
"""

"""theme.py - colours, ttk styles and small UI helpers (Card, NavItem, tree helper, ScrollFrame) shared by every window."""
import tkinter as tk
from tkinter import ttk, font as tkfont

# --- palette ---------------------------------------------------------------
BLUE, BLUE_DK, BLUE_LT = "#2563EB", "#1D4ED8", "#EAF1FF"      # accent (kept under the old names)
SIDEBAR, SIDEBAR_HI, SIDEBAR_TXT = "#0F172A", "#1E293B", "#94A3B8"
BG, CARD, LINE, CANVAS = "#F5F7FA", "#FFFFFF", "#E2E8F0", "#E8ECF2"
TEXT, MUTED, RED, GREEN, AMBER = "#0F172A", "#64748B", "#B42318", "#15803D", "#B45309"
ZEBRA = "#F8FAFC"
FONT = "Segoe UI"          # replaced by the first installed font in apply_theme()

_SCROLLERS = []            # canvases that react to the mouse wheel


# sets the fonts and colors for all the widgets
def apply_theme(root):
    global FONT
    # pick the first font that is installed
    families = set(tkfont.families(root))
    FONT = next((f for f in ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter",
                             "Arial", "DejaVu Sans") if f in families), "TkDefaultFont")
    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox.background", "white")
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", BLUE)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    root.option_add("*TCombobox*Listbox.font", (FONT, 10))
    # styles for labels, inputs, buttons, tables and scrollbars
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", font=(FONT, 10), background=BG, foreground=TEXT, bordercolor=LINE,
                 lightcolor=BG, darkcolor=BG, focuscolor=BG, troughcolor=BG)
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=CARD)
    st.configure("TLabel", background=BG, foreground=TEXT)
    st.configure("Card.TLabel", background=CARD, foreground=TEXT)
    st.configure("Field.TLabel", background=CARD, foreground=MUTED, font=(FONT, 9))
    st.configure("Hint.TLabel", background=CARD, foreground=MUTED, font=(FONT, 9))
    st.configure("Info.TLabel", background=BLUE_LT, foreground=BLUE_DK, font=(FONT, 9, "bold"), padding=(10, 7))
    st.configure("Error.TLabel", background=BG, foreground=RED, font=(FONT, 9))
    st.configure("Ok.TLabel", background=BG, foreground=GREEN, font=(FONT, 9, "bold"))
    st.configure("Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 18, "bold"))
    st.configure("Sub.TLabel", background=BG, foreground=MUTED, font=(FONT, 10))

    st.configure("TLabelframe", background=CARD, bordercolor=LINE, relief="solid", borderwidth=1,
                 lightcolor=CARD, darkcolor=CARD)
    st.configure("TLabelframe.Label", background=CARD, foreground=TEXT, font=(FONT, 10, "bold"))

    entry = dict(fieldbackground="white", bordercolor=LINE, padding=(8, 7), lightcolor="white", darkcolor="white")
    st.configure("TEntry", **entry)
    st.map("TEntry", fieldbackground=[("readonly", "#F1F5F9")], foreground=[("readonly", TEXT)],
           bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)], darkcolor=[("focus", BLUE)])
    st.configure("Big.TEntry", **{**entry, "padding": (10, 9)})
    st.map("Big.TEntry", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)], darkcolor=[("focus", BLUE)])
    st.configure("TCombobox", background="white", arrowcolor=MUTED, **entry)
    st.map("TCombobox", fieldbackground=[("readonly", "white")], bordercolor=[("focus", BLUE)],
           lightcolor=[("focus", BLUE)], darkcolor=[("focus", BLUE)], arrowcolor=[("active", BLUE)])
    st.configure("TSpinbox", arrowcolor=MUTED, background="white", **entry)
    st.map("TSpinbox", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)], darkcolor=[("focus", BLUE)])
    st.configure("TCheckbutton", background=CARD, foreground=TEXT)
    st.map("TCheckbutton", background=[("active", CARD)])

    flat = dict(relief="flat", borderwidth=1)
    st.configure("TButton", padding=(14, 9), background="white", foreground=TEXT, bordercolor=LINE,
                 lightcolor="white", darkcolor="white", font=(FONT, 10, "bold"), **flat)
    st.map("TButton", background=[("active", "#F1F5F9")], bordercolor=[("active", "#CBD5E1")])
    st.configure("Primary.TButton", background=BLUE, foreground="white", bordercolor=BLUE,
                 lightcolor=BLUE, darkcolor=BLUE)
    st.map("Primary.TButton", background=[("active", BLUE_DK), ("pressed", BLUE_DK)], bordercolor=[("active", BLUE_DK)],
           foreground=[("active", "white")], lightcolor=[("active", BLUE_DK)], darkcolor=[("active", BLUE_DK)])
    st.configure("Link.TButton", padding=(6, 3), background=CARD, foreground=BLUE, bordercolor=CARD,
                 lightcolor=CARD, darkcolor=CARD, font=(FONT, 9, "bold"))
    st.map("Link.TButton", background=[("active", BLUE_LT)], bordercolor=[("active", BLUE_LT)],
           lightcolor=[("active", BLUE_LT)], darkcolor=[("active", BLUE_LT)])

    st.configure("Vertical.TScrollbar", troughcolor=BG, background="#CBD5E1", bordercolor=BG, relief="flat",
                 arrowcolor=BG, lightcolor="#CBD5E1", darkcolor="#CBD5E1", arrowsize=10, gripcount=0)
    st.map("Vertical.TScrollbar", background=[("active", "#94A3B8")])
    st.configure("Treeview", background="white", fieldbackground="white", rowheight=32, bordercolor=LINE,
                 borderwidth=0, font=(FONT, 10), lightcolor="white", darkcolor="white")
    st.configure("Treeview.Heading", background="#F1F5F9", foreground=MUTED, font=(FONT, 9, "bold"),
                 padding=(8, 8), relief="flat", borderwidth=0)
    st.map("Treeview.Heading", background=[("active", "#E2E8F0")])
    st.map("Treeview", background=[("selected", BLUE_LT)], foreground=[("selected", BLUE_DK)])
    st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # mouse wheel scrolling
    root.bind_all("<MouseWheel>", _on_wheel, add="+")
    root.bind_all("<Button-4>", _on_wheel, add="+")
    root.bind_all("<Button-5>", _on_wheel, add="+")


# scrolls the scroll area the mouse is over
def _on_wheel(e):
    w = e.widget.winfo_containing(e.x_root, e.y_root) if hasattr(e.widget, "winfo_containing") else None
    while w is not None:
        if w in _SCROLLERS:
            if w.yview() != (0.0, 1.0):
                up = e.num == 4 or getattr(e, "delta", 0) > 0
                w.yview_scroll(-3 if up else 3, "units")
            return
        w = w.master


class Card(tk.Frame):
    """White panel with a thin border and a bold title. Put widgets in .body (a ttk Card.TFrame)."""

    def __init__(self, parent, title, subtitle=None):
        super().__init__(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE, highlightcolor=LINE)
        tk.Label(self, text=title, bg=CARD, fg=TEXT, font=(FONT, 11, "bold"), anchor="w").pack(
            fill="x", padx=18, pady=(14, 0))
        if subtitle:
            tk.Label(self, text=subtitle, bg=CARD, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", padx=18)
        self.body = ttk.Frame(self, style="Card.TFrame", padding=(14, 8, 14, 14))
        self.body.pack(fill="x")


class NavItem(tk.Frame):
    """Top-bar tab; shows an accent underline when selected."""

    def __init__(self, parent, text, command):
        super().__init__(parent, bg=SIDEBAR, cursor="hand2")
        self.lbl = tk.Label(self, text=text, bg=SIDEBAR, fg=SIDEBAR_TXT, font=(FONT, 10), padx=16, pady=12)
        self.lbl.pack()
        self.bar = tk.Frame(self, bg=SIDEBAR, height=3)
        self.bar.pack(fill="x", side="bottom")
        self.active = False
        for w in (self, self.lbl):
            w.bind("<Button-1>", lambda _e: command())
            w.bind("<Enter>", lambda _e: self._paint(True))
            w.bind("<Leave>", lambda _e: self._paint(False))

    # highlights the tab when hovered or selected
    def _paint(self, hover=False):
        on = self.active or hover
        self.lbl.configure(fg="white" if on else SIDEBAR_TXT, font=(FONT, 10, "bold" if self.active else "normal"))
        self.bar.configure(bg=BLUE if self.active else SIDEBAR)

    # turns the highlight on or off
    def set_active(self, on):
        self.active = on
        self._paint()


def make_tree(parent, columns, heads, widths, right=()):
    """Bordered Treeview with scrollbar and zebra / status tags. Returns (frame, tree)."""
    box = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
    tree = ttk.Treeview(box, columns=columns, show="headings", selectmode="browse")
    for c, t, w in zip(columns, heads, widths):
        tree.heading(c, text=t, anchor="e" if c in right else "w")
        tree.column(c, width=w, anchor="e" if c in right else "w")
    vsb = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    tree.tag_configure("odd", background=ZEBRA)
    tree.tag_configure("approved", foreground=GREEN)
    tree.tag_configure("pending", foreground=AMBER)
    return box, tree


class ScrollFrame(ttk.Frame):
    """A frame whose .inner area scrolls vertically when it is taller than the window."""

    def __init__(self, parent, bg=BG):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        # keep the scroll area sized to its content
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))
        _SCROLLERS.append(self.canvas)
