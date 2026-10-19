"""theme.py - colours, ttk styles and a small scrollable-frame helper shared by every window."""
import tkinter as tk
from tkinter import ttk, font as tkfont

BLUE, BLUE_DK, BLUE_LT = "#2F5C99", "#244A7D", "#E8EEF7"
BG, CARD, LINE = "#F3F5F9", "#FFFFFF", "#D5DBE5"
TEXT, MUTED, RED, GREEN = "#1F2937", "#6B7280", "#B42318", "#1A7F4B"
FONT = "Segoe UI"          # replaced by the first installed font in apply_theme()

_SCROLLERS = []            # canvases that react to the mouse wheel


def apply_theme(root):
    global FONT
    families = set(tkfont.families(root))
    FONT = next((f for f in ("Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans") if f in families), "TkDefaultFont")
    root.configure(bg=BG)
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", font=(FONT, 10), background=BG, foreground=TEXT, bordercolor=LINE,
                 lightcolor=BG, darkcolor=BG, focuscolor=BG)
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=CARD)
    st.configure("TLabel", background=BG, foreground=TEXT)
    st.configure("Card.TLabel", background=CARD, foreground=TEXT)
    st.configure("Field.TLabel", background=CARD, foreground=MUTED, font=(FONT, 8))
    st.configure("Hint.TLabel", background=CARD, foreground=MUTED, font=(FONT, 9))
    st.configure("Info.TLabel", background=BLUE_LT, foreground=BLUE_DK, font=(FONT, 9, "bold"), padding=(8, 5))
    st.configure("Error.TLabel", background=BG, foreground=RED, font=(FONT, 9))
    st.configure("Ok.TLabel", background=BG, foreground=GREEN, font=(FONT, 9, "bold"))
    st.configure("Title.TLabel", background=BG, foreground=BLUE, font=(FONT, 12, "bold"))

    st.configure("TLabelframe", background=CARD, bordercolor=LINE, relief="solid", borderwidth=1,
                 lightcolor=CARD, darkcolor=CARD)
    st.configure("TLabelframe.Label", background=CARD, foreground=BLUE, font=(FONT, 10, "bold"))

    st.configure("TEntry", fieldbackground="white", bordercolor=LINE, padding=5,
                 lightcolor="white", darkcolor="white")
    st.map("TEntry", fieldbackground=[("readonly", "#EEF1F6")], foreground=[("readonly", TEXT)],
           bordercolor=[("focus", BLUE)])
    st.configure("TCombobox", fieldbackground="white", background="white", bordercolor=LINE, padding=5,
                 arrowcolor=BLUE, lightcolor="white", darkcolor="white")
    st.map("TCombobox", fieldbackground=[("readonly", "white")], bordercolor=[("focus", BLUE)])
    st.configure("TSpinbox", fieldbackground="white", bordercolor=LINE, padding=5, arrowcolor=BLUE,
                 lightcolor="white", darkcolor="white")
    st.map("TSpinbox", bordercolor=[("focus", BLUE)])
    st.configure("TCheckbutton", background=CARD, foreground=TEXT)
    st.map("TCheckbutton", background=[("active", CARD)])

    st.configure("TButton", padding=(12, 8), background="white", foreground=BLUE, bordercolor=BLUE,
                 lightcolor="white", darkcolor="white", font=(FONT, 10, "bold"))
    st.map("TButton", background=[("active", BLUE_LT)])
    st.configure("Primary.TButton", background=BLUE, foreground="white", bordercolor=BLUE,
                 lightcolor=BLUE, darkcolor=BLUE)
    st.map("Primary.TButton", background=[("active", BLUE_DK)], foreground=[("active", "white")])
    st.configure("Link.TButton", padding=(6, 2), background=CARD, foreground=BLUE, bordercolor=CARD,
                 lightcolor=CARD, darkcolor=CARD, font=(FONT, 9))
    st.map("Link.TButton", background=[("active", BLUE_LT)])

    st.configure("TNotebook", background=BG, borderwidth=0)
    st.configure("TNotebook.Tab", padding=(18, 8), background="#DDE4EF", foreground=TEXT, borderwidth=0)
    st.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", BLUE)])

    st.configure("Vertical.TScrollbar", troughcolor=BG, background="#C5CCD8", bordercolor=BG,
                 arrowcolor=BLUE_DK, lightcolor="#C5CCD8", darkcolor="#C5CCD8")
    st.configure("Treeview", background="white", fieldbackground="white", rowheight=26, bordercolor=LINE)
    st.configure("Treeview.Heading", background=BLUE_LT, foreground=BLUE_DK, font=(FONT, 9, "bold"), padding=5)
    st.map("Treeview", background=[("selected", BLUE)], foreground=[("selected", "white")])

    root.bind_all("<MouseWheel>", _on_wheel, add="+")
    root.bind_all("<Button-4>", _on_wheel, add="+")
    root.bind_all("<Button-5>", _on_wheel, add="+")


def _on_wheel(e):
    w = e.widget.winfo_containing(e.x_root, e.y_root) if hasattr(e.widget, "winfo_containing") else None
    while w is not None:
        if w in _SCROLLERS:
            if w.yview() != (0.0, 1.0):
                up = e.num == 4 or getattr(e, "delta", 0) > 0
                w.yview_scroll(-3 if up else 3, "units")
            return
        w = w.master


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
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))
        _SCROLLERS.append(self.canvas)
