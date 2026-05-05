"""
PDF Toolkit — Main App
-----------------------
A desktop GUI app combining two tools in one window:
  Tab 1: PDF Filler    — fills a PDF template with each row from an Excel sheet
  Tab 2: PDF Flattener — bakes form fields into permanent text

How it fits together:
  main_app.py       <- this file (the launcher)
  ├── pdf_filler.py     -> Tab 1
  ├── pdf_flattener.py  -> Tab 2
  └── utils.py          -> shared logging + helpers
"""

import tkinter as tk
from tkinter import ttk

from pdf_filler import PdfFillerTab
from pdf_flattener import PdfFlattenerTab


class PdfToolkitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Toolkit")
        self.geometry("820x680")
        self.minsize(740, 620)

        # Use a cleaner theme if available
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Top header
        header = ttk.Frame(self, padding=(16, 12, 16, 4))
        header.pack(fill="x")
        ttk.Label(header, text="PDF Toolkit",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(header,
                  text="Fill PDFs from Excel data, then flatten them to lock the data in.",
                  foreground="#666").pack(anchor="w")

        # Tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=8)

        filler_tab = PdfFillerTab(notebook)
        flattener_tab = PdfFlattenerTab(notebook)

        notebook.add(filler_tab, text="  1. Fill PDFs  ")
        notebook.add(flattener_tab, text="  2. Flatten PDFs  ")


def main():
    app = PdfToolkitApp()
    app.mainloop()


if __name__ == "__main__":
    main()
